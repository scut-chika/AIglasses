# -*- coding: utf-8 -*-
"""OpenAI 兼容 LLM 客户端（仅用标准库 urllib），支持视觉与 JSON 输出。

兼容：OpenAI / DeepSeek / Moonshot / 通义千问（DashScope 兼容模式）/
本地 Ollama（base_url 填 http://127.0.0.1:11434/v1）等。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Dict, List


class LLMError(Exception):
    pass


def _post(cfg: Dict, payload: Dict, timeout: int = 120) -> Dict:
    api_key = cfg.get("api_key", "")
    base_url = (cfg.get("base_url") or "").rstrip("/")
    if not base_url:
        raise LLMError("未配置 API 地址 base_url")
    url = base_url + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:600]
        raise LLMError(f"HTTP {e.code}：{body}")
    except Exception as e:
        raise LLMError(f"网络错误：{e}")


def _content(data: Dict) -> str:
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise LLMError("模型返回格式异常：" + json.dumps(data, ensure_ascii=False)[:300])


def _base_payload(cfg: Dict, messages: List[Dict], temperature: float, max_tokens: int) -> Dict:
    return {
        "model": cfg.get("model", ""),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def chat_json(cfg: Dict, messages: List[Dict], temperature: float = 0.3, max_tokens: int = 2000) -> Dict:
    payload = _base_payload(cfg, messages, temperature, max_tokens)
    payload["response_format"] = {"type": "json_object"}
    try:
        return extract_json(_content(_post(cfg, payload)))
    except LLMError:
        # 部分服务商不支持 response_format，重试一次（不带该字段）
        payload.pop("response_format", None)
        return extract_json(_content(_post(cfg, payload)))


def chat(cfg: Dict, messages: List[Dict], temperature: float = 0.3, max_tokens: int = 500) -> str:
    payload = _base_payload(cfg, messages, temperature, max_tokens)
    return _content(_post(cfg, payload))


def vision(cfg: Dict, image_b64: str, prompt: str, max_tokens: int = 600) -> Dict:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                },
            ],
        }
    ]
    payload = _base_payload(cfg, messages, 0.1, max_tokens)
    payload["response_format"] = {"type": "json_object"}
    try:
        return extract_json(_content(_post(cfg, payload)))
    except LLMError:
        payload.pop("response_format", None)
        return extract_json(_content(_post(cfg, payload)))


def extract_json(text: str) -> Dict:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"```\s*$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise LLMError("模型未返回合法 JSON：" + t[:200])
