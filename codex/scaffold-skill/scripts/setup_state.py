"""Read-only setup contracts, intake readiness and repository checks."""
from pathlib import Path
import subprocess

FACETS = ('intake', 'filesystem', 'registration', 'sidebar', 'chats', 'cross_device', 'handoff', 'publication')
STATUSES = ('pending', 'in_progress', 'verified', 'blocked', 'skipped')

def meaningful(value):
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith(('Q1:', 'Q2:', 'TODO', 'TBD'))

def intake_errors(data):
    errors = []
    state = data.get('readiness', 'unreviewed')
    if state not in ('unreviewed', 'unconfigured', 'ready'):
        errors.append('readiness must be unreviewed, unconfigured or ready')
    if state == 'ready':
        for field in ('goal', 'done', 'scope'):
            if not meaningful(data.get(field)):
                errors.append(f'ready intake requires substantive {field}')
        if data.get('project_type') not in ('ongoing', 'finite', 'reference'):
            errors.append('ready intake requires project_type ongoing|finite|reference')
        if data.get('reviewed') is not True:
            errors.append('ready intake requires reviewed=true after actual intake review')
        provenance = data.get('provenance')
        if not isinstance(provenance, dict) or any(not meaningful(provenance.get(k)) for k in ('goal', 'done', 'scope')):
            errors.append('ready intake requires provenance for goal, done and scope')
    if 'reply_style' in data and data['reply_style'] not in ('terse', 'balanced', 'detailed'):
        errors.append('reply_style must be terse|balanced|detailed')
    if 'scope' in data and not isinstance(data['scope'], str):
        errors.append('scope must be a string')
    for field in ('tone', 'initiative', 'clarification', 'technical_detail'):
        if field in data and not isinstance(data[field], str):
            errors.append(f'{field} must be a string')
    return errors

def template():
    return {'schema_version': 1, 'requested': ['intake', 'filesystem', 'registration', 'chats'],
            'coverage': {'complete': False, 'limitations': ['Inventory not yet reviewed']},
            'facets': {k: {'status': 'pending', 'evidence': []} for k in FACETS},
            'projects': []}

def evaluate(data):
    errors = []
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        return {'status': 'invalid', 'errors': ['unsupported setup schema']}
    requested = data.get('requested')
    if not isinstance(requested, list) or not requested or any(k not in FACETS for k in requested) or len(set(requested)) != len(requested):
        return {'status': 'invalid', 'errors': ['requested must be a nonempty unique list of known facets']}
    facets = data.get('facets', {})
    if not isinstance(facets, dict):
        return {'status': 'invalid', 'errors': ['facets must be an object']}
    for key in requested:
        row = facets.get(key, {})
        if not isinstance(row, dict) or row.get('status') not in STATUSES:
            errors.append(f'{key}: missing or invalid status'); continue
        if row['status'] == 'verified':
            evidence = row.get('evidence')
            if not isinstance(evidence, list) or not evidence or any(not isinstance(e, dict) or any(not meaningful(e.get(f)) for f in ('source', 'observed_at', 'host', 'detail')) for e in evidence):
                errors.append(f'{key}: verified requires source, observed_at, host and detail evidence')
        if row['status'] == 'skipped' and (row.get('excluded_by_user') is not True or not meaningful(row.get('reason'))):
            errors.append(f'{key}: skipped requires user scope exclusion and reason')
    coverage = data.get('coverage', {})
    if not isinstance(coverage, dict) or not isinstance(coverage.get('complete'), bool):
        errors.append('coverage.complete must be explicit')
    elif not coverage['complete'] and any(facets.get(k, {}).get('status') == 'verified' for k in ('chats', 'cross_device') if k in requested):
        errors.append('partial coverage cannot verify chats/cross_device; narrow requested scope or finish inventory')
    projects = data.get('projects', [])
    if not isinstance(projects, list):
        errors.append('projects must be a list'); projects = []
    ids = set()
    for p in projects:
        if not isinstance(p, dict): errors.append('invalid project record'); continue
        pid = p.get('id')
        if not meaningful(pid) or str(pid) in ids: errors.append('project IDs must be unique nonempty strings')
        ids.add(str(pid))
        if p.get('registration_status') == 'verified':
            if p.get('app_kind') != 'local' or not meaningful(p.get('app_project_id')) or not meaningful(p.get('host')) or not isinstance(p.get('path'), str) or not Path(p['path']).is_absolute():
                errors.append(f'{pid}: filesystem registration requires local app ID, host and absolute path')
    if 'registration' in requested and facets.get('registration', {}).get('status') == 'verified' and (not projects or any(p.get('registration_status') != 'verified' for p in projects if isinstance(p, dict))):
        errors.append('registration requires verified project records')
    complete = not errors and all(facets[k]['status'] in ('verified', 'skipped') for k in requested)
    return {'status': 'invalid' if errors else ('complete' if complete else 'incomplete'), 'errors': errors, 'requested': requested,
            'note': 'Evidence contract validation only; tool readback and human/agent review must establish truth.'}

def repository_check(path):
    results = {}
    for name, args in [('root', ['rev-parse', '--show-toplevel']), ('commit', ['rev-parse', '--verify', 'HEAD^{commit}']), ('tree', ['cat-file', '-e', 'HEAD^{tree}']), ('status', ['status', '--porcelain']), ('origin', ['remote', 'get-url', 'origin'])]:
        try:
            r = subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True, timeout=30)
            results[name] = {'ok': r.returncode == 0, 'output': r.stdout.strip(), 'error': r.stderr.strip()}
        except (OSError, subprocess.TimeoutExpired) as e:
            results[name] = {'ok': False, 'error': str(e)}
    return {'repository_ready': all(v['ok'] for v in results.values()), 'handoff_ready': False,
            'checks': results, 'remaining': ['Verify source repository identity and subdirectory', 'Read back saved destination project', 'Resolve composer blockers', 'Verify actual handoff']}

def discover(root, max_depth=3):
    """Bounded discovery, not semantic review. Does not follow symlinks."""
    import os
    root = Path(root)
    markers = ('AGENTS.md', 'CLAUDE.md', 'MEMORY.md', 'STATE.md', '.git')
    excluded = {'.git', 'node_modules', '.venv', '__pycache__', '.scaffold-skill'}
    projects, skipped = [], []
    for directory, dirs, files in os.walk(root, followlinks=False):
        path = Path(directory)
        depth = len(path.relative_to(root).parts)
        found = [m for m in markers if m in files or m in dirs]
        if found:
            projects.append({'path': str(path), 'markers': found, 'reviewed': False})
        keep = []
        for name in sorted(dirs):
            child = path / name
            reason = 'excluded' if name in excluded else ('symlink' if child.is_symlink() else ('depth_limit' if depth >= max_depth else None))
            if reason:
                skipped.append({'path': str(child), 'reason': reason})
            else:
                keep.append(name)
        dirs[:] = keep
    return {'root': str(root), 'max_depth': max_depth, 'projects': projects, 'skipped': skipped,
            'coverage': 'bounded_discovery_only', 'content_review_complete': False}
