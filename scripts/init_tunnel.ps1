#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$TunnelId,
    [Parameter(Mandatory=$true)][string]$OrganizationId,
    [Parameter(Mandatory=$true)][string]$DataDir,
    [string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/tunnel')
)
. (Join-Path $PSScriptRoot 'tunnel_common.ps1')
if ($TunnelId -notmatch '^tunnel_[a-f0-9]{32}$' -or $OrganizationId -notmatch '^org-[A-Za-z0-9]+$') { throw 'Invalid tunnel association.' }
$taskData = Assert-WALocalPath $DataDir
$taskDir = Initialize-WATunnelDirectory $RuntimeDir
$taskFile = Join-Path $taskDir 'connection.json'
if (Test-Path -LiteralPath $taskFile) {
    $taskOld = Get-WATunnelMetadata $taskDir
    if ($taskOld.tunnel_id -ne $TunnelId -or $taskOld.organization_id -ne $OrganizationId -or $taskOld.data_dir -ne $taskData) { throw 'Existing tunnel association differs. Review it separately before changing it.' }
} else {
    Write-WAText $taskFile (@{schema_version=1; tunnel_id=$TunnelId; organization_id=$OrganizationId; data_dir=$taskData} | ConvertTo-Json)
}
$null = Write-WATunnelProfile $taskDir
Write-Output 'Protected local tunnel configuration prepared. No credential or connection created.'
