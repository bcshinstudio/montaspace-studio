"""File-system-only project reliability helpers (no Qt media or GUI dependencies)."""

import os
from collections import defaultdict
from pathlib import Path

MAX_RECOVERY_ENTRIES = 4000


def resolve_sources(records, base, portable_root=None):
    """Resolve relative linked paths without touching records or the board."""
    result = []
    base = Path(base)
    for record in records:
        source = Path(record['source'])
        if portable_root is not None:
            source = Path(portable_root) / source
        elif not source.is_absolute():
            source = base / source
        row = dict(record)
        row['source'] = str(source.resolve())
        result.append(row)
    return result


def missing_sources(records):
    """Unique unresolved paths in order of first occurrence."""
    return list(dict.fromkeys(r['source'] for r in records
                              if not Path(r['source']).is_file()))


def candidate_relocations(missing, folder, max_entries=MAX_RECOVERY_ENTRIES):
    """Find unique filename matches in a user-selected folder; no guessing on ties.

    Bounded walk avoids traversing an entire external drive indefinitely.
    Call this on explicit user action only, not on every project open.
    """
    folder = Path(folder)
    if not folder.is_dir():
        return {}
    targets = {Path(name).name.casefold() for name in missing}
    found = defaultdict(list)
    visited = 0
    for root, directories, files in os.walk(folder):
        directories[:] = sorted(d for d in directories if not d.startswith('.'))
        for filename in sorted(files):
            visited += 1
            if visited > max_entries:
                # Incomplete scans cannot safely claim a unique match.
                return {}
            if filename.casefold() in targets:
                found[filename.casefold()].append(str((Path(root) / filename).resolve()))
    return {original: found[Path(original).name.casefold()][0]
            for original in missing
            if len(found[Path(original).name.casefold()]) == 1}


def apply_relocations(records, mapping):
    result = []
    for record in records:
        row = dict(record)
        row['source'] = mapping.get(row['source'], row['source'])
        result.append(row)
    return result


def verify_staged_project(path, expected_count, expected_video_count, portable):
    """Verify a complete staged file BEFORE atomic replacement of destination."""
    import json
    import zipfile
    path = Path(path)
    if portable:
        with zipfile.ZipFile(path, 'r') as package:
            info = package.infolist()
            if len({x.filename for x in info}) != len(info):
                raise ValueError('Portable project contains duplicate archive names.')
            data = json.loads(package.read('project.json').decode('utf-8'))
            entries = data.get('items', [])
            names = {x.filename for x in info}
            if not all(r.get('source') in names for r in entries):
                raise ValueError('Portable project is missing embedded media.')
    else:
        with path.open('r', encoding='utf-8') as stream:
            data = json.load(stream)
        entries = data.get('items', [])
    if (data.get('format') != 'MontaSpaceStudio'
            or data.get('version') != 1
            or data.get('portable') is not portable
            or len(entries) != expected_count
            or sum(r.get('type') == 'video' for r in entries) != expected_video_count):
        raise ValueError('Staged project verification failed; original file was preserved.')
