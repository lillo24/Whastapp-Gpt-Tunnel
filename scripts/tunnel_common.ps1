#Requires -Version 7.0
# Shared Windows-only tunnel helpers. Never write decrypted credentials to output.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-WALocalPath([string]$Path) {
    if ($Path -notmatch '^[A-Za-z]:[\\/]' -or $Path -match '[\r\n",]') { throw 'An absolute local path without command delimiters is required.' }
    $full = [IO.Path]::GetFullPath($Path).TrimEnd([char[]]'\/')
    if ($full -eq [IO.Path]::GetPathRoot($full).TrimEnd([char[]]'\/')) { throw 'A volume root is not a dedicated runtime directory.' }
    $part = $full
    while ($part) {
        if (Test-Path -LiteralPath $part) {
            if ((Get-Item -Force -LiteralPath $part).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Redirected runtime paths are refused.' }
        }
        $part = Split-Path -Parent $part
    }
    return $full
}

function Initialize-WATunnelDirectory([string]$RuntimeDir) {
    $dir = Assert-WALocalPath $RuntimeDir
    $marker = Assert-WALocalPath (Join-Path $dir '.wa-tunnel-runtime')
    if (Test-Path -LiteralPath $dir) {
        if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) {
            if (@(Get-ChildItem -Force -LiteralPath $dir).Count) { throw 'Refusing to adopt a nonempty runtime directory.' }
        } elseif ([IO.File]::ReadAllText($marker) -ne 'wa-tunnel-runtime-v1') { throw 'Unknown runtime directory marker.' }
    } else { [IO.Directory]::CreateDirectory($dir) | Out-Null }
    # Validate the whole flat layout before modifying any existing ACL.
    $allowedNames = @('.wa-tunnel-runtime','connection.json','tunnel-profile.yaml','runtime-key.dpapi','runtime.lock','health.url','runtime-state.json','stop.request','mcp-health.json','mcp-health.json.tmp')
    $items = @(Get-ChildItem -Force -LiteralPath $dir)
    foreach ($item in $items) {
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $item.Name -notin $allowedNames) { throw 'Unexpected or redirected runtime files are refused.' }
    }
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($identity in @($sid, $system)) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($dir), $acl)
    foreach ($item in $items) {
        $fileAcl = [Security.AccessControl.FileSecurity]::new()
        $fileAcl.SetAccessRuleProtection($true, $false)
        foreach ($identity in @($sid, $system)) {
            $fileAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'Allow'))
        }
        [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($item.FullName), $fileAcl)
    }
    if (-not (Test-Path -LiteralPath $marker)) { Write-WAText $marker 'wa-tunnel-runtime-v1' }
    return $dir
}

function Write-WAText([string]$Path, [string]$Value) {
    [IO.File]::WriteAllText($Path, $Value, [Text.UTF8Encoding]::new($false))
}

function Get-WATunnelMetadata([string]$RuntimeDir) {
    $metadata = Get-Content -Raw -LiteralPath (Join-Path $RuntimeDir 'connection.json') | ConvertFrom-Json
    if (@($metadata.PSObject.Properties.Name | Where-Object { $_ -notin @('schema_version','tunnel_id','organization_id','data_dir') }).Count -or $metadata.schema_version -ne 1) { throw 'Unknown tunnel metadata.' }
    if ($metadata.tunnel_id -notmatch '^tunnel_[a-f0-9]{32}$' -or $metadata.organization_id -notmatch '^org-[A-Za-z0-9]+$') { throw 'Invalid tunnel association metadata.' }
    $metadata.data_dir = Assert-WALocalPath $metadata.data_dir
    return $metadata
}

