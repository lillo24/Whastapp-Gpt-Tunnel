# WA02 acceptance — 2026-10-12

Local synthetic acceptance passed; WA03's local-code prerequisites are ready.
No real account was linked, private messages queried, or tunnel/plugin created.

Executed `scripts/test_local_mcp.ps1 -PythonExe <absolute Python 3.12.14 path>`.
UV locked dependency sync passed. Python unittest discovery ran **36 tests:
35 passed, 1 skipped**. This includes 13 preserved WA00 checks, 21 query tests
(one symlink privilege skip) and two real stdio protocol integration tests.

Coverage includes all six published tools; ambiguous and unresolved names;
composite IDs; Unicode/multiline and literal SQL-looking searches; leap days,
explicit offsets and invalid ranges; keyset ordering/ties; cursor authentication,
filter binding and restart expiry; long excerpts and Unicode payload caps;
bounded target-preserving context; no unrelated-contact or media-secret leakage;
read-only authorizer refusal; missing/empty/locked/incompatible stores; linked
versus synthetic status; stale versus quiet collectors; and fresh append reads.

The actual SDK client spawned the fixed UV stdio server, exercised tools/list
and read annotations, and read data inserted by the Go fixture command. A second
Go append became visible to the same MCP process. Write, media, file and SQL
tool attempts failed without echoing private-looking input. Raw JSON-RPC tested
initialization, repeated calls, malformed argument validation, protocol-only
stdout, physically closed stderr and clean EOF. No real network/account needed.

Actual `tools/list` names only:

```text
health_status
list_chats
list_messages
get_message_context
search_contacts
get_chat
```

One filesystem test could not create a Windows symlink without additional
privilege and is explicitly skipped; its canonical-path refusal check passed.
We did not change Developer Mode, privilege policy or antivirus settings.
No real WhatsApp compatibility, historical coverage, ChatGPT invocation,
tunnel authorization or reboot/Task Scheduler behavior is claimed.

Tool limits/schema and sanitized answers: `MCP_TOOL_CONTRACT.md`.
Read-only reachability/evidence and residual limits: `READ_ONLY_PROOF.md`.
Next gate and exact local launch: `WA03_HANDOFF.md`.
