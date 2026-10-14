# Supported surfaces and account gate

Checked official documentation and the operator's signed-in ChatGPT UI on
2026-10-12. Plugins → Add → Add custom MCP server displays a selectable Tunnel
connection and Tunnel ID field. The draft dialog was canceled without creating
anything. Subsequent explicitly authorized saved-account sign-in succeeded in
Platform. Personal lists only the operator as Owner; Create tunnel is available
and one ChatGPT workspace association is offered. The reviewed tunnel was
approved and created; its saved associations match only that organization and
workspace. The separately approved restricted runtime key is encrypted locally
and real client polls succeed. The separately approved plugin Connect and
synthetic Work invocation passed on 2026-10-13, including app disconnect and
reconnect. This does not establish real WhatsApp compatibility or boot operation.

| Capability | Documentation | Actual user's account |
|---|---|---|
| ChatGPT custom MCP: Plugins → plus → Add custom MCP server | Documented | Observed in signed-in UI |
| Connection mode: Tunnel | Documented | Selectable; Tunnel ID field observed |
| Platform tunnel creation | Requires organization Tunnels Read + Manage | Approved creation succeeded; saved scope checked |
| Runtime/use and plugin tunnel selection | Requires organization Tunnels Read + Use | Restricted Read + Use key created; actual polls succeed; named tunnel selectable in ChatGPT |
| Intended personal ChatGPT workspace association | Must be explicitly associated | Sole workspace association saved; Personal account; actual synthetic invocation passed |
| Invocation in ChatGPT Work | Must test the installed plugin in that surface | Passed: six reads, synthetic queries/fresh append, disconnect/reconnect |
| Ordinary-chat invocation | No entitlement/compatibility conclusion from this audit | Unverified |
| Single intended user, authentication and sharing scope | Transport is not sufficient proof of user authorization | Personal org lists operator only; private personal development plugin observed; alternate-workspace authenticated invocation untested |
| Billing/usage limits | No account-specific cost evidence | Unverified; no free-use promise |

The [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
documents outbound HTTPS and local stdio forwarding, without inbound Internet
access. Its transport permission and ChatGPT custom-MCP permissions are separate.
The [plugin connection guide](https://developers.openai.com/plugins/deploy/connect-chatgpt)
documents Tunnel selection and tool/schema/auth review. Read
[authentication guidance](https://developers.openai.com/plugins/build/auth)
before deciding how caller authorization will be enforced.

## Manual account check for WA03

1. In the intended ChatGPT personal workspace, confirm the custom MCP controls and
   Tunnel option. Record only yes/no and date, not identifying screenshots.
2. In the intended personal Platform organization, confirm Read + Manage and
   Read + Use permissions and ability to associate only the intended workspace.
3. Review who can discover/invoke that tunnel and plugin. If a shared workspace
   can expose other users to messages, narrow access with a supported auth
   strategy or stop. Do not interpret runtime-key possession as end-user auth.
4. At WA03, create/review the tunnel in the official UI, keep the runtime key in
   local protected secret storage, and test a synthetic MCP call in Work.
5. Test ordinary chat separately only if desired; do not claim it is supported
   from a successful Work test.

Never paste runtime keys, QR payloads, screenshots of messages, or account
identifiers into chat, source, task descriptions, shell history, or CI. Unknown
permissions mean the account gate is still pending. Lack of access means local
MCP only after WA01–WA02; no public workaround.

The official client's loopback administration UI is a different surface from a
bridge/MCP listener. WA03 must inspect its actual bind behavior and pin a reviewed
client version using that version's help. WA00 did not install a client.
Subsequent WA03 preparation pins official Windows client v0.0.16 and verifies
its archive SHA256, version and local help. Draft doctor checks validate config
and executable path only: a placeholder credential also passes, so this is
explicitly not proof of control-plane authorization.
