// Keyboard, mouse, touch and gamepad, reduced to one small state object the player reads.
export function createInput(canvas, stickEl, opts) {
  const state = {
    moveX: 0, moveZ: 0,       // strafe right, forward: -1..1
    lookX: 0, lookY: 0,       // radians accumulated since last read
    run: false, up: false, down: false,
    jump: false,
    touch: false,             // true once a touch has been seen
  };
  const keys = new Set();
  const settings = { sensitivity: 1, invertY: false, ...opts };
  let enabled = true;
  const listeners = { tap: [], action: [], firstInput: [] };
  const emit = (k, ...a) => listeners[k].forEach((f) => f(...a));
  let sawInput = false;
  const noteInput = () => { if (!sawInput) { sawInput = true; emit('firstInput'); } };

  // ------------------------------------------------------------ keyboard
  const ACTIONS = {
    KeyF: 'fly', KeyM: 'map', KeyT: 'tour', KeyH: 'help', Slash: 'help',
    BracketRight: 'next', BracketLeft: 'prev', KeyN: 'next', KeyP: 'prev', Escape: 'escape', KeyG: 'go',
  };
  const isTyping = (e) => /INPUT|TEXTAREA|SELECT/.test(e.target.tagName) || e.target.isContentEditable;
  window.addEventListener('keydown', (e) => {
    if (isTyping(e) || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.code === 'Escape') { emit('action', 'escape'); return; }
    if (!enabled) return;
    // Space and Enter belong to a focused button, not to jumping.
    if ((e.code === 'Space' || e.code === 'Enter') && e.target.closest && e.target.closest('button, a, [role="button"]')) return;
    keys.add(e.code);
    if (ACTIONS[e.code] && !e.repeat) emit('action', ACTIONS[e.code]);
    if (e.code === 'Space' && !e.repeat) state.jump = true;
    if (/^(Arrow|Space)/.test(e.code)) e.preventDefault();
    noteInput();
  });
  window.addEventListener('keyup', (e) => keys.delete(e.code));
  window.addEventListener('blur', () => { keys.clear(); endStick(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { keys.clear(); endStick(); } });

  // ------------------------------------------------------------ pointer: look, joystick, tap
  const pointers = new Map(); // id -> { kind, x0, y0, x, y, t0, moved }
  let stickId = null;
  const STICK_R = 56;
  function endStick() {
    stickId = null;
    state.stickX = 0; state.stickY = 0;
    stickEl.classList.remove('on');
  }
  state.stickX = 0; state.stickY = 0;

  canvas.addEventListener('pointerdown', (e) => {
    if (!enabled) return;
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    canvas.setPointerCapture?.(e.pointerId);
    const p = { x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY, t0: performance.now(), moved: 0, kind: 'look', type: e.pointerType };
    if (e.pointerType === 'touch') {
      state.touch = true;
      const leftZone = e.clientX < window.innerWidth * 0.45 && e.clientY > window.innerHeight * 0.3;
      if (leftZone && stickId === null) {
        p.kind = 'stick';
        stickId = e.pointerId;
        stickEl.style.left = `${e.clientX}px`;
        stickEl.style.top = `${e.clientY}px`;
        stickEl.style.setProperty('--kx', '0px');
        stickEl.style.setProperty('--ky', '0px');
        stickEl.classList.add('on');
      }
    }
    pointers.set(e.pointerId, p);
    noteInput();
  });
  canvas.addEventListener('pointermove', (e) => {
    if (document.pointerLockElement === canvas) {
      state.lookX -= e.movementX * 0.0022 * settings.sensitivity;
      state.lookY -= e.movementY * 0.0022 * settings.sensitivity * (settings.invertY ? -1 : 1);
      return;
    }
    const p = pointers.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    p.moved += Math.abs(dx) + Math.abs(dy);
    if (p.kind === 'stick') {
      let sx = p.x - p.x0, sy = p.y - p.y0;
      const len = Math.hypot(sx, sy);
      if (len > STICK_R) { sx *= STICK_R / len; sy *= STICK_R / len; }
      stickEl.style.setProperty('--kx', `${sx}px`);
      stickEl.style.setProperty('--ky', `${sy}px`);
      state.stickX = sx / STICK_R;
      state.stickY = -sy / STICK_R;
    } else {
      const k = (p.type === 'touch' ? 0.0052 : 0.0036) * settings.sensitivity;
      state.lookX -= dx * k;
      state.lookY -= dy * k * (settings.invertY ? -1 : 1);
    }
  });
  const end = (e) => {
    const p = pointers.get(e.pointerId);
    if (!p) return;
    pointers.delete(e.pointerId);
    if (p.kind === 'stick') endStick();
    else if (e.type === 'pointerup' && p.moved < 8 && performance.now() - p.t0 < 350) emit('tap', e.clientX, e.clientY);
  };
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', end);
  canvas.addEventListener('lostpointercapture', end);
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  canvas.addEventListener('dblclick', () => {
    if (enabled && !state.touch && canvas.requestPointerLock) canvas.requestPointerLock();
  });

  // ------------------------------------------------------------ per-frame read
  function read(dt) {
    let mx = 0, mz = 0;
    if (keys.has('KeyW') || keys.has('ArrowUp')) mz += 1;
    if (keys.has('KeyS') || keys.has('ArrowDown')) mz -= 1;
    if (keys.has('KeyD')) mx += 1;
    if (keys.has('KeyA')) mx -= 1;
    const turn = (keys.has('ArrowLeft') ? 1 : 0) - (keys.has('ArrowRight') ? 1 : 0);
    state.lookX += turn * 1.9 * dt;
    let run = keys.has('ShiftLeft') || keys.has('ShiftRight');
    let up = keys.has('Space') || keys.has('KeyE');
    let down = keys.has('KeyQ') || keys.has('KeyC');

    mx += state.stickX; mz += state.stickY;
    if (Math.hypot(state.stickX, state.stickY) > 0.96) run = true;

    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (const gp of pads) {
      if (!gp || !gp.connected) continue;
      const dz = (v) => (Math.abs(v) < 0.16 ? 0 : v);
      mx += dz(gp.axes[0] || 0); mz -= dz(gp.axes[1] || 0);
      state.lookX -= dz(gp.axes[2] || 0) * 2.4 * dt * settings.sensitivity;
      state.lookY -= dz(gp.axes[3] || 0) * 1.8 * dt * settings.sensitivity * (settings.invertY ? -1 : 1);
      if (gp.buttons[7]?.pressed || gp.buttons[10]?.pressed) run = true;
      if (gp.buttons[0]?.pressed) up = true;
      if (gp.buttons[1]?.pressed) down = true;
      break;
    }
    if (touchUp) up = true;
    if (touchDown) down = true;

    const len = Math.hypot(mx, mz);
    if (len > 1) { mx /= len; mz /= len; }
    const out = {
      moveX: enabled ? mx : 0, moveZ: enabled ? mz : 0, run, up: enabled && up, down: enabled && down,
      lookX: state.lookX, lookY: state.lookY, jump: enabled && state.jump,
    };
    state.lookX = 0; state.lookY = 0; state.jump = false;
    return out;
  }

  let touchUp = false, touchDown = false;
  function holdButton(el, set) {
    const on = (e) => { e.preventDefault(); set(true); noteInput(); };
    const off = () => set(false);
    el.addEventListener('pointerdown', on);
    el.addEventListener('pointerup', off);
    el.addEventListener('pointercancel', off);
    el.addEventListener('pointerleave', off);
  }

  return {
    read,
    settings,
    on: (k, f) => listeners[k].push(f),
    setEnabled(v) { enabled = v; if (!v) { keys.clear(); endStick(); pointers.clear(); } },
    bindAscend: (el) => holdButton(el, (v) => { touchUp = v; }),
    bindDescend: (el) => holdButton(el, (v) => { touchDown = v; }),
    get isTouch() { return state.touch; },
  };
}
