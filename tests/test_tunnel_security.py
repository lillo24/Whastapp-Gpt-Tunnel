"""Windows DPAPI/ACL/provisioning tests using only an obviously fake key."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh")
FAKE_KEY = "sk-fixture-" + "a" * 40
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


@unittest.skipUnless(os.name == "nt" and PWSH, "Windows PowerShell 7 is required")
class TunnelSecurityTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".local-fixtures"
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="tunnel-security-test-", dir=base)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.runtime = self.base / "runtime"

    def script(self, name, *args, env=None):
        return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-File", str(ROOT / "scripts" / name), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=20, env=env, creationflags=FLAGS)

    def initialize(self, **changes):
        params = {"TunnelId": "tunnel_" + "0" * 32, "OrganizationId": "org-fixture",
                  "DataDir": self.base / "absent-synthetic-store", "RuntimeDir": self.runtime}
        params.update(changes)
        args = [part for name, value in params.items() for part in ("-" + name, str(value))]
        return self.script("init_tunnel.ps1", *args)

    def provision(self):
        name = "wa-tunnel-key-" + uuid.uuid4().hex
        proc = subprocess.Popen([PWSH, "-NoProfile", "-NonInteractive", "-File", str(ROOT / "scripts/provision_tunnel_key.ps1"),
                                 "-PipeName", name, "-RuntimeDir", str(self.runtime)], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=FLAGS)
        try:
            first = proc.stdout.readline()
            self.assertIn(b"receiver ready", first)
            with open("\\\\.\\pipe\\" + name, "wb", buffering=0) as pipe:
                pipe.write((FAKE_KEY + "\n").encode("ascii"))
                # Hold the sender open until the receiver acknowledges encryption.
                # Closing a Windows pipe too early can discard unread bytes.
                out, err = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, "Synthetic credential provisioning failed")
            self.assertFalse(err)
            self.assertNotIn(FAKE_KEY.encode(), first + out)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
            proc.stdout.close()
            proc.stderr.close()

    def test_dpapi_private_acls_and_isolated_doctor(self):
        self.assertEqual(self.initialize().returncode, 0)
        self.assertEqual(self.initialize().returncode, 0)  # Idempotent; no association changes.
        self.provision()
        cipher = (self.runtime / "runtime-key.dpapi").read_text()
        self.assertNotIn(FAKE_KEY, cipher)
        # Emit booleans only, never the decrypted test credential or ACL identities.
        code = r'''
param([string]$RuntimeDir)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$cipher = [Convert]::FromBase64String([IO.File]::ReadAllText((Join-Path $RuntimeDir 'runtime-key.dpapi')))
$plain = [Security.Cryptography.ProtectedData]::Unprotect($cipher,[Text.Encoding]::UTF8.GetBytes('WhatsappGptTunnel/runtime-key/v1'),[Security.Cryptography.DataProtectionScope]::CurrentUser)
$secretMatches = [Text.Encoding]::UTF8.GetString($plain) -eq ('sk-fixture-' + ('a' * 40))
[Array]::Clear($plain,0,$plain.Length)
$allowed = @([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18')
$aclOK = $true
foreach ($item in @((Get-Item -LiteralPath $RuntimeDir)) + @(Get-ChildItem -Force -LiteralPath $RuntimeDir)) {
 if ($item.PSIsContainer) { $acl = [IO.FileSystemAclExtensions]::GetAccessControl([IO.DirectoryInfo]::new($item.FullName)) }
 else { $acl = [IO.FileSystemAclExtensions]::GetAccessControl([IO.FileInfo]::new($item.FullName)) }
 $rules = @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
 if (-not $acl.AreAccessRulesProtected -or $rules.Count -ne 2) { $aclOK = $false }
 foreach ($rule in $rules) {
  if ($rule.IdentityReference.Value -notin $allowed -or $rule.AccessControlType -ne 'Allow' -or $rule.FileSystemRights -ne 'FullControl') { $aclOK = $false }
 }
}
@{secret_matches=$secretMatches; private_acl=$aclOK} | ConvertTo-Json
'''
        script = self.base / "verify.ps1"
        script.write_text(code, encoding="utf-8")
        checked = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-File", str(script), "-RuntimeDir", str(self.runtime)],
                                 cwd=ROOT, capture_output=True, timeout=15, creationflags=FLAGS)
        self.assertEqual(checked.returncode, 0)
        self.assertEqual(json.loads(checked.stdout), {"secret_matches": True, "private_acl": True})
        poison = {**os.environ, "MCP_SERVER_URL": "http://example.invalid/poison", "LOG_HTTP_RAW_UNSAFE": "true",
                  "HARPOON_TARGETS": "poison", "CLOUDFLARED_TOKEN": "poison", "OPENAI_API_KEY": "poison"}
        doctor = self.script("check_tunnel.ps1", "-RuntimeDir", self.runtime, "-Doctor", env=poison)
        self.assertEqual(doctor.returncode, 0, "Isolated doctor failed with inherited configuration poison")
        self.assertEqual(json.loads(doctor.stdout), {"config_ok": True, "live_authorization_tested": False, "stdio_protocol_tested": False})

    def test_missing_corrupt_and_duplicate_credentials_fail_closed(self):
        self.assertEqual(self.initialize().returncode, 0)
        missing = self.script("check_tunnel.ps1", "-RuntimeDir", self.runtime, "-Doctor")
        self.assertNotEqual(missing.returncode, 0)
        self.provision()
        before = (self.runtime / "runtime-key.dpapi").read_bytes()
        duplicate = self.script("provision_tunnel_key.ps1", "-RuntimeDir", self.runtime, "-PipeName", "wa-tunnel-key-" + uuid.uuid4().hex)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertEqual((self.runtime / "runtime-key.dpapi").read_bytes(), before)
        (self.runtime / "runtime-key.dpapi").write_text("invalid-ciphertext", encoding="ascii")
        corrupt = self.script("check_tunnel.ps1", "-RuntimeDir", self.runtime, "-Doctor")
        self.assertNotEqual(corrupt.returncode, 0)
        self.assertNotIn(FAKE_KEY.encode(), missing.stdout + missing.stderr + duplicate.stdout + duplicate.stderr + corrupt.stdout + corrupt.stderr)

    def test_runtime_adoption_and_association_guardrails(self):
        unrelated = self.base / "unrelated"
        unrelated.mkdir()
        (unrelated / "keep.txt").write_text("unrelated")
        self.assertNotEqual(self.initialize(RuntimeDir=unrelated).returncode, 0)
        (unrelated / ".wa-tunnel-runtime").write_text("wa-tunnel-runtime-v1")
        self.assertNotEqual(self.initialize(RuntimeDir=unrelated).returncode, 0)
        self.assertEqual((unrelated / "keep.txt").read_text(), "unrelated")
        self.assertEqual(self.initialize().returncode, 0)
        original = (self.runtime / "connection.json").read_bytes()
        self.assertNotEqual(self.initialize(TunnelId="tunnel_" + "1" * 32).returncode, 0)
        self.assertEqual((self.runtime / "connection.json").read_bytes(), original)
        for invalid in ("relative", "C:\\", "\\\\server\\share"):
            self.assertNotEqual(self.initialize(DataDir=invalid).returncode, 0)
        link = self.base / "redirected"
        junction_script = self.base / "make-junction.ps1"
        junction_script.write_text("param([string]$Link,[string]$Target)\n$ErrorActionPreference='Stop'\nNew-Item -ItemType Junction -Path $Link -Target $Target | Out-Null\n", encoding="utf-8")
        junction = subprocess.run([PWSH,"-NoProfile","-NonInteractive","-File",str(junction_script),"-Link",str(link),"-Target",str(self.runtime)],
                                  cwd=ROOT,capture_output=True,timeout=10,creationflags=FLAGS)
        self.assertEqual(junction.returncode, 0, "Synthetic junction setup failed")
        self.assertNotEqual(self.initialize(RuntimeDir=link).returncode, 0)
        self.assertEqual((self.runtime / "connection.json").read_bytes(), original)

    def test_fake_key_runtime_loopback_single_writer_and_stop(self):
        self.assertEqual(self.initialize().returncode, 0)
        self.provision()
        proc = subprocess.Popen([PWSH, "-NoProfile", "-NonInteractive", "-File", str(ROOT / "scripts/run_tunnel.ps1"),
                                 "-RuntimeDir", str(self.runtime)], cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, creationflags=FLAGS)
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline and proc.poll() is None:
                if (self.runtime / "health.url").exists() and (self.runtime / "runtime-state.json").exists():
                    break
                time.sleep(0.1)
            self.assertIsNone(proc.poll(), "Fake-key tunnel runtime exited before local health was available")
            uri = (self.runtime / "health.url").read_text().strip()
            parsed = urllib.parse.urlparse(uri)
            self.assertEqual((parsed.scheme, parsed.hostname), ("http", "127.0.0.1"))
            checked = self.script("check_tunnel.ps1", "-RuntimeDir", self.runtime)
            self.assertEqual(checked.returncode, 0, "Local tunnel status failed: " + checked.stdout.decode())
            health = json.loads(checked.stdout)
            self.assertTrue(health["process_live"])
            self.assertFalse(health["control_plane_ok"])
            self.assertFalse(health["six_tools_observed"])
            state = json.loads((self.runtime / "runtime-state.json").read_text())
            listener = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command",
                "Get-NetTCPConnection -State Listen -OwningProcess " + str(state["pid"]) + " | Select-Object -ExpandProperty LocalAddress | ConvertTo-Json"],
                cwd=ROOT, capture_output=True, timeout=15, creationflags=FLAGS)
            self.assertEqual(listener.returncode, 0)
            addresses = json.loads(listener.stdout)
            self.assertEqual(addresses if isinstance(addresses, list) else [addresses], ["127.0.0.1"])
            duplicate = self.script("run_tunnel.ps1", "-RuntimeDir", self.runtime)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertEqual(json.loads((self.runtime / "runtime-state.json").read_text())["pid"], state["pid"])
            stopped = self.script("stop_tunnel.ps1", "-RuntimeDir", self.runtime)
            self.assertEqual(stopped.returncode, 0)
            out, err = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, "Local stop failed")
            self.assertFalse(err)
            self.assertNotIn(FAKE_KEY.encode(), out)
            unavailable = self.script("check_tunnel.ps1", "-RuntimeDir", self.runtime)
            self.assertNotEqual(unavailable.returncode, 0)
        finally:
            if proc.poll() is None:
                self.script("stop_tunnel.ps1", "-RuntimeDir", self.runtime)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            proc.stdout.close()
            proc.stderr.close()
