# Pinned upstream application surface inventory

Source paths/lines below refer to `lharries/whatsapp-mcp` at
`7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88`, **not shipped product code**.
Raw object hashes and static scan line lists are in `audit/upstream-audit.json`.
The reference checkout is ignored and must never be launched.

## Inbound and outgoing paths

| Surface | Exact upstream evidence | Remediation owner |
|---|---|---|
| Unauthenticated all-interface HTTP listener | Go `startRESTServer`, main.go:679–786; `serverAddr=":8080"` via port argument; `ListenAndServe` at 783; invoked at 909 | WA01 remove whole REST server and net/http import |
| Text/file/voice sending endpoint | `/api/send` handler at 681; `sendWhatsAppMessage` at 206; dispatch at 365; arbitrary recipient/media path from JSON | WA01 remove endpoint, structs, dispatcher and media-send code |
| File read and media upload | `os.ReadFile(mediaPath)` at 237; `client.Upload` at 286; media metadata logged at 291 | WA01 remove these paths entirely |
| Download endpoint | `/api/download` at 727; `downloadMedia` at 557; `client.Download` at 644; local write at 650 | WA01 remove downloader, media-key persistence and filesystem exports |
| Dormant history send helper | `requestHistorySync` at 1151; `BuildHistorySyncRequest` at 1168; `SendMessage` at 1174 | WA01 remove unused helper; passive history events only initially |
| CLI sending | No input scanner/command parser or command dispatch in this pin; stale `Type 'help'` text at 906 | WA01 replace startup; regression tests reject sending arguments |
| Incoming WhatsApp data | event handler at 838; `events.Message` and `events.HistorySync` at 840/844; local parsers at 412/1009 | WA01 keep minimal passive ingestion, validate nil/malformed input |
| Outbound connection/pairing | main.go:803–904, sqlstore/client startup, `GetQRChannel`, `Connect`, QR at 873 | WA01 isolate manual terminal pairing; no unattended QR |
| Group name lookup | `GetChatName` at 926; `GetGroupInfo` at 976 | WA01 prefer event/contact cache; if retained document necessary outbound query |
| Contact lookup | `client.Store.Contacts.GetContact` at 991 reads device-store contacts | WA01 resolve cautiously within collector; do not give MCP session-store access |
| MCP transport | Python main.py:251 `mcp.run(transport='stdio')` | WA02 build separate minimal package, stdout protocol only |
| MCP write/media tools | main.py functions at 158,187,207,225; imports at 12–15 | WA02 remove all four registrations **and** implementation imports |
| Python bridge HTTP calls | whatsapp.py base URL at 11; requests.post at 637,671,711,744 | WA02 no requests/audio/bridge REST module reachable |
| Audio command execution | audio.py:52 `subprocess.run` list invokes ffmpeg; CLI at 94; no shell=True | WA02 do not ship/import module; no executable or path input |

Upstream `requestHistorySync` has no callers in this source. Its send is a
protocol history request, not a human text send; removing it makes the
application's no-SendMessage proof simpler. The third-party client still needs
outbound authentication, protocol exchanges and acknowledgments. Read-only
means no user-generated sends/edits through our runtime, not zero network writes
inside the WhatsApp protocol library. No claim of a whole-dependency call-graph
proof has been made.

## Filesystem, credentials and logs

