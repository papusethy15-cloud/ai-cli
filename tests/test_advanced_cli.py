import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from commands.fix_project import fix_project
from utils.code_analyzer import analyze_file


class AdvancedCliTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tmp.cleanup()

    def test_analyze_file_detects_python_syntax_error(self):
        with open("broken.py", "w", encoding="utf-8") as f:
            f.write("print('hello'\n")

        result = analyze_file("broken.py", use_llm=False, refresh=True)
        issue_types = [issue["type"] for issue in result["issues"]]

        self.assertIn("syntax_error", issue_types)
        self.assertFalse(result["from_cache"])

    def test_analyze_file_uses_memory_cache_for_unchanged_file(self):
        with open("ok.py", "w", encoding="utf-8") as f:
            f.write("print('ok')\n")

        first = analyze_file("ok.py", use_llm=False, refresh=True)
        second = analyze_file("ok.py", use_llm=False, refresh=False)

        self.assertFalse(first["from_cache"])
        self.assertTrue(second["from_cache"])

    def test_fix_project_dry_run_lists_actionable_files(self):
        with open("broken.py", "w", encoding="utf-8") as f:
            f.write("print('hello'\n")

        out = io.StringIO()
        with redirect_stdout(out):
            fix_project(".", apply=False, use_llm=False, refresh=True, max_files=5)

        text = out.getvalue()
        self.assertIn("Dry-run mode", text)
        self.assertIn("Would fix: broken.py", text)


if __name__ == "__main__":
    unittest.main()
