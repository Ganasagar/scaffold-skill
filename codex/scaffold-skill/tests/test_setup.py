import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'scripts'))
import setup_state as S
import scaffold as C

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cwd = self.root / 'scratch'; self.cwd.mkdir()
        self.home = self.root / 'config'; self.home.mkdir()
        self.projects = self.root / 'Projects'; self.projects.mkdir()
        self.intake = self.root / 'intake.json'
        self.ready = {'goal': 'Compare flight training options', 'done': 'A sourced shortlist', 'scope': 'Training providers only', 'project_type': 'finite', 'readiness': 'ready', 'reviewed': True, 'provenance': {k:'user answer' for k in ('goal','done','scope')}}
    def cli(self, *args, data=None):
        self.intake.write_text(json.dumps(self.ready if data is None else data))
        return subprocess.run([sys.executable, str(SKILL/'scripts/scaffold.py'), *args, '--codex-home', str(self.home), '--json'], cwd=self.cwd, env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}, text=True, capture_output=True)
    def new(self, *args, data=None):
        return self.cli('new','example','--intake',str(self.intake),*args,data=data)
    def test_no_cwd_fallback(self):
        r=self.new('--dry-run');self.assertNotEqual(r.returncode,0);self.assertEqual(list(self.cwd.iterdir()),[])
    def test_goal_only_rejected(self):
        r=self.new('--parent',str(self.projects),'--dry-run',data={'goal':'Create local workspace'})
        self.assertNotEqual(r.returncode,0)
    def test_ready_missing_scope_rejected(self):
        d={**self.ready};d.pop('scope');self.assertTrue(S.intake_errors(d))
    def test_ready_missing_provenance_rejected(self):
        d={**self.ready,'provenance':{}};self.assertTrue(S.intake_errors(d))
    def test_explicit_placeholder(self):
        r=self.new('--parent',str(self.projects),'--dry-run',data={'goal':'Placeholder for cloud project','readiness':'unconfigured'})
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('unconfigured',r.stdout)
    def test_configured_root_and_override(self):
        p=self.home/'scaffold-skill';p.mkdir();(p/'profile.json').write_text(json.dumps({'projects_root':str(self.projects),'name_style':'plain'}))
        r=self.new('--dry-run');self.assertEqual(json.loads(r.stdout)['root'],str(self.projects/'example'))
        other=self.root/'override';other.mkdir()
        r=self.new('--parent',str(other),'--dry-run');self.assertEqual(json.loads(r.stdout)['root'],str(other/'example'))
    def test_create_and_idempotent_adoption_preserve_legacy(self):
        r=self.new('--parent',str(self.projects),'--name-style','plain');self.assertEqual(r.returncode,0,r.stderr)
        project=self.projects/'example';legacy=project/'MEMORY.md';legacy.write_text('Preserve original knowledge')
        before=(project/'STATE.md').read_bytes()
        r=self.cli('apply',str(project),'--intake',str(self.intake));self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(legacy.read_text(),'Preserve original knowledge');self.assertEqual((project/'STATE.md').read_bytes(),before)
    def test_pending_manifest_incomplete(self):
        self.assertEqual(S.evaluate(S.template())['status'],'incomplete')
    def test_false_verification_rejected(self):
        d=S.template();d['facets']['intake']['status']='verified'
        self.assertEqual(S.evaluate(d)['status'],'invalid')
    def test_missing_tool_cannot_skip(self):
        d=S.template();d['facets']['registration']={'status':'skipped','reason':'no tool'}
        self.assertEqual(S.evaluate(d)['status'],'invalid')
    def test_cloud_id_not_filesystem_registration(self):
        d=S.template();d['projects']=[{'id':'p','registration_status':'verified','app_kind':'chatgpt','app_project_id':'cloud','host':'here','path':str(self.projects)}]
        self.assertEqual(S.evaluate(d)['status'],'invalid')
    def test_narrow_scope_complete(self):
        d=S.template();d['requested']=['filesystem'];d['facets']['filesystem']={'status':'verified','evidence':[{'source':'file readback','observed_at':'2026-10-19','host':'test','detail':'files match'}]}
        self.assertEqual(S.evaluate(d)['status'],'complete')
    def test_partial_chat_inventory_not_complete(self):
        d=S.template();d['requested']=['chats'];d['facets']['chats']={'status':'verified','evidence':[{'source':'latest 50','observed_at':'2026-10-19','host':'test','detail':'moved'}]}
        self.assertEqual(S.evaluate(d)['status'],'invalid')
    def test_repo_without_commit_not_ready(self):
        subprocess.run(['git','init','-q',str(self.projects)],check=True)
        r=S.repository_check(self.projects);self.assertFalse(r['repository_ready']);self.assertFalse(r['handoff_ready'])
    def test_legacy_profile_supported(self):
        self.assertEqual(C.validate_harness({'reply_style':'terse','name_style':'plain'}),[])
    def test_profile_preferences_render(self):
        body=C.harness_body({"tone":"direct", "projects_root":str(self.projects)})
        self.assertIn("Tone: direct",body)
        self.assertIn(str(self.projects),body)
    def test_relative_profile_root_rejected(self):
        self.assertTrue(C.validate_harness({'projects_root':'relative'}))

    def test_discovery_depth_and_symlinks(self):
        nested=self.projects/'category'/'project';nested.mkdir(parents=True)
        (nested/'MEMORY.md').write_text('legacy')
        (self.projects/'outside').symlink_to(self.cwd, target_is_directory=True)
        result=S.discover(self.projects, 3)
        self.assertEqual(len(result['projects']),1)
        self.assertTrue(any(x['reason']=='symlink' for x in result['skipped']))
        limited=S.discover(self.projects,0)
        self.assertEqual(limited['projects'],[])
        self.assertTrue(any(x['reason']=='depth_limit' for x in limited['skipped']))
    def test_bad_tree_detected(self):
        subprocess.run(['git','init','-q',str(self.projects)],check=True)
        (self.projects/'file').write_text('data')
        subprocess.run(['git','-C',str(self.projects),'add','file'],check=True)
        subprocess.run(['git','-C',str(self.projects),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','test'],check=True)
        tree=subprocess.check_output(['git','-C',str(self.projects),'rev-parse','HEAD^{tree}'],text=True).strip()
        (self.projects/'.git'/'objects'/tree[:2]/tree[2:]).unlink()
        result=S.repository_check(self.projects)
        self.assertTrue(result['checks']['commit']['ok'])
        self.assertFalse(result['checks']['tree']['ok'])
        self.assertFalse(result['repository_ready'])

if __name__=='__main__': unittest.main()
