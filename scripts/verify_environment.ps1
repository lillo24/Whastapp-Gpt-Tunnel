[CmdletBinding()]
param(
    [string]$PythonExe = 'python',
    [string]$GoExe = 'go',
    [string]$UvExe = 'uv',
    [string]$GccExe = 'gcc'
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot

function Get-TaskToolVersion {
    param([string]$Name, [string]$Executable, [string[]]$Arguments)
    $taskCommand = Get-Command -Name $Executable -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $taskCommand) {
        return [pscustomobject]@{ name = $Name; status = 'MISSING'; version = $null }
    }
    if ($taskCommand.Source -like '*\Microsoft\WindowsApps\*') {
        return [pscustomobject]@{ name = $Name; status = 'UNUSABLE_APP_ALIAS'; version = $null }
    }
    try {
        $taskOutput = & $taskCommand.Source @Arguments 2>&1
        $taskExit = $LASTEXITCODE
        $taskFirstLine = (($taskOutput | Out-String).Trim() -split "`r?`n")[0]
        if ($taskExit -ne 0) { throw 'Version command failed.' }
        return [pscustomobject]@{ name = $Name; status = 'AVAILABLE'; version = $taskFirstLine }
    } catch {
        return [pscustomobject]@{ name = $Name; status = 'FAILED'; version = $null }
    }
}

$taskTools = @(
    Get-TaskToolVersion -Name 'go' -Executable $GoExe -Arguments @('version')
    Get-TaskToolVersion -Name 'python' -Executable $PythonExe -Arguments @('--version')
    Get-TaskToolVersion -Name 'uv' -Executable $UvExe -Arguments @('--version')
    Get-TaskToolVersion -Name 'gcc' -Executable $GccExe -Arguments @('--version')
    Get-TaskToolVersion -Name 'git' -Executable 'git' -Arguments @('--version')
)
foreach ($taskTool in $taskTools) {
    if ($taskTool.status -ne 'AVAILABLE') { continue }
    if ($taskTool.name -eq 'python') {
        if ($taskTool.version -notmatch '^Python (\d+)\.(\d+)\.') { $taskTool.status = 'UNRECOGNIZED' }
        elseif ([int]$Matches[1] -lt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -lt 11)) { $taskTool.status = 'UNSUPPORTED' }
    }
    if ($taskTool.name -eq 'go') {
        if ($taskTool.version -notmatch '^go version go(\d+)\.(\d+)\.(\d+)') { $taskTool.status = 'UNRECOGNIZED' }
        elseif ([version]($Matches[1] + '.' + $Matches[2] + '.' + $Matches[3]) -lt [version]'1.24.1') { $taskTool.status = 'UNSUPPORTED' }
    }
}
$taskRepositoryCommit = & git -C $taskRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot read implementation Git commit.' }
$taskPin = Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'audit/upstream-pin.json') | ConvertFrom-Json
$taskSourceCommit = $null
$taskSourcePath = Join-Path $taskRoot $taskPin.source_directory
if (Test-Path -LiteralPath (Join-Path $taskSourcePath '.git')) {
    $taskSourceCommit = & git -C $taskSourcePath rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read audit Git commit.' }
}
$taskReady = @($taskTools | Where-Object { $_.status -ne 'AVAILABLE' }).Count -eq 0
if ($taskSourceCommit -ne $taskPin.commit) { $taskReady = $false }
[pscustomobject]@{
    tools = $taskTools
    implementation_commit = $taskRepositoryCommit
    upstream_expected = $taskPin.commit
    upstream_actual = $taskSourceCommit
    tooling_available = $taskReady
    windows_cgo_build_verified = $false
    credentials_required = $false
    network_used = $false
    note = 'GCC presence alone does not establish UCRT64/CGO compatibility; WA01 must compile and test.'
} | ConvertTo-Json -Depth 5
if (-not $taskReady) { exit 1 }
exit 0
