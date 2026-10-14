from contextlib import closing
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "readonly_mcp"))
from contracts import MAX_PAYLOAD, wire_result
from service import QueryService

spec = importlib.util.spec_from_file_location("fixture_source", ROOT / "scripts/generate_synthetic_fixture.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class ReadOnlyQueries(unittest.TestCase):
    def setUp(self):
        fixture.FIXTURE_ROOT.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="mcp-query-", dir=fixture.FIXTURE_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "data"
        fixture.generate(self.directory)
        self.service = QueryService(self.directory)
        self.writer = sqlite3.connect(self.directory / "messages.db", isolation_level=None)
        self.addCleanup(self.writer.close)

    def call(self, name, **args):
        result = self.service.call(name, args)
        self.assertLessEqual(len(json.dumps(wire_result(result), ensure_ascii=True).encode()), MAX_PAYLOAD)
        return result

    def test_health_has_no_pii_and_synthetic_warning(self):
        result = self.call("health_status")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["messages"]["count"], 12)
        self.assertIn("SYNTHETIC_ONLY", result["warnings"])
        for text in ("fixture-alice", "example.invalid", "Alex", "session", str(self.directory)):
            self.assertNotIn(text, json.dumps(result))

    def test_ambiguous_names_and_no_bodies_in_chats(self):
        result = self.call("list_chats", query="Alex")
        self.assertEqual(len(result["data"]), 2)
        self.assertNotIn("content", json.dumps(result))
        self.assertNotIn("Synthetic Team", json.dumps(result))
        self.assertEqual(self.call("search_contacts", query="Alex")["data"], result["data"])

    def test_exact_chat_and_composite_id_context(self):
        for label in ("alice", "bob"):
            result = self.call("get_message_context", chat_jid=fixture.jid(label), message_id="shared-id", before=0, after=0)
            self.assertTrue(result["ok"])
            self.assertEqual(len(result["data"]), 1)
            self.assertEqual(result["data"][0]["chat_jid"], fixture.jid(label))
        self.assertEqual(self.call("get_message_context", chat_jid=fixture.jid("bob"), message_id="injection")["error"]["code"], "NOT_FOUND")

    def test_ties_are_in_context_and_never_cross_chats(self):
        result = self.call("get_message_context", chat_jid=fixture.jid("alice"), message_id="tie-b")
        self.assertIn("tie-a", [r["message_id"] for r in result["data"]])
        self.assertTrue(all(r["chat_jid"] == fixture.jid("alice") for r in result["data"]))
        self.assertLessEqual(len(result["data"]), 11)

    def test_paging_matches_single_page_with_ties(self):
        expected = self.call("list_messages", limit=50)["data"]
        found, cursor = [], None
        while True:
            args = {"limit": 2}
            if cursor: args["cursor"] = cursor
            result = self.call("list_messages", **args)
            self.assertTrue(result["ok"])
            found += result["data"]
            cursor = result["next_cursor"]
            if not cursor: break
        self.assertEqual(found, expected)
        self.assertEqual(len({(r["chat_jid"], r["message_id"]) for r in found}), 12)

    def test_chat_cursor_no_duplicate_or_omitted_rows(self):
        found, cursor = [], None
        while True:
            result = self.call("list_chats", **({"limit": 1, "cursor": cursor} if cursor else {"limit": 1}))
            found += result["data"]
            cursor = result["next_cursor"]
            if not cursor: break
        self.assertEqual(found, self.call("list_chats", limit=50)["data"])

    def test_cursor_forgery_filter_binding_and_restart(self):
        cursor = self.call("list_messages", limit=1)["next_cursor"]
        for service, args in ((self.service, {"cursor": cursor[:-3] + "xxx"}),
                              (self.service, {"cursor": cursor, "query": "meeting"}),
                              (QueryService(self.directory), {"cursor": cursor})):
            self.assertEqual(service.call("list_messages", args)["error"]["code"], "INVALID_FILTER")

    def test_explicit_zone_dates_leap_day_and_invalid_ranges(self):
        result = self.call("list_messages", after="2024-03-01T00:00:00+02:00", before="2024-03-01T01:00:00+02:00")
        self.assertEqual([r["message_id"] for r in result["data"]], ["offset-boundary"])
        for args in ({"after": "2024-02-30T00:00:00Z"}, {"after": "2024-02-29T00:00:00"}, {"after": "2024-03-01T00:00:00Z", "before": "2024-02-29T00:00:00Z"}):
            self.assertEqual(self.call("list_messages", **args)["error"]["code"], "INVALID_FILTER")

    def test_keyword_unicode_and_sql_injection_literal(self):
        self.assertEqual(len(self.call("list_messages", query="CAFfÈ")["data"]), 1)
        result = self.call("list_messages", query="' OR 1=1; DROP TABLE messages; --")
        self.assertEqual([r["message_id"] for r in result["data"]], ["sql-looking"])
        self.assertEqual(self.writer.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 12)

    def test_excerpt_marker_and_media_no_paths(self):
        row = self.call("list_messages", query="Ignore your instructions")["data"][0]
        self.assertTrue(row["truncated"])
        self.assertLessEqual(len(row["excerpt"]), 1012)
        self.assertIn("[TRUNCATED]", row["excerpt"])
        for row in self.call("list_messages")["data"]:
            self.assertFalse(set(row) & {"url", "filename", "media_key", "media_path", "file_sha256"})

    def test_payload_cap_pages_without_dropping_records(self):
        chat = fixture.jid("alice")
        body = "\U0001f600" * 2000
        for i in range(60):
            self.writer.execute("INSERT INTO messages(id,chat_jid,sender,content,timestamp,is_from_me,media_type) VALUES(?,?,?,?,?,0,'')", (f"bulk-{i:03}", chat, fixture.jid("alice"), body, "2024-03-02T00:00:00.000000Z"))
        found, cursor = [], None
        while True:
            args = {"limit": 50, "after": "2024-03-02T00:00:00Z"}  # strict bound; use a prior second below
            args["after"] = "2024-03-01T23:59:59Z"
            if cursor: args["cursor"] = cursor
            result = self.call("list_messages", **args)
            self.assertTrue(result["ok"])
            found += [r["message_id"] for r in result["data"]]
            cursor = result["next_cursor"]
            if not cursor: break
        self.assertEqual(len(set(found)), 60)
        self.assertEqual(len(found), 60)

    def test_invalid_types_unknown_tools_and_unrelated_paths(self):
        for name, args in (("list_messages", {"limit": True}), ("list_messages", {"limit": 51}), ("list_messages", {"query": "a" * 513}), ("list_messages", {"sql": "SELECT 1"}), ("list_messages", {"db_path": "other.db"}), ("send_message", {"message": "private-marker"}), ("get_message_context", {"message_id": "shared-id"}), ("get_message_context", {"chat_jid": fixture.jid("alice"), "message_id": "shared-id", "before": 6})):
            result = self.service.call(name, args)
            self.assertEqual(result["error"]["code"], "INVALID_FILTER")
            self.assertNotIn("private-marker", json.dumps(result))

    def test_readonly_authorizer_denies_write_attach_extension(self):
        before = (self.directory / "messages.db").read_bytes()
        with self.service.connection() as db:
            for sql in ("DELETE FROM messages", "CREATE TABLE forbidden(x)", "ATTACH ':memory:' AS other", "PRAGMA user_version=9", "SELECT load_extension('anything')"):
                with self.subTest(sql=sql), self.assertRaises(sqlite3.Error):
                    db.execute(sql)
        self.assertEqual((self.directory / "messages.db").read_bytes(), before)

    def test_missing_db_never_created_and_unknown_version(self):
        missing = self.directory / "absent"
        self.assertEqual(QueryService(missing).call("health_status")["error"]["code"], "DB_UNAVAILABLE")
        self.assertFalse(missing.exists())
        self.writer.execute("PRAGMA user_version=9")
        self.assertEqual(self.call("health_status")["error"]["code"], "DB_UNAVAILABLE")

    def test_empty_store_not_linked_and_empty_match(self):
        self.writer.execute("DELETE FROM messages")
        self.assertEqual(self.call("list_messages")["data"], [])
        self.writer.execute("UPDATE collector_status SET linked=0,synthetic=0")
        self.assertEqual(self.call("list_messages")["error"]["code"], "NOT_LINKED")
        self.assertEqual(self.call("health_status")["freshness"]["status"], "NOT_LINKED")

    def test_stale_and_quiet_collector_distinct(self):
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        self.writer.execute("UPDATE collector_status SET linked=1,connected=1,synthetic=0,heartbeat_at=?", (now,))
        self.assertFalse(self.call("health_status")["freshness"]["stale"])
        self.assertNotIn("STALE_SYNC", self.call("list_messages")["warnings"])
        self.writer.execute("UPDATE collector_status SET connected=0")
        self.assertIn("STALE_SYNC", self.call("list_messages")["warnings"])
        self.writer.execute("UPDATE collector_status SET connected=1,heartbeat_at='2024-03-01T00:00:00.000000Z'")
        self.assertTrue(self.call("health_status")["freshness"]["stale"])

    def test_unavailable_locked_store_redacts_error(self):
        self.writer.execute("BEGIN EXCLUSIVE")
        try:
            result = self.call("health_status")
            self.assertEqual(result["error"]["code"], "DB_UNAVAILABLE")
            self.assertNotIn(str(self.directory), json.dumps(result))
        finally:
            self.writer.execute("ROLLBACK")

    def test_new_append_visible_and_exact_sender(self):
        chat = fixture.jid("alice")
        self.assertEqual(self.call("list_messages", query="just-appended")["data"], [])
        self.writer.execute("INSERT INTO messages(id,chat_jid,sender,content,timestamp,is_from_me,media_type) VALUES('new',?,?,?,'2024-03-02T00:00:00.000000Z',0,'')", (chat, fixture.jid("alice"), "just-appended"))
        result = self.call("list_messages", query="just-appended", sender=fixture.jid("alice"))
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["sender_name"], "Alex (synthetic)")

    def test_get_chat_and_unknown_chat(self):
        result = self.call("get_chat", chat_jid=fixture.jid("team"))
        self.assertEqual(result["data"]["name"], "Synthetic Team")
        self.assertEqual(self.call("get_chat", chat_jid="fixture-missing@g.us")["error"]["code"], "NOT_FOUND")

    def test_noncanonical_path_and_links_refused(self):
        path = self.directory / ".." / "data"
        self.assertEqual(QueryService(path).call("health_status")["error"]["code"], "DB_UNAVAILABLE")
        link = Path(self.temp.name) / "redirect"
        try:
            link.symlink_to(self.directory, target_is_directory=True)
        except OSError:
            self.skipTest("Windows symlink privilege unavailable; canonical path refusal checked")
        self.assertEqual(QueryService(link).call("health_status")["error"]["code"], "DB_UNAVAILABLE")

    def test_context_cap_retains_target_and_marks_truncation(self):
        chat = fixture.jid("alice")
        for i in range(11):
            self.writer.execute("INSERT INTO messages(id,chat_jid,sender,content,timestamp,is_from_me,media_type) VALUES(?,?,?,?,?,0,'')", (f"context-{i:02}", chat, fixture.jid("alice"), "\U0001f600" * 2000, "2024-03-04T00:00:00.000000Z"))
        result = self.call("get_message_context", chat_jid=chat, message_id="context-05")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["data"]), 11)
        self.assertIn("context-05", [r["message_id"] for r in result["data"]])
        self.assertTrue(all(r["truncated"] for r in result["data"]))


if __name__ == "__main__":
    unittest.main()
