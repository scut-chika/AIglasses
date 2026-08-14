/* 暖眸 Agent 核心（浏览器版）—— 与 Python 版逻辑一致。
   感知 → 理解 → 主动触发 → 决策 → 工具 → 反馈 → 记忆 */
'use strict';

const INTENT_LABELS = {
  find_item: '找物',
  confirm_medication: '确认服药',
  sos: '紧急求助',
  ack: '应答/确认',
  chat: '闲聊',
  none: '无主动请求',
};

const TRIGGER_LABELS = {
  time: '时间触发',
  scene: '场景触发',
  anomaly: '异常触发',
  memory: '记忆触发',
  emotion: '情绪触发',
};

const ITEM_ALIASES = {
  '老花镜': '老花镜',
  '眼镜': '老花镜',
  '钥匙': '钥匙',
  '降压药': '降压药',
  '药盒': '降压药',
  '药': '降压药',
  '手机': '手机',
  '遥控器': '遥控器',
};

class MemoryStore {
  constructor(initialItems) {
    this.items = initialItems ? initialItems.map(it => ({ ...it })) : [];
  }

  findItem(objectName) {
    const hits = this.items.filter(it => it.type === 'item' && it.object.includes(objectName));
    if (!hits.length) return null;
    return hits.reduce((best, it) => (it.confidence > best.confidence ? it : best));
  }

  updateItem(objectName, location, time, confidence) {
    for (const it of this.items) {
      if (it.type === 'item' && it.object.includes(objectName)) {
        if (location) it.location = location;
        if (time) it.time = time;
        if (confidence !== undefined) it.confidence = confidence;
        return it;
      }
    }
    const item = {
      type: 'item',
      object: objectName,
      location: location || '未知',
      time: time || new Date().toLocaleString('zh-CN'),
      confidence: confidence === undefined ? 0.5 : confidence,
    };
    this.items.push(item);
    return item;
  }

  addEvent(kind, detail) {
    const ev = { type: 'event', kind, detail, time: new Date().toLocaleString('zh-CN') };
    this.items.push(ev);
    return ev;
  }

  itemSummary() {
    return this.items.filter(it => it.type === 'item');
  }

  events() {
    return this.items.filter(it => it.type === 'event');
  }
}

class WarmEyeAgent {
  constructor(memory, elderName = '王奶奶', agentName = '暖眸', context = {}) {
    this.memory = memory;
    this.elder = elderName;
    this.name = agentName;
    this.context = { ...context };
    this.medicationPlan = [{ name: '降压药', time: '08:00', dose: '1粒/日' }];
    this.escalationCount = 0;
    this.pendingFind = null;
    this.lastFind = null;
    this.medicationPrompted = false;
  }

  /* ① 意图理解 */
  understand(speech) {
    if (!speech) return { kind: 'none', target: null, raw: '' };
    const s = speech.trim();
    if (/(在哪|哪里|找不到|放哪|找不到了|呢)/.test(s)) {
      for (const [alias, canonical] of Object.entries(ITEM_ALIASES)) {
        if (s.includes(alias)) return { kind: 'find_item', target: canonical, raw: s };
      }
      return { kind: 'find_item', target: null, raw: s };
    }
    if (/(吃完|吃了|喝完了|已经吃)/.test(s)) return { kind: 'confirm_medication', target: null, raw: s };
    if (/(救命|help|摔倒|摔了|求助|帮忙)/i.test(s)) return { kind: 'sos', target: null, raw: s };
    if (/(谢谢|嗯|好|知道了|找到了|这就|关了)/.test(s)) return { kind: 'ack', target: null, raw: s };
    return { kind: 'chat', target: null, raw: s };
  }

