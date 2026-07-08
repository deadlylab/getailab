# Contributing to GetAiLab

Thanks for helping shape a self-hosted research operating system. This repo is optimized for **beta testers and peer reviewers** first; code contributions follow the same bar.

## Before you start

1. Read [`README.md`](README.md) and [`docs/peer-review/QUICKSTART_15MIN.md`](docs/peer-review/QUICKSTART_15MIN.md).
2. Copy `.env.example` → `.env` — never commit `.env`.
3. Run `./doctor.sh` after `./boot_example.sh`.

## How to give feedback (preferred for beta)

- **Bug** → [GitHub Issue → Bug report](.github/ISSUE_TEMPLATE/bug_report.yml)
- **Feature / idea** → [Feature request](.github/ISSUE_TEMPLATE/feature_request.yml)
- **Peer review** → `docs/peer-review/EVALUATION_RUBRIC.md` + your notes

Include: OS, Python version, `python3 run_chimera.py --status` output, and relevant log lines from `logs/`.

## Code contributions

1. Fork → branch from `main` (`fix/…`, `feat/…`, `docs/…`).
2. Keep changes focused — one concern per PR.
3. Run `./scripts/repo_preflight.sh` before pushing.
4. If the squad is up: `./evals/smoke_test.sh`.
5. Open a PR using the template.

### Style

- Match existing file layout (`getailab/`, `lab/`, `scientists/`, `scripts/`).
- Python 3.11+; type hints where the surrounding module already uses them.
- No new secrets, no committed loop reports or `lab/artifacts/`.

## Lab Forge / new departments

Use `python3 scripts/create_lab.py` or `python3 run_chimera.py --forge-lab` — see [`docs/LAB_BUILDER.md`](docs/LAB_BUILDER.md). Do not commit another lab's `data/labs/<id>/scientists/` vault bulk.

## Security

See [`SECURITY.md`](SECURITY.md). Do **not** open public issues for undisclosed vulnerabilities.

## Legal

Beta participation is governed by [`legal/Beta_Trial_Terms_and_Conditions.md`](legal/Beta_Trial_Terms_and_Conditions.md).