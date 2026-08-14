"""暖眸 Agent 核心：感知 → 理解 → 主动触发 → 决策 → 工具 → 反馈 → 记忆。

Mock 模式下输入来自场景脚本，但 Agent 的决策逻辑是真实代码：
意图理解、主动触发评估、工具调用、记忆更新都在这里完成。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from memory import MemoryStore

INTENT_LABELS = {
    "find_item": "找物",
    "confirm_medication": "确认服药",
    "sos": "紧急求助",
    "ack": "应答/确认",
    "chat": "闲聊",
    "none": "无主动请求",
}

TRIGGER_LABELS = {
    "time": "时间触发",
    "scene": "场景触发",
    "anomaly": "异常触发",
    "memory": "记忆触发",
    "emotion": "情绪触发",
}

# 物品别名归一化
ITEM_ALIASES = {
    "老花镜": "老花镜",
    "眼镜": "老花镜",
    "钥匙": "钥匙",
    "降压药": "降压药",
    "药盒": "降压药",
    "药": "降压药",
    "手机": "手机",
    "遥控器": "遥控器",
}


@dataclass
class Perception:
    timestamp: str
    scene: str
    person_state: str
    visible_objects: List[str]
    speech: Optional[str] = None


@dataclass
class Intent:
    kind: str
    target: Optional[str] = None
    raw: str = ""


@dataclass
class Trigger:
    kind: str       # time | scene | anomaly | memory | emotion
    priority: str   # HIGH | MEDIUM | LOW
    detail: str


@dataclass
class Feedback:
    text: str
    channel: str = "voice"          # voice | vibration | notify_family | silent
    priority: str = "MEDIUM"


@dataclass
class ActionResult:
    tool: Optional[str]
    memory_updated: bool = False
    detail: str = ""


class WarmEyeAgent:
    """居家养老 AI 眼镜智能体（演示版）。"""

    def __init__(
        self,
        memory: MemoryStore,
        elder_name: str = "王奶奶",
        agent_name: str = "暖眸",
        context: Optional[Dict] = None,
    ):
        self.memory = memory
        self.elder = elder_name
        self.name = agent_name
        self.context = context or {}
        self.medication_plan = [{"name": "降压药", "time": "08:00", "dose": "1粒/日"}]
        self.escalation_count = 0               # 用药未确认的升级次数
        self.pending_find: Optional[str] = None
        self.last_find: Optional[str] = None
        self.medication_prompted = False

    # ---------- ① 意图理解 ----------

    def understand(self, speech: Optional[str]) -> Intent:
        if not speech:
            return Intent("none")
        s = speech.strip()
        if re.search(r"(在哪|哪里|找不到|放哪|找不到了|呢)", s):
            for alias, canonical in ITEM_ALIASES.items():
                if alias in s:
                    return Intent("find_item", canonical, s)
            return Intent("find_item", None, s)
        if re.search(r"(吃完|吃了|喝完了|已经吃)", s):
            return Intent("confirm_medication", None, s)
        if re.search(r"(救命|help|摔倒|摔了|求助|帮忙)", s, re.IGNORECASE):
            return Intent("sos", None, s)
        if re.search(r"(谢谢|嗯|好|知道了|找到了|这就|关了)", s):
            return Intent("ack", None, s)
        return Intent("chat", None, s)

    # ---------- ② 主动触发评估 ----------

    def proactive_triggers(self, p: Perception, intent: Intent) -> List[Trigger]:
        triggers: List[Trigger] = []

        # 时间触发：用药计划
        for med in self.medication_plan:
            if p.timestamp.startswith(med["time"]):
                triggers.append(Trigger("time", "HIGH", f"{p.timestamp} 用药计划：{med['name']}"))
                self.medication_prompted = True

        # 场景触发：识别到走向门口
        if "门口" in p.person_state or "出门" in p.person_state:
            details = []
            weather = self.context.get("weather")
            if weather and weather != "晴":
                details.append(f"今天{weather}，带伞")
            if self.context.get("kitchen_fire_on"):
                details.append("厨房火好像还开着")
            if details:
                triggers.append(Trigger("scene", "HIGH", " / ".join(details)))

        # 异常触发：跌倒（IMU + 视觉双通道）
        if "跌倒" in p.person_state or "倒地" in p.person_state:
            triggers.append(Trigger("anomaly", "HIGH", "IMU 姿态突变 + 视觉人形倒地（双通道）"))

        # 记忆触发：短时间内重复问同一个物品
        if intent.kind == "find_item" and intent.target and intent.target == self.last_find:
            triggers.append(Trigger("memory", "MEDIUM", f"{self.elder} 又问了同一个物品：{intent.target}"))

        return triggers

    # ---------- ③ 决策 ----------

    def decide(self, p: Perception, intent: Intent, triggers: List[Trigger]) -> str:
        if intent.kind == "find_item":
            return "find_item"
        if intent.kind == "confirm_medication":
            return "confirm_medication"
        if intent.kind == "sos":
            return "sos"
        if intent.kind == "ack":
            return "ack"
        if intent.kind == "chat":
            return "chat"
        if triggers:
            t = triggers[0]
            if t.kind == "time":
                return "medication_prompt"
            if t.kind == "scene":
                return "door_reminder"
            if t.kind == "anomaly":
                return "fall_check"
            if t.kind == "memory":
                return "find_item"
        return "observe"

    # ---------- ④ 执行（工具调用 + 反馈） ----------

    def act(self, action: str, p: Perception, intent: Intent) -> Tuple[Feedback, ActionResult]:
        # 主动提醒服药（时间触发）
        if action == "medication_prompt":
            med = self.medication_plan[0]
            return (
                Feedback(f"{self.elder}，该吃{med['name']}了。", channel="voice", priority="HIGH"),
                ActionResult("用药计划", False, f"当前药品：{med['name']}（{med['dose']}）"),
            )

        # 出门提醒（场景触发）
        if action == "door_reminder":
            parts = []
            weather = self.context.get("weather")
            if weather and weather != "晴":
                parts.append(f"今天{weather}，带伞")
            if self.context.get("kitchen_fire_on"):
                parts.append("厨房火好像还开着")
            detail = "，".join(parts)
            return (
                Feedback(f"{self.elder}，{detail}，出门前注意一下。", channel="voice", priority="HIGH"),
                ActionResult("天气 API + 室内状态记忆", False, detail),
            )

        # 跌倒二次确认（异常触发）
        if action == "fall_check":
            return (
                Feedback(f"{self.elder}，您摔着了吗？需要帮忙吗？", channel="voice", priority="HIGH"),
                ActionResult("语音二次确认", False, "等待回应；无回应 15 秒后自动呼叫紧急联系人"),
            )

        # 找物
        if action == "find_item":
            target = intent.target or self.pending_find
            self.pending_find = target
            if not target:
                return Feedback("您要找什么？再说一遍好吗？"), ActionResult(None, False)
            self.last_find = target
            item = self.memory.find_item(target)
            if item and item.get("confidence", 0) >= 0.7:
                return (
                    Feedback(
                        f"{self.elder}，{target}在{item['location']}，我上次看到是{item.get('time')}。",
                        priority="MEDIUM",
                    ),
                    ActionResult("记忆库检索", False, f"命中 {item['object']}，置信度 {item.get('confidence')}"),
                )
            # 置信度低：现场视觉扫描
            for obj in p.visible_objects:
                if target in obj or obj in target:
                    self.memory.update_item(target, p.scene, p.timestamp, 0.95)
                    return (
                        Feedback(f"找到了，就在{p.scene}。我记下了。", priority="MEDIUM"),
                        ActionResult("视觉扫描", True, f"在现场识别到 {obj}"),
                    )
            return (
                Feedback(f"暂时没找到，我帮您记着，下次看到{target}再告诉您。", priority="LOW"),
                ActionResult("记忆库检索", False, "未命中，尝试视觉扫描"),
            )

        # 确认服药
        if action == "confirm_medication":
            self.memory.add_event("medication", f"{p.timestamp} 确认服药")
            return (
                Feedback(
                    f"好的，已记录您这次服药。今晚 8 点我会把今天的情况发给您女儿。",
                    channel="voice",
                ),
                ActionResult("健康日志", True, "服药记录已写入；漏服升级计数重置"),
            )

        # 应答/确认
        if action == "ack":
            # 场景 A：刚提醒过吃药，老人取药 → 视觉确认
            if self.medication_prompted and any("药" in obj for obj in p.visible_objects):
                return (
                    Feedback(f"我看到您拿着降压药了，吃完跟我说一声。", channel="voice"),
                    ActionResult("视觉确认", False, "识别到药盒/药瓶"),
                )
            # 场景 B：正在找物，老人找到 → 记忆复核更新
            if self.pending_find:
                for obj in p.visible_objects:
                    if self.pending_find in obj or obj in self.pending_find:
                        self.memory.update_item(self.pending_find, p.scene, p.timestamp, 0.95)
                        return (
                            Feedback(f"太好了！我记下了，{self.pending_find}在{p.scene}。", channel="voice"),
                            ActionResult("记忆更新", True, f"{self.pending_find} → {p.scene}"),
                        )
            # 场景 C：返回厨房确认关火 → 更新室内状态
            if p.scene == "厨房" and self.context.get("kitchen_fire_on"):
                self.context["kitchen_fire_on"] = False
                return (
                    Feedback("火已经关了，可以放心出门。", channel="voice"),
                    ActionResult("视觉确认", True, "灶台已关火，室内状态记忆已更新"),
                )
            return Feedback("好的，有需要随时叫我。", priority="LOW"), ActionResult(None, False)

        # 紧急求助
        if action == "sos":
            return (
                Feedback(
                    f"{self.elder}，别怕，我马上联系您女儿，并发送您的位置。",
                    channel="notify_family",
                    priority="HIGH",
                ),
                ActionResult("紧急联系", True, "已通知紧急联系人（定位 + 第一视角快照）"),
            )

        # 闲聊
        if action == "chat":
            return (
                Feedback("嗯嗯，我听着呢。要不要我给您念念今天的新闻？", priority="LOW"),
                ActionResult(None, False),
            )

        # 静默观察
        return Feedback("", channel="silent", priority="LOW"), ActionResult(None, False)

    # ---------- 主循环 ----------

    def tick(self, p: Perception) -> Tuple[List[str], Optional[Feedback]]:
        trace: List[str] = []
        intent = self.understand(p.speech)
        triggers = self.proactive_triggers(p, intent)

        visible = ",".join(p.visible_objects) if p.visible_objects else "无"
        speech_part = f' 语音="{p.speech}"' if p.speech else " 语音=无"
        trace.append(f"[感知] {p.timestamp} 场景={p.scene} 状态={p.person_state} 可见={visible}{speech_part}")

        if intent.kind != "none":
            target_part = f" 目标={intent.target}" if intent.target else ""
            trace.append(f"[理解] 意图={INTENT_LABELS.get(intent.kind, intent.kind)}{target_part}")

        for t in triggers:
            label = TRIGGER_LABELS.get(t.kind, t.kind)
            trace.append(f"[触发] {label} · {t.detail}（优先级 {t.priority}）")

        action = self.decide(p, intent, triggers)
        feedback, result = self.act(action, p, intent)

        if result.tool:
            trace.append(f"[工具] {result.tool} → {result.detail}")
        trace.append(f"[记忆] {'已更新' if result.memory_updated else '无变更'}")
        if feedback.text:
            channel_part = f"（通道：{feedback.channel}）" if feedback.channel not in ("voice", "silent") else ""
            trace.append(f"[反馈] 🔊 {feedback.text} {channel_part}".rstrip())

        return trace, feedback
