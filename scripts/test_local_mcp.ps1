[CmdletBinding()]
param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskUv = Join-Path $taskRoot '.tools/uv/uv.exe'
& $taskUv sync --directory (Join-Path $taskRoot 'readonly_mcp') --locked --python $PythonExe
if ($LASTEXITCODE -ne 0) { throw 'Locked MCP dependency setup failed.' }
Push-Location -LiteralPath $taskRoot
try {
    & (Join-Path $taskRoot 'readonly_mcp/.venv/Scripts/python.exe') -m unittest discover -s tests -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Local acceptance failed.' }
} finally { Pop-Location }
