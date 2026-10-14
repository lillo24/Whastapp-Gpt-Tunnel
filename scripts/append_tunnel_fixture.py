"""Append one invented event through Go, only to the configured synthetic fixture."""
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def append() -> dict:
    base = ROOT / ".local-fixtures"
    if base.resolve(strict=True) != base.absolute():
        raise ValueError("Redirected fixture root")
    config_path = Path(os.environ["LOCALAPPDATA"]) / "WhatsappGptTunnel/tunnel/connection.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    store = Path(config["data_dir"])
    if not store.is_absolute() or store.resolve(strict=True) != store.absolute() or not store.is_relative_to(base):
        raise ValueError("Not a canonical fixture store")
    if store.name != "go-store" or not store.parent.name.startswith("tunnel-acceptance-"):
        raise ValueError("Not the dedicated tunnel acceptance store")
    for part in (store, *store.parents):
        if part == ROOT:
            break
        if part.resolve(strict=True) != part.absolute():
            raise ValueError("Redirected fixture path")
    if not (store / ".wa-private-store").is_file():
        raise ValueError("Not a private Go store")
    message_id = "fresh-" + uuid.uuid4().hex
    marker = "tunnel-fresh-" + uuid.uuid4().hex
    proof = "arrival-proof-" + uuid.uuid4().hex
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    db_uri = (store / "messages.db").as_uri() + "?mode=ro"
    with closing(sqlite3.connect(db_uri, uri=True)) as db:
        if db.execute("SELECT synthetic FROM collector_status WHERE singleton=1").fetchone() != (1,):
            raise ValueError("Not synthetic")
        if db.execute("SELECT 1 FROM chats WHERE jid NOT LIKE 'fixture-%' LIMIT 1").fetchone():
            raise ValueError("Nonfixture chat")
        if db.execute("SELECT 1 FROM messages WHERE instr(content,?) > 0 LIMIT 1", (marker,)).fetchone():
            raise ValueError("Marker already exists")
    event = dict(id=message_id, chat_jid="fixture-alice@s.whatsapp.net", sender="fixture-alice@s.whatsapp.net",
                 chat_name="Alex (synthetic)", content=marker + " " + proof, timestamp=stamp,
                 is_from_me=0, media_type="")
    output = base / ("tunnel-append-" + uuid.uuid4().hex)
    output.mkdir(exist_ok=False)
    events = output / "events.json"
    events.write_text(json.dumps({"synthetic": True, "events": [event]}), encoding="utf-8")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    result = subprocess.run([str(ROOT / "bin/wa-bridge.exe"), "fixture", "--synthetic", "--input", str(events), "--data-dir", str(store)],
                            capture_output=True, creationflags=flags, timeout=15)
    if result.returncode != 0 or result.stdout or result.stderr:
        raise ValueError("Go fixture ingestion failed")
    with closing(sqlite3.connect(db_uri, uri=True)) as db:
        if db.execute("SELECT content,timestamp FROM messages WHERE id=? AND chat_jid=?", (message_id, event["chat_jid"])).fetchone() != (event["content"], stamp):
            raise ValueError("Append verification failed")
    report = {"synthetic": True, "query_marker": marker, "expected_message_id": message_id,
              "expected_timestamp": stamp, "expected_proof": proof, "previous_match_count": 0}
    (output / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    try:
        print(json.dumps(append(), indent=2))
    except (OSError, KeyError, ValueError, sqlite3.Error, subprocess.SubprocessError):
        print("Synthetic tunnel append refused or failed; no private data or path emitted.", file=sys.stderr)
        raise SystemExit(1)
