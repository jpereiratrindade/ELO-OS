'use strict';
const byId = id => document.getElementById(id);
let token = sessionStorage.getItem('eloAdminToken') || '';
let state = null;
let selected = [];
let credentialUrl = null;
function message(text, error=false) { byId('message').textContent = text; byId('message').classList.toggle('error', error); }
async function api(path, options={}) {
  const response = await fetch(path, {...options, headers: {...options.headers, Authorization: `Bearer ${token}`, 'Content-Type':'application/json'}});
  if (response.status === 401) { logout(); throw new Error('Chave administrativa inválida.'); }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Operação não concluída.');
  return data;
}
function logout() { if(credentialUrl){URL.revokeObjectURL(credentialUrl);credentialUrl=null;}byId('credential-ready').hidden=true;token=''; state=null; sessionStorage.removeItem('eloAdminToken'); byId('login').hidden=false; byId('dashboard').hidden=true; byId('logout').hidden=true; }
function preview() {
  const container = byId('preview'); container.replaceChildren();
  for (const [index,id] of selected.entries()) {
    const variant=state.variants.find(v=>v.id===id); if(!variant)continue;
    const article=document.createElement('article'); const title=document.createElement('h2'); const body=document.createElement('p');
    title.textContent=`${index+1}. ${variant.title}`; body.textContent=variant.text; article.append(title,body);if(variant.image){const note=document.createElement('p');note.className='hint';note.textContent=`Imagem incluída no cliente: ${variant.image.alt}`;article.append(note);}container.append(article);
  }
  if(!selected.length)container.textContent='Selecione conteúdo para conferir prévia.';
}
function render() {
  renderTerminals(state.terminals || []);
  byId('autoplay').checked=state.exposure_seconds>0;
  byId('exposure').value=state.exposure_seconds || 15;
  byId('login').hidden=true;byId('dashboard').hidden=false;byId('logout').hidden=false;
  byId('title').textContent=state.manifest.title;
  byId('version').textContent=`Versão ${state.manifest.version} · ${state.manifest.bundle_id}`;
  byId('count').textContent=`${state.selected.length} página(s) selecionada(s)`;
  byId('studio-status').textContent=state.studio_available?'Disponível':'Indisponível';
  const container=byId('variants');container.replaceChildren();
  for(const variant of state.variants) {
    const label=document.createElement('label');label.className='variant'+(variant.supported?'':' unsupported');
    const check=document.createElement('input');check.type='checkbox';check.value=variant.id;check.checked=selected.includes(variant.id);check.disabled=!variant.supported;
    check.addEventListener('change',()=>{if(check.checked){if(selected.length===32){check.checked=false;message('Limite de 32 páginas.',true);return;}selected.push(variant.id);}else selected=selected.filter(id=>id!==variant.id);preview();});
    const detail=document.createElement('div');const title=document.createElement('strong');title.textContent=variant.title;const id=document.createElement('small');id.textContent=variant.id;const text=document.createElement('p');text.textContent=variant.text;detail.append(title,id,text);
    if(variant.interaction==='reveal'){const tag=document.createElement('span');tag.className='tag';tag.textContent=state.exposure_seconds>0?'Revelação automática':'Toque para revelar';detail.append(tag);}
    if(variant.image){const tag=document.createElement('span');tag.className='tag';tag.textContent='Texto + imagem';detail.append(tag);}
    if(variant.media){const tag=document.createElement('span');tag.className='tag';tag.textContent=variant.media.kind==='video'?'Vídeo offline':'Áudio offline';detail.append(tag);}
    if(!variant.supported){const tag=document.createElement('span');tag.className='tag';tag.textContent='Requer capacidade ainda não disponível no cliente';detail.append(tag);}
    label.append(check,detail);container.append(label);
  }
  preview();
}
async function refresh(){try{state=await api('/manage/status');selected=[...state.selected];render();message('Publicação carregada.');}catch(error){message(error.message,true);}}
byId('login-form').addEventListener('submit',async event=>{event.preventDefault();token=byId('key').value.trim();byId('key').value='';try{state=await api('/manage/status');sessionStorage.setItem('eloAdminToken',token);selected=[...state.selected];render();message('Acesso administrativo autorizado.');}catch(error){message(error.message,true);}});
byId('logout').addEventListener('click',async()=>{try{await api('/manage/logout',{method:'POST'});}catch{}logout();message('Sessão encerrada neste navegador.');});
byId('refresh').addEventListener('click',refresh);
byId('selection-form').addEventListener('submit',async event=>{event.preventDefault();if(!selected.length){message('Selecione ao menos uma página compatível.',true);return;}byId('publish').disabled=true;try{await api('/manage/selection',{method:'POST',body:JSON.stringify({variants:selected,expected_hash:state.manifest.content_hash,exposure_seconds:byId('autoplay').checked?Number(byId('exposure').value):0})});await refresh();message('Seleção publicada. Cliente consulta em até 30 segundos; modo automático aplica no fim do ciclo. Cliente manual aplica ao Recomeçar.');}catch(error){message(error.message,true);}finally{byId('publish').disabled=false;}});
if(token)refresh();

