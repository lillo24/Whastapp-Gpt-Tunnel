"""WA00 offline acceptance: synthetic stores and static audit only."""
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


fixture = module("generate_synthetic_fixture")
audit = module("audit_upstream")


class FixtureTests(unittest.TestCase):
    def setUp(self):
        fixture.FIXTURE_ROOT.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix="wa00-test-", dir=fixture.FIXTURE_ROOT)
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "data"
        with patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
            self.summary = fixture.generate(self.output)
        self.db_path = self.output / "messages.db"
        self.db = sqlite3.connect(self.db_path)
        self.addCleanup(self.db.close)

    def test_integrity_and_no_session(self):
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.db.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(self.summary["messages"], 12)
        self.assertEqual(self.summary["chats"], 4)
        self.assertEqual({p.name for p in self.output.iterdir()}, {"messages.db", "events.json", "manifest.json"})
        self.assertEqual(self.db.execute("SELECT linked,connected,synthetic,partial_history FROM collector_status").fetchone(), (0, 0, 1, 1))

    def test_duplicate_replay_and_composite_identity(self):
        self.assertEqual(self.summary["input_events"], 13)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM messages WHERE id='shared-id'").fetchone()[0], 2)
        self.assertEqual(self.db.execute("SELECT COUNT(DISTINCT chat_jid) FROM messages WHERE id='shared-id'").fetchone()[0], 2)

    def test_unicode_multiline_own_history_and_groups(self):
        self.assertIn("你好", self.db.execute("SELECT content FROM messages WHERE id='tie-a'").fetchone()[0])
        self.assertIn("\n", self.db.execute("SELECT content FROM messages WHERE id='tie-b'").fetchone()[0])
        self.assertEqual(self.db.execute("SELECT is_from_me FROM messages WHERE id='own-history'").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT sender FROM messages WHERE id='group-a'").fetchone()[0], fixture.jid("alice"))

    def test_dates_normalized_with_ties(self):
        self.assertEqual(self.db.execute("SELECT timestamp FROM messages WHERE id='shared-id' AND chat_jid=?", (fixture.jid("alice"),)).fetchone()[0], "2024-02-29T08:00:00.000000Z")
        self.assertEqual(self.db.execute("SELECT timestamp FROM messages WHERE id='offset-boundary'").fetchone()[0], "2024-02-29T22:30:00.000000Z")
        ids = self.db.execute("SELECT id FROM messages WHERE timestamp='2024-02-29T10:00:00.000000Z' ORDER BY timestamp,chat_jid,id").fetchall()
        self.assertEqual(ids, [("tie-a",), ("tie-b",)])
        with self.assertRaises(ValueError):
            fixture.utc("2024-02-29T10:00:00")

    def test_adversarial_text_is_inert_data(self):
        text = self.db.execute("SELECT content FROM messages WHERE id='injection'").fetchone()[0]
        self.assertGreater(len(text), 10000)
        self.assertIn("example.invalid", text)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 12)
        # This validates fixture preservation only; no LLM was invoked.

    def test_metadata_only_and_unresolved_names(self):
        self.assertEqual(self.db.execute("SELECT media_type,filename,url,media_key FROM messages WHERE id='media-a'").fetchone(), ("image", None, None, None))
        self.assertEqual(self.db.execute("SELECT name FROM chats WHERE jid=?", (fixture.jid("unknown"),)).fetchone()[0], None)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chats WHERE name='Alex (synthetic)'").fetchone()[0], 2)

    def test_readonly_connection_rejects_write(self):
        before = hashlib.sha256(self.db_path.read_bytes()).digest()
        with closing(sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True)) as reader:
            self.assertEqual(reader.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 12)
            with self.assertRaises(sqlite3.OperationalError):
                reader.execute("DELETE FROM messages")
        self.assertEqual(hashlib.sha256(self.db_path.read_bytes()).digest(), before)

    def test_refuses_existing_directory_without_changing_database(self):
        before = self.db_path.read_bytes()
        with self.assertRaises(FileExistsError):
            fixture.generate(self.output)
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_refuses_outside_or_root_destination(self):
        for path in (ROOT / "store", ROOT, fixture.FIXTURE_ROOT, fixture.FIXTURE_ROOT / ".." / "escape"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                fixture.output_path(path)


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.collect(ROOT / audit.PIN["source_directory"])

    def test_pin_and_archived_evidence(self):
        archived = json.loads((ROOT / "audit/upstream-audit.json").read_text(encoding="utf-8"))
        self.assertEqual(self.report, archived)
        for path, expected in archived["dependency_sha256"].items():
            actual = hashlib.sha256((ROOT / audit.PIN["dependency_directory"] / path).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, path)

    def test_upstream_unsafe_surfaces_are_found(self):
        findings = self.report["findings"]
        for name, count in (("go_send_calls", 2), ("go_http_handlers", 2),
                            ("go_listeners", 1), ("go_upload_calls", 1),
                            ("go_download_calls", 1), ("python_http_posts", 4),
                            ("audio_process_execution", 1)):
            self.assertEqual(len(findings[name]["lines"]), count, name)
        self.assertEqual(len(self.report["registered_tools"]), 12)
        self.assertTrue({"send_message", "send_file", "send_audio_message", "download_media"}.issubset(self.report["registered_tools"]))

    def test_sensitive_paths_are_git_ignored(self):
        paths = [".audit/upstream/whatsapp-bridge/main.go", ".local-fixtures/test/events.json",
                 "store/messages.db", "store/messages.db-wal", "nested/whatsapp.db-shm",
                 "backups/snapshot.sqlite", "media/image.png", "logs/bridge.txt", ".env",
                 "private/runtime.key", "private/credentials.json", "private/secrets.json",
                 "private/session.json", "private/qr-code.png", "private/tunnel-profile.json",
                 "private/runtime-key.dpapi", "private/backup.dpapi", "private/tunnel-profile.yaml",
                 "private/connection.json", "private/operations.json", "private/runtime-state.json",
                 "private/mcp-health.json", "private/mcp-health.json.tmp", "private/health.url",
                 "private/bridge.task.xml", "private/tunnel.task.xml", "private/bridge.state.json",
                 "private/tunnel.state.json", "private/bridge.events.jsonl", "private/tunnel.events.previous.jsonl",
                 "private/collector.lock", "private/runtime.lock", "private/stop.request",
                 "private/history.db3", "private/history.db3-wal", "private/trace.log.1",
                 "private/trace.jsonl", "private/browser.har", "private/process.dmp",
                 "private/trace.etl", "private/database.dump", "private/device.session"]
        result = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "--stdin", "-z"],
                                input=("\0".join(paths) + "\0").encode(), capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(set(result.stdout.decode().rstrip("\0").split("\0")), set(paths))

    def test_original_plans_preserved(self):
        plans = sorted((ROOT / "history-implementations").glob("WA*.md"))
        self.assertEqual(len(plans), 5)
        for path in plans:
            original = subprocess.run(["git", "-C", str(ROOT), "show", f"0f80410423daff77e40892b27615f6df2bcfc167:{path.relative_to(ROOT).as_posix()}"], capture_output=True, check=True).stdout.decode("utf-8")
            self.assertEqual(path.read_text(encoding="utf-8").splitlines(), original.splitlines())


if __name__ == "__main__":
    unittest.main()
