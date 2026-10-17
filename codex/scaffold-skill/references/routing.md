# Routing & reliability — when to spend tokens

Codex delegates to subagents only when asked, or when AGENTS.md / skill instructions say so.
The routing table in each project's AGENTS.md is therefore the on/off switch. Keep it strict.

## Tiers
| Tier | Trigger | Execution | Verification |
|---|---|---|---|
| P0 | trivial edit, rename, STATE update | main thread | none |
| P1 | low-stakes deliverable | main thread | deterministic checks + self-checklist |
| P2 | any stake: money, legal, health, outbound, irreversible (or harness floor = high) | main thread | claims ledger → `verifier`; REFUTED blocks `output/` |
| P3 | ≥5 homogeneous items or ≥3 heavy independent sources | ≤4 parallel workers | summaries + paths only; P2 rule on the final artifact |

`scaffold.py route --stakes money --decision` gives the same answer deterministically.

## Agents
| Agent | Kind | Runs when | Input | Output |
|---|---|---|---|---|
| `verifier` | custom (`~/.codex/agents/verifier.toml`) | P2 deliverables | `work/claims.md` + cited sources only | `work/verify-<x>.md`, PASS/BLOCK |
| `challenger` | custom (`~/.codex/agents/challenger.toml`) | high-stakes decision memos, or "challenge this" | decision brief only | `work/challenge-<x>.md`, ranked objections |
| workers | built-in `default` / `explorer` | P3 fan-out | one slice + questions | ≤ 20-line summary + file path |
| `codex review` | built-in | code changes at P2 | the diff | review findings |

Never: dual verifiers, verifiers checking verifiers, agents at P0/P1, silent escalation.
User words "verify", "challenge", "fan out" escalate any task.

## Claims ledger (`work/claims.md`)
```text
| claim | source | tier |
| Award costs 70k miles one-way | https://… (partner chart) | primary |
| Lounge access included | blog post | secondary |
```
Write rows while drafting, not afterwards. Unsourced → 🔍 unverified in the draft.
The verifier reads only this file and its sources — bounded input, bounded cost.

## Deterministic before LLM
Recompute totals, check dates and links, validate JSON/YAML, `python -m py_compile`, run tests.
These cost no tokens and catch most errors.

## Known limits (Codex)
- Custom agents cannot get a read-only sandbox; they inherit the parent's. "Read-only" is an
  instruction. After a verifier run, `git status` should show changes only under `work/`.
- Concurrency cap: `[agents] max_concurrent_threads_per_session = 4` in `~/.codex/config.toml`
  (`harness init --write-config` appends it if no `[agents]` table exists).
- Per-agent model: set `model` in the agent TOML to run the verifier on a cheaper model.
