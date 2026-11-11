#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Explicitly upload one validated PCM package; quarantined is NOT editorial acceptance."""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import re
import ssl
from urllib.parse import urlsplit

from elo_consumable import canonical_manifest, read_package, validate_payload
from elo_content import decode
from elo_server import terminal_token


class Publisher:
    def __init__(self, endpoint, token, certificate=None, allow_loopback_http=False):
        url = urlsplit(endpoint)
        if (url.username or url.password or url.query or url.fragment or url.path not in ('', '/')
                or not url.hostname or url.scheme not in ('https', 'http')):
            raise ValueError('Endpoint must be an HTTPS origin without path, user info or query')
        if url.scheme == 'http' and not (allow_loopback_http and url.hostname == '127.0.0.1'):
            raise ValueError('HTTP is restricted to explicit loopback development mode')
        self.url, self.token = url, token
        self.context = ssl.create_default_context(cafile=str(certificate) if certificate else None)

    def request(self, method, path, raw=b'', headers=None):
        if self.url.scheme == 'https':
            connection = http.client.HTTPSConnection(self.url.hostname, self.url.port or 443,
                                                      context=self.context, timeout=20)
        else:
            connection = http.client.HTTPConnection(self.url.hostname, self.url.port or 80, timeout=20)
        request_headers = {'Authorization': 'Bearer ' + self.token.decode('ascii'),
                           'Content-Length': str(len(raw)), **(headers or {})}
        try:
            connection.request(method, path, body=raw, headers=request_headers)
            response = connection.getresponse()
            data = response.read(65537)
            if len(data) > 65536:
                raise ValueError('Intake response too large')
            value = decode(data)
            if not isinstance(value, dict):
                raise ValueError('Invalid intake response')
            if response.status not in (200, 201):
                # No redirects: credentials are never forwarded to another origin.
                raise ValueError('Intake refused request: ' + str(value.get('error', response.status)))
            return value
        finally:
            connection.close()

    def publish(self, package):
        value, raw = read_package(package)
        expected = validate_payload(value, raw)
        canonical = canonical_manifest(value)
        key = 'manifest_' + hashlib.sha256(canonical).hexdigest()
        receipt = self.request('POST', '/v1/ingest/submissions', canonical,
                               {'Content-Type': 'application/json', 'Idempotency-Key': key})
        submission = receipt.get('submission_id')
        if (not isinstance(submission, str) or not re.fullmatch(r'sub_[0-9a-f]{32}', submission)
                or receipt.get('schema') != 'elo-consumable-receipt/v1'
                or receipt.get('manifest_sha256') != expected['manifest_sha256']
                or receipt.get('production_id') != value['production_id']
                or receipt.get('production_version') != value['production_version']):
            raise ValueError('Intake receipt does not match submitted production')
        base = '/v1/ingest/submissions/' + submission
        if receipt.get('status') == 'staged':
            asset = value['assets'][0]
            self.request('PUT', base + '/assets/' + asset['asset_id'], raw, {'Content-Type': asset['mime']})
            receipt = self.request('POST', base + '/commit')
        if (receipt.get('submission_id') != submission
                or receipt.get('manifest_sha256') != expected['manifest_sha256']
                or receipt.get('asset_sha256') != expected['asset_sha256']):
            raise ValueError('Final intake receipt does not match submitted package')
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--certificate', type=Path, help='Explicit local CA/certificate trust; verification remains enabled')
    parser.add_argument('--allow-loopback-http', action='store_true')
    args = parser.parse_args()
    try:
        publisher = Publisher(args.endpoint, terminal_token(args.token_file), args.certificate, args.allow_loopback_http)
        receipt = publisher.publish(args.package)
        print(json.dumps(receipt, ensure_ascii=True))
        return 0 if receipt.get('status') in ('quarantined', 'accepted') else 1
    except (OSError, ValueError, UnicodeError, http.client.HTTPException):
        print(json.dumps({'error': 'publication_failed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
