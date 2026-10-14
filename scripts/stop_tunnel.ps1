#Requires -Version 7.0
[CmdletBinding()]
param([string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/tunnel'))
. (Join-Path $PSScriptRoot 'tunnel_common.ps1')
$taskDir = Initialize-WATunnelDirectory $RuntimeDir
Write-WAText (Join-Path $taskDir 'stop.request') ''
Write-Output 'Local tunnel stop requested. Stored data and credentials retained.'
