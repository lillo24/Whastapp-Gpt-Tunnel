#Requires -Version 7.0
[CmdletBinding()]
param([string]$OpsDir=(Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'),
      [switch]$MessagesAndSession,[switch]$Backups,[switch]$RuntimeCredentials,[switch]$OperationLogs,
      [switch]$Apply,[switch]$ConfirmDelete)
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskOps=Assert-WALocalPath $OpsDir
$taskConfig=Get-WAOperations $taskOps
$taskTargets=[Collections.Generic.List[string]]::new()
if ($MessagesAndSession) { $taskTargets.Add($taskConfig.data_dir) }
if ($Backups) { $taskTargets.Add($taskConfig.backup_dir) }
if ($RuntimeCredentials) { $taskTargets.Add($taskConfig.runtime_dir) }
if ($OperationLogs) { $taskTargets.Add($taskOps) }
if (-not $taskTargets.Count) { throw 'Select explicit deletion categories; no data was deleted.' }
$taskRepo=Split-Path -Parent $PSScriptRoot
$taskRoots=@((Assert-WALocalPath (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel')),(Assert-WALocalPath (Join-Path $taskRepo '.local-fixtures')))
foreach ($taskTarget in $taskTargets) {
    # Resolve and check each final absolute target before any recursive deletion.
    $taskChecked=Assert-WALocalPath $taskTarget
    if (-not @($taskRoots | Where-Object { $taskChecked.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase) }).Count) { throw 'Deletion is restricted to dedicated application or fixture child directories.' }
    if (-not (Test-Path -LiteralPath $taskChecked)) { continue }
    $taskMarker=if ($taskChecked -eq $taskConfig.data_dir) {'.wa-private-store'} elseif ($taskChecked -eq $taskConfig.runtime_dir) {'.wa-tunnel-runtime'} elseif ($taskChecked -eq $taskConfig.backup_dir) {'.wa-backups'} else {'.wa-operations'}
    if (-not (Test-Path -LiteralPath (Assert-WALocalPath (Join-Path $taskChecked $taskMarker)) -PathType Leaf)) { throw 'Unknown deletion target.' }
    $taskPending=[Collections.Generic.Stack[string]]::new(); $taskPending.Push($taskChecked)
    while ($taskPending.Count) {
        foreach ($taskItem in Get-ChildItem -Force -LiteralPath $taskPending.Pop()) {
            if ($taskItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Redirected deletion contents are refused.' }
            if ($taskItem.PSIsContainer) {
                if ($taskItem.Name -notmatch '^(?:backups|backup-[0-9TZ-]+[a-f0-9]{12})$') { throw 'Unexpected nested deletion directory.' }
                $taskPending.Push($taskItem.FullName)
            } elseif ($taskItem.Name -notmatch '^(?:\.wa-(?:private-store|restored-disconnected|tunnel-runtime|backups|operations)|(?:messages|whatsapp)\.db(?:-wal|-shm|-journal)?|pre-v1-[a-zA-Z0-9.-]+\.db|collector\.lock|stop\.request|connection\.json|tunnel-profile\.yaml|runtime-key\.dpapi|runtime\.lock|health\.url|runtime-state\.json|mcp-health\.json(?:\.tmp)?|manifest\.json|operations\.json|(?:bridge|tunnel)\.(?:lock|stop|state\.json|task\.xml|events(?:\.previous)?\.jsonl))$') { throw 'Unexpected deletion file; inspect it locally before proceeding.' }
        }
    }
}
if (-not $Apply) {
    @{applied=$false; targets=@($taskTargets); removes_local_data_only=$true; prior_chatgpt_results_retained=$true} | ConvertTo-Json
    exit 0
}
if (-not $ConfirmDelete) { throw 'Explicit ConfirmDelete is required after reviewing the preview.' }
Assert-WAUnregistered $taskConfig
$taskLocks=Open-WAIdleLocks $taskConfig $taskOps
foreach ($taskHandle in $taskLocks) { $taskHandle.Dispose() }
foreach ($taskTarget in $taskTargets) {
    $taskChecked=Assert-WALocalPath $taskTarget
    if (-not @($taskRoots | Where-Object { $taskChecked.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase) }).Count) { throw 'Deletion boundary changed.' }
    if (Test-Path -LiteralPath $taskChecked) { Remove-Item -LiteralPath $taskChecked -Recurse -Force }
}
Write-Output 'Selected local data removed. Revoke remote credentials, disconnect the app and unlink the phone separately. Prior ChatGPT results remain.'
