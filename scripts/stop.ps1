#Requires -Version 7.0
[CmdletBinding()]
param([string]$OpsDir=(Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'))
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskConfig=Get-WAOperations $OpsDir
foreach ($taskComponent in @('tunnel','bridge')) { Write-WAText (Join-Path $OpsDir ($taskComponent+'.stop')) '' }
Write-WAText (Join-Path $taskConfig.runtime_dir 'stop.request') ''
$taskRepo=Split-Path -Parent $PSScriptRoot
& (Join-Path $taskRepo 'bin/wa-bridge.exe') stop --data-dir $taskConfig.data_dir 2>$null
$taskStopped=$false
for ($taskSecond=0; $taskSecond -lt 13; $taskSecond++) {
    $taskIdle=$false; $taskLocks=$null
    try { $taskLocks=Open-WAIdleLocks $taskConfig $OpsDir; $taskIdle=$true }
    catch {} finally { if ($null -ne $taskLocks) { foreach ($taskHandle in $taskLocks) { $taskHandle.Dispose() } } }
    $taskChildren=@(
        (Get-WARecordedProcess (Join-Path $OpsDir 'bridge.state.json') (Join-Path $taskRepo 'bin/wa-bridge.exe')),
        (Get-WARecordedProcess (Join-Path $taskConfig.runtime_dir 'runtime-state.json') (Join-Path $taskRepo '.tools/tunnel-client/tunnel-client.exe'))
    ) | Where-Object { $null -ne $_ }
    if ($taskIdle -and -not @($taskChildren).Count) { $taskStopped=$true; break }
    foreach ($taskChild in $taskChildren) {
        try {
            # A killed launcher may leave its native child without a stop-file
            # watcher. Kill only the verified executable + exact creation time.
            if ($taskSecond -ge 8 -and -not $taskChild.HasExited) { $taskChild.Kill($true) }
        } finally { $taskChild.Dispose() }
    }
    Start-Sleep -Seconds 1
}
if (-not $taskStopped) { throw 'COMPONENTS_STILL_STOPPING: verify local process state before unregistering jobs.' }
Write-Output 'Collection and tunnel stopped. Databases, session credentials and backups are retained.'
