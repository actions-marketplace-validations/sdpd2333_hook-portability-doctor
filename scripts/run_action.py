#!/usr/bin/env python3
"""GitHub Actions adapter. Inputs are arguments, never interpolated shell code."""

import json
import os
from pathlib import Path
import sys
import uuid

from hook_doctor.analyzer import PROFILE_ID
from hook_doctor.cli import main as check_main
from hook_doctor.loader import InputError
from hook_doctor.report import LABELS, STATUSES


def write_outputs(path, values):
    """Use the runner's multiline protocol even for paths containing newlines."""
    with Path(path).open("a", encoding="utf-8", newline="\n") as stream:
        for key, value in values.items():
            value = str(value)
            delimiter = uuid.uuid4().hex
            while delimiter in value:
                delimiter = uuid.uuid4().hex
            stream.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def write_summary(path, result, exit_code):
    lines = ["## Hook Portability Doctor", ""]
    if result is None:
        lines += [f"检查未完成，退出码 {exit_code}。没有导出本次报告；详见步骤日志。", ""]
    else:
        lines += [
            STATUSES[result["summary"]["status"]] + "。",
            "", f"规则：{result['profile_id']}", "",
            "| 分类 | 问题组数量 |", "|---|---:|",
        ]
        lines += [f"| {LABELS[key]} | {value} |"
                  for key, value in result["summary"]["categories"].items()]
        lines += ["", "这是一份静态检查结果；目标实际安装版本和 Hook 执行尚未验证。", ""]
    with Path(path).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines))


def main(environ=None):
    env = os.environ if environ is None else environ
    result = None
    outputs = {}
    try:
        input_path = env.get("HPD_INPUT_PATH", "")
        if not input_path:
            raise InputError("Action 的 path 输入不能为空。")
        strict = env.get("HPD_STRICT", "true").strip().lower()
        if strict not in ("true", "false"):
            raise InputError("Action 的 strict 必须是 true 或 false。")
        output = Path(env.get("HPD_OUTPUT_DIRECTORY") or "reports/hook-portability").expanduser().resolve()
        arguments = [
            "--profile=" + (env.get("HPD_PROFILE") or PROFILE_ID),
            "--out=" + str(output),
        ]
        for flag, key in (("--plugin-root", "HPD_PLUGIN_ROOT"), ("--project-dir", "HPD_PROJECT_DIR")):
            if env.get(key):
                arguments.append(flag + "=" + env[key])
        if strict == "true":
            arguments.append("--strict")
        # A filename such as --version must not activate an argparse early exit
        # and then allow an old report to be mistaken for a fresh scan.
        arguments += ["--", input_path]
        try:
            exit_code = check_main(arguments)
        except SystemExit as exc:
            exit_code = int(exc.code)
        # CLI success/strict failure means both reports were written this run.
        # Error exits deliberately do not expose files left by earlier runs.
        if exit_code in (0, 1):
            result = json.loads((output / "report.json").read_text(encoding="utf-8"))
            outputs = {
                "status": result["summary"]["status"],
                "incompatible-count": result["summary"]["categories"]["incompatible"],
                "report-json": output / "report.json",
                "report-markdown": output / "report.md",
            }
    except (InputError, OSError) as exc:
        print(f"Action 输入/输出错误：{exc}", file=sys.stderr)
        exit_code = 2
        result, outputs = None, {}
    except Exception as exc:
        print(f"Action 内部错误（{type(exc).__name__}）：{exc}", file=sys.stderr)
        exit_code = 3
        result, outputs = None, {}
    try:
        if env.get("GITHUB_STEP_SUMMARY"):
            write_summary(env["GITHUB_STEP_SUMMARY"], result, exit_code)
    except OSError as exc:
        print(f"无法写入 Action 摘要：{exc}", file=sys.stderr)
        exit_code, outputs = 2, {}
    outputs["exit-code"] = exit_code
    try:
        if env.get("GITHUB_OUTPUT"):
            write_outputs(env["GITHUB_OUTPUT"], outputs)
    except OSError as exc:
        print(f"无法写入 Action 结果：{exc}", file=sys.stderr)
        return 2
    return exit_code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
