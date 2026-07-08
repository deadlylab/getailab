"""
Vault crush test + Merkle scan orchestration — adapted from Old Mate knowledge_index.py.

Crush test: every library page's on-disk content hash must match its stored checksum
(and SQLite index when present). Refuses tampered pages at verify time.

Merkle orchestration: snapshot vault + lab artifacts, diff against previous scans.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from getailab.integrity.merkle import (
    compare_saved_trees,
    load_tree,
    scan_directory,
    tree_summary,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _lab_path(lab_id: str, project_root: Optional[Path] = None) -> Path:
    root = project_root or _project_root()
    return root / "data" / "labs" / lab_id


def _artifacts_dir(lab_id: str, project_root: Optional[Path] = None) -> Path:
    from getailab.lab_config import lab_artifacts_dir
    return lab_artifacts_dir(lab_id)


def content_checksum(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def iter_vault_pages(lab_path: Path) -> Iterator[Tuple[str, Path]]:
    """Yield (book_id, path) for every page JSON under the vault."""
    codex_pages = lab_path / "codex" / "book" / "pages"
    if codex_pages.is_dir():
        for path in sorted(codex_pages.glob("*.json")):
            yield "codex", path

    scientists_dir = lab_path / "scientists"
    if scientists_dir.is_dir():
        for sci_dir in sorted(scientists_dir.iterdir()):
            if not sci_dir.is_dir():
                continue
            pages_dir = sci_dir / "book" / "pages"
            if pages_dir.is_dir():
                for path in sorted(pages_dir.glob("*.json")):
                    yield sci_dir.name, path


def crush_test_page(path: Path, book_id: str) -> Dict[str, Any]:
    """
    Verify one page file: JSON checksum, optional .sha256 sidecar.
    Returns per-page result with integrity PASS/FAIL semantics.
    """
    page_id = path.stem
    result: Dict[str, Any] = {
        "page_id": page_id,
        "book_id": book_id,
        "file_path": str(path),
        "integrity": "PASS",
        "issues": [],
    }

    if not path.exists():
        result["integrity"] = "FAIL"
        result["issues"].append({"type": "missing", "detail": "page file not found"})
        return result

    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        result["integrity"] = "FAIL"
        result["issues"].append({"type": "read_error", "detail": str(exc)})
        return result

    page_id = data.get("page_id", page_id)
    result["page_id"] = page_id
    content = data.get("content", "")
    expected = data.get("content_checksum", "")
    actual = content_checksum(content)

    if expected and actual != expected:
        result["integrity"] = "FAIL"
        result["issues"].append({
            "type": "checksum_mismatch",
            "expected": expected,
            "actual": actual,
        })

    sidecar = path.parent / f"{path.stem}.sha256"
    if sidecar.exists():
        sidecar_val = sidecar.read_text().strip()
        if sidecar_val != expected:
            result["integrity"] = "FAIL"
            result["issues"].append({
                "type": "sidecar_mismatch",
                "expected": expected,
                "actual": sidecar_val,
            })
    elif expected:
        result["issues"].append({
            "type": "sidecar_missing",
            "detail": f"no sidecar at {sidecar}",
        })

    result["expected_checksum"] = expected
    result["actual_checksum"] = actual
    return result


def crush_test_vault(
    lab_id: str = "chimera",
    *,
    book_id: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Crush test all library pages in the vault (Old Mate verify_integrity pattern).
    """
    vault = _lab_path(lab_id, project_root)
    if not vault.is_dir():
        return {
            "integrity": "FAIL",
            "error": f"vault not found: {vault}",
            "lab_id": lab_id,
        }

    verified = 0
    mismatches: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []
    sidecar_issues: List[Dict[str, Any]] = []
    read_errors: List[Dict[str, Any]] = []
    total = 0

    for page_book_id, path in iter_vault_pages(vault):
        if book_id and book_id != "codex" and page_book_id != book_id:
            continue
        total += 1
        if not path.exists():
            missing.append({
                "page_id": path.stem,
                "book_id": page_book_id,
                "file_path": str(path),
            })
            continue

        page_result = crush_test_page(path, page_book_id)
        if page_result["integrity"] == "PASS":
            verified += 1
            for issue in page_result.get("issues", []):
                if issue["type"] == "sidecar_missing":
                    sidecar_issues.append({
                        "page_id": page_result["page_id"],
                        "book_id": page_book_id,
                        "file_path": str(path),
                        "detail": issue["detail"],
                    })
            continue

        for issue in page_result.get("issues", []):
            entry = {
                "page_id": page_result["page_id"],
                "book_id": page_book_id,
                "file_path": str(path),
            }
            if issue["type"] == "checksum_mismatch":
                entry["expected"] = issue["expected"]
                entry["actual"] = issue["actual"]
                mismatches.append(entry)
            elif issue["type"] == "sidecar_mismatch":
                entry["expected"] = issue["expected"]
                entry["actual"] = issue["actual"]
                sidecar_issues.append(entry)
            elif issue["type"] == "read_error":
                entry["detail"] = issue["detail"]
                read_errors.append(entry)
            else:
                entry["detail"] = issue.get("detail", issue["type"])
                mismatches.append(entry)

    integrity = "PASS" if not mismatches and not missing and not read_errors else "FAIL"

    return {
        "integrity": integrity,
        "lab_id": lab_id,
        "vault": str(vault),
        "book_filter": book_id,
        "total": total,
        "verified": verified,
        "mismatches": mismatches[:50],
        "missing": missing[:50],
        "sidecar_issues": sidecar_issues[:50],
        "read_errors": read_errors[:20],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def crush_test_indexes(
    lab_id: str = "chimera",
    *,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Verify SQLite knowledge.db checksums match on-disk page JSON content.
    Detects index drift after manual edits or failed reindex.
    """
    vault = _lab_path(lab_id, project_root)
    stale: List[Dict[str, Any]] = []
    missing_index: List[Dict[str, Any]] = []
    orphan_index: List[Dict[str, Any]] = []
    checked = 0

    book_dirs: List[Tuple[str, Path]] = [("codex", vault / "codex" / "book")]
    scientists_dir = vault / "scientists"
    if scientists_dir.is_dir():
        for sci_dir in sorted(scientists_dir.iterdir()):
            if sci_dir.is_dir():
                book_dirs.append((sci_dir.name, sci_dir / "book"))

    for book_name, book_dir in book_dirs:
        db_path = book_dir / "knowledge.db"
        pages_dir = book_dir / "pages"
        if not db_path.exists() or not pages_dir.is_dir():
            continue

        on_disk: Dict[str, str] = {}
        for path in pages_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                on_disk[data.get("page_id", path.stem)] = content_checksum(
                    data.get("content", "")
                )
            except Exception:
                continue

        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT page_id, content_checksum FROM pages"
        ).fetchall()
        conn.close()

        indexed = {row["page_id"]: row["content_checksum"] for row in rows}
        checked += len(on_disk)

        for page_id, actual in on_disk.items():
            expected = indexed.get(page_id)
            if expected is None:
                missing_index.append({
                    "book_id": book_name,
                    "page_id": page_id,
                    "actual_checksum": actual,
                })
            elif expected != actual:
                stale.append({
                    "book_id": book_name,
                    "page_id": page_id,
                    "expected": expected,
                    "actual": actual,
                })

        for page_id in indexed:
            if page_id not in on_disk:
                orphan_index.append({"book_id": book_name, "page_id": page_id})

    integrity = "PASS" if not stale and not missing_index and not orphan_index else "FAIL"
    return {
        "integrity": integrity,
        "lab_id": lab_id,
        "checked_pages": checked,
        "stale_index": stale[:50],
        "missing_index": missing_index[:50],
        "orphan_index": orphan_index[:50],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def scan_integrity_targets(
    lab_id: str = "chimera",
    *,
    vault: bool = True,
    artifacts: bool = True,
    loop_id: Optional[int] = None,
    rotate_previous: bool = True,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run Merkle snapshots for vault and/or lab artifacts."""
    root = project_root or _project_root()
    scans: Dict[str, Any] = {}

    if vault:
        vault_path = _lab_path(lab_id, root)
        if vault_path.is_dir():
            scans["vault"] = scan_directory(
                vault_path,
                "vault",
                lab_id=lab_id,
                rotate_previous=rotate_previous,
            )
        else:
            scans["vault"] = {"error": f"vault not found: {vault_path}"}

    if artifacts or loop_id is not None:
        artifacts_root = _artifacts_dir(lab_id, root)
        if loop_id is not None:
            target = artifacts_root / str(loop_id)
            name = f"artifacts_loop_{loop_id}"
            if target.is_dir():
                scans[name] = scan_directory(
                    target,
                    name,
                    lab_id=lab_id,
                    rotate_previous=rotate_previous,
                )
            else:
                scans[name] = {"error": f"artifacts path not found: {target}"}
        elif artifacts:
            target = artifacts_root
            name = "lab_artifacts"
            if target.is_dir():
                scans[name] = scan_directory(
                    target,
                    name,
                    lab_id=lab_id,
                    rotate_previous=rotate_previous,
                )
            else:
                scans[name] = {"error": f"artifacts path not found: {target}"}

    return {
        "lab_id": lab_id,
        "scans": scans,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def merkle_status(lab_id: str = "chimera") -> Dict[str, Any]:
    """Report saved Merkle trees and change counts vs previous snapshots."""
    names = ["vault", "lab_artifacts"]
    trees: Dict[str, Any] = {}
    for name in names:
        current = load_tree(name, lab_id=lab_id)
        if not current:
            trees[name] = {"saved": False}
            continue
        diff = compare_saved_trees(name, lab_id=lab_id)
        trees[name] = {
            "saved": True,
            **tree_summary(current),
            "changes_vs_previous": diff.get("change_count") if "error" not in diff else None,
            "compare_error": diff.get("error"),
        }
    return {"lab_id": lab_id, "trees": trees}


def verify_full(
    lab_id: str = "chimera",
    *,
    book_id: Optional[str] = None,
    merkle_scan: bool = False,
    loop_id: Optional[int] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Full integrity report: vault crush test + index crush test + Merkle status/scan.
    """
    pages = crush_test_vault(lab_id, book_id=book_id, project_root=project_root)
    indexes = crush_test_indexes(lab_id, project_root=project_root)

    merkle: Dict[str, Any]
    if merkle_scan:
        merkle = scan_integrity_targets(
            lab_id,
            vault=True,
            artifacts=True,
            loop_id=loop_id,
            project_root=project_root,
        )
    else:
        merkle = merkle_status(lab_id)

    signing: Dict[str, Any] = {"available": False}
    try:
        from getailab.integrity.signing import (
            signing_available,
            signing_status,
            verify_merkle_signature,
        )

        signing["available"] = signing_available()
        signing["status"] = signing_status(lab_id, project_root=project_root)
        if signing_available():
            signing["vault"] = verify_merkle_signature(
                lab_id, tree_name="vault", project_root=project_root
            )
    except Exception as exc:
        signing["error"] = str(exc)

    overall = "PASS"
    if pages.get("integrity") != "PASS" or indexes.get("integrity") != "PASS":
        overall = "FAIL"
    vault_sig = signing.get("vault") or {}
    if vault_sig.get("valid") is False and vault_sig.get("message") != "no signatures found":
        overall = "FAIL"

    return {
        "integrity": overall,
        "lab_id": lab_id,
        "book_filter": book_id,
        "pages": pages,
        "indexes": indexes,
        "merkle": merkle,
        "signing": signing,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("GetAiLab Integrity Verify")
        print("Usage:")
        print("  python3 -m getailab.integrity.verify crush [--lab chimera] [--book albert]")
        print("  python3 -m getailab.integrity.verify index [--lab chimera]")
        print("  python3 -m getailab.integrity.verify scan [--lab chimera] [--loop N]")
        print("  python3 -m getailab.integrity.verify full [--lab chimera] [--book albert] [--scan]")
        sys.exit(0)

    cmd = sys.argv[1]
    lab_id = "chimera"
    book_id: Optional[str] = None
    loop_id: Optional[int] = None
    merkle_scan = "--scan" in sys.argv

    if "--lab" in sys.argv:
        lab_id = sys.argv[sys.argv.index("--lab") + 1]
    if "--book" in sys.argv:
        book_id = sys.argv[sys.argv.index("--book") + 1]
    if "--loop" in sys.argv:
        loop_id = int(sys.argv[sys.argv.index("--loop") + 1])

    if cmd == "crush":
        report = crush_test_vault(lab_id, book_id=book_id)
    elif cmd == "index":
        report = crush_test_indexes(lab_id)
    elif cmd == "scan":
        report = scan_integrity_targets(
            lab_id,
            vault=loop_id is None,
            artifacts=loop_id is None,
            loop_id=loop_id,
        )
    elif cmd == "full":
        report = verify_full(
            lab_id, book_id=book_id, merkle_scan=merkle_scan, loop_id=loop_id
        )
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    print(json.dumps(report, indent=2))