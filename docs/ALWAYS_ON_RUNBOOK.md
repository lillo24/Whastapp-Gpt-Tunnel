# Windows operations — implementation ready, production acceptance pending

Use PowerShell 7 as the private store owner, from the checkout. Keep the checkout
at its fixed absolute location; generated tasks contain absolute executable,
script and Start In paths. Toolchains and Python dependencies must already be
installed from the pins/lockfile. No runtime downloads occur.

`install.ps1` prepares protected configuration and two reviewable XML files
under `%LOCALAPPDATA%/WhatsappGptTunnel/operations`. Default is preview only.
Current configuration still targets invented data. Start/stop/status commands:

```powershell
.\scripts\install.ps1
.\scripts\start.ps1
.\scripts\status.ps1
.\scripts\stop.ps1
.\scripts\uninstall.ps1
# After reviewing the uninstall preview:
.\scripts\uninstall.ps1 -Apply -ConfirmUninstall
```

Start requires registered jobs. Stop signals both supervisors/children, waits
for idle locks and exit, and can terminate a recorded orphan only after matching
its executable and exact creation time. It retains databases, key and session.
Uninstall waits for stop before removing only two owned jobs and
retains all data. Supplied OpsDir lets isolated synthetic tests use their own
configuration and task names.

Production uses Password logon with LeastPrivilege, not Administrator/SYSTEM.
Bridge boot delay is one minute, tunnel two minutes; logon delays are 15/30
seconds. Scheduler ignores duplicates and allows three one-minute retries. Each
supervisor has an exclusive lock, five bounded child attempts with exponential
delay, a graceful stop and final child-tree cleanup. Collector network retry is
1 second to 1 minute; revoked/unlinked sessions require manual pairing and never
show unattended QR. The tunnel owns the sole stdio MCP child.

## Local administrator and credential handoff

On this host boot-trigger registration returned **80070005 Access denied** from
the standard-user process. Microsoft requires an administrator to create a
[boot-trigger task](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskfolder-registertask).
Two disposable logon-only InteractiveToken jobs registered and ran successfully;
that does not establish boot/logged-off operation.

An administrator must import the reviewed bridge.task.xml/tunnel.task.xml into
Task Scheduler as WhatsappGptTunnel-Bridge / WhatsappGptTunnel-Tunnel. If a
different administrator account is used, the owner can provide copies of only
these XML files in an agreed local handoff folder; they contain paths and the
owner SID, no key, password or message data. Keep the execution principal as the
original store owner, Run whether user is logged on or not, and leave Run with
highest privileges unchecked. Enter that owner's Windows account password
locally, not its PIN and never in chat or a command-line string. Check that the
owner has Log on as a batch job; do not broaden rights automatically. Remove
handoff XML copies after successful import. The owner must retain permission
to start/stop/unregister these jobs.

For an owner who can register boot jobs in their own elevated local session,
the script accepts a PSCredential object obtained locally:

```powershell
$startupCredential = Get-Credential
.\scripts\install.ps1 -Apply -ConfirmInstall -Credential $startupCredential
$startupCredential = $null
```

Do not run the daemons as a different administrator to work around ACL/DPAPI.
Microsoft documents that [S4U lacks network/encrypted-file access, while
InteractiveToken requires an existing logon](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskfolder-registertask).
Those modes do not establish the required logged-off CurrentUser-DPAPI runtime.
Task registration credentials and batch rights are described in
[security contexts](https://learn.microsoft.com/en-us/windows/win32/taskschd/security-contexts-for-running-tasks).

## Pair and activate only in a local foreground session

The unofficial-client account risk is recorded in OPERATOR_DECISIONS.md. A phone
scan cannot be automated from this PC. Use a private terminal without recording:

```powershell
.\scripts\pair_bridge.ps1
```

Scan from WhatsApp Linked devices; stop the foreground process before activation.
This defaults to a separate protected real store, leaving fixture data separate.
The following helper validates linked/non-synthetic schema 1, refuses restored
sessions, requires unregistered/stopped jobs, preserves old data and retains the
same tunnel/workspace associations:

```powershell
$pairedStore = Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/store'
.\scripts\activate_store.ps1 -DataDir $pairedStore
# Only after reviewing the real-data routing preview:
.\scripts\activate_store.ps1 -DataDir $pairedStore -Apply -ConfirmRealData
.\scripts\install.ps1
```

Then register jobs locally and perform the human checklist in ACCEPTANCE_REPORT.md.
Do not call the system live until a real message is collected and queried after
reboot with no terminal or interactive user session keeping the jobs alive.

## Host and maintenance

Observed 2026-10-13: Balanced plan, AC sleep never, battery sleep 15 minutes;
hibernation timeout zero. Effective firewall inbound policy is Block for Domain,
Private and Public; all enabled. No project path/bridge/tunnel/Python Defender
exclusion was found. Adapter power inspection was unavailable. No policy or
adapter setting changed. Stay on AC for the intended always-on operation; review
sleep/network interruption deliberately rather than changing global settings.
The collector/MCP have no listeners; actual client binds only 127.0.0.1. No new
firewall rule, router forwarding or shared/network SQLite location is needed.

`status.ps1` separates linked, connected, DB access, receive/sync/heartbeat,
tunnel status and last successful MCP execution. It never proves history
completeness. A quiet connected collector can be fresh; an old/disconnected
heartbeat is stale even if old messages remain readable. The tiny local
mcp-health.json stores timestamps/count/fixed error class, no call data. Vendor
six_tools_observed may remain false due to the observed diagnostic gap.

Supervisor logs contain only component/start/retry/stop/date/exit code, capped
at approximately 128 KiB plus one previous file. Child output is discarded.
Review Windows updates, then stop, opt into backup if wanted, review upstream
diffs/dependency pins, build/test and smoke-test before restarting. Never auto
upgrade whatsmeow, tunnel binary or the SDK. Dependency updates need fresh review
of protocol/auth/privacy behavior. Re-run tests after a change; never export
private runtime files or raw support logs to CI.
