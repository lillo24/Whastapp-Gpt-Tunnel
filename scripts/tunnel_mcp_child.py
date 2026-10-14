"""Fixed stdio launcher: remove tunnel credentials before UV or MCP starts."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SAFE_NAMES = frozenset(name.casefold() for name in (
    "SystemRoot", "WINDIR", "SystemDrive", "COMSPEC", "USERPROFILE", "LOCALAPPDATA",
    "APPDATA", "TEMP", "TMP", "HOMEDRIVE", "HOMEPATH", "USERNAME", "USERDOMAIN",
    "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PATHEXT", "PATH", "WA_DATA_DIR", "WA_MCP_HEALTH_FILE",
))


def clean_environment(source: dict[str, str]) -> dict[str, str]:
    return {name: value for name, value in source.items() if name.casefold() in SAFE_NAMES}


def main() -> int:
    env = clean_environment(dict(os.environ))
    # The trusted launcher briefly inherits the client's environment; clear it
    # before starting UV. Neither UV nor the read-only server receives the key.
    os.environ.clear()
    os.environ.update(env)
    command = [str(ROOT / ".tools/uv/uv.exe"), "--directory", str(ROOT / "readonly_mcp"),
               "run", "--locked", "--offline", "--no-sync", "python", "main_readonly.py"]
    child = None
    try:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=sys.stdin.buffer,
                                 stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)
        return child.wait()
    except (OSError, KeyboardInterrupt):
        sys.stderr.write("MCP_LAUNCH_UNAVAILABLE\n")
        return 1
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
