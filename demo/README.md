# 暖眸 · 可运行 Demo（Mock 演示器）

一套**不需要硬件、不需要 API Key** 就能跑起来的 Agent 闭环演示。
输入来自预置场景脚本，但 Agent 的感知 → 理解 → 主动触发 → 决策 →
工具 → 反馈 → 记忆逻辑是真实代码，可直接演示，也可作为接入真机前的骨架。

> 另有浏览器版 Web 前端（免安装、可部署在线、适合录视频）：见
> [../web/README.md](../web/README.md)。

## 快速开始

要求：Python 3.8+

```powershell
cd demo
python main.py --scene find_glasses    # 闭环一：记忆找物
python main.py --scene medication      # 闭环二：用药提醒与确认（主动 Agent）
python main.py --scene door_reminder   # 闭环三：出门提醒（场景触发）
python main.py --check                 # 自动跑完所有步骤并校验（退出码 0 = 通过）
python main.py --no-wait               # 不按回车，连续播放
```

如果 `python` 命令不可用，换成 `py` 即可（Windows 官方启动器）。
Windows 也可以直接运行 `.\run_demo.ps1 -Scene medication`。

可选语音朗读：

```powershell
pip install edge-tts
python main.py --scene medication --tts
```

## 目录结构

```text
demo/
  main.py                 # 入口：加载场景、推进步骤、校验输出
  agent.py                # 暖眸 Agent 核心（真实决策逻辑）
  memory.py               # 长期记忆（本地 JSON）
  scenes/
    find_glasses.json     # 闭环一：记忆找物
    medication.json       # 闭环二：用药提醒与确认
    door_reminder.json    # 闭环三：出门提醒
  run_demo.ps1            # Windows 启动脚本
```

## 运行效果（用药闭环）

```text
[感知] 08:00 场景=卧室 状态=坐在床边 可见=无 语音=无
[触发] 时间触发 · 08:00 用药计划：降压药（优先级 HIGH）
[工具] 用药计划 → 当前药品：降压药（1粒/日）
[反馈] 🔊 王奶奶，该吃降压药了。
```

每个步骤都会打印 Agent 的完整决策链，这正是演示视频里
"画中画决策可视化"的素材来源。

## 怎么变成真机 Demo

1. **替换感知层**：`agent.py` 中 `Perception` 来自场景脚本；接入真机后，
   改为摄像头帧 + ASR 的实时输出（Rokid/雷鸟眼镜，或手机摄像头模拟第一视角）
2. **替换理解层**：`understand()` 现在是关键词规则；接 LLM 后换成语义解析
3. **替换记忆层**：`memory.py` 换成 SQLite / 向量数据库，接口不变
4. **替换反馈层**：`Feedback` 的 `channel` 字段映射到骨传导 / 震动 / LED / 家人推送

## 演示建议

* 录屏跑一遍 `--check`，把输出叠加到第一视角实拍视频上作为画中画
* 现场断网时用 `--no-wait` 回放，保证演示不翻车
