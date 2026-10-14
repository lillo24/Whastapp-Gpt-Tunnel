[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPin = Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'audit/tunnel-client-pin.json') | ConvertFrom-Json
$taskArchive = Join-Path $taskRoot ('.tools/' + $taskPin.archive)
$taskDestination = Join-Path $taskRoot '.tools/tunnel-client'
New-Item -ItemType Directory -Force -Path $taskDestination | Out-Null
if (-not (Test-Path -LiteralPath $taskArchive)) {
    & curl.exe --fail --location --silent --show-error --output $taskArchive $taskPin.url
    if ($LASTEXITCODE -ne 0) { throw 'Official tunnel-client download failed.' }
}
if ((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskPin.sha256) {
    throw 'Official tunnel-client checksum mismatch.'
}
# Extract only the reviewed client and notices; Cloudflare is not used.
& tar.exe -xf $taskArchive -C $taskDestination tunnel-client.exe LICENSE NOTICE ('tunnel-client-' + $taskPin.version + '-windows-amd64-licenses.txt')
if ($LASTEXITCODE -ne 0) { throw 'Official tunnel-client extraction failed.' }
$taskVersion = & (Join-Path $taskDestination 'tunnel-client.exe') --version
if ($LASTEXITCODE -ne 0 -or $taskVersion -notlike ($taskPin.version.TrimStart('v') + '+*')) { throw 'Tunnel-client version mismatch.' }
if ((Get-FileHash -LiteralPath (Join-Path $taskDestination 'tunnel-client.exe') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskPin.binary_sha256) { throw 'Extracted tunnel-client checksum mismatch.' }
Write-Output $taskVersion
Write-Output 'Pinned tunnel-client installed locally. No tunnel, credential or runtime created.'
