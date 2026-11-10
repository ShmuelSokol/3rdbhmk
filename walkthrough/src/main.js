import * as THREE from 'three';
import { createWorld, TIMES } from './world.js';
import { createPlayer, lookAngles } from './player.js';
import { createInput } from './input.js';
import { createUI } from './ui.js';
import tour from './data/tour.json';
import codex from './data/codex.json';

const params = new URLSearchParams(location.search);
const canvas = document.getElementById('view');
const fadeEl = document.getElementById('fade');
const stops = tour.stops;

// ---------------------------------------------------------------- settings
const STORE = 'mikdash-walk-v1';
const defaults = {
  time: 'morning', quality: 'auto', sensitivity: 1, invertY: false, showTour: true,
  reduceMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
};
let saved = {};
try { saved = JSON.parse(localStorage.getItem(STORE) || '{}') || {}; } catch { saved = {}; }
const prefs = { ...defaults, ...saved.prefs };
let seen = new Set(Array.isArray(saved.seen) ? saved.seen.filter((i) => i >= 0 && i < stops.length) : []);
function persist() {
  try { localStorage.setItem(STORE, JSON.stringify({ prefs, seen: [...seen] })); } catch { /* private mode */ }
}

const coarse = window.matchMedia('(pointer: coarse)').matches;
function pickQuality() {
  const q = params.get('q') || prefs.quality;
  if (q === 'low' || q === 'medium' || q === 'high') return q;
  const mem = navigator.deviceMemory || 4;
  const cores = navigator.hardwareConcurrency || 4;
  if (coarse) return mem <= 3 || cores <= 4 ? 'low' : 'medium';
  return cores >= 8 && mem >= 8 ? 'high' : 'medium';
}
const quality = pickQuality();

// ---------------------------------------------------------------- renderer
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: quality !== 'low', powerPreference: 'high-performance', stencil: false });
} catch (err) {
  document.getElementById('loadbar').hidden = true;
  const note = document.getElementById('loadnote');
  note.textContent = 'This browser could not start 3D graphics (WebGL). Try a current Chrome, Safari, Edge or Firefox.';
  note.style.color = '#f0b9a0';
  throw err;
}
const PR_CAP = { low: 1, medium: 1.5, high: 2 }[quality];
const basePR = Math.min(window.devicePixelRatio || 1, PR_CAP);
let prScale = 1;
renderer.setPixelRatio(basePR);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = quality === 'low' ? THREE.PCFShadowMap : THREE.PCFSoftShadowMap;

const camera = new THREE.PerspectiveCamera(70, 1, 0.1, 14000);
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  // keep a comfortable horizontal view on tall phone screens
  camera.fov = w < h ? 82 : 68;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
window.addEventListener('orientationchange', () => setTimeout(resize, 200));
resize();

// ---------------------------------------------------------------- places
const PLACES = {
  mount: ['The Mount', 'הר הבית'],
  outerGateE: ['East gate, outer court', 'שער המזרח החיצון'],
  outerGateN: ['North gate, outer court', 'שער הצפון החיצון'],
  outerGateS: ['South gate, outer court', 'שער הדרום החיצון'],
  outer: ['The outer court', 'העזרה החיצונה'],
  innerGateE: ['East gate, inner court', 'שער המזרח הפנימי'],
  innerGateN: ['North gate, inner court', 'שער הצפון הפנימי'],
  innerGateS: ['South gate, inner court', 'שער הדרום הפנימי'],
  yisroel: ['The Court of Israel', 'עזרת ישראל'],
  kohanim: ['The Court of the Kohanim', 'עזרת כהנים'],
  altar: ['At the altar', 'המזבח'],
  steps: ['The twelve steps', 'שתים עשרה מעלות'],
  ulam: ['The Ulam', 'אולם'],
  heikhal: ['The Heikhal', 'היכל'],
  kodesh: ['Kodesh HaKodashim', 'קדש הקדשים'],
  house: ['Beside the House', 'הבית'],
  above: ['Above the Mikdash', ''],
};
function placeAt(p, flying) {
  const { x, y, z } = p;
  const ax = Math.abs(x), az = Math.abs(z);
  if (flying && y > 38) return PLACES.above;
  if (ax > 81.5 || az > 81.5) {
    if (x > 78 && x < 93 && az < 13) return PLACES.outerGateE;
    if (z < -78 && z > -96 && ax < 13) return PLACES.outerGateN;
    if (z > 78 && z < 96 && ax < 13) return PLACES.outerGateS;
    return PLACES.mount;
  }
  if (x > 55 && az < 13) return PLACES.outerGateE;
  if (z < -55 && ax < 13) return PLACES.outerGateN;
  if (z > 55 && ax < 13) return PLACES.outerGateS;
  if (az <= 5.2 && y > 8.5) {
    if (x >= -67.5 && x < -56.5) return PLACES.kodesh;
    if (x >= -56.5 && x < -36) return PLACES.heikhal;
  }
  if (x >= -36 && x < -25 && az < 12.5 && y > 8.5) return PLACES.ulam;
  if (x >= -25 && x < -14 && az < 8) return PLACES.steps;
  if (ax <= 25 && az <= 25) {
    if ((ax < 9.5 && az < 9.5) || (ax < 4.5 && z > 0 && z < 23.5)) return PLACES.altar;
    return x > 11.5 ? PLACES.yisroel : PLACES.kohanim;
  }
  if (x > 25 && x < 51 && az < 13) return PLACES.innerGateE;
  if (z < -25 && z > -51 && ax < 13) return PLACES.innerGateN;
  if (z > 25 && z < 51 && ax < 13) return PLACES.innerGateS;
  if (x < -25 && x > -76 && az < 26) return PLACES.house;
  return PLACES.outer;
}

