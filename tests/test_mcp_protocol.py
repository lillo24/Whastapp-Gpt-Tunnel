"""Official SDK and raw JSON-RPC tests over real local stdio processes."""
import asyncio
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "readonly_mcp"))
sys.path.insert(0, str(ROOT / "scripts"))
from contracts import MAX_PAYLOAD, TOOLS
from generate_synthetic_fixture import generate, synthetic_events

FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        base = ROOT / ".local-fixtures"
        base.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="mcp-protocol-", dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = self.root / "go-store"
        self.events = self.root / "events.json"
        self.events.write_text(json.dumps({"synthetic": True, "events": synthetic_events()}), encoding="utf-8")
        self.ingest()

    def ingest(self):
        result = subprocess.run([str(ROOT / "bin/wa-bridge.exe"), "fixture", "--synthetic", "--input", str(self.events), "--data-dir", str(self.store)], capture_output=True, creationflags=FLAGS, timeout=15)
        self.assertEqual(result.returncode, 0, "Go synthetic collector failed")
        self.assertFalse(result.stdout or result.stderr)

    async def test_go_sqlite_mcp_pipeline_and_live_append(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        (runtime / ".wa-tunnel-runtime").write_text("wa-tunnel-runtime-v1")
        config = StdioServerParameters(command=str(ROOT / "readonly_mcp/.venv/Scripts/python.exe"),
            args=["-I", str(ROOT / "scripts/tunnel_mcp_child.py")],
            env={"WA_DATA_DIR": str(self.store), "WA_MCP_HEALTH_FILE": str(runtime / "mcp-health.json"), "WA_TUNNEL_API_KEY": "fixture-do-not-forward",
                 "MCP_SERVER_URL": "http://example.invalid/poison", "PYTHONPATH": "invalid-fixture-path"}, cwd=ROOT)
        with open(os.devnull, "w") as errlog:
            async with stdio_client(config, errlog=errlog) as streams:
                reader, writer = streams
                async with ClientSession(reader, writer, read_timeout_seconds=10) as client:
                    await client.initialize()
                    tools = await client.list_tools()
                    self.assertEqual({tool.name for tool in tools.tools}, set(TOOLS))
                    for tool in tools.tools:
                        self.assertTrue(tool.annotations.read_only_hint)
                        self.assertFalse(tool.annotations.destructive_hint)
                        self.assertFalse(tool.annotations.open_world_hint)
                        self.assertIn("untrusted", tool.description)
                    answer = await client.call_tool("list_messages", {"query": "Caffè"})
                    data = answer.structured_content
                    self.assertTrue(data["ok"])
                    self.assertEqual(len(data["data"]), 1)
                    self.assertEqual(data["data"][0]["message_id"], "tie-a")
                    self.assertLess(len(answer.model_dump_json(by_alias=True).encode()), MAX_PAYLOAD)
                    none = await client.call_tool("list_messages", {"query": "newly-collected-fixture"})
                    self.assertEqual(none.structured_content["data"], [])
                    events = synthetic_events()
                    events.append(dict(events[0], id="newly-ingested", content="newly-collected-fixture", timestamp="2024-03-03T00:00:00.000000Z"))
                    self.events.write_text(json.dumps({"synthetic": True, "events": events}), encoding="utf-8")
                    self.ingest()
                    new = await client.call_tool("list_messages", {"query": "newly-collected-fixture"})
                    self.assertEqual(new.structured_content["data"][0]["message_id"], "newly-ingested")
                    observed = json.loads((runtime / "mcp-health.json").read_text())
                    self.assertEqual(observed["successful_calls"], 3)
                    self.assertNotIn("newly-collected", json.dumps(observed))
                    for name in ("send_message", "send_file", "download_media", "execute_sql"):
                        rejected = await client.call_tool(name, {"private-marker": "secret-fixture"})
                        self.assertTrue(rejected.is_error)
                        self.assertNotIn("secret-fixture", rejected.model_dump_json())
                    print("tools/list names: " + ", ".join(tool.name for tool in tools.tools))

    async def test_raw_jsonrpc_stdout_and_clean_eof_with_closed_stderr(self):
        # The SDK supports older handshake clients too. Close fd2 deliberately.
        code = "import os,runpy; os.close(2); runpy.run_path('main_readonly.py',run_name='__main__')"
        proc = subprocess.Popen([sys.executable, "-c", code], cwd=ROOT / "readonly_mcp",
            env={**os.environ, "WA_DATA_DIR": str(self.store)}, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=FLAGS)
        messages = queue.Queue()

        def collect():
            for line in proc.stdout:
                messages.put(line)
        worker = threading.Thread(target=collect, daemon=True)
        worker.start()

        def request(payload):
            proc.stdin.write((json.dumps(payload) + "\n").encode())
            proc.stdin.flush()
            while True:
                line = messages.get(timeout=10)
                response = json.loads(line)
                self.assertEqual(response.get("jsonrpc"), "2.0")
                if response.get("id") == payload.get("id"):
                    return response
        try:
            response = await asyncio.to_thread(request, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "synthetic-test", "version": "1"}}})
            self.assertIn("result", response)
            proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            proc.stdin.flush()
            response = await asyncio.to_thread(request, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            self.assertEqual({t["name"] for t in response["result"]["tools"]}, set(TOOLS))
            for i in range(3, 6):
                response = await asyncio.to_thread(request, {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": "health_status", "arguments": {}}})
                self.assertTrue(response["result"]["structuredContent"]["ok"])
                self.assertLess(len(json.dumps(response).encode()), MAX_PAYLOAD)
            malformed = await asyncio.to_thread(request, {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "list_messages", "arguments": "private-fixture-marker"}})
            self.assertIn("error", malformed)
            self.assertNotIn("private-fixture-marker", json.dumps(malformed))
            proc.stdin.close()
            await asyncio.to_thread(proc.wait, 10)
            self.assertEqual(proc.returncode, 0)
            worker.join(timeout=2)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
            proc.stdout.close()
            if not proc.stdin.closed:
                proc.stdin.close()


if __name__ == "__main__":
    unittest.main()
