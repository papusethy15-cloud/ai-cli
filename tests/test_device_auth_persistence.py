import os
import tempfile
import unittest
from unittest.mock import patch

from services.device_auth_service import DeviceAuthService


class DeviceAuthPersistenceTests(unittest.TestCase):
    def test_tokens_survive_service_restart_with_same_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "auth_state.db")

            with patch("services.device_auth_service.DEVICE_AUTH_ENABLED", True), patch(
                "services.device_auth_service.AUTH_USERS_JSON",
                '{"alice":{"password":"pw","scopes":["read","write"]}}',
            ):
                service_one = DeviceAuthService(
                    persist_enabled=True,
                    state_db_path=db_path,
                )
                payload = service_one.login_password("alice", "pw")
                access_token = payload["access_token"]

                service_two = DeviceAuthService(
                    persist_enabled=True,
                    state_db_path=db_path,
                )
                context = service_two.authenticate_access_token(access_token)
                self.assertEqual(context.user_id, "alice")
                self.assertIn("write", context.scopes)


if __name__ == "__main__":
    unittest.main()
