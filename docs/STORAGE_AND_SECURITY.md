# Storage and security

The bridge creates a dedicated canonical absolute directory, rejects links and
unexpected existing content, and applies a protected NTFS DACL to the directory
and existing files: current process user and SYSTEM full control. New files
inherit that boundary. Administrators and malware running as the same user
remain outside this protection guarantee. No secrets live in source or CI.

Windows locking uses an exclusive CreateFile handle to `collector.lock`, with
no sharing. Process exit/crash releases the handle; a leftover file does not
block restart. No stale-lock deletion race or TCP lock service. Headless runs
read no stdin. `stop.request` is an empty local file watched once per second;
the stop command refuses existing nonempty/nonregular files.

`messages.db` is SQLite WAL with foreign keys, busy timeout and FULL synchronous
writes. Chat/message/status updates are transactional. Python reads a different
read-only connection. `whatsapp.db` is the separate device/session store; never
give the MCP its credentials or permissions to browse it.

Version-0 migration snapshots the message DB using SQLite's backup API under
the protected `backups` directory before normalizing dates and adding status/
indexes. Unknown schemas, empty message keys or timestamps with no known zone
fail closed; the original transaction is rolled back. Legacy media columns
are preserved for data compatibility but never returned by the read API.
No data is silently deleted. Backup tests include committed WAL data.

SQLite is plaintext at rest. Consider Windows BitLocker/device encryption if
available; the application does not change disk/power/firewall/Defender settings.
Protect backups equally; do not copy a live WAL DB as a single file. General
operator backup/restore and explicit session-backup opt-in are implemented in
WA04; see BACKUP_RESTORE.md. Restored credentials are quarantined from Go startup.

All third-party client logs are discarded. App diagnostics contain fixed error
classes or a generic failure sentence only, with no raw errors, paths, content,
IDs, JIDs, names or tokens. QR blocks are an exception solely in the deliberate
foreground pairing terminal; never run it through log redirection or Task Scheduler.

Inbound bridge/MCP ports are absent. The client still performs necessary
outbound WhatsApp protocol traffic, authentication and acknowledgments. Those
protocol operations are distinct from a user-facing ability to send messages.
