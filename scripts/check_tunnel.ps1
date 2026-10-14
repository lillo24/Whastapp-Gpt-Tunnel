#Requires -Version 7.0
[CmdletBinding()]
param(
    [string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/tunnel'),
    [switch]$Doctor
)
. (Join-Path $PSScriptRoot 'tunnel_common.ps1')
$taskDir = Initialize-WATunnelDirectory $RuntimeDir
if ($Doctor) {
    $taskProcess = New-WATunnelProcess $taskDir doctor
    try {
        $taskOut = $taskProcess.StandardOutput.ReadToEndAsync()
        $taskErr = $taskProcess.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        if (-not $taskProcess.WaitForExit(15000)) { $taskProcess.Kill($true); throw 'Doctor timed out.' }
        $taskReport = $taskOut.Result | ConvertFrom-Json
        [pscustomobject]@{config_ok=($taskProcess.ExitCode -eq 0 -and $taskReport.result -eq 'ok'); live_authorization_tested=$false; stdio_protocol_tested=$false} | ConvertTo-Json
        if ($taskProcess.ExitCode -ne 0) { exit 1 }
    } catch { throw 'Tunnel doctor failed; raw diagnostic output withheld.' }
    finally { $taskProcess.Dispose() }
    exit 0
}
$taskStage = 'process'
try {
    $taskState = Get-Content -Raw -LiteralPath (Join-Path $taskDir 'runtime-state.json') | ConvertFrom-Json
    $taskProcess = Get-Process -Id $taskState.pid -ErrorAction Stop
    $taskClient = [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $PSScriptRoot) '.tools/tunnel-client/tunnel-client.exe'))
    if ($taskProcess.Path -ne $taskClient -or $taskProcess.StartTime.ToUniversalTime().Ticks -ne ([datetime]$taskState.started_at).ToUniversalTime().Ticks) { throw 'Stale process state.' }
    $taskStage = 'health_url'
    $taskUri = [uri]([IO.File]::ReadAllText((Join-Path $taskDir 'health.url')).Trim())
    if ($taskUri.Scheme -ne 'http' -or $taskUri.Host -ne '127.0.0.1' -or $taskUri.Port -lt 1 -or $taskUri.UserInfo -or $taskUri.Query -or $taskUri.Fragment -or $taskUri.AbsolutePath -notin @('','/')) { throw 'Nonlocal health URL refused.' }
    $taskStage = 'health_request'
    $taskHealth = Invoke-RestMethod -Uri ($taskUri.AbsoluteUri.TrimEnd('/') + '/health?details=true') -NoProxy -TimeoutSec 5
    $taskStage = 'health_schema'
    if ($taskHealth.schema_version -ne 1) { throw 'Unknown health schema.' }
    $taskStage = 'mcp_observations'
    $taskMcp = $taskHealth.components.mcp
    $taskControl = $taskHealth.components.'control-plane'
    $taskExpected = @('get_chat','get_message_context','health_status','list_chats','list_messages','search_contacts')
    $taskToolsVerified = $false
    if ($taskMcp.PSObject.Properties.Name -contains 'details' -and $taskMcp.details.PSObject.Properties.Name -contains 'tools_list') {
        $taskTools = $taskMcp.details.tools_list
        $taskToolsVerified = ($taskTools.ok -eq $true -and $taskTools.complete -eq $true -and $taskTools.partial -eq $false -and $taskTools.limited -eq $false -and (@($taskTools.tool_names | Sort-Object) -join ',') -eq ($taskExpected -join ','))
    }
    [pscustomobject]@{
        process_live=($taskHealth.live -eq $true)
        startup_ready=($taskHealth.ready -eq $true)
        control_plane_ok=($taskControl.status -eq 'ok')
        six_tools_observed=$taskToolsVerified
        collector_freshness='Check MCP health_status separately; transport readiness does not establish collection freshness.'
    } | ConvertTo-Json
} catch {
    [pscustomobject]@{process_live=$false; startup_ready=$false; control_plane_ok=$false; six_tools_observed=$false; error_class='TUNNEL_UNAVAILABLE'; failed_check=$taskStage} | ConvertTo-Json
    exit 1
}
