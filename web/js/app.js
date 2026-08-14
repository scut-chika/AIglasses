/* 暖眸 Web Demo 控制器：场景切换、逐步播放、决策轨迹、语音、记忆面板 */
'use strict';

const $ = id => document.getElementById(id);

const SCENE_ICONS = {
  '客厅': '🛋️',
  '客厅茶几': '🛋️',
  '卧室': '🛏️',
  '餐厅': '🍚',
  '厨房': '🍳',
  '门口': '🚪',
};

const OBJECT_ICONS = {
  '茶杯': '☕',
  '电视': '📺',
  '报纸': '📰',
  '老花镜': '👓',
  '钥匙': '🔑',
  '降压药': '💊',
  '降压药药盒': '💊',
  '水杯': '🥛',
  '灶台': '🔥',
  '门口': '🚪',
  '雨伞架': '🌂',
};

const TRIGGER_ICONS = { time: '⏰', scene: '🚪', anomaly: '🆘', memory: '💡', emotion: '💬' };

const state = {
  scene: null,
  memory: null,
  agent: null,
  stepIndex: 0,
  currentStepName: '',
  finished: false,
  autoplay: false,
  ttsOn: true,
  timer: null,
};

function init() {
  renderTabs();
  loadScene(SCENES[0].id);
  bindControls();
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function renderTabs() {
  const wrap = $('sceneTabs');
  wrap.innerHTML = '';
  SCENES.forEach(s => {
    const btn = document.createElement('button');
    btn.className = 'scene-tab';
    btn.dataset.id = s.id;
    btn.innerHTML = `${s.icon} ${esc(s.name)}<em>${esc(s.badge)}</em>`;
    btn.addEventListener('click', () => loadScene(s.id));
    wrap.appendChild(btn);
  });
}

function loadScene(id) {
  stopAutoplay();
  const scene = SCENES.find(s => s.id === id);
  if (!scene) return;
  state.scene = scene;
  state.memory = new MemoryStore(scene.initialMemory);
  state.agent = new WarmEyeAgent(state.memory, '王奶奶', '暖眸', scene.context);
  state.stepIndex = 0;
  state.currentStepName = '';
  state.finished = false;

  document.querySelectorAll('.scene-tab').forEach(b => b.classList.toggle('active', b.dataset.id === id));
  clearLog();
  $('sceneIntro').textContent = scene.intro || '';
  updateVisual(null, null, []);
  renderMemory();
  updateControls();
  pushInfo(`场景已加载：${scene.name}。点击「下一步」开始，或开启自动播放。`, 'info');
}

function clearLog() {
  $('traceLog').innerHTML = '';
}

function pushInfo(text) {
  const log = $('traceLog');
  const row = document.createElement('div');
  row.className = 'entry info';
  row.innerHTML = `<span class="label">系统</span><span class="text">${esc(text)}</span>`;
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
}

function appendTrace(trace, speakIt) {
  const log = $('traceLog');
  let spoken = null;
  for (const entry of trace) {
    const row = document.createElement('div');
    row.className = 'entry ' + entry.kind;
    row.innerHTML = `<span class="label">${esc(entry.label)}</span><span class="text">${esc(entry.text)}</span>`;
    log.appendChild(row);
    if (entry.kind === 'feedback' && entry.spoken) spoken = entry.spoken;
  }
  log.scrollTop = log.scrollHeight;
  if (speakIt && spoken) speak(spoken);
}

function speak(text) {
  if (!state.ttsOn || !window.speechSynthesis) return;
  try {
    const clean = String(text).replace(/^🔊\s*/, '').replace(/（通道：[^）]*）/g, '');
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = 'zh-CN';
    u.rate = 0.92;
    const voices = window.speechSynthesis.getVoices();
    const zh = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('zh'));
    if (zh) u.voice = zh;
    window.speechSynthesis.speak(u);
  } catch (e) {
    /* 静默降级 */
  }
}

function updateVisual(p, feedback, trace) {
  $('stepName').textContent = state.currentStepName || '—';

  if (!p) {
    $('sceneIcon').textContent = '🕶️';
    $('sceneName').textContent = '等待开始';
    $('personState').textContent = '—';
    $('visibleChips').innerHTML = '';
    $('elderSpeech').textContent = '—';
    $('elderBubble').hidden = true;
    $('agentBubble').hidden = true;
    $('triggerBadge').hidden = true;
    return;
  }

  $('sceneIcon').textContent = SCENE_ICONS[p.scene] || '🕶️';
  $('sceneName').textContent = p.scene;
  $('personState').textContent = p.personState;
  $('visibleChips').innerHTML = p.visibleObjects.length
    ? p.visibleObjects.map(o => `<span class="chip">${OBJECT_ICONS[o] || ''} ${esc(o)}</span>`).join('')
    : '<span class="muted">无</span>';
  $('elderSpeech').textContent = p.speech || '（无语音输入）';

  const trig = (trace || []).find(e => e.kind === 'trigger');
  if (trig) {
    $('triggerBadge').textContent = `${TRIGGER_ICONS[trig.type] || '⚡'} ${trig.text}`;
    $('triggerBadge').hidden = false;
  } else {
    $('triggerBadge').hidden = true;
  }

  $('elderBubble').textContent = p.speech || '';
  $('elderBubble').hidden = !p.speech;
  if (feedback && feedback.text) {
    $('agentBubble').textContent = '🔊 ' + feedback.text;
    $('agentBubble').hidden = false;
  } else {
    $('agentBubble').hidden = true;
  }
}