// ---------------------------------------------------------------- boot
let world, player, input, ui;
let started = false;
let traveling = null;      // active glide between stops
let current = 0;           // selected tour stop
let insideStop = -1;       // stop whose radius the visitor is standing in
let panelOpen = false;

const ARRIVE = (i) => (i === 0 ? 8 : 4);

const settingsApi = {
  get: () => ({ ...prefs, quality: prefs.quality }),
  set(key, value) {
    prefs[key] = value;
    persist();
    if (key === 'time') world.setTime(value);
    else if (key === 'quality') { setTimeout(() => location.reload(), 150); }
    else if (key === 'sensitivity' || key === 'invertY') input.settings[key] = value;
    else if (key === 'reduceMotion') player.reduceMotion = value;
    else if (key === 'showTour') ui.setTourVisible(value);
  },
};

const fade = (on) => new Promise((resolve) => {
  fadeEl.classList.toggle('on', on);
  setTimeout(resolve, prefs.reduceMotion ? 20 : 400);
});

function stopPose(i) {
  const s = stops[i];
  const gy = world.groundBelow(s.stand[0], s.stand[1] + 2.5, s.stand[2]);
  const feet = new THREE.Vector3(s.stand[0], gy ?? s.stand[1], s.stand[2]);
  const eye = feet.clone(); eye.y += player.EYE;
  const a = lookAngles(eye, new THREE.Vector3(...s.look));
  return { feet, yaw: a.yaw, pitch: THREE.MathUtils.clamp(a.pitch, -0.6, 0.75) };
}

function selectStop(i, announce) {
  if (i < 0 || i >= stops.length) return;
  current = i;
  ui.setStop(i, seen);
  updateMarker();
  refreshArrival();
  if (announce && !prefs.showTour) ui.toast(`Stop ${i + 1}: ${stops[i].name}`);
  try { history.replaceState(null, '', `#stop=${stops[i].key}`); } catch { /* file:// */ }
}

function refreshArrival() {
  const s = stops[current];
  const d = Math.hypot(player.position.x - s.stand[0], player.position.z - s.stand[2]);
  const here = d < ARRIVE(current) + 1.5 && Math.abs(player.position.y - s.stand[1]) < 4;
  ui.setArrived(here && !traveling);
  marker.visible = started && !here;
}

