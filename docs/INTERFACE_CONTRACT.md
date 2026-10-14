# WA01 → WA02 interface contract (implemented v1)

This contract is implemented by the Go writer and Python MCP, and exercised by
synthetic integration tests. `fixtures/schema.sql` and `bridge/schema.sql` are
identical. See `MCP_TOOL_CONTRACT.md` for exact published input schemas.

## Store and migrations

- Production path: explicit absolute private local data directory; `messages.db`
  and separate `whatsapp.db` session DB. Only the bridge writes. MCP receives
  only the message-store path through trusted local config, never a tool argument.
- `PRAGMA user_version=1`. `chats(jid,name,last_message_time)` and `messages`
  retain upstream core names. Message primary key is `(id,chat_jid)`; both must
  be nonempty. Sender is a full exact JID if known, with `is_from_me` authoritative
  for own messages. Unknown sender/name stays unresolved, never guessed.
- Message timestamps, chat recency and status times are UTC fixed-width ISO8601
  `YYYY-MM-DDTHH:MM:SS.ffffffZ`. Normalize timezone offsets before storage and
  comparisons. Reject timezone-naive or unparseable input; preserve historical
  event times independently of ingest time.
- Media is a coarse type marker only. Legacy filename/url/key/hash/length columns
  are nullable and new data leaves them NULL. Never return them from MCP.
- The writer uses transactions for parent/message/status updates, conflict
  handling keyed by both ID and chat, and recency equal to maximum known event
  time. A replay must not overwrite a newer correction without a defined policy.
- WA01 backs up preexisting data with SQLite's backup API, normalizes old
  Go/SQLite date representations, preserve counts/attribution and reject unknown
  schemas. Fixture generation is not a migration tool and refuses existing paths.
- WAL and busy timeout are implemented and tested under Windows.
  Do not use `immutable=1` on a live DB. Reader URI uses `mode=ro`, bound SQL,
  no arbitrary SQL, ATTACH, extensions, schema changes or writable pragmas.

## Collector status

`collector_status` is a singleton row (`singleton=1`) updated atomically by the
writer. Boolean fields: `linked`, `connected`, `partial_history` (always 1),
`synthetic`. UTC times: `heartbeat_at`, `last_connected_at`, `last_receive_at`,
`last_db_update_at`, `last_sync_attempt_at`, `last_history_event_at`. Nullable
`error_class` is a fixed enum/class, never raw error text. No content or identity.

Writer target heartbeat: 30 seconds. Reader marks collector stale after 120
seconds without heartbeat, on invalid/future heartbeat, or when disconnected.
Not linked is distinct from stale. An old last-receive time with a current
heartbeat and connected state is a quiet collector, not necessarily stale.
Never interpret a history event or live socket as complete history. Synthetic
status is always labeled synthetic and is never used as pairing evidence.

## Implemented read APIs

| Tool | Inputs/intent |
|---|---|
| `health_status` | No identifiers; linked/connected/stale/partial, timestamps, coarse/bounded counts |
| `list_chats` | Optional name query; bounded metadata page, no unsolicited message excerpts |
| `list_messages` | Optional exact chat/sender, literal keyword, UTC date bounds, cursor, limit; newest first |
| `get_message_context` | Exact chat JID **and** message ID required; small neighboring window |
| `search_contacts` | Required literal query; matching stored direct-chat metadata only |
| `get_chat` | Exact chat metadata; no unsolicited body |

Every tool is read-only/non-destructive/idempotent and must describe message
content as untrusted. No send/file/audio/download tools, path browsing, raw SQL,
URL/network fetch, automation or notification API. The refined names preserve
the bounded read intents described in WA02.

Default page 20, max 50 messages/chats; context max 5 before + target + 5 after.
Excerpt max 1000 Unicode characters with explicit truncation marker. Strings,
cursors and output metadata must be length-limited too. Full serialized tool
response, including human-readable and structured forms, <=64 KiB UTF-8. Stop
the page before exceeding the byte cap, report a cursor for the last returned
row, and preserve all omitted rows for later retrieval. Health contains no PII.

Message entries: chat JID, chat name if resolved, message ID, sender identifier
and cautious display name, UTC timestamp, own-sender boolean, media type,
excerpt and `truncated`. These identify requested evidence; no unrelated contact
directory or session-store details. Human-readable citation examples must use
`chat + message ID + date`; names alone are not unique.

Stable descending order uses `(timestamp,chat_jid,id)` and a keyset cursor bound
to the normalized filters/tool/sort. Context in one chat uses `(timestamp,id)`.
Validate cursors rather than interpolating SQL; reject forged/oversize/foreign
filter cursors. New rows after an earlier cursor are visible on a new first-page
query; backfilled rows can appear on subsequent pages. This is eventual
consistency, not a pinned multi-call database snapshot.

## Result/error envelope

Return human-readable text plus structured `{ok, data, next_cursor, warnings,
freshness}`; structured errors have fixed `{code,message}` without raw tracebacks
or paths. Dates in filters are explicit-offset ISO8601, normalized UTC; validate
before<after relationships, sizes, numeric types (reject bool as int) and caps.

| Code | Meaning |
|---|---|
| `NOT_LINKED` | No active linked device; do not describe an empty DB as no messages |
| `DB_UNAVAILABLE` | Missing, denied, locked beyond timeout, corrupt or incompatible schema; no raw path |
| `STALE_SYNC` | Missing/expired heartbeat or disconnected collector; attach last verified timestamps; never claim latest |
| `NOT_FOUND` | Exact composite message/chat lookup has no match |
| `INVALID_FILTER` | Invalid type/limit/time/range/cursor or unsupported input |
| `PARTIAL_HISTORY` | Persistent coverage warning even on successful reads |

Historical reads may remain available with explicit `STALE_SYNC` warning; tools
asking for latest data must clearly report degraded freshness. Empty successful
results mean no matching **stored** records only. Missing status is unknown/stale,
not proof of connection. MCP stdout is JSON-RPC only; stderr logs fixed redacted
errors. WA02 protocol and query acceptance is recorded in `WA02_VALIDATION.md`.
