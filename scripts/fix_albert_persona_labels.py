#!/usr/bin/env python3
"""Patch Albert's book pages: legacy 'Quantum Physicist' → 'Theoretical Physicist'."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from personas.loader import sanitize_albert_persona_labels

BOOK_PAGES = ROOT / "data" / "labs" / "chimera" / "scientists" / "albert" / "book" / "pages"


def main():
    if not BOOK_PAGES.is_dir():
        print(f"❌ Missing: {BOOK_PAGES}")
        sys.exit(1)

    changed = 0
    scanned = 0
    for path in sorted(BOOK_PAGES.glob("*.json")):
        scanned += 1
        data = json.loads(path.read_text(encoding="utf-8"))
        content = data.get("content", "")
        if not content:
            continue
        fixed = sanitize_albert_persona_labels(content)
        if fixed == content:
            continue
        data["content"] = fixed
        data["content_checksum"] = hashlib.sha256(fixed.encode()).hexdigest()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        (BOOK_PAGES / f"{path.stem}.sha256").write_text(data["content_checksum"])
        changed += 1
        print(f"  ✅ {path.name}")

    print(f"\nDone — {changed}/{scanned} Albert book pages updated.")


if __name__ == "__main__":
    main()