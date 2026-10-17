#!/usr/bin/env python3
"""scaffold-skill: scaffold, audit and organize personal agent projects for Codex.

Stdlib only. Every write path is non-destructive: missing files are created,
existing files are never overwritten (managed blocks are upserted, with a backup).

Commands:
  harness   show / init the one-time harness profile (~/.codex/AGENTS.md block + agents)
  template  print an intake JSON skeleton (project or harness)
  new       create a new project folder (name style + emoji) and scaffold it
  apply     scaffold an existing folder (create only what is missing)
  refine    re-run project intake: upsert the managed block in AGENTS.md
  check     read-only audit of one project
  index     add REFERENCES.md stub rows for unindexed context/ files and archives
  rotate    move old STATE.md log entries to work/state-archive.md
  route     classify a task into P0-P3 and name the agents it may use
  onboard   inventory an existing projects root and propose tiers / migrations
  version   print version
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

VERSION = "0.1.0"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "assets" / "templates"
AGENT_ASSETS = SKILL_DIR / "assets" / "agents"
HARNESS_ASSET = SKILL_DIR / "assets" / "harness" / "global-block.md"

DIRS = ("context", "work", "output")
CONTROL_FILES = ("AGENTS.md", "STATE.md", "REFERENCES.md", "SKILLS.md")
LEGACY_FILES = ("CLAUDE.md", "MEMORY.md")

INTAKE_START = "<!-- scaffold-skill:intake:start -->"
INTAKE_END = "<!-- scaffold-skill:intake:end -->"
HARNESS_START = "<!-- scaffold-skill:harness:start -->"
HARNESS_END = "<!-- scaffold-skill:harness:end -->"

AGENTS_MAX_LINES = 60
STATE_MAX_BYTES = 8 * 1024
NOW_MAX_LINES = 15
CODEX_DOC_LIMIT = 32 * 1024  # project_doc_max_bytes default
STAKES = ("money", "legal", "health", "outbound", "irreversible")
NAMING = ("name-vN", "YYYY-MM-DD-name", "name-MM-DD-YYYY")
NAME_STYLES = ("plain", "tier", "rich")
REPLY_STYLES = ("terse", "balanced", "detailed")
SECRET_PATTERNS = (".env", "*.key", "*.pem")

# Personal tiers: (emoji, keywords). Only tiers backed by real projects are proposed.
TIERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "Life-admin": ("🏠", ("home", "house", "tax", "taxes", "insurance", "bills", "admin", "property",
                         "lawn", "appliance", "move", "relocation", "family", "garden", "car")),
    "Finance": ("💰", ("finance", "financy", "money", "invest", "investing", "budget", "assets",
                      "mortgage", "refinance", "bank", "retirement", "stocks")),
    "Travel": ("✈️", ("travel", "trip", "flight", "flights", "award", "miles", "hotel", "aviation",
                     "ifr", "flying", "vacation", "itinerary")),
    "Builds": ("🛠️", ("robot", "robotics", "lekiwi", "rover", "3d", "print", "printing", "hardware",
                     "homelab", "nuc", "peloton", "arm", "jetson", "maker", "iot")),
    "Agents": ("🤖", ("agent", "agents", "agentos", "hermes", "persona", "skill", "skills",
                     "scaffold", "codex", "mcp", "automation", "assistant", "llm", "media-manager")),
    "Career": ("🎓", ("career", "job", "jobs", "eb1a", "fde", "resume", "interview", "judging",
                     "fellowship", "fiet", "pccm", "promotion", "hiring", "offer")),
    "Writing": ("✍️", ("blog", "blogging", "writing", "hackernoon", "dzone", "content", "article",
                      "site", "website", "portfolio", "newsletter", "techie")),
    "Learning": ("📚", ("learn", "learning", "research", "course", "study", "deep-research",
                       "notes", "explorers", "reading", "infra")),
}
UNSORTED = ("Unsorted", "🗂️")

# Per-project glyphs for the "rich" style: first keyword hit wins.
PROJECT_GLYPHS: tuple[tuple[str, str], ...] = (
    ("award", "🎫"), ("flight", "🛫"), ("aviation", "🛩️"), ("ifr", "🛩️"), ("travel", "🧳"),
    ("robot", "🦾"), ("rover", "🛞"), ("print", "🖨️"), ("homelab", "🖥️"), ("tax", "🧾"),
    ("mortgage", "🏦"), ("finance", "📈"), ("home", "🏡"), ("garden", "🌱"), ("agent", "🧠"),
    ("hermes", "🪽"), ("blog", "📝"), ("site", "🌐"), ("website", "🌐"), ("job", "💼"),
    ("career", "💼"), ("eb1a", "📜"), ("research", "🔬"), ("fitness", "🏋️"), ("music", "🎵"),
    ("media", "🎬"), ("skill", "🧩"), ("scaffold", "🏗️"),
)

DATED_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOG_LINE = re.compile(r"^- \d{4}-\d{2}-\d{2}")


# ---------------------------------------------------------------- helpers
def today() -> str:
    return _dt.date.today().isoformat()


def stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "project"


def strip_emoji_prefix(name: str) -> str:
    """Drop leading non-ASCII glyphs and spaces (emoji prefixes) from a folder name."""
    i = 0
    while i < len(name) and (not name[i].isascii() or name[i] == " "):
        i += 1
    return name[i:] or name


def words(*texts: str) -> set[str]:
    out: set[str] = set()
    for t in texts:
        t = (t or "").lower()
        out.update(re.findall(r"[a-z0-9]+", t))
        out.update(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", t))
    return out


def est_tokens(nbytes: int) -> int:
    return (nbytes + 3) // 4


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def emit(obj, as_json: bool, text: str) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False) if as_json else text)


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render(template: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        template = template.replace("{{" + k + "}}", v)
    return template


def upsert_block(text: str, start: str, end: str, body: str) -> str:
    block = f"{start}\n{body.rstrip()}\n{end}"
    if start in text and end in text:
        pre, rest = text.split(start, 1)
        _, post = rest.split(end, 1)
        return pre + block + post
    return text.rstrip() + "\n\n" + block + "\n"


def backup(path: Path, archive_dir: Path) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    dst = archive_dir / f"{path.stem}-{stamp()}{path.suffix}"
    shutil.copy2(path, dst)
    return dst


# ---------------------------------------------------------------- tiers & emoji
def score_tiers(*texts: str) -> list[tuple[str, int]]:
    w = words(*texts)
    scores = [(tier, sum(1 for k in kws if k in w)) for tier, (_, kws) in TIERS.items()]
    return sorted([s for s in scores if s[1] > 0], key=lambda s: -s[1])


def pick_tier(*texts: str) -> tuple[str, str, str]:
    """Return (tier, emoji, rationale). Ambiguous on a tie or no hits."""
    scores = score_tiers(*texts)
    if not scores:
        return UNSORTED[0], UNSORTED[1], "no keyword hits"
    if len(scores) > 1 and scores[0][1] == scores[1][1]:
        return UNSORTED[0], UNSORTED[1], f"tie: {scores[0][0]} vs {scores[1][0]}"
    tier = scores[0][0]
    return tier, TIERS[tier][0], f"{scores[0][1]} keyword hit(s)"


def pick_project_glyph(*texts: str) -> str | None:
    w = words(*texts)
    for key, glyph in PROJECT_GLYPHS:
        if key in w:
            return glyph
    return None


def display_name(slug: str, style: str, tier_emoji: str | None, project_emoji: str | None) -> str:
    if style == "plain" or not tier_emoji:
        return slug
    if style == "rich" and project_emoji and project_emoji != tier_emoji:
        return f"{tier_emoji} {project_emoji} {slug}"
    return f"{tier_emoji} {slug}"


# ---------------------------------------------------------------- intake
def project_template() -> dict:
    return {
        "name": "my-project",
        "goal": "Q1: what this project must achieve",
        "done": "Q1: how you will know it is done",
        "horizon": "Q1: e.g. 2026-12-31 or ongoing",
        "never": ["Q2: things the agent must never do here"],
        "caveats": ["Q2: context not written anywhere else"],
        "stakes": [],
        "git": {"push": True, "visibility": "private", "ignore_context": True},
        "tier": None,
        "emoji": None,
        "_help": {
            "stakes": f"Q3: any of {list(STAKES)}; empty = low stakes",
            "git": "Q4: push to GitHub? visibility private|public; ignore_context keeps context/ out of git",
        },
    }


def harness_template() -> dict:
    return {
        "reply_style": "terse",
        "naming": "name-vN",
        "stakes_floor": "low",
        "git_default": {"push": True, "visibility": "private", "ignore_context": True},
        "name_style": "tier",
        "_help": {
            "reply_style": f"Q1: one of {list(REPLY_STYLES)}",
            "naming": f"Q2: one of {list(NAMING)}",
            "stakes_floor": "Q3: low | high (high = every deliverable is P2)",
            "git_default": "Q4: default for new projects",
            "name_style": f"folder display style, one of {list(NAME_STYLES)}",
        },
    }


def validate_project(intake: dict) -> list[str]:
    errs = []
    if not str(intake.get("goal", "")).strip():
        errs.append("goal (Q1) is required")
    bad = [s for s in intake.get("stakes", []) if s not in STAKES]
    if bad:
        errs.append(f"unknown stakes {bad}; allowed {list(STAKES)}")
    vis = (intake.get("git") or {}).get("visibility", "private")
    if vis not in ("private", "public"):
        errs.append("git.visibility must be private|public")
    if len(intake.get("never", [])) > 15 or len(intake.get("caveats", [])) > 15:
        errs.append("never/caveats capped at 15 items each")
    return errs


def validate_harness(h: dict) -> list[str]:
    errs = []
    if h.get("reply_style", "terse") not in REPLY_STYLES:
        errs.append(f"reply_style must be one of {list(REPLY_STYLES)}")
    if h.get("naming", "name-vN") not in NAMING:
        errs.append(f"naming must be one of {list(NAMING)}")
    if h.get("stakes_floor", "low") not in ("low", "high"):
        errs.append("stakes_floor must be low|high")
    if h.get("name_style", "tier") not in NAME_STYLES:
        errs.append(f"name_style must be one of {list(NAME_STYLES)}")
    return errs


def default_tier(intake: dict, harness: dict | None = None) -> str:
    if intake.get("stakes") or (harness or {}).get("stakes_floor") == "high":
        return "P2"
    return "P1"


def clean(s: str, limit: int = 240) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip().lstrip("#").strip()
    return s[:limit]


def intake_block(intake: dict, harness: dict | None = None) -> str:
    g = intake.get("git") or {}
    lines = [
        "## Project intake (managed by scaffold-skill — edit via `refine`)",
        f"- Goal: {clean(intake.get('goal', ''))}",
        f"- Done when: {clean(intake.get('done', '') or 'not set')}",
        f"- Horizon: {clean(intake.get('horizon', '') or 'ongoing')}",
        f"- Stakes: {', '.join(intake.get('stakes') or []) or 'low'} → default tier "
        f"**{default_tier(intake, harness)}** for deliverables",
    ]
    for label, key in (("Never", "never"), ("Caveats", "caveats")):
        items = [clean(x) for x in (intake.get(key) or []) if clean(x) and not clean(x).startswith("Q2:")]
        if items:
            lines.append(f"- {label}:")
            lines.extend(f"  - {x}" for x in items[:15])
    push = "push" if g.get("push", True) else "local only"
    ctx = "context/ ignored" if g.get("ignore_context", True) else "context/ tracked"
    lines.append(f"- Git: {push}, {g.get('visibility', 'private')}, {ctx}")
    return "\n".join(lines)


# ---------------------------------------------------------------- harness
def codex_home(arg: str | None) -> Path:
    return Path(arg or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()


def harness_body(h: dict) -> str:
    g = h.get("git_default") or {}
    git = (f"{'push' if g.get('push', True) else 'local only'}, {g.get('visibility', 'private')}, "
           f"{'context/ ignored' if g.get('ignore_context', True) else 'context/ tracked'}")
    return render(read(HARNESS_ASSET), {
        "REPLY_STYLE": h.get("reply_style", "terse"),
        "NAMING": h.get("naming", "name-vN"),
        "STAKES_FLOOR": h.get("stakes_floor", "low"),
        "GIT_DEFAULT": git,
        "NAME_STYLE": h.get("name_style", "tier"),
    })


CONFIG_SNIPPET = "[agents]\nmax_concurrent_threads_per_session = 4\n"


def cmd_harness(a) -> int:
    home = codex_home(a.codex_home)
    prof_path = home / "scaffold-skill" / "profile.json"
    if a.action == "show":
        if not prof_path.exists():
            emit({"status": "missing", "path": str(prof_path)}, a.json,
                 f"harness profile: MISSING ({prof_path}) — run `harness init --answers FILE`")
            return 1
        prof = json.loads(read(prof_path))
        emit({"status": "ok", "profile": prof}, a.json, json.dumps(prof, indent=2, ensure_ascii=False))
        return 0
    h = {**harness_template(), **load_json(a.answers)}
    h.pop("_help", None)
    errs = validate_harness(h)
    if errs:
        emit({"status": "invalid", "errors": errs}, a.json, "invalid answers:\n- " + "\n- ".join(errs))
        return 2
    agents_md = home / "AGENTS.md"
    old = read(agents_md) if agents_md.exists() else ""
    new = upsert_block(old, HARNESS_START, HARNESS_END, harness_body(h))
    actions = [{"path": str(agents_md), "op": "upsert-block" if old else "create"},
               {"path": str(prof_path), "op": "write"}]
    for src in sorted(AGENT_ASSETS.glob("*.toml")):
        dst = home / "agents" / src.name
        actions.append({"path": str(dst), "op": "skip (exists)" if dst.exists() else "create"})
    cfg = home / "config.toml"
    cfg_has_agents = cfg.exists() and re.search(r"^\[agents\]", read(cfg), re.M)
    if a.write_config:
        actions.append({"path": str(cfg), "op": "skip ([agents] exists)" if cfg_has_agents else "append [agents]"})
    if a.dry_run:
        emit({"dry_run": True, "actions": actions, "block": harness_body(h)}, a.json,
             "DRY RUN\n" + "\n".join(f"  {x['op']:<22} {x['path']}" for x in actions)
             + "\n\n--- block ---\n" + harness_body(h))
        return 0
    home.mkdir(parents=True, exist_ok=True)
    if old and old != new:
        backup(agents_md, home / "scaffold-skill" / "backups")
    agents_md.write_text(new, encoding="utf-8")
    prof_path.parent.mkdir(parents=True, exist_ok=True)
    prof_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (home / "agents").mkdir(exist_ok=True)
    for src in sorted(AGENT_ASSETS.glob("*.toml")):
        dst = home / "agents" / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
    if a.write_config and not cfg_has_agents:
        with cfg.open("a", encoding="utf-8") as f:
            f.write("\n" + CONFIG_SNIPPET)
    note = "" if a.write_config else f"\nOptional, add to {cfg}:\n{CONFIG_SNIPPET}"
    emit({"status": "ok", "actions": actions}, a.json,
         "\n".join(f"  {x['op']:<22} {x['path']}" for x in actions) + note)
    return 0


def load_harness(home_arg: str | None) -> dict:
    p = codex_home(home_arg) / "scaffold-skill" / "profile.json"
    try:
        return json.loads(read(p))
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- scaffold
def gitignore_text(intake: dict) -> str:
    text = read(TEMPLATES / "gitignore.txt")
    if (intake.get("git") or {}).get("ignore_context", True):
        text += "context/\n"
    return text


def plan_scaffold(root: Path, intake: dict, harness: dict, title: str) -> list[tuple[str, Path, str | None]]:
    """Return [(op, path, content)]; op in mkdir|create|skip."""
    name = intake.get("name") or strip_emoji_prefix(root.name)
    values = {"NAME": name, "TITLE": title, "DATE": today(), "TIER": default_tier(intake, harness),
              "NEXT": "fill SKILLS.md procedures; add inputs to context/ and run `scaffold.py index`."}
    block = f"{INTAKE_START}\n{intake_block(intake, harness)}\n{INTAKE_END}"
    files = {
        "AGENTS.md": render(read(TEMPLATES / "AGENTS.md"), {**values, "INTAKE_BLOCK": block}),
        "STATE.md": render(read(TEMPLATES / "STATE.md"), values),
        "REFERENCES.md": render(read(TEMPLATES / "REFERENCES.md"), values),
        "SKILLS.md": render(read(TEMPLATES / "SKILLS.md"), values),
        ".gitignore": gitignore_text(intake),
    }
    plan: list[tuple[str, Path, str | None]] = []
    for d in DIRS:
        p = root / d
        plan.append(("skip" if p.is_dir() else "mkdir", p, None))
    for fname, content in files.items():
        p = root / fname
        plan.append(("skip" if p.exists() else "create", p, content))
    return plan


def execute(plan) -> None:
    for op, p, content in plan:
        if op == "mkdir":
            p.mkdir(parents=True, exist_ok=True)
        elif op == "create":
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "x", encoding="utf-8") as f:  # "x" = never overwrite
                f.write(content or "")


def report_plan(plan, root: Path, dry: bool) -> str:
    head = "DRY RUN — nothing written" if dry else "applied"
    rows = [f"  {'SKIP (exists)' if op == 'skip' else op.upper():<14} {p.relative_to(root) if p != root else '.'}"
            for op, p, _ in plan]
    return f"{head}: {root}\n" + "\n".join(rows)


def resolve_intake(a) -> tuple[dict, list[str]]:
    intake = {**project_template(), **load_json(getattr(a, "intake", None))}
    intake.pop("_help", None)
    return intake, validate_project(intake)


def cmd_apply(a) -> int:
    root = Path(a.path).expanduser().resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    intake, errs = resolve_intake(a)
    if errs:
        emit({"status": "invalid", "errors": errs}, a.json, "invalid intake:\n- " + "\n- ".join(errs))
        return 2
    harness = load_harness(a.codex_home)
    name = intake.get("name") if intake.get("name") != "my-project" else strip_emoji_prefix(root.name)
    intake["name"] = name
    title = root.name if root.name != name else name
    plan = plan_scaffold(root, intake, harness, title)
    if not a.dry_run:
        execute(plan)
    emit({"root": str(root), "dry_run": a.dry_run,
          "actions": [{"op": op, "path": str(p)} for op, p, _ in plan]}, a.json,
         report_plan(plan, root, a.dry_run))
    return 0


def cmd_new(a) -> int:
    parent = Path(a.parent).expanduser().resolve()
    intake, errs = resolve_intake(a)
    intake["name"] = a.name
    if errs:
        emit({"status": "invalid", "errors": errs}, a.json, "invalid intake:\n- " + "\n- ".join(errs))
        return 2
    harness = load_harness(a.codex_home)
    style = a.name_style or harness.get("name_style", "tier")
    tier, tier_emoji, why = (intake["tier"], TIERS[intake["tier"]][0], "pinned") \
        if intake.get("tier") in TIERS else pick_tier(a.name, intake.get("goal", ""))
    proj_emoji = a.emoji or intake.get("emoji") or pick_project_glyph(a.name, intake.get("goal", ""))
    slug = slugify(a.name)
    folder = display_name(slug, style, tier_emoji, proj_emoji)
    root = parent / folder
    if root.exists() and any(root.iterdir()):
        print(f"exists and not empty: {root} — use `apply` instead", file=sys.stderr)
        return 2
    title = folder
    plan = [("skip" if root.is_dir() else "mkdir", root, None)] + plan_scaffold(root, intake, harness, title)
    if not a.dry_run:
        execute(plan)
    emit({"root": str(root), "folder": folder, "slug": slug, "tier": tier, "tier_emoji": tier_emoji,
          "tier_rationale": why, "project_emoji": proj_emoji, "dry_run": a.dry_run,
          "actions": [{"op": op, "path": str(p)} for op, p, _ in plan]}, a.json,
         f"folder: {folder}  (tier {tier} {tier_emoji}: {why}; git repo name: {slug})\n"
         + report_plan(plan, root, a.dry_run))
    return 0


def cmd_refine(a) -> int:
    root = Path(a.path).expanduser().resolve()
    agents = root / "AGENTS.md"
    if not agents.exists():
        print("AGENTS.md missing — run `apply` first", file=sys.stderr)
        return 2
    intake, errs = resolve_intake(a)
    if errs:
        emit({"status": "invalid", "errors": errs}, a.json, "invalid intake:\n- " + "\n- ".join(errs))
        return 2
    old = read(agents)
    new = upsert_block(old, INTAKE_START, INTAKE_END, intake_block(intake, load_harness(a.codex_home)))
    if new == old:
        emit({"status": "unchanged"}, a.json, "unchanged")
        return 0
    if a.dry_run:
        emit({"dry_run": True, "new_block": intake_block(intake)}, a.json, "DRY RUN — new block:\n"
             + intake_block(intake))
        return 0
    bk = backup(agents, root / "work" / "archive")
    agents.write_text(new, encoding="utf-8")
    emit({"status": "updated", "backup": str(bk)}, a.json, f"updated AGENTS.md block; backup: {bk}")
    return 0


# ---------------------------------------------------------------- index / rotate
def ref_rows(text: str) -> set[str]:
    rows = set()
    for line in text.splitlines():
        m = re.match(r"^\|\s*`?([^|`]+?)`?\s*\|", line)
        if m and m.group(1).strip() not in ("path", "---"):
            rows.add(m.group(1).strip())
    return rows


def indexable(root: Path) -> list[Path]:
    out = []
    ctx = root / "context"
    if ctx.is_dir():
        out += [p for p in sorted(ctx.rglob("*")) if p.is_file() and not p.name.startswith(".")]
    for extra in ("work/state-archive.md", "MEMORY.md"):
        if (root / extra).is_file():
            out.append(root / extra)
    return out


def cmd_index(a) -> int:
    root = Path(a.path).expanduser().resolve()
    ref = root / "REFERENCES.md"
    if not ref.exists():
        print("REFERENCES.md missing — run `apply` first", file=sys.stderr)
        return 2
    text = read(ref)
    have = ref_rows(text)
    files = {str(p.relative_to(root)): p for p in indexable(root)}
    added = [rel for rel in files if rel not in have]
    stale = sorted(h for h in have if not (root / h).exists())
    if added and not a.dry_run:
        rows = "".join(f"| {rel} | TODO | TODO | {est_tokens(files[rel].stat().st_size)} |\n" for rel in added)
        ref.write_text(text.rstrip("\n") + "\n" + rows, encoding="utf-8")
    emit({"added": added, "stale": stale, "dry_run": a.dry_run}, a.json,
         f"added {len(added)} row(s){' (dry run)' if a.dry_run else ''}"
         + "".join(f"\n  + {r}" for r in added)
         + "".join(f"\n  ! stale: {s}" for s in stale))
    return 0


def split_state(text: str) -> tuple[str, list[str], str]:
    """Return (head_through_log_header, log_lines, tail_after_log)."""
    m = re.search(r"^## Log[^\n]*\n", text, re.M)
    if not m:
        return text, [], ""
    head, rest = text[:m.end()], text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    body, tail = (rest[:n.start()], rest[n.start():]) if n else (rest, "")
    return head, body.splitlines(), tail


def cmd_rotate(a) -> int:
    root = Path(a.path).expanduser().resolve()
    state = root / "STATE.md"
    if not state.exists():
        print("STATE.md missing", file=sys.stderr)
        return 2
    text = read(state)
    size = len(text.encode("utf-8"))
    if size <= a.max_bytes and not a.force:
        emit({"status": "under-budget", "bytes": size}, a.json, f"STATE.md {size} B ≤ {a.max_bytes} B — nothing to do")
        return 0
    head, log, tail = split_state(text)
    entries: list[list[str]] = []
    for line in log:
        if LOG_LINE.match(line) or not entries:
            entries.append([line])
        else:
            entries[-1].append(line)
    entries = [e for e in entries if any(x.strip() for x in e)]
    # newest-first if the first dated entry sorts after the last; keep the newest `keep`.
    dates = [e[0][2:12] for e in entries if LOG_LINE.match(e[0])]
    newest_first = len(dates) > 1 and dates[0] > dates[-1]
    keep_n = max(a.keep, 0)
    if len(entries) <= keep_n:
        emit({"status": "nothing-to-rotate", "entries": len(entries)}, a.json,
             f"only {len(entries)} log entries — nothing to rotate (shrink ## Now/Decisions instead)")
        return 0
    if newest_first:
        keep, move = entries[:keep_n], entries[keep_n:]
    else:
        keep, move = entries[len(entries) - keep_n:], entries[:len(entries) - keep_n]
    if a.dry_run:
        emit({"dry_run": True, "move": len(move), "keep": len(keep)}, a.json,
             f"DRY RUN — would move {len(move)} entr(ies), keep {len(keep)}")
        return 0
    archive = root / "work" / "state-archive.md"
    archive.parent.mkdir(parents=True, exist_ok=True)
    moved_text = "\n".join("\n".join(e) for e in move) + "\n"
    with archive.open("a", encoding="utf-8") as f:
        if archive.stat().st_size == 0:
            f.write("# STATE archive — rotated log entries\n\n")
        f.write(f"## Rotated {today()}\n{moved_text}\n")
    note = f"- {today()}: Rotated {len(move)} older log entries → work/state-archive.md"
    kept = [note] + ["\n".join(e) for e in keep] if newest_first else ["\n".join(e) for e in keep] + [note]
    state.write_text(head + "\n".join(kept) + "\n" + (("\n" + tail) if tail else ""), encoding="utf-8")
    ref = root / "REFERENCES.md"
    if ref.exists() and "work/state-archive.md" not in ref_rows(read(ref)):
        with ref.open("a", encoding="utf-8") as f:
            f.write(f"| work/state-archive.md | rotated STATE log | history questions | "
                    f"{est_tokens(archive.stat().st_size)} |\n")
    new_size = len(read(state).encode("utf-8"))
    emit({"status": "rotated", "moved": len(move), "kept": len(keep), "bytes_before": size,
          "bytes_after": new_size}, a.json, f"moved {len(move)} entries; STATE.md {size} B → {new_size} B")
    return 0


# ---------------------------------------------------------------- check
def git_root(p: Path) -> Path | None:
    for d in [p, *p.parents]:
        if (d / ".git").exists():
            return d
    return None


def agents_chain_bytes(root: Path, home: Path) -> int:
    total = 0
    g = home / "AGENTS.override.md" if (home / "AGENTS.override.md").exists() else home / "AGENTS.md"
    if g.exists():
        total += g.stat().st_size
    top = git_root(root) or root
    chain, cur = [top], top
    for part in root.relative_to(top).parts:
        cur = cur / part
        chain.append(cur)
    for d in chain:
        for fname in ("AGENTS.override.md", "AGENTS.md"):
            if (d / fname).exists():
                total += (d / fname).stat().st_size
                break
    return total


def now_lines(state_text: str) -> int:
    m = re.search(r"^## Now[^\n]*\n(.*?)(?=^## |\Z)", state_text, re.M | re.S)
    return len([x for x in m.group(1).splitlines() if x.strip()]) if m else -1


def run_checks(root: Path, home: Path) -> list[dict]:
    res = []

    def add(cid, ok, detail, level="FAIL"):
        res.append({"id": cid, "status": "OK" if ok else level, "detail": detail})

    missing_dirs = [d for d in DIRS if not (root / d).is_dir()]
    add("C01_DIRS", not missing_dirs, f"missing: {missing_dirs}" if missing_dirs else "context/ work/ output/")
    missing_files = [f for f in CONTROL_FILES if not (root / f).is_file()]
    add("C02_CONTROL_FILES", not missing_files, f"missing: {missing_files}" if missing_files else "all present")
    agents_text = read(root / "AGENTS.md") if (root / "AGENTS.md").exists() else ""
    add("C03_INTAKE_BLOCK", INTAKE_START in agents_text, "managed intake block present"
        if INTAKE_START in agents_text else "no intake block — run `refine`")
    n = len(agents_text.splitlines())
    add("C04_AGENTS_BUDGET", 0 < n <= AGENTS_MAX_LINES, f"{n} lines (≤ {AGENTS_MAX_LINES})", "WARN")
    st = root / "STATE.md"
    if st.exists():
        stext = read(st)
        sz, nl = len(stext.encode("utf-8")), now_lines(stext)
        add("C05_STATE_BUDGET", sz <= STATE_MAX_BYTES and 0 <= nl <= NOW_MAX_LINES,
            f"{sz} B (≤ {STATE_MAX_BYTES}), ## Now {nl} lines (≤ {NOW_MAX_LINES})"
            + ("" if nl >= 0 else " — no ## Now section"), "WARN")
    else:
        add("C05_STATE_BUDGET", False, "STATE.md missing")
    ref = root / "REFERENCES.md"
    if ref.exists():
        have = ref_rows(read(ref))
        unindexed = [str(p.relative_to(root)) for p in indexable(root) if str(p.relative_to(root)) not in have]
        add("C06_REFERENCES_COVERAGE", not unindexed,
            f"{len(unindexed)} unindexed — run `index`" if unindexed else "all inputs indexed", "WARN")
    else:
        add("C06_REFERENCES_COVERAGE", False, "REFERENCES.md missing")
    gi = root / ".gitignore"
    lines = {x.strip() for x in read(gi).splitlines()} if gi.exists() else set()
    need = {"output/", *SECRET_PATTERNS}
    miss = sorted(need - lines)
    add("C07_GITIGNORE", not miss, f"missing patterns: {miss}" if miss else "output/ + secrets ignored")
    dup = [f for f in LEGACY_FILES if (root / f).exists()]
    add("C08_NO_DUPLICATE_CHARTER", not dup,
        f"legacy charter files present: {dup} — index or fold into AGENTS/STATE" if dup else "single charter", "WARN")
    chain = agents_chain_bytes(root, home)
    add("C09_CODEX_DOC_LIMIT", chain < 0.8 * CODEX_DOC_LIMIT,
        f"merged AGENTS chain {chain} B (warn ≥ 80% of {CODEX_DOC_LIMIT}; Codex truncates past the limit)", "WARN")
    return res


def cmd_check(a) -> int:
    root = Path(a.path).expanduser().resolve()
    res = run_checks(root, codex_home(a.codex_home))
    fails = sum(r["status"] == "FAIL" for r in res)
    warns = sum(r["status"] == "WARN" for r in res)
    emit({"root": str(root), "checks": res, "fail": fails, "warn": warns}, a.json,
         f"check: {root}\n" + "\n".join(f"  [{r['status']:<4}] {r['id']:<26} {r['detail']}" for r in res)
         + f"\nsummary: {fails} fail, {warns} warn")
    return 1 if fails else 0


# ---------------------------------------------------------------- route
def route(stakes: list[str], kind: str, items: int, sources: int, decision: bool,
          floor: str = "low", asked: str | None = None) -> dict:
    kind = kind.lower()
    high = bool(stakes) or floor == "high"
    if asked == "fan-out" or items >= 5 or sources >= 3:
        tier = "P3"
    elif kind in ("trivial", "edit", "rename", "state", "maintenance") and not high and asked is None:
        tier = "P0"
    elif high or asked in ("verify", "challenge") or kind == "outbound":
        tier = "P2"
    else:
        tier = "P1"
    agents: list[str] = []
    if tier == "P3":
        agents.append(f"workers≤4 ({'explorer' if kind == 'code' else 'default'})")
    if tier in ("P2", "P3") and (high or asked == "verify" or kind == "outbound"):
        agents.append("codex review" if kind == "code" else "verifier")
    if (decision and high) or asked == "challenge":
        agents.append("challenger")
    checks = {"P0": "none", "P1": "deterministic checks + self-checklist",
              "P2": "deterministic checks + claims ledger + verifier; REFUTED blocks output/",
              "P3": "worker summaries only; P2 rule on the final artifact"}[tier]
    return {"tier": tier, "spawn": bool(agents), "agents": agents, "verification": checks,
            "stage_in_work_first": tier != "P0"}


def cmd_route(a) -> int:
    floor = load_harness(a.codex_home).get("stakes_floor", "low")
    stakes = [s for s in (a.stakes or "").split(",") if s]
    bad = [s for s in stakes if s not in STAKES]
    if bad:
        print(f"unknown stakes {bad}; allowed {list(STAKES)}", file=sys.stderr)
        return 2
    r = route(stakes, a.kind, a.items, a.sources, a.decision, floor, a.asked)
    emit(r, a.json, f"{r['tier']} · agents: {', '.join(r['agents']) or 'none'} · {r['verification']}")
    return 0


# ---------------------------------------------------------------- onboard
def generation(d: Path) -> str:
    has = {f: (d / f).is_file() for f in CONTROL_FILES + LEGACY_FILES}
    if has["AGENTS.md"] and has["STATE.md"]:
        return "standard"
    if has["MEMORY.md"]:
        return "legacy-memory"
    if any(has.values()):
        return "partial"
    return "bare"


def control_bytes(d: Path) -> int:
    return sum((d / f).stat().st_size for f in CONTROL_FILES + LEGACY_FILES if (d / f).is_file())


def file_hash(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def is_tier_dir(name: str) -> bool:
    bare = strip_emoji_prefix(name)
    return bare in TIERS or bare == UNSORTED[0]


def inventory(root: Path) -> list[dict]:
    projects = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith((".", "_")):
            continue
        if is_tier_dir(d.name):
            for c in sorted(d.iterdir()):
                if c.is_dir() and not c.name.startswith((".", "_")):
                    projects.append((c, strip_emoji_prefix(d.name)))
        else:
            projects.append((d, None))
    out = []
    for d, current_tier in projects:
        cb = control_bytes(d)
        snippet = ""
        for f in ("AGENTS.md", "CLAUDE.md", "MEMORY.md"):
            if (d / f).is_file():
                snippet += read(d / f)[:2000] + " "
        out.append({
            "path": str(d), "name": d.name, "slug": slugify(strip_emoji_prefix(d.name)),
            "dated": bool(DATED_DIR.match(d.name)), "generation": generation(d),
            "control_bytes": cb, "est_tokens_per_session": est_tokens(cb),
            "current_tier": current_tier, "_text": snippet,
            "_hash": file_hash(d / "AGENTS.md") or file_hash(d / "CLAUDE.md"),
        })
    return out


def propose(root: Path, style: str) -> dict:
    inv = inventory(root)
    by_slug: dict[str, list[str]] = {}
    by_hash: dict[str, list[str]] = {}
    for p in inv:
        if p["dated"]:
            continue
        by_slug.setdefault(p["slug"], []).append(p["name"])
        if p["_hash"]:
            by_hash.setdefault(p["_hash"], []).append(p["name"])
    dups = [v for v in by_slug.values() if len(v) > 1] + [v for v in by_hash.values() if len(v) > 1]
    dup_sets = []
    for v in dups:
        s = sorted(set(v))
        if len(s) > 1 and s not in dup_sets:
            dup_sets.append(s)
    dup_names = {n for s in dup_sets for n in s}
    actions, ambiguous, tiers_used = [], [], {}
    for p in inv:
        if p["dated"]:
            actions.append({"op": "review", "path": p["path"], "reason": "dated run folder (scheduled output?)"})
            continue
        tier, emoji, why = pick_tier(p["slug"], p["_text"][:600])
        p.update(proposed_tier=tier, tier_emoji=emoji, tier_rationale=why)
        if tier == UNSORTED[0]:
            ambiguous.append({"name": p["name"], "reason": why})
        tiers_used.setdefault(tier, []).append(p["name"])
        if p["name"] in dup_names:
            actions.append({"op": "review", "path": p["path"], "reason": "possible duplicate — decide which survives"})
            continue
        glyph = pick_project_glyph(p["slug"], p["_text"][:600])
        folder = display_name(p["slug"], style, emoji, glyph)
        tier_dir = root / f"{emoji} {tier}" if style != "plain" else root / tier
        dst = tier_dir / folder
        if Path(p["path"]) != dst:
            actions.append({"op": "move", "src": p["path"], "dst": str(dst), "tier": tier})
        if p["generation"] in ("legacy-memory", "partial", "bare"):
            actions.append({"op": "convert", "path": str(dst), "from": p["generation"]})
    for p in inv:
        p.pop("_text", None)
        p.pop("_hash", None)
    total = sum(p["est_tokens_per_session"] for p in inv)
    return {
        "root": str(root), "style": style, "projects": inv,
        "proposed_tiers": {t: {"emoji": TIERS[t][0] if t in TIERS else UNSORTED[1],
                               "projects": sorted(v)} for t, v in sorted(tiers_used.items())},
        "duplicates": dup_sets, "ambiguous": ambiguous, "actions": actions,
        "summary": {"projects": len(inv), "dated": sum(p["dated"] for p in inv),
                    "generations": {g: sum(p["generation"] == g for p in inv)
                                    for g in ("standard", "legacy-memory", "partial", "bare")},
                    "est_tokens_per_session_total": total},
    }


def apply_plan(plan: dict, yes: bool) -> list[dict]:
    done = []
    for act in plan.get("actions", []):
        if act["op"] == "move":
            src, dst = Path(act["src"]), Path(act["dst"])
            if not src.exists():
                done.append({**act, "result": "skip (src missing)"})
            elif dst.exists():
                done.append({**act, "result": "skip (dst exists)"})
            elif not yes:
                done.append({**act, "result": "would move"})
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.rename(src, dst)
                done.append({**act, "result": "moved"})
        elif act["op"] == "convert":
            path = Path(act["path"])
            if not path.is_dir():
                done.append({**act, "result": "skip (not moved yet)" if yes else "would convert"})
                continue
            intake = {**project_template(), "name": strip_emoji_prefix(path.name),
                      "goal": "TODO — migrated project; run `refine` with the 4-question intake"}
            intake.pop("_help", None)
            sp = plan_scaffold(path, intake, {}, path.name)
            if yes:
                execute(sp)
                created = [str(p.name) for op, p, _ in sp if op != "skip"]
                done.append({**act, "result": f"created {created}"})
            else:
                done.append({**act, "result": "would create " + str([p.name for op, p, _ in sp if op != "skip"])})
        else:
            done.append({**act, "result": "manual review"})
    return done


def cmd_onboard(a) -> int:
    if a.apply_plan:
        plan = load_json(a.apply_plan)
        res = apply_plan(plan, a.yes)
        emit({"applied": a.yes, "results": res}, a.json,
             ("APPLIED" if a.yes else "DRY RUN (pass --yes to execute)") + "\n"
             + "\n".join(f"  {r['op']:<8} {r.get('src', r.get('path'))} → {r.get('dst', '')}  [{r['result']}]"
                         for r in res))
        return 0
    root = Path(a.root).expanduser().resolve()
    style = a.name_style or load_harness(a.codex_home).get("name_style", "tier")
    prop = propose(root, style)
    if a.plan_out:
        Path(a.plan_out).write_text(json.dumps(prop, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    s = prop["summary"]
    lines = [f"onboard: {root}  ({s['projects']} folders, {s['dated']} dated, "
             f"~{s['est_tokens_per_session_total']} tokens/session in control files)",
             "generations: " + ", ".join(f"{k}={v}" for k, v in s["generations"].items()), "", "proposed tiers:"]
    for t, v in prop["proposed_tiers"].items():
        lines.append(f"  {v['emoji']} {t}: {', '.join(v['projects'])}")
    heavy = sorted(prop["projects"], key=lambda p: -p["est_tokens_per_session"])[:5]
    lines.append("\nheaviest per-session reads:")
    lines += [f"  ~{p['est_tokens_per_session']:>6} tok  {p['name']} ({p['generation']})" for p in heavy if p["control_bytes"]]
    if prop["duplicates"]:
        lines.append("\nduplicates: " + "; ".join(" = ".join(d) for d in prop["duplicates"]))
    if prop["ambiguous"]:
        lines.append("ambiguous: " + ", ".join(f"{x['name']} ({x['reason']})" for x in prop["ambiguous"]))
    lines.append(f"\n{sum(x['op'] == 'move' for x in prop['actions'])} move(s), "
                 f"{sum(x['op'] == 'convert' for x in prop['actions'])} convert(s), "
                 f"{sum(x['op'] == 'review' for x in prop['actions'])} review(s) proposed"
                 + (f" → plan written to {a.plan_out}" if a.plan_out else ""))
    emit(prop, a.json, "\n".join(lines))
    return 0


# ---------------------------------------------------------------- cli
def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--codex-home", help="override ~/.codex (or $CODEX_HOME)")
    p = argparse.ArgumentParser(prog="scaffold.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    _add = sub.add_parser
    sub.add_parser = lambda *x, **k: _add(*x, parents=[common], **k)  # type: ignore[method-assign]

    h = sub.add_parser("harness", help="show / init the harness profile")
    h.add_argument("action", choices=("show", "init"))
    h.add_argument("--answers", help="harness answers JSON (from `template --level harness`)")
    h.add_argument("--dry-run", action="store_true")
    h.add_argument("--write-config", action="store_true", help="append [agents] cap to config.toml if absent")

    t = sub.add_parser("template", help="print an intake skeleton")
    t.add_argument("--level", choices=("project", "harness"), default="project")

    n = sub.add_parser("new", help="create + scaffold a new project folder")
    n.add_argument("name")
    n.add_argument("--parent", default=".")
    n.add_argument("--intake")
    n.add_argument("--name-style", choices=NAME_STYLES)
    n.add_argument("--emoji", help="pin the per-project glyph (rich style)")
    n.add_argument("--dry-run", action="store_true")

    for cmd, hlp in (("apply", "scaffold an existing folder"), ("refine", "upsert the intake block")):
        x = sub.add_parser(cmd, help=hlp)
        x.add_argument("path")
        x.add_argument("--intake")
        x.add_argument("--dry-run", action="store_true")

    c = sub.add_parser("check", help="read-only audit")
    c.add_argument("path")

    i = sub.add_parser("index", help="index context/ + archives in REFERENCES.md")
    i.add_argument("path")
    i.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("rotate", help="rotate STATE.md log")
    r.add_argument("path")
    r.add_argument("--max-bytes", type=int, default=STATE_MAX_BYTES)
    r.add_argument("--keep", type=int, default=10)
    r.add_argument("--force", action="store_true")
    r.add_argument("--dry-run", action="store_true")

    ro = sub.add_parser("route", help="classify a task into P0-P3")
    ro.add_argument("--stakes", help=f"comma list of {','.join(STAKES)}")
    ro.add_argument("--kind", default="deliverable", help="trivial|edit|deliverable|outbound|code|research")
    ro.add_argument("--items", type=int, default=1)
    ro.add_argument("--sources", type=int, default=1)
    ro.add_argument("--decision", action="store_true")
    ro.add_argument("--asked", choices=("verify", "challenge", "fan-out"))

    o = sub.add_parser("onboard", help="inventory a projects root; propose tiers + migrations")
    o.add_argument("root", nargs="?", default=".")
    o.add_argument("--name-style", choices=NAME_STYLES)
    o.add_argument("--plan-out", help="write the proposal JSON here")
    o.add_argument("--apply-plan", help="execute a (reviewed) proposal JSON")
    o.add_argument("--yes", action="store_true", help="actually execute --apply-plan")

    sub.add_parser("version")
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "version":
        print(VERSION)
        return 0
    if a.cmd == "template":
        tpl = project_template() if a.level == "project" else harness_template()
        print(json.dumps(tpl, indent=2, ensure_ascii=False))
        return 0
    return {"harness": cmd_harness, "new": cmd_new, "apply": cmd_apply, "refine": cmd_refine,
            "check": cmd_check, "index": cmd_index, "rotate": cmd_rotate, "route": cmd_route,
            "onboard": cmd_onboard}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
