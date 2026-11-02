#!/usr/bin/env python3
"""One-command, offline acceptance: tests + real CLI scenarios + a readable index."""

import argparse
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "reports/acceptance")
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    log = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (output / "tests.txt").write_text(log.getvalue(), encoding="utf-8")
    scenarios = [
        ("supported", "最小支持配置", "minimal-supported.json", ["--strict"], 0),
        ("gaps", "迁移差异与严格模式", "migration-gaps.json", ["--strict"], 1),
        ("root-unknown", "未提供根目录上下文", "root-context.json", [], 0),
        ("root-provided", "补充根目录后复查", "root-context.json", ["--plugin-root", str(ROOT)], 0),
    ]
    outcomes = []
    for key, name, source, extra, expected_exit in scenarios:
        report_path = output / key / "report.json"
        # A previous successful report must not make a failed invocation pass.
        report_path.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_hooks.py"), str(ROOT / "examples" / source),
             "--out", str(output / key), *extra],
            cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=20,
        )
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
        passed = result.returncode == expected_exit and report is not None
        if report:
            categories = report["summary"]["categories"]
            if key == "supported":
                passed &= not report["findings"] and not report["execution_verified"]
            elif key == "gaps":
                passed &= categories["incompatible"] >= 2 and categories["behavior_change"] >= 1
            elif key == "root-unknown":
                passed &= categories["configuration"] > 0
            elif key == "root-provided":
                passed &= categories["configuration"] == 0
        outcomes.append({"scenario": key, "name": name, "passed": bool(passed),
                         "expected_exit": expected_exit, "actual_exit": result.returncode,
                         "summary": report["summary"] if report else None,
                         "stderr": result.stderr})
    all_passed = tests.wasSuccessful() and all(item["passed"] for item in outcomes)
    verification = {
        "passed": all_passed, "python": platform.python_version(), "platform": platform.platform(),
        "tests_run": tests.testsRun, "failures": len(tests.failures), "errors": len(tests.errors),
        "scenarios": outcomes, "actual_hook_execution_tested": False,
        "client_discovery_tested": False,
    }
    (output / "verification.json").write_text(json.dumps(verification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Hook Portability Doctor 验收", "",
             "结果：**" + ("通过" if all_passed else "存在失败") + "**", "",
             f"- Python：{verification['python']}", f"- 系统：{verification['platform']}",
             f"- 回归测试：{tests.testsRun} 项；失败 {len(tests.failures)}；错误 {len(tests.errors)}。", "",
             "| 场景 | 结果 | 期望/实际退出码 | 报告 |", "|---|---|---|---|"]
    for item in outcomes:
        lines.append(f"| {item['name']} | {'通过' if item['passed'] else '失败'} | {item['expected_exit']}/{item['actual_exit']} | [查看]({item['scenario']}/report.md) |")
    lines += ["", "建议先打开迁移差异报告，再对比两份根目录报告，确认补充信息后相关提示消失。", "",
              "本验收验证本地静态检查器。它不代表目标 Hook 实际运行成功，也不代表 AI 客户端已自动发现此 skill。", "",
              "[完整测试输出](tests.txt) · [机器可读验收结果](verification.json)", ""]
    (output / "ACCEPTANCE.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{'PASS' if all_passed else 'FAIL'}: {tests.testsRun} tests, {len(outcomes)} CLI scenarios")
    print(output / "ACCEPTANCE.md")
    if not all_passed:
        print(log.getvalue(), file=sys.stderr)
    return 0 if all_passed else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
