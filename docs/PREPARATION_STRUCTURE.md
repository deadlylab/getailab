# GetAiLab — Preparation Structure (Squeaky Clean)

**Purpose:** Realistic map for peer review, pilot testing, and (if you want) investor conversations.  
**Not** another strategy essay — this is **where things go** and **what gets done in what order**.

The competitive audit (`COMPETITIVE_AUDIT_JULY_2026.md`) is the *analysis*. This doc is the *operating structure*.

---

## 1. Top-Level Layout

```
getailab_live/
│
├── 📦 PRODUCT (already built — don't reorganise code)
│   ├── run_chimera.py              # CLI + Commander
│   ├── scientists/                 # Squad agents
│   ├── lab/                        # Sandbox + artifacts
│   ├── getailab/                   # Library, tickets, integrity, learning
│   ├── personas/                   # Squad YAML + loader
│   ├── scripts/                    # Ops + ingest + review tools
│   └── dashboard/                  # Web UI
│
├── 📋 PREP (new — fill these in)
│   ├── docs/peer-review/           # What evaluators receive
│   ├── docs/pilot/                 # Beta program ops
│   ├── docs/evidence/              # Case studies + validation receipts
│   ├── docs/investor/              # Data room lite (only when ready)
│   ├── evals/                      # Golden loops + regression harness
│   ├── examples/                   # Curated demo runs for strangers
│   └── release/                    # Alpha packaging checklist + scripts
│
├── 🤝 OUTREACH (already started)
│   ├── outreach/                   # Contact lists
│   └── legal/                      # NDA, beta terms
│
└── 📚 ARCHIVE (existing — reference only)
    ├── docs/loops/                 # Historical loop reports
    └── loop_*_report.md            # Live runs (move to docs/loops when done)
```

---

## 2. Folder Purposes — What Goes Where

### `docs/peer-review/` — *Give this to serious evaluators*

| File | Status | Purpose |
|------|--------|---------|
| `README.md` | ✅ scaffold | Index — start here |
| `HOW_TO_EVALUATE.md` | ✅ done | What to look for (provenance, dissent, falsifiability) |
| `QUICKSTART_15MIN.md` | ✅ done | Boot → one loop → read report (Ollama m2.5 + Google variant) |
| `EVALUATION_RUBRIC.md` | ✅ done | 1–5 scores: rigour, novelty, reproducibility, UX |
| `FAQ.md` | ✅ done | "Is this just ChatGPT?" / self-host / data privacy / credits |

### `docs/pilot/` — *Beta program operations*

| File | Status | Purpose |
|------|--------|---------|
| `README.md` | ✅ scaffold | Pilot overview |
| `PILOT_CHARTER.md` | ⬜ todo | Scope, duration (4–6 weeks), what you need from them |
| `ONBOARDING_CHECKLIST.md` | ⬜ todo | Install → status green → sample loop → feedback form |
| `FEEDBACK_FORM.md` | ⬜ todo | Structured questions post-loop |
| `COHORT_TRACKER.md` | ⬜ todo | Who's in, which loop they ran, status |

### `docs/evidence/` — *Proof receipts (the "statistically absurd" folder)*

| File | Status | Purpose |
|------|--------|---------|
| `README.md` | ✅ scaffold | Evidence index |
| `LOOP_29_CASE_STUDY.md` | ⬜ todo | **Priority** — κ_c falsification arc (Loop 29); Loop 23 alternate |
| `OLLAMA_VS_GOOGLE_COMPARISON.md` | ⬜ todo | Side-by-side loop on same problem |
| `VALIDATION_SPRINT_01.md` | ⬜ todo | Direction #2 literature/data check (pass/fail) |
| `VAULT_SNAPSHOT.md` | ⬜ todo | Merkle root + page counts + integrity verify output |

### `docs/investor/` — *Only when you want conversations*

