# Organize — tiers, emoji names, existing installations

## Tiers (personal catalog)
Only tiers backed by real projects are proposed. Glyph selection is keyword scoring — no LLM.

| Tier | Emoji | Typical projects |
|---|---|---|
| Life-admin | 🏠 | home, property, taxes, insurance, relocation |
| Finance | 💰 | budgeting, investing, mortgage |
| Travel | ✈️ | trips, award bookings, flying |
| Builds | 🛠️ | robotics, 3D printing, homelab, hardware |
| Agents | 🤖 | assistants, personas, skills, automation |
| Career | 🎓 | jobs, applications, credentials |
| Writing | ✍️ | blogs, sites, content |
| Learning | 📚 | research, courses, notes |
| Unsorted | 🗂️ | no hits or a tie → asked once |

## Name styles
| Style | Folder | Git repo name |
|---|---|---|
| `plain` | `award-travel` | `award-travel` |
| `tier` (default) | `✈️ award-travel` | `award-travel` |
| `rich` | `✈️ 🎫 award-travel` | `award-travel` |

GitHub repo names cannot contain emoji, so the slug is always ASCII; only the folder name carries
glyphs. Pin glyphs with `--emoji` or the intake `emoji` / `tier` keys.

## Existing installation (`onboard`)
1. Inventory (read-only): `scaffold.py onboard ROOT --plan-out work/onboard-plan.json`
   - structure generation per folder: standard · legacy-memory · partial · bare
   - control-file bytes → estimated tokens read per session
   - duplicates (same slug or identical charter file), dated run folders
   - proposed tier per project, ambiguous items
2. Present the summary. Ask ONE consolidated question for ambiguous items and duplicates.
   Edit the plan JSON with the answers (delete actions the user rejects).
3. Dry run: `scaffold.py onboard --apply-plan work/onboard-plan.json`
4. Execute after explicit approval: add `--yes`.
   - `move`: renames into `<emoji> <Tier>/<display-name>`; skipped if the destination exists.
   - `convert`: creates missing standard files only; legacy `MEMORY.md` / `CLAUDE.md` are kept
     and get indexed in REFERENCES.md by `index`. Then run `refine` per project with the
     4-question intake.
   - `review`: never executed — duplicates and dated folders are the user's call.
Nothing is deleted. Ever.
