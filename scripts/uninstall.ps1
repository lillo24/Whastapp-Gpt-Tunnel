#Requires -Version 7.0
[CmdletBinding()]
param([string]$OpsDir=(Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'),[switch]$Apply,[switch]$ConfirmUninstall)
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskConfig=Get-WAOperations $OpsDir
if (-not $Apply) { Write-Output 'Preview: unregister the two owned startup tasks; retain all data, keys, session files and backups.'; exit 0 }
if (-not $ConfirmUninstall) { throw 'Explicit ConfirmUninstall is required.' }
& (Join-Path $PSScriptRoot 'stop.ps1') -OpsDir $OpsDir
$taskFolder=Get-WATaskService
foreach ($taskComponent in @('tunnel','bridge')) {
    $taskName=$taskConfig.task_prefix+'-'+(Get-Culture).TextInfo.ToTitleCase($taskComponent)
    $taskTask=Get-WATask $taskFolder $taskName
    if ($null -ne $taskTask) { Assert-WAOwnedTask $taskTask $taskComponent; $taskTask.Stop(0); $taskFolder.DeleteTask($taskName,0) }
}
Write-Output 'Owned startup tasks removed. All stored data and credentials retained.'
