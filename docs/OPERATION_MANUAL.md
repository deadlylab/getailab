# GetAiLab Live — Operating Manual

Working handbook for the current build (updated **8 July 2026**). Covers architecture, boot, loop flow, outputs, degraded mode, and extension points.

---

## 1. What the platform is

GetAiLab Live is a **local-first research operating system**: a squad of scientist personas (the shipped example has two), one Oracle, a sandbox lab, and a persistent vault per `LAB_ID`.

A full research loop — **five work stages**, plus intake and optional vault archive:

| Stage | What happens | CLI header | Job ticket tag |
|-------|----------------|------------|----------------|
| Intake | Problem registered with Oracle; optional Sauron URL + literature grounding | *(not numbered)* | `phase:loop` (parent) |
| 1. Hypothesis | Each scientist contributes (book context + literature) | **Phase 1** | `hypothesis` |
| 2. Implement | Experiment code per scientist | **Phase 2** *(bundled)* | `implement` |
| 3. Execute | Lab sandbox runs code, writes artifacts | **Phase 2** *(bundled)* | `execute` |
| 4. Synthesize | Oracle consensus with preserved dissent | **Phase 3** | `synthesize` |
| Archive | Vault ingest when synthesis archives to library | *(not shown)* | `archive` *(optional)* |
| 5. Direction | Three ranked next problems; you or Oracle pick the next loop or quit | **Phase 4** | *(not ticketed)* |

```
Intake → Hypothesis (×N) → Implement → Execute → Synthesize → [Archive] → Direction picker
```

The terminal shows **four phase headers** because implement and execute run under one banner: *Phase 2: Experiment & Artifact Audit*.

**Evidence it works:** dialectic loops complete end-to-end on `minimax-m2.5:cloud`; a mature local deployment accumulates vault pages and sandbox artifacts under `data/labs/<lab_id>/`.

---

## 2. Runtime architecture

### Core services (example lab: 4 when booted)

Ports come from `data/labs/<lab_id>/config/lab.yaml`. Shipped example:

| Service | Port | File |
|---------|------|------|
| Lab (sandbox + dashboard) | 5135 | `lab/app_lab.py` |
| Oracle | 5124 | `scientists/app_oracle.py` |
| Researcher | 5125 | `scientists/forges/example/app_researcher.py` |
| Critic | 5126 | `scientists/forges/example/app_critic.py` |

Forged labs use the same pattern under `scientists/forges/<lab_id>/`. Lab config: `data/labs/<lab_id>/config/lab.yaml`

### Supporting modules

| Module | Purpose |
|--------|---------|
| `run_chimera.py` | CLI, Commander Console, loop orchestration, `--status` |
| `scientists/base_agent.py` | Shared Flask agent (hypothesis, implement, 503 on LLM failure) |
| `personas/<lab_id>_squad.yaml` | Squad definitions (v1.4) |
| `personas/loader.py` | YAML → agent config |
| `getailab/literature_search.py` | PubMed / arXiv / Semantic Scholar |
| `llm/sanitize.py` | Strip tool-call artifacts from model output |
| `getailab/library/` | Scientist books, skills, ingest, Merkle vault |
| `getailab/integrity/` | Crush test, verify, signing |
| `getailab/tickets/` | Per-phase job tickets |
| `scripts/collaborative_review.py` | Multi-scientist document review |
| `doctor.sh` | One-command health check |

### Data locations

| Path | Contents |
|------|----------|
| `data/labs/<your_lab>/scientists/*/book/` | Per-scientist vault (pages, skills, knowledge.db) |
| `lab/artifacts/{loop_id}/` | Sandbox outputs (.py, .csv, .json, .png) |
| `data/labs/<lab_id>/reports/` | Loop markdown reports (forged + example labs) |
| `data/labs/<lab_id>/agora.db` | Oracle loop records |
| `data/labs/<lab_id>/lab_results.db` | Sandbox execution records |
| `logs/` | Per-service logs |

---

## 3. LLM configuration

Default for loops (`.env`):

```
LLM_PROVIDER=ollama
LLM_ENDPOINT=http://localhost:11434
LLM_MODEL=minimax-m2.5:cloud
LLM_MODEL_CODE=minimax-m2.5:cloud
SCIENTIST_HTTP_TIMEOUT=600
OLLAMA_TIMEOUT=600
CHAT_MAX_REPLY_CHARS=8000
```

**Loops:** use `minimax-m2.5:cloud` only. **Loop 28** on m3 emitted `<tool_call>` blocks into hypotheses — use m3 for chat experiments only.

Alternatives: Google, OpenAI, Anthropic via `LLM_PROVIDER` + API key (see `.env.example`).

Vision (Sauron): `LLM_MODEL_VISION=llava:latest` (local Ollama).

---

## 4. Starting the platform

### Native (recommended)

```bash
./boot_example.sh          # backgrounds lab + oracle + all scientists
./doctor.sh                # verify stack
python3 run_chimera.py --status   # example lab: lab + oracle + 2 scientists healthy
```