| File | Status | Purpose |
|------|--------|---------|
| `README.md` | ✅ scaffold | "Do not send until pilot has 3+ users" |
| `ONE_PAGER.md` | ⬜ todo | Problem, solution, moat, traction, ask |
| `TRACTION_SNAPSHOT.md` | ⬜ todo | Loops run, pages archived, pilot quotes |
| `USE_OF_FUNDS.md` | ⬜ todo | Reliability, literature agent, 2 hires, etc. |
| `DECK_OUTLINE.md` | ⬜ todo | 10-slide structure (not full deck yet) |

### `evals/` — *Regression + quality gates*

| Item | Status | Purpose |
|------|--------|---------|
| `README.md` | ✅ scaffold | How to run evals |
| `golden_loops.yaml` | ⬜ todo | Loop IDs 7, 14, 23 — expected phases complete |
| `smoke_test.sh` | ⬜ todo | status + dry-run review + mini hypothesis ping |
| `results/` | ✅ dir | Timestamped eval outputs |

### `examples/` — *Stranger-friendly demos*

| Item | Status | Purpose |
|------|--------|---------|
| `README.md` | ✅ scaffold | Pick a demo by time available |
| `5min_status/` | ⬜ todo | `--status` output + screenshot |
| `30min_loop/` | ⬜ todo | Short problem + expected report excerpt |
| `loop_23_showcase/` | ✅ done | Curated excerpts from Loop 23 |
| `loop_29_showcase/` | ⬜ todo | κ_c falsification — **primary peer-review story** |

### `release/` — *Alpha packaging*

| Item | Status | Purpose |
|------|--------|---------|
| `README.md` | ✅ scaffold | Release checklist |
| `ALPHA_CHECKLIST.md` | ⬜ todo | Gate criteria before any external send |
| `CHANGELOG.md` | ⬜ todo | What's new since last tester drop |
| `TESTER_PACKAGE.md` | ⬜ todo | Exactly what files/zips a beta tester gets |

---

## 3. Preparation Phases — Realistic Timeline

### Phase A — Peer Review Pack (Week 1–2)

**Goal:** 5 trusted researchers can evaluate without you on a call.

```
[x] Write QUICKSTART_15MIN.md (Ollama m2.5 + Google API config)
[x] Write HOW_TO_EVALUATE.md + EVALUATION_RUBRIC.md + FAQ.md
[ ] Run Google API loop — same problem as Loop 23 or simpler
[ ] Write OLLAMA_VS_GOOGLE_COMPARISON.md
[ ] Create loop_23_showcase/ (10-page distillation, not raw dump)
[ ] doctor/smoke: boot → 10/10 status → done
[ ] Pick 5 names from outreach/ — send peer-review pack + legal/NDA
```

**Exit criteria:** 3+ evaluators complete a loop and return rubric scores.

---

### Phase B — Pilot Cohort (Week 3–6)

**Goal:** 5–10 beta labs running independently.

```
[ ] Finalise PILOT_CHARTER + ONBOARDING_CHECKLIST
[ ] DocuSign legal/NDA_Beta_Tester_* ready
[ ] COHORT_TRACKER live
[ ] Collaborative review dogfood (1 real doc set)
[ ] VALIDATION_SPRINT_01 (Direction #2 literature pass)
[ ] Move completed loop_*_report.md → docs/loops/ routinely
[ ] Weekly office hours (optional 30min call slot)
```

**Exit criteria:** 5 pilots, ≥3 complete loops each, ≥2 would recommend.

---

### Phase C — Evidence & Credibility (Week 6–10)

**Goal:** External-facing proof, not just internal excitement.

```
[ ] LOOP_23_CASE_STUDY.md polished
[ ] VALIDATION_SPRINT_01 results (pass or honest fail — both publishable)
[ ] VAULT_SNAPSHOT.md with integrity verify command output
[ ] evals/golden_loops.yaml + smoke_test.sh in CI or manual ritual
[ ] Technical brief (6–10 pages) — arXiv-style or PDF in docs/evidence/
[ ] ALPHA_CHECKLIST all green → tag v0.1.0-alpha
```

**Exit criteria:** One shareable URL/folder you'd hand a sceptical professor.

