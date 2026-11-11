// The setting of the Mount as it is today: real ground heights, the platform with its
// retaining walls, the Old City's houses and lanes beyond it, and trees on the slopes.
// The city is drawn from the project's own Old City data (mapped footprints with authored
// detail); it is scenery, and nothing in it is a claim about the Temple.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { install } from './materials.js';
import siteData from './data/site.json';

const loadImage = (url) => new Promise((resolve, reject) => {
  const img = new Image();
  img.onload = () => resolve(img);
  img.onerror = reject;
  img.src = url;
});
function pixels(img) {
  const cv = document.createElement('canvas');
  cv.width = img.width; cv.height = img.height;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  cx.drawImage(img, 0, 0);
  return cx.getImageData(0, 0, cv.width, cv.height).data;
}

export async function createSite(scene, mats, quality, soup, soupOid, wallMat) {
  const ring = siteData.ring; // [x, z] outline of the platform
  const T = siteData.terrain;
  const CM = siteData.citymap;

  // ---------------------------------------------------------------- platform outline
  let rMinX = 1e9, rMaxX = -1e9, rMinZ = 1e9, rMaxZ = -1e9;
  for (const [x, z] of ring) { rMinX = Math.min(rMinX, x); rMaxX = Math.max(rMaxX, x); rMinZ = Math.min(rMinZ, z); rMaxZ = Math.max(rMaxZ, z); }
  function onDeck(x, z) {
    if (x < rMinX || x > rMaxX || z < rMinZ || z > rMaxZ) return false;
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], zi = ring[i][1], xj = ring[j][0], zj = ring[j][1];
      if ((zi > z) !== (zj > z) && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) inside = !inside;
    }
    return inside;
  }

  // ---------------------------------------------------------------- ground heights
  const tp = pixels(await loadImage('assets/terrain.png'));
  const N = T.n;
  const H = new Float32Array(N * N);
  for (let k = 0; k < N * N; k++) H[k] = T.lo + ((tp[k * 4] * 256 + tp[k * 4 + 1]) / 65535) * T.span;
  const coreMaxX = T.x0 + (N - 1) * T.step, coreMaxZ = T.z0 + (N - 1) * T.step;
  const hills = (x, z) => 34 * Math.sin(x * 0.0011 + 1.3) * Math.cos(z * 0.0009 + 0.4) + 18 * Math.sin(x * 0.0031 + z * 0.0023) + 8 * Math.sin(x * 0.0071 - z * 0.0063 + 2.0);
  function ringDist(x, z) {
    let best = 1e18;
    for (let i = 0; i < ring.length; i++) {
      const [ax, az] = ring[i], [bx, bz] = ring[(i + 1) % ring.length];
      const ux = bx - ax, uz = bz - az;
      const t = Math.max(0, Math.min(1, ((x - ax) * ux + (z - az) * uz) / (ux * ux + uz * uz || 1)));
      const dx = x - ax - ux * t, dz = z - az - uz * t;
      const q = dx * dx + dz * dz;
      if (q < best) best = q;
    }
    return Math.sqrt(best);
  }
  function terrainAt(x, z) {
    const cx = Math.min(coreMaxX, Math.max(T.x0, x)), cz = Math.min(coreMaxZ, Math.max(T.z0, z));
    const fx = Math.min(N - 1.001, (cx - T.x0) / T.step), fz = Math.min(N - 1.001, (cz - T.z0) / T.step);
    const i = Math.floor(fx), j = Math.floor(fz), u = fx - i, v = fz - j;
    const k = j * N + i;
    // the same two flat triangles the mesh draws, so feet and tree trunks meet the ground
    const h00 = H[k], h10 = H[k + 1], h01 = H[k + N], h11 = H[k + N + 1];
    const h = u + v <= 1 ? h00 + (h10 - h00) * u + (h01 - h00) * v : h11 + (h01 - h11) * (1 - u) + (h10 - h11) * (1 - v);
    const d = Math.hypot(x - cx, z - cz);
    if (d <= 0) return h;
    // beyond the surveyed square the land rolls away into hills
    const f = Math.exp(-d / 700);
    return h * f + (-25 + hills(x, z)) * (1 - f);
  }

  // The city map arrives a moment later; until then the ground is the only obstacle.
  let tops = null, kinds = null;
  const cmPx = CM.size / CM.n;
  function cmIndex(x, z) {
    const u = Math.floor((x - CM.x0) / cmPx), v = Math.floor((z - CM.z0) / cmPx);
    return u >= 0 && v >= 0 && u < CM.n && v < CM.n ? v * CM.n + u : -1;
  }
  /** Height of whatever stands at (x, z): a roof where there is a building, else the ground. */
  function topAt(x, z) {
    if (onDeck(x, z)) return 0;
    const g = terrainAt(x, z);
    if (!tops) return g;
    const k = cmIndex(x, z);
    return k >= 0 && kinds[k] === 255 ? Math.max(g, tops[k]) : g;
  }
  const kindAt = (x, z) => { if (!kinds) return 0; const k = cmIndex(x, z); return k < 0 ? 0 : kinds[k]; };

  // ---------------------------------------------------------------- terrain mesh
  const cityTex = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1, THREE.RGBAFormat);
  cityTex.needsUpdate = true;
  const maskCv = document.createElement('canvas');
  const MASK = 512;
  maskCv.width = maskCv.height = MASK;
  const mPad = 4;
  const mSize = Math.max(rMaxX - rMinX, rMaxZ - rMinZ) + mPad * 2;
  {
    const c = maskCv.getContext('2d');
    c.fillStyle = '#000'; c.fillRect(0, 0, MASK, MASK);
    c.fillStyle = '#fff';
    c.beginPath();
    ring.forEach(([x, z], i) => {
      const u = ((x - rMinX + mPad) / mSize) * MASK, v = ((z - rMinZ + mPad) / mSize) * MASK;
      if (i) c.lineTo(u, v); else c.moveTo(u, v);
    });
    c.closePath(); c.fill();
  }
  const maskTex = new THREE.CanvasTexture(maskCv);
  maskTex.flipY = false;
  maskTex.colorSpace = THREE.NoColorSpace;
  const siteUniforms = {
    uStoneD: mats.uniforms.uStoneD, uStoneN: mats.uniforms.uStoneN, uBrickD: mats.uniforms.uBrickD, uBrickN: mats.uniforms.uBrickN,
    ...mats.uniforms,
    uCityMap: { value: cityTex },
    uCityRect: { value: new THREE.Vector3(CM.x0, CM.z0, 1 / CM.size) },
    uDeckMask: { value: maskTex },
    uDeckRect: { value: new THREE.Vector3(rMinX - mPad, rMinZ - mPad, 1 / mSize) },
  };
  const SITE_PARS = /* glsl */ `
    uniform sampler2D uCityMap; uniform vec3 uCityRect;
    uniform sampler2D uDeckMask; uniform vec3 uDeckRect;
    float cityKind(vec2 xz){
      vec2 uv = (xz - uCityRect.xy) * uCityRect.z;
      if (uv.x < 0. || uv.x > 1. || uv.y < 0. || uv.y > 1.) return 0.;
      return texture2D(uCityMap, uv).b;
    }`;

  const terrainMat = install(new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.96, metalness: 0 }), {
    uniforms: siteUniforms, sky: false, fragPars: SITE_PARS,
    color: /* glsl */ `
      {
        vec2 duv = (vWPos.xz - uDeckRect.xy) * uDeckRect.z;
        if (duv.x > 0. && duv.x < 1. && duv.y > 0. && duv.y < 1. && texture2D(uDeckMask, duv).r > .5) discard;
        float kind = cityKind(vWPos.xz);
        float urban = smoothstep(.08, .22, kind);
        float lane = smoothstep(.30, .42, kind);
        float px = max(length(fwidth(vWPos.xz)), 1e-4);
        float coarse = fbm(vec3(vWPos.xz * .012, 2.));
        float mid = fbm(vec3(vWPos.xz * .11, 5.));
        float fine = mix(.5, fbm(vWPos * 1.3), 1. - smoothstep(.2, 1.2, px));
        float d2 = mix(.5, fbm(vec3(vWPos.xz * .33, 9.)), 1. - smoothstep(1.5, 9., px));
        float d3 = mix(.5, fbm(vec3(vWPos.xz * .045, 3.)), 1. - smoothstep(12., 60., px));
        vec3 earth = mix(vec3(.42, .33, .22), vec3(.60, .51, .36), coarse);
        vec3 scrub = mix(vec3(.19, .24, .11), vec3(.34, .36, .19), mid);
        // scrub in speckled clumps rather than stains
        float veg = smoothstep(.47, .55, fbm(vec3(vWPos.xz * .06, 7.)) * .55 + d2 * .3 + d3 * .15);
        vec3 c = mix(earth, scrub, veg * .85) * (.8 + .4 * fine) * (.74 + .5 * d2) * (.85 + .3 * d3);
        // limestone terraces follow the contours of the slopes
        float slope = 1. - wN.y;
        float terr = fract(vWPos.y / 3.2 + (d3 - .5) * .8);
        float ledge = smoothstep(.0, .06, terr) * (1. - smoothstep(.06, .22, terr)) * smoothstep(.02, .10, slope) * (1. - smoothstep(20., 90., px));
        c = mix(c, vec3(.62, .57, .46) * (.7 + .5 * d2), ledge * .45 * smoothstep(.35, .6, d3 + (d2 - .5) * .6));
        // bare rock shows through on the steeper slopes
        c = mix(c, vec3(.58, .52, .41) * (.6 + .7 * d2), smoothstep(.12, .34, slope) * .75);
        // inside the city the ground is trodden limestone; the lanes are paved
        c = mix(c, vec3(.56, .50, .40) * (.82 + .3 * fine), urban);
        vec3 ash = ashlar(vWPos.xz, .42, .62);
        float joint = (1. - smoothstep(.0, .012 + px, ash.z)) * (1. - smoothstep(.03, .2, px));
        float worn = fbm(vec3(vWPos.xz * .9, 2.));
        vec3 pave = vec3(.70, .62, .48) * (.8 + .28 * mix(.5, hash21(ash.xy), 1. - smoothstep(.05, .25, px))) * (.86 + .28 * worn) * (1. - .35 * joint);
        { vec3 off; vec3 st = mkStone(vWPos + vec3(ash.x * 1.3, 0., ash.y * 2.1), vec3(0., 1., 0.), 1.9, off); pave *= mix(vec3(1.), st, .55); mkTexN = off * .5 * lane; }
        c = mix(c, pave, lane);
        // lanes lie in the shade of their houses: darker the more walls stand around
        float enc = 0., foot = 0.;
        for (int i = 0; i < 8; i++) { float a = float(i) * .7854; enc += step(.9, cityKind(vWPos.xz + vec2(cos(a), sin(a)) * 3.2)); }
        for (int i = 0; i < 4; i++) { float a = float(i) * 1.5708 + .4; foot += step(.9, cityKind(vWPos.xz + vec2(cos(a), sin(a)) * 1.1)); }
        c *= mix(1., .55, enc / 8. * urban) * mix(1., .8, min(foot, 1.) * urban);
        diffuseColor.rgb = c;
      }`,
  });
  terrainMat.customProgramCacheKey = () => 'mk-terrain';

  {
    // Core grid at the surveyed spacing, then rows that widen toward the horizon.
    const K = 12;
    const axis = (lo) => {
      const a = [];
      let s = T.step, p = lo;
      const before = [];
      for (let k = 0; k < K; k++) { s *= 1.45; p -= s; before.unshift(p); }
      a.push(...before);
      for (let i = 0; i < N; i++) a.push(lo + i * T.step);
      s = T.step; p = lo + (N - 1) * T.step;
      for (let k = 0; k < K; k++) { s *= 1.45; p += s; a.push(p); }
      return a;
    };
    const xs = axis(T.x0), zs = axis(T.z0);
    const M = xs.length;
    const pos = new Float32Array(M * M * 3);
    for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
      const k = (j * M + i) * 3;
      pos[k] = xs[i]; pos[k + 1] = terrainAt(xs[i], zs[j]); pos[k + 2] = zs[j];
    }
    const idx = new Uint32Array((M - 1) * (M - 1) * 6);
    let q = 0;
    for (let j = 0; j < M - 1; j++) for (let i = 0; i < M - 1; i++) {
      const a = j * M + i, b = a + 1, c = a + M, d = c + 1;
      idx[q++] = a; idx[q++] = c; idx[q++] = b; idx[q++] = b; idx[q++] = c; idx[q++] = d;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    g.computeVertexNormals();
    const terrain = new THREE.Mesh(g, terrainMat);
    terrain.receiveShadow = true;
    terrain.frustumCulled = false;
    scene.add(terrain);
  }

  // ---------------------------------------------------------------- deck and parapet
  {
    const contour = ring.map(([x, z]) => new THREE.Vector2(x, z));
    const tris = THREE.ShapeUtils.triangulateShape(contour, []);
    const pos = new Float32Array(ring.length * 3);
    ring.forEach(([x, z], i) => { pos[i * 3] = x; pos[i * 3 + 1] = -0.02; pos[i * 3 + 2] = z; });
    const idx = [];
    for (const [a, b, c] of tris) {
      // face up
      const ux = ring[b][0] - ring[a][0], uz = ring[b][1] - ring[a][1];
      const vx = ring[c][0] - ring[a][0], vz = ring[c][1] - ring[a][1];
      if (uz * vx - ux * vz > 0) idx.push(a, b, c); else idx.push(a, c, b);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(pos.length).map((_, k) => (k % 3 === 1 ? 1 : 0)), 3));
    g.setIndex(idx);
    const deck = new THREE.Mesh(g, mats.ground);
    deck.receiveShadow = true;
    scene.add(deck);
    for (let i = 0; i < idx.length; i += 3) {
      for (let k = 0; k < 3; k++) soup.push(pos[idx[i + k] * 3], 0, pos[idx[i + k] * 3 + 2]);
      soupOid.push(-1);
    }

    // A parapet along the edge. Where the ground outside stands higher than the deck
    // (the north-west, as today) it rises into a retaining wall.
    const parts = [];
    const cx = (rMinX + rMaxX) / 2, cz = (rMinZ + rMaxZ) / 2;
    for (let i = 0; i < ring.length; i++) {
      const [x0, z0] = ring[i], [x1, z1] = ring[(i + 1) % ring.length];
      const len = Math.hypot(x1 - x0, z1 - z0);
      if (len < 0.05) continue;
      const dx = (x1 - x0) / len, dz = (z1 - z0) / len;
      let nx = dz, nz = -dx; // outward normal
      const mx = (x0 + x1) / 2, mz = (z0 + z1) / 2;
      if (nx * (mx - cx) + nz * (mz - cz) < 0) { nx = -nx; nz = -nz; }
      let outside = -1e9;
      for (const t of [0, 0.5, 1]) for (const d of [3, 9]) {
        outside = Math.max(outside, terrainAt(x0 + (x1 - x0) * t + nx * d, z0 + (z1 - z0) * t + nz * d));
      }
      // where the ground falls away the wall goes down to meet it
      let low = 1e9;
      for (const t of [0, 0.5, 1]) for (const d of [1, 4]) low = Math.min(low, terrainAt(x0 + (x1 - x0) * t + nx * d, z0 + (z1 - z0) * t + nz * d));
      if (low < -0.5) {
        const dpt = -low + 3;
        const face = new THREE.BoxGeometry(len + 0.7, dpt, 0.7);
        face.rotateY(Math.atan2(-dz, dx));
        face.translate(mx - nx * 0.2, -dpt / 2, mz - nz * 0.2);
        parts.push(face);
      }
      const h = Math.max(1.15, Math.min(30, outside + 1.15));
      const box = new THREE.BoxGeometry(len + 0.7, h + 0.6, 0.7);
      box.rotateY(Math.atan2(-dz, dx));
      box.translate(mx - nx * 0.2, h / 2 - 0.3, mz - nz * 0.2);
      parts.push(box);
      // collider: a tall thin sheet so nobody steps or hops over the edge
      const top = Math.max(h, 4.5);
      const ax = x0 - nx * 0.55, az = z0 - nz * 0.55, bx = x1 - nx * 0.55, bz = z1 - nz * 0.55;
      soup.push(ax, -0.5, az, bx, -0.5, bz, bx, top, bz, ax, -0.5, az, bx, top, bz, ax, top, az);
      soupOid.push(-3, -3);
    }
    const parapet = new THREE.Mesh(mergeGeometries(parts), wallMat);
    parapet.castShadow = true;
    parapet.receiveShadow = true;
    scene.add(parapet);
  }

  // ---------------------------------------------------------------- trees
  // Cypress, olive and pine on the slopes and at the edges of the city. None on the Mount.
  const treeGroup = new THREE.Group();
  scene.add(treeGroup);
  function plantTrees() {
    treeGroup.clear();
    let seed = 20261110;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const want = quality === 'low' ? 2200 : quality === 'medium' ? 5000 : 8000;
    const spots = { cypress: [], olive: [], pine: [] };
    const grove = (x, z) => 0.5 + 0.5 * Math.sin(x * 0.011 + 1.7) * Math.cos(z * 0.013 - 0.6) + 0.3 * Math.sin(x * 0.037 + z * 0.029);
    let tries = 0, placed = 0;
    while (placed < want && tries++ < want * 30) {
      const x = -1450 + rnd() * 3200, z = -1450 + rnd() * 3200;
      if (x > rMinX - 14 && x < rMaxX + 14 && z > rMinZ - 14 && z < rMaxZ + 14) {
        if (onDeck(x, z) || onDeck(x + 12, z) || onDeck(x - 12, z) || onDeck(x, z + 12) || onDeck(x, z - 12)) continue;
      }
      const kd = kindAt(x, z);
      if (kd >= 100) continue;                   // lane or building
      if (kd === 60 && rnd() > 0.05) continue;   // a rare courtyard tree inside the city
      const east = x > 230;                      // the valley and the slope facing the Mount
      if (rnd() > (east ? 0.35 : 0.12) + grove(x, z) * 0.75) continue;
      const y = terrainAt(x, z);
      const yx = terrainAt(x + 4, z), yz = terrainAt(x, z + 4);
      if (Math.abs(yx - y) > 3.2 || Math.abs(yz - y) > 3.2) continue; // too steep
      const r = rnd();
      const type = kd === 60 ? 'cypress' : east ? (r < 0.62 ? 'olive' : r < 0.84 ? 'cypress' : 'pine') : (r < 0.4 ? 'olive' : r < 0.7 ? 'cypress' : 'pine');
      spots[type].push([x, y, z, 0.7 + rnd() * rnd() * 1.4, rnd() * 6.283, rnd()]);
      placed++;
    }
    const paint = (geo, r, g, b, vary) => {
      const n = geo.attributes.position.count;
      const col = new Float32Array(n * 3);
      const P = geo.attributes.position;
      let lo = 1e9, hi = -1e9;
      for (let i = 0; i < n; i++) { lo = Math.min(lo, P.getY(i)); hi = Math.max(hi, P.getY(i)); }
      for (let i = 0; i < n; i++) {
        const t = 0.72 + 0.4 * ((P.getY(i) - lo) / (hi - lo || 1)) * vary; // darker underneath
        col[i * 3] = r * t; col[i * 3 + 1] = g * t; col[i * 3 + 2] = b * t;
      }
      geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
      return geo;
    };
    const trunk = (h, r) => paint(new THREE.CylinderGeometry(r * 0.7, r, h, 5).translate(0, h / 2, 0), 0.30, 0.24, 0.18, 0);
    const blob = (rx, ry, y, detail) => {
      const g = new THREE.IcosahedronGeometry(1, detail);
      const P = g.attributes.position;
      for (let i = 0; i < P.count; i++) {
        const k = 0.82 + 0.36 * Math.abs(Math.sin(P.getX(i) * 5.1 + P.getY(i) * 3.7 + P.getZ(i) * 4.3));
        P.setXYZ(i, P.getX(i) * rx * k, P.getY(i) * ry * k + y, P.getZ(i) * rx * k);
      }
      g.computeVertexNormals();
      return g;
    };
    const ni = (g) => (g.index ? g.toNonIndexed() : g);
    // a crown is several overlapping clumps, never one ball
    const crown = (n, R, y0, spread, flat, seed0) => {
      const parts = [];
      for (let k = 0; k < n; k++) {
        const a = k * 2.4 + seed0, r = k === 0 ? 0 : spread * (0.45 + 0.55 * ((k * 0.618) % 1));
        const rr = R * (0.55 + 0.35 * ((k * 0.37 + 0.2) % 1));
        parts.push(ni(blob(rr, rr * flat, y0 + ((k * 0.53) % 1) * R * 0.35, 1).translate(Math.cos(a) * r, 0, Math.sin(a) * r)));
      }
      return mergeGeometries(parts);
    };
    // a cypress: a tall narrow flame, widest a third of the way up
    const spire = () => {
      const g = new THREE.CylinderGeometry(0.08, 0.5, 10, 7, 6).translate(0, 5.6, 0);
      const P = g.attributes.position;
      for (let i = 0; i < P.count; i++) {
        const t = (P.getY(i) - 0.6) / 10, w = 1.25 * Math.sin(Math.min(1, t * 1.15 + 0.12) * Math.PI) ** 0.7 + 0.08;
        const l = Math.hypot(P.getX(i), P.getZ(i)) || 1, wob = 1 + 0.18 * Math.sin(P.getY(i) * 2.3 + Math.atan2(P.getZ(i), P.getX(i)) * 3);
        P.setXYZ(i, (P.getX(i) / l) * w * wob, P.getY(i), (P.getZ(i) / l) * w * wob);
      }
      g.computeVertexNormals();
      return g;
    };
    const shapes = {
      cypress: mergeGeometries([trunk(0.9, 0.2), paint(spire(), 0.11, 0.19, 0.10, 1)].map(ni)),
      olive: mergeGeometries([trunk(1.3, 0.42), paint(crown(quality === 'low' ? 3 : 5, 2.5, 2.4, 1.5, 0.62, 0), 0.34, 0.39, 0.28, 1)].map(ni)),
      pine: mergeGeometries([trunk(3.6, 0.3), paint(crown(quality === 'low' ? 3 : 5, 3.1, 5.0, 1.9, 0.42, 1), 0.15, 0.25, 0.13, 1)].map(ni)),
    };
    const mat = new THREE.MeshLambertMaterial({ vertexColors: true });
    const m4 = new THREE.Matrix4(), qt = new THREE.Quaternion(), sc = new THREE.Vector3(), ps = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
    const tint = new THREE.Color();
    for (const [type, list] of Object.entries(spots)) {
      if (!list.length) continue;
      const inst = new THREE.InstancedMesh(shapes[type], mat, list.length);
      list.forEach(([x, y, z, s, a, v], i) => {
        qt.setFromAxisAngle(up, a);
        sc.set(s * (0.85 + v * 0.3), s, s * (0.85 + v * 0.3));
        ps.set(x, y - 0.45, z);
        m4.compose(ps, qt, sc);
        inst.setMatrixAt(i, m4);
        { const b = 0.72 + v * 0.42, hsh = ((v * 7.3) % 1) - 0.5; inst.setColorAt(i, tint.setRGB(b * (1 + hsh * 0.14), b, b * (1 - hsh * 0.2))); }
      });
      inst.frustumCulled = false;
      treeGroup.add(inst);
    }
    return placed;
  }
  plantTrees();

  // ---------------------------------------------------------------- the city
  const cityMat = install(new THREE.MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.94, metalness: 0, side: THREE.DoubleSide }), {
    uniforms: siteUniforms, sky: false,
    color: /* glsl */ `
      {
        float ao = diffuseColor.r;
        float plain = diffuseColor.g; // 1 on rebuilt walls and roofs: no openings there
        vec3 gn = normalize(cross(dFdx(vWPos), dFdy(vWPos)));
        float roofness = smoothstep(.55, .85, gn.y);
        vec2 blk = floor(vWPos.xz / 9.);
        float t1 = hash21(blk), t2 = hash21(blk + 7.3);
        float big = fbm(vec3(vWPos.xz * .01, 4.));
        float px = max(length(fwidth(vWPos)), 1e-4);
        float grain = mix(.5, fbm(vWPos * 1.9), 1. - smoothstep(.15, .9, px));
        float tone = diffuseColor.b; // one value per rebuilt house; .5 on the trim shells
        float th = mix(t1, tone, plain), tg = mix(t2, fract(tone * 7.31), plain);
        vec3 wall = mix(vec3(.90, .79, .58), vec3(.79, .60, .37), th);
        wall = mix(wall, vec3(.93, .87, .74), smoothstep(.72, 1., tg) * .6);       // newer pale stone
        wall = mix(wall, vec3(.63, .57, .47), (1. - smoothstep(0., .25, tg)) * .5);  // old and weathered grey
        wall *= (.86 + .2 * big) * (.9 + .2 * grain) * mix(1., .88 + .24 * fract(tone * 3.17), plain);
        // coursed ashlar on the walls, visible until the blocks shrink below a pixel
        float wu = vWPos.x * gn.z - vWPos.z * gn.x;
        // real coursed masonry on the walls: every house starts at a different place in the photograph
        vec3 wT = normalize(vec3(gn.z, 0., -gn.x) + 1e-5);
        vec3 bOff; vec3 brick = mkScan(uBrickD, uBrickN, vec3(.454, .362, .242), vec2(wu, vWPos.y) / 3.6 + tone * vec2(7.3, 3.1), wT, vec3(0., 1., 0.), bOff);
        vec3 rOff; vec3 rst = mkStone(vWPos + tone * 40., vec3(0., 1., 0.), 3.1, rOff);
        vec3 ash = ashlar(vec2(wu, vWPos.y + tone * 3.), .36, .62);
        float show = 1. - smoothstep(.03, .14, px);
        wall *= mix(vec3(1.), brick, .85);
        // rain streaks down the walls, and a darker foot where the lane is narrow
        float streak = fbm(vec3(wu * 1.4, vWPos.y * .08, tone * 9.));
        wall *= 1. - .2 * smoothstep(.5, .8, streak) * (1. - roofness);
        vec3 rs = ashlar(vWPos.xz + tone * 5., .6, .6);
        vec3 roof = mix(vec3(.82, .75, .61), vec3(.70, .62, .48), tg) * (.84 + .26 * grain);
        roof *= 1. - .14 * (1. - smoothstep(0., .012 + px, rs.z)) * show;
        roof *= mix(vec3(1.), rst, .5);
        vec3 c = mix(wall, roof, roofness);
        mkTexN = mix(bOff * .7, rOff * .4, roofness);
        // deep recesses are windows and doorways: dark glass and shade
        float opening = smoothstep(.58, .30, ao) * (1. - roofness) * (1. - plain);
        c = mix(c, vec3(.09, .11, .14), opening * .8);
        c *= mix(mix(.42, .72, roofness), 1.06, smoothstep(.12, .95, ao));
        diffuseColor.rgb = c;
      }`,
  });
  cityMat.customProgramCacheKey = () => 'mk-city';

  // Windows and doors are flat panels drawn by the shader: a stone surround, then glass,
  // shutters or a painted door. Red and blue carry the position across the panel; green
  // carries the kind (quarters) and a random number for this opening (the remainder).
  const winMat = install(new THREE.MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.9, metalness: 0 }), {
    uniforms: siteUniforms, sky: false,
    color: /* glsl */ `
      {
        vec2 q = vec2(diffuseColor.r, diffuseColor.b);
        float kindv = diffuseColor.g * 4.;
        float cls = floor(kindv + .02);
        float rnd = clamp(fract(kindv + .02) / .8, 0., 1.);
        bool door = cls > 1.5;
        bool arched = mod(cls, 2.) > .5;
        vec2 sz = door ? vec2(1.2, 2.3) : vec2(1.0, 1.8);
        vec2 p = (q - .5) * sz;
        // distance to the outline: a rectangle, or one with a round head
        vec2 hb = sz * .5;
        float sd;
        if (arched) {
          float r = hb.x;
          vec2 pc = vec2(p.x, max(p.y - (hb.y - r), 0.));
          sd = max(length(pc) - r, max(abs(p.x) - hb.x, -p.y - hb.y));
        } else {
          vec2 d = abs(p) - hb;
          sd = max(d.x, d.y);
        }
        if (sd > 0.) discard;
        float px = max(length(fwidth(p)), 1e-4);
        float inner = sd + (door ? .13 : .10);
        vec3 stoneC = vec3(.86, .80, .66) * (.92 + .16 * rnd);
        vec3 c;
        if (inner > 0.) {
          // the surround, darker where it turns into the reveal
          c = stoneC * mix(.72, 1., smoothstep(0., .05, inner));
        } else {
          float depth = smoothstep(-.10, 0., inner); // shade under the lintel and beside the jambs
          vec3 paint = rnd < .28 ? vec3(.16, .34, .30) : rnd < .5 ? vec3(.17, .33, .50) : rnd < .7 ? vec3(.36, .25, .15) : vec3(.30, .32, .33);
          if (door) {
            float plank = abs(fract(p.x / .2) - .5);
            c = paint * (.85 + .25 * hash21(vec2(floor(p.x / .2), rnd * 91.)));
            c *= 1. - .35 * (1. - smoothstep(.0, .03 + px, plank)) * (1. - smoothstep(.02, .1, px));
            c = mix(c, vec3(.05), step(.93, fract(rnd * 13.)) * .0);
          } else if (fract(rnd * 5.7) < .36) {
            // closed shutters with slats
            float slat = fract((p.y + 2.) / .09);
            c = paint * (.75 + .3 * smoothstep(.0, .6, slat) * (1. - smoothstep(.01, .06, px)));
            c *= 1. - .5 * (1. - smoothstep(.0, .012 + px, abs(p.x)));
          } else {
            // glass, with a dark frame and glazing bars
            vec3 glass = mix(vec3(.05, .07, .10), vec3(.16, .22, .30), smoothstep(-.9, .9, p.y) * (.4 + .6 * fract(rnd * 3.3)));
            float bars = min(abs(p.x), abs(p.y - .25));
            float bar = 1. - smoothstep(.018, .018 + px * 1.5, bars);
            c = mix(glass, paint * .5, bar * (1. - smoothstep(.03, .15, px)));
            mkRough = -.72;
          }
          c *= mix(1., .45, depth);
        }
        diffuseColor.rgb = c;
      }`,
  });
  winMat.customProgramCacheKey = () => 'mk-window';
  {
    // Panels stand a hand's breadth off walls that were rebuilt to the nearest quarter metre,
    // so draw them as if half a metre nearer the eye: they never sink into their own wall.
    const inner = winMat.onBeforeCompile;
    winMat.onBeforeCompile = (shader, r) => {
      inner(shader, r);
      shader.vertexShader = shader.vertexShader.replace('#include <project_vertex>', `#include <project_vertex>
        { float dist = length(mvPosition.xyz); mvPosition.xyz *= 1. - min(.5, dist * .0012) / max(dist, .6); gl_Position = projectionMatrix * mvPosition; }`);
    };
  }

  /** Loads the houses, the retaining skirt and the outer wall. Resolves when they are in the scene. */
  // What stands on the roofs of the Old City today: white water tanks with their solar
  // panels, small stone domes, and planters.
  function roofThings() {
    const g = new THREE.Group();
    const R = siteData.roofs || [];
    const flat = (geo, r, gr, b) => {
      const q = geo.index ? geo.toNonIndexed() : geo;
      const n = q.attributes.position.count, col = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) { col[i * 3] = r; col[i * 3 + 1] = gr; col[i * 3 + 2] = b; }
      q.setAttribute('color', new THREE.BufferAttribute(col, 3));
      q.deleteAttribute('uv');
      return q;
    };
    const leg = (x, z) => flat(new THREE.BoxGeometry(0.06, 0.7, 0.06).translate(x, 0.35, z), 0.35, 0.35, 0.36);
    const shapes = [
      mergeGeometries([
        flat(new THREE.CylinderGeometry(0.42, 0.42, 1.25, 10).rotateZ(Math.PI / 2).translate(0, 1.15, -0.55), 0.93, 0.93, 0.91),
        leg(-0.5, -0.85), leg(0.5, -0.85), leg(-0.5, -0.25), leg(0.5, -0.25),
        flat(new THREE.BoxGeometry(1.9, 0.06, 1.15).rotateX(0.62).translate(0, 0.5, 0.55), 0.07, 0.10, 0.19),
        flat(new THREE.BoxGeometry(1.98, 0.04, 1.23).rotateX(0.62).translate(0, 0.47, 0.55), 0.62, 0.63, 0.65),
      ]),
      mergeGeometries([
        flat(new THREE.CylinderGeometry(1, 1.04, 0.5, 14).translate(0, 0.25, 0), 0.80, 0.74, 0.60),
        flat(new THREE.SphereGeometry(1, 14, 6, 0, Math.PI * 2, 0, Math.PI / 2).scale(1, 0.82, 1).translate(0, 0.5, 0), 0.74, 0.71, 0.63),
      ]),
      mergeGeometries([
        flat(new THREE.BoxGeometry(1.6, 0.4, 0.5).translate(0, 0.2, 0), 0.62, 0.42, 0.30),
        flat(new THREE.IcosahedronGeometry(0.5, 1).scale(1.5, 0.9, 0.7).translate(0, 0.75, 0), 0.24, 0.36, 0.18),
        flat(new THREE.BoxGeometry(0.5, 0.45, 0.5).translate(1.5, 0.22, 0.9), 0.66, 0.46, 0.33),
        flat(new THREE.IcosahedronGeometry(0.45, 1).translate(1.5, 0.8, 0.9), 0.30, 0.40, 0.20),
      ]),
    ];
    const mat = new THREE.MeshLambertMaterial({ vertexColors: true });
    const m4 = new THREE.Matrix4(), qt = new THREE.Quaternion(), sc = new THREE.Vector3(), ps = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
    const step = quality === 'low' ? 2 : 1; // phones get every other one
    for (let kind = 0; kind < 3; kind++) {
      const list = [];
      for (let i = 0; i < R.length; i += 6 * step) if (R[i + 3] === kind) list.push(i);
      if (!list.length) continue;
      const inst = new THREE.InstancedMesh(shapes[kind], mat, list.length);
      list.forEach((i, n) => {
        // tanks all face their panels south; the rest turn freely
        qt.setFromAxisAngle(up, kind === 0 ? (R[i + 4] - 3.14) * 0.12 : R[i + 4]);
        const k = kind === 1 ? Math.min(2.6, R[i + 5] * 0.62) : 0.8 + 0.45 * ((R[i + 4] * 7.13) % 1);
        sc.set(k, k, k);
        ps.set(R[i], R[i + 1], R[i + 2]);
        inst.setMatrixAt(n, m4.compose(ps, qt, sc));
      });
      inst.frustumCulled = false;
      g.add(inst);
    }
    return g;
  }

  async function loadCity() {
    const [img, gltf] = await Promise.all([
      loadImage('assets/citymap.png'),
      new Promise((resolve, reject) => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).load('assets/city.glb', resolve, undefined, reject)),
    ]);
    const cp = pixels(img);
    tops = new Float32Array(CM.n * CM.n);
    kinds = new Uint8Array(CM.n * CM.n);
    for (let k = 0; k < tops.length; k++) {
      tops[k] = CM.lo + ((cp[k * 4] * 256 + cp[k * 4 + 1]) / 65535) * CM.span;
      kinds[k] = cp[k * 4 + 2];
    }
    const tex = new THREE.Texture(img);
    tex.flipY = false;
    tex.colorSpace = THREE.NoColorSpace;
    tex.generateMipmaps = false;
    tex.minFilter = tex.magFilter = THREE.LinearFilter;
    tex.needsUpdate = true;
    siteUniforms.uCityMap.value = tex;

    const group = new THREE.Group();
    gltf.scene.traverse((o) => {
      if (!o.isMesh || o.name === 'deck') return;
      const structural = o.name === 'skirt' || o.name === 'precinctwall';
      if (structural) { o.geometry.deleteAttribute('color'); o.geometry.computeVertexNormals(); }
      const mesh = new THREE.Mesh(o.geometry, structural ? wallMat : o.name.startsWith('win_') ? winMat : cityMat);
      o.updateWorldMatrix(true, false);
      mesh.matrixAutoUpdate = false;
      mesh.matrix.copy(o.matrixWorld);
      mesh.matrixWorld.copy(o.matrixWorld);
      const win = o.name.startsWith('win_');
      // the contact-shading pass reads normals; the panels stay out of it
      if (win) mesh.userData.noAO = true; else if (!structural && quality !== 'low' && !o.geometry.attributes.normal) o.geometry.computeVertexNormals();
      mesh.receiveShadow = true;
      mesh.castShadow = structural || (quality !== 'low' && o.name.startsWith('solid_'));
      if (structural) mesh.frustumCulled = false;
      group.add(mesh);
    });
    group.add(roofThings());
    scene.add(group);
    plantTrees(); // again, now that houses and lanes are known
  }

  return { terrainAt, topAt, onDeck, loadCity };
}
