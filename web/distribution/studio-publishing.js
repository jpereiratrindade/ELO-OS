/* ELO-OS Studio adapter: explicitly resolve immutable publication conflicts. */
(() => {
  'use strict';
  const versionPattern = /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/;
  const editorialPlan = plan => Object.fromEntries(Object.entries(plan).filter(
    ([key]) => !['published_versions', 'is_published', 'is_active', 'active_version'].includes(key)));
  const stable = value => JSON.stringify(value, (_, item) => item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);

  function nextVersion(versions) {
    const parsed = versions.filter(v => typeof v === 'string' && versionPattern.test(v))
      .map(v => v.split('.').map(BigInt));
    parsed.sort((a, b) => {
      for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
      return 0;
    });
    const latest = parsed.pop() || [0n, 1n, 0n];
    return `${latest[0]}.${latest[1]}.${latest[2] + 1n}`;
  }

  function chooseVersion(plan) {
    return new Promise(resolve => {
      const dialog = document.createElement('dialog');
      dialog.className = 'modal-content';
      dialog.style.cssText = 'padding:24px;max-width:520px;width:calc(100% - 48px);border:1px solid var(--border-subtle);border-radius:16px;color:var(--text-main);background:var(--bg-surface)';
      dialog.innerHTML = '<form><h2>Publicar nova versão</h2><p class="version-explanation"></p>' +
        '<label for="publication-version">Nova versão da aplicação</label>' +
        '<input id="publication-version" class="input-text" required maxlength="64" style="width:100%;margin:12px 0">' +
        '<p class="version-error" role="alert"></p><div style="display:flex;gap:12px;justify-content:flex-end">' +
        '<button type="button" class="btn btn-secondary">Cancelar</button>' +
        '<button type="submit" class="btn btn-primary">Publicar nova versão</button></div></form>';
      dialog.querySelector('h2').id = 'publication-version-title';
      dialog.setAttribute('aria-labelledby', 'publication-version-title');
      dialog.querySelector('.version-explanation').textContent =
        `A versão ${plan.version} de “${plan.title || plan.bundle_id}” já foi publicada. ` +
        'As alterações de conteúdo, incluindo imagens, precisam de uma nova versão. A anterior será preservada.';
      const input = dialog.querySelector('input');
      const used = new Set([plan.version, ...(plan.published_versions || [])]);
      input.value = nextVersion([...used]);
      const finish = value => { dialog.close(); dialog.remove(); resolve(value); };
      dialog.querySelector('button[type="button"]').addEventListener('click', () => finish(null));
      dialog.addEventListener('cancel', event => { event.preventDefault(); finish(null); });
      dialog.querySelector('form').addEventListener('submit', event => {
        event.preventDefault();
        const value = input.value.trim();
        if (!versionPattern.test(value) || used.has(value)) {
          dialog.querySelector('.version-error').textContent = 'Informe uma versão inédita no formato 0.1.1.';
          return;
        }
        finish(value);
      });
      document.body.appendChild(dialog);
      dialog.showModal();
      input.focus();
      input.select();
    });
  }

  async function plans() {
    const response = await fetch('/api/packages');
    const value = await response.json();
    if (!response.ok || !Array.isArray(value.packages)) throw new Error('Não foi possível consultar as versões da aplicação.');
    return value.packages;
  }

  async function publish(bundleId, requestVersion = chooseVersion) {
    const send = async () => {
      const response = await fetch('/api/publish', { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bundle_id: bundleId || '' }) });
      return response.json();
    };
    let result = await send();
    const conflict = result.code === 'version_conflict' || /increment the semantic version/.test(result.error || '');
    if (result.success || !conflict) return result;
    if (!bundleId) {
      const response = await fetch('/api/status');
      const status = await response.json();
      if (!response.ok) throw new Error('Não foi possível identificar a aplicação para publicar.');
      bundleId = status.active_bundle?.bundle_id;
    }
    const plan = (await plans()).find(item => item.bundle_id === bundleId);
    if (!plan) throw new Error('Abra a aplicação para definir e publicar uma nova versão.');
    const version = await requestVersion(plan);
    if (version === null) return { cancelled: true };
    if (!versionPattern.test(version) || [plan.version, ...(plan.published_versions || [])].includes(version)) {
      throw new Error('A nova versão precisa ser inédita e seguir o formato 0.1.1.');
    }
    const fresh = (await plans()).find(item => item.bundle_id === bundleId);
    if (!fresh || stable(editorialPlan(fresh)) !== stable(editorialPlan(plan))
        || (fresh.published_versions || []).includes(version)) {
      throw new Error('A aplicação mudou enquanto você escolhia a versão. Atualize e publique novamente.');
    }
    const response = await fetch('/api/packages', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...editorialPlan(fresh), version }) });
    const saved = await response.json();
    if (!response.ok || !saved.success) throw new Error(saved.error || 'Não foi possível salvar a nova versão.');
    result = await send();
    return result;
  }

  window.eloStudioPublishing = { publish, nextVersion };
})();
