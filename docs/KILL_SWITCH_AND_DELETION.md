# Stop, revoke and delete are separate operations

```powershell
.\scripts\stop.ps1
.\scripts\uninstall.ps1
.\scripts\uninstall.ps1 -Apply -ConfirmUninstall
```

Stop ends collection/tunnel activity without deleting history. Uninstall removes
only owned startup jobs and retains data and credentials. For a remote access
kill switch, disconnect WhatsApp ReadOnly in ChatGPT, revoke its restricted key
or the tunnel in Platform as appropriate, and unlink the companion on the
phone's Linked devices screen. Those actions are distinct. App disconnect was
tested: tools disappeared even with a running tunnel. Same-scope reconnect
restored synthetic access. Real phone/API-key/tunnel revocation remains untested.

Local deletion is a separate dry-run-first command. Select only categories the
operator intends to remove:

```powershell
.\scripts\delete_data.ps1 -MessagesAndSession -Backups -RuntimeCredentials -OperationLogs
# Stop/unregister jobs, review the exact absolute targets, then explicitly apply:
.\scripts\delete_data.ps1 -MessagesAndSession -Backups -RuntimeCredentials -OperationLogs -Apply -ConfirmDelete
```

MessagesAndSession removes the configured store including SQLite WAL/SHM/journal,
session DB, collector lock/status and migration snapshots. Backups removes the
configured snapshot root. RuntimeCredentials removes the encrypted key, tunnel
configuration and derived health/state. OperationLogs removes supervisor logs,
locks, task previews and local operation configuration. Choosing a subset leaves
the other categories; if configuration is deleted first, save the remaining
local paths so they can still be handled deliberately.

Apply requires startup jobs absent and collector/tunnel/supervisor locks idle.
Every final absolute target must be a marked child of the dedicated application
root or this checkout's .local-fixtures. Volume roots, network shares, redirected
contents and unexpected files/directories refuse deletion. The implementation
uses literal native PowerShell removal after validating boundaries. Tests apply
deletion only to newly created synthetic directories; separate restored
inspection copies are retained. Other old fixtures, inspection copies, offsite
archives, Windows backups and ChatGPT conversation results are separate copies
and require their own review/deletion.

Deleting local data does not erase prior query results already shared with
ChatGPT or revoke remote credentials/linked devices. It is ordinary file
deletion, not guaranteed secure erasure on SSDs/backups. Keep disk encryption
and the account's own data controls in mind when choosing retention.
