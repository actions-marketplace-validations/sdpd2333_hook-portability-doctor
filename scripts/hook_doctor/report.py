"""Two views of one analysis, with atomic writes and input-overwrite protection."""

import html
import json
import os
from pathlib import Path
import tempfile

from .loader import InputError

LABELS = {
    "incompatible": "明确不兼容", "behavior_change": "行为变化",
    "configuration": "配置待确认", "manual_review": "需要核对",
}
STATUSES = {
    "no_hooks": "未发现可检查的 Hook 事件",
    "no_handlers": "存在事件项，但没有配置处理器",
    "incompatibilities_found": "发现明确不兼容项",
    "behavior_changes_found": "发现配置行为差异",
    "review_required": "存在需要补充信息或运行核对的事项",
    "no_static_differences_found": "未检出已覆盖规则中的静态差异",
}


def _text(value):
    value = html.escape(str(value)).replace("\r", " ").replace("\n", " ")
    for character in ("\\", "`", "*", "_", "[", "]", "|", "#"):
        value = value.replace(character, "\\" + character)
    return value


def render_markdown(result):
    summary = result["summary"]
    lines = [
        "# Hook 迁移检查报告", "",
        "**结论：" + STATUSES[summary["status"]] + "。**", "",
        "本报告检查 Claude Hook 配置通过指定 DSH 兼容桥的静态差异。安装版本和实际执行尚未验证。", "",
        f"- 输入：{_text(result['input']['file'])}",
        f"- 规则：`{result['profile_id']}`；目标提交：`{result['repository_revision']}`",
        f"- 输入 SHA-256：`{result['input']['sha256']}`",
        f"- 检查器版本：`{result['analyzer_version']}`；规则核对日期：{result['profile_checked_date']}",
        f"- 事件：{summary['event_types']}；配置处理器：{summary['configured_handlers']}；待运行验证的 command 候选：{summary['candidate_command_handlers']}", "",
        "同一原因的路径配置、工具匹配提示按问题组归并，关联位置仍全部保留。", "",
        "| 分类 | 问题组数量 |", "|---|---:|",
    ]
    lines += [f"| {LABELS[key]} | {value} |" for key, value in summary["categories"].items()]
    lines += ["", "## 检查项", ""]
    if not result["findings"]:
        lines += ["没有命中当前规则。此结果不等于插件已经通过实际运行验证。", ""]
    for index, item in enumerate(result["findings"], 1):
        lines += [
            f"### {index}. {LABELS[item['category']]} · {item['rule_id']}", "",
            f"- 位置：<code>{html.escape(item['pointer'])}</code>",
            f"- 判断：{_text(item['message'])}",
            f"- 建议：{_text(item['suggestion'])}",
            "- 确定性：" + ("已确认该目标快照的行为" if item["certainty"] == "confirmed-for-profile" else "需要目标上下文或实际验证"),
            "- 依据：" + "、".join(f"[{key}]({result['evidence'][key]['url']})" for key in item["evidence_ids"]), "",
        ]
        if "related_pointers" in item:
            lines += ["同组位置：" + "、".join(f"<code>{html.escape(value)}</code>" for value in item["related_pointers"]), ""]
    lines += ["## 尚未验证", ""] + ["- " + _text(value) for value in result["unverified"]]
    lines += ["", "处理器候选数量只反映静态结构；正则、脚本依赖和运行时仍可能阻止注册或执行。", ""]
    return "\n".join(lines)


def write_reports(result, output_dir, input_path):
    output_dir = Path(output_dir).expanduser().resolve()
    input_path = Path(input_path).resolve()
    destinations = [output_dir / "report.json", output_dir / "report.md"]
    for destination in destinations:
        same = destination.resolve() == input_path
        if destination.exists() and input_path.exists():
            same |= destination.samefile(input_path)
        if same:
            raise InputError("输出位置会覆盖输入配置；请指定另一个 --out 目录。")
    payloads = [json.dumps(result, indent=2, ensure_ascii=False) + "\n", render_markdown(result)]
    temporary = []
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        # Prepare both files before replacing either destination.
        for destination, payload in zip(destinations, payloads):
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=output_dir, delete=False) as stream:
                temporary.append(Path(stream.name))
                stream.write(payload)
        for source, destination in zip(temporary, destinations):
            os.replace(source, destination)
    except OSError as exc:
        raise InputError(f"无法写入报告：{exc.strerror or exc}") from exc
    finally:
        for source in temporary:
            source.unlink(missing_ok=True)
    return destinations
