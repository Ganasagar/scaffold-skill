# Scaffold-skill 0.2: finalized feature and implementation plan

Status: v0.2 implementation complete on the feature branch; release qualification limits below. Baseline: repository commit `dda324d088903b726bb5288e43baddb30eb94396`, version 0.1.0. Release implementation and installation are separate steps; this document defines the implementation scope.

## Intended result

A reusable personal Codex skill that safely scaffolds new projects and proposes reviewed migrations of existing projects. Preserve the standard-library runtime and existing useful layout. Make adoption project-scoped by default, with explicit opt-in for global behavior. Ship the improvements back to Ganasagar/scaffold-skill in small, reviewable changes.

## 1. Establish regression coverage and shared safety primitives

Capture the reproduced destination-collision, outside-root, backup-collision, and missing-P3-verifier failures as regression tests. Keep all fixtures inside temporary directories with isolated HOME/CODEX_HOME and skill installation paths.

Add small internal modules for path policy, file writes/backups, and migration planning/execution as needed; avoid an unrelated full rewrite of the engine. Keep command entry points and existing supported behavior where safe. Document any intentional change in defaults.

Acceptance:
- Existing 19 tests continue to pass except where an explicitly documented safety change requires updating expectations.
- New regression tests fail on the baseline and pass after their corresponding fixes.
- Test runs cannot mutate the real home configuration, live projects, or connected services.

## 2. Make migration plans bounded, validated, and recoverable

Introduce a versioned plan schema containing the canonical allowed root, plan ID, source identities, expected file types, preconditions, explicit destinations, and dependencies between moves and conversions. Reject malformed plans, unsupported operations, invalid names, traversal components, absolute name overrides, and paths outside the selected root.

Preflight the entire plan before the first mutation. Detect destination collisions, duplicate operations, missing sources, stale control-file hashes, symlink escapes, cycles, and cross-filesystem moves. For the first hardened release, reject cross-filesystem moves and symlinked migration paths rather than silently copying or following them. Report nested repositories, worktrees, and path-dependent infrastructure; block automatic relocation of worktrees and flagged infrastructure until handled explicitly.

Conversion must reference the exact source project and a successful move outcome. An existing destination is an error, never an invitation to convert that directory. Recheck relevant preconditions immediately before each write; document that concurrent external edits are not a supported migration mode.

Persist a private operation journal outside paths being moved. Record completed operations, backup locations, identities, and failure status. Stop on failure. Provide a recovery command that previews reversing completed operations, refuses conflicts, and never overwrites newer user changes. Do not claim filesystem-wide atomicity: individual file replacement can be atomic, a multi-folder migration cannot.

Acceptance:
- Any invalid plan produces zero project mutations.
- Collision fixtures never change the unrelated destination.
- Outside-root and symlink escape fixtures are rejected.
- A modified source invalidates the reviewed plan.
- Injected failure after each operation produces an accurate journal and a safe recovery preview.
- A repeated apply refuses a completed/stale plan or reports a verified no-op; it cannot duplicate conversion.

## 3. Unify writes, backups, and previews

Route refine, index, rotate, harness profile/config updates, and managed-block edits through shared write helpers. Use exclusive collision-proof backup names, preserve original bytes and permissions where relevant, and record content hashes. Stage replacement files beside their targets and replace atomically after validating the original is unchanged. Reject symlinked control-file targets by default.

Generate both dry-run previews and actual execution from the same planned content, including harness stakes floors. Validate managed-block marker pairs and refuse ambiguous/duplicate markers. Parse TOML before changing config; preserve unrelated settings and report unsupported edit cases instead of appending a conflicting table.

Acceptance:
- Multiple writes in one timestamp interval preserve every recovery version.
- Index and rotation both have recoverable originals.
- Preview hashes match the bytes applied when preconditions are unchanged.
- Malformed managed blocks and invalid TOML leave files untouched.
- Rotation handles chronological order, boundaries, and repeated runs without losing entries.

## 4. Preserve project knowledge during onboarding

Separate read-only inventory, proposed classification, reviewed project intake, and execution. Inventory legacy AGENTS/CLAUDE/MEMORY files, state archives, resources/, existing references, Git boundaries, and relevant symlinks without following external targets. Treat directory names and matching instruction hashes as classification hints, not proof that projects are duplicates.

