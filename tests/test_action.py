"""Exercise the real Action adapter, including failed-run report handling."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_action import write_outputs


def parse_outputs(path):
    lines = iter(path.read_text(encoding="utf-8").splitlines())
    values = {}
    for line in lines:
        key, delimiter = line.split("<<", 1)
        value = []
        for part in lines:
            if part == delimiter:
                break
            value.append(part)
        else:
            raise AssertionError("Unterminated GitHub output value")
        values[key] = "\n".join(value)
    return values


class ActionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hpd-action-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.input = self.base / "hooks.json"
        self.output_file = self.base / "github-output"
        self.summary_file = self.base / "github-summary"
        self.reports = self.base / "reports"

    def config(self, event="Stop", **fields):
        self.input.write_text(json.dumps({
            "hooks": {event: [{"hooks": [{"command": "echo sample", **fields}]}]},
        }), encoding="utf-8")

    def run_action(self, **overrides):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("HPD_", "GITHUB_"))}
        env.update({
            "HPD_INPUT_PATH": str(self.input),
            "HPD_OUTPUT_DIRECTORY": str(self.reports),
            "GITHUB_OUTPUT": str(self.output_file),
            "GITHUB_STEP_SUMMARY": str(self.summary_file),
            **overrides,
        })
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_action.py")],
            cwd=self.base, env=env, capture_output=True, text=True,
            encoding="utf-8", timeout=20,
        )
        return result, parse_outputs(self.output_file)

    def test_supported_configuration_exports_fresh_reports_and_summary(self):
        self.config()
        result, outputs = self.run_action()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs["status"], "no_static_differences_found")
        self.assertEqual(outputs["incompatible-count"], "0")
        report = json.loads(Path(outputs["report-json"]).read_text(encoding="utf-8"))
        self.assertFalse(report["execution_verified"])
        self.assertTrue(Path(outputs["report-markdown"]).is_file())
        self.assertIn("尚未验证", self.summary_file.read_text(encoding="utf-8"))

    def test_strict_failure_keeps_new_reports_available(self):
        self.config("PreCompact")
        result, outputs = self.run_action()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(outputs["exit-code"], "1")
        self.assertEqual(outputs["incompatible-count"], "1")
        self.assertTrue(Path(outputs["report-json"]).is_file())

    def test_report_only_mode_does_not_fail_on_incompatibilities(self):
        self.config("PreCompact")
        result, outputs = self.run_action(HPD_STRICT="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs["status"], "incompatibilities_found")

    def test_behavior_changes_do_not_fail_strict_mode(self):
        self.config(args=["ignored"])
        result, outputs = self.run_action()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs["status"], "behavior_changes_found")

    def test_invalid_input_does_not_export_a_previous_report(self):
        self.input.write_text("{", encoding="utf-8")
        self.reports.mkdir()
        stale = self.reports / "report.json"
        stale.write_text('{"old": true}', encoding="utf-8")
        result, outputs = self.run_action()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(outputs, {"exit-code": "2"})
        self.assertEqual(stale.read_text(encoding="utf-8"), '{"old": true}')
        self.assertIn("检查未完成", self.summary_file.read_text(encoding="utf-8"))

    def test_invalid_strict_is_an_error_instead_of_silent_report_mode(self):
        self.config()
        result, outputs = self.run_action(HPD_STRICT="tru")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(outputs, {"exit-code": "2"})
        self.assertFalse(self.reports.exists())

    def test_missing_input_is_an_action_error(self):
        result, outputs = self.run_action(HPD_INPUT_PATH="")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(outputs, {"exit-code": "2"})

    def test_unknown_profile_is_an_input_error(self):
        self.config()
        result, outputs = self.run_action(HPD_PROFILE="../untrusted")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(outputs, {"exit-code": "2"})

    def test_literal_paths_and_commands_are_not_executed(self):
        self.input = self.base / "中文 $(sample); hooks.json"
        self.reports = self.base / "中文 report ' space"
        marker = self.base / "must-not-exist"
        self.config(command=f'echo should-not-run > "{marker}"')
        before = self.input.read_bytes()
        result, outputs = self.run_action()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.input.read_bytes(), before)
        self.assertFalse(marker.exists())
        # Windows runners may spell the temp directory with an 8.3 path alias.
        self.assertTrue(Path(outputs["report-json"]).samefile(self.reports / "report.json"))

    def test_context_is_explicit_and_forwarded(self):
        self.config(command="node " + "$" + "{CLAUDE_PLUGIN_ROOT}/example.js")
        result, outputs = self.run_action(HPD_PLUGIN_ROOT=str(self.base))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(Path(outputs["report-json"]).read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["categories"]["configuration"], 0)
        self.assertTrue(report["context"]["plugin_root_provided"])

    def test_multiline_output_cannot_inject_another_output(self):
        malicious_path = "folder\nexit-code=0\nincompatible-count=0"
        write_outputs(self.output_file, {"report-json": malicious_path, "exit-code": 1})
        self.assertEqual(parse_outputs(self.output_file),
                         {"report-json": malicious_path, "exit-code": "1"})

    def test_option_like_missing_path_cannot_replay_an_old_report(self):
        self.reports.mkdir()
        (self.reports / "report.json").write_text(
            '{"summary":{"status":"no_static_differences_found","categories":{"incompatible":0}}}',
            encoding="utf-8",
        )
        for path in ("--version", "--help"):
            with self.subTest(path=path):
                self.output_file.unlink(missing_ok=True)
                result, outputs = self.run_action(HPD_INPUT_PATH=path)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(outputs, {"exit-code": "2"})

    def test_option_like_existing_filename_is_scanned_literally(self):
        self.input = self.base / "--version"
        self.config("PreCompact")
        result, outputs = self.run_action(HPD_INPUT_PATH="--version")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(outputs["incompatible-count"], "1")

    def test_summary_write_failure_is_reported_as_error(self):
        self.config()
        result, outputs = self.run_action(GITHUB_STEP_SUMMARY=str(self.base))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(outputs, {"exit-code": "2"})


if __name__ == "__main__":
    unittest.main()
