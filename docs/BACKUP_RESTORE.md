# Opt-in backup and disconnected restore

Backups are off until explicitly selected. The default local backup directory is
outside the checkout under the protected application data root, with only the
owner and SYSTEM access. They are plaintext SQLite snapshots, not encrypted
archives. No cloud/offsite destination is configured. If offsite storage is
chosen later, encrypt locally first and separately approve its destination/key
handling. Do not put live databases in a sync folder or network share.

```powershell
.\scripts\backup.ps1                 # Preview; no snapshot
.\scripts\backup.ps1 -IncludeMessages # Live SQLite backup API, includes WAL commits
.\scripts\stop.ps1
.\scripts\backup.ps1 -IncludeMessages -IncludeSession
```

Session snapshots require a stopped collector. The backup holds the existing
collector lock file while snapshotting the selected pair to prevent another Go
collector starting. Missing session DB or an active exclusive collector lock
refuses the operation. No session DB is read by MCP. Snapshot integrity, file
hashes and sizes are recorded in a private manifest. Five snapshot directories
are the cap; hitting it refuses a new backup without deleting old backups.
Failed snapshots remove only known newly created scratch files. Retention and
message expiry remain opt-in; no silent deletion is implemented.

Use the returned backup ID and a fresh inspection path:

```powershell
$inspection = Join-Path $env:LOCALAPPDATA 'WhatsappGptTunnel/restores/inspection-1'
.\scripts\restore.ps1 -BackupId 'BACKUP_ID_FROM_LOCAL_OUTPUT' -Destination $inspection
# Review hashes/files/path first:
.\scripts\restore.ps1 -BackupId 'BACKUP_ID_FROM_LOCAL_OUTPUT' -Destination $inspection -Apply -ConfirmRestore
```

Dry-run does not create the target. Apply creates a protected fresh directory,
verifies hashes and restores through SQLite's backup API. Restored status is
linked=false, connected=false, STOPPED; historical timestamps remain historical.
The .wa-restored-disconnected marker makes the Go bridge refuse run/pair/logout/
fixture before opening any credentials or networking. activate_store.ps1 also
refuses it. Never remove that quarantine to duplicate a linked-device session.
Inspect data offline; use a fresh deliberate phone pairing for recovery rather
than activating the same session on two machines. Inspection copies remain
sensitive and must be separately removed when no longer needed.

Synthetic tests cover a committed live WAL row, integrity/hash checks, tampered
manifest refusal, no-opt-in refusal, retention cap, active session-backup refusal,
two-file stopped backup, restore preview/no write, disconnected restore and Go
startup refusal. No real session restore or encrypted offsite restore is claimed.
