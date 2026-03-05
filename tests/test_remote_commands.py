import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from commands.remote import _request, remote_health, remote_job_stream


class RemoteCommandTests(unittest.TestCase):
    def test_request_handles_http_error(self):
        mocked = Mock()
        mocked.status_code = 500
        mocked.json.return_value = {"detail": "boom"}
        mocked.text = "boom"

        with patch("commands.remote.requests.request", return_value=mocked):
            out = io.StringIO()
            with redirect_stdout(out):
                result = _request("GET", "/health")
        self.assertIsNone(result)
        self.assertIn("HTTP 500", out.getvalue())

    def test_remote_health_prints_json_on_success(self):
        mocked = Mock()
        mocked.status_code = 200
        mocked.json.return_value = {"ok": True}
        mocked.text = '{"ok": true}'

        with patch("commands.remote.requests.request", return_value=mocked):
            out = io.StringIO()
            with redirect_stdout(out):
                remote_health(base_url="http://localhost:8787", api_key="")
        self.assertIn('"ok": true', out.getvalue().lower())

    def test_remote_job_stream_prints_events(self):
        class FakeStreamResponse:
            status_code = 200
            text = ""

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def iter_lines(self, decode_unicode=True):
                yield 'data: {"seq":1,"event":{"type":"step_started"}}'
                yield ""
                yield 'data: {"type":"stream_end","status":"done"}'

        with patch("commands.remote.requests.get", return_value=FakeStreamResponse()):
            out = io.StringIO()
            with redirect_stdout(out):
                remote_job_stream("job-1", base_url="http://localhost:8787", api_key="")
        text = out.getvalue()
        self.assertIn('"step_started"', text)
        self.assertIn('"stream_end"', text)


if __name__ == "__main__":
    unittest.main()
