#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Optional Firefox test: real Studio tab, file import and authenticated preview."""
import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_studio_assets import publication_actions, versioned_assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elo-root', type=Path, default=ROOT.parent / 'elo')
    args = parser.parse_args()
    firefox = shutil.which('firefox')
    if not firefox:
        parser.error('Firefox required for this optional browser test')
    spec = importlib.util.spec_from_file_location('intake_tests', ROOT / 'tests/network/ingest-test.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    intake = module.IntakeTest()
    intake.setUp()
    try:
        with tempfile.TemporaryDirectory(prefix='elo-studio-browser-') as temporary:
            root = Path(temporary)
            web = root / 'web'
            shutil.copytree(ROOT / 'web/distribution', web)
            (web / 'studio').mkdir()
            original = args.elo_root / 'web/admin'
            html = versioned_assets((original / 'index.html').read_text()).replace(
                '<script src="app.js?', '<script src="/probe.js"></script><script src="app.js?')
            (web / 'studio/index.html').write_text(html)
            (web / 'studio/app.js').write_text(publication_actions((original / 'app.js').read_text()))
            shutil.copyfile(original / 'app.css', web / 'studio/app.css')
            intake.panel.web_root = web
            package = {'schema': 'elo-consumable-package/v1', 'manifest': intake.fixture.value,
                       'asset_base64': base64.b64encode(intake.fixture.raw).decode()}
            report_event = threading.Event()
            report = {}
            probe = '''
              sessionStorage.setItem('eloAdminToken', TOKEN);
              window.prompt = () => TOKEN;
              window.confirm = () => false;
              const errors=[];window.addEventListener('error',event=>errors.push(event.message));
              window.addEventListener('load', async () => {
                let phase='open-tab';
                const pause = () => new Promise(resolve => setTimeout(resolve, 50));
                async function waitFor(test) { for(let i=0;i<150;i++){if(test())return;await pause();}throw Error('DOM timeout'); }
                try {
                  const tab=document.querySelector('[data-tab="tab-sister-productions"]');
                  if(!tab)throw Error('Sister tab absent');
                  if(![...document.querySelectorAll('button')].some(b=>b.textContent==='Receber do Sister-Studio'))throw Error('Main shortcut absent');
                  tab.click();
                  await waitFor(()=>document.getElementById('tab-sister-productions').classList.contains('active'));
                  phase='import-file';
                  const file=new File([JSON.stringify(PACKAGE)],'producao.elo.json',{type:'application/json'});
                  const transfer=new DataTransfer();transfer.items.add(file);
                  document.getElementById('sister-intake-file').files=transfer.files;
                  document.getElementById('sister-intake-form').requestSubmit();
                  await waitFor(()=>document.getElementById('sister-intake-list').textContent.includes(PACKAGE.manifest.title));
                  phase='preview-audio';
                  const listen=[...document.querySelectorAll('#sister-intake-list button')].find(b=>b.textContent==='Ouvir produção recebida');
                  if(!listen)throw Error('Private audio action absent');listen.click();
                  await waitFor(()=>document.querySelector('#sister-intake-list audio'));
                  await fetch('/probe-report',{method:'POST',body:JSON.stringify({success:true,tab:tab.textContent,quarantine:document.getElementById('sister-intake-list').textContent.includes('aguardando integração editorial')})});
                } catch(error) {
                  await fetch('/probe-report',{method:'POST',body:JSON.stringify({success:false,error:error.message,phase,errors,message:document.getElementById('sister-intake-message')?.textContent})});
                }
              });
            '''.replace('TOKEN', json.dumps(module.ADMIN.decode())).replace('PACKAGE', json.dumps(package))

            class Proxy(BaseHTTPRequestHandler):
                def log_message(self, *_):
                    pass

                def respond(self, status, data, mime='application/javascript'):
                    self.send_response(status)
                    self.send_header('Content-Type', mime)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

                def do_GET(self):
                    if self.path == '/probe.js':
                        self.respond(200, probe.encode())
                    else:
                        self.forward()

                def do_POST(self):
                    if self.path == '/probe-report':
                        report.update(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                        self.respond(200, b'{}', 'application/json')
                        report_event.set()
                    else:
                        self.forward()

                def forward(self):
                    body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                    connection = http.client.HTTPConnection('127.0.0.1', intake.service.server_port, timeout=10)
                    connection.request(self.command, self.path, body, dict(self.headers))
                    response = connection.getresponse()
                    self.send_response(response.status)
                    for name, value in response.getheaders():
                        if name.lower() not in ('server', 'date', 'connection'):
                            self.send_header(name, value)
                    self.end_headers()
                    self.wfile.write(response.read())
                    connection.close()

            proxy = ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
            threading.Thread(target=proxy.serve_forever, daemon=True).start()
            profile = root / 'firefox'
            profile.mkdir()
            process = subprocess.Popen([firefox, '--headless', '--no-remote', '--profile', str(profile),
                                        f'http://127.0.0.1:{proxy.server_port}/studio/'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       env=dict(os.environ, MOZ_CRASHREPORTER_DISABLE='1'))
            try:
                if not report_event.wait(30):
                    raise RuntimeError('Firefox did not report UI result')
                assert report.get('success') and report.get('quarantine'), report
                print('PASS: Firefox shows Sister-Studio tab and main shortcut, imports a real file, displays quarantine and opens authenticated audio preview')
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                proxy.shutdown()
                proxy.server_close()
    finally:
        intake.doCleanups()


if __name__ == '__main__':
    main()
