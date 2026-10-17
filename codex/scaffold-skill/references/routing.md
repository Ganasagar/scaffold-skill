# Routing and reliability

The engine's `route()` is the decision source; project tables are generated from its
results. `route --project ROOT --stakes money --decision --json` resolves local profile
precedence. It reports requested execution, not proof that an agent was available or ran.

P0 trivial maintenance stays in the main thread. P1 low-stakes deliverables use
appropriate deterministic checks. P2 stakes (money/legal/health/outbound/irreversible)
or a high profile floor require verification. P3 (at least five items, three independent
sources, or an explicit fan-out request) permits up to four workers and requires the
P2 final verification step, even for otherwise low-stakes work. Code verification uses
`codex review`; other artifacts use `verifier`. High-stakes decisions also use `challenger`.
Explicit verify/challenge requests escalate to their requested review.

Create `work/claims.md` as needed: claim | source | primary/secondary. Give reviewers only
the relevant draft, ledger, and sources. Recompute numbers and run appropriate code checks
before model review. A REFUTED claim or an unverified load-bearing claim blocks PASS.
Missing agents or host restrictions leave verification incomplete; report that clearly.

Project agents live in ROOT/.codex/agents/; user-wide agents in CODEX_HOME/agents/.
These are standalone TOML files. The optional concurrency setting is
`[agents] max_concurrent_threads_per_session = 4`. Setup never replaces an existing
agents table or silently overwrites a conflicting agent file.

Read-only reviewer behavior is an instruction. Custom agents inherit parent permissions;
a local agent TOML cannot establish an independent read-only sandbox. Review changed
files after execution. User scope and host tool policy take precedence over the routing
recommendation. Intake, scaffolding, checking, and refinement require no subagents.

Official references (checked against the local CLI 0.163.0 documentation):
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://learn.chatgpt.com/docs/config-file/config-reference

Native agent discovery has not been exercised by the unit tests; perform an isolated
host smoke test before relying on custom agents in a new installation.
