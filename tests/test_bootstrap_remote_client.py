import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from commands.bootstrap import bootstrap_remote_client_setup


class BootstrapRemoteClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.home = self.root / "home"
        self.cli_home = self.home / ".ai-cli"
        self.project.mkdir(parents=True, exist_ok=True)
        self.home.mkdir(parents=True, exist_ok=True)

        (self.project / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (self.project / "requirements.txt").write_text("typer\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _ok(self, *args, **kwargs):
        mocked = Mock()
        mocked.returncode = 0
        return mocked

    def test_bootstrap_writes_wrapper_rc_and_saved_remote(self):
        venv_bin = self.project / "venv" / "bin"
        venv_bin.mkdir(parents=True, exist_ok=True)
        (venv_bin / "python").write_text("", encoding="utf-8")
        (venv_bin / "pip").write_text("", encoding="utf-8")

        with patch.dict(
            os.environ,
            {"HOME": str(self.home), "SHELL": "/bin/bash"},
            clear=False,
        ), patch("commands.bootstrap.subprocess.run", side_effect=self._ok) as run_mock, patch(
            "utils.cli_config.CLI_HOME", self.cli_home
        ), patch("utils.cli_config.CLI_CONFIG_FILE", self.cli_home / "config.json"):
            bootstrap_remote_client_setup(
                base_url="http://127.0.0.1:8787",
                api_key="test-key",
                project_root=self.project,
            )
            bootstrap_remote_client_setup(
                base_url="http://127.0.0.1:8787",
                api_key="test-key",
                project_root=self.project,
            )

        commands = [c.args[0] for c in run_mock.call_args_list]
        self.assertIn(
            [
                str(self.project / "venv" / "bin" / "pip"),
                "install",
                "-r",
                str(self.project / "requirements.txt"),
            ],
            commands,
        )
        self.assertIn(
            [
                str(self.project / "venv" / "bin" / "python"),
                "-m",
                "pip",
                "install",
                "-e",
                str(self.project),
            ],
            commands,
        )

        wrapper = self.home / ".local" / "bin" / "aicli"
        self.assertTrue(wrapper.exists())
        wrapper_text = wrapper.read_text(encoding="utf-8")
        self.assertIn(str(self.project / "main.py"), wrapper_text)

        rc_path = self.home / ".bashrc"
        self.assertTrue(rc_path.exists())
        rc_text = rc_path.read_text(encoding="utf-8")
        self.assertEqual(rc_text.count('export PATH="$HOME/.local/bin:$PATH"'), 1)
        self.assertEqual(rc_text.count('export AI_CLI_REMOTE_URL="http://127.0.0.1:8787"'), 1)
        self.assertEqual(rc_text.count('export AI_CLI_REMOTE_API_KEY="test-key"'), 1)

        config = json.loads((self.cli_home / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["remote"]["base_url"], "http://127.0.0.1:8787")
        self.assertEqual(config["remote"]["api_key"], "test-key")

    def test_bootstrap_creates_venv_when_missing(self):
        with patch.dict(
            os.environ,
            {"HOME": str(self.home), "SHELL": "/bin/bash"},
            clear=False,
        ), patch("commands.bootstrap.subprocess.run", side_effect=self._ok) as run_mock:
            bootstrap_remote_client_setup(
                install_command=False,
                install_editable=False,
                project_root=self.project,
            )

        commands = [c.args[0] for c in run_mock.call_args_list]
        self.assertEqual(commands[0][:3], ["python3", "-m", "venv"])
        self.assertEqual(commands[1][1:4], ["install", "-r", str(self.project / "requirements.txt")])

    def test_bootstrap_windows_writes_cmd_wrapper_and_powershell_profile(self):
        scripts = self.project / "venv" / "Scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        (scripts / "python.exe").write_text("", encoding="utf-8")
        (scripts / "pip.exe").write_text("", encoding="utf-8")

        with patch.dict(
            os.environ,
            {"HOME": str(self.home)},
            clear=False,
        ), patch("commands.bootstrap._is_windows", return_value=True), patch(
            "commands.bootstrap.subprocess.run", side_effect=self._ok
        ) as run_mock, patch("utils.cli_config.CLI_HOME", self.cli_home), patch(
            "utils.cli_config.CLI_CONFIG_FILE", self.cli_home / "config.json"
        ):
            bootstrap_remote_client_setup(
                base_url="http://127.0.0.1:8787",
                api_key="windows-key",
                project_root=self.project,
            )
            bootstrap_remote_client_setup(
                base_url="http://127.0.0.1:8787",
                api_key="windows-key",
                project_root=self.project,
            )

        commands = [c.args[0] for c in run_mock.call_args_list]
        self.assertIn(
            [
                str(self.project / "venv" / "Scripts" / "pip.exe"),
                "install",
                "-r",
                str(self.project / "requirements.txt"),
            ],
            commands,
        )
        self.assertIn(
            [
                str(self.project / "venv" / "Scripts" / "python.exe"),
                "-m",
                "pip",
                "install",
                "-e",
                str(self.project),
            ],
            commands,
        )

        wrapper = self.home / ".local" / "bin" / "aicli.cmd"
        self.assertTrue(wrapper.exists())
        wrapper_text = wrapper.read_text(encoding="utf-8")
        self.assertIn(str(self.project / "main.py"), wrapper_text)

        profile = self.home / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        self.assertTrue(profile.exists())
        profile_text = profile.read_text(encoding="utf-8")
        self.assertEqual(profile_text.count("# >>> AI_CLI_BOOTSTRAP >>>"), 1)
        self.assertIn('$env:AI_CLI_REMOTE_URL = "http://127.0.0.1:8787"', profile_text)
        self.assertIn('$env:AI_CLI_REMOTE_API_KEY = "windows-key"', profile_text)


if __name__ == "__main__":
    unittest.main()
