[CmdletBinding()]
param(
    [switch]$IncludeDatabase
)

$ErrorActionPreference = 'Stop'
$qhWorkspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$qhBackend = Join-Path $qhWorkspace 'agent-learning'
$qhFrontend = Join-Path $qhWorkspace 'Agent'
$qhPgCtl = Join-Path $qhWorkspace '.runtime\postgresql-17.10\pgsql\bin\pg_ctl.exe'
$qhPgData = Join-Path $qhWorkspace '.runtime\postgres-data'

function Get-QhProcessRecord {
    param([int]$ProcessId)
    return Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
}

function Test-QhOwnedListener {
    param(
        [Parameter(Mandatory)]$ProcessRecord,
        [Parameter(Mandatory)][int]$Port
    )

    $qhExecutable = [string]$ProcessRecord.ExecutablePath
    $qhCommandLine = [string]$ProcessRecord.CommandLine
    if ($Port -eq 5173) {
        return $qhCommandLine -match 'vite' -and $qhCommandLine.Contains($qhFrontend)
    }
    if ($Port -eq 8001) {
        return (
            $ProcessRecord.Name -eq 'python.exe' -and
            ($qhExecutable.StartsWith($qhWorkspace, [System.StringComparison]::OrdinalIgnoreCase) -or
             $qhCommandLine.Contains($qhBackend))
        )
    }
    return $false
}

function Get-QhOwnedProcessChain {
    param(
        [Parameter(Mandatory)]$ListenerProcess,
        [Parameter(Mandatory)][int]$Port
    )

    $qhChain = [System.Collections.Generic.List[int]]::new()
    $qhCurrent = $ListenerProcess
    for ($qhDepth = 0; $qhCurrent -and $qhDepth -lt 6; $qhDepth++) {
        if ($qhDepth -eq 0 -and -not (Test-QhOwnedListener -ProcessRecord $qhCurrent -Port $Port)) {
            return @()
        }
        $qhChain.Add([int]$qhCurrent.ProcessId)
        $qhParent = Get-QhProcessRecord -ProcessId ([int]$qhCurrent.ParentProcessId)
        if (-not $qhParent) {
            break
        }

        $qhParentExecutable = [string]$qhParent.ExecutablePath
        $qhParentCommandLine = [string]$qhParent.CommandLine
        $qhParentIsOwned = if ($Port -eq 5173) {
            $qhParentCommandLine.Contains($qhFrontend) -and
            $qhParent.Name -in @('node.exe', 'cmd.exe')
        } else {
            $qhParent.Name -eq 'python.exe' -and
            ($qhParentExecutable.StartsWith($qhWorkspace, [System.StringComparison]::OrdinalIgnoreCase) -or
             $qhParentCommandLine.Contains($qhBackend))
        }
        if (-not $qhParentIsOwned) {
            break
        }
        $qhCurrent = $qhParent
    }
    return $qhChain.ToArray()
}

$qhTargets = [System.Collections.Generic.List[int]]::new()
foreach ($qhPort in @(5173, 8001)) {
    $qhListeners = @(Get-NetTCPConnection -LocalPort $qhPort -State Listen -ErrorAction SilentlyContinue)
    foreach ($qhListener in $qhListeners) {
        $qhProcess = Get-QhProcessRecord -ProcessId ([int]$qhListener.OwningProcess)
        if (-not $qhProcess) {
            # Uvicorn reloaders can exit while a spawned worker keeps the inherited
            # listening socket. Windows then reports the vanished parent as owner.
            $qhOrphanWorkers = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
                $_.ParentProcessId -eq [int]$qhListener.OwningProcess
            })
            foreach ($qhOrphanWorker in $qhOrphanWorkers) {
                if (Test-QhOwnedListener -ProcessRecord $qhOrphanWorker -Port $qhPort) {
                    $qhProcess = $qhOrphanWorker
                    break
                }
            }
        }
        if (-not $qhProcess) {
            throw "端口 $qhPort 的监听 PID $($qhListener.OwningProcess) 不存在，且未找到可验证的轻衡子进程；已拒绝终止其他进程。"
        }
        $qhChain = @(Get-QhOwnedProcessChain -ListenerProcess $qhProcess -Port $qhPort)
        if (-not $qhChain.Count) {
            throw "端口 $qhPort 由非轻衡进程占用，已拒绝终止。"
        }
        foreach ($qhProcessId in $qhChain) {
            if (-not $qhTargets.Contains($qhProcessId)) {
                $qhTargets.Add($qhProcessId)
            }
        }
    }
}

if ($qhTargets.Count) {
    for ($qhIndex = $qhTargets.Count - 1; $qhIndex -ge 0; $qhIndex--) {
        Stop-Process -Id $qhTargets[$qhIndex] -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 500
    Write-Host "已关闭轻衡网页和 API（PID：$($qhTargets -join '、')）。" -ForegroundColor Green
} else {
    Write-Host '轻衡网页和 API 当前未运行。' -ForegroundColor Yellow
}

if ($IncludeDatabase) {
    foreach ($qhRequired in @($qhPgCtl, $qhPgData)) {
        if (-not (Test-Path -LiteralPath $qhRequired)) {
            throw "找不到数据库运行文件：$qhRequired"
        }
    }
    & $qhPgCtl status -D $qhPgData *> $null
    if ($LASTEXITCODE -eq 0) {
        & $qhPgCtl stop -D $qhPgData -m fast
        Write-Host '已关闭轻衡 PostgreSQL。' -ForegroundColor Green
    } else {
        Write-Host '轻衡 PostgreSQL 当前未运行。' -ForegroundColor Yellow
    }
}
