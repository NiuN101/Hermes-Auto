"""模型配置对话框：增 / 改 / 删 profile。"""
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable

from . import profile_manager


class ProfileEditDialog(tk.Toplevel):
    """新增 / 编辑 profile 的表单。"""

    def __init__(self, master, title: str, initial: Optional[dict] = None,
                 on_save: Optional[Callable[[dict], None]] = None):
        super().__init__(master)
        self.title(title)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        self.on_save = on_save
        self._initial = initial or {}
        self._vars = {}

        self._build_ui()
        self._populate()

        # 居中
        self.update_idletasks()
        w, h = 640, 640
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def _build_ui(self):
        # 滚动容器
        canvas = tk.Canvas(self, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        outer = ttk.Frame(canvas, padding=12)
        canvas_window = canvas.create_window((0, 0), window=outer, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfigure(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_outer_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        outer.bind("<Configure>", _on_outer_configure)

        def _on_mousewheel(event):
            # Windows / Mac
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        # profile name
        ttk.Label(outer, text="Profile 名（英文/数字/-/_，用作 key）:").grid(
            row=0, column=0, sticky="w", padx=4, pady=4)
        self._vars["name"] = tk.StringVar()
        name_entry = ttk.Entry(outer, textvariable=self._vars["name"], width=50)
        name_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        # 表单字段
        row = 1
        for key, label, hint in profile_manager.PROFILE_FIELDS:
            ttk.Label(outer, text=f"{label}:").grid(
                row=row, column=0, sticky="w", padx=4, pady=(4, 0))
            self._vars[key] = tk.StringVar()
            ent = ttk.Entry(outer, textvariable=self._vars[key])
            ent.grid(row=row, column=1, sticky="ew", padx=4, pady=(4, 0))
            # hint 放下一行，不和 Entry 抢格子
            ttk.Label(outer, text=hint, foreground="#888",
                      font=("", 8)).grid(
                row=row + 1, column=1, sticky="w", padx=4, pady=(0, 4))
            row += 2

        outer.columnconfigure(1, weight=1)

        # 按钮区
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=12)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ttk.Button(btn_frame, text="取消", command=self.destroy).grid(
            row=0, column=0, sticky="e", padx=4)
        ttk.Button(btn_frame, text="保存", command=self._on_save).grid(
            row=0, column=1, sticky="w", padx=4)

        # 快捷键
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-Return>", lambda e: self._on_save())

    def _populate(self):
        if not self._initial:
            return
        # 名字
        self._vars["name"].set(self._initial.get("name", ""))
        # 字段
        fields = self._initial.get("fields", {})
        for k in self._vars:
            if k == "name":
                continue
            self._vars[k].set(fields.get(k, ""))

        # 编辑模式下名字不可改（因为是 key）
        if "name" in self._initial and self._initial.get("editing", False):
            for child in self.winfo_children():
                self._disable_name_entry()

    def _disable_name_entry(self):
        # 简单做法：找到第一个 Entry，禁用
        for child in self.winfo_children():
            for sub in child.winfo_children():
                if isinstance(sub, ttk.Entry):
                    sub.configure(state="disabled")
                    return

    def _on_save(self):
        name = self._vars["name"].get().strip()
        if not name:
            messagebox.showerror("错误", "Profile 名不能为空。", parent=self)
            return
        if not all(c.isalnum() or c in "-_." for c in name):
            messagebox.showerror(
                "错误", "Profile 名只能用字母数字和 - _ .", parent=self)
            return

        fields = {k: v.get() for k, v in self._vars.items() if k != "name"}

        # 转成 PROFILES 字典格式
        try:
            script_fields = profile_manager.fields_to_script(fields)
        except ValueError as e:
            messagebox.showerror("字段错误", str(e), parent=self)
            return

        if self.on_save:
            try:
                self.on_save({"name": name, "fields": script_fields, "raw_fields": fields})
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=self)
                return
        self.destroy()


class ConfigWindow(tk.Toplevel):
    """配置模型：左侧列表，右侧操作按钮。"""

    def __init__(self, master):
        super().__init__(master)
        self.title("配置模型 - Hermes")
        self.geometry("780x520")
        self.transient(master)

        # 居中
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - 780) // 2
        y = master.winfo_rooty() + (master.winfo_height() - 520) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="刷新", command=self._refresh_list).pack(side="left", padx=2)
        ttk.Button(toolbar, text="新增", command=self._on_add).pack(side="left", padx=2)
        ttk.Button(toolbar, text="导入导出", command=self._on_import_export).pack(side="left", padx=2)
        ttk.Button(toolbar, text="编辑", command=self._on_edit).pack(side="left", padx=2)
        ttk.Button(toolbar, text="删除", command=self._on_delete).pack(side="left", padx=2)
        ttk.Button(toolbar, text="查看原文", command=self._on_view).pack(side="left", padx=2)
        ttk.Button(toolbar, text="关闭", command=self.destroy).pack(side="right", padx=2)

        # 列表
        body = ttk.Frame(self, padding=(8, 0))
        body.pack(fill="both", expand=True)

        cols = ("name", "model", "provider", "base_url")
        self.tree = ttk.Treeview(body, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Profile")
        self.tree.heading("model", text="Model ID")
        self.tree.heading("provider", text="Provider")
        self.tree.heading("base_url", text="Base URL")
        self.tree.column("name", width=160)
        self.tree.column("model", width=200)
        self.tree.column("provider", width=80)
        self.tree.column("base_url", width=280)
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self._on_edit())

        # 状态栏
        self.status = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status, anchor="w",
                  relief="sunken", padding=(6, 2)).pack(fill="x", side="bottom")

    def _set_status(self, msg: str, error: bool = False):
        self.status.set(msg)
        self.status_label_error = error  # 颜色保留位
        # 简单起见不染色

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        try:
            profiles = profile_manager.parse_profiles()
        except Exception as e:
            messagebox.showerror("读取失败", str(e), parent=self)
            return

        for name, info in profiles.items():
            self.tree.insert(
                "", "end", iid=name,
                values=(name, info.get("default", ""),
                        info.get("provider", ""), info.get("base_url", "")))
        self._set_status(f"共 {len(profiles)} 个 profile")

    def _selected_name(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _on_add(self):
        def on_save(data):
            profile_manager.add_profile(data["name"], data["fields"])
            self._refresh_list()

        ProfileEditDialog(self, "新增 Profile", on_save=on_save)

    def _on_import_export(self):
        ImportExportDialog(self, on_imported=self._refresh_list)

    def _on_edit(self):
        name = self._selected_name()
        if not name:
            messagebox.showinfo("提示", "请先选一个 profile。", parent=self)
            return
        profile = profile_manager.get_profile(name)
        raw = profile_manager.fields_from_script(profile)
        initial = {"name": name, "fields": raw, "editing": True}

        def on_save(data):
            new_name = data["name"]
            if new_name != name:
                profile_manager.rename_profile(name, new_name)
            profile_manager.update_profile(new_name, data["fields"])
            self._refresh_list()

        ProfileEditDialog(self, f"编辑 Profile - {name}", initial=initial, on_save=on_save)

    def _on_delete(self):
        name = self._selected_name()
        if not name:
            messagebox.showinfo("提示", "请先选一个 profile。", parent=self)
            return
        if not messagebox.askyesno("确认删除", f"确定要删除 '{name}' 吗？\n（会先备份脚本再写回）", parent=self):
            return
        try:
            profile_manager.delete_profile(name)
        except Exception as e:
            messagebox.showerror("删除失败", str(e), parent=self)
            return
        self._refresh_list()

    def _on_view(self):
        name = self._selected_name()
        if not name:
            return
        try:
            from . import wsl_bridge
            text = wsl_bridge.show_profile(name)
        except Exception as e:
            messagebox.showerror("查看失败", str(e), parent=self)
            return
        ViewDialog(self, f"Profile 详情 - {name}", text)


class ViewDialog(tk.Toplevel):
    """只读展示一段文本（用于查看 profile 原文 / YAML 等）。"""

    def __init__(self, master, title: str, text: str):
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.geometry("640x420")

        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - 640) // 2
        y = master.winfo_rooty() + (master.winfo_height() - 420) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        outer = ttk.Frame(self, padding=8)
        outer.pack(fill="both", expand=True)

        txt = tk.Text(outer, wrap="none", font=("Consolas", 10))
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(outer, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)

        ttk.Button(self, text="关闭", command=self.destroy).pack(pady=6)


