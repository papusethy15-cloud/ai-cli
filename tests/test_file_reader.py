import os
import tempfile
import unittest

from utils.file_reader import FileReadError, read_file


class FileReaderTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tmp.cleanup()

    def test_read_file_success_and_truncate(self):
        with open("sample.txt", "w", encoding="utf-8") as f:
            f.write("abcdef")

        self.assertEqual(read_file("sample.txt"), "abcdef")
        self.assertEqual(read_file("sample.txt", max_chars=3), "abc")

    def test_read_file_missing_path_raises(self):
        with self.assertRaises(FileReadError) as ctx:
            read_file("missing.txt")
        self.assertIn("File not found", str(ctx.exception))

    def test_read_file_directory_path_raises(self):
        os.makedirs("folder", exist_ok=True)
        with self.assertRaises(FileReadError) as ctx:
            read_file("folder")
        self.assertIn("Path is not a file", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
