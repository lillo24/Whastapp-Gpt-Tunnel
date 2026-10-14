#Requires -Version 7.0
. (Join-Path $PSScriptRoot 'tunnel_common.ps1')

function Initialize-WAPrivateFolder([string]$Path, [string]$Marker) {
    $dir = Assert-WALocalPath $Path
    $markerPath = Assert-WALocalPath (Join-Path $dir $Marker)
    $alreadyPrivate = Test-Path -LiteralPath $markerPath -PathType Leaf
    if (Test-Path -LiteralPath $dir) {
        if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf) -and @(Get-ChildItem -Force -LiteralPath $dir).Count) { throw 'Refusing to adopt unrelated operation files.' }
        if ((Test-Path -LiteralPath $markerPath) -and [IO.File]::ReadAllText($markerPath) -ne 'wa-operations-v1') { throw 'Unknown operation directory marker.' }
    } else { [IO.Directory]::CreateDirectory($dir) | Out-Null }
    # Walk one level at a time and refuse reparse points before descending.
    $pending = [Collections.Generic.Stack[string]]::new()
    $pending.Push($dir)
    $all = [Collections.Generic.List[IO.FileSystemInfo]]::new()
    while ($pending.Count) {
        foreach ($item in Get-ChildItem -Force -LiteralPath $pending.Pop()) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Redirected operation files are refused.' }
            $all.Add($item)
            if ($item.PSIsContainer) { $pending.Push($item.FullName) }
        }
    }
    $identities = @([Security.Principal.WindowsIdentity]::GetCurrent().User, [Security.Principal.SecurityIdentifier]::new('S-1-5-18'))
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($identity in $identities) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')) }
    [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($dir),$acl)
    # Existing children inherited the protected root. Avoid reopening exclusive
    # supervisor lock files merely to ask for status or stop the service.
    foreach ($item in $(if ($alreadyPrivate) { @() } else { $all })) {
        if ($item.Attributes -band [IO.FileAttributes]::Directory) { [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($item.FullName),$acl) }
        else {
            $fileAcl = [Security.AccessControl.FileSecurity]::new()
            $fileAcl.SetAccessRuleProtection($true,$false)
            foreach ($identity in $identities) { $fileAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','Allow')) }
            [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($item.FullName),$fileAcl)
        }
    }
    if (-not (Test-Path -LiteralPath $markerPath)) { Write-WAText $markerPath 'wa-operations-v1' }
    return $dir
}

function Assert-WAUnregistered([object]$Config) {
    $folder = Get-WATaskService
    foreach ($component in @('bridge','tunnel')) {
        if ($null -ne (Get-WATask $folder ($Config.task_prefix+'-'+(Get-Culture).TextInfo.ToTitleCase($component)))) {
            throw 'Uninstall the owned startup tasks before activating a store or deleting data.'
        }
    }
}

function Open-WAIdleLocks([object]$Config, [string]$OpsDir) {
    $handles = [Collections.Generic.List[IO.FileStream]]::new()
    try {
        foreach ($path in @((Join-Path $Config.data_dir 'collector.lock'),(Join-Path $Config.runtime_dir 'runtime.lock'),(Join-Path $OpsDir 'bridge.lock'),(Join-Path $OpsDir 'tunnel.lock'))) {
            $checked = Assert-WALocalPath $path
            if (Test-Path -LiteralPath $checked) { $handles.Add([IO.File]::Open($checked,'Open','ReadWrite','None')) }
        }
        return ,$handles
    } catch { foreach ($handle in $handles) { $handle.Dispose() }; throw 'A collector, tunnel or supervisor is active. Stop it before this operation.' }
}

function Get-WARecordedProcess([string]$StateFile, [string]$ExpectedExe) {
    try {
        $path=Assert-WALocalPath $StateFile
        $ExpectedExe=[IO.Path]::GetFullPath($ExpectedExe)
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $null }
        $state=Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
        $process=Get-Process -Id $state.pid -ErrorAction Stop
        if ($process.Path -ne $ExpectedExe -or $process.StartTime.ToUniversalTime().Ticks -ne ([datetime]$state.started_at).ToUniversalTime().Ticks) { $process.Dispose(); return $null }
        return $process
    } catch { return $null }
}

