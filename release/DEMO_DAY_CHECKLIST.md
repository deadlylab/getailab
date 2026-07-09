# Demo day preflight — afternoon checklist

**For:** Dad visit tomorrow (API credits) + cross-platform sanity before showing the goods.  
**You:** Linux native demo · **Nephew:** Windows `.bat` trial · **Mac:** later (VM)

Tick boxes as you go. Target: **~2–3 hours** this arvo if labs are mostly healthy.

---

## 0 — Before you sit down (already doing this ✅)

- [ ] Laundry / garden / sun — done, head clear
- [ ] Phone on silent for the preflight block
- [ ] Glass of water, laptop charged

---

## 1 — Kill stale processes (5 min)

Old Chimera/rf_research Pythons love to hog ports.

```bash
cd /path/to/getailab_live   # or fresh clone path
pkill -f 'python3.*app_' 2>/dev/null || true
./stop_example.sh 2>/dev/null || true
# local only if you use them:
# ./stop_rf_research.sh  ./stop_chimera.sh
fuser -k 5124/tcp 5135/tcp 5125/tcp 5126/tcp 2>/dev/null || true
ss -tlnp | grep -E ':51(2[4-9]|3[0-5])\b'   # should be empty
```

- [ ] Ports 5124–5135 clear (example lab block)

---

## 2 — Fresh clone test — Linux (20 min)

Proves GitHub works for a stranger (nephew/Dad path).

```bash
cd /tmp   # or ~/test
rm -rf getailab-fresh-test
git clone git@github.com:deadlylab/getailab.git getailab-fresh-test
cd getailab-fresh-test
cp .env.example .env
# paste YOUR keys into .env only on this machine — never commit
./Install-GetAiLab-Linux.sh    # or: pip install -r requirements.txt
./boot_example.sh
./doctor.sh
LAB_ID=example python3 run_chimera.py --status
```

**Pass criteria:**

- [ ] Clone OK (SSH or HTTPS)
- [ ] `doctor.sh` green enough (Ollama warn OK if using cloud tomorrow)
- [ ] Status: `lab` active, `oracle` + `researcher` + `critic` healthy
- [ ] Dashboard http://localhost:5135 loads

**Optional — Docker path:**

```bash
./docker.sh build    # slow first time; skip if short on time
./docker.sh up
./docker.sh status
```

- [ ] Docker example lab healthy (optional)

---

## 3 — Your live workspace vs public repo (10 min)

| Check | Command / action |
|-------|------------------|
| Git clean for demo | `git status` — no accidental `.env` staged |
| Preflight | `./scripts/repo_preflight.sh` |
| Public face | Open README on GitHub — sovereign + provider links look right |
| Moat not leaked | `git ls-files \| grep -i chimera` → should be **code paths only**, not squad yaml |

- [ ] `repo_preflight.sh` PASSED
- [ ] Happy showing Dad **GitHub repo**, not `getailab_live` moat folder

---

## 4 — Labs to demo tomorrow (15 min)

**Primary (shipped):** example lab — always works from repo.

```bash
cd getailab-fresh-test   # or your live tree with LAB_ID=example
./boot_example.sh
python3 run_chimera.py --status
```

- [ ] Example lab boot + status 4/4

**Secondary (local only, optional wow):** your forged / legacy lab if Dad asks “can it scale?”

```bash
# only if boot scripts exist locally (not on GitHub):
# ./boot_rf_research.sh  OR  ./boot_chimera.sh
# source .env.<lab_id>
# python3 run_chimera.py --status
```

- [ ] Know which local lab you’ll mention vs which is on GitHub
- [ ] Forge demo ready: `python3 scripts/create_lab.py --list-labs`

---

## 5 — API credits prep for tomorrow (10 min)

Dad loads you up — **decide the stack tonight**, not in front of him.

Edit `.env` (local only):

```bash
# Pick ONE primary for tomorrow's demo loop:
LLM_PROVIDER=openai          # or google / anthropic
OPENAI_API_KEY=sk-...        # Dad's credits
LLM_MODEL=gpt-4o             # or agreed model
SCIENTIST_HTTP_TIMEOUT=600
```

**Smoke one short call before bed (optional):**

```bash
python3 run_chimera.py --status
python3 run_chimera.py --problem "Quick smoke: one falsifiable hypothesis about battery degradation in WA heat."
# or --chat for 1 scientist reply
```

- [ ] `.env` has provider + key (not committed)
- [ ] One scientist responds without HTTP/timeout errors
- [ ] Note spend cap / model choice to discuss with Dad

**Sovereign story for Dad:** “Default is local Ollama; today we’re using your credits on [provider] to show speed — same engine either way.”

---

## 6 — Windows trial — nephew (30–45 min, can be tonight or tomorrow)

Send him **only the public repo**:

```
git clone https://github.com/deadlylab/getailab.git
cd getailab
```

On his machine:

1. `Install-GetAiLab-Windows.bat` (double-click or right-run)
2. Copy `.env.example` → `.env` (your cloud key or his Ollama)
3. `Boot-GetAiLab-Windows.bat`
4. Browser → http://localhost:5135
5. In PowerShell: `python run_chimera.py --status`

**Nephew pass criteria:**

- [ ] Install completes without manual pip surgery
- [ ] Dashboard loads
- [ ] Status shows example scientists healthy
- [ ] Screenshot sent to you (proof for Dad story)

**If Windows fights you:** WSL2 + Linux install path is plan B — note what broke.

---

## 7 — Demo script for Dad (write on a sticky note)

**15-min version:**

1. README — sovereign data, pick your API
2. `./boot_example.sh` → dashboard
3. `run_chimera.py --status`
4. One loop OR pre-baked report from `data/labs/example/reports/` if loop is slow
5. Lab Forge — `create_lab.py` menu (30 sec, don’t need to finish forge)
6. GitHub — “this is what we ship; my research vault stays local”

**Talking points:**

- Local-first; his credits = optional accelerator
- Not a chatbot — ticketed research method
- WA / grant / Alex Jenkins angle only if he bites

- [ ] Demo order rehearsed once out loud
- [ ] Backup: screen recording or status JSON if live loop tanks

---

## 8 — Park for later

- [ ] Mac — `Install-GetAiLab-Mac.command` in VM when time
- [ ] Alex Jenkins outreach — after Dad + nephew runs green
- [ ] Loop 29 showcase / evidence docs — not blocking tomorrow

---

## Quick reference

| What | Port / URL |
|------|------------|
| Dashboard | http://localhost:5135 |
| Oracle | http://localhost:5124/health |
| GitHub | https://github.com/deadlylab/getailab |
| Peer review | `docs/peer-review/QUICKSTART_15MIN.md` |

---

*Smash chores. Smash checklist. Show the old man something real.* 🌿