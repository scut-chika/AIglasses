# -*- coding: utf-8 -*-
"""暖眸 Agent 端到端测试：用 Mock OpenAI 兼容服务验证全链路。

运行：py tests/test_e2e.py
覆盖：视觉感知 → LLM 决策 → 工具执行 → 记忆持久化 → 无 Key 兜底。
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import WarmEyeAgent            # noqa: E402
from agent.memory import MemoryStore            # noqa: E402


def _decision_for(system: str, user: str) -> dict:
    """根据输入返回不同的决策，模拟真实 LLM。"""
    m = re.search(r"老人语音：(.+)", system)
    speech = m.group(1).strip() if m else ""
    if "用药时间已到" in system:
        return {
            "intent": {"type": "none", "target": "", "detail": ""},
            "triggers": [{"type": "time", "detail": "08:00 用药计划：降压药", "priority": "HIGH"}],
            "action": "remind_medication",
            "tool_uses": [{"tool": "medication_plan", "args": {}}],
            "memory_updates": [],
            "feedback": "王奶奶，该吃降压药了。",
        }
    if "我的老花镜呢" in speech:
        return {
            "intent": {"type": "find_item", "target": "老花镜", "detail": ""},
            "triggers": [],
            "action": "search_memory",
            "tool_uses": [{"tool": "memory_search", "args": {"query": "老花镜"}}],
            "memory_updates": [],
            "feedback": "老花镜在客厅茶几上，我上次看到是昨天下午。",
        }
    if "吃完了" in speech:
        return {
            "intent": {"type": "confirm_medication", "target": "", "detail": ""},
            "triggers": [],
            "action": "confirm_medication",
            "tool_uses": [],
            "memory_updates": [{"type": "event", "object": "", "location": "", "confidence": 1.0, "detail": "确认服药：降压药"}],
            "feedback": "好的，已记录您这次服药。",
        }
    return {
        "intent": {"type": "none", "target": "", "detail": ""},
        "triggers": [],
        "action": "answer",
        "tool_uses": [],
        "memory_updates": [],
        "feedback": "好的，我在。",
    }


class MockLLMServer(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        messages = payload["messages"]
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")

        has_image = any(
            isinstance(m.get("content"), list)
            and any(c.get("type") == "image_url" for c in m["content"])
            for m in messages
        )
        if has_image:
            content = json.dumps({
                "scene": "客厅",
                "person_state": "坐在沙发上翻找",
                "visible_objects": ["老花镜", "茶几", "电视"],
                "notes": "老人正在找东西",
            }, ensure_ascii=False)
        else:
            content = json.dumps(_decision_for(system, user), ensure_ascii=False)

        body = json.dumps({"choices": [{"message": {"content": content}}]}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_mock_server() -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), MockLLMServer)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> None:
    failures = 0

    def check(cond, msg):
        nonlocal failures
        print(("PASS  " if cond else "FAIL  ") + msg)
        if not cond:
            failures += 1

    tmp = tempfile.mkdtemp(prefix="nuanmou_test_")
    mem_path = os.path.join(tmp, "memory.json")
    srv = start_mock_server()
    port = srv.server_address[1]

    base_config = {
        "agent": {"elder_name": "王奶奶", "agent_name": "暖眸", "timezone": "Asia/Shanghai"},
        "llm": {
            "api_key": "test-key",
            "base_url": f"http://127.0.0.1:{port}/v1",
            "model": "mock-model",
            "vision_supported": True,
            "temperature": 0.3,
        },
        "medication_plan": [{"name": "降压药", "time": "08:00", "dose": "1粒/日"}],
        "weather": {"city": "广州", "api_key": ""},
        "family_webhook": "",
    }

    # ① 视觉 + 找物全链路
    memory = MemoryStore(mem_path)
    agent = WarmEyeAgent(base_config, memory)
    r = agent.run_step({
        "image_b64": "aW1hZ2U=",
        "scene_text": "",
        "speech": "我的老花镜呢？",
    })
    trace_text = " | ".join(e["text"] for e in r["trace"])
    check(r["ok"], "视觉+找物：运行成功")
    check(any(e["kind"] == "perception" for e in r["trace"]), "包含感知轨迹")
    check(any(e["kind"] == "intent" for e in r["trace"]), "包含理解(意图)轨迹")
    check(any(e["kind"] == "tool" and "记忆库检索" in e["text"] or e["kind"] == "tool" and "memory_search" in e["text"] for e in r["trace"]),
          "包含工具调用轨迹")
    check("老花镜在客厅茶几上" in r["feedback"], f"反馈基于真实记忆：{r['feedback']}")
    check("客厅" in trace_text, "感知识别出场景=客厅")

    # ② 确认服药 → 事件写入
    r2 = agent.run_step({"speech": "吃完了"})
    check(r2["ok"], "确认服药：运行成功")
    check(any("确认服药" in ev["detail"] for ev in r2["state"]["events"]), "服药事件已写入记忆")
    check(any(e["kind"] == "memory" for e in r2["trace"]), "包含记忆更新轨迹")

    # ③ 用药时间规则兜底（无语音）
    r3 = agent.run_step({"speech": "", "scene_text": "卧室，老人坐在床边", "force_time": "08:00"})
    check(any(e["kind"] == "trigger" and "规则兜底" in e["text"] for e in r3["trace"]), "规则触发：用药时间（兜底）")
    check("该吃降压药了" in r3["feedback"], "主动提醒服药")

    # ④ 无 Key 兜底
    no_key = dict(base_config)
    no_key["llm"] = dict(no_key["llm"], api_key="")
    r4 = WarmEyeAgent(no_key, MemoryStore(mem_path)).run_step({"speech": "你好"})
    check(not r4["ok"], "无 Key：返回友好提示")
    check("API Key" in r4["message"], "提示用户配置 API Key")

    srv.shutdown()
    print(f"\n[{'FAIL ' + str(failures) if failures else 'ALL PASS'}]")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
