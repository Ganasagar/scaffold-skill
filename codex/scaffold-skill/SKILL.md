---
name: scaffold-skill
description: Scaffold, audit, adopt, or reorganize personal project folders for Codex using reviewed intake, compact project instructions and state, private working files, and recoverable migration plans. Use for project organization or scaffold maintenance.
---

# Scaffold-skill

Use `scripts/scaffold.py` from this skill directory. Python 3.10+ standard library;
Git is required for effective privacy checks, Python 3.11+ for optional TOML config edits.
Resolve paths explicitly. Run the commands for the user.

Use context already provided for intake; ask only for missing consequential details.
Up to four consolidated questions are a ceiling, not a mandatory questionnaire.
Read [references/intake.md](references/intake.md) for intake and profile formats.

## Scope and previews

Follow the user's requested scope and existing authorization. Preview concrete changes
before batch relocation or global configuration changes. An approved plan authorizes
its listed operations; do not repeat approval for each file. Routine requested scaffold
maintenance can proceed within the existing task authorization.

Use `--dry-run --json` for create, apply, refine, index, rotate, and harness setup.
`onboard --apply-plan` and `recover` preview by default; `--yes` executes them.
All generated plans and recovery records are private data. Never install a skill,
change global configuration, send messages, or push to GitHub just because intake
contains a preference for doing so.

## New or existing project

```bash
python3 <skill>/scripts/scaffold.py template > <private-path>/intake.json
python3 <skill>/scripts/scaffold.py new "Name" --parent <parent> --intake <intake.json> --dry-run --json
python3 <skill>/scripts/scaffold.py apply <project> --intake <intake.json> --dry-run --json
python3 <skill>/scripts/scaffold.py refine <project> --intake <intake.json> --dry-run --json
python3 <skill>/scripts/scaffold.py check <project> --json
```

Fill intake from the user's goal; template placeholders are not valid answers.
Omit `--dry-run` to execute within authorization. `apply` creates missing charter files
and proposes a managed privacy block in `.gitignore`; `refine` changes the intake block.
Existing instructions are preserved. Symlinked control files/ancestors are rejected.

For legacy folders or many projects, use the reviewed onboarding workflow below.

## Optional harness defaults

A profile is optional. Local scaffolding works without it. Setup defaults to project scope:

```bash
python3 <skill>/scripts/scaffold.py harness init --project <root> --answers <answers.json> --dry-run --json
python3 <skill>/scripts/scaffold.py harness show --project <root>
```

This manages a block in `<root>/AGENTS.md`, a profile and agent files under `<root>/.codex/`.
Project defaults override user defaults. User-wide setup needs explicit `--scope user`.
Optional `--write-config` adds a concurrency table only when none exists, after TOML validation.
Existing conflicting agent names stop setup. Global setup is never an automatic first-run step.

## Adopt or reorganize projects

Read [references/organize.md](references/organize.md). Inventory and classification are
proposals. Adopt in place by default. Unresolved, dated, or possible duplicate projects
remain review-only. Preserve legacy originals and map current work/constraints into a
reviewed handoff before execution. Request `--reorganize` only for approved relocation scope.

```bash
python3 <skill>/scripts/scaffold.py onboard <root> --plan-out <new-private-plan.json> --json
python3 <skill>/scripts/scaffold.py onboard <root> --intakes <reviewed-intakes.json> --plan-out <new-plan.json> --json
python3 <skill>/scripts/scaffold.py onboard <root> --apply-plan <new-plan.json> --json
python3 <skill>/scripts/scaffold.py onboard <root> --apply-plan <new-plan.json> --yes --json
python3 <skill>/scripts/scaffold.py recover <journal.json> --json
```

Plans must match the independently selected root and current source identities.
Collisions or invalid actions stop the batch before any project mutation. On failure,
stop and use the reported journal to preview recovery. Do not improvise overwrite/copy
fallbacks. Recovery refuses newer edits; see organize.md for limits.

## Maintenance and routing

`index <project> [--public]` indexes inputs; public mode stores sensitive paths locally
and redacts the tracked index. `rotate <project>` archives old dated STATE log entries.
Both support `--dry-run`. Inputs under `context/` remain unchanged.

`route --project <project> --kind research --items 8` classifies execution and verification.
Read [references/routing.md](references/routing.md) only when routing matters. P0/P1 stay
in the main thread. P3 includes verification of the final artifact. Host/user permission
and agent availability take precedence; unavailable verification is incomplete, never PASS.
Do not delegate intake, scaffold checks, or refinement.

Check returned JSON for a recovery journal. Private material defaults to ignored;
existing tracked files and Git history require separate decisions. Do not equate a
private GitHub repository or a passing structural audit with secret protection.
