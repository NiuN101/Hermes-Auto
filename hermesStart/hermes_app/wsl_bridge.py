"""WSL 通信层：所有与 WSL 的交互都走这里。

注意：所有路径都是 WSL 内部的路径（如 ~/.hermes/...），
不要在这里用 Windows 路径。
"""
import subprocess
import time
import threading
import shlex
from typing import Optional, Tuple

from . import settings


def _wsl_args() -> list:
    cfg = settings.load_config()
    return ["wsl.exe", "-d", cfg["wsl_distro"], "bash", "-c"]


def _wsl_prefix() -> str:
    """在每条命令前面拼的 shell snippet：把 hermes-model 所在目录加进 PATH。

    非交互 bash（bash -c）不读 .bashrc，所以 ~/.local/bin 不会出现在 PATH 里。
    显式 source 一下最稳。
    """
    cfg = settings.load_config()
    script_dir = "$HOME/.local/bin"  # 默认
    # 尝试从配置里的脚本路径推断目录
    script_path = cfg.get("hermes_model_script", "")
    if script_path and "/" in script_path:
        script_dir = script_path.rsplit("/", 1)[0]
    return f'export PATH="{script_dir}:$PATH"; '


def run(cmd: str, timeout: int = 30, check: bool = False) -> Tuple[str, str, int]:
    """在 WSL 里跑一条命令，返回 (stdout, stderr, returncode)。

    跑 hermes-model switch / list 这类命令时用 capture=True。
    """
    full = _wsl_args() + [_wsl_prefix() + cmd]
    try:
        result = subprocess.run(
            full,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        return "", f"[超时] {e}", -1
    if check and result.returncode != 0:
        raise RuntimeError(
            f"WSL 命令失败: {cmd}\n--- stderr ---\n{result.stderr}"
        )
    return result.stdout, result.stderr, result.returncode


def run_async(cmd: str) -> subprocess.Popen:
    """异步跑命令（不等待结束），用于启动 hermes 之类。"""
    full = _wsl_args() + [cmd]
    return subprocess.Popen(
        full,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def read_file(path: str) -> str:
    """读 WSL 里的文件内容。"""
    # 用 cat，避免 Windows 端处理 WSL 路径的转义问题
    out, err, rc = run(f"cat {shlex.quote(path)}")
    if rc != 0:
        raise FileNotFoundError(f"读文件失败: {path}\n{err}")
    return out


def write_file(path: str, content: str) -> None:
    """写 WSL 里的文件。用 heredoc 避免转义噩梦。"""
    # 用 python 写文件最稳，避免 shell 对特殊字符的干扰
    # 把内容 base64 编码后传给 python 解码写入
    import base64
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    cmd = (
        f"python3 -c "
        f"\"import base64,sys; "
        f"open({path!r},'wb').write(base64.b64decode({b64!r}))\""
    )
    out, err, rc = run(cmd, timeout=60)
    if rc != 0:
        raise IOError(f"写文件失败: {path}\n{err}")


def file_exists(path: str) -> bool:
    out, _, rc = run(f"test -f {shlex.quote(path)} && echo YES || echo NO")
    return "YES" in out


# ---------------- 业务封装 ----------------

def is_hermes_running() -> int:
    """返回 hermes 相关进程数（0 = 没在跑）。"""
    out, _, rc = run("pgrep -af 'hermes' 2>/dev/null | grep -v pgrep | wc -l", check=False)
    try:
        return int(out.strip())
    except ValueError:
        return 0


def hermes_processes() -> list:
    """返回 hermes 进程详情列表，每项是 'PID CMD...'。"""
    out, _, _ = run("pgrep -af 'hermes' 2>/dev/null | grep -v pgrep", check=False)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines


def start_hermes_window() -> None:
    """开一个新的 WSL 终端窗口跑 hermes。"""
    cfg = settings.load_config()
    distro = cfg["wsl_distro"]
    terminal = cfg.get("terminal", "auto")

    # 强制 wsl.exe 用交互模式并执行 hermes
    # 用 `bash -ic` 让它加载 .bashrc（PATH 才会配上 ~/.local/bin）
    inner = "hermes"

    if terminal == "wt":
        # 优先用 Windows Terminal
        try:
            subprocess.Popen(
                ["wt.exe", "-d", "~", "wsl.exe", "-d", distro, "--", "bash", "-ic", inner],
                shell=False,
            )
            return
        except FileNotFoundError:
            pass  # 回退到 cmd
    # 默认用 cmd /c start 弹新窗口
    # 注意：cmd /c start 第一个带引号的参数是窗口标题
    subprocess.Popen(
        f'start "Hermes" wsl.exe -d {distro} -- bash -ic "{inner}"',
        shell=True,
    )


def hermes_model_list() -> list:
    """调用 hermes-model list，解析成 [{name, description, current}, ...]。"""
    out, err, rc = run("hermes-model list", check=False)
    if rc != 0:
        raise RuntimeError(f"hermes-model list 失败:\n{err or out}")
    profiles = []
    for line in out.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        is_current = line.lstrip().startswith("*")
        cleaned = line.lstrip().lstrip("*").strip()
        if not cleaned:
            continue
        parts = cleaned.split(None, 1)
        if not parts:
            continue
        name = parts[0]
        desc = parts[1] if len(parts) > 1 else ""
        profiles.append({"name": name, "description": desc, "current": is_current})
    return profiles


def hermes_model_current() -> str:
    """返回当前 profile 名字，失败时返回空串。"""
    out, _, rc = run("hermes-model current", check=False)
    if rc != 0:
        return ""
    return out.strip()


def hermes_model_switch(name: str, no_test: bool = False, yes: bool = True) -> Tuple[bool, str]:
    """切换 profile。返回 (success, combined_output)。"""
    parts = ["hermes-model", "switch", shlex.quote(name)]
    if no_test:
        parts.append("--no-test")
    if yes:
        parts.append("-y")
    cmd = " ".join(parts)
    out, err, rc = run(cmd, timeout=120, check=False)
    return rc == 0, (out + err).strip()


def show_profile(name: str) -> str:
    """hermes-model show <name>，原文返回。"""
    out, err, rc = run(f"hermes-model show {shlex.quote(name)}", check=False)
    return out + err


# ---------------- 环境探测 ----------------

def check_wsl_available() -> tuple:
    """检查 WSL 是否安装且有发行版。

    返回 (ok, message):
      ok=True  -> 发行版已就绪（message 是 wsl -l -v 的输出）
      ok=False -> message 给出原因

    注意：wsl -l -v 输出是 UTF-16 LE。
    """
    try:
        result = subprocess.run(
            ["wsl.exe", "-l", "-v"],
            capture_output=True, timeout=10,
        )
    except FileNotFoundError:
        return False, "系统里找不到 wsl.exe。\n\n请先启用 WSL：\n  1. 控制面板 → 程序 → 启用或关闭 Windows 功能\n  2. 勾选「适用于 Linux 的 Windows 子系统」\n  3. 点确定，等安装完，重启电脑\n  4. 重启后打开 Microsoft Store，搜索 Ubuntu 并安装"
    except subprocess.TimeoutExpired:
        return False, "调用 wsl.exe 超时（WSL 服务没起来）。\n\n请打开 PowerShell 跑 `wsl --status` 看具体报错。"
    except Exception as e:
        return False, f"无法启动 wsl.exe: {e}"
    if result.returncode != 0:
        return False, (
            f"wsl.exe 返回错误（代码 {result.returncode}），可能没装任何 WSL 发行版。\n\n"
            f"请打开 Microsoft Store 装一个 Ubuntu（推荐 22.04 或 24.04），\n"
            f"装好后启动一次让用户初始化完成，再回来重试。\n\n"
            f"--- 原始输出 ---\n{result.stdout}\n{result.stderr}"
        )
    # UTF-16 LE 解码
    try:
        text = result.stdout.decode("utf-16")
    except UnicodeDecodeError:
        text = result.stdout.decode("utf-8", errors="replace")
    # 检查是否真的有发行版（去掉表头那行）
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 2:  # 只有表头 = 没装发行版
        return False, (
            "WSL 已启用，但没装任何发行版。\n\n"
            "请打开 Microsoft Store 装一个 Ubuntu（推荐 22.04 或 24.04），\n"
            "装好后启动一次让用户初始化完成，再回来重试。"
        )
    return True, text


def detect_wsl_user(distro: Optional[str] = None) -> str:
    """自动检测 WSL 默认用户。失败返回空串。"""
    cfg_distro = (distro or settings.load_config().get("wsl_distro", "Ubuntu") or "").strip()
    # 清理可能残留的 UTF-16 字符
    cfg_distro = cfg_distro.replace("\x00", "").strip()
    if not cfg_distro:
        cfg_distro = "Ubuntu"
    try:
        # 跑一个 `whoami`，强制非交互
        result = subprocess.run(
            ["wsl.exe", "-d", cfg_distro, "--", "bash", "-c", "whoami"],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            # bash -c 输出是普通 UTF-8
            user = result.stdout.decode("utf-8", errors="replace").strip()
            if user and user != "root":
                return user
    except Exception:
        pass
    return ""


def detect_hermes_install(distro: Optional[str] = None) -> dict:
    """自动探测 hermes 安装位置。

    返回 dict 形如:
      {
        "user": "<wsl_username>",              # 自动检测到的 WSL 用户
        "hermes_home": "/home/<user>/.hermes",  # 实际存在的目录
        "hermes_model_script": "/home/<user>/.local/bin/hermes-model",  # 实际存在的脚本
        "version": "<x.y.z>",                  # 若可读到
      }
    """
    cfg = settings.load_config()
    distro = distro or cfg.get("wsl_distro", "Ubuntu")
    user = cfg.get("wsl_user") or detect_wsl_user(distro)
    if not user:
        return {"user": "", "hermes_home": "", "hermes_model_script": "", "version": ""}

    info = {"user": user, "hermes_home": "", "hermes_model_script": "", "version": ""}

    # 检查 ~ 展开
    out, _, rc = run("echo $HOME", timeout=10, check=False)
    if rc == 0 and out.strip():
        home = out.strip()
        info["hermes_home"] = f"{home}/.hermes"

    # 检查 hermes-model 脚本
    candidates = [
        f"/home/{user}/.local/bin/hermes-model",
        "/usr/local/bin/hermes-model",
        "/usr/bin/hermes-model",
    ]
    for c in candidates:
        if file_exists(c):
            info["hermes_model_script"] = c
            break

    # 检查 hermes 二进制
    hermes_bin = ""
    for c in [f"/home/{user}/.local/bin/hermes", "/usr/local/bin/hermes", "/usr/bin/hermes"]:
        if file_exists(c):
            hermes_bin = c
            break

    # 读版本
    if hermes_bin:
        out, _, rc = run(f"{hermes_bin} --version 2>&1 | head -1", timeout=10, check=False)
        if rc == 0 and out.strip():
            info["version"] = out.strip()

    return info


def read_hermes_config() -> dict:
    """从 ~/.hermes/config.yaml 读当前激活的 profile（如果存在）。

    返回:
      {"profile": "deepseek-v4-pro", "model": "deepseek-v4-pro", "base_url": "..."}
    没有则返回空 dict。
    """
    cfg = settings.load_config()
    script_path = cfg.get("hermes_model_script", "~/.local/bin/hermes-model")
    # 用 hermes-model current
    out, _, rc = run("hermes-model current", timeout=10, check=False)
    if rc == 0 and out.strip():
        return {"profile": out.strip()}
    return {}
