[CmdletBinding()]
param([string]$DataDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/store'))
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPreviousData = $env:WA_DATA_DIR
try {
    $env:WA_DATA_DIR = $DataDir
    & (Join-Path $taskRoot '.tools/uv/uv.exe') --directory (Join-Path $taskRoot 'readonly_mcp') run --locked --offline --no-sync python main_readonly.py
    if ($LASTEXITCODE -ne 0) { throw 'Read-only MCP exited with a failure.' }
} finally { $env:WA_DATA_DIR = $taskPreviousData }
