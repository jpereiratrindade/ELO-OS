#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Embed source/configuration provenance in virtual appliance images."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(directory, *arguments):
    return subprocess.check_output(['git', '-C', str(directory), *arguments])


def main():
    target = Path(sys.argv[1]).resolve()
    config = target.parent / '.config'
    release = (target / 'etc/elo-os-release').read_text()
    profile = re.search(r'(?m)^PLATFORM="(qemu-(?:x86_64|aarch64)-appliance)"$', release)
    if not profile:
        raise SystemExit('Build metadata is restricted to virtual appliance profiles')
    names = git(ROOT, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')
    files = {}
    modes = {}
    tree = hashlib.sha256()
    for name in sorted(set(filter(None, names))):
        if name not in ('VERSION', 'LICENSE', 'Config.in', 'external.desc', 'external.mk') and not name.startswith(
                ('board/', 'configs/', 'package/', 'scripts/')):
            continue
        path = ROOT / name
        if path.is_symlink():
            content = b'symlink:' + os.fsencode(os.readlink(path))
        elif path.is_file():
            content = path.read_bytes()
        else:
            continue
        files[name] = hashlib.sha256(content).hexdigest()
        modes[name] = oct(path.lstat().st_mode & 0o777)
        tree.update(f'{name}\0{modes[name]}\0{files[name]}\0'.encode())
    version = (ROOT / 'VERSION').read_text().strip()
    config_hash = hashlib.sha256(config.read_bytes()).hexdigest()
    tree_hash = tree.hexdigest()
    metadata = {
        'schema_version': 1,
        'image_id': f'elo-os/{version}+{tree_hash[:12]}.{config_hash[:12]}',
        'profile': profile[1], 'project_version': version,
        'source_commit': git(ROOT, 'rev-parse', 'HEAD').decode().strip(),
        'source_dirty': bool(git(ROOT, 'status', '--porcelain')),
        'source_tree_sha256': tree_hash, 'source_files_sha256': files,
        'source_modes': modes, 'config_sha256': config_hash,
        'buildroot_version': os.environ['BR2_VERSION'],
        'buildroot_commit': git(Path.cwd(), 'rev-parse', 'HEAD').decode().strip(),
        'buildroot_dirty': bool(git(Path.cwd(), 'status', '--porcelain')),
    }
    temporary = target / 'etc/.elo-build.json.tmp'
    temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n')
    temporary.chmod(0o644)
    temporary.replace(target / 'etc/elo-build.json')


if __name__ == '__main__':
    main()
