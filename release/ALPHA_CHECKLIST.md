# Alpha Release Checklist

Gate before sending **Package 2** (Beta Pilot) to anyone.

## Infrastructure

- [ ] `./boot_chimera.sh` → Commander loads
- [ ] `python3 run_chimera.py --status` → **13/13** (lab + oracle + 11 scientists)
- [ ] `./doctor.sh` passes
- [ ] `evals/smoke_test.sh` passes (or manual status + dry-run review)
- [ ] `.env.example` documents Ollama + Google blocks (no real keys)

## Documentation

- [x] `docs/peer-review/QUICKSTART_15MIN.md`
- [x] `docs/peer-review/HOW_TO_EVALUATE.md`
- [x] `docs/peer-review/EVALUATION_RUBRIC.md`
- [x] `docs/peer-review/FAQ.md`
- [x] `examples/loop_23_showcase/README.md`
- [x] `examples/5min_status/README.md`
- [ ] `examples/loop_29_showcase/` (κ_c falsification — priority)
- [ ] `docs/evidence/LOOP_29_CASE_STUDY.md`
- [ ] `docs/evidence/OLLAMA_VS_GOOGLE_COMPARISON.md` Section B filled
- [ ] `docs/pilot/PILOT_CHARTER.md`
- [ ] `docs/pilot/ONBOARDING_CHECKLIST.md`

## Evidence

- [ ] One non-you human completes quickstart without a call
- [ ] 3 peer review rubrics returned
- [ ] Google comparison loop run (optional but recommended)

## Legal

- [ ] `legal/NDA_*` reviewed for your jurisdiction
- [ ] `legal/Beta_Trial_Terms_and_Conditions.md` current

## Tag when all green

```bash
git tag v0.1.0-alpha
```