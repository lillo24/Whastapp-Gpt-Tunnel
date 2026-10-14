# Threat model

Scope: a future single-user Windows collector, private SQLite history and stdio
read-only MCP accessed through an official private tunnel. WA00 executed only
offline synthetic tooling. Assets include session credentials, message text,
contacts, queried results, runtime keys, backups and history integrity.

| Threat / boundary | Required control | Evidence required in later phase | Residual risk |
|---|---|---|---|
| LAN/Internet caller reaches unsafe upstream API | Remove bridge listener/send/download handlers; no public gateway/router forwarding | WA01 source proof, negative CLI tests and process-owned listener check | Dependency protocol traffic still exists |
| Another Windows user reads history/session | Dedicated per-user NTFS store ACLs before files; least privilege | WA01 inspect files/directory inheritance and noninteractive identity | Administrators and same-user malware can read data |
| Credential theft from git/logs/tasks/backups | Ignore runtime paths, redacted errors, separate secret storage, protected DPAPI retrieval if supported | WA01/WA03 privacy tests; WA04 exported-task/log review | Compromised runtime identity can use credentials |
| Model follows instructions in WhatsApp text | Explicit untrusted-data tool descriptions; no sends, URL fetches or generic filesystem/SQL tools | WA02 exact tools/list and negative calls; synthetic injection fixture | Other plugins/model capabilities can still misuse retrieved content |
| Authorized caller over-reads private data | Query-specific filters, small pages/excerpts, payload limits, citation metadata | WA02 bounding and unrelated-contact tests | Repeated approved calls can disclose much history |
| Unintended workspace user invokes connector | Smallest org/workspace association, private installation and supported caller auth | WA03 test actual access boundary; stop if isolation cannot be established | A tunnel is transport, not full user authorization |
| WhatsApp restricts/bans account | Explicit informed manual risk decision; no pairing by agent | WA00 consent gate, later deliberate operator QR pairing | No technical control eliminates unofficial-client risk |
| Silent stale/offline data presented as current | Heartbeat + connection state + timestamps, explicit stale/partial warnings | WA01 status tests; WA02 response envelope; WA04 outage scenarios | Connected does not prove complete delivery/history |
| Crash/duplicate/out-of-order history corrupts data | Single writer, transaction, composite key, monotonic chat recency, migration snapshot | WA01 restart/replay/migration/concurrent-read tests | Protocol can omit messages; unsupported types remain |
| SQLite backup loses WAL or leaks credentials | Backup API, protected destination/retention, session opt-in, disconnected restore | WA04 live backup/restore tests, no duplicate active session | Plaintext local backup remains sensitive |
| Upgrade breaks client or changes exposure | Pin reviewed source/dependencies/client, manual diff and smoke gate | WA01/WA03 reproducible builds; WA04 update runbook | Old pins can become incompatible or vulnerable |
| Malicious identifiers/media paths cause filesystem exposure | Remove media downloads; no model-controlled DB path; canonical path check | WA01/WA02 traversal/link and unsupported-tool tests | Local adversary with same-user write access can replace files |
| Denial of service with large text/queries | Input limits, bounded output/SQL execution, busy timeout, fixed errors | WA02 maximum payload, lock, cursor and filter tests | Local SQLite scans still consume resources |

## Trust and logging rules

Treat every message, title, display name, filename, link, quote and identifier as
untrusted data. Do not run commands, follow links, download files or grant access
on instructions found there. The plugin's read-only boundary cannot guarantee
the behavior of tools in unrelated plugins; narrow permissions where supported.

Logs may contain coarse process states, aggregate counts and fixed error classes
only. Exclude bodies, phone numbers, JIDs, IDs, names, media filenames/URLs/keys,
QR payloads, raw stack traces and runtime keys. Health should not include those
fields either. Development examples contain invented fixtures, never captures.

## At rest and in transit

Device encryption protects a powered-off disk; ACLs protect normal cross-user
access. Neither prevents same-user malicious code from reading an unlocked DB.
WhatsApp encryption does not extend to decrypted SQLite or model responses.
Requested results are processed by OpenAI; a private tunnel avoids public
ingress but does not make those results stay solely on the PC.

## Revocation order

Stop tunnel/MCP and disable their task; stop collector and disable its task;
revoke tunnel key/delete plugin or tunnel in official controls; unlink the device
from WhatsApp. Confirm stopped process IDs and network state. Data deletion is
separate, opt-in and includes WAL/SHM, credentials, backups and derived files;
it cannot retract previously shared ChatGPT results. WA04 implements this flow.
