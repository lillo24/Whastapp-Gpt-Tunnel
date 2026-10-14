[CmdletBinding()]
param([string]$DataDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/store'))
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $taskRoot 'bin/wa-bridge.exe') run --data-dir $DataDir
if ($LASTEXITCODE -ne 0) { throw 'Bridge stopped with a failure; inspect status.' }