function Get-WAOperations([string]$OpsDir) {
    $dir = Initialize-WAPrivateFolder $OpsDir '.wa-operations'
    $config = Get-Content -Raw -LiteralPath (Join-Path $dir 'operations.json') | ConvertFrom-Json
    if ($config.schema_version -ne 1 -or @($config.PSObject.Properties.Name | Where-Object { $_ -notin @('schema_version','data_dir','runtime_dir','backup_dir','synthetic','task_prefix') }).Count) { throw 'Unknown operation configuration.' }
    $config.data_dir = Assert-WALocalPath $config.data_dir
    $config.runtime_dir = Assert-WALocalPath $config.runtime_dir
    $config.backup_dir = Assert-WALocalPath $config.backup_dir
    if ($config.synthetic -isnot [bool] -or $config.task_prefix -notmatch '^WhatsappGptTunnel(?:-Test-[a-f0-9]{8})?$') { throw 'Invalid operation mode or task names.' }
    $tunnel = Get-WATunnelMetadata $config.runtime_dir
    if ($tunnel.data_dir -ne $config.data_dir) { throw 'Collector and tunnel stores differ; explicit activation is required.' }
    return $config
}

function Invoke-WAOperation([string]$OpsDir, [string]$Operation, [string[]]$Extra = @()) {
    $repo = Split-Path -Parent $PSScriptRoot
    $null = Get-WAOperations $OpsDir
    & (Join-Path $repo 'readonly_mcp/.venv/Scripts/python.exe') -I (Join-Path $PSScriptRoot 'operations.py') $Operation --config (Join-Path $OpsDir 'operations.json') @Extra
    if ($LASTEXITCODE -ne 0) { throw 'Operation refused or failed; inspect its fixed error class.' }
}

function Get-WATaskService {
    $scheduler = New-Object -ComObject Schedule.Service
    $scheduler.Connect()
    return $scheduler.GetFolder('\')
}

function Get-WATask([object]$Folder, [string]$Name) {
    try { return $Folder.GetTask($Name) }
    catch {
        if ($_.Exception.GetBaseException().HResult.ToString('X8') -eq '80070002') { return $null }
        throw 'Windows task state could not be read; refusing to assume the task is absent.'
    }
}

function Assert-WAOwnedTask([object]$Task, [string]$Component) {
    if ($Task.Definition.RegistrationInfo.Description -ne ('WhatsappGptTunnel operations v1; ' + $Component)) { throw 'Refusing to alter an unrelated scheduled task.' }
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $taskSid = [Security.Principal.NTAccount]::new($Task.Definition.Principal.UserId)
    if ($Task.Definition.Principal.UserId -match '^S-1-') { $actual = $Task.Definition.Principal.UserId }
    else { $actual = $taskSid.Translate([Security.Principal.SecurityIdentifier]).Value }
    if ($actual -ne $sid) { throw 'Scheduled task belongs to another identity.' }
}

function New-WATaskXml([string]$OpsDir, [string]$Component, [switch]$InteractiveTest) {
    $repo = Assert-WALocalPath (Split-Path -Parent $PSScriptRoot)
    $pwsh = [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    if ([IO.Path]::GetFileName($pwsh) -ne 'pwsh.exe') { throw 'Task preparation requires PowerShell 7.' }
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $delay = if ($Component -eq 'bridge') { 'PT15S' } else { 'PT30S' }
    $bootDelay = if ($Component -eq 'bridge') { 'PT1M' } else { 'PT2M' }
    $logon = if ($InteractiveTest) { 'InteractiveToken' } else { 'Password' }
    $limit = if ($InteractiveTest) { 'PT10M' } else { 'PT0S' }
    # A disposable standard-user test exercises the job runtime while logged in.
    # Production retains BootTrigger and needs administrator registration.
    $bootTrigger = if ($InteractiveTest) { '' } else { "<BootTrigger><Enabled>true</Enabled><Delay>$bootDelay</Delay></BootTrigger>" }
    $arguments = '-NoProfile -NonInteractive -File "' + (Join-Path $PSScriptRoot 'supervise.ps1') + '" -Component ' + $Component + ' -OpsDir "' + $OpsDir + '"'
    $escapedExe = [Security.SecurityElement]::Escape($pwsh)
    $escapedArgs = [Security.SecurityElement]::Escape($arguments)
    $escapedRepo = [Security.SecurityElement]::Escape($repo)
    return @"
<?xml version="1.0"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
 <RegistrationInfo><Description>WhatsappGptTunnel operations v1; $Component</Description></RegistrationInfo>
 <Triggers>$bootTrigger<LogonTrigger><Enabled>true</Enabled><UserId>$sid</UserId><Delay>$delay</Delay></LogonTrigger></Triggers>
 <Principals><Principal id="Operator"><UserId>$sid</UserId><LogonType>$logon</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
 <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable><IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings><AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled><Hidden>false</Hidden><ExecutionTimeLimit>$limit</ExecutionTimeLimit><Priority>7</Priority><RestartOnFailure><Interval>PT1M</Interval><Count>3</Count></RestartOnFailure></Settings>
 <Actions Context="Operator"><Exec><Command>$escapedExe</Command><Arguments>$escapedArgs</Arguments><WorkingDirectory>$escapedRepo</WorkingDirectory></Exec></Actions>
</Task>
"@
}
