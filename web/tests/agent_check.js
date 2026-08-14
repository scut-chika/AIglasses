/* 暖眸 Web Agent 逻辑校验（Node.js，无需浏览器）：
   node web/tests/agent_check.js */
'use strict';

const { MemoryStore, WarmEyeAgent } = require('../js/agent.js');
const { SCENES } = require('../js/scenes.js');

let failures = 0;

function assert(cond, msg) {
  if (cond) {
    console.log('  PASS:', msg);
  } else {
    console.error('  FAIL:', msg);
    failures++;
  }
}

for (const scene of SCENES) {
  console.log(`\n[${scene.id}] ${scene.name}`);
  const memory = new MemoryStore(scene.initialMemory);
  const agent = new WarmEyeAgent(memory, '王奶奶', '暖眸', scene.context);

  scene.steps.forEach((step, i) => {
    const { trace, feedback } = agent.tick(step.perception);
    const text = feedback && feedback.text ? feedback.text : '';
    console.log(`  步骤 ${i + 1}：${step.name}`);
    trace.forEach(t => console.log(`    ${t.label} | ${t.text}`));

    assert(text.length > 0, '有语音反馈');
    const exp = step.expect || {};
    if (exp.feedback_contains) {
      assert(text.includes(exp.feedback_contains), `反馈包含「${exp.feedback_contains}」`);
    }
    if (exp.tool) {
      assert(trace.some(t => t.kind === 'tool' && t.text.includes(exp.tool)), `调用工具「${exp.tool}」`);
    }
    if (exp.trigger) {
      assert(trace.some(t => t.kind === 'trigger' && t.text.includes(exp.trigger)), `触发「${exp.trigger}」`);
    }
  });
}

console.log(failures ? `\n✗ ${failures} 项未通过` : '\n✓ 全部校验通过');
process.exit(failures ? 1 : 0);
