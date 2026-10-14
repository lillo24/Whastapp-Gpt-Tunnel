# Operator decisions

2026-10-12: After the WA00 account-risk explanation and explicit acceptance
question, the operator instructed: **“Keep going.”** This is recorded as consent
to proceed with implementation with the disclosed unofficial-client account
risk. WA01/WA02 may proceed using synthetic data. It does not perform or replace
the separate deliberate foreground QR pairing step.

2026-10-12 UI observation: the signed-in ChatGPT account offers Plugins → Add →
Add custom MCP server, with selectable Tunnel mode and a Tunnel ID field. The
draft was canceled; no plugin was created. Platform opens at sign-in; manual
operator sign-in was requested, without requesting credentials in chat.
Platform permissions, intended workspace association, actual invocation and
single-user access remain unverified. No publishing to the public origin is
authorized by this continuation.

2026-10-12 continuation: the operator asked “Can you automate it for this time?”
in response to the Platform sign-in handoff. This specifically authorizes the
normal sign-in flow despite the computer-use skill's default manual-auth rule.
The existing saved-account flow succeeded without entering a password or MFA.
Personal organization was selected. Its People page lists only the operator,
with Owner role. ChatGPT's account menu identifies a Personal account. Platform
offers Create tunnel and a single workspace association option. A draft named
WhatsApp ReadOnly selects only Personal and that sole workspace; it is unsaved.

Separate approval was requested for creating that persistent tunnel route.
Login authorization is not recorded as approval to create credentials, expand
sharing, or link WhatsApp. No runtime key, tunnel or plugin has been created.
No account/organization/workspace identifiers or auth callback values are saved
in tracked evidence. Review screenshot and local draft use ignored fixture paths.

2026-10-12 tunnel approval: in response to the exact reviewed draft and Create
question, the operator answered **“Yes”**. The Create action succeeded. Reopening
Edit verified the saved name/description and sole Personal organization/workspace
associations; no changes were saved in that inspection. This approval covers
that tunnel creation only. Runtime credential and private-plugin grants remain
separate actions. Local metadata is protected and targets synthetic data only.

The runtime credential editor supports separate Tunnels Read and Use permissions.
An unsaved draft named WhatsApp ReadOnly runtime selects You, Default project,
Restricted, only those two permissions, and 30-day expiration. Separate approval
was requested for creating/protecting it and synthetic use. No real key has been
created, copied, stored or used. DPAPI/ACL/pipe/runtime tests use obvious fake keys.

2026-10-13 runtime credential approval: the operator answered **“Yes, do anything
you need”** to the exact restricted key creation/protection/synthetic-test
question (the message was repeated). The unchanged reviewed draft was created.
The one-time secret dialog confirmed only Tunnels Read + Use; all other API
permissions None. Its masked list entry is Active, Restricted, Default project,
expiration 2026-11-12. The value moved directly from the visible browser field
to the ACL-protected local pipe; the receiver confirmed DPAPI encryption. No
plaintext file, command argument, clipboard, source, or output contains the key.
The real client completed successful control-plane polls with zero consecutive
failures; readiness alone was not used as authorization evidence.

A custom ChatGPT plugin record named WhatsApp ReadOnly was prepared using the
same named tunnel and No authentication for its stdio application layer. This
opened the separate Connect WhatsApp ReadOnly consent. It states that basic web
information and recent ChatGPT context are shared with the app. Approval was
requested at that final grant for Connect and synthetic/disconnect/reconnect
acceptance. It remains pending; no real-tunnel MCP discovery or ChatGPT message
query is claimed. The general continuation does not replace action-time consent
for this newly presented access grant, or deliberate foreground WhatsApp pairing.

2026-10-13 Connect/test approval: the operator answered **“Continue”** to the
specific final Connect and synthetic acceptance question, including disconnect
and reconnect. Connect succeeded. The six Read tools were reviewed in ChatGPT.
Work returned Unicode and a newly appended invented message, treated an injected
instruction as data, timed out while the tunnel was stopped, lost its tool
registry after app disconnect, and succeeded again after same-scope reconnect.
No other plugin/site was called by these tests. This permits synthetic WA04
operations work. No phone pairing, real-message disclosure, broader workspace
grant, public publication or Windows credential entry has occurred.

WA04 startup test: boot-trigger registration was refused with 80070005 under
the standard user. Two temporary synthetic jobs with logon-only InteractiveToken
triggers registered and started, then were removed. No OS power, firewall,
Defender, execution-policy or credential policy was changed. Production boot/
logoff acceptance still requires local administrator registration and the
protected-store owner's Windows credential, entered locally.

2026-10-14 publication authorization: the operator explicitly requested pushing
the WA00-WA04 implementation, acceptance report and Windows setup instructions
to lillo24/Whastapp-Gpt-Tunnel and verifying GitHub access. This supersedes the
original private-repository preference for the implementation source and
redacted evidence only. Credentials, actual WhatsApp messages, session files,
databases, sensitive logs and local runtime artifacts are excluded. This
authorization does not claim or perform phone pairing or production acceptance.
