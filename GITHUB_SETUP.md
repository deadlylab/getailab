# GitHub Setup — Push GetAiLab for Testing

One-time guide to publish this repo and let testers clone from GitHub.

## Prerequisites

- [Git](https://git-scm.com/) installed
- [GitHub account](https://github.com/)
- Optional: [GitHub CLI](https://cli.github.com/) (`gh`)

## 1. Preflight (local)

```bash
cd getailab_live
./scripts/repo_preflight.sh
```

Fix any **FAIL** lines before continuing.

## 2. Initialise git (first time only)

Already done if `.git/` exists:

```bash
git init -b main
git add .
git status    # confirm: no .env, no *.db, no loop_*_report.md
git commit -m "chore: initial GetAiLab repository for beta testing"
```

## 3. Create the GitHub repository

### Option A — GitHub website

1. Go to [github.com/new](https://github.com/new)
2. Name: `getailab` (or `getailab-live`)
3. **Private** recommended for beta (add testers as collaborators)
4. Do **not** add README, .gitignore, or license (we already have them)
5. Create repository

### Option B — GitHub CLI

```bash
gh auth login
gh repo create getailab --private --source=. --remote=origin --push
```

## 4. Push

```bash
git remote add origin git@github.com:deadlylab/getailab.git
# or HTTPS: https://github.com/deadlylab/getailab.git

git push -u origin main
```

## 5. Repository settings (recommended)

In **Settings → General**:

| Setting | Value |
|---------|--------|
| Description | Self-hosted multi-agent research lab — dialectic loops, Oracle synthesis, signed vault |
| Website | (optional) your docs URL |
| Topics | `research`, `multi-agent`, `ollama`, `python`, `science`, `self-hosted` |

In **Settings → Actions → General**: allow Actions.

In **Settings → Branches** (optional but good):

- Add rule for `main`
- Require status check: **CI / import-check**

## 6. Invite testers

**Private repo:** Settings → Collaborators → Add people.

Share with testers:

```
git clone git@github.com:deadlylab/getailab.git
cd getailab
cp .env.example .env
pip install -r requirements.txt
./boot_chimera.sh
./doctor.sh
```

Full path: [`docs/peer-review/QUICKSTART_15MIN.md`](docs/peer-review/QUICKSTART_15MIN.md)

## 7. First release tag (when alpha gate is green)

```bash
# Gate: release/ALPHA_CHECKLIST.md
git tag -a v0.1.0-alpha -m "First alpha for peer review"
git push origin v0.1.0-alpha
```

Then GitHub → **Releases → Draft new release** from tag `v0.1.0-alpha`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Permission denied (publickey)` | Add SSH key to GitHub, or use HTTPS remote |
| Push rejected (large files) | Run `./scripts/repo_preflight.sh`; remove `data/labs/*/scientists/` from index |
| CI fails on import | `pip install -r requirements.txt` locally; fix missing module |
| Accidentally committed `.env` | `git rm --cached .env`, rotate keys, amend commit |

See also: [`docs/REPOSITORY_CHECKLIST.md`](docs/REPOSITORY_CHECKLIST.md)