Produce a per-project migration worksheet: goal, active work, constraints, decisions, authoritative files, proposed category, proposed moves, and unresolved questions, each with source paths. Preserve originals byte-for-byte. Require reviewed intake for conversion; unresolved projects stay in place. Generated AGENTS.md must link preserved legacy instructions and warn of unresolved conflicts. STATE.md must carry reviewed current work or explicitly mark migration incomplete, rather than imply a generic TODO is an adequate handoff.

Keep semantic synthesis in the Codex workflow and deterministic validation/execution in Python. Do not silently rewrite or discard old instructions. Support an adopt-in-place mode as the default; physical reorganization is a separate reviewed operation.

Acceptance:
- Representative legacy fixtures retain every original file and all identified constraints/current actions in the reviewed handoff.
- Existing native Codex projects are preserved or merged through a visible diff.
- Ambiguous projects receive no relocation or fabricated intake.
- Identical template files do not automatically classify distinct projects as duplicates.

## 5. Protect personal material and Git boundaries

Default new projects to ignoring context/, work/, output/, local archives, credentials, and migration recovery artifacts. Provide explicit opt-in tracking for selected reproducible material. Preserve existing Git policy; propose a managed-block diff rather than replacing or silently skipping an existing .gitignore.

Use Git's actual ignore evaluation for representative paths, including ancestor rules and negations. Inspect already-tracked sensitive paths separately: .gitignore does not remove them from history. Report findings without automatically untracking or rewriting history. For folders without Git, report policy validation as limited rather than claiming effective protection.

Provide private/public reference-index modes so tracked indexes need not disclose sensitive filenames. Keep detailed migration inventories and backups private. Do not introduce GitHub creation or automatic push as part of scaffolding.

Acceptance:
- Negated ignore rules cannot produce a false privacy pass.
- Nested repositories and parent allowlists are evaluated in their correct Git context.
- Existing tracked private material is reported without alteration.
- Public-mode metadata fixtures omit private names and paths.

## 6. Make routing and Codex scope consistent

Define routing in one source of truth used by the CLI, templates, and documentation. P3 final artifacts must include the documented verification step; high-stakes decisions include challenger review. Keep P0/P1 lightweight. Describe reviewer write restrictions accurately as instructions inheriting parent permissions.

Add explicit project/user installation scopes. Default installation to an explicitly selected project root with project-scoped agent files/profile. Global instructions and config changes require a separate, visible opt-in. Reuse existing authorization for routine requested writes; require review of the concrete batch plan for relocation. Do not ask again for every file in an approved plan. Resolve profile precedence explicitly: project values override user defaults; absent profiles must still permit local scaffolding.

Detect agent-name collisions and overlapping scaffold skills. Use namespaced custom-agent names where appropriate. Move installation backups outside every skill discovery directory. Add version/hash manifests, repeat-install behavior, upgrade preview, and uninstall that removes only owned, unchanged files/blocks. Warn that link mode activates checkout edits immediately.

Acceptance:
- Routing matrix covers stakes, task kind, item/source thresholds, and explicit user requests.
- Project installation leaves real global Codex files unchanged.
- Reinstallation produces one discoverable skill and no hidden competing backup copies.
- Upgrade/uninstall preserves user edits and unrelated agents/configuration.
- A later authorized disposable Codex smoke test confirms custom-agent discovery; unit tests alone do not establish this.

## 7. Package and contribute upstream

Suggested review sequence:
1. PR: bounded migration plans, collision handling, operation journal, and regression tests.
2. PR: shared write/backup helpers and accurate previews.
3. PR: reviewed legacy adoption and privacy-aware Git policy.
4. PR: project-scoped installation, routing consistency, upgrade/uninstall, documentation.

Keep each PR independently tested and document any dependency on earlier PRs. Add a standard-library CI matrix covering the supported Python range and Linux/macOS filesystem behavior. Validate the advertised minimum Python version against any TOML implementation choice; do not silently add a newer Python requirement or dependency.

Update README, SKILL.md, references, templates, changelog, CLI help, recovery examples, and known limits together. Add a compatibility statement based on tested Codex versions. Select a license with the repository owner before adding a LICENSE; do not choose one on the owner's behalf. Propose version 0.2.0 for the combined behavior/default changes.

Implementation can prepare commits and PR descriptions locally. Publishing/pushing and opening PRs follow explicit authorization for that step.

## 8. Release qualification on disposable projects

Use representative fixtures: a legacy project, an existing Codex project, a nested Git repository, a sensitive-document project, and an ambiguous project. Review inventory and adopt-in-place previews before applying to copies. Exercise failure recovery and verify original hashes remain unchanged. Test actual agent discovery in an isolated Codex environment when authorized; label it unverified until completed.

