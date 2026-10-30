import assert from 'node:assert/strict';
const tabs=await (await fetch('http://127.0.0.1:9238/json')).json();
const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(r=>ws.onopen=r);
let id=0; const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){pending.get(m.id)(m);pending.delete(m.id);}};
async function call(method,params={}){const n=++id;const p=new Promise(r=>pending.set(n,r));ws.send(JSON.stringify({id:n,method,params}));const m=await p;if(m.error)throw Error(JSON.stringify(m.error));return m.result;}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function key(key,code,num){await call('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:num,text:key==='Enter'?'\r':undefined});await call('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:num});}

await call('Page.reload');
await new Promise(r=>setTimeout(r,1500));
const pause=()=>new Promise(r=>setTimeout(r,700));
await evaluate("window.loginCount=0; window.changeCount=0; window.submitPinLogin=()=>window.loginCount++; window.submitChangePin=()=>window.changeCount++; document.querySelector('button[onclick=\"showPinLoginModal()\"]').focus(); showPinLoginModal()");
await pause();
assert.equal(await evaluate('document.activeElement.id'),'pinInput');
await key('Enter','Enter',13);
assert.equal(await evaluate('window.loginCount'),1);
await evaluate("document.getElementById('login-tab').focus()");
await key('ArrowRight','ArrowRight',39);
await pause();
assert.equal(await evaluate("document.getElementById('change-pin-tab').getAttribute('aria-selected')"),'true');
assert.equal(await evaluate("document.getElementById('modalSubmitBtn').onclick === window.submitChangePin"),true);
await evaluate("['oldPin','newPin1','newPin2'].forEach(id=>document.getElementById(id).value='synthetic');document.getElementById('newPin2').focus()");
await key('Enter','Enter',13);
assert.equal(await evaluate('window.changeCount'),1);
await key('Escape','Escape',27);
await pause();
assert.equal(await evaluate("document.activeElement.getAttribute('onclick')"),'showPinLoginModal()');
await evaluate('showPinLoginModal()');
await pause();
await evaluate("bootstrap.Tab.getOrCreateInstance(document.getElementById('login-tab')).show()");
await pause();
await evaluate("document.getElementById('pinInput').focus()");
await key('Enter','Enter',13);
assert.equal(await evaluate('window.loginCount'),2);
for(let n=0;n<18;n++){
 await key('Tab','Tab',9); await new Promise(r=>setTimeout(r,40));
 if (await evaluate('document.activeElement === document.body')) await key('Tab','Tab',9); await new Promise(r=>setTimeout(r,40));
 assert.equal(await evaluate("Boolean(document.activeElement.closest('#pinLoginModal'))"),true);
}
console.log('PASS: initial focus, Enter once after reopening, arrow tabs, form Enter, Escape return, Tab containment');
ws.close();