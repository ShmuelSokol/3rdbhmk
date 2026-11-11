// Sound made in the browser, with no recordings: wind over the Mount, footsteps on stone that
// ring a little under a roof, the fire on the altar, and sparrows in the lanes of the city. It starts with the visitor's first
// touch or key, because browsers allow no sound before that.

export function createSound() {
  let ctx = null, master = null, on = true;
  let windGain, windFilter, fireGain, stepBus, roomGain, crackleAt = 0;
  let walked = 0, lastX = 0, lastZ = 0, havePos = false, foot = 0, birdAt = 0;

  function noiseBuffer(seconds, brown) {
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * seconds), ctx.sampleRate);
    const d = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < d.length; i++) {
      const w = Math.random() * 2 - 1;
      if (brown) { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; } else d[i] = w;
    }
    return buf;
  }

  function begin() {
    if (ctx || !on) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0;
    master.gain.linearRampToValueAtTime(0.9, ctx.currentTime + 2.5);
    master.connect(ctx.destination);

    // wind: two bands of noise that swell and fall on their own slow rhythms
    const white = noiseBuffer(4, false), brown = noiseBuffer(5, true);
    const loop = (buf) => { const s = ctx.createBufferSource(); s.buffer = buf; s.loop = true; s.start(); return s; };
    windFilter = ctx.createBiquadFilter();
    windFilter.type = 'bandpass'; windFilter.frequency.value = 420; windFilter.Q.value = 0.6;
    windGain = ctx.createGain(); windGain.gain.value = 0.05;
    loop(white).connect(windFilter).connect(windGain).connect(master);
    const low = ctx.createBiquadFilter(); low.type = 'lowpass'; low.frequency.value = 160;
    const lowGain = ctx.createGain(); lowGain.gain.value = 0.35;
    loop(brown).connect(low).connect(lowGain).connect(windGain);
    for (const [rate, depth, target] of [[0.07, 0.03, windGain.gain], [0.11, 160, windFilter.frequency]]) {
      const lfo = ctx.createOscillator(); lfo.frequency.value = rate;
      const g = ctx.createGain(); g.gain.value = depth;
      lfo.connect(g).connect(target); lfo.start();
    }

    // the altar fire: a low roar, with crackles added as they happen
    fireGain = ctx.createGain(); fireGain.gain.value = 0;
    const roar = ctx.createBiquadFilter(); roar.type = 'bandpass'; roar.frequency.value = 240; roar.Q.value = 0.4;
    loop(brown).connect(roar).connect(fireGain).connect(master);

    // footsteps go out dry, and through a short echo that only opens up indoors
    stepBus = ctx.createGain(); stepBus.gain.value = 1;
    stepBus.connect(master);
    roomGain = ctx.createGain(); roomGain.gain.value = 0;
    let prev = stepBus;
    for (const t of [0.061, 0.097, 0.149]) {
      const dl = ctx.createDelay(0.5); dl.delayTime.value = t;
      const fb = ctx.createGain(); fb.gain.value = 0.42;
      const damp = ctx.createBiquadFilter(); damp.type = 'lowpass'; damp.frequency.value = 2200;
      prev.connect(dl); dl.connect(damp).connect(fb).connect(dl);
      dl.connect(roomGain);
      prev = dl;
    }
    roomGain.connect(master);
    crackleAt = ctx.currentTime + 1;
  }

  function burst(dest, when, dur, freq, q, gain, type = 'bandpass') {
    const src = ctx.createBufferSource();
    src.buffer = burst.buf || (burst.buf = noiseBuffer(0.4, false));
    const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(gain, when + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    src.connect(f).connect(g).connect(dest);
    src.start(when, Math.random() * 0.3, dur + 0.02);
  }

  function chirp(t, k) {
    const notes = 2 + Math.floor(Math.random() * 5), base = 3200 + Math.random() * 2200, far = 0.25 + Math.random() * 0.75;
    const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    if (pan) { pan.pan.value = Math.random() * 1.6 - 0.8; pan.connect(master); }
    for (let i = 0; i < notes; i++) {
      const at = t + i * (0.07 + Math.random() * 0.05), o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sine';
      o.frequency.setValueAtTime(base * (0.9 + Math.random() * 0.3), at);
      o.frequency.exponentialRampToValueAtTime(base * (0.6 + Math.random() * 0.8), at + 0.05);
      g.gain.setValueAtTime(0, at);
      g.gain.linearRampToValueAtTime(0.035 * far * k, at + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0001, at + 0.06);
      o.connect(g).connect(pan || master);
      o.start(at); o.stop(at + 0.08);
    }
  }

  function step(speedK) {
    const t = ctx.currentTime;
    foot ^= 1;
    const v = 0.85 + Math.random() * 0.3;
    // heel on stone, then the softer roll of the sole
    burst(stepBus, t, 0.07, (foot ? 190 : 220) * v, 1.2, 0.5 * speedK, 'lowpass');
    burst(stepBus, t + 0.004, 0.035, 1900 * v, 0.9, 0.11 * speedK);
    burst(stepBus, t + 0.06 + Math.random() * 0.02, 0.09, 900 * v, 0.7, 0.05 * speedK);
  }

  /** state: { x, y, z, walking, onGround, roofed (0..1), fireDist, flying } */
  function update(dt, s) {
    if (!ctx || !on) return;
    if (ctx.state === 'suspended') ctx.resume();
    const t = ctx.currentTime;
    const open = 1 - s.roofed;
    windGain.gain.setTargetAtTime((0.035 + 0.06 * open) * (s.flying ? 1.7 + Math.min(1, s.y / 60) : 1), t, 0.6);
    roomGain.gain.setTargetAtTime(0.75 * s.roofed, t, 0.3);
    const near = 1 / (1 + (s.fireDist / 9) ** 2);
    fireGain.gain.setTargetAtTime(0.5 * near * (0.35 + 0.65 * open), t, 0.4);
    if (t > crackleAt) {
      if (near > 0.02) burst(master, t, 0.012 + Math.random() * 0.03, 1500 + Math.random() * 3500, 2.5, (0.1 + Math.random() * 0.35) * near);
      crackleAt = t + 0.03 + Math.random() * Math.random() * 0.5;
    }
    // sparrows in the lanes of the city, west of the Mount
    if (t > birdAt) {
      if (s.x < -225 && !s.roofed) chirp(t, s.flying ? 0.5 : 1);
      birdAt = t + 0.8 + Math.random() * Math.random() * 9;
    }
    if (havePos && s.walking && s.onGround) {
      const d = Math.hypot(s.x - lastX, s.z - lastZ);
      if (d < 2) walked += d;
      if (walked > 0.74) { walked = 0; step(Math.min(1.3, 0.6 + (d / Math.max(dt, 1e-3)) / 6)); }
    } else walked = 0.5;
    lastX = s.x; lastZ = s.z; havePos = true;
  }

  function setOn(v) {
    on = v;
    if (!ctx) return;
    master.gain.setTargetAtTime(v ? 0.9 : 0, ctx.currentTime, 0.2);
  }

  for (const ev of ['pointerdown', 'keydown', 'touchend']) window.addEventListener(ev, begin, { passive: true });
  document.addEventListener('visibilitychange', () => { if (ctx) (document.hidden ? ctx.suspend() : ctx.resume()); });
  return { update, setOn, get on() { return on; } };
}
