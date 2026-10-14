import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("execution_health", ROOT / "readonly_mcp/execution_health.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExecutionHealthTests(unittest.TestCase):
    def test_bounded_timestamps_and_redacted_error_class(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".local-fixtures") as tmp:
            directory = Path(tmp)
            (directory / ".wa-tunnel-runtime").write_text("wa-tunnel-runtime-v1")
            health = module.ExecutionHealth(str(directory / "mcp-health.json"))
            health.record(True)
            health.record(False, "private SQL argument or content")
            data = json.loads((directory / "mcp-health.json").read_text())
            self.assertEqual(data["successful_calls"], 1)
            self.assertEqual(data["last_error_class"], "UNKNOWN_ERROR")
            self.assertTrue(data["last_successful_execution_at"].endswith("Z"))
            self.assertLess(len(json.dumps(data)), 512)
            self.assertNotIn("private SQL", json.dumps(data))
            self.assertFalse((directory / "mcp-health.json.tmp").exists())

    def test_unmarked_parent_and_other_filename_are_refused(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".local-fixtures") as tmp:
            directory = Path(tmp)
            module.ExecutionHealth(str(directory / "mcp-health.json")).record(True)
            self.assertFalse((directory / "mcp-health.json").exists())
            (directory / ".wa-tunnel-runtime").write_text("wa-tunnel-runtime-v1")
            module.ExecutionHealth(str(directory / "unrelated.txt")).record(True)
            self.assertFalse((directory / "unrelated.txt").exists())
