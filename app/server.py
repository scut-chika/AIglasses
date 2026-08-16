# -*- coding: utf-8 -*-
"""暖眸 真实 Agent 服务端（Python 标准库，零第三方依赖）。

启动：py server.py [--port 8000] [--host 127.0.0.1]
然后浏览器打开 http://127.0.0.1:8000 ，在「配置」页填写 AI 服务 Key 即可使用。
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.join(ROOT, "web")
DATA_DIR = os.path.join(ROOT, "data")

for _ext, _type in [
    (".js", "text/javascript; charset=utf-8"),
    (".mjs", "text/javascript; charset=utf-8"),
    (".css", "text/css; charset=utf-8"),
    (".html", "text/html; charset=utf-8"),
    (".json", "application/json; charset=utf-8"),
    (".svg", "image/svg+xml"),
]:
    mimetypes.add_type(_type, _ext)

from agent.agent import WarmEyeAgent          # noqa: E402
from agent.config import load_config, save_config, public_config  # noqa: E402
from agent.llm import LLMError, chat          # noqa: E402
from agent.memory import MemoryStore          # noqa: E402


class App:
    def __init__(self):
        self.config = load_config()
        self.memory = MemoryStore(os.path.join(DATA_DIR, "memory.json"))
        self.agent = WarmEyeAgent(self.config, self.memory)


APP = App()


class Handler(BaseHTTPRequestHandler):
    server_version = "NuanMou/1.0"

    def log_message(self, fmt, *args):  # 安静模式
        pass

    # ---------- 基础响应 ----------
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _file(self, full: str) -> None:
        full = os.path.abspath(full)
        if not full.startswith(os.path.abspath(WEB_ROOT) + os.sep) and full != os.path.abspath(WEB_ROOT):
            self._send(403, b"forbidden", "text/plain; charset=utf-8")
            return
        if not os.path.isfile(full):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {}

    # ---------- GET ----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._file(os.path.join(WEB_ROOT, "index.html"))
            return
        if path == "/api/health":
            self._json(200, self._health())
            return
        if path == "/api/state":
            self._json(200, {"ok": True, **APP.agent.state()})
            return
        self._file(os.path.join(WEB_ROOT, path.lstrip("/")))

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        if path == "/api/run":
            self._json(200, APP.agent.run_step(body))
        elif path == "/api/config":
            self._save_config(body)
        elif path == "/api/test":
            self._test_llm(body)
        elif path == "/api/reset":
            APP.agent.reset()
            self._json(200, {"ok": True, "message": "会话已重置", "state": APP.agent.state()})
        elif path == "/api/memory/delete":
            self._delete_memory(body)
        else:
            self._json(404, {"ok": False, "message": "接口不存在"})

    # ---------- 业务 ----------
    def _health(self) -> dict:
        cfg = APP.config
        llm = cfg.get("llm", {})
        return {
            "ok": bool(llm.get("api_key")),
            "has_key": bool(llm.get("api_key")),
            "model": llm.get("model", ""),
            "base_url": llm.get("base_url", ""),
            "elder_name": cfg.get("agent", {}).get("elder_name", "王奶奶"),
            "message": "已配置" if llm.get("api_key") else "未配置 AI 服务 Key，请打开「配置」页填写",
        }

    def _save_config(self, body: dict) -> None:
        if not isinstance(body, dict):
            self._json(400, {"ok": False, "message": "配置格式错误"})
            return
        cfg = APP.config
        if "llm" in body and isinstance(body["llm"], dict):
            llm = body["llm"]
            if "api_key" in llm:
                if llm["api_key"]:
                    cfg["llm"]["api_key"] = llm["api_key"].strip()
                # 空字符串 = 清除
                elif not llm["api_key"]:
                    cfg["llm"]["api_key"] = ""
            for key in ("base_url", "model", "vision_supported", "temperature"):
                if key in llm:
                    cfg["llm"][key] = llm[key]
        if "agent" in body and isinstance(body["agent"], dict):
            for key in ("elder_name", "agent_name", "timezone"):
                if key in body["agent"] and body["agent"][key]:
                    cfg["agent"][key] = body["agent"][key].strip()
        if "medication_plan" in body and isinstance(body["medication_plan"], list):
            plan = []
            for m in body["medication_plan"]:
                if isinstance(m, dict) and m.get("name") and m.get("time"):
                    plan.append({
                        "name": m["name"].strip(),
                        "time": m["time"].strip(),
                        "dose": (m.get("dose") or "").strip(),
                    })
            if plan:
                cfg["medication_plan"] = plan
        if "weather" in body and isinstance(body["weather"], dict):
            if "api_key" in body["weather"]:
                cfg["weather"]["api_key"] = body["weather"]["api_key"].strip()
            if "city" in body["weather"] and body["weather"]["city"]:
                cfg["weather"]["city"] = body["weather"]["city"].strip()
        if "family_webhook" in body:
            cfg["family_webhook"] = (body["family_webhook"] or "").strip()
        try:
            save_config(cfg)
        except Exception as e:
            self._json(500, {"ok": False, "message": f"配置保存失败：{e}"})
            return
        APP.agent.config = cfg
        self._json(200, {"ok": True, "message": "配置已保存", "config": public_config(cfg)})

    def _test_llm(self, body: dict) -> None:
        cfg = APP.config
        if not cfg["llm"].get("api_key"):
            self._json(200, {"ok": False, "message": "未配置 API Key"})
            return
        messages = [{"role": "user", "content": "请只回复两个字：正常"}]
        try:
            reply = chat(cfg["llm"], messages, temperature=0, max_tokens=20)
            self._json(200, {"ok": True, "message": f"连接成功，模型回复：{reply[:60]}"})
        except LLMError as e:
            self._json(200, {"ok": False, "message": f"连接失败：{e}"})

    def _delete_memory(self, body: dict) -> None:
        obj = (body.get("object") or "").strip()
        if body.get("all"):
            APP.memory.clear()
            self._json(200, {"ok": True, "message": "全部记忆已清除", "state": APP.agent.state()})
            return
        if not obj:
            self._json(400, {"ok": False, "message": "缺少 object 参数"})
            return
        removed = APP.memory.delete_item(obj)
        self._json(200, {"ok": True, "message": f"已删除「{obj}」" if removed else "未找到该记忆",
                         "state": APP.agent.state()})


def main() -> None:
    parser = argparse.ArgumentParser(description="暖眸 · 居家养老 AI 眼镜智能体（真实 Agent 服务）")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认仅本机）")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 60)
    print(f" 暖眸 · 居家养老 AI 眼镜智能体（真实 Agent 版）")
    print(f" 服务地址：http://{args.host}:{args.port}")
    print(f" 提示：首次使用请在页面「配置」页填写 AI 服务 API Key")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
