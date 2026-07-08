"""
Merkle tree integrity — adapted from Old Mate (old-mate-og/foundations/merkle.py).

Walks a directory, hashes every file (SHA-256), builds a tree, detects changes.
Stdlib only. Used for artifact vault snapshots and change detection.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any, List, Optional


def _merkle_dir(lab_id: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    path = root / "data" / "labs" / lab_id / "merkle"
    path.mkdir(parents=True, exist_ok=True)
    return path


def hash_file(filepath: str | Path) -> str:
    """Hash a single file using SHA-256."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return "ERROR_UNREADABLE"


def hash_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def build_tree(root_path: str | Path, ignore_patterns: Optional[List[str]] = None) -> dict:
    """Walk a directory and build a Merkle tree."""
    if ignore_patterns is None:
        ignore_patterns = [
            "__pycache__", ".pyc", "node_modules", ".git", "venv", ".venv",
            ".cache", ".npm", ".sha256", "/merkle/",
        ]

    root_path = os.path.abspath(str(root_path))
    total_files = 0
    total_size = 0

    def should_ignore(path: str) -> bool:
        return any(pattern in path for pattern in ignore_patterns)

    def walk_dir(dirpath: str) -> dict:
        nonlocal total_files, total_size
        children = {}
        child_hashes = []

        try:
            entries = sorted(os.listdir(dirpath))
        except PermissionError:
            return {"hash": "ERROR_PERMISSION", "type": "directory", "children": {}}

        for entry in entries:
            fullpath = os.path.join(dirpath, entry)
            if should_ignore(fullpath):
                continue

            if os.path.isfile(fullpath):
                file_hash = hash_file(fullpath)
                file_size = os.path.getsize(fullpath) if os.path.exists(fullpath) else 0
                children[entry] = {"hash": file_hash, "type": "file", "size": file_size}
                child_hashes.append(f"{entry}:{file_hash}")
                total_files += 1
                total_size += file_size
            elif os.path.isdir(fullpath):
                subtree = walk_dir(fullpath)
                children[entry] = subtree
                child_hashes.append(f"{entry}:{subtree['hash']}")

        dir_hash = hash_string("\n".join(child_hashes)) if child_hashes else hash_string("EMPTY_DIR")
        return {"hash": dir_hash, "type": "directory", "children": children}

    tree = walk_dir(root_path)
    tree["path"] = root_path
    tree["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tree["total_files"] = total_files
    tree["total_size"] = total_size
    return tree


def save_tree(tree: dict, name: str, lab_id: str = "chimera") -> str:
    filepath = _merkle_dir(lab_id) / f"{name}.json"
    filepath.write_text(json.dumps(tree, indent=2))
    return str(filepath)


def load_tree(name: str, lab_id: str = "chimera") -> Optional[dict]:
    filepath = _merkle_dir(lab_id) / f"{name}.json"
    if not filepath.exists():
        return None
    return json.loads(filepath.read_text())


def compare_trees(old: dict, new: dict, path: str = "") -> List[dict]:
    """Compare two Merkle trees. Returns list of added/removed/modified paths."""
    changes: List[dict] = []

    if hmac.compare_digest(old.get("hash", ""), new.get("hash", "")):
        return changes

    old_children = old.get("children", {})
    new_children = new.get("children", {})

    for name in new_children:
        child_path = f"{path}/{name}" if path else name
        if name not in old_children:
            kind = (
                "directory" if new_children[name]["type"] == "directory"
                else f"file ({new_children[name].get('size', 0)} bytes)"
            )
            changes.append({"type": "added", "path": child_path, "detail": kind})
        elif not hmac.compare_digest(old_children[name]["hash"], new_children[name]["hash"]):
            if new_children[name]["type"] == "file":
                changes.append({
                    "type": "modified",
                    "path": child_path,
                    "detail": (
                        f"hash changed: {old_children[name]['hash'][:12]}... "
                        f"→ {new_children[name]['hash'][:12]}..."
                    ),
                })
            else:
                changes.extend(compare_trees(old_children[name], new_children[name], child_path))

    for name in old_children:
        if name not in new_children:
            child_path = f"{path}/{name}" if path else name
            changes.append({
                "type": "removed",
                "path": child_path,
                "detail": (
                    "directory" if old_children[name]["type"] == "directory" else "file"
                ) + " deleted",
            })

    return changes


def find_duplicates(tree: dict) -> List[dict]:
    """
    Find files with identical content hashes.

    Returns groups sorted by wasted bytes (descending):
    [{"hash": "...", "count": 3, "wasted_bytes": 12345, "files": [...]}, ...]
    """
    hash_to_files: dict[str, List[dict]] = {}

    def walk(node: dict, path: str) -> None:
        for name, child in node.get("children", {}).items():
            child_path = f"{path}/{name}" if path else name
            if child["type"] == "file" and child["hash"] != "ERROR_UNREADABLE":
                hash_to_files.setdefault(child["hash"], []).append({
                    "path": child_path,
                    "size": child.get("size", 0),
                })
            elif child["type"] == "directory":
                walk(child, child_path)

    walk(tree, tree.get("path", ""))

    duplicates = []
    for file_hash, files in hash_to_files.items():
        if len(files) > 1:
            total_waste = sum(f["size"] for f in files[1:])
            duplicates.append({
                "hash": file_hash,
                "count": len(files),
                "wasted_bytes": total_waste,
                "files": files,
            })

    return sorted(duplicates, key=lambda d: d["wasted_bytes"], reverse=True)


def tree_summary(tree: dict) -> dict[str, Any]:
    """Return a compact summary dict for APIs and logging."""
    return {
        "path": tree.get("path"),
        "root_hash": tree.get("hash"),
        "total_files": tree.get("total_files", 0),
        "total_size": tree.get("total_size", 0),
        "timestamp": tree.get("timestamp"),
    }


def print_tree_summary(tree: dict) -> None:
    """Pretty-print a one-line summary of a tree."""
    print(f"Path:        {tree.get('path', '?')}")
    print(f"Root hash:   {tree.get('hash', '?')[:16]}...")
    print(f"Total files: {tree.get('total_files', '?')}")
    print(f"Total size:  {tree.get('total_size', 0) / 1048576:.1f} MB")
    print(f"Scanned:     {tree.get('timestamp', '?')}")


def scan_directory(
    directory: str | Path,
    name: str,
    *,
    lab_id: str = "chimera",
    ignore_patterns: Optional[List[str]] = None,
    rotate_previous: bool = True,
) -> dict[str, Any]:
    """
    Build a Merkle tree over *directory*, save it as *name*, and diff against the
    previous snapshot (rotated to ``{name}_previous`` when *rotate_previous* is True).

    Returns a summary dict suitable for APIs, tickets, and loop provenance.
    """
    directory = os.path.abspath(str(directory))
    if not os.path.isdir(directory):
        return {"error": f"not a directory: {directory}"}

    old_tree = load_tree(name, lab_id=lab_id)
    tree = build_tree(directory, ignore_patterns=ignore_patterns)

    if rotate_previous and old_tree is not None:
        save_tree(old_tree, f"{name}_previous", lab_id=lab_id)

    tree_path = save_tree(tree, name, lab_id=lab_id)
    changes = compare_trees(old_tree, tree) if old_tree else []

    return {
        "name": name,
        "lab_id": lab_id,
        "directory": directory,
        "tree_path": tree_path,
        "root_hash": tree["hash"],
        "total_files": tree["total_files"],
        "total_size": tree["total_size"],
        "timestamp": tree["timestamp"],
        "had_previous": old_tree is not None,
        "changes_since_previous": len(changes),
        "changes": changes,
    }


def compare_saved_trees(
    name: str,
    *,
    lab_id: str = "chimera",
    use_previous: bool = True,
) -> dict[str, Any]:
    """Compare current saved tree against its ``_previous`` snapshot (or an explicit baseline)."""
    current = load_tree(name, lab_id=lab_id)
    if not current:
        return {"error": f"no saved tree: {name}"}

    baseline_name = f"{name}_previous" if use_previous else name
    baseline = load_tree(baseline_name, lab_id=lab_id) if use_previous else None
    if use_previous and not baseline:
        return {"error": f"no previous snapshot: {baseline_name}"}

    changes = compare_trees(baseline, current) if baseline else []
    return {
        "name": name,
        "lab_id": lab_id,
        "root_hash": current["hash"],
        "baseline": baseline_name if use_previous else None,
        "changes": changes,
        "change_count": len(changes),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("GetAiLab Merkle Tool")
        print("Usage:")
        print(f"  python3 -m getailab.integrity.merkle scan <dir> <name> [--lab chimera]")
        print(f"  python3 -m getailab.integrity.merkle compare <name> [--lab chimera]")
        print(f"  python3 -m getailab.integrity.merkle duplicates <name> [--lab chimera]")
        print(f"  python3 -m getailab.integrity.merkle show <name> [--lab chimera]")
        sys.exit(0)

    cmd = sys.argv[1]
    lab_id = "chimera"
    if "--lab" in sys.argv:
        idx = sys.argv.index("--lab")
        if idx + 1 < len(sys.argv):
            lab_id = sys.argv[idx + 1]

    if cmd == "scan":
        if len(sys.argv) < 4:
            print("Usage: scan <directory> <name> [--lab chimera]")
            sys.exit(1)
        directory, name = sys.argv[2], sys.argv[3]
        print(f"Scanning {directory}...")
        result = scan_directory(directory, name, lab_id=lab_id)
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        print_tree_summary(load_tree(name, lab_id=lab_id) or {})
        print(f"Saved: {result['tree_path']}")
        if result["had_previous"]:
            print(f"Changes since last: {result['changes_since_previous']}")
            for change in result["changes"][:10]:
                print(f"  {change['type']}: {change['path']} — {change['detail']}")

    elif cmd == "compare":
        if len(sys.argv) < 3:
            print("Usage: compare <name> [--lab chimera]")
            sys.exit(1)
        name = sys.argv[2]
        result = compare_saved_trees(name, lab_id=lab_id)
        if "error" in result:
            print(result["error"])
            sys.exit(1)
        print(f"Changes: {result['change_count']}")
        for change in result["changes"]:
            print(f"  [{change['type']}] {change['path']} — {change['detail']}")

    elif cmd == "duplicates":
        if len(sys.argv) < 3:
            print("Usage: duplicates <name> [--lab chimera]")
            sys.exit(1)
        name = sys.argv[2]
        tree = load_tree(name, lab_id=lab_id)
        if not tree:
            print("No tree. Run scan first.")
            sys.exit(1)
        dups = find_duplicates(tree)
        waste = sum(d["wasted_bytes"] for d in dups)
        print(f"{len(dups)} duplicate groups, {waste / 1024 / 1024:.1f} MB wasted")
        for dup in dups[:5]:
            print(f"  {dup['hash'][:12]}... ({dup['count']} copies)")

    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: show <name> [--lab chimera]")
            sys.exit(1)
        name = sys.argv[2]
        tree = load_tree(name, lab_id=lab_id)
        if tree:
            print_tree_summary(tree)
        else:
            print("Not found")

    else:
        print("Unknown command")
        sys.exit(1)