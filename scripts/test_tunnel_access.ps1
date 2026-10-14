#Requires -Version 7.0
[CmdletBinding()]
param([string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/tunnel'))
. (Join-Path $PSScriptRoot 'tunnel_common.ps1')
$taskDir = Initialize-WATunnelDirectory $RuntimeDir
$taskMetadata = Get-WATunnelMetadata $taskDir
# The pinned vendor protocol documents these metadata/poll routes. This test
# never decrypts the real key, posts commands, or reads private response bodies.
$taskHandler = [Net.Http.HttpClientHandler]::new()
$taskHandler.UseProxy = $false
$taskHandler.AllowAutoRedirect = $false
$taskClient = [Net.Http.HttpClient]::new($taskHandler)
$taskClient.Timeout = [TimeSpan]::FromSeconds(10)
$taskChecks = @()
try {
    foreach ($taskKind in @('anonymous','bad_key')) {
        foreach ($taskRoute in @('metadata','poll')) {
            $taskUrl = 'https://api.openai.com/v1/tunnels/' + $taskMetadata.tunnel_id
            if ($taskRoute -eq 'poll') { $taskUrl += '/poll?limit=1&timeout_ms=5000' }
            $taskRequest = [Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Get, $taskUrl)
            $taskResponse = $null
            try {
                if ($taskKind -eq 'bad_key') { $taskRequest.Headers.Authorization = [Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', 'fixture-not-a-valid-runtime-key') }
                $taskResponse = $taskClient.SendAsync($taskRequest, [Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
                $taskCode = [int]$taskResponse.StatusCode
                $taskChecks += [pscustomobject]@{credential=$taskKind; route=$taskRoute; status=$taskCode; denied=($taskCode -in @(401,403))}
            } finally {
                if ($null -ne $taskResponse) { $taskResponse.Dispose() }
                $taskRequest.Dispose()
            }
        }
    }
    [pscustomobject]@{checks=$taskChecks; caller_workspace_scope_tested=$false; chat_enumeration_attempted=$false} | ConvertTo-Json -Depth 4
    if (@($taskChecks | Where-Object { -not $_.denied }).Count) { exit 1 }
} catch { throw 'Control-plane negative authorization test failed; response bodies withheld.' }
finally { $taskClient.Dispose(); $taskHandler.Dispose() }
