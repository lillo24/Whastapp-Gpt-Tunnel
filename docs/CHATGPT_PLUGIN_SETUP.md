# WA03 setup — synthetic Work path verified

Account controls were checked on 2026-10-12. ChatGPT Plugins → Add → Add custom
MCP server offers Tunnel mode and a Tunnel ID field. The Personal Platform
organization lists the operator as its only member and Owner; Settings →
Organization → Tunnels offers Create tunnel. ChatGPT identifies a Personal
account. The tunnel dialog offers one workspace association. After the operator
approved the reviewed draft, WhatsApp ReadOnly was created with only Personal
and that workspace. The saved scope was checked in Edit and left unchanged.

Automated saved-account sign-in was explicitly requested by the operator and
succeeded. The operator separately approved the runtime key: You, Default
project, only Tunnels Read + Use, all other permissions None, 30-day expiration.
Creation and local DPAPI protection succeeded on 2026-10-13; its UI expiration
is 2026-11-12. Actual client polls succeed. The operator approved the final
Connect and synthetic acceptance tests with Continue. The app is connected;
actual Work queries, fresh append, offline timeout and disconnect/reconnect
passed. Real WhatsApp pairing and production acceptance remain incomplete.

The official Windows client is pinned in `audit/tunnel-client-pin.json`.
Run `scripts/setup_tunnel_client.ps1` to checksum-verify/extract the client and
notices under ignored `.tools`. Cloudflare is not extracted or used. Review
upstream release changes before changing the pin; installation never silently
adopts a new release. The pin retains the official latest-release review link.

The inspected version supports `init --sample sample_mcp_stdio_local --profile
<name> --profile-dir <absolute private directory> --tunnel-id <reviewed ID>
--mcp-command <quoted absolute UV command> --control-plane-api-key-ref
env:WA_TUNNEL_API_KEY --health-listen-addr 127.0.0.1:0`. Derive the actual profile
from this binary's help, never put a literal key in those arguments. Use the
fixed UV launch in `WA03_HANDOFF.md`; the redacted configuration shape is in
`examples/tunnel-profile.example.yaml`.

The saved tunnel associations are verified. The separate least-privilege
runtime credential was created through official UI and stored locally under
DPAPI/current-user ACL protection. The wrapper injects it into the new client
process configuration; the trusted child sanitizer removes it before UV/MCP.
Do not use an admin key for the daemon or save
keys in chat/history/source/exported task XML. Ensure inherited environment
cannot enable additional transports, Harpoon targets, raw logs or remote UI.

The new PowerShell 7 scripts are `init_tunnel.ps1`, `provision_tunnel_key.ps1`,
`run_tunnel.ps1`, `check_tunnel.ps1` and `stop_tunnel.ps1`. Current protected local
configuration targets an invented Go-created store only. The profile launches
the fixed Python environment sanitizer, which then launches UV with the exact
locked/offline command above. See `WA03_VALIDATION.md` for fake-key, ACL,
environment, loopback, duplicate-run and stop evidence.

The client is running against that synthetic store. Actual polling succeeded;
the loopback UI shows main/stdio transport and disabled Harpoon, and has no log
events at the reviewed warn level. Anonymous/fake-key metadata and poll requests
all returned 401. ChatGPT displayed exactly six Read tools and Work queries
succeeded. The vendor MCP health diagnostic still reports not_observed; keep
that separate from actual invocation evidence.

The prepared ChatGPT plugin record uses Tunnel, the reviewed named ID and
No authentication for the local stdio application. Creating the record opened
a separate Connect WhatsApp ReadOnly consent. This consent describes basic web
information and recent ChatGPT context shared with the app. Action-time approval
was received, Connect succeeded and synthetic tests passed. The private personal
development installation and descriptions were reviewed. Do not publish
to the plugin Directory. The MCP is stdio and does not implement OAuth; a
broad/shared caller boundary requires additional supported auth or stopping.

Synthetic search, append, adversarial data, stopped tunnel, app disconnect and
same-scope reconnect passed. Local write/media refusal and unavailable/stale
collector tests pass. Authenticated alternate-workspace invocation and real
key/tunnel/phone revocation remain untested. Follow ACCEPTANCE_REPORT.md before
querying a controlled real conversation; never put its contents in evidence.

Doctor limitation observed locally: a placeholder key value passes config
validation, and stdio network reachability is skipped. Doctor success alone
does not prove a valid key, tunnel membership, ready transport or successful
ChatGPT invocation. The local configuration check is not an end-to-end test.

Current official references: [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels),
[connect a plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt),
[authentication](https://developers.openai.com/plugins/build/auth).
