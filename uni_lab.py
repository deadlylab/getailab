#!/usr/bin/env python3
"""
uni_lab.py — compatibility entry point (Universal Lab Forge)

The original uni_lab.py lived at development/dcai/labs/uni_lab.py and scaffolded
a *separate mini-repo* (duplicate base_agent, app_lab, run_canvas.py, etc.).

GetAiLab Lab Forge merged that wizard into GetAiLab's engine:
  scripts/create_lab.py  +  data/labs/<id>/ vault  +  scientists/forges/<id>/

This shim forwards to the merged forge so old habits still work:

    python3 uni_lab.py              # interactive wizard
    python3 uni_lab.py --list-labs

Canvas profile (--profile canvas) = thin personas, uni_lab-style fast squad.
Research profile (default)        = full vault, books, tickets, library.

See docs/LAB_BUILDER.md
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_FORGE = _ROOT / "scripts" / "create_lab.py"

if __name__ == "__main__":
    if not _FORGE.is_file():
        print(f"Lab Forge not found: {_FORGE}")
        sys.exit(1)
    sys.argv[0] = str(_FORGE)
    runpy.run_path(str(_FORGE), run_name="__main__")