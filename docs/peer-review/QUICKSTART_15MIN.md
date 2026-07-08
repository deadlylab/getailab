# Quickstart — 15 Minutes to Your First Loop

**For peer reviewers.** Goal: boot squad → run one loop → read the report.

---

## Before you start (2 min)

- Python 3.11+, repo cloned, `.env` copied from `.env.example`
- **Either** local Ollama running **or** cloud API key in `.env`
- Linux/macOS terminal (Windows: WSL2 or Docker)

---

## Step 1 — Boot the squad (3 min)

```bash
cd getailab_live
./boot_example.sh
```

Wait for Commander Console menu. In another terminal:

```bash
python3 run_chimera.py --status
```

**Target:** lab `active`, oracle + **2 example scientists** `healthy` (ports 5124–5135). Forge a bigger squad with `scripts/create_lab.py`. See `docs/BOOT_MANUAL.md`.

```bash
./doctor.sh   # optional one-liner before --status
```

---

## Step 2 — Pick your LLM backend (1 min)

**Local Ollama (privacy default):**

```bash
# .env
LLM_PROVIDER=ollama
LLM_MODEL=minimax-m2.5:cloud   # or your pulled model
OLLAMA_TIMEOUT=600
```

**Google API (comparison / faster runs):**

```bash
# .env
LLM_PROVIDER=google
GOOGLE_API_KEY=your_key_here
LLM_MODEL=gemini-2.0-flash
```

Restart squad after `.env` changes:

```bash
./boot_example.sh
```

---

## Step 3 — Run a loop (5–60 min depending on model)

**Short problem (recommended for first run):**

```bash
python3 run_chimera.py --problem "What minimal experiment would falsify the claim that hierarchical gating reduces metabolic cost in neural active inference?"
```

**Or interactive:**

```bash
python3 run_chimera.py
# → 1 (Run a research loop)
# paste problem or type: muse
```

The live report writes to `loop_N_report.md` in the project root as each scientist completes.

---

## Step 4 — Read the output (5 min)

Open `loop_N_report.md`. Check:

1. **Hypotheses** — distinct voices, not copy-paste?
2. **Experiments** — code ran? STDOUT/STDERR present?
3. **Oracle synthesis** — consensus + dissent?
4. **Direction picker** (CLI Phase 4) — three next directions at the end?

Optional: inspect artifacts in `lab/artifacts/N/`.

---

## Step 5 — Verify provenance (2 min)

```bash
# Library page counts
ls data/labs/example/scientists/*/book/pages 2>/dev/null | wc -l

# Integrity (optional)
python3 -c "from getailab.integrity.verify import full_integrity_report; import json; print(json.dumps(full_integrity_report(), indent=2)[:2000])"
```

---

## Ending the loop chain

At the direction picker (CLI Phase 4 — Researcher Input):

| Choice | Action |
|--------|--------|
| `1` / `2` / `3` | Start next loop with that direction |
| `o` or Enter | Let Oracle decide |
| `c` | Enter your own problem |
| `q` or `stop` | **Quit cleanly** — report saved, squad keeps running |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Scientist timeouts | Raise `OLLAMA_TIMEOUT=600` in `.env`, restart |
| 503 on hypothesis | Ollama down, credits exhausted, or wrong model — report stays clean; resume when fixed |
| Partial loop (credits) | Expected — scientists show `LLM unavailable`; partial report saved |
| Oracle offline | `tail -f logs/app_oracle.log` |
| Docker | `docker-compose.yml` (configure for your lab) |

Full manual: `docs/BOOT_MANUAL.md`

---

## What to send back

Fill in [`EVALUATION_RUBRIC.md`](EVALUATION_RUBRIC.md) or reply with:

- Loop ID and problem used
- Rubric scores (1–5)
- One thing that surprised you
- One thing that needs work

---

*Flagship runs: Loop 29 (κ_c falsification) · `examples/loop_23_showcase/` · Loop 34 partial (graceful failure)*