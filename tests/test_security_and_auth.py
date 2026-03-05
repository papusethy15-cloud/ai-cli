import unittest
from unittest.mock import patch

from services.auth_service import AuthContext, AuthError, authenticate_api_key, has_scope
from utils.path_guard import WorkspacePathError, resolve_in_workspace
from utils.shell_runner import run_shell


class AuthServiceTests(unittest.TestCase):
    def test_auth_fails_when_not_configured(self):
        with patch("services.auth_service.API_KEY", ""), patch(
            "services.auth_service.AUTH_TOKENS_JSON", ""
        ), patch("services.auth_service.ALLOW_NO_AUTH", False):
            with self.assertRaises(AuthError) as ctx:
                authenticate_api_key(None)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_allow_no_auth_returns_anonymous(self):
        with patch("services.auth_service.API_KEY", ""), patch(
            "services.auth_service.AUTH_TOKENS_JSON", ""
        ), patch("services.auth_service.ALLOW_NO_AUTH", True):
            context = authenticate_api_key(None)
        self.assertEqual(context.user_id, "anonymous")

    def test_json_tokens_support_scopes(self):
        with patch("services.auth_service.API_KEY", ""), patch(
            "services.auth_service.AUTH_TOKENS_JSON",
            '{"token-read":{"user_id":"reader","scopes":["read"]}}',
        ), patch("services.auth_service.ALLOW_NO_AUTH", False):
            context = authenticate_api_key("token-read")
        self.assertEqual(context.user_id, "reader")
        self.assertTrue(has_scope(context, "read"))
        self.assertFalse(has_scope(context, "write"))


class WorkspaceGuardTests(unittest.TestCase):
    def test_blocks_path_outside_workspace(self):
        with self.assertRaises(WorkspacePathError):
            resolve_in_workspace("../outside.py", workspace_root=".")

    def test_allows_relative_path_inside_workspace(self):
        safe_path = resolve_in_workspace("README.md", workspace_root=".")
        self.assertTrue(safe_path.endswith("README.md"))


class ShellRunnerSafetyTests(unittest.TestCase):
    def test_blocks_shell_operators(self):
        result = run_shell("echo hi && ls")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "blocked_command")

    def test_blocks_unknown_command(self):
        result = run_shell("unknown_command_name_xyz")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "blocked_command")


if __name__ == "__main__":
    unittest.main()
