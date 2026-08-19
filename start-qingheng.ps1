[CmdletBinding()]
param(
    [switch]$LocalOnly
)

$ErrorActionPreference = 'Stop'
$qhWorkspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$qhRuntime = Join-Path $qhWorkspace '.runtime'
$qhBackend = Join-Path $qhWorkspace 'agent-learning'
$qhFrontend = Join-Path $qhWorkspace 'Agent'
$qhPgBin = Join-Path $qhRuntime 'postgresql-17.10\pgsql\bin'
$qhPgCtl = Join-Path $qhPgBin 'pg_ctl.exe'
$qhPgReady = Join-Path $qhPgBin 'pg_isready.exe'
$qhPgData = Join-Path $qhRuntime 'postgres-data'
$qhPython = Join-Path $qhBackend '.venv\Scripts\python.exe'
$qhEnvFile = Join-Path $qhBackend '.env'
$qhNpm = (Get-Command npm.cmd -ErrorAction Stop).Source
$qhFrontendHost = if ($LocalOnly) { '127.0.0.1' } else { '0.0.0.0' }

foreach ($qhRequired in @($qhPgCtl, $qhPgReady, $qhPython, $qhEnvFile)) {
    if (-not (Test-Path -LiteralPath $qhRequired)) {
        throw "Missing local runtime file: $qhRequired"
    }
}

$qhDatabaseLine = Get-Content -LiteralPath $qhEnvFile | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $qhDatabaseLine) {
    $qhLegacyLine = Get-Content -LiteralPath $qhEnvFile | Where-Object { $_ -match '^CHECKPOINT_DATABASE_URL=' } | Select-Object -First 1
    if ($qhLegacyLine) {
        $env:DATABASE_URL = ($qhLegacyLine -split '=', 2)[1]
        Write-Warning 'Using legacy CHECKPOINT_DATABASE_URL; rename it to DATABASE_URL in .env.'
    } else {
        throw 'DATABASE_URL is missing from agent-learning\.env'
    }
}

& $qhPgReady -h 127.0.0.1 -p 5432 *> $null
if ($LASTEXITCODE -ne 0) {
    & $qhPgCtl start -D $qhPgData -l (Join-Path $qhRuntime 'postgresql.log')
}

$qhBackendOut = Join-Path $qhRuntime 'qingheng-backend.out.log'
$qhBackendErr = Join-Path $qhRuntime 'qingheng-backend.err.log'
$qhFrontendOut = Join-Path $qhRuntime 'qingheng-frontend.out.log'
$qhFrontendErr = Join-Path $qhRuntime 'qingheng-frontend.err.log'

$qhBackendProcess = Start-Process -FilePath $qhPython -ArgumentList @('-m', 'app.main') -WorkingDirectory $qhBackend -RedirectStandardOutput $qhBackendOut -RedirectStandardError $qhBackendErr -WindowStyle Hidden -PassThru
$qhFrontendProcess = Start-Process -FilePath $qhNpm -ArgumentList @('run', 'dev', '--', '--host', $qhFrontendHost) -WorkingDirectory $qhFrontend -RedirectStandardOutput $qhFrontendOut -RedirectStandardError $qhFrontendErr -WindowStyle Hidden -PassThru

try {
    $qhReady = $false
    for ($qhAttempt = 0; $qhAttempt -lt 30; $qhAttempt++) {
        try {
            $qhHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/api/v1/health' -TimeoutSec 2
            if ($qhHealth.status -eq 'ok') {
                $qhReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $qhReady) {
        throw "Backend startup timed out. Check $qhBackendErr"
    }

    Write-Host 'Qingheng local address: http://127.0.0.1:5173/' -ForegroundColor Green
    if (-not $LocalOnly) {
        $qhLanAddresses = [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
            Where-Object {
                $_.OperationalStatus -eq [System.Net.NetworkInformation.OperationalStatus]::Up -and
                $_.NetworkInterfaceType -notin @(
                    [System.Net.NetworkInformation.NetworkInterfaceType]::Loopback,
                    [System.Net.NetworkInformation.NetworkInterfaceType]::Tunnel
                ) -and
                $_.Name -notmatch 'VMware|Virtual|Hyper-V|vEthernet|VPN' -and
                $_.Description -notmatch 'VMware|Virtual|Hyper-V|vEthernet|VPN'
            } |
            ForEach-Object { $_.GetIPProperties().UnicastAddresses } |
            Where-Object {
                $_.Address.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
                $_.Address.IPAddressToString -notlike '169.254.*'
            } |
            ForEach-Object { $_.Address.IPAddressToString } |
            Sort-Object -Unique
        foreach ($qhLanAddress in $qhLanAddresses) {
            Write-Host "Qingheng LAN address: http://${qhLanAddress}:5173/" -ForegroundColor Cyan
        }
        try {
            $qhPublicProfiles = @(Get-NetConnectionProfile -ErrorAction Stop | Where-Object {
                $_.IPv4Connectivity -ne 'Disconnected' -and $_.NetworkCategory -eq 'Public'
            })
            if ($qhPublicProfiles.Count -gt 0) {
                Write-Warning 'The active network is Public. Windows may block LAN access. Only mark a trusted home/work network as Private, then run enable-qingheng-lan.ps1 as administrator.'
            }
        } catch {
            Write-Warning 'Could not read the Windows network profile. If another device cannot connect, run enable-qingheng-lan.ps1 as administrator.'
        }
        Write-Warning 'LAN mode has no account authentication. Use it only on a trusted private network.'
    }
    Write-Host "Backend log: $qhBackendOut"
    Write-Host "Frontend log: $qhFrontendOut"
    Write-Host 'Press Ctrl+C to stop the web processes. PostgreSQL will stay running.'

    while (-not $qhBackendProcess.HasExited -and -not $qhFrontendProcess.HasExited) {
        Start-Sleep -Seconds 1
        $qhBackendProcess.Refresh()
        $qhFrontendProcess.Refresh()
    }
    if ($qhBackendProcess.HasExited) { throw "Backend exited with code $($qhBackendProcess.ExitCode)" }
    if ($qhFrontendProcess.HasExited) { throw "Frontend exited with code $($qhFrontendProcess.ExitCode)" }
} finally {
    foreach ($qhProcess in @($qhBackendProcess, $qhFrontendProcess)) {
        if ($qhProcess -and -not $qhProcess.HasExited) {
            Stop-Process -Id $qhProcess.Id -Force
        }
    }
}
