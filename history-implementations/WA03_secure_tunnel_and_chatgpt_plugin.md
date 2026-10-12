# WA03 — Private Secure MCP Tunnel & ChatGPT Plugin Connection

**Standalone Codex implementation prompt. Dependencies: WA00–WA02.**

## Mission

Connect the WA02 **read-only local stdio MCP server** on the user's always-on Windows PC to ChatGPT through the **official OpenAI Secure MCP Tunnel**. Avoid port-forwarding, public endpoints, cloud-hosted message databases, `ngrok` sharing links, or unauthenticated HTTP gateways. Keep all credentials local and allow GPT to call only approved read tools in supported ChatGPT product surfaces.

## Verified design references (recheck live docs)

- OpenAI secure tunnel docs: `https://developers.openai.com/api/docs/guides/secure-mcp-tunnels`.
- Official Windows-capable client: `https://github.com/openai/tunnel-client/releases/latest`.
- Connecting custom MCP plugin: `https://developers.openai.com/plugins/deploy/connect-chatgpt`.
- MCP auth/authorization: `https://developers.openai.com/plugins/build/auth`.
- OpenAI documents `tunnel-client` outbound HTTPS to its control plane, local stdio/HTTP MCP support, `tunnel_id`, runtime API key, `doctor --explain`, and **ChatGPT Plugins → Add custom MCP server → Tunnel**. Product permissions and availability vary by account/workspace.

## Preflight gate (must pass before handling real data)

1. Confirm the user's own ChatGPT account/workspace shows **Add custom MCP server** and supports **Tunnel** mode and invoking the resulting plugin, at minimum in ChatGPT Work. Do not assume ordinary-chat availability. If access absent, STOP with a concise blocker report; do not expose private WhatsApp traffic to a public unauthenticated endpoint as a workaround.
2. Confirm an OpenAI Platform organization with permission to create/use a tunnel and appropriate association to the personal ChatGPT workspace. Require the user to create/review `tunnel_id` and runtime API credentials through the official UI. Avoid placing secrets in prompts or chat transcripts.
3. Confirm WA01/WA02 read-only assertions: no network bridge API listener, zero write/media tools, valid synthetic integration tests. Check whether WA00 documented explicit acceptance of unofficial WhatsApp linked-client risk; if not, keep synthetic data only.
4. Re-check if the selected custom MCP connection/auth mode is appropriately scoped to this single user. Apply supported authentication and least-privilege workspace/tunnel restrictions. Do not assume the tunnel is a user-authorization system; it is primarily private transport. If more than the intended user/workspace can invoke it, implement a supported auth strategy or STOP rather than allowing sensitive-message access.

## Tasks

- Download official `tunnel-client` Windows binary from official release/settings. Pin an exact reviewed version and verify checksum/signature when provided; verify `--version` and `help quickstart` locally. Avoid copy/pasted third-party installation scripts.
- Configure a private **stdio** tunnel profile to launch the WA02 read-only MCP using UV with **absolute paths**. Derive exact PowerShell syntax from `tunnel-client --help` for the pinned binary; the documentation's Unix `export`/quoting examples are illustrative, not Windows commands. Do not invent flags. Keep runtime API key out of command history, process arguments, Task Scheduler exported XML, shell transcripts, source, and logs; use supported secret storage/user-scoped environment/injection method (e.g. protected DPAPI-backed retrieval if needed).
- Associate tunnel with the smallest correct **personal** Platform org and target ChatGPT workspace; disallow unnecessary associations or plugin sharing. No publicly routed `localhost:8080` API.
- Run `tunnel-client doctor --profile <chosen-profile> --explain` and validate local UI `/ui` status / logs for tunnel readiness. Explicitly distinguish transport healthy from WhatsApp sync healthy; if bridge is down, tooling should report stale or unavailable, not old data as fresh.
- Create a **private custom MCP plugin** from ChatGPT Plugins. Connection: **Tunnel**, select existing ID. Configure auth based on actual supported flow and security policy, inspect all exposed tool descriptions and read-only annotations; install only to personal context. Invoke from ChatGPT Work or another **verified** supported interface. Do not publish plugin to Directory.
- Provide example prompts for user to ask ChatGPT: search last 7 days in named chat; find next meeting mentioned by specified person; show newest messages since a given timestamp; summarize conversation with evidence and coverage caveat. Treat content as untrusted data.
- Ensure service does not accept unknown third-party MCP callers or expose the database beyond selected workspace/org. If product allows plugin permissions, choose read-only and restrict permissions to least privilege.
- Run end-to-end **synthetic** smoke before real pairing: test `/tools/list`, local search, ChatGPT tool invocation, handling of unavailable bridge, and no write tool present. Once accepted and manually approved, test a small selected real conversation only. Do not post message contents in CI/evidence/issue logs; redact screenshots.

## Tests / failure cases

- Offline tunnel / bad runtime key / revoked tunnel access / wrong workspace association / sleeping Windows PC / stale DB / expired WhatsApp linked device / removed plugin.
- Unauthorized connection attempt cannot enumerate chats. Inspect the actual access boundary, not merely whether `/mcp` has an HTTPS URL.
- Zero externally accessible listening ports from this stack on local machine/router. `tunnel-client` outbound only.
- `tools/list` contains only WA02 approved bounded read APIs and annotations.
- User can request newly inserted synthetic message without restarting ChatGPT/tunnel service, assuming bridge has ingested it.
- Audit log never writes private content or tokens.

## Deliverables

`docs/CHATGPT_PLUGIN_SETUP.md` (Windows screenshots/field guide or textual steps), `docs/TUNNEL_SECURITY.md` (trust boundary and auth), redacted connection profile example, versioned runtime install/run PowerShell scripts, `scripts/check_tunnel.ps1` and tested example prompts. NO keys, QR codes, JIDs, chats, dbs, or identifying logs in repository.

## Acceptance gate

Supported ChatGPT interface successfully invokes the read-only MCP over private tunnel with synthetic content; no inbound Internet access is needed; proper scoping/auth is verified; negative tests demonstrate writes cannot be invoked; removing plugin/tunnel disables access. If ChatGPT feature is unavailable, mark **blocked, local MCP operational**.

## Report back

Verified product surface and available features, pinned client version, commands with secrets redacted, exact security boundary, synthetic end-to-end results, and WA04 operations handoff. Do not claim 'GPT can read every historical message'.