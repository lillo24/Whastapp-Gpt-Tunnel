# Store schema v1

`bridge/schema.sql` is embedded by the Go executable; `fixtures/schema.sql` is
the matching offline fixture definition. `PRAGMA user_version=1` identifies the
contract. See `INTERFACE_CONTRACT.md` for fields, UTC format, limits and semantics.

| Table | Key | Purpose |
|---|---|---|
| chats | jid | Optional display name, monotonic last-message UTC time |
| messages | (id, chat_jid) | Sender, body, UTC date, own flag, coarse media type |
| collector_status | singleton=1 | Safe linked/connected/heartbeat/ingest/history state |

Ordering indexes are `(timestamp,chat_jid,id)` and `(chat_jid,timestamp,id)`.
Message and chat timestamps use fixed-width UTC microseconds. Legacy media
columns are retained nullable for compatible migration, always omitted from
query output. `partial_history=1` is mandatory; there is no complete-sync flag.

Status contains only state booleans, UTC timestamps and fixed error classes.
`synthetic=1` labels test stores; it never implies an actual linked account.
Migrations take a backup first and normalize known explicit-zone representations;
naive dates and unknown schema versions require operator investigation.