# ---------------- 导入/导出 ----------------

# 字段约定（跟 fields_to_script / fields_from_script 对齐）
_REQUIRED_FIELDS = ("default", "provider", "base_url", "max_output_tokens", "context_window")
_OPTIONAL_FIELDS = ("desc", "api_key_env", "extra_body")
_BOOL_TO_PY = {True: "True", False: "False", None: "None"}


def _json_default(obj):
    """把 Python 字面量值（True/False/None）转成 JSON 兼容。"""
    if obj is True:
        return "true"  # 故意走字符串占位，下面 _dumps_to_python 反向转
    if obj is False:
        return "false"
    if obj is None:
        return "null"
    raise TypeError(f"unsupported: {type(obj)}")


def _profile_to_jsonable(profile: dict) -> dict:
    """把 PROFILES 里的 profile 转成 JSON 友好的 dict。

    api_key_env=None 变成 null
    extra_body 里的 True/False/None 保留语义（JSON true/false/null）
    """
    out = dict(profile)
    if "api_key_env" in out and out["api_key_env"] is None:
        out["api_key_env"] = None
    return out


def _jsonable_to_profile(d: dict) -> dict:
    """JSON-friendly dict -> 写入 PROFILES 用的 dict。"""
    out = dict(d)
    if "api_key_env" in out and out["api_key_env"] in ("", None):
        out["api_key_env"] = None
    return out