let deliveryBusy=false;
setInterval(async()=>{
  if(!token || !state || document.hidden || deliveryBusy)return;
  deliveryBusy=true;
  try{renderTerminals(await api('/manage/terminals'));}
  catch{byId('terminals-summary').textContent='Não foi possível atualizar situação do terminal.';}
  finally{deliveryBusy=false;}
},5000);

function renderTerminals(terminals) {
  const container=byId('terminals');container.replaceChildren();
  byId('terminals-summary').textContent=`${terminals.filter(t=>t.recent&&!t.revoked).length} com contato recente · ${terminals.length} cadastrado(s)`;
  for(const terminal of terminals){
    const card=document.createElement('article');card.className='terminal-card';card.dataset.terminalId=terminal.id;
    const name=document.createElement('h3');name.textContent=terminal.name;
    const connection=document.createElement('p');connection.className='terminal-status'+(terminal.recent&&!terminal.revoked?' recent':(terminal.last_seen?' stale':''));
    connection.textContent=terminal.revoked?'Credencial revogada':terminal.recent?'Contato recente':terminal.downtime_label?`Sem contato recente (há ${terminal.downtime_label})`:terminal.last_seen?'Sem comunicação recente':'Aguardando primeira comunicação';
    const delivery=document.createElement('p');delivery.textContent=terminal.label;
    const display=document.createElement('p');display.className='terminal-display';
    const shown=terminal.display;
    display.textContent=shown?`${shown.publication} · Página ${shown.page}/${shown.pages}: ${shown.title}`:'Página ainda não informada pelo cliente.';
    const mode=document.createElement('p');mode.className='hint';mode.textContent=shown?(shown.mode==='automatic'?`Sequência automática · ${shown.exposure_seconds} s por página`:'Navegação manual'):'';
    const seen=document.createElement('p');seen.className='hint';seen.textContent=terminal.last_seen?`Último contato: ${new Date(terminal.last_seen*1000).toLocaleString('pt-BR')}`:'Sem contato registrado.';
    card.append(name,connection,display,mode,delivery,seen);
    if(terminal.telemetry){
      const tele=terminal.telemetry;
      const teleDiv=document.createElement('div');teleDiv.className='terminal-telemetry';
      const items=[];
      if(tele.cpu_temp_c!==null&&tele.cpu_temp_c!==undefined){
        const isHot=tele.cpu_temp_c>=75;
        items.push(`<span class="tele-item${isHot?' alert':''}">🌡️ ${tele.cpu_temp_c}°C</span>`);
      }
      if(tele.voltage_v!==null&&tele.voltage_v!==undefined){
        const isLow=tele.voltage_v<4.75||tele.under_voltage;
        items.push(`<span class="tele-item${isLow?' alert':''}">⚡ ${tele.voltage_v}V${tele.under_voltage?' (subtensão!)':''}</span>`);
      } else if(tele.under_voltage){
        items.push(`<span class="tele-item alert">⚡ Subtensão detectada!</span>`);
      }
      if(tele.cpu_load_1m!==null&&tele.cpu_load_1m!==undefined){
        items.push(`<span class="tele-item">⚙️ Carga: ${tele.cpu_load_1m}</span>`);
      }
      if(tele.memory_free_mb!==null&&tele.memory_free_mb!==undefined){
        const ramGb=(tele.memory_free_mb/1024).toFixed(1);
        items.push(`<span class="tele-item">🧠 RAM: ${ramGb}GB</span>`);
      }
      if(items.length){
        teleDiv.innerHTML='<small class="tele-label">SAÚDE DO HARDWARE (TEMPO REAL)</small><div class="tele-row">'+items.join('')+'</div>';
        card.append(teleDiv);
      }
    }
    if(terminal.events&&terminal.events.length){
      const history=document.createElement('div');history.className='terminal-history';
      const hTitle=document.createElement('h4');hTitle.textContent='Histórico de conectividade';
      const list=document.createElement('ul');list.className='terminal-events-list';
      for(const ev of [...terminal.events].reverse().slice(0,5)){
        const li=document.createElement('li');li.className=ev.type||'';
        const timeStr=new Date(ev.time*1000).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
        li.textContent=`${timeStr} · ${ev.label}`;
        list.append(li);
      }
      history.append(hTitle,list);
      card.append(history);
    }
    if(terminal.control?.supported&&!terminal.revoked){
      const control=terminal.control;
      const note=document.createElement('p');note.className='hint terminal-control-status';note.setAttribute('aria-live','polite');
      const labels={pending:'Aguardando recebimento do comando pelo totem.',accepted:'Comando recebido pelo totem. Aguardando execução.',reboot_observed:'Totem conectado após reinicialização.',expired:'Prazo encerrado: comando não recebido.',unconfirmed:'Comando recebido; execução não confirmada.',failed:'O totem não conseguiu executar o comando.',cancelled:'Comando cancelado após mudança de inicialização ou revogação.'};
      note.textContent=control.command?`${control.command.action==='reboot'?'Reiniciar':'Desligar'} · ${labels[control.command.state]||'Estado desconhecido'}`:control.available?'Manutenção disponível':'Manutenção sem contato recente';
      const actions=document.createElement('div');actions.className='terminal-actions';
      for(const [action,label] of [['reboot','Reiniciar'],['poweroff','Desligar']]){
        const button=document.createElement('button');button.type='button';button.textContent=label;button.className=action==='poweroff'?'danger':'';
        button.disabled=!control.available||control.busy;button.setAttribute('aria-label',`${label} ${terminal.name}`);
        button.addEventListener('click',async()=>{
          const detail=action==='poweroff'?'Será necessário ligar o aparelho fisicamente para voltar a usá-lo.':'A apresentação será interrompida durante a reinicialização.';
          if(!window.confirm(`${label} “${terminal.name}”?\n\n${detail}`))return;
          for(const sibling of actions.querySelectorAll('button'))sibling.disabled=true;
          try{
            await api(`/manage/terminals/${terminal.id}/power`,{method:'POST',body:JSON.stringify({action,request_id:crypto.randomUUID()})});
            renderTerminals(await api('/manage/terminals'));message(`${label}: solicitação enviada para ${terminal.name}.`);
          }catch(error){message(error.message,true);try{renderTerminals(await api('/manage/terminals'));}catch{}}
        });
        actions.append(button);
      }
      card.append(note,actions);
    }
    if(terminal.id!=='local'&&!terminal.revoked){
      const revoke=document.createElement('button');revoke.type='button';revoke.textContent='Revogar credencial';
      revoke.addEventListener('click',async()=>{revoke.disabled=true;try{await api(`/manage/terminals/${terminal.id}/revoke`,{method:'POST'});renderTerminals(await api('/manage/terminals'));message('Credencial revogada. Cópia offline permanece no aparelho.');}catch(error){message(error.message,true);revoke.disabled=false;}});
      card.append(revoke);
    }
    container.append(card);
  }
}
byId('terminal-form').addEventListener('submit',async event=>{
  event.preventDefault();
  const button=event.submitter;button.disabled=true;
  try{
    const created=await api('/manage/terminals',{method:'POST',body:JSON.stringify({name:byId('terminal-name').value.trim()})});
    if(credentialUrl)URL.revokeObjectURL(credentialUrl);
    credentialUrl=URL.createObjectURL(new Blob([created.token+'\n'],{type:'application/octet-stream'}));
    byId('download-token').href=credentialUrl;byId('download-token').download=`elo-terminal-${created.id}.token`;
    byId('credential-ready').hidden=false;byId('terminal-name').value='';
    renderTerminals(await api('/manage/terminals'));message('Totem cadastrado. Baixe credencial individual.');
  }catch(error){message(error.message,true);}finally{button.disabled=false;}
});
