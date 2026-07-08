# Changelog

All notable changes to this repository are documented here.  
Format based on [Keep a Changelog](https://keepachangelog.com/). Versioning follows pre-release tags (`v0.1.0-alpha`, etc.).

## [Unreleased]

### Added
- **Builder repo split:** example lab (`boot_example.sh`, 2 scientists), `docs/BUILDER_REPO.md`
- Git repository UX pack: checklist, CI, issue/PR templates, `GITHUB_SETUP.md`
- Galaxy sigil branding on dashboard (header still + animated hero field)
- Per-lab isolation for library, council voices, resonance stats
- `scripts/persona_builder.py` — LLM-assisted lab forge wizard
- `docs/REPOSITORY_CHECKLIST.md` — publish gate for GitHub testers

### Changed
- Public repo scoped to **lab builder** — Chimera personas, vault, outreach, legal, competitive docs removed from git (local moat via `.gitignore`)
- Default `LAB_ID=example`; `enumerate_all_labs()` lists disk configs only
- Docs, dashboard, and CLI copy: accurate dialectic loop description (five stages + intake; four CLI headers; per-stage tickets) — removed misleading "6-phase" marketing
- Dashboard inspiration resonance wired to real per-lab data

## [0.1.0-alpha] — TBD

First tagged alpha for external peer review. Gate: [`release/ALPHA_CHECKLIST.md`](release/ALPHA_CHECKLIST.md).

[Unreleased]: https://github.com/deadlylab/getailab/compare/v0.1.0-alpha...main
[0.1.0-alpha]: https://github.com/deadlylab/getailab/releases/tag/v0.1.0-alpha