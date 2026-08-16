# -*- coding: utf-8 -*-
"""暖眸 Agent 主循环（真实 LLM 驱动）。

感知 → 理解 → 主动触发 → 决策 → 工具 → 反馈 → 记忆。
规则兜底保证关键主动触发（用药时间 / 跌倒）可靠，其余由 LLM 判断。
"""

from __future__ import annotations

import datetime
import threading
from typing import Dict, List, Optional, Tuple

from . import llm
from .config import public_config
from .memory import MemoryStore, now_str
from .tools import run_tool

TRIGGER_LABELS = {
    "time": "时间触发",
    "scene": "场景触发",
    "anomaly": "异常触发",
    "memory": "记忆触发",
    "emotion": "情绪触发",
}

VISION_PROMPT = (
    "你是智能眼镜「暖眸」的视觉理解模块，正在以第一视角观察居家场景。\n"
    "请用 JSON 输出以下字段（只输出 JSON）：\n"
    '{"scene": "场景名称（如客厅/卧室/厨房/门口）",\n'
    ' "person_state": "人物状态（如坐在沙发上翻找/走向门口/站在灶台前/跌倒在地上）",\n'
    ' "visible_objects": ["可见物体列表"],\n'
    ' "notes": "一句话补充"}'
)

SYSTEM_PROMPT_TEMPLATE = (
    "你是「{agent_name}」，一款居家养老 AI 眼镜智能体，正在陪伴 {elder}（独居老人）。\n"
    "你的原则：\n"
    "1. 看得见、记得住、靠得住；低打扰——只在值得开口时主动说话。\n"
    "2. 不编造记忆：物品位置必须以长期记忆中的记录为准，找不到就说不知道。\n"
    "3. 不做医疗诊断，只做提醒与记录。\n"
    "4. 回复要像陪老人说话：自然、口语化、简短（一句话为主）。\n"
    "\n"
    "当前时间：{now}（{timezone}）\n"
    "老人：{elder}\n"
    "用药计划：{meds}\n"
    "长期记忆：\n{memory_text}\n"
    "最近对话：\n{conversation_text}\n"
    "可用工具：memory_search、memory_update、medication_plan、weather、notify_family、sos\n"
    "\n"
    "本轮感知：\n"
    "场景={scene}\n"
    "人物状态={person_state}\n"
    "可见物体={visible}\n"
    "老人语音：{speech}\n"
    "{rule_hint}"
    "\n"
    "请综合判断：老人语音的意图；是否存在值得主动开口的触发（时间触发：用药到点；场景触发："
    "走向门口/灶台开火；异常触发：跌倒；记忆触发：重复提问）；需要调用哪些工具（工具会真实执行）；"
    "需要写入哪些记忆（会真实持久化）；对老人的语音反馈。\n"
    "只输出 JSON（不要任何其他文字），格式：\n"
    "{{\n"
    '  "intent": {{"type": "find_item|confirm_medication|chat|sos|none|other", "target": "", "detail": ""}},\n'
    '  "triggers": [{{"type": "time|scene|anomaly|memory|emotion", "detail": "", "priority": "HIGH|MEDIUM|LOW"}}],\n'
    '  "action": "answer|search_memory|remind_medication|confirm_medication|sos|notify_family|silent",\n'
    '  "tool_uses": [{{"tool": "memory_search|memory_update|medication_plan|weather|notify_family", "args": {{"query": "", "object": "", "location": "", "detail": "", "confidence": 0.9}}}}],\n'
    '  "memory_updates": [{{"type": "item|event|fact", "object": "", "location": "", "confidence": 0.9, "detail": ""}}],\n'
    '  "feedback": "对老人说的一句话语音反馈"\n'
    "}}"
)


class AgentStepError(Exception):
    pass


