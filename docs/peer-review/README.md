# Peer Review Pack

**For:** Researchers, academics, and technical evaluators.  
**Updated:** 8 July 2026

## Start here

1. [`QUICKSTART_15MIN.md`](QUICKSTART_15MIN.md) — boot squad, run a loop, read the report
2. [`HOW_TO_EVALUATE.md`](HOW_TO_EVALUATE.md) — what makes this different from chatbots
3. [`EVALUATION_RUBRIC.md`](EVALUATION_RUBRIC.md) — structured 1–5 scoring
4. [`FAQ.md`](FAQ.md) — privacy, models, credits, degraded mode

## Showcase material

| Example | Best for |
|---------|----------|
| [`../../examples/loop_23_showcase/`](../../examples/loop_23_showcase/) | Orch-OR / metabolic cost flagship (Jul 7) |
| `loop_29_report.md` (root) | **κ_c falsification** — Oracle rejects its own mechanism (primary story) |
| `loop_34_report.md` (partial) | Graceful LLM failure when credits exhaust — honest limits |

Never hand evaluators a raw 4,000-line report without a distillation.

## Current build facts (for evaluators)

- **13 services** when booted: lab + Oracle + 11 scientists (incl. Tesla)
- **Loop model:** `minimax-m2.5:cloud` — do not use m3 for loops
- **Health:** `./doctor.sh` or `python3 run_chimera.py --status` → expect 13/13
- **Vault:** ~9,800 page files in `data/labs/chimera/`
- **18 loop reports** on disk; loops 29–33 = complete recent arc

## Legal

NDA: [`../../legal/NDA_Beta_Tester_Chimera_DocuSign_Ready.txt`](../../legal/NDA_Beta_Tester_Chimera_DocuSign_Ready.txt)  
Beta terms: [`../../legal/Beta_Trial_Terms_and_Conditions.md`](../../legal/Beta_Trial_Terms_and_Conditions.md)