### Docker

```bash
docker compose build
docker compose squad
docker compose status
```

### Health check

`python3 run_chimera.py --status` probes **all** scientists (not a sample). Expect:

```json
"lab": { "status": "active" }
"oracle": { "status": "healthy" }
"researcher": { "status": "healthy" }
... (all scientists in your squad)
```

### Shutdown

```bash
./stop_example.sh
# or: pkill -f 'python3.*app_'
```

See [`BOOT_MANUAL.md`](BOOT_MANUAL.md) for port conflicts, Ollama + Docker, and troubleshooting.

---

## 5. Running a loop

### Direct problem

```bash
python3 run_chimera.py --problem "Your concrete research question"
```

### Interactive

```bash
python3 run_chimera.py
# Menu: run loop, chat, status, no-idea Muse flow, beef-up references, collab review
```

### No-idea / Muse

```bash
python3 run_chimera.py --no-idea
```

### Council chat

```bash
python3 run_chimera.py --chat
```

### Direction picker (CLI Phase 4)

At the end of a loop: pick direction `1`/`2`/`3`, Oracle pick `o`, custom `c`, or quit `q`/`stop`. Report is saved either way. This is the fifth work stage; the CLI labels it Phase 4 because Phases 1–3 cover hypothesis, experiment, and synthesis.

---

## 6. What happens in each stage

**Intake:** `POST /initiate_loop` on Oracle. Optional Sauron URL scrape + literature search injected before hypotheses.

**Hypothesis:** `POST /hypothesis` per scientist. Book context + skills injected. On LLM failure → HTTP **503** + `"LLM unavailable"` — no corrupted prose in report.

**Implement:** `POST /implement` — Python experiment code per scientist.

**Execute:** Lab sandbox runs code; STDOUT/STDERR and artifacts logged to report.

**Synthesize:** Oracle builds consensus artefact with dissent, metric tables, artifact inventory.

**Archive:** When synthesis archives to GetAiLabLibrary — ticketed, not a separate CLI banner.

**Direction:** Oracle `recommend_next` → three options + researcher choice for chained loops.

---

## 7. Graceful degradation (LLM unavailable)

When Ollama credits expire, the endpoint is down, or the model errors:

- Scientist returns **503** with clear error JSON
- Commander prints `❌ {Name} — LLM unavailable.`
- Report records the failure — **no tool-call sludge**
- Systemic failure (all scientists same error) → early abort with fix hints
- User can **Ctrl+C** or `q` at the direction picker (CLI Phase 4) — partial report preserved

**Observed:** Loop 34 (8 Jul 2026) — Albert hypothesis succeeded; remaining scientists 503 when cloud credits exhausted.

---

## 8. Inspecting outputs

After a loop:

1. `loop_N_report.md` — full dialectic
2. `lab/artifacts/N/` — code, plots, data
3. `data/labs/<your_lab>/scientists/*/book/pages/` — archived pages grow
4. `logs/app_*.log` — per-scientist traces
5. Dashboard → http://localhost:5035 — live progress, loop history, learner panel

Integrity snapshot:

```bash
python3 -c "from getailab.integrity.verify import full_integrity_report; import json; print(json.dumps(full_integrity_report(), indent=2))"
```

---

## 9. Troubleshooting

| Symptom | Check |
|---------|-------|
| `--status` shows fewer than 13 | `./boot_example.sh` — partial boot after Ctrl+C |
| 503 on all scientists | Ollama down, credits exhausted, or wrong model |
| Timeouts | Raise `OLLAMA_TIMEOUT=600`; local hardware needs minutes per scientist |
| Oracle offline | `tail -f logs/app_oracle.log` |
| No artifacts | `curl localhost:5035/health`; check `logs/app_lab.log` |
| Tool-call garbage in hypotheses | Switch loops to m2.5; sanitizer should block but don't rely on m3 |

---

## 10. Extension points

- New persona fields: `personas/<lab_id>_squad.yaml` (reference operational lab fixed — fork for new labs)
- Agent behaviour: `scientists/base_agent.py`
- Sandbox tools: `lab/app_lab.py` (execute, vision, web, literature)
- Oracle synthesis: `scientists/app_oracle.py`
- CLI / loop logic: `run_chimera.py`

Preserve: artifact flow, ticket trail, vault checksums, dissent in synthesis.

---

## 11. Further reading

- Boot & ports: [`BOOT_MANUAL.md`](BOOT_MANUAL.md)
- Capabilities: [`CAPABILITIES_AND_USE_CASES.md`](CAPABILITIES_AND_USE_CASES.md)
- Peer review: [`peer-review/QUICKSTART_15MIN.md`](peer-review/QUICKSTART_15MIN.md)
- Competitive position: [`COMPETITIVE_AUDIT_JULY_2026.md`](COMPETITIVE_AUDIT_JULY_2026.md)

*GetAiLab Live · GetAiLab · CryptO'Brien Pty Ltd*