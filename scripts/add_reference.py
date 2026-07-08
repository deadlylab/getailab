#!/usr/bin/env python3
"""
Add reference material to a scientist's research book (beef up brains).

Examples:
  python3 scripts/add_reference.py albert --file paper.md --title "Riemannian Agents"
  python3 scripts/add_reference.py albert --url https://example.com/article --title "Background"
  python3 scripts/add_reference.py albert --text "Key insight: agents follow geodesics on curved manifolds."
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from getailab.library import add_scientist_reference, get_scientist_references
from personas.loader import get_squad_names


def main() -> int:
    scientists = [n for n in get_squad_names() if n != "oracle"]
    parser = argparse.ArgumentParser(description="Beef up a scientist's research book with reference material.")
    parser.add_argument("scientist", choices=scientists, help="Squad member to enrich")
    parser.add_argument("--title", default="", help="Reference title")
    parser.add_argument("--text", default="", help="Inline note content")
    parser.add_argument("--file", dest="file_path", help="Path to a text/markdown file")
    parser.add_argument("--url", default="", help="URL to fetch and archive")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--list", action="store_true", help="List existing references instead of adding")
    parser.add_argument("--query", default="", help="Search when using --list")
    args = parser.parse_args()

    if args.list:
        result = get_scientist_references(args.scientist, query=args.query)
        print(json.dumps(result, indent=2))
        return 0

    content = args.text or ""
    if args.file_path:
        with open(args.file_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] or None
    source_label = "file" if args.file_path else "user"

    result = add_scientist_reference(
        args.scientist,
        title=args.title,
        content=content,
        url=args.url,
        tags=tags,
        source_label=source_label,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())