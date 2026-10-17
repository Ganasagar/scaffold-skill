"""Versioned, preflighted migrations. No content is synthesized by this module."""
import json
import os
import datetime
import uuid
from pathlib import Path

import safeio as IO

VERSION = 2


def tree(path):
    """Full regular-file identity, including Git metadata; never follow symlinks."""
    path = IO.bounded(path, Path(path).anchor)
    files = {}
    for directory, dirs, names in os.walk(path, followlinks=False):
        d = Path(directory)
        for name in dirs + names:
            p = d / name
            if p.is_symlink():
                raise ValueError(f'migration contains symlink: {p}')
        dirs[:] = sorted(dirs)
        files[str(d.relative_to(path)) + '/'] = {'mode': d.stat().st_mode & 0o777}
        for name in sorted(names):
            p = d / name
            files[str(p.relative_to(path))] = IO.snapshot(p)
    return files


def project_id(root, path):
    return IO.digest(str(path.relative_to(root)).encode())[:20]


def hazards(path):
    found = []
    for directory, dirs, names in os.walk(path, followlinks=False):
        d = Path(directory)
        dirs[:] = [n for n in dirs if n not in ('.git', 'node_modules', '.venv') and not (d / n).is_symlink()]
        if '.git' in names:
            found.append(f'worktree/submodule Git file: {d.relative_to(path)}')
        for name in names:
            if name.endswith(('.sh', '.py', '.toml', '.yaml', '.yml', '.json')):
                p = d / name
                if not p.is_symlink() and p.stat().st_size < 1024 * 1024 and str(path) in p.read_text(errors='replace'):
                    found.append(f'absolute project path: {p.relative_to(path)}')
            if name.endswith(('.service', '.timer')):
                found.append(f'service configuration: {(d / name).relative_to(path)}')
        if d != path and '.git' in [p.name for p in d.iterdir()]:
            found.append(f'nested repository: {d.relative_to(path)}')
    return found


