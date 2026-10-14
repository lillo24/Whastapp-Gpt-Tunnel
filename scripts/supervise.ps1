#Requires -Version 7.0
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('bridge','tunnel')][string]$Component,
      [string]$OpsDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/operations'))
. (Join-Path $PSScriptRoot 'operations_common.ps1')
$taskOps = Initialize-WAPrivateFolder $OpsDir '.wa-operations'
$taskConfig = Get-WAOperations $taskOps
$taskStop = Join-Path $taskOps ($Component + '.stop')
$taskLock = $null
$taskChild = $null
function Write-WAEvent([string]$Event, [int]$Attempt, [int]$Code = 0) {
    $file = Join-Path $taskOps ($Component + '.events.jsonl')
    if ((Test-Path -LiteralPath $file) -and (Get-Item -LiteralPath $file).Length -gt 131072) {
        $previous = Join-Path $taskOps ($Component + '.events.previous.jsonl')
        if (Test-Path -LiteralPath $previous) { Remove-Item -LiteralPath $previous }
        Move-Item -LiteralPath $file -Destination $previous
    }
    $line = @{at=[datetime]::UtcNow.ToString('O'); component=$Component; event=$Event; attempt=$Attempt; exit_code=$Code} | ConvertTo-Json -Compress
    [IO.File]::AppendAllText($file,$line+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
}
try {
    $taskLock = [IO.File]::Open((Join-Path $taskOps ($Component + '.lock')),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    if (Test-Path -LiteralPath $taskStop) { Remove-Item -LiteralPath $taskStop }
    for ($taskAttempt=1; $taskAttempt -le 5; $taskAttempt++) {
        $taskInfo = [Diagnostics.ProcessStartInfo]::new()
        $taskInfo.WorkingDirectory = Split-Path -Parent $PSScriptRoot
        $taskInfo.UseShellExecute=$false; $taskInfo.CreateNoWindow=$true
        $taskInfo.RedirectStandardOutput=$true; $taskInfo.RedirectStandardError=$true
        $taskInfo.EnvironmentVariables.Clear()
        foreach ($taskEntry in (Get-WACleanEnvironment).GetEnumerator()) { $taskInfo.EnvironmentVariables[$taskEntry.Key]=$taskEntry.Value }
        if ($Component -eq 'bridge') {
            $taskInfo.FileName = Join-Path $taskInfo.WorkingDirectory 'bin/wa-bridge.exe'
            foreach ($taskArg in @('run','--data-dir',$taskConfig.data_dir)) { $taskInfo.ArgumentList.Add($taskArg) }
            if ($taskConfig.synthetic) { $taskInfo.ArgumentList.Add('--synthetic') }
        } else {
            $taskInfo.FileName = [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
            foreach ($taskArg in @('-NoProfile','-NonInteractive','-File',(Join-Path $PSScriptRoot 'run_tunnel.ps1'),'-RuntimeDir',$taskConfig.runtime_dir)) { $taskInfo.ArgumentList.Add($taskArg) }
        }
        $taskChild = [Diagnostics.Process]::new(); $taskChild.StartInfo=$taskInfo
        if (-not $taskChild.Start()) { throw 'Component did not start.' }
        $taskOut=$taskChild.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null)
        $taskErr=$taskChild.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        Write-WAText (Join-Path $taskOps ($Component + '.state.json')) (@{pid=$taskChild.Id; started_at=$taskChild.StartTime.ToUniversalTime().ToString('O'); component=$Component} | ConvertTo-Json)
        Write-WAEvent 'started' $taskAttempt
        while (-not $taskChild.WaitForExit(1000)) {
            if (Test-Path -LiteralPath $taskStop) {
                if ($Component -eq 'bridge') { & (Join-Path $taskInfo.WorkingDirectory 'bin/wa-bridge.exe') stop --data-dir $taskConfig.data_dir 2>$null }
                else { Write-WAText (Join-Path $taskConfig.runtime_dir 'stop.request') '' }
                if (-not $taskChild.WaitForExit(7000)) { $taskChild.Kill($true); $taskChild.WaitForExit() }
                break
            }
        }
        $taskExit=$taskChild.ExitCode; $taskChild.Dispose(); $taskChild=$null
        if (Test-Path -LiteralPath $taskStop) { Write-WAEvent 'stopped' $taskAttempt; exit 0 }
        Write-WAEvent 'retry' $taskAttempt $taskExit
        $taskDelay = [Math]::Min(60,[Math]::Pow(2,$taskAttempt))
        for ($taskSecond=0; $taskSecond -lt $taskDelay; $taskSecond++) {
            if (Test-Path -LiteralPath $taskStop) { exit 0 }
            Start-Sleep -Seconds 1
        }
    }
    Write-WAEvent 'failed' 5
    exit 1
} catch { throw 'Component supervision failed; raw output and private details withheld.' }
finally {
    if ($null -ne $taskChild) { if (-not $taskChild.HasExited) { $taskChild.Kill($true); $taskChild.WaitForExit() }; $taskChild.Dispose() }
    if ($null -ne $taskLock) { $taskLock.Dispose() }
}
