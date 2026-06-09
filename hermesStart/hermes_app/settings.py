"""应用配置：本地 Windows 侧的设置（与 WSL ~/.hermes/.env 无关）。"""
import json
import os
import sys
import subprocess
from pathlib import Path


def _get_config_dir() -> Path:
    """决定 config 文件放哪里。

    统一用 Windows 标准的 %APPDATA%\\hermesStart\\：
      - 不污染桌面 / exe 所在目录
      - 重装 / 移动 exe 不会丢配置
      - 多用户隔离
      - 卸载时一处清理
    """
    if sys.platform != "win32":
        # 非 Windows（开发机），回退到 XDG 标准位置
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hermesStart"
    else:
        # Windows：%APPDATA%\hermesStart\
        # 正常情况下 APPDATA 一定有；如果没有就抛错让用户自己修环境
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError(
                "环境变量 APPDATA 未设置，无法定位用户配置目录。\n"
                "请确认你在 Windows 上以正常用户身份运行，而不是 service / SYSTEM。"
            )
        base = Path(appdata) / "hermesStart"
    base.mkdir(parents=True, exist_ok=True)
    return base


CONFIG_DIR = _get_config_dir()
CONFIG_FILE = CONFIG_DIR / "app_config.json"

# 默认配置 - 首次运行时会自动检测 WSL 环境
DEFAULT_CONFIG = {
    # WSL 发行版名称（PowerShell 里 `wsl -l -v` 可查）
    "wsl_distro": "Ubuntu",
    # WSL 里的用户名（首次运行自动检测）
    "wsl_user": "",
    # Hermes 主目录（WSL 内路径）
    "hermes_home": "~/.hermes",
    # hermes-model 脚本路径（WSL 内路径）
    "hermes_model_script": "~/.local/bin/hermes-model",
    # 用哪个终端启动 hermes：auto / wt / cmd
    "terminal": "auto",
    # 窗口几何信息（记住上次大小位置）
    "window_geometry": "560x640+200+200",
}

# 缓存，避免每次都读盘
_cache = None


def _detect_wsl_default() -> str:
    """从 wsl -l -v 提取 Default 那一列的发行版名（无 DEFAULT 标记时取第一行）。

    注意：wsl -l -v 的 stdout 是 **UTF-16 LE**（带 \x00 字节），
    subprocess 默认按 utf-8 解会拿到乱码。这里用 bytes 模式 + 手动 utf-16 解。
    """
    try:
        result = subprocess.run(
            ["wsl.exe", "-l", "-v"],
            capture_output=True, timeout=5,
        )
        if result.returncode != 0:
            return "Ubuntu"
        raw = result.stdout
        # 尝试 UTF-16 LE 解码（带 BOM 的更稳）
        try:
            text = raw.decode("utf-16")
        except UnicodeDecodeError:
            # 退而求其次，去掉 \x00 再当 ASCII
            text = raw.decode("utf-8", errors="replace")
        lines = [l for l in text.splitlines() if l.strip()]
        # 第一行是表头（NAME STATE VERSION）
        for l in lines[1:]:
            if "Default" in l or l.lstrip().startswith("*"):
                # 去掉前导的 "*" 标记和空白
                return l.replace("*", "").split()[0].strip()
        # 没有 Default 标记就取第一个发行版
        if len(lines) >= 2:
            return lines[1].replace("*", "").split()[0].strip()
    except Exception:
        pass
    return "Ubuntu"


def _detect_wsl_user(distro: str) -> str:
    """通过 wsl.exe whoami 检测默认用户。"""
    try:
        result = subprocess.run(
            ["wsl.exe", "-d", distro, "--", "bash", "-c", "whoami"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        )
        if result.returncode == 0:
            user = result.stdout.strip()
            if user and user != "root":
                return user
    except Exception:
        pass
    return ""


def _auto_detect() -> dict:
    """首次运行时的自动检测：尽量把可填的字段填好。"""
    distro = _detect_wsl_default()
    user = _detect_wsl_user(distro)
    cfg = dict(DEFAULT_CONFIG)
    cfg["wsl_distro"] = distro
    if user:
        cfg["wsl_user"] = user
        cfg["hermes_home"] = f"/home/{user}/.hermes"
        cfg["hermes_model_script"] = f"/home/{user}/.local/bin/hermes-model"
    return cfg


def load_config() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    cfg_existed = CONFIG_FILE.exists()
    if cfg_existed:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    else:
        cfg = {}
    # 首次运行（配置文件还不存在）→ 跑自动检测
    # 注意：只在文件**完全不存在**时跑检测。如果文件存在但 first_run_done 未设
    # 或部分字段为空，那是用户自己改的，不覆盖。
    if not cfg_existed:
        detected = _auto_detect()
        for k, v in detected.items():
            cfg.setdefault(k, v)
        cfg["first_run_done"] = True
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    # 补全缺失字段
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    _cache = cfg
    return cfg


def save_config(cfg: dict) -> None:
    global _cache
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    _cache = cfg


def update(**kwargs) -> None:
    cfg = load_config()
    cfg.update(kwargs)
    save_config(cfg)
