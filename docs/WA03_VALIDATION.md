# WA03 validation — synthetic functional gate passed

Validated 2026-10-12 on Windows with existing PowerShell 7.6.5, Python 3.12.14,
official tunnel-client v0.0.16 build 5f99daabd4aa4a77049e6d81d54a0d8c18335397
and the locked WA02 SDK. Archive and extracted binary SHA256 are in
`audit/tunnel-client-pin.json`. The local test suite uses fake keys; the approved
real runtime credential was used for control-plane connection and approved
synthetic ChatGPT Work tests on 2026-10-13.
No WhatsApp account or private message data is used.

## Account state

Operator approval **“Yes”** covered the reviewed private tunnel Create action.
Creation succeeded. Edit displayed the saved name, description and sole
Personal organization/workspace associations. IDs and review screenshots remain
local/ignored.

The exact runtime key draft has You, Default project, Restricted, only Tunnels
Read + Use, all other API permissions None and 30-day expiration. The operator
approved it; creation and DPAPI protection succeeded on 2026-10-13, with UI expiry
2026-11-12. No key value was exposed in chat/tool output, saved as plaintext or
passed in arguments.
The protected local profile targets only an
invented Go-created store (four chats, initially twelve unique messages;
thirteen after the fresh-append test).

## Implemented runtime controls

- `init_tunnel.ps1`: private dedicated flat directory and marker; current-user
  and SYSTEM DACL only; fixed profile; refuse unrelated folders, volume/network/
  relative paths, redirected paths and unreviewed association changes.
- `provision_tunnel_key.ps1`: random local pipe name, ACL to current user/SYSTEM,
  network-logon deny; bounded transfer and timeout; current-user DPAPI with fixed
  app entropy; no plaintext file, console input, argument or transcript. Hold
  the sender open until the receiver acknowledges encryption. Existing keys
  require explicit rotation via Replace.
- `run_tunnel.ps1`: verify client build/hash, regenerate fixed configuration,
  inject decrypted key into only the new process configuration, remove it from
  reusable launch state, drain output without retaining logs; exclusive lock
  prevents duplicate instances. Stop request ends the client and its child tree.
- `tunnel_mcp_child.py`: trusted launcher clears inherited secret/config before
  UV/MCP starts; fixed absolute locked/offline UV command, binary stdio unchanged.
- `check_tunnel.ps1`: sanitized doctor summary or local bounded health status;
  verify PID creation time and executable, refuse a nonloopback health URL,
  separate process/startup readiness, control-plane observation, exact complete
  six-tool discovery and collector freshness.

PowerShell 7 uses the existing RemoteSigned policy. Windows PowerShell 5.1 was
Restricted and refused the first provisioning attempt; its policy was not changed
or bypassed. The new runtime scripts explicitly require PowerShell 7.

## Test evidence

Full Python acceptance suite: **42 run, 41 passed, 1 skipped**. The existing
symlink privilege skip remains; the new runtime junction-refusal check passes
without that privilege. PowerShell syntax, pinned client extraction/hash and
Git whitespace checks passed. Earlier WA01 Go/build/storage results remain valid.

`tests/test_tunnel_environment.py` verifies credential/proxy/config removal and
case-insensitive Windows environment names. `tests/test_tunnel_security.py`
verifies private ACLs and DPAPI decryption with a fake key, idempotent setup,
poisoned inherited client configuration isolation, missing/corrupt/duplicate
credential failures, association/path guards, an actual fake-key runtime,
127.0.0.1-only listener, single runtime and clean stop/unavailable status.

`tests/test_mcp_protocol.py` now exercises the exact sanitized tunnel child
launcher through the official SDK: six read-only tools, synthetic Unicode
query, fresh append visible without restart, and fixed refusal of write/media/
SQL tool names. A separate raw JSON-RPC test still covers the direct server.

The client process with the fake key is local runtime/bind/failure evidence.
It does not establish valid authorization. Doctor also succeeds with a fake key:
its result is explicitly labeled configuration-only and skips stdio reachability.
That fake-key test does not establish synthetic ChatGPT invocation. The separate
approved real-tunnel Work tests below do.

## Real runtime authorization — 2026-10-13

The actual client completed successful polls with zero consecutive failures.
Its local UI showed live/ready, fixed main stdio channel, direct control-plane
connection, disabled Harpoon and no log events at warn level. Initial startup
readiness preceded successful polling. Vendor MCP health remained `not_observed`
even after successful Work calls; this is an observed diagnostic gap, with root
cause unproven. No MCP or model response is inferred from
process liveness, startup readiness or the Create-as-plugin metadata step.
Direct checks of the actual runtime confirmed protected root/key DACLs with
only the current user and SYSTEM having FullControl, and exactly one client
listener at 127.0.0.1. Safe results are recorded in
`audit/wa03-transport-acceptance.json` without identifiers or credentials.

`test_tunnel_access.ps1` made four requests to the pinned vendor protocol's
plural `/v1/tunnels/{id}` metadata/poll routes: anonymous and fake-key variants
all returned HTTP 401. The test never decrypts the real key or reads response
bodies. It is limited to control-plane authorization; another ChatGPT workspace's
MCP invocation boundary is not tested by these requests.

## Approved ChatGPT Work acceptance — 2026-10-13

The operator's **Continue** approved the specific Connect and synthetic tests,
including disconnect/reconnect. The personal cloud plugin is Connected in
development mode, with exactly six Read tools and untrusted-content descriptions.
Local SDK tests verify all four tool annotations.

| Test | Actual result |
|---|---|
| Fresh health and Unicode query | Successful calls; correct invented ID/date/text; synthetic/partial/stale flags |
| Append after initial query | Work knew only a unique search marker and returned the unknown ID/time/proof without restarting client/MCP |
| Injected instructions | Inert short quotation; no URL followed or other app called; six reads only |
| Stop local tunnel | Fresh health returned MCP timeout; no cached health reused |
| Disconnect app while tunnel runs | Tool absent from Work's current registry; no call attempted |
| Reconnect same app/scope | Fresh health and exact-marker reads succeeded again |
| Updated local execution timestamp | Fresh Work health succeeded; bounded local telemetry recorded it without arguments/results |

The synthetic functional gate passed, permitting WA04 implementation. A separate
authenticated alternate-workspace invocation test, physical network/sleep
recovery and controlled real pairing remain untested. Four control-plane 401s
do not substitute for the alternate-workspace test. See ACCEPTANCE_REPORT.md.
