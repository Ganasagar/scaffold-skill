# Optional cross-device migration readiness

Enter only for a user-requested migration. Refresh official product documentation and
available capabilities; do not generalize this installation's historical chat counts
or assume a handoff limitation is permanent.

Reconcile source/destination chat IDs, parent IDs, archive flags, ordinary chats,
automation runs, subagents and rollouts. Preserve originals. Transcript exports are
history artifacts, not original resumable chats. Check file hashes and report missing
items. Preserve attachments and ignored inputs separately where authorized.

Preserve unsent drafts before clearing anything. Unrecoverable composer state blocks
affected chats, not independent preparation. Never send drafts to clear a blocker.
Do not replace, merge or write live Codex databases as a migration shortcut.

`scaffold.py repo-check PATH --json` checks the current root, HEAD commit/tree, status
and origin. A readable HEAD string alone is insufficient. Compare source and target
repository identity and subdirectory, inspect dirty state and worktree pointers,
verify saved destination registration, and recheck immediately before handoff. The
command intentionally never certifies handoff-ready: it cannot observe app state.
Use full object integrity checks when transfer corruption is suspected. Do not reset
or repair existing repositories destructively. Isolated staging clones are not yet
canonical project homes; record destination changes explicitly.

Use serialized checkpointed handoffs and reconcile original IDs, archived state and
files. Test the first eligible item before continuing a batch. Automations need a
separate path/schedule/notification review; preserve child history with its parent.
A host connection alone does not prove saved projects or chats are visible remotely.

Git publication is separate: organize first, preserve independent histories, review
tracked files and exclusions, then perform only authorized GitHub creation/push.
No git init, clone, push or service execution is implicit in ordinary scaffolding.
