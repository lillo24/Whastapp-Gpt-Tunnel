# Upstream provenance

Reviewed 2026-10-12; publication scope updated 2026-10-14. This implementation is based on
`https://github.com/lillo24/Whastapp-Gpt-Tunnel`, originally at
`0f80410423daff77e40892b27615f6df2bcfc167`. Its origin is **public**. On 2026-10-14
the operator explicitly requested publishing the implementation, acceptance
report and Windows instructions to that existing public repository, overriding
the original plan's private-repository preference for source publication.
Credentials, messages, sessions, databases, generated runtime configuration and
sensitive logs remain local and excluded. Repository visibility is unchanged.

## Audited source

- Repository: https://github.com/lharries/whatsapp-mcp
- Main/HEAD observed by `git ls-remote`: `7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88`.
- Commit date: 2025-07-13. It matches the plan's original pin.
- Local, ignored reference: `.audit/upstream`, detached at that SHA, clean.
- This source has been read as data only. No upstream bridge, MCP, audio converter,
  dependency installer, or pairing code has been run.
- License: MIT, copyright 2025 Luke Harries. Verbatim license retained in
  `audit/dependency-inputs/LICENSE`; preserve it with future derived source.
- `audit/upstream-pin.json` is the pin. `audit/upstream-audit.json` records raw Git
  object SHA256 hashes and application-source findings with exact line numbers.
- Original plans in `history-implementations/` remain unchanged.

## Dependency inputs

Exact Git object bytes of `go.mod`, `go.sum`, `pyproject.toml`, `uv.lock`, and
`.python-version` are archived beneath `audit/dependency-inputs/`, with hashes in
the scan report. They are **audit evidence**, not installed runtime packages.

Go requires 1.24.1, `go-sqlite3 v1.14.24` and
`whatsmeow v0.0.0-20250318233852-06705625cf82`; the module sums are present.
Python requires >=3.11 (`.python-version`: 3.11); its lock pins MCP 1.6.0,
httpx 0.28.1 and requests 2.32.3, among transitive packages. The upstream
pyproject's direct version ranges do not independently pin dependencies; the
lock supplies exact versions and artifact hashes. These are upstream evidence;
the shipped MCP instead uses a new minimal project with SDK 2.3.0 and its exact
`readonly_mcp/uv.lock`, without upstream send/audio imports. Go module checksum
verification passed during WA01. No full dependency-security/CVE approval is
claimed merely from checksums or successful synthetic tests.

The 2025 unofficial protocol library may be incompatible with current WhatsApp.
Source inspection cannot establish account compatibility. A later approved,
controlled manual device test must establish that; do not auto-upgrade the pin.

## Local patches and reproduction

WA00 adds audit evidence, synthetic fixtures and contracts. WA01 replaces the
upstream monolith with `bridge/` storage/ingest/runtime/security components,
retaining exact Go module inputs and MIT notice. REST/send/media helpers and
raw logs are omitted; private storage, migration backup, headless/manual-pair
separation, reconnect and tests are added. WA02 independently implements the
six bounded SQLite-read tools under `readonly_mcp/`, with a new SDK 2.3.0 lock.
The upstream Python package and installers are not used by the new runtime.
Toolchain versions/archives and all compiler packages are pinned in
`audit/toolchain-pin.json` and `audit/msys2-packages-pin.json`.

See `docs/WA01_VALIDATION.md`, `docs/WA02_VALIDATION.md` and
`docs/READ_ONLY_PROOF.md` for implemented boundaries and actual test evidence.
No protocol dependency was auto-upgraded or real account paired.

```powershell
.\scripts\fetch_audit_source.ps1
python .\scripts\audit_upstream.py
.\scripts\test_wa00.ps1 -PythonExe 'C:\absolute\path\python.exe'
.\scripts\verify_environment.ps1 -PythonExe 'C:\absolute\path\python.exe'
```

Only the fetch command needs the network; all following commands are local and
need no credentials. `--archive-inputs` was used once to capture the reviewed
inputs; it refuses to replace differing evidence. A changed upstream HEAD is
not adopted by these commands.
