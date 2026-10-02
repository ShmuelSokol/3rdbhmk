// Semantic controls only. Never emit UE data-channel input or console commands.
export class Controls {
  constructor(port) { this.port=port; this.keys=new Set(); this.active=false; this.closed=false; this.suspended=false; this.move=[0,0]; }
  setReady() { if(!this.closed)this.active=true; }
  setVisible(visible) { if(!visible)this.release(); this.suspended=!visible; }
  emit(action,x=0,y=0) {
    if(!this.active||this.suspended)return;
    if (action==='move') this.move=[x,y];
    if (this.active) this.port.input({action,x,y});
  }
  heartbeat() { if(this.active&&!this.suspended&&(this.move[0]||this.move[1]))this.emit('move',...this.move); }
  key(code,down,repeat=false) {
    if (!this.active||this.suspended) return;
    const movement=['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowLeft','ArrowDown','ArrowRight'];
    if (movement.includes(code)) {
      if (down) this.keys.add(code); else this.keys.delete(code);
      const k=(a,b)=>this.keys.has(a)||this.keys.has(b);
      this.emit('move',Number(k('KeyD','ArrowRight'))-Number(k('KeyA','ArrowLeft')),
        Number(k('KeyW','ArrowUp'))-Number(k('KeyS','ArrowDown')));
      return true;
    }
    const action={KeyE:'interact',KeyP:'pause',KeyM:'mute'}[code];
    if (action && down && !repeat) this.emit(action);
    return Boolean(action);
  }
  stick(x,y) {
    if (![x,y].every(Number.isFinite)) return;
    const axis=v=>Math.abs(v)<0.2?0:Math.sign(v);
    this.emit('move',axis(x),-axis(y));
  }
  look(dx,dy) {
    if (![dx,dy].every(Number.isFinite)) return;
    const norm=v=>Math.max(-1,Math.min(1,v/100));
    this.emit('look',norm(dx),norm(dy));
  }
  release() { this.keys.clear(); this.move=[0,0]; if (this.active) this.port.release(); }
  disconnect() {
    if (this.closed) return;
    try { this.release(); } finally { this.active=false; this.closed=true; this.port.close(); }
  }
}

// One in-flight request plus at most 8 queued events; no unbounded input backlog.
// Release supersedes queued input. Missing/mismatched ACK closes the transport.
export class ControlPort {
  constructor(ws,{clock=()=>performance.now(),timeout=1500,onClose=()=>{}}={}) {
    this.ws=ws; this.clock=clock; this.timeout=timeout; this.onClose=onClose;
    this.sequence=0; this.pending=null; this.queue=[]; this.closed=false;
    ws.addEventListener('message',e=>{
      try {
        if (typeof e.data!=='string' || e.data.length>256) throw Error();
        const m=JSON.parse(e.data);
        if (m.type!=='ack'||!this.pending||m.sequence!==this.pending.sequence) throw Error();
        const now=this.clock();
        if(!Number.isFinite(now)||now>=this.pending.deadline)throw Error();
        this.pending=null; this.pump();
      } catch { this.close(); }
    });
    ws.addEventListener('close',()=>this.close());
    ws.addEventListener('error',()=>this.close());
  }
  input(event) {
    if (this.closed) return;
    const tail=this.queue.at(-1);
    if (event.action==='move'&&tail?.event?.action==='move') tail.event=event;
    else if (event.action==='look'&&tail?.event?.action==='look') {
      const x=tail.event.x+event.x,y=tail.event.y+event.y;
      if (Math.abs(x)>8 || Math.abs(y)>8) { this.close(); return; }
      tail.event={action:'look',x,y};
    } else {
      if (this.queue.length>=8) { this.close(); return; }
      this.queue.push({type:'input',event:{...event}});
    }
    this.pump();
  }
  release() {
    if (this.closed) return;
    this.queue=[{type:'release'}]; this.pump();
  }
  pump() {
    if (this.closed || this.pending || !this.queue.length) return;
    if (this.ws.readyState!==1 || this.ws.bufferedAmount>8192) { this.close(); return; }
    const next=this.queue[0];
    let m;
    if(next.event?.action==='look') {
      const x=Math.max(-1,Math.min(1,next.event.x)),y=Math.max(-1,Math.min(1,next.event.y));
      m={type:'input',event:{action:'look',x,y},sequence:++this.sequence};
      next.event.x-=x;next.event.y-=y;
      if(Math.abs(next.event.x)<1e-12&&Math.abs(next.event.y)<1e-12)this.queue.shift();
    } else m={...this.queue.shift(),sequence:++this.sequence};
    this.pending={sequence:m.sequence,deadline:this.clock()+this.timeout};
    try { this.ws.send(JSON.stringify(m)); } catch { this.close(); }
  }
  tick() { if (this.pending && this.clock()>=this.pending.deadline) this.close(); }
  close() {
    if (this.closed) return;
    this.closed=true; this.queue=[]; this.pending=null;
    // Server-side transport-close must call core.disconnect, release ACK or quarantine.
    try { this.ws.close(); } finally { this.onClose(); }
  }
}