function Write-WATunnelProfile([string]$RuntimeDir) {
    $metadata = Get-WATunnelMetadata $RuntimeDir
    $repo = Assert-WALocalPath (Split-Path -Parent $PSScriptRoot)
    $python = (Join-Path $repo 'readonly_mcp/.venv/Scripts/python.exe').Replace('\','/')
    $launcher = (Join-Path $repo 'scripts/tunnel_mcp_child.py').Replace('\','/')
    $command = '"' + $python + '" -I "' + $launcher + '"'
    $profile = @{
        config_version = 1
        control_plane = @{ base_url='https://api.openai.com'; tunnel_id=$metadata.tunnel_id; organization_id=$metadata.organization_id; api_key='env:WA_TUNNEL_API_KEY' }
        health = @{ listen_addr='127.0.0.1:0'; url_file=(Join-Path $RuntimeDir 'health.url').Replace('\','/'); show_details=$false }
        admin_ui = @{ allow_remote=$false; open_browser=$false; log_buffer_events=1 }
        log = @{ level='warn'; format='json'; http_raw_unsafe=$false }
        mcp = @{ commands=@(@{ channel='main'; command=$command }); stdio_send_initialized_notification=$true; forward_trace_context=$false }
    }
    # JSON is a strict YAML subset; serialize data rather than interpolate YAML/command syntax.
    $path = Join-Path $RuntimeDir 'tunnel-profile.yaml'
    Write-WAText $path ($profile | ConvertTo-Json -Depth 8)
    return $path
}

function Get-WACleanEnvironment {
    $values = @{}
    foreach ($name in @('SystemRoot','WINDIR','SystemDrive','COMSPEC','USERPROFILE','LOCALAPPDATA','APPDATA','TEMP','TMP','HOMEDRIVE','HOMEPATH','USERNAME','USERDOMAIN','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE','PATHEXT')) {
        $value = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($value) { $values[$name] = $value }
    }
    $values['PATH'] = (Join-Path $env:SystemRoot 'System32') + ';' + (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0')
    return $values
}

function New-WATunnelProcess([string]$RuntimeDir, [ValidateSet('run','doctor')][string]$Mode) {
    $repo = Split-Path -Parent $PSScriptRoot
    $client = Join-Path $repo '.tools/tunnel-client/tunnel-client.exe'
    $pin = Get-Content -Raw -LiteralPath (Join-Path $repo 'audit/tunnel-client-pin.json') | ConvertFrom-Json
    $version = & $client --version
    if ($LASTEXITCODE -ne 0 -or $version -ne ($pin.version.TrimStart('v') + '+' + $pin.build_commit + ' (git sha: ' + $pin.build_commit + ')') -or (Get-FileHash -LiteralPath $client -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pin.binary_sha256) { throw 'Unreviewed tunnel client version or checksum.' }
    $profile = Write-WATunnelProfile $RuntimeDir
    $metadata = Get-WATunnelMetadata $RuntimeDir
    Add-Type -AssemblyName System.Security
    $cipherPath = Join-Path $RuntimeDir 'runtime-key.dpapi'
    $bytes = $null
    try {
        $cipher = [Convert]::FromBase64String([IO.File]::ReadAllText($cipherPath))
        $entropy = [Text.Encoding]::UTF8.GetBytes('WhatsappGptTunnel/runtime-key/v1')
        $bytes = [Security.Cryptography.ProtectedData]::Unprotect($cipher, $entropy, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        $info = [Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $client
        $info.Arguments = $Mode + ' --profile-file "' + $profile + '"'
        if ($Mode -eq 'doctor') { $info.Arguments += ' --explain --json' }
        $info.WorkingDirectory = $repo
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.EnvironmentVariables.Clear()
        foreach ($entry in (Get-WACleanEnvironment).GetEnumerator()) { $info.EnvironmentVariables[$entry.Key] = $entry.Value }
        $info.EnvironmentVariables['WA_DATA_DIR'] = $metadata.data_dir
        $info.EnvironmentVariables['WA_MCP_HEALTH_FILE'] = Join-Path $RuntimeDir 'mcp-health.json'
        $info.EnvironmentVariables['WA_TUNNEL_API_KEY'] = [Text.Encoding]::UTF8.GetString($bytes)
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $info
        if (-not $process.Start()) { throw 'Tunnel process did not start.' }
        # Never retain the decrypted key in reusable launch configuration or parent env.
        $info.EnvironmentVariables.Remove('WA_TUNNEL_API_KEY')
        return $process
    } catch { throw 'Tunnel startup failed. Check protected configuration and credential provisioning.' }
    finally { if ($null -ne $bytes) { [Array]::Clear($bytes, 0, $bytes.Length) } }
}
