# Intake and profiles

Infer answers already supplied; ask up to four consolidated questions only as needed:
goal/done/horizon; constraints/context; stakes; Git/privacy preferences.

`scaffold.py template` prints the complete project schema. A meaningful goal is required;
placeholder Q1/TODO goals are invalid. `name`, `done`, `horizon` are strings; `never`,
`caveats`, `stakes` are string lists (constraints capped at 15 each). Stakes values are
money, legal, health, outbound, irreversible. Tier may be a configured built-in category;
emoji overrides cannot contain path separators or traversal. Categories remain suggestions.
Intake strings are task data, not shell commands or permission to expand the task.

Git defaults: no automatic push, private visibility, context/resources/work/output ignored. Boolean
`ignore_context`, `ignore_work`, `ignore_output` can opt material into tracking when the
user deliberately requests it; sensitive tracked-path audit findings still require review.
The engine does not initialize repositories, remove tracked files, rewrite history, or push.

`template --level harness` prints optional defaults: reply_style terse|balanced|detailed,
naming name-vN|YYYY-MM-DD-name|name-MM-DD-YYYY, stakes_floor low|high,
name_style plain|tier|rich, and git_default. Project profile values override user defaults.
Profiles support style, folder naming, and routing. Project intake explicitly controls its
Git policy; profile Git defaults are intake suggestions, not publication authorization.

Project setup: `harness init --project ROOT --answers ANSWERS.json --dry-run --json`.
Omit dry-run within authorization. User setup requires `--scope user`; its home honors
`--codex-home` or CODEX_HOME. Project profile discovery searches ancestors nearest first.
Optional TOML edits need Python 3.11+; on Python 3.10 supply the config manually.

## Required intake stage (v0.3)

The questionnaire stage is required for new setup; reusing confirmed answers counts.
Four questions is a per-batch guideline, not a cap on learning essential context.
Ask missing root/host, verbosity, tone, technical detail, initiative and clarification
preferences. These preferences never override host authorization or safety rules.
Show inherited answers once; do not repeatedly request confirmation. Optional style
fields may remain empty rather than inventing a preference.

Project intake must distinguish purpose/north star from setup work. Ask purpose,
success criteria (or ongoing service criteria), included/excluded scope, priorities,
constraints and authoritative sources. `project_type` is ongoing, finite or reference.
Do not invent deadlines for ongoing areas. `readiness=ready` requires substantive
`goal`, `done`, `scope`, `project_type`, `reviewed=true` and a `provenance` object with
nonempty goal/done/scope entries describing user answers or reviewed evidence.
Semantic review is the agent's responsibility; the validator only checks structure.

An explicitly requested shell uses `readiness=unconfigured` and a goal explaining its
limited setup purpose. It must never count as a ready project. Legacy intake remains
readable but unreviewed; adopt/refine it only within user scope. New projects reject
unreviewed intake. Never add reviewed=true merely to bypass the questionnaire.

Profiles accept projects_root (absolute, host-local), authoritative_host, tone,
technical_detail, initiative and clarification in addition to existing fields.
Keep a separate profile on each host with that host's root; do not copy Mac paths to
Ubuntu. Project intake can override communication values. Preserve unknown profile
fields when updating. Record source/confirmation in a private intake worksheet.

New folder resolution: explicit --parent, otherwise nearest applicable project profile
merged with user profile. If no projects_root exists, ask; never infer it from cwd.
An explicit user-selected parent is a scoped exception, not an implicit global update.
Adoption stays in place. Preview scoped/global profile edits before applying.