async function goStop(i) {
  if (traveling || i < 0 || i >= stops.length) return;
  if (current !== i) selectStop(i, false);
  ui.hideHint();
  const target = stopPose(i);
  if (player.mode === 'fly') { player.setMode('walk'); ui.setFly(false, input.isTouch); }

  // Glide along the walking line when it is clear of walls; otherwise fade across.
  const from = player.position.clone();
  const pts = [from];
  if (insideStop === i - 1) for (const a of stops[i].approach) pts.push(new THREE.Vector3(...a));
  pts.push(target.feet);
  let clear = !prefs.reduceMotion && player.onGround;
  let length = 0;
  const chest = new THREE.Vector3(0, 1.15, 0);
  for (let k = 0; k + 1 < pts.length && clear; k++) {
    length += pts[k].distanceTo(pts[k + 1]);
    if (!world.segmentClear(pts[k].clone().add(chest), pts[k + 1].clone().add(chest))) clear = false;
  }
  if (clear && length > 0.5 && length < 160) {
    const speed = THREE.MathUtils.clamp(length / 4.5, 5, 20);
    traveling = { pts, length, t: 0, duration: length / speed + 0.6, target, yaw0: player.yaw, pitch0: player.pitch, index: i };
    input.setEnabled(false);
    ui.setArrived(false);
    return;
  }
  traveling = { fading: true };
  input.setEnabled(false);
  await fade(true);
  player.setPose(target.feet, target.yaw, target.pitch);
  traveling = null;
  input.setEnabled(!panelOpen);
  arrive(i);
  await fade(false);
}

function arrive(i) {
  insideStop = i;
  if (!seen.has(i)) { seen.add(i); persist(); }
  ui.setStop(current, seen);
  refreshArrival();
}

const smooth = (t) => t * t * (3 - 2 * t);
const lerpAngle = (a, b, t) => a + (((b - a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI) * t;
function updateTravel(dt) {
  const tr = traveling;
  if (!tr || tr.fading) return;
  tr.t = Math.min(1, tr.t + dt / tr.duration);
  const e = smooth(tr.t);
  let d = e * tr.length;
  const p = new THREE.Vector3().copy(tr.pts[tr.pts.length - 1]);
  let heading = tr.target.yaw;
  for (let k = 0; k + 1 < tr.pts.length; k++) {
    const segLen = tr.pts[k].distanceTo(tr.pts[k + 1]);
    if (d <= segLen || k === tr.pts.length - 2) {
      p.lerpVectors(tr.pts[k], tr.pts[k + 1], segLen > 0 ? Math.min(1, d / segLen) : 1);
      heading = lookAngles(tr.pts[k], tr.pts[k + 1]).yaw;
      break;
    }
    d -= segLen;
  }
  const g = world.groundBelow(p.x, p.y + 1.6, p.z);
  if (g !== null && Math.abs(g - p.y) < 2.2) p.y = g;
  // face the way we are going, then settle on the stop's view
  const settle = smooth(THREE.MathUtils.clamp((tr.t - 0.55) / 0.45, 0, 1));
  const lead = smooth(THREE.MathUtils.clamp(tr.t / 0.25, 0, 1));
  const yaw = lerpAngle(lerpAngle(tr.yaw0, heading, lead), tr.target.yaw, settle);
  const pitch = THREE.MathUtils.lerp(THREE.MathUtils.lerp(tr.pitch0, 0, lead), tr.target.pitch, settle);
  player.setPose(p, yaw, pitch);
  if (tr.t >= 1) {
    traveling = null;
    input.setEnabled(!panelOpen);
    arrive(tr.index);
  }
}

// ---------------------------------------------------------------- stop marker
const marker = new THREE.Group();
let markerMats = [];
function buildMarker() {
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.62, 0.8, 48).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ color: 0xffd98a, transparent: true, opacity: 0.9, depthWrite: false, toneMapped: false }));
  ring.position.y = 0.04;
  const beamMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, depthTest: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
    fragmentShader: 'uniform float uTime; varying vec2 vUv; void main(){ float a = pow(1. - vUv.y, 1.6) * (.16 + .05 * sin(uTime * 2.2)); gl_FragColor = vec4(vec3(1., .82, .45) * a, a); }',
  });
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 26, 20, 1, true).translate(0, 13, 0), beamMat);
  beam.renderOrder = 8;
  marker.add(ring, beam);
  markerMats = [ring, beamMat];
  marker.visible = false;
  world.scene.add(marker);
}
function updateMarker() {
  const s = stops[current];
  const gy = world.groundBelow(s.stand[0], s.stand[1] + 2.5, s.stand[2]);
  marker.position.set(s.stand[0], gy ?? s.stand[1], s.stand[2]);
}

