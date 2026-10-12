# WA00 — Source Audit, Feasibility & Consent Gates

**Use as a standalone Codex implementation prompt.**

## Mission

Start a **new, isolated, private** implementation repository for an always-on, Windows-hosted WhatsApp → ChatGPT *read-only* connector, based on `https://github.com/lharries/whatsapp-mcp`. Audit compatibility and security before any real WhatsApp account is linked. Prepare a reproducible, tested path for later plans WA01–WA04.

## Environment and input assumptions

- Host is an always-on **Windows** desktop with PowerShell. Do not modify PLANETS, Icarus, or other existing projects.
- The user's goal is to **ask ChatGPT to search existing and newly collected WhatsApp chats on demand**, without manual export; automatic sending or notification is not requested.
- Upstream code inspected on 2026-10-11: `lharries/whatsapp-mcp`, main at `7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88` (2025-07-13). Audit latest HEAD in the implementation environment and pin the reviewed commit; do not silently use HEAD if it changed.
- Upstream README Windows support requires CGO and MSYS2 UCRT GCC. Its `whatsapp-bridge/go.mod` declares Go 1.24.1; `whatsapp-mcp-server/pyproject.toml` declares Python >=3.11 (the README's older '3.6+' claim is stale). Python uses `uv`, MCP stdio, and a SQLite messages DB.

## Non-negotiable safety / legal gates

1. **Do not scan a QR code, connect a real WhatsApp account, ingest private messages, or send traffic as the user's linked device during WA00.** Tests use synthetic fixtures.
2. Document the WhatsApp risk explicitly: `whatsmeow` is an unofficial client; WhatsApp warns that linking unofficial apps may violate terms and may lead to account suspension/restrictions. 'Read only' does not eliminate account-risk. Provide manual go/no-go checkpoint for the user, without making the decision for them.
3. The original bridge binds `:8080` and publishes unauthenticated `/api/send` and `/api/download`; the MCP exposes `send_message`, `send_file`, `send_audio_message`, and `download_media`. Never expose this unchanged upstream service to a network or ChatGPT. WA01–WA02 will remove the ability to send, not hide it with prompts.
4. Preserve privacy: no tokens, QR payloads, real chat contents, personal identifiers, local DBs, media, or authentication files in git, CI uploads, issue descriptions, debug logs, demo data, or model-generated artifacts.
5. This does **not** use the official WhatsApp Business Platform, which is not an official method to read a user's personal WhatsApp history.

## Tasks

- Initialize/reuse a clearly dedicated **private** repository/worktree; document exact paths. If the workspace is ambiguous, stop before modifying unrelated repos.
- Vendor/fork upstream in a traceable way (git remote or separate source subtree), pin SHA, review license, `go.mod`, `go.sum`, `pyproject.toml`, `uv.lock`, and current WhatsApp compatibility. Create `UPSTREAM_PROVENANCE.md` recording commit and local patches.
- Inventory every inbound path, WhatsApp send-capable code path (including CLI commands), network listener, filesystem storage path, potential command execution, media handling, stdout logging of private text, auth session handling, and message deletion/retention behavior. Identify any technical sync limitations. Make a structured threat model: unauthorized network access, malicious local process, credential theft, prompt injection in messages, exfiltration via the model, account restriction, offline staleness.
- In ChatGPT and OpenAI Platform (manual portal check; do not require the agent to log in), confirm availability of **ChatGPT Plugins → Add custom MCP server**, **Tunnel** as connection option, and ability to create/use a Platform tunnel (`tunnel_id` and runtime key). Record a concise `SUPPORTED_SURFACE.md`, including whether invocation is supported in ChatGPT Work and whether ordinary chat is supported; don't guess plan entitlements. Note user action required if not confirmed.
- Identify security controls: private tunnel rather than public URL, narrow ChatGPT workspace/org association, read-only tools only, token storage strategy, Windows ACLs, optional BitLocker/device encryption, no inbound ports, and full shutdown procedure.
- Implement only local synthetic fixtures and an offline tooling verification script (show `go version`, `python --version`, `uv --version`, `gcc --version`, Git commit hash). No WhatsApp login.
- Define a clear interface contract to support WA01 and WA02: local SQLite schema; read-only query limits; eventual freshness status; payload attribution (chat JID, sender, message ID, timestamp). Explain that old history may be incomplete.

## Required deliverables

- `docs/WA00_GO_NO_GO.md`: risk summary, user consent gate, supported ChatGPT surface check, concrete blockers.
- `docs/ARCHITECTURE.md` and `docs/THREAT_MODEL.md`.
- `UPSTREAM_PROVENANCE.md` and pinned dependency inputs.
- Sanitized synthetic fixture generator; local environment verify script for PowerShell.
- A precise WA01 handoff and list of observed upstream write/network paths.

## Validation / acceptance

- No real WhatsApp account has been linked and no private data exists locally.
- A static search over source finds and documents all write tools, HTTP send/download endpoints, CLI sends, and sensitive logs; there is a remediation owner in WA01 or WA02 for each.
- A developer on Windows can reproduce tooling checks without needing credentials.
- Documentation clearly distinguishes local data at rest from WhatsApp/LLM data in transit.
- Documented fallback if ChatGPT custom MCP or Secure MCP Tunnel access is unavailable: **stop at local-only proof**, do not open an insecure public endpoint.
- The next implementation plan WA01 may start only after upstream pin/review and the operator accepts the stated WhatsApp account risk *before any future real linking*.

## Explicit non-goals

No pairing, message collection, cloud deployment, public URL, ChatGPT plugin registration, sending, media downloads, embeddings, or user-data testing.

## Report back

Give changed paths, exact source pin, risk/blocker matrix, results from synthetic checks, and whether WA01 is ready. Never claim account compatibility verified from code alone.