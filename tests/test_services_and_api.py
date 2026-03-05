import os
import tempfile
import unittest
from unittest.mock import patch

from services.analyze_service import run_analysis
from services.agent_service import run_agent_goal
from services.fix_service import run_file_fix, run_project_fix
from services.memory_service import clear_memory, get_memory_stats


class ServiceLayerTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tmp.cleanup()

    def test_run_analysis_handles_missing_path(self):
        result = run_analysis("missing_path", use_llm=False, refresh=True)
        self.assertFalse(result["ok"])
        self.assertIn("Path not found", result["error"])

    def test_run_project_fix_dry_run(self):
        with open("broken.py", "w", encoding="utf-8") as f:
            f.write("print('x'\n")

        result = run_project_fix(".", apply=False, use_llm=False, refresh=True, max_files=5)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "dry_run_ready")
        self.assertGreaterEqual(result["summary"]["selected"], 1)

    def test_run_file_fix_preview_with_mocked_llm(self):
        with open("sample.py", "w", encoding="utf-8") as f:
            f.write("print('a')\n")

        with patch("services.fix_service.ask_llm", return_value="print('b')\n"):
            result = run_file_fix("sample.py", apply=False, refresh=True)

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "preview")
        self.assertIn("print('b')", result["fixed_code"])

    def test_memory_service_clear_flow(self):
        stats_before = get_memory_stats()
        self.assertIn("cached_files", stats_before)

        denied = clear_memory(yes=False)
        self.assertFalse(denied["ok"])
        cleared = clear_memory(yes=True)
        self.assertTrue(cleared["ok"])

    def test_agent_service_emits_progress_events(self):
        events = []
        with patch("services.agent_service.analyze_project_issues", return_value=[]), patch(
            "services.agent_service.scan_project", return_value=[]
        ), patch("services.agent_service.ask_coder", return_value="[]"):
            result = run_agent_goal("Create simple app", on_event=events.append)

        self.assertTrue(result["ok"])
        event_types = [event.get("type") for event in events]
        self.assertIn("agent_started", event_types)
        self.assertIn("step_started", event_types)
        self.assertIn("agent_finished", event_types)


class ApiContractTests(unittest.TestCase):
    def test_api_app_contains_expected_routes(self):
        try:
            import api.server as server
        except Exception:
            self.skipTest("FastAPI server module not available in this environment")

        app = server.create_app()
        route_paths = {route.path for route in app.routes}
        self.assertIn("/health", route_paths)
        self.assertIn("/auth/login", route_paths)
        self.assertIn("/auth/device/start", route_paths)
        self.assertIn("/auth/device/verify", route_paths)
        self.assertIn("/auth/device/token", route_paths)
        self.assertIn("/auth/refresh", route_paths)
        self.assertIn("/auth/logout", route_paths)
        self.assertIn("/auth/whoami", route_paths)
        self.assertIn("/analyze", route_paths)
        self.assertIn("/fix/file", route_paths)
        self.assertIn("/fix/project", route_paths)
        self.assertIn("/agent/run", route_paths)
        self.assertIn("/jobs/{job_id}/events", route_paths)
        self.assertIn("/jobs/{job_id}/stream", route_paths)


if __name__ == "__main__":
    unittest.main()
