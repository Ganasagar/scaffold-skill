# 🏗️ scaffold-skill

> Opinionated project scaffolding for AI coding agents, built for personal projects where every token counts.
> **Status:** ✅ Codex version `0.1.0` · 🚧 Claude version planned

`scaffold-skill` gives every project you run with an agent the same small, predictable charter: what the project is for, what it must never do, how risky it is, where its inputs live, and what happened last session. It then uses that charter to decide when it is worth spending tokens on subagents and verification, and when it is not.

It also reviews an existing pile of project folders, proposes a tiered layout with emoji folder names, and migrates them, without deleting or overwriting anything.

---

## 📑 Contents

- [Why](#-why)
- [Features](#-features)
- [Install](#-install)
- [Quick start](#-quick-start)
- [What a project looks like](#-what-a-project-looks-like)
- [Questionnaires](#-questionnaires)
- [Routing: when agents are worth it](#-routing-when-agents-are-worth-it)
- [Reliability agents](#-reliability-agents)
- [Memory and progressive disclosure](#-memory-and-progressive-disclosure)
- [Emoji tiers and folder names](#-emoji-tiers-and-folder-names)
- [Organizing an existing installation](#-organizing-an-existing-installation)
- [Command reference](#-command-reference)
- [Checks](#-checks)
- [Safety model](#-safety-model)
- [Known limits](#-known-limits)
- [Development](#-development)
- [Roadmap](#-roadmap)

---

## 💡 Why

Agent projects decay in three predictable ways:

| Problem | What it costs | What scaffold-skill does |
|---|---|---|
| Charter files grow without limit | Every session re-reads them. A 40 KB memory file is roughly 10k tokens gone before any work starts. | Hard budgets: AGENTS.md ≤ 60 lines, STATE.md ≤ 8 KB with log rotation, `## Now` ≤ 15 lines. |
| Multi-agent and QA runs on everything | Each subagent cold-starts and re-reads context, so a verified task costs several times a plain one. | A P0–P3 routing table. Agents run only when the stakes justify it. |
| Every project is structured differently | Agents waste turns working out where things are. | One standard layout, a 9-point check, and a migration path for old projects. |

---

## ✨ Features

| | Feature | Summary |
|---|---|---|
| ❓ | **Two-level questionnaires** | A harness profile asked once per machine and a project intake asked per project. Max 4 questions each. |
| 🧱 | **Standard charter** | AGENTS.md, STATE.md, REFERENCES.md, SKILLS.md, plus `context/`, `work/`, `output/`. |
| 🧮 | **Token-aware routing** | P0–P3 tiers decide main thread vs. verifier vs. fan-out. Deterministic `route` command. |
| 🧪 | **Reliability agents** | `verifier` (fact check against sources) and `challenger` (attacks a decision), as Codex custom agents. |
| 🗂️ | **Progressive disclosure** | REFERENCES.md indexes every input, so the agent opens only what a task needs. |
| 🧠 | **Memory upkeep** | `rotate` archives old STATE.md log entries; `index` keeps REFERENCES.md complete. |
| 🎨 | **Emoji folder names** | `plain` / `tier` / `rich` styles with keyword-scored glyphs, no LLM involved. |
| 🧭 | **Brownfield onboarding** | Inventory an existing projects root, propose tiers, find duplicates, and migrate on approval. |
| 🔍 | **9-point check** | Structure, budgets, index coverage, `.gitignore`, and Codex's 32 KiB AGENTS.md limit. |
| 🛡️ | **Non-destructive by design** | Create-only writes, managed blocks, backups, dry runs, no deletes. |

---

## 📦 Install

Requirements: Codex CLI or app with skills support, and Python 3.10+. Standard library only, nothing to `pip install`.

```bash
git clone https://github.com/Ganasagar/scaffold-skill.git
cd scaffold-skill
./install.sh          # copies codex/scaffold-skill → ~/.agents/skills/scaffold-skill
# or
./install.sh --link   # symlink, so edits in the repo go live
```

Restart Codex. The skill appears in the skill list; ask for it by name (for example "use scaffold-skill to set up a new project") or let Codex select it from its description.

> ⚠️ **Gotcha.** Codex loads user skills from `~/.agents/skills/`, not `~/.codex/skills/`. Set `SKILLS_DIR` to install elsewhere.

---

## 🚀 Quick start

In Codex:

1. **"Set up scaffold-skill"** runs the harness questionnaire once, writes your profile block into `~/.codex/AGENTS.md`, and installs the two reliability agents.
2. **"Start a new project called Award Travel"** asks the project questions, shows a dry run, and creates `✈️ award-travel/` (folder style permitting).
3. **"Check this project"** runs the 9-point audit and tells you what to fix.

Or run the engine directly:

```bash
S=~/.agents/skills/scaffold-skill/scripts/scaffold.py

python3 $S template --level harness > harness.json   # edit answers
python3 $S harness init --answers harness.json --dry-run
python3 $S harness init --answers harness.json --write-config

python3 $S template > intake.json                    # edit answers
python3 $S new "Award Travel" --parent ~/projects --intake intake.json --dry-run
python3 $S new "Award Travel" --parent ~/projects --intake intake.json
python3 $S check ~/projects/"✈️ award-travel"
```

---

## 🧱 What a project looks like

```text
✈️ award-travel/
├── AGENTS.md        rules + managed intake block + routing table   (≤ 60 lines, read every session)
├── STATE.md         ## Now · ## Decisions · ## Log                 (≤ 8 KB, only ## Now read every session)
├── REFERENCES.md    index of inputs and archives                   (read when a task needs inputs)
├── SKILLS.md        project procedures                             (read only when running one)
├── .gitignore       output/ + secrets, and context/ if sensitive
├── context/         inputs — read-only by rule
├── work/            drafts, claims.md, verification logs, archive/, state-archive.md
└── output/          verified deliverables only — never pushed
```

| Zone | Rule |
|---|---|
| `context/` | Inputs. Never edited; derive into `work/`. Git-ignored when the project holds sensitive documents. |
| `work/` | Anything goes: drafts, data, `claims.md`, `verify-*.md`, `challenge-*.md`, `archive/`. |
| `output/` | Only artifacts that passed their tier's verification. Always git-ignored. |

The intake lives inside a **managed block** in AGENTS.md:

```markdown
<!-- scaffold-skill:intake:start -->
## Project intake (managed by scaffold-skill — edit via `refine`)
- Goal: Book business-class award to HYD for 2027
- Done when: tickets issued
- Horizon: 2027-03
- Stakes: money → default tier **P2** for deliverables
- Never:
  - never transfer points without asking
- Git: push, private, context/ ignored
<!-- scaffold-skill:intake:end -->
```

`refine` rewrites only that block. Anything you add outside it is preserved.

---

## ❓ Questionnaires

Both are asked in a single message, numbered, with defaults shown. Saying "use defaults" skips everything except project Q1.

### Harness (once per machine)

| # | Question | Default |
|---|---|---|
| 1 | Reply style: terse, balanced or detailed? | terse |
| 2 | File naming: `name-vN`, `YYYY-MM-DD-name` or `name-MM-DD-YYYY`? | `name-vN` |
| 3 | Stakes floor: low (route per task) or high (verify every deliverable)? | low |
| 4 | New projects: push to GitHub? private or public? keep `context/` out of git? | push · private · ignore context |

Stored in `~/.codex/scaffold-skill/profile.json` and rendered into a managed block in `~/.codex/AGENTS.md`, which Codex loads for every session. Projects point at it instead of repeating it.

### Project (every new project)

| # | Question | Drives |
|---|---|---|
| 1 | What must it achieve, how will you know it is done, by when? *(required)* | intake block |
| 2 | Anything the agent must never do here, or context written nowhere else? | never / caveats list |
| 3 | Stakes: money, legal, health, outbound, irreversible? | default routing tier |
| 4 | Push to GitHub? private or public? keep `context/` out of git? | `.gitignore` |

Full schema: [`references/intake.md`](codex/scaffold-skill/references/intake.md).

---

## 🧮 Routing: when agents are worth it

Codex spawns subagents only when you ask or when `AGENTS.md` or skill instructions tell it to. This table, written into every project's AGENTS.md, is therefore the on/off switch.

| Tier | When | Execution | Verification |
|---|---|---|---|
| **P0** | trivial edit, rename, STATE update | main thread | none |
| **P1** | low-stakes deliverable | main thread | deterministic checks + self-checklist |
| **P2** | money · legal · health · outbound · irreversible | main thread builds | `verifier` on `work/claims.md`; REFUTED blocks `output/` |
| **P3** | ≥ 5 similar items or ≥ 3 heavy sources | ≤ 4 parallel workers, summaries only | P2 rule on the final artifact |

Principles:

- 💡 **Stakes buy verification, not size.** A long research note is P1. A short email to a tax office is P2.
- 💡 **Deterministic before LLM.** Recompute numbers, validate dates, links and JSON, compile code. Free.
- 💡 **One verifier, never two.** No chains of agents checking agents.
- 💡 **Bounded inputs.** The verifier gets the claims list and the cited sources, not the conversation.
- 💡 **No silent escalation.** "verify", "challenge" or "fan out" from you escalate any task. Nothing else does.

Ask the engine when unsure:

```bash
$ python3 $S route --stakes money,legal --decision
P2 · agents: verifier, challenger · deterministic checks + claims ledger + verifier; REFUTED blocks output/

$ python3 $S route --kind research --items 8
P3 · agents: workers≤4 (default) · worker summaries only; P2 rule on the final artifact
```

---

## 🧪 Reliability agents

Installed once into `~/.codex/agents/` by `harness init`, not copied into each project.

| Agent | Purpose | Runs | Reads | Writes |
|---|---|---|---|---|
| `verifier` | Marks each claim VERIFIED, UNVERIFIED or REFUTED, and recomputes numbers and dates. | P2 deliverables | `work/claims.md` + cited sources only | `work/verify-<artifact>.md` → PASS / BLOCK |
| `challenger` | Steelmans the objections: hidden assumptions, missed options, irreversible downsides. | High-stakes decisions, or "challenge this" | the decision brief only | `work/challenge-<decision>.md` → ranked objections |

They catch different failures. The verifier catches wrong facts; the challenger catches a well-sourced argument built on a bad premise.

For code at P2, the routing table points to Codex's built-in **`codex review`** instead of the custom verifier. Fan-out at P3 uses Codex's built-in `default` / `explorer` agents, so there is no custom researcher to maintain.

### Claims ledger

While drafting a P2 artifact, the main thread records every load-bearing claim:

```text
| claim                              | source                         | tier      |
| Award costs 70k miles one way      | https://… partner award chart  | primary   |
| Lounge access included             | blog post                      | secondary |
```

Unsourced claims are marked 🔍 *unverified* in the draft. The verifier reads only this file and its sources, which keeps its cost bounded.

Want a cheaper verifier? Add `model = "<model>"` to `~/.codex/agents/verifier.toml`. Codex uses a model set in the agent file ahead of the parent's.

---

## 🧠 Memory and progressive disclosure

| Layer | Read | Files | Budget |
|---|---|---|---|
| **L0** | every session | AGENTS.md + STATE.md `## Now` | about 1–2k tokens |
| **L1** | when a task needs inputs | REFERENCES.md index | one line per resource |
| **L2** | on demand | `context/*`, SKILLS.md, `work/state-archive.md` | only what the task needs |

| Store | Holds | Lifecycle |
|---|---|---|
| `STATE.md ## Now` | current status, next action | overwritten each session, ≤ 15 lines |
| `STATE.md ## Decisions` | durable choices and rationale | append-only |
| `STATE.md ## Log` | dated activity | append; `rotate` archives past 8 KB |
| `REFERENCES.md` | what exists and when to read it | `index` adds rows and flags stale ones |
| `~/.codex/AGENTS.md` block | who you are, style, defaults | set by `harness init` |

```bash
python3 $S index  <project>   # add stub rows for new context/ files; flag rows whose file is gone
python3 $S rotate <project>   # keep the newest 10 log entries, archive the rest
```

---

## 🎨 Emoji tiers and folder names

| Style | Folder | Git repo name |
|---|---|---|
| `plain` | `award-travel` | `award-travel` |
| `tier` *(default)* | `✈️ award-travel` | `award-travel` |
| `rich` | `✈️ 🎫 award-travel` | `award-travel` |

GitHub repo names cannot contain emoji, so the slug always stays ASCII; only the local folder carries glyphs.

Personal tier catalog (only tiers your projects actually use are proposed):

| 🏠 Life-admin | 💰 Finance | ✈️ Travel | 🛠️ Builds | 🤖 Agents | 🎓 Career | ✍️ Writing | 📚 Learning | 🗂️ Unsorted |
|---|---|---|---|---|---|---|---|---|

Selection is keyword scoring over the name and goal. A tie or no hits lands in 🗂️ Unsorted and gets asked about once. Pin with `--emoji`, or with the intake keys `tier` and `emoji`.

---

## 🧭 Organizing an existing installation

```bash
python3 $S onboard ~/projects --plan-out plan.json      # read-only inventory + proposal
python3 $S onboard --apply-plan plan.json               # dry run of the reviewed plan
python3 $S onboard --apply-plan plan.json --yes         # execute
```

The inventory reports:

- 🧬 **Structure generation** per folder: `standard`, `legacy-memory`, `partial`, `bare`
- 📏 **Per-session cost:** control-file bytes converted to estimated tokens, heaviest first
- 👯 **Duplicates:** same slug, or byte-identical charter files
- 📅 **Dated run folders:** `YYYY-MM-DD/` output dumps
- 🗂️ **Proposed tiers,** plus the ambiguous items

| Plan action | Executed? | Behaviour |
|---|---|---|
| `move` | with `--yes` | Renames into `<emoji> <Tier>/<display-name>`. Skipped if the destination exists. |
| `convert` | with `--yes` | Adds missing standard files only. Legacy `MEMORY.md` / `CLAUDE.md` are kept and can be indexed. |
| `review` | never | Duplicates and dated folders are your call. |

Edit `plan.json` to drop anything you disagree with before executing. Nothing is deleted.

---

## 📚 Command reference

All commands accept `--json` and `--codex-home <dir>` (default `$CODEX_HOME` or `~/.codex`). Every write command accepts `--dry-run`.

| Command | Purpose | Writes |
|---|---|---|
| `harness show` | print the harness profile (exit 1 if missing) | — |
| `harness init --answers F [--write-config]` | write the profile block and install agents | `~/.codex/AGENTS.md` block, `profile.json`, `agents/*.toml`, optional `config.toml` append |
| `template [--level project\|harness]` | print an answers skeleton | — |
| `new NAME --parent DIR --intake F [--name-style S] [--emoji G]` | create and scaffold a project folder | new folder only |
| `apply PATH --intake F` | scaffold an existing folder | missing files only |
| `refine PATH --intake F` | update the managed intake block | AGENTS.md block (backup in `work/archive/`) |
| `check PATH` | 9-point audit; exit 1 on any FAIL | — |
| `index PATH` | add REFERENCES.md rows for unindexed inputs | REFERENCES.md (append) |
| `rotate PATH [--keep N] [--max-bytes B]` | archive old STATE.md log entries | STATE.md, `work/state-archive.md` |
| `route [--stakes ...] [--kind K] [--items N] [--sources N] [--decision] [--asked A]` | P0–P3 classification | — |
| `onboard ROOT [--plan-out F]` / `onboard --apply-plan F [--yes]` | inventory, propose, migrate | moves + create-only files with `--yes` |
| `version` | print version | — |

---

## 🔍 Checks

| ID | Verifies | Level |
|---|---|---|
| C01_DIRS | `context/`, `work/`, `output/` exist | FAIL |
| C02_CONTROL_FILES | AGENTS, STATE, REFERENCES, SKILLS exist | FAIL |
| C03_INTAKE_BLOCK | managed intake block present | FAIL |
| C04_AGENTS_BUDGET | AGENTS.md ≤ 60 lines | WARN |
| C05_STATE_BUDGET | STATE.md ≤ 8 KB and `## Now` ≤ 15 lines | WARN |
| C06_REFERENCES_COVERAGE | every `context/` file and archive is indexed | WARN |
| C07_GITIGNORE | `output/` and secret patterns ignored | FAIL |
| C08_NO_DUPLICATE_CHARTER | no legacy `CLAUDE.md` / `MEMORY.md` competing with the charter | WARN |
| C09_CODEX_DOC_LIMIT | merged AGENTS.md chain below 80% of Codex's 32 KiB default | WARN |

---

## 🛡️ Safety model

- ✅ **Create-only writes.** Files are opened in exclusive-create mode, so an existing file is never overwritten.
- ✅ **Managed blocks.** Only text between `scaffold-skill` markers is ever rewritten, with a timestamped backup first.
- ✅ **Dry runs.** Every write command previews first. The skill instructions require showing the preview and getting a yes.
- ✅ **No deletes.** Migrations only rename, and skip if the destination exists. Duplicates are review-only.
- ✅ **Read-only inputs.** `context/` is never edited by rule.
- ✅ **Secrets stay local.** `.env*`, `*.key`, `*.pem` and `output/` are always git-ignored.
- ✅ **Intake is data.** Free-text answers are length-capped and stripped of headings before they reach AGENTS.md.

> ⚠️ **Privacy.** If a project's `context/` holds tax, immigration, health or financial documents, keep `ignore_context: true` (the default) or keep the repository private.

---

## ⚠️ Known limits

| Limit | Detail |
|---|---|
| Read-only agents are instruction-only | Codex custom agents inherit the parent sandbox. After a verifier run, `git status` should show changes only under `work/`. |
| Spawning is instruction-driven | Codex delegates when asked or instructed. The routing table makes that predictable; it cannot make it guaranteed. |
| Silent truncation | Codex stops reading AGENTS.md files past `project_doc_max_bytes` (32 KiB default). C09 warns at 80%. |
| Emoji paths | Some shells and tools handle emoji paths poorly. Use `plain` style if that bites. |
| Token estimates | Bytes ÷ 4. Good for ranking, not billing. |

---

## 🧰 Development

```text
scaffold-skill/
├── README.md · CHANGELOG.md · install.sh · .gitignore
└── codex/scaffold-skill/          ← the installable skill
    ├── SKILL.md                   ← loaded only when the skill is selected
    ├── scripts/scaffold.py        ← engine (stdlib)
    ├── scripts/test_scaffold.py   ← 19 tests
    ├── assets/templates/          ← AGENTS / STATE / REFERENCES / SKILLS / gitignore
    ├── assets/agents/             ← verifier.toml · challenger.toml
    ├── assets/harness/            ← global profile block
    └── references/                ← intake.md · routing.md · organize.md (progressive disclosure)
```

```bash
cd codex/scaffold-skill
python3 -m unittest discover -s scripts -v
```

The suite includes a scrub test that fails if work- or harness-specific terms ever enter the repository.

---

## 🗺️ Roadmap

- 🚧 **Claude version** (`claude/scaffold-skill/`): `CLAUDE.md` as a one-line `@AGENTS.md` import, multiple-choice intake, Claude subagent definitions.
- 🔧 Optional hooks that turn the "ask before outbound / irreversible" rule into an enforced gate.
- 🔧 `onboard` support for merging duplicate projects interactively.
