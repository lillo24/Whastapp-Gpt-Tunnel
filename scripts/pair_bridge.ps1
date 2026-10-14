[CmdletBinding()]
param([string]$DataDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/store'))
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Write-Output 'Unofficial linked-device account risk applies. Use a private foreground terminal without recording/transcription.'
& (Join-Path $taskRoot 'bin/wa-bridge.exe') pair --data-dir $DataDir
if ($LASTEXITCODE -ne 0) { throw 'Manual pairing did not complete; no QR or raw error is logged.' }
