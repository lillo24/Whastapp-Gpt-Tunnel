"""Local operator backup/restore/status engine. Never a callable MCP tool."""
import argparse
from contextlib import closing, nullcontext
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "readonly_mcp"))
from service import QueryService


def canonical(value, exists=True):
    path = Path(value)
    if not path.is_absolute() or str(path).startswith("\\\\") or path.parent == path:
        raise ValueError("Invalid local path")
    if path.resolve(strict=exists) != path.absolute():
        raise ValueError("Redirected path")
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and part.resolve() != part.absolute()):
            raise ValueError("Redirected path")
    return path


def config(path):
    path = canonical(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or set(data) != {"schema_version", "data_dir", "runtime_dir", "backup_dir", "synthetic", "task_prefix"}:
        raise ValueError("Unknown config")
    for name in ("data_dir", "runtime_dir", "backup_dir"):
        data[name] = canonical(data[name], exists=name != "backup_dir")
    if not (data["data_dir"] / ".wa-private-store").is_file():
        raise ValueError("Unknown store")
    return data


def digest(path):
    h = hashlib.sha256()
    with canonical(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def snapshot(source, destination):
    deadline = time.monotonic() + 30
    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError("Backup deadline")
    with closing(sqlite3.connect(canonical(source).as_uri() + "?mode=ro", uri=True, timeout=1)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst, pages=256, progress=progress, sleep=.05)
            if dst.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("Snapshot corrupt")


def backup(data, include_messages=False, include_session=False):
    if not include_messages and not include_session:
        return {"applied": False, "error_class": "OPT_IN_REQUIRED", "message_backup": False, "session_backup": False}
    base = canonical(data["backup_dir"])
    if (base / ".wa-backups").read_text() != "wa-operations-v1":
        raise ValueError("Unknown backup root")
    if len(list(base.glob("backup-*"))) >= 5:
        return {"applied": False, "error_class": "RETENTION_CAP_REACHED", "retention_cap": 5}
    files = (["messages.db"] if include_messages else []) + (["whatsapp.db"] if include_session else [])
    # A session+messages pair requires a stopped collector. Holding its existing
    # lock file open also prevents Go's exclusive CreateFile lock from starting.
    lock = (data["data_dir"] / "collector.lock").open("rb") if include_session else nullcontext()
    with lock:
        for name in files:
            canonical(data["data_dir"] / name)
        identifier = "backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
        directory = base / identifier
        directory.mkdir(exist_ok=False)
        entries = []
        try:
            for name in files:
                target = directory / name
                snapshot(data["data_dir"] / name, target)
                entries.append({"file": name, "sha256": digest(target), "bytes": target.stat().st_size})
            manifest = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                        "disconnected_restore_only": True, "files": entries}
            (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            return {"applied": True, "backup_id": identifier, "files": files, "retention_cap": 5, "offsite": False}
        except Exception:
            # Only files created in this fresh, canonical private snapshot are removed.
            for item in directory.iterdir():
                if item.name not in {"manifest.json", *(n + suffix for n in files for suffix in ("", "-journal", "-wal", "-shm"))}:
                    raise ValueError("Unexpected snapshot file") from None
                canonical(item).unlink()
            directory.rmdir()
            raise


def restore(data, identifier, destination, apply=False):
    if not identifier.startswith("backup-") or len(identifier) > 80 or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-TZ" for c in identifier):
        raise ValueError("Invalid backup ID")
    source = canonical(data["backup_dir"] / identifier)
    manifest = json.loads(canonical(source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("disconnected_restore_only") is not True:
        raise ValueError("Unknown backup")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 2:
        raise ValueError("Invalid snapshot set")
    names = []
    for entry in entries:
        name = entry.get("file")
        if name not in {"messages.db", "whatsapp.db"} or name in names:
            raise ValueError("Unexpected snapshot file")
        names.append(name)
        file = canonical(source / name)
        if digest(file) != entry.get("sha256") or file.stat().st_size != entry.get("bytes"):
            raise ValueError("Backup hash mismatch")
    target = canonical(destination, exists=apply)
    permitted = [ROOT / ".local-fixtures", Path(os.environ["LOCALAPPDATA"]) / "WhatsappGptTunnel/restores"]
    if not any(target != base and target.is_relative_to(base) for base in permitted):
        raise ValueError("Restore must use a disconnected dedicated test path")
    if not apply:
        if target.exists():
            raise ValueError("Restore target already exists")
        return {"applied": False, "validated": True, "files": names, "disconnected": True}
    if {item.name for item in target.iterdir()} != {".wa-restored-disconnected"}:
        raise ValueError("Restore target is not fresh")
    for name in names:
        snapshot(source / name, target / name)
    if "messages.db" in names:
        with closing(sqlite3.connect(target / "messages.db")) as db:
            if db.execute("PRAGMA user_version").fetchone() != (1,):
                raise ValueError("Unknown restored schema")
            # Preserve the historical heartbeat; restoring is not a new sync.
            db.execute("UPDATE collector_status SET linked=0, connected=0, error_class='STOPPED'")
            db.commit()
    (target / ".wa-private-store").touch(exist_ok=False)
    return {"applied": True, "files": names, "disconnected": True, "network_started": False}


def status(data):
    health = QueryService(data["data_dir"]).call("health_status")
    execution = {"last_successful_execution_at": None, "last_error_class": None}
    path = data["runtime_dir"] / "mcp-health.json"
    try:
        observed = json.loads(canonical(path).read_text())
        if observed.get("schema_version") == 1:
            for key in execution:
                value = observed.get(key)
                if key.endswith("_at"):
                    if value is not None:
                        value = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                elif value not in {None, "INVALID_FILTER", "DB_UNAVAILABLE", "NOT_LINKED", "NOT_FOUND", "UNKNOWN_ERROR"}:
                    value = "UNKNOWN_ERROR"
                execution[key] = value
    except (OSError, ValueError, TypeError):
        pass
    return {"collector": health, "mcp_execution": execution, "history_complete": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("status", "backup", "restore"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--include-messages", action="store_true")
    parser.add_argument("--include-session", action="store_true")
    parser.add_argument("--backup-id")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        data = config(args.config)
        if args.operation == "status":
            report = status(data)
        elif args.operation == "backup":
            report = backup(data, args.include_messages, args.include_session)
        else:
            report = restore(data, args.backup_id or "", args.destination, args.apply)
        print(json.dumps(report))
        return 0 if not report.get("error_class") else 1
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, TimeoutError):
        print(json.dumps({"applied": False, "error_class": "OPERATION_REFUSED", "private_details_withheld": True}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
