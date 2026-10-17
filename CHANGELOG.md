# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [0.1.0] - 2026-10-17

### Added
- Codex version of scaffold-skill (`codex/scaffold-skill/`), stdlib-only engine `scripts/scaffold.py`.
- Two-level questionnaires, max 4 questions each: harness (once per machine) and project (every project).
- `harness` command: managed block in `~/.codex/AGENTS.md`, installs `verifier` and `challenger`
  custom agents into `~/.codex/agents/`, optional `[agents]` concurrency cap in `config.toml`.
- `new` / `apply` / `refine`: non-destructive scaffolding with a managed intake block in AGENTS.md.
- Project charter: AGENTS.md (≤60 lines, routing table), STATE.md (`## Now` read every session),
  REFERENCES.md (progressive-disclosure index), SKILLS.md (on-demand procedures), `.gitignore`
  (always `output/` + secrets; `context/` when sensitive).
- `index` (REFERENCES.md stub rows, stale-row detection) and `rotate` (STATE.md log rotation).
- `check`: 9-point audit including Codex's 32 KiB AGENTS.md chain limit.
- `route`: deterministic P0–P3 tiering with agent selection.
- `onboard`: inventory an existing projects root, propose personal tiers, emoji folder names,
  duplicates and migrations; reviewed plan executed with `--apply-plan --yes`, never overwriting.
- Emoji name styles `plain` / `tier` / `rich`; ASCII slug kept for git repo names.
- 19 unittest cases, including a scrub test that blocks work- or harness-specific terms.