| Path/behavior | Evidence | Remediation owner |
|---|---|---|
| Working-directory-relative history DB | `store/messages.db`, main.go:57–62 | WA01 absolute configured protected local directory |
| Working-directory-relative session DB | `store/whatsapp.db`, main.go:798–803 | WA01 separate ACL-protected secret store; never expose to MCP |
| Weak POSIX-mode directory creation on Windows | `MkdirAll(...,0755)` at 54,589,798 | WA01 explicit per-user NTFS ACL verification before data |
| Metadata/keys persisted with history | main.go:74–89 and 119–124; StoreMediaInfo at 488; URL/media-key/hash/filename columns | WA01 leave compatibility columns NULL in new records, never export legacy values |
| Download destination derived from JID/filename | main.go:564–603; `filepath.Abs` does not enforce containment | WA01 delete download feature; path construction would require a separate security review if ever added |
| Python media temp/output files | audio.py:30–37,79–91; non-ogg conversion imported by whatsapp.py:699 | WA02 eliminate audio code; WA04 cleanup only with explicit data-deletion scope |
| Session writes | `sqlstore` device persistence and contact cache used by whatsmeow | WA01 required protocol state only; never put session store in source/CI |
| Raw message and sender output | main.go:466–468,1076,1136–1141 | WA01 remove; coarse event/error classes only |
| Chat/contact/JID logging | main.go:932,941,985,988,1002,1024 | WA01 remove names/identifiers and sanitize nested library logs |
| HTTP request/result and media logs | main.go:613,654,706,710; paths, filenames, bodies | WA01 delete corresponding features |
| QR display | main.go:872–873 writes terminal blocks to stdout | WA01 manual foreground TTY only, never redirected/transcript/scheduled |
| Python stdout diagnostics | whatsapp.py:88,111,219,312,386,428,479,528,576,619,750–766 | WA02 fixed redacted errors on stderr; stdout JSON-RPC only |
| Raw library error output | Go logger calls and Python request/ffmpeg exception formatting | WA01/WA02 map to fixed error classes, never echo raw input/errors |

## Retention, correctness and sync limitations

- `INSERT OR REPLACE` is used for chats/messages (main.go:104,119). It is not a
  transaction spanning chat and message updates; chat replacements can regress
  recency when old history arrives. Use monotonic maximum recency and a single
  transaction with a conflict policy, not replacement of parent rows (WA01).
- Message key is `(id,chat_jid)`. History ingestion can derive an empty ID if the
  key is missing; repeated empty IDs can overwrite rows. Reject malformed keys
  explicitly, preserve attribution and classify unsupported events (WA01).
- Live sender uses `.User`; history attribution varies for groups, self and
  missing participants. Normalize to resolvable sender identifiers without
  inventing names; keep `is_from_me` (WA01/WA02).
- Text extraction is conversation/extended text only; media metadata handles
  image/video/audio/document. Reactions, edits, deletion/control events and
  ephemeral/view-once wrappers have no dedicated lifecycle implementation.
  There is no automatic retention/deletion of message rows. Old stored content
  can outlive a message deleted/disappeared in WhatsApp. Document or implement
  explicit handling later; never imply this is an exact mirror (WA01/WA04).
- HistorySync receives whatever WhatsApp supplies; no complete backfill proof.
  Zero/missing timestamps are skipped. The unused helper requests a bounded
  history batch, not all years of history. Prolonged offline capture is unknown.
- Python `sqlite3.connect(path)` opens read/write and may create an empty DB.
  WA02 must instead fail on missing DB and use a validated `mode=ro` URI.
- Python query `limit` and context sizes have no robust caps. Ordering only by
  timestamp and offset pagination can drop/duplicate ties or concurrent data.
  `get_message_context` initially looks up ID without chat JID (whatsapp.py:241),
  allowing the wrong chat for repeated IDs; contact fallback uses substring JID
  matching. WA02 uses composite IDs, stable keysets and exact mappings.
- Most SQL data predicates are parameterized; that alone does not establish
  boundedness, date correctness, privacy, or safe sorting. No arbitrary SQL or
  generic filesystem interface should be introduced (WA02).
- `LoggedOut` only logs a warning; connection state is not persisted. Main
  attempts initial connection and can exit on failure; it has no application
  backoff/supervision/status contract. After connecting it waits for a signal,
  not stdin, so the plan's assumed active interactive CLI was not found (WA01).
- Upstream README suggests deleting both databases on sync trouble. Do not
  follow this destructive recovery advice; WA04 needs backup/relink commands
  that preserve history and require separate deletion opt-in.

The static scan is a reproducible inventory aid, not a security certification.
Transitive dependency internals, real protocol behavior, unknown vulnerabilities,
and actual user/workspace permissions remain separate verification work.
