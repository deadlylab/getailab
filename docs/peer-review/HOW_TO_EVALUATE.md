# How to Evaluate GetAiLab

This is **not** a chatbot. You're evaluating a **research operating system**.

---

## What to compare it against

| Wrong benchmark | Right benchmark |
|-----------------|-----------------|
| "Is the answer correct?" | "Is the *process* auditable and multi-perspective?" |
| Single-shot ChatGPT | Google AI Co-Scientist / lab notebook + team meeting |
| Code completion | Hypothesis → experiment → synthesis loop |

---

## Five things that matter

### 1. Multi-perspective rigour

- Do **11 scientists** genuinely disagree?
- Is dissent preserved in Oracle synthesis (not flattened)?
- See Loop 23 Section IV — quantum vs geometric primacy tension.

### 2. Falsifiability

- Do hypotheses include testable predictions?
- Do experiments produce inspectable artifacts (CSV, JSON, plots)?
- Can you trace stdout/stderr in the report?

### 3. Provenance

- Live report updates per scientist
- Library pages archived post-synthesis
- Optional: Merkle vault integrity check

### 4. Compounding memory

- Scientists pull from their **book** (prior loops, references)
- Run loop 2 on a related problem — do they cite prior work?

### 5. Researcher control

- Phase 4 offers three directions + Oracle decide + custom input + clean stop
- You choose the next problem; the system doesn't trap you in a chain

---

## 6. Graceful failure (optional but impressive)

- If LLM credits exhaust mid-loop, do scientists return clear errors (503)?
- Does the partial report stay clean — no tool-call garbage?
- See Loop 34 partial (8 Jul 2026) as reference.

## Red flags (honest)

- All hypotheses sound the same voice → persona drift
- Code never executes → implement phase failure
- Synthesis ignores stderr → Oracle not grounding in evidence
- Metaphor recycling without new predictions → needs novelty judge (on roadmap)
- Tool-call / shell artifacts in hypotheses → wrong model (use m2.5 for loops)

---

## Scoring

Use `EVALUATION_RUBRIC.md` when ready. Quick gut check:

- **Would you use this for grant ideation?** (yes/no/maybe)
- **Would you trust the audit trail for a team meeting?** (yes/no/maybe)
- **Would you recommend a colleague try it?** (yes/no/maybe)

---

## Showcase without running

- **Primary:** Loop 29 — κ_c falsification (full report in repo root)
- **Alternate:** `examples/loop_23_showcase/README.md` — Orch-OR dialectic (7 Jul 2026)
- **Failure mode:** Loop 34 partial — graceful LLM degradation