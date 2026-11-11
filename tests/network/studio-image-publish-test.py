#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Optional integration with a compiled ELO backend; isolated workspace and IPC."""
import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_content import decode, read_active
from elo_import import import_bundle, project
from elo_panel import Panel
from elo_server import server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elo-root', type=Path, default=ROOT.parent / 'elo')
    args = parser.parse_args()
    executable = args.elo_root.resolve() / 'build/apps/elo-admin/elo-admin'
    if not executable.is_file():
        parser.error('Compile elo-admin in --elo-root before running this optional test')
    with tempfile.TemporaryDirectory(prefix='elo-image-publication-') as temporary:
        root = Path(temporary)
        content = root / 'content'
        atom = {'schema_version': '0.2', 'content_id': 'image-atom', 'type': 'entity',
                'title': 'Imagem de teste', 'modalities': {'image': []}, 'provenance': {'reviewed': True}}
        plan = {'schema_version': '0.2', 'bundle_id': 'image-test', 'version': '0.1.0',
                'title': 'Publicação de imagem', 'atom_ids': ['image-atom']}
        variant = {'variant_id': 'image-variant', 'content_id': 'image-atom', 'role': 'ambient',
                   'interaction': 'none', 'presentation': {'title': 'Imagem', 'text': 'Teste isolado', 'media': []}}
        for name, value in [('manifest.json', plan), ('catalog/atoms/image-atom.json', atom),
                            ('catalog/variants/variants.json', [variant])]:
            path = content / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        token = 'a' * 43
        env = dict(os.environ, ELO_CONTENT_DIR=str(content), ELO_WEB_ROOT=str(ROOT / 'web/distribution'),
                   ELO_ADMIN_TOKEN=token, ELO_ADMIN_PORT=str(port), ELO_CONTROL_SOCKET=str(root / 'no-kiosk.sock'))
        process = subprocess.Popen([str(executable)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        gateway = None
        try:
            def api(path, method='GET', value=None):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                connection.request(method, path, None if value is None else json.dumps(value),
                                   {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
                response = connection.getresponse()
                status, result = response.status, json.loads(response.read())
                connection.close()
                return status, result

            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError(process.stderr.read().decode())
                try:
                    api('/api/packages')
                    break
                except OSError:
                    time.sleep(0.05)
            else:
                raise RuntimeError('Isolated ELO backend did not start')
            status, first = api('/api/publish', 'POST', {'bundle_id': 'image-test'})
            assert status == 200 and first['success'], first
            previous = content / 'bundles/image-test-0.1.0'
            before = {str(p.relative_to(previous)): p.read_bytes() for p in previous.rglob('*') if p.is_file()}
            image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDXsAAAAASUVORK5CYII=')
            status, upload = api('/api/upload', 'POST', {'folder': 'images', 'filename': 'test.png',
                                                       'base64_data': base64.b64encode(image).decode()})
            assert status == 200 and upload['success'], upload
            atom['modalities']['image'] = [upload['path']]
            assert api('/api/atoms/image-atom', 'PUT', atom)[0] == 200
            panel = Panel(content / 'current', ['image-variant'], token.encode(), root / 'selection.json',
                          ROOT / 'web/distribution', studio_port=port)
            gateway = server(content / 'current', ['image-variant'], b't' * 43, panel=panel)
            threading.Thread(target=gateway.serve_forever, daemon=True).start()
            # Actual gateway, backend, SQLite, publisher and JavaScript helper.
            script = r'''
                const fs = require('node:fs'); const vm = require('node:vm');
                const context = {window: {}, fetch: (path, init={}) => fetch(process.env.TEST_ORIGIN + path,
                  {...init, headers: {...init.headers, Authorization: 'Bearer ' + process.env.TEST_ADMIN}})};
                vm.createContext(context); vm.runInContext(fs.readFileSync(process.env.TEST_HELPER,'utf8'), context);
                context.window.eloStudioPublishing.publish('image-test', async plan => {
                  if (plan.version !== '0.1.0') throw Error('Unexpected draft version');
                  return context.window.eloStudioPublishing.nextVersion([plan.version, ...plan.published_versions]);
                }).then(result => { console.log(JSON.stringify(result)); if (!result.success) process.exitCode=1; })
                  .catch(error => { console.error(error); process.exitCode=1; });
            '''
            outcome = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=20,
                                     env=dict(os.environ, TEST_ORIGIN=f'http://127.0.0.1:{gateway.server_port}',
                                              TEST_ADMIN=token, TEST_HELPER=str(ROOT / 'web/distribution/studio-publishing.js')))
            assert outcome.returncode == 0, outcome.stdout + outcome.stderr
            assert json.loads(outcome.stdout)['version'] == '0.1.1'
            assert before == {str(p.relative_to(previous)): p.read_bytes() for p in previous.rglob('*') if p.is_file()}
            assert 'image' not in decode(project(previous, ['image-variant'])[0])['pages'][0]
            current, _ = project(content / 'current', ['image-variant'])
            assert decode(current)['pages'][0]['image']['sha256'] == hashlib.sha256(image).hexdigest()
            import_bundle(content / 'current', root / 'client-cache', ['image-variant'])
            process.terminate()
            process.wait(timeout=5)
            assert base64.b64decode(read_active(root / 'client-cache')['pages'][0]['image']['base64']) == image
            print('PASS: real ELO image upload → immutable version conflict → Studio 0.1.1 → image projection → cache readable without backend; 0.1.0 preserved')
        finally:
            if gateway:
                gateway.shutdown()
                gateway.server_close()
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            process.stderr.close()


if __name__ == '__main__':
    main()