def validate(plan, root, scaffold):
    root = IO.bounded(root, Path(root).anchor)
    if not isinstance(plan, dict):
        raise ValueError('plan must be an object')
    if plan.get('schema_version') != VERSION or plan.get('root') != str(root):
        raise ValueError('unsupported plan version or selected root mismatch; regenerate plan')
    if not root.is_dir() or not isinstance(plan.get('actions'), list):
        raise ValueError('invalid root or actions')
    try:
        datetime.date.fromisoformat(plan['date'])
    except (ValueError, KeyError, TypeError):
        raise ValueError('plan date must be an ISO date') from None
    seen, destinations, execution = set(), set(), []
    for action in plan['actions']:
        if not isinstance(action, dict):
            raise ValueError('each action must be an object')
        op = action.get('op')
        if op == 'review':
            IO.bounded(action['path'], root)
            continue
        if op != 'adopt':
            raise ValueError(f'unsupported operation: {op}')
        src = IO.bounded(action['src'], root)
        dst = IO.bounded(action['dst'], root)
        if src == root or dst == root or src in seen or dst in destinations:
            raise ValueError('duplicate/root project operation')
        if src in dst.parents or dst in src.parents:
            raise ValueError('overlapping source and destination')
        if not src.is_dir() or tree(src) != action.get('identity'):
            raise ValueError(f'stale or missing project: {src}')
        if action.get('project_id') != project_id(root, src):
            raise ValueError('project identity mismatch')
        if action.get('reviewed') is not True:
            raise ValueError(f'project intake not reviewed: {src}')
        if src != dst:
            if dst.exists():
                raise ValueError(f'destination collision: {dst}')
            issues = hazards(src)
            if issues:
                raise ValueError('relocation needs manual handling: ' + '; '.join(issues))
            parent = dst.parent
            while not parent.exists():
                parent = parent.parent
            if parent.stat().st_dev != src.stat().st_dev:
                raise ValueError('cross-filesystem relocation is unsupported')
        intake = action.get('intake')
        errors = scaffold.validate_project(intake) if isinstance(intake, dict) else ['intake must be an object']
        if errors:
            raise ValueError('; '.join(errors))
        if (src / 'CLAUDE.md').exists() or (src / 'MEMORY.md').exists():
            if action.get('handoff_reviewed') is not True or not action.get('now'):
                raise ValueError('legacy adoption requires reviewed handoff and current actions')
        if not isinstance(action.get('now', []), list) or any(not isinstance(x, str) for x in action.get('now', [])):
            raise ValueError('now must be a list of strings')
        # Resolve every eventual write before moving anything.
        sp = scaffold.plan_scaffold(src, intake, {}, src.name, plan['date'])
        legacy = [n for n in ('CLAUDE.md', 'MEMORY.md') if (src / n).is_file()]
        for i, (kind, path, content) in enumerate(sp):
            if kind == 'create' and path.name == 'AGENTS.md' and legacy:
                content += '\n## Preserved instructions\nRead these before acting; unresolved conflicts require user guidance.\n' + ''.join(f'- [{n}]({n})\n' for n in legacy)
            if kind == 'create' and path.name == 'STATE.md':
                now = action.get('now') or ['Adoption incomplete: review current actions before starting work.']
                content = '# STATE\n\n## Now\n' + ''.join(f'- {x}\n' for x in now) + '\n## Decisions\n- Legacy files retained unchanged.\n\n## Log\n'
            if kind == 'skip' and path.name == 'AGENTS.md' and legacy:
                original = scaffold.read(path)
                body = 'Read preserved instructions before acting; unresolved conflicts require user guidance.\n' + ''.join(f'- [{n}]({n})\n' for n in legacy)
                content = scaffold.upsert_block(original, '<!-- scaffold-skill:legacy:start -->', '<!-- scaffold-skill:legacy:end -->', body)
                kind = 'replace' if content != original else 'skip'
            sp[i] = (kind, path, content)
        seen.add(src)
        destinations.add(dst)
        execution.append((action, src, dst, sp))
    # Disallow sources/destinations that nest or depend on other project moves.
    paths = list(seen | destinations)
    for i, a in enumerate(paths):
        for b in paths[i + 1:]:
            if a in b.parents or b in a.parents:
                raise ValueError('nested project operations are unsupported')
    if any(dst in seen and src != dst for _, src, dst, _ in execution):
        raise ValueError('move cycles/dependencies are unsupported')
    return execution


def apply(plan, root, yes, scaffold):
    execution = validate(plan, root, scaffold)
    results = [{'op': 'adopt', 'src': str(src), 'dst': str(dst),
                'result': 'would adopt', 'preview': [{'op': k, 'path': str(dst / p.relative_to(src)), 'content': text}
                                                   for k, p, text in sp]} for _, src, dst, sp in execution]
    if not yes or not execution:
        return {'results': results, 'journal': None, 'dry_run': not yes}
    root = Path(root)
    area = IO.bounded(root / '.scaffold-skill' / 'migrations' / uuid.uuid4().hex, root)
    area.mkdir(parents=True, mode=0o700)
    os.chmod(area, 0o700)
    journal = area / 'journal.json'
    record = {'version': VERSION, 'root': str(root), 'status': 'applying', 'projects': []}
    def save():
        IO.write(journal, json.dumps(record, indent=2) + '\n', area / 'journal-backups')
    save()
    try:
        for (action, src, dst, sp), result in zip(execution, results):
            if tree(src) != action['identity']:
                raise ValueError(f'project changed: {src}')
            entry = {'src': str(src), 'dst': str(dst), 'identity': action['identity'], 'moved': False,
                     'created': [], 'directories': [], 'status': 'prepared'}
            record['projects'].append(entry)
            save()
            if src != dst:
                if dst.exists():
                    raise ValueError(f'destination appeared: {dst}')
                missing = []
                parent = dst.parent
                while not parent.exists():
                    missing.append(str(parent)); parent = parent.parent
                entry['parents'] = missing
                save()
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.rename(src, dst)
                entry['moved'] = True
                save()
            edits = []
            for kind, path, text in sp:
                path = dst / path.relative_to(src)
                IO.bounded(path, root)
                if kind == 'mkdir':
                    entry['directories'].append(str(path)); save()
                    path.mkdir()
                elif kind in ('create', 'replace'):
                    # Expected created paths are journaled before mutation, allowing crash recovery.
                    entry['created'].append({'path': str(path), 'sha256': IO.digest(text.encode()),
                                             'before': IO.snapshot(path),
                                             'backup_text': path.read_text() if path.exists() else None})
                    edits.append((path, text))
            save()
            tx = IO.commit_files(dst, edits)
            entry['write_journal'] = tx['journal']
            entry['status'] = 'complete'
            save()
            result['result'] = 'adopted'
        record['status'] = 'complete'
    except Exception as e:
        record['status'] = 'failed'; record['error'] = str(e)
        raise ValueError(f'{e}; recovery journal: {journal}') from e
    finally:
        save()
    return {'results': results, 'journal': str(journal), 'dry_run': False}


