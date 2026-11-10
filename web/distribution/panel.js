'use strict';
const byId = id => document.getElementById(id);
let token = sessionStorage.getItem('eloAdminToken') || '';
let state = null;
let selected = [];
function message(text, error=false) { byId('message').textContent = text; byId('message').classList.toggle('error', error); }
async function api(path, options={}) {
  const response = await fetch(path, {...options, headers: {...options.headers, Authorization: `Bearer ${token}`, 'Content-Type':'application/json'}});
  if (response.status === 401) { logout(); throw new Error('Chave administrativa inválida.'); }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Operação não concluída.');
  return data;
}
function logout() { token=''; state=null; sessionStorage.removeItem('eloAdminToken'); byId('login').hidden=false; byId('dashboard').hidden=true; byId('logout').hidden=true; }
function preview() {
  const container = byId('preview'); container.replaceChildren();
  for (const [index,id] of selected.entries()) {
    const variant=state.variants.find(v=>v.id===id); if(!variant)continue;
    const article=document.createElement('article'); const title=document.createElement('h2'); const body=document.createElement('p');
    title.textContent=`${index+1}. ${variant.title}`; body.textContent=variant.text; article.append(title,body);if(variant.image){const note=document.createElement('p');note.className='hint';note.textContent=`Imagem incluída no cliente: ${variant.image.alt}`;article.append(note);}container.append(article);
  }
  if(!selected.length)container.textContent='Selecione conteúdo para conferir prévia.';
}
function renderDelivery(delivery) {
  byId('delivery-label').textContent=delivery.label;
  byId('delivery-seen').textContent=delivery.last_seen ? `Última comunicação: ${new Date(delivery.last_seen*1000).toLocaleString('pt-BR')}` : 'Aguardando primeira comunicação do cliente atualizado.';
}
function render() {
  renderDelivery(state.delivery);
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
    if(variant.image){const tag=document.createElement('span');tag.className='tag';tag.textContent='Texto + imagem';detail.append(tag);}
    if(!variant.supported){const tag=document.createElement('span');tag.className='tag';tag.textContent='Requer capacidade ainda não disponível no cliente';detail.append(tag);}
    label.append(check,detail);container.append(label);
  }
  preview();
}
async function refresh(){try{state=await api('/manage/status');selected=[...state.selected];render();message('Publicação carregada.');}catch(error){message(error.message,true);}}
byId('login-form').addEventListener('submit',async event=>{event.preventDefault();token=byId('key').value.trim();byId('key').value='';try{state=await api('/manage/status');sessionStorage.setItem('eloAdminToken',token);selected=[...state.selected];render();message('Acesso administrativo autorizado.');}catch(error){message(error.message,true);}});
byId('logout').addEventListener('click',async()=>{try{await api('/manage/logout',{method:'POST'});}catch{}logout();message('Sessão encerrada neste navegador.');});
byId('refresh').addEventListener('click',refresh);
byId('selection-form').addEventListener('submit',async event=>{event.preventDefault();if(!selected.length){message('Selecione ao menos uma página compatível.',true);return;}byId('publish').disabled=true;try{await api('/manage/selection',{method:'POST',body:JSON.stringify({variants:selected,expected_hash:state.manifest.content_hash})});await refresh();message('Seleção publicada. Cliente consultará atualização em até 30 segundos; aplique ao Recomeçar.');}catch(error){message(error.message,true);}finally{byId('publish').disabled=false;}});
if(token)refresh();

let deliveryBusy=false;
setInterval(async()=>{
  if(!token || !state || document.hidden || deliveryBusy)return;
  deliveryBusy=true;
  try{renderDelivery(await api('/manage/delivery'));}
  catch{byId('delivery-seen').textContent='Não foi possível atualizar situação do terminal.';}
  finally{deliveryBusy=false;}
},5000);
