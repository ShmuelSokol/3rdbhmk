// Actual bundled entry/main/pinned Epic frontend -> actual Python HTTP/Gateway/Core.
// Only DOM, WebSocket bytes and native/OS effects are adapters. No media proof.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {pathToFileURL} from 'node:url';
const [bundle,driver,python='python']=process.argv.slice(2);
const print=console.log;for(const k of ['log','info','warn','error','debug'])console[k]=()=>{};
const child=spawn(python,['-I','-B',driver],{stdio:['pipe','pipe','pipe'],windowsHide:true});
let failure=false;child.stderr.on('data',()=>{failure=true;});
const requests=[];let tail=Promise.resolve(),cookie='';const sockets=new Map();
createInterface({input:child.stdout}).on('line',s=>{const pending=requests.shift();if(pending)pending(JSON.parse(s));});
const deadline=setTimeout(()=>child.kill(),15000);
function rpc(m){const result=tail.then(()=>new Promise(resolve=>{requests.push(resolve);child.stdin.write(JSON.stringify(m)+'\n');}));tail=result.then(()=>{});return result;}
function emit(ws,name,data={}){const e=new Event(name);Object.assign(e,data);ws.dispatchEvent(e);ws['on'+name]?.(e);}
function deliver(r){assert(r.ok);for(const [p,state] of Object.entries(r.peers)){const ws=sockets.get(p);if(!ws)continue;for(const m of state.messages)emit(ws,'message',{data:JSON.stringify(m)});if(state.closed&&ws.readyState!==3){ws.readyState=3;emit(ws,'close',{code:1000,reason:''});}}}
class WS extends EventTarget {
  static CLOSED=3;
  constructor(url){super();this.path=new URL(url).pathname;this.readyState=0;this.bufferedAmount=0;sockets.set(this.path,this);
    rpc({op:'upgrade',path:this.path,cookie}).then(r=>{assert(r.ok);this.readyState=1;emit(this,'open');deliver(r);});}
  send(text){rpc({op:'message',path:this.path,text}).then(deliver);}
  close(){if(this.readyState===3)return;this.readyState=3;rpc({op:'close',path:this.path}).then(deliver);emit(this,'close',{code:1000,reason:''});}
}
class Element extends EventTarget {
  constructor(){super();this.style={};this.children=[];this.dataset={};this.clientWidth=800;this.clientHeight=600;this.offsetWidth=800;this.offsetHeight=600;this.classList={contains:()=>false};this.parts=new Map();}
  appendChild(e){this.children.push(e);e.parentElement=this;return e;}
  remove(){} setAttribute(){} getBoundingClientRect(){return {left:0,top:0,width:800,height:600};}
  querySelector(s){if(!this.parts.has(s))this.parts.set(s,new Element());return this.parts.get(s);}
  querySelectorAll(){return [];}
  hasPointerCapture(){return false;} setPointerCapture(){} releasePointerCapture(){}
}
globalThis.location=new URL('https://127.0.0.1:19443/');
globalThis.window=new EventTarget();window.location=location;window.innerWidth=800;window.innerHeight=600;
globalThis.document=new EventTarget();document.createElement=()=>new Element();document.querySelector=()=>null;document.hasFocus=()=>true;document.hidden=false;document.documentElement=new Element();
globalThis.WebSocket=WS;globalThis.Image=Element;
globalThis.RTCRtpReceiver={getCapabilities:()=>({codecs:[{mimeType:'video/H264'}]})};
let lastRtc;
globalThis.RTCPeerConnection=class {constructor(){lastRtc=this;}close(){}};
Object.defineProperty(globalThis,'navigator',{value:{userAgent:'offline byte fixture',platform:'Win32',maxTouchPoints:0}});
const fetcher=async()=>{const r=await rpc({op:'post'});assert(r.ok);cookie=r.cookie;return {ok:true,json:async()=>r.body};};
async function settled(){for(let i=0;i<8;i++){await tail;await new Promise(r=>setImmediate(r));}}
try {
  const {enter}=await import(pathToFileURL(bundle));
  const mounted=await enter({element:new Element(),fetcher,Socket:WS,where:location});
  await settled();
  const order=[...sockets.keys()];assert(order[0].endsWith('/control'));assert(order[1].endsWith('/player'));
  const key=(code,down=true,repeat=false)=>{const e=new Event(down?'keydown':'keyup',{cancelable:true});Object.assign(e,{code,repeat});window.dispatchEvent(e);};
  key('KeyW');await settled(); // actual controls must ignore Connecting input
  let snap=await rpc({op:'snapshot'});assert.equal(snap.subscribed,false);assert.equal(snap.inputs,0);
  deliver(await rpc({op:'native'}));await settled();
  snap=await rpc({op:'snapshot'});assert.equal(snap.subscribed,true); // real upstream handles pushed owned list
  // Synthetic browser ICE event ONLY, not video/runtime evidence. Real frontend
  // event -> real main controls -> real gateway/FlightAuthority release/rebind.
  lastRtc.iceConnectionState='connected';lastRtc.oniceconnectionstatechange(new Event('iceconnectionstatechange'));
  key('KeyW');await settled();key('KeyF');await settled();
  snap=await rpc({op:'snapshot'});assert.deepEqual(snap.operations.slice(-3),['input','release','bind']);
  const count=snap.inputs;key('KeyW',true,true);await settled();
  snap=await rpc({op:'snapshot'});assert.equal(snap.inputs,count);
  key('KeyW',false);await settled();key('KeyW');await settled();
  snap=await rpc({op:'snapshot'});assert.equal(snap.inputs,count+2);
  mounted.disconnect();await settled();snap=await rpc({op:'snapshot'});assert.equal(snap.routes,0);assert.equal(snap.processes,0);
  // Real entry and real mount fail on an invalid DOM target AFTER control opens.
  const before=sockets.size;
  await assert.rejects(enter({element:null,fetcher,Socket:WS,where:location}),/Owned session unavailable/);
  await settled();snap=await rpc({op:'snapshot'});assert.equal(snap.routes,0);assert.equal(snap.processes,0);
  assert.equal(sockets.size,before+1);assert([...sockets.values()].every(s=>s.readyState===3));
  assert(!failure);
} catch(e){print(e.stack);process.exitCode=1;}
finally {
  await rpc({op:'shutdown'});child.stdin.end();
  await new Promise(resolve=>{if(child.exitCode!==null)resolve();else child.once('exit',resolve);});clearTimeout(deadline);
  if(child.exitCode!==0)process.exitCode=1;
  if(!process.exitCode)print(JSON.stringify({cases:7,actualEntry:true,actualPinnedFrontend:true,actualPythonGateway:true,domAndNativeAdapters:true,mediaExecuted:false,testChildExit:0}));
}
