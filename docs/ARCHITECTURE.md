# Architecture and data boundaries

WA01 collector and WA02 local stdio MCP are implemented and synthetically
accepted. WA03 actual ChatGPT Work synthetic acceptance passed. WA04 operations
scripts/recovery tests are implemented; real-device pairing and administrator
boot registration/reboot acceptance remain. No WhatsApp account is linked.
See `ACCEPTANCE_REPORT.md` for observed results and remaining steps.

```text
WhatsApp servers <-> outbound linked-device protocol <-> Go collector (WA01)
                                                        |
                                               private local SQLite
                                               messages + status
                                                        |
                                              Python MCP (WA02)
                                              read-only / stdio
                                                        |
                                              official tunnel-client (WA03)
                                              outbound HTTPS only
                                                        |
                                              selected OpenAI workspace
                                              private read-only plugin
```

## Runtime responsibilities

- WA01: receive incoming/history events, preserve attribution and UTC timestamps,
  transactional storage, safe heartbeat, reconnect and explicit relink-required
  state. No HTTP server, messaging command, send dispatcher or media download.
  A manual foreground pairing command is distinct from headless collection.
- WA02: open only the configured message DB with `mode=ro`; expose bounded
  approved read APIs. No access to session credentials, generic SQL/filesystem
  APIs, media bytes/paths, network fetches, or upstream send/audio modules.
- WA03: an exact reviewed official tunnel runtime supervises the stdio MCP.
  Secrets are locally protected; workspace associations and app authorization
  must limit who can invoke the tools. No public ingress or port forwarding.
- WA04: least-privileged scheduled processes, status, backup API, controlled
  recovery and separate opt-in deletion. No unattended QR display and no GPT
  monitoring/notifications or automatic summarization.
  A fixed private runtime health file records bounded execution timestamps and
  error classes only; tool arguments/results and message content are not logged.

## Storage and privacy

Future production data belongs under an explicit absolute local private directory,
preferably `%LOCALAPPDATA%\WhatsappGptTunnel\store`, separate from this checkout.
The bridge is the single writer. `messages.db` contains history and the safe
status table. `whatsapp.db` contains device credentials and contacts; Python must
not read it. Protect both directory ACLs and newly created files before pairing.
Keep SQLite off network shares and cloud-synced folders. Device encryption is
optional operator configuration, not an automatic OS-wide change.

The source checkout currently inherits access for the operator, SYSTEM,
Administrators and a local Codex sandbox group. It is suitable for synthetic
source work, **not an approved production-secret ACL**. WA01 creates and tests
a separate protected runtime store with only current-user/SYSTEM access.
`.gitignore` is a repository guard,
not an access-control mechanism or secret scanner.

WhatsApp protocol traffic and OpenAI query traffic have different boundaries:
the linked-device client participates in WhatsApp's protocol; the collector
decrypts received data into local plaintext SQLite; user-selected tool responses
travel through the OpenAI tunnel for model processing. The database is not
uploaded wholesale by design, but repeated queries can expose many messages.

## Stable interface

`INTERFACE_CONTRACT.md` and `fixtures/schema.sql` define the implemented version-1
store and output limits. Preserve upstream core column names, composite message
identity, and older timestamps during migration. Legacy media-secret columns
remain nullable and must not be populated by the new collector. Migration of an
existing DB is implemented with a SQLite backup API snapshot, date normalization
and transactional rollback on failure, tested using synthetic legacy data.

History coverage is always partial/unknown. A live socket does not prove receipt
of every message. A recent heartbeat with a connected state can distinguish
quiet chats from a dead process; last message time alone cannot. No promise of
complete past history, disappearance handling, or gap-free offline recovery.

## Shutdown and revocation

Stop tunnel/MCP first to remove model access; stop bridge gracefully to end
collection. Disable scheduled tasks if present. Revoke runtime credentials or
delete the tunnel/plugin in the official interfaces. Unlink the companion from
WhatsApp Linked devices. Preserve the history unless separately authorized to
delete it; unlinking and deleting data are different actions. Prior results
shared with ChatGPT are not undone by local deletion.
