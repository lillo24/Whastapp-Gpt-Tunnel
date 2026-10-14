"""Fixed-query SQLite reads only; no runtime imports of the upstream MCP."""
from __future__ import annotations

import base64
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import time

from contracts import EXCERPT, PAGE_BUDGET, TOOLS, wire_result

ERRORS = {
    "INVALID_FILTER": "Invalid tool, filter, type, date, limit or cursor.",
    "DB_UNAVAILABLE": "The configured message store is unavailable or incompatible.",
    "NOT_LINKED": "No linked collector is available; stored history may be incomplete.",
    "NOT_FOUND": "No matching stored chat/message identity was found.",
}


class QueryError(Exception):
    def __init__(self, code):
        self.code = code


def normalized_date(value):
    if type(value) is not str or len(value) > 256:
        raise QueryError("INVALID_FILTER")
    try:
        if "T" not in value:
            raise ValueError
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError
        return date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except (ValueError, OverflowError):
        raise QueryError("INVALID_FILTER") from None


def bounded(value, size):
    if value is None:
        return None
    if not isinstance(value, str):
        raise QueryError("DB_UNAVAILABLE")
    return value[:size]


def stored_date(value):
    try:
        normalized = normalized_date(value)
        if normalized != value:
            raise QueryError("DB_UNAVAILABLE")
        return normalized
    except QueryError:
        raise QueryError("DB_UNAVAILABLE") from None


def error(code):
    return {"ok": False, "error": {"code": code, "message": ERRORS[code]}, "data": None,
            "next_cursor": None, "warnings": ["PARTIAL_HISTORY"], "freshness": None}


