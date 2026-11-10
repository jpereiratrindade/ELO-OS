#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Host-only fixture activation. SHA-256 checks integrity, not publisher identity."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

MAX_CONTENT = 8 * 1024 * 1024
MAX_IMAGE = 2 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}')


class ActivationUncertain(OSError):
    """The pointer was published; its directory fsync did not complete."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def decode(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)


def fixture(data):
    if not 0 < len(data) <= MAX_CONTENT:
        raise ValueError('Fixture size out of bounds')
    value = decode(data)
    if not isinstance(value, dict) or set(value) not in ({'schema', 'id', 'name', 'version', 'pages'}, {'schema', 'id', 'name', 'version', 'pages', 'exposure_seconds'}):
        raise ValueError('Unsupported fixture fields')
    if type(value['schema']) is not int or value['schema'] != 1 or value['version'] not in ('1', '2', '3', '4'):
        raise ValueError('Unsupported fixture version')

    if 'exposure_seconds' in value and (value['version'] != '4' or type(value['exposure_seconds']) is not int or not 5 <= value['exposure_seconds'] <= 3600):
        raise ValueError('Invalid exposure time')
    if value['version'] == '4' and 'exposure_seconds' not in value:
        raise ValueError('Missing exposure time')

    def text(value, limit):
        return isinstance(value, str) and 0 < len(value.encode('utf-8')) <= limit and '\0' not in value

    if not text(value['id'], 128) or not text(value['name'], 256):
        raise ValueError('Invalid fixture identity')
    pages = value['pages']
    if not isinstance(pages, list) or not 1 <= len(pages) <= 32:
        raise ValueError('Invalid page count')
    for page in pages:
        if (not isinstance(page, dict) or not {'title', 'body'} <= set(page) or set(page) - {'title', 'body', 'image', 'interaction'}
                or not text(page['title'], 256) or not text(page['body'], 4096)):
            raise ValueError('Invalid page')
        if 'interaction' in page and (value['version'] not in ('3', '4') or page['interaction'] not in ('none', 'reveal')):
            raise ValueError('Unsupported interaction')
        if 'image' in page:
            image = page['image']
            if (value['version'] not in ('2', '3', '4') or not isinstance(image, dict)
                    or set(image) != {'mime', 'sha256', 'base64', 'alt'}
                    or image['mime'] not in ('image/png', 'image/jpeg')
                    or not text(image['alt'], 512) or not isinstance(image['base64'], str)):
                raise ValueError('Invalid image metadata')
            raw = base64.b64decode(image['base64'], validate=True)
            if (not 0 < len(raw) <= MAX_IMAGE or hashlib.sha256(raw).hexdigest() != image['sha256']
                    or (image['mime'] == 'image/png' and not raw.startswith(b'\x89PNG\r\n\x1a\n'))
                    or (image['mime'] == 'image/jpeg' and not (raw.startswith(b'\xff\xd8') and raw.rstrip(b'\xff\x00').endswith(b'\xff\xd9')))):
                raise ValueError('Invalid image bytes/hash')
    return value


def read_bytes(path, limit):
    if path.is_symlink():
        raise ValueError('Symlinks are not fixture files')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('File too large')
    return data


def read_bundle(root, bundle):
    if not isinstance(bundle, str) or not HEX.fullmatch(bundle):
        raise ValueError('Invalid bundle identifier')
    directory = root / 'bundles' / bundle
    if (root / 'bundles').is_symlink() or directory.is_symlink():
        raise ValueError('Symlinked bundle directory')
    return read_bundle_directory(directory, bundle)


def read_bundle_directory(directory, bundle):
    manifest = decode(read_bytes(directory / 'manifest.json', 4096))
    if (not isinstance(manifest, dict) or set(manifest) != {'schema', 'file', 'size', 'sha256'}
            or type(manifest['schema']) is not int or manifest['schema'] != 1
            or manifest['file'] != 'presentation.json' or manifest['sha256'] != bundle
            or type(manifest['size']) is not int or not 0 < manifest['size'] <= MAX_CONTENT):
        raise ValueError('Invalid manifest')
    data = read_bytes(directory / 'presentation.json', MAX_CONTENT)
    if len(data) != manifest['size'] or hashlib.sha256(data).hexdigest() != bundle:
        raise ValueError('Fixture integrity mismatch')
    return fixture(data)


def read_active(root):
    root = Path(root)
    pointer = decode(read_bytes(root / 'active.json', 4096))
    if not isinstance(pointer, dict) or set(pointer) != {'bundle'}:
        raise ValueError('Invalid activation pointer')
    return read_bundle(root, pointer['bundle'])


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_file(path, data):
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')


def activate(root, source, expected_size, expected_sha256, fault=lambda point: None):
    """Publish one immutable bundle and one atomic pointer, on the same filesystem.

    `fault` is an injectable test seam, never a command-line option. Old bundles
    remain available; no garbage collection or OS update/rollback is performed.
    """
    if type(expected_size) is not int or not 0 < expected_size <= MAX_CONTENT:
        raise ValueError('Invalid expected size')
    if not isinstance(expected_sha256, str) or not HEX.fullmatch(expected_sha256):
        raise ValueError('Invalid expected SHA-256')
    data = read_bytes(Path(source), MAX_CONTENT)
    if len(data) != expected_size or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Staged fixture integrity mismatch')
    fixture(data)
    root = Path(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError('Content root must be a real directory')
    bundles = root / 'bundles'
    if bundles.is_symlink():
        raise ValueError('Bundle directory must not be a symlink')
    bundles.mkdir(mode=0o700, exist_ok=True)
    if root.stat().st_dev != bundles.stat().st_dev:
        raise ValueError('Activation requires the same filesystem')
    lock_fd = os.open(root / '.activation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        target = bundles / expected_sha256
        if target.exists():
            read_bundle(root, expected_sha256)  # Never reuse a corrupted bundle.
            for name in ('presentation.json', 'manifest.json'):
                with (target / name).open('rb') as stream:
                    os.fsync(stream.fileno())
            sync_dir(target)
        else:
            staged = Path(tempfile.mkdtemp(prefix='.staged-', dir=root))
            try:
                write_file(staged / 'presentation.json', data)
                write_file(staged / 'manifest.json', encoded({
                    'schema': 1, 'file': 'presentation.json', 'size': len(data),
                    'sha256': expected_sha256}))
                fault('after-staged-write')
                read_bundle_directory(staged, expected_sha256)
                sync_dir(staged)
                fault('before-bundle-rename')
                os.rename(staged, target)
                fault('after-bundle-rename')
            finally:
                if staged.exists():
                    shutil.rmtree(staged)
        # Also complete directory durability when reusing a bundle left by a
        # previous interrupted activation, before publishing its pointer.
        sync_dir(bundles)
        sync_dir(root)
        pointer = root / 'active.json'
        if pointer.exists() and read_bytes(pointer, 4096) == encoded({'bundle': expected_sha256}):
            read_active(root)
            sync_dir(bundles)
            sync_dir(root)
            return 'unchanged'
        fd, temporary = tempfile.mkstemp(prefix='.active-', dir=root)
        os.close(fd)
        temporary = Path(temporary)
        published = False
        try:
            with temporary.open('wb') as stream:
                stream.write(encoded({'bundle': expected_sha256}))
                stream.flush()
                os.fsync(stream.fileno())
            fault('before-pointer-rename')
            os.replace(temporary, pointer)
            published = True
            fault('after-pointer-rename')
            sync_dir(root)
        except OSError as error:
            if published:
                raise ActivationUncertain('Pointer published; durability must be reconciled with read_active') from error
            raise
        finally:
            temporary.unlink(missing_ok=True)
        return 'activated'
    finally:
        os.close(lock_fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    publish = sub.add_parser('activate')
    publish.add_argument('root', type=Path)
    publish.add_argument('source', type=Path)
    publish.add_argument('--size', type=int, required=True)
    publish.add_argument('--sha256', required=True)
    show = sub.add_parser('show')
    show.add_argument('root', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'activate':
            print(activate(args.root, args.source, args.size, args.sha256))
        else:
            print(json.dumps(read_active(args.root), ensure_ascii=False, indent=2))
    except ActivationUncertain as error:
        parser.exit(3, f'{error}\n')
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
