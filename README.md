# scaffold-skill

Codex project setup and maintenance, version 0.3.0. Python 3.10+ standard library; Git is required for effective privacy checks and Python 3.11+ for optional TOML configuration edits.

The skill gathers a project's north star, scope, success criteria and working preferences, resolves its permanent folder, and preserves existing instructions and state. Collection setup tracks filesystem work, saved app projects, sidebar organization and chat placement separately. A folder alone does not establish a registered Codex project or cross-device handoff readiness.

## Install

Clone this repository, then preview a project-scoped installation:

```bash
python3 codex/scaffold-skill/scripts/install_skill.py --project /absolute/project --dry-run
python3 codex/scaffold-skill/scripts/install_skill.py --project /absolute/project
```

For an explicitly chosen user-wide installation, replace `--project /absolute/project` with `--scope user`. Restart Codex to refresh skill discovery. The installer tracks owned files and refuses to overwrite an unowned or locally modified installation. Review existing installations before replacement. The legacy `install.sh` remains available for copy/symlink installs with a timestamped backup; it does not provide ownership tracking.

## Usage

Ask Codex to use scaffold-skill to set up, audit, adopt or organize a project. It reuses confirmed answers and asks for missing consequential details, including communication preferences and project objectives. Full setup follows [the setup workflow](codex/scaffold-skill/references/setup.md).

For direct CLI use:

```bash
python3 codex/scaffold-skill/scripts/scaffold.py template
python3 codex/scaffold-skill/scripts/scaffold.py new "Project Name" --parent /absolute/projects --intake /private/intake.json --dry-run --json
python3 codex/scaffold-skill/scripts/scaffold.py check /absolute/projects/project-name --json
```

Populate the intake using [the intake schema](codex/scaffold-skill/references/intake.md). New projects require reviewed substantive intake or an explicit unconfigured placeholder. A configured `projects_root` can replace `--parent`; the current directory is never the implicit permanent destination. Omit `--dry-run` to apply an authorized preview.

Existing projects use `apply` to add missing control files and `refine` to update managed intake. User instructions and historical state remain available. The standard charter comprises AGENTS.md, STATE.md, REFERENCES.md and SKILLS.md, with private work and context separated from deliverables. Optional harness configuration defaults to project scope; use explicit user scope for global settings.

## Collection and app setup

- [Organization and reviewed migration](codex/scaffold-skill/references/organize.md)
- [Saved projects, sidebar sections and chats](codex/scaffold-skill/references/app-integration.md)
- [Cross-device migration readiness](codex/scaffold-skill/references/migration-readiness.md)
- [Task routing](codex/scaffold-skill/references/routing.md)

`discover` reports bounded folder coverage. `setup template` produces a manifest and `setup check --manifest PATH --json` checks its evidence contract. It cannot independently authenticate self-reported evidence. `repo-check PATH --json` checks Git health but does not certify app handoff readiness. Use command `--help` for options.

Folder relocation requires a concrete reviewed plan. App changes use supported tools or UI, with readback. Missing capabilities and incomplete inventories remain visible as pending or blocked work. Filesystem scaffolding does not authorize messaging, GitHub publishing, database edits or cross-device synchronization.

## Development and validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s codex/scaffold-skill/scripts -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s codex/scaffold-skill/tests -v
```

The 38 automated tests cover local scaffold behavior, preservation, intake validation, destination selection, setup evidence, inventory limits and repository checks. Full interactive app setup and migration acceptance testing remains pending. No test result should be presented as proof that real projects or chats were registered or migrated.

See [CHANGELOG.md](CHANGELOG.md) for changes and [SKILL.md](codex/scaffold-skill/SKILL.md) for the agent entry point.
