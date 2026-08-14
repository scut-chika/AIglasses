"""暖眸 · 记忆库（本地 JSON 存储，比赛演示版）。

演示阶段用 JSON 文件模拟长期记忆；接入真机后可替换为
SQLite / 向量数据库，接口保持不变。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "memory.json")


class MemoryStore:
    """长期记忆：物品位置、健康事件、生活事实。"""

    def __init__(
        self,
        initial_items: Optional[List[Dict[str, Any]]] = None,
        path: str = DEFAULT_PATH,
    ):
        self.path = path
        if initial_items:
            self.items: List[Dict[str, Any]] = list(initial_items)
        elif os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.items = json.load(f)
        else:
            self.items = []

    def find_item(self, object_name: str) -> Optional[Dict[str, Any]]:
        """按名称检索物品记忆，返回置信度最高的一条。"""
        hits = [
            it for it in self.items
            if it.get("type") == "item" and object_name in it.get("object", "")
        ]
        if not hits:
            return None
        return max(hits, key=lambda it: it.get("confidence", 0))

    def update_item(
        self,
        object_name: str,
        location: Optional[str] = None,
        time: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """更新或新增物品位置记忆。"""
        for it in self.items:
            if it.get("type") == "item" and object_name in it.get("object", ""):
                if location:
                    it["location"] = location
                if time:
                    it["time"] = time
                if confidence is not None:
                    it["confidence"] = confidence
                return it
        item = {
            "type": "item",
            "object": object_name,
            "location": location or "未知",
            "time": time or now_str(),
            "confidence": confidence if confidence is not None else 0.5,
        }
        self.items.append(item)
        return item

    def add_event(self, kind: str, detail: str) -> Dict[str, Any]:
        event = {"type": "event", "kind": kind, "detail": detail, "time": now_str()}
        self.items.append(event)
        return event

    def events(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        events = [it for it in self.items if it.get("type") == "event"]
        if kind:
            return [it for it in events if it.get("kind") == kind]
        return events

    def get_fact(self, keyword: str) -> Optional[str]:
        for it in self.items:
            if it.get("type") == "fact" and keyword in it.get("content", ""):
                return it["content"]
        return None

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    def summary(self) -> List[str]:
        return [
            f"{it.get('object')} → {it.get('location')}（{it.get('time')}，置信度 {it.get('confidence')}）"
            for it in self.items
            if it.get("type") == "item"
        ]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
