# GetAiLab Build — Operational Plan

**Working directory:** `/home/deadly/x/getailab_live` (official build → repo → testers)

**Status (8 July 2026):** **Working product.** Chimera division fully operational. Not "getting there" — **there**.

---

## What's proven

- [x] Personas load from `personas/chimera_squad.yaml` v1.4 (11 scientists + Oracle)
- [x] Full dialectic loops with sandbox execution + artifacts
- [x] Per-scientist books + skills retrieval (~9,800 vault page files)
- [x] Tickets, Merkle vault, integrity verify, optional signing
- [x] Literature search (PubMed/arXiv/S2) at hypothesis
- [x] Council chat, adaptive learner, collaborative review script
- [x] Graceful LLM degradation (503 — Loop 34)
- [x] `doctor.sh` + full squad `--status`
- [x] 18 loop reports; loops 29–33 complete arc on m2.5

## Model (locked)

| Use | Model |
|-----|--------|
| Loops | `minimax-m2.5:cloud` |
| Chat | m2.5 or m3 (experiments) |
| Vision | `llava:latest` local |

## Next (packaging, not engine)

1. `LOOP_29_CASE_STUDY.md` — primary peer-review story
2. `evals/golden_loops.yaml` + `smoke_test.sh`
3. Dogfood one `collaborative_review` run
4. ~~Lab generator~~ **Done** — `scripts/create_lab.py` + [`docs/LAB_BUILDER.md`](docs/LAB_BUILDER.md)
5. Peer-review wave: 5 trusted evaluators + rubrics

## Chimera division (fixed)

The team in `personas/chimera_squad.yaml` is the **reference implementation**. Personalities and structure are not altered for Chimera. New labs fork from this blueprint via generator (future).

## Scope (unchanged)

**In:** 6-phase loops, sandbox, tickets, library provenance, self-host, SQLite/file only.

**Out:** Postgres, unrelated side projects, fake verification scripts.

---

See [`README.md`](README.md) and [`docs/PREPARATION_STRUCTURE.md`](docs/PREPARATION_STRUCTURE.md) for full doc map.