#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Private upload spool, not an editorial catalog. Valid content stays quarantined."""
from contextlib import contextmanager
import base64
import fcntl
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
import threading
import uuid

from elo_consumable import (IDENTITY, MAX_ASSET, MAX_MANIFEST, canonical_manifest,
                            read_regular, validate_payload)
from elo_content import decode, sync_dir


class IngestError(ValueError):
    def __init__(self, status, code):
        super().__init__(code)
        self.status, self.code = status, code


class Ingest:
    """One server-configured producer instance; keys are scoped to that instance.

    SQLite stores only intake state. No accepted consumables or editorial records.
    The private root and its ancestors must be owned by the service operator.
    """
    def __init__(self, root, token, producer, max_submissions=128, max_bytes=256 * 1024 * 1024):
        if (not re.fullmatch(IDENTITY, producer) or not isinstance(token, bytes)
                or not re.fullmatch(rb'[A-Za-z0-9_-]{32,128}', token)):
            raise ValueError('Invalid ingest identity or credential')
        if type(max_submissions) is not int or type(max_bytes) is not int or min(max_submissions, max_bytes) < 1:
            raise ValueError('Invalid ingest quota')
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if info.st_mode & 0o077 or info.st_uid != os.getuid():
                raise ValueError('Ingest spool must be a private operator-owned directory (0700)')
        finally:
            os.close(fd)
        self.token, self.producer = token, producer
        self.max_submissions, self.max_bytes = max_submissions, max_bytes
        self.lock = threading.RLock()
        # Refuse pre-existing symlink/special files before sqlite opens its files.
        for name in ('intake.sqlite3', 'intake.sqlite3-wal', 'intake.sqlite3-shm', '.lock'):
            path = self.root / name
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise ValueError('Unsafe intake state')
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY, producer TEXT NOT NULL,
                    production_id TEXT NOT NULL, version TEXT NOT NULL,
                    manifest BLOB NOT NULL, manifest_hash TEXT NOT NULL,
                    reserved_bytes INTEGER NOT NULL, status TEXT NOT NULL,
                    rejection TEXT,
                    UNIQUE(producer, production_id, version));
                CREATE TABLE IF NOT EXISTS request_keys (
                    producer TEXT NOT NULL, request_key TEXT NOT NULL,
                    submission_id TEXT NOT NULL REFERENCES submissions(id),
                    PRIMARY KEY(producer, request_key));
            ''')
            # Only leftovers from interrupted writes; active writes hold this lock.
            for path in self.root.glob('.upload-*'):
                if path.is_symlink() or not path.is_file():
                    raise ValueError('Unsafe temporary intake state')
                path.unlink()

    @contextmanager
    def connection(self):
        with self.lock:
            fd = os.open(self.root / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            db = None
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                db = sqlite3.connect(self.root / 'intake.sqlite3', timeout=5)
                os.chmod(self.root / 'intake.sqlite3', 0o600)
                db.row_factory = sqlite3.Row
                db.execute('PRAGMA foreign_keys=ON')
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('PRAGMA synchronous=FULL')
                with db:
                    yield db
            finally:
                if db is not None:
                    db.close()
                os.close(fd)

    def row(self, db, submission):
        if not isinstance(submission, str) or not re.fullmatch(r'sub_[0-9a-f]{32}', submission):
            raise IngestError(404, 'submission_not_found')
        row = db.execute('SELECT * FROM submissions WHERE id=? AND producer=?',
                         (submission, self.producer)).fetchone()
        if row is None:
            raise IngestError(404, 'submission_not_found')
        return row

    @staticmethod
    def receipt(row):
        value = decode(row['manifest'])
        result = {'schema': 'elo-consumable-receipt/v1', 'submission_id': row['id'],
                  'producer_instance_id': row['producer'], 'status': row['status'],
                  'production_id': row['production_id'], 'production_version': row['version'],
                  'manifest_sha256': row['manifest_hash'], 'asset_sha256': value['assets'][0]['sha256'],
                  'consumable_id': None,
                  'rejections': [{'code': row['rejection']}] if row['rejection'] else []}
        if row['status'] == 'quarantined':
            result['pending_reason'] = 'editorial_integration_required'
        return result

    def create(self, value, key):
        if not isinstance(key, str) or not re.fullmatch(IDENTITY, key):
            raise IngestError(400, 'invalid_idempotency_key')
        try:
            payload = canonical_manifest(value)
        except (ValueError, UnicodeError, TypeError):
            raise IngestError(422, 'invalid_manifest') from None
        if len(payload) > MAX_MANIFEST:
            raise IngestError(413, 'manifest_too_large')
        digest = hashlib.sha256(payload).hexdigest()
        with self.connection() as db:
            # A key is permanently bound to a single payload and producer.
            old = db.execute('SELECT s.* FROM submissions s JOIN request_keys k '
                             'ON s.id=k.submission_id WHERE k.producer=? AND k.request_key=?',
                             (self.producer, key)).fetchone()
            if old:
                if old['manifest_hash'] != digest:
                    raise IngestError(409, 'idempotency_conflict')
                return self.receipt(old), False
            old = db.execute('SELECT * FROM submissions WHERE producer=? AND production_id=? AND version=?',
                             (self.producer, value['production_id'], value['production_version'])).fetchone()
            if old and old['manifest_hash'] != digest:
                raise IngestError(409, 'production_version_conflict')
            # Bound keys as well as reserved bytes, including rejected submissions.
            count, reserved = db.execute('SELECT count(*), coalesce(sum(reserved_bytes),0) FROM submissions').fetchone()
            keys = db.execute('SELECT count(*) FROM request_keys').fetchone()[0]
            size = value['assets'][0]['size_bytes']
            if keys >= self.max_submissions * 4 or (not old and
                    (count >= self.max_submissions or reserved + size > self.max_bytes)):
                raise IngestError(429, 'intake_quota_exceeded')
            if not old:
                submission = 'sub_' + uuid.uuid4().hex
                db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?,?,NULL)',
                           (submission, self.producer, value['production_id'], value['production_version'],
                            payload, digest, size, 'staged'))
            else:
                submission = old['id']
            db.execute('INSERT INTO request_keys VALUES(?,?,?)', (self.producer, key, submission))
            return self.receipt(self.row(db, submission)), old is None

    def get(self, submission):
        with self.connection() as db:
            return self.receipt(self.row(db, submission))

    def summaries(self):
        with self.connection() as db:
            submissions = []
            for row in db.execute('SELECT * FROM submissions ORDER BY rowid DESC'):
                value = decode(row['manifest'])
                submissions.append({**self.receipt(row), 'title': value['title'], 'rights': value['rights'],
                                    'duration_ms': value['assets'][0]['duration_ms']})
            return {'schema': 'elo-consumable-intake/v1', 'submissions': submissions}

    def import_package(self, value):
        """Explicit operator import, separately authorized by the admin route."""
        if (not isinstance(value, dict) or set(value) != {'schema', 'manifest', 'asset_base64'}
                or value['schema'] != 'elo-consumable-package/v1'
                or not isinstance(value['asset_base64'], str)
                or len(value['asset_base64']) > 4 * ((MAX_ASSET + 2) // 3)):
            raise IngestError(422, 'invalid_export_package')
        try:
            raw = base64.b64decode(value['asset_base64'], validate=True)
            checked = validate_payload(value['manifest'], raw)
        except (ValueError, UnicodeError, TypeError):
            raise IngestError(422, 'invalid_export_package') from None
        receipt, _ = self.create(value['manifest'], 'import_' + checked['manifest_sha256'])
        submission = receipt['submission_id']
        self.upload(submission, value['manifest']['assets'][0]['asset_id'], raw)
        return self.commit(submission)

    def audio(self, submission):
        with self.connection() as db:
            row = self.row(db, submission)
            if row['status'] != 'quarantined':
                raise IngestError(409, 'audio_not_ready')
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                raw = read_regular(fd, submission + '.wav', MAX_ASSET)
            finally:
                os.close(fd)
            validate_payload(decode(row['manifest']), raw)
            return raw

    def asset_spec(self, submission, asset_id):
        with self.connection() as db:
            value = decode(self.row(db, submission)['manifest'])
            asset = value['assets'][0]
            if asset_id != asset['asset_id']:
                raise IngestError(404, 'asset_not_found')
            return asset

    def upload(self, submission, asset_id, raw):
        with self.connection() as db:
            row = self.row(db, submission)
            asset = decode(row['manifest'])['assets'][0]
            if asset_id != asset['asset_id']:
                raise IngestError(404, 'asset_not_found')
            if len(raw) != asset['size_bytes'] or hashlib.sha256(raw).hexdigest() != asset['sha256']:
                raise IngestError(422, 'asset_integrity_mismatch')
            if row['status'] != 'staged':
                # Exact retries after commit succeed without mutating files.
                return self.receipt(row)
            fd, temporary = tempfile.mkstemp(prefix='.upload-', dir=self.root)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                target = self.root / (submission + '.wav')
                if target.is_symlink() or (target.exists() and not target.is_file()):
                    raise IngestError(409, 'unsafe_spool_file')
                os.replace(temporary, target)
                sync_dir(self.root)
            finally:
                Path(temporary).unlink(missing_ok=True)
            return self.receipt(row)

    def commit(self, submission):
        with self.connection() as db:
            row = self.row(db, submission)
            if row['status'] != 'staged':
                return self.receipt(row)
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                try:
                    raw = read_regular(fd, submission + '.wav', MAX_ASSET)
                except FileNotFoundError:
                    raise IngestError(409, 'assets_missing') from None
            finally:
                os.close(fd)
            rejection = None
            try:
                validate_payload(decode(row['manifest']), raw)
            except (ValueError, UnicodeError):
                rejection = 'invalid_audio_payload'
            status = 'rejected' if rejection else 'quarantined'
            db.execute('UPDATE submissions SET status=?, rejection=? WHERE id=?',
                       (status, rejection, submission))
            return self.receipt(self.row(db, submission))
