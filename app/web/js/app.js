/* 暖眸 · 真实 Agent 前端控制器 */
'use strict';

const $ = id => document.getElementById(id);

const state = {
  imageB64: null,
  ttsOn: true,
  stream: null,
};

/* ---------- 工具 ---------- */
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || 'GET',
    headers: opts.body ? { 'Content-Type': 'application/json' } : undefined,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  return res.json();
}

function speak(text) {
  if (!state.ttsOn || !window.speechSynthesis || !text) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'zh-CN';
    u.rate = 0.92;
    const zh = window.speechSynthesis.getVoices().find(v => v.lang && v.lang.toLowerCase().startsWith('zh'));
    if (zh) u.voice = zh;
    window.speechSynthesis.speak(u);
  } catch (e) { /* ignore */ }
}

/* ---------- 初始化 ---------- */
async function init() {
  bindTabs();
  bindUsePanel();
  bindConfigPanel();
  await refreshHealth();
  await refreshState();
  renderStatus('就绪。选择场景或开启摄像头，然后点击「运行一步」。');
}

function bindTabs() {
  $('tabUse').addEventListener('click', () => switchTab('use'));
  $('tabConfig').addEventListener('click', () => switchTab('config'));
}

function switchTab(name) {
  const use = name === 'use';
  $('panelUse').hidden = !use;
  $('panelConfig').hidden = use;
  $('tabUse').classList.toggle('active', use);
  $('tabConfig').classList.toggle('active', !use);
}

/* ---------- 健康与状态 ---------- */
async function refreshHealth() {
  try {
    const h = await api('/api/health');
    const badge = $('healthBadge');
    badge.textContent = h.ok ? `已配置：${h.elder_name || ''} 的 AI 服务` : '未配置 AI Key';
    badge.classList.toggle('ok', h.ok);
    $('modelBadge').textContent = h.ok ? `${h.model} @ ${h.base_url || ''}` : '';
  } catch (e) {
    $('healthBadge').textContent = '服务未连接';
  }
}

async function refreshState() {
  try {
    const s = await api('/api/state');
    renderMemory(s);
    renderConfigForm(s.config || {});
  } catch (e) { /* ignore */ }
}

function renderMemory(s) {
  const items = s.memory_items || [];
  $('memoryItems').innerHTML = items.length
    ? items.map(it => `<div class="mem-item del" title="点击删除该记忆" data-obj="${esc(it.object)}">📦 <b>${esc(it.object)}</b> → ${esc(it.location)} <span class="muted">${esc(it.time)} · 置信度 ${it.confidence}</span></div>`).join('')
    : '<div class="muted">暂无物品记忆</div>';
  document.querySelectorAll('.mem-item.del').forEach(el => {
    el.addEventListener('click', async () => {
      await api('/api/memory/delete', { method: 'POST', body: { object: el.dataset.obj } });
      refreshState();
    });
  });

  const events = s.events || [];
  $('memoryEvents').innerHTML = events.length
    ? events.map(ev => `<div class="mem-item">✅ ${esc(ev.detail)} <span class="muted">${esc(ev.time)}</span></div>`).join('')
    : '<div class="muted">暂无事件记录</div>';

  const notify = s.notify || [];
  $('notifyList').innerHTML = notify.length
    ? notify.map(n => `<div class="mem-item">📤 ${esc(n)}</div>`).join('')
    : '<div class="muted">暂无家人通知记录</div>';
}

/* ---------- 操作面板 ---------- */
function bindUsePanel() {
  $('btnRun').addEventListener('click', runStep);
  $('btnClearLog').addEventListener('click', () => { $('traceLog').innerHTML = ''; });
  $('btnReset').addEventListener('click', async () => {
    const r = await api('/api/reset', { method: 'POST', body: {} });
    clearTrace();
    renderMemory(r.state || {});
    renderStatus('会话已重置');
  });
  $('btnTts').addEventListener('click', () => {
    state.ttsOn = !state.ttsOn;
    $('btnTts').textContent = state.ttsOn ? '语音 🔊' : '语音 🔇';
    $('btnTts').classList.toggle('active', !state.ttsOn);
  });

  bindCamera();
  bindUpload();
  bindAsr();
  bindQuickChips();
}

function renderStatus(text) {
  $('statusLine').textContent = text;
}

