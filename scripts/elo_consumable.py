#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only, host-side preflight for the initial PCM WAV ingest profile.

This does not authenticate publishers, approve rights, import or activate content.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import wave

from elo_content import decode

MAX_ASSET = 8 * 1024 * 1024
MAX_MANIFEST = 64 * 1024
IDENTITY = r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}'
VERSION = r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def fields(value, names):
    require(isinstance(value, dict) and set(value) == set(names.split()), 'invalid_fields')


def text(value, limit=1024):
    return (isinstance(value, str) and bool(value.strip())
            and len(value.encode('utf-8')) <= limit
            and not any(ord(c) < 32 for c in value))


def matches(pattern, value):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def manifest(value):
    fields(value, 'schema production_id production_version producer title description language '
           'suggested_uses assets provenance rights privacy')
    require(value['schema'] == 'elo-consumable-ingest/v1', 'unsupported_schema')
    require(matches(IDENTITY, value['production_id'])
            and matches(VERSION, value['production_version']), 'invalid_identity')
    fields(value['producer'], 'system release')
    require(value['producer']['system'] == 'sister-studio'
            and text(value['producer']['release'], 128), 'invalid_producer')
    require(text(value['title'], 256) and text(value['description'], 4096)
            and matches(r'[a-z]{2,3}(-[A-Za-z0-9]{2,8})*', value['language']), 'invalid_metadata')
    uses = value['suggested_uses']
    require(isinstance(uses, list) and len(uses) <= 16
            and all(text(item, 128) for item in uses), 'invalid_suggested_uses')
    fields(value['provenance'], 'declared_creator source_project_ref reviewed')
    require(text(value['provenance']['declared_creator'], 256)
            and matches(IDENTITY, value['provenance']['source_project_ref'])
            and value['provenance']['reviewed'] is True, 'review_required')
    fields(value['rights'], 'license rights_holder voice_permission')
    require(text(value['rights']['license'], 256) and text(value['rights']['rights_holder'], 256)
            and value['rights']['voice_permission'] in ('not-applicable', 'granted'), 'rights_declaration_required')
    fields(value['privacy'], 'classification purpose')
    require(value['privacy']['classification'] == 'public'
            and value['privacy']['purpose'] == 'catalogo-editorial-e-distribuicao', 'unsupported_privacy')
    require(isinstance(value['assets'], list) and len(value['assets']) == 1, 'initial_profile_requires_one_asset')
    asset = value['assets'][0]
    fields(asset, 'asset_id role kind filename mime size_bytes sha256 duration_ms')
    require(matches(IDENTITY, asset['asset_id']) and asset['role'] == 'primary'
            and asset['kind'] == 'media.audio' and asset['mime'] == 'audio/wav', 'unsupported_asset')
    require(matches(r'[A-Za-z0-9][A-Za-z0-9_-]{0,123}\.wav', asset['filename']), 'unsafe_filename')
    require(type(asset['size_bytes']) is int and 1 <= asset['size_bytes'] <= MAX_ASSET
            and type(asset['duration_ms']) is int and 1 <= asset['duration_ms'] <= 60000
            and matches(r'[0-9a-f]{64}', asset['sha256']), 'invalid_asset_metadata')
    return value


def read_regular(directory_fd, name, limit):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit, 'invalid_file')
        data = stream.read(limit + 1)
    require(0 < len(data) <= limit, 'file_too_large')
    return data


def read_package(package):
    # Only immediate children of an operator-selected directory are ever opened.
    fd = os.open(package, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        value = manifest(decode(read_regular(fd, 'manifest.json', MAX_MANIFEST)))
        asset = value['assets'][0]
        require(set(os.listdir(fd)) == {'manifest.json', asset['filename']}, 'unexpected_package_files')
        raw = read_regular(fd, asset['filename'], MAX_ASSET)
    finally:
        os.close(fd)
    return value, raw


def canonical_manifest(value):
    # Sorted ASCII JSON, no floats in this profile; not a general JCS claim.
    return json.dumps(manifest(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def validate_payload(value, raw):
    manifest(value)
    asset = value['assets'][0]
    require(len(raw) == asset['size_bytes'], 'size_mismatch')
    require(hashlib.sha256(raw).hexdigest() == asset['sha256'], 'digest_mismatch')
    try:
        with wave.open(io.BytesIO(raw), 'rb') as audio:
            channels, width, rate, frames, compression, _ = audio.getparams()
            require(channels in (1, 2) and width == 2 and rate in (16000, 22050, 24000, 44100, 48000)
                    and compression == 'NONE' and frames > 0, 'unsupported_pcm')
            require(len(audio.readframes(frames)) == frames * channels * width, 'truncated_wav')
            require(abs(asset['duration_ms'] - frames * 1000 / rate) <= 1, 'duration_mismatch')
    except (wave.Error, EOFError, RuntimeError) as error:
        raise ValueError('invalid_wav') from error
    canonical = canonical_manifest(value)
    return {'schema': 'elo-consumable-preflight/v1', 'status': 'validated_locally',
            'production_id': value['production_id'], 'production_version': value['production_version'],
            'manifest_sha256': hashlib.sha256(canonical).hexdigest(),
            'asset_sha256': asset['sha256']}


def validate(package):
    return validate_payload(*read_package(package))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path, help='Directory containing manifest.json and one PCM WAV')
    args = parser.parse_args()
    try:
        result = validate(args.package)
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({'schema': 'elo-consumable-preflight/v1', 'status': 'invalid_package'}))
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
