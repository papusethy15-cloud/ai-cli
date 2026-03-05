import unittest
from unittest.mock import patch

from services.auth_service import AuthError
from services.device_auth_service import DeviceAuthService


class DeviceAuthServiceTests(unittest.TestCase):
    def _service(self):
        return DeviceAuthService()

    def test_password_login_and_bearer_auth(self):
        service = self._service()
        with patch("services.device_auth_service.DEVICE_AUTH_ENABLED", True), patch(
            "services.device_auth_service.AUTH_USERS_JSON",
            '{"alice":{"password":"secret","scopes":["read","agent"]}}',
        ):
            payload = service.login_password("alice", "secret")
            self.assertTrue(payload["ok"])
            context = service.authenticate_access_token(payload["access_token"])
            self.assertEqual(context.user_id, "alice")
            self.assertIn("agent", context.scopes)

    def test_device_flow_end_to_end(self):
        service = self._service()
        with patch("services.device_auth_service.DEVICE_AUTH_ENABLED", True), patch(
            "services.device_auth_service.AUTH_USERS_JSON",
            '{"dev":{"password":"pw","scopes":["read","write","agent"]}}',
        ):
            started = service.start_device_authorization("aicli", "http://localhost:8787")
            self.assertTrue(started["ok"])
            self.assertIn("user_code", started)
            approved = service.approve_device_code(started["user_code"], "dev", "pw")
            self.assertEqual(approved["status"], "approved")
            tokens = service.poll_device_token(started["device_code"])
            self.assertTrue(tokens["ok"])
            self.assertIn("access_token", tokens)
            self.assertIn("refresh_token", tokens)

    def test_refresh_rotates_tokens(self):
        service = self._service()
        with patch("services.device_auth_service.DEVICE_AUTH_ENABLED", True), patch(
            "services.device_auth_service.AUTH_USERS_JSON",
            '{"bob":{"password":"pw","scopes":["read"]}}',
        ):
            first = service.login_password("bob", "pw")
            refreshed = service.refresh_access_token(first["refresh_token"])
            self.assertTrue(refreshed["ok"])
            self.assertNotEqual(first["access_token"], refreshed["access_token"])
            with self.assertRaises(AuthError):
                service.refresh_access_token(first["refresh_token"])


if __name__ == "__main__":
    unittest.main()