function appendTrace(trace, speakIt) {
  const log = $('traceLog');
  let spoken = null;
  for (const entry of trace || []) {
    const row = document.createElement('div');
    row.className = 'entry ' + (entry.kind || 'info');
    row.innerHTML = `<span class="label">${esc(entry.label || '')}</span><span class="text">${esc(entry.text || '')}</span>`;
    log.appendChild(row);
    if (entry.kind === 'feedback' && entry.spoken) spoken = entry.spoken;
  }
  log.scrollTop = log.scrollHeight;
  if (speakIt && spoken) speak(spoken);
}

function clearTrace() {
  $('traceLog').innerHTML = '';
}

async function runStep() {
  const btn = $('btnRun');
  btn.disabled = true;
  btn.textContent = '运行中…';
  renderStatus('Agent 正在感知与决策…');
  try {
    const body = {
      image_b64: state.imageB64,
      scene_text: $('sceneText').value.trim(),
      speech: $('speech').value.trim(),
      force_time: $('forceTime').checked ? '08:00' : null,
    };
    const r = await api('/api/run', { method: 'POST', body });
    appendTrace(r.trace || [], true);
    if (r.perception) {
      $('personState').textContent = `${r.perception.scene || '?'} · ${r.perception.person_state || '未知'}`;
      $('visibleChips').innerHTML = (r.perception.visible_objects || []).length
        ? r.perception.visible_objects.map(o => `<span class="chip">${esc(o)}</span>`).join('')
        : '<span class="muted">无</span>';
    }
    renderMemory(r.state || {});
    if (r.ok) {
      renderStatus(r.feedback ? `反馈：${r.feedback}` : '本步为静默观察（低打扰）。');
    } else {
      renderStatus(`⚠ ${r.message || '运行失败'}`);
      if ((r.message || '').includes('API Key')) switchTab('config');
    }
  } catch (e) {
    renderStatus(`请求失败：${e}`);
  } finally {
    btn.disabled = false;
    btn.textContent = '运行一步 ▶';
  }
}

/* ---------- 摄像头 / 图片 ---------- */
function bindCamera() {
  $('btnCamera').addEventListener('click', async () => {
    try {
      state.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      const video = $('video');
      video.srcObject = state.stream;
      video.hidden = false;
      $('camPlaceholder').hidden = true;
      $('btnCapture').disabled = false;
      $('btnCamera').textContent = '摄像头已开启';
    } catch (e) {
      alert('无法开启摄像头：' + e.message + '\n可改用「上传图片」或手动场景描述。');
    }
  });
  $('btnCapture').addEventListener('click', captureFrame);
  $('btnClearFrame').addEventListener('click', clearFrame);
}

function captureFrame() {
  const video = $('video');
  if (!video.srcObject) return;
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 1280;
  canvas.height = video.videoHeight || 720;
  canvas.getContext('2d').drawImage(video, 0, 0);
  setFrame(canvas.toDataURL('image/jpeg', 0.72));
}

function bindUpload() {
  $('btnUpload').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', e => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => downscale(reader.result, dataUrl => setFrame(dataUrl));
    reader.readAsDataURL(file);
  });
}

function downscale(dataUrl, cb) {
  const img = new Image();
  img.onload = () => {
    const maxW = 1280;
    const scale = Math.min(1, maxW / img.width);
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
    cb(canvas.toDataURL('image/jpeg', 0.72));
  };
  img.src = dataUrl;
}

function setFrame(dataUrl) {
  state.imageB64 = dataUrl.split(',')[1];
  $('framePreview').src = dataUrl;
  $('framePreview').hidden = false;
  $('camPlaceholder').hidden = true;
  $('btnClearFrame').textContent = '清空画面';
}

function clearFrame() {
  state.imageB64 = null;
  $('framePreview').hidden = true;
  $('camPlaceholder').hidden = false;
  $('personState').textContent = '—';
  $('visibleChips').innerHTML = '';
  $('btnClearFrame').textContent = '清空画面';
  if (state.stream) {
    state.stream.getTracks().forEach(t => t.stop());
    state.stream = null;
    $('video').hidden = true;
    $('btnCamera').textContent = '📷 开启摄像头';
    $('btnCapture').disabled = true;
  }
}

