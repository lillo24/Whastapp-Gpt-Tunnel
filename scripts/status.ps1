#Requires -Version 7.0
[CmdletBinding()]
param([string]$OpsDir=(Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'))
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskConfig=Get-WAOperations $OpsDir
$taskData=Invoke-WAOperation $OpsDir status | ConvertFrom-Json
$taskTunnel=(& (Join-Path $PSScriptRoot 'check_tunnel.ps1') -RuntimeDir $taskConfig.runtime_dir) | ConvertFrom-Json
[pscustomobject]@{local_data=$taskData; tunnel=$taskTunnel; history_complete=$false} | ConvertTo-Json -Depth 8
