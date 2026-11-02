"""Installed bundles must run independently and preserve existing user content."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from install_skill import install


class InstallTest(unittest.TestCase):
    def test_installed_skill_runs_from_its_new_location(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = install(base / "中文 skills")
            result = subprocess.run([sys.executable, str(target / "scripts/check_hooks.py"),
                                     str(target / "examples/minimal-supported.json"), "--out", str(base / "report")],
                                    cwd=base, capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((base / "report/report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["findings"])
            self.assertTrue((target / "references/rule-evidence.md").is_file())

    def test_existing_skill_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "hook-portability-doctor"
            target.mkdir()
            marker = target / "custom.txt"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "未覆盖"):
                install(directory)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_install_does_not_copy_private_or_generated_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            target = install(directory)
            for name in (".git", ".work", "reports", "node_modules"):
                self.assertFalse((target / name).exists())
            self.assertFalse(list(target.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
