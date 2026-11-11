#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Optional real Sister C++ export → ELO authenticated UI import roundtrip."""
import argparse
import base64
import http.client
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_consumable import validate_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sister-root', type=Path, default=ROOT.parents[1] / 'Sister-Studio')
    args = parser.parse_args()
    audio = args.sister_root.resolve() / 'apps/audio'
    executable = audio / 'build/sister_audio'
    if not executable.is_file():
        parser.error('Build Sister-Studio apps/audio first')
    spec = importlib.util.spec_from_file_location('intake_tests', ROOT / 'tests/network/ingest-test.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    intake = module.IntakeTest()
    intake.setUp()
    try:
        with tempfile.TemporaryDirectory(prefix='sister-export-') as temporary:
            root = Path(temporary)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env = dict(os.environ, SISTER_STUDIO_LOCAL_USER_ID='00000000-0000-4000-8000-000000000001')
            process = subprocess.Popen([str(executable), 'serve', '--host', '127.0.0.1', '--port', str(port),
                                        '--web', str(audio / 'web'), '--generated', str(root / 'generated')],
                                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                def request(path, method='GET', body=None, content_type='application/json'):
                    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=20)
                    connection.request(method, path, body, {'Content-Type': content_type})
                    response = connection.getresponse()
                    status, data = response.status, response.read()
                    connection.close()
                    return status, data
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError(process.stderr.read().decode())
                    try:
                        request('/api/health')
                        break
                    except OSError:
                        time.sleep(.05)
                status, body = request('/api/generations', 'POST', json.dumps({'duration_seconds': 5, 'seed': 20261111}))
                assert status == 201, body
                generation = json.loads(body)
                target = '/api/generations/' + generation['id'] + '/elo'
                fields = {'title': 'Composição "ELO" — teste', 'version': '1.0.0', 'license': 'autorizacao-de-teste',
                          'rights_holder': 'fixture-do-teste', 'reviewed': 'true'}
                status, body = request(target, 'POST', urlencode(fields), 'application/x-www-form-urlencoded')
                assert status == 200, body
                package = json.loads(body)
                assert set(package) == {'schema', 'manifest', 'asset_base64'}
                assert package['schema'] == 'elo-consumable-package/v1'
                raw = base64.b64decode(package['asset_base64'], validate=True)
                validate_payload(package['manifest'], raw)
                assert package['manifest']['title'] == fields['title']
                assert 'user_id' not in body.decode() and str(root) not in body.decode()
                status, receipt = intake.request('/manage/ingest/import', value=package, token=module.ADMIN)
                assert status == 200 and receipt['status'] == 'quarantined', receipt
                assert intake.request('/manage/ingest/import', value=package, token=module.ADMIN)[1] == receipt
                preview = intake.ingest.audio(receipt['submission_id'])
                assert preview == raw
                for invalid in [dict(fields, reviewed='false'), dict(fields, license=''), dict(fields, version='01.0.0')]:
                    assert request(target, 'POST', urlencode(invalid), 'application/x-www-form-urlencoded')[0] == 400
                assert request(target, 'POST', urlencode(fields) + '&reviewed=true', 'application/x-www-form-urlencoded')[0] == 400
                print('PASS: real Sister-Studio C++ render/export → ELO contract validation → authenticated manual import → idempotent receipt → exact private audio preview; invalid declarations rejected')
            finally:
                process.terminate()
                process.wait(timeout=5)
                process.stderr.close()
    finally:
        intake.doCleanups()


if __name__ == '__main__':
    main()
