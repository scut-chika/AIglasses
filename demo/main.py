#!/usr/bin/env python3
"""暖眸 · 居家养老 AI 眼镜智能体 —— 可运行 Demo（Mock 模式）

无需 API Key、无需硬件即可运行。输入来自预置场景脚本，
Agent 的感知 → 理解 → 主动触发 → 决策 → 工具 → 反馈 → 记忆
逻辑是真实代码。

用法：
    python main.py                         # 默认跑「用药提醒」场景
    python main.py --scene medication      # 用药提醒闭环
    python main.py --scene find_glasses    # 记忆找物闭环
    python main.py --check                 # 自动跑完全部步骤并校验输出
    python main.py --no-wait               # 不按回车，连续播放
    python main.py --tts                   # 尝试用 edge-tts 语音朗读（可选）

退出码 0 表示 --check 全部通过。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from agent import Perception, WarmEyeAgent
from memory import MemoryStore

SCENE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenes")
SCENES = {
    "medication": os.path.join(SCENE_DIR, "medication.json"),
    "find_glasses": os.path.join(SCENE_DIR, "find_glasses.json"),
    "door_reminder": os.path.join(SCENE_DIR, "door_reminder.json"),
}


def load_scene(name: str) -> dict:
    path = SCENES.get(name)
    if not path or not os.path.exists(path):
        sys.exit(f"找不到场景 {name}，可用场景：{', '.join(sorted(SCENES))}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_header(scene: dict) -> None:
    line = "=" * 66
    print(line)
    print(f" {scene.get('agent_name', '暖眸')} · 居家养老 AI 眼镜智能体 Demo")
    print(f" 场景：{scene['title']}")
    print(f" 人物：{scene.get('elder_name', '王奶奶')}（独居老人）")
    print(line)


def print_initial_memory(scene: dict) -> None:
    items = scene.get("initial_memory", [])
    if items:
        print("初始长期记忆：")
        for it in items:
            if it.get("type") == "item":
                print(f"  * {it['object']} → {it['location']}（{it['time']}，置信度 {it['confidence']}）")
        print()


def check_expectations(step: dict, trace: list, feedback_text: str, passed: list) -> None:
    expect = step.get("expect", {})
    expect_contains = expect.get("feedback_contains")
    expect_tool = expect.get("tool")
    expect_trigger = expect.get("trigger")
    expect_memory = expect.get("memory_update")

    checks = []
    if expect_contains:
        checks.append(("反馈包含", expect_contains, expect_contains in feedback_text))
    if expect_tool:
        ok_tool = any(f"[工具] {expect_tool}" in line for line in trace)
        checks.append(("工具调用", expect_tool, ok_tool))
    if expect_trigger:
        ok_trigger = any(f"[触发] {expect_trigger}" in line for line in trace)
        checks.append(("触发类型", expect_trigger, ok_trigger))
    if expect_memory is not None:
        ok_memory = any(("[记忆] 已更新" in line) == bool(expect_memory) for line in trace)
        checks.append(("记忆更新", str(expect_memory), ok_memory))

    all_ok = all(ok for _, _, ok in checks)
    passed.append(all_ok)
    for label, want, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}：{want}")
    if not all_ok:
        print(f"  [FAIL] 步骤「{step.get('name', '')}」未通过校验")


def run_scene(scene_name: str, interactive: bool, check: bool, tts: bool) -> bool:
    scene = load_scene(scene_name)
    memory = MemoryStore(scene.get("initial_memory", []))
    agent = WarmEyeAgent(
        memory,
        elder_name=scene.get("elder_name", "王奶奶"),
        agent_name=scene.get("agent_name", "暖眸"),
        context=scene.get("context", {}),
    )
    print_header(scene)
    print_initial_memory(scene)

    passed: list = []
    steps = scene.get("steps", [])
    for i, step in enumerate(steps, 1):
        if interactive and i > 1:
            try:
                input("按 Enter 推进…（Ctrl+C 退出）")
            except KeyboardInterrupt:
                print("\n演示已退出。")
                break
        print("-" * 66)
        print(f"第 {i}/{len(steps)} 步：{step.get('name', '')}")
        p = Perception(**step["perception"])
        trace, feedback = agent.tick(p)
        for line in trace:
            print(line)
        if check:
            check_expectations(step, trace, feedback.text if feedback else "", passed)
        if tts and feedback and feedback.text:
            speak(feedback.text)
        print()

    print("=" * 66)
    print("演示结束 · 长期记忆当前状态：")
    for line in memory.summary():
        print(f"  * {line}")
    events = memory.events()
    if events:
        print("本次产生的记录：")
        for ev in events:
            print(f"  * [{ev['time']}] {ev['kind']}：{ev['detail']}")
    try:
        memory.save()
        print(f"\n记忆已保存到：{memory.path}")
    except Exception as exc:
        print(f"\n（提示：记忆文件写入失败，本次记忆仅保留在内存中：{exc}）")

    if check:
        ok = bool(passed) and all(passed) and len(passed) == len(steps)
        print("\n" + ("✓ 全部步骤校验通过" if ok else "✗ 存在未通过的校验"))
        return ok
    return True


def speak(text: str) -> None:
    """可选语音朗读：pip install edge-tts。任何失败都静默降级。"""
    try:
        import asyncio
        import subprocess

        import edge_tts

        async def _say():
            tts = edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural", rate="-15%")
            await tts.save("_demo_tts.mp3")
            subprocess.Popen(["start", "_demo_tts.mp3"], shell=True)

        asyncio.run(_say())
    except Exception:
        print("（提示：安装 edge-tts 可语音朗读：pip install edge-tts）")


def main() -> None:
    parser = argparse.ArgumentParser(description="暖眸 · 居家养老 AI 眼镜智能体 Demo")
    parser.add_argument("--scene", choices=sorted(SCENES), default="medication", help="场景名称")
    parser.add_argument("--check", action="store_true", help="自动跑完全部步骤并校验输出")
    parser.add_argument("--no-wait", action="store_true", help="不按回车，连续播放")
    parser.add_argument("--tts", action="store_true", help="尝试语音朗读反馈")
    args = parser.parse_args()

    interactive = not (args.check or args.no_wait)
    ok = run_scene(args.scene, interactive=interactive, check=args.check, tts=args.tts)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
