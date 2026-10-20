"""Bounded writes with collision-proof backups and conflict-aware recovery.

Concurrent external mutation is unsupported. Preconditions are checked immediately
before replacement; a transaction is journaled, not filesystem-wide atomic.
"""
import hashlib
import json
import os
import stat
import tempfile
import uuid
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bounded(path, root):
    root = Path(root).absolute()
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError(f'parent traversal is forbidden: {path}')
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError(f'outside selected root: {path}') from None
    for p in (path, *path.parents):
        if p.is_symlink():
            raise ValueError(f'symlink path is forbidden: {p}')
        if p != path and p.exists() and not p.is_dir():
            raise ValueError(f'ancestor is not a directory: {p}')
    if path.resolve() != path:
        raise ValueError(f'noncanonical path: {path}')
    return path


def snapshot(path):
    path = Path(path)
    if not path.exists():
        return None
    if not path.is_file() or path.is_symlink():
        raise ValueError(f'expected regular file: {path}')
    return {'sha256': digest(path.read_bytes()), 'mode': stat.S_IMODE(path.stat().st_mode)}


def atomic(path, data, expected):
    path = bounded(path, Path(path).anchor)
    if snapshot(path) != expected:
        raise ValueError(f'file changed since preview: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.scaffold-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, expected['mode'] if expected else 0o600)
        if snapshot(path) != expected:
            raise ValueError(f'file changed during write: {path}')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def backup(path, archive):
    path = bounded(path, Path(path).anchor)
    archive = bounded(archive, Path(archive).anchor)
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    dest = archive / f'{path.stem}-{uuid.uuid4().hex}{path.suffix}'
    with dest.open('xb') as f:
        f.write(path.read_bytes())
    os.chmod(dest, 0o600)
    return dest


def write(path, text, archive=None):
    path = Path(path)
    bounded(path, path.anchor)
    before = snapshot(path)
    data = text.encode('utf-8')
    if before and before['sha256'] == digest(data):
        return None
    bk = backup(path, archive or path.parent / '.scaffold-skill' / 'backups') if before else None
    atomic(path, data, before)
    return bk


def commit_files(root, edits, dry=False):
    """Journal a batch of replacements. Caller supplies every exact old snapshot."""
    root = bounded(root, Path(root).anchor)
    ops = []
    seen = set()
    for path, text in edits:
        path = bounded(path, root)
        if path in seen:
            raise ValueError(f'duplicate write target: {path}')
        seen.add(path)
        before = snapshot(path)
        if before and before['sha256'] == digest(text.encode()):
            continue
        ops.append({'path': str(path), 'before': before, 'after': digest(text.encode()),
                    'text': text, 'status': 'pending'})
    preview = [{'path': o['path'], 'before': o['before'], 'after': o['after'], 'content': o['text']} for o in ops]
    if dry or not ops:
        return {'files': preview, 'journal': None}
    area = bounded(root / '.scaffold-skill' / 'transactions' / uuid.uuid4().hex, root)
    area.mkdir(parents=True, mode=0o700)
    os.chmod(area, 0o700)
    journal = area / 'journal.json'
    record = {'version': 1, 'root': str(root), 'status': 'applying', 'ops': ops}
    def save():
        write(journal, json.dumps(record, indent=2) + '\n', area / 'journal-backups')
    save()
    try:
        for i, op in enumerate(ops):
            p = Path(op['path'])
            if snapshot(p) != op['before']:
                raise ValueError(f'file changed: {p}')
            if op['before']:
                bk = area / f'{i}.bak'
                with bk.open('xb') as f:
                    f.write(p.read_bytes())
                os.chmod(bk, 0o600)
                op['backup'] = str(bk)
            op['status'] = 'prepared'
            save()
            atomic(p, op['text'].encode(), op['before'])
            op['status'] = 'done'
            save()
        record['status'] = 'complete'
    except Exception as e:
        record['status'] = 'failed'
        record['error'] = str(e)
        raise
    finally:
        save()
    return {'files': preview, 'journal': str(journal)}


def recover_files(journal, yes=False):
    journal = Path(journal).absolute()
    record = json.loads(journal.read_text())
    if record.get('version') != 1 or not isinstance(record.get('ops'), list):
        raise ValueError('unsupported write journal')
    root = bounded(record['root'], Path(record['root']).anchor)
    bounded(journal, root / '.scaffold-skill' / 'transactions')
    actions = []
    for op in reversed(record['ops']):
        p = bounded(op['path'], root)
        current = snapshot(p)
        if current == op['before']:
            continue
        if not current or current['sha256'] != op['after'] or current['mode'] != (op['before']['mode'] if op['before'] else 0o600):
            raise ValueError(f'recovery conflict: {p}')
        data = None
        if op['before']:
            bk = bounded(op['backup'], journal.parent)
            data = bk.read_bytes()
            if digest(data) != op['before']['sha256']:
                raise ValueError(f'backup hash mismatch: {bk}')
        actions.append((p, data, current, op))
    if yes:
        for p, data, current, op in actions:
            if snapshot(p) != current:
                raise ValueError(f'recovery drift: {p}')
            if data is None:
                p.unlink()
            else:
                atomic(p, data, current)
                os.chmod(p, op['before']['mode'])
        record['status'] = 'recovered'
        write(journal, json.dumps(record, indent=2) + '\n')
    return {'dry_run': not yes, 'restore': [str(x[0]) for x in actions]}
