# 暖眸 · 真实 Agent 版（可用版）

> 与 `web/`、`demo/` 的规则版概念演示不同，**本目录是真实可用的 Agent 应用**：
> 接入你自己的 AI 服务 Key，即可用摄像头 / 照片 / 语音真实运行三个闭环，
> Agent 的感知、理解、主动触发、决策、工具调用、记忆持久化全部真实执行。

> 关于产品形态：网页端为**初赛演示形态**（便于评审打开浏览器复现）；正式产品为
> 「AI 眼镜 + 老人端 App + 子女端 App」，双端功能与界面构想见
> [docs/暖眸-产品设计方案.md](../docs/暖眸-产品设计方案.md) 第 9 章。

## 快速开始（三步）

要求：Python 3.9+，无需安装任何第三方库（仅用标准库）。

```powershell
cd app
py server.py
```

浏览器打开 http://127.0.0.1:8000 → 切到「配置」页 → 填入你的 AI 服务 Key → 保存 → 测试连接 → 回「智能体操作」页使用。

## 支持的服务商（OpenAI 兼容接口）

| 服务商 | base_url | 模型示例 | 视觉 |
| --- | --- | --- | --- |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini / gpt-4o | ✅ |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat | ❌ |
| Moonshot（月之暗面） | https://api.moonshot.cn/v1 | moonshot-v1-8k | ❌ |
| 通义千问（兼容模式） | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus / qwen-vl-plus | ✅ |
| 本地 Ollama | http://127.0.0.1:11434/v1 | qwen2.5 / llava | 视模型 |

模型支持图片时，在配置页勾选「模型支持图片理解」，即可用摄像头拍照做第一视角视觉识别；
不支持时关闭该选项，用手动场景描述代替。

## 使用方式

* **第一视角**：开启摄像头拍照，或上传图片，Agent 调用视觉模型识别场景/人物状态/可见物体
* **语音输入**：浏览器内置语音识别（Chrome/Edge），点「🎤 语音输入」说即可；也可以直接打字
* **主动触发**：语音留空时，Agent 按低打扰原则自行判断是否主动开口；勾选「模拟 08:00 用药时间」可随时演示时间触发
* **真实工具**：记忆检索/更新、用药计划、天气（可选 Key）、家人通知（可选 Webhook）都会真实执行并在决策轨迹中展示
* **记忆持久化**：物品位置、健康日志自动保存到 `app/data/memory.json`，刷新不丢；可点击记忆项删除（隐私）
* **语音反馈**：浏览器朗读 Agent 回复

## 目录结构

```text
app/
  server.py              # HTTP 服务（零依赖），托管前端 + 提供接口
  config.example.json    # 配置模板
  config.json            # 你的实际配置（已 gitignore，不会上传）
  data/memory.json       # 运行产生的长期记忆（已 gitignore）
  agent/
    agent.py             # Agent 主循环：感知→理解→触发→决策→工具→反馈→记忆
    llm.py               # OpenAI 兼容客户端（支持视觉 + JSON 输出）
    memory.py            # 长期记忆（本地 JSON）
    tools.py             # 工具层：记忆/用药/天气/家人通知
    config.py            # 配置读写
  web/                   # 可视化操作前端（摄像头/语音/配置/决策轨迹）
  tests/test_e2e.py      # 端到端测试（Mock LLM 验证全链路）
```

## 测试

```powershell
cd app
py tests/test_e2e.py
```

用 Mock OpenAI 兼容服务验证：视觉感知 → 决策 → 工具 → 记忆全链路，无需真实 Key。

## 安全说明

* API Key 只保存在本机 `app/config.json`，不会上传，也不会进入 Git 提交
* 如需手动编辑 `config.json`，请务必使用 **UTF-8（无 BOM）编码**保存，否则中文会乱码
* 默认只监听 `127.0.0.1`（本机）；如需局域网访问，自行加 `--host 0.0.0.0` 并注意安全
* 家人通知 Webhook 为通用 POST（钉钉/企业微信机器人格式），未配置时仅本地记录