  /* ② 主动触发评估 */
  proactiveTriggers(p, intent) {
    const triggers = [];

    for (const med of this.medicationPlan) {
      if (p.timestamp.startsWith(med.time)) {
        triggers.push({ kind: 'time', priority: 'HIGH', detail: `${p.timestamp} 用药计划：${med.name}` });
        this.medicationPrompted = true;
      }
    }

    if (p.personState.includes('门口') || p.personState.includes('出门')) {
      const details = [];
      const weather = this.context.weather;
      if (weather && weather !== '晴') details.push(`今天${weather}，带伞`);
      if (this.context.kitchen_fire_on) details.push('厨房火好像还开着');
      if (details.length) triggers.push({ kind: 'scene', priority: 'HIGH', detail: details.join(' / ') });
    }

    if (p.personState.includes('跌倒') || p.personState.includes('倒地')) {
      triggers.push({ kind: 'anomaly', priority: 'HIGH', detail: 'IMU 姿态突变 + 视觉人形倒地（双通道）' });
    }

    if (intent.kind === 'find_item' && intent.target && intent.target === this.lastFind) {
      triggers.push({ kind: 'memory', priority: 'MEDIUM', detail: `${this.elder} 又问了同一个物品：${intent.target}` });
    }

    return triggers;
  }

  /* ③ 决策 */
  decide(p, intent, triggers) {
    if (intent.kind === 'find_item') return 'find_item';
    if (intent.kind === 'confirm_medication') return 'confirm_medication';
    if (intent.kind === 'sos') return 'sos';
    if (intent.kind === 'ack') return 'ack';
    if (intent.kind === 'chat') return 'chat';
    if (triggers.length) {
      const t = triggers[0];
      if (t.kind === 'time') return 'medication_prompt';
      if (t.kind === 'scene') return 'door_reminder';
      if (t.kind === 'anomaly') return 'fall_check';
      if (t.kind === 'memory') return 'find_item';
    }
    return 'observe';
  }

  /* ④ 执行（工具调用 + 反馈） */
  act(action, p, intent) {
    const result = { tool: null, memoryUpdated: false, detail: '' };
    let feedback = null;

    if (action === 'medication_prompt') {
      const med = this.medicationPlan[0];
      feedback = { text: `${this.elder}，该吃${med.name}了。`, channel: 'voice', priority: 'HIGH' };
      result.tool = '用药计划';
      result.detail = `当前药品：${med.name}（${med.dose}）`;
    } else if (action === 'door_reminder') {
      const parts = [];
      const weather = this.context.weather;
      if (weather && weather !== '晴') parts.push(`今天${weather}，带伞`);
      if (this.context.kitchen_fire_on) parts.push('厨房火好像还开着');
      const detail = parts.join('，');
      feedback = { text: `${this.elder}，${detail}，出门前注意一下。`, channel: 'voice', priority: 'HIGH' };
      result.tool = '天气 API + 室内状态记忆';
      result.detail = detail;
    } else if (action === 'fall_check') {
      feedback = { text: `${this.elder}，您摔着了吗？需要帮忙吗？`, channel: 'voice', priority: 'HIGH' };
      result.tool = '语音二次确认';
      result.detail = '等待回应；无回应 15 秒后自动呼叫紧急联系人';
    } else if (action === 'find_item') {
      const target = intent.target || this.pendingFind;
      this.pendingFind = target;
      if (!target) {
        feedback = { text: '您要找什么？再说一遍好吗？', priority: 'MEDIUM' };
      } else {
        this.lastFind = target;
        const item = this.memory.findItem(target);
        if (item && item.confidence >= 0.7) {
          feedback = { text: `${this.elder}，${target}在${item.location}，我上次看到是${item.time}。`, priority: 'MEDIUM' };
          result.tool = '记忆库检索';
          result.detail = `命中 ${item.object}，置信度 ${item.confidence}`;
        } else {
          const found = p.visibleObjects.find(obj => target.includes(obj) || obj.includes(target));
          if (found) {
            this.memory.updateItem(target, p.scene, p.timestamp, 0.95);
            feedback = { text: `找到了，就在${p.scene}。我记下了。`, priority: 'MEDIUM' };
            result.tool = '视觉扫描';
            result.memoryUpdated = true;
            result.detail = `在现场识别到 ${found}`;
          } else {
            feedback = { text: `暂时没找到，我帮您记着，下次看到${target}再告诉您。`, priority: 'LOW' };
            result.tool = '记忆库检索';
            result.detail = '未命中，尝试视觉扫描';
          }
        }
      }
    } else if (action === 'confirm_medication') {
      this.memory.addEvent('medication', `${p.timestamp} 确认服药`);
      feedback = { text: '好的，已记录您这次服药。今晚 8 点我会把今天的情况发给您女儿。', channel: 'voice' };
      result.tool = '健康日志';
      result.memoryUpdated = true;
      result.detail = '服药记录已写入；漏服升级计数重置';
    } else if (action === 'ack') {
      if (this.medicationPrompted && p.visibleObjects.some(obj => obj.includes('药'))) {
        feedback = { text: '我看到您拿着降压药了，吃完跟我说一声。', channel: 'voice' };
        result.tool = '视觉确认';
        result.detail = '识别到药盒/药瓶';
      } else if (this.pendingFind) {
        const found = p.visibleObjects.find(obj => this.pendingFind.includes(obj) || obj.includes(this.pendingFind));
        if (found) {
          this.memory.updateItem(this.pendingFind, p.scene, p.timestamp, 0.95);
          feedback = { text: `太好了！我记下了，${this.pendingFind}在${p.scene}。`, channel: 'voice' };
          result.tool = '记忆更新';
          result.memoryUpdated = true;
          result.detail = `${this.pendingFind} → ${p.scene}`;
        } else {
          feedback = { text: '好的，有需要随时叫我。', priority: 'LOW' };
        }
      } else if (p.scene === '厨房' && this.context.kitchen_fire_on) {
        this.context.kitchen_fire_on = false;
        feedback = { text: '火已经关了，可以放心出门。', channel: 'voice' };
        result.tool = '视觉确认';
        result.memoryUpdated = true;
        result.detail = '灶台已关火，室内状态记忆已更新';
      } else {
        feedback = { text: '好的，有需要随时叫我。', priority: 'LOW' };
      }
    } else if (action === 'sos') {
      feedback = { text: `${this.elder}，别怕，我马上联系您女儿，并发送您的位置。`, channel: 'notify_family', priority: 'HIGH' };
      result.tool = '紧急联系';
      result.memoryUpdated = true;
      result.detail = '已通知紧急联系人（定位 + 第一视角快照）';
    } else if (action === 'chat') {
      feedback = { text: '嗯嗯，我听着呢。要不要我给您念念今天的新闻？', priority: 'LOW' };
    } else {
      feedback = { text: '', channel: 'silent', priority: 'LOW' };
    }

    return { feedback, result };
  }

