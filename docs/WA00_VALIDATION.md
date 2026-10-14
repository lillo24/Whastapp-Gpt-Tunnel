# WA00 validation — 2026-10-12

Historical WA00-stage report: at this point the operator risk gate was pending.
For the subsequent continuation and completed local components see
`OPERATOR_DECISIONS.md`, `WA01_VALIDATION.md` and `WA02_VALIDATION.md`.
The environment observations below describe the initial audit, before local
toolchain setup. All
runtime data created during these checks is invented. No upstream program was
run, QR generated/scanned, WhatsApp account connected, tunnel created, plugin
installed, scheduled task registered or real message collected.

## Environment

Windows PowerShell, current execution policy RemoteSigned; no bypass used.
Verification with an explicit bundled Python executable produced:

```text
go      MISSING
python  AVAILABLE  Python 3.12.14
uv      MISSING
gcc     MISSING
git     AVAILABLE  git version 2.54.0.windows.1
tooling_available: false
windows_cgo_build_verified: false
credentials_required: false
network_used: false
```

`scripts/verify_environment.ps1` exited **1 as intended**, because prerequisites
are missing. Go and GCC were also absent from the checked default Go and MSYS2
UCRT64 locations. This is an observed tooling prerequisite, not a failed bridge
build; no bridge has been built. An unqualified WindowsApps Python alias is not
considered a working interpreter; use the real executable explicitly.

## Source review

```text
implementation starting commit: 0f80410423daff77e40892b27615f6df2bcfc167
upstream expected/actual HEAD:   7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88
audit reference working tree:   clean
source audit:                  PASS
archived dependency inputs:    6, byte hashes verified
original implementation plans: all 5 preserved
```

The source audit recorded 2 Go SendMessage calls (one unused history helper),
1 upload, 1 download, 2 HTTP handlers, 1 HTTP listener, 55 Go logging sites,
9 Python read/write-mode SQLite connections, 4 Python HTTP POSTs, 16 Python
logging sites and 1 audio subprocess execution site. These are **upstream
findings to remove/refactor**, not a claim the eventual product is read-only.
See `UPSTREAM_SURFACE_INVENTORY.md` for attribution and remediation owners.

Upstream registered tool names (static AST read; not a live tools/list call):

```text
search_contacts
list_messages
list_chats
get_chat
get_direct_chat_by_contact
get_contact_chats
get_last_interaction
get_message_context
send_message
send_file
send_audio_message
download_media
```

WA02 must prove the replacement's actual tools/list contains only approved reads.

## Offline acceptance

Executed `scripts/test_wa00.ps1 -PythonExe <absolute Python path>`:

```text
Ran 13 tests
OK
exit code: 0
```

Tests cover source pin/evidence hashes, unchanged plans, sensitive-path Git
exclusions; SQLite integrity/foreign keys/schema; composite message identity and
duplicate replay; Unicode/group/own sender data; UTC dates/leap-day/offset/ties;
inert long injection/SQL-looking strings; ambiguous/unresolved names;
metadata-only media; read-only SQLite rejects a DELETE with unchanged file hash;
and refusal to overwrite existing fixtures or write outside the fixture root.
Fixture generation ran with socket creation forbidden by the test harness.

The initial Windows Git-ignore test exposed CRLF interpretation in stdin. The
test now uses Git's NUL-delimited path interface; all intended paths are ignored.
This was a test-harness issue, not accepted as a false passing result.

Additional executed checks:

- `scripts/fetch_audit_source.ps1`: verified existing clean pin; exit 0.
- Fixture CLI in `.local-fixtures/wa00-smoke`: 4 chats, 12 messages, 13 input
  events; synthetic=true, linked=false, connected=false, partial_history=true.
- PowerShell parser: all three `.ps1` scripts parsed without errors.
- No private WhatsApp session database exists in the generated fixture output.

## Limits and next gate

No real protocol compatibility, Go build, device sync, Windows no-listener
process check, MCP JSON-RPC, account permissions, tunnel boundary or reboot test
has been claimed. These belong to WA01–WA04 in sequence. The reference checkout
contains unsafe upstream code for inspection only; it is ignored and not a
shipped application entrypoint. Synthetic fixtures are not real history.

WA01 may proceed only after explicit operator acceptance recorded from the
human. Product surface/access and single-user scoping must be established before
WA03. The remote is public and remains unchanged; local deliverables have not
been pushed. No phase after WA00 has started.
