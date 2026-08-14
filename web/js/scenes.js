/* 暖眸 · 三个演示闭环的场景数据（与 Python 版一致） */
'use strict';

const SCENES = [
  {
    id: 'find_glasses',
    name: '记忆找物',
    badge: '被动响应',
    icon: '👓',
    intro: '老人找不到老花镜 → 眼镜检索第一视角记忆 → 语音回答位置 → 找到后复核更新记忆。',
    context: { weather: '晴', kitchen_fire_on: false },
    initialMemory: [
      { type: 'item', object: '老花镜', location: '客厅茶几', time: '昨天 14:32', confidence: 0.9 },
      { type: 'item', object: '钥匙', location: '玄关鞋柜', time: '昨天 17:00', confidence: 0.95 },
      { type: 'item', object: '降压药', location: '餐桌药盒', time: '昨天 08:00', confidence: 0.98 },
      { type: 'fact', content: '王奶奶每天早上 8 点吃降压药' },
    ],
    steps: [
      {
        name: '老人提问：老花镜在哪',
        expect: { feedback_contains: '客厅茶几', tool: '记忆库检索' },
        perception: {
          timestamp: '09:12',
          scene: '客厅',
          personState: '坐在沙发上翻找',
          visibleObjects: ['茶杯', '电视', '报纸'],
          speech: '我的老花镜呢？',
        },
      },
      {
        name: '老人找到，记忆复核更新',
        expect: { feedback_contains: '记下了' },
        perception: {
          timestamp: '09:13',
          scene: '客厅茶几',
          personState: '起身走向茶几',
          visibleObjects: ['老花镜'],
          speech: '找到了',
        },
      },
    ],
  },
  {
    id: 'medication',
    name: '用药提醒',
    badge: '主动 Agent',
    icon: '💊',
    intro: '08:00 时间触发 → 主动开口提醒 → 视觉确认药盒 → 确认服药 → 写入健康日志（漏服会升级通知家人）。',
    context: { weather: '雨', kitchen_fire_on: false },
    initialMemory: [
      { type: 'item', object: '老花镜', location: '客厅茶几', time: '昨天 14:32', confidence: 0.9 },
      { type: 'item', object: '降压药', location: '餐桌药盒', time: '昨天 08:00', confidence: 0.98 },
      { type: 'fact', content: '王奶奶每天早上 8 点吃降压药' },
    ],
    steps: [
      {
        name: '08:00 时间触发：主动提醒服药',
        expect: { feedback_contains: '该吃降压药了', trigger: '时间触发' },
        perception: {
          timestamp: '08:00',
          scene: '卧室',
          personState: '坐在床边',
          visibleObjects: [],
          speech: null,
        },
      },
      {
        name: '老人取药，视觉确认',
        expect: { feedback_contains: '降压药' },
        perception: {
          timestamp: '08:02',
          scene: '餐厅',
          personState: '站立',
          visibleObjects: ['降压药药盒'],
          speech: '好，我这就吃',
        },
      },
      {
        name: '确认服药，写入健康日志',
        expect: { feedback_contains: '已记录', tool: '健康日志' },
        perception: {
          timestamp: '08:04',
          scene: '餐厅',
          personState: '坐下喝水',
          visibleObjects: ['水杯'],
          speech: '吃完了',
        },
      },
    ],
  },
  {
    id: 'door_reminder',
    name: '出门提醒',
    badge: '场景触发',
    icon: '🚪',
    intro: '识别到走向门口 → 天气 API + 室内状态联动提醒 → 返回关火后状态更新 → 再次出门只提醒天气。',
    context: { weather: '雨', kitchen_fire_on: true },
    initialMemory: [
      { type: 'item', object: '老花镜', location: '客厅茶几', time: '昨天 14:32', confidence: 0.9 },
      { type: 'item', object: '降压药', location: '餐桌药盒', time: '昨天 08:00', confidence: 0.98 },
      { type: 'fact', content: '王奶奶每天早上 8 点吃降压药' },
    ],
    steps: [
      {
        name: '走向门口：天气 + 关火联动提醒',
        expect: { feedback_contains: '带伞', trigger: '场景触发', tool: '天气 API + 室内状态记忆' },
        perception: {
          timestamp: '08:50',
          scene: '客厅',
          personState: '走向门口',
          visibleObjects: ['门口', '雨伞架'],
          speech: null,
        },
      },
      {
        name: '返回厨房关火，状态确认',
        expect: { feedback_contains: '放心出门' },
        perception: {
          timestamp: '08:52',
          scene: '厨房',
          personState: '站立',
          visibleObjects: ['灶台'],
          speech: '火关了',
        },
      },
      {
        name: '再次出门：只提醒天气',
        expect: { feedback_contains: '带伞' },
        perception: {
          timestamp: '08:54',
          scene: '客厅',
          personState: '再次走向门口',
          visibleObjects: ['门口'],
          speech: null,
        },
      },
    ],
  },
];

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SCENES };
}
