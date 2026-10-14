#Requires -Version 7.0
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$BackupId,[Parameter(Mandatory=$true)][string]$Destination,
      [string]$OpsDir=(Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'),[switch]$Apply,[switch]$ConfirmRestore)
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskConfig=Get-WAOperations $OpsDir
$taskDestination=Assert-WALocalPath $Destination
$taskArgs=@('--backup-id',$BackupId,'--destination',$taskDestination)
# Always validate hashes and destination without touching a restore target first.
Invoke-WAOperation $OpsDir restore $taskArgs
if (-not $Apply) { exit 0 }
if (-not $ConfirmRestore) { throw 'Explicit ConfirmRestore is required after the dry-run.' }
$null=Initialize-WAPrivateFolder $taskDestination '.wa-restored-disconnected'
Invoke-WAOperation $OpsDir restore ($taskArgs+@('--apply'))
