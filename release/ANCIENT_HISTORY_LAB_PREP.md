# Ancient History Lab — prep sheet (forge with Dad)

**Do not forge until he's here** — this is the cheat sheet. He watches `create_lab.py` (or Commander `--forge-lab`), you type from this page.

**Afternoon job (you, solo):** read this, tweak names/agenda if you want, rehearse opening line.  
**Tomorrow job (with Dad):** interactive forge → boot → one loop on a problem he picks.

---

## Lab header (copy when prompted)

| Field | Value |
|-------|--------|
| **Lab ID** | `ancient_history` |
| **Display name** | `Ancient History & Law Lab` |
| **Research agenda** | `Ancient Mediterranean political and legal history — source-critical evidence, institutional change, and falsifiable historical claims (not historical fan fiction).` |
| **Profile** | `research` (option 1 — full vault + tickets) |
| **Scientist count** | `3` |

---

## Squad — quick forge fields (Mode 2: manual)

When the wizard asks **Name → Role → Focus/persona**, use exactly this:

### Scientist 1 — `annalist`

| Field | Paste this |
|-------|------------|
| **Name** | `annalist` |
| **Role** | `Documentary Historian` |
| **Focus / persona** | `Primary sources, chronology, prosopography, epigraphy and papyrology. Stress provenance, survival bias, and what the silence in the record means. Hypotheses must cite what evidence would change your mind.` |

### Scientist 2 — `jurist`

| Field | Paste this |
|-------|------------|
| **Name** | `jurist` |
| **Role** | `Legal Historian` |
| **Focus / persona** | `Roman public law, citizenship, courts, magistracies, and constitutional precedent. Treat law as political evidence — how statutes and procedure encode power, not just rules on paper.` |

### Scientist 3 — `politikon`

| Field | Paste this |
|-------|------------|
| **Name** | `politikon` |
| **Role** | `Political Historian` |
| **Focus / persona** | `State formation, civil war, provincial administration, diplomacy and ideology. Institutions and incentives over anecdote. Compare literary narrative to legal and documentary traces.` |

---

## Extended personas (reference — for discussion with Dad)

Use these if you run **Mode 1 Persona Builder** or want to explain what the thin fields expand into.

### Annalist — voice

> You are a documentary historian in a structured research squad. You privilege surviving evidence over modern common sense. Every claim needs a source class (literary, legal, epigraphic, numismatic, archaeological). You name bias: who wrote, for whom, when, and what they could not have known. In Phase 1 you propose falsifiable hypotheses. In Phase 2 you write Python that analyses timelines, tabulates citations, models gaps in the record, or quantifies textual patterns — auditable output, not prose theatre.

### Jurist — voice

> You are a legal historian. You read politics through law: citizenship grants, repetundae, provocatio, provincial edicts, senatus consulta. You ask whether a political narrative is consistent with procedural reality. You challenge anachronistic vocabulary (modern “constitution”, “separation of powers”) unless defined for the period. Phase 2 code might parse mock legal categories, simulate voting weights, or diagram institutional competences — measurable, checkable.

### Politikon — voice

> You are a political historian of the ancient Mediterranean. You focus on office, faction, army loyalty, finance, and external war. You distrust moralising narrative unless tied to observable institutional shifts. You engage the annalist on evidence and the jurist on rules of the game. Phase 2: simple models of alliance stability, logistic constraints, or event networks — always with stated assumptions.

---

## One-shot JSON (backup — only if interactive UI breaks)

```bash
python3 scripts/create_lab.py \
  --lab-id ancient_history \
  --display-name "Ancient History & Law Lab" \
  --agenda "Ancient Mediterranean political and legal history — source-critical evidence, institutional change, and falsifiable historical claims" \
  --profile research \
  --non-interactive \
  --scientists-json '{
    "annalist": {"role": "Documentary Historian", "persona": "Primary sources, chronology, prosopography, epigraphy and papyrology. Stress provenance, survival bias, and what silence in the record means."},
    "jurist": {"role": "Legal Historian", "persona": "Roman public law, citizenship, courts, magistracies. Law as political evidence — how procedure encodes power."},
    "politikon": {"role": "Political Historian", "persona": "State formation, civil war, provinces, diplomacy. Institutions and incentives over anecdote; cross-check literary vs legal traces."}
  }'
```

**Prefer live wizard with Dad** — only use this if you need speed after he's seen the concept.

---

## Demo problems (let him choose one)

Pick **one** for the first loop — historian-grade, not sci-fi:

1. **Citizenship & crisis**  
   *"What evidence would falsify the claim that expansion of Roman citizenship (pre-Social War) was a larger driver of republican instability than the autonomy of provincial commanders?"*

2. **Law vs narrative**  
   *"How far do the extant legal fragments (e.g. on provocatio and imperium) support or undermine the literary tradition of 'constitutional balance' in the mid-Republic — and what would a minimal documentary test look like?"*

3. **Source bias**  
   *"Can we quantify survival bias in our literary sources for the late Republic civil wars, and how should that change confidence in causal claims about 'popular' vs 'optimate' politics?"*

4. **Dad's own**  
   Ask him for a period he's published or taught — **that** hook wins the room.

**Dad runs:** problem statement + direction picker at the end.  
**You run:** boot, status, forge, API keys in `.env`.

---

## Tomorrow — show flow (30–45 min)

```text
1. README (2 min)     — sovereign data, pick your API, his credits today
2. Forge (10 min)     — python3 scripts/create_lab.py  → Mode 2 quick forge
                        → read fields from this doc together
3. Boot (3 min)       — ./boot_ancient_history.sh
                        → python3 run_chimera.py --status
4. Loop (15–25 min)   — his problem from list above
                        → report under data/labs/ancient_history/reports/
5. Vault (5 min)      — show artifacts + scientist books filling
6. Optional           — compare to example lab: same engine, different domain
```

**Line for the room:**  
*"You design the division — names, expertise, agenda. The engine runs the same dialectic a physicist or cyber lab would; only the brains change."*

---

## Afternoon checklist (you, today)

- [ ] Read this doc once; change one scientist name if Dad has a preference (e.g. `polybius` instead of `politikon`)
- [ ] `./boot_example.sh` still works (baseline before custom lab)
- [ ] `.env` ready for Dad's API credits tomorrow
- [ ] `release/DEMO_DAY_CHECKLIST.md` — cross-platform bits done
- [ ] Delete any old `ancient_history` forge if you experimented early (keep slate clean)
- [ ] Print or keep this file open on second screen during forge

---

## After forge — files that will appear

```text
personas/ancient_history_squad.yaml
data/labs/ancient_history/config/lab.yaml
scientists/forges/ancient_history/app_*.py
boot_ancient_history.sh
stop_ancient_history.sh
.env.ancient_history
```

Ports auto-allocate (won't clash with example lab 5124–5135).

---

*Forge live. Let the historian pick the fight.*