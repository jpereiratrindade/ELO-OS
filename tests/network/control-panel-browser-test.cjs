// SPDX-License-Identifier: GPL-3.0-only
// Isolated browser fixture: no power request reaches an operational terminal.
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE || 'playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    const base={recent:true,revoked:false,label:'Apresentação confirmada',last_seen:1794510000,display:{publication:'Bioma Pampa',page:1,pages:3,title:'Campos Sulinos',mode:'automatic',exposure_seconds:5}};
    const pc={...base,id:'local',name:'PC de testes',control:{supported:false,available:false,busy:false,command:null}};
    const pi={...base,id:'1234567890abcdef',name:'Raspberry Pi 5 · CPPSUL',control:{supported:true,available:true,busy:false,command:null}};
    const state={terminals:[pc,pi],manifest:{title:'Bioma Pampa',version:'0.1.1',bundle_id:'elo-pampa'},variants:[],selected:[],studio_available:true,exposure_seconds:5};
    const requests=[];
    await page.route('https://elo-control.test/**',async route=>{
      const request=route.request(),url=new URL(request.url());
      if(url.pathname==='/manage/status')return route.fulfill({json:state});
      if(url.pathname==='/manage/terminals')return route.fulfill({json:state.terminals});
      if(url.pathname.endsWith('/power')){
        const data=request.postDataJSON();requests.push(data);
        pi.control.command={id:data.request_id,action:data.action,state:'pending'};pi.control.busy=true;
        return route.fulfill({status:202,json:pi.control.command});
      }
      const name=url.pathname==='/'?'index.html':url.pathname.slice(1);
      const file=path.join(__dirname,'../../web/distribution',name);
      if(fs.existsSync(file))return route.fulfill({body:fs.readFileSync(file),contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':name.endsWith('.svg')?'image/svg+xml':'text/html'});
      return route.fulfill({status:404,body:''});
    });
    await page.goto('https://elo-control.test/');
    await page.locator('#key').fill('a'.repeat(43));await page.locator('#login-form button').click();
    const card=page.locator('[data-terminal-id="1234567890abcdef"]');
    const reboot=card.getByRole('button',{name:'Reiniciar Raspberry Pi 5 · CPPSUL',exact:true});
    const shutdown=card.getByRole('button',{name:'Desligar Raspberry Pi 5 · CPPSUL',exact:true});
    await reboot.waitFor();
    assert.equal(await page.locator('[data-terminal-id="local"] .terminal-actions').count(),0);
    page.once('dialog',dialog=>dialog.dismiss());await reboot.click();assert.equal(requests.length,0);
    page.once('dialog',dialog=>{assert.match(dialog.message(),/Raspberry Pi 5/);return dialog.accept();});
    await reboot.click();await page.waitForFunction(()=>document.querySelector('.terminal-control-status')?.textContent.includes('Aguardando recebimento'));
    assert.equal(requests.length,1);assert.equal(requests[0].action,'reboot');assert.match(requests[0].request_id,/^[0-9a-f-]{36}$/);
    assert.equal(await reboot.isDisabled(),true);assert.equal(await shutdown.isDisabled(),true);
    pi.control.busy=false;pi.control.command.state='reboot_observed';
    await page.evaluate(terminals=>renderTerminals(terminals),state.terminals);
    page.once('dialog',dialog=>{assert.match(dialog.message(),/ligar o aparelho fisicamente/);return dialog.accept();});
    await shutdown.click();await page.waitForFunction(()=>document.querySelector('.terminal-control-status')?.textContent.startsWith('Desligar'));
    assert.equal(requests.length,2);assert.equal(requests[1].action,'poweroff');
    pi.control.available=false;pi.control.busy=false;pi.control.command.state='unconfirmed';
    await page.evaluate(terminals=>renderTerminals(terminals),state.terminals);
    assert.equal(await reboot.isDisabled(),true);assert.equal(await shutdown.isDisabled(),true);
    assert.match(await card.locator('.terminal-control-status').textContent(),/execução não confirmada/);
    pi.revoked=true;await page.evaluate(terminals=>renderTerminals(terminals),state.terminals);
    assert.equal(await card.locator('.terminal-actions').count(),0);
    assert.deepEqual(errors,[]);
    console.log('PASS browser: capability gating, confirmation cancel/accept, reboot/shutdown, pending/offline/revoked states');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
