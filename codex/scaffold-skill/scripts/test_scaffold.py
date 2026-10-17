"""Tests for scaffold.py — run: python3 -m unittest discover -s scripts -v"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scaffold as S  # noqa: E402

INTAKE = {"goal": "Book an award flight", "done": "tickets issued", "horizon": "2027-03",
          "never": ["never transfer points without asking"], "stakes": ["money"],
          "git": {"push": True, "visibility": "private", "ignore_context": True}}


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = S.main(list(argv))
    return code, buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.home = self.root / "codexhome"
        self.previous_codex_home = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = str(self.home)
        self.intake = self.root / "intake.json"
        self.intake.write_text(json.dumps(INTAKE))

    def tearDown(self):
        self.tmp.cleanup()
        if self.previous_codex_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = self.previous_codex_home


class TestScaffold(Base):
    def test_apply_creates_standard_and_passes_check(self):
        p = self.root / "proj"
        p.mkdir()
        self.assertEqual(run("apply", str(p), "--intake", str(self.intake))[0], 0)
        for f in S.CONTROL_FILES + (".gitignore",):
            self.assertTrue((p / f).is_file(), f)
        for d in S.DIRS:
            self.assertTrue((p / d).is_dir(), d)
        code, out = run("check", str(p), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["fail"], 0)

    def test_apply_never_overwrites(self):
        p = self.root / "proj"
        p.mkdir()
        (p / "AGENTS.md").write_text("MINE\n")
        run("apply", str(p), "--intake", str(self.intake))
        self.assertEqual((p / "AGENTS.md").read_text(), "MINE\n")
        before = {f: (p / f).read_text() for f in S.CONTROL_FILES}
        run("apply", str(p), "--intake", str(self.intake))  # idempotent
        self.assertEqual(before, {f: (p / f).read_text() for f in S.CONTROL_FILES})

    def test_dry_run_writes_nothing(self):
        p = self.root / "proj"
        p.mkdir()
        run("apply", str(p), "--intake", str(self.intake), "--dry-run")
        self.assertEqual(list(p.iterdir()), [])

    def test_gitignore_context_toggle(self):
        p = self.root / "pub"
        p.mkdir()
        i = dict(INTAKE, git={"push": True, "visibility": "public", "ignore_context": False})
        f = self.root / "i2.json"
        f.write_text(json.dumps(i))
        run("apply", str(p), "--intake", str(f))
        gi = (p / ".gitignore").read_text()
        self.assertIn("output/", gi)
        self.assertNotIn("context/", gi)

    def test_invalid_intake_rejected(self):
        p = self.root / "proj"
        p.mkdir()
        f = self.root / "bad.json"
        f.write_text(json.dumps({"goal": "", "stakes": ["vibes"]}))
        self.assertEqual(run("apply", str(p), "--intake", str(f))[0], 2)

    def test_new_uses_emoji_styles(self):
        code, out = run("new", "Award Travel", "--parent", str(self.root), "--intake", str(self.intake),
                        "--name-style", "rich", "--json")
        self.assertEqual(code, 0)
        r = json.loads(out)
        self.assertEqual(r["tier"], "Travel")
        self.assertEqual(r["slug"], "award-travel")
        self.assertTrue(r["folder"].startswith("✈️ "))
        self.assertTrue(Path(r["root"]).is_dir())
        _, out = run("new", "Award Travel", "--parent", str(self.root / "plain"), "--intake",
                     str(self.intake), "--name-style", "plain", "--json")
        self.assertEqual(json.loads(out)["folder"], "award-travel")

    def test_refine_preserves_user_edits_and_backs_up(self):
        p = self.root / "proj"
        p.mkdir()
        run("apply", str(p), "--intake", str(self.intake))
        agents = p / "AGENTS.md"
        agents.write_text(agents.read_text() + "\nUSER NOTE\n")
        f = self.root / "i3.json"
        f.write_text(json.dumps(dict(INTAKE, goal="New goal")))
        self.assertEqual(run("refine", str(p), "--intake", str(f))[0], 0)
        t = agents.read_text()
        self.assertIn("New goal", t)
        self.assertNotIn("Book an award flight", t)
        self.assertIn("USER NOTE", t)
        self.assertEqual(t.count(S.INTAKE_START), 1)
        self.assertTrue(list((p / "work" / "archive").glob("AGENTS-*.md")))


class TestMemory(Base):
    def make(self):
        p = self.root / "proj"
        p.mkdir()
        run("apply", str(p), "--intake", str(self.intake))
        return p

    def test_index_adds_and_flags_stale(self):
        p = self.make()
        (p / "context" / "a.txt").write_text("x" * 400)
        code, out = run("index", str(p), "--json")
        self.assertEqual(json.loads(out)["added"], ["context/a.txt"])
        self.assertEqual(json.loads(run("index", str(p), "--json")[1])["added"], [])
        (p / "context" / "a.txt").unlink()
        self.assertEqual(json.loads(run("index", str(p), "--json")[1])["stale"], ["context/a.txt"])

    def test_check_warns_on_unindexed(self):
        p = self.make()
        (p / "context" / "b.pdf").write_text("x")
        res = {r["id"]: r["status"] for r in json.loads(run("check", str(p), "--json")[1])["checks"]}
        self.assertEqual(res["C06_REFERENCES_COVERAGE"], "WARN")

    def test_rotate_moves_old_entries(self):
        p = self.make()
        st = p / "STATE.md"
        log = "\n".join(f"- 2026-{m:02d}-{d:02d}: entry {'y' * 80}" for m in range(1, 13) for d in range(1, 15))
        st.write_text(st.read_text().replace("- " + S.today() + ": Created.", log))
        before = st.stat().st_size
        self.assertGreater(before, S.STATE_MAX_BYTES)
        code, out = run("rotate", str(p), "--json", "--keep", "10")
        r = json.loads(out)
        self.assertEqual(r["status"], "rotated")
        self.assertLess(st.stat().st_size, before)
        text = st.read_text()
        self.assertIn("2026-12-14", text)  # newest kept
        self.assertNotIn("2026-01-01", text)  # oldest moved
        self.assertIn("2026-01-01", (p / "work" / "state-archive.md").read_text())
        self.assertIn("## Now", text)
        self.assertIn("work/state-archive.md", (p / "REFERENCES.md").read_text())

    def test_rotate_under_budget_noop(self):
        p = self.make()
        before = (p / "STATE.md").read_text()
        self.assertEqual(json.loads(run("rotate", str(p), "--json")[1])["status"], "under-budget")
        self.assertEqual(before, (p / "STATE.md").read_text())


class TestHarness(Base):
    def test_init_upserts_block_and_keeps_user_text(self):
        self.home.mkdir()
        (self.home / "AGENTS.md").write_text("# my global rules\n")
        ans = self.root / "h.json"
        ans.write_text(json.dumps({"reply_style": "terse", "naming": "name-vN"}))
        self.assertEqual(run("harness", "init", "--scope", "user", "--answers", str(ans))[0], 0)
        run("harness", "init", "--scope", "user", "--answers", str(ans))
        t = (self.home / "AGENTS.md").read_text()
        self.assertIn("# my global rules", t)
        self.assertEqual(t.count(S.HARNESS_START), 1)
        self.assertTrue((self.home / "agents" / "verifier.toml").is_file())
        self.assertTrue((self.home / "agents" / "challenger.toml").is_file())
        self.assertEqual(run("harness", "show", "--scope", "user")[0], 0)

    def test_init_rejects_bad_answers(self):
        ans = self.root / "h.json"
        ans.write_text(json.dumps({"naming": "whatever"}))
        self.assertEqual(run("harness", "init", "--scope", "user", "--answers", str(ans))[0], 2)

    @unittest.skipIf(sys.version_info < (3, 11), "TOML edits require Python 3.11+")
    def test_config_append_once(self):
        ans = self.root / "h.json"
        ans.write_text("{}")
        run("harness", "init", "--scope", "user", "--answers", str(ans), "--write-config")
        run("harness", "init", "--scope", "user", "--answers", str(ans), "--write-config")
        self.assertEqual((self.home / "config.toml").read_text().count("[agents]"), 1)

    def test_agent_tomls_have_required_fields(self):
        for f in S.AGENT_ASSETS.glob("*.toml"):
            t = f.read_text()
            for key in ("name =", "description =", "developer_instructions ="):
                self.assertIn(key, t, f.name)


class TestRoute(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(S.route([], "trivial", 1, 1, False)["tier"], "P0")
        self.assertEqual(S.route([], "deliverable", 1, 1, False)["agents"], [])
        r = S.route(["legal"], "deliverable", 1, 1, True)
        self.assertEqual(r["tier"], "P2")
        self.assertEqual(r["agents"], ["verifier", "challenger"])
        self.assertEqual(S.route([], "research", 8, 1, False)["tier"], "P3")
        self.assertIn("codex review", S.route(["money"], "code", 1, 1, False)["agents"])
        self.assertEqual(S.route([], "deliverable", 1, 1, False, floor="high")["tier"], "P2")
        self.assertEqual(S.route([], "deliverable", 1, 1, False, asked="challenge")["agents"], ["challenger"])


class TestOnboard(Base):
    def test_inventory_proposes_and_applies(self):
        projects = self.root / "projects"
        projects.mkdir()
        (projects / "award-travel").mkdir()
        (projects / "award-travel" / "CLAUDE.md").write_text("points and miles flights")
        (projects / "award-travel" / "MEMORY.md").write_text("log")
        (projects / "Award Travel").mkdir()
        (projects / "lekiwi-robot").mkdir()
        (projects / "2026-10-01").mkdir()
        (projects / "zzz").mkdir()
        plan_file = self.root / "plan.json"
        code, out = run("onboard", str(projects), "--json", "--plan-out", str(plan_file), "--name-style", "tier")
        prop = json.loads(out)
        self.assertEqual(prop["summary"]["dated"], 1)
        self.assertIn(["Award Travel", "award-travel"], prop["duplicates"])
        self.assertIn("Builds", prop["proposed_tiers"])
        self.assertTrue(any(a["name"] == "zzz" for a in prop["ambiguous"]))
        # dry run moves nothing
        run("onboard", "--apply-plan", str(plan_file))
        self.assertTrue((projects / "lekiwi-robot").is_dir())
        run("onboard", "--apply-plan", str(plan_file), "--yes")
        moved = projects / "🛠️ Builds" / "🛠️ lekiwi-robot"
        self.assertFalse(moved.exists())  # no reviewed intake: proposal remains review-only
        self.assertTrue((projects / "lekiwi-robot").is_dir())
        self.assertTrue((projects / "award-travel").is_dir())  # duplicate left for review
        self.assertTrue((projects / "2026-10-01").is_dir())  # dated left for review

    def test_apply_plan_never_clobbers(self):
        projects = self.root / "p"
        projects.mkdir()
        (projects / "src").mkdir()
        (projects / "dst").mkdir()
        (projects / "dst" / "keep.txt").write_text("keep")
        plan = {"actions": [{"op": "move", "src": str(projects / "src"), "dst": str(projects / "dst")}]}
        f = self.root / "plan.json"
        f.write_text(json.dumps(plan))
        run("onboard", "--apply-plan", str(f), "--yes")
        self.assertTrue((projects / "src").is_dir())
        self.assertEqual((projects / "dst" / "keep.txt").read_text(), "keep")


class TestScrub(unittest.TestCase):
    """No work- or harness-specific references may ship in the skill."""
    BANNED = [w[::-1] for w in ("ikstej", "ytivargitna", "inimeg", "potduolc", "amom", "rezinagub",
                                 "euqitirc", "xelpelgoog", "elgoog/nib/", "MTG", "repip")]
    BANNED_WORDS = ["jj"]

    def test_no_banned_terms(self):
        import re
        root = Path(S.SKILL_DIR).parent.parent
        hits = []
        for f in root.rglob("*"):
            if not f.is_file() or ".git" in f.parts or f.name == Path(__file__).name or f.suffix == ".pyc":
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            low = text.lower()
            hits += [(str(f), b) for b in self.BANNED if b.lower() in low]
            hits += [(str(f), b) for b in self.BANNED_WORDS if re.search(rf"\b{b}\b", low)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
