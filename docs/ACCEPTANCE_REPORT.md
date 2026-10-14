# Acceptance report — 2026-10-13

**Go for synthetic operation and local review. No-go for claiming the real
WhatsApp system live or reboot-safe.** All five plans have implementation work;
final production exit criteria need physical/operator acceptance below.
Original plan texts remain unchanged in history-implementations.

| Area | Observed result |
|---|---|
| WA00 provenance/risk | Source and tools pinned; disclosed unofficial-client risk continuation recorded |
| WA01 collector | 13 Go tests passed; Windows CGO build; synthetic/unlinked process, storage/ACL and no-listener checks |
| WA02 read boundary | Exact six bounded stdio reads; actual SDK pipeline; rejected send/media/SQL/write operations; read-only SQLite authorizer |
| Local combined tests | 50 unique tests checked: full 49-test suite plus added activation test in a focused six-test rerun; 49 passed, one skipped for Windows symlink privilege; separate junction-refusal test passed |
| WA03 actual Work | Unicode attribution, fresh invented append without restart, inert injection, stopped tunnel timeout, app revocation and same-scope reconnection passed |
| Workspace scope | Sole saved Personal org/workspace; single operator Owner; personal development plugin; anonymous/fake-key API requests all 401; authenticated alternate-workspace call untested |
| Credentials | Restricted Read + Use only, DPAPI/current-user+SYSTEM ACLs, no plaintext output/file; expiry 2026-11-12 |
| WA04 recovery | Live WAL snapshot, tamper/cap guards, session-backup lock, quarantined restore/startup refusal, explicit synthetic deletion, supervisor restart/singleton/stop passed |
| Windows jobs | Two disposable logon-only InteractiveToken tasks registered and started independently, gracefully stopped and removed; final orphan check passed; boot-trigger registration refused 80070005 |
| Host | AC sleep never; battery 15min; firewall enabled/default inbound Block; no project Defender exclusions; adapter power inspection unavailable; no policy changes |
| Freshness diagnostics | Real Work health call recorded a bounded local success timestamp; collector correctly remains synthetic/disconnected/stale/partial |

All queries used invented fixture content. Four chats and thirteen unique
messages are currently in the acceptance store. The fresh-append test returned
an unknown unique result proof after Go ingestion; this proves visibility without
restart, not WhatsApp ingestion latency. No real-message lag or historical
coverage was measured. Work response times include model/tool handling and are
not transport or WhatsApp real-time guarantees. Vendor MCP health remains
not_observed despite successful actual calls; six_tools_observed is kept false.

At the 2026-10-13 acceptance check no phone account was paired or production
startup jobs installed. On 2026-10-14 the operator requested public publication
of the implementation and this report; that does not complete the remaining
production acceptance steps. Credentials, messages, session files, databases,
generated runtime configuration, screenshots and sensitive logs are excluded.
A foreground tunnel may stop when its
launching session ends. Use the local run command or verified installed jobs;
do not infer continuous service from this report.

## Human production checklist

1. Pair locally using the phone QR in a non-recorded foreground terminal;
   verify the expected companion in Linked devices. Retain conscious acceptance
   of the unofficial-client risk. No QR, session or phone IDs in evidence.
2. Review activate_store.ps1 preview, confirm real-data routing and retain the
   narrowly saved workspace/plugin scope. If another workspace/account is
   available, test its authenticated access boundary; do not grant one for testing.
3. Have a local administrator register the reviewed boot jobs as the original
   owner, least privilege, using that owner's local Windows credential. Verify
   CurrentUser DPAPI/DB access and batch logon rights without broadening policy.
4. Start jobs, close launching terminals, sign out and reboot at a chosen time.
   Verify collector/tunnel operation before the interactive user logs in. This
   workflow has not rebooted or signed out the user's active PC.
5. Receive one controlled real message in an intentionally chosen chat after
   startup. Compare local receive/insert time with a fresh Work query and record
   actual lag privately. Inspect correct chat, sender and UTC date.
6. Ask for a bounded date-range summary from the selected contact; inspect
   attribution/message IDs and ensure an unrelated chat is excluded. Privately
   record oldest/newest actually synced coverage; never infer missing years.
7. Temporarily remove network; require accurate stale/degraded status; restore
   and verify recovery. Test real unlink/expiry/re-link only at a deliberate time.
   Recheck key expiry, permission changes and app access after updates.
8. Confirm no messages, keys, QR, sessions or identifiers appear in Git, CI,
   logs or exported task files. Follow backup/kill-switch/data lifecycle runbooks.

Run synthetic checks again after relevant changes:

```powershell
.\scripts\build_bridge.ps1 -Test
& .\readonly_mcp\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v
& .\readonly_mcp\.venv\Scripts\python.exe .\scripts\test_bridge_runtime.py
.\scripts\test_startup_tasks.ps1
```

The Scheduler harness uses a fresh synthetic store, fake key, unique test names,
logon-only triggers and final cleanup. It neither pairs a device nor establishes
boot/logged-off acceptance. No GPT background monitoring or notifications exist;
retrieval remains on demand. Costs and ordinary-chat compatibility remain
account/product-specific and unverified.
