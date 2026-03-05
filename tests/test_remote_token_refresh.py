import unittest
from unittest.mock import Mock, patch

from commands.remote import _request


def _resp(code, body):
    mocked = Mock()
    mocked.status_code = code
    mocked.json.return_value = body
    mocked.text = str(body)
    return mocked


class RemoteTokenRefreshTests(unittest.TestCase):
    def test_request_refreshes_and_retries_on_401(self):
        responses = [
            _resp(401, {"detail": "expired"}),
            _resp(
                200,
                {
                    "ok": True,
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "access_expires_at": 9999999999,
                    "user": {"id": "u1", "scopes": ["read"]},
                },
            ),
            _resp(200, {"ok": True, "status": "healthy"}),
        ]

        with patch(
            "commands.remote._effective_remote",
            return_value={
                "base_url": "http://localhost:8787",
                "api_key": "",
                "access_token": "old-access",
                "refresh_token": "old-refresh",
                "access_expires_at": 1,
                "auth_user_id": "u1",
                "auth_scopes": ["read"],
            },
        ), patch("commands.remote.requests.request", side_effect=responses), patch(
            "commands.remote.set_saved_remote_tokens"
        ) as save_tokens, patch(
            "commands.remote.set_saved_remote"
        ):
            result = _request("GET", "/health")

        self.assertEqual(result, {"ok": True, "status": "healthy"})
        self.assertTrue(save_tokens.called)


if __name__ == "__main__":
    unittest.main()
