#Requires -Version 7.0
[CmdletBinding()]
param([string]$OpsDir=(Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'),[switch]$IncludeMessages,[switch]$IncludeSession)
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskConfig=Get-WAOperations $OpsDir
if (-not $IncludeMessages -and -not $IncludeSession) { Write-Output 'Preview only. Opt in with IncludeMessages and/or IncludeSession. Session snapshots require a stopped collector.'; exit 0 }
$null=Initialize-WAPrivateFolder $taskConfig.backup_dir '.wa-backups'
$taskArgs=@()
if ($IncludeMessages) { $taskArgs+='--include-messages' }
if ($IncludeSession) { $taskArgs+='--include-session' }
Invoke-WAOperation $OpsDir backup $taskArgs
