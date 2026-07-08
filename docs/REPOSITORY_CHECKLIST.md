# Git Repository UX Checklist

What a **tester-friendly, contributor-ready** GetAiLab repository needs — and where each item lives in this repo.

Use this before every external send or GitHub publish. Run `./scripts/repo_preflight.sh` for an automated pass.

---

## 1. First impression (60 seconds)

| Item | Why it matters | Status | Location |
|------|----------------|--------|----------|
| Clear project name + one-line pitch | Visitors know what they're looking at | ✅ | `README.md` header |
| Status badge row (build, license, docs) | Trust at a glance | ✅ | `README.md` |
| Hero screenshot or architecture diagram | Visual anchor | ⬜ optional | `docs/assets/` (add when ready) |
| License file | Legal clarity for forks/clones | ✅ | `LICENSE` |
| Short “who is this for?” | Sets expectations | ✅ | `README.md` → Scope |

---

## 2. Clone → run (15 minutes)

| Item | Why it matters | Status | Location |
|------|----------------|--------|----------|
| Prerequisites listed | No mystery deps | ✅ | `README.md` + `docs/BOOT_MANUAL.md` |
| `.env.example` with comments | Safe copy-paste setup | ✅ | `.env.example` |
| One-command boot | Lowest friction path | ✅ | `./boot_example.sh` |
| One-command health check | “Is it working?” | ✅ | `./doctor.sh` |
| Cross-platform installers | Windows/Mac/Linux testers | ✅ | `Install-GetAiLab-*` |
| Smoke test script | Pre-send validation | ✅ | `evals/smoke_test.sh` |
| Peer-review quickstart | External evaluators | ✅ | `docs/peer-review/QUICKSTART_15MIN.md` |

---

## 3. Repository hygiene

| Item | Why it matters | Status | Location |
|------|----------------|--------|----------|
| `.gitignore` — secrets | Never commit `.env`, keys, DBs | ✅ | `.gitignore` |
| `.gitignore` — generated artifacts | Repo stays cloneable (<100 MB) | ✅ | `.gitignore` |
| `.gitattributes` — line endings | Windows/Mac/Linux diffs clean | ✅ | `.gitattributes` |
| Root `requirements.txt` | Single `pip install` entry | ✅ | `requirements.txt` |
| No committed runtime vault bulk | Fresh clone = fresh lab | ✅ | `data/labs/README.md` |
| Preflight script before push | Catch leaks early | ✅ | `scripts/repo_preflight.sh` |

---

## 4. Developer & contributor experience

| Item | Why it matters | Status | Location |
|------|----------------|--------|----------|
| `CONTRIBUTING.md` | How to report bugs, PR flow | ✅ | `CONTRIBUTING.md` |
| Issue templates | Structured bug/feature reports | ✅ | `.github/ISSUE_TEMPLATE/` |
| Pull request template | Reviewers get context | ✅ | `.github/pull_request_template.md` |
| `CODE_OF_CONDUCT.md` | Community baseline | ✅ | `CODE_OF_CONDUCT.md` |
| Architecture / operation docs | Deep dive without reading code | ✅ | `docs/OPERATION_MANUAL.md` |
| Scripts README | Utility discovery | ✅ | `scripts/README.md` |

---

## 5. Security & trust

| Item | Why it matters | Status | Location |
|------|----------------|--------|----------|
| `SECURITY.md` | Responsible disclosure path | ✅ | `SECURITY.md` |
| No API keys in history | Rotate if ever leaked | ✅ | preflight checks |
| Beta/legal terms linked | Trial scope clear | ✅ | `legal/` |
| Dependency pinning | Reproducible installs | ✅ | `lab/requirements.txt` |

---

## 6. CI / GitHub Actions

| Item | Why it matters | Status | Location |
|------|----------------|--------|----------|
| CI on push + PR | Broken main caught early | ✅ | `.github/workflows/ci.yml` |
| Import / syntax gate | No boot required in CI | ✅ | workflow `import-check` job |
| Optional full smoke (self-hosted) | Post-merge squad check | ⬜ later | label `full-smoke` runner |
| Branch protection (main) | Require CI green | ⬜ GitHub settings | see `GITHUB_SETUP.md` |

---

## 7. Releases & versioning

| Item | Why it matters | Status | Location |
|------|----------------|--------|----------|
| `CHANGELOG.md` | What changed between tags | ✅ | `CHANGELOG.md` |
| Semantic version tags | `v0.1.0-alpha` etc. | ⬜ on release | `git tag` |
| Alpha gate checklist | Don’t ship half-ready | ✅ | `release/ALPHA_CHECKLIST.md` |
| GitHub Release notes | Testers download a known build | ⬜ on first tag | GitHub Releases UI |

---

## 8. GitHub repository settings (manual)

Do these in the GitHub UI after first push — see [`GITHUB_SETUP.md`](../GITHUB_SETUP.md).

- [ ] Description: *Self-hosted multi-agent research lab*
- [ ] Topics: `research`, `multi-agent`, `ollama`, `python`, `science`
- [ ] Default branch: `main`
- [ ] Actions enabled
- [ ] Issues enabled
- [ ] Wiki disabled (docs live in-repo)
- [ ] Branch protection on `main` (require CI)
- [ ] Optional: GitHub Discussions for beta feedback

---

## 9. Pre-push gate (you)

```bash
./scripts/repo_preflight.sh    # must pass
git status                     # no .env, no *.db, no loop_*_report.md staged
./doctor.sh                    # optional — if squad is running locally
```

---

## 10. Post-publish smoke (tester simulates)

```bash
git clone git@github.com:deadlylab/getailab.git
cd getailab
cp .env.example .env
pip install -r requirements.txt
./boot_example.sh
./doctor.sh
python3 run_chimera.py --status   # example lab: lab + oracle + 2 scientists when Ollama + models ready
```

---

*Maintained for GetAiLab — CryptO'Brien Pty Ltd.*