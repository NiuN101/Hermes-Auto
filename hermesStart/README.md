# hermesStart

Windows 下的 Hermes 启动器 + 模型管理 GUI。

把 WSL 里的 `hermes-model` 脚本包成双击可用的桌面程序：

- **双击 / 启动**：自动判断 Hermes 是否在跑，没在跑就开一个新窗口启动
- **使用默认模型运行**：直接拉起 hermes
- **切换模型**：弹窗选 profile，一键切换
- **配置模型**：图形化增 / 改 / 删 profile（直接编辑 WSL 里 `~/.local/bin/hermes-model` 的 PROFILES 段，自动备份）
- **退出**

## 文件结构

```
hermesStart/
├── hermesStart.py         # 入口，双击即跑
├── run.bat                # Windows 批处理入口（推荐用这个）
├── build.bat              # 用 PyInstaller 打成 exe
├── src/
│   ├── main_window.py     # 主窗口 + 切换对话框 + 设置对话框
│   ├── config_window.py   # 「配置模型」子窗口
│   ├── profile_manager.py # 解析/编辑 PROFILES 字典
│   ├── wsl_bridge.py      # 所有与 WSL 的通信
│   └── settings.py        # 本地 app_config.json 读写
├── config/
│   └── app_config.json    # 自动生成，存 WSL 用户名/路径等
└── README.md
```

## 怎么跑（开发/调试）

```cmd
cd hermesStart
run.bat
```

或者：
```cmd
python hermesStart.py
```

需要 Python 3.10+（自带 tkinter 即可，无需额外依赖）。

## 怎么打 exe

```cmd
build.bat
```

完成后 `dist\hermesStart.exe` 就是单文件可执行程序，可以拷到任何位置双击。

## 第一次运行的配置

应用启动时如果 WSL 通信失败，点右下角 **「设置 WSL 路径」**，确认：

- `wsl_distro`：WSL 发行版名（PowerShell 跑 `wsl -l -v` 看 Default 那列）
- `wsl_user`：WSL 用户名
- `hermes_home`：`/home/<user>/.hermes`
- `hermes_model_script`：`/home/<user>/.local/bin/hermes-model`
- `terminal`：`auto` / `wt` / `cmd`
  - `auto`：有 Windows Terminal 用 wt，否则回退到 cmd
  - `wt`：强制用 Windows Terminal
  - `cmd`：强制用 `cmd /c start`

## 「配置模型」怎么用

打开后列出所有 profile（从脚本的 PROFILES 字典解析得到）。

- **新增**：填 Profile 名（key，只能字母数字 + `-_.`）+ 各项字段
- **编辑**：双击或选「编辑」，可改字段；Profile 名作为 key 不能改（如要改名字：先复制新条目，再删旧的）
- **删除**：先备份再写回（最多保留 5 个 `.bak.YYYYMMDD_HHMMSS` 备份）
- **查看原文**：`hermes-model show <name>` 的输出

> **重要**：UI 字段只覆盖常用项。如果你的 PROFILES 里有脚本才识别的自定义字段（比如 `display_name`、某些 `extra_body` 子键），直接编辑脚本保留这些字段更安全。

## 已知限制

- 启动 Hermes 是**新开一个 WSL 终端窗口**，TUI 在那里跑；GUI 本身不嵌入 TUI（嵌进去得跑 pseudoterminal，跨 WSL 边界很折腾）
- 「切换模型」会调 `hermes-model switch`，**会触发 smoke test**（默认行为）。批量切换时可在对话框里勾「跳过 smoke test」
- 当前激活 profile 的判断只看 `default + base_url`，跟脚本里 `hermes-model current` 行为一致；手动改过 config 但不通过脚本切换的，会显示「未知」

## 故障排查

| 现象 | 排查 |
|---|---|
| 启动报「WSL 通信失败」 | PowerShell 跑 `wsl -l -v` 看发行版名；点「设置 WSL 路径」改 |
| 「读取失败: 在 hermes-model 脚本里没找到 PROFILES = { ... }」 | 打开脚本，确认顶部有 `PROFILES = { ... }` 这一段，且 `PROFILES` 是 Python 字典字面量（不是 bash 数组） |
| 「PROFILES 字典解析失败」 | 脚本顶部有 `f-string` / 函数调用等 `ast.literal_eval` 不支持的东西；可以把那些项注释掉或挪到 PROFILES 之外 |
| 点了「启动 Hermes」没反应 | 试试把 `terminal` 改成 `cmd`；看是否被杀毒拦了 |
| 切换失败 | 终端跑 `hermes-model switch <name>` 看原始报错；通常是 API key 缺/失效、模型名拼错、余额用完 |