/* ---------- 语音输入（浏览器 ASR） ---------- */
function bindAsr() {
  $('btnAsr').addEventListener('click', () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      alert('当前浏览器不支持语音识别，请使用 Chrome/Edge。');
      return;
    }
    const rec = new SR();
    rec.lang = 'zh-CN';
    rec.interimResults = true;
    rec.onresult = e => {
      let text = '';
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      $('speech').value = text;
    };
    rec.onend = () => { $('btnAsr').textContent = '🎤 语音输入'; $('btnAsr').classList.remove('active'); };
    rec.onerror = () => { $('btnAsr').textContent = '🎤 语音输入'; $('btnAsr').classList.remove('active'); };
    $('btnAsr').textContent = '🎤 正在听…';
    $('btnAsr').classList.add('active');
    rec.start();
  });
  $('btnClearSpeech').addEventListener('click', () => { $('speech').value = ''; });
}

/* ---------- 快捷场景 / 指令 ---------- */
function bindQuickChips() {
  document.querySelectorAll('#sceneChips button').forEach(btn => {
    btn.addEventListener('click', () => {
      $('sceneText').value = btn.dataset.scene || '';
      if (btn.dataset.speech) $('speech').value = btn.dataset.speech;
    });
  });
  document.querySelectorAll('#speechChips button').forEach(btn => {
    btn.addEventListener('click', () => { $('speech').value = btn.dataset.speech || ''; });
  });
}

/* ---------- 配置面板 ---------- */
function renderConfigForm(cfg) {
  const llm = cfg.llm || {};
  const agent = cfg.agent || {};
  const weather = cfg.weather || {};
  $('cfgElder').value = agent.elder_name || '王奶奶';
  $('cfgAgentName').value = agent.agent_name || '暖眸';
  $('cfgApiKey').value = '';
  $('cfgApiKey').placeholder = llm.has_key ? '已配置（留空保持不变，输入新值可覆盖）' : 'sk-...';
  $('cfgBaseUrl').value = llm.base_url || 'https://api.openai.com/v1';
  $('cfgModel').value = llm.model || 'gpt-4o-mini';
  $('cfgTemperature').value = llm.temperature ?? 0.3;
  $('cfgVision').checked = llm.vision_supported !== false;
  const meds = (cfg.medication_plan || []).map(m => `${m.name} ${m.time} ${m.dose || ''}`.trim()).join('\n');
  $('cfgMeds').value = meds;
  $('cfgCity').value = weather.city || '广州';
  $('cfgWeatherKey').placeholder = weather.has_key ? '已配置（留空保持不变）' : '可选';
  $('cfgWebhook').value = cfg.family_webhook === '已配置' ? '已配置（留空清除）' : (cfg.family_webhook || '');
}

function bindConfigPanel() {
  $('btnSaveConfig').addEventListener('click', async () => {
    const meds = [];
    $('cfgMeds').value.split('\n').forEach(line => {
      const parts = line.trim().split(/\s+/);
      if (parts.length >= 2) {
        meds.push({ name: parts[0], time: parts[1], dose: parts.slice(2).join(' ') || '' });
      }
    });
    const body = {
      agent: { elder_name: $('cfgElder').value, agent_name: $('cfgAgentName').value },
      llm: {
        api_key: $('cfgApiKey').value,
        base_url: $('cfgBaseUrl').value,
        model: $('cfgModel').value,
        vision_supported: $('cfgVision').checked,
        temperature: parseFloat($('cfgTemperature').value) || 0.3,
      },
      medication_plan: meds,
      weather: { city: $('cfgCity').value, api_key: $('cfgWeatherKey').value },
      family_webhook: $('cfgWebhook').value.startsWith('已配置') ? undefined : $('cfgWebhook').value,
    };
    const r = await api('/api/config', { method: 'POST', body });
    $('configResult').textContent = r.ok ? `✓ ${r.message}` : `✗ ${r.message || '保存失败'}`;
    await refreshHealth();
    await refreshState();
  });

  $('btnTestConfig').addEventListener('click', async () => {
    $('configResult').textContent = '正在测试连接…';
    const r = await api('/api/test', { method: 'POST', body: {} });
    $('configResult').textContent = r.ok ? `✓ ${r.message}` : `✗ ${r.message || '连接失败'}`;
  });
}

document.addEventListener('DOMContentLoaded', init);
