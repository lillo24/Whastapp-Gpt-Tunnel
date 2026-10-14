# Recovery and freshness

Start with scripts/status.ps1. No recent messages alone does not imply a failure;
look at linked/connected and heartbeat. GPT must report stale/partial warnings
and last verified sync time, avoiding a claim of the latest messages while
disconnected. Historical coverage remains partial even after healthy startup.

| Condition | Action |
|---|---|
| RELINK_REQUIRED / phone removed device | Stop jobs; inspect Linked devices; run the separate foreground pair command on a fresh store; never print QR unattended |
| DISCONNECTED / CONNECT_FAILED | Check the PC network and heartbeat; collector retries with capped backoff; old messages may remain readable with stale warning |
| DB_UNAVAILABLE / unknown schema / corrupt DB | Stop writer; retain originals; validate an opt-in snapshot into a quarantined disconnected path; review migration/version before reuse |
| Tunnel unavailable | Check local process separately from control-plane status; verify current-user DPAPI and fixed profile; restart only after resolving the cause |
| Key expired/revoked | Review the existing runtime key's Read + Use scope; refresh/rotate through official UI and protected pipe with Replace; never use an admin key or paste it into chat |
| Tunnel ID revoked / app permission changed | Verify saved org/workspace mapping and private plugin installation; stop access if scope cannot be established; no public proxy workaround |
| Protocol/library incompatibility | Stop collection, retain data, review a pinned upstream change and synthetic tests; account compatibility is not proven by endless restart |
| Boot registration 80070005 | Local administrator registration is required; keep the daemon principal as the protected-store owner, least privilege |
| Child repeatedly exits | Supervisor stops after bounded attempts; inspect fixed event/exit classes; do not turn on raw private-content logging |
| six_tools_observed=false while Work succeeds | Pinned vendor diagnostic gap; inspect real Work results and local execution timestamp; do not fabricate a successful diagnostic |

Pairing uses scripts/pair_bridge.ps1 in a private foreground terminal with a
phone scan. Re-link does not delete old history. Use the activation preview and
explicit real-data confirmation from ALWAYS_ON_RUNBOOK.md before routing a new
paired store to the existing app. A restored credential copy is quarantined.

Actual tests: tunnel stopped → Work MCP timeout, app disconnected → tool absent,
reconnect → fresh reads work, synthetic child killed → supervisor restarts it,
active collector → session backup refused, corrupt/unknown DB → fixed error.
Physical network outage, sleep, real phone unlink, real key/tunnel revocation,
Windows reboot and logged-off startup remain manual acceptance cases. Do not
confuse app disconnect with API-key or WhatsApp-device revocation.
