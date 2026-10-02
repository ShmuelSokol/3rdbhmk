import test from 'node:test';
import assert from 'node:assert/strict';
import {Controls,ControlPort} from './controls.mjs';
function socket() {
  const handlers={};
  return {readyState:1,bufferedAmount:0,sent:[],closes:0,
    addEventListener(k,fn){handlers[k]=fn;},send(s){this.sent.push(JSON.parse(s));},
    close(){this.closes++;handlers.close?.({});},ack(n){handlers.message({data:JSON.stringify({type:'ack',sequence:n})});}};
}
test('desktop key chords and mobile deadzone map to same semantic axes',()=>{
  const events=[];const c=new Controls({input:e=>events.push(e)});
  c.setReady();
  c.key('KeyW',true);c.key('KeyD',true);assert.deepEqual(events.at(-1),{action:'move',x:1,y:1});
  c.key('KeyW',false);assert.deepEqual(events.at(-1),{action:'move',x:1,y:0});
  c.stick(-.9,.7);assert.deepEqual(events.at(-1),{action:'move',x:-1,y:-1});
  c.stick(.1,.1);assert.equal(events.at(-1).x,0);
  c.look(200,-50);assert.deepEqual(events.at(-1),{action:'look',x:1,y:-.5});
});
test('discrete repeats ignored and unsupported native actions not guessed',()=>{
  const events=[];const c=new Controls({input:e=>events.push(e)});
  c.setReady();
  c.key('KeyE',true);c.key('KeyE',true,true);c.key('KeyE',false);
  for(const k of ['Escape','KeyF','KeyV','Space','ControlLeft','ShiftLeft'])assert.equal(c.key(k,true),false);
  assert.equal(events.length,1);
});
test('disconnect releases once clears held input and heartbeat stops',()=>{
  const calls=[];const c=new Controls({input:e=>calls.push(e.action),release:()=>calls.push('release'),close:()=>calls.push('close')});
  c.setReady();
  c.key('KeyW',true);c.disconnect();c.disconnect();c.heartbeat();c.key('KeyD',true);
  assert.deepEqual(calls,['move','release','close']);assert.equal(c.keys.size,0);
});
test('release supersedes queued movement; ACK strictly ordered',()=>{
  const ws=socket();const p=new ControlPort(ws);
  p.input({action:'move',x:1});p.input({action:'interact'});p.release();
  assert.equal(ws.sent.length,1);ws.ack(1);
  assert.deepEqual(ws.sent.at(-1),{type:'release',sequence:2});
  ws.ack(1);assert.equal(ws.closes,1);assert.equal(p.closed,true);
});
test('missing ACK timeout and queue overflow close without retry/replay',()=>{
  let now=0;const ws=socket();const p=new ControlPort(ws,{clock:()=>now});
  p.input({action:'move'});now=1500;p.tick();assert.equal(ws.closes,1);
  const s=socket();const q=new ControlPort(s);for(let i=0;i<10;i++)q.input({action:'interact'});
  assert.equal(q.closed,true);assert.equal(s.sent.length,1);
});
test('blur release clears repeat movement and close reentry is bounded',()=>{
  const ws=socket();let calls=0;const port=new ControlPort(ws,{onClose:()=>{calls++;port.close();}});
  const c=new Controls(port);c.setReady();c.key('KeyW',true);c.release();ws.ack(1);ws.ack(2);c.heartbeat();
  assert.equal(ws.sent.length,2);port.close();assert.equal(calls,1);assert.equal(ws.closes,1);
});
test('late matching ACK before delayed tick closes without dispatching queued input',()=>{
  let now=0;const ws=socket();const port=new ControlPort(ws,{clock:()=>now});
  port.input({action:'interact'});port.input({action:'mute'});
  now=1501;ws.ack(1);
  assert.equal(port.closed,true);assert.equal(ws.sent.length,1);assert.equal(ws.closes,1);
});
test('connecting controls discard input and disconnect still closes transport',()=>{
  const events=[];const c=new Controls({input:e=>events.push(e),release:()=>events.push('release'),close:()=>events.push('close')});
  c.key('KeyW',true);c.stick(1,0);c.look(1,1);c.emit('interact');c.heartbeat();c.release();
  assert.deepEqual(events,[]);assert.equal(c.keys.size,0);
  c.disconnect();c.setReady();c.key('KeyW',true);
  assert.deepEqual(events,['close']);
});
test('60Hz look at 100ms RTT stays bounded and conserves integrated deltas',()=>{
  let now=0;const ws=socket();const port=new ControlPort(ws,{clock:()=>now});
  let target=0,nextAck=100;
  for(let frame=0;frame<600;frame++) {
    now=frame*1000/60;
    if(now>=nextAck&&port.pending){ws.ack(port.pending.sequence);nextAck=now+100;}
    port.input({action:'look',x:.08,y:-.03});target+=.08;
    port.tick();assert.equal(port.closed,false);assert.ok(port.queue.length<=1);
  }
  while(port.pending){now+=100;ws.ack(port.pending.sequence);}
  assert.ok(Math.abs(ws.sent.reduce((s,m)=>s+m.event.x,0)-target)<1e-9);
  assert.ok(Math.abs(ws.sent.reduce((s,m)=>s+m.event.y,0)+18)<1e-9);
});
test('full queue permits replacement; release removes accumulated look and move',()=>{
  const ws=socket();const p=new ControlPort(ws);
  p.input({action:'interact'});
  for(let i=0;i<7;i++)p.input({action:'mute'});
  p.input({action:'move',x:1,y:0});p.input({action:'move',x:-1,y:0});
  assert.equal(p.closed,false);assert.equal(p.queue.length,8);
  p.release();ws.ack(1);ws.ack(2);assert.equal(ws.sent.length,2);
  p.input({action:'look',x:.5,y:0});p.input({action:'look',x:.8,y:0});p.input({action:'look',x:.8,y:0});
  p.release();ws.ack(3);ws.ack(4);
  assert.deepEqual(ws.sent.map(m=>m.type),['input','release','input','release']);
});
test('stationary touch for 5 seconds refreshes with 100ms RTT and releases on blur',()=>{
  let now=0,due=null,lastApplied=null,maxGap=0;
  const ws=socket();const baseSend=ws.send;
  ws.send=function(s){baseSend.call(this,s);due=now+100;};
  const port=new ControlPort(ws,{clock:()=>now});const controls=new Controls(port);controls.setReady();
  controls.stick(1,0); // exactly one pointer move; no keyboard repeats
  function acknowledge(){
    if(due!==null&&now>=due){
      const message=ws.sent.at(-1);due=null;
      if(message.event?.action==='move'){
        if(lastApplied!==null)maxGap=Math.max(maxGap,now-lastApplied);
        lastApplied=now;
      }
      ws.ack(message.sequence);
    }
  }
  for(now=20;now<=5000;now+=20){
    acknowledge();if(now%200===0)controls.heartbeat();port.tick();
    if(lastApplied!==null)assert.ok(now-lastApplied<2000);
    assert.equal(port.closed,false);assert.ok(port.queue.length<=1);
  }
  assert.ok(maxGap<=200);assert.ok(ws.sent.length>=25&&ws.sent.length<=27);
  controls.setVisible(false);assert.deepEqual(controls.move,[0,0]);
  for(let i=0;i<150;i++){now+=20;acknowledge();controls.heartbeat();port.tick();}
  assert.equal(ws.sent.at(-1).type,'release');
  const count=ws.sent.length;controls.setVisible(true);controls.heartbeat();
  assert.equal(ws.sent.length,count); // resume never resurrects old touch state
});