// ---------------------------------------------------------------- start
function parseHash() {
  const m = /stop=([\w-]+)/.exec(location.hash);
  if (m) { const i = stops.findIndex((s) => s.key === m[1]); if (i >= 0) return { stop: i }; }
  const p = /p=(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)/.exec(location.hash);
  if (p) return { pose: p.slice(1).map(Number) };
  return {};
}

async function start(mode) {
  if (started) return;
  await fade(true);
  started = true;
  const hash = parseHash();
  const first = hash.stop ?? 0;
  current = first;
  const pose = stopPose(first);
  if (hash.pose) player.setPose(new THREE.Vector3(hash.pose[0], hash.pose[1], hash.pose[2]), hash.pose[3], hash.pose[4]);
  else player.setPose(pose.feet, pose.yaw, pose.pitch);
  const showTour = mode === 'tour';
  if (prefs.showTour !== showTour) { prefs.showTour = showTour; persist(); }
  ui.enter(showTour);
  ui.setStop(current, seen);
  updateMarker();
  if (!hash.pose) arrive(first);
  await fade(false);
  if (coarse) ui.hint(['Slide your left thumb to walk. Drag anywhere else to look.'], 12000);
  else ui.hint([['W'], ['A'], ['S'], ['D'], ' to walk · drag to look · ', ['F'], ' to fly · ', ['H'], ' for help'], 12000);
}

function share() {
  const p = player.position;
  const url = `${location.origin}${location.pathname}#p=${p.x.toFixed(1)},${p.y.toFixed(1)},${p.z.toFixed(1)},${player.yaw.toFixed(2)},${player.pitch.toFixed(2)}`;
  const done = () => ui.toast('Link copied');
  if (navigator.clipboard?.writeText) navigator.clipboard.writeText(url).then(done, () => ui.toast(url, 6000));
  else ui.toast(url, 6000);
}

function toggleFly() {
  if (traveling) return;
  const fly = player.mode !== 'fly';
  player.setMode(fly ? 'fly' : 'walk');
  ui.setFly(fly, input.isTouch || coarse);
  ui.toast(fly ? 'Flying as a dove. Look where you want to go.' : 'Walking');
}

async function boot() {
  ui = createUI({
    tour, codex, times: TIMES, settings: settingsApi,
    actions: {
      start, selectStop, goStop, toggleFly, share,
      panel(open) { panelOpen = open; input?.setEnabled(!open && !traveling); },
      playerPose: () => ({ x: player.position.x, z: player.position.z, yaw: player.yaw }),
      restart() { selectStop(0, false); goStop(0); },
    },
  });
  try {
    world = await createWorld(renderer, quality, (p) => ui.setProgress(p * 0.96));
  } catch (err) {
    console.error(err);
    ui.fail('The model could not be loaded. Check the connection and reload the page.');
    return;
  }
  if (TIMES[prefs.time]) world.setTime(params.get('time') || prefs.time);
  player = createPlayer(camera, world);
  player.reduceMotion = prefs.reduceMotion;
  input = createInput(canvas, document.getElementById('stick'), { sensitivity: prefs.sensitivity, invertY: prefs.invertY });
  input.bindAscend(ui.upButton);
  input.bindDescend(ui.downButton);
  input.setEnabled(false);
  buildMarker();

  input.on('firstInput', () => setTimeout(() => ui.hideHint(), 2500));
  input.on('tap', (x, y) => {
    if (!started || traveling) return;
    const ndc = new THREE.Vector2((x / window.innerWidth) * 2 - 1, -(y / window.innerHeight) * 2 + 1);
    const rc = new THREE.Raycaster();
    rc.setFromCamera(ndc, camera);
    const hit = world.identify(rc.ray);
    if (hit) ui.tag(x, y, hit.name, hit.part);
  });
  input.on('action', (a) => {
    if (a === 'escape') { if (!ui.closeSheet() && document.pointerLockElement) document.exitPointerLock(); return; }
    if (!started || ui.panelOpen) return;
    if (a === 'fly') toggleFly();
    else if (a === 'map') ui.toggle('map');
    else if (a === 'tour') ui.toggle('stops');
    else if (a === 'help') ui.toggle('help');
    else if (a === 'next') selectStop(current + 1, true);
    else if (a === 'prev') selectStop(current - 1, true);
    else if (a === 'go') goStop(current);
  });

  // warm the shaders up before the welcome buttons appear, so the first step is smooth
  camera.position.set(150, 46, 60);
  camera.lookAt(-20, 16, 0);
  renderer.compile(world.scene, camera);
  ui.setProgress(1);
  if (manual) loop(0); else requestAnimationFrame(loop);
  setTimeout(() => { ui.ready(); input.setEnabled(true); window.__mk.ready = true; }, 60);
  // The Old City is several megabytes; it joins the scene once the Mikdash is already usable.
  world.loadCity().then(() => { window.__mk.city = true; }, (e) => { console.warn('The Old City did not load', e); window.__mk.city = 'failed'; });
}

