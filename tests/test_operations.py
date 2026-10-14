"""Synthetic WAL snapshots, quarantine, lifecycle and Windows supervision."""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh")
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
spec = importlib.util.spec_from_file_location("operations", ROOT / "scripts/operations.py")
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)
sys_spec = importlib.util.spec_from_file_location("synthetic_generator", ROOT / "scripts/generate_synthetic_fixture.py")
fixture = importlib.util.module_from_spec(sys_spec)
sys_spec.loader.exec_module(fixture)


class OperationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local-fixtures").mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="operations-", dir=ROOT / ".local-fixtures")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.store = self.base / "store"
        self.events = self.base / "events.json"
        self.events.write_text(json.dumps({"synthetic": True, "events": fixture.synthetic_events()}), encoding="utf-8")
        result = subprocess.run([str(ROOT / "bin/wa-bridge.exe"), "fixture", "--synthetic", "--input", str(self.events), "--data-dir", str(self.store)], capture_output=True, timeout=15, creationflags=FLAGS)
        self.assertEqual(result.returncode, 0)
        self.runtime = self.base / "runtime"
        self.runtime.mkdir()
        self.backups = self.base / "backups"
        self.backups.mkdir()
        (self.backups / ".wa-backups").write_text("wa-operations-v1")
        self.data = dict(data_dir=self.store, runtime_dir=self.runtime, backup_dir=self.backups)

    def ps(self, script, *args, timeout=20):
        return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-File", str(ROOT / "scripts" / script), *map(str, args)], capture_output=True, cwd=ROOT, timeout=timeout, creationflags=FLAGS)

    def prepare(self):
        self.assertEqual(self.ps("init_tunnel.ps1", "-TunnelId", "tunnel_" + "0"*32, "-OrganizationId", "org-fixture", "-DataDir", self.store, "-RuntimeDir", self.runtime).returncode, 0)
        self.opsdir = self.base / "ops"
        self.prefix = "WhatsappGptTunnel-Test-" + uuid.uuid4().hex[:8]
        result = self.ps("install.ps1", "-OpsDir", self.opsdir, "-RuntimeDir", self.runtime, "-BackupDir", self.backups, "-TaskPrefix", self.prefix, "-InteractiveTest")
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result

    def test_live_wal_snapshot_restore_quarantine_and_opt_in(self):
        self.assertEqual(ops.backup(self.data)["error_class"], "OPT_IN_REQUIRED")
        self.assertEqual(len(list(self.backups.glob("backup-*"))), 0)
        with closing(sqlite3.connect(self.store / "messages.db", isolation_level=None)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO messages(id,chat_jid,sender,content,timestamp,is_from_me) VALUES('wal-new',?,?,?,'2024-03-04T00:00:00.000000Z',0)", (fixture.jid("alice"), fixture.jid("alice"), "WAL synthetic proof"))
            self.assertGreater((self.store / "messages.db-wal").stat().st_size, 0)
            report = ops.backup(self.data, include_messages=True)
        target = self.base / "restored"
        self.assertTrue(ops.restore(self.data, report["backup_id"], target)["validated"])
        self.assertFalse(target.exists())
        target.mkdir()
        (target / ".wa-restored-disconnected").write_text("wa-operations-v1")
        self.assertFalse(ops.restore(self.data, report["backup_id"], target, apply=True)["network_started"])
        with closing(sqlite3.connect(target / "messages.db")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages").fetchone(), (13,))
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            self.assertEqual(db.execute("SELECT linked,connected,error_class FROM collector_status").fetchone(), (0,0,"STOPPED"))
        health=ops.QueryService(target).call("health_status")
        self.assertTrue(health["ok"])
        self.assertTrue(health["freshness"]["stale"])
        refused = subprocess.run([str(ROOT / "bin/wa-bridge.exe"), "run", "--synthetic", "--data-dir", str(target)], capture_output=True, timeout=5, creationflags=FLAGS)
        self.assertNotEqual(refused.returncode, 0)

    def test_retention_tamper_and_destination_guards(self):
        report = ops.backup(self.data, include_messages=True)
        manifest = self.backups / report["backup_id"] / "manifest.json"
        data = json.loads(manifest.read_text())
        data["files"][0]["sha256"] = "0"*64
        manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError): ops.restore(self.data, report["backup_id"], self.base / "tampered")
        for i in range(4): (self.backups / f"backup-cap-{i}").mkdir()
        self.assertEqual(ops.backup(self.data, True)["error_class"], "RETENTION_CAP_REACHED")
        self.assertEqual(len(list(self.backups.glob("backup-*"))), 5)
        for path in (Path("relative"), ROOT / "outside-fixtures"):
            with self.assertRaises(ValueError): ops.canonical(path) if not path.is_absolute() else ops.restore(self.data, "../escape", path)

    def test_session_pair_backup_refuses_active_collector(self):
        with closing(sqlite3.connect(self.store / "whatsapp.db")) as db:
            db.execute("CREATE TABLE fixture_session(synthetic INTEGER)")
            db.commit()
        proc = subprocess.Popen([str(ROOT / "bin/wa-bridge.exe"), "run", "--synthetic", "--data-dir", str(self.store)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=FLAGS)
        try:
            deadline = time.monotonic()+5
            while time.monotonic()<deadline:
                try:
                    with (self.store / "collector.lock").open("rb"): pass
                except PermissionError: break
                time.sleep(.05)
            self.assertIsNone(proc.poll())
            with self.assertRaises(PermissionError): ops.backup(self.data, True, True)
            self.assertEqual(len(list(self.backups.glob("backup-*"))), 0)
        finally:
            subprocess.run([str(ROOT / "bin/wa-bridge.exe"), "stop", "--data-dir", str(self.store)], capture_output=True, timeout=5, creationflags=FLAGS)
            proc.wait(timeout=7)
        report = ops.backup(self.data, True, True)
        self.assertEqual(report["files"], ["messages.db", "whatsapp.db"])

    @unittest.skipUnless(os.name == "nt" and PWSH, "Windows PowerShell 7 required")
    def test_task_previews_wrappers_and_explicit_deletion(self):
        result = self.prepare()
        self.assertFalse(json.loads(result.stdout)["registered"])
        self.assertEqual(len(json.loads(result.stdout)["tasks"]),2)
        for component in ("bridge", "tunnel"):
            xml = (self.opsdir / f"{component}.task.xml").read_text()
            self.assertIn("<RunLevel>LeastPrivilege</RunLevel>", xml)
            self.assertIn("<WorkingDirectory>", xml)
            self.assertNotIn("ExecutionPolicy", xml)
        self.assertEqual(self.ps("backup.ps1", "-OpsDir", self.opsdir).returncode, 0)
        saved = self.ps("backup.ps1", "-OpsDir", self.opsdir, "-IncludeMessages")
        self.assertEqual(saved.returncode, 0, saved.stderr.decode(errors="replace"))
        identifier = json.loads(saved.stdout)["backup_id"]
        restored = self.base / "wrapper-restored"
        preview = self.ps("restore.ps1", "-OpsDir", self.opsdir, "-BackupId", identifier, "-Destination", restored)
        self.assertEqual(preview.returncode, 0)
        self.assertFalse(restored.exists())
        applied = self.ps("restore.ps1", "-OpsDir", self.opsdir, "-BackupId", identifier, "-Destination", restored, "-Apply", "-ConfirmRestore")
        self.assertEqual(applied.returncode, 0, applied.stderr.decode(errors="replace"))
        args = ("-OpsDir", self.opsdir, "-MessagesAndSession", "-Backups", "-RuntimeCredentials", "-OperationLogs")
        self.assertEqual(self.ps("delete_data.ps1", *args).returncode, 0)
        self.assertTrue((self.store / "messages.db").exists())
        self.assertNotEqual(self.ps("delete_data.ps1", *args, "-Apply").returncode, 0)
        deleted = self.ps("delete_data.ps1", *args, "-Apply", "-ConfirmDelete")
        self.assertEqual(deleted.returncode, 0, deleted.stderr.decode(errors="replace"))
        self.assertFalse(self.store.exists() or self.opsdir.exists() or self.backups.exists() or self.runtime.exists())
        self.assertTrue((restored / "messages.db").exists())  # Separate inspection copy retained.

    @unittest.skipUnless(os.name == "nt" and PWSH, "Windows PowerShell 7 required")
    def test_supervisor_restart_singleton_status_and_stop(self):
        self.prepare()
        proc = subprocess.Popen([PWSH,"-NoProfile","-NonInteractive","-File",str(ROOT / "scripts/supervise.ps1"),"-Component","bridge","-OpsDir",str(self.opsdir)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=FLAGS)
        try:
            statefile=self.opsdir / "bridge.state.json"
            deadline=time.monotonic()+8
            while time.monotonic()<deadline and not statefile.exists() and proc.poll() is None: time.sleep(.1)
            self.assertIsNone(proc.poll())
            first=json.loads(statefile.read_text())["pid"]
            # Force only the known synthetic child to exercise bounded restart.
            killed=subprocess.run([PWSH,"-NoProfile","-NonInteractive","-Command",f"Stop-Process -Id {first} -Force"],capture_output=True,timeout=10,creationflags=FLAGS)
            self.assertEqual(killed.returncode,0)
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                if json.loads(statefile.read_text())["pid"] != first: break
                time.sleep(.1)
            self.assertNotEqual(json.loads(statefile.read_text())["pid"],first)
            duplicate=self.ps("supervise.ps1","-Component","bridge","-OpsDir",self.opsdir)
            self.assertNotEqual(duplicate.returncode,0)
            health=self.ps("status.ps1","-OpsDir",self.opsdir)
            self.assertEqual(health.returncode,0,health.stderr.decode(errors="replace"))
            self.assertFalse(json.loads(health.stdout)["tunnel"]["process_live"])
            stopped=self.ps("stop.ps1","-OpsDir",self.opsdir)
            self.assertEqual(stopped.returncode,0,stopped.stderr.decode(errors="replace"))
            out,err=proc.communicate(timeout=10)
            self.assertEqual(proc.returncode,0,err.decode(errors="replace"))
            self.assertFalse(out or err)
            log=(self.opsdir / "bridge.events.jsonl").read_text()
            self.assertIn('"event":"retry"',log)
            self.assertIn('"event":"stopped"',log)
            self.assertNotIn("Caff",log)
        finally:
            if proc.poll() is None:
                self.ps("stop.ps1","-OpsDir",self.opsdir)
                proc.communicate(timeout=10)
            proc.stdout.close(); proc.stderr.close()

    @unittest.skipUnless(os.name == "nt" and PWSH, "Windows PowerShell 7 required")
    def test_activation_requires_review_and_preserves_tunnel_scope(self):
        self.prepare()
        newstore=self.base / "new-store"
        result=subprocess.run([str(ROOT / "bin/wa-bridge.exe"),"fixture","--synthetic","--input",str(self.events),"--data-dir",str(newstore)],capture_output=True,timeout=10,creationflags=FLAGS)
        self.assertEqual(result.returncode,0)
        args=("-OpsDir",self.opsdir,"-DataDir",newstore)
        self.assertNotEqual(self.ps("activate_store.ps1",*args).returncode,0)
        # Invented status projection exercises only local configuration routing;
        # no session credential exists and no collector/network job is started.
        with closing(sqlite3.connect(newstore / "messages.db")) as db:
            db.execute("UPDATE collector_status SET linked=1,synthetic=0")
            db.commit()
        old=json.loads((self.runtime / "connection.json").read_text())
        self.assertEqual(self.ps("activate_store.ps1",*args).returncode,0)
        self.assertEqual(json.loads((self.runtime / "connection.json").read_text()),old)
        self.assertNotEqual(self.ps("activate_store.ps1",*args,"-Apply").returncode,0)
        quarantine=newstore / ".wa-restored-disconnected"
        quarantine.write_text("wa-operations-v1")
        self.assertNotEqual(self.ps("activate_store.ps1",*args,"-Apply","-ConfirmRealData").returncode,0)
        quarantine.unlink()
        activated=self.ps("activate_store.ps1",*args,"-Apply","-ConfirmRealData")
        self.assertEqual(activated.returncode,0,activated.stderr.decode(errors="replace"))
        changed=json.loads((self.runtime / "connection.json").read_text())
        self.assertEqual(changed,{**old,"data_dir":str(newstore)})
        configured=json.loads((self.opsdir / "operations.json").read_text())
        self.assertEqual(configured["data_dir"],str(newstore))
        self.assertFalse(configured["synthetic"])
        self.assertTrue((self.store / "messages.db").exists())
