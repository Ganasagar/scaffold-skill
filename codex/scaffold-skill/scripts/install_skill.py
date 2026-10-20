#!/usr/bin/env python3
"""Owned-file installation and uninstall. No harness edits are implicit."""
import argparse
import json
import os
from pathlib import Path

import safeio as IO

SOURCE = Path(__file__).resolve().parent.parent
MANIFEST = '.scaffold-install.json'


def install(root, uninstall=False, dry=False, source=SOURCE):
    root = IO.bounded(root, Path(root).anchor)
    dest = IO.bounded(root / '.agents' / 'skills' / 'scaffold-skill', root)
    overlap = root / '.agents/skills/workspace-scaffold/SKILL.md'
    if overlap.exists() and not uninstall:
        raise ValueError('overlapping workspace-scaffold skill found; select one before installation')
    manifest = IO.bounded(dest / MANIFEST, root)
    owned = json.loads(manifest.read_text()) if manifest.exists() else {'files': {}}
    for name, digest in owned['files'].items():
        p = IO.bounded(dest / name, dest)
        if p.exists() and (not p.is_file() or IO.digest(p.read_bytes()) != digest):
            raise ValueError(f'user edit blocks upgrade/uninstall: {p}')
    files = {}
    if not uninstall:
        for d, dirs, names in os.walk(source, followlinks=False):
            dirs[:] = [n for n in dirs if n not in ('__pycache__', 'tests')]
            for name in names:
                p = Path(d) / name
                if p.suffix == '.pyc' or name.startswith('test_') or name == MANIFEST:
                    continue
                IO.bounded(p, source)
                rel = str(p.relative_to(source))
                target = IO.bounded(dest / rel, dest)
                if target.exists() and rel not in owned['files']:
                    raise ValueError(f'unowned installation collision: {target}')
                files[rel] = p.read_text()
    stale = sorted(set(owned['files']) - set(files))
    report = {'dry_run': dry, 'destination': str(dest), 'write': sorted(files), 'remove': stale}
    if dry:
        return report
    edits = [(dest / n, text) for n, text in files.items()]
    # Journal each removed file's original bytes outside discovery. Files use .bak extensions.
    for name in stale:
        p = dest / name
        if p.exists():
            IO.backup(p, root / '.scaffold-skill' / 'install-backups')
    if not uninstall:
        record = {'version': '0.3.0', 'files': {n: IO.digest(t.encode()) for n, t in files.items()}}
        edits.append((manifest, json.dumps(record, indent=2) + '\n'))
        report.update(IO.commit_files(root, edits))
    for name in stale:
        p = dest / name
        if p.exists():
            # Recheck ownership immediately before deletion.
            if IO.digest(p.read_bytes()) != owned['files'][name]:
                raise ValueError(f'file changed during uninstall: {p}')
            p.unlink()
    if uninstall and manifest.exists():
        IO.backup(manifest, root / '.scaffold-skill' / 'install-backups')
        manifest.unlink()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=('project', 'user'), default='project')
    parser.add_argument('--project', help='explicit project root (required for default scope)')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    a = parser.parse_args()
    if a.scope == 'project' and not a.project:
        parser.error('--project is required; use --scope user to opt into user-wide installation')
    root = Path(a.project).expanduser().absolute() if a.scope == 'project' else Path.home().absolute()
    try:
        print(json.dumps(install(root, a.uninstall, a.dry_run), indent=2))
    except (ValueError, OSError) as e:
        parser.exit(2, f'error: {e}\n')


if __name__ == '__main__':
    main()
