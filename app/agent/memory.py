# -*- coding: utf-8 -*-
"""暖眸 长期记忆（本地 JSON 持久化）：物品位置、事件、事实。"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class MemoryStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "memory.json"
        )
        self.items: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.items = data
            except Exception:
                self.items = []

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    # ---------- 物品记忆 ----------
    def find_item(self, object_name: str) -> Optional[Dict[str, Any]]:
        hits = [
            it for it in self.items
            if it.get("type") == "item" and object_name in it.get("object", "")
        ]
        if not hits:
            return None
        return max(hits, key=lambda it: it.get("confidence", 0))

    def search(self, query: str) -> List[Dict[str, Any]]:
        hits = [
            it for it in self.items
            if it.get("type") == "item"
            and (query in it.get("object", "") or query in it.get("location", ""))
        ]
        return hits[:5]

    def update_item(self, object_name: str, location: Optional[str] = None,
                    time: Optional[str] = None, confidence: Optional[float] = None) -> Dict[str, Any]:
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

    def delete_item(self, object_name: str) -> bool:
        before = len(self.items)
        self.items = [
            it for it in self.items
            if not (it.get("type") == "item" and object_name in it.get("object", ""))
        ]
        self.save()
        return len(self.items) < before

    # ---------- 事件 / 事实 ----------
    def add_event(self, kind: str, detail: str) -> Dict[str, Any]:
        ev = {"type": "event", "kind": kind, "detail": detail, "time": now_str()}
        self.items.append(ev)
        self.save()
        return ev

    def item_summary(self) -> List[Dict[str, Any]]:
        return [it for it in self.items if it.get("type") == "item"]

    def events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [it for it in self.items if it.get("type") == "event"][-limit:]

    def clear(self) -> None:
        self.items = []
        self.save()
