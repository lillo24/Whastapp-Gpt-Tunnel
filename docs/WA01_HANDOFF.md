# WA01 handoff

This original WA00 handoff has been executed after the continuation recorded
in `OPERATOR_DECISIONS.md`. WA01 local synthetic acceptance passed; see
`WA01_VALIDATION.md`. The checklist below records the implementation scope.

## Inputs ready

- Source pin and exact dependency evidence in `audit/`; clean reference source
  in ignored `.audit/upstream` (refetch with `scripts/fetch_audit_source.ps1`).
- MIT attribution in `audit/dependency-inputs/LICENSE` for future derived source.
- `UPSTREAM_SURFACE_INVENTORY.md` assigns every observed send/listener/media/log
  path to WA01 or WA02. Do not launch unmodified upstream to explore it.
- `INTERFACE_CONTRACT.md`, fixture schema and generator for stable composite
  identity, UTC dates, privacy-safe status and bounded read outputs.
- Tests with duplicate replay, tied dates, Unicode, groups, own history, ambiguous
  names, unresolved mappings, malicious-looking inert text and metadata-only media.

## Execution after gate passes

1. Establish the intended private source destination before any remote publish.
   Keep production state outside the checkout; do not change the origin's
   visibility or push to the public repository without a separate request.
2. Obtain a reviewed Go >=1.24.1 and MSYS2 UCRT64 GCC from official sources.
   Use dedicated paths; verify checksums where provided. Set CGO_ENABLED=1 only
   in build process environment. No global `go env -w`, power changes or Defender
   exceptions. Capture actual versions/build outcome.
3. Build a minimal collector from audited receive/history code. Omit REST, send
   helpers, file/voice upload/download and unused explicit history-send helper.
   Refactor into testable storage/ingest/status/runtime components. No dormant
   dispatch or config toggle for writes. Separate terminal-only pair command.
4. Implement NTFS-protected absolute storage, single-writer ownership, safe
   migrations/backup, transactions, deduplication and monotonic chat recency.
5. Implement headless startup, closed-stdin behavior, graceful stop, capped
   reconnect/backoff, non-sensitive status and manual relink-required state.
   Ensure whatsmeow logs cannot emit private content or keys.
6. Run Go fixture/restart/migration/backup/concurrent-reader tests, malformed and
   unsupported events, no-listener process check and negative CLI/send tests.
   Use only synthetic data. Add real device access only with a later deliberate
   local pairing action; never infer compatibility from a passing build.

## WA02 prerequisite proof

WA01 must produce a tested Windows executable, fixed-path run/build scripts,
private-store runbook, actual source proof of no reachable send/media/listener
surface, and read-only SQLite access from a separate process. Mark unsupported
edits/deletes/reactions/wrappers explicitly and distinguish partial history from
freshness. All original WA01 acceptance checks must pass before WA02.

## Current outcome and remaining limits

The pinned tools, collector, migrations/snapshots, protected ACLs, single-writer
lock, process startup/stop and bounded MCP are implemented and synthetically
tested. Go module checksum verification passed. Full dependency CVE/security
approval and real WhatsApp protocol compatibility are not claimed. No private
remote, real pairing, tunnel or scheduled job exists. ChatGPT MCP/Tunnel controls
are observed; Platform permissions and caller scoping remain the WA03 gate.
