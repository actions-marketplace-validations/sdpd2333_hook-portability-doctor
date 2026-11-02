#!/usr/bin/env python3
"""Copy a complete skill into an explicit skill root without replacing an existing skill."""

import argparse
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "hook-portability-doctor"
CONTENTS = ("SKILL.md", "LICENSE", "README.md", "CONTRIBUTING.md", "agents", "scripts",
            "rules", "references", "examples", "tests", "docs", "integrations")


def install(skills_dir):
    container = Path(skills_dir).expanduser().resolve()
    target = container / NAME
    if target.exists() or target.is_symlink():
        raise ValueError(f"目标已存在，未覆盖：{target}")
    for name in CONTENTS:
        source = ROOT / name
        if source.is_dir() and container.is_relative_to(source.resolve()):
            raise ValueError("目标不能位于将被复制的资源目录内部。")
    container.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".hpd-stage-", dir=container) as temporary:
        stage = Path(temporary).resolve()
        if not stage.is_relative_to(container):
            raise ValueError("安装暂存路径不在指定根目录内。")
        bundle = stage / NAME
        bundle.mkdir()
        for name in CONTENTS:
            source = ROOT / name
            if source.is_dir():
                shutil.copytree(source, bundle / name,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
            else:
                shutil.copyfile(source, bundle / name)
        bundle.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, required=True, help="客户端扫描的 skill 根目录；不会覆盖已有 skill")
    args = parser.parse_args()
    try:
        print(install(args.skills_dir))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
