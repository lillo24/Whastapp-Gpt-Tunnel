# Application read-only proof — 2026-10-12

This records the implemented local boundaries and synthetic evidence. It is
not a proof against arbitrary code execution or malware running as this user.

The shipped Go application contains no HTTP server/handler, send dispatcher,
SendMessage, media Upload or Download call. Allowed commands are run, pair,
logout, fixture and stop. Negative send commands fail with fixed redacted
stderr. Manual pairing requires both stdin/stdout terminals before opening a
store; headless startup never renders QR. Logout is an explicit operator device
operation, unavailable from MCP. Third-party WhatsApp logs are discarded.

Pinned whatsmeow retains internal protocol capabilities needed for a linked
device. Protocol acknowledgments/history synchronization are distinct from
user-authored outgoing messages. We removed application access to sends and
downloads; we do not claim every third-party protocol method has been erased.
The unmodified upstream checkout remains ignored under `.audit`, and is not
part of the build or runtime launch.

Actual Windows process tests started synthetic and unlinked collectors with
closed stdin. Each PID had zero TCP listeners according to Get-NetTCPConnection.
Second-writer startup failed, local stop was clean, stdout/stderr stayed empty,
and private-looking invalid arguments were not echoed. NTFS root and generated
file ACLs are checked for only current-user/SYSTEM full access, with a protected
root. Synthetic mode creates no WhatsApp session database. These checks do
not establish behavior of a real linked account, which was not tested.

Python imports only the new query/contracts/operational-health modules and the locked MCP stdio
SDK. It imports no upstream REST client, WhatsApp send, audio, download or
subprocess application helper. There is no URL fetch, arbitrary SQL, file path,
recipient, credential, write or media operation among the six tools. The SDK's
transitive HTTP packages support other SDK transports; this entrypoint only
starts stdio and registers no HTTP transport or listener.

The only data file opened by the query service is canonical
`WA_DATA_DIR/messages.db`, with SQLite `mode=ro`. It never opens `whatsapp.db`.
Tools cannot change the trusted directory. Link/canonical checks precede open;
the runtime directory ACL restricts who can replace files. SQLite authorizer
permits only SELECT, reads of the three approved tables, read transactions,
user_version inspection and a small function allowlist. Extension loading is
disabled. All dynamic filter values are bound parameters; SQL templates and
table names are fixed. There is no writable PRAGMA, ATTACH or generic SQL API.

Tests attempt DELETE, CREATE, ATTACH, load_extension and writable PRAGMA against
the actual service connection: all denied, DB unchanged. Missing DB is not
created; unknown schemas, locked DB, malformed filters, forged/filter-mismatched
cursors and unsupported write/file/media tool names return fixed errors.
Canonical-path refusal passes. One Windows symlink creation test was skipped
because the test process lacks symlink privilege; source resolves/rejects
redirected files, but that particular filesystem scenario is unverified here.

Actual SDK stdio tools/list reports only approved names and all four read-only
annotations. Process tests cover Go fixture → SQLite → MCP, live fixture append
visible without MCP restart, protocol-only stdout, closed stderr, repeated calls,
malformed JSON-RPC parameters without echo, negative tool calls and clean EOF.
Long Unicode outputs are bounded and paged without losing rows; contexts retain
the target. Media legacy secret columns and unrelated names do not enter results.

Every successful read warns PARTIAL_HISTORY. Disconnected/stale states are
explicit, including when stored history remains readable. Prompt-injection
text is returned as inert data with untrusted-content instructions. The server
has no means to execute its instructions or follow URLs; a model using other
plugins still requires appropriate user/product controls. Repeated authorized
pages can disclose substantial history, so bounded calls are not a total
session quota. Same-user/admin malware, a compromised dependency, and a caller
authorized too broadly remain outside this local query boundary.

The WA04 operational-health addition can write only the trusted configured
runtime's fixed mcp-health.json through an atomic replacement. Its bounded data
is a process ID, count, timestamps and fixed error class; it never contains tool
names, arguments, results or message text. No MCP argument chooses this path.
It does not open or write either data/session database. Operator backup/restore/
deletion scripts are separate local commands, never tools in the MCP registry.
Restored stores carry a Go-enforced network-startup quarantine.

WA03 synthetic Work tests now verify the actual scoped tunnel/plugin path,
inert prompt injection and app revocation. No real WhatsApp chat was used.
An authenticated alternate-workspace boundary remains untested. See
`WA03_VALIDATION.md`, `ACCEPTANCE_REPORT.md` and `SUPPORTED_SURFACE.md`.
