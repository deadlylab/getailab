"""
Per-lab inspiration resonance + activity streak — grounded in vault data, not Chimera defaults.

Stored under data/labs/<lab_id>/config/resonance.json (engagement boosts + activity dates).
Streak = consecutive calendar days (ending today) with a completed loop and/or dashboard activity.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from getailab.lab_config import DATA_LABS, agora_db_path, get_lab_id, lab_results_db_path


def _resonance_file(lab_id: Optional[str] = None) -> Path:
    lid = lab_id or get_lab_id()
    return DATA_LABS / lid / "config" / "resonance.json"


def load_resonance(lab_id: Optional[str] = None) -> Dict[str, Any]:
    path = _resonance_file(lab_id)
    default: Dict[str, Any] = {
        "engagement_boost": 0,
        "activity_dates": [],
        "last_updated": None,
    }
    if not path.is_file():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default
        data.setdefault("engagement_boost", 0)
        data.setdefault("activity_dates", [])
        return data
    except Exception:
        return default


def save_resonance(state: Dict[str, Any], lab_id: Optional[str] = None) -> Path:
    path = _resonance_file(lab_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return path


def record_engagement(
    lab_id: Optional[str] = None,
    *,
    boost: int = 1,
    activity: bool = True,
) -> Dict[str, Any]:
    """Persist a user interaction (pulse, resonate, nudge) for this lab only."""
    lid = lab_id or get_lab_id()
    state = load_resonance(lid)
    if activity:
        today = date.today().isoformat()
        dates = set(state.get("activity_dates") or [])
        dates.add(today)
        state["activity_dates"] = sorted(dates)[-120:]
    if boost:
        state["engagement_boost"] = min(28, int(state.get("engagement_boost", 0)) + int(boost))
    save_resonance(state, lid)
    return state


def decay_engagement_boost(lab_id: Optional[str] = None) -> int:
    """Gentle daily decay so inspiration reflects recent activity."""
    lid = lab_id or get_lab_id()
    state = load_resonance(lid)
    boost = int(state.get("engagement_boost", 0))
    last = state.get("last_updated")
    if boost > 0 and last:
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", ""))
            days = (datetime.utcnow() - last_dt).days
            if days >= 1:
                boost = max(0, boost - min(days, 3))
                state["engagement_boost"] = boost
                save_resonance(state, lid)
        except Exception:
            pass
    return boost


def _loop_dates(lab_id: str) -> List[str]:
    """YYYY-MM-DD strings from agora_loops.start_time for this lab."""
    db = agora_db_path(lab_id)
    if not db.is_file():
        return []
    dates: List[str] = []
    try:
        conn = sqlite3.connect(db, timeout=5)
        rows = conn.execute("SELECT start_time FROM agora_loops ORDER BY loop_id ASC").fetchall()
        conn.close()
        for (raw,) in rows:
            if not raw:
                continue
            s = str(raw).strip()
            if len(s) >= 10:
                dates.append(s[:10])
    except Exception:
        pass
    return dates


def compute_resonance_streak(lab_id: Optional[str] = None) -> int:
    """
    Consecutive days ending today with at least one loop or recorded dashboard activity.
    Returns 0 when the lab has no history.
    """
    lid = lab_id or get_lab_id()
    loop_days = set(_loop_dates(lid))
    activity_days = set(load_resonance(lid).get("activity_dates") or [])
    all_days = loop_days | activity_days
    if not all_days:
        return 0

    streak = 0
    d = date.today()
    for _ in range(366):
        if d.isoformat() in all_days:
            streak += 1
            d -= timedelta(days=1)
        else:
            break
    return streak


def compute_inspiration_score(
    stats: Dict[str, Any],
    lab_id: Optional[str] = None,
    squad_size: int = 1,
) -> int:
    """
    Deterministic 0–99 score from this lab's loops, artifacts, library pages, squad balance,
    plus a capped engagement boost from recent pulses/resonates.
    """
    lid = lab_id or get_lab_id()
    loops = int(stats.get("loops_completed") or 0)
    arts = int(stats.get("total_artifacts") or 0)
    lib_pages = int(stats.get("library_pages") or 0)
    agents = len(stats.get("agent_contributions") or {})
    squad = max(1, squad_size)

    loop_pts = min(36, loops * 4)
    art_pts = min(28, arts // 4)
    lib_pts = min(18, lib_pages // 2)
    squad_pts = min(18, int(18 * agents / squad))

    base = loop_pts + art_pts + lib_pts + squad_pts
    if loops == 0 and arts == 0 and lib_pages == 0:
        base = 0

    engagement = decay_engagement_boost(lid)
    return min(99, max(0, base + engagement))


def compute_synthesis_rate(lab_id: Optional[str] = None) -> Dict[str, Any]:
    """Fraction of loops with Oracle consensus for the loop-resonance panel."""
    lid = lab_id or get_lab_id()
    db = agora_db_path(lid)
    total = 0
    with_synth = 0
    if db.is_file():
        try:
            conn = sqlite3.connect(db, timeout=5)
            total = int(conn.execute("SELECT COUNT(*) FROM agora_loops").fetchone()[0] or 0)
            with_synth = int(
                conn.execute(
                    "SELECT COUNT(*) FROM agora_loops WHERE consensus_artefact IS NOT NULL "
                    "AND TRIM(consensus_artefact) != ''"
                ).fetchone()[0]
                or 0
            )
            conn.close()
        except Exception:
            pass
    pct = int(round(100 * with_synth / total)) if total else 0
    return {
        "total_loops": total,
        "synthesized_loops": with_synth,
        "synthesis_pct": pct,
        "has_loops": total > 0,
    }


def _artifacts_per_loop(lab_id: str) -> Dict[int, int]:
    out: Dict[int, int] = {}
    db = lab_results_db_path(lab_id)
    if not db.is_file():
        return out
    try:
        import json as _json
        conn = sqlite3.connect(db, timeout=5)
        rows = conn.execute("SELECT loop_id, artifacts_json FROM lab_experiments").fetchall()
        conn.close()
        for lid_raw, aj in rows:
            try:
                loop_id = int(str(lid_raw))
            except (TypeError, ValueError):
                continue
            cnt = 0
            if aj:
                try:
                    arr = _json.loads(aj)
                    cnt = len(arr) if isinstance(arr, list) else 0
                except Exception:
                    pass
            out[loop_id] = out.get(loop_id, 0) + cnt
    except Exception:
        pass
    return out


def build_trajectory(
    stats: Dict[str, Any],
    lab_id: Optional[str] = None,
    squad_size: int = 1,
) -> Dict[str, Any]:
    """
    Per-loop series for the resonance trajectory chart (this lab only).
    """
    lid = lab_id or get_lab_id()
    db = agora_db_path(lid)
    labels: List[str] = []
    progress: List[int] = []
    library: List[int] = []
    streaks: List[int] = []
    inspiration: List[int] = []

    art_map = _artifacts_per_loop(lid)
    activity_days = set(load_resonance(lid).get("activity_dates") or [])
    loop_day_list: List[str] = []

    rows: List[tuple] = []
    if db.is_file():
        try:
            conn = sqlite3.connect(db, timeout=5)
            rows = conn.execute(
                "SELECT loop_id, start_time FROM agora_loops ORDER BY loop_id ASC"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []

    if not rows:
        return {
            "labels": [],
            "research_progress": [],
            "library_pages": [],
            "streak": [],
            "inspiration": [],
        }

    cumulative_arts = 0
    lib_pages = int(stats.get("library_pages") or 0)
    per_loop_lib = max(1, lib_pages // max(1, len(rows)))

    for loop_id, start_time in rows[-12:]:
        try:
            lid_int = int(loop_id)
        except (TypeError, ValueError):
            continue
        labels.append(f"L{lid_int}")
        cumulative_arts += art_map.get(lid_int, 0)
        day = str(start_time)[:10] if start_time else ""
        if day:
            loop_day_list.append(day)
            activity_days.add(day)

        partial_stats = {
            "loops_completed": len([x for x in labels]),
            "total_artifacts": cumulative_arts,
            "library_pages": per_loop_lib * len(labels),
            "agent_contributions": stats.get("agent_contributions") or {},
        }
        prog = min(
            99,
            int(
                (partial_stats["loops_completed"] * 4)
                + (partial_stats["total_artifacts"] / 20)
                + (partial_stats["library_pages"] / 3)
            ),
        )
        progress.append(prog)
        library.append(partial_stats["library_pages"])

        streak = 0
        if day:
            d = date.fromisoformat(day)
            while d.isoformat() in activity_days:
                streak += 1
                d -= timedelta(days=1)
        streaks.append(streak)
        inspiration.append(compute_inspiration_score(partial_stats, lid, squad_size))

    return {
        "labels": labels,
        "research_progress": progress,
        "library_pages": library,
        "streak": streaks,
        "inspiration": inspiration,
    }