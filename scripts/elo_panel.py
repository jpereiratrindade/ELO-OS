#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Local distribution administration; existing ELO Studio stays the editor."""
import http.client
import hashlib
import hmac
from http.cookies import SimpleCookie
from pathlib import Path
import threading
from urllib.parse import urlsplit, unquote

from elo_content import decode, encoded, sync_dir
from elo_import import snapshot, records, project, project_snapshot
from elo_receipts import Receipts
import os
import tempfile


class Panel:
    def __init__(self, bundle, variants, token, selection_file, web_root, studio_port=8080):
        self.bundle = bundle
        self.defaults = variants
        self.token = token
        self.selection_file = Path(selection_file)
        self.web_root = Path(web_root)
        self.studio_port = studio_port
        self.lock = threading.RLock()
        self.receipts = Receipts(self.selection_file.parent / "receipt.json")

    def variants(self):
        with self.lock:
            if not self.selection_file.exists():
                return self.defaults
            return decode(self.selection_file.read_bytes())['variants']

    def status(self):
        manifest, files = snapshot(self.bundle)
        variants = records(files, 'variants')
        atoms = records(files, 'atoms') or records(files, 'objects')
        selected = manifest.get('atom_ids', [])
        choices = []
        for key, value in variants.items():
            presentation = value.get('presentation', {})
            image_info = None
            try:
                projected, _ = project_snapshot(manifest, files, [key])
                image = decode(projected)['pages'][0].get('image')
                if image:
                    image_info = {'alt': image['alt'], 'mime': image['mime']}
                supported = True
            except (ValueError, TypeError, KeyError):
                supported = False
            choices.append({'id': key, 'title': presentation.get('title', key),
                            'text': presentation.get('text', ''), 'supported': supported, 'image': image_info})
        return {'manifest': manifest, 'variants': choices, 'selected': self.variants(),
                'studio_available': self.studio_available(), 'delivery': self.delivery()}

    def delivery(self):
        try:
            payload, _ = project(self.bundle, self.variants())
            expected = hashlib.sha256(payload).hexdigest()
        except (ValueError, OSError, KeyError):
            expected = None
        return self.receipts.status(expected)

    def studio_available(self):
        try:
            connection = http.client.HTTPConnection('127.0.0.1', self.studio_port, timeout=2)
            connection.request('GET', '/api/status', headers={'Authorization': 'Bearer ' + self.token.decode()})
            response = connection.getresponse()
            response.read(1024 * 1024)
            return response.status == 200
        except (OSError, http.client.HTTPException):
            return False
        finally:
            connection.close()

    def select(self, value):
        from elo_server import envelope
        with self.lock:
            if not isinstance(value, dict) or set(value) != {'variants', 'expected_hash'}:
                raise ValueError('Seleção inválida')
            variants = value['variants']
            if not isinstance(variants, list) or any(not isinstance(x, str) for x in variants):
                raise ValueError('Lista de variantes inválida')
            result = decode(envelope(self.bundle, variants))
            if result['source']['content_hash'] != value['expected_hash']:
                raise ValueError('Publicação mudou; atualize a página antes de confirmar')
            self.selection_file.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='.selection-', dir=self.selection_file.parent)
            os.close(fd)
            try:
                with open(name, 'wb') as stream:
                    stream.write(encoded({'variants': variants}))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, self.selection_file)
                sync_dir(self.selection_file.parent)
            finally:
                Path(name).unlink(missing_ok=True)
            return result['source']

    def media_cookie(self):
        return hashlib.sha256(b'ELO_MEDIA_SESSION\0' + self.token).hexdigest()

    def media_authorized(self, value):
        cookie = SimpleCookie()
        try:
            cookie.load(value or '')
            return 'elo_media' in cookie and hmac.compare_digest(cookie['elo_media'].value, self.media_cookie())
        except (ValueError, TypeError):
            return False

    def proxy(self, method, path, body, content_type):
        # Fixed loopback upstream. Never accept an upstream host from a request.
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith(('/api/', '/assets/')) or '\r' in path or '\n' in path:
            raise ValueError('Rota editorial inválida')
        if any(part == '..' for part in unquote(parsed.path).split('/')) or '\\' in unquote(parsed.path):
            raise ValueError('Caminho inválido')
        connection = http.client.HTTPConnection('127.0.0.1', self.studio_port, timeout=15)
        try:
            connection.request(method, path, body=body, headers={
                'Authorization': 'Bearer ' + self.token.decode(), 'Content-Type': content_type})
            response = connection.getresponse()
            data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024:
                raise ValueError('Resposta editorial excedeu limite')
            mime = response.getheader('Content-Type', 'application/json')
            if response.status == 400 and mime.startswith('application/json'):
                value = decode(data)
                if isinstance(value, dict) and 'increment the semantic version' in value.get('error', ''):
                    value['error'] = 'Esta versão já foi publicada com conteúdo diferente. Edite a aplicação, aumente a versão (por exemplo, 0.1.0 para 0.1.1), salve e ative novamente.'
                    value['code'] = 'version_conflict'
                    data = encoded(value)
            return response.status, mime, data
        finally:
            connection.close()