---

### Phase D — Investor-Ready Lite (Week 10+ — optional)

**Goal:** Conversations informed by data, not vibes.

```
[ ] TRACTION_SNAPSHOT with real pilot quotes
[ ] ONE_PAGER.md
[ ] DECK_OUTLINE → slides if you want
[ ] Clear ask: amount, runway, milestones
[ ] 3 case studies in docs/evidence/
```

**Only open this folder when Phase B has real names in COHORT_TRACKER.**

---

## 4. The Three Packages You'll Actually Send

### Package 1 — "Peer Review" (professor / researcher friend)

```
docs/peer-review/README.md
docs/peer-review/QUICKSTART_15MIN.md
docs/peer-review/HOW_TO_EVALUATE.md
legal/NDA_Beta_Tester_Chimera_DocuSign_Ready.txt   (if needed)
examples/loop_23_showcase/
```

### Package 2 — "Beta Pilot" (committed tester)

```
Everything in Package 1, plus:
docs/pilot/PILOT_CHARTER.md
docs/pilot/ONBOARDING_CHECKLIST.md
docs/BOOT_MANUAL.md
release/TESTER_PACKAGE.md
```

### Package 3 — "Investor Intro" (warm intro only)

```
docs/investor/ONE_PAGER.md
docs/evidence/LOOP_23_CASE_STUDY.md
docs/evidence/TRACTION_SNAPSHOT.md   (when exists)
examples/loop_23_showcase/
```

---

## 5. Housekeeping Rules (keep it squeaky)

| Rule | Why |
|------|-----|
| **Live loops** stay as `loop_N_report.md` in root until reviewed | You're still iterating |
| **Approved loops** move to `docs/loops/` | Clean archive for testers |
| **Never send raw 3,500-line reports** | Use `examples/*/showcase` distillations |
| **One `.env.example`** with Google + Ollama blocks | Testers don't guess config |
| **`python3 run_chimera.py --status` must pass 10/10** before any external send | First impression |
| **Investor folder stays closed** until 3+ pilot completions | Traction talks, promises walk |

---

## 6. Immediate Next 5 Actions (this week)

1. **Run Google API loop** — fill Section B in `docs/evidence/OLLAMA_VS_GOOGLE_COMPARISON.md` ⬜
2. **Write `docs/peer-review/QUICKSTART_15MIN.md`** ✅ done 7 Jul 2026
3. **Distil Loop 23** → `examples/loop_23_showcase/README.md` ✅ done 7 Jul 2026
4. **Verify boot** → status snapshot → `examples/5min_status/` ✅ scaffold (re-run at 10/10 before send)
5. **Pick 3 peer reviewers** — drafts in `outreach/PEER_REVIEW_WAVE_01.md` ✅ ready to send when squad green

---

## 7. What You Already Have (don't rebuild)

| Asset | Location |
|-------|----------|
| Full loop proof | `loop_23_report.md` |
| 5,180+ book pages | `data/labs/chimera/scientists/` |
| Legal drafts | `legal/` |
| Outreach lists | `outreach/Trial_Testers_Compiled.md` |
| Competitive analysis | `docs/COMPETITIVE_AUDIT_JULY_2026.md` |
| Boot + ops | `boot_chimera.sh`, `docs/BOOT_MANUAL.md` |
| Collaborative review | `scripts/collaborative_review.py` |

You're not starting from zero. You're **packaging** what exists.

---

## 8. Success Picture (90 days)

```
docs/evidence/          → 3 case studies, 1 validation sprint, 1 model comparison
docs/pilot/             → 5–10 completed cohort rows in COHORT_TRACKER
evals/                  → smoke_test.sh green before every external send
examples/               → stranger runs a loop in <15 min without calling you
docs/investor/          → optional, backed by real quotes
```

That's peer-review ready → pilot proven → investor *credible*. Not "final file and done" — a **living structure** you fill as you go.

---

*Structure created 7 Jul 2026. Update COHORT_TRACKER and CHANGELOG as things move.*