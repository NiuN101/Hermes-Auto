"""主窗口。"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from . import settings
from . import wsl_bridge
from .config_window import ConfigWindow


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Hermes 启动器")
        self.root.geometry(settings.load_config()["window_geometry"])
        self.root.minsize(480, 540)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        # 启动后做一次环境检查
        self.root.after(100, self._preflight)

    # ---------------- UI ----------------

    def _build_ui(self):
        # 标题
        header = tk.Frame(self.root, bg="#1f2937", height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="Hermes 启动器",
            bg="#1f2937", fg="white",
            font=("Microsoft YaHei", 16, "bold"),
        ).pack(side="left", padx=16, pady=14)
        tk.Label(
            header, text="WSL + 模型管理",
            bg="#1f2937", fg="#9ca3af",
            font=("Microsoft YaHei", 10),
        ).pack(side="left", padx=4, pady=18)

        # 状态条
        status_frame = tk.Frame(self.root, bg="#f3f4f6", height=80)
        status_frame.pack(fill="x")
        status_frame.pack_propagate(False)
        self.status_text = tk.StringVar(value="正在检查 Hermes 状态…")
        self.current_model = tk.StringVar(value="—")
        tk.Label(
            status_frame, textvariable=self.status_text,
            bg="#f3f4f6", fg="#111827",
            font=("Microsoft YaHei", 11),
        ).pack(anchor="w", padx=16, pady=(10, 0))
        tk.Label(
            status_frame, text="当前模型:",
            bg="#f3f4f6", fg="#6b7280",
            font=("Microsoft YaHei", 10),
        ).pack(side="left", padx=(16, 4), pady=(4, 8))
        tk.Label(
            status_frame, textvariable=self.current_model,
            bg="#f3f4f6", fg="#111827",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(side="left", pady=(4, 8))

        # 按钮区
        btn_outer = tk.Frame(self.root)
        btn_outer.pack(fill="both", expand=True, padx=24, pady=18)

        # 按钮 1：使用当前模型运行（改名）
        self.btn_run = self._big_button(
            btn_outer, "使用当前模型运行",
            color="#2563eb", hover="#1d4ed8",
            command=self._on_run_current,
        )
        self.btn_run.pack(fill="x", pady=6, ipady=10)

        # 按钮 2：切换模型
        self.btn_switch = self._big_button(
            btn_outer, "切换模型",
            color="#059669", hover="#047857",
            command=self._on_switch,
        )
        self.btn_switch.pack(fill="x", pady=6, ipady=10)

        # 按钮 3：配置模型
        self.btn_config = self._big_button(
            btn_outer, "配置模型",
            color="#7c3aed", hover="#6d28d9",
            command=self._on_config,
        )
        self.btn_config.pack(fill="x", pady=6, ipady=10)

        # 按钮 4：退出
        self.btn_exit = self._big_button(
            btn_outer, "退出",
            color="#dc2626", hover="#b91c1c",
            command=self._on_close,
        )
        self.btn_exit.pack(fill="x", pady=6, ipady=10)

        # 底部
        bottom = tk.Frame(self.root)
        bottom.pack(fill="x", side="bottom", padx=16, pady=8)
        ttk.Button(bottom, text="刷新状态", command=self._refresh_status).pack(side="left")
        ttk.Button(bottom, text="设置 WSL 路径", command=self._on_settings).pack(side="right")

    def _big_button(self, parent, text, color, hover, command):
        """返回带 hover 效果的大按钮。"""
        btn = tk.Button(
            parent, text=text,
            bg=color, fg="white",
            activebackground=hover, activeforeground="white",
            font=("Microsoft YaHei", 12, "bold"),
            relief="flat", cursor="hand2",
            bd=0, command=command,
        )
        btn._default_bg = color
        btn._hover_bg = hover

        def on_enter(e):
            btn.config(bg=hover)
        def on_leave(e):
            btn.config(bg=color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    # ---------------- 环境检查 ----------------

    def _preflight(self):
        """启动后做完整环境检查：WSL / hermes-model / 路径。"""
        self.status_text.set("正在检查 WSL 环境…")

        def work():
            wsl_ok, wsl_msg = wsl_bridge.check_wsl_available()
            if not wsl_ok:
                self.root.after(0, lambda: self._on_preflight_fail("WSL 不可用", wsl_msg))
                return

            # WSL OK，看 hermes-model
            cfg = settings.load_config()
            script_path = cfg.get("hermes_model_script", "")
            if script_path and not wsl_bridge.file_exists(script_path):
                # 路径不对，弹自动检测
                detected = wsl_bridge.detect_hermes_install()
                self.root.after(0, lambda: self._on_preflight_hermes_missing(detected))
                return

            # WSL OK，hermes-model 也在，直接刷新状态
            self.root.after(0, self._refresh_status)

        threading.Thread(target=work, daemon=True).start()

    def _on_preflight_fail(self, title, msg):
        messagebox.showerror(title, msg, parent=self.root)
        self.status_text.set("● 环境未就绪")
        self.current_model.set("（不可用）")

    def _on_preflight_hermes_missing(self, detected):
        """hermes-model 路径不对，弹窗让用户选：自动检测 / 自己改。"""
        if detected.get("hermes_model_script"):
            # 自动检测到了
            new_path = detected["hermes_model_script"]
            choice = messagebox.askyesno(
                "找不到 hermes-model",
                f"配置里的路径下没找到 hermes-model，但自动检测到了：\n\n"
                f"  {new_path}\n\n"
                f"是否更新配置用这个路径？\n"
                f"（点「否」会打开手动设置窗口）",
                parent=self.root,
            )
            if choice:
                settings.update(
                    wsl_user=detected.get("user", "") or settings.load_config().get("wsl_user", ""),
                    hermes_home=detected.get("hermes_home", "") or settings.load_config().get("hermes_home", ""),
                    hermes_model_script=new_path,
                )
                self._refresh_status()
                return
        else:
            messagebox.showwarning(
                "找不到 hermes-model",
                "配置里和自动扫描都没找到 hermes-model 脚本。\n\n"
                "请确认你已经安装过 hermes（pip install hermes 或类似方式），\n"
                "然后点「设置 WSL 路径」改路径。",
                parent=self.root,
            )
        self._on_settings()
        self.status_text.set("● 请配置 WSL 路径")
        self.current_model.set("（未配置）")

    # ---------------- 行为 ----------------

    def _refresh_status(self):
        """异步检查 hermes 状态和当前模型。"""
        def work():
            try:
                count = wsl_bridge.is_hermes_running()
                procs = wsl_bridge.hermes_processes() if count else []
                current = wsl_bridge.hermes_model_current()
                self.root.after(0, self._apply_status, count, procs, current)
            except Exception as e:
                self.root.after(0, lambda: self._apply_status(0, [], ""))
                self.root.after(0, lambda: messagebox.showerror(
                    "WSL 通信失败", f"无法连接 WSL:\n{e}\n\n请确认 WSL 已安装、用户名/路径正确。"))

        threading.Thread(target=work, daemon=True).start()

    def _apply_status(self, count: int, procs: list, current: str):
        if count > 0:
            self.status_text.set(f"● Hermes 正在运行（{count} 个进程）")
        else:
            self.status_text.set("○ Hermes 未运行")
        if current:
            self.current_model.set(current)
        else:
            self.current_model.set("（未知，点击刷新重试）")

    def _on_run_current(self):
        """使用当前 profile 开一个新窗口跑 hermes。"""
        # 先快速读一次当前 profile
        current = wsl_bridge.hermes_model_current() or None
        count = wsl_bridge.is_hermes_running()
        if count > 0:
            if not messagebox.askyesno(
                "Hermes 已在运行",
                f"检测到 {count} 个 hermes 进程仍在运行（当前模型: {current or '?'}）。\n\n"
                "是否再开一个新窗口？",
            ):
                return
        try:
            wsl_bridge.start_hermes_window()
            self.status_text.set("已发送启动指令…")
            self.root.after(1500, self._refresh_status)
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def _on_switch(self):
        """弹一个选择对话框，点哪个就切到哪个。"""
        try:
            profiles = wsl_bridge.hermes_model_list()
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
            return
        if not profiles:
            messagebox.showinfo("提示", "没有任何 profile。先去「配置模型」加一个。")
            return
        # 检查 hermes 是否在跑，在跑时给提示
        running = wsl_bridge.is_hermes_running() > 0
        SwitchDialog(self.root, profiles, self._do_switch, on_after_switch=self._refresh_status, hermes_running=running)

    def _do_switch(self, name: str, no_test: bool):
        """实际切换动作（切完跑 smoke test 由 hermes-model 自己负责）。"""
        ok, out = wsl_bridge.hermes_model_switch(name, no_test=no_test, yes=True)
        if ok:
            messagebox.showinfo("切换成功", f"已切换到: {name}\n\n{out[:500]}")
            self._refresh_status()
        else:
            messagebox.showerror("切换失败", out[:1500])

    def _on_config(self):
        ConfigWindow(self.root)

    def _on_settings(self):
        SettingsDialog(self.root, on_saved=self._refresh_status)

    def _on_close(self):
        try:
            geom = self.root.geometry()
            settings.update(window_geometry=geom)
        except Exception:
            pass
        self.root.destroy()


# ---------------- 切换模型对话框 ----------------

class SwitchDialog(tk.Toplevel):
    def __init__(self, master, profiles, on_pick, on_after_switch=None, hermes_running=False):
        super().__init__(master)
        self.title("切换模型")
        self.transient(master)
        self.grab_set()
        self.on_pick = on_pick
        self.on_after_switch = on_after_switch

        self._var = tk.StringVar(value="")
        self._build(profiles, hermes_running)
        self._center(master)

    def _build(self, profiles, hermes_running):
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="选择要切换的 profile:", font=("", 11)).pack(anchor="w", pady=(0, 8))

        if hermes_running:
            ttk.Label(
                outer,
                text="⚠ Hermes 正在运行：切换 profile 后，需要在新窗口里才会用新模型。\n"
                     "（已在跑的会话不会自动 reload）",
                foreground="#b45309", font=("", 9),
            ).pack(anchor="w", pady=(0, 8))

        list_frame = ttk.Frame(outer)
        list_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(list_frame, font=("Consolas", 11), height=10)
        for p in profiles:
            label = ("● " if p["current"] else "  ") + p["name"]
            if p.get("description"):
                label += f"   — {p['description']}"
            self.listbox.insert("end", label)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.bind("<Double-1>", lambda e: self._confirm())

        # 默认选中当前
        for i, p in enumerate(profiles):
            if p["current"]:
                self.listbox.selection_set(i)
                self.listbox.see(i)
                break

        self.no_test_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            outer, text="切换后跳过 smoke test（--no-test）",
            variable=self.no_test_var,
        ).pack(anchor="w", pady=(8, 0))

        btn_frame = ttk.Frame(outer)
        btn_frame.pack(fill="x", pady=(12, 0))
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="切换", command=self._confirm).pack(side="right", padx=4)

    def _center(self, master):
        self.update_idletasks()
        w, h = 520, 400
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def _confirm(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "选一个再确认。", parent=self)
            return
        # 去掉前缀 "● " 或 "  "
        label = self.listbox.get(sel[0])
        name = label[2:].split("   ")[0].strip()
        no_test = self.no_test_var.get()
        self.destroy()
        if self.on_pick:
            self.on_pick(name, no_test)


# ---------------- 设置对话框 ----------------

class SettingsDialog(tk.Toplevel):
    def __init__(self, master, on_saved=None):
        super().__init__(master)
        self.title("WSL 路径设置")
        self.transient(master)
        self.grab_set()
        self.on_saved = on_saved

        cfg = settings.load_config()
        self._vars = {
            k: tk.StringVar(value=cfg.get(k, "")) for k in
            ("wsl_distro", "wsl_user", "hermes_home", "hermes_model_script", "terminal")
        }

        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        rows = [
            ("wsl_distro", "WSL 发行版名（PowerShell: wsl -l -v）"),
            ("wsl_user", "WSL 用户名（首次运行会自动检测）"),
            ("hermes_home", "Hermes 主目录（WSL 内路径）"),
            ("hermes_model_script", "hermes-model 脚本路径（WSL 内路径）"),
            ("terminal", "终端类型：auto / wt / cmd"),
        ]
        for i, (k, label) in enumerate(rows):
            ttk.Label(outer, text=label + ":").grid(row=i, column=0, sticky="w", padx=4, pady=4)
            ttk.Entry(outer, textvariable=self._vars[k], width=50).grid(
                row=i, column=1, sticky="ew", padx=4, pady=4)
        outer.columnconfigure(1, weight=1)

        # 重新自动检测按钮
        detect_row = ttk.Frame(outer)
        detect_row.grid(row=len(rows), column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(detect_row, text="重新自动检测 WSL", command=self._detect).pack(side="left")

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=len(rows) + 1, column=0, columnspan=2, pady=(12, 0), sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        ttk.Button(btn_frame, text="取消", command=self.destroy).grid(row=0, column=0, sticky="e", padx=4)
        ttk.Button(btn_frame, text="保存", command=self._save).grid(row=0, column=1, sticky="w", padx=4)

        self.update_idletasks()
        w, h = 640, 320
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def _detect(self):
        """重新跑自动检测，覆盖表单。"""
        detected = wsl_bridge.detect_hermes_install(distro=self._vars["wsl_distro"].get())
        if detected.get("user"):
            self._vars["wsl_user"].set(detected["user"])
        if detected.get("hermes_home"):
            self._vars["hermes_home"].set(detected["hermes_home"])
        if detected.get("hermes_model_script"):
            self._vars["hermes_model_script"].set(detected["hermes_model_script"])
        if detected.get("user"):
            messagebox.showinfo(
                "检测完成",
                f"用户名: {detected['user']}\n"
                f"hermes-model: {detected['hermes_model_script'] or '(没找到)'}\n"
                f"版本: {detected.get('version') or '(未知)'}",
                parent=self,
            )
        else:
            messagebox.showwarning("检测失败", "没找到 WSL 用户，请手动填写。", parent=self)

    def _save(self):
        cfg = {k: v.get().strip() for k, v in self._vars.items()}
        # 同步拼 hermes_home
        if cfg["wsl_user"] and not cfg["hermes_home"]:
            cfg["hermes_home"] = f"/home/{cfg['wsl_user']}/.hermes"
        settings.save_config(cfg)
        if self.on_saved:
            self.on_saved()
        self.destroy()


def main():
    root = tk.Tk()
    # 稍微美化
    try:
        root.tk.call("source", "sun-valley.tcl")
    except tk.TclError:
        pass
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    elif "clam" in style.theme_names():
        style.theme_use("clam")

    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
