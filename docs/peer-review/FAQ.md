# Peer Review FAQ

**Is this just ChatGPT with eleven tabs?**  
No. Fixed personas, structured phases (hypothesis → implement → execute → synthesize), sandbox artifacts, library vault, ticket provenance. The *process* is the product.

**Do my documents leave my machine?**  
Self-hosted: data stays local unless you use a cloud LLM API (then prompts go to that provider). You control `.env`.

**Which model should I use for loops?**  
`minimax-m2.5:cloud` via Ollama. **Do not use m3 for loops** — Loop 28 produced tool-call garbage in hypotheses. m3 is fine for council chat experiments.

**How long does a loop take?**  
30–90+ minutes depending on model and hardware. Ollama cloud m2.5: several minutes per scientist. Budget time and API credits.

**What if Ollama credits run out mid-loop?**  
Scientists return HTTP 503 with `LLM unavailable`. The Commander prints clear errors. The report stays clean — no corrupted output. Resume when credits return. Loop 34 (8 Jul 2026) demonstrates this.

**What if I stop at the end?**  
Type `q` or `stop` at Phase 4. Report saves; squad keeps running. Ctrl+C during a loop also preserves partial report.

**Do I need to be a developer?**  
Peer review quickstart assumes you can open a terminal. See `QUICKSTART_15MIN.md`.

**How do I verify the squad is up?**  
```bash
./doctor.sh
python3 run_chimera.py --status   # expect 13/13: lab + oracle + 11 scientists
```

**What's the flagship example?**  
- **Primary:** Loop 29 — κ_c resonance falsification (Oracle rejects demonstratable coupling)  
- **Alternate:** `examples/loop_23_showcase/` — Orch-OR metabolic cost dialectic  
- **Failure mode:** Loop 34 partial — graceful degradation receipt

**NDA?**  
`legal/NDA_Beta_Tester_Chimera_DocuSign_Ready.txt` if your institution requires it.