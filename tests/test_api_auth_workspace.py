import unittest
from unittest.mock import patch

from fastapi import HTTPException

import api.server as server
from services.auth_service import AuthContext, AuthError
from utils.path_guard import WorkspacePathError


def _ctx(scopes):
    return AuthContext(user_id="u1", scopes=set(scopes), token_source="test")


class ApiAuthWorkspaceTests(unittest.TestCase):
    def test_auth_guard_maps_auth_error_to_http_exception(self):
        with patch(
            "api.server.authenticate_api_key",
            side_effect=AuthError(status_code=401, message="Invalid API key."),
        ):
            with self.assertRaises(HTTPException) as ctx:
                server._auth_guard(x_api_key="bad")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_auth_guard_returns_context_on_success(self):
        with patch("api.server.authenticate_api_key", return_value=_ctx(["read"])):
            context = server._auth_guard(x_api_key="ok")
        self.assertEqual(context.user_id, "u1")

    def test_auth_guard_uses_bearer_token(self):
        with patch("api.server.device_auth_service.authenticate_access_token", return_value=_ctx(["read"])):
            context = server._auth_guard(authorization="Bearer token-1", x_api_key=None)
        self.assertEqual(context.user_id, "u1")

    def test_scope_dependency_blocks_missing_scope(self):
        dependency = server._require_scope("write")
        with self.assertRaises(HTTPException) as ctx:
            dependency(context=_ctx(["read"]))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_scope_dependency_allows_matching_scope(self):
        dependency = server._require_scope("read")
        context = dependency(context=_ctx(["read"]))
        self.assertEqual(context.user_id, "u1")

    def test_safe_path_blocks_outside_workspace(self):
        with self.assertRaises(WorkspacePathError):
            server._safe_path("../outside", require_exists=False)


if __name__ == "__main__":
    unittest.main()
