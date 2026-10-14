"""Credential/config isolation without a control-plane request or real key."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tunnel_child", ROOT / "scripts/tunnel_mcp_child.py")
child = importlib.util.module_from_spec(spec)
spec.loader.exec_module(child)


class TunnelEnvironmentTests(unittest.TestCase):
    def test_only_runtime_basics_reach_mcp(self):
        original = {"WA_DATA_DIR": "C:/synthetic/store", "SystemRoot": "C:/Windows", "PATH": "fixed",
                    "WA_TUNNEL_API_KEY": "fixture-secret", "OPENAI_API_KEY": "fixture-secret",
                    "CONTROL_PLANE_API_KEY": "fixture-secret", "MCP_SERVER_URL": "poison",
                    "PYTHONPATH": "poison", "HTTP_PROXY": "poison", "UV_INDEX_URL": "poison"}
        self.assertEqual(child.clean_environment(original), {"WA_DATA_DIR": "C:/synthetic/store", "SystemRoot": "C:/Windows", "PATH": "fixed"})
        self.assertIn("WA_TUNNEL_API_KEY", original)

    def test_allowlist_is_case_insensitive(self):
        self.assertEqual(child.clean_environment({"systemroot": "fixed", "wa_tunnel_api_key": "secret"}), {"systemroot": "fixed"})
