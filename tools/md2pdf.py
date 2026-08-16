# -*- coding: utf-8 -*-
"""Markdown → PDF（python-markdown + Chrome headless 打印）。

用法：py tools/md2pdf.py
输出：docs/pdf/*.pdf（与 docs/*.md 同名）
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
OUT_DIR = os.path.join(DOCS, "pdf")
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  color: #1c2333; font-size: 11pt; line-height: 1.75;
}
h1 { color: #1a2f8f; border-bottom: 3px solid #6d8dff; padding-bottom: 8px; font-size: 21pt; }
h2 {
  color: #23307a; border-left: 6px solid #6d8dff; padding-left: 10px;
  margin-top: 24px; font-size: 15pt;
}
h3 { color: #23307a; font-size: 13pt; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10pt; }
th, td { border: 1px solid #c9d2e8; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #eef2ff; }
blockquote {
  border-left: 4px solid #ffb454; background: #fff8ec;
  margin: 10px 0; padding: 8px 14px; color: #6b4d1f;
}
code {
  background: #eef1f8; border-radius: 4px; padding: 1px 5px;
  font-family: Consolas, monospace; font-size: 9.5pt;
}
pre {
  background: #0d1020; color: #e8eaf6; border-radius: 8px;
  padding: 12px 14px; overflow-x: auto; page-break-inside: avoid;
}
pre code { background: none; color: inherit; padding: 0; }
a { color: #2a4bd7; text-decoration: none; }
li { margin: 3px 0; }
"""


def find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    sys.exit("未找到 Chrome/Edge，无法生成 PDF")


def md_to_pdf(md_path: str, pdf_path: str, chrome: str) -> None:
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    html_body = markdown.markdown(
        md_text, extensions=["tables", "fenced_code", "sane_lists", "nl2br"]
    )
    html = (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{html_body}</body></html>"
    )
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nuanmou_pdf_") as td:
        html_path = os.path.join(td, "doc.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        profile = os.path.join(td, "profile")
        url = "file:///" + html_path.replace("\\", "/")
        cmd = [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--no-first-run",
            "--password-store=basic",
            "--disable-extensions",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={pdf_path}",
            "--no-pdf-header-footer",
            url,
        ]
        try:
            subprocess.run(cmd, check=True, timeout=120)
        except subprocess.CalledProcessError:
            # 兼容旧版 Chrome：去掉 no-pdf-header-footer 再试一次
            cmd.remove("--no-pdf-header-footer")
            subprocess.run(cmd, check=True, timeout=120)


def main() -> None:
    chrome = find_chrome()
    tasks = [
        "产品简介",
        "暖眸-产品设计方案",
        "功能闭环演示",
    ]
    for name in tasks:
        md_path = os.path.join(DOCS, name + ".md")
        pdf_path = os.path.join(OUT_DIR, name + ".pdf")
        md_to_pdf(md_path, pdf_path, chrome)
        size = os.path.getsize(pdf_path)
        print(f"OK  {name}.pdf  ({size} bytes)")


if __name__ == "__main__":
    main()
