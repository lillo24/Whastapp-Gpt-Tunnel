[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskClean = Join-Path $taskRoot ('.local-fixtures/clean-build-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskClean | Out-Null
Get-ChildItem -LiteralPath (Join-Path $taskRoot 'bridge') -File | Where-Object { $_.Extension -eq '.go' -or $_.Name -in @('go.mod','go.sum','schema.sql','LICENSE.upstream') } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $taskClean
}
$taskOldEnv = @{}
foreach ($taskName in @('PATH','CC','CGO_ENABLED','GOTOOLCHAIN','GOMODCACHE','GOCACHE')) { $taskOldEnv[$taskName] = [Environment]::GetEnvironmentVariable($taskName,'Process') }
try {
    . (Join-Path $PSScriptRoot 'with_bridge_toolchain.ps1')
    Push-Location -LiteralPath $taskClean
    try {
        & $taskGo build -mod=readonly -trimpath -buildvcs=false -o (Join-Path $taskClean 'wa-bridge.exe') .
        if ($LASTEXITCODE -ne 0) { throw 'Clean source Windows build failed.' }
        Write-Output 'Clean source Windows CGO build: PASS'
    } finally { Pop-Location }
} finally {
    foreach ($taskName in $taskOldEnv.Keys) { [Environment]::SetEnvironmentVariable($taskName,$taskOldEnv[$taskName],'Process') }
}
