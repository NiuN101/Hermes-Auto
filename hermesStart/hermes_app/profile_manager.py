"""Profile 管理：解析和编辑 hermes-model 脚本里的 PROFILES 字典。

脚本里 PROFILES 段长这样（带类型注解）：

    PROFILES: dict[str, dict] = {
        "name": {
            "desc": "...",
            "default": "model-id",
            "provider": "custom",
            "base_url": "...",
            "max_output_tokens": N,
            "context_window": N,
            "extra_body": {...},
            "api_key_env": "ENV_VAR",   # 仅环境变量名
        },
        ...
    }

我们：
  1. 用正则定位 PROFILES 那一行（保留原行不变，只换 body）
  2. body 用 ast.literal_eval 解析
  3. 编辑后用 pprint 输出 body，前面拼上原行
"""
import ast
import re
import time
import pprint
from typing import Dict, List

from . import settings
from . import wsl_bridge

# 备份保留数量
BACKUP_KEEP = 5


def _read_script() -> str:
    cfg = settings.load_config()
    return wsl_bridge.read_file(cfg["hermes_model_script"])


def _backup_script() -> str:
    """备份原脚本，返回备份路径。"""
    cfg = settings.load_config()
    src = cfg["hermes_model_script"]
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = f"{src}.bak.{ts}"
    wsl_bridge.run(f"cp {src} {bak}")
    # 清理旧备份
    wsl_bridge.run(
        f"ls -t {src}.bak.* 2>/dev/null | tail -n +{BACKUP_KEEP + 1} | xargs -r rm"
    )
    return bak


def _extract_profiles_block(script: str) -> tuple:
    """从脚本里抠出 PROFILES 段。

    返回:
        prefix    - 原行 'PROFILES: dict[str, dict] = '（含末尾空格）
        start_idx - 整个段在 script 里的起始位置
        end_idx   - 整个段在 script 里的结束位置（'}' 之后）
        dict_literal - '{ ... }' 字面量
    """
    # 允许 PROFILES = { 或 PROFILES: ... = { 两种格式
    m = re.search(
        r"^(PROFILES\b[^\n]*=\s*)\{",
        script,
        re.MULTILINE,
    )
    if not m:
        raise RuntimeError(
            "在 hermes-model 脚本里没找到 PROFILES = { ... } 段。\n"
            "请确认脚本里有一个顶层 PROFILES 字典定义。"
        )
    prefix = m.group(1)
    brace_start = m.end() - 1  # '{' 位置
    # 配对花括号（处理字符串、注释、嵌套）
    depth = 0
    i = brace_start
    in_str = None
    triple = False
    while i < len(script):
        ch = script[i]
        if in_str:
            if triple and script[i:i + 3] in ('"""', "'''"):
                in_str = None
                triple = False
                i += 3
                continue
            if ch == "\\" and not triple:
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = ch
            triple = script[i:i + 3] in ('"""', "'''")
            i += 1
            continue
        if ch == "#":
            nl = script.find("\n", i)
            i = nl + 1 if nl != -1 else len(script)
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    if depth != 0:
        raise RuntimeError("PROFILES 字典的括号没配平，请检查脚本。")
    end = i + 1
    dict_literal = script[brace_start:end]
    return prefix, m.start(), end, dict_literal


def parse_profiles() -> Dict[str, dict]:
    """解析脚本里的 PROFILES，返回 {name: fields}。"""
    script = _read_script()
    _, _, _, literal = _extract_profiles_block(script)
    try:
        data = ast.literal_eval(literal)
    except Exception as e:
        raise RuntimeError(
            f"PROFILES 字典解析失败: {e}\n"
            f"如果你用了 f-string、lambda 或不支持的字面量，ast.literal_eval 解析不了。\n"
            f"把那部分挪到 PROFILES 外面去再试。"
        )
    if not isinstance(data, dict):
        raise RuntimeError("PROFILES 解析结果不是字典。")
    return data


def write_profiles(profiles: Dict[str, dict]) -> str:
    """把新的 profiles 写回脚本。返回备份路径。"""
    cfg = settings.load_config()
    script = _read_script()
    prefix, start, end, _ = _extract_profiles_block(script)

    # 生成新的 body
    new_literal = pprint.pformat(profiles, width=88, sort_dicts=False)
    # pprint 默认花括号闭合是 '}'，开头可能是 '{\n' 也可能是 '{'
    # 我们强制保持 '{' 单独一行、'}' 单独一行的风格
    new_block = prefix + "{\n"
    inner = new_literal.strip()
    if inner.startswith("{"):
        inner = inner[1:]
    if inner.endswith("}"):
        inner = inner[:-1]
    new_block += inner
    new_block += "}\n"

    # 替换
    new_script = script[:start] + new_block + script[end:]

    bak = _backup_script()
    wsl_bridge.write_file(cfg["hermes_model_script"], new_script)
    return bak