def _validate_profile(name: str, fields: dict) -> list:
    """返回错误信息列表，空列表表示合法。"""
    errs = []
    if not isinstance(fields, dict):
        return [f"profile '{name}' 不是对象"]
    for k in _REQUIRED_FIELDS:
        if k not in fields:
            errs.append(f"profile '{name}' 缺必填字段: {k}")
    if "max_output_tokens" in fields and not isinstance(fields["max_output_tokens"], int):
        errs.append(f"profile '{name}': max_output_tokens 必须是整数")
    if "context_window" in fields and not isinstance(fields["context_window"], int):
        errs.append(f"profile '{name}': context_window 必须是整数")
    if "extra_body" in fields and not isinstance(fields["extra_body"], dict):
        errs.append(f"profile '{name}': extra_body 必须是对象")
    if "api_key_env" in fields and fields["api_key_env"] is not None \
            and not isinstance(fields["api_key_env"], str):
        errs.append(f"profile '{name}': api_key_env 必须是字符串或 null")
    return errs


class ImportExportDialog(tk.Toplevel):
    """导入/导出配置。

    文本框里放的是 JSON（pretty-printed，UTF-8，可直接编辑）。
    5 个动作：
      - 复制到剪贴板
      - 保存到文件…
      - 从文件加载…
      - 导入（解析文本框里的 JSON 并写入 PROFILES）
      - 关闭
    """

    def __init__(self, master, on_imported: Optional[Callable] = None):
        super().__init__(master)
        self.title("导入 / 导出配置")
        self.transient(master)
        self.geometry("780x600")
        self.on_imported = on_imported

        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - 780) // 2
        y = master.winfo_rooty() + (master.winfo_height() - 600) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self._build_ui()
        self._load_current()

    def _build_ui(self):
        # 顶部说明
        tip = ttk.Frame(self, padding=(10, 8))
        tip.pack(fill="x")
        ttk.Label(
            tip,
            text="下面是所有 profile 的 JSON 表达。\n"
                 "可以编辑后点「导入」写回；也可以「保存到文件」/「从文件加载」做备份和恢复。\n"
                 "api_key_env: null 表示本地无 key；extra_body 是对象，可空。",
            justify="left",
        ).pack(anchor="w")

        # 文本编辑区
        body = ttk.Frame(self, padding=(10, 0))
        body.pack(fill="both", expand=True)

        self.text = tk.Text(body, wrap="none", font=("Consolas", 10), undo=True)
        self.text.pack(side="left", fill="both", expand=True)

        sb_y = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        sb_y.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb_y.set)

        sb_x = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        sb_x.pack(fill="x")
        self.text.configure(xscrollcommand=sb_x.set)

        # 按钮
        btn = ttk.Frame(self, padding=10)
        btn.pack(fill="x")
        ttk.Button(btn, text="重新加载当前配置", command=self._load_current).pack(side="left", padx=2)
        ttk.Button(btn, text="复制到剪贴板", command=self._copy).pack(side="left", padx=2)
        ttk.Button(btn, text="保存到文件…", command=self._save_file).pack(side="left", padx=2)
        ttk.Button(btn, text="从文件加载…", command=self._load_file).pack(side="left", padx=2)
        ttk.Button(btn, text="导入", command=self._do_import).pack(side="left", padx=2)
        ttk.Button(btn, text="关闭", command=self.destroy).pack(side="right", padx=2)

        # 状态
        self.status = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status, anchor="w",
                  relief="sunken", padding=(6, 2)).pack(fill="x", side="bottom")

    def _set_status(self, msg: str):
        self.status.set(msg)

    def _load_current(self):
        """把当前 PROFILES 加载到文本框。"""
        try:
            profiles = profile_manager.parse_profiles()
        except Exception as e:
            messagebox.showerror("读取失败", str(e), parent=self)
            return
        data = {name: _profile_to_jsonable(info) for name, info in profiles.items()}
        text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self._set_status(f"已加载 {len(data)} 个 profile")

    def _copy(self):
        content = self.text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)
        self._set_status(f"已复制 {len(content)} 字符到剪贴板")

    def _save_file(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="保存配置到文件",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialfile="hermes-profiles.json",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=self)
            return
        self._set_status(f"已保存到: {path}")

    def _load_file(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="从文件加载配置",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("读取失败", str(e), parent=self)
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self._set_status(f"已从 {path} 加载（未导入，点「导入」才写回）")

    def _do_import(self):
        """把文本框里的 JSON 解析后写回 PROFILES。"""
        content = self.text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showinfo("提示", "文本框是空的。", parent=self)
            return
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON 解析失败",
                                 f"第 {e.lineno} 行第 {e.colno} 列: {e.msg}",
                                 parent=self)
            return
        if not isinstance(data, dict):
            messagebox.showerror("格式错误", "顶层必须是对象 { ... }。", parent=self)
            return

        # 校验每个 profile
        all_errs = []
        for name, fields in data.items():
            all_errs.extend(_validate_profile(name, fields))
        if all_errs:
            messagebox.showerror(
                "校验失败",
                "以下问题需要先修正再导入：\n\n" + "\n".join(all_errs),
                parent=self,
            )
            return

        # 询问冲突
        try:
            existing = profile_manager.parse_profiles()
        except Exception as e:
            messagebox.showerror("读取现有配置失败", str(e), parent=self)
            return

        conflicts = [n for n in data.keys() if n in existing]
        overwrite_all = False
        skip_all = False
        skip_set = set()
        for name in conflicts:
            if skip_all:
                skip_set.add(name)
                continue
            if overwrite_all:
                continue
            choice = messagebox.askyesnocancel(
                "冲突",
                f"profile '{name}' 已存在。\n\n"
                f"是(Y) = 覆盖    否(N) = 跳过    取消 = 中止导入",
                parent=self,
            )
            if choice is None:
                self._set_status("导入已取消")
                return
            if choice is False:
                skip_set.add(name)

        # 写入
        new_profiles = dict(existing)
        for name, fields in data.items():
            if name in skip_set:
                continue
            new_profiles[name] = _jsonable_to_profile(fields)

        try:
            profile_manager.write_profiles(new_profiles)
        except Exception as e:
            messagebox.showerror("写入失败", str(e), parent=self)
            return

        n_added = sum(1 for n in data if n not in existing and n not in skip_set)
        n_overw = sum(1 for n in data if n in existing and n not in skip_set)
        n_skipped = len(skip_set)
        self._set_status(
            f"导入完成：新增 {n_added}，覆盖 {n_overw}，跳过 {n_skipped}"
        )
        messagebox.showinfo(
            "导入成功",
            f"新增 {n_added}，覆盖 {n_overw}，跳过 {n_skipped}。\n"
            f"脚本已自动备份。",
            parent=self,
        )
        if self.on_imported:
            self.on_imported()
