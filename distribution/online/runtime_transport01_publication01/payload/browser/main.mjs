import {Config,PixelStreaming} from '@epicgames-ps/lib-pixelstreamingfrontend-ue5.8';
import {Controls,ControlPort} from './controls.mjs';

// Host supplies an ALREADY authenticated control WebSocket and same-origin player
// URL whose upgrade is bound to the same allocation. No credentials in URL/storage.
// transport01 entry performs private-cookie HTTP admission before mounting.
export function mountWalkthrough({element,playerUrl,streamId,controlSocket}) {
  const url=new URL(playerUrl,location.href);
  if (!['ws:','wss:'].includes(url.protocol) || url.host!==location.host || url.search || url.hash ||
      url.username || url.password || !/^[A-Za-z0-9_-]{1,128}$/.test(streamId) || controlSocket.readyState!==1) {
    throw Error('Invalid stream attachment');
  }
  if (location.protocol==='https:'&&url.protocol!=='wss:') throw Error('Invalid stream attachment');
  element.innerHTML='<div class="video"></div><div class="pads"><div class="pad move" aria-label="Walk joystick">Walk</div><div class="pad look" aria-label="Look pad">Look</div></div><div class="buttons"><button data-action="interact">Talk / next (E)</button><button data-action="pause">Menu (P)</button><button data-action="mute">Mute (M)</button><button data-action="dove">Fly / return (F)</button><button data-play>Play video</button><button data-leave>Leave</button></div><p role="status">Connecting to native stream…</p>';
  const video=element.querySelector('.video');
  const status=element.querySelector('[role=status]');
  const config=new Config({useUrlParams:false,initialSettings:{
    ss:url.href,StreamerId:streamId,AutoConnect:false,AutoPlayVideo:true,WaitForStreamer:true,
    MaxReconnectAttempts:0,KeyboardInput:false,MouseInput:false,TouchInput:false,
    GamepadInput:false,XRControllerInput:false,FakeMouseWithTouches:false,UseMic:false,UseCamera:false
  }});
  const stream=new PixelStreaming(config,{videoElementParent:video});
  let stopped=false, timer, controls=null, port=null;
  const abort=new AbortController();
  const on=(target,event,fn)=>target.addEventListener(event,fn,{signal:abort.signal});
  const stop=()=>{
    if (stopped) return;
    stopped=true; clearInterval(timer); abort.abort();
    try { if(controls)controls.disconnect(); else port?.close(); } finally { stream.disconnect(); }
    status.textContent='Disconnected. Request a new authenticated attachment to reconnect.';
  };
  const resetPointers=[];
  try {
  port=new ControlPort(controlSocket,{onClose:stop,
    onFlightStart:()=>{controls.beginHandoff();for(const reset of resetPointers)reset();},
    onFlightEnd:()=>{for(const reset of resetPointers)reset();controls.endHandoff();}
  });
  controls=new Controls(port);
  for(const button of element.querySelectorAll('[data-action],[data-play]'))button.disabled=true;
  for (const name of ['webRtcDisconnected','webRtcFailed']) stream.addEventListener(name,stop);
  stream.addEventListener('webRtcConnected',()=>{
    if(stopped)return;
    controls.setReady();
    controls.setVisible(!document.hidden && document.hasFocus());
    for(const button of element.querySelectorAll('[data-action],[data-play]'))button.disabled=false;
    status.textContent='Native stream connected';
  });
  on(window,'keydown',e=>{if(controls.key(e.code,true,e.repeat))e.preventDefault();});
  on(window,'keyup',e=>{if(controls.key(e.code,false))e.preventDefault();});
  on(window,'blur',()=>controls.setVisible(false));
  on(window,'focus',()=>controls.setVisible(!document.hidden));
  on(document,'visibilitychange',()=>controls.setVisible(!document.hidden && document.hasFocus()));
  on(window,'pagehide',stop);
  let drag=null;
  resetPointers.push(()=>{drag=null;});
  on(video,'pointerdown',e=>{if(!controls.handoff&&!controls.suspended)drag=e.pointerId;});
  on(video,'pointerup',()=>{drag=null;});on(video,'pointercancel',()=>{drag=null;});
  on(video,'pointermove',e=>{if(e.pointerId===drag&&e.buttons===1)controls.look(e.movementX,e.movementY);});
  for (const button of element.querySelectorAll('[data-action]')) on(button,'click',()=>controls.emit(button.dataset.action));
  on(element.querySelector('[data-play]'),'click',()=>stream.play());
  on(element.querySelector('[data-leave]'),'click',stop);
  for (const pad of element.querySelectorAll('.pad')) {
    let pointer=null,startX=0,startY=0,lastX=0,lastY=0;
    resetPointers.push(()=>{const old=pointer;pointer=null;if(old!==null&&pad.hasPointerCapture(old))pad.releasePointerCapture(old);});
    on(pad,'pointerdown',e=>{
      if(!controls.active||controls.suspended||controls.handoff)return;
      if(pointer!==null)return;
      pointer=e.pointerId; startX=lastX=e.clientX; startY=lastY=e.clientY; pad.setPointerCapture(pointer);
    });
    on(pad,'pointermove',e=>{
      if(e.pointerId!==pointer)return;
      if(pad.classList.contains('move')) controls.stick((e.clientX-startX)/50,(e.clientY-startY)/50);
      else controls.look(e.clientX-lastX,e.clientY-lastY);
      lastX=e.clientX;lastY=e.clientY;
    });
    const release=e=>{if(e.pointerId===pointer){pointer=null;controls.release();}};
    for(const event of ['pointerup','pointercancel','lostpointercapture'])on(pad,event,release);
  }
  timer=setInterval(()=>{port.tick();controls.heartbeat();},200);
  stream.connect();
  return {disconnect:stop};
  } catch { stop(); throw Error('Stream mount unavailable'); }
}
