#Requires -Version 7.0
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$DataDir,
      [string]$OpsDir=(Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'),
      [switch]$Apply,[switch]$ConfirmRealData)
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskConfig=Get-WAOperations $OpsDir
$taskNewStore=Assert-WALocalPath $DataDir
if (-not (Test-Path -LiteralPath (Assert-WALocalPath (Join-Path $taskNewStore '.wa-private-store')) -PathType Leaf) -or (Test-Path -LiteralPath (Join-Path $taskNewStore '.wa-restored-disconnected'))) { throw 'Use a newly paired private store, never a restored session copy.' }
$taskRepo=Split-Path -Parent $PSScriptRoot
$taskInspect='import sys,json,sqlite3; from pathlib import Path; p=Path(sys.argv[1]); d=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True); v=d.execute("PRAGMA user_version").fetchone()[0]; r=d.execute("SELECT linked,synthetic FROM collector_status WHERE singleton=1").fetchone(); print(json.dumps(v==1 and r==(1,0)))'
$taskReady=(& (Join-Path $taskRepo 'readonly_mcp/.venv/Scripts/python.exe') -I -c $taskInspect (Assert-WALocalPath (Join-Path $taskNewStore 'messages.db'))) | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $taskReady -ne $true) { throw 'A linked, non-synthetic schema-1 store is required.' }
if (-not $Apply) { @{applied=$false; paired_store_ready=$true; old_store_retained=$true; tunnel_scope_changed=$false; real_query_results_will_reach_chatgpt=$true} | ConvertTo-Json; exit 0 }
if (-not $ConfirmRealData) { throw 'Explicit ConfirmRealData is required after reviewing the preview.' }
Assert-WAUnregistered $taskConfig
$taskLocks=Open-WAIdleLocks $taskConfig $OpsDir
$taskNewLock=$null
try {
    $taskNewLock=[IO.File]::Open((Join-Path $taskNewStore 'collector.lock'),'Open','ReadWrite','None')
    $taskMetadataFile=Join-Path $taskConfig.runtime_dir 'connection.json'
    $taskOpsFile=Join-Path $OpsDir 'operations.json'
    $taskOldMetadata=[IO.File]::ReadAllText($taskMetadataFile)
    $taskOldOps=[IO.File]::ReadAllText($taskOpsFile)
    try {
        $taskMetadata=$taskOldMetadata | ConvertFrom-Json
        $taskMetadata.data_dir=$taskNewStore
        $taskConfig.data_dir=$taskNewStore; $taskConfig.synthetic=$false
        Write-WAText $taskMetadataFile ($taskMetadata | ConvertTo-Json)
        Write-WAText $taskOpsFile ($taskConfig | ConvertTo-Json)
        $null=Write-WATunnelProfile $taskConfig.runtime_dir
    } catch {
        Write-WAText $taskMetadataFile $taskOldMetadata; Write-WAText $taskOpsFile $taskOldOps
        throw 'Store activation rolled back.'
    }
    Write-Output 'Paired store activated locally. Old store retained; tunnel associations unchanged. Re-run install preview before registering startup tasks.'
} finally {
    if ($null -ne $taskNewLock) { $taskNewLock.Dispose() }
    foreach ($taskHandle in $taskLocks) { $taskHandle.Dispose() }
}
