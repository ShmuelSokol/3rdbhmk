// Restricted UE 5.8 JSON signalling, no listeners and no default-stream fallback.
// authority is a TRUSTED synchronous, bounded core-host port, never browser data.
export class GatewayError extends Error { constructor() { super('Session unavailable'); } }
const id = v => typeof v === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(v);
const number = v => typeof v === 'number' && Number.isFinite(v);
const fail = () => { throw new GatewayError(); };
export const ACTIONS = Object.freeze(['move', 'look', 'interact', 'pause', 'mute', 'dove']);
export function semantic(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).some(k => !['action', 'x', 'y'].includes(k)) || !ACTIONS.includes(value.action)) fail();
  const {action, x = 0, y = 0} = value;
  if (![x,y].every(v => number(v) && Math.abs(v) <= 1) ||
      (!['move','look'].includes(action) && (x !== 0 || y !== 0))) fail();
  return {action,x,y};
}
function parse(raw) {
  if (typeof raw !== 'string' || raw.length > 65536) fail();
  let m; try { m = JSON.parse(raw); } catch { fail(); }
  if (!m || typeof m !== 'object' || Array.isArray(m) || typeof m.type !== 'string') fail();
  return m;
}
function rtc(m) {
  if (m.type === 'offer' || m.type === 'answer') {
    if (typeof m.sdp !== 'string' || !m.sdp.length || m.sdp.length > 60000) fail();
    return {type:m.type, sdp:m.sdp};
  }
  if (m.type === 'iceCandidate') {
    const c = m.candidate;
    if (!c || typeof c !== 'object' || typeof c.candidate !== 'string' || c.candidate.length > 4096 ||
      !(c.sdpMid === null || (typeof c.sdpMid === 'string' && c.sdpMid.length <= 128)) ||
      !(c.sdpMLineIndex === null || (Number.isInteger(c.sdpMLineIndex) && c.sdpMLineIndex >= 0 && c.sdpMLineIndex <= 65535))) fail();
    return {type:m.type,candidate:{candidate:c.candidate,sdpMid:c.sdpMid,sdpMLineIndex:c.sdpMLineIndex}};
  }
  fail();
}
export class Gateway {
  #routes = new Map(); #clock; #last = -Infinity; #authority; #capacity;
  constructor(authority, {clock = () => performance.now()/1000, capacity = 1} = {}) {
    if (!Number.isInteger(capacity) || capacity < 1 || capacity > 10000) fail();
    this.#authority = authority; this.#clock = clock; this.#capacity = capacity;
  }
  #now() {
    let n; try { n = this.#clock(); } catch { fail(); }
    if (!number(n) || n < 0 || n < this.#last || n > 2**40) fail();
    return this.#last = n;
  }
  #live(r) {
    if (!r || r.closing || this.#now() >= r.expiresAt) fail();
    // Host checks core credential/connection and exact ownership, not just a cached lease.
    try { if (this.#authority.validate(r.binding) !== true) fail(); } catch { fail(); }
    if (r.closing || this.#now() >= r.expiresAt) fail();
  }
  // Called only after core.connect and native gate installation + release ACK.
  // expiresAt is host-converted into THIS gateway's monotonic domain; never browser supplied.
  allocate({streamId, playerId, expiresAt, binding}) {
    if (!id(streamId) || !id(playerId) || !number(expiresAt) || expiresAt <= this.#now() ||
      expiresAt - this.#now() > 86400 || this.#routes.has(streamId) || this.#routes.size >= this.#capacity) fail();
    const r = {streamId,playerId,expiresAt,binding,streamer:null,player:null,control:null,
      ready:false,subscribed:false,closing:false,cleaning:false,disconnected:false,sequence:0,controlGeneration:0,handoffOld:null,window:0,count:0};
    this.#live(r); this.#routes.set(streamId,r);
  }
  // peer is an already authenticated, bounded transport. It must throw on failed send.
  // Transport close calls returned .close(); tick is required even with no traffic.
  attach(streamId, role, peer) {
    const r = this.#routes.get(streamId);
    this.#live(r);
    if (!['streamer','player','control'].includes(role) || r[role]) fail();
    r[role] = peer;
    try {
      if (role !== 'control') peer.send({type:'config',protocolVersion:'1.3.0',peerConnectionOptions:{iceServers:[]}});
      if (role === 'streamer') peer.send({type:'identify'});
    } catch { this.#revoke(r); fail(); }
    return Object.freeze({
      receive: raw => {
        try {
          this.#live(r);
          const n = this.#now();
          if (n - r.window >= 1) { r.window = n; r.count = 0; }
          if (++r.count > 240) fail(); // bounded total ingress per session
          this.#message(r,role,parse(raw));
        } catch { this.#revoke(r); fail(); }
      },
      close: () => this.#revoke(r)
    });
  }
  #send(r,peer,m) { this.#live(r); if (!peer) fail(); peer.send(m); }
  #message(r,role,m) {
    if (m.type === 'ping' && role !== 'control') {
      if (!number(m.time)) fail();
      return this.#send(r,r[role],{type:'pong',time:m.time});
    }
    if (role === 'streamer') {
      if (m.type === 'endpointId' && !r.ready && m.id === r.streamId) {
        r.ready = true;
        return this.#send(r,r.streamer,{type:'endpointIdConfirm',committedId:r.streamId});
      }
      if (!r.ready || !r.subscribed || m.playerId !== r.playerId) fail();
      if (m.type === 'disconnectPlayer') return this.#revoke(r);
      return this.#send(r,r.player,rtc(m));
    }
    if (role === 'player') {
      if (m.type === 'listStreamers') return this.#send(r,r.player,{type:'streamerList',ids:r.ready?[r.streamId]:[]});
      if (m.type === 'subscribe') {
        if (m.streamerId !== r.streamId || !r.ready || r.subscribed || !r.control) fail();
        r.subscribed = true;
        return this.#send(r,r.streamer,{type:'playerConnected',playerId:r.playerId,dataChannel:true,sfu:false});
      }
      if (m.type === 'unsubscribe') return this.#revoke(r);
      if (!r.subscribed || !r.ready) fail(); // NEVER choose first streamer
      return this.#send(r,r.streamer,{...rtc(m),playerId:r.playerId});
    }
    let handoff=false;
    if(m.generation!==r.controlGeneration)fail();
    if (m.type === 'release') {
      if (!Number.isSafeInteger(m.sequence) || m.sequence !== r.sequence + 1) fail();
      if (this.#authority.release(r.binding) !== undefined) fail(); // synchronous applied ACK only
    } else if (m.type === 'input') {
      if (!r.subscribed || !Number.isSafeInteger(m.sequence) || m.sequence !== r.sequence + 1) fail();
      const event=semantic(m.event);
      if(event.action==='dove') {
        if(r.controlGeneration>=255)fail(); // BEFORE any native action/credential rotation
        r.handoffOld=r.binding;
      }
      const result=this.#authority.submit(r.binding,event);
      if(result!==undefined&&result!==null) {
        if(m.event.action!=='dove'||!result||Object.keys(result).sort().join(',')!=='binding,streamId'||
           result.streamId!==r.streamId)fail();
        r.binding=result.binding;this.#live(r); // fresh Core binding, original expiry unchanged
        if(this.#authority.commitHandoff(r.handoffOld,r.binding)!==undefined)fail();
        r.handoffOld=null;
        r.controlGeneration++;handoff=true;
      } else r.handoffOld=null;
    } else fail();
    r.sequence = m.sequence;
    this.#send(r,r.control,{type:'ack',sequence:r.sequence,generation:r.controlGeneration,handoff});
  }
  #revoke(r) {
    if (this.#routes.get(r.streamId) !== r) return; // delayed close must not delete a replacement
    r.closing = true; r.subscribed = false;
    if (r.cleaning) return;
    r.cleaning = true;
    if(r.handoffOld!==null) {
      try {
        if(this.#authority.abortHandoff(r.handoffOld)!==undefined)fail();
        r.handoffOld=null;
      } catch {} // retain route/capacity until exact fresh allocation cleanup succeeds
    }
    // Retry unfinished cleanup, retaining slot. Never expose adapter exception strings.
    for (const key of ['player','control','streamer']) {
      if (r[key]) { try { r[key].close(); r[key] = null; } catch {} }
    }
    if (!r.disconnected) {
      try { if (this.#authority.disconnect(r.binding) === undefined) r.disconnected = true; } catch {}
    }
    if (r.handoffOld===null && r.disconnected && !r.player && !r.control && !r.streamer) this.#routes.delete(r.streamId);
    r.cleaning = false;
  }
  tick() {
    for (const r of [...this.#routes.values()]) {
      try { this.#live(r); } catch { this.#revoke(r); }
    }
  }
  get occupied() { return this.#routes.size; }
}
