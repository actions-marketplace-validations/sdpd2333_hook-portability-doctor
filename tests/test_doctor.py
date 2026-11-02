"""Behavioral checks for target semantics, reporting, and CLI isolation."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hook_doctor.analyzer import analyze, load_profile
from hook_doctor.loader import InputError, load_document
from hook_doctor.report import render_markdown, write_reports


def config(event="Stop", handler=None, **group_fields):
    handler = {"type": "command", "command": "echo example"} if handler is None else handler
    return {"hooks": {event: [{"hooks": [handler], **group_fields}]}}


class DoctorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hook-doctor-")
        self.base = Path(self.temp.name)
        self.path = self.base / "input.json"

    def tearDown(self):
        self.temp.cleanup()

    def document(self, value, *, path=None):
        path = path or self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return load_document(path)

    def inspect(self, value, **context):
        return analyze(self.document(value), **context)

    def rules(self, result, name):
        return [item for item in result["findings"] if item["rule_id"] == name]

    def cli(self, *arguments, cwd=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_hooks.py"), *map(str, arguments)],
            cwd=cwd or self.base, capture_output=True, text=True, encoding="utf-8", timeout=15,
        )

    def test_supported_command_is_not_a_runtime_guarantee(self):
        result = self.inspect(config())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"]["status"], "no_static_differences_found")
        self.assertFalse(result["execution_verified"])
        self.assertFalse(result["target_runtime_verified"])

    def test_wrapped_and_bare_have_same_semantics(self):
        wrapped = self.inspect(config("PreCompact"))
        bare = self.inspect(config("PreCompact")["hooks"])
        self.assertEqual(wrapped["summary"], bare["summary"])
        self.assertEqual(wrapped["findings"][0]["pointer"], "/hooks/PreCompact")
        self.assertEqual(bare["findings"][0]["pointer"], "/PreCompact")

    def test_empty_hooks_are_not_a_successful_compatibility_check(self):
        result = self.inspect({"hooks": {}})
        self.assertEqual(result["summary"]["status"], "no_hooks")

    def test_empty_supported_event_has_no_handlers(self):
        result = self.inspect({"hooks": {"Stop": []}})
        self.assertEqual(result["summary"]["status"], "no_handlers")

    def test_empty_unsupported_event_does_not_fail_strict_compatibility(self):
        result = self.inspect({"hooks": {"PreCompact": []}})
        self.assertEqual(result["summary"]["categories"]["incompatible"], 0)

    def test_settings_without_hooks_does_not_treat_preferences_as_events(self):
        doc = self.document({"model": "example", "permissions": {}}, path=self.base / "settings.json")
        self.assertEqual(analyze(doc)["summary"]["status"], "no_hooks")

    def test_invalid_json_has_location(self):
        self.path.write_text('{"hooks": ', encoding="utf-8")
        with self.assertRaisesRegex(InputError, "第 1 行"):
            load_document(self.path)

    def test_root_and_hooks_must_be_objects(self):
        for value in ([], None, True, {"hooks": []}):
            with self.subTest(value=value), self.assertRaises(InputError):
                self.document(value)

    def test_duplicate_keys_are_rejected(self):
        self.path.write_text('{"hooks": {}, "hooks": {}}', encoding="utf-8")
        with self.assertRaisesRegex(InputError, "重复键"):
            load_document(self.path)

    def test_non_json_constants_are_rejected(self):
        self.path.write_text('{"hooks": {"Stop": NaN}}', encoding="utf-8")
        with self.assertRaises(InputError):
            load_document(self.path)

    def test_unsupported_event_skips_bad_nested_entries(self):
        result = self.inspect({"hooks": {"PreCompact": [None, {"hooks": [False]}]}})
        self.assertEqual([f["rule_id"] for f in result["findings"]], ["HP001"])

    def test_noncommand_is_skipped_without_inspecting_its_fields(self):
        result = self.inspect(config(handler={"type": "prompt", "async": True, "prompt": "sample"}))
        self.assertEqual([f["rule_id"] for f in result["findings"]], ["HP002"])
        self.assertEqual(result["summary"]["candidate_command_handlers"], 0)

    def test_missing_or_nonstring_type_defaults_to_command(self):
        for handler in ({"command": "echo ok"}, {"type": None, "command": "echo ok"}):
            with self.subTest(handler=handler):
                self.assertEqual(self.inspect(config(handler=handler))["findings"], [])

    def test_empty_string_type_is_not_defaulted(self):
        self.assertTrue(self.rules(self.inspect(config(handler={"type": "", "command": "echo ok"})), "HP002"))

    def test_malformed_groups_and_commands_are_local_findings(self):
        value = {"hooks": {"Stop": [None, {"hooks": [None, {"command": 7}, {"command": "echo ok"}]}]}}
        result = self.inspect(value)
        self.assertEqual(len(self.rules(result, "HP007")), 3)
        self.assertEqual(result["summary"]["candidate_command_handlers"], 1)

    def test_async_true_changes_behavior_but_false_does_not(self):
        active = self.inspect(config(handler={"command": "echo ok", "async": True}))
        inactive = self.inspect(config(handler={"command": "echo ok", "async": False}))
        self.assertEqual(active["summary"]["categories"]["behavior_change"], 1)
        self.assertEqual(inactive["findings"], [])

    def test_invalid_boolean_is_unknown_intent(self):
        result = self.inspect(config(handler={"command": "echo ok", "async": "false"}))
        self.assertEqual(result["summary"]["categories"]["behavior_change"], 0)
        self.assertTrue(self.rules(result, "HP008"))

    def test_empty_args_do_not_create_spurious_difference(self):
        self.assertEqual(self.inspect(config(handler={"command": "echo ok", "args": []}))["findings"], [])
        self.assertTrue(self.rules(self.inspect(config(handler={"command": "echo ok", "args": ["--help"]})), "HP003"))

    def test_timeout_boolean_is_not_a_javascript_number(self):
        result = self.inspect(config(handler={"command": "echo ok", "timeout": True}))
        self.assertTrue(self.rules(result, "HP003"))

    def test_large_integer_timeout_does_not_crash(self):
        result = self.inspect(config(handler={"command": "echo ok", "timeout": 10 ** 400}))
        self.assertEqual(result["summary"]["candidate_command_handlers"], 1)

    def test_stop_matcher_is_discarded_not_compiled(self):
        result = self.inspect(config(matcher="["))
        self.assertEqual([f["rule_id"] for f in result["findings"]], ["HP004"])
        self.assertEqual(result["summary"]["categories"]["incompatible"], 0)

    def test_dead_group_matcher_is_not_reported(self):
        result = self.inspect(config("PreToolUse", {"type": "prompt"}, matcher="["))
        self.assertEqual([f["rule_id"] for f in result["findings"]], ["HP002"])

    def test_tool_matcher_is_review_not_a_claim_of_failure(self):
        result = self.inspect(config("PreToolUse", matcher="Bash|Read"))
        finding = self.rules(result, "HP006")[0]
        self.assertEqual(finding["certainty"], "needs-context")
        self.assertEqual(result["summary"]["categories"]["incompatible"], 0)

    def test_plugin_root_context_removes_missing_context_notice(self):
        value = config(handler={"command": 'node "${CLAUDE_PLUGIN_ROOT}/hook.mjs"'})
        absent = self.inspect(value)
        supplied = self.inspect(value, plugin_root=self.base)
        self.assertEqual(self.rules(absent, "HP005")[0]["certainty"], "needs-context")
        self.assertFalse(self.rules(supplied, "HP005"))

    def test_absent_project_dir_is_not_missing_target_configuration(self):
        result = self.inspect(config(handler={"command": 'echo "${CLAUDE_PROJECT_DIR}"'}))
        self.assertEqual(result["summary"]["categories"]["configuration"], 0)

    def test_shell_environment_is_not_reported_as_unsupported(self):
        result = self.inspect(config(handler={"command": 'echo "${HOME}"'}))
        self.assertEqual(result["summary"]["categories"]["incompatible"], 0)
        self.assertTrue(self.rules(result, "HP008"))

    def test_unknown_handler_field_is_review(self):
        result = self.inspect(config(handler={"command": "echo ok", "futureFeature": True}))
        self.assertEqual(result["summary"]["categories"]["incompatible"], 0)
        self.assertTrue(self.rules(result, "HP008"))

    def test_unicode_spaces_and_bom(self):
        path = self.base / "中文 目录" / "配置.json"
        path.parent.mkdir()
        path.write_text(json.dumps(config()), encoding="utf-8-sig")
        result = analyze(load_document(path))
        self.assertFalse(result["findings"])

    def test_discovery_is_fixed_and_unambiguous(self):
        self.document(config(), path=self.base / "hooks/hooks.json")
        self.assertEqual(load_document(self.base).path.name, "hooks.json")
        self.document(config(), path=self.base / "hooks.json")
        with self.assertRaisesRegex(InputError, "多个"):
            load_document(self.base)

    def test_discovery_does_not_recurse_arbitrary_directories(self):
        self.document(config(), path=self.base / "unrelated/deep/hooks.json")
        with self.assertRaises(InputError):
            load_document(self.base)

    def test_input_is_unchanged_and_hook_is_never_executed(self):
        marker = self.base / "must-not-exist"
        command = f'{sys.executable} -c "open({str(marker)!r}, \'w\').write(\'bad\')"'
        self.document(config(handler={"command": command}))
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        completed = self.cli(self.path, "--out", self.base / "out")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)

    def test_strict_exit_and_reports_are_independent(self):
        self.document(config("Notification"))
        completed = self.cli(self.path, "--strict", "--out", self.base / "out")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertTrue((self.base / "out/report.json").exists())
        normal = self.cli(self.path, "--out", self.base / "out")
        self.assertEqual(normal.returncode, 0)

    def test_behavior_change_alone_does_not_fail_strict(self):
        self.document(config(handler={"command": "echo ok", "async": True}))
        self.assertEqual(self.cli(self.path, "--strict", "--out", self.base / "out").returncode, 0)

    def test_cli_input_error_uses_code_two(self):
        self.path.write_text("broken", encoding="utf-8")
        completed = self.cli(self.path, "--out", self.base / "out")
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn("Traceback", completed.stderr)

    def test_cli_from_different_working_directory(self):
        self.document(config())
        completed = self.cli(self.path, "--out", self.base / "out", cwd=self.base)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_output_cannot_overwrite_input(self):
        path = self.base / "report.json"
        doc = self.document(config(), path=path)
        before = path.read_bytes()
        with self.assertRaises(InputError):
            write_reports(analyze(doc), self.base, doc.path)
        self.assertEqual(path.read_bytes(), before)

    def test_markdown_and_json_derive_from_same_result(self):
        doc = self.document(config("Notification"))
        result = analyze(doc)
        json_path, md_path = write_reports(result, self.base / "report", doc.path)
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), result)
        self.assertEqual(md_path.read_text(encoding="utf-8"), render_markdown(result))
        self.assertIn("HP001", md_path.read_text(encoding="utf-8"))

    def test_json_pointer_escaping_and_html_inertness(self):
        result = self.inspect({"hooks": {"<img src=x onerror=alert(1)>/~": [{}]}})
        self.assertIn("~1~0", result["findings"][0]["pointer"])
        markdown = render_markdown(result)
        self.assertNotIn("<img", markdown)
        self.assertIn("&lt;img", markdown)

    def test_findings_are_deterministic_and_evidenced(self):
        doc = self.document(config("PreCompact"))
        first, second = analyze(doc), analyze(doc)
        self.assertEqual(first, second)
        for finding in first["findings"]:
            for evidence in finding["evidence_ids"]:
                self.assertIn(evidence, first["evidence"])

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(InputError):
            load_profile("../../something")

    def test_repeated_context_issues_keep_all_locations_in_one_group(self):
        value = {"hooks": {"Stop": [{"hooks": [{"command": "node ${CLAUDE_PLUGIN_ROOT}/a.js"}, {"command": "node ${CLAUDE_PLUGIN_ROOT}/b.js"}]}]}}
        result = self.inspect(value)
        issues = self.rules(result, "HP005")
        self.assertEqual(len(issues), 1)
        self.assertEqual(len(issues[0]["related_pointers"]), 2)
        self.assertEqual(result["summary"]["affected_locations"], 2)

    def test_grouped_context_findings_have_distinct_ids_for_same_locations(self):
        command = 'node "${CLAUDE_PLUGIN_ROOT}/hook.js" "${CLAUDE_PROJECT_DIR}"'
        value = {"hooks": {"Stop": [{"hooks": [{"command": command}, {"command": command}]}]}}
        result = self.inspect(value)
        issues = self.rules(result, "HP005")
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0]["related_pointers"], issues[1]["related_pointers"])
        self.assertEqual(len({issue["id"] for issue in issues}), 2)


if __name__ == "__main__":
    unittest.main()
