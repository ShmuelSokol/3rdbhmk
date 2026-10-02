import {mountWalkthrough} from '../browser/main.mjs';

export async function enter({element,fetcher=fetch,Socket=WebSocket,where=location}) {
  if(where.protocol!=='https:'||where.hostname!=='127.0.0.1')throw Error('Local TLS origin required');
  const abort=new AbortController();
  const timeout=setTimeout(()=>abort.abort(),35000);
  let socket=null,mounted=null,closed=false;
  const close=()=>{closed=true;abort.abort();mounted?.disconnect();socket?.close();};
  window.addEventListener('pagehide',close,{once:true});
  try {
    const response=await fetcher('/session',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json'},body:'{}',signal:abort.signal});
    if(!response.ok)throw Error();
    const session=await response.json();
    if(!session||Object.keys(session).sort().join(',')!=='route,streamId'||
       !/^\/s\/[a-f0-9]{32}$/.test(session.route)||
       !/^[A-Za-z0-9_-]{1,128}$/.test(session.streamId)||closed)throw Error();
    const base='wss://'+where.host+session.route;
    socket=new Socket(base+'/control');
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(Error()),5000);
      socket.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
      socket.addEventListener('error',()=>{clearTimeout(timer);reject(Error());},{once:true});
      socket.addEventListener('close',()=>{clearTimeout(timer);reject(Error());},{once:true});
    });
    if(closed)throw Error();
    mounted=mountWalkthrough({element,playerUrl:base+'/player',streamId:session.streamId,controlSocket:socket});
    return {disconnect:close};
  } catch {
    close();throw Error('Owned session unavailable');
  } finally {clearTimeout(timeout);}
}

const button=document.querySelector('[data-enter]');
if(button)button.addEventListener('click',async()=>{
  button.disabled=true;
  try{await enter({element:document.querySelector('main')});button.hidden=true;}
  catch{document.querySelector('[data-status]').textContent='Session unavailable. Close this page before requesting another session.';}
});
