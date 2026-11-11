/* Explicit reception UI; intake quarantine is separate from the ELO catalog. */
document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.tab-nav');
  if (!nav) return;
  const tab = document.createElement('button');
  tab.className = 'tab-btn';
  tab.dataset.tab = 'tab-sister-productions';
  tab.textContent = 'Produções Sister-Studio';
  nav.insertBefore(tab, nav.querySelector('[data-tab="tab-media"]'));
  const pane = document.createElement('section');
  pane.id = 'tab-sister-productions';
  pane.className = 'tab-pane';
  pane.innerHTML = '<div class="pane-header-row"><div><h3 class="pane-title">Produções Sister-Studio</h3>' +
    '<p class="pane-subtitle">Receba composições exportadas e confira os arquivos antes da integração editorial.</p></div>' +
    '<button class="btn btn-secondary" type="button" id="sister-intake-refresh">Atualizar recepção</button></div>' +
    '<div class="sister-intake-panel"><h4>Receber pacote do Sister-Studio</h4>' +
    '<p>No Sister-Studio · Composição, use “Exportar para ELO”. Escolha aqui o arquivo .elo.json baixado.</p>' +
    '<form id="sister-intake-form"><label for="sister-intake-file">Pacote da produção</label>' +
    '<input id="sister-intake-file" type="file" accept=".elo.json,application/json" required>' +
    '<button type="submit" class="btn btn-primary">Receber produção</button></form>' +
    '<p id="sister-intake-message" role="status" aria-live="polite"></p></div>' +
    '<p class="pane-subtitle">Produções recebidas ficam em quarentena. A entrada no catálogo, o vínculo a átomos e a publicação de aplicações ainda dependem da integração editorial ELO.</p>' +
    '<div id="sister-intake-list" class="sister-intake-list"></div>';
  nav.after(pane);
  const toolbar = document.querySelector('.action-toolbar');
  const shortcut = document.createElement('button');
  shortcut.type = 'button';
  shortcut.className = 'btn btn-secondary';
  shortcut.textContent = 'Receber do Sister-Studio';
  toolbar?.append(shortcut);
  shortcut.addEventListener('click', () => { tab.click(); pane.scrollIntoView({behavior: 'smooth'}); });
  const message = pane.querySelector('#sister-intake-message');
  const file = pane.querySelector('#sister-intake-file');
  const list = pane.querySelector('#sister-intake-list');
  const audioUrls = new Set();

  async function request(path, options = {}, audio = false) {
    const token = sessionStorage.getItem('eloAdminToken');
    if (!token) throw new Error('Entre pelo painel Distribuição para autorizar a recepção.');
    const response = await fetch(path, {...options, headers: {...options.headers, Authorization: `Bearer ${token}`}});
    if (!response.ok) {
      let value = {};
      try { value = await response.json(); } catch {}
      const errors = {invalid_export_package: 'Pacote inválido: confira formato, hash, duração e direitos.',
        production_version_conflict: 'Esta versão da produção já foi recebida com conteúdo diferente. Exporte uma nova versão.',
        ingest_disabled: 'A recepção ainda não está habilitada nesta instalação.',
        intake_quota_exceeded: 'A recepção atingiu o limite de armazenamento. Solicite manutenção.',
        unauthorized: 'Sua sessão expirou. Entre novamente no painel Distribuição.'};
      throw new Error(errors[value.error] || 'Não foi possível concluir a recepção.');
    }
    return audio ? response.blob() : response.json();
  }

  async function refresh() {
    try {
      const state = await request('/manage/ingest');
      if (state.enabled === false) throw new Error('A recepção ainda não está habilitada nesta instalação.');
      for (const url of audioUrls) URL.revokeObjectURL(url);
      audioUrls.clear();
      list.replaceChildren();
      for (const item of state.submissions || []) {
        const card = document.createElement('article');
        card.className = 'sister-intake-panel';
        const title = document.createElement('h4');
        title.textContent = item.title || item.production_id;
        const details = document.createElement('p');
        details.textContent = `Produção v${item.production_version} · ${(item.duration_ms / 1000).toFixed(1)} s · ` +
          ({quarantined: 'Recebida — aguardando integração editorial', rejected: 'Recusada', staged: 'Envio incompleto'}[item.status] || item.status);
        const rights = document.createElement('p');
        rights.textContent = `Direitos declarados: ${item.rights?.license || '—'} · ${item.rights?.rights_holder || '—'}`;
        card.append(title, details, rights);
        if (item.status === 'quarantined') {
          const button = document.createElement('button');
          button.type = 'button'; button.className = 'btn btn-secondary'; button.textContent = 'Ouvir produção recebida';
          button.addEventListener('click', async () => {
            button.disabled = true;
            try {
              const blob = await request(`/manage/ingest/${item.submission_id}/audio`, {}, true);
              const player = document.createElement('audio');
              const url = URL.createObjectURL(blob); audioUrls.add(url);
              player.src = url; player.controls = true; player.setAttribute('aria-label', item.title || 'Produção recebida');
              button.replaceWith(player); player.play().catch(() => {});
            } catch (error) { message.textContent = error.message; button.disabled = false; }
          });
          card.append(button);
        }
        list.append(card);
      }
      if (!list.children.length) list.textContent = 'Nenhuma produção recebida. Exporte uma composição no Sister-Studio para começar.';
    } catch (error) { message.textContent = error.message; }
  }
  tab.addEventListener('click', refresh);
  pane.querySelector('#sister-intake-refresh').addEventListener('click', refresh);
  pane.querySelector('form').addEventListener('submit', async event => {
    event.preventDefault();
    const selected = file.files[0];
    if (!selected || selected.size > 12 * 1024 * 1024) {
      message.textContent = 'Escolha um pacote ELO de até 12 MiB.'; return;
    }
    const button = event.submitter || event.target.querySelector('button[type="submit"]');
    button.disabled = true; message.textContent = 'Validando e recebendo produção…';
    try {
      await request('/manage/ingest/import', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: await selected.text()});
      message.textContent = 'Produção recebida e validada. Está em quarentena, aguardando integração editorial ELO.';
      file.value = ''; await refresh();
    } catch (error) { message.textContent = error.message; }
    finally { button.disabled = false; }
  });
});
