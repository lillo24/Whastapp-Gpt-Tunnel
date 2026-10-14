[CmdletBinding()]
param([switch]$Test)
$ErrorActionPreference = 'Stop'
$taskOldEnv = @{}
foreach ($taskName in @('PATH','CC','CGO_ENABLED','GOTOOLCHAIN','GOMODCACHE','GOCACHE')) {
    $taskOldEnv[$taskName] = [Environment]::GetEnvironmentVariable($taskName,'Process')
}
try {
    . (Join-Path $PSScriptRoot 'with_bridge_toolchain.ps1')
    Push-Location -LiteralPath (Join-Path $taskRoot 'bridge')
    try {
        & $taskGo mod verify
        if ($LASTEXITCODE -ne 0) { throw 'Go module verification failed.' }
        if ($Test) {
            & $taskGo test -mod=readonly -count=1 -v ./...
            if ($LASTEXITCODE -ne 0) { throw 'Bridge tests failed.' }
        }
        New-Item -ItemType Directory -Force -Path (Join-Path $taskRoot 'bin') | Out-Null
        & $taskGo build -mod=readonly -trimpath -buildvcs=false -ldflags '-s -w' -o (Join-Path $taskRoot 'bin/wa-bridge.exe') .
        if ($LASTEXITCODE -ne 0) { throw 'Bridge build failed.' }
    } finally { Pop-Location }
} finally {
    foreach ($taskName in $taskOldEnv.Keys) { [Environment]::SetEnvironmentVariable($taskName,$taskOldEnv[$taskName],'Process') }
}
