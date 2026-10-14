#Requires -Version 7.0
[CmdletBinding()]
param([string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/tunnel'))
. (Join-Path $PSScriptRoot 'tunnel_common.ps1')
$taskDir = Initialize-WATunnelDirectory $RuntimeDir
$taskLock = $null
$taskProcess = $null
try {
    $taskLock = [IO.File]::Open((Join-Path $taskDir 'runtime.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    foreach ($taskName in @('health.url','stop.request','runtime-state.json','mcp-health.json','mcp-health.json.tmp')) {
        $taskFile = Join-Path $taskDir $taskName
        if (Test-Path -LiteralPath $taskFile) { Remove-Item -LiteralPath $taskFile }
    }
    $taskProcess = New-WATunnelProcess $taskDir run
    # Drain without retaining raw client/application output or exporting support logs.
    $taskOut = $taskProcess.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null)
    $taskErr = $taskProcess.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
    Write-WAText (Join-Path $taskDir 'runtime-state.json') (@{pid=$taskProcess.Id; started_at=$taskProcess.StartTime.ToUniversalTime().ToString('O')} | ConvertTo-Json)
    Write-Output 'Tunnel process started. Use check_tunnel.ps1; startup is not authorization proof.'
    while (-not $taskProcess.WaitForExit(1000)) {
        if (Test-Path -LiteralPath (Join-Path $taskDir 'stop.request')) {
            $taskProcess.Kill($true)
            $taskProcess.WaitForExit()
            break
        }
    }
    if ($taskProcess.ExitCode -ne 0 -and -not (Test-Path -LiteralPath (Join-Path $taskDir 'stop.request'))) { throw 'Tunnel runtime exited unsuccessfully.' }
} catch { throw 'Tunnel stopped or could not start. Check protected config, credential and local health.' }
finally {
    if ($null -ne $taskProcess) {
        if (-not $taskProcess.HasExited) { $taskProcess.Kill($true); $taskProcess.WaitForExit() }
        $taskProcess.Dispose()
    }
    if ($null -ne $taskLock) { $taskLock.Dispose() }
}