class WarmEyeAgent:
    def __init__(self, config: Dict, memory: MemoryStore):
        self.config = config
        self.memory = memory
        self.conversation: List[Dict] = []
        self.notify_log: List[str] = []
        self.lock = threading.Lock()

    # ---------- 对外接口 ----------

    def reset(self) -> None:
        with self.lock:
            self.conversation = []
            self.notify_log = []

    def state(self) -> Dict:
        return {
            "config": public_config(self.config),
            "memory_items": self.memory.item_summary(),
            "events": self.memory.events(20),
            "notify": self.notify_log[-10:],
            "conversation_len": len(self.conversation),
        }

    def run_step(self, inp: Dict) -> Dict:
        with self.lock:
            return self._run_step_locked(inp)

    # ---------- 主循环 ----------

    def _run_step_locked(self, inp: Dict) -> Dict:
        trace: List[Dict] = []
        image_b64 = inp.get("image_b64") or None
        scene_text = (inp.get("scene_text") or "").strip() or None
        speech = (inp.get("speech") or "").strip() or None
        force_time = (inp.get("force_time") or "").strip() or None

        now = datetime.datetime.now()
        ts = now.strftime("%H:%M")
        date_str = now.strftime("%Y-%m-%d %H:%M（星期") + "一二三四五六日"[now.weekday()] + "）"

        if not self.config["llm"].get("api_key"):
            trace.append({"label": "配置", "kind": "info", "text": "未配置 AI 服务 API Key"})
            return {
                "ok": False,
                "message": "请先在「配置」页填写 AI 服务 API Key 并保存",
                "trace": trace,
                "feedback": "",
                "state": self.state(),
            }

        # ① 感知
        perception, perceive_note = self._perceive(image_b64, scene_text)
        for note in perceive_note:
            trace.append({"label": "感知", "kind": "info", "text": note})
        visible = "，".join(perception.get("visible_objects", [])) or "无"
        speech_part = f' · 语音="{speech}"' if speech else " · 语音=无"
        trace.append({
            "label": "感知",
            "kind": "perception",
            "text": f"{ts} 场景={perception.get('scene', '（无画面信息）')} · "
                    f"状态={perception.get('person_state', '未知')} · 可见=[{visible}]{speech_part}",
        })

        # 规则兜底：关键主动触发（用药时间 / 跌倒 / 模拟时间）
        rule_hint, rule_triggers = self._rule_check(ts, perception, speech, force_time)
        for t in rule_triggers:
            label = TRIGGER_LABELS.get(t["type"], t["type"])
            trace.append({
                "label": "触发",
                "kind": "trigger",
                "type": t["type"],
                "text": f"{label} · {t['detail']}（优先级 {t['priority']}，规则兜底）",
            })

        # ②③ 理解 + 触发 + 决策（LLM）
        try:
            decision = self._decide(perception, speech, date_str, rule_hint, trace, rule_triggers)
        except llm.LLMError as e:
            trace.append({"label": "决策", "kind": "decision", "text": f"模型调用失败：{e}"})
            return {
                "ok": False,
                "message": f"AI 服务调用失败：{e}",
                "trace": trace,
                "feedback": "",
                "state": self.state(),
            }

        # ④ 工具执行
        for tu in decision.get("tool_uses", []):
            tool = tu.get("tool")
            args = tu.get("args") or {}
            result = run_tool(tool, args, self.memory, self.config, self.notify_log)
            trace.append({"label": "工具", "kind": "tool", "text": f"{tool} → {result}"})

        # ⑤ 记忆更新
        for mu in decision.get("memory_updates", []):
            self._apply_memory_update(mu)
            summary = mu.get("object") or mu.get("detail") or mu.get("type")
            trace.append({"label": "记忆", "kind": "memory", "text": f"已写入：{summary}"})

        # ⑥ 反馈
        feedback = (decision.get("feedback") or "").strip()
        if feedback:
            trace.append({"label": "反馈", "kind": "feedback", "text": feedback, "spoken": feedback})

        # 对话记录（简短摘要）
        self.conversation.append({
            "role": "user",
            "content": f"[{ts}] 场景={perception.get('scene', '无')} 语音={speech or '无'}",
        })
        if feedback:
            self.conversation.append({"role": "assistant", "content": feedback})
        self.conversation = self.conversation[-8:]

        self.memory.save()
        return {
            "ok": True,
            "trace": trace,
            "feedback": feedback,
            "perception": perception,
            "decision": {
                "intent": decision.get("intent"),
                "triggers": decision.get("triggers"),
                "action": decision.get("action"),
            },
            "state": self.state(),
        }

    # ---------- 感知 ----------

    def _perceive(self, image_b64: Optional[str], scene_text: Optional[str]) -> Tuple[Dict, List[str]]:
        notes: List[str] = []
        if image_b64:
            cfg = self.config["llm"]
            if cfg.get("vision_supported"):
                try:
                    p = llm.vision(cfg, image_b64, VISION_PROMPT)
                    if not isinstance(p, dict):
                        raise llm.LLMError("视觉识别返回格式异常")
                    p.setdefault("scene", "（画面未识别）")
                    p.setdefault("person_state", "未知")
                    p.setdefault("visible_objects", [])
                    return p, notes
                except llm.LLMError as e:
                    notes.append(f"视觉识别失败（{e}），已回退到手动场景描述")
            else:
                notes.append("视觉未启用（配置中关闭），使用手动场景描述")
        if scene_text:
            return {"scene": scene_text, "person_state": "未知", "visible_objects": []}, notes
        return {"scene": "（无画面信息）", "person_state": "未知", "visible_objects": []}, notes

    # ---------- 规则兜底 ----------

    def _rule_check(self, ts: str, perception: Dict, speech: Optional[str],
                    force_time: Optional[str]) -> Tuple[str, List[Dict]]:
        hints: List[str] = []
        triggers: List[Dict] = []
        for med in self.config.get("medication_plan", []):
            med_time = med.get("time")
            if (med_time and med_time == ts) or (force_time and med_time == force_time):
                if not speech or force_time:
                    hints.append(
                        f"⚠️ 系统规则触发：用药时间已到（{med_time}），"
                        f"请主动提醒老人服用「{med['name']}」。"
                    )
                    triggers.append({
                        "type": "time",
                        "detail": f"{med_time} 用药计划：{med['name']}",
                        "priority": "HIGH",
                    })
        person_state = perception.get("person_state", "")
        if "跌倒" in person_state or "倒地" in person_state:
            hints.append("⚠️ 系统规则触发：检测到跌倒/倒地姿态，请先语音确认老人状况，必要时执行 sos。")
            triggers.append({
                "type": "anomaly",
                "detail": "IMU 姿态突变 + 视觉人形倒地（双通道）",
                "priority": "HIGH",
            })
        return "\n".join(hints), triggers

    # ---------- LLM 决策 ----------

    def _decide(self, perception: Dict, speech: Optional[str], date_str: str,
                rule_hint: str, trace: List[Dict], rule_triggers: List[Dict]) -> Dict:
        cfg = self.config
        elder = cfg["agent"].get("elder_name", "王奶奶")
        agent_name = cfg["agent"].get("agent_name", "暖眸")
        meds = "；".join(
            f"{m.get('name')} {m.get('time')} {m.get('dose')}"
            for m in cfg.get("medication_plan", [])
        ) or "（无）"
        memory_text = self._memory_text()
        conv_text = "\n".join(f"{m['role']}: {m['content']}" for m in self.conversation[-6:]) or "（无）"
        system = SYSTEM_PROMPT_TEMPLATE.format(
            agent_name=agent_name,
            elder=elder,
            now=date_str,
            timezone=cfg["agent"].get("timezone", "Asia/Shanghai"),
            meds=meds,
            memory_text=memory_text,
            conversation_text=conv_text,
            scene=perception.get("scene", "（无画面信息）"),
            person_state=perception.get("person_state", "未知"),
            visible="，".join(perception.get("visible_objects", [])) or "无",
            speech=speech or "（无）",
            rule_hint=rule_hint,
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "请开始判断。"},
        ]
        decision = llm.chat_json(cfg["llm"], messages, temperature=cfg["llm"].get("temperature", 0.3))

        intent = decision.get("intent") or {}
        if intent.get("type") and intent["type"] != "none":
            target = intent.get("target") or ""
            trace.append({
                "label": "理解",
                "kind": "intent",
                "text": f"意图={intent['type']}" + (f" · 目标={target}" if target else ""),
            })

        rule_keys = {(t["type"], t["detail"]) for t in rule_triggers}
        for t in decision.get("triggers", []):
            key = (t.get("type"), t.get("detail", ""))
            if key in rule_keys:
                continue
            label = TRIGGER_LABELS.get(t.get("type"), t.get("type", "触发"))
            trace.append({
                "label": "触发",
                "kind": "trigger",
                "type": t.get("type"),
                "text": f"{label} · {t.get('detail', '')}（优先级 {t.get('priority', '')}）",
            })

        trace.append({"label": "决策", "kind": "decision", "text": f"动作={decision.get('action', 'answer')}"})
        return decision

    # ---------- 记忆 ----------

    def _memory_text(self) -> str:
        lines = []
        for it in self.memory.item_summary():
            lines.append(
                f"物品 {it['object']} → 位置 {it['location']}"
                f"（记录时间 {it['time']}，置信度 {it.get('confidence', 0)}）"
            )
        for ev in self.memory.events(5):
            lines.append(f"事件 {ev.get('detail', '')}（{ev.get('time', '')}）")
        return "\n".join(lines) or "（暂无）"

    def _apply_memory_update(self, mu: Dict) -> None:
        kind = mu.get("type")
        obj = (mu.get("object") or "").strip()
        if kind == "item" and obj:
            self.memory.update_item(
                obj,
                (mu.get("location") or "").strip() or None,
                now_str(),
                float(mu.get("confidence", 0.9)),
            )
        elif kind == "event":
            self.memory.add_event("event", (mu.get("detail") or "").strip())
        elif kind == "fact":
            self.memory.add_event("fact", (mu.get("detail") or "").strip())
