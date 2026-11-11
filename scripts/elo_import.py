#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Import selected text variants from a sealed local ELO 0.1/0.2 bundle.

Operator-trusted input only: ELO content_hash provides integrity, not authenticity.
This is a text projection, not an ELO recipe executor or network protocol.
"""
import argparse
import base64
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile

from elo_content import MAX_IMAGE, MAX_MEDIA, ActivationUncertain, activate, decode, encoded, fixture, read_bytes

MAX_FILE = MAX_MEDIA
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
    return project_snapshot(manifest, files, variant_ids)


def project_snapshot(manifest, files, variant_ids):
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
        if (variant.get('interaction', 'none') not in ('none', 'reveal')
                or presentation.get('options', []) != []
                or presentation.get('correct_option', '') != ''):
            raise ValueError(f'Unsupported capability in variant: {key}; none/reveal only')
        # Never silently replace an interactive or media variant with its summary.
        page = {'title': required_text(presentation.get('title'), key),
                'body': required_text(presentation.get('text'), key)}
        if variant.get('interaction') == 'reveal':
            page['interaction'] = 'reveal'
        media = presentation.get('media', [])
        modalities = atom.get('modalities', {})
        if not isinstance(modalities, dict):
            raise ValueError('Invalid atom modalities')
        # Explicit variant media wins; otherwise use the atom's published audio/video.
        if isinstance(media, list) and not any(PurePosixPath(str(x)).suffix.lower() in ('.wav', '.mp3', '.ogg', '.mp4', '.webm') for x in media):
            audio = modalities.get('audio', [])
            video = modalities.get('video', [])
            if not isinstance(audio, list) or not isinstance(video, list) or len(audio) > 1 or len(video) > 1 or (audio and video):
                raise ValueError('Select one audiovisual asset per atom or variant')
            media = media + audio + video
        if not isinstance(media, list) or len(media) > 2:
            raise ValueError('At most one image and one audio, or one video per page are supported')
        for reference in media:
            reference = required_text(reference, key)
            path = PurePosixPath(reference)
            if path.is_absolute() or '..' in path.parts or '\\' in reference or '?' in reference or '#' in reference:
                raise ValueError('Invalid image reference')
            name = reference if reference.startswith('assets/') else 'assets/' + reference
            mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(path.suffix.lower())
            raw = files.get(name)
            audiovisual = {'.wav': ('audio', 'audio/wav'), '.mp3': ('audio', 'audio/mpeg'), '.ogg': ('audio', 'audio/ogg'),
                           '.mp4': ('video', 'video/mp4'), '.webm': ('video', 'video/webm')}.get(path.suffix.lower())
            if audiovisual:
                if 'media' in page or not raw or len(raw) > MAX_MEDIA:
                    raise ValueError('Missing, duplicate or oversized audiovisual asset')
                kind, media_mime = audiovisual
                page['media'] = {'kind': kind, 'mime': media_mime, 'sha256': hashlib.sha256(raw).hexdigest(),
                                 'base64': base64.b64encode(raw).decode('ascii')}
                continue
            if not mime or not raw or len(raw) > MAX_IMAGE or 'image' in page:
                raise ValueError('Missing, duplicate or unsupported image')
            accessibility = atom.get('accessibility', {})
            alt = accessibility.get('alt_text') or page['title']
            page['image'] = {'mime': mime, 'sha256': hashlib.sha256(raw).hexdigest(),
                             'base64': base64.b64encode(raw).decode('ascii'), 'alt': alt}
        pages.append(page)
    bundle_id = required_text(manifest.get('bundle_id'), 'bundle_id')
    version = required_text(manifest.get('version'), 'version')
    title = required_text(manifest.get('title'), 'title')
    output = {'schema': 1, 'id': bundle_id, 'version': '5' if any('media' in page for page in pages) else '3' if any(page.get('interaction') == 'reveal' for page in pages) else ('2' if any('image' in page for page in pages) else '1'),
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
