# Ollama vs Google API — Model Comparison Protocol

**Purpose:** Document performance delta between local/cloud Ollama and Google Gemini for the same research loop.  
**Baseline captured:** Loop 23 (Ollama). **Google run:** pending — fill Section B after you execute tonight/tomorrow.

---

## A. Baseline — Loop 23 (Ollama)

| Field | Value |
|-------|-------|
| Date | 7 Jul 2026 |
| Loop ID | 23 |
| Provider | `ollama` |
| Model | `minimax-m2.5:cloud` |
| Scientists | 10/10 hypotheses + experiments |
| Report size | ~3,580 lines |
| Wall time | ~record on next run (`date` at start/end) |
| Notable | Full consensus + dissent; Phase 4 directions logged |

**Strengths observed:**
- Complete squad participation
- Rich dialectic; Albert/Roger tension substantive
- Large artifact inventory

**Weaknesses observed:**
- Long wall-clock per scientist (book context + large prompts)
- Some simulated metrics partial vs predicted (10³ vs 10⁶ cost ratio)
- Occasional verbosity / metaphor density

---

## B. Comparison run — Google Gemini (fill after execution)

### Config

```bash
# .env — then restart squad
LLM_PROVIDER=google
GOOGLE_API_KEY=<your key>
LLM_MODEL=gemini-2.0-flash
# Optional faster code pass:
LLM_MODEL_CODE=gemini-2.0-flash
```

```bash
./boot_chimera.sh
python3 run_chimera.py --problem "SAME OR NARROWED PROBLEM AS LOOP 23 — see below"
```

**Suggested comparison problem (shortened from Loop 23):**

> Can microtubular Penrose tiling geometry explain a 6–8 order metabolic efficiency advantage for biological active inference over symbolic AI, and what single experiment would best falsify the geometric vs quantum primacy debate?

Record start: `date`  
Record end: `date`  
Loop ID: _______

### Scorecard (fill in)

| Metric | Loop 23 (Ollama) | Loop N (Google) |
|--------|------------------|-----------------|
| Scientists completed | 10 | |
| Hypotheses distinct? (1–5) | 4 | |
| Code executed (count) | 10 | |
| Synthesis quality (1–5) | 4 | |
| Dissent preserved? (y/n) | y | |
| Wall time (minutes) | ~estimate | |
| API errors (403/timeout) | 0 | |
| Report lines | 3580 | |

### Qualitative notes

**Google better at:**



**Ollama better at:**



**Recommendation for peer review demos:**



---

## C. How to run A/B without burning credits

1. **Hypothesis-only pass** — curl one scientist `/hypothesis` with same problem on each backend  
2. **Single-scientist loop** — temporarily reduce squad in test env  
3. **Full loop** — use for flagship comparison doc only  

---

## D. Security note

- Never commit `.env` or API keys  
- Rotate keys if exposed in logs or chat  
- Use `.env.example` for tester docs only  

---

*Update this file after Google loop completes. Link loop report: `loop_N_report.md`*