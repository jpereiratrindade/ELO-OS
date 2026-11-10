#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Import selected text variants from a sealed local ELO 0.1/0.2 bundle.

Operator-trusted input only: ELO content_hash provides integrity, not authenticity.
This is a text projection, not an ELO recipe executor or network protocol.
"""
import argparse
import hashlib
import os
from pathlib import Path
import stat
import tempfile

from elo_content import ActivationUncertain, activate, decode, encoded, fixture, read_bytes

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_FILES = 1024


def object_value(value, context):
    if not isinstance(value, dict):
        raise ValueError(f'{context}: expected object')
    return value


def required_text(value, context):
    if not isinstance(value, str) or not value or '\0' in value:
        raise ValueError(f'{context}: expected nonempty text')
    return value


def snapshot(source):
    # Resolve only the operator-selected bundle root (ELO current is a symlink).
    root = Path(source).resolve(strict=True)
    manifest = object_value(decode(read_bytes(root / 'manifest.json', 16384)), 'manifest')
    files = {}
    total = 0
    for folder in ('catalog', 'assets'):
        directory = root / folder
        if directory.is_symlink():
            raise ValueError('Symlinked bundle directory')
        if not directory.exists():
            continue
        for parent, dirs, names in os.walk(directory, followlinks=False):
            for name in dirs + names:
                path = Path(parent) / name
                mode = path.lstat().st_mode
                if stat.S_ISDIR(mode):
                    continue
                if not stat.S_ISREG(mode):
                    raise ValueError('Bundle contains symlink or special file')
                if len(files) >= MAX_FILES:
                    raise ValueError('Bundle file count exceeds limit')
                data = read_bytes(path, MAX_FILE)
                total += len(data)
                if total > MAX_TOTAL:
                    raise ValueError('Bundle size exceeds limit')
                files[path.relative_to(root).as_posix()] = data
    digest = hashlib.sha256()
    for name, data in sorted(files.items()):
        digest.update(name.encode('utf-8'))
        digest.update(data)
    # Matches ContentBundle::compute_content_hash in ELO, including path bytes.
    if manifest.get('content_hash') != 'sha256:' + digest.hexdigest():
        raise ValueError('ELO bundle integrity mismatch')
    if manifest.get('schema_version') not in ('0.1', '0.2'):
        raise ValueError('Unsupported ELO schema_version')
    return manifest, files


def records(files, folder):
    result = {}
    for name, data in sorted(files.items()):
        path = Path(name)
        if path.parent.as_posix() != 'catalog/' + folder or path.suffix != '.json':
            continue
        value = decode(data)
        values = value if isinstance(value, list) else [value]
        for item in values:
            item = object_value(item, name)
            key = required_text(item.get('variant_id' if folder == 'variants' else 'content_id'), name)
            if key in result:
                raise ValueError(f'Duplicate catalog identity: {key}')
            result[key] = item
    return result


def project(source, variant_ids):
    if not 1 <= len(variant_ids) <= 32 or len(set(variant_ids)) != len(variant_ids):
        raise ValueError('Select 1..32 distinct variants in presentation order')
    manifest, files = snapshot(source)
    atoms = records(files, 'atoms')
    if not atoms:
        atoms = records(files, 'objects')
    variants = records(files, 'variants')
    selected_atoms = manifest.get('atom_ids', [])
    if not isinstance(selected_atoms, list) or any(not isinstance(x, str) for x in selected_atoms):
        raise ValueError('Invalid manifest atom_ids')
    pages = []
    for key in variant_ids:
        if key not in variants:
            raise ValueError(f'Unknown variant: {key}')
        variant = variants[key]
        atom_id = required_text(variant.get('content_id'), key)
        if (atom_id not in atoms or (selected_atoms and atom_id not in selected_atoms)
                or (manifest['schema_version'] == '0.2' and atom_id not in selected_atoms)):
            raise ValueError(f'Variant references atom outside package: {key}')
        atom = atoms[atom_id]
        if atom.get('schema_version', '0.1') not in ('0.1', '0.2'):
            raise ValueError(f'Unsupported atom schema: {atom_id}')
        presentation = object_value(variant.get('presentation'), key)
        if (variant.get('interaction', 'none') != 'none'
                or presentation.get('media', []) != []
                or presentation.get('options', []) != []
                or presentation.get('correct_option', '') != ''):
            raise ValueError(f'Unsupported capability in variant: {key}; text/none only')
        # Never silently replace an interactive or media variant with its summary.
        pages.append({'title': required_text(presentation.get('title'), key),
                      'body': required_text(presentation.get('text'), key)})
    bundle_id = required_text(manifest.get('bundle_id'), 'bundle_id')
    version = required_text(manifest.get('version'), 'version')
    title = required_text(manifest.get('title'), 'title')
    output = {'schema': 1, 'id': bundle_id, 'version': '1',
              'name': f'{title} · ELO {version}', 'pages': pages}
    data = encoded(output)
    fixture(data)  # Enforce exact client text/page/byte limits before any write.
    return data, manifest


def import_bundle(source, destination, variant_ids):
    data, manifest = project(source, variant_ids)
    # Reuse existing fsync/lock/atomic activation; failed imports keep old pointer.
    with tempfile.TemporaryDirectory(prefix='elo-import-') as temporary:
        staged = Path(temporary) / 'presentation.json'
        staged.write_bytes(data)
        result = activate(destination, staged, len(data), hashlib.sha256(data).hexdigest())
    return {'result': result, 'source_bundle': manifest['bundle_id'],
            'source_version': manifest['version'], 'source_hash': manifest['content_hash'],
            'presentation_hash': hashlib.sha256(data).hexdigest(), 'variants': variant_ids}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--content-dir', required=True, type=Path)
    parser.add_argument('--variant', action='append', required=True, help='Repeat in display order')
    args = parser.parse_args()
    try:
        print(encoded(import_bundle(args.bundle, args.content_dir, args.variant)).decode(), end='')
    except ActivationUncertain as error:
        parser.exit(3, f'{error}\n')
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