# ---------------- 单 profile CRUD ----------------

def get_profile(name: str) -> dict:
    profiles = parse_profiles()
    if name not in profiles:
        raise KeyError(f"profile 不存在: {name}")
    return profiles[name]


def add_profile(name: str, fields: dict) -> None:
    profiles = parse_profiles()
    if name in profiles:
        raise ValueError(f"profile 已存在: {name}（如需修改请用编辑）")
    profiles[name] = fields
    write_profiles(profiles)


def update_profile(name: str, fields: dict) -> None:
    profiles = parse_profiles()
    if name not in profiles:
        raise KeyError(f"profile 不存在: {name}")
    profiles[name] = fields
    write_profiles(profiles)


def delete_profile(name: str) -> None:
    profiles = parse_profiles()
    if name not in profiles:
        raise KeyError(f"profile 不存在: {name}")
    if len(profiles) <= 1:
        raise ValueError("至少保留一个 profile，不能全删。")
    del profiles[name]
    write_profiles(profiles)


def rename_profile(old: str, new: str) -> None:
    profiles = parse_profiles()
    if old not in profiles:
        raise KeyError(f"profile 不存在: {old}")
    if new in profiles and new != old:
        raise ValueError(f"目标名字已存在: {new}")
    profiles[new] = profiles.pop(old)
    write_profiles(profiles)


# ---------------- 表单字段定义（UI 用） ----------------

# 一个 profile 在脚本里的字段。desc / api_key_env / extra_body 是可选的。
PROFILE_FIELDS = [
    ("default", "模型 ID（default）", "如 qwen3.5:9b-65k / deepseek-chat"),
    ("provider", "Provider", "通常 custom 或 openai"),
    ("base_url", "Base URL", "OpenAI 兼容端点"),
    ("max_output_tokens", "max_output_tokens", "整数"),
    ("context_window", "context_window", "整数"),
    ("api_key_env", "API key 环境变量名", "如 DEEPSEEK_API_KEY，留空=本地无 key"),
    ("extra_body", "extra_body（Python dict 字面量）", "如 {\"thinking\": {\"type\": \"enabled\"}}，留空=无"),
    ("desc", "描述（仅展示）", "如 DeepSeek V4-Pro / 本地 qwen，留空也行"),
]


def fields_to_script(fields: dict) -> dict:
    """把 UI 表单字段整理成 PROFILES 字典里的实际字段。

    注意：脚本里就是 'api_key_env' 字段，存裸的环境变量名字符串。
    """
    out = {}

    # desc
    desc = fields.get("desc", "").strip()
    if desc:
        out["desc"] = desc

    # 必填数值/字符串
    for k in ("default", "provider", "base_url"):
        v = fields.get(k, "").strip()
        if not v:
            raise ValueError(f"字段 {k} 不能为空。")
        out[k] = v

    for k in ("max_output_tokens", "context_window"):
        v = fields.get(k, "").strip()
        if not v:
            raise ValueError(f"字段 {k} 不能为空。")
        try:
            out[k] = int(v)
        except ValueError:
            raise ValueError(f"{k} 必须是整数，你填的是: {v}")

    # api_key_env：留空表示 None（本地无 key）
    env = fields.get("api_key_env", "").strip()
    out["api_key_env"] = env if env else None

    # extra_body：Python dict 字面量
    eb = fields.get("extra_body", "").strip()
    if eb:
        if eb in ("{}", "{ }"):
            out["extra_body"] = {}
        else:
            try:
                parsed = ast.literal_eval(eb)
            except Exception as e:
                raise ValueError(f"extra_body 不是合法的 Python 字面量: {e}")
            if not isinstance(parsed, dict):
                raise ValueError("extra_body 必须是 dict。")
            out["extra_body"] = parsed
    # else: 不写入 extra_body，渲染时用空 dict 兜底

    return out


def fields_from_script(profile: dict) -> dict:
    """把 PROFILES 里的字段反向拆成 UI 表单字段。"""
    out = {
        "default": str(profile.get("default", "")),
        "provider": str(profile.get("provider", "")),
        "base_url": str(profile.get("base_url", "")),
        "max_output_tokens": str(profile.get("max_output_tokens", "")),
        "context_window": str(profile.get("context_window", "")),
        "desc": str(profile.get("desc", "")),
    }
    env = profile.get("api_key_env")
    out["api_key_env"] = env if env else ""

    eb = profile.get("extra_body", {})
    if isinstance(eb, dict) and eb:
        # 用 pprint 保持可读，且 Python 字面量格式（True/False/None）
        out["extra_body"] = pprint.pformat(eb, width=80, sort_dicts=False)
    else:
        out["extra_body"] = ""
    return out
