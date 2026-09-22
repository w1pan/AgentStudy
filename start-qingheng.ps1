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
$qhNode = (Get-Command node.exe -ErrorAction Stop).Source
$qhVite = Join-Path $qhFrontend 'node_modules\vite\bin\vite.js'
$qhFrontendHost = if ($LocalOnly) { '127.0.0.1' } else { '0.0.0.0' }

foreach ($qhRequired in @($qhPgCtl, $qhPgReady, $qhPython, $qhEnvFile, $qhVite)) {
    if (-not (Test-Path -LiteralPath $qhRequired)) {
        throw "Missing local runtime file: $qhRequired"
    }
}

function Assert-QhPortAvailable {
    param(
        [Parameter(Mandatory)]
        [int]$Port,
        [Parameter(Mandatory)]
        [string]$ServiceName
    )

    $qhListener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $qhListener) {
        return
    }

    $qhOwner = Get-Process -Id $qhListener.OwningProcess -ErrorAction SilentlyContinue
    $qhOwnerDescription = if ($qhOwner) {
        "$($qhOwner.ProcessName).exe (PID $($qhOwner.Id))"
    } else {
        "PID $($qhListener.OwningProcess)"
    }
    throw "$ServiceName port $Port is already in use by $qhOwnerDescription. Stop the existing process, then run this script again."
}

function Test-QhExistingBackend {
    try {
        $qhHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/api/v1/health' -TimeoutSec 2
        return $qhHealth.status -eq 'ok'
    } catch {
        return $false
    }
}

function Test-QhExistingFrontend {
    try {
        $qhResponse = Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -TimeoutSec 2 -UseBasicParsing
        return $qhResponse.StatusCode -eq 200 -and $qhResponse.Content -match '<title>轻衡'
    } catch {
        return $false
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

if ((Test-QhExistingBackend) -and (Test-QhExistingFrontend)) {
    Write-Host 'Qingheng is already running in another/background process: http://127.0.0.1:5173/' -ForegroundColor Yellow
    Write-Host 'This window does not own those processes, so Ctrl+C here cannot stop them.' -ForegroundColor Yellow
    Write-Host 'Run .\stop-qingheng.ps1 to stop the existing instance.' -ForegroundColor Cyan
    exit 0
}

Assert-QhPortAvailable -Port 8001 -ServiceName 'Backend'
Assert-QhPortAvailable -Port 5173 -ServiceName 'Frontend'

$qhBackendProcess = Start-Process -FilePath $qhPython -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8001') -WorkingDirectory $qhBackend -RedirectStandardOutput $qhBackendOut -RedirectStandardError $qhBackendErr -WindowStyle Hidden -PassThru
$qhFrontendProcess = Start-Process -FilePath $qhNode -ArgumentList @($qhVite, '--host', $qhFrontendHost, '--port', '5173', '--strictPort') -WorkingDirectory $qhFrontend -RedirectStandardOutput $qhFrontendOut -RedirectStandardError $qhFrontendErr -WindowStyle Hidden -PassThru

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
    if ($qhBackendProcess.HasExited) {
        $qhBackendProcess.Refresh()
        throw "Backend exited with code $($qhBackendProcess.ExitCode). Check $qhBackendErr"
    }
    if ($qhFrontendProcess.HasExited) {
        $qhFrontendProcess.Refresh()
        throw "Frontend exited with code $($qhFrontendProcess.ExitCode). Check $qhFrontendErr"
    }
} finally {
    foreach ($qhProcess in @($qhBackendProcess, $qhFrontendProcess)) {
        if ($qhProcess -and -not $qhProcess.HasExited) {
            Stop-Process -Id $qhProcess.Id -Force
        }
    }
}
