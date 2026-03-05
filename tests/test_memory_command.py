import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from commands.memory import memory_command
from utils.analysis_memory import save_memory


class MemoryCommandTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tmp.cleanup()

    def test_stats_and_show(self):
        save_memory(
            {
                "version": 1,
                "files": {
                    "a.py": {
                        "hash": "x",
                        "use_llm": False,
                        "updated_at": "2026-01-01T00:00:00+00:00",
                        "analysis": {"issues": []},
                    },
                    "b.py": {
                        "hash": "y",
                        "use_llm": True,
                        "updated_at": "2026-01-02T00:00:00+00:00",
                        "analysis": {"issues": [{"severity": "warning"}]},
                    },
                },
            }
        )

        out = io.StringIO()
        with redirect_stdout(out):
            memory_command("stats")
            memory_command("show", limit=2)

        text = out.getvalue()
        self.assertIn("Cached files: 2", text)
        self.assertIn("LLM analyses: 1", text)
        self.assertIn("b.py", text)

    def test_clear_requires_yes(self):
        save_memory({"version": 1, "files": {"a.py": {"analysis": {"issues": []}}}})

        out = io.StringIO()
        with redirect_stdout(out):
            memory_command("clear", yes=False)
            memory_command("clear", yes=True)
            memory_command("stats")

        text = out.getvalue()
        self.assertIn("Refusing to clear memory without --yes.", text)
        self.assertIn("Memory cache cleared.", text)
        self.assertIn("Cached files: 0", text)


if __name__ == "__main__":
    unittest.main()
