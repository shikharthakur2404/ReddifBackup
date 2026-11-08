// Minimal dependency-free CDP bridge for the Rediffmail tab in Brave.
import fs from 'node:fs';
export async function connect() {
  const tabs = await (await fetch('http://127.0.0.1:9223/json/list')).json();
  const matches = tabs.filter(t => t.type === 'page' && /^https:\/\/([\w-]+\.)?rediffmailpro\.com\//.test(t.url));
  const tab = matches.find(t => t.url.startsWith('https://webmail.rediffmailpro.com/ajaxprism/')) || matches[0];
  if (!tab) throw new Error('No Rediffmail tab in Brave');
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  let id=0;
  const pending=new Map();
  ws.onmessage=event=>{
    const msg=JSON.parse(event.data), p=pending.get(msg.id);
    if(p){pending.delete(msg.id);clearTimeout(p.timer);msg.error?p.reject(new Error(msg.error.message)):p.resolve(msg.result);}
  };
  function send(method,params={}) {
    return new Promise((resolve,reject)=>{
      const n=++id;
      const timer=setTimeout(()=>{pending.delete(n);reject(new Error('CDP timeout: '+method));},60000);
      pending.set(n,{resolve,reject,timer});ws.send(JSON.stringify({id:n,method,params}));
    });
  }
  async function evaluate(expression){
    const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
    if(r.exceptionDetails)throw new Error(r.exceptionDetails.text);
    return r.result.value;
  }
  return {send,evaluate,close:()=>ws.close()};
}
if(process.argv[1] && import.meta.url===new URL('file://'+process.argv[1]).href){
  const c=await connect();
  try {console.log(JSON.stringify(await c.evaluate(fs.readFileSync(0,'utf8')),null,2));}
  finally{c.close();}
}
