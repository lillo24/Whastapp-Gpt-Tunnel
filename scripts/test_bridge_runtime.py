"""Windows synthetic process acceptance. Never connects or pairs an account."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "bin/wa-bridge.exe"
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def call(*args):
    return subprocess.run([str(EXE), *map(str, args)], capture_output=True, creationflags=FLAGS, timeout=15)


def main():
    base = ROOT / ".local-fixtures"
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bridge-runtime-", dir=base) as tmp:
        for synthetic in (True, False):
            store = Path(tmp) / ("synthetic-store" if synthetic else "unlinked-store")
            args = [str(EXE), "run", "--data-dir", str(store)] + (["--synthetic"] if synthetic else [])
            proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=FLAGS)
            try:
                deadline = time.monotonic() + 15
                state = None
                while time.monotonic() < deadline:
                    assert proc.poll() is None, "headless process exited"
                    try:
                        with closing(sqlite3.connect((store / "messages.db").as_uri() + "?mode=ro", uri=True)) as db:
                            state = db.execute("SELECT linked,connected,synthetic,error_class FROM collector_status").fetchone()
                    except sqlite3.Error:
                        state = None
                    if state and state[3] in ("SYNTHETIC_ONLY", "RELINK_REQUIRED"):
                        break
                    time.sleep(.1)
                assert state == (0, 0, int(synthetic), "SYNTHETIC_ONLY" if synthetic else "RELINK_REQUIRED"), "wrong safe startup status"
                if os.name == "nt":
                    query = f"@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object OwningProcess -eq {proc.pid}).Count"
                    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", query], capture_output=True, creationflags=FLAGS, timeout=15)
                    assert result.returncode == 0 and result.stdout.strip() == b"0", "bridge listener found or check unavailable"
                    acl_query = """
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
$taskAclUser = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskAclRoot = Get-Acl -LiteralPath $env:WA_ACL_TEST_STORE
if (-not $taskAclRoot.AreAccessRulesProtected) { throw 'Unprotected root' }
$taskAclPaths = @($env:WA_ACL_TEST_STORE) + @(Get-ChildItem -LiteralPath $env:WA_ACL_TEST_STORE -Force -Recurse | Select-Object -ExpandProperty FullName)
foreach ($taskAclPath in $taskAclPaths) {
    $taskAclRules = @((Get-Acl -LiteralPath $taskAclPath).GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
    if ($taskAclRules.Count -ne 2) { throw 'Unexpected ACL entries' }
    foreach ($taskAclRule in $taskAclRules) {
        if ($taskAclRule.IdentityReference.Value -notin @($taskAclUser,'S-1-5-18') -or $taskAclRule.AccessControlType -ne 'Allow' -or ($taskAclRule.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -ne [Security.AccessControl.FileSystemRights]::FullControl) { throw 'Unexpected ACL access' }
    }
}
Write-Output 'PASS'
"""
                    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", acl_query], env={**os.environ, "WA_ACL_TEST_STORE": str(store)}, capture_output=True, creationflags=FLAGS, timeout=15)
                    assert result.returncode == 0 and result.stdout.strip() == b"PASS", "private store ACL check failed"
                blocked = call("run", "--data-dir", store, "--synthetic")
                assert blocked.returncode != 0, "second writer started"
                assert call("stop", "--data-dir", store).returncode == 0
                out, err = proc.communicate(timeout=10)
                assert proc.returncode == 0 and not out and not err, "unsafe logs or unclean stop"
                with closing(sqlite3.connect((store / "messages.db").as_uri() + "?mode=ro", uri=True)) as db:
                    assert db.execute("SELECT connected,error_class FROM collector_status").fetchone() == (0, "STOPPED")
                assert not (store / "whatsapp.db").exists() if synthetic else True
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate()
        marker = b"fixture-private-marker"
        negative = call("send_message", marker.decode(), "--data-dir", str(Path(tmp) / "bad"))
        assert negative.returncode != 0 and marker not in negative.stderr and not negative.stdout
        pairing = call("pair", "--data-dir", str(Path(tmp) / "never-pair"))
        assert pairing.returncode != 0 and not (Path(tmp) / "never-pair").exists(), "noninteractive pairing reachable"
    print(json.dumps({"headless_closed_stdin": "PASS", "synthetic_and_unlinked_startup": "PASS", "no_process_listeners": "PASS", "private_store_acl": "PASS", "writer_lock": "PASS", "graceful_local_stop": "PASS", "redacted_negative_calls": "PASS", "noninteractive_pairing_refused": "PASS", "real_account_used": False}, indent=2))


if __name__ == "__main__":
    main()
