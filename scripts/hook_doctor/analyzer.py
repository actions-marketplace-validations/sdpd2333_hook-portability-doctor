"""Deterministic analysis against a pinned target snapshot, not a shell interpreter."""

from collections import Counter
import hashlib
import math
from pathlib import Path
import re

from . import __version__
from .loader import InputError, pointer, read_json

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ID = "dsh-claude-ce7073d"
CATEGORIES = ("incompatible", "behavior_change", "configuration", "manual_review")
VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def load_profile(profile_id=PROFILE_ID):
    if profile_id != PROFILE_ID:
        raise InputError(f"未知规则集：{profile_id}。可用规则集：{PROFILE_ID}")
    profile, _ = read_json(ROOT / "rules" / (profile_id + ".json"))
    return profile


def _nonempty(value):
    return value is not None and value is not False and value != "" and value != [] and value != {} and value != 0


def analyze(document, profile=None, *, plugin_root=None, project_dir=None):
    profile = profile or load_profile()
    findings = []
    counts = {"event_types": len(document.hooks), "configured_handlers": 0, "candidate_command_handlers": 0}

    def add(rule, category, location, message, suggestion, *, confirmed=True, evidence="DSH-CONFIG"):
        key = f"{rule}\0{category}\0{location}\0{message}"
        findings.append({
            "id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:12],
            "rule_id": rule, "category": category,
            "certainty": "confirmed-for-profile" if confirmed else "needs-context",
            "pointer": location, "message": message, "suggestion": suggestion,
            "evidence_ids": [evidence],
        })

    def skipped(location, message):
        add("HP007", "incompatible", location, message, "修正此配置项后重新检查；该问题不表示其他有效项都会失效。")

    for event, groups in document.hooks.items():
        ep = pointer(document.base_pointer, event)
        if isinstance(groups, list):
            counts["configured_handlers"] += sum(
                len(group["hooks"]) for group in groups
                if isinstance(group, dict) and isinstance(group.get("hooks"), list)
            )
        if event not in profile["recognized_events"]:
            empty = groups == []
            add("HP001", "manual_review" if empty else "incompatible", ep,
                "目标不识别此事件；当前事件没有处理器。" if empty else "目标不识别此事件，整组配置会在解析处理器之前被忽略。",
                "核对源平台事件名称；需要保留该功能时寻找目标的原生入口。删除配置不等于完成迁移。")
            continue
        if not isinstance(groups, list):
            skipped(ep, "事件对应的值不是数组，目标会跳过它。")
            continue
        for gi, group in enumerate(groups):
            gp = pointer(ep, gi)
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                skipped(gp, "处理器组需要包含 hooks 数组；目标会跳过此组。")
                continue
            eligible = 0
            for hi, handler in enumerate(group["hooks"]):
                hp = pointer(pointer(gp, "hooks"), hi)
                if not isinstance(handler, dict):
                    skipped(hp, "处理器不是对象，目标会跳过它。")
                    continue
                kind = handler.get("type")
                # Target uses typeof type === 'string' ? type : 'command'.
                kind = kind if isinstance(kind, str) else "command"
                if kind not in profile["handler_types"]:
                    add("HP002", "incompatible", pointer(hp, "type"),
                        "目标只执行 command 处理器，这个处理器会被跳过。",
                        "确认其意图后编写经过验证的目标实现；仅修改 type 无法保留原功能。")
                    continue
                command = handler.get("command")
                if not isinstance(command, str):
                    skipped(pointer(hp, "command"), "command 不是字符串，目标会跳过此处理器。")
                    continue
                eligible += 1
                counts["candidate_command_handlers"] += 1
                if not command.strip():
                    add("HP008", "manual_review", pointer(hp, "command"),
                        "command 为空；解析器接受字符串不代表有可执行的行为。", "提供实际命令并单独验证。", confirmed=False)
                for option, detail in profile["ignored_options"].items():
                    if option not in handler:
                        continue
                    value = handler[option]
                    if detail["when"] == "true":
                        if value is True:
                            active = True
                        elif value is False or value is None:
                            active = False
                        else:
                            add("HP008", "manual_review", pointer(hp, option),
                                "此控制字段不是布尔值；目标不会采用它，源配置意图需要确认。",
                                "核对字段类型，不把不确定意图当成已证实的行为变化。", confirmed=False)
                            active = False
                    else:
                        active = _nonempty(value)
                    if active:
                        add("HP003", "behavior_change", pointer(hp, option), detail["message"],
                            "核对是否依赖此选项；在目标中验证替代方式。", evidence="DSH-LIMITATIONS")
                if "timeout" in handler:
                    timeout = handler["timeout"]
                    if type(timeout) not in (int, float):
                        add("HP003", "behavior_change", pointer(hp, "timeout"),
                            "timeout 不是数值，目标解析器不会保留该超时设置。", "按源格式提供数值并验证目标超时行为。")
                    elif timeout < 0 or (type(timeout) is float and not math.isfinite(timeout)) or abs(timeout) > 1.7976931348623157e308:
                        add("HP008", "manual_review", pointer(hp, "timeout"),
                            "timeout 的数值需要确认；本工具不推断目标运行时计时器行为。", "使用明确的非负有限超时。", confirmed=False)
                known = set(profile["retained_handler_fields"]) | set(profile["ignored_options"])
                for key in sorted(set(handler) - known):
                    add("HP008", "manual_review", pointer(hp, key),
                        "该处理器字段不在本规则快照的保留字段中，未推断其意图。",
                        "查证该字段的源语义及目标实现。", confirmed=False)
                for variable in sorted(set(VARIABLE.findall(command))):
                    if variable == "CLAUDE_PLUGIN_ROOT":
                        if plugin_root is None:
                            add("HP005", "configuration", pointer(hp, "command"),
                                "命令引用 CLAUDE_PLUGIN_ROOT，本次检查未收到 pluginRoot；不能据此断言用户没有配置。",
                                "用 --plugin-root 提供目标桥的实际插件根目录后复查。", confirmed=False)
                        elif not Path(plugin_root).is_dir():
                            add("HP005", "configuration", pointer(hp, "command"),
                                "提供的 pluginRoot 在本机不是现有目录；本机路径是否代表目标环境需要确认。",
                                "核对路径和目标机器上下文。", confirmed=False)
                    elif variable == "CLAUDE_PROJECT_DIR":
                        if project_dir is None:
                            add("HP005", "manual_review", pointer(hp, "command"),
                                "命令依赖项目目录；目标可使用会话目录，本次未验证具体目录。",
                                "如需静态核对，提供 --project-dir；未提供不等于目标配置缺失。", confirmed=False)
                        elif not Path(project_dir).is_dir():
                            add("HP005", "configuration", pointer(hp, "command"),
                                "提供的项目目录在本机不存在；目标环境路径仍需确认。", "核对项目目录。", confirmed=False)
                    else:
                        add("HP008", "manual_review", pointer(hp, "command"),
                            "命令包含其他变量替换，是否由目标 shell 或环境提供尚未验证。",
                            "在目标环境核对变量，不把 shell 环境变量一律当作不支持。", confirmed=False)
            # Target doesn't parse matchers for groups with no runnable commands.
            if not eligible:
                continue
            matcher = group.get("matcher")
            if isinstance(matcher, str) and matcher:
                if event in profile["matcher_ignored_events"]:
                    add("HP004", "manual_review", pointer(gp, "matcher"),
                        "目标对该事件忽略 matcher。源平台也可能如此，不能仅凭此字段断言迁移产生回归。",
                        "确认功能未依赖此匹配条件；此 matcher 不参与目标正则校验。")
                else:
                    is_tool = event in profile["tool_matcher_events"]
                    add("HP006" if is_tool else "HP008", "manual_review", pointer(gp, "matcher"),
                        "工具名与目标正则语义需要运行核对。" if is_tool else "该事件的匹配主体和目标正则语义尚未验证。",
                        "核对实际匹配主体；本工具不使用 Python 正则冒充目标正则验证。", confirmed=False)
            elif matcher is not None and not isinstance(matcher, str):
                add("HP008", "manual_review", pointer(gp, "matcher"),
                    "matcher 不是字符串，目标不保留此值。", "核对配置类型与预期匹配范围。")
            for key in sorted(set(group) - {"hooks", "matcher"}):
                add("HP008", "manual_review", pointer(gp, key),
                    "该组字段未被目标配置解析器保留。", "核对源意图；未将此未知字段直接判定为功能故障。", confirmed=False)

    # A command can reference several environment variables at the same location.
    findings = list({item["id"]: item for item in findings}.values())
    grouped = {}
    for item in findings:
        key = (item["rule_id"], item["category"], item["message"], item["certainty"]) if item["rule_id"] in ("HP005", "HP006") else (item["id"],)
        if key not in grouped:
            grouped[key] = item
        else:
            existing = grouped[key]
            existing.setdefault("related_pointers", [existing["pointer"]]).append(item["pointer"])
    findings = list(grouped.values())
    for item in findings:
        if "related_pointers" in item:
            item["related_pointers"] = sorted(set(item["related_pointers"]))
            item["pointer"] = item["related_pointers"][0]
            identity = "\0".join((item["rule_id"], item["category"], item["message"],
                                    item["certainty"], repr(item["related_pointers"])))
            item["id"] = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    findings.sort(key=lambda item: (item["pointer"], item["rule_id"], item["id"]))
    by_category = Counter(item["category"] for item in findings)
    if not counts["event_types"]:
        status = "no_hooks"
    elif by_category["incompatible"]:
        status = "incompatibilities_found"
    elif by_category["behavior_change"]:
        status = "behavior_changes_found"
    elif findings:
        status = "review_required"
    elif not counts["configured_handlers"]:
        status = "no_handlers"
    else:
        status = "no_static_differences_found"
    return {
        "schema_version": "1", "analyzer_version": __version__,
        "target": profile["target"], "profile_id": profile["profile_id"],
        "target_package": profile["target_package"],
        "repository_revision": profile["repository_revision"], "profile_checked_date": profile["checked_date"],
        "target_runtime_verified": False, "execution_verified": False,
        "input": {"file": document.display_path, "sha256": document.sha256, "format": document.source_format},
        "context": {
            "plugin_root_provided": plugin_root is not None,
            "project_dir_provided": project_dir is not None,
        },
        "summary": {"status": status, **counts, "finding_count": len(findings),
                    "affected_locations": sum(len(item.get("related_pointers", [item["pointer"]])) for item in findings),
                    "categories": {category: by_category[category] for category in CATEGORIES}},
        "findings": findings, "evidence": profile["evidence"],
        "unverified": [
            "目标实际安装版本与规则快照是否一致",
            "Hook 命令、脚本输出、依赖和 shell 行为",
            "目标正则是否合法及实际工具名称是否匹配",
            "其他配置层的合并、事件时序与实际运行结果",
        ],
    }
