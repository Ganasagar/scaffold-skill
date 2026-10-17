# v0.2 validation

Local environment: Linux, Python 3.14.4. Repository baseline:
`dda324d088903b726bb5288e43baddb30eb94396`.

Passed:
- 49 unittest methods, including parameterized routing and write-failure cases.
- Python compilation of all runtime/test scripts.
- Bash syntax check of install.sh.
- Codex skill-creator format validator.
- Git diff whitespace validation.
- All six GitHub CI jobs: Linux/macOS × Python 3.10/3.11/3.14.
  Initial matrix run: https://github.com/Ganasagar/scaffold-skill/actions/runs/39077689246

A separate real CLI pilot in disposable folders inventoried five projects: legacy,
existing Codex, nested Git, sensitive inputs, and ambiguous. Four projects were adopted
in place; the ambiguous project remained untouched. All 26 original file hashes were
preserved. Migration recovery preview and execution passed. Installer CLI preview,
installation, uninstall preview, and uninstall passed with no discoverable skill left.
No live home configuration or real projects were modified.

Regression coverage includes unrelated destination collisions, root/schema enforcement,
traversal and symlink rejection, stale sources, whole-batch preflight, preview/content
agreement, recovery after failures at every created charter file, rename failure,
recovery refusing newer edits, cross-device rejection, worktree rejection, unique backups,
legacy handoffs, ambiguous classification, typed intake, effective Git negations and
ancestor rules, already-tracked private material, escaped/redacted indexes, local profiles,
malformed markers/TOML, repeated install, owned upgrade, stale-resource cleanup, uninstall
conflicts, routing combinations, accurate stakes-floor previews, and log rotation boundaries.

Not established by these checks: native custom-agent
discovery/execution, arbitrary external path dependencies, configured Codex instruction
budget overrides, a real production migration, or import completeness. The license is
also an owner release decision, not an implementation test.