The release is ready when the migration regressions are fixed, no preflight failure mutates projects, recovery refuses conflicts, reviewed knowledge survives adoption, effective Git checks pass, and project installation preserves unrelated configuration.

## Final feature boundaries

Included in 0.2:
- Safe new-project creation and adoption in place.
- Separate, explicitly reviewed folder reorganization.
- Versioned plans, dependency-aware execution, drift checks, private journals, and conflict-aware recovery.
- Consistent backups, atomic single-file replacement, and faithful previews across write commands.
- Reviewed legacy knowledge mapping and unresolved-project reporting.
- Effective Git privacy checks and optional redacted reference indexes.
- Project/user scope, collision detection, upgrade/uninstall manifests, and routing consistency.
- Documentation, regression tests, and release qualification fixtures.

Additional acceptance details from final inspection:
- Ambiguity blocks conversion and relocation for that project even if a category proposal exists.
- Project IDs derive from canonical relative paths, never display names alone; same-named projects in different tiers remain distinct.
- Intake validation checks types, enum values, required meaningful goals, and path-safe naming/emoji overrides. Placeholder template answers are incomplete intake.
- The instruction-budget audit distinguishes configurable limits and discovery overrides from its own estimates. If effective Codex settings cannot be resolved, report an estimate rather than a definitive pass.
- Markdown indexes escape unusual filenames and retain usable paths without corrupting table structure.
- Agent instructions remain subordinate to the user's scope and host capabilities. Missing agents are reported rather than silently counted as completed verification.
- Generic skill discovery remains enabled. Narrow its description to scaffolding and project organization so it does not activate for ordinary project implementation.
- New requests infer intake from supplied context and ask only for missing consequential information; a four-question maximum is a ceiling, not a mandatory questionnaire.

Deferred: cloud/Drive sync, automatic GitHub publishing, cross-filesystem migration, worktree relocation, duplicate deletion/merging, background monitoring, additional agent harnesses, and a web UI. These are independent features and not required to fix the reviewed failures.

## Implementation decisions

Default to adopting in place, explicit project scope, private work/context/output, rejecting unsafe symlink paths and cross-filesystem moves, no automatic push, and one active scaffold skill. Preserve configurable categories and emoji styles; do not impose one person's taxonomy on every installation.

Use a Python-standard-library implementation. Keep the advertised Python 3.10 minimum unless a tested technical constraint justifies an explicit version change; config mutation can fail safely with actionable guidance where parsing support is unavailable. Git-backed audits require Git and report unavailable checks when it is missing.

License selection remains an owner decision before public release. Remote publishing authorization and the final contribution branch are determined when the tested patches are ready. These do not block local implementation.

## Final check evidence

The supplied local checkout was clean before this planning document was added and matches `dda324d088903b726bb5288e43baddb30eb94396`. On 2026-10-17, all 19 supplied tests passed and the Codex skill-creator format validator reported “Skill is valid!”. The earlier isolated migration probes still apply to this identical source revision. Format validation and the supplied tests do not cover those demonstrated failures. No production migration or native custom-agent launch was performed.

## Implementation outcome

The implementation is delivered together on `feat/safe-scaffolding-v0.2` because the
shared write layer, migration preflight, installation ownership, and their regressions
must be reviewed as one coherent behavior change. The four review areas above remain
useful review boundaries within this contribution.

Implemented: version-2 bounded plans, reviewed intake, adoption in place, separately
requested reorganization, full source identities, collision/drift checks, private journals,
conflict-aware recovery, unique backups, atomic file writes, legacy instruction bridges,
privacy-aware indexes and effective Git checks, project/user installation scope,
owned-file upgrade/uninstall, optional local profiles, consistent P3 verification,
workflow documentation, and CI configuration.

The CLI budget check deliberately reports an estimate until discovery/config overrides
are fully resolved. Dependency detection is heuristic; relocation of externally referenced
infrastructure remains a manual decision. Categories remain built-in; naming styles and
reviewed destinations are configurable. Config edits on Python 3.10 fail safely with
instructions to edit manually rather than adding a runtime dependency.

Release qualification still requiring external or owner action: CI matrix results,
a native Codex custom-agent discovery smoke test in a permitted host session, owner
license selection, and real deployment approval/import reconciliation. No real project
migration or live skill installation is included in this code contribution.
