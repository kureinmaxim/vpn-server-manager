import assert from 'node:assert/strict';
const tabs=await (await fetch('http://127.0.0.1:9238/json')).json();
const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(r=>ws.onopen=r);
let id=0; const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){pending.get(m.id)(m);pending.delete(m.id);}};
async function call(method,params={}){const n=++id;const p=new Promise(r=>pending.set(n,r));ws.send(JSON.stringify({id:n,method,params}));const m=await p;if(m.error)throw Error(JSON.stringify(m.error));return m.result;}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function key(key,code,num,modifiers=0){await call('Input.dispatchKeyEvent',{type:'keyDown',key,code,modifiers,windowsVirtualKeyCode:num,text:key==='Enter'?'\r':undefined});await call('Input.dispatchKeyEvent',{type:'keyUp',key,code,modifiers,windowsVirtualKeyCode:num});}


const pause=()=>new Promise(r=>setTimeout(r,800));
async function page(name) { console.log('page',name); await evaluate('isInternalNavigation = true'); await call('Page.navigate',{url:'file:///tmp/vsm-'+name+'.html'}); await new Promise(r=>setTimeout(r,1500)); }
async function walk(modal) {
 for(const modifiers of [0,8]) for(let n=0;n<12;n++) {
  await key('Tab','Tab',9,modifiers); await new Promise(r=>setTimeout(r,40));
  if(await evaluate('document.activeElement===document.body')) await key('Tab','Tab',9,modifiers);
  assert.equal(await evaluate('Boolean(document.activeElement.closest('+JSON.stringify('#'+modal)+'))'),true);
 }
}
await page('modal');
await evaluate("document.getElementById('firstSetupButton').style.display='';document.getElementById('firstSetupButton').disabled=false;document.getElementById('firstSetupButton').focus();showFirstTimeSetup()");
await pause();
await evaluate("document.querySelector('[onclick=\"setupNewPin()\"]').focus()");
await key('Enter','Enter',13); await new Promise(r=>setTimeout(r,1500));
assert.equal(await evaluate('document.activeElement.id'),'newPinInput');
assert.equal(await evaluate("document.querySelectorAll('.modal.show').length"),1);
assert.equal(await evaluate("document.querySelectorAll('.modal-backdrop').length"),1);
await walk('createPinModal');
await key('Escape','Escape',27); await pause();
assert.equal(await evaluate('document.activeElement.id'),'firstSetupButton');
await page('settings');
await evaluate("document.querySelector('[data-export=package]').focus()");
await key('Enter','Enter',13); await pause();
await walk('exportInfoModal');
await evaluate("window.exportsCount=0;document.getElementById('secretExportForm').addEventListener('submit',e=>{e.preventDefault();window.exportsCount++});document.querySelector('#secretExportForm button').focus()");
await key('Enter','Enter',13);
assert.equal(await evaluate('window.exportsCount'),0);
assert.equal(await evaluate('document.activeElement.id'),'confirmSecretExport');
await key(' ','Space',32);
assert.equal(await evaluate("document.getElementById('confirmSecretExport').checked"),true);
await evaluate("document.querySelector('#secretExportForm button').focus()");
await key('Enter','Enter',13);
assert.equal(await evaluate('window.exportsCount'),1);
await key('Escape','Escape',27); await pause();
assert.equal(await evaluate("document.activeElement.dataset.export"),'package');
await evaluate("window.pinRequests=0;window.fetch=async()=>{window.pinRequests++;return {json:async()=>({success:true})}};['oldPin','newPin','newPin2'].forEach(id=>document.getElementById(id).value='synthetic');document.getElementById('newPin2').focus()");
await key('Enter','Enter',13); await pause();
assert.equal(await evaluate('window.pinRequests'),1);
assert.equal(await evaluate("document.getElementById('changePinSettingsMessage').hidden"),false);
await page('add');
console.log('validate name');
await evaluate("document.querySelector('form').reportValidity()");
assert.equal(await evaluate('document.activeElement.id'),'name');
console.log('validate file');
// The shared picker is also used for required receipt files. Check native invalid focus.
await evaluate("const f=document.querySelector('.js-file-picker-input');f.required=true;f.reportValidity()");
assert.equal(await evaluate("document.activeElement.matches('.js-file-picker-input')"),true);
assert.equal(await evaluate("getComputedStyle(document.activeElement).display !== 'none'"),true);
console.log('PASS: setup transition, Tab/Shift+Tab in create/export, Space consent, Enter forms, Escape return, invalid field/file focus');
ws.close();
