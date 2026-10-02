// Offline load test uses actual FROZEN browser controls. Native frame service is
// a deterministic scheduling model, not an executed UE/socket integration test.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Controls,ControlPort} from '../../browser/controls.mjs';
const header=fs.readFileSync(new URL('./Receiver.h',import.meta.url),'utf8');
const limit=Number(header.match(/MaximumAcceptedPerSecond=(\d+)/)[1]);
function offered(cap,fps=60){
  let now=0,pending=null,closed=false,handler,window=0,count=0,maximum=0,applied=0,sum=0,offeredSum=0;
  const ws={readyState:1,bufferedAmount:0,addEventListener(k,f){if(k==='message')handler=f;},
    send(s){assert.equal(pending,null);pending=JSON.parse(s);},close(){closed=true;}};
  const port=new ControlPort(ws,{clock:()=>now});const controls=new Controls(port);controls.setReady();
  let nextMouse=0,nextHeartbeat=0,nextFrame=0;
  function serve(){
    if(now-window>=1000){maximum=Math.max(maximum,count);window=now;count=0;}
    if(pending){
      if(++count>cap){port.close();pending=null;return;}
      const m=pending;pending=null;++applied;
      if(m.event?.action==='look')sum+=m.event.x;
      handler({data:JSON.stringify({type:'ack',sequence:m.sequence})});
    }
  }
  controls.stick(1,0);
  for(now=0;now<=5000&&!closed;now++){
    if(now>=nextMouse){controls.look(8,0);offeredSum+=.08;nextMouse+=1000/60;}
    if(now>=nextHeartbeat){controls.heartbeat();nextHeartbeat+=200;}
    if(now>=nextFrame){serve();nextFrame+=1000/fps;}
    port.tick();assert.ok(port.queue.length<=8);
  }
  for(let n=0;n<40&&pending&&!closed;n++){now+=1000/fps;serve();port.tick();}
  maximum=Math.max(maximum,count);
  return {closed,maximum,applied,sum,offeredSum};
}
test('source02 60Hz look plus movement heartbeat has no periodic cap stall',()=>{
  assert.ok(limit>=240+8);
  const r=offered(limit);assert.equal(r.closed,false);assert.ok(r.applied>200);
  assert.ok(r.maximum<=61);assert.ok(Math.abs(r.sum-r.offeredSum)<1e-9);
});
test('the former 16-per-second cap demonstrably fails the same offered load',()=>{
  assert.equal(offered(16).closed,true);
});
test('30fps native scheduling remains usable through source02 coalescing',()=>{
  const r=offered(limit,30);assert.equal(r.closed,false);assert.ok(r.maximum<=31);
  assert.ok(Math.abs(r.sum-r.offeredSum)<1e-9);
});