// ---------------------------------------------------------------- loop
const clock = new THREE.Clock();
let emaMs = 16;
let lastTune = 0;
let placeTimer = 0;
const fixedRes = params.has('fixed');
// ?manual stops the animation loop so an automated test can step frames itself.
const manual = params.has('manual');
let manualTime = 0;
function loop(stepDt) {
  if (!manual) requestAnimationFrame(loop);
  const dt = manual ? stepDt || 0 : Math.min(clock.getDelta(), 0.05);
  if (manual) manualTime += dt;
  const time = manual ? manualTime : clock.elapsedTime;

  if (!started) {
    // a slow establishing arc from the east while the welcome card is up
    const a = -0.42 + Math.sin(time * 0.05) * 0.5;
    camera.position.set(-10 + Math.cos(a) * 175, 44 + Math.sin(time * 0.07) * 6, Math.sin(a) * 175);
    camera.lookAt(-18, 17, 0);
    world.update(dt, time, camera.position);
  } else {
    const inp = input.read(dt);
    if (traveling) { updateTravel(dt); inp.moveX = inp.moveZ = inp.lookX = inp.lookY = 0; inp.jump = false; }
    player.update(dt, inp);
    world.update(dt, time, camera.position);

    placeTimer -= dt;
    if (placeTimer <= 0) {
      placeTimer = 0.2;
      const [en, he] = placeAt(player.position, player.mode === 'fly');
      ui.setPlace(en, he);
      if (!traveling) {
        // walking into a stop's circle selects it; walking out forgets it
        let inside = -1;
        for (let i = 0; i < stops.length; i++) {
          const s = stops[i];
          const r = ARRIVE(i) + (insideStop === i ? 2.2 : 0);
          if (Math.hypot(player.position.x - s.stand[0], player.position.z - s.stand[2]) < r && Math.abs(player.position.y - s.stand[1]) < 3) {
            if (inside < 0 || i === current) inside = i;
          }
        }
        if (inside >= 0 && inside !== insideStop) {
          if (inside !== current) selectStop(inside, false);
          arrive(inside);
          ui.toast(`Stop ${inside + 1}: ${stops[inside].name}`);
        } else if (inside < 0) insideStop = -1;
        refreshArrival();
      }
    }
    ui.setCompass(player.yaw);
    if (marker.visible) {
      markerMats[1].uniforms.uTime.value = time;
      const pulse = 1 + 0.12 * Math.sin(time * 2.6);
      marker.children[0].scale.set(pulse, 1, pulse);
    }
  }
  renderer.render(world.scene, camera);

  // dynamic resolution: trade sharpness for smoothness on slow devices, and take it back
  emaMs += (dt * 1000 - emaMs) * 0.05;
  if (!fixedRes && time - lastTune > 1.5) {
    lastTune = time;
    let next = prScale;
    if (emaMs > 36) next = Math.max(0.55, prScale - 0.12);
    else if (emaMs < 19 && prScale < 1) next = Math.min(1, prScale + 0.06);
    if (next !== prScale) { prScale = next; renderer.setPixelRatio(basePR * prScale); renderer.setSize(window.innerWidth, window.innerHeight, false); }
  }
}

window.__mk = {
  ready: false,
  get world() { return world; }, get player() { return player; }, get started() { return started; },
  get traveling() { return !!traveling; }, get quality() { return quality; }, get emaMs() { return emaMs; },
  stops, start, goStop, selectStop, placeAt, camera, renderer,
  step(dt = 1 / 30, n = 1) { for (let i = 0; i < n; i++) loop(dt); },
  get input() { return input; }, get ui() { return ui; }, get seen() { return [...seen]; }, get current() { return current; },
};

boot();
