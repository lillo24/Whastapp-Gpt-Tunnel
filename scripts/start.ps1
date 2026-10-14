#Requires -Version 7.0
[CmdletBinding()]
param([string]$OpsDir=(Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'))
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskConfig=Get-WAOperations $OpsDir
$taskFolder=Get-WATaskService
foreach ($taskComponent in @('bridge','tunnel')) {
    $taskName=$taskConfig.task_prefix+'-'+(Get-Culture).TextInfo.ToTitleCase($taskComponent)
    $taskTask=Get-WATask $taskFolder $taskName
    if ($null -eq $taskTask) { throw 'Tasks are not installed; review install.ps1.' }
    Assert-WAOwnedTask $taskTask $taskComponent
    $null=$taskTask.Run($null)
}
Write-Output 'Start requested in bridge/tunnel order. Check status; request acceptance is not readiness.'
