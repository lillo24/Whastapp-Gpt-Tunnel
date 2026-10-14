# WA00 go/no-go — 2026-10-12

**Updated 2026-10-13: WA00–WA02 local acceptance and WA03 synthetic Work gate
passed; WA04 implementation tested, production acceptance incomplete.**
The scoped tunnel and private app are connected to invented data. No WhatsApp
account is paired or production startup job registered. See ACCEPTANCE_REPORT.md.

## Gate matrix

| Gate | Evidence/status | Resolution/owner |
|---|---|---|
| Dedicated workspace | This task's cloned repository only; no other projects modified | Passed locally |
| Publication scope | Origin is public; on 2026-10-14 operator explicitly requested publication to this repository | Publish implementation/redacted evidence only; all runtime private data excluded; visibility unchanged |
| Upstream pin/review | `7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88`, unchanged HEAD; static scan and MIT/dependency evidence archived | Passed for application-source audit |
| Unofficial-account risk | Operator continued after the explicit risk question; see `OPERATOR_DECISIONS.md` | Implementation gate passed; manual pairing remains separate |
| Windows build tools | Dedicated pinned Go 1.27.2, UCRT GCC 16.2.0, uv 0.13.0; Python 3.12.14 | Clean Windows CGO build and synthetic tests passed |
| Product permissions | Scoped tunnel/key created with separate approvals; connected personal app; actual synthetic Work tests passed | Alternate-workspace authenticated invocation untested |
| Real pairing | None; only synthetic/unlinked test state | Deliberate foreground operator pairing required |
| Synthetic acceptance | See WA00 historical report and `WA01_VALIDATION.md` / `WA02_VALIDATION.md` | Passed locally; one symlink test privilege skip disclosed |
| Account/protocol compatibility | Unverified; pinned client dates to March 2025 | Later controlled test only, no safety guarantee |

## Account and privacy decision

This uses `whatsmeow`, an unofficial linked-device client. WhatsApp warns that
using/linking unofficial apps violates its terms and can cause restrictions or a
temporary/permanent ban. Read-only access does not remove this risk. Review the
[official warning](https://faq.whatsapp.com/1217634902127718/) and applicable
[EEA terms](https://www.whatsapp.com/legal/terms-of-service-eea). The official
Business Platform does not provide arbitrary personal-account history access.

The operator answered “Keep going” after the risk explanation and explicit
acceptance question. That continuation is recorded in `OPERATOR_DECISIONS.md`;
the original general implementation request alone was not used as acceptance.
The WA00 acceptance rule says:

> The next implementation plan WA01 may start only after upstream pin/review and the operator accepts the stated WhatsApp account risk *before any future real linking*.

Acceptance permits continued implementation; it does not scan a QR code or
authorize automatic linking. Pairing remains a deliberate foreground action.

SQLite history and linked-device credentials are sensitive plaintext unless
protected by appropriate device encryption. Local account ACLs reduce access
by other users, not malware running as the same user or an administrator.
Queries selected by the user transmit retrieved content to OpenAI and may
include third-party personal data. Avoid unrelated content and broad summaries.

## Capability decision

Follow `SUPPORTED_SURFACE.md`. ChatGPT custom-MCP and Tunnel controls are
observed. Personal Platform Owner and enabled tunnel creation were subsequently
checked after authorized automated sign-in. Synthetic invocation in Work passed;
an authenticated alternate-workspace caller boundary remains untested. Never infer costs from a plan
name. If these are unavailable, stop at a tested local-only milestone; do not
introduce a public proxy or unauthenticated endpoint.

## Next phase

WA03 synthetic acceptance passed and WA04 operator scripts/recovery tests are
implemented. Windows refused boot-trigger registration from this standard user;
temporary logon-only test jobs ran and were removed. Production requires local
administrator registration, phone pairing and controlled real-message/reboot/
logoff acceptance. See `ALWAYS_ON_RUNBOOK.md` and `ACCEPTANCE_REPORT.md`.
