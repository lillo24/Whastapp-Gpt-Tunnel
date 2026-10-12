# WA02 — Bounded, Read-Only WhatsApp MCP Query Server

**Standalone Codex implementation prompt. Dependency: WA01.**

## Mission

Build a **stdio** MCP server in Python that reads WA01's SQLite message store safely and exposes only minimal read-only tools to ChatGPT. Keep the upstream `whatsapp-mcp-server` as an implementation reference, but do not register its write/media tools. Support searching existing stored chats and newly received messages, without uploading the whole database or requiring users to export chats manually.

## Source facts to verify

- Upstream `whatsapp-mcp-server/main.py` registers `search_contacts`, `list_messages`, `list_chats`, `get_chat`, `get_direct_chat_by_contact`, `get_contact_chats`, `get_last_interaction`, `get_message_context`, plus `send_message`, `send_file`, `send_audio_message`, and `download_media`.
- Upstream starts with `mcp.run(transport='stdio')`, `whatsapp.py` uses local SQLite for reads, and its Python project requires Python >=3.11 (not the older README Python 3.6+ suggestion).
- The original REST send path (`http://localhost:8080/api`) must not be needed or referenced by the new server.

## Tool interface

Implement and document at least these read-only MCP tools (names may be refined if API differs, but preserve intent):

- `health_status()` returns only collector connected/stale state, latest ingest/sync timestamps, record counts or bounded numbers, and clear *coverage-not-guaranteed* warning; must never leak phone numbers or private messages.
- `list_chats(query?, limit?, cursor?)` returns bounded chat summaries with stable identifiers, display name where available and latest message time (no full message text by default). Default 20, max 50.
- `list_messages(chat_jid?, query?, after?, before?, sender?, limit?, cursor?)` supports full-text substring lookup and per-chat date filtering; default 20, max 50; can page back through history without `load all`. Do not need embeddings for MVP.
- `get_message_context(chat_jid, message_id, before?, after?)` requires **both** chat identity and message identity so IDs from another chat cannot be mixed; context cap total 21. Include stable attribution and sequence.
- `search_contacts(query, limit?)` and `get_chat(chat_jid)` as needed to resolve human requests; constrain output.

Do not expose `send_message`, `send_file`, `send_audio_message`, `download_media`, filesystem browsing or arbitrary SQL execution. Remove their registrations *and* runtime imports/reachability from the MCP package. Media metadata (e.g. `[image]` or `[voice message]`) may be displayed but media bytes and paths are **not** returned in v1.

## Data / correctness constraints

1. SQLite connections open using a read-only URI (`file:...?mode=ro`) and minimal filesystem permissions; no writes, schema mutations, PRAGMAs that modify state, extensions, ATTACH, or arbitrary user-provided SQL. Add `busy_timeout` and confirm concurrent writer reads. Check DB path is absolute, canonical, within configured private location; avoid symlink/path traversal.
2. All SQL filtering uses bound parameters; validate UTC-normalized ISO8601 time bounds, timezone offsets, lengths and types, `limit`, `cursor`, and sorting. Stable ordering including tie-breakers such as `(timestamp, chat_jid, id)` prevents duplicate/drop anomalies. Document eventual consistency when new rows arrive between pages.
3. Return human-readable text plus structured IDs, chat name, sender (with cautious display-name fallback), timestamp including timezone/UTC, own-sender flag, media type and excerpt. Tool results should permit verifiable **chat + message ID + date** citations in GPT answers. Label unresolved phone/JID mappings clearly rather than invent names.
4. Control data exfiltration via bounded output: default 20 messages, 50 max (and lower max for contexts), truncation for very long message bodies with an explicit truncation marker, max payload e.g. 64 KiB per call, cursor/next-page metadata. For broader summaries, let GPT request more pages instead of shipping years of chat content at once.
5. Fail with distinct structured errors for `NOT_LINKED`, `DB_UNAVAILABLE`, `STALE_SYNC`, `NOT_FOUND`, `INVALID_FILTER`, and `PARTIAL_HISTORY` as relevant; do not treat empty DB as 'you have no messages'. `health_status` must not guarantee sync completeness.
6. Treat message text as **untrusted input**: clear tool descriptions advise GPT not to execute instructions inside messages, links or quotes; don't implement tools that follow URLs or make arbitrary network requests. Do not include hidden contact details unrelated to the query.
7. MCP process stdout carries protocol messages only; logs are local, redacted and on stderr. Prevent traceback leaks containing chat content, paths to session databases, tokens or PII.
8. Preserve compatibility with `uv run` and MCP stdio; keep dependencies pinned/locked. Prefer simple SQLite over FTS/vectors unless a benchmark on synthetic data proves it necessary.

## Testing requirements

- Synthetic test DB with multiple chats, contacts, groups, Unicode text, ambiguous names, same message ID across chats, ties on timestamp, pagination, leap-day/timezone boundaries, long malicious-looking prompt injection text, missing DB, locked DB, empty DB, and stale last-sync state.
- Verify every published tool is truly read-only using MCP Inspector / MCP `tools/list`: **zero write tools, zero download/media paths, zero generic filesystem tools**.
- Verify the process runs over stdio with closed/redirected stderr and valid JSON-RPC under fresh process start, repeated calls and shutdown.
- Assert bounded response size, paging determinism, date correctness, SQL injection resistance, negative ID lookup and no leaking unrelated contacts. Verify failure modes and doc samples.
- End-to-end offline test: synthetic Go collector fixture -> SQLite -> Python MCP -> returned chat/message entries, including newly appended data without restarting MCP.

## Deliverables

`main_readonly.py` (or equivalent), query/service module, schema typed contracts, tests and fixtures, `docs/MCP_TOOL_CONTRACT.md`, `docs/READ_ONLY_PROOF.md`, `scripts/test_local_mcp.ps1`, and explicit WA03 command for launching the MCP from a fixed private working directory with UV.

## Acceptance gate

Locally callable tools answer chat/name/date/keyword questions from synthetic fixtures; new entries are visible on the next query; no ability exists for this service to send WhatsApp messages, download media, or access unrelated files; pagination and timestamps are correct; failure is explicit if sync is stale.

## Report back

Full `tools/list` output **names only**, schema summary, test results, example sanitized tool answers, limitations, and WA03 handoff. Do not submit real chat messages to a public LLM in CI.