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
        // distance along the wall. The normal comes from screen derivatives and trembles in its last
        // digits, which hundreds of metres from the origin would smear the masonry sideways: so
        // steady it, and measure from a nearby corner of a 64 m grid instead of from the origin.
        vec2 gh = floor(gn.xz * 96. + .5) / 96.;
        gh /= max(length(gh), 1e-4);
        vec2 lp = vWPos.xz - floor(vWPos.xz / 64.) * 64.;
        float wu = lp.x * gh.y - lp.y * gh.x;
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
          // doors keep the lower half of the random number for paint; the upper half marks a door
          // standing open, in eight steps: its paint, and whether the leaf shows inside the doorway
          bool open = door && rnd > .49;
          float ok = floor(clamp((rnd - .525) * 16. + .25, 0., 7.9));
          float ps = door ? (open ? (mod(ok, 4.) + .5) * .25 : rnd / .47) : rnd;
          vec3 paint = ps < .28 ? vec3(.16, .34, .30) : ps < .5 ? vec3(.17, .33, .50) : ps < .7 ? vec3(.36, .25, .15) : vec3(.30, .32, .33);
          if (door) {
            float plank = abs(fract(p.x / .2) - .5);
            c = paint * (.85 + .25 * hash21(vec2(floor(p.x / .2), rnd * 91.)));
            c *= 1. - .35 * (1. - smoothstep(.0, .03 + px, plank)) * (1. - smoothstep(.02, .1, px));
            if (open) {
              // a dark room, its floor catching daylight at the threshold
              float fl = 1. - smoothstep(-hb.y + .13, -hb.y + .75, p.y);
              vec3 room = mix(vec3(.030, .026, .024), vec3(.26, .22, .17), fl * fl);
              room += vec3(.05, .035, .02) * smoothstep(.5, .0, length(p - vec2(.1, .25))); // something lit, far inside
              if (ok < 3.5) {
                // the leaf swung in on its hinge: a narrowed, shaded strip of it shows at one jamb
                float side = mod(ok, 2.) < .5 ? -1. : 1.;
                float fromHinge = (p.x * side + hb.x - .13);
                float wv = mix(.3, .62, fract(ok * .37 + .2)) * (sz.x - .26);
                float top = hb.y - .13 - fromHinge * .22;
                if (fromHinge < wv && p.y < top) room = c * mix(.62, .38, fromHinge / wv);
              }
              c = room;
            }
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

  // Life in the lanes, as the Jewish Quarter has it today: plants in clay pots, cloth awnings,
  // bicycles against the walls, parked cars where a lane is wide enough, crates, chairs, the odd
  // bin and bags outside an overflowing garbage room,
  // lanterns, drainpipes, cables, air conditioners, window boxes, flags, doors left open, cats.
  // Each thing is eight numbers: x, y, z, kind, turn, random, and two sizes.
  function streetThings() {
    const g = new THREE.Group();
    const R = siteData.street || [];
    const N = 8;
    const tintable = (geo, r, gr, b) => {
      const q = geo.index ? geo.toNonIndexed() : geo;
      const n = q.attributes.position.count, col = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) { col[i * 3] = r; col[i * 3 + 1] = gr; col[i * 3 + 2] = b; }
      q.setAttribute('color', new THREE.BufferAttribute(col, 3));
      q.deleteAttribute('uv');
      return q;
    };
    const box = (w, h, d, x, y, z, c) => tintable(new THREE.BoxGeometry(w, h, d).translate(x, y, z), c[0], c[1], c[2]);
    const yv = new THREE.Vector3(0, 1, 0), va = new THREE.Vector3(), vb = new THREE.Vector3(), tq = new THREE.Quaternion();
    const tube = (p, q, r, c, seg = 5) => {
      va.set(...p); vb.set(...q);
      const len = va.distanceTo(vb);
      tq.setFromUnitVectors(yv, vb.clone().sub(va).normalize());
      return tintable(new THREE.CylinderGeometry(r, r, len, seg).applyQuaternion(tq).translate((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2), c[0], c[1], c[2]);
    };
    const leaf = (x, y, z, r, sx, c = [0.5, 0.66, 0.36]) => {
      const b = new THREE.IcosahedronGeometry(r, 1);
      const P = b.attributes.position;
      for (let i = 0; i < P.count; i++) { const k = 0.8 + 0.4 * Math.abs(Math.sin(P.getX(i) * 9 + P.getY(i) * 7 + P.getZ(i) * 5)); P.setXYZ(i, P.getX(i) * k * sx, P.getY(i) * k, P.getZ(i) * k * sx); }
      return tintable(b.translate(x, y, z), c[0], c[1], c[2]);
    };
    const W = [1, 1, 1], IRON = [0.07, 0.07, 0.08], TYRE = [0.05, 0.05, 0.05], GLASS = [0.04, 0.05, 0.07];
    const chair = (cx, cz, turn, c) => {
      const parts = [box(0.42, 0.04, 0.42, 0, 0.44, 0, c), box(0.42, 0.42, 0.04, 0, 0.68, -0.2, c)];
      for (const [x, z] of [[-0.18, -0.18], [0.18, -0.18], [-0.18, 0.18], [0.18, 0.18]]) parts.push(box(0.04, 0.44, 0.04, x, 0.22, z, c));
      return mergeGeometries(parts).rotateY(turn).translate(cx, 0, cz);
    };
    const wheel = (x, z) => tintable(new THREE.CylinderGeometry(0.31, 0.31, 0.2, 12).rotateX(Math.PI / 2).translate(x, 0.31, z), ...TYRE);
    const carSide = (pts, depth) => {
      const sh = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
      return new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: false }).translate(0, 0, -depth / 2);
    };
    const bikeParts = () => {
      const p = [];
      for (const x of [-0.52, 0.52]) {
        p.push(tintable(new THREE.TorusGeometry(0.33, 0.022, 5, 18).translate(x, 0.35, 0), ...TYRE));
        p.push(tintable(new THREE.TorusGeometry(0.31, 0.006, 3, 12).translate(x, 0.35, 0), 0.6, 0.6, 0.62));
        for (let k = 0; k < 4; k++) { const an = k * Math.PI / 4; p.push(tube([x - Math.cos(an) * 0.31, 0.35 - Math.sin(an) * 0.31, 0], [x + Math.cos(an) * 0.31, 0.35 + Math.sin(an) * 0.31, 0], 0.004, [0.6, 0.6, 0.62], 3)); }
      }
      const Rr = [-0.52, 0.35, 0], B = [-0.08, 0.32, 0], St = [-0.2, 0.82, 0], H = [0.36, 0.86, 0], Hb = [0.41, 0.64, 0], F = [0.52, 0.35, 0];
      for (const [u, v] of [[Rr, B], [B, St], [Rr, St], [St, H], [B, Hb], [H, Hb], [Hb, F]]) p.push(tube(u, v, 0.017, W));
      p.push(tube([-0.215, 0.82, 0], [-0.23, 0.93, 0], 0.012, IRON), box(0.25, 0.045, 0.12, -0.24, 0.95, 0, IRON));
      p.push(tube([0.35, 0.86, 0], [0.33, 1.0, 0], 0.012, IRON), tube([0.33, 1.0, -0.26], [0.33, 1.0, 0.26], 0.012, IRON));
      p.push(tube([-0.08, 0.32, 0.07], [0.02, 0.2, 0.09], 0.01, IRON, 3), box(0.09, 0.02, 0.05, 0.03, 0.2, 0.11, IRON));
      return mergeGeometries(p);
    };
    const flagTex = (() => {
      const c = document.createElement('canvas'); c.width = 128; c.height = 96;
      const x = c.getContext('2d');
      x.fillStyle = '#f4f3ee'; x.fillRect(0, 0, 128, 96);
      x.fillStyle = '#1c43a8'; x.fillRect(0, 10, 128, 13); x.fillRect(0, 73, 128, 13);
      x.strokeStyle = '#1c43a8'; x.lineWidth = 3.4;
      for (const s of [1, -1]) { x.beginPath(); for (let k = 0; k < 3; k++) { const an = -Math.PI / 2 * s + k * 2.0944; x[k ? 'lineTo' : 'moveTo'](64 + Math.cos(an) * 17, 48 + Math.sin(an) * 17); } x.closePath(); x.stroke(); }
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
    })();
    const flagGeo = (() => {
      // a short pole out of the wall and the cloth hanging from it, a little slack
      const cloth = new THREE.PlaneGeometry(0.95, 0.66, 6, 1);
      const P = cloth.attributes.position;
      for (let i = 0; i < P.count; i++) { const u = P.getX(i) / 0.95 + 0.5; P.setXYZ(i, Math.sin(u * 7) * 0.035 * (0.5 - P.getY(i) / 0.66), P.getY(i) - 0.33 + 0.5 * (0.25 + u * 0.95) - u * 0.06, 0.28 + u * 0.9); }
      cloth.computeVertexNormals();
      const q = cloth.toNonIndexed(), n = q.attributes.position.count;
      q.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 3).fill(1), 3));
      const pole = new THREE.CylinderGeometry(0.013, 0.013, 1.42, 5).applyQuaternion(new THREE.Quaternion().setFromUnitVectors(yv, new THREE.Vector3(0, 0.447, 0.894))).translate(0, 0.32, 0.63).toNonIndexed();
      const pn = pole.attributes.position.count;
      pole.setAttribute('color', new THREE.BufferAttribute(new Float32Array(pn * 3).fill(0.75), 3));
      pole.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(pn * 2).fill(0.4), 2));
      return mergeGeometries([q, pole]);
    })();

    // Ground things have their origin on the paving at the wall, with +Z out into the lane.
    const shapes = {
      0: mergeGeometries([
        tintable(new THREE.CylinderGeometry(0.26, 0.18, 0.44, 9).translate(0, 0.22, 0), 1.0, 0.56, 0.36),
        leaf(0, 0.74, 0, 0.3, 1), leaf(0.1, 1.02, 0.04, 0.22, 0.9), leaf(-0.12, 0.92, -0.06, 0.2, 1),
      ]),
      1: mergeGeometries([
        tintable(new THREE.BoxGeometry(1.9, 0.03, 1.25).rotateX(0.42).translate(0, -0.26, 0.56), 1, 1, 1),
        tintable(new THREE.BoxGeometry(1.9, 0.22, 0.02).translate(0, -0.62, 1.13), 0.92, 0.92, 0.92),
        tintable(new THREE.CylinderGeometry(0.015, 0.015, 1.3, 4).rotateX(Math.PI / 2 + 0.42).translate(-0.93, -0.27, 0.56), 0.25, 0.25, 0.25),
        tintable(new THREE.CylinderGeometry(0.015, 0.015, 1.3, 4).rotateX(Math.PI / 2 + 0.42).translate(0.93, -0.27, 0.56), 0.25, 0.25, 0.25),
      ]),
      // a bicycle leaning on the wall
      2: bikeParts().rotateX(-0.2).translate(0, 0, 0.42),
      // a small parked car
      3: mergeGeometries([
        tintable(carSide([[-1.93, 0.42], [-1.97, 0.8], [-1.8, 0.95], [-1.45, 1.42], [0.25, 1.45], [0.95, 0.98], [1.85, 0.86], [1.97, 0.62], [1.95, 0.42]], 1.64), 1, 1, 1),
        tintable(carSide([[-1.95, 0.24], [-1.95, 0.44], [1.97, 0.44], [1.97, 0.24]], 1.66), 0.1, 0.1, 0.11),
        tintable(carSide([[-1.38, 0.98], [-1.3, 1.37], [0.22, 1.39], [0.8, 1.0]], 1.67), ...GLASS),
        tintable(new THREE.BoxGeometry(0.78, 0.02, 1.42).rotateZ(-0.59).translate(0.612, 1.228, 0), ...GLASS),
        tintable(new THREE.BoxGeometry(0.46, 0.02, 1.38).rotateZ(0.93).translate(-1.637, 1.194, 0), ...GLASS),
        tintable(new THREE.BoxGeometry(0.06, 0.42, 1.69).translate(-0.52, 1.18, 0), 0.9, 0.9, 0.9),
        wheel(-1.25, 0.76), wheel(1.25, 0.76), wheel(-1.25, -0.76), wheel(1.25, -0.76),
        box(0.04, 0.13, 0.3, 1.95, 0.7, 0.58, [1.3, 1.3, 1.2]), box(0.04, 0.13, 0.3, 1.95, 0.7, -0.58, [1.3, 1.3, 1.2]),
        box(0.04, 0.14, 0.26, -1.96, 0.82, 0.6, [0.7, 0.05, 0.04]), box(0.04, 0.14, 0.26, -1.96, 0.82, -0.6, [0.7, 0.05, 0.04]),
        box(0.03, 0.11, 0.5, 1.98, 0.5, 0, [1.2, 1.1, 0.4]), box(0.03, 0.11, 0.5, -1.98, 0.52, 0, [1.2, 1.1, 0.4]),
        box(0.07, 0.07, 0.14, 0.85, 1.02, 0.9, TYRE), box(0.07, 0.07, 0.14, 0.85, 1.02, -0.9, TYRE),
      ]),
      // a wheeled rubbish bin
      4: mergeGeometries([
        tintable(new THREE.CylinderGeometry(0.4, 0.33, 0.92, 4).rotateY(Math.PI / 4).translate(0, 0.52, 0), 1, 1, 1),
        box(0.62, 0.07, 0.64, 0, 1.01, 0.02, [0.85, 0.85, 0.85]),
        tintable(new THREE.CylinderGeometry(0.09, 0.09, 0.06, 8).rotateZ(Math.PI / 2).translate(-0.25, 0.09, -0.2), ...TYRE),
        tintable(new THREE.CylinderGeometry(0.09, 0.09, 0.06, 8).rotateZ(Math.PI / 2).translate(0.25, 0.09, -0.2), ...TYRE),
      ]),
      // an iron lantern on a bracket
      5: mergeGeometries([
        box(0.035, 0.035, 0.56, 0, 0.3, 0.28, IRON), tube([0, 0, 0.02], [0, 0.3, 0.36], 0.012, IRON, 4), box(0.1, 0.34, 0.02, 0, 0.16, 0.01, IRON),
        tube([0, 0.3, 0.5], [0, 0.2, 0.5], 0.008, IRON, 3),
        tintable(new THREE.ConeGeometry(0.17, 0.13, 4).rotateY(Math.PI / 4).translate(0, 0.14, 0.5), ...IRON),
        tintable(new THREE.CylinderGeometry(0.125, 0.085, 0.3, 4).rotateY(Math.PI / 4).translate(0, -0.08, 0.5), 1.0, 0.93, 0.7),
        tintable(new THREE.CylinderGeometry(0.09, 0.05, 0.05, 4).rotateY(Math.PI / 4).translate(0, -0.255, 0.5), ...IRON),
      ]),
      // the outdoor half of an air conditioner, with its pipe
      6: mergeGeometries([
        box(0.82, 0.56, 0.3, 0, 0, 0.2, [0.86, 0.86, 0.83]),
        tintable(new THREE.CylinderGeometry(0.21, 0.21, 0.02, 14).rotateX(Math.PI / 2).translate(-0.12, 0, 0.356), 0.2, 0.21, 0.22),
        box(0.04, 0.04, 0.34, -0.3, -0.3, 0.17, IRON), box(0.04, 0.04, 0.34, 0.3, -0.3, 0.17, IRON),
        box(0.035, 1.5, 0.035, 0.47, -0.75, 0.03, [0.8, 0.8, 0.78]),
      ]),
      // a drainpipe, one metre tall until it is stretched to its wall
      7: mergeGeometries([
        tintable(new THREE.CylinderGeometry(0.05, 0.05, 1, 6).translate(0, 0.5, 0.06), 1, 1, 1),
      ]),
      8: mergeGeometries([
        box(1.5, 0.05, 0.4, 0, 0.45, 0.05, [0.5, 0.33, 0.19]), box(1.5, 0.1, 0.04, 0, 0.66, -0.16, [0.5, 0.33, 0.19]), box(1.5, 0.1, 0.04, 0, 0.84, -0.18, [0.5, 0.33, 0.19]),
        box(0.05, 0.9, 0.05, -0.68, 0.45, -0.16, IRON), box(0.05, 0.9, 0.05, 0.68, 0.45, -0.16, IRON), box(0.05, 0.45, 0.05, -0.68, 0.22, 0.22, IRON), box(0.05, 0.45, 0.05, 0.68, 0.22, 0.22, IRON),
      ]),
      // a cafe table and two chairs
      9: mergeGeometries([
        tintable(new THREE.CylinderGeometry(0.36, 0.36, 0.03, 14).translate(0, 0.73, 0), 0.9, 0.9, 0.88),
        tintable(new THREE.CylinderGeometry(0.03, 0.03, 0.72, 6).translate(0, 0.36, 0), ...IRON),
        tintable(new THREE.CylinderGeometry(0.22, 0.24, 0.03, 10).translate(0, 0.015, 0), ...IRON),
        chair(-0.68, 0.05, 1.45, [0.55, 0.36, 0.2]), chair(0.62, -0.2, -1.9, [0.55, 0.36, 0.2]),
      ]),
      // crates and a carton, as left outside a shop
      10: mergeGeometries([
        box(0.55, 0.3, 0.38, 0, 0.15, 0, [0.72, 0.13, 0.1]), box(0.55, 0.3, 0.38, 0.02, 0.46, 0.01, [0.14, 0.3, 0.62]),
        tintable(new THREE.BoxGeometry(0.46, 0.4, 0.36).rotateY(0.3).translate(0.62, 0.2, 0.06), 0.66, 0.53, 0.36),
        box(0.5, 0.02, 0.33, 0.02, 0.6, 0.01, [0.75, 0.6, 0.2]),
      ]),
      // a window box in flower
      11: mergeGeometries([
        box(0.95, 0.17, 0.22, 0, -0.08, 0.13, [0.6, 0.36, 0.25]),
        leaf(-0.28, 0.1, 0.14, 0.17, 1), leaf(0.05, 0.13, 0.15, 0.19, 1), leaf(0.32, 0.09, 0.14, 0.16, 1),
        leaf(-0.2, 0.2, 0.2, 0.06, 1, [1.25, 0.2, 0.25]), leaf(0.12, 0.25, 0.2, 0.06, 1, [1.25, 0.3, 0.5]), leaf(0.33, 0.19, 0.19, 0.05, 1, [1.25, 0.2, 0.25]), leaf(-0.02, 0.07, 0.25, 0.05, 1, [1.3, 0.5, 0.6]),
      ]),
      // a door leaf, hinged at its origin
      12: mergeGeometries([
        box(1, 1, 0.05, 0.5, 0.5, 0, W), box(0.94, 0.03, 0.07, 0.5, 0.3, 0, [0.7, 0.7, 0.7]), box(0.94, 0.03, 0.07, 0.5, 0.7, 0, [0.7, 0.7, 0.7]),
        box(0.035, 0.07, 0.11, 0.9, 0.47, 0, [0.5, 0.42, 0.2]),
      ]),
      // a run of cable along the wall, one metre long until stretched
      13: mergeGeometries([box(1, 0.022, 0.022, 0, 0, 0.03, IRON), box(1, 0.016, 0.016, 0, -0.07, 0.025, IRON)]),
      14: flagGeo,
      // a cat, sitting
      15: mergeGeometries([
        tintable(new THREE.SphereGeometry(1, 8, 6).scale(0.1, 0.15, 0.13).translate(0, 0.14, 0), 1, 1, 1),
        tintable(new THREE.SphereGeometry(0.072, 8, 6).translate(0, 0.32, 0.07), 1, 1, 1),
        tintable(new THREE.ConeGeometry(0.03, 0.06, 4).translate(-0.04, 0.4, 0.07), 1, 1, 1), tintable(new THREE.ConeGeometry(0.03, 0.06, 4).translate(0.04, 0.4, 0.07), 1, 1, 1),
        tube([0.02, 0.03, -0.1], [0.2, 0.03, 0.0], 0.02, W, 4),
      ]),
      // a white plastic chair
      16: chair(0, 0, 0, [0.9, 0.9, 0.88]),
      // rubbish bags, where a garbage room has overflowed
      17: mergeGeometries([
        leaf(0, 0.2, 0, 0.3, 1.15, [0.05, 0.05, 0.06]), leaf(0.42, 0.17, 0.12, 0.25, 1.1, [0.07, 0.07, 0.08]), leaf(0.16, 0.42, 0.06, 0.2, 1.1, [0.05, 0.05, 0.06]),
        leaf(-0.36, 0.14, 0.2, 0.2, 1.1, [0.78, 0.78, 0.74]), box(0.4, 0.26, 0.3, 0.2, 0.13, -0.38, [0.6, 0.48, 0.32]),
      ]),
    };
    const P = (...hex) => hex.map((h) => new THREE.Color(h));
    const palette = {
      1: P(0x8c211a, 0x1f4d33, 0x243d6b, 0xb88c40, 0xccc2a8),
      2: P(0x1b1b1d, 0xb5352a, 0x2a5fa8, 0xd8d8d2, 0x2e7d4f, 0xd9a21b),
      3: P(0xe9e9e6, 0xe9e9e6, 0xb9bcc0, 0x8d9197, 0x2b2d31, 0x27406e, 0x8a1f1c, 0x6f7a6a),
      4: P(0x1c5230, 0x1c5230, 0x2f4f3a, 0x55585c, 0x234f80),
      7: P(0xcfcfc9, 0x8f8f8c, 0x3b3b3b, 0xcfcfc9),
      12: P(0x29574d, 0x2b547f, 0x5c4026, 0x4d5254),
      15: P(0xc97a2b, 0x1c1c1c, 0x8a8782, 0xe8e4dc, 0x6b5a48),
    };
    const ground = new Set([0, 2, 3, 4, 8, 9, 10, 15, 16, 17]);
    const lambert = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide });
    const paintwork = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.32, metalness: 0.35 });
    const flagMat = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide, map: flagTex });
    const m4 = new THREE.Matrix4(), qt = new THREE.Quaternion(), sc = new THREE.Vector3(), ps = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
    const tint = new THREE.Color();
    const low = quality === 'low';
    // one batch per kind per 220 m square, so squares out of sight cost nothing
    const groups = new Map();
    for (let i = 0, n = 0; i < R.length; i += N, n++) {
      const kind = R[i + 3];
      if (!shapes[kind]) continue;
      if (low && kind > 1 && kind !== 3 && kind !== 12 && n % 2) continue; // phones get every other small thing
      const key = kind + ':' + Math.floor(R[i] / 220) + ':' + Math.floor(R[i + 2] / 220);
      let L = groups.get(key);
      if (!L) groups.set(key, (L = []));
      L.push(i);
    }
    for (const [key, list] of groups) {
      const kind = +key.split(':')[0];
      const inst = new THREE.InstancedMesh(shapes[kind], kind === 3 ? paintwork : kind === 14 ? flagMat : lambert, list.length);
      list.forEach((i, n) => {
        const r = R[i + 5], r2 = (r * 7.31) % 1, p1 = R[i + 6], p2 = R[i + 7];
        qt.setFromAxisAngle(up, kind === 0 ? r * 6.28 : R[i + 4]);
        sc.set(1, 1, 1);
        if (kind === 0) { const k = 0.8 + r * 0.9; sc.set(k, k * (0.9 + r2 * 0.5), k); }
        else if (kind === 2) sc.set(p1 < 0 ? -1 : 1, 0.94 + r2 * 0.12, 1);
        else if (kind === 3) sc.set(0.94 + r2 * 0.14, 0.95 + ((r * 3.7) % 1) * 0.12, 1);
        else if (kind === 4) { const k = 0.85 + r2 * 0.4; sc.set(k, k, k); }
        else if (kind === 7) sc.set(1, p1, 1);
        else if (kind === 12) sc.set(p1, p2, 1);
        else if (kind === 13) sc.set(p1, 1, 1);
        else if (kind === 15) { const k = 0.9 + r2 * 0.35; sc.set(k, k, k); }
        ps.set(R[i], ground.has(kind) ? terrainAt(R[i], R[i + 2]) - 0.03 : R[i + 1], R[i + 2]);
        inst.setMatrixAt(n, m4.compose(ps, qt, sc));
        const pal = palette[kind];
        if (kind === 12) tint.copy(pal[r < 0.28 ? 0 : r < 0.5 ? 1 : r < 0.7 ? 2 : 3]);
        else if (pal) tint.copy(pal[Math.floor(r * pal.length) % pal.length]);
        else tint.setScalar(kind === 0 ? 0.75 + ((r * 3.3) % 1) * 0.4 : 0.86 + r2 * 0.22);
        inst.setColorAt(n, tint);
      });
      inst.computeBoundingSphere();
      inst.castShadow = !low && kind !== 13 && kind !== 7;
      inst.receiveShadow = kind === 3;
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
      if (win) mesh.userData.noAO = true;
      mesh.receiveShadow = true;
      mesh.castShadow = structural || (quality !== 'low' && o.name.startsWith('solid_'));
      if (structural) mesh.frustumCulled = false;
      group.add(mesh);
    });
    group.add(roofThings());
    group.add(streetThings());
    scene.add(group);
    plantTrees(); // again, now that houses and lanes are known
  }

  return { terrainAt, topAt, onDeck, loadCity };
}
