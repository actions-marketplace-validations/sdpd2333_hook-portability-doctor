"""Bounded, read-only JSON input and explicit configuration discovery."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

MAX_INPUT_BYTES = 5 * 1024 * 1024
DISCOVERY_PATHS = (
    "hooks/hooks.json", "hooks.json", ".claude/hooks.json",
    ".claude/settings.json", ".claude/settings.local.json", "settings.json",
)


class InputError(ValueError):
    """An actionable input problem rather than an analyzer defect."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"JSON 包含重复键 {key!r}；请先消除歧义。")
        result[key] = value
    return result


def _invalid_constant(value):
    raise InputError(f"{value} 不是标准 JSON 数值。")


def read_json(path):
    path = Path(path)
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise InputError(f"无法读取 {path}: {exc.strerror or exc}") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise InputError("配置超过 5 MiB，请提供较小的 Hook 配置。")
    try:
        data = json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
    except UnicodeError as exc:
        raise InputError("配置必须使用 UTF-8 编码（允许 BOM）。") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"JSON 格式错误，第 {exc.lineno} 行第 {exc.colno} 列：{exc.msg}") from exc
    except RecursionError as exc:
        raise InputError("JSON 嵌套过深，无法检查。") from exc
    except InputError:
        raise
    except ValueError as exc:
        raise InputError(f"JSON 数值无法处理：{exc}") from exc
    return data, hashlib.sha256(raw).hexdigest()


def discover(path):
    path = Path(path).expanduser()
    if path.is_file():
        return path.resolve()
    if not path.is_dir():
        raise InputError(f"输入路径不存在或不是文件/目录：{path}")
    candidates = [path / name for name in DISCOVERY_PATHS if (path / name).is_file()]
    if not candidates:
        raise InputError("目录中没有找到 Hook 配置。请直接指定 hooks.json 或含 hooks 的 settings.json。")
    if len(candidates) != 1:
        choices = "\n".join(f"  - {item}" for item in candidates)
        raise InputError(f"发现多个配置，请明确指定一个文件；不会自动合并：\n{choices}")
    return candidates[0].resolve()


@dataclass(frozen=True)
class Document:
    path: Path
    display_path: str
    hooks: dict
    base_pointer: str
    source_format: str
    sha256: str


def load_document(path):
    resolved = discover(path)
    data, digest = read_json(resolved)
    if not isinstance(data, dict):
        raise InputError("JSON 根节点必须是对象。")
    if "hooks" in data:
        if not isinstance(data["hooks"], dict):
            raise InputError("hooks 字段必须是对象。目标的宽松回退不作为有效配置处理。")
        hooks, base, kind = data["hooks"], "/hooks", "wrapped"
    elif resolved.name in ("settings.json", "settings.local.json"):
        hooks, base, kind = {}, "/hooks", "settings-without-hooks"
    else:
        hooks = {key: value for key, value in data.items() if key not in ("$schema", "description")}
        base, kind = "", "bare"
    try:
        display = resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        display = resolved.as_posix()
    return Document(resolved, display, hooks, base, kind, digest)


def pointer(base, part):
    return base + "/" + str(part).replace("~", "~0").replace("/", "~1")
