[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPin = Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'audit/upstream-pin.json') | ConvertFrom-Json
$taskSource = Join-Path $taskRoot $taskPin.source_directory
if (-not (Test-Path -LiteralPath $taskSource)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $taskSource) | Out-Null
    & git clone --no-checkout -- $taskPin.repository $taskSource
    if ($LASTEXITCODE -ne 0) { throw 'Audit source clone failed.' }
    & git -C $taskSource checkout --detach $taskPin.commit
    if ($LASTEXITCODE -ne 0) { throw 'Pinned audit checkout failed.' }
}
$taskActual = & git -C $taskSource rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $taskActual -ne $taskPin.commit) {
    throw 'Existing audit checkout has a different pin. It was not changed.'
}
$taskDirty = & git -C $taskSource status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0 -or $taskDirty) { throw 'Audit checkout is not clean. It was not changed.' }
Write-Output ('Audit reference fetched at ' + $taskActual + '. No upstream program was executed.')
