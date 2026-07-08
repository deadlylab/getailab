# GetAiLab Live — Operating Manual

Working handbook for the current build (updated **8 July 2026**). Covers architecture, boot, loop flow, outputs, degraded mode, and extension points.

---

## 1. What the platform is

GetAiLab Live is a **local-first research operating system** built around the Chimera squad: eleven specialist scientist personas, one Oracle, a sandbox lab, and a persistent vault.

A full research loop:

1. Problem intake (user, Muse, or chained from prior Oracle direction)
2. Hypothesis phase — each scientist contributes (with book context + optional literature inject)
3. Implement phase — experiment code per scientist
4. Execute phase — lab sandbox runs code, writes artifacts
5. Synthesis phase — Oracle consensus with preserved dissent
6. Phase 4 — three ranked next directions; researcher or Oracle picks the next loop

**Evidence it works:** 18 loop reports, loops 29–33 complete end-to-end on `minimax-m2.5:cloud`, ~9,800 vault page files, ~400 sandbox artifacts.

---

## 2. Runtime architecture

### Core services (13 when fully booted)

| Service | Port | File |
|---------|------|------|
| Lab (sandbox + dashboard) | 5035 | `lab/app_lab.py` |
| Oracle | 5024 | `scientists/app_oracle.py` |
| Albert | 5025 | `scientists/app_albert.py` |
| Andrew | 5026 | `scientists/app_andrew.py` |
| Alan | 5027 | `scientists/app_alan.py` |
| Carl | 5028 | `scientists/app_carl.py` |
| Emmy | 5029 | `scientists/app_emmy.py` |
| Tesla | 5030 | `scientists/app_tesla.py` |
| Brian | 5032 | `scientists/app_brian.py` |
| Neil | 5034 | `scientists/app_neil.py` |
| Roger | 5038 | `scientists/app_roger.py` |
| Bohr | 5039 | `scientists/app_bohr.py` |
| Heisenberg | 5040 | `scientists/app_heisenberg.py` |

Lab config: `data/labs/chimera/config/lab.yaml`

### Supporting modules

| Module | Purpose |
|--------|---------|
| `run_chimera.py` | CLI, Commander Console, loop orchestration, `--status` |
| `scientists/base_agent.py` | Shared Flask agent (hypothesis, implement, 503 on LLM failure) |
| `personas/chimera_squad.yaml` | Squad definitions (v1.4) |
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
| `data/labs/chimera/scientists/*/book/` | Per-scientist vault (pages, skills, knowledge.db) |
| `lab/artifacts/{loop_id}/` | Sandbox outputs (.py, .csv, .json, .png) |
| `loop_*_report.md` | Live loop markdown reports |
| `chimera_lab.db` | Oracle loop records |
| `lab/lab_results.db` | Sandbox execution records |
| `logs/` | Per-service logs (`app_albert.log`, etc.) |

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
./boot_chimera.sh          # backgrounds lab + oracle + all scientists
./doctor.sh                # verify stack
python3 run_chimera.py --status   # expect 13/13 healthy
```

### Docker

```bash
./docker_chimera.sh build
./docker_chimera.sh squad
./docker_chimera.sh status
```

### Health check

`python3 run_chimera.py --status` probes **all** scientists (not a sample). Expect:

```json
"lab": { "status": "active" }
"oracle": { "status": "healthy" }
"albert": { "status": "healthy" }
... (all 11 scientists)
```

### Shutdown

```bash
./stop_chimera.sh
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

### Phase 4 (next loop)

At the end of a loop: pick direction `1`/`2`/`3`, Oracle pick `o`, custom `c`, or quit `q`/`stop`. Report is saved either way.

---

## 6. What happens in each phase

**Hypothesis:** POST `/hypothesis` per scientist. Book context + skills injected. Literature search may auto-run. On LLM failure → HTTP **503** + `"LLM unavailable"` — no corrupted prose in report.

**Implement:** POST `/implement` — Python experiment code.

**Execute:** Lab sandbox runs code; STDOUT/STDERR and artifacts logged to report.

**Synthesize:** Oracle builds consensus artefact with dissent, metric tables, artifact inventory.

**Phase 4:** Three next directions + Oracle recommendation.

---

## 7. Graceful degradation (LLM unavailable)

When Ollama credits expire, the endpoint is down, or the model errors:

- Scientist returns **503** with clear error JSON
- Commander prints `❌ {Name} — LLM unavailable.`
- Report records the failure — **no tool-call sludge**
- Systemic failure (all scientists same error) → early abort with fix hints
- User can **Ctrl+C** or `q` at Phase 4 — partial report preserved

**Observed:** Loop 34 (8 Jul 2026) — Albert hypothesis succeeded; remaining scientists 503 when cloud credits exhausted.

---

## 8. Inspecting outputs

After a loop:

1. `loop_N_report.md` — full dialectic
2. `lab/artifacts/N/` — code, plots, data
3. `data/labs/chimera/scientists/*/book/pages/` — archived pages grow
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
| `--status` shows fewer than 13 | `./boot_chimera.sh` — partial boot after Ctrl+C |
| 503 on all scientists | Ollama down, credits exhausted, or wrong model |
| Timeouts | Raise `OLLAMA_TIMEOUT=600`; local hardware needs minutes per scientist |
| Oracle offline | `tail -f logs/app_oracle.log` |
| No artifacts | `curl localhost:5035/health`; check `logs/app_lab.log` |
| Tool-call garbage in hypotheses | Switch loops to m2.5; sanitizer should block but don't rely on m3 |

---

## 10. Extension points

- New persona fields: `personas/chimera_squad.yaml` (Chimera division fixed — fork for new labs)
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

*GetAiLab Live · Project Chimera · CryptO'Brien Pty Ltd*