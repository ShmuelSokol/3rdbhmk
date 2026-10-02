import test from 'node:test';
import assert from 'node:assert/strict';
import {Gateway,GatewayError,semantic} from './gateway.mjs';
import {Controls} from '../browser/controls.mjs';

function setup(options={}) {
  let now=100;
  const calls=[];
  const authority={validate:()=>true,submit:()=>{calls.push('submit');},release:()=>{calls.push('release');},disconnect:()=>{calls.push('disconnect');},...options};
  const g=new Gateway(authority,{clock:()=>now,capacity:2});
  const binding={};
  const allocate=(id='s')=>g.allocate({streamId:id,playerId:'p_'+id,expiresAt:110,binding});
  allocate();
  const peers={};
  function attach(role,s='s') {
    const peer={messages:[],closed:0,send(m){this.messages.push(m);},close(){this.closed++;}};
    const endpoint=g.attach(s,role,peer);
    const entry={peer,endpoint,send:m=>endpoint.receive(JSON.stringify(m))};
    peers[role]=entry; return entry;
  }
  const streamer=attach('streamer'),player=attach('player'),control=attach('control');
  streamer.send({type:'endpointId',id:'s'});
  const subscribe=()=>player.send({type:'subscribe',streamerId:'s'});
  return {g,authority,calls,peers,streamer,player,control,allocate,attach,subscribe,setTime:n=>now=n};
}
test('unallocated and hostile IDs reject',()=>{
  const {g}=setup();
  for(const id of ['missing',[],{},'x'.repeat(129)])assert.throws(()=>g.attach(id,'player',{}),GatewayError);
});
test('offer before explicit subscribe cannot fall back',()=>{
  const x=setup();
  assert.throws(()=>x.player.send({type:'offer',sdp:'real-sdp'}),GatewayError);
  assert.equal(x.streamer.peer.messages.some(m=>m.type==='offer'),false);
});
test('delayed subscription: connecting browser input never reaches gateway or tears down',()=>{
  const x=setup();let sequence=0;
  const c=new Controls({input:event=>x.control.send({type:'input',sequence:++sequence,event}),
    release:()=>x.control.send({type:'release',sequence:++sequence}),close:()=>x.control.endpoint.close()});
  c.key('KeyW',true);c.look(20,10);c.stick(1,1);c.release();
  assert.equal(sequence,0);assert.equal(x.g.occupied,1);assert.equal(x.calls.length,0);
  x.subscribe();c.setReady();c.heartbeat();assert.equal(sequence,0);
  c.key('KeyW',true);assert.equal(sequence,1);assert.equal(x.g.occupied,1);
});
test('subscribe other allocated stream denied and list private',()=>{
  const x=setup(); x.allocate('other');
  x.player.send({type:'listStreamers'});
  assert.deepEqual(x.player.peer.messages.at(-1),{type:'streamerList',ids:['s']});
  assert.throws(()=>x.player.send({type:'subscribe',streamerId:'other'}),GatewayError);
});
test('real offer answer ICE relayed only exact subscribed peers',()=>{
  const x=setup();x.subscribe();
  x.player.send({type:'offer',sdp:'v=0\r\n',playerId:'attacker'});
  assert.deepEqual(x.streamer.peer.messages.at(-1),{type:'offer',sdp:'v=0\r\n',playerId:'p_s'});
  x.streamer.send({type:'answer',sdp:'v=0\r\n',playerId:'p_s'});
  assert.deepEqual(x.player.peer.messages.at(-1),{type:'answer',sdp:'v=0\r\n'});
  x.player.send({type:'iceCandidate',candidate:{candidate:'candidate:1',sdpMid:'0',sdpMLineIndex:0}});
  assert.equal(x.streamer.peer.messages.at(-1).playerId,'p_s');
  assert.throws(()=>x.streamer.send({type:'answer',sdp:'x',playerId:'p_other'}),GatewayError);
});
test('streamer cannot squat or rename',()=>{
  const x=setup(); assert.throws(()=>x.streamer.send({type:'endpointId',id:'other'}),GatewayError);
});
test('synchronous transport-close callback cleanup is bounded and once',()=>{
  const x=setup();
  for(const {peer,endpoint} of Object.values(x.peers))peer.close=function(){this.closed++;endpoint.close();};
  x.player.endpoint.close(); x.player.endpoint.close();
  for(const {peer} of Object.values(x.peers))assert.equal(peer.closed,1);
  assert.equal(x.calls.filter(v=>v==='disconnect').length,1);assert.equal(x.g.occupied,0);
});
test('reentrant failed close keeps quarantine and retries only unfinished',()=>{
  const x=setup();let fail=true;
  x.player.peer.close=function(){this.closed++;x.player.endpoint.close();if(fail)throw Error('secret');};
  x.player.endpoint.close();assert.equal(x.g.occupied,1);
  assert.equal(x.player.peer.closed,1); assert.equal(x.control.peer.closed,1);
  fail=false;x.g.tick();assert.equal(x.g.occupied,0);
  assert.equal(x.player.peer.closed,2);assert.equal(x.control.peer.closed,1);
  assert.equal(x.calls.filter(v=>v==='disconnect').length,1);
});
test('delayed close cannot dispose replacement allocation with same stream ID',()=>{
  const x=setup();x.player.endpoint.close();x.allocate();
  x.player.endpoint.close();assert.equal(x.g.occupied,1);
});
test('noncompleted authority results never produce ACK or free cleanup slot',()=>{
  for(const result of [false,{status:'queued'}]){
    for(const op of ['submit','release']){
      const x=setup({[op]:()=>result,disconnect:()=>false});x.subscribe();
      const m=op==='submit'?{type:'input',sequence:1,event:{action:'pause'}}:{type:'release',sequence:1};
      assert.throws(()=>x.control.send(m),GatewayError);
      assert.equal(x.control.peer.messages.length,0);assert.equal(x.g.occupied,1);
    }
  }
});
for(const op of ['submit','release'])test(`${op} failure never ACKs or leaks adapter error`,()=>{
  const x=setup({[op]:()=>{throw Error('credential-DO-NOT-EXPOSE');}});x.subscribe();
  const msg=op==='submit'?{type:'input',sequence:1,event:{action:'interact'}}:{type:'release',sequence:1};
  assert.throws(()=>x.control.send(msg),e=>e instanceof GatewayError&&!e.message.includes('credential'));
  assert.equal(x.control.peer.messages.length,0);assert.equal(x.g.occupied,0);
});
test('ACK after adapter applied and sequence replay refused',()=>{
  const x=setup();x.subscribe();
  x.authority.submit=()=>assert.equal(x.control.peer.messages.length,0);
  x.control.send({type:'input',sequence:1,event:{action:'move',x:1}});
  assert.deepEqual(x.control.peer.messages,[{type:'ack',sequence:1}]);
  assert.throws(()=>x.control.send({type:'release',sequence:1}),GatewayError);
});
test('expiry after authority callback refuses dispatch and ACK',()=>{
  const x=setup();x.subscribe();
  x.authority.validate=()=>{x.setTime(111);return true;};
  assert.throws(()=>x.control.send({type:'input',sequence:1,event:{action:'mute'}}),GatewayError);
  assert.equal(x.calls.includes('submit'),false);assert.equal(x.control.peer.messages.length,0);
});
test('slow input or release passing expiry is never ACKed',()=>{
  for(const op of ['submit','release']){
    const x=setup();x.subscribe();x.authority[op]=()=>x.setTime(111);
    const m=op==='submit'?{type:'input',sequence:1,event:{action:'mute'}}:{type:'release',sequence:1};
    assert.throws(()=>x.control.send(m),GatewayError);assert.equal(x.control.peer.messages.length,0);
  }
});
test('disconnect adapter failure keeps allocation charged',()=>{
  const x=setup({disconnect:()=>{throw Error('private');}});x.player.endpoint.close();
  assert.equal(x.g.occupied,1);x.g.tick();assert.equal(x.g.occupied,1);
  x.authority.disconnect=()=>{};x.g.tick();assert.equal(x.g.occupied,0);
});
test('bounded messages rate and unsupported commands',()=>{
  for(const raw of ['x'.repeat(65537),'[]','null','{"type":"Command","console":"quit"}']) {
    const x=setup();assert.throws(()=>x.player.endpoint.receive(raw),GatewayError);
  }
  for(const action of ['reset','dove','console','keypress'])assert.throws(()=>semantic({action}),GatewayError);
  for(const value of [Infinity,NaN,1e300,{},true])assert.throws(()=>semantic({action:'move',x:value}),GatewayError);
  const x=setup(); for(let i=0;i<239;i++)x.player.send({type:'ping',time:0});
  assert.throws(()=>x.player.send({type:'ping',time:0}),GatewayError);
});
