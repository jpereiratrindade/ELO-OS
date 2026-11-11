// SPDX-License-Identifier: GPL-3.0-only
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const context = { window: {}, console };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root, 'web/distribution/studio-publishing.js'), 'utf8'), context);
const { publish, nextVersion } = context.window.eloStudioPublishing;
const original = { bundle_id: 'app', title: 'Imagem de teste', version: '0.1.0',
  atom_ids: ['image-atom', 'text-atom'], metadata: { source: 'original' },
  published_versions: ['0.1.0', '0.1.2'], is_active: true };

async function run() {
  assert.equal(nextVersion(['0.1.0', '0.1.9', '0.1.10']), '0.1.11');
  assert.equal(nextVersion(['1.0.0', 'bad', '0.9.99']), '1.0.1');
  for (const scenario of ['publish', 'cancel', 'changed', 'validation', 'existing', 'save-fails', 'empty-target']) {
    const calls = [];
    let planReads = 0;
    let publishCount = 0;
    let saved;
    context.fetch = async (url, init = {}) => {
      calls.push([url, init]);
      let body;
      let ok = true;
      if (url === '/api/publish') {
        publishCount++;
        if (scenario === 'validation') body = { success: false, error: 'Missing media' };
        else body = publishCount === 1 ? { success: false, code: 'version_conflict' }
          : { success: true, bundle_id: 'app', version: '0.1.3' };
      } else if (url === '/api/status') body = { active_bundle: { bundle_id: 'app' } };
      else if (url === '/api/packages' && init.method === 'POST') {
        saved = JSON.parse(init.body);
        body = { success: scenario !== 'save-fails' };
        ok = body.success;
      } else if (url === '/api/packages') {
        planReads++;
        body = { packages: [JSON.parse(JSON.stringify(original))] };
        if (scenario === 'changed' && planReads > 1) body.packages[0].metadata.source = 'another-editor';
      } else throw new Error(`Unexpected request ${url}`);
      return { ok, json: async () => body };
    };
    const choose = async plan => {
      assert.equal(plan.version, '0.1.0');
      return scenario === 'cancel' ? null : scenario === 'existing' ? '0.1.0' : '0.1.3';
    };
    if (['changed', 'existing', 'save-fails'].includes(scenario)) {
      await assert.rejects(publish('app', choose));
      assert.equal(publishCount, 1);
      if (scenario !== 'save-fails') assert.equal(saved, undefined);
    } else {
      const result = await publish(scenario === 'empty-target' ? '' : 'app', choose);
      if (scenario === 'publish' || scenario === 'empty-target') {
        assert.equal(result.success, true);
        assert.equal(saved.version, '0.1.3');
        assert.deepEqual(saved.atom_ids, original.atom_ids);
        assert.deepEqual(saved.metadata, original.metadata);
        assert.equal(saved.published_versions, undefined);
        assert.equal(publishCount, 2);
        assert.equal(JSON.parse(calls.at(-1)[1].body).bundle_id, 'app');
      } else {
        assert.equal(saved, undefined);
        assert.equal(publishCount, 1);
        assert.equal(result.cancelled, scenario === 'cancel' ? true : undefined);
      }
    }
  }
  console.log('PASS: Studio version conflict, cancellation, concurrent edit, validation, save failure and image atom selection preserved');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
