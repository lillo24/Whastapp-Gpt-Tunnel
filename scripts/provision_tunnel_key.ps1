#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^wa-tunnel-key-[a-f0-9]{32}$')][string]$PipeName,
    [string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/tunnel'),
    [switch]$Replace
)
# Secret arrives over an ACL-protected local
# named pipe, never as a parameter, plaintext file, transcript or console input.
. (Join-Path $PSScriptRoot 'tunnel_common.ps1')
$taskDir = Initialize-WATunnelDirectory $RuntimeDir
$taskKeyFile = Join-Path $taskDir 'runtime-key.dpapi'
if ((Test-Path -LiteralPath $taskKeyFile) -and -not $Replace) { throw 'A runtime credential already exists; explicit rotation is required.' }
Add-Type -AssemblyName System.Security
$taskPipeSecurity = [IO.Pipes.PipeSecurity]::new()
$taskPipeSecurity.SetAccessRuleProtection($true, $false)
# Deny network logons even if they have the same account SID.
$taskPipeSecurity.AddAccessRule([IO.Pipes.PipeAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-5-2'), 'FullControl', 'Deny'))
foreach ($taskIdentity in @([Security.Principal.WindowsIdentity]::GetCurrent().User, [Security.Principal.SecurityIdentifier]::new('S-1-5-18'))) {
    $taskPipeSecurity.AddAccessRule([IO.Pipes.PipeAccessRule]::new($taskIdentity, 'FullControl', 'Allow'))
}
$taskPipe = $null
$taskBuffer = New-Object byte[] 1025
$taskPlain = $null
$taskSecure = $null
$taskStage = 'receiver'
try {
    $taskPipe = [IO.Pipes.NamedPipeServerStreamAcl]::Create($PipeName, [IO.Pipes.PipeDirection]::In, 1, [IO.Pipes.PipeTransmissionMode]::Byte, [IO.Pipes.PipeOptions]::Asynchronous, 2048, 2048, $taskPipeSecurity, [IO.HandleInheritability]::None, [IO.Pipes.PipeAccessRights]::ChangePermissions)
    Write-Output 'Protected local credential receiver ready (60-second timeout).'
    $taskStage = 'connection'
    if (-not $taskPipe.WaitForConnectionAsync().Wait(60000)) { throw 'Credential connection timed out.' }
    $taskCount = 0
    $taskStage = 'transfer'
    do {
        $taskRead = $taskPipe.ReadAsync($taskBuffer, $taskCount, $taskBuffer.Length - $taskCount)
        if (-not $taskRead.Wait(5000)) { throw 'Credential transfer timed out.' }
        $taskN = $taskRead.Result
        $taskCount += $taskN
        if ($taskCount -ge $taskBuffer.Length) { throw 'Invalid credential length.' }
    } while ($taskN -gt 0 -and $taskBuffer[$taskCount - 1] -ne 10)
    $taskPlain = [Text.Encoding]::UTF8.GetString($taskBuffer, 0, $taskCount).TrimEnd([char[]]"`r`n")
    $taskStage = 'format'
    if ($taskPlain -notmatch '^sk-[A-Za-z0-9_-]{20,1000}$') { throw 'Invalid credential format.' }
    $taskSecure = [Text.Encoding]::UTF8.GetBytes($taskPlain)
    $taskStage = 'protection'
    $taskCipher = [Security.Cryptography.ProtectedData]::Protect($taskSecure, [Text.Encoding]::UTF8.GetBytes('WhatsappGptTunnel/runtime-key/v1'), [Security.Cryptography.DataProtectionScope]::CurrentUser)
    $taskStage = 'storage'
    Write-WAText $taskKeyFile ([Convert]::ToBase64String($taskCipher))
    $null = Initialize-WATunnelDirectory $taskDir
    Write-Output 'Runtime credential encrypted with current-user DPAPI and private ACLs.'
} catch { throw ('Credential provisioning failed at ' + $taskStage + '; no credential value was logged.') }
finally {
    $taskPlain = $null
    [Array]::Clear($taskBuffer, 0, $taskBuffer.Length)
    if ($null -ne $taskSecure) { [Array]::Clear($taskSecure, 0, $taskSecure.Length) }
    if ($null -ne $taskPipe) { $taskPipe.Dispose() }
}
