# -*- coding: utf-8 -*-
"""暖眸 工具层：记忆检索/更新、用药计划、天气、家人通知。"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Dict, List

from .memory import MemoryStore, now_str


def run_tool(tool: str, args: Dict, memory: MemoryStore,
             config: Dict, notify_log: List[str]) -> str:
    try:
        if tool == "memory_search":
            query = (args.get("query") or "").strip()
            hits = memory.search(query)
            if not hits:
                return f"未找到与「{query}」相关的记忆"
            return "；".join(
                f"{it['object']} → {it['location']}（置信度 {it.get('confidence', 0)}）"
                for it in hits[:3]
            )
        if tool == "memory_update":
            obj = (args.get("object") or "").strip()
            if not obj:
                return "缺少 object 参数"
            loc = (args.get("location") or "").strip()
            memory.update_item(obj, loc or None, now_str(), float(args.get("confidence", 0.9)))
            memory.save()
            return f"已记录：{obj} → {loc or '未知'}"
        if tool == "medication_plan":
            plan = config.get("medication_plan", [])
            if not plan:
                return "暂无用药计划"
            return "；".join(
                f"{m.get('name')} {m.get('time')} {m.get('dose')}" for m in plan
            )
        if tool == "weather":
            return _weather(config)
        if tool == "notify_family":
            detail = (args.get("detail") or "").strip() or "家人通知"
            notify_log.append(f"[{now_str()}] {detail}")
            _webhook(config, detail)
            return f"已通知家人：{detail}"
        return f"未知工具：{tool}"
    except Exception as e:
        return f"工具执行失败：{e}"


def _weather(config: Dict) -> str:
    weather_cfg = config.get("weather", {})
    key = weather_cfg.get("api_key", "")
    city = weather_cfg.get("city", "")
    if not key:
        return "天气服务未配置（在配置页填写可选天气 Key 后可查询）"
    if not city:
        return "天气服务未配置城市"
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={urllib.parse.quote(city)}&appid={key}&units=metric&lang=zh_cn"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"{city}：{desc}，{temp}°C"
    except Exception:
        return "天气获取失败（请检查网络或 Key）"


def _webhook(config: Dict, detail: str) -> None:
    url = (config.get("family_webhook") or "").strip()
    if not url:
        return
    try:
        payload = json.dumps({"text": detail}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception:
        pass
