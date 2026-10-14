# Tunnel trust boundary and current evidence

The client forwards only the fixed read-only stdio process. WhatsApp
session credentials stay in the collector's private store; the MCP reads only
messages.db. Query results intentionally travel to OpenAI when requested;
the database is not uploaded as a file. Repeated pages can disclose substantial
history despite per-call limits. All returned text is untrusted data.

The approved, created tunnel selects one Personal Platform organization and one offered
ChatGPT workspace. Personal's People page lists only the operator as Owner;
ChatGPT identifies a Personal account. These observations narrow the intended
boundary but do not prove authorization of every future caller. Private personal
plugin scope and actual synthetic invocation were observed. An authenticated
alternate-workspace invocation remains untested.
Saved associations were verified after creation. The separately approved
restricted runtime key is encrypted locally; actual control-plane polls succeed.
A custom plugin is connected following the specific operator approval; Work
synthetic tests and reversible app disconnect/reconnect passed.

Official tunnel transport uses outbound HTTPS. The inspected client also has
an operator health/admin listener: pin it to 127.0.0.1:0, never all interfaces,
and leave remote UI disabled. No router forwarding or public proxy is planned.
A loopback operator UI is distinct from the absent Go/MCP network listeners.
An actual client process with a fake key bound only 127.0.0.1; stop and duplicate
instance tests passed. This does not prove control-plane access. Other local
processes able to access loopback remain inside the operator trust boundary;
loopback alone is not Windows user authentication.

Use only the reviewed main stdio channel. No embedded demo server, HTTP MCP
target, Harpoon target, Cloudflare mode or generic HTTP callout is intended.
The client binary has these capabilities. `tunnel_common.ps1` regenerates a fixed
profile and passes only a small environment allowlist, excluding inherited MCP,
Harpoon, Cloudflare, proxy, Python/UV, logging and control-plane overrides.
`tunnel_mcp_child.py` clears the credential before UV starts the fixed MCP.
The binary's presence alone is not a read-only guarantee.

The runtime key belongs only in protected local secret storage and child
environment. It is separate from an admin API key; never grant admin CRUD to
the daemon. Profiles contain a secret reference, not its value, and stay
outside tracked source. Use DPAPI plus current-user/SYSTEM ACLs; do not collect
the key through chat or emit it in tool results. Provisioning/injection was
tested with a fake key. Missing/corrupt/duplicate credentials
fail closed. The real key was created with only Tunnels Read + Use, expires on
2026-11-12, and was transferred directly from its visible UI field to the private
local receiver without clipboard or plaintext file use. App disconnect/reconnect
was tested; real key rotation/revocation remains pending.

Raw HTTP logging must stay disabled. Application stderr is already redacted;
client output is drained to a null stream by the wrapper, raw HTTP logging is
false, level is warn, and the UI buffer is limited to one event. Zero is not used
because the inspected vendor code replaces it with the default 2000 events.
Do not export UI support logs with private content. Actual private access
boundary needs the remaining alternate-workspace check before production sign-off.
Tests used only synthetic stores, fake test keys and the approved restricted
runtime key; no real message or WhatsApp session has been used.

SHA256 verification of official v0.0.16 passed and local help/sample commands
were inspected. Doctor's config checks passed with a clearly fake placeholder
credential and therefore cannot establish actual authorization or readiness.
Missing secret references fail. Actual control-plane authorization is now proven
by successful runtime polls. `test_tunnel_access.ps1` confirms anonymous and fake
keys receive HTTP 401 on the vendor-documented metadata and poll routes, without
reading response bodies. These are control-plane tests, not proof that another
ChatGPT workspace cannot invoke the MCP. That caller boundary remains untested.
Synthetic end-to-end Work access passed, allowing WA04 code/tests. Production
pairing, administrator boot registration and final acceptance remain incomplete.
