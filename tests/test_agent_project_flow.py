import unittest
from unittest.mock import patch

from core.agent import (
    _build_project_brief,
    _default_project_plan,
    _generate_project_plan,
    _is_project_creation_goal,
)


class AgentProjectFlowTests(unittest.TestCase):
    def test_detects_project_creation_goal(self):
        self.assertTrue(_is_project_creation_goal("Create a new project for FastAPI API"))
        self.assertTrue(_is_project_creation_goal("build app with React and Node"))
        self.assertFalse(_is_project_creation_goal("fix syntax error in core/agent.py"))

    def test_project_brief_contains_user_details(self):
        details = {
            "project_name": "demo-app",
            "technology": "FastAPI + React",
            "environment": "docker",
            "package_manager": "npm + pip",
            "features": "auth, dashboard",
            "extra": "tests and ci",
        }
        brief = _build_project_brief("Create project", details)
        self.assertIn("demo-app", brief)
        self.assertIn("FastAPI + React", brief)
        self.assertIn("tests and ci", brief)

    def test_plan_falls_back_when_planner_errors(self):
        details = {
            "project_name": "demo",
            "technology": "Python",
            "environment": "local",
            "package_manager": "pip",
            "features": "api",
            "extra": "tests",
        }
        with patch("core.agent.ask_planner", return_value="[LLM Error] timeout"):
            plan = _generate_project_plan("brief", details)
        self.assertEqual(plan, _default_project_plan(details))
        self.assertIn("1.", plan)


if __name__ == "__main__":
    unittest.main()
