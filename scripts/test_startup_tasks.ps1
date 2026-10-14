#Requires -Version 7.0
[CmdletBinding()]
param()
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskRepo=Split-Path -Parent $PSScriptRoot
$taskId=[guid]::NewGuid().ToString('N').Substring(0,8)
$taskBase=Assert-WALocalPath (Join-Path $taskRepo ('.local-fixtures/startup-test-'+$taskId))
$null=[IO.Directory]::CreateDirectory($taskBase)
$taskEvents=Join-Path $taskBase 'events.json'
$taskStore=Join-Path $taskBase 'store'
$taskRuntime=Join-Path $taskBase 'runtime'
$taskOps=Join-Path $taskBase 'ops'
$taskBackups=Join-Path $taskBase 'backups'
$taskPrefix='WhatsappGptTunnel-Test-'+$taskId
Write-WAText $taskEvents '{"synthetic":true,"events":[]}'
& (Join-Path $taskRepo 'bin/wa-bridge.exe') fixture --synthetic --input $taskEvents --data-dir $taskStore
if ($LASTEXITCODE -ne 0) { throw 'Synthetic collector setup failed.' }
$null=& (Join-Path $PSScriptRoot 'init_tunnel.ps1') -TunnelId ('tunnel_'+('0'*32)) -OrganizationId 'org-fixture' -DataDir $taskStore -RuntimeDir $taskRuntime
# An obviously fake local key tests process supervision without accessing any
# account. Provisioning of real secrets uses the separately tested pipe helper.
Add-Type -AssemblyName System.Security
$taskPlain=[Text.Encoding]::UTF8.GetBytes('sk-fixture-'+('a'*40))
try {
    $taskCipher=[Security.Cryptography.ProtectedData]::Protect($taskPlain,[Text.Encoding]::UTF8.GetBytes('WhatsappGptTunnel/runtime-key/v1'),[Security.Cryptography.DataProtectionScope]::CurrentUser)
    Write-WAText (Join-Path $taskRuntime 'runtime-key.dpapi') ([Convert]::ToBase64String($taskCipher))
} finally { [Array]::Clear($taskPlain,0,$taskPlain.Length) }
$taskReport=@{synthetic_only=$true; mode='interactive logon only; no boot trigger'; registration=$false; jobs_started=$false; independent_of_launching_terminal=$false; cleanup=$false; reboot_and_logged_off='not tested'; error_class=$null}
try {
    $null=& (Join-Path $PSScriptRoot 'install.ps1') -OpsDir $taskOps -RuntimeDir $taskRuntime -BackupDir $taskBackups -TaskPrefix $taskPrefix -InteractiveTest -Apply -ConfirmInstall
    $taskReport.registration=$true
    $null=& (Join-Path $PSScriptRoot 'start.ps1') -OpsDir $taskOps
    for ($taskSecond=0; $taskSecond -lt 25; $taskSecond++) {
        if ((Test-Path -LiteralPath (Join-Path $taskOps 'bridge.state.json')) -and (Test-Path -LiteralPath (Join-Path $taskRuntime 'health.url'))) { $taskReport.jobs_started=$true; break }
        Start-Sleep -Seconds 1
    }
    $taskReport.independent_of_launching_terminal=$taskReport.jobs_started
} catch {
    $taskReport.error_class=if ($_.Exception.Message -match '80070005') {'WINDOWS_ACCESS_DENIED'} else {'WINDOWS_TASK_TEST_FAILED'}
    if ($_.Exception.Message -match 'HRESULT ([A-F0-9]{8})') { $taskReport.hresult=$Matches[1] }
} finally {
    # Never touch tasks belonging to other tests or the production prefix.
    if ($taskReport.registration) { $null=& (Join-Path $PSScriptRoot 'stop.ps1') -OpsDir $taskOps }
    $taskFolder=Get-WATaskService
    foreach ($taskComponent in @('tunnel','bridge')) {
        $taskName=$taskPrefix+'-'+(Get-Culture).TextInfo.ToTitleCase($taskComponent)
        $taskJob=Get-WATask $taskFolder $taskName
        if ($null -ne $taskJob) { Assert-WAOwnedTask $taskJob $taskComponent; $taskJob.Stop(0); $taskFolder.DeleteTask($taskName,0) }
    }
    $taskReport.cleanup=$true
}
$taskReport | ConvertTo-Json
