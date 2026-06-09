# HermesAutoStart

> 一键启动 Hermes + 可视化管理 AI 模型配置 — Windows 桌面应用

[English](#english) | [中文](#中文)

---

## English

### What is this?

A lightweight Windows GUI launcher for [Hermes Agent](https://github.com/AI-Hermes-Project/hermes), running inside WSL Ubuntu. Double-click to launch, double-click to switch models. No CLI knowledge required.

### Why this, not the official Hermes Agent Desktop?

The official [Hermes Agent Desktop](https://github.com/AI-Hermes-Project/hermes-desktop) is great for users who want a **fully-integrated TUI experience embedded in a graphical window** — colors, streaming output, history, the works. It brings the TUI to you.

**This project is for users who prefer something simpler.** We don't embed the TUI at all. We just:

- Start a normal WSL terminal with `hermes` already running inside
- Manage `hermes-model` profiles visually (add / edit / delete / import / export)
- Switch profiles with one click

If you just want a launcher and a model switcher — and you're fine opening a separate terminal for the actual TUI — this is for you. If you want the full embedded TUI experience, use the official desktop app.

### Features

- **One-click launch** — starts a WSL terminal with `hermes` already running
- **One-click model switch** — pick a profile, click, done (smoke test included)
- **Visual profile management** — add / edit / delete / import / export profiles directly from the GUI
- **Zero dependencies** — single `.exe`, ~14 MB, no Python install required
- **Auto-detect on first run** — finds your WSL distro, username, and `hermes-model` script automatically
- **Standard config location** — settings live in `%APPDATA%\hermesStart\`, not next to the exe

### System Requirements

You need **all three** of these before installing:

| Component | Minimum | Recommended | How to install |
|-----------|---------|-------------|----------------|
| **Windows** | Windows 10 (1809+) | Windows 11 | — |
| **WSL** | WSL 2 | WSL 2 | `wsl --install` in PowerShell (admin), then reboot |
| **Linux distro** | Ubuntu 22.04 (or any distro) | Ubuntu 22.04 / 24.04 | `wsl --install -d Ubuntu` |
| **Hermes Agent** | v0.15+ (must include `hermes-model` CLI) | latest | `pip install hermes-agent` (or follow [official install guide](https://github.com/AI-Hermes-Project/hermes)) |

**You do NOT need Python** to run the prebuilt `.exe`. Python is only needed if you want to build from source.

> The `hermes-model` script must be in your WSL's `~/.local/bin/` (or wherever your `PATH` points). The app auto-detects common locations on first run.

### Quick Start

1. Make sure WSL Ubuntu is set up and `hermes-model` is installed (see Requirements above)
2. Download `hermesStart.exe` from [Releases](../../releases)
3. Double-click to launch
4. First run: the app auto-detects your WSL setup. Confirm or fix the paths in **「设置 WSL 路径」** (bottom-right)
5. Click **「使用当前模型运行」** to start Hermes in a new terminal window
6. Click **「切换模型」** anytime to switch profiles

### Build from Source

```cmd
cd hermesStart
build.bat
```

Requires Python 3.10+ (only at build time). Output: `dist\hermesStart.exe`.

### Run in dev mode

```cmd
run.bat
```

### Where are my settings?

```
%APPDATA%\hermesStart\app_config.json
```

In PowerShell: `$env:APPDATA\hermesStart\app_config.json`

To reset everything: delete that file and re-launch.

### License

MIT — see [LICENSE](LICENSE)

---

## 中文

### 这是什么？

Hermes Agent（运行在 WSL Ubuntu 里）的 Windows 桌面启动器。不需要记命令，双击就能用。

### 为什么用这个，不用官方的 Hermes Agent Desktop？

官方的 [Hermes Agent Desktop](https://github.com/AI-Hermes-Project/hermes-desktop) 适合想要**把 TUI 完整嵌进窗口里**的用户——颜色、流式输出、历史记录、应有尽有，把 TUI 直接送到你面前。

**这个项目适合喜欢简洁的用户**。我们完全不嵌 TUI，只做：

- 启动一个普通的 WSL 终端，`hermes` 已经在里面跑
- 可视化地管理 `hermes-model` 的 profile（增 / 改 / 删 / 导入 / 导出）
- 一键切换 profile

如果你只想要一个启动器 + 模型切换器，不在乎单独开个终端跑 TUI——这个项目就适合你。如果你要完整的嵌入式 TUI 体验，用官方桌面版。

### 功能

- **一键启动** — 自动开一个 WSL 终端窗口，`hermes` 已经在跑
- **一键切换模型** — 选 profile → 点切换 → 完成（带 smoke test）
- **可视化 profile 管理** — 图形化增/改/删/导入/导出 profile，直接编辑 WSL 里 `hermes-model` 的 PROFILES 段，写回前自动备份
- **零依赖单文件** — `dist/hermesStart.exe` 双击即用，~14 MB，**不需要装 Python**
- **首次运行自动检测** — 自动找 WSL 发行版、用户名、`hermes-model` 路径
- **配置位置规范** — 设置存在 `%APPDATA%\hermesStart\`，不污染 exe 所在目录

### 环境要求（缺一不可）

| 组件 | 最低版本 | 推荐 | 怎么装 |
|------|----------|------|--------|
| **Windows** | Windows 10 (1809+) | Windows 11 | — |
| **WSL** | WSL 2 | WSL 2 | PowerShell（管理员）跑 `wsl --install`，重启电脑 |
| **Linux 发行版** | Ubuntu 22.04（或任何） | Ubuntu 22.04 / 24.04 | `wsl --install -d Ubuntu` |
| **Hermes Agent** | v0.15+（必须带 `hermes-model` CLI） | 最新 | `pip install hermes-agent`（或看 [官方安装指南](https://github.com/AI-Hermes-Project/hermes)） |

**预编译的 `.exe` 不需要 Python**——只有从源码 build 才需要。

> `hermes-model` 脚本要在 WSL 的 `~/.local/bin/` 下（或你的 PATH 能找到的地方）。首次运行程序会自动检测常见位置。

### 快速上手

1. 确认 WSL Ubuntu 装好，`hermes-model` 装好（看上面"环境要求"）
2. 从 [Releases](../../releases) 下载 `hermesStart.exe`
3. 双击运行
4. 首次启动程序会**自动检测** WSL 环境。如果有错，点右下角 **「设置 WSL 路径」** 修正
5. 点 **「使用当前模型运行」** 启动 Hermes（在新的终端窗口里）
6. 任何时候点 **「切换模型」** 切换 profile

### 从源码构建

```cmd
cd hermesStart
build.bat
```

需要 Python 3.10+（仅构建时需要，exe 本身不需要）。产物：`dist/hermesStart.exe`。

### 开发调试

```cmd
run.bat
```

### 配置存在哪里？

```
%APPDATA%\hermesStart\app_config.json
```

PowerShell 里看：`$env:APPDATA\hermesStart\app_config.json`

想重置一切：删掉这个文件，重新启动即可。

### 开源致谢

本项目由 [Minmax-M3](https://github.com/Minmax-M3) 协助开发。

本项目受以下项目启发并使用其生态：

- [Hermes Agent](https://github.com/AI-Hermes-Project/hermes) — LLM 本地优先 CLI agent
- [Hermes Agent Desktop](https://github.com/AI-Hermes-Project/hermes-desktop) — 官方 GUI（功能更全：嵌入 TUI）
- [Ollama](https://ollama.com) — 本地模型运行时
- [StepFun](https://platform.stepfun.com) / [DeepSeek](https://platform.deepseek.com) / [MiniMax](https://www.minimaxi.com) — 云端 LLM API

### 许可证

MIT — 详见 [LICENSE](LICENSE)
