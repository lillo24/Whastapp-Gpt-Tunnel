"""Bounded operational timestamps only; never persist arguments or results."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path


class ExecutionHealth:
    def __init__(self, configured_path):
        self.path = Path(configured_path) if configured_path else None
        self.state = {"schema_version": 1, "process_id": os.getpid(), "successful_calls": 0,
                      "last_successful_execution_at": None, "last_error_at": None, "last_error_class": None}

    def record(self, ok, error_class=None):
        if self.path is None:
            return
        try:
            path = self.path
            parent = path.parent
            if not path.is_absolute() or path.name != "mcp-health.json" or parent.resolve(strict=True) != parent:
                return
            if (parent / ".wa-tunnel-runtime").read_text() != "wa-tunnel-runtime-v1":
                return
            if path.is_symlink() or (path.exists() and path.resolve(strict=True) != path):
                return
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            if ok:
                self.state["successful_calls"] = min(1_000_000_000, self.state["successful_calls"] + 1)
                self.state["last_successful_execution_at"] = stamp
            else:
                self.state["last_error_at"] = stamp
                self.state["last_error_class"] = error_class if error_class in {"INVALID_FILTER", "DB_UNAVAILABLE", "NOT_LINKED", "NOT_FOUND"} else "UNKNOWN_ERROR"
            # Atomic replace does not follow an existing destination link. The
            # dedicated parent is protected to this user/SYSTEM by the launcher.
            temporary = parent / "mcp-health.json.tmp"
            # Exclusive creation refuses normal and dangling links atomically.
            with temporary.open("x", encoding="utf-8") as stream:
                json.dump(self.state, stream, separators=(",", ":"))
            os.replace(temporary, path)
        except (OSError, ValueError):
            pass  # Diagnostic failure never changes a read result or emits a path.