function renderMemory() {
  const items = state.memory.itemSummary();
  $('memoryItems').innerHTML = items.length
    ? items.map(it =>
        `<div class="mem-item">${OBJECT_ICONS[it.object] || '📦'} <b>${esc(it.object)}</b> → ${esc(it.location)} ` +
        `<span class="muted">${esc(it.time)} · 置信度 ${it.confidence}</span></div>`
      ).join('')
    : '<div class="muted">暂无物品记忆</div>';

  const events = state.memory.events();
  $('memoryEvents').innerHTML = events.length
    ? events.map(ev =>
        `<div class="mem-item">✅ ${esc(ev.detail)} <span class="muted">${esc(ev.time)}</span></div>`
      ).join('')
    : '<div class="muted">暂无事件记录</div>';
}

function next() {
  if (!state.scene || state.finished) return;
  const scene = state.scene;
  if (state.stepIndex >= scene.steps.length) {
    state.finished = true;
    updateControls();
    return;
  }
  const step = scene.steps[state.stepIndex];
  state.currentStepName = step.name;
  const p = step.perception;
  const { trace, feedback } = state.agent.tick(p);
  appendTrace(trace, true);
  updateVisual(p, feedback, trace);
  renderMemory();
  state.stepIndex++;
  if (state.stepIndex >= scene.steps.length) {
    state.finished = true;
    pushInfo('✅ 闭环完成：任务目标达成，记忆与健康日志已沉淀。');
  }
  updateControls();
}

function prev() {
  if (!state.scene || state.stepIndex <= 0) return;
  stopAutoplay();
  replayTo(state.stepIndex - 1);
}

function replayTo(target) {
  const scene = state.scene;
  state.memory = new MemoryStore(scene.initialMemory);
  state.agent = new WarmEyeAgent(state.memory, '王奶奶', '暖眸', scene.context);
  clearLog();
  renderMemory();
  for (let i = 0; i < target; i++) {
    const step = scene.steps[i];
    state.currentStepName = step.name;
    const p = step.perception;
    const { trace, feedback } = state.agent.tick(p);
    appendTrace(trace, false);
    updateVisual(p, feedback, trace);
    renderMemory();
  }
  state.stepIndex = target;
  state.finished = false;
  updateControls();
}

function reset() {
  if (state.scene) loadScene(state.scene.id);
}

function toggleAutoplay() {
  if (state.autoplay) {
    stopAutoplay();
  } else {
    state.autoplay = true;
    $('btnAuto').textContent = '暂停 ⏸';
    $('btnAuto').classList.add('active');
    state.timer = setInterval(() => {
      if (state.finished) stopAutoplay();
      else next();
    }, 3800);
  }
}

function stopAutoplay() {
  state.autoplay = false;
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
  $('btnAuto').textContent = '自动播放 ▶';
  $('btnAuto').classList.remove('active');
}

function toggleTts() {
  state.ttsOn = !state.ttsOn;
  $('btnTts').textContent = state.ttsOn ? '语音 🔊' : '语音 🔇';
  $('btnTts').classList.toggle('active', !state.ttsOn);
}

function updateControls() {
  $('btnPrev').disabled = !state.scene || state.stepIndex <= 0;
  $('btnNext').disabled = !state.scene || state.finished;
  $('stepIndicator').textContent = state.scene ? `步骤 ${state.stepIndex} / ${state.scene.steps.length}` : '';
  $('btnNext').textContent = state.finished ? '已完成 ✅' : '下一步 ▶';
}

function bindControls() {
  $('btnNext').addEventListener('click', next);
  $('btnPrev').addEventListener('click', prev);
  $('btnAuto').addEventListener('click', toggleAutoplay);
  $('btnTts').addEventListener('click', toggleTts);
  $('btnReset').addEventListener('click', reset);
  document.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight') next();
    if (e.key === 'ArrowLeft') prev();
  });
}

document.addEventListener('DOMContentLoaded', init);
