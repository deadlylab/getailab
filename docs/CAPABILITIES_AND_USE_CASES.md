# GetAiLab — Capabilities and Use Cases

Updated **8 July 2026** to reflect the working Chimera build.

---

## 1. What the platform is for

GetAiLab is a **self-hostable research operating system**: eleven specialist scientist personas, one Oracle, structured loops, sandbox execution, and a vault trail you can show to a reviewer.

It is not a chatbot. The **process** is the product:

```
Intake → Hypothesis (×11) → Implement → Execute → Synthesize → [Archive] → Next direction
```

CLI shows four phase headers; implement and execute share Phase 2. See `docs/OPERATION_MANUAL.md` §1.

---

## 2. Live capabilities (verified)

### Research loop

- Full dialectic: hypothesis, implement, sandbox execute, Oracle synthesis, direction picker (CLI Phase 4)
- Live markdown report (`loop_N_report.md`) written as each phase completes
- Chained loops — Oracle pick seeds the next problem (loops 24→33 demonstrated)
- No-idea / Muse onboarding for problem generation
- Collaborative document review (`python3 run_chimera.py --collab-review`)

### Multi-agent dialectic

- **11 scientists** + Oracle — distinct personas from `personas/chimera_squad.yaml` v1.4
- Preserved dissent in Oracle synthesis (Section IV style productive tensions)
- Tesla integrated (coupled-oscillator / resonance framing)
- Book context + skills injected at hypothesis and implement phases

### Sandbox and artifacts

- NumPy, SciPy, Matplotlib, Pandas, SymPy execution
- Artifacts under `lab/artifacts/{loop_id}/` (~400 files in current build)
- STDOUT/STDERR captured in loop reports

### Literature and web grounding

- **Literature search** — PubMed, arXiv, Semantic Scholar (`getailab/literature_search.py`)
- Auto-inject at hypothesis phase
- Sauron vision (plot extraction from papers)
- Web reader for URL content

### Provenance and memory

- Per-scientist books — **~9,800 vault page files** in `data/labs/chimera/`
- Skills patterns extracted from prior experiments
- Job tickets per scientist per phase
- Merkle integrity scan + optional Ed25519 vault signing
- Reference ingest (`--beef-up albert --file paper.md`)

### Operations and reliability

- `doctor.sh` — one-command health
- `python3 run_chimera.py --status` — probes all 13 services
- **Graceful LLM degradation** — HTTP 503, clear errors, no corrupted reports (Loop 34 proven)
- LLM output sanitizer (blocks tool-call artifacts — insurance against wrong model)
- Council chat with real LLM (`--chat` or dashboard)
- Adaptive learner (Gabby) — post-loop + dashboard loop modal

### Interfaces

- CLI / Commander Console (`run_chimera.py`)
- Web dashboard PWA (`http://localhost:5035`)
- Desktop launcher (`desktop_launcher.py`)
- Docker full squad (`./docker_chimera.sh squad`)
- Mobile chat stub + `/api/mobile/chat`

### LLM backends

- **Ollama** (default) — `minimax-m2.5:cloud` for loops (stable)
- Google, OpenAI, Anthropic via `.env`
- Local vision: `llava:latest`

---

## 3. Current use cases (ready now)

| Use case | How |
|----------|-----|
| **Research ideation** | `--no-idea` or `--problem` with concrete question |
| **Multi-perspective debate** | Full loop — read hypotheses + Oracle dissent |
| **In-silico experiments** | Implement + execute phases → artifacts |
| **Auditable R&D trail** | Loop report + vault pages + tickets |
| **Literature-grounded hypotheses** | Auto literature inject at hypothesis |
| **Document review** | `--collab-review --file doc.md` |
| **Education / mastery** | Adaptive learner tracks loop engagement |
| **Peer evaluation** | `docs/peer-review/` pack + Loop 29 showcase |

---

## 4. Adaptable use cases (roadmap)

- Grant / thesis preparation with collaborative review
- Competitive analysis via multi-lens document ingest
- WA education corpus (337 units on disk — not yet wired to Chimera)
- External validation sprint (literature + public dataset check)
- Robin-style closed loop (upload CSV → interpret → next loop)

---

## 5. Differentiation

| Generic agent | GetAiLab |
|---------------|----------|
| Single voice | 11 perspectives + Oracle |
| Ephemeral chat | Compounding scientist books |
| No experiment trail | Sandbox artifacts + checksums |
| Black-box answers | Dissent preserved, falsification encouraged |
| Cloud-only | Self-host, any model, air-gap capable |

**Positioning:** *The auditable research operating system — for teams who must show their working.*

---

## 6. Known limits (honest)

- In-silico only — no wet-lab validation loop yet
- Ollama cloud credits can exhaust mid-loop (degrades gracefully)
- Golden-loop eval harness not built (`evals/golden_loops.yaml` todo)
- Collaborative review script not yet dogfooded
- m3 cloud unsuitable for loops (use m2.5)
- ~30+ min to first loop for new users without quickstart hand-holding

---

## 7. Further reading

- [`OPERATION_MANUAL.md`](OPERATION_MANUAL.md) — how to run
- [`COMPETITIVE_AUDIT_JULY_2026.md`](COMPETITIVE_AUDIT_JULY_2026.md) — field comparison
- [`peer-review/HOW_TO_EVALUATE.md`](peer-review/HOW_TO_EVALUATE.md) — evaluator guide

*GetAiLab Live · Project Chimera*