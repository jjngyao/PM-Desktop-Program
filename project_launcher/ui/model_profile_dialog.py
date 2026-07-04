"""Dialog for creating or editing a model provider profile."""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from constants import FONT_FAMILY, FONT_SIZE_LARGE, FONT_SIZE_NORMAL, FONT_SIZE_STATUS
from model_profiles import (
    DEFAULT_API_FORMAT,
    DEFAULT_AUTH_FIELD,
    ModelMapping,
    ModelProfile,
    build_claude_settings,
    empty_model_mappings,
    validate_profile,
)


class ModelProfileDialog:
    """Modal dialog for collecting a model provider configuration."""

    def __init__(self, parent: tk.Tk, profile: Optional[ModelProfile] = None):
        self._parent = parent
        self._profile = profile or ModelProfile(name="", api_key="")
        self.result: Optional[ModelProfile] = None
        self._secret_visible = False
        self._mapping_rows: list[dict] = []

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("新建模型配置")
        self._dialog.geometry("860x720")
        self._dialog.minsize(760, 620)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build()
        self._load_profile()
        self._refresh_preview()
        self._dialog.wait_window()

    def _build(self) -> None:
        outer = ttk.Frame(self._dialog, padding=18)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(
            header,
            text="新建模型配置",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Button(header, text="取消", command=self._dialog.destroy).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        ttk.Button(header, text="保存", command=self._on_save).pack(side=tk.RIGHT)

        body = ttk.Frame(outer)
        body.pack(fill=tk.BOTH, expand=True)

        self._build_basic_section(body)
        self._build_format_section(body)
        self._build_mapping_section(body)
        self._build_advanced_section(body)
        self._build_preview_section(body)

    def _build_basic_section(self, parent) -> None:
        self.name_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.base_url_var = tk.StringVar()

        self._add_label(parent, "配置名称")
        self._entry(parent, self.name_var)

        self._add_label(parent, "API Key")
        key_row = ttk.Frame(parent)
        key_row.pack(fill=tk.X, pady=(0, 12))
        self.api_key_entry = ttk.Entry(
            key_row,
            textvariable=self.api_key_var,
            show="•",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        )
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(key_row, text="显示", command=self._toggle_secret).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        self._add_label(parent, "请求地址")
        self._entry(parent, self.base_url_var)

    def _build_format_section(self, parent) -> None:
        self.api_format_var = tk.StringVar(value=DEFAULT_API_FORMAT)
        self.auth_field_var = tk.StringVar(value=DEFAULT_AUTH_FIELD)

        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=(2, 12))

        left = ttk.Frame(row)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self._add_label(left, "API 格式")
        ttk.Combobox(
            left,
            textvariable=self.api_format_var,
            state="readonly",
            values=[DEFAULT_API_FORMAT],
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        ).pack(fill=tk.X)

        right = ttk.Frame(row)
        right.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self._add_label(right, "认证字段")
        ttk.Combobox(
            right,
            textvariable=self.auth_field_var,
            values=[DEFAULT_AUTH_FIELD, "ANTHROPIC_API_KEY"],
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        ).pack(fill=tk.X)

    def _build_mapping_section(self, parent) -> None:
        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, pady=(4, 12))
        ttk.Label(
            parent,
            text="模型映射",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            parent,
            text="显示名称用于 Claude Code 菜单；实际请求模型用于供应商 API。",
            font=(FONT_FAMILY, FONT_SIZE_STATUS),
            foreground="#666666",
        ).pack(anchor=tk.W, pady=(2, 8))

        header = ttk.Frame(parent)
        header.pack(fill=tk.X)
        for label, width in (("模型角色", 14), ("显示名称", 28), ("实际请求模型", 28), ("支持 1M", 10)):
            ttk.Label(header, text=label, width=width).pack(side=tk.LEFT, padx=(0, 8))

        for mapping in self._mappings_for_form():
            self._add_mapping_row(parent, mapping)

    def _mappings_for_form(self) -> list[ModelMapping]:
        rows = empty_model_mappings()
        by_role = {mapping.role: mapping for mapping in rows}
        for mapping in self._profile.mappings:
            if mapping.role in by_role:
                by_role[mapping.role] = mapping
            else:
                rows.append(mapping)
        return [by_role.get(mapping.role, mapping) for mapping in rows]

    def _build_advanced_section(self, parent) -> None:
        self.default_model_var = tk.StringVar()
        self.user_agent_var = tk.StringVar()

        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, pady=(12, 12))
        self._add_label(parent, "默认兜底模型")
        self._entry(parent, self.default_model_var)

        self._add_label(parent, "自定义 User-Agent")
        self._entry(parent, self.user_agent_var)

    def _build_preview_section(self, parent) -> None:
        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, pady=(12, 12))
        ttk.Label(
            parent,
            text="配置 JSON 预览",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
        ).pack(anchor=tk.W)
        self.preview_text = tk.Text(
            parent,
            height=10,
            font=("Consolas", FONT_SIZE_STATUS),
            wrap=tk.NONE,
            bg="#f7f9fc",
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        for var in (
            self.name_var,
            self.api_key_var,
            self.base_url_var,
            self.api_format_var,
            self.auth_field_var,
            self.default_model_var,
            self.user_agent_var,
        ):
            var.trace_add("write", lambda *_: self._refresh_preview())

    def _add_mapping_row(self, parent, mapping: ModelMapping) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=3)

        role_var = tk.StringVar(value=mapping.role)
        display_var = tk.StringVar(value=mapping.display_name)
        request_var = tk.StringVar(value=mapping.request_model)
        supports_var = tk.BooleanVar(value=mapping.supports_1m)

        ttk.Label(row, textvariable=role_var, width=14).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(row, textvariable=display_var, width=30).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(row, textvariable=request_var, width=30).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Checkbutton(row, variable=supports_var).pack(side=tk.LEFT)

        for var in (display_var, request_var, supports_var):
            var.trace_add("write", lambda *_: self._refresh_preview())

        self._mapping_rows.append({
            "role": role_var,
            "display": display_var,
            "request": request_var,
            "supports": supports_var,
        })

    def _entry(self, parent, variable: tk.StringVar) -> ttk.Entry:
        entry = ttk.Entry(parent, textvariable=variable, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        entry.pack(fill=tk.X, pady=(0, 12))
        return entry

    def _add_label(self, parent, text: str) -> None:
        ttk.Label(parent, text=text, font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(
            anchor=tk.W, pady=(0, 4)
        )

    def _load_profile(self) -> None:
        self.name_var.set(self._profile.name)
        self.api_key_var.set(self._profile.api_key)
        self.base_url_var.set(self._profile.base_url)
        self.api_format_var.set(self._profile.api_format or DEFAULT_API_FORMAT)
        self.auth_field_var.set(self._profile.auth_field or DEFAULT_AUTH_FIELD)
        self.default_model_var.set(self._profile.default_model)
        self.user_agent_var.set(self._profile.user_agent)

    def _collect_profile(self) -> ModelProfile:
        mappings = [
            ModelMapping(
                row["role"].get(),
                row["display"].get().strip(),
                row["request"].get().strip(),
                row["supports"].get(),
            )
            for row in self._mapping_rows
        ]
        return ModelProfile(
            name=self.name_var.get().strip(),
            api_key=self.api_key_var.get().strip(),
            base_url=self.base_url_var.get().strip(),
            api_format=self.api_format_var.get().strip(),
            auth_field=self.auth_field_var.get().strip(),
            default_model=self.default_model_var.get().strip(),
            user_agent=self.user_agent_var.get().strip(),
            mappings=mappings,
        )

    def _refresh_preview(self) -> None:
        if not hasattr(self, "preview_text"):
            return
        profile = self._collect_profile()
        preview = build_claude_settings(
            {"autoUpdatesChannel": "latest"},
            profile,
            redact_secrets=True,
        )
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", json.dumps(preview, indent=2, ensure_ascii=False))
        self.preview_text.configure(state=tk.DISABLED)

    def _toggle_secret(self) -> None:
        self._secret_visible = not self._secret_visible
        self.api_key_entry.configure(show="" if self._secret_visible else "•")

    def _on_save(self) -> None:
        profile = self._collect_profile()
        errors = validate_profile(profile)
        if errors:
            messagebox.showerror("无法保存模型配置", "\n".join(errors), parent=self._dialog)
            return
        self.result = profile
        self._dialog.destroy()
