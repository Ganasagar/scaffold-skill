# Reviewed onboarding and recovery

## Inventory first

`onboard ROOT --json` is read-only. `--plan-out NEW.json` explicitly writes a private,
exclusive new plan file. Do not reuse a filename or publish plans: they include local
paths, source hashes, and reviewed intake. Keep plans outside the projects being adopted.

Inventory examines immediate folders and one level inside known category folders.
Symlinked project folders are skipped; symlinked control files are rejected. Category
keywords are hints. Matching slugs are duplicate hints; matching instruction templates
alone never prove duplicates. IDs use full relative paths.

Read each project's `knowledge_sources` and complete its worksheet. Retain the goal,
constraints, decisions, next actions, and source paths in reviewed intake/handoff notes.
Never infer permission for future sends, GitHub pushes, or global changes from old files.

## Reviewed intake map

Create a private JSON object keyed by paths relative to ROOT:

```json
{
  "award-travel": {
    "reviewed": true,
    "handoff_reviewed": true,
    "intake": {
      "goal": "Compare award tickets for the spring trip",
      "done": "A sourced shortlist is ready",
      "never": ["Do not transfer points without explicit authorization"],
      "caveats": ["See MEMORY.md for the current airline shortlist"],
      "stakes": ["money"],
      "git": {"push": false, "visibility": "private", "ignore_context": true}
    },
    "now": ["Compare the existing shortlist in MEMORY.md with current schedules"]
  }
}
```

Legacy CLAUDE/MEMORY projects require `handoff_reviewed` and current actions. New
AGENTS.md links the originals; existing AGENTS.md gains a managed legacy bridge.
Existing STATE.md is retained, so inspect it during handoff review. Other original
files are retained. Ambiguous projects stay in place; clarify their purpose/metadata
and regenerate the inventory rather than forcing an Unsorted move.

Generate with `onboard ROOT --intakes INTAKES.json --plan-out NEW.json`. Add
`--reorganize` only when physical relocation is intended. Plain/tier/rich naming remains
available through `--name-style`. Customize the reviewed destination inside ROOT if needed.
Do not edit source identities to bypass stale-plan checks: regenerate and review instead.

## Apply

`onboard ROOT --apply-plan NEW.json --json` previews exact planned file contents.
Add `--yes` after review. Old unversioned plans are rejected. The executor preflights
all actionable projects, including full source file hashes and expected destinations.
A source is tied to its adoption operation; a skipped move can never trigger conversion
of an existing destination. Relocations reject collisions, nested operation paths,
worktree Git files, detected service/path dependencies, symlinks, and filesystem boundaries.
Ordinary standalone Git repositories can move on the same filesystem; review any external
scripts, deployments, or links that reference their old paths. Dependency detection is
heuristic and cannot establish that every external reference is safe.

## Recovery

Write commands create private `.scaffold-skill/transactions/<id>/journal.json` records.
Migration journals are under `ROOT/.scaffold-skill/migrations/<id>/journal.json`.
`recover JOURNAL --json` preflights recovery; add `--yes` to execute. Keep recovery data
until the migration and resulting work have been reviewed and backed up.

Recovery restores original file bytes/permissions, removes only owned created files,
and reverses completed moves. It refuses conflicting newer edits or changed project
content. Save those edits elsewhere and review manually; never force an overwrite.
Private transaction records are retained for audit; empty scaffold directories may remain.
Backups of index, rotation, profile, config, and instruction edits use unique names.

Single-file replacement is atomic. A multi-project batch is journaled, not atomic.
Concurrent external editing and hostile concurrent filesystem mutation are unsupported.
On errors the process stops and reports recovery information. Never rerun an old plan
blindly after a partial failure. There is no automatic cross-filesystem copy or rollback
that might overwrite newer work. Recovery journals are trusted local artifacts: editing
their contents changes recovery instructions, so retain them privately and review previews.

## Coverage and current state

The built-in inventory is deliberately shallow; it is not a complete account or deep
folder audit. For collection setup, supplement it with a bounded nested-project search
and record exclusions and unreviewed sources. Do not classify dated task directories
as enduring projects automatically. Use substantive source evidence over keyword hints.
Existing STATE is preserved by adoption. Review its Now separately and propose a sourced
update when stale; preserving the file does not establish current-state correctness.

Use `scaffold.py discover ROOT --depth 3 --json` for bounded marker-based nested
project discovery. It reports excluded and depth-limited directories. Markers are
candidates only; directories without markers still need human/agent review when
substantive work may exist there. Never equate discovery with content assessment.
