#!/usr/bin/env python3
"""
SAURON VISION — Research scraper for GetAiLab.
Uses the configured LLM provider (Ollama, OpenAI, Google, etc.) via llm.adapter.

Usage:
    python3 sauron_vision.py --url "https://arxiv.org/abs/2301.12345" "Extract key formulas"
    python3 sauron_vision.py --path "./lab/artifacts/loop_8/field_plot.png" "Describe the symmetry"
"""

import argparse
import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from markdownify import markdownify as md
from playwright.async_api import async_playwright

from llm.adapter import create_default_adapter
from llm.sauron_core import extract_with_adapter

load_dotenv()

BASE_DIR = Path("data")
INBOX_DIR = BASE_DIR / "inbox"
RECORDINGS_DIR = BASE_DIR / "recordings"
CODE_DIR = BASE_DIR / "code"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
DB_PATH = BASE_DIR / "sauron_data.db"

for d in [INBOX_DIR, RECORDINGS_DIR, CODE_DIR, SCREENSHOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS extractions (
        id INTEGER PRIMARY KEY,
        scraped_at TEXT,
        query TEXT,
        topic TEXT,
        source_url TEXT,
        raw_json TEXT,
        raw_markdown TEXT,
        type TEXT,
        confidence REAL
    )""")
    conn.commit()
    conn.close()


init_db()


class CaptureEngine:
    async def capture_url(self, url: str, record_media: bool = False) -> Tuple[Optional[Path], Optional[str], Optional[bytes]]:
        print(f"  Sauron observing: {url}")
        try:
            async with async_playwright() as p:
                context_kwargs = {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "viewport": {"width": 1920, "height": 1080},
                }
                if record_media:
                    context_kwargs["record_video_dir"] = str(RECORDINGS_DIR)

                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=60000)

                content = await page.content()
                soup = BeautifulSoup(content, 'lxml')
                for tag in soup(['script', 'style', 'nav', 'footer']):
                    tag.decompose()
                markdown_text = md(str(soup))

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                shot_path = SCREENSHOTS_DIR / f"sauron_{ts}.png"
                screenshot_bytes = await page.screenshot(path=str(shot_path), full_page=True)
                await browser.close()
                return shot_path, markdown_text, screenshot_bytes
        except Exception as e:
            print(f"  Capture error: {e}")
            return None, None, None


def stack_results(data: dict, query: str, url: str = "local", markdown: str = ""):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    inbox_path = INBOX_DIR / f"{ts}_extraction.json"
    inbox_path.write_text(json.dumps(data, indent=2))

    for i, snip in enumerate(data.get("code_snippets", [])):
        ext = "py" if "python" in snip.get("language", "").lower() else "txt"
        (CODE_DIR / f"{ts}_snippet_{i}.{ext}").write_text(snip.get("code", ""))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""INSERT INTO extractions
        (scraped_at, query, topic, source_url, raw_json, raw_markdown, type, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
        datetime.now().isoformat(), query, data.get("topic", "Unknown"),
        url, json.dumps(data), markdown, data.get("type", "general"),
        data.get("confidence", 0.5),
    ))
    conn.commit()
    conn.close()
    print(f"  Data stacked. ID: {ts}")


async def run_sauron(query: str, url: Optional[str] = None, path: Optional[str] = None, record: bool = False):
    adapter = create_default_adapter()
    info = adapter.get_info()
    print(f"  LLM: {info.get('configured_provider')} | vision={info.get('supports_vision')}")

    image_bytes = None
    markdown_context = ""

    if path:
        img_path = Path(path)
        if not img_path.exists():
            print(f"  Path not found: {path}")
            return None
        image_bytes = img_path.read_bytes()
    elif url:
        _, markdown_context, image_bytes = await CaptureEngine().capture_url(url, record)
        if not markdown_context and not image_bytes:
            return None
    else:
        print("  Provide --url or --path.")
        return None

    print("  Analyzing...")
    data = extract_with_adapter(adapter, query, image_bytes=image_bytes, text_context=markdown_context or None)
    if data:
        source = url or str(path) or "local"
        stack_results(data, query, source, markdown_context or "")
        return data

    print("  Extraction failed — check LLM provider and logs.")
    return None


def main():
    parser = argparse.ArgumentParser(description="Sauron Vision — provider-agnostic research extraction")
    parser.add_argument("query", help="What to find or analyze")
    parser.add_argument("--url", help="Web URL to scrape")
    parser.add_argument("--path", help="Local image path to analyze")
    parser.add_argument("--record-media", action="store_true", help="Record video (URLs only)")
    args = parser.parse_args()
    asyncio.run(run_sauron(args.query, args.url, args.path, args.record_media))


if __name__ == "__main__":
    main()