# scaffold-skill

Personal project scaffolding for Codex: a compact project charter, current state,
references, private working files, and reviewed adoption of existing projects.

Version **0.2.0**. Python 3.10+ standard library; Git for effective ignore audits.
Optional automatic TOML configuration edits require Python 3.11+.

## Install

Clone this repository, then preview a project-scoped installation:

```bash
./install.sh --project /absolute/path/to/project --dry-run
./install.sh --project /absolute/path/to/project
```

The skill goes into PROJECT/.agents/skills/scaffold-skill. Reload/restart the Codex
session to refresh discovery. User-wide installation is an explicit choice:

```bash
./install.sh --scope user --dry-run
./install.sh --scope user
```

Installation does not initialize a harness or change Codex global configuration.
The previous --link mode and SKILLS_DIR override are removed: installations are owned
copies with manifests. Existing unowned installations are rejected; archive them outside
all skill discovery directories after reviewing their contents. An overlapping
workspace-scaffold skill is reported so you can choose one.

Rerun the same command to upgrade. Unchanged owned files are updated; user modifications
or unowned collisions stop the upgrade. Backups and write journals stay outside skill
discovery. Uninstall also previews first and refuses user edits:

```bash
./install.sh --project /absolute/path/to/project --uninstall --dry-run
./install.sh --project /absolute/path/to/project --uninstall
```

Uninstall removes only owned skill files; it does not remove optional harness instructions,
profiles, or agents. Those changes have their own recovery journal. Review its recovery
preview if you also want to undo setup. Private backups and journals are retained.

## Use

Ask Codex to use scaffold-skill to start a project, adopt an existing folder, check its
structure, or propose a reorganization. It uses your supplied context for intake and
asks only for missing consequential details. A global questionnaire is not required.

Projects use AGENTS.md, STATE.md, REFERENCES.md, SKILLS.md and context/work/output folders.
Context, legacy resources, working files, outputs, private scaffold metadata, and credentials default to
ignored. Git policy changes are shown as a managed block; existing user rules are retained.
No command creates a GitHub repository or pushes automatically.

For direct CLI use, replace SKILL below with the installed skill directory:

```bash
python3 SKILL/scripts/scaffold.py template > /private/path/intake.json
# Fill the meaningful goal, constraints, stakes, and Git policy.
python3 SKILL/scripts/scaffold.py apply /path/to/project --intake /private/path/intake.json --dry-run --json
python3 SKILL/scripts/scaffold.py apply /path/to/project --intake /private/path/intake.json --json
python3 SKILL/scripts/scaffold.py check /path/to/project --json
```

Returned JSON includes recovery journal paths for scaffold writes. Other commands:
new, refine, index, rotate, route, harness, onboard, recover. Use COMMAND --help.
Profiles are optional: `harness init --project ROOT --answers ANSWERS --dry-run` previews
project defaults and custom-agent installation. User-wide setup needs `--scope user`.
Read [intake](codex/scaffold-skill/references/intake.md) for schemas and precedence.

## Existing projects

Default to adoption in place; physical moves are a separate explicit proposal.

```bash
python3 SKILL/scripts/scaffold.py onboard /projects --plan-out /private/path/inventory.json --json
# Review each project's source files; build reviewed-intakes.json.
python3 SKILL/scripts/scaffold.py onboard /projects --intakes /private/path/reviewed-intakes.json --plan-out /private/path/adoption.json --json
python3 SKILL/scripts/scaffold.py onboard /projects --apply-plan /private/path/adoption.json --json
python3 SKILL/scripts/scaffold.py onboard /projects --apply-plan /private/path/adoption.json --yes --json
```

Add --reorganize during proposal generation only when moves are intended. Missing
intake, ambiguity, dated folders, and duplicate hints leave projects review-only.
Legacy knowledge must be reviewed; original instructions/state remain available.
Old 0.1 unversioned migration plans are rejected: regenerate them.

Read the [migration and recovery guide](codex/scaffold-skill/references/organize.md)
for the intake map, versioned plan, preflight checks, and conflict-aware recovery.
`recover JOURNAL` previews; `--yes` performs recovery. Never edit a journal to force
recovery over newer work. Plans and journals are trusted private local artifacts.

## Privacy and verification

Git audits evaluate actual ignore behavior, including negations and ancestor rules,
and report already-tracked private paths without untracking them or rewriting history.
Without Git, protection is explicitly unverified. The audit does not inspect history or
replace a secret scan. A private repository does not make credentials safe to commit.

`index ROOT --public` moves the detailed index to private local metadata and replaces
REFERENCES.md with a redacted pointer. It does not scrub prior Git history. Ordinary
index mode escapes unusual filenames and includes context/resources/legacy references.

Routing uses P0/P1 for main-thread work, P2 verification for high-stakes artifacts, and
P3 workers plus final verification for larger tasks. High-stakes decisions also use a
challenger. [Routing details](codex/scaffold-skill/references/routing.md).
Missing agents leave verification incomplete. Reviewers inherit parent permissions;
read-only behavior is an instruction, not an independent sandbox.

## Limits and compatibility

- File replacement is atomic; multi-project migrations are journaled and recoverable,
  not atomic. Concurrent external edits or hostile filesystem races are unsupported.
- Symlinked migration paths and control files, cross-filesystem moves, worktree relocation,
  and detected infrastructure dependencies require manual handling. Ordinary standalone
  repositories can move; external path references still require review.
- Category recognition is heuristic and currently uses configurable naming styles with
  built-in personal categories. Edit reviewed plan destinations inside the allowed root
  rather than treating category hints as authoritative.
- Instruction-budget checks are estimates using default discovery/budget assumptions;
  configuration overrides are not fully resolved.
- Filesystem behavior has been tested locally on Linux with Python 3.14. CI covers
  Python 3.10/3.11/3.14 on Linux and macOS; CI success must be checked separately.
- Agent schema/config documentation was checked against Codex CLI 0.163.0. Native custom
  agent discovery is not exercised by unit tests; validate it in a disposable host session.
- License selection remains pending with the repository owner; no license is implied by
  public hosting. Additional harnesses, cloud sync, and automatic publishing are deferred.

## Development

```bash
python3 -m unittest discover -s codex/scaffold-skill/scripts -v
python3 -m py_compile codex/scaffold-skill/scripts/*.py
```

The runtime uses only the standard library. Tests isolate all mutations in temporary
folders and cover preflight, drift, collisions, boundaries, failure recovery, legacy
handoff, Git privacy, routing, and installation ownership.

[Implementation plan and release scope](docs/implementation-plan-v0.2.md).
