# -*- coding: utf-8 -*-
"""生成《暖眸 · 居家养老 AI 眼镜智能体》路演 PPT。

运行：py make_ppt.py
输出：暖眸-居家养老AI眼镜智能体-路演PPT.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---------------- 主题 ----------------
BG = RGBColor(0x0D, 0x10, 0x20)
PANEL = RGBColor(0x15, 0x1A, 0x30)
PANEL2 = RGBColor(0x1A, 0x20, 0x40)
BORDER = RGBColor(0x2A, 0x31, 0x57)
TEXT = RGBColor(0xE8, 0xEA, 0xF6)
MUTED = RGBColor(0x8B, 0x93, 0xB8)
ACCENT = RGBColor(0x6D, 0x8D, 0xFF)
AMBER = RGBColor(0xFF, 0xB4, 0x54)
GREEN = RGBColor(0x57, 0xD9, 0xA3)
RED = RGBColor(0xFF, 0x6B, 0x81)
PER = RGBColor(0x5A, 0xB0, 0xFF)
LOG = RGBColor(0xCD, 0xD3, 0xEC)
FONT = "Microsoft YaHei"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def set_font(run, size=14, bold=False, color=TEXT, italic=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    f.name = FONT
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", FONT)


def add_text(slide, x, y, w, h, text, size=14, bold=False, color=TEXT,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.12):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        set_font(r, size, bold, color)
    return box


def add_rect(slide, x, y, w, h, fill=PANEL, line=BORDER, radius=0.12, line_w=1.0):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    try:
        shape.adjustments[0] = radius
    except Exception:
        pass
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(line_w)
    shape.shadow.inherit = False
    return shape


def shape_text(shape, text, size=13, bold=False, color=TEXT,
               align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.03)
    tf.margin_bottom = Inches(0.03)
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = 1.1
        r = p.add_run()
        r.text = line
        set_font(r, size, bold, color)


def add_arrow(slide, x, y, w, h, color=ACCENT, direction="right"):
    kind = MSO_SHAPE.RIGHT_ARROW if direction == "right" else MSO_SHAPE.DOWN_ARROW
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def new_slide():
    slide = prs.slides.add_slide(BLANK)
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG
    return slide


def add_footer(slide):
    add_text(slide, 10.7, 7.13, 2.2, 0.3, "暖眸 · 居家养老 AI 眼镜智能体",
             size=9.5, color=MUTED, align=PP_ALIGN.RIGHT)


def add_header(slide, num, title, subtitle=None):
    add_text(slide, 0.6, 0.3, 0.8, 0.55, f"{num:02d}", size=24, bold=True, color=ACCENT)
    add_text(slide, 1.2, 0.26, 10.6, 0.7, title, size=25, bold=True)
    if subtitle:
        add_text(slide, 1.22, 0.82, 10.6, 0.4, subtitle, size=12.5, color=MUTED)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(7.1), Inches(12.13), Pt(2))
    line.fill.solid()
    line.fill.fore_color.rgb = BORDER
    line.line.fill.background()
    line.shadow.inherit = False
    add_footer(slide)


def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def flow_slide(num, title, subtitle, steps, branches, notes, accent=ACCENT):
    """闭环流程页：横向步骤 + 异常分支/沉淀面板。steps: [(标题, 说明)]"""
    s = new_slide()
    add_header(s, num, title, subtitle)

    n = len(steps)
    gap = 0.32
    box_w = (12.13 - gap * (n - 1)) / n
    box_h = 1.95
    y = 1.55
    x = 0.6
    for i, (t, d) in enumerate(steps):
        bx = x + i * (box_w + gap)
        box = add_rect(s, bx, y, box_w, box_h, fill=PANEL2, line=accent, radius=0.1)
        shape_text(box, f"{t}\n\n{d}", size=12.5 if len(d) > 14 else 13, bold=False)
        if i < n - 1:
            add_arrow(s, bx + box_w + 0.045, y + box_h / 2 - 0.12, gap - 0.09, 0.24,
                      color=accent, direction="right")

    add_text(s, 0.6, 3.85, 12.1, 0.35, "异常分支与沉淀", size=15, bold=True, color=AMBER)
    for i, (t, d, c) in enumerate(branches):
        bw = (12.13 - 0.3) / len(branches)
        bbox = add_rect(s, 0.6 + i * (bw + 0.1), 4.3, bw, 1.55, fill=PANEL, line=BORDER)
        shape_text(bbox, f"{t}\n{d}", size=12.5, color=c)

    add_text(s, 0.6, 6.15, 12.1, 0.6, "闭环价值：感知 → 决策 → 行动 → 反馈 → 记忆沉淀，全链路可回溯。",
             size=13, color=MUTED)
    add_footer(s)
    set_notes(s, notes)
    return s


# ================= 01 封面 =================
s = new_slide()
add_rect(s, 0.6, 1.25, 0.14, 4.4, fill=ACCENT, line=ACCENT, radius=0.5)
add_text(s, 1.15, 1.55, 11.4, 1.0, "暖眸", size=64, bold=True, color=ACCENT)
add_text(s, 1.15, 2.62, 11.4, 0.8, "居家养老 AI 眼镜智能体", size=36, bold=True)
add_text(s, 1.15, 3.5, 11.4, 0.5, "看得见 · 记得住 · 靠得住", size=19, color=AMBER)
add_text(s, 1.15, 4.5, 11.4, 0.4, "赛题方向：AI+眼镜 · 下一代个人智能终端原生智能体", size=14, color=TEXT)
add_text(s, 1.15, 4.95, 11.4, 0.4, "赛道：生活健康", size=14, color=TEXT)
add_text(s, 1.15, 5.4, 11.4, 0.4, "重点验证：第一视角 · 语音交互 · 实时感知 · 随身陪伴 · 轻量反馈", size=12.5, color=MUTED)
add_text(s, 1.15, 6.45, 11.4, 0.4, "队伍：＿＿＿＿＿＿   |   2026 年 8 月", size=12.5, color=MUTED)
set_notes(s, "开场：独居老人王奶奶的一天。戴上眼镜，她再也不怕忘吃药、找不到东西。暖眸——看得见、记得住、靠得住。")

# ================= 02 痛点 =================
s = new_slide()
add_header(s, 2, "独居老人的一天：遗忘、安全、孤独", "目标用户：60–80 岁独居 / 白天独居、轻度记忆衰退、生活基本自理的老人")
cards = [
    ("🧓 遗忘", "找不到老花镜、钥匙\n忘记吃药、重复吃药\n反复翻找、着急无助", RED),
    ("🆘 安全", "跌倒无人知晓\n出门忘带伞、忘关火\n错过黄金救援时间", AMBER),
    ("🏠 孤独", "子女不在身边\n没人说话、情绪低落\n子女打电话追问反而嫌烦", PER),
    ("📱 子女焦虑", "“吃药了吗？”式电话\n问了嫌烦、不问担心\n无法获得日常真实状态", GREEN),
]
cw = (12.13 - 0.3) / 4
for i, (t, d, c) in enumerate(cards):
    box = add_rect(s, 0.6 + i * (cw + 0.1), 1.7, cw, 3.3, fill=PANEL, line=c)
    shape_text(box, f"{t}\n\n{d}", size=14)
add_text(s, 0.6, 5.4, 12.1, 0.4, "核心矛盾：老人需要“看得见、记得住、靠得住”的随身守护，而现有设备做不到第一视角。", size=15, bold=True, color=AMBER)
add_text(s, 0.6, 5.95, 12.1, 0.4, "手机：老人不会用、操作繁琐，无法感知“眼前的世界”   手表：只测数据，看不见、听不见、不会主动说话", size=13, color=MUTED)
add_footer(s)
set_notes(s, "痛点数据化：找东西平均每天 1–2 次；忘服药在轻度认知障碍老人中比例高；跌倒后独居老人错过救援是重大风险。")

# ================= 03 产品定位 =================
s = new_slide()
add_header(s, 3, "产品定位：给独居老人配一个随身智能体", "为什么是眼镜：第一视角才能“看见老人看见的”")
box = add_rect(s, 0.6, 1.6, 12.13, 1.5, fill=PANEL2, line=ACCENT, radius=0.08)
shape_text(box, "暖眸 = 眼镜（第一视角感知） + 语音（说比按方便） + 持续记忆（记得住） + 主动 Agent（靠得住）", size=17, bold=True)
rows = [
    ("一级用户", "60–80 岁独居老人：轻度健忘、生活自理、不愿用手机"),
    ("二级用户", "子女（远程安心）与社区护工（批量服务）"),
    ("典型画像", "王奶奶，68 岁，独居，轻度健忘：常找不到老花镜、偶尔忘吃降压药"),
    ("差异化", "不是“拍照+问答”的眼镜，而是感知驱动、主动触发、记忆沉淀的原生智能体"),
]
for i, (t, d) in enumerate(rows):
    box = add_rect(s, 0.6, 3.35 + i * 0.88, 12.13, 0.72, fill=PANEL, line=BORDER, radius=0.1)
    add_text(s, 0.85, 3.52 + i * 0.88, 1.6, 0.4, t, size=14, bold=True, color=ACCENT)
    add_text(s, 2.6, 3.52 + i * 0.88, 9.9, 0.45, d, size=13.5)
add_footer(s)
set_notes(s, "定位一句话：给独居老人配一个看得见、记得住、靠得住的随身智能体。为什么是眼镜——找物、确认服药、判断跌倒都要第一视角。")

# ================= 04 功能总览 =================
s = new_slide()
add_header(s, 4, "功能总览：7 项能力，3 个 P0 闭环", "P0：可演示闭环 ｜ P1：安全守护与陪伴")
funcs = [
    ("F1", "记忆找物", "被动响应 · 语音提问", "第一视角记忆物品位置，随问随答", "P0"),
    ("F2", "用药提醒+确认", "主动服务 · 时间触发", "到点提醒，视觉确认，漏服通知家人", "P0"),
    ("F3", "出门提醒", "主动服务 · 场景触发", "天气+室内状态联动，出门前一句话", "P0"),
    ("F4", "跌倒检测求助", "主动守护 · 异常触发", "IMU+视觉双通道，无回应自动联系家人", "P1"),
    ("F5", "主动陪伴播报", "主动陪伴 · 情绪触发", "天气/新闻/回忆，低打扰聊天", "P1"),
    ("F6", "家人健康日报", "异步通知 · 每日汇总", "每晚一条“今天都挺好”，异常才详报", "P1"),
    ("F7", "一键紧急求助", "被动响应 · 镜腿长按/SOS", "呼叫紧急联系人并发送位置", "P1"),
]
cw2 = (12.13 - 0.3) / 4
ch2 = 2.28
for i, (fid, name, trig, desc, pri) in enumerate(funcs):
    r, c = divmod(i, 4)
    x = 0.6 + c * (cw2 + 0.1)
    y = 1.55 + r * (ch2 + 0.2)
    box = add_rect(s, x, y, cw2, ch2, fill=PANEL, line=ACCENT if pri == "P0" else BORDER)
    shape_text(box, f"{fid} {name}\n\n{trig}\n{desc}\n\n优先级：{pri}", size=11.5)
add_text(s, 0.6, 6.35, 12.1, 0.4, "反功能：不做医疗诊断 · 不持续云端录像 · 不识别陌生人面孔 · 不做营销打扰", size=12.5, color=MUTED)
add_footer(s)
set_notes(s, "功能分层：P0 是本次比赛演示的三个闭环；P1 是展示完整产品边界的加分项。明确“不做”比“什么都会”更重要。")

# ================= 05 原生智能体：主动触发 =================
s = new_slide()
add_header(s, 5, "原生智能体：主动触发引擎", "不是泛问答——“是否开口”由 Agent 自主评估")
triggers = [
    ("⏰", "时间触发", "08:00 用药计划", "“该吃降压药了”", "HIGH"),
    ("🚪", "场景触发", "识别到走向门口", "“下雨带伞，厨房火没关”", "HIGH"),
    ("🆘", "异常触发", "跌倒 / 久未活动", "“您摔着了吗？”", "HIGH"),
    ("💡", "记忆触发", "重复问同一物品", "“您上次问过，在床头柜”", "MEDIUM"),
    ("💬", "情绪触发", "语气低沉 / 久未说话", "“天气好，出去走走？”", "LOW"),
]
cw3 = (12.13 - 0.4) / 5
for i, (icon, t, cond, out, pri) in enumerate(triggers):
    box = add_rect(s, 0.6 + i * (cw3 + 0.1), 1.6, cw3, 3.0, fill=PANEL2, line=BORDER)
    shape_text(box, f"{icon} {t}\n\n触发条件：\n{cond}\n\n输出：\n{out}\n\n优先级 {pri}", size=11.5)
box = add_rect(s, 0.6, 5.0, 12.13, 1.2, fill=PANEL, line=ACCENT, radius=0.08)
shape_text(box, "决策守卫：是否开口 = f(事件价值, 紧急程度, 打扰成本, 当前上下文)\n深夜不主动闲聊 · 跌倒立即触发 · 对话中降级为静默记录 · 低打扰才是长期陪伴", size=13.5, bold=False)
add_footer(s)
set_notes(s, "这是评分核心：原生智能体必须有主动性。每条主动消息都有触发原因和优先级，且遵守低打扰原则。")

# ================= 06 闭环一：记忆找物 =================
flow_slide(
    6, "闭环一 · 记忆找物", "第一视角记忆：看过即记住，随问随答，找到后复核更新",
    [("① 语音提问", "“我的老花镜呢？”"), ("② 检索记忆", "物品-位置-置信度"), ("③ 语音回答", "“在客厅茶几上”"), ("④ 找到确认", "“找到了”"), ("⑤ 复核更新", "记忆置信度刷新")],
    [("记忆未命中", "现场视觉扫描高频区域，找到后回写记忆", AMBER), ("拒绝泛答", "没有把握时明确告知，不编造位置", RED)],
    "演示实录：09:12 老人提问 → 记忆库检索命中（置信度 0.9）→ 语音回答 → 09:13 复核更新。",
)

# ================= 07 闭环二：用药提醒 =================
flow_slide(
    7, "闭环二 · 用药提醒（主动 Agent 核心演示）", "时间触发 → 主动开口 → 视觉确认 → 健康日志 → 漏服升级",
    [("① 08:00 触发", "用药计划到点"), ("② 主动开口", "“该吃降压药了”"), ("③ 视觉确认", "识别到药盒"), ("④ 确认服药", "“吃完了”"), ("⑤ 写入日志", "健康日志+日报")],
    [("10 分钟未确认", "震动 + 再次提醒", AMBER), ("30 分钟未确认", "通知子女“可能漏服”", RED)],
    "演示实录：08:00 Agent 主动开口（时间触发 HIGH）→ 08:02 视觉确认药盒 → 08:04 确认服药写入健康日志。",
)

# ================= 08 闭环三：出门提醒 =================
flow_slide(
    8, "闭环三 · 出门提醒", "场景触发 → 天气 API + 室内状态联动 → 确认后状态更新",
    [("① 走向门口", "视觉识别出门意图"), ("② 状态查询", "天气 + 灶台状态"), ("③ 联动提醒", "“带伞，火没关”"), ("④ 返回关火", "“火关了，放心出门”"), ("⑤ 状态更新", "室内状态记忆刷新")],
    [("再次出门", "只提醒天气，不重复唠叨", GREEN), ("30 分钟未归", "家人低打扰通知", AMBER)],
    "演示实录：08:50 场景触发提醒 → 08:52 确认关火更新状态 → 08:54 再次出门只提醒天气（状态记忆生效）。",
)

# ================= 09 闭环四：跌倒求助 =================
flow_slide(
    9, "闭环四 · 跌倒检测与求助（安全守护）", "IMU + 视觉双通道确认，降低误报；无回应自动联系家人",
    [("① 双通道检测", "IMU 姿态突变 + 人形倒地"), ("② 语音二次确认", "“您摔着了吗？”"), ("③ 有回应", "“没事”→ 通知家人一条"), ("④ 无回应 15s", "自动呼叫紧急联系人"), ("⑤ 事件沉淀", "入健康日志 + 误报样本")],
    [("责任边界", "定位为提醒+通知工具，非医疗设备", MUTED), ("家属联动", "附定位 + 第一视角快照", PER)],
    "安全守护是完整性的加分项：双通道确认降低误报，二次确认避免打扰，无回应自动升级。",
)

# ================= 10 Agent 架构 =================
s = new_slide()
add_header(s, 10, "Agent 架构：感知 → 决策 → 工具 → 反馈 → 记忆", "端云协同：实时感知在端侧，理解与推理在云端")
layers = [
    ("感知层", "摄像头帧流（第一视角）· 麦克风（含方言 ASR）· IMU · GPS", ACCENT),
    ("情境引擎", "场景标签 · 人物状态 · 物品位置 · 对话 / 时间 / 天气上下文", PER),
    ("Agent 核心", "意图理解 · 主动触发引擎 · 任务规划 · 决策守卫（优先级 / 打扰成本 / 权限）", AMBER),
    ("工具层", "记忆库（物品/事件/健康）· 用药计划 · 天气 API · 紧急联系 · 家人通知", GREEN),
    ("反馈层", "TTS 语音 · 骨传导 · 震动 · LED · 微显示（轻量反馈）", RED),
    ("记忆沉淀", "短期事件 → 长期记忆 · 遗忘策略 · 用户可删除 · 可回溯审计", MUTED),
]
y = 1.42
bh = 0.72
for i, (t, d, c) in enumerate(layers):
    box = add_rect(s, 0.6, y, 12.13, bh, fill=PANEL2, line=c, radius=0.08)
    add_text(s, 0.85, y + 0.16, 2.1, 0.4, t, size=15, bold=True, color=c)
    add_text(s, 3.05, y + 0.18, 9.5, 0.42, d, size=12.5)
    if i < len(layers) - 1:
        add_arrow(s, 6.35, y + bh + 0.015, 0.45, 0.17, color=BORDER, direction="down")
    y += bh + 0.21
add_text(s, 0.6, 6.55, 12.1, 0.4, "决策全程可回溯 → 隐私审计 + 演示可视化（决策轨迹就是“原生智能体”的证据）", size=13, bold=True, color=AMBER)
add_footer(s)
set_notes(s, "架构一句话：眼镜负责看和听，Agent 决定说什么做什么，记忆让服务越用越懂老人。")

# ================= 11 记忆系统与隐私 =================
s = new_slide()
add_header(s, 11, "记忆系统：Agent 的核心资产", "物品位置 · 用药记录 · 生活习惯 · 健康事件")
mems = [
    ("短期记忆", "当前对话 · 最近 30 分钟事件", "对话上下文"),
    ("长期记忆", "物品-位置（时间戳+置信度）· 用药记录 · 习惯 · 健康事件", "随问随答"),
    ("遗忘策略", "低置信度自动降权 · 周期性清理 · 支持“忘记这个”", "隐私友好"),
    ("家人可见", "云端仅同步摘要（服药、出门、异常）", "低打扰"),
]
for i, (t, d, tag) in enumerate(mems):
    box = add_rect(s, 0.6 + (i % 2) * 6.16, 1.55 + (i // 2) * 1.85, 5.96, 1.6, fill=PANEL, line=ACCENT if i == 1 else BORDER)
    shape_text(box, f"{t}\n{d}", size=13)
add_text(s, 0.6, 5.45, 12.1, 0.4, "隐私设计：本地优先 · 最小必要 · 高价值物品才记忆 · 支持查看与删除", size=15, bold=True, color=AMBER)
add_text(s, 0.6, 5.95, 12.1, 0.4, "反功能：不做持续云端录像 · 不识别陌生人面孔 · 采集有指示灯并可随时撤回", size=13, color=MUTED)
add_footer(s)
set_notes(s, "记忆即能力：找物靠记忆、服药靠记忆、出门提醒靠记忆。隐私是底线，本地优先 + 可删除。")

# ================= 12 技术路线 =================
s = new_slide()
add_header(s, 12, "技术路线", "模型 · 语音 · Agent 编排 · 知识库 · 部署")
techs = [
    ("端侧感知", "眼镜摄像头 + IMU；轻量模型（场景 / 物体 / 人形），或 GPASS 端侧 API"),
    ("多模态理解", "GPT-4o / 千问 VL：复杂场景理解、OCR 文字识别"),
    ("语音交互", "支持方言的 ASR（讯飞 / 通义）+ 慢速清晰 TTS"),
    ("Agent 编排", "蚂蚁百宝箱 + GPASS（镜腿触控 / 语音 / 摄像头 API）；备选 LangGraph"),
    ("知识库", "用药常识、老年健康问答（RAG），明确“不做诊断”边界"),
    ("部署方式", "端云协同：实时性要求高的端侧，理解与推理云端，家人通知走云推送"),
]
for i, (t, d) in enumerate(techs):
    box = add_rect(s, 0.6, 1.5 + i * 0.9, 12.13, 0.74, fill=PANEL, line=BORDER, radius=0.1)
    add_text(s, 0.85, 1.66 + i * 0.9, 1.9, 0.4, t, size=14, bold=True, color=ACCENT)
    add_text(s, 2.9, 1.66 + i * 0.9, 9.6, 0.45, d, size=13)
add_footer(s)
set_notes(s, "技术选型强调可落地：初赛用规则版 Agent 跑通闭环，真机阶段替换为多模态 LLM 与 GPASS 能力。")

# ================= 13 数据与合规 =================
s = new_slide()
add_header(s, 13, "数据来源与合规边界", "数据授权 · 隐私保护 · 风险提示 · 行业边界")
comps = [
    ("数据来源", "用户与家属授权采集\n开源 / 自采模拟数据\n演示用剧本数据", PER),
    ("隐私保护", "本地优先 · 最小必要\n人脸模糊 · 加密存储\n可查看、可删除、可撤回", GREEN),
    ("合规边界", "个人信息保护法\n采集指示灯 + 知情同意\n适老化认证", AMBER),
    ("风险声明", "不做医疗诊断（提醒工具）\n跌倒求助为通知辅助\n误报 / 依赖 / 误触发有预案", RED),
]
cw4 = (12.13 - 0.3) / 4
for i, (t, d, c) in enumerate(comps):
    box = add_rect(s, 0.6 + i * (cw4 + 0.1), 1.7, cw4, 3.6, fill=PANEL, line=c)
    shape_text(box, f"{t}\n\n{d}", size=12.5)
add_text(s, 0.6, 5.6, 12.1, 0.4, "核心原则：服务的是“提醒与陪伴”，把医疗诊断、急救责任明确挡在边界之外。", size=15, bold=True, color=AMBER)
add_footer(s)
set_notes(s, "合规是评委必问项：数据从哪来、存哪里、谁能删、出问题谁负责——逐条讲清楚。")

# ================= 14 Demo 演示 =================
s = new_slide()
add_header(s, 14, "Demo：Web 端可运行演示（初赛无需硬件）", "三个闭环 · 决策轨迹可视化 · 浏览器即可复现")
box = add_rect(s, 0.6, 1.5, 5.9, 3.9, fill=PANEL, line=ACCENT, radius=0.06)
shape_text(box, "三个闭环一键切换\n\n① 记忆找物（被动响应）\n② 用药提醒（主动 Agent）\n③ 出门提醒（场景触发）\n\n逐步 / 自动播放 · 浏览器中文语音\n长期记忆面板实时更新", size=13)
box = add_rect(s, 6.75, 1.5, 5.98, 3.9, fill=RGBColor(0x0B, 0x0E, 0x1C), line=BORDER, radius=0.06)
shape_text(box, "[感知] 08:00 场景=卧室 · 语音=无\n[触发] ⏰ 时间触发 · 用药计划（HIGH）\n[工具] 用药计划 → 降压药（1粒/日）\n[记忆] 无变更\n[反馈] 🔊 王奶奶，该吃降压药了。\n\nAgent 决策轨迹实时展示\n= 原生智能体直接证据", size=12, align=PP_ALIGN.LEFT)
add_text(s, 0.6, 5.65, 12.13, 0.4, "无需硬件 · 无需后端 · 双击 index.html 即可运行 · 可部署为在线链接 · 录屏即演示视频", size=14, bold=True, color=AMBER)
add_text(s, 0.6, 6.15, 12.13, 0.4, "配套：Python 版 Demo（三个闭环 --check 全部通过）· 逻辑校验页 · 分镜脚本", size=12.5, color=MUTED)
add_footer(s)
set_notes(s, "现场演示：打开 Web Demo，依次跑三个闭环；强调每一步的决策轨迹和记忆面板变化。断网也能跑（file:// 直接打开）。")

# ================= 15 迭代计划 =================
s = new_slide()
add_header(s, 15, "后续迭代计划", "从可演示闭环到长期陪伴")
vers = [
    ("V1 · 本次比赛", "记忆找物\n用药提醒+确认\n出门提醒", ACCENT),
    ("V2 · 安全守护", "跌倒检测求助\n家人健康日报\n心率 / 血氧体征", GREEN),
    ("V3 · 规模服务", "方言扩展\n社区护工多对多\n端侧模型离线化", AMBER),
    ("长期 · 生态", "沉淀为可复用模板\n入驻智能体商店\n开放工具组件", RED),
]
cw5 = (12.13 - 0.9) / 4
for i, (t, d, c) in enumerate(vers):
    box = add_rect(s, 0.6 + i * (cw5 + 0.3), 1.7, cw5, 2.9, fill=PANEL2, line=c)
    shape_text(box, f"{t}\n\n{d}", size=13.5)
    if i < 3:
        add_arrow(s, 0.6 + (i + 1) * (cw5 + 0.3) - 0.26, 2.95, 0.24, 0.3, color=MUTED, direction="right")
add_text(s, 0.6, 5.1, 12.1, 0.5, "设计原则：先做深一个场景，再做宽多个场景；每一步都保留可演示、可验证的任务闭环。", size=15, bold=True, color=AMBER)
add_footer(s)
set_notes(s, "迭代路线突出可落地：本次比赛交付可运行 Demo，后续按安全守护、规模服务、生态沉淀推进。")

# ================= 16 结尾 =================
s = new_slide()
add_text(s, 0.9, 2.3, 11.5, 1.0, "谢谢聆听", size=52, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
add_text(s, 0.9, 3.5, 11.5, 0.6, "暖眸——看得见、记得住、靠得住", size=20, color=AMBER, align=PP_ALIGN.CENTER)
add_text(s, 0.9, 4.3, 11.5, 0.5, "让每一位独居老人，都有一位 24 小时在身边的智能守护者", size=15, color=TEXT, align=PP_ALIGN.CENTER)
add_text(s, 0.9, 6.0, 11.5, 0.5, "队伍：＿＿＿＿＿＿   |   联系方式：＿＿＿＿＿＿", size=13, color=MUTED, align=PP_ALIGN.CENTER)
set_notes(s, "结尾 30 秒：回归愿景——不是参数竞赛，而是让老人被看见、被记得、被守护。")

# ---------------- 保存 ----------------
import os

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "暖眸-居家养老AI眼镜智能体-路演PPT.pptx")
prs.save(out)
print("已生成：", out)
print("页数：", len(prs.slides))
