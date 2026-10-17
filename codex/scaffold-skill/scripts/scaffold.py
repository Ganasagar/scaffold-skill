#!/usr/bin/env python3
"""scaffold-skill: scaffold, audit and organize personal agent projects for Codex.

Stdlib only. Create missing charter files, update managed blocks and maintenance
files with backups, and apply preflighted migrations with private recovery journals.

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
import subprocess
from urllib.parse import quote, unquote

import safeio as IO
import migration as M
from pathlib import Path

VERSION = "0.2.0"
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
    IO.bounded(p, p.anchor)
    return p.read_text(encoding="utf-8", errors="replace")


def emit(obj, as_json: bool, text: str) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False) if as_json else text)


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError('JSON input must be an object')
        return data


def render(template: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        template = template.replace("{{" + k + "}}", v)
    return template


def upsert_block(text: str, start: str, end: str, body: str) -> str:
    block = f"{start}\n{body.rstrip()}\n{end}"
    if text.count(start) != text.count(end) or text.count(start) > 1 or (end in text and text.index(end) < text.index(start)):
        raise ValueError("ambiguous managed block markers")
    if start in text and end in text:
        pre, rest = text.split(start, 1)
        _, post = rest.split(end, 1)
        return pre + block + post
    return text.rstrip() + "\n\n" + block + "\n"


def backup(path: Path, archive_dir: Path) -> Path:
    return IO.backup(path, archive_dir)


def project_root(value):
    p = Path(value).expanduser().absolute()
    return IO.bounded(p, p.anchor)


def profile_for(a, root=None):
    user = load_harness(a.codex_home)
    if root:
        for d in (root, *root.parents):
            p = d / '.codex' / 'scaffold-skill' / 'profile.json'
            if p.is_file():
                IO.bounded(p, d)
                return {**user, **json.loads(read(p))}
    return user


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
        "git": {"push": False, "visibility": "private", "ignore_context": True},
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
        "git_default": {"push": False, "visibility": "private", "ignore_context": True},
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
    if not isinstance(intake, dict):
        return ['intake must be an object']
    goal = intake.get('goal')
    if not isinstance(goal, str) or not goal.strip() or goal.startswith(('Q1:', 'TODO')):
        errs.append('a meaningful goal is required; template placeholders are incomplete')
    for key in ('name', 'done', 'horizon'):
        if key in intake and not isinstance(intake[key], str):
            errs.append(f'{key} must be a string')
    for key in ('stakes', 'never', 'caveats'):
        vals = intake.get(key, [])
        if not isinstance(vals, list) or any(not isinstance(v, str) for v in vals):
            errs.append(f'{key} must be a list of strings')
        elif key == 'stakes' and any(v not in STAKES for v in vals):
            errs.append('unknown stakes')
        elif key != 'stakes' and len(vals) > 15:
            errs.append(f'{key} capped at 15 items')
    g = intake.get('git', {})
    if not isinstance(g, dict):
        errs.append('git must be an object')
    else:
        if g.get('visibility', 'private') not in ('private', 'public'):
            errs.append('git.visibility must be private|public')
        for key in ('push', 'ignore_context', 'ignore_work', 'ignore_output'):
            if key in g and not isinstance(g[key], bool):
                errs.append(f'git.{key} must be boolean')
    if intake.get('tier') is not None and (not isinstance(intake['tier'], str) or intake['tier'] not in TIERS):
        errs.append('unknown tier')
    emoji = intake.get('emoji')
    if emoji is not None and (not isinstance(emoji, str) or any(c in emoji for c in '/\\\n\r') or '..' in emoji):
        errs.append('emoji must be a path-safe string')
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
    push = "push only when requested" if g.get("push", False) else "local only"
    ctx = "context/ ignored" if g.get("ignore_context", True) else "context/ tracked"
    lines.append(f"- Git: {push}, {g.get('visibility', 'private')}, {ctx}")
    return "\n".join(lines)


# ---------------------------------------------------------------- harness
def codex_home(arg: str | None) -> Path:
    return Path(arg or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()


def harness_body(h: dict) -> str:
    g = h.get("git_default") or {}
    git = (f"{'push only when requested' if g.get('push', False) else 'local only'}, {g.get('visibility', 'private')}, "
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
    if a.scope == 'project':
        if not a.project:
            raise ValueError('--project is required for project-scoped harness setup')
        root = project_root(a.project)
        home = root / '.codex'
    else:
        home = project_root(str(codex_home(a.codex_home)))
        root = home
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
    git_errors = validate_project({"goal": "profile defaults", "git": h.get("git_default", {})})
    errs.extend(git_errors)
    if errs:
        emit({"status": "invalid", "errors": errs}, a.json, "invalid answers:\n- " + "\n- ".join(errs))
        return 2
    agents_md = root / 'AGENTS.md'
    old = read(agents_md) if agents_md.exists() else ''
    new = upsert_block(old, HARNESS_START, HARNESS_END, harness_body(h))
    edits = [(agents_md, new), (prof_path, json.dumps(h, indent=2) + '\n')]
    for src in sorted(AGENT_ASSETS.glob('*.toml')):
        dst = home / 'agents' / src.name
        if dst.exists() and read(dst) != read(src):
            raise ValueError(f'agent name collision: {dst}')
        edits.append((dst, read(src)))
    cfg = home / 'config.toml'
    if a.write_config:
        try:
            import tomllib
        except ImportError:
            raise ValueError('config edits require Python 3.11+; omit --write-config and edit TOML manually') from None
        previous = read(cfg) if cfg.exists() else ''
        parsed = tomllib.loads(previous)
        if 'agents' not in parsed:
            proposed = previous + '\n' + CONFIG_SNIPPET
            tomllib.loads(proposed)
            edits.append((cfg, proposed))
        elif not isinstance(parsed['agents'], dict):
            raise ValueError('agents config must be a table')
    result = IO.commit_files(root, edits, a.dry_run)
    emit(result, a.json, ('DRY RUN' if a.dry_run else 'APPLIED') + '\n' +
         '\n'.join(f['path'] for f in result['files']) +
         (f"\nRecovery: {result['journal']}" if result['journal'] else ''))
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
    for folder in ("work", "output"):
        if (intake.get("git") or {}).get("ignore_" + folder, True):
            text += folder + "/\n"
    if (intake.get("git") or {}).get("ignore_context", True):
        text += "context/\nresources/\n"
    return text


def plan_scaffold(root: Path, intake: dict, harness: dict, title: str, date: str | None = None) -> list[tuple[str, Path, str | None]]:
    """Return [(op, path, content)]; op in mkdir|create|skip."""
    IO.bounded(root, root.anchor)
    IO.bounded(root / ".scaffold-skill", root)
    name = intake.get("name") or strip_emoji_prefix(root.name)
    values = {"NAME": name, "TITLE": title, "DATE": date or today(), "TIER": default_tier(intake, harness), "ROUTING_TABLE": routing_table(),
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
        p = IO.bounded(root / d, root)
        if p.exists() and not p.is_dir():
            raise ValueError(f"expected directory: {p}")
        plan.append(("skip" if p.is_dir() else "mkdir", p, None))
    for fname, content in files.items():
        p = IO.bounded(root / fname, root)
        if p.exists() and not p.is_file():
            raise ValueError(f'expected regular file: {p}')
        if fname == '.gitignore':
            old = read(p) if p.exists() else ''
            content = upsert_block(old, '# scaffold-skill:privacy:start', '# scaffold-skill:privacy:end', content)
            op = 'skip' if old == content else ('replace' if p.exists() else 'create')
        else:
            op = 'skip' if p.exists() else 'create'
        plan.append((op, p, content))
    return plan


def execute(plan) -> None:
    # Validate all outputs before creating even a directory.
    paths = [p for _, p, _ in plan]
    root = Path(os.path.commonpath([str(p) for p in paths]))
    for op, p, content in plan:
        IO.bounded(p, p.anchor)
        if op == 'create' and p.exists():
            raise ValueError(f'create target exists: {p}')
        if op == 'mkdir' and p.exists() and not p.is_dir():
            raise ValueError(f'directory target is a file: {p}')
    for op, p, content in plan:
        if op == 'mkdir':
            p.mkdir(parents=True, exist_ok=True)
    return IO.commit_files(root, [(p, text) for op, p, text in plan if op in ('create', 'replace')])


def report_plan(plan, root: Path, dry: bool) -> str:
    head = "DRY RUN — nothing written" if dry else "applied"
    rows = [f"  {'SKIP (exists)' if op == 'skip' else op.upper():<14} {p.relative_to(root) if p != root else '.'}"
            for op, p, _ in plan]
    return f"{head}: {root}\n" + "\n".join(rows)


def resolve_intake(a) -> tuple[dict, list[str]]:
    supplied = load_json(getattr(a, 'intake', None))
    if not isinstance(supplied, dict):
        return {}, ['intake must be an object']
    intake = {**project_template(), **supplied}
    intake.pop("_help", None)
    return intake, validate_project(intake)


def cmd_apply(a) -> int:
    root = project_root(a.path)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    intake, errs = resolve_intake(a)
    if errs:
        emit({"status": "invalid", "errors": errs}, a.json, "invalid intake:\n- " + "\n- ".join(errs))
        return 2
    harness = profile_for(a, root)
    name = intake.get("name") if intake.get("name") != "my-project" else strip_emoji_prefix(root.name)
    intake["name"] = name
    title = root.name if root.name != name else name
    plan = plan_scaffold(root, intake, harness, title)
    result = execute(plan) if not a.dry_run else None
    emit({"recovery": result["journal"] if result else None, "root": str(root), "dry_run": a.dry_run,
          "actions": [{"op": op, "path": str(p), "content": text, "sha256": IO.digest(text.encode()) if text is not None else None} for op, p, text in plan]}, a.json,
         report_plan(plan, root, a.dry_run))
    return 0


def cmd_new(a) -> int:
    parent = project_root(a.parent)
    intake, errs = resolve_intake(a)
    intake["name"] = a.name
    if errs:
        emit({"status": "invalid", "errors": errs}, a.json, "invalid intake:\n- " + "\n- ".join(errs))
        return 2
    harness = profile_for(a, parent)
    style = a.name_style or harness.get("name_style", "tier")
    tier, tier_emoji, why = (intake["tier"], TIERS[intake["tier"]][0], "pinned") \
        if intake.get("tier") in TIERS else pick_tier(a.name, intake.get("goal", ""))
    if a.emoji and validate_project({**intake, "emoji": a.emoji}):
        raise ValueError("invalid emoji override")
    proj_emoji = a.emoji or intake.get("emoji") or pick_project_glyph(a.name, intake.get("goal", ""))
    slug = slugify(a.name)
    folder = display_name(slug, style, tier_emoji, proj_emoji)
    root = parent / folder
    if root.exists() and any(root.iterdir()):
        print(f"exists and not empty: {root} — use `apply` instead", file=sys.stderr)
        return 2
    title = folder
    plan = [("skip" if root.is_dir() else "mkdir", root, None)] + plan_scaffold(root, intake, harness, title)
    result = execute(plan) if not a.dry_run else None
    emit({"recovery": result["journal"] if result else None, "root": str(root), "folder": folder, "slug": slug, "tier": tier, "tier_emoji": tier_emoji,
          "tier_rationale": why, "project_emoji": proj_emoji, "dry_run": a.dry_run,
          "actions": [{"op": op, "path": str(p), "content": text, "sha256": IO.digest(text.encode()) if text is not None else None} for op, p, text in plan]}, a.json,
         f"folder: {folder}  (tier {tier} {tier_emoji}: {why}; git repo name: {slug})\n"
         + report_plan(plan, root, a.dry_run))
    return 0


def cmd_refine(a) -> int:
    root = project_root(a.path)
    agents = root / "AGENTS.md"
    if not agents.exists():
        print("AGENTS.md missing — run `apply` first", file=sys.stderr)
        return 2
    intake, errs = resolve_intake(a)
    if errs:
        emit({"status": "invalid", "errors": errs}, a.json, "invalid intake:\n- " + "\n- ".join(errs))
        return 2
    old = read(agents)
    new = upsert_block(old, INTAKE_START, INTAKE_END, intake_block(intake, profile_for(a, root)))
    if new == old:
        emit({"status": "unchanged"}, a.json, "unchanged")
        return 0
    if a.dry_run:
        emit({"dry_run": True, "new_block": intake_block(intake, profile_for(a, root)), "content": new, "sha256": IO.digest(new.encode())}, a.json, "DRY RUN — new block:\n"
             + intake_block(intake, profile_for(a, root)))
        return 0
    bk = backup(agents, root / "work" / "archive")
    IO.commit_files(root, [(agents, new)])
    emit({"status": "updated", "backup": str(bk)}, a.json, f"updated AGENTS.md block; backup: {bk}")
    return 0


# ---------------------------------------------------------------- index / rotate
def ref_rows(text: str) -> set[str]:
    rows = set()
    for line in text.splitlines():
        m = re.match(r"^\|\s*`?([^|`]+?)`?\s*\|", line)
        if m and m.group(1).strip() not in ("path", "---"):
            rows.add(unquote(m.group(1).strip()))
    return rows


def indexable(root: Path) -> list[Path]:
    out = []
    for directory in ('context', 'resources', 'work/archive'):
        ctx = root / directory
        IO.bounded(ctx, root)
        if ctx.is_dir():
            for d, dirs, names in os.walk(ctx, followlinks=False):
                dirs[:] = [n for n in dirs if not n.startswith('.') and not (Path(d) / n).is_symlink()]
                for n in sorted(names):
                    p = Path(d) / n
                    if not n.startswith('.') and not p.is_symlink() and p.is_file():
                        out.append(p)
    for extra in ('work/state-archive.md', 'CLAUDE.md', 'MEMORY.md'):
        p = IO.bounded(root / extra, root)
        if p.is_file():
            out.append(p)
    return sorted(out)


def cmd_index(a) -> int:
    root = project_root(a.path)
    ref = root / "REFERENCES.md"
    if not ref.exists():
        print("REFERENCES.md missing — run `apply` first", file=sys.stderr)
        return 2
    text = read(ref)
    if a.public:
        target = root / '.scaffold-skill' / 'private-references.md'
        private = read(target) if target.exists() else text
        for file in indexable(root):
            rel = str(file.relative_to(root))
            if rel not in ref_rows(private):
                private += f'| {quote(rel, safe="/.-_")} | input | review privately | {est_tokens(file.stat().st_size)} |\n'
        public = '# REFERENCES\n\nPrivate input index is maintained locally; request relevant sources when needed.\n'
        gi = root / '.gitignore'
        policy = upsert_block(read(gi) if gi.exists() else '', '# scaffold-skill:private-index:start', '# scaffold-skill:private-index:end', '/.scaffold-skill/')
        result = IO.commit_files(root, [(target, private), (ref, public), (gi, policy)], a.dry_run)
        emit({'redacted': True, **result}, a.json, 'private input index retained locally; public index redacted')
        return 0
    if 'Private input index is maintained locally' in text:
        raise ValueError('redacted index: use --public to update the private index')
    have = ref_rows(text)
    files = {str(p.relative_to(root)): p for p in indexable(root)}
    added = [rel for rel in files if rel not in have]
    stale = sorted(h for h in have if not (root / h).exists())
    rows = "".join(f"| {quote(rel, safe='/.-_')} | TODO | TODO | {est_tokens(files[rel].stat().st_size)} |\n" for rel in added)
    result = IO.commit_files(root, [(ref, text.rstrip("\n") + "\n" + rows)] if added else [], a.dry_run)
    emit({"added": added, "stale": stale, "dry_run": a.dry_run, **result}, a.json,
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
    root = project_root(a.path)
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
    if len(dates) != len(entries) or (dates != sorted(dates) and dates != sorted(dates, reverse=True)):
        raise ValueError('log entries must all be dated and chronologically ordered before rotation')
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
    archive = root / 'work' / 'state-archive.md'
    moved_text = '\n'.join('\n'.join(e) for e in move) + '\n'
    archive_text = read(archive) if archive.exists() else '# STATE archive — rotated log entries\n\n'
    archive_text += f'## Rotated {today()}\n{moved_text}\n'
    state_text = head + '\n'.join('\n'.join(e) for e in keep) + '\n' + (('\n' + tail) if tail else '')
    ref = root / 'REFERENCES.md'
    edits = [(archive, archive_text), (state, state_text)]
    if ref.exists() and 'work/state-archive.md' not in ref_rows(read(ref)):
        edits.append((ref, read(ref) + f'| work/state-archive.md | rotated STATE log | history questions | {est_tokens(len(archive_text.encode()))} |\n'))
    result = IO.commit_files(root, edits, a.dry_run)
    new_size = len(state_text.encode("utf-8"))
    emit({"status": "preview" if a.dry_run else "rotated", "dry_run": a.dry_run, "recovery": result["journal"], "files": result["files"], "moved": len(move), "kept": len(keep), "bytes_before": size,
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


def git_privacy(root):
    if not shutil.which('git'):
        return None, 'Git unavailable; effective ignore policy not verified'
    probe = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    if probe.returncode:
        return None, 'No Git repository; ignore patterns are proposals, not verified protection'
    names = ['work/probe.txt', 'output/probe.txt', '.env', 'key.pem', '.scaffold-skill/probe.json']
    gi = root / '.gitignore'
    if gi.is_file() and 'context/' in read(gi):
        names.append('context/probe.txt')
        names.append('resources/probe.txt')
    result = subprocess.run(['git', '-C', str(root), 'check-ignore', '--no-index', '--stdin'],
                            input='\n'.join(names) + '\n', capture_output=True, text=True)
    if result.returncode not in (0, 1):
        return False, 'Git ignore evaluation failed: ' + result.stderr.strip()
    ignored = set(result.stdout.splitlines())
    missing = sorted(set(names) - ignored)
    tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--', 'context', 'resources', 'work', 'output',
                              '.scaffold-skill', '.env', '.env.*', '*.pem', '*.key'], capture_output=True, text=True)
    if tracked.returncode:
        return False, 'Unable to inspect already-tracked private paths'
    paths = [p for p in tracked.stdout.split('\0') if p]
    return not missing and not paths, f'unprotected examples: {missing}; already-tracked private paths: {len(paths)} (history unchanged)'


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
    protected, detail = git_privacy(root)
    add('C07_GITIGNORE', protected is not False, detail, 'WARN' if protected is None else 'FAIL')
    if protected is None:
        res[-1]['status'] = 'WARN'
    dup = [f for f in LEGACY_FILES if (root / f).exists()]
    add("C08_NO_DUPLICATE_CHARTER", not dup,
        f"legacy charter files present: {dup} — index or fold into AGENTS/STATE" if dup else "single charter", "WARN")
    chain = agents_chain_bytes(root, home)
    add("C09_CODEX_DOC_LIMIT", chain < 0.8 * CODEX_DOC_LIMIT,
        f"estimated default AGENTS chain {chain} B; default budget {CODEX_DOC_LIMIT}; config overrides/fallback discovery not resolved", "WARN")
    if res[-1]["status"] == "OK":
        res[-1]["status"] = "WARN"
    return res


def cmd_check(a) -> int:
    root = project_root(a.path)
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
    if tier == "P3" or (tier == "P2" and (high or asked == "verify" or kind == "outbound")):
        agents.append("codex review" if kind == "code" else "verifier")
    if (decision and high) or asked == "challenge":
        agents.append("challenger")
    checks = {"P0": "none", "P1": "deterministic checks + self-checklist",
              "P2": "deterministic checks + claims ledger + verifier; REFUTED blocks output/",
              "P3": "worker summaries only; P2 rule on the final artifact"}[tier]
    return {"tier": tier, "spawn": bool(agents), "agents": agents, "verification": checks,
            "stage_in_work_first": tier != "P0"}


def routing_table():
    rows = [('| Tier | Trigger | Verification |'), ('|---|---|---|')]
    for kind, items, stakes in (('trivial', 1, []), ('deliverable', 1, []), ('deliverable', 1, ['money']), ('research', 5, [])):
        result = route(stakes, kind, items, 1, False)
        trigger = {'P0': 'Trivial maintenance', 'P1': 'Low-stakes deliverable', 'P2': 'Money/legal/health/outbound/irreversible or high floor', 'P3': 'At least 5 items or 3 independent sources'}[result['tier']]
        rows.append(f"| {result['tier']} | {trigger} | {result['verification']} |")
    return '\n'.join(rows)


def cmd_route(a) -> int:
    floor = profile_for(a, project_root(a.project or ".")).get("stakes_floor", "low")
    if a.items < 0 or a.sources < 0:
        raise ValueError("item/source counts cannot be negative")
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
        if d.is_symlink() or not d.is_dir() or d.name.startswith((".", "_")):
            continue
        if is_tier_dir(d.name):
            for c in sorted(d.iterdir()):
                if not c.is_symlink() and c.is_dir() and not c.name.startswith((".", "_")):
                    projects.append((c, strip_emoji_prefix(d.name)))
        else:
            projects.append((d, None))
    out = []
    for d, current_tier in projects:
        for f in CONTROL_FILES + LEGACY_FILES:
            IO.bounded(d / f, root)
        cb = control_bytes(d)
        snippet = ""
        for f in ("AGENTS.md", "CLAUDE.md", "MEMORY.md"):
            if (d / f).is_file():
                snippet += read(d / f)[:2000] + " "
        out.append({
            "path": str(d), "project_id": M.project_id(root, d), "hazards": M.hazards(d), "name": d.name, "slug": slugify(strip_emoji_prefix(d.name)),
            "dated": bool(DATED_DIR.match(d.name)), "generation": generation(d),
            "control_bytes": cb, "est_tokens_per_session": est_tokens(cb),
            "current_tier": current_tier,
            "knowledge_sources": [str(p.relative_to(d)) for p in indexable(d)] + [f for f in CONTROL_FILES if (d / f).is_file()],
            "worksheet": {"goal": None, "active_work": None, "constraints": None, "decisions": None,
                          "unresolved": ["Review source instructions and complete intake with evidence paths"]},
            "_text": snippet,
            "_hash": file_hash(d / "AGENTS.md") or file_hash(d / "CLAUDE.md"),
        })
    return out


def propose(root: Path, style: str, intakes=None, reorganize=False) -> dict:
    inv = inventory(root)
    groups = {}
    for p in inv:
        groups.setdefault(p['slug'], []).append(str(Path(p['path']).relative_to(root)))
    duplicates = [v for v in groups.values() if len(v) > 1]
    actions, ambiguous, tiers = [], [], {}
    intakes = intakes or {}
    for p in inv:
        tier, emoji, why = pick_tier(p['slug'], p['_text'][:600])
        p.update(proposed_tier=tier, tier_rationale=why)
        tiers.setdefault(tier, {'emoji': emoji, 'projects': []})['projects'].append(p['name'])
        rel = str(Path(p['path']).relative_to(root))
        reviewed = intakes.get(rel)
        if tier == UNSORTED[0]:
            ambiguous.append({'name': p['name'], 'path': rel, 'reason': why})
        if p['dated'] or not reviewed or tier == UNSORTED[0] or any(rel in g for g in duplicates):
            actions.append({'op': 'review', 'path': p['path'], 'reason': 'dated, ambiguous, duplicate hint, or missing reviewed intake'})
            continue
        src = Path(p['path'])
        dst = root / (f'{emoji} {tier}' if style != 'plain' else tier) / display_name(p['slug'], style, emoji, pick_project_glyph(p['slug'])) if reorganize else src
        actions.append({'op': 'adopt', 'project_id': p['project_id'], 'src': str(src), 'dst': str(dst),
                        'identity': M.tree(src), **{k: v for k, v in reviewed.items() if k in ('reviewed', 'handoff_reviewed', 'intake', 'now')}})
    for p in inv:
        p.pop('_text', None); p.pop('_hash', None)
    return {'schema_version': M.VERSION, 'date': today(), 'plan_id': IO.digest(os.urandom(32)), 'root': str(root),
            'style': style, 'projects': inv, 'duplicates': duplicates, 'ambiguous': ambiguous,
            'proposed_tiers': tiers, 'actions': actions,
            'summary': {'projects': len(inv), 'dated': sum(p['dated'] for p in inv),
                        'generations': {g: sum(p['generation'] == g for p in inv) for g in ('standard', 'legacy-memory', 'partial', 'bare')},
                        'est_tokens_per_session_total': sum(p['est_tokens_per_session'] for p in inv)}}


def apply_plan(plan: dict, yes: bool, root=None) -> list[dict]:
    if root is None:
        raise ValueError('selected root required independently of plan contents')
    return M.apply(plan, root, yes, sys.modules[__name__])


def cmd_onboard(a) -> int:
    if a.apply_plan:
        if not a.root:
            raise ValueError('supply the selected root when applying a plan')
        res = apply_plan(load_json(a.apply_plan), a.yes, project_root(a.root))
        emit(res, a.json, json.dumps(res, indent=2))
        return 0
    root = project_root(a.root or '.')
    style = a.name_style or profile_for(a, root).get('name_style', 'tier')
    prop = propose(root, style, load_json(a.intakes), a.reorganize)
    if a.plan_out:
        target = project_root(a.plan_out)
        if target.exists():
            raise ValueError('plan output exists; choose a new filename')
        IO.write(target, json.dumps(prop, indent=2, ensure_ascii=False) + '\n')
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
    adopts = [x for x in prop['actions'] if x['op'] == 'adopt']
    lines.append(f"\n{len(adopts)} adoption(s), {sum(x['src'] != x['dst'] for x in adopts)} relocation(s), "
                 f"{sum(x['op'] == 'review' for x in prop['actions'])} review-only project(s) proposed"
                 + (f" → plan written to {a.plan_out}" if a.plan_out else ''))
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
    h.add_argument("--scope", choices=("project", "user"), default="project")
    h.add_argument("--project", help="project root for local harness")
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
    i.add_argument("--public", action="store_true", help="redact public reference metadata; retain private index locally")
    i.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("rotate", help="rotate STATE.md log")
    r.add_argument("path")
    r.add_argument("--max-bytes", type=int, default=STATE_MAX_BYTES)
    r.add_argument("--keep", type=int, default=10)
    r.add_argument("--force", action="store_true")
    r.add_argument("--dry-run", action="store_true")

    ro = sub.add_parser("route", help="classify a task into P0-P3")
    ro.add_argument("--project", help="resolve project-local routing profile")
    ro.add_argument("--stakes", help=f"comma list of {','.join(STAKES)}")
    ro.add_argument("--kind", default="deliverable", help="trivial|edit|deliverable|outbound|code|research")
    ro.add_argument("--items", type=int, default=1)
    ro.add_argument("--sources", type=int, default=1)
    ro.add_argument("--decision", action="store_true")
    ro.add_argument("--asked", choices=("verify", "challenge", "fan-out"))

    o = sub.add_parser("onboard", help="inventory a projects root; propose tiers + migrations")
    o.add_argument("root", nargs="?", help="selected root, required independently when applying plans")
    o.add_argument("--intakes", help="reviewed intake map keyed by project relative path")
    o.add_argument("--reorganize", action="store_true", help="propose relocation separately from adoption")
    o.add_argument("--name-style", choices=NAME_STYLES)
    o.add_argument("--plan-out", help="write the proposal JSON here")
    o.add_argument("--apply-plan", help="execute a (reviewed) proposal JSON")
    o.add_argument("--yes", action="store_true", help="actually execute --apply-plan")

    rec = sub.add_parser('recover', help='preview/recover a write or migration journal')
    rec.add_argument('journal')
    rec.add_argument('--yes', action='store_true')
    sub.add_parser("version")
    return p


def _main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "version":
        print(VERSION)
        return 0
    if a.cmd == "template":
        tpl = project_template() if a.level == "project" else harness_template()
        print(json.dumps(tpl, indent=2, ensure_ascii=False))
        return 0
    if a.cmd == 'recover':
        record = load_json(a.journal)
        result = M.recover(a.journal, a.yes) if record.get('version') == M.VERSION else IO.recover_files(a.journal, a.yes)
        emit(result, a.json, json.dumps(result, indent=2))
        return 0
    return {"harness": cmd_harness, "new": cmd_new, "apply": cmd_apply, "refine": cmd_refine,
            "check": cmd_check, "index": cmd_index, "rotate": cmd_rotate, "route": cmd_route,
            "onboard": cmd_onboard}[a.cmd](a)


def main(argv=None):
    try:
        return _main(argv)
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(f'error: {e}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
