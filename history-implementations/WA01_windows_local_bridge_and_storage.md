# WA01 — Windows Go Bridge, Private Storage & Zero Send Surface

**Standalone Codex implementation prompt. Dependency: WA00.**

## Mission

Turn the reviewed upstream Go bridge into a **local-only, read-only WhatsApp message collector** for an always-on Windows PC. Preserve the minimum code needed for WhatsApp connection, receiving incoming messages, initial history-sync events, and SQLite persistence. Make it reproducibly buildable on Windows. No WhatsApp pairing in this phase until the WA00 risk gate is explicitly accepted; most tests use synthetic data.

## Starting facts (verify against pinned upstream)

- Source: `whatsapp-bridge/main.go`; `go.mod` declares Go 1.24.1, `github.com/mattn/go-sqlite3`, and `whatsmeow`.
- Upstream stores messages in `whatsapp-bridge/store/messages.db` and its linked-device session in `whatsapp-bridge/store/whatsapp.db`.
- Its `startRESTServer()` exposes unauthenticated `/api/send` and `/api/download` on all interfaces via `http.ListenAndServe(":8080", ...)`, and its logs print message contents. These are unsafe defaults for private data on an always-on PC.
- Python MCP in WA02 reads SQLite directly: **for text search, the HTTP bridge API is unnecessary**.

## Strict implementation scope

1. **Remove the network listener entirely** from the shipped read-only bridge (preferred for text-only mode). Remove/unregister `/api/send` and `/api/download` and prevent any entrypoint from exposing a messaging API. If upstream protocol mechanics require other network traffic to WhatsApp servers, preserve only necessary outbound client traffic and document it. Do not conflate protocol acknowledgments with user-generated WhatsApp sends.
2. Remove user-facing sending capabilities, including interactive CLI commands for text, files, voice or arbitrary recipients, and any daemon endpoint or environment toggle that would re-enable them. Do not ship dormant dispatch code reachable from runtime config. Future write support is out of scope.
3. Refactor runtime into a headless executable with graceful shutdown, reconnect/backoff, re-link-required state, and clean handling of stdin closure. Audit `main()` to ensure it does not die or spin when run by Task Scheduler without interactive console input. Retain a separate **manual, local, foreground pairing command** that displays QR only on the operator's terminal, requires explicit human action, and never logs the QR payload.
4. Define stable **absolute** data/config paths via approved environment or config settings; do not rely on the service working directory. Preserve database schema/migrate safely, back up before changing existing schema, and ensure only one writer runs. Use transactional/deduplicated inserts keyed by `(id, chat_jid)`; preserve historical timestamps and sender attribution. Don't overpromise complete backfill.
5. Persist a **non-sensitive status record** (e.g., linked, connected, last connected, last receive, DB update, last sync attempt, error class), with atomic updates and no message excerpts or phone numbers. Define stale status behavior. Avoid conflating socket connected with freshness or complete sync.
6. Apply Windows per-user NTFS ACLs to `store/`, generated files, session secrets and logs; document device-level encryption using Windows BitLocker/device encryption when available. SQLite is otherwise plaintext at rest. `.gitignore` must exclude `store/`, `*.db`, WAL/SHM files, tokens, QR artefacts, media, logs, and backups. Never log message text, IDs, JIDs, phone numbers, media metadata beyond coarse aggregate counters, or WhatsApp session tokens.
7. Keep existing Go+SQLite compatible with Windows: install MSYS2 UCRT64 GCC using official instructions, make compiler available on PATH, build with `CGO_ENABLED=1` **for this process only** (avoid globally changing `go env` if unnecessary), and produce pinned `wa-bridge.exe` with reproducible build/run PowerShell scripts. Verify compiler and Go versions. `uv`/Python are WA02.
8. Support manual device logout/re-link, plus controlled local stop and safe cleanup with the ability to revoke the linked device in WhatsApp. Do not reset data without explicit opt-in or silently delete messages.

## Tests (must run without personal data)

- Go unit/integration tests with synthetic inbound event/history fixtures: direct chat, group, own/outgoing history, duplicate replay, non-ASCII text, multiline text, dates, large message, edits/deletes/reactions where supported; if unsupported, document precisely.
- Test schema migration and zero data loss under restart; test SQLite concurrent read with active writer and correct backup procedure.
- Test no listeners: `Get-NetTCPConnection` or equivalent confirms no bridge-created listener; source/test assertions that any `POST /api/send` concept is absent.
- Test no WhatsApp send is callable through CLI or IPC; static grep plus runtime negative tests.
- Test log sanitization under failures, pairing, reconnect, malformed events. Use dummy phone identifiers in fixtures only.
- Test headless task environment with closed stdin, offline network, reconnect and graceful stop.
- Verify Windows build from clean checkout using pinned Go modules and documented commands.

## Deliverables

`bin` build scripts (not committed binaries if policy forbids), sanitized configuration example, `docs/WINDOWS_BRIDGE_RUNBOOK.md`, `docs/STORAGE_AND_SECURITY.md`, `docs/SCHEMA.md`, tests, and a setup command that **does not link WhatsApp until the operator deliberately runs the foreground pairing step**.

## Acceptance gate

All synthetic tests pass; executable survives noninteractive startup; no bridge network listener; no sending tool/command/endpoint exists; logs contain no chat content/secrets; SQLite remains accessible to a separate read-only process. No personal data in repo/CI.

## Report back

Source revision and changed files, compile/test commands and outcomes, recorded unhandled message types and history limitations, security review results, and WA02 handoff. If any send path is still reachable, mark the phase **blocked**.