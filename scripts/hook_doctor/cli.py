#!/usr/bin/env python3
"""CLI entry point. Python 3.11+, standard library only."""

import argparse
from pathlib import Path
import sys

from . import __version__
from .analyzer import PROFILE_ID, analyze, load_profile
from .loader import InputError, load_document
from .report import STATUSES, write_reports


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="检查 Claude Hook 配置到 DSH 指定兼容桥的静态差异；不执行 Hook。")
    parser.add_argument("input", type=Path, help="JSON 文件或插件目录")
    parser.add_argument("--target", choices=["dsh-claude-bridge"], default="dsh-claude-bridge")
    parser.add_argument("--profile", choices=[PROFILE_ID], default=PROFILE_ID)
    parser.add_argument("--plugin-root", type=Path, help="显式提供目标插件根目录上下文")
    parser.add_argument("--project-dir", type=Path, help="显式提供目标项目目录上下文")
    parser.add_argument("--out", type=Path, default=Path("reports/latest"), help="报告目录，默认 reports/latest")
    parser.add_argument("--strict", action="store_true", help="有明确不兼容项时返回 1；其他提示不改变退出码")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        document = load_document(args.input)
        result = analyze(document, load_profile(args.profile), plugin_root=args.plugin_root, project_dir=args.project_dir)
        paths = write_reports(result, args.out, document.path)
    except (InputError, OSError) as exc:
        print(f"输入/输出错误：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"检查器内部错误（{type(exc).__name__}）：{exc}", file=sys.stderr)
        return 3
    print(STATUSES[result["summary"]["status"]])
    for category, count in result["summary"]["categories"].items():
        print(f"  {category}: {count}")
    print("实际安装版本和运行结果：未验证")
    for path in paths:
        print(path)
    return 1 if args.strict and result["summary"]["categories"]["incompatible"] else 0
