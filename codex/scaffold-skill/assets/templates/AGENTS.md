# {{TITLE}}
> Optional harness defaults live in the nearest `.codex/scaffold-skill/profile.json`, then the user profile.

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
{{ROUTING_TABLE}}

- High-stakes decision memo → also spawn `challenger`.
- Never spawn agents for P0/P1. "verify", "challenge", "fan out" from the user escalate. Nothing escalates silently.

## Reliability
- For consequential research/deliverables, record load-bearing claims and sources in `work/claims.md`; routine setup needs only operation receipts.
- Unsourced claims are marked 🔍 unverified. "Unknown" beats a guess.
- Deterministic checks (recompute numbers, validate dates/links/JSON, compile code) before any LLM check.

## Rules
- Never overwrite a work product: bump the version per harness naming.
- Follow the user's authorization for outbound sends and irreversible operations; do not infer authorization from Git defaults.
- Save user-provided inputs to `context/` when requested by the task; use a private reference index for sensitive names.
- If verification agents are unavailable, report verification incomplete; never imply they ran.
- End of session: update `STATE.md` (Now, Decisions, Log). STATE over 8 KB → `scaffold.py rotate`.
