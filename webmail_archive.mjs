// Archive originals through an authenticated Brave Rediffmail tab. No saved cookies/passwords.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {connect} from './browser_cdp.mjs';
const root=path.resolve('backup_vault/Webmail');
fs.mkdirSync(root,{recursive:true});
const manifestPath=path.join(root,'manifest.json');
const manifest=fs.existsSync(manifestPath)?JSON.parse(fs.readFileSync(manifestPath)): {messages:{},folders:{}};
const save=()=>{fs.writeFileSync(manifestPath+'.tmp',JSON.stringify(manifest,null,2));fs.renameSync(manifestPath+'.tmp',manifestPath);};
manifest.originals_complete=false;save();
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const safe=s=>String(s).replace(/[^a-zA-Z0-9._-]/g,'_').slice(0,110);
const c=await connect();
try {
  await c.evaluate(`window.__archiveApi=async(path,params)=>{
    const body=new URLSearchParams({output:'json',angular:'1',jsversion:'4.01',uitype:'vayu',els:new URL(location.href).searchParams.get('els'),...params});
    const r=await fetch('/ajaxprism/'+path,{method:'POST',body,signal:AbortSignal.timeout(45000)});
    if(!r.ok)throw Error('HTTP '+r.status);
    const j=await r.json();if(j.rmail?.reason==='INVALID_SESSION')throw Error('INVALID_SESSION: sign in to Rediffmail in Brave');
    if(j.rmail?.status!=='Success')throw Error('Mail API rejected request');
    window.__archiveSession={els:j.rmail.els,ols:j.rmail.ols};
    return j.rmail;
  };true`);
  const api=(endpoint,params)=>c.evaluate(`__archiveApi(${JSON.stringify(endpoint)},${JSON.stringify(params)}).then(r=>{const {els,ols,sessionid,rm,show_button,...clean}=r;return clean})`);
  const folders=await api('folder',{});
  for(const f of folders.folder){
    const folder=f.foldername, messages=[], seen=new Set(), cursors=new Set();
    let next='',start=0,ended=false;
    for(let page=0;page<1000;page++){
      const r=await api('maillist',{folder,startcount:start,msgcount:100,mail_conversation_view:0,...(next?{nextfn:next}:{})});
      for(const m of r.mail||[])if(!seen.has(m.uidl)){seen.add(m.uidl);messages.push(m);}
      console.log(`LIST ${folder}: ${messages.length} messages`);
      if(String(r.hasMoreMails)==='false' || (!r.nextfn && !(r.mail||[]).length)){ended=true;break;}
      if(!r.nextfn || cursors.has(r.nextfn))throw Error('Pagination did not reach a verified end: '+folder);
      cursors.add(r.nextfn);next=r.nextfn;start=Number(r.nextCount)||start+(r.mail||[]).length;
    }
    if(!ended)throw Error('Pagination limit: '+folder);
    manifest.folders[folder]={enumeration_complete:true,total:messages.length,messages};save();
    console.log(`ENUMERATED ${folder}: ${messages.length}`);
    if(process.argv.includes('--list-only'))continue;
    for(let index=0;index<messages.length;index++){
      const m=messages[index],key=folder+'/'+m.uidl;
      const date=new Date(Number(m.timestamp)*1000).toISOString();
      const rel=path.join(safe(folder),date.slice(0,7),safe(m.uidl),'message.eml');
      const file=path.join(root,rel),old=manifest.messages[key];
      if(old?.sha256 && fs.existsSync(file) && hash(fs.readFileSync(file))===old.sha256){continue;}
      let success=false;
      for(let attempt=1;attempt<=3&&!success;attempt++){
        try{
          const info=await c.evaluate(`(async()=>{
            const p=new URLSearchParams({...window.__archiveSession,file_name:${JSON.stringify(m.filename)},folder:${JSON.stringify(folder)},format:'eml',output:'web'});
            const r=await fetch('/ajaxprism/downloadmail?'+p,{signal:AbortSignal.timeout(45000)});
            if(!r.ok)throw Error('Download HTTP '+r.status);
            window.__archiveBytes=new Uint8Array(await r.arrayBuffer());
            const prefix=new TextDecoder().decode(__archiveBytes.slice(0,4096));
            if(/exhausted the number of limit/i.test(prefix))throw Error('DAILY_DOWNLOAD_LIMIT: retry after the server resets its quota');
            if(!/^(Return-Path|Received|From|Date|Delivered-To|MIME-Version|DKIM-Signature|Message-ID|Subject):/im.test(prefix)||/^\\s*</.test(prefix))throw Error('Response is not an email');
            return {bytes:__archiveBytes.length};
          })()`);
          fs.mkdirSync(path.dirname(file),{recursive:true});
          const fd=fs.openSync(file+'.part','w',0o600);
          try{
            for(let offset=0;offset<info.bytes;offset+=524288){
              const b64=await c.evaluate(`(()=>{const b=__archiveBytes.subarray(${offset},${offset+524288});let s='';for(let i=0;i<b.length;i+=8192)s+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(s)})()`);
              fs.writeSync(fd,Buffer.from(b64,'base64'));
            }
          }finally{fs.closeSync(fd);}
          const bytes=fs.readFileSync(file+'.part');
          if(bytes.length!==info.bytes)throw Error('Download length mismatch');
          fs.renameSync(file+'.part',file);fs.utimesSync(file,Number(m.timestamp),Number(m.timestamp));
          manifest.messages[key]={path:rel,bytes:bytes.length,sha256:hash(bytes),date,attachment_expected:m.attachments==='Yes'};
          save();success=true;
          console.log(`SAVED ${folder} ${index+1}/${messages.length} ${date.slice(0,10)} ${bytes.length} bytes`);
        }catch(e){
          if(/DAILY_DOWNLOAD_LIMIT/.test(e.message)){manifest.last_error={type:'daily_download_limit',message:key,at:new Date().toISOString()};save();throw e;}
          console.log(`RETRY ${folder} ${index+1} attempt ${attempt}: ${e.message}`);
        }
      }
      if(!success)throw Error('Download failed after retries: '+key);
    }
  }
  manifest.originals_complete=!process.argv.includes('--list-only');save();
  console.log(manifest.originals_complete?'All enumerated originals saved and hashed.':'Enumeration complete.');
}finally{await c.evaluate('delete window.__archiveBytes;delete window.__archiveSession;true').catch(()=>{});c.close();}
