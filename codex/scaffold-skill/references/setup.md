# Installation setup and completion

Read this only for installation, collection organization, or repair requests. Narrow
index/rotate/scaffold maintenance does not require the full installation workflow.

1. Record requested outcomes: intake, filesystem, app registration, sidebar, chats,
   optional cross-device access, handoff or publication. Discover available tools early.
2. Reuse confirmed preferences; ask consequential missing questionnaire items from
   intake.md. Explain inherited defaults. Do not fabricate project purposes.
3. Resolve permanent project root and authoritative host. A temporary ChatGPT task
   directory is not a permanent root; CODEX_HOME is configuration storage. No universal
   Codex project directory is assumed. Explicit user paths take precedence.
4. Assess substantive files and relevant chats; record discovered versus reviewed sources,
   inventory limits, nested projects and unavailable sources. Preserve legacy material.
5. Produce one canonical map: stable project ID, purpose, section, per-host folder,
   app project IDs, aliases, source evidence and current priorities. Same names or
   instruction templates do not establish identity. Categories are user choices.
6. Apply authorized filesystem changes with previews/recovery. Propose sourced updates
   to stale STATE Now, preserving historical entries and custom instructions.
7. Register filesystem projects and assign chats only if requested and supported.
   Follow app-integration.md. Continue independent work if a capability is unavailable.
8. Read back each outcome. Use a private setup manifest and `setup check` to detect
   missing evidence. It validates the evidence contract, not the truth of assertions.

Use `python3 scripts/scaffold.py setup template --json` to obtain the manifest schema.
Fill `requested` to match scope. Every verified facet needs evidence objects with
source, observed_at, host and detail. Each filesystem registration needs a project
record: id, path, host, app_kind=local, app_project_id, registration_status=verified.
Coverage must refer to the explicitly selected inventory scope. Truncated history is
incomplete, not complete account coverage. Requested facets can only be skipped for
an explicit user scope exclusion with a reason. A missing tool means blocked.

Store run manifests, before/after mappings and receipts privately in the hub work/
or .scaffold-skill directory. Reuse completed operations on retries after readback;
never blindly repeat project creation or chat moves. Filesystem recovery cannot roll
back external app operations; keep separate receipts and restoration mappings.

Final reports distinguish: created files, reviewed intake, saved app registrations,
chat membership, migration readiness, actual migrated chats and cross-device checks.
Never call a full installation complete based on the structural `check` command.
