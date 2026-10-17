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
