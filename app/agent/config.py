# -*- coding: utf-8 -*-
"""暖眸 配置管理：config.json（本地保存，含用户提供的 AI 服务 Key）。"""

from __future__ import annotations

import copy
import json
import os
from typing import Dict

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.environ.get("APP_CONFIG_PATH", os.path.join(APP_DIR, "config.json"))

DEFAULTS: Dict = {
    "agent": {
        "elder_name": "王奶奶",
        "agent_name": "暖眸",
        "timezone": "Asia/Shanghai",
    },
    "llm": {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "vision_supported": True,
        "temperature": 0.3,
    },
    "medication_plan": [
        {"name": "降压药", "time": "08:00", "dose": "1粒/日"}
    ],
    "weather": {
        "city": "广州",
        "api_key": "",
    },
    "family_webhook": "",
}


def _deep_merge(base: Dict, patch: Dict) -> Dict:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str = CONFIG_PATH) -> Dict:
    cfg = copy.deepcopy(DEFAULTS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg = _deep_merge(cfg, saved)
        except Exception:
            pass
    return cfg


def save_config(cfg: Dict, path: str = CONFIG_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def public_config(cfg: Dict) -> Dict:
    """对外暴露的配置：隐藏所有 Key。"""
    out = copy.deepcopy(cfg)
    llm = out.setdefault("llm", {})
    llm.pop("api_key", None)
    llm["has_key"] = bool(cfg.get("llm", {}).get("api_key"))
    weather = out.setdefault("weather", {})
    weather.pop("api_key", None)
    weather["has_key"] = bool(cfg.get("weather", {}).get("api_key"))
    out["family_webhook"] = "已配置" if cfg.get("family_webhook") else ""
    return out
