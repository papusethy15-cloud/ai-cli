import os
import tempfile
import unittest

from utils.file_editor import edit_file
from utils.file_writer import write_file
from utils.project_scanner import list_project_files, scan_project
from utils.shell_runner import run_shell


class UtilsIoAndScanTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tmp.cleanup()

    def test_write_and_edit_file(self):
        self.assertTrue(write_file("src/app.py", "print('a')\n"))
        self.assertTrue(edit_file("src/app.py", "print('b')\n"))

        with open("src/app.py", "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "print('b')\n")

        self.assertFalse(edit_file("src/missing.py", "x"))

    def test_scanner_excludes_venv_and_matches_extensions_case_insensitive(self):
        os.makedirs("venv", exist_ok=True)
        os.makedirs("pkg", exist_ok=True)

        with open("venv/skip.py", "w", encoding="utf-8") as f:
            f.write("print('skip')\n")
        with open("pkg/main.PY", "w", encoding="utf-8") as f:
            f.write("print('ok')\n")

        files = list_project_files(".")
        self.assertTrue(any(path.endswith("pkg/main.PY") for path in files))
        self.assertFalse(any(path.endswith("venv/skip.py") for path in files))

        scanned = scan_project(".")
        scanned_paths = {item["path"] for item in scanned}
        self.assertTrue(any(path.endswith("pkg/main.PY") for path in scanned_paths))

    def test_shell_runner_returns_structured_result(self):
        result = run_shell("printf ok")
        self.assertTrue(result["ok"])
        self.assertEqual(result["returncode"], 0)
        self.assertIn("ok", result["stdout"])

        empty = run_shell("")
        self.assertFalse(empty["ok"])
        self.assertEqual(empty["error"], "empty_command")


if __name__ == "__main__":
    unittest.main()
