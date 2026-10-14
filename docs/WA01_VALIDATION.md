# WA01 acceptance — 2026-10-12

Local synthetic acceptance passed. No account was linked, no QR displayed and
no private messages used. WA02 may proceed; actual protocol compatibility and
later account/tunnel/reboot acceptance remain unverified.

Toolchain: Go 1.27.2 windows/amd64; MSYS2 UCRT64 GCC 16.2.0 Rev5; Python 3.12.14;
uv 0.13.0. Archives and all 19 compiler packages are hash-pinned in `audit/`.
Go module verification passed. No global environment or OS policy was changed.

`scripts/build_bridge.ps1 -Test`: **12 Go tests passed**, Windows executable
built with CGO, trimpath and pinned modules. Tests cover actual synthetic live/
history protobufs, direct/group/self/unresolved attribution, Unicode/multiline
text, duplicate replay (including altered replay dates), monotonic recency,
malformed transaction rollback,
restart and writer exclusion, read-only rejection, concurrent active writer
snapshots, backup of WAL data, migration snapshot/date preservation, unsupported
reaction/protocol events, CLI negatives, dedicated paths and retry recovery/
cancellation with injected offline failures. Synchronous real network calls
remain subject to the pinned client's timeout behavior.

`scripts/test_clean_bridge_build.ps1`: passed Windows CGO build from a fresh
source-only directory with pinned modules/tools and no runtime configuration.
`scripts/setup_toolchain.ps1`: repeat run verified hashes and all 19 exact
compiler packages; no rolling package update or global PATH change.

`scripts/test_bridge_runtime.py`: passed closed-stdin synthetic and unlinked
headless startup; separate-process read-only status; exclusive writer; live
Get-NetTCPConnection check of each bridge PID returned zero listeners; local
stop exited cleanly with STOPPED status; stdout/stderr empty; private-looking
invalid arguments did not leak; redirected/noninteractive pairing was refused
before creating a store. No session DB was created by synthetic mode.
Direct NTFS checks verify protected root and only current-user/SYSTEM full
access on the root and generated files.

Source assertions reject send/upload/download/listener/HTTP API dispatch in
shipped application code. The third-party protocol library still contains
protocol functionality; it is not exposed through CLI, IPC or config. No
claim that every internal network exchange is absent. The original unsafe
reference stays ignored under `.audit` and is never built.

Unsupported edits/deletes/reactions and wrapped/disappearing/view-once data are
skipped and documented. History coverage is partial; legacy SQLite files with
unknown/naive timestamps fail without destructive repair. Stored historical
messages are not silently purged. See runbook/storage/schema documentation.
