# WhatsApp → ChatGPT (Windows) | Implementation plan index

Plan index prepared: 2026-10-11. Updated implementation status: 2026-10-13.

## Current implementation status

WA00–WA02 are implemented and tested locally: audited source, Windows Go
collector and bounded read-only stdio MCP. The private ChatGPT Work connector
passed synthetic end-to-end tests. **WhatsApp is not paired; unattended production
startup and real-message acceptance remain incomplete.**

| Plan | Status |
|---|---|
| WA00 | Complete locally; source/dependency audit and 13 tests pass; continuation recorded in operator decisions |
| WA01 | Synthetic acceptance passed: 12 Go tests, clean Windows CGO build and process/storage checks |
| WA02 | Synthetic acceptance passed: bounded six-tool MCP, actual stdio integration; WA02 milestone suite 35 passed, 1 skipped |
| WA03 | Synthetic functional gate passed in ChatGPT Work: six reads, fresh append, adversarial data, offline timeout, disconnect and reconnect |
| WA04 | Operator scripts and recovery tests implemented; temporary logged-in Scheduler tests passed; boot registration requires Windows administrator; phone/reboot/logoff acceptance pending |

Start with [current acceptance and remaining steps](docs/ACCEPTANCE_REPORT.md),
[always-on runbook](docs/ALWAYS_ON_RUNBOOK.md),
[WA03 gate and launch](docs/WA03_HANDOFF.md),
[collector validation](docs/WA01_VALIDATION.md),
[MCP validation](docs/WA02_VALIDATION.md),
[tool contract](docs/MCP_TOOL_CONTRACT.md),
[read-only proof](docs/READ_ONLY_PROOF.md) and
[upstream provenance](UPSTREAM_PROVENANCE.md).
This public repository contains the implementation and redacted acceptance
evidence. Runtime databases, credentials, session files, logs, screenshots,
the audit checkout and generated fixtures stay local and are excluded. No WhatsApp
account has been linked. One scoped tunnel and encrypted runtime key exist. A
custom plugin is connected for synthetic data only. No production startup task
is installed. Temporary synthetic test tasks were removed after verification.
See [WA03 validation](docs/WA03_VALIDATION.md).

To build and verify locally (tested with Python 3.12.14):

```powershell
.\scripts\fetch_audit_source.ps1
.\scripts\setup_toolchain.ps1
.\scripts\build_bridge.ps1 -Test
.\scripts\test_clean_bridge_build.ps1
.\scripts\test_local_mcp.ps1 -PythonExe 'C:\absolute\path\python.exe'
& 'C:\absolute\path\python.exe' .\scripts\test_bridge_runtime.py
```

Initial source/tool/module/locked-package setup needs the network; acceptance
uses synthetic local data and never pairs an account. Toolchain archives and
compiler packages are hash-pinned in `audit/`; installations/caches/binaries
stay ignored and local. See [Windows runbook](docs/WINDOWS_BRIDGE_RUNBOOK.md)
and [storage security](docs/STORAGE_AND_SECURITY.md). Real pairing requires the
separate foreground command. Original plans below and in
`history-implementations/` remain preserved.

## Objective

Keep a personal Windows desktop running a **private, read-only** WhatsApp history collector and MCP interface. When explicitly asked from supported ChatGPT interfaces, GPT can query synchronized chats and recent messages. Data stays in a local SQLite store until individual query results are transmitted to ChatGPT. No automatic outgoing WhatsApp messages. No public network ports.

## Architecture (synthetic path verified; real device pending)

```
WhatsApp linked device (unofficial whatsmeow client)
    │ incoming WhatsApp events / partial historical sync
    ▼
Local Go bridge (no send API, no network listener)
    │ SQLite messages.db + local session store (ACL-protected)
    ▼
Local Python read-only MCP server (stdio, bounded queries)
    │
    ▼
OpenAI tunnel-client (outbound TLS to OpenAI; no public ingress)
    │
    ▼
Private custom MCP plugin in supported ChatGPT Work surface
```

## Crucial limitations / gates

