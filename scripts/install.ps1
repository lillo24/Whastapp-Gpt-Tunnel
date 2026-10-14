#Requires -Version 7.0
[CmdletBinding()]
param(
    [string]$OpsDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'),
    [string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/tunnel'),
    [string]$BackupDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/backups'),
    [string]$TaskPrefix = 'WhatsappGptTunnel',
    [switch]$Apply, [switch]$ConfirmInstall, [switch]$InteractiveTest,
    [PSCredential]$Credential
)
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskOps = Initialize-WAPrivateFolder $OpsDir '.wa-operations'
$taskRuntime = Initialize-WATunnelDirectory $RuntimeDir
$taskMetadata = Get-WATunnelMetadata $taskRuntime
$taskBackup = Assert-WALocalPath $BackupDir
if ($TaskPrefix -notmatch '^WhatsappGptTunnel(?:-Test-[a-f0-9]{8})?$') { throw 'Invalid task prefix.' }
$taskRepo = Split-Path -Parent $PSScriptRoot
# Read only bounded collector status, never message/session records.
$taskInspect = 'import sys,json,sqlite3; from pathlib import Path; p=Path(sys.argv[1]); d=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True); r=d.execute("SELECT synthetic FROM collector_status WHERE singleton=1").fetchone(); print(json.dumps(bool(r and r[0]==1)))'
$taskSynthetic = (& (Join-Path $taskRepo 'readonly_mcp/.venv/Scripts/python.exe') -I -c $taskInspect (Join-Path $taskMetadata.data_dir 'messages.db')) | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $taskSynthetic -isnot [bool]) { throw 'Collector preflight failed.' }
if ($InteractiveTest -and (-not $taskSynthetic -or $TaskPrefix -notmatch '-Test-')) { throw 'Interactive test tasks require a synthetic store and unique Test prefix.' }
if (-not $InteractiveTest -and $TaskPrefix -ne 'WhatsappGptTunnel') { throw 'Production task names must use the fixed prefix.' }
$taskConfig = @{schema_version=1; data_dir=$taskMetadata.data_dir; runtime_dir=$taskRuntime; backup_dir=$taskBackup; synthetic=$taskSynthetic; task_prefix=$TaskPrefix}
$taskConfigFile = Join-Path $taskOps 'operations.json'
if (Test-Path -LiteralPath $taskConfigFile) {
    $taskOld = Get-WAOperations $taskOps
    foreach ($taskName in @('data_dir','runtime_dir','backup_dir','synthetic','task_prefix')) {
        if ($taskOld.$taskName -ne $taskConfig[$taskName]) { throw 'Existing operator configuration differs; explicit activation/review is required.' }
    }
} else { Write-WAText $taskConfigFile ($taskConfig | ConvertTo-Json) }
foreach ($taskComponent in @('bridge','tunnel')) { Write-WAText (Join-Path $taskOps ($taskComponent + '.task.xml')) (New-WATaskXml $taskOps $taskComponent -InteractiveTest:$InteractiveTest) }
if (-not $Apply) {
    [pscustomobject]@{registered=$false; preview_ready=$true; tasks=@(($TaskPrefix+'-Bridge'),($TaskPrefix+'-Tunnel')); least_privilege=$true; logon= $(if ($InteractiveTest) {'interactive synthetic test only'} else {'password; runs while logged off'}); synthetic=$taskSynthetic; secrets_in_task_xml=$false} | ConvertTo-Json
    exit 0
}
if (-not $ConfirmInstall) { throw 'Review the generated task preview, then pass ConfirmInstall explicitly.' }
$taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $InteractiveTest) {
    if ($null -eq $Credential) { throw 'WINDOWS_CREDENTIAL_REQUIRED: obtain Get-Credential locally, then pass its PSCredential object. Never provide the password in chat or arguments.' }
    $taskCredentialSid = [Security.Principal.NTAccount]::new($Credential.UserName).Translate([Security.Principal.SecurityIdentifier]).Value
    if ($taskCredentialSid -ne $taskIdentity.User.Value) { throw 'Startup identity must be the protected store owner.' }
}
$taskFolder = Get-WATaskService
foreach ($taskComponent in @('bridge','tunnel')) {
    $taskName = $TaskPrefix + '-' + (Get-Culture).TextInfo.ToTitleCase($taskComponent)
    $taskExisting = Get-WATask $taskFolder $taskName
    if ($null -ne $taskExisting) { Assert-WAOwnedTask $taskExisting $taskComponent }
}
$taskPassword = $null
$taskCreated = [Collections.Generic.List[string]]::new()
try {
    if ($null -ne $Credential) { $taskPassword = $Credential.GetNetworkCredential().Password }
    $taskLogon = if ($InteractiveTest) { 3 } else { 1 }
    foreach ($taskComponent in @('bridge','tunnel')) {
        $taskName = $TaskPrefix + '-' + (Get-Culture).TextInfo.ToTitleCase($taskComponent)
        $taskXml = [IO.File]::ReadAllText((Join-Path $taskOps ($taskComponent + '.task.xml')))
        $taskSddl = 'D:P(A;;FA;;;' + $taskIdentity.User.Value + ')(A;;FA;;;SY)'
        $taskWasAbsent = $null -eq (Get-WATask $taskFolder $taskName)
        $null = $taskFolder.RegisterTask($taskName,$taskXml,6,$taskIdentity.User.Value,$taskPassword,$taskLogon,$taskSddl)
        if ($taskWasAbsent) { $taskCreated.Add($taskName) }
    }
    Write-Output 'Two current-user, least-privilege tasks registered. No service, power, firewall or credential policy changed.'
} catch {
    $taskFailureCode = $_.Exception.GetBaseException().HResult.ToString('X8')
    foreach ($taskName in $taskCreated) { try { $taskFolder.DeleteTask($taskName,0) } catch {} }
    throw ('TASK_REGISTRATION_FAILED: Windows rejected registration (HRESULT '+$taskFailureCode+'). Newly created tasks were rolled back; review existing task status before retrying. No credential value was logged.')
}
finally { $taskPassword = $null; $Credential = $null }
