# Dot-source within a build/test script; the caller restores these process variables.
$taskRoot = Split-Path -Parent $PSScriptRoot
$env:PATH = (Join-Path $taskRoot '.tools/msys64/ucrt64/bin') + ';' + $env:PATH
$env:CC = Join-Path $taskRoot '.tools/msys64/ucrt64/bin/gcc.exe'
$env:CGO_ENABLED = '1'
$env:GOTOOLCHAIN = 'local'
$env:GOMODCACHE = Join-Path $taskRoot 'bridge/.tools/gomod'
$env:GOCACHE = Join-Path $taskRoot '.tools/go-build'
$taskGo = Join-Path $taskRoot '.tools/go/bin/go.exe'
