[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$qhRuleName = 'Qingheng LAN (TCP 5173)'

$qhIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$qhPrincipal = [System.Security.Principal.WindowsPrincipal]::new($qhIdentity)
$qhIsAdministrator = $qhPrincipal.IsInRole(
    [System.Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $qhIsAdministrator) {
    throw '请以管理员身份打开 PowerShell，再运行 .\enable-qingheng-lan.ps1'
}

$qhActiveProfiles = @(Get-NetConnectionProfile | Where-Object {
    $_.IPv4Connectivity -ne 'Disconnected'
})
if (-not $qhActiveProfiles) {
    throw '没有检测到活动的 IPv4 网络。'
}

$qhPublicProfiles = @($qhActiveProfiles | Where-Object { $_.NetworkCategory -eq 'Public' })
if ($qhPublicProfiles.Count -gt 0) {
    $qhNames = ($qhPublicProfiles.InterfaceAlias -join '、')
    throw "当前网络（${qhNames}）是公用网络。请仅在确认是可信家庭/办公网络后，通过 Windows 设置将它改为专用网络，再重新运行本脚本。"
}

$qhNode = (Get-Command node.exe -ErrorAction Stop).Source
$qhExistingRule = Get-NetFirewallRule -DisplayName $qhRuleName -ErrorAction SilentlyContinue
if ($qhExistingRule) {
    Write-Host "防火墙规则已存在：$qhRuleName" -ForegroundColor Green
    exit 0
}

New-NetFirewallRule `
    -DisplayName $qhRuleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 5173 `
    -Profile Private `
    -RemoteAddress LocalSubnet `
    -Program $qhNode `
    -EdgeTraversalPolicy Block | Out-Null

Write-Host '轻衡局域网规则已启用：仅专用网络、本地子网、Node 和 TCP 5173。' -ForegroundColor Green
