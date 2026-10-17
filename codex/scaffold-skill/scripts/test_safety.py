"""Observable migration, failure recovery, privacy, and installer regressions."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install_skill
import migration as M
import safeio as IO
import scaffold as S
from test_scaffold import INTAKE, run


class Safety(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.projects = self.root / 'projects'
        self.projects.mkdir()
        self.src = self.projects / 'award-travel'
        self.src.mkdir()
        (self.src / 'source.txt').write_text('untouched')

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, move=False):
        intake = {'award-travel': {'reviewed': True, 'intake': INTAKE, 'now': ['Compare ticket options.']}}
        return S.propose(self.projects, 'plain', intake, move)

    def test_collision_cannot_convert_unrelated_destination(self):
        plan = self.plan(True)
        dst = Path(plan['actions'][0]['dst']); dst.mkdir(parents=True)
        (dst / 'keep').write_text('unrelated')
        before = M.tree(dst)
        with self.assertRaisesRegex(ValueError, 'collision'):
            S.apply_plan(plan, True, self.projects)
        self.assertEqual(M.tree(dst), before)
        self.assertTrue(self.src.exists())
        self.assertFalse((self.projects / '.scaffold-skill').exists())

    def test_root_and_schema_are_required(self):
        with self.assertRaises(ValueError):
            S.apply_plan(self.plan(), True)
        with self.assertRaises(ValueError):
            S.apply_plan({'root': str(self.projects), 'actions': []}, True, self.projects)
        plan = self.plan(); plan['root'] = str(self.root)
        with self.assertRaises(ValueError):
            S.apply_plan(plan, True, self.projects)

    def test_external_destination_and_traversal_rejected(self):
        for dst in (str(self.root / 'outside'), str(self.projects / '..' / 'outside')):
            plan = self.plan(); plan['actions'][0]['dst'] = dst
            with self.assertRaises(ValueError):
                S.apply_plan(plan, True, self.projects)
        self.assertFalse((self.root / 'outside').exists())

    def test_symlink_read_and_write_boundaries(self):
        external = self.root / 'outside'; external.mkdir()
        (self.src / 'context').symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError):
            S.plan_scaffold(self.src, INTAKE, {}, 'test')
        with self.assertRaises(ValueError):
            self.plan()
        self.assertEqual(list(external.iterdir()), [])

    def test_stale_identity_rejected_before_writes(self):
        plan = self.plan()
        (self.src / 'source.txt').write_text('new work')
        with self.assertRaisesRegex(ValueError, 'stale'):
            S.apply_plan(plan, True, self.projects)
        self.assertFalse((self.src / 'AGENTS.md').exists())

    def test_all_projects_preflight_before_any_write(self):
        plan = self.plan(); second = copy.deepcopy(plan['actions'][0])
        second['dst'] = str(self.root / 'outside'); plan['actions'].append(second)
        with self.assertRaises(ValueError):
            S.apply_plan(plan, True, self.projects)
        self.assertFalse((self.src / 'AGENTS.md').exists())

    def test_adoption_preview_bytes_match_and_recover(self):
        plan = self.plan()
        before = M.tree(self.src)
        preview = S.apply_plan(plan, False, self.projects)
        self.assertEqual(M.tree(self.src), before)
        result = S.apply_plan(plan, True, self.projects)
        for f in preview['results'][0]['preview']:
            if f['op'] in ('create', 'replace'):
                self.assertEqual(Path(f['path']).read_text(), f['content'])
        journal = result['journal']
        M.recover(journal)
        self.assertTrue((self.src / 'AGENTS.md').exists())
        M.recover(journal, True)
        after = {k: v for k, v in M.tree(self.src).items() if not k.startswith('.scaffold-skill')}
        self.assertEqual(after, before)
        M.recover(journal, True)  # repeat recovery is safe

    def test_move_and_recovery(self):
        result = S.apply_plan(self.plan(True), True, self.projects)
        self.assertFalse(self.src.exists())
        M.recover(result['journal'], True)
        self.assertEqual((self.src / 'source.txt').read_text(), 'untouched')

    def test_recovery_refuses_newer_edits(self):
        result = S.apply_plan(self.plan(), True, self.projects)
        (self.src / 'AGENTS.md').write_text('newer edit')
        with self.assertRaisesRegex(ValueError, 'user edit'):
            M.recover(result['journal'], True)
        self.assertEqual((self.src / 'AGENTS.md').read_text(), 'newer edit')

    def test_injected_write_failure_is_recoverable(self):
        original = IO.atomic
        calls = 0
        def fail(path, data, expected):
            nonlocal calls
            if Path(path).name == 'STATE.md':
                calls += 1
                if calls == 1:
                    raise OSError('injected failure')
            return original(path, data, expected)
        with patch.object(IO, 'atomic', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'recovery journal'):
                S.apply_plan(self.plan(True), True, self.projects)
        journal = next((self.projects / '.scaffold-skill/migrations').glob('*/journal.json'))
        self.assertEqual(json.loads(journal.read_text())['status'], 'failed')
        M.recover(journal, True)
        self.assertTrue(self.src.exists())
        self.assertFalse((self.src / 'AGENTS.md').exists())

    def test_relocation_blocks_worktrees_and_cross_filesystem(self):
        (self.src / '.git').write_text('gitdir: /somewhere')
        with self.assertRaisesRegex(ValueError, 'worktree'):
            S.apply_plan(self.plan(True), True, self.projects)

    def test_backups_never_replace_each_other(self):
        p = self.src / 'AGENTS.md'; p.write_text('original')
        one = IO.backup(p, self.root / 'backups')
        p.write_text('edited'); two = IO.backup(p, self.root / 'backups')
        self.assertNotEqual(one, two)
        self.assertEqual(one.read_text(), 'original')
        self.assertEqual(two.read_text(), 'edited')

    def test_file_transaction_failure_and_recovery(self):
        p = self.src / 'a'; p.write_text('old')
        result = IO.commit_files(self.src, [(p, 'new')])
        IO.recover_files(result['journal'], True)
        self.assertEqual(p.read_text(), 'old')

    def test_legacy_handoff_requires_review_and_preserves_originals(self):
        (self.src / 'CLAUDE.md').write_text('Never transfer points without approval.')
        (self.src / 'MEMORY.md').write_text('Awaiting airline schedule.')
        plan = self.plan()
        with self.assertRaisesRegex(ValueError, 'handoff'):
            S.apply_plan(plan, True, self.projects)
        plan['actions'][0]['handoff_reviewed'] = True
        result = S.apply_plan(plan, True, self.projects)
        self.assertIn('CLAUDE.md', (self.src / 'AGENTS.md').read_text())
        self.assertEqual((self.src / 'MEMORY.md').read_text(), 'Awaiting airline schedule.')
        self.assertIn('Compare ticket options', (self.src / 'STATE.md').read_text())
        self.assertIsNotNone(result['journal'])

    def test_ambiguous_projects_and_template_hashes(self):
        other = self.projects / 'zzz'; other.mkdir()
        (other / 'AGENTS.md').write_text('generic rules')
        (self.src / 'AGENTS.md').write_text('generic rules')
        plan = self.plan()
        self.assertEqual(plan['duplicates'], [])
        self.assertTrue(any(a['op'] == 'review' and a['path'] == str(other) for a in plan['actions']))

    def test_invalid_intake_and_emoji_are_rejected(self):
        for intake in ({'goal': 3}, {'goal': 'Q1: placeholder'}, {'goal': 'okay', 'stakes': 'money'},
                       {'goal': 'okay', 'git': []}, {'goal': 'okay', 'emoji': '../../bad'}):
            self.assertTrue(S.validate_project(intake))
        self.assertEqual(run('apply', str(self.src))[0], 2)

    def test_git_negations_and_tracked_private_data(self):
        subprocess.run(['git', 'init', '-q', str(self.src)], check=True)
        S.execute(S.plan_scaffold(self.src, INTAKE, {}, 'test'))
        self.assertTrue(S.git_privacy(self.src)[0])
        gi = self.src / '.gitignore'; gi.write_text(gi.read_text() + '\n!output/\n')
        self.assertFalse(S.git_privacy(self.src)[0])
        gi.write_text(S.gitignore_text(INTAKE))
        (self.src / 'context' / 'secret.txt').write_text('private')
        subprocess.run(['git', '-C', str(self.src), 'add', '-f', 'context/secret.txt'], check=True)
        self.assertFalse(S.git_privacy(self.src)[0])

    def test_parent_allowlist_and_no_git_audit(self):
        self.assertIsNone(S.git_privacy(self.src)[0])
        subprocess.run(['git', 'init', '-q', str(self.projects)], check=True)
        (self.projects / '.gitignore').write_text('*\n')
        self.assertTrue(S.git_privacy(self.src)[0])

    def test_index_escapes_unusual_names_and_redacts(self):
        S.execute(S.plan_scaffold(self.src, INTAKE, {}, 'test'))
        private = self.src / 'context' / 'private|name\n.txt'; private.write_text('secret')
        self.assertEqual(run('index', str(self.src))[0], 0)
        self.assertIn('context/private|name\n.txt', S.ref_rows((self.src / 'REFERENCES.md').read_text()))
        self.assertEqual(run('index', str(self.src), '--public')[0], 0)
        self.assertNotIn('private', (self.src / 'REFERENCES.md').read_text().lower().replace('private input index', ''))
        self.assertTrue((self.src / '.scaffold-skill/private-references.md').exists())

    def test_project_harness_and_conflicting_agent(self):
        ans = self.root / 'answers.json'; ans.write_text('{"stakes_floor":"high"}')
        code, out = run('harness', 'init', '--project', str(self.src), '--answers', str(ans))
        self.assertEqual(code, 0, out)
        args = type('Args', (), {'codex_home': str(self.root / 'absent')})()
        self.assertEqual(S.profile_for(args, self.src)['stakes_floor'], 'high')
        agent = self.src / '.codex/agents/verifier.toml'; agent.write_text('user owned')
        before = (self.src / 'AGENTS.md').read_text()
        self.assertEqual(run('harness', 'init', '--project', str(self.src), '--answers', str(ans))[0], 2)
        self.assertEqual((self.src / 'AGENTS.md').read_text(), before)

    def test_malformed_markers_and_invalid_toml(self):
        with self.assertRaises(ValueError):
            S.upsert_block('start orphan', 'start', 'end', 'new')
        cfg = self.src / '.codex/config.toml'; cfg.parent.mkdir(); cfg.write_text('not [toml')
        self.assertEqual(run('harness', 'init', '--project', str(self.src), '--write-config')[0], 2)
        self.assertFalse((self.src / 'AGENTS.md').exists())

    def test_installer_repeat_upgrade_conflict_uninstall(self):
        preview = install_skill.install(self.src, dry=True)
        self.assertFalse((self.src / '.agents').exists())
        install_skill.install(self.src)
        install_skill.install(self.src)
        dest = Path(preview['destination'])
        self.assertEqual(len(list((self.src / '.agents/skills').rglob('SKILL.md'))), 1)
        skill = dest / 'SKILL.md'; original = skill.read_text(); skill.write_text('user changes')
        with self.assertRaisesRegex(ValueError, 'user edit'):
            install_skill.install(self.src, uninstall=True)
        skill.write_text(original)
        install_skill.install(self.src, uninstall=True)
        self.assertFalse(skill.exists())
        self.assertFalse((self.src / '.codex').exists())

    def test_refine_preview_respects_project_stakes_floor(self):
        S.execute(S.plan_scaffold(self.src, INTAKE, {}, 'test'))
        profile = self.src / '.codex/scaffold-skill/profile.json'
        profile.parent.mkdir(parents=True); profile.write_text('{"stakes_floor":"high"}')
        intake = self.root / 'intake.json'; intake.write_text(json.dumps({**INTAKE, 'goal': 'A new goal', 'stakes': []}))
        code, out = run('refine', str(self.src), '--intake', str(intake), '--dry-run', '--json')
        self.assertEqual(code, 0)
        preview = json.loads(out)
        self.assertIn('**P2**', preview['new_block'])
        self.assertEqual(run('refine', str(self.src), '--intake', str(intake))[0], 0)
        self.assertEqual((self.src / 'AGENTS.md').read_text(), preview['content'])

    def test_index_and_rotation_have_recoverable_originals(self):
        S.execute(S.plan_scaffold(self.src, INTAKE, {}, 'test'))
        state = self.src / 'STATE.md'
        original = '# STATE\n\n## Now\n- keep\n\n## Log\n- 2026-01-01: old\n- 2026-02-01: new\n'
        state.write_text(original)
        self.assertEqual(run('rotate', str(self.src), '--force', '--keep', '1')[0], 0)
        self.assertNotIn('2026-01-01', state.read_text())
        journals = list((self.src / '.scaffold-skill/transactions').glob('*/journal.json'))
        journal = next(j for j in journals if any(x['path'] == str(state) and x['before'] for x in json.loads(j.read_text())['ops']))
        IO.recover_files(journal, True)
        self.assertEqual(state.read_text(), original)

    def test_unordered_log_and_zero_keep(self):
        S.execute(S.plan_scaffold(self.src, INTAKE, {}, 'test'))
        state = self.src / 'STATE.md'
        state.write_text('## Now\n- current\n## Log\n- 2026-02-01: middle\n- 2026-01-01: old\n- 2026-03-01: new\n')
        before = state.read_text()
        self.assertEqual(run('rotate', str(self.src), '--force')[0], 2)
        self.assertEqual(state.read_text(), before)
        state.write_text('## Now\n- current\n## Log\n- 2026-01-01: old\n')
        self.assertEqual(run('rotate', str(self.src), '--force', '--keep', '0')[0], 0)
        self.assertNotIn('2026-01-01', state.read_text())

    def test_ancestor_file_rejected_before_any_write(self):
        bad = self.src / 'bad'; bad.write_text('file')
        with self.assertRaises(ValueError):
            IO.commit_files(self.src, [(self.src / 'first', 'new'), (bad / 'child', 'bad')])
        self.assertFalse((self.src / 'first').exists())

    def test_move_failure_before_rename_and_cross_device(self):
        plan = self.plan(True)
        original = Path.stat
        class Device:
            st_dev = -1
        def fake_stat(path, *args, **kwargs):
            # Preflight compares selected existing destination parent with source device.
            if path == self.projects and kwargs.get('follow_symlinks', True):
                value = original(path, *args, **kwargs)
                class Info:
                    st_dev = value.st_dev + 1
                    def __getattr__(self, key):
                        return getattr(value, key)
                return Info()
            return original(path, *args, **kwargs)
        with patch.object(Path, 'stat', fake_stat):
            with self.assertRaisesRegex(ValueError, 'cross-filesystem'):
                S.apply_plan(plan, True, self.projects)
        with patch.object(M.os, 'rename', side_effect=OSError('injected rename failure')):
            with self.assertRaisesRegex(ValueError, 'recovery journal'):
                S.apply_plan(plan, True, self.projects)
        journal = next((self.projects / '.scaffold-skill/migrations').glob('*/journal.json'))
        M.recover(journal, True)
        self.assertTrue(self.src.exists())

    def test_failure_at_each_created_file_recovers(self):
        original = IO.atomic
        for filename in ('AGENTS.md', 'STATE.md', 'REFERENCES.md', 'SKILLS.md', '.gitignore'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                src = root / 'award-travel'; src.mkdir(); (src / 'original').write_text('keep')
                plan = S.propose(root, 'plain', {'award-travel': {'reviewed': True, 'intake': INTAKE}}, True)
                fired = []
                def fail(path, data, expected):
                    if Path(path).name == filename and not fired:
                        fired.append(True)
                        raise OSError('one injected failure')
                    return original(path, data, expected)
                with patch.object(IO, 'atomic', side_effect=fail):
                    with self.assertRaisesRegex(ValueError, 'recovery journal'):
                        S.apply_plan(plan, True, root)
                journal = next((root / '.scaffold-skill/migrations').glob('*/journal.json'))
                M.recover(journal, True)
                self.assertEqual((src / 'original').read_text(), 'keep')
                self.assertFalse((src / 'AGENTS.md').exists())

    def test_installer_upgrades_owned_and_removes_only_stale(self):
        source = self.root / 'package'; source.mkdir()
        (source / 'SKILL.md').write_text('version one')
        (source / 'old.txt').write_text('old resource')
        install_skill.install(self.src, source=source)
        dest = self.src / '.agents/skills/scaffold-skill'
        (dest / 'user.txt').write_text('unowned user file')
        (source / 'SKILL.md').write_text('version two')
        (source / 'old.txt').unlink()
        install_skill.install(self.src, source=source)
        self.assertEqual((dest / 'SKILL.md').read_text(), 'version two')
        self.assertFalse((dest / 'old.txt').exists())
        install_skill.install(self.src, uninstall=True, source=source)
        self.assertEqual((dest / 'user.txt').read_text(), 'unowned user file')
        self.assertTrue(list((self.src / '.scaffold-skill/install-backups').glob('old-*.txt')))

    def test_routing_matrix(self):
        for kind in ('research', 'code', 'deliverable'):
            for stakes in ([], ['money'], ['health'], ['legal'], ['outbound'], ['irreversible']):
                for items, sources in ((1, 1), (5, 1), (1, 3)):
                    for asked in (None, 'verify', 'challenge', 'fan-out'):
                        r = S.route(stakes, kind, items, sources, True, asked=asked)
                        if r['tier'] == 'P3':
                            self.assertIn('codex review' if kind == 'code' else 'verifier', r['agents'])
                        if stakes:
                            self.assertIn('challenger', r['agents'])


if __name__ == '__main__':
    unittest.main()