  /* 主循环：返回决策轨迹 + 反馈 */
  tick(p) {
    const trace = [];
    const intent = this.understand(p.speech);
    const triggers = this.proactiveTriggers(p, intent);

    const visible = p.visibleObjects.length ? p.visibleObjects.join(', ') : '无';
    trace.push({
      label: '感知',
      kind: 'perception',
      text: `${p.timestamp} 场景=${p.scene} · 状态=${p.personState} · 可见=[${visible}]${p.speech ? ` · 语音="${p.speech}"` : ' · 语音=无'}`,
    });

    if (intent.kind !== 'none') {
      trace.push({
        label: '理解',
        kind: 'intent',
        text: `意图=${INTENT_LABELS[intent.kind] || intent.kind}${intent.target ? ` · 目标=${intent.target}` : ''}`,
      });
    }

    for (const t of triggers) {
      trace.push({
        label: '触发',
        kind: 'trigger',
        type: t.kind,
        text: `${TRIGGER_LABELS[t.kind] || t.kind} · ${t.detail}（优先级 ${t.priority}）`,
      });
    }

    const action = this.decide(p, intent, triggers);
    const { feedback, result } = this.act(action, p, intent);

    if (result.tool) trace.push({ label: '工具', kind: 'tool', text: `${result.tool} → ${result.detail}` });
    trace.push({ label: '记忆', kind: 'memory', text: result.memoryUpdated ? '已更新' : '无变更' });
    if (feedback.text) {
      const ch = feedback.channel && feedback.channel !== 'voice' && feedback.channel !== 'silent'
        ? `（通道：${feedback.channel}）` : '';
      trace.push({ label: '反馈', kind: 'feedback', text: `${feedback.text}${ch}`, spoken: feedback.text });
    }

    return { trace, feedback };
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MemoryStore, WarmEyeAgent, INTENT_LABELS, TRIGGER_LABELS };
}
