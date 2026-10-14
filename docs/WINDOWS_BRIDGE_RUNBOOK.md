# Windows bridge

WA01 implements a passive linked-device collector. Operator risk acceptance is
recorded in `OPERATOR_DECISIONS.md`; no account has been paired by the agent.
The reviewed source/dependencies remain pinned; real WhatsApp compatibility is
unverified. Original MIT notice is retained in `bridge/LICENSE.upstream`.

```powershell
.\scripts\setup_toolchain.ps1
.\scripts\build_bridge.ps1 -Test
python .\scripts\test_bridge_runtime.py
```

Toolchain archives and 19 UCRT64 compiler packages have exact SHA256 pins in
`audit/`. The setup uses official Go, MSYS2 and Astral releases, validates hashes,
and installs only under ignored `.tools`. MSYS2 package signatures are checked
by pacman. Reproduction uses the pinned package set, not a rolling upgrade.
Build scripts restore process PATH/CC/CGO/cache settings when finished and never
use global `go env -w`. No FFmpeg is required.

## Manual foreground pairing

In a private local terminal with transcription/recording disabled, deliberately
run `scripts/pair_bridge.ps1`. It requires a real terminal for stdin/stdout and
displays QR blocks there only. Scan using WhatsApp Linked devices. The command
exits after pairing; then start `scripts/run_bridge.ps1` for collection. Neither
setup nor ordinary `run` generates QR. A missing session remains headless with
`RELINK_REQUIRED` and a heartbeat. Pairing has not been exercised with real data.

Default store: `%LOCALAPPDATA%\WhatsappGptTunnel\store`. Override with an
absolute `-DataDir` script argument or `WA_DATA_DIR` for the executable. An
existing populated unrelated directory, redirected directory/file, volume root
or relative directory is rejected. Use local NTFS storage, not network/cloud
sync. A marker identifies an initialized dedicated store; do not copy it to
unrelated folders. The Windows ACL grants only the current user and SYSTEM.

```powershell
# Start collection in the foreground (safe unlinked state if no session).
.\scripts\run_bridge.ps1
# Graceful stop from another local terminal; no network control endpoint.
.\bin\wa-bridge.exe stop --data-dir "$env:LOCALAPPDATA\WhatsappGptTunnel\store"
# Stop collection first, then revoke the linked device deliberately.
.\bin\wa-bridge.exe logout --data-dir "$env:LOCALAPPDATA\WhatsappGptTunnel\store"
```

Unlink in the phone's Linked devices controls if protocol logout is unavailable.
Logout leaves history intact. After unlinking, run manual pair again; never
delete history to fix authentication. No cleanup/deletion command is provided.
Unattended jobs/boot/reboot acceptance belong to WA04 after WA03 is verified.

## Behavior and limitations

- Incoming text and passive HistorySync are persisted with exact sender and UTC
  dates; a duplicate `(id,chat_jid)` is ignored. Old history cannot regress chat
  recency. Unknown group senders are explicitly `unresolved`.
- Image/video captions and coarse image/video/audio/document markers are stored.
  No bytes, filenames, URLs or media keys from new events are retained.
- Edits, deletes, reactions, disappearing/view-once/wrapped messages and unsupported
  event types are skipped. There is no retention job or exact mirroring of later
  deletion; stored text may outlive WhatsApp content. No complete backfill claim.
- Initial/reconnect attempts back off 1,2,4…60 seconds. Protocol errors are not
  logged. Failure-injection tests verify retry/recovery/cancel behavior; actual
  WhatsApp outage/relink behavior awaits manual acceptance. The pinned client's
  synchronous Connect can delay cancellation until its network call returns.
- Status heartbeat is 30 seconds, independent of chat activity. Connection state
  and ingest/history timestamps are distinct; neither proves complete coverage.
- The executable has no listener, arbitrary command execution, sends, uploads,
  download dispatch or runtime toggle for those capabilities. CLI commands are
  exactly run/pair/logout/fixture/stop. Synthetic fixtures cannot be inserted
  into a populated production store.

Runbook examples never include keys, QR payloads, phone numbers or real chats.
