"""Read pinned source as data; never import, build, or execute upstream code."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PIN = json.loads((ROOT / "audit/upstream-pin.json").read_text(encoding="utf-8"))
INPUTS = (
    "LICENSE",
    "whatsapp-bridge/go.mod",
    "whatsapp-bridge/go.sum",
    "whatsapp-mcp-server/pyproject.toml",
    "whatsapp-mcp-server/uv.lock",
    "whatsapp-mcp-server/.python-version",
)
RULES = {
    "go_send_calls": ("whatsapp-bridge/main.go", r"client\.SendMessage\("),
    "go_upload_calls": ("whatsapp-bridge/main.go", r"client\.Upload\("),
    "go_download_calls": ("whatsapp-bridge/main.go", r"client\.Download\("),
    "go_http_handlers": ("whatsapp-bridge/main.go", r"http\.HandleFunc\("),
    "go_listeners": ("whatsapp-bridge/main.go", r"http\.ListenAndServe\("),
    "go_file_reads": ("whatsapp-bridge/main.go", r"os\.ReadFile\("),
    "go_file_writes": ("whatsapp-bridge/main.go", r"os\.(?:WriteFile|MkdirAll)\("),
    "go_logs": ("whatsapp-bridge/main.go", r"(?:fmt\.Print|logger\.\w+f|waLog\.Stdout)"),
    "go_pairing": ("whatsapp-bridge/main.go", r"GetQRChannel|GenerateHalfBlock"),
    "go_db_mutations": ("whatsapp-bridge/main.go", r"CREATE TABLE|INSERT OR REPLACE|UPDATE messages"),
    "python_http_posts": ("whatsapp-mcp-server/whatsapp.py", r"requests\.post\("),
    "python_db_connections": ("whatsapp-mcp-server/whatsapp.py", r"sqlite3\.connect\("),
    "python_logs": ("whatsapp-mcp-server/whatsapp.py", r"print\("),
    "audio_process_execution": ("whatsapp-mcp-server/audio.py", r"subprocess\.run\("),
    "audio_filesystem": ("whatsapp-mcp-server/audio.py", r"os\.(?:makedirs|unlink)|NamedTemporaryFile"),
}


def git(source: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(source), *args], capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError("Audit Git read failed; check the pinned source checkout.")
    return result.stdout


def source_bytes(source: Path, path: str) -> bytes:
    return git(source, "show", f"{PIN['commit']}:{path}")


def collect(source: Path) -> dict:
    if git(source, "rev-parse", "HEAD").decode().strip() != PIN["commit"]:
        raise ValueError("Source pin mismatch.")
    if git(source, "status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("Audit source is dirty.")
    paths = set(INPUTS) | {path for path, _ in RULES.values()} | {"whatsapp-mcp-server/main.py"}
    contents = {path: source_bytes(source, path) for path in paths}
    findings = {}
    for rule, (path, pattern) in RULES.items():
        findings[rule] = {
            "path": path,
            "lines": [i for i, line in enumerate(contents[path].decode().splitlines(), 1) if re.search(pattern, line)],
        }
    tree = ast.parse(contents["whatsapp-mcp-server/main.py"].decode())
    tools = [node.name for node in tree.body if isinstance(node, ast.FunctionDef) and any(
        isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
        and isinstance(d.func.value, ast.Name) and d.func.value.id == "mcp"
        and d.func.attr == "tool" for d in node.decorator_list
    )]
    return {
        "commit": PIN["commit"],
        "dependency_sha256": {path: hashlib.sha256(contents[path]).hexdigest() for path in INPUTS},
        "reviewed_source_sha256": {path: hashlib.sha256(contents[path]).hexdigest() for path in sorted(paths)},
        "registered_tools": tools,
        "findings": findings,
        "scope": "Application source at pin; transitive protocol internals are not proven safe by this scan.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-inputs", action="store_true", help="Create immutable dependency evidence; refuse differences.")
    args = parser.parse_args()
    source = ROOT / PIN["source_directory"]
    try:
        report = collect(source)
        evidence = ROOT / "audit/upstream-audit.json"
        if args.archive_inputs:
            files = {ROOT / PIN["dependency_directory"] / p: source_bytes(source, p) for p in INPUTS}
            files[evidence] = (json.dumps(report, indent=2) + "\n").encode()
            # Check every destination before creating any new evidence.
            for path, data in files.items():
                if path.exists() and path.read_bytes() != data:
                    raise ValueError("Existing audit evidence differs; review changes before replacing it.")
            for path, data in files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    with path.open("xb") as stream:
                        stream.write(data)
        else:
            expected = json.loads(evidence.read_text(encoding="utf-8"))
            if expected != report:
                raise ValueError("Source scan differs from archived evidence.")
            for path, expected_hash in report["dependency_sha256"].items():
                data = (ROOT / PIN["dependency_directory"] / path).read_bytes()
                if hashlib.sha256(data).hexdigest() != expected_hash:
                    raise ValueError("Archived dependency input differs from source.")
        print(json.dumps({
            "commit": report["commit"], "registered_tools": report["registered_tools"],
            "findings": {name: len(item["lines"]) for name, item in report["findings"].items()},
            "result": "PASS", "upstream_executed": False,
        }, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        # Only fixed audit errors; never echo upstream stderr or file contents.
        print("Audit failed: " + (str(exc) if isinstance(exc, ValueError) else "required evidence is unavailable."), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