1. **WhatsApp Terms/account risk:** The upstream project uses `whatsmeow`, an *unofficial linked-device client*, rather than the official WhatsApp Business Platform. WhatsApp's help guidance warns that linking unofficial apps can violate its terms and may lead to restrictions or an account ban. Read-only access and small traffic volumes **do not eliminate this risk**. Do not link a personal account without conscious acceptance of this risk. The official WhatsApp Business Platform is not a substitute for reading arbitrary history from a personal account.
2. **Product access:** Availability of **Add custom MCP server**, OpenAI Platform tunnel creation/use permissions, and ChatGPT Work invocation must be confirmed in *the actual user's accounts* before assuming end-to-end compatibility. Access cannot be inferred from a plan name. If unavailable, stop at the local-only milestone; never substitute an unauthenticated public endpoint.
3. **Historical coverage:** Linked-device history sync may supply only a subset of historical messages. The design captures future messages while the bridge remains connected but cannot guarantee all pre-existing history, missing/disappearing messages, or reliable capture during prolonged disconnects.
4. **Privacy:** Message data, names, and potentially third-party personal information are stored unencrypted by the upstream SQLite code unless disk encryption is used. Responses to ChatGPT questions include the retrieved private content and are processed by OpenAI. Treat both the local store and model-facing outputs as sensitive.
5. **Maintenance:** The upstream `lharries/whatsapp-mcp` default branch was re-verified at commit `7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88` (2025-07-13) on 2026-10-12. Code, modules and tools are pinned; real protocol compatibility is unverified. Do not auto-update an unofficial client.
6. **Costs:** Running the app locally avoids a hosting server, but OpenAI Platform access, tunnel use, API usage, or other account requirements may impose restrictions or costs. Validate these; no zero-cost guarantee.

## Sequence (finish gate before the next plan)

| ID | File | Deliverable | Gate |
|---|---|---|---|
| WA00 | `WA00_source_audit_and_access_gate.md` | Provenance, risks, capability gate, sterile test environment | No personal account paired |
| WA01 | `WA01_windows_local_bridge_and_storage.md` | Locally runnable safe Go bridge, SQLite data, no sending endpoints | Synthetic-only tests pass |
| WA02 | `WA02_read_only_mcp_query_layer.md` | Bounded read-only stdio MCP tools with fixture tests | Zero writing tools or media exfiltration |
| WA03 | `WA03_secure_tunnel_and_chatgpt_plugin.md` | Private OpenAI tunnel and ChatGPT custom plugin | Real end-to-end read test only after risk consent |
| WA04 | `WA04_always_on_operations_and_acceptance.md` | Windows startup/restart/backup/health runbook and privacy QA | Final sign-off |

### Suggested execution model

Feed **one complete `.md` plan at a time** to Codex (or another coding agent) in a dedicated new private repository/worktree for this project. Insist on a finished implementation plus tests for that phase before proceeding; use the next file only after its explicit dependencies pass. Store **exact text** of executed plans in the project's `history-implementations/` folder. Nothing in these documents authorizes access to the user's account, QR scanning, publishing the database, or sending WhatsApp messages.

## Source of truth at plan time

- Original repo: https://github.com/lharries/whatsapp-mcp
- Official OpenAI Secure MCP Tunnel: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- OpenAI custom MCP plugin setup: https://developers.openai.com/plugins/deploy/connect-chatgpt
- OpenAI authentication guidance: https://developers.openai.com/plugins/build/auth
- WhatsApp Terms: https://www.whatsapp.com/legal/terms-of-service
- WhatsApp guidance on unofficial apps: https://faq.whatsapp.com/1217634902127718/

## Explicitly deferred

- Sending messages, making calls, editing chat state or manipulating contacts.
- Auto-monitoring and push notifications: the user requested **on-demand reading**, not unsolicited alerts.
- Media downloads, OCR, speech transcription, and semantic embeddings/vector databases.
- Hosting a public MCP endpoint or distributing a public plugin.
- Guaranteeing complete historical WhatsApp access or guaranteeing account safety.
