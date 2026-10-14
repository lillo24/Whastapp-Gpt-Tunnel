[CmdletBinding()]
param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $taskRoot
try {
    & $PythonExe (Join-Path $PSScriptRoot 'audit_upstream.py')
    if ($LASTEXITCODE -ne 0) { throw 'Pinned source audit failed; fetch reference source first.' }
    & $PythonExe -m unittest discover -s tests -p 'test_wa00.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'WA00 offline acceptance failed.' }
} finally {
    Pop-Location
}