class QueryService:
    def __init__(self, directory: Path):
        self.directory = directory
        self._cursor_key = secrets.token_bytes(32)

    @contextmanager
    def connection(self):
        root = self.directory
        if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
            raise QueryError("DB_UNAVAILABLE")
        path = root / "messages.db"
        if path.resolve(strict=True) != path or not path.is_file():
            raise QueryError("DB_UNAVAILABLE")
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=.5)) as db:
            db.row_factory = sqlite3.Row
            db.enable_load_extension(False)
            deadline = time.monotonic() + 2
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
            db.create_function("_contains", 2, lambda text, query: int(query.casefold() in (text or "").casefold()), deterministic=True)

            def authorize(action, first, second, *_):
                if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_TRANSACTION):
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_READ and first in {"chats", "messages", "collector_status"}:
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_PRAGMA and first == "user_version" and second is None:
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_FUNCTION and (second or "").lower() in {"_contains", "substr", "coalesce", "count", "like"}:
                    return sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY

            db.set_authorizer(authorize)
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise QueryError("DB_UNAVAILABLE")
            db.execute("BEGIN")  # A read snapshot for status and records in this call.
            yield db

    def validate(self, name, args):
        if name not in TOOLS or type(args) is not dict:
            raise QueryError("INVALID_FILTER")
        props, required, _ = TOOLS[name]
        if set(args) - set(props) or any(key not in args for key in required):
            raise QueryError("INVALID_FILTER")
        for key, value in args.items():
            spec = props[key]
            if spec["type"] == "integer":
                if type(value) is not int or not spec["minimum"] <= value <= spec["maximum"]:
                    raise QueryError("INVALID_FILTER")
            elif type(value) is not str or not spec.get("minLength", 1) <= len(value) <= spec["maxLength"]:
                raise QueryError("INVALID_FILTER")
        result = dict(args)
        for key in ("before", "after"):
            if key in result and name == "list_messages":
                result[key] = normalized_date(result[key])
        if name == "list_messages" and result.get("after") and result.get("before") and result["after"] >= result["before"]:
            raise QueryError("INVALID_FILTER")
        return result

    def freshness(self, db):
        row = db.execute("SELECT linked,connected,heartbeat_at,last_connected_at,last_receive_at,last_db_update_at,last_sync_attempt_at,last_history_event_at,partial_history,synthetic,error_class FROM collector_status WHERE singleton=1").fetchone()
        if not row:
            return {"linked": False, "connected": False, "stale": True, "partial_history": True, "synthetic": False, "status": "UNKNOWN"}
        data = dict(row)
        if type(data["heartbeat_at"]) is not str:
            raise QueryError("DB_UNAVAILABLE")
        if data["error_class"] not in {None, "SYNTHETIC_ONLY", "STOPPED", "RELINK_REQUIRED", "NOT_LINKED", "CONNECT_FAILED", "DISCONNECTED"}:
            data["error_class"] = "UNKNOWN_ERROR"
        for field in ("linked", "connected", "synthetic"):
            data[field] = bool(data[field])
        for key in list(data):
            if key.endswith("_at") and data[key] is not None:
                try:
                    data[key] = stored_date(data[key])
                except QueryError:
                    raise QueryError("DB_UNAVAILABLE") from None
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(data["heartbeat_at"].replace("Z", "+00:00"))).total_seconds()
        data.update(stale=not data["connected"] or not 0 <= age <= 120, partial_history=True)
        data["status"] = "SYNTHETIC_ONLY" if data["synthetic"] else "NOT_LINKED" if not data["linked"] else "STALE_SYNC" if data["stale"] else "CONNECTED_COVERAGE_UNKNOWN"
        return data

    def scope(self, name, args):
        return hashlib.sha256(json.dumps([name, {k: v for k, v in args.items() if k not in {"cursor", "limit"}}], sort_keys=True).encode()).hexdigest()

    def encode_cursor(self, scope, key):
        raw = json.dumps({"v": 1, "scope": scope, "key": key}, separators=(",", ":")).encode()
        signed = raw + hmac.digest(self._cursor_key, raw, "sha256")
        return base64.urlsafe_b64encode(signed).decode().rstrip("=")

    def decode_cursor(self, token, scope, width):
        try:
            signed = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
            raw, signature = signed[:-32], signed[-32:]
            if not hmac.compare_digest(signature, hmac.digest(self._cursor_key, raw, "sha256")):
                raise ValueError
            data = json.loads(raw)
            if set(data) != {"v", "scope", "key"} or data["v"] != 1 or data["scope"] != scope:
                raise ValueError
            key = data["key"]
            if type(key) is not list or len(key) != width or any(type(x) is not str or len(x) > 256 for x in key):
                raise ValueError
            return key
        except (ValueError, TypeError, KeyError):
            raise QueryError("INVALID_FILTER") from None

    def envelope(self, data, freshness, cursor=None):
        warnings = ["PARTIAL_HISTORY"]
        if freshness["synthetic"]:
            warnings.append("SYNTHETIC_ONLY")
        if freshness["stale"]:
            warnings.append("STALE_SYNC")
        return {"ok": True, "data": data, "next_cursor": cursor, "warnings": warnings, "freshness": freshness}

    def size(self, result):
        # ASCII-escaped JSON is a conservative bound even for Unicode/control text.
        return len(json.dumps(wire_result(result), ensure_ascii=True).encode("utf-8"))

    def page(self, rows, limit, fresh, scope, convert, key):
        selected = list(rows[:limit])
        more = len(rows) > limit
        while True:
            cursor = self.encode_cursor(scope, key(selected[-1])) if selected and more else None
            result = self.envelope([convert(row) for row in selected], fresh, cursor)
            if self.size(result) <= PAGE_BUDGET:
                return result
            if len(selected) <= 1:
                raise QueryError("DB_UNAVAILABLE")
            selected.pop()
            more = True

    def chat_row(self, row):
        jid = bounded(row["jid"], 256)
        if jid != row["jid"]:
            raise QueryError("DB_UNAVAILABLE")
        date = row["last_message_time"]
        if date is not None:
            date = stored_date(date)
        return {"chat_jid": jid, "name": bounded(row["name"], 512), "last_message_time": date, "name_resolved": bool(row["name"])}

    def message_row(self, row):
        for key in ("id", "chat_jid", "sender"):
            if not row[key] or len(row[key]) > 256:
                raise QueryError("DB_UNAVAILABLE")
        content = row["body"] or ""
        return {"message_id": row["id"], "chat_jid": row["chat_jid"], "chat_name": bounded(row["chat_name"], 512),
                "sender": row["sender"], "sender_name": "Me" if row["is_from_me"] else bounded(row["sender_name"], 512),
                "sender_resolved": bool(row["is_from_me"] or row["sender_name"]), "timestamp": stored_date(row["timestamp"]),
                "is_from_me": bool(row["is_from_me"]), "media_type": bounded(row["media_type"], 24),
                "excerpt": content[:EXCERPT] + (" [TRUNCATED]" if len(content) > EXCERPT else ""), "truncated": len(content) > EXCERPT}

    def message_sql(self):
        return """SELECT m.id,m.chat_jid,m.sender,m.timestamp,m.is_from_me,m.media_type,
            substr(m.content,1,1001) AS body,substr(c.name,1,512) AS chat_name,
            (SELECT substr(name,1,512) FROM chats WHERE jid=m.sender) AS sender_name
            FROM messages m JOIN chats c ON c.jid=m.chat_jid"""

    def query(self, db, name, args, fresh):
        limit = args.get("limit", 20)
        scope = self.scope(name, args)
        if name == "health_status":
            counts = {}
            for table in ("chats", "messages"):
                n = db.execute(f"SELECT COUNT(*) FROM (SELECT 1 FROM {table} LIMIT 100001)").fetchone()[0]
                counts[table] = {"count": min(n, 100000), "capped": n > 100000}
            return self.envelope(counts, fresh)
        if not fresh["linked"] and not fresh["synthetic"]:
            if fresh["status"] == "UNKNOWN":
                raise QueryError("DB_UNAVAILABLE")
            raise QueryError("NOT_LINKED")
        if name in {"list_chats", "search_contacts", "get_chat"}:
            where, params = [], []
            if name == "get_chat":
                where.append("jid=?");params.append(args["chat_jid"])
            if name == "search_contacts":
                where.append("jid NOT LIKE '%@g.us'")
            if args.get("query"):
                where.append("(_contains(name,?) OR _contains(jid,?))");params += [args["query"], args["query"]]
            if args.get("cursor"):
                where.append("(COALESCE(last_message_time,''),jid)<(?,?)")
                params += self.decode_cursor(args["cursor"], scope, 2)
            sql = "SELECT jid,substr(name,1,512) AS name,last_message_time FROM chats"
            if where: sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY COALESCE(last_message_time,'') DESC,jid DESC LIMIT ?"
            rows = db.execute(sql, [*params, limit + 1]).fetchall()
            if name == "get_chat":
                if not rows: raise QueryError("NOT_FOUND")
                return self.envelope(self.chat_row(rows[0]), fresh)
            return self.page(rows, limit, fresh, scope, self.chat_row, lambda r: [r["last_message_time"] or "", r["jid"]])
        if name == "get_message_context":
            target = db.execute(self.message_sql() + " WHERE m.chat_jid=? AND m.id=?", [args["chat_jid"], args["message_id"]]).fetchone()
            if not target: raise QueryError("NOT_FOUND")
            key = [args["chat_jid"], target["timestamp"], target["id"]]
            before = db.execute(self.message_sql() + " WHERE m.chat_jid=? AND (m.timestamp,m.id)<(?,?) ORDER BY m.timestamp DESC,m.id DESC LIMIT ?", [*key, args.get("before", 5)]).fetchall()
            after = db.execute(self.message_sql() + " WHERE m.chat_jid=? AND (m.timestamp,m.id)>(?,?) ORDER BY m.timestamp,m.id LIMIT ?", [*key, args.get("after", 5)]).fetchall()
            rows = list(reversed(before)) + [target] + list(after)
            result = self.envelope([self.message_row(r) for r in rows], fresh)
            # Context has no paging. Reduce only surrounding excerpts, never omit the target.
            while self.size(result) > PAGE_BUDGET:
                for row in result["data"]:
                    row["excerpt"] = row["excerpt"][:max(50, len(row["excerpt"]) // 2)] + " [TRUNCATED]"
                    row["truncated"] = True
                if all(len(r["excerpt"]) <= 64 for r in result["data"]):
                    break
            if self.size(result) > PAGE_BUDGET: raise QueryError("DB_UNAVAILABLE")
            return result
        where, params = [], []
        for field, expression in (("chat_jid", "m.chat_jid=?"), ("sender", "m.sender=?"), ("after", "m.timestamp>?"), ("before", "m.timestamp<?"), ("query", "_contains(m.content,?)")):
            if field in args: where.append(expression);params.append(args[field])
        if args.get("cursor"):
            where.append("(m.timestamp,m.chat_jid,m.id)<(?,?,?)")
            params += self.decode_cursor(args["cursor"], scope, 3)
        sql = self.message_sql() + (" WHERE " + " AND ".join(where) if where else "")
        sql += " ORDER BY m.timestamp DESC,m.chat_jid DESC,m.id DESC LIMIT ?"
        rows = db.execute(sql, [*params, limit + 1]).fetchall()
        return self.page(rows, limit, fresh, scope, self.message_row, lambda r: [r["timestamp"], r["chat_jid"], r["id"]])

    def call(self, name, args=None):
        try:
            args = self.validate(name, {} if args is None else args)
            with self.connection() as db:
                fresh = self.freshness(db)
                result = self.query(db, name, args, fresh)
            if self.size(result) > PAGE_BUDGET:
                raise QueryError("DB_UNAVAILABLE")
            return result
        except QueryError as exc:
            return error(exc.code)
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, OverflowError):
            return error("DB_UNAVAILABLE")
