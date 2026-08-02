"""用户个性化配置（从 InfraCoder 移植的最小版本）。

配置文件：~/.veriforge/config.json
- preferred_model: 覆盖 .env 的模型名
- output_style: default / concise / detailed / bullet
- disabled_tools: 从工具白名单中移除的工具名
- preferred_language: chinese / english
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class UserConfig:
    def __init__(self, username: str | None = None):
        self.username = username or os.environ.get("VERIFORGE_USER") or os.environ.get("USER") or "default"
        self.preferred_model: str | None = None
        self.output_style: str = "default"
        self.disabled_tools: list[str] = []
        self.preferred_language: str = "chinese"
        self._load()

    @property
    def config_path(self) -> Path:
        return Path.home() / ".veriforge" / f"{self.username}.json"

    def _load(self):
        if not self.config_path.exists():
            return
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.preferred_model = data.get("preferred_model") or self.preferred_model
            self.output_style = data.get("output_style", self.output_style)
            self.disabled_tools = data.get("disabled_tools", self.disabled_tools)
            self.preferred_language = data.get("preferred_language", self.preferred_language)
        except (json.JSONDecodeError, OSError):
            pass

    def describe(self) -> str:
        return (
            f"User: {self.username} | Model: {self.preferred_model or '(env)'} | "
            f"Style: {self.output_style} | Language: {self.preferred_language}"
        )


def load_user_config() -> UserConfig:
    """加载用户配置，不存在时返回默认配置。"""
    return UserConfig()
