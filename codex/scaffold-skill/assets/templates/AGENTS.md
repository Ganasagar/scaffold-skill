# {{TITLE}}
> Harness profile (style, naming, defaults) lives in `~/.codex/AGENTS.md`. Not restated here.

{{INTAKE_BLOCK}}

## Session start — read budget
1. This file.
2. `STATE.md` → `## Now` only. Read Decisions/Log only when the task needs history.
3. `REFERENCES.md` when a task needs inputs; open only the rows the task needs.
4. `SKILLS.md` only when running one of its procedures.

## Folders
- `context/` inputs — read-only. Never edit; derive into `work/`.
- `work/` drafts, data, `claims.md`, verification logs, `archive/`.
- `output/` verified deliverables only. Git-ignored.

## Routing — tokens are not free
| Tier | When | Execution | Verification |
|---|---|---|---|
| P0 | trivial edit, rename, STATE update | main thread | none |
| P1 | low-stakes deliverable | main thread | scripted checks + self-checklist |
| P2 | money · legal · health · outbound · irreversible | main thread builds | spawn `verifier` on `work/claims.md`; REFUTED blocks `output/` |
| P3 | ≥5 like items or ≥3 heavy sources | ≤4 parallel workers, summaries + file paths only | P2 rule on the final artifact |

- High-stakes decision memo → also spawn `challenger`.
- Never spawn agents for P0/P1. "verify", "challenge", "fan out" from the user escalate. Nothing escalates silently.

## Reliability
- Log every load-bearing claim in `work/claims.md`: claim | source | primary/secondary.
- Unsourced claims are marked 🔍 unverified. "Unknown" beats a guess.
- Deterministic checks (recompute numbers, validate dates/links/JSON, compile code) before any LLM check.

## Rules
- Never overwrite a work product: bump the version per harness naming.
- Ask before outbound sends or irreversible operations.
- Files dropped in chat → `context/` + a row in `REFERENCES.md`.
- End of session: update `STATE.md` (Now, Decisions, Log). STATE over 8 KB → `scaffold.py rotate`.
