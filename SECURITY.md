# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` branch (pre-release) | ✅ active beta |
| Tagged releases (`v0.1.x`) | ✅ while listed in Releases |

## Reporting a vulnerability

**Do not** open a public GitHub issue for security problems.

Email or message your **GetAiLab beta contact** with:

- Description and impact
- Steps to reproduce
- Affected files / endpoints (e.g. lab dashboard port, Oracle API)
- Your environment (OS, commit hash, deployment mode: native vs Docker)

We aim to acknowledge within **5 business days** during active beta.

## Scope notes

GetAiLab is **self-hosted**. You are responsible for:

- Network exposure of lab ports (default 5024–5040, 5035)
- Protecting `.env` and API keys
- Not exposing the stack to the public internet without authentication

## Safe defaults

- Keep `.env` out of git (see `.gitignore`).
- Run `./scripts/repo_preflight.sh` before any push to catch accidental secret staging.
- Use Docker only with trusted images built from this repo's `Dockerfile`.