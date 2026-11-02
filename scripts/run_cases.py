#!/usr/bin/env python3
"""Reproduce pinned public-configuration scans. Fetch is explicit; hooks never run."""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

from hook_doctor.analyzer import ROOT, analyze
from hook_doctor.loader import InputError, MAX_INPUT_BYTES, load_document, read_json
from hook_doctor.report import write_reports


def run(fetch=False, output=None):
    manifest, _ = read_json(ROOT / "examples/cases.json")
    cache = ROOT / ".work/upstream"
    cache.mkdir(parents=True, exist_ok=True)
    output = Path(output or ROOT / "reports/cases").resolve()
    outcomes = []
    for case in manifest["cases"]:
        source = cache / (case["id"] + ".json")
        url = f"https://raw.githubusercontent.com/{case['repository']}/{case['revision']}/{case['path']}"
        if not source.exists():
            if not fetch:
                raise InputError(f"缺少 {case['id']} 的缓存；用 --fetch 获取固定提交的公开 JSON。")
            request = urllib.request.Request(url, headers={"User-Agent": "hook-portability-doctor/0.1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(MAX_INPUT_BYTES + 1)
            if hashlib.sha256(raw).hexdigest() != case["sha256"]:
                raise InputError(f"{case['id']} 下载内容的 SHA-256 不匹配，未保存或分析。")
            source.write_bytes(raw)
        if hashlib.sha256(source.read_bytes()).hexdigest() != case["sha256"]:
            raise InputError(f"{case['id']} 缓存摘要不匹配，请核对缓存文件。")
        document = replace(load_document(source), display_path=f"{case['repository']}@{case['revision'][:12]}/{case['path']}")
        result = analyze(document)
        result["case_source"] = {**case, "url": url}
        observed = sorted(item["pointer"].removeprefix("/hooks/") for item in result["findings"]
                          if item["rule_id"] == "HP001" and item["category"] == "incompatible")
        if observed != sorted(case["expected_incompatible_events"]):
            raise InputError(f"{case['id']} 的固定案例结果发生变化：{observed}")
        write_reports(result, output / case["id"], source)
        outcomes.append({"case": case["id"], "input_sha256": document.sha256,
                         "incompatible_events": observed, "summary": result["summary"]})
    (output / "summary.json").write_text(json.dumps(outcomes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    lines = ["# 固定版本真实配置案例", "",
             "以下结果来自配置静态扫描；没有运行第三方 Hook，也没有证明整套插件可在 DSH 中工作。", "",
             "| 案例 | 固定源文件 | 目标不支持的事件 | 报告 |", "|---|---|---|---|"]
    for case, item in zip(manifest["cases"], outcomes):
        source_url = f"https://github.com/{case['repository']}/blob/{case['revision']}/{case['path']}"
        events = "、".join(item["incompatible_events"]) or "未检出"
        lines.append(f"| {case['id']} | [{case['revision'][:12]}]({source_url}) | {events} | [Markdown]({case['id']}/report.md) · [JSON]({case['id']}/report.json) |")
    lines += ["", "复现：在仓库根目录运行 `python scripts/run_cases.py --fetch`。首次下载固定版本公开 JSON，随后可离线使用缓存。", "",
              "每份 JSON 报告的 `case_source` 记录来源提交、路径和输入摘要。源 JSON 仅缓存在 `.work/`，不随仓库分发。", "",
              "[本批次完整计数](summary.json)", ""]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return outcomes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="允许下载清单中固定提交的公开 JSON")
    parser.add_argument("--out", type=Path, default=ROOT / "reports/cases")
    args = parser.parse_args()
    try:
        for item in run(args.fetch, args.out):
            print(f"{item['case']}: {item['summary']['categories']}")
    except (InputError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
