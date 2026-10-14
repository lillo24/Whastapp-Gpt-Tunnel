[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskTools = Join-Path $taskRoot '.tools'
$taskPin = Get-Content -Raw (Join-Path $taskRoot 'audit/toolchain-pin.json') | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $taskTools | Out-Null
foreach ($taskName in @('go','msys2','uv')) {
    $taskItem = $taskPin.$taskName
    $taskArchive = Join-Path $taskTools $taskItem.archive
    if (-not (Test-Path -LiteralPath $taskArchive)) {
        & curl.exe --fail --location --silent --show-error --output $taskArchive $taskItem.url
        if ($LASTEXITCODE -ne 0) { throw ('Download failed: ' + $taskName) }
    }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $taskArchive).Hash.ToLowerInvariant() -ne $taskItem.sha256) {
        throw ('Toolchain checksum mismatch: ' + $taskName)
    }
    $taskBinary = switch ($taskName) {
        'go' { Join-Path $taskTools 'go/bin/go.exe' }
        'msys2' { Join-Path $taskTools 'msys64/usr/bin/bash.exe' }
        'uv' { Join-Path $taskTools 'uv/uv.exe' }
    }
    if (-not (Test-Path -LiteralPath $taskBinary)) {
        $taskExtract = if ($taskName -eq 'uv') { Join-Path $taskTools 'uv' } else { $taskTools }
        New-Item -ItemType Directory -Force -Path $taskExtract | Out-Null
        if ($taskName -eq 'msys2') { & $taskArchive '-y' ('-o' + $taskExtract) }
        else { & tar.exe -xf $taskArchive -C $taskExtract }
        if ($LASTEXITCODE -ne 0) { throw ('Archive extraction failed: ' + $taskName) }
    }
}
$taskBash = Join-Path $taskTools 'msys64/usr/bin/bash.exe'
$taskOldMsystem = $env:MSYSTEM
try {
    $env:MSYSTEM = 'UCRT64'
    # Only this isolated MSYS2 installation is initialized/updated.
    & $taskBash --login -c 'exit'
    if ($LASTEXITCODE -ne 0) { throw 'MSYS2 initialization failed.' }
    $taskPackagePin = Join-Path $taskRoot 'audit/msys2-packages-pin.json'
    if (-not (Test-Path -LiteralPath $taskPackagePin)) { throw 'Reviewed MSYS2 package pin is missing.' }
    $taskPackages = (Get-Content -Raw -LiteralPath $taskPackagePin | ConvertFrom-Json).packages
    $taskCache = Join-Path $taskTools 'msys64/var/cache/pacman/pkg'
    foreach ($taskPackage in $taskPackages) {
        $taskPackagePath = Join-Path $taskCache $taskPackage.filename
        if (-not (Test-Path -LiteralPath $taskPackagePath)) {
            & curl.exe --fail --location --silent --show-error --output $taskPackagePath $taskPackage.url
            if ($LASTEXITCODE -ne 0) { throw 'Pinned compiler package download failed.' }
            & curl.exe --fail --location --silent --show-error --output ($taskPackagePath + '.sig') ($taskPackage.url + '.sig')
            if ($LASTEXITCODE -ne 0) { throw 'Pinned compiler package signature download failed.' }
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $taskPackagePath).Hash.ToLowerInvariant() -ne $taskPackage.sha256) {
            throw 'Pinned compiler package checksum mismatch.'
        }
    }
    # All files in this dedicated cache are pinned and verified above; reject extras.
    $taskCachedFiles = @(Get-ChildItem -LiteralPath $taskCache -Filter '*.pkg.tar.zst')
    if ($taskCachedFiles.Count -ne $taskPackages.Count) { throw 'Unexpected compiler packages in cache.' }
    & $taskBash --login -c 'pacman -U --noconfirm --needed /var/cache/pacman/pkg/*.pkg.tar.zst'
    if ($LASTEXITCODE -ne 0) { throw 'MSYS2 UCRT64 GCC installation failed.' }
} finally { $env:MSYSTEM = $taskOldMsystem }
& (Join-Path $taskTools 'go/bin/go.exe') version
& (Join-Path $taskTools 'msys64/ucrt64/bin/gcc.exe') --version
& (Join-Path $taskTools 'uv/uv.exe') --version
Write-Output 'Dedicated toolchain ready. No account pairing or global PATH/config change.'
