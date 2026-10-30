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
await call('Network.enable');
await call('Network.setCookie',{name:process.env.KEYBOARD_COOKIE_NAME,value:process.env.KEYBOARD_COOKIE,url:process.env.KEYBOARD_URL});
await call('Page.enable');
await call('Page.setInterceptFileChooserDialog',{enabled:true});
let chooser;
const handler=ws.onmessage;
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Page.fileChooserOpened') chooser=m.params;handler(e);};
await evaluate("if (typeof isInternalNavigation !== 'undefined') isInternalNavigation = true");
await call('Page.navigate',{url:process.env.KEYBOARD_URL+'/edit_server/1'});
await new Promise(r=>setTimeout(r,1500));
await evaluate("document.querySelector('[data-bs-target=\"#receiptsModal\"]').focus()");
await key('Enter','Enter',13); await pause();
await evaluate("document.getElementById('new_receipt_description').focus()");
await call('Input.insertText',{text:'Keyboard receipt'});
await key('Tab','Tab',9);
assert.equal(await evaluate('document.activeElement.id'),'receipt_file');
await key(' ','Space',32); await pause();
assert(chooser,'Space must open the native file chooser');
await call('DOM.setFileInputFiles',{files:[process.env.KEYBOARD_FILE],backendNodeId:chooser.backendNodeId});
await key('Tab','Tab',9);
assert.equal(await evaluate("document.activeElement.type"),'submit');
await key('Enter','Enter',13); await pause();
assert.equal(await evaluate("document.querySelectorAll('#receipts-list a').length"),1);
assert.equal(await evaluate("document.activeElement.closest('#receipts-list') !== null"),true);
assert.equal(await evaluate("document.querySelector('#receipts-list strong').textContent"),'Keyboard receipt');
for(const modifiers of [0,8]) for(let n=0;n<12;n++){
 await key('Tab','Tab',9,modifiers);await new Promise(r=>setTimeout(r,40));
 if(await evaluate('document.activeElement===document.body')) await key('Tab','Tab',9,modifiers);
 assert.equal(await evaluate("Boolean(document.activeElement.closest('#receiptsModal'))"),true);
}
await key('Escape','Escape',27); await pause();
assert.equal(await evaluate("document.activeElement.dataset.bsTarget"),'#receiptsModal');
console.log('PASS: keyboard file chooser, real multipart upload, rendered receipt, Tab/Shift+Tab, Escape return');
async function sshPage(screen) {
 await evaluate('isInternalNavigation=true');
 await call('Page.navigate',{url:process.env.KEYBOARD_URL+'/__keyboard_ssh/'+screen});
 await new Promise(r=>setTimeout(r,1500));
}
async function walkDialog(id) {
 for(const modifiers of [0,8]) for(let n=0;n<10;n++) {
  await key('Tab','Tab',9,modifiers); await new Promise(r=>setTimeout(r,40));
  if(await evaluate('document.activeElement===document.body')) await key('Tab','Tab',9,modifiers);
  assert.equal(await evaluate('Boolean(document.activeElement.closest('+JSON.stringify('#'+id)+'))'),true);
 }
}
await sshPage('stats');
await evaluate("document.querySelector('.btn-show-stats').focus()");
await key('Enter','Enter',13); await pause();
await walkDialog('serverStatusModal');
await key('Escape','Escape',27); await pause();
assert.equal(await evaluate("document.activeElement.classList.contains('btn-show-stats')"),true);
await sshPage('monitoring');
await evaluate("window.removals=0;window.startUninstallation=()=>window.removals++;document.getElementById('stats-container').style.display='block';document.getElementById('uninstall-btn-main').focus()");
await key('Enter','Enter',13); await pause();
assert.equal(await evaluate('document.activeElement.id'),'cancel-uninstall-btn');
await walkDialog('uninstallModal');
await key('Escape','Escape',27); await pause();
assert.equal(await evaluate('window.removals'),0);
assert.equal(await evaluate("document.activeElement.id"),'uninstall-btn-main');
console.log('PASS: synthetic SSH error dialog, destructive confirmation defaults to Cancel, Tab/Shift+Tab and Escape; no SSH actions');
ws.close();