def recover(journal, yes=False):
    journal = Path(journal).absolute()
    r = json.loads(journal.read_text())
    if r.get('version') != VERSION or not isinstance(r.get('projects'), list):
        raise ValueError('unsupported migration journal')
    root = IO.bounded(r['root'], Path(r['root']).anchor)
    IO.bounded(journal, root / '.scaffold-skill' / 'migrations')
    prepared = []
    for e in reversed(r['projects']):
        src, dst = IO.bounded(e['src'], root), IO.bounded(e['dst'], root)
        # Handle a crash immediately following rename and idempotent completed recovery.
        moved = src != dst and not src.exists() and dst.exists()
        if src != dst and src.exists() and dst.exists():
            raise ValueError(f'recovery collision: {src}')
        location = dst if moved or src == dst else src
        if not location.is_dir():
            raise ValueError(f'missing recovery project: {location}')
        current = tree(location)
        expected = dict(e['identity'])
        created = []
        for f in e['created']:
            rel = str(Path(f['path']).relative_to(dst))
            p = IO.bounded(location / rel, root)
            snap = IO.snapshot(p)
            if snap == f['before']:
                continue
            if not snap or snap['sha256'] != f['sha256'] or snap['mode'] != (f['before']['mode'] if f['before'] else 0o600):
                raise ValueError(f'newer user edit blocks recovery: {p}')
            expected[rel] = snap
            if f['before'] and IO.digest(f['backup_text'].encode()) != f['before']['sha256']:
                raise ValueError('corrupt recovery original')
            created.append((p, f))
        for d in e['directories']:
            rel = str(Path(d).relative_to(dst)) + '/'
            if rel in current:
                expected[rel] = current[rel]
        # Private transaction journals are owned outputs, checked separately by write recovery.
        operational = {k: v for k, v in current.items() if k != '.scaffold-skill/' and not k.startswith('.scaffold-skill/')}
        baseline = {k: v for k, v in expected.items() if k != '.scaffold-skill/' and not k.startswith('.scaffold-skill/')}
        if operational != baseline:
            raise ValueError(f'project changed after migration: {location}')
        prepared.append((e, src, dst, location, moved, created))
    if yes:
        for e, src, dst, location, moved, created in prepared:
            for p, f in created:
                if f['before']:
                    IO.atomic(p, f['backup_text'].encode(), IO.snapshot(p))
                    os.chmod(p, f['before']['mode'])
                else:
                    p.unlink()
            for d in reversed(e['directories']):
                p = location / Path(d).relative_to(dst)
                if p.exists():
                    p.rmdir()
            if moved:
                os.rename(dst, src)
            for parent in e.get('parents', []):
                p = IO.bounded(parent, root)
                if p.is_dir() and not any(p.iterdir()):
                    p.rmdir()
        r['status'] = 'recovered'
        IO.write(journal, json.dumps(r, indent=2) + '\n')
    return {'dry_run': not yes, 'projects': [str(x[3]) for x in prepared]}
