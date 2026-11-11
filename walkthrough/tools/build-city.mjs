// Converts the present-day surroundings of the Mount into compact browser files:
//   public/assets/city.glb     the Old City building shells, simplified, with baked shading
//   public/assets/terrain.png  ground height (16 bit in red+green) on a 12.5 m grid
//   public/assets/citymap.png  1.37 m raster over the city: top height (red+green), kind (blue)
//   src/data/site.json         the Mount platform outline, retaining skirt, stepped precinct wall
//
// Sources, all already in world centimetres with the Temple court at the origin:
//   context-review/OldCityFacadesV1/obj   building shells (OSM footprints plus authored detail)
//   context-review/OldCityFoundationV2    footings that close the gap under buildings on slopes
//   context-review/OldCityStreetsV1/obj   lane surfaces: used for ground heights and the lane mask
//   FutureMountV1/terrain-generated       the four real terrain tiles around the Mount
//   FutureMountV1/mount-platform-*.obj    the platform deck and its retaining skirt
//   FutureMountV1/EnclosureV1             the 3000-amot wall, stepped over the real ground
//
// three.js frame: +X east, +Y up, +Z south, metres.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { MeshBVH } from 'three-mesh-bvh';
import { Document, NodeIO } from '@gltf-transform/core';
import { EXTMeshoptCompression, KHRMeshQuantization } from '@gltf-transform/extensions';
import { quantize, reorder, prune } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer';

const here = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.resolve(here, '../../unreal/MikdashCourtyardV3/SourceAssets');
const OUT_ASSETS = path.resolve(here, '../public/assets');
const OUT_DATA = path.resolve(here, '../src/data');
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^﻿/, ''));
const ONLY = process.env.CITY_ONLY ? process.env.CITY_ONLY.split(',') : null; // debugging: a few cells
const FAST = !!process.env.CITY_FAST; // rasters and terrain only; keep the existing city.glb
await MeshoptEncoder.ready;
await MeshoptSimplifier.ready;

// ---------------------------------------------------------------- OBJ reading
/** Reads a "legacy adapter" OBJ (Y reflected, winding reversed) into three.js metres. */
function readAdapterObj(file, { metres = false } = {}) {
  const text = fs.readFileSync(file, 'latin1');
  const pos = [];
  const idx = [];
  let p = 0;
  const n = text.length;
  while (p < n) {
    let e = text.indexOf('\n', p);
    if (e < 0) e = n;
    const c0 = text.charCodeAt(p), c1 = text.charCodeAt(p + 1);
    if (c0 === 118 && c1 === 32) { // "v "
      const parts = text.slice(p + 2, e).trim().split(/\s+/);
      const x = +parts[0], y = +parts[1], z = +parts[2];
      if (metres) pos.push(x, z, -y);           // Blender metres: east, north, up
      else pos.push(x / 100, z / 100, -y / 100); // adapter cm: UE y = -objY, three z = UE y
    } else if (c0 === 102 && c1 === 32) { // "f "
      const parts = text.slice(p + 2, e).trim().split(/\s+/);
      const a = parseInt(parts[0], 10) - 1;
      for (let k = 1; k + 1 < parts.length; k++) {
        idx.push(a, parseInt(parts[k], 10) - 1, parseInt(parts[k + 1], 10) - 1);
      }
    }
    p = e + 1;
  }
  return { pos: new Float32Array(pos), idx: new Uint32Array(idx) };
}

/** Merges vertices that share a position (to the centimetre) and drops collapsed triangles. */
function weldPositions(pos, idx) {
  const map = new Map();
  const remap = new Uint32Array(pos.length / 3);
  const out = [];
  for (let i = 0; i < remap.length; i++) {
    const key = `${Math.round(pos[i * 3] * 100)},${Math.round(pos[i * 3 + 1] * 100)},${Math.round(pos[i * 3 + 2] * 100)}`;
    let j = map.get(key);
    if (j === undefined) { j = out.length / 3; map.set(key, j); out.push(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]); }
    remap[i] = j;
  }
  const tri = [];
  for (let i = 0; i < idx.length; i += 3) {
    const a = remap[idx[i]], b = remap[idx[i + 1]], c = remap[idx[i + 2]];
    if (a !== b && b !== c && a !== c) tri.push(a, b, c);
  }
  return { pos: new Float32Array(out), idx: new Uint32Array(tri) };
}

/** Makes triangles face outward: the source winding is reversed for a left-handed engine. */
function fixWinding(pos, idx) {
  // Signed volume is positive for outward-facing closed shells.
  let vol = 0;
  for (let i = 0; i < idx.length; i += 3) {
    const a = idx[i] * 3, b = idx[i + 1] * 3, c = idx[i + 2] * 3;
    vol += pos[a] * (pos[b + 1] * pos[c + 2] - pos[b + 2] * pos[c + 1])
      - pos[a + 1] * (pos[b] * pos[c + 2] - pos[b + 2] * pos[c])
      + pos[a + 2] * (pos[b] * pos[c + 1] - pos[b + 1] * pos[c]);
  }
  if (vol < 0) for (let i = 0; i < idx.length; i += 3) { const t = idx[i + 1]; idx[i + 1] = idx[i + 2]; idx[i + 2] = t; }
  return vol;
}

function vertexNormals(pos, idx) {
  const nor = new Float32Array(pos.length);
  for (let i = 0; i < idx.length; i += 3) {
    const a = idx[i] * 3, b = idx[i + 1] * 3, c = idx[i + 2] * 3;
    const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2];
    const vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    for (const k of [a, b, c]) { nor[k] += nx; nor[k + 1] += ny; nor[k + 2] += nz; }
  }
  for (let i = 0; i < nor.length; i += 3) {
    const l = Math.hypot(nor[i], nor[i + 1], nor[i + 2]) || 1;
    nor[i] /= l; nor[i + 1] /= l; nor[i + 2] /= l;
  }
  return nor;
}

// Fixed, well-spread directions on the upper hemisphere (cosine weighted).
const AO_DIRS = (() => {
  const out = [];
  const N = 14;
  for (let i = 0; i < N; i++) {
    const u = (i + 0.5) / N, phi = i * 2.399963;
    const r = Math.sqrt(u), z = Math.sqrt(1 - u);
    out.push([r * Math.cos(phi), r * Math.sin(phi), z]);
  }
  return out;
})();

/** Ambient occlusion per vertex: how much of the sky dome nearby geometry hides. */
function bakeAO(pos, idx, nor) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  const bvh = new MeshBVH(g);
  const ray = new THREE.Ray();
  const ao = new Float32Array(pos.length / 3);
  const t = new THREE.Vector3(), b = new THREE.Vector3(), nrm = new THREE.Vector3();
  for (let i = 0; i < ao.length; i++) {
    nrm.set(nor[i * 3], nor[i * 3 + 1], nor[i * 3 + 2]);
    if (Math.abs(nrm.y) < 0.9) t.set(0, 1, 0); else t.set(1, 0, 0);
    t.cross(nrm).normalize(); b.crossVectors(nrm, t);
    ray.origin.set(pos[i * 3] + nrm.x * 0.06, pos[i * 3 + 1] + nrm.y * 0.06, pos[i * 3 + 2] + nrm.z * 0.06);
    let open = 0;
    for (const d of AO_DIRS) {
      ray.direction.set(
        t.x * d[0] + b.x * d[1] + nrm.x * d[2],
        t.y * d[0] + b.y * d[1] + nrm.y * d[2],
        t.z * d[0] + b.z * d[1] + nrm.z * d[2]);
      const hit = bvh.raycastFirst(ray, THREE.DoubleSide, 0.02, 7);
      open += hit ? Math.min(1, hit.distance / 7) * 0.6 : 1;
    }
    ao[i] = open / AO_DIRS.length;
  }
  return ao;
}

// ---------------------------------------------------------------- city shells
const facDir = path.join(SRC, 'context-review/OldCityFacadesV1/obj');
const fndDir = path.join(SRC, 'context-review/OldCityFoundationV2/obj');
const cells = new Map(); // "N002_N004" -> [files]
for (const f of fs.readdirSync(facDir)) {
  const m = f.match(/_Grid_([NP]\d+_[NP]\d+)\.obj$/);
  if (!m) continue;
  if (ONLY && !ONLY.includes(m[1])) continue;
  if (!cells.has(m[1])) cells.set(m[1], []);
  cells.get(m[1]).push(path.join(facDir, f));
}


const KEEP_TRIM = !!process.env.CITY_TRIM;
const genWin = new Map(); // cell -> { pos, col, idx } openings made with the rebuilt walls
let nGenWin = 0, nGenDoor = 0, nCar = 0, nTrash = 0, nRail = 0, nShop = 0;
const archC = [], roofById = new Map(), bayStat = [0, 0, 0, 0];
const streetItems = []; // eight numbers each: x, y, z, kind, turn, random, and two sizes (see streetThings in src/site.js)
const roofItems = []; // x, y, z, kind, turn, clearance for each thing standing on a roof
const cityMeshes = []; // { name, pos, idx, ao }
const footprints = []; // triangles for rasterising: [pos, idx]
const rooflines = []; // the same, only the pieces that run along a roofline
let triIn = 0, triOut = 0;
const t0 = Date.now();
let nWindows = 0, nDoors = 0, nDropped = 0;
for (const [cell, files] of [...cells].sort()) {
  const P = [], I = [];
  let base = 0;
  for (const f of files) {
    const o = readAdapterObj(f);
    fixWinding(o.pos, o.idx);
    for (let i = 0; i < o.pos.length; i++) P.push(o.pos[i]);
    for (let i = 0; i < o.idx.length; i++) I.push(o.idx[i] + base);
    base += o.pos.length / 3;
  }
  const w = weldPositions(new Float32Array(P), new Uint32Array(I));
  triIn += w.idx.length / 3;
  footprints.push([w.pos, w.idx]);

  // Every detail is its own closed piece. Sort the pieces by what they are.
  const nV = w.pos.length / 3;
  const par = new Uint32Array(nV);
  for (let i = 0; i < nV; i++) par[i] = i;
  const find = (a) => { while (par[a] !== a) { par[a] = par[par[a]]; a = par[a]; } return a; };
  for (let i = 0; i < w.idx.length; i += 3) {
    const a = find(w.idx[i]); par[find(w.idx[i + 1])] = a; par[find(w.idx[i + 2])] = a;
  }
  const comps = new Map();
  for (let i = 0; i < w.idx.length; i += 3) {
    const r = find(w.idx[i]);
    let c = comps.get(r);
    if (!c) { c = { tris: [], min: [1e9, 1e9, 1e9], max: [-1e9, -1e9, -1e9] }; comps.set(r, c); }
    c.tris.push(i);
    for (let k = 0; k < 3; k++) for (let d = 0; d < 3; d++) {
      const v = w.pos[w.idx[i + k] * 3 + d];
      if (v < c.min[d]) c.min[d] = v; if (v > c.max[d]) c.max[d] = v;
    }
  }
  let ccx = 0, ccz = 0;
  for (let i = 0; i < w.pos.length; i += 3) { ccx += w.pos[i]; ccz += w.pos[i + 2]; }
  ccx /= nV; ccz /= nV;
  const near = Math.hypot(Math.max(-215 - ccx, 0, ccx - 150), Math.max(-262 - ccz, 0, ccz - 254)) < 140;

  // long pieces (cornices, parapets, roof slabs) trace the roofline of a house
  {
    const rIdx = [];
    for (const c of comps.values()) {
      if (Math.max(c.max[0] - c.min[0], c.max[2] - c.min[2]) > 2.6) for (const t of c.tris) rIdx.push(w.idx[t], w.idx[t + 1], w.idx[t + 2]);
    }
    rooflines.push([w.pos, new Uint32Array(rIdx)]);
  }
  // The shells' loose detail (cornices, corner stones, window frames) no longer lines up with
  // the rebuilt walls, so none of it is kept: parapets and openings are made with the walls.
  if (FAST || !KEEP_TRIM) continue;
  const keepIdx = [];
  const wp = [], wc = [], wi = []; // openings: one quad each
  for (const c of comps.values()) {
    const n = c.tris.length;
    const h = c.max[1] - c.min[1], wd = Math.max(c.max[0] - c.min[0], c.max[2] - c.min[2]);
    if (n >= 28 && n <= 64 && h > 1.4 && h < 2.7 && wd > 0.5 && wd < 1.7) {
      // a window or a door: find the wall plane from its largest upright face
      let best = 0, nx = 1, nz = 0;
      for (const t of c.tris) {
        const a = w.idx[t] * 3, b = w.idx[t + 1] * 3, d = w.idx[t + 2] * 3;
        const ux = w.pos[b] - w.pos[a], uy = w.pos[b + 1] - w.pos[a + 1], uz = w.pos[b + 2] - w.pos[a + 2];
        const vx = w.pos[d] - w.pos[a], vy = w.pos[d + 1] - w.pos[a + 1], vz = w.pos[d + 2] - w.pos[a + 2];
        const fx = uy * vz - uz * vy, fy = uz * vx - ux * vz, fz = ux * vy - uy * vx;
        const ar = Math.hypot(fx, fy, fz);
        if (Math.abs(fy) < ar * 0.2 && ar > best) { best = ar; const l = Math.hypot(fx, fz); nx = fx / l; nz = fz / l; }
      }
      const tx = -nz, tz = nx;
      let u0 = 1e9, u1 = -1e9, d1 = -1e9;
      for (const t of c.tris) for (let k = 0; k < 3; k++) {
        const a = w.idx[t + k] * 3;
        const u = w.pos[a] * tx + w.pos[a + 2] * tz, d = w.pos[a] * nx + w.pos[a + 2] * nz;
        if (u < u0) u0 = u; if (u > u1) u1 = u; if (d > d1) d1 = d;
      }
      const door = h > 2.05;
      const arched = n >= 40;
      const rnd = ((Math.round(c.min[0] * 37 + c.min[2] * 91 + c.min[1] * 13) * 2654435761) >>> 0) / 4294967296;
      const cls = ((door ? 2 : 0) + (arched ? 1 : 0)) * 0.25 + rnd * 0.2; // class in quarters, a random in between
      const d = d1 + 0.02;
      const q0 = wp.length / 3;
      const corner = (u, y) => wp.push(tx * u + nx * d, y, tz * u + nz * d);
      corner(u0, c.min[1]); corner(u1, c.min[1]); corner(u1, c.max[1]); corner(u0, c.max[1]);
      wc.push(0, cls, 0, 1, cls, 0, 1, cls, 1, 0, cls, 1);
      // face outward: (u1-u0) x up must point along n
      // tangent x up = (tx,0,tz) x (0,1,0) = (-tz, 0, tx) = (-nx, 0, -nz): flip the order
      wi.push(q0, q0 + 2, q0 + 1, q0, q0 + 3, q0 + 2);
      if (door) nDoors++; else nWindows++;
      continue;
    }
    // corner stones and sills are too small to matter away from the Mount
    if (!near && n <= 12 && h < 0.9 && wd < 1.8) { nDropped++; continue; }
    // of the three cornice mouldings only the parapet band reads from a distance
    if (!near && h < 0.4 && wd > 2.6) { nDropped++; continue; }
    for (const t of c.tris) keepIdx.push(w.idx[t], w.idx[t + 1], w.idx[t + 2]);
  }
  if (wi.length) cityMeshes.push({ name: `win_${cell}`, pos: new Float32Array(wp), idx: new Uint32Array(wi), col: new Float32Array(wc) });

  // cornices, parapets, domes, tanks, stair heads: keep, lightly simplified, with baked shading
  const kIdx = new Uint32Array(keepIdx);
  const [sIdx] = MeshoptSimplifier.simplify(kIdx, w.pos, 3, Math.floor((kIdx.length / 3) * (near ? 0.8 : 0.5)) * 3, near ? 0.03 : 0.08, ['ErrorAbsolute']);
  const used = new Map();
  const cp = [];
  const ci = new Uint32Array(sIdx.length);
  for (let i = 0; i < sIdx.length; i++) {
    let j = used.get(sIdx[i]);
    if (j === undefined) { j = cp.length / 3; used.set(sIdx[i], j); cp.push(w.pos[sIdx[i] * 3], w.pos[sIdx[i] * 3 + 1], w.pos[sIdx[i] * 3 + 2]); }
    ci[i] = j;
  }
  const tpos = new Float32Array(cp);
  const ao = bakeAO(tpos, ci, vertexNormals(tpos, ci));
  triOut += ci.length / 3 + wi.length / 3;
  cityMeshes.push({ name: `trim_${cell}`, pos: tpos, idx: ci, ao });
}
console.log(`city detail: ${cells.size} cells, ${triIn} -> ${triOut} triangles (${nWindows} windows, ${nDoors} doors as panels; ${nDropped} small stones dropped) in ${((Date.now() - t0) / 1000).toFixed(0)} s`);


// Footings: plain boxes under buildings on sloping ground. Kept whole, they are cheap.
let fndTris = 0;
if (!ONLY) {
  const P = [], I = [];
  let base = 0;
  for (const f of fs.readdirSync(fndDir).filter((x) => x.endsWith('.obj'))) {
    const o = readAdapterObj(path.join(fndDir, f));
    fixWinding(o.pos, o.idx);
    for (let i = 0; i < o.pos.length; i++) P.push(o.pos[i]);
    for (let i = 0; i < o.idx.length; i++) I.push(o.idx[i] + base);
    base += o.pos.length / 3;
  }
  const w = weldPositions(new Float32Array(P), new Uint32Array(I));
  const ao = new Float32Array(w.pos.length / 3).fill(0.55);
  if (KEEP_TRIM) cityMeshes.push({ name: 'footings', pos: w.pos, idx: w.idx, ao });
  fndTris = w.idx.length / 3;
  console.log(`footings: ${fndTris} triangles`);
}


// ---------------------------------------------------------------- platform, skirt, precinct wall
const fm = path.join(SRC, 'FutureMountV1');
const deck = readAdapterObj(path.join(fm, 'mount-platform-surface.obj'), { metres: true });
const skirt = readAdapterObj(path.join(fm, 'mount-platform-skirt.obj'), { metres: true });
// The deck must face up, the skirt outward (away from the platform centre).
for (let i = 0; i < deck.idx.length; i += 3) {
  const a = deck.idx[i] * 3, b = deck.idx[i + 1] * 3, c = deck.idx[i + 2] * 3;
  const ny = (deck.pos[b + 2] - deck.pos[a + 2]) * (deck.pos[c] - deck.pos[a]) - (deck.pos[b] - deck.pos[a]) * (deck.pos[c + 2] - deck.pos[a + 2]);
  if (ny < 0) { const t = deck.idx[i + 1]; deck.idx[i + 1] = deck.idx[i + 2]; deck.idx[i + 2] = t; }
}
const dw = weldPositions(deck.pos, deck.idx);
// Outline: edges used by exactly one triangle, chained into a ring.
const ring = (() => {
  const count = new Map();
  for (let i = 0; i < dw.idx.length; i += 3) {
    for (let k = 0; k < 3; k++) {
      const a = dw.idx[i + k], b = dw.idx[i + (k + 1) % 3];
      const key = a < b ? `${a},${b}` : `${b},${a}`;
      count.set(key, (count.get(key) || 0) + 1);
    }
  }
  const next = new Map();
  for (let i = 0; i < dw.idx.length; i += 3) {
    for (let k = 0; k < 3; k++) {
      const a = dw.idx[i + k], b = dw.idx[i + (k + 1) % 3];
      const key = a < b ? `${a},${b}` : `${b},${a}`;
      if (count.get(key) === 1) next.set(a, b);
    }
  }
  const start = next.keys().next().value;
  const out = [];
  let cur = start;
  do { out.push([+dw.pos[cur * 3].toFixed(2), +dw.pos[cur * 3 + 2].toFixed(2)]); cur = next.get(cur); } while (cur !== start && cur !== undefined && out.length < 1000);
  return out;
})();
const inRing = (x, z) => {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, zi] = ring[i], [xj, zj] = ring[j];
    if ((zi > z) !== (zj > z) && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) inside = !inside;
  }
  return inside;
};
const cxr = ring.reduce((s, p) => s + p[0], 0) / ring.length, czr = ring.reduce((s, p) => s + p[1], 0) / ring.length;
for (let i = 0; i < skirt.idx.length; i += 3) {
  const a = skirt.idx[i] * 3, b = skirt.idx[i + 1] * 3, c = skirt.idx[i + 2] * 3;
  const P = skirt.pos;
  const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2];
  const vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
  const nx = uy * vz - uz * vy, nz = ux * vy - uy * vx;
  if (nx * (P[a] - cxr) + nz * (P[a + 2] - czr) < 0) { const t = skirt.idx[i + 1]; skirt.idx[i + 1] = skirt.idx[i + 2]; skirt.idx[i + 2] = t; }
}
const flat = (n, v) => new Float32Array(n).fill(v);
cityMeshes.push({ name: 'deck', pos: dw.pos, idx: dw.idx, ao: flat(dw.pos.length / 3, 1) });
cityMeshes.push({ name: 'skirt', pos: skirt.pos, idx: skirt.idx, ao: flat(skirt.pos.length / 3, 1) });
console.log(`platform: ring of ${ring.length} points, deck ${dw.idx.length / 3} + skirt ${skirt.idx.length / 3} triangles`);

const wallSamples = []; // [x, z, groundY]
const placeOf = new Map(readJson(path.join(fm, 'EnclosureV1/enclosure-design.json')).placements.map((q) => [q.mesh, q.location]));
{
  const P = [], I = [];
  let base = 0;
  for (const f of fs.readdirSync(path.join(fm, 'EnclosureV1')).filter((x) => /_(Wall|Gate)_.*\.obj$/.test(x))) {
    const o = readAdapterObj(path.join(fm, 'EnclosureV1', f));
    fixWinding(o.pos, o.idx);
    // these parts are modelled about their own origin; the design file places them
    const loc = placeOf.get(f.replace('.obj', ''));
    if (!loc) throw new Error(`no placement for ${f}`);
    for (let i = 0; i < o.pos.length; i += 3) { o.pos[i] += loc[0] / 100; o.pos[i + 1] += loc[2] / 100; o.pos[i + 2] += loc[1] / 100; }
    for (let i = 0; i < o.pos.length; i++) P.push(o.pos[i]);
    for (let i = 0; i < o.idx.length; i++) I.push(o.idx[i] + base);
    base += o.pos.length / 3;
    if (f.includes('_Wall_')) {
      // each stepped piece: its top is the highest ground under it plus the 3 m wall
      const tops = new Map();
      for (let i = 0; i < o.pos.length; i += 3) {
        const key = `${o.pos[i].toFixed(1)},${o.pos[i + 2].toFixed(1)}`;
        tops.set(key, Math.max(tops.get(key) ?? -1e9, o.pos[i + 1]));
      }
      for (const [key, top] of tops) { const [x, z] = key.split(',').map(Number); wallSamples.push([x, z, top - 3.4]); }
    }
  }
  cityMeshes.push({ name: 'precinctwall', pos: new Float32Array(P), idx: new Uint32Array(I), ao: flat(P.length / 3, 1) });
  console.log(`precinct wall: ${I.length / 3} triangles, ${wallSamples.length} ground samples`);
}

// ---------------------------------------------------------------- terrain
const STEP = 12.5, N = 272;
const X0 = -391.24515625 - 90 * STEP, Z0 = -400.2756640625 - 90 * STEP;
const H = new Float32Array(N * N);
const W = new Float32Array(N * N); // sample weight; 0 = unknown
const hard = new Uint8Array(N * N); // surveyed terrain node: never moved
const node = (x, z) => {
  const i = Math.round((x - X0) / STEP), j = Math.round((z - Z0) / STEP);
  return i >= 0 && j >= 0 && i < N && j < N ? j * N + i : -1;
};
for (const f of fs.readdirSync(path.join(fm, 'terrain-generated')).filter((x) => x.endsWith('.mesh.json'))) {
  const t = readJson(path.join(fm, 'terrain-generated', f));
  for (const [x, y, z] of t.vertices) {
    const k = node(x / 100, y / 100);
    if (k >= 0) { H[k] = z / 100; W[k] = 1; hard[k] = 1; }
  }
}
const surveyed = hard.reduce((s, v) => s + v, 0);
// Lane surfaces give the ground level across the rest of the city.
const laneAcc = new Float32Array(N * N), laneCnt = new Uint32Array(N * N);
const CM = { x0: -1100, z0: -700, size: 1400, n: 1024 };
const cmPx = CM.size / CM.n;
const kind = new Uint8Array(CM.n * CM.n);
const top = new Float32Array(CM.n * CM.n).fill(-1e9);
const stDir = path.join(SRC, 'context-review/OldCityStreetsV1/obj');
/** Marks every map pixel a lane triangle covers. */
function fillTri(sv, a, b, c) {
  const ax = (sv[a * 2] - CM.x0) / cmPx, az = (sv[a * 2 + 1] - CM.z0) / cmPx;
  const bx = (sv[b * 2] - CM.x0) / cmPx, bz = (sv[b * 2 + 1] - CM.z0) / cmPx;
  const cx = (sv[c * 2] - CM.x0) / cmPx, cz = (sv[c * 2 + 1] - CM.z0) / cmPx;
  const u0 = Math.max(0, Math.floor(Math.min(ax, bx, cx))), u1 = Math.min(CM.n - 1, Math.floor(Math.max(ax, bx, cx)));
  const v0 = Math.max(0, Math.floor(Math.min(az, bz, cz))), v1 = Math.min(CM.n - 1, Math.floor(Math.max(az, bz, cz)));
  if (u1 < u0 || v1 < v0) return;
  const area = (bx - ax) * (cz - az) - (cx - ax) * (bz - az);
  if (Math.abs(area) < 1e-9) return;
  for (let v = v0; v <= v1; v++) for (let u = u0; u <= u1; u++) {
    const px = u + 0.5, pz = v + 0.5;
    const w0 = ((bx - px) * (cz - pz) - (cx - px) * (bz - pz)) / area;
    const w1 = ((cx - px) * (az - pz) - (ax - px) * (cz - pz)) / area;
    if (w0 < -0.3 || w1 < -0.3 || 1 - w0 - w1 < -0.3) continue;
    kind[v * CM.n + u] = 110;
  }
}
for (const f of fs.readdirSync(stDir).filter((x) => x.endsWith('.obj'))) {
  const text = fs.readFileSync(path.join(stDir, f), 'latin1');
  const sv = []; // x, z of this file's vertices
  let p = 0;
  while (p < text.length) {
    let e = text.indexOf('\n', p);
    if (e < 0) e = text.length;
    if (text.charCodeAt(p) === 118 && text.charCodeAt(p + 1) === 32) {
      const parts = text.slice(p + 2, e).split(' ');
      const x = +parts[0] / 100, y = +parts[2] / 100, z = -parts[1] / 100;
      const k = node(x, z);
      if (k >= 0) { laneAcc[k] += y; laneCnt[k]++; }
      sv.push(x, z);
    } else if (text.charCodeAt(p) === 102 && text.charCodeAt(p + 1) === 32) {
      const parts = text.slice(p + 2, e).trim().split(/\s+/);
      const a = parseInt(parts[0], 10) - 1;
      for (let q = 1; q + 1 < parts.length; q++) fillTri(sv, a, parseInt(parts[q], 10) - 1, parseInt(parts[q + 1], 10) - 1);
    }
    p = e + 1;
  }
}
let laneNodes = 0;
for (let k = 0; k < N * N; k++) {
  if (!hard[k] && laneCnt[k] >= 4) { H[k] = laneAcc[k] / laneCnt[k]; W[k] = 1; laneNodes++; }
}
for (const [x, z, y] of wallSamples) { const k = node(x, z); if (k >= 0 && !W[k]) { H[k] = y; W[k] = 1; } }
// Fill the gaps smoothly (relaxation), starting from the mean of what is known.
{
  let sum = 0, cnt = 0;
  for (let k = 0; k < N * N; k++) if (W[k]) { sum += H[k]; cnt++; }
  const mean = sum / cnt;
  for (let k = 0; k < N * N; k++) if (!W[k]) H[k] = mean;
  // coarse-to-fine: relax on strided grids first so far gaps converge
  for (const s of [16, 8, 4, 2, 1]) {
    for (let it = 0; it < (s === 1 ? 400 : 300); it++) {
      for (let j = 0; j < N; j += s) for (let i = 0; i < N; i += s) {
        const k = j * N + i;
        if (W[k]) continue;
        let a = 0, c = 0;
        if (i - s >= 0) { a += H[k - s]; c++; }
        if (i + s < N) { a += H[k + s]; c++; }
        if (j - s >= 0) { a += H[k - s * N]; c++; }
        if (j + s < N) { a += H[k + s * N]; c++; }
        H[k] += 1.6 * (a / c - H[k]);
      }
    }
    // spread to the finer nodes before the next level
    if (s > 1) {
      const h = s / 2;
      for (let j = 0; j < N; j += h) for (let i = 0; i < N; i += h) {
        const k = j * N + i;
        if (W[k] || (i % s === 0 && j % s === 0)) continue;
        const i0 = Math.min(N - 1, Math.floor(i / s) * s), j0 = Math.min(N - 1, Math.floor(j / s) * s);
        const i1 = Math.min(N - 1 - ((N - 1) % s), i0 + s), j1 = Math.min(N - 1 - ((N - 1) % s), j0 + s);
        H[k] = (H[j0 * N + i0] + H[j0 * N + i1] + H[j1 * N + i0] + H[j1 * N + i1]) / 4;
      }
    }
  }
}
// Under the deck the ground is cut away; keep it below the paving.
for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
  if (inRing(X0 + i * STEP, Z0 + j * STEP)) H[j * N + i] = Math.min(H[j * N + i], -1.5);
}
// East of the city the ground is cut back so the Mount's wall stands tall above the valley,
// as the eastern wall does today, instead of being buried to its parapet.
{
  const ringDist = (x, z) => {
    let best = 1e18;
    for (let q = 0; q < ring.length; q++) {
      const [ax, az] = ring[q], [bx, bz] = ring[(q + 1) % ring.length];
      const ux = bx - ax, uz = bz - az;
      const t = Math.max(0, Math.min(1, ((x - ax) * ux + (z - az) * uz) / (ux * ux + uz * uz || 1)));
      best = Math.min(best, (x - ax - ux * t) ** 2 + (z - az - uz * t) ** 2);
    }
    return Math.sqrt(best);
  };
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const x = X0 + i * STEP, z = Z0 + j * STEP;
    if (x < 30 || x > 300 || z < -400 || z > 400) continue;
    const rd = ringDist(x, z);
    if (rd > 110) continue;
    const side = Math.min(1, (x - 30) / 60);
    if (inRing(x, z)) { if (rd < 30) H[j * N + i] = Math.min(H[j * N + i], -1.5 - 16.5 * side); continue; }
    const k = (1 - rd / 110) * side, sm = k * k * (3 - 2 * k);
    const cap = -18 + rd * 0.08;
    if (H[j * N + i] > cap) H[j * N + i] += (cap - H[j * N + i]) * Math.min(1, sm * 1.6);
  }
}
let hMin = 1e9, hMax = -1e9;
for (const h of H) { hMin = Math.min(hMin, h); hMax = Math.max(hMax, h); }
console.log(`terrain: ${N}x${N} at ${STEP} m; ${surveyed} surveyed nodes, ${laneNodes} from lanes, ${wallSamples.length} from the wall; ${hMin.toFixed(0)}..${hMax.toFixed(0)} m`);
const terrainAt = (x, z) => {
  const fx = Math.min(N - 1.001, Math.max(0, (x - X0) / STEP)), fz = Math.min(N - 1.001, Math.max(0, (z - Z0) / STEP));
  const i = Math.floor(fx), j = Math.floor(fz), u = fx - i, v = fz - j;
  const k = j * N + i;
  return (H[k] * (1 - u) + H[k + 1] * u) * (1 - v) + (H[k + N] * (1 - u) + H[k + N + 1] * u) * v;
};

function writePng(file, w, h, data) { // RGB8
  const stride = w * 3;
  const raw = Buffer.alloc((stride + 1) * h);
  for (let y = 0; y < h; y++) Buffer.from(data.buffer, data.byteOffset + y * stride, stride).copy(raw, y * (stride + 1) + 1);
  const chunk = (type, body) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(body.length);
    const td = Buffer.concat([Buffer.from(type), body]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(zlib.crc32(td) >>> 0);
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  const out = Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0))]);
  fs.writeFileSync(file, out);
  return out.length;
}
const H_LO = -220, H_SPAN = 400; // metres encoded in 16 bits
const enc = (h) => Math.max(0, Math.min(65535, Math.round(((h - H_LO) / H_SPAN) * 65535)));
{
  const px = new Uint8Array(N * N * 3);
  for (let k = 0; k < N * N; k++) { const e = enc(H[k]); px[k * 3] = e >> 8; px[k * 3 + 1] = e & 255; }
  const bytes = writePng(path.join(OUT_ASSETS, 'terrain.png'), N, N, px);
  console.log(`terrain.png: ${(bytes / 1e3).toFixed(0)} kB`);
}

// ---------------------------------------------------------------- house solids
// The source shells carry only the detail of each house (window surrounds, cornices,
// parapets, domes, tanks); the plain walls and roofs behind them live in engine assets
// this tool cannot read. They are rebuilt here: every outline the parapets enclose is
// traced on a half-metre raster, straightened, and extruded from the ground to its roofline.
const solidTris = { count: 0 };
{
  const FN = 5600, FP = CM.size / FN; // 0.25 m
  const mark = new Uint8Array(FN * FN);
  const ftop = new Float32Array(FN * FN).fill(-1e9);
  const rtop = new Float32Array(FN * FN).fill(-1e9); // roofline pieces only
  let target = ftop;
  const put = (u, v, y) => {
    if (u < 0 || v < 0 || u >= FN || v >= FN) return;
    const k = v * FN + u; mark[k] = 1; if (y > target[k]) target[k] = y;
  };
  const line = (ax, az, ay, bx, bz, by) => {
    const n = Math.max(1, Math.ceil(Math.max(Math.abs(bx - ax), Math.abs(bz - az)) * 2.2));
    if (n > 4000) return;
    for (let i = 0; i <= n; i++) { const t = i / n; put(Math.floor(ax + (bx - ax) * t), Math.floor(az + (bz - az) * t), ay + (by - ay) * t); }
  };
  for (const [list, into] of [[footprints, ftop], [rooflines, rtop]]) for (const [pos, idx] of list) {
    target = into;
    for (let t = 0; t < idx.length; t += 3) {
      const a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
      const ax = (pos[a] - CM.x0) / FP, az = (pos[a + 2] - CM.z0) / FP, ay = pos[a + 1];
      const bx = (pos[b] - CM.x0) / FP, bz = (pos[b + 2] - CM.z0) / FP, by = pos[b + 1];
      const cx = (pos[c] - CM.x0) / FP, cz = (pos[c + 2] - CM.z0) / FP, cy = pos[c + 1];
      line(ax, az, ay, bx, bz, by); line(bx, bz, by, cx, cz, cy); line(cx, cz, cy, ax, az, ay);
      const area = (bx - ax) * (cz - az) - (cx - ax) * (bz - az);
      if (Math.abs(area) < 0.5) continue;
      const u0 = Math.max(0, Math.floor(Math.min(ax, bx, cx))), u1 = Math.min(FN - 1, Math.ceil(Math.max(ax, bx, cx)));
      const v0 = Math.max(0, Math.floor(Math.min(az, bz, cz))), v1 = Math.min(FN - 1, Math.ceil(Math.max(az, bz, cz)));
      for (let v = v0; v <= v1; v++) for (let u = u0; u <= u1; u++) {
        const px = u + 0.5, pz = v + 0.5;
        const w0 = ((bx - px) * (cz - pz) - (cx - px) * (bz - pz)) / area;
        const w1 = ((cx - px) * (az - pz) - (ax - px) * (cz - pz)) / area;
        const w2 = 1 - w0 - w1;
        if (w0 < 0 || w1 < 0 || w2 < 0) continue;
        put(u, v, w0 * ay + w1 * by + w2 * cy);
      }
    }
  }
  // close hairline gaps, then find everything the outlines enclose
  const dil = new Uint8Array(FN * FN);
  for (let v = 1; v < FN - 1; v++) for (let u = 1; u < FN - 1; u++) {
    const k = v * FN + u;
    dil[k] = mark[k] | mark[k - 1] | mark[k + 1] | mark[k - FN] | mark[k + FN] | mark[k - FN - 1] | mark[k - FN + 1] | mark[k + FN - 1] | mark[k + FN + 1];
  }
  const ext = new Uint8Array(FN * FN);
  const stack = new Int32Array(FN * FN);
  let sp = 0;
  const seed = (k) => { if (!dil[k] && !ext[k]) { ext[k] = 1; stack[sp++] = k; } };
  for (let i = 0; i < FN; i++) { seed(i); seed((FN - 1) * FN + i); seed(i * FN); seed(i * FN + FN - 1); }
  while (sp) {
    const k = stack[--sp], u = k % FN, v = (k / FN) | 0;
    if (u > 0) seed(k - 1); if (u < FN - 1) seed(k + 1); if (v > 0) seed(k - FN); if (v < FN - 1) seed(k + FN);
  }
  // roofline height for every built pixel: spread inward from the outline
  const hgt = new Float32Array(FN * FN).fill(NaN);
  const queue = new Int32Array(FN * FN);
  let qh = 0, qt = 0;
  // The roofline of a house is the top of its parapet. Every roofline mark is a source,
  // speaking for the highest roofline point within a metre (so a cornice lip does not pass
  // for the roof), and the height spreads from there across the roof it encloses.
  const band = rtop; // kept under its old name for the debug scan
  for (let v = 5; v < FN - 5; v++) for (let u = 5; u < FN - 5; u++) {
    const k = v * FN + u;
    if (rtop[k] < -1e8 || ext[k]) continue;
    let hi = rtop[k];
    for (let dv = -4; dv <= 4; dv++) for (let du = -4; du <= 4; du++) { const j = k + dv * FN + du; if (rtop[j] > hi) hi = rtop[j]; }
    hgt[k] = hi; queue[qt++] = k;
  }
  while (qh < qt) {
    const k = queue[qh++], u = k % FN, v = (k / FN) | 0;
    for (const d of [-1, 1, -FN, FN]) {
      const j = k + d;
      if ((d === -1 && u === 0) || (d === 1 && u === FN - 1) || (d === -FN && v === 0) || (d === FN && v === FN - 1)) continue;
      if (ext[j] || !Number.isNaN(hgt[j])) continue;
      hgt[j] = hgt[k]; queue[qt++] = j;
    }
  }
  // pull the walls just inside the cornice line so the detail stays in front of them
  const body = new Uint8Array(FN * FN);
  for (let v = 2; v < FN - 2; v++) for (let u = 2; u < FN - 2; u++) {
    const k = v * FN + u;
    if (ext[k] || Number.isNaN(hgt[k])) continue;
    // a lane stays a lane, whatever roof slab the source hung over it
    { const lu = Math.floor((u * FP) / cmPx), lv = Math.floor((v * FP) / cmPx); if (kind[lv * CM.n + lu] === 110) continue; }
    let ok = true;
    for (let dv = -2; dv <= 2 && ok; dv++) for (let du = -2; du <= 2; du++) if (ext[k + dv * FN + du]) { ok = false; break; }
    body[k] = ok ? 1 : 0;
  }
  // regions that share a roofline
  const label = new Int32Array(FN * FN);
  const regions = []; // { pixels: [k...], band }
  for (let k0 = 0; k0 < FN * FN; k0++) {
    if (!body[k0] || label[k0]) continue;
    const id = regions.length + 1;
    const pix = [];
    label[k0] = id; sp = 0; stack[sp++] = k0;
    while (sp) {
      const k = stack[--sp]; pix.push(k);
      for (const d of [-1, 1, -FN, FN]) {
        const j = k + d;
        if (j < 0 || j >= FN * FN || !body[j] || label[j] || Math.abs(hgt[j] - hgt[k]) > 0.3) continue; // one house: one roofline
        label[j] = id; stack[sp++] = j;
      }
    }
    regions.push(pix);
  }
  // fold slivers into a neighbouring region so no holes are left between houses
  for (let pass = 0; pass < 3; pass++) {
    regions.forEach((pix, r) => {
      if (!pix.length) return;
      const votes = new Map();
      let edge = 0;
      for (const k of pix) {
        let onEdge = false;
        for (const d of [-1, 1, -FN, FN]) { const l = label[k + d]; if (l !== r + 1) { onEdge = true; if (l) votes.set(l, (votes.get(l) || 0) + 1); } }
        if (onEdge) edge++;
      }
      // a strip under two metres wide is a cornice band or a gap between roofs, not a house
      const thin = ((2 * pix.length) / Math.max(1, edge)) * FP < 2.0;
      if (pix.length >= 160 && !thin) return;
      let best = 0, bestN = 0;
      for (const [l, n] of votes) if (n > bestN) { best = l; bestN = n; }
      if (!best) { if (thin) { for (const k of pix) { label[k] = 0; body[k] = 0; } regions[r] = []; } return; }
      for (const k of pix) { label[k] = best; regions[best - 1].push(k); }
      regions[r] = [];
    });
  }

  const VX = FN + 1;
  const simplify = (loop, tol) => { // Douglas-Peucker on a closed loop of [x, z]
    const n = loop.length;
    if (n < 5) return loop;
    let far = 0, fd = -1;
    for (let i = 1; i < n; i++) { const d = (loop[i][0] - loop[0][0]) ** 2 + (loop[i][1] - loop[0][1]) ** 2; if (d > fd) { fd = d; far = i; } }
    const keep = new Uint8Array(n);
    keep[0] = keep[far] = 1;
    const rec = (i0, i1) => { // i1 may wrap to n (== index 0)
      const a = loop[i0], b = loop[i1 % n];
      const dx = b[0] - a[0], dz = b[1] - a[1], len = Math.hypot(dx, dz) || 1;
      let worst = -1, wd = tol;
      for (let i = i0 + 1; i < i1; i++) {
        const d = Math.abs((loop[i][0] - a[0]) * dz - (loop[i][1] - a[1]) * dx) / len;
        if (d > wd) { wd = d; worst = i; }
      }
      if (worst >= 0) { keep[worst] = 1; rec(i0, worst); rec(worst, i1); }
    };
    rec(0, far); rec(far, n);
    return loop.filter((_, i) => keep[i]);
  };
  const areaOf = (loop) => { let a = 0; for (let i = 0, j = loop.length - 1; i < loop.length; j = i++) a += loop[j][0] * loop[i][1] - loop[i][0] * loop[j][1]; return a / 2; };

  const cellsOut = new Map(); // "sx_sz" -> { pos: [], flag: [] } non-indexed
  let nRegions = 0;
  regions.forEach((pix, r) => {
    if (pix.length < 160) return;
    const id = r + 1;
    // directed boundary edges, region on the left when walking
    const next = new Map();
    const add = (a, b) => { const l = next.get(a); if (l) l.push(b); else next.set(a, [b]); };
    const hs = [];
    for (const k of pix) {
      const u = k % FN, v = (k / FN) | 0;
      hs.push(hgt[k]);
      const tl = v * VX + u, tr = tl + 1, bl = tl + VX, br = bl + 1;
      if (label[k - FN] !== id) add(tr, tl);
      if (label[k + FN] !== id) add(bl, br);
      if (label[k - 1] !== id) add(tl, bl);
      if (label[k + 1] !== id) add(br, tr);
    }
    hs.sort((a, b) => a - b);
    const roofY = hs[hs.length >> 1] - 0.3; // just under the parapet top, so the cornice wraps the wall head
    roofById.set(id, roofY);
    const loops = [];
    for (const [start, outs] of next) {
      while (outs.length) {
        const loop = [];
        let cur = start, prev = -1, guard = 0;
        do {
          const o = next.get(cur);
          if (!o || !o.length) break;
          let pick = 0;
          if (o.length > 1 && prev >= 0) { // at a pinch point keep hugging this side
            const dx0 = (cur % VX) - (prev % VX), dz0 = ((cur / VX) | 0) - ((prev / VX) | 0);
            let bestTurn = -9;
            o.forEach((cand, i) => {
              const dx1 = (cand % VX) - (cur % VX), dz1 = ((cand / VX) | 0) - ((cur / VX) | 0);
              const turn = dx0 * dz1 - dz0 * dx1; // left turn positive
              if (turn > bestTurn) { bestTurn = turn; pick = i; }
            });
          }
          const nx = o.splice(pick, 1)[0];
          loop.push([CM.x0 + (cur % VX) * FP, CM.z0 + ((cur / VX) | 0) * FP]);
          prev = cur; cur = nx;
        } while (cur !== start && guard++ < 200000);
        if (loop.length >= 4) loops.push(loop);
      }
    }
    if (!loops.length) return;
    const simp = loops.map((l) => simplify(l, 0.3)).filter((l) => l.length >= 3);
    let outer = null, oa = 0;
    for (const l of simp) { const a = Math.abs(areaOf(l)); if (a > oa) { oa = a; outer = l; } }
    if (!outer || oa < 9) return;
    const holes = simp.filter((l) => l !== outer && Math.abs(areaOf(l)) > 9);
    nRegions++;
    let gMin = 1e9, cxs = 0, czs = 0;
    for (const [x, z] of outer) { gMin = Math.min(gMin, terrainAt(x, z)); cxs += x; czs += z; }
    const key = `${Math.floor(cxs / outer.length / 100)}_${Math.floor(czs / outer.length / 100)}`;
    if (!cellsOut.has(key)) cellsOut.set(key, { pos: [], nor: [], tint: [] });
    const tintV = ((r * 2654435761) >>> 0) / 4294967296;
    const tint0 = cellsOut.get(key).pos.length / 3;
    const out = cellsOut.get(key);
    const y0 = Math.min(gMin - 1.2, roofY - 2.5);
    const PT = 0.3, topY = roofY + 0.85; // parapet thickness and top
    const sign = Math.sign(areaOf(outer));
    for (const l of [outer, ...holes]) {
      const flip = Math.sign(areaOf(l)) !== sign; // holes run the other way round
      for (let i = 0; i < l.length; i++) {
        const [xa, za] = l[i], [xb, zb] = l[(i + 1) % l.length];
        // outward normal: to the right of the walk for the outer loop
        let nx = (zb - za), nz = -(xb - xa);
        const len = Math.hypot(nx, nz) || 1; nx /= len; nz /= len;
        if (sign < 0) { nx = -nx; nz = -nz; }
        void flip; // holes are traced with the region on the same side, so the same rule holds
        const quad = nx * (zb - za) - nz * (xb - xa) > 0
          ? [xa, y0, za, xb, y0, zb, xb, roofY, zb, xa, y0, za, xb, roofY, zb, xa, roofY, za]
          : [xb, y0, zb, xa, y0, za, xa, roofY, za, xb, y0, zb, xa, roofY, za, xb, roofY, zb];
        for (let q = 0; q < 18; q++) out.pos.push(quad[q] === roofY ? topY : quad[q]);
        for (let q = 0; q < 6; q++) out.nor.push(nx, 0, nz);
        // the parapet's inner face and its coping
        {
          const ia = [xa - nx * PT, za - nz * PT], ib = [xb - nx * PT, zb - nz * PT];
          const front = nx * (zb - za) - nz * (xb - xa) > 0;
          const inner = front
            ? [ib[0], roofY, ib[1], ia[0], roofY, ia[1], ia[0], topY, ia[1], ib[0], roofY, ib[1], ia[0], topY, ia[1], ib[0], topY, ib[1]]
            : [ia[0], roofY, ia[1], ib[0], roofY, ib[1], ib[0], topY, ib[1], ia[0], roofY, ia[1], ib[0], topY, ib[1], ia[0], topY, ia[1]];
          for (const v of inner) out.pos.push(v);
          for (let q = 0; q < 6; q++) out.nor.push(-nx, 0, -nz);
          const A = [xa, topY, za], B = [xb, topY, zb], C = [ib[0], topY, ib[1]], D = [ia[0], topY, ia[1]];
          const upc = (B[2] - A[2]) * (C[0] - A[0]) - (B[0] - A[0]) * (C[2] - A[2]) > 0;
          for (const P of (upc ? [A, B, C, A, C, D] : [A, C, B, A, D, C])) out.pos.push(P[0], P[1], P[2]);
          for (let q = 0; q < 6; q++) out.nor.push(0, 1, 0);
        }
        // doors at lane level and windows above, on walls that face open ground
        const L = Math.hypot(xb - xa, zb - za);
        if (L <= 1.5) bayStat[3]++;
        if (L > 1.5) {
          const ux = (xb - xa) / L, uz = (zb - za) / L;
          const tx = -nz, tz = nx; // the panel's own left-to-right
          const lab = (x, z) => { const u = Math.floor((x - CM.x0) / FP), v = Math.floor((z - CM.z0) / FP); return u < 0 || v < 0 || u >= FN || v >= FN ? 0 : label[v * FN + u]; };
          const bays = Math.max(1, Math.floor(L / 3.4));
          if (!genWin.has(key)) genWin.set(key, { pos: [], col: [], idx: [] });
          const G = genWin.get(key);
          for (let j = 0; j < bays; j++) {
            const t = (j + 0.5) / bays, mx = xa + (xb - xa) * t, mz = za + (zb - za) * t;
            if (lab(mx + nx * 0.4, mz + nz * 0.4) || lab(mx + nx * 0.8, mz + nz * 0.8) || lab(mx + nx * 1.15, mz + nz * 1.15)) { bayStat[0]++; continue; } // a party wall, or a gap too tight to be a lane
            if (lab(mx - nx * 0.8, mz - nz * 0.8) !== id) { bayStat[1]++; continue; } // the normal points the wrong way here
            bayStat[2]++;
            const g = Math.max(terrainAt(mx + nx * 0.6, mz + nz * 0.6), terrainAt(mx + nx * 0.6 + ux, mz + nz * 0.6 + uz), terrainAt(mx + nx * 0.6 - ux, mz + nz * 0.6 - uz));
            // a different, unrelated number for every n at this spot on the wall
            const hbase = Math.round(mx * 37.1 + mz * 91.7);
            const hsh = (n) => { let x = Math.imul(hbase ^ Math.imul(n + 1, 0x9e3779b1), 0x85ebca6b); x ^= x >>> 15; x = Math.imul(x, 0xc2b2ae35); x ^= x >>> 13; x = Math.imul(x, 0x27d4eb2f); x ^= x >>> 16; return (x >>> 0) / 4294967296; };
            const put = (y0p, wdt, hgt, cls, r) => {
              const q0 = G.pos.length / 3, d = 0.05;
              for (const [su, yy] of [[-1, y0p], [1, y0p], [1, y0p + hgt], [-1, y0p + hgt]]) G.pos.push(mx + tx * su * wdt / 2 + nx * d, yy, mz + tz * su * wdt / 2 + nz * d);
              const c = cls * 0.25 + r * 0.2;
              G.col.push(0, c, 0, 1, c, 0, 1, c, 1, 0, c, 1);
              G.idx.push(q0, q0 + 2, q0 + 1, q0, q0 + 3, q0 + 2);
            };
            const S = (kind, x, y, z, yaw, r, p1 = 0, p2 = 0) => streetItems.push(+x.toFixed(2), +y.toFixed(2), +z.toFixed(2), kind, +yaw.toFixed(2), +r.toFixed(3), +p1.toFixed(2), +p2.toFixed(2));
            const yaw = Math.atan2(nx, nz);
            const jewishQ = mx > -660 && mx < -235 && mz > -30 && mz < 330;
            let y = g + 1.05, isDoor = false;
            if (roofY - g > 2.9) {
              const h0 = L < 2.2 ? 0.34 + hsh(0) * 0.66 : hsh(0); // a short wall has room for a window, not a door
              // shops keep together: a wall is a row of them or has none
              const wb = Math.round(xa * 37.1 + za * 91.7); let wx = Math.imul(wb ^ 0x51ed270b, 0x85ebca6b); wx ^= wx >>> 15; wx = Math.imul(wx, 0xc2b2ae35); wx ^= wx >>> 13;
              const shopWall = (wx >>> 0) / 4294967296 < 0.1 && L >= 3.2 && L / bays >= 3.0;
              if (shopWall && roofY - g > 3.3 && hsh(90) < 0.75 && !lab(mx + nx * 2.2, mz + nz * 2.2) && Math.abs(terrainAt(mx + ux * 1.3 + nx * 0.5, mz + uz * 1.3 + nz * 0.5) - terrainAt(mx - ux * 1.3 + nx * 0.5, mz - uz * 1.3 + nz * 0.5)) < 0.3) {
                isDoor = true; nShop++;
                const shut = hsh(91) < 0.35;
                S(shut ? 33 : 32, mx + nx * 0.03, g + 0.02, mz + nz * 0.03, yaw, hsh(92));
                if (!shut && hsh(93) < 0.45) S(10, mx + tx * 0.9 + nx * 0.5, g, mz + tz * 0.9 + nz * 0.5, yaw + (hsh(94) - 0.5) * 0.4, hsh(94));
                if (!shut && hsh(95) < 0.4) S(34, mx - tx * 0.9 + nx * 0.55, g, mz - tz * 0.9 + nz * 0.55, yaw + (hsh(96) - 0.5) * 0.8, hsh(96));
                if (!shut && hsh(97) < 0.35) S(1, mx + nx * 0.06, g + 2.9, mz + nz * 0.06, yaw, hsh(98));
              }
              else if (L >= 2.2 && hsh(33) < 0.014) {
                // a garbage room: the quarter keeps its bins behind a plain grey metal door, not in
                // the lane. About one in four is overflowing: door open, a bin and bags outside.
                isDoor = true; nTrash++;
                const over = ((hsh(33) * 1000) % 1) < 0.26, dw = 1.5, dh = 1.95;
                put(g + 0.05, dw, dh, 2, over ? 0.5 + 7.5 / 16 : 0.36 + hsh(35) * 0.07); nGenDoor++;
                if (over) {
                  const sd = hsh(15) < 0.5 ? -1 : 1, lw = dw * 0.76, ang = 1.5 + hsh(16) * 0.9;
                  const dx = -sd * tx * Math.cos(ang) + nx * Math.sin(ang), dz = -sd * tz * Math.cos(ang) + nz * Math.sin(ang);
                  S(12, mx + sd * tx * lw / 2 + nx * 0.07, g + 0.08, mz + sd * tz * lw / 2 + nz * 0.07, Math.atan2(-dz, dx), 0.875, lw, dh * 0.84);
                  S(4, mx - sd * tx * 0.15 + nx * 0.6, g, mz - sd * tz * 0.15 + nz * 0.6, yaw + (hsh(36) - 0.5) * 0.7, hsh(37));
                  S(17, mx - sd * tx * 0.95 + nx * 0.5, g, mz - sd * tz * 0.95 + nz * 0.5, yaw + hsh(38) * 6, hsh(38));
                  if (hsh(39) < 0.5) S(17, mx + sd * tx * 0.2 + nx * 1.15, g, mz + sd * tz * 0.2 + nz * 1.15, yaw + hsh(42) * 6, hsh(42));
                }
              }
              else if (h0 < 0.34) {
                isDoor = true;
                // no two doors alike: width and height wander, and about one in three stands open
                const dw = 1.05 + hsh(12) * 0.4, dh = 2.1 + hsh(13) * 0.4, open = hsh(11) < 0.32;
                const ok = Math.floor(hsh(14) * 8) % 8; // paint (low two bits) and which way the leaf swings
                const paintSel = open ? ((ok & 3) + 0.5) / 4 : hsh(2);
                put(g + 0.05, dw, dh, hsh(1) < 0.65 ? 3 : 2, open ? 0.5 + (ok + 0.5) / 16 : hsh(2) * 0.44); nGenDoor++;
                if (open && ok >= 4) {
                  // the leaf itself, swung out into the lane on its hinge
                  const sd = hsh(15) < 0.5 ? -1 : 1, lw = dw * 0.76, ang = 0.7 + hsh(16) * 1.5;
                  const dx = -sd * tx * Math.cos(ang) + nx * Math.sin(ang), dz = -sd * tz * Math.cos(ang) + nz * Math.sin(ang);
                  S(12, mx + sd * tx * lw / 2 + nx * 0.07, g + 0.08, mz + sd * tz * lw / 2 + nz * 0.07, Math.atan2(-dz, dx), paintSel, lw, dh * 0.84);
                }
                // life at the door: a pot or two beside it, sometimes a cloth awning over it
                const r5 = hsh(5);
                if (r5 < 0.5) { const sd = hsh(6) < 0.5 ? -1 : 1; S(0, mx + tx * sd * 1.05 + nx * 0.38, g + 0.02, mz + tz * sd * 1.05 + nz * 0.38, yaw, hsh(7)); }
                if (r5 > 0.3 && r5 < 0.42) S(0, mx - tx * 1.1 + nx * 0.4, g + 0.02, mz - tz * 1.1 + nz * 0.4, yaw, hsh(8));
                if (hsh(9) < 0.24) S(1, mx + nx * 0.06, g + 2.55, mz + nz * 0.06, yaw, hsh(10));
                if (hsh(17) < 0.07) S(16, mx + tx * 1.0 + nx * 0.45, g, mz + tz * 1.0 + nz * 0.45, yaw + (hsh(18) - 0.5) * 1.2, hsh(19));
              }
              else if (h0 < 0.62 && roofY - g > 3.4) {
                put(y, 0.95, 1.5, hsh(1) < 0.3 ? 1 : 0, hsh(2)); nGenWin++;
                if (hsh(40) < 0.16) S(11, mx + nx * 0.06, y - 0.05, mz + nz * 0.06, yaw, hsh(41));
              }
            }
            for (let f = 1; g + f * 3.15 + 1.0 + 1.75 < roofY - 0.35; f++) {
              if (hsh(f * 7) > 0.78) continue;
              const wy = g + f * 3.15 + 1.0;
              put(wy, 1.0, 1.75, hsh(f * 7 + 1) < 0.4 ? 1 : 0, hsh(f * 7 + 2)); nGenWin++;
              const e = hsh(f * 7 + 3);
              if (e < 0.14) S(11, mx + nx * 0.06, wy - 0.05, mz + nz * 0.06, yaw, hsh(f * 7 + 4));
              else if (e < 0.25) S(6, mx + tx * 1.0 + nx * 0.05, wy - 0.25, mz + tz * 1.0 + nz * 0.05, yaw, hsh(f * 7 + 4));
              else if (e > 0.31 && e < 0.38) S(27, mx + nx * 0.05, wy - 0.1, mz + nz * 0.05, yaw, hsh(f * 7 + 4));
              else if (e < 0.31 && jewishQ) S(14, mx + nx * 0.05, wy + 0.25, mz + nz * 0.05, yaw, hsh(f * 7 + 4));
            }
            // what hangs on the wall: an iron lantern, a drainpipe
            if (roofY - g > 3.6 && hsh(20) < 0.075) S(5, mx - tx * 1.2 + nx * 0.05, g + 2.95, mz - tz * 1.2 + nz * 0.05, yaw, hsh(23));
            if (hsh(21) < 0.11) S(7, mx + tx * 1.45 + nx * 0.04, g - 0.4, mz + tz * 1.45 + nz * 0.04, yaw, hsh(24), roofY - g + 0.4);
            if (j === 0 && roofY - g > 4.3 && hsh(22) < 0.3) S(13, xa + (xb - xa) * 0.5 + nx * 0.05, g + 3.3 + hsh(25) * 0.7, za + (zb - za) * 0.5 + nz * 0.05, yaw, hsh(26), L);
            // how far to the house opposite, and which house it is
            let cw = 0.75, oid = 0;
            while (cw < 7 && !(oid = lab(mx + nx * (cw + 0.25), mz + nz * (cw + 0.25)))) cw += 0.25;
            // a wire slung across the lane, an arch between the two houses
            if (oid && roofY - g > 4 && hsh(50) < 0.07) S(25, mx + nx * 0.05, g + 3.5 + hsh(51) * 1.3, mz + nz * 0.05, yaw, hsh(52), cw + 0.2);
            if (oid && oid !== id && cw >= 2.2 && cw <= 4.6 && roofY - g > 4.9 && hsh(53) < 0.06) archC.push({ mx, mz, nx, nz, ux, uz, g, cw: cw + 0.25, oid, out, W: hsh(69) < 0.55 ? 0.6 + hsh(73) * 0.5 : 1.2 + hsh(73) * 1.8 });
            // a handrail on the wall where the lane climbs
            {
              const gA = terrainAt(mx - ux * 1.6 + nx * 0.5, mz - uz * 1.6 + nz * 0.5), gB = terrainAt(mx + ux * 1.6 + nx * 0.5, mz + uz * 1.6 + nz * 0.5);
              const sl = (gB - gA) / 3.2;
              if (!isDoor && Math.abs(sl) > 0.1 && Math.abs(sl) < 0.5 && cw < 6.9) { S(18, mx + nx * 0.1, (gA + gB) / 2 + 0.95, mz + nz * 0.1, yaw, hsh(64), L / bays + 0.05, Math.atan(-sl * (ux * tx + uz * tz))); nRail++; }
            }
            // what grows here: weeds at the foot of the wall, caper bushes out of its cracks and
            // along its top, a creeper over the odd door
            if (hsh(54) < 0.3) S(20, mx + tx * (hsh(55) - 0.5) * 2.8 + nx * 0.14, g, mz + tz * (hsh(55) - 0.5) * 2.8 + nz * 0.14, yaw, hsh(56));
            if (hsh(65) < 0.12) S(20, mx + tx * (hsh(66) - 0.5) * 2.8 + nx * 0.2, g, mz + tz * (hsh(66) - 0.5) * 2.8 + nz * 0.2, yaw, hsh(67));
            if (roofY - g > 3.2 && hsh(57) < 0.06) S(19, mx + tx * (hsh(58) - 0.5) * 2.2 + nx * 0.04, g + 1.6 + hsh(59) * (Math.min(roofY - g, 8) - 2.2), mz + tz * (hsh(58) - 0.5) * 2.2 + nz * 0.04, yaw, hsh(60));
            if (hsh(63) < 0.05) S(19, mx + tx * (hsh(58) - 0.5) * 2.2 + nx * 0.02, roofY + 0.8, mz + tz * (hsh(58) - 0.5) * 2.2 + nz * 0.02, yaw, hsh(68));
            if (roofY - g > 5 && hsh(70) < 0.04) S(26, mx + tx * (hsh(71) - 0.5) * 2 + nx * 0.1, g, mz + tz * (hsh(71) - 0.5) * 2 + nz * 0.1, yaw, hsh(71), Math.min(roofY - g - 0.3, 3.5 + hsh(72) * 4));
            // what people fix to a wall: a street-name plaque, a shop sign, a meter box by the door,
            // and washing strung across to the neighbours
            if (j === 0 && L > 4 && roofY - g > 3.4 && hsh(80) < 0.07) S(29, mx + tx * 1.35 + nx * 0.06, g + 2.75, mz + tz * 1.35 + nz * 0.06, yaw, hsh(81));
            if (isDoor && roofY - g > 3.6 && hsh(82) < 0.08) S(28, mx + tx * 0.95 + nx * 0.05, g + 2.9, mz + tz * 0.95 + nz * 0.05, yaw, hsh(85));
            if (isDoor && hsh(83) < 0.4) S(30, mx - tx * 1.0 + nx * 0.04, g + 1.4, mz - tz * 1.0 + nz * 0.04, yaw, hsh(86));
            if (oid && cw >= 1.8 && cw < 5 && roofY - g > 5.6 && hsh(84) < 0.04) S(31, mx + nx * 0.05, g + 4.4 + hsh(87) * 1.2, mz + nz * 0.05, yaw, hsh(88), cw + 0.2);
            if (isDoor && hsh(61) < 0.08) S(21, mx + nx * 0.1, g + 2.65, mz + nz * 0.1, yaw, hsh(62));
            // what stands in the lane beside it
            if (!isDoor && cw >= 2.4 && L >= 2.4) {
              let clear = 2.4;
              while (clear < 9 && !lab(mx + nx * (clear + 0.5), mz + nz * (clear + 0.5))) clear += 0.5;
              const r30 = hsh(30), r31 = hsh(31);
              // a car needs a street it could have driven in on, not a closed courtyard
              const onLane = (x, z) => { const u = Math.floor((x - CM.x0) / cmPx), v = Math.floor((z - CM.z0) / cmPx); return u >= 0 && v >= 0 && u < CM.n && v < CM.n && kind[v * CM.n + u] === 110; };
              const flat = (d, half) => {
                const cx = mx + nx * d, cz = mz + nz * d, c0 = terrainAt(cx, cz);
                return Math.abs(terrainAt(cx + ux * half, cz + uz * half) - c0) < 0.3 && Math.abs(terrainAt(cx - ux * half, cz - uz * half) - c0) < 0.3 && Math.abs(c0 - g) < 0.45
                  && !lab(cx + ux * half, cz + uz * half) && !lab(cx - ux * half, cz - uz * half);
              };
              if (r30 < 0.13 && clear >= 5.5 && j % 2 === 0 && L >= 5 && flat(1.3, 2.1) && onLane(mx + nx * 1.3, mz + nz * 1.3) && onLane(mx + nx * 4, mz + nz * 4)) { S(3, mx + nx * 1.3, g, mz + nz * 1.3, yaw + (r31 < 0.5 ? 0 : Math.PI), r31, nx, nz); nCar++; }
              else if (r30 >= 0.13 && r30 < 0.165) S(2, mx + nx * 0.02, g, mz + nz * 0.02, yaw + (r31 < 0.5 ? 0 : Math.PI) * 0, r31, r31 < 0.5 ? 1 : -1);
              else if (r30 >= 0.235 && r30 < 0.26 && clear >= 3.4 && flat(0.4, 0.8)) S(8, mx + nx * 0.36, g, mz + nz * 0.36, yaw, r31);
              else if (r30 >= 0.26 && r30 < 0.29 && clear >= 4.4 && flat(1.1, 0.9)) S(9, mx + nx * 1.05, g, mz + nz * 1.05, yaw + r31 * 3, r31);
              else if (r30 >= 0.29 && r30 < 0.335) S(10, mx + nx * 0.36, g, mz + nz * 0.36, yaw + (r31 - 0.5) * 0.4, r31);
              else if (r30 >= 0.335 && r30 < 0.36) S(16, mx + nx * 0.5, g, mz + nz * 0.5, yaw + (r31 - 0.5) * 1.6, r31);
              else if (r30 >= 0.36 && r30 < 0.378) S(15, mx + nx * (0.3 + r31 * 0.6), g, mz + nz * (0.3 + r31 * 0.6), yaw + (r31 - 0.5) * 3, r31);
            }
          }
        }
      }
    }
    const tris = THREE.ShapeUtils.triangulateShape(outer.map(([x, z]) => new THREE.Vector2(x, z)), holes.map((h) => h.map(([x, z]) => new THREE.Vector2(x, z))));
    const all = [outer, ...holes].flat();
    for (const [a, b, c] of tris) {
      const A = all[a], B = all[b], C = all[c];
      const up = (B[1] - A[1]) * (C[0] - A[0]) - (B[0] - A[0]) * (C[1] - A[1]) > 0;
      const order = up ? [A, B, C] : [A, C, B];
      for (const P of order) { out.pos.push(P[0], roofY, P[1]); out.nor.push(0, 1, 0); }
    }
    for (let i = tint0; i < out.pos.length / 3; i++) out.tint.push(tintV);
    // what stands on a Jerusalem roof today: a white water tank with its solar panel, a small
    // dome, a few planters. Each sits in the middle of one of the roof's larger triangles.
    {
      const cand = [];
      for (const [a, b, c] of tris) {
        const A = all[a], B = all[b], C = all[c];
        const ar = Math.abs((B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])) / 2;
        const e = Math.max(Math.hypot(B[0] - A[0], B[1] - A[1]), Math.hypot(C[0] - B[0], C[1] - B[1]), Math.hypot(A[0] - C[0], A[1] - C[1]));
        const inr = (2 * ar) / (3 * e); // rough clearance from the edges
        if (inr > 1.1) cand.push([inr, (A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3]);
      }
      cand.sort((p, q) => q[0] - p[0]);
      const want = oa > 260 ? 3 : oa > 90 ? 2 : oa > 22 ? 1 : 0;
      const taken = [];
      for (const [inr, x, z] of cand) {
        if (taken.length >= want) break;
        if (taken.some(([tx, tz]) => Math.hypot(tx - x, tz - z) < 4)) continue;
        taken.push([x, z]);
        const h1 = ((r * 40503 + taken.length * 9973) >>> 0) % 1000 / 1000;
        const kind = inr > 2.6 && h1 < 0.36 ? 1 : h1 < 0.62 ? 0 : 2; // 0 tank, 1 dome, 2 planters
        roofItems.push(+x.toFixed(2), +roofY.toFixed(2), +z.toFixed(2), kind, +(h1 * 6.28).toFixed(2), +Math.min(inr, 5).toFixed(1));
      }
    }
  });

  // shade the solids: lanes and courtyards are darker than rooftops
  const allPos = [];
  // Stone arches thrown across the narrow lanes, house to house.
  {
    const made = [];
    for (const A of archC) {
      const ro = roofById.get(A.oid);
      if (ro === undefined || ro - A.g < 4.7) continue;
      if (made.some(([x, z]) => Math.hypot(x - A.mx, z - A.mz) < 14)) continue;
      made.push([A.mx, A.mz]);
      const SEG = 8, W = A.W, base = A.g + 2.75, rise = 0.95, topY = A.g + 4.4, o = A.out;
      const P = (sd, y, w) => [A.mx + A.nx * sd + A.ux * w, y, A.mz + A.nz * sd + A.uz * w];
      const quad = (p, q, r2, t, n) => { for (const v of [p, q, r2, p, r2, t]) { o.pos.push(v[0], v[1], v[2]); o.nor.push(n[0], n[1], n[2]); o.tint.push(0.5); } };
      const sAt = (i) => -0.2 + (A.cw + 0.4) * (i / SEG), yAt = (i) => base + rise * Math.sin(Math.PI * Math.min(1, Math.max(0, (sAt(i)) / A.cw)));
      for (let i = 0; i < SEG; i++) {
        const s0 = sAt(i), s1 = sAt(i + 1), y0 = yAt(i), y1 = yAt(i + 1);
        for (const w of [-W, W]) quad(P(s0, y0, w), P(s1, y1, w), P(s1, topY, w), P(s0, topY, w), [A.ux * Math.sign(w), 0, A.uz * Math.sign(w)]);
        quad(P(s0, y0, -W), P(s1, y1, -W), P(s1, y1, W), P(s0, y0, W), [0, -1, 0]);
      }
      quad(P(sAt(0), topY, -W), P(sAt(SEG), topY, -W), P(sAt(SEG), topY, W), P(sAt(0), topY, W), [0, 1, 0]);
    }
    console.log('bays: party', bayStat[0], 'wrong way', bayStat[1], 'used', bayStat[2], 'short walls', bayStat[3]);
    console.log(`arches over lanes: ${made.length}; handrail runs: ${nRail}`);
  }
  // The drain down the middle of each lane: the line furthest from the houses on either side,
  // found on the quarter-metre raster and written as a half-metre map for the paving shader.
  {
    const dist = new Float32Array(FN * FN);
    for (let k = 0; k < dist.length; k++) dist[k] = label[k] ? 0 : 1e6;
    const D1 = 1, D2 = Math.SQRT2;
    for (let v = 1; v < FN - 1; v++) for (let u = 1; u < FN - 1; u++) {
      const k = v * FN + u; let d = dist[k]; if (d === 0) continue;
      d = Math.min(d, dist[k - 1] + D1, dist[k - FN] + D1, dist[k - FN - 1] + D2, dist[k - FN + 1] + D2); dist[k] = d;
    }
    for (let v = FN - 2; v > 0; v--) for (let u = FN - 2; u > 0; u--) {
      const k = v * FN + u; let d = dist[k]; if (d === 0) continue;
      d = Math.min(d, dist[k + 1] + D1, dist[k + FN] + D1, dist[k + FN + 1] + D2, dist[k + FN - 1] + D2); dist[k] = d;
    }
    // soften the field a little so the crest is a single clean line
    const sm = new Float32Array(FN * FN);
    for (let v = 2; v < FN - 2; v++) for (let u = 2; u < FN - 2; u++) {
      const k = v * FN + u;
      if (dist[k] < 2 || dist[k] > 24) continue;
      sm[k] = (dist[k] * 2 + dist[k - 1] + dist[k + 1] + dist[k - FN] + dist[k + FN] + dist[k - 2] + dist[k + 2] + dist[k - 2 * FN] + dist[k + 2 * FN]) / 10;
    }
    const isRidge = new Uint8Array(FN * FN);
    let nR = 0;
    for (let v = 5; v < FN - 5; v++) for (let u = 5; u < FN - 5; u++) {
      const k = v * FN + u, d = sm[k];
      if (d < 3.6 || d > 20) continue;
      { const lu = Math.floor((u * FP) / cmPx), lv = Math.floor((v * FP) / cmPx); if (kind[lv * CM.n + lu] !== 110) continue; }
      for (const [du, dv, sl] of [[1, 0, 1], [0, 1, 1], [1, 1, 1.414], [1, -1, 1.414]]) {
        const o1 = dv * FN + du;
        if (d > sm[k + o1] && d >= sm[k - o1] && d - sm[k + 4 * o1] >= 2.2 * sl && d - sm[k - 4 * o1] >= 2.2 * sl) { isRidge[k] = 1; nR++; break; }
      }
    }
    // string the crest pixels into runs
    const runs = [];
    const NB = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1], [2, 0], [-2, 0], [0, 2], [0, -2], [2, 1], [2, -1], [-2, 1], [-2, -1], [1, 2], [-1, 2], [1, -2], [-1, -2], [2, 2], [2, -2], [-2, 2], [-2, -2]];
    const walk = (u, v, pu, pv) => {
      const pts = [];
      for (;;) {
        let best = -1, bs = -1e9, bu = 0, bv = 0;
        for (const [du, dv] of NB) {
          const k2 = (v + dv) * FN + u + du;
          if (isRidge[k2] !== 1) continue;
          const sc = (du * pu + dv * pv) / Math.hypot(du, dv) - Math.hypot(du, dv) * 0.3;
          if (sc > bs) { bs = sc; best = k2; bu = du; bv = dv; }
        }
        if (best < 0 || ((pu || pv) && bs < -0.9)) break;
        isRidge[best] = 2; u += bu; v += bv; const l = Math.hypot(bu, bv); pu = bu / l; pv = bv / l;
        pts.push([CM.x0 + (u + 0.5) * FP, CM.z0 + (v + 0.5) * FP]);
      }
      return pts;
    };
    for (let v = 5; v < FN - 5; v++) for (let u = 5; u < FN - 5; u++) {
      if (isRidge[v * FN + u] !== 1) continue;
      isRidge[v * FN + u] = 2;
      const fwd = walk(u, v, 0, 0);
      const d0 = fwd.length > 1 ? [fwd[0][0] - fwd[1][0], fwd[0][1] - fwd[1][1]] : [0, 0];
      const back = walk(u, v, Math.sign(d0[0]) || 0, Math.sign(d0[1]) || 0);
      const run = [...back.reverse(), [CM.x0 + (u + 0.5) * FP, CM.z0 + (v + 0.5) * FP], ...fwd];
      if (run.length >= 16) runs.push(run);
    }
    // smooth each run, then lay it as a ribbon of dished stones on the ground
    const dp = [], dc = [], di = [];
    let total = 0;
    for (let run of runs) {
      for (let pass = 0; pass < 3; pass++) {
        const o = run.map((p) => p.slice());
        for (let i = 1; i < run.length - 1; i++) {
          let sx = 0, sz = 0, n = 0;
          for (let j = Math.max(0, i - 5); j <= Math.min(run.length - 1, i + 5); j++) { sx += run[j][0]; sz += run[j][1]; n++; }
          o[i] = [sx / n, sz / n];
        }
        run = o;
      }
      const pts = [run[0]];
      let acc = 0;
      for (let i = 1; i < run.length; i++) {
        acc += Math.hypot(run[i][0] - run[i - 1][0], run[i][1] - run[i - 1][1]);
        if (acc >= 0.9 || i === run.length - 1) { pts.push(run[i]); acc = 0; }
      }
      if (pts.length < 4) continue;
      const base = dp.length / 3, HW = 0.2;
      for (let i = 0; i < pts.length; i++) {
        const a = pts[Math.max(0, i - 1)], b2 = pts[Math.min(pts.length - 1, i + 1)];
        let tx = b2[0] - a[0], tz = b2[1] - a[1]; const l = Math.hypot(tx, tz) || 1; tx /= l; tz /= l;
        if (i) total += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
        for (const sd of [-1, 1]) {
          const x = pts[i][0] - tz * HW * sd, z = pts[i][1] + tx * HW * sd;
          dp.push(x, terrainAt(x, z) + 0.02, z);
          dc.push(sd < 0 ? 0 : 1, (total / 0.62) % 1 < 0.5 ? 0.25 : 0.75, 0.5);
        }
        if (i) { const q = base + i * 2; di.push(q - 2, q - 1, q, q - 1, q + 1, q); }
        // an iron grate or a manhole cover in the drain, now and then
        const h = ((Math.round(pts[i][0] * 53.7 + pts[i][1] * 97.3) * 2654435761) >>> 0) / 4294967296;
        if (h < 0.012) streetItems.push(+pts[i][0].toFixed(2), 0, +pts[i][1].toFixed(2), 23, +Math.atan2(tx, tz).toFixed(2), +((h * 7919) % 1).toFixed(3), 0, 0);
      }
    }
    if (di.length) cityMeshes.push({ name: 'drain_0', pos: new Float32Array(dp), idx: new Uint32Array(di), col: new Float32Array(dc) });
    console.log(`lane drains: ${nR} crest pixels, ${runs.length} runs, ${(total / 1000).toFixed(1)} km, ${di.length / 3} triangles`);
  }
  for (const o of cellsOut.values()) for (const v of o.pos) allPos.push(v);
  const bg = new THREE.BufferGeometry();
  bg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(allPos), 3));
  const bvh = new MeshBVH(bg);
  const ray = new THREE.Ray();
  const tv = new THREE.Vector3(), bv = new THREE.Vector3(), nv = new THREE.Vector3();
  for (const [key, o] of cellsOut) {
    const n = o.pos.length / 3;
    const ao = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      nv.set(o.nor[i * 3], o.nor[i * 3 + 1], o.nor[i * 3 + 2]);
      const wall = nv.y < 0.5;
      // sample a little inside the face so shared corners do not all read the same
      let cx = 0, cy = 0, cz = 0;
      const f = Math.floor(i / 3) * 3;
      for (let q = 0; q < 3; q++) { cx += o.pos[(f + q) * 3]; cy += o.pos[(f + q) * 3 + 1]; cz += o.pos[(f + q) * 3 + 2]; }
      const px = o.pos[i * 3] * 0.9 + (cx / 3) * 0.1, pz = o.pos[i * 3 + 2] * 0.9 + (cz / 3) * 0.1;
      let py = o.pos[i * 3 + 1];
      if (wall) { const g = terrainAt(px, pz); py = Math.max(py, g + 0.4); py = py * 0.94 + (cy / 3) * 0.06; }
      if (Math.abs(nv.y) < 0.9) tv.set(0, 1, 0); else tv.set(1, 0, 0);
      tv.cross(nv).normalize(); bv.crossVectors(nv, tv);
      ray.origin.set(px + nv.x * 0.25, py + nv.y * 0.25, pz + nv.z * 0.25);
      let open = 0;
      for (const d of AO_DIRS) {
        ray.direction.set(tv.x * d[0] + bv.x * d[1] + nv.x * d[2], tv.y * d[0] + bv.y * d[1] + nv.y * d[2], tv.z * d[0] + bv.z * d[1] + nv.z * d[2]);
        if (wall && ray.direction.y < -0.05) { open += 0.35; continue; } // the ground below
        const hit = bvh.raycastFirst(ray, THREE.DoubleSide, 0.05, 30);
        open += hit ? Math.min(1, hit.distance / 30) * 0.55 : 1;
      }
      ao[i] = open / AO_DIRS.length;
    }
    const idx = new Uint32Array(n);
    for (let i = 0; i < n; i++) idx[i] = i;
    const pos = new Float32Array(o.pos);
    cityMeshes.push({ name: `solid_${key}`, pos, idx, ao, flag: 1, tint: new Float32Array(o.tint) });
    footprints.push([pos, idx]);
    solidTris.count += n / 3;
  }
  for (const [key, G] of genWin) if (G.idx.length) cityMeshes.push({ name: `win_${key}`, pos: new Float32Array(G.pos), idx: new Uint32Array(G.idx), col: new Float32Array(G.col) });
  console.log(`house solids: ${nRegions} roof regions, ${solidTris.count} triangles`);
  console.log(`openings made: ${nGenWin} windows, ${nGenDoor} doors, ${nTrash} garbage rooms, ${nShop} shops`);
  if (process.env.CITY_SCAN) {
    const [sx0, sx1, sz] = process.env.CITY_SCAN.split(',').map(Number);
    const v = Math.round((sz - CM.z0) / FP);
    for (let x = sx0; x <= sx1; x += FP) {
      const k = v * FN + Math.round((x - CM.x0) / FP);
      console.log(x.toFixed(2), mark[k] ? 'M' : '.', ext[k] ? 'E' : '.', rtop[k] > -1e8 ? 'R' : '.', body[k] ? 'S' : '.', String(label[k]).padStart(5), 'top', ftop[k] > -1e8 ? ftop[k].toFixed(1) : '  -  ', 'hgt', Number.isNaN(hgt[k]) ? '  -  ' : hgt[k].toFixed(1), 'ground', terrainAt(x, sz).toFixed(1), 'region', label[k] ? regions[label[k] - 1].length : 0);
    }
  }
  if (process.env.CITY_DEBUG) {
    // picture of a 300 m square: outline marks (white), enclosed body (green), exterior (black)
    const D = 1200, u0 = Math.round((-390 - CM.x0) / FP), v0 = Math.round((-90 - CM.z0) / FP);
    const px = new Uint8Array(D * D * 3);
    for (let v = 0; v < D; v++) for (let u = 0; u < D; u++) {
      const k = (v0 + v) * FN + u0 + u, o = (v * D + u) * 3;
      if (body[k]) { px[o] = 40; px[o + 1] = 120 + ((label[k] * 37) % 100); px[o + 2] = 40 + ((label[k] * 91) % 160); }
      else if (!ext[k]) { px[o] = 120; px[o + 1] = 60; px[o + 2] = 30; }
      if (mark[k]) { px[o] = 255; px[o + 1] = Math.max(px[o + 1], 200); px[o + 2] = 255; }
    }
    for (const m of cityMeshes) {
      if (!m.name.startsWith('win_')) continue;
      for (let q = 0; q + 11 < m.pos.length; q += 12) {
        const u = Math.round(((m.pos[q] + m.pos[q + 3]) / 2 - CM.x0) / FP) - u0, v = Math.round(((m.pos[q + 2] + m.pos[q + 5]) / 2 - CM.z0) / FP) - v0;
        if (u > 0 && v > 0 && u < D - 1 && v < D - 1) for (const d of [0, 1, -1, D, -D]) { const o = (v * D + u + d) * 3; px[o] = 255; px[o + 1] = 0; px[o + 2] = 0; }
      }
    }
    writePng('/tmp/citydebug.png', D, D, px);
  }
  // diagnostic: how far behind each window panel is the rebuilt wall?
  {
    const hist = new Map();
    let n = 0;
    for (const m of cityMeshes) {
      if (!m.name.startsWith('win_')) continue;
      for (let q = 0; q + 11 < m.pos.length && n < 6000; q += 12 * 7, n++) {
        const ax = m.pos[q], ay = m.pos[q + 1], az = m.pos[q + 2], bx = m.pos[q + 3], bz = m.pos[q + 5], cy = m.pos[q + 7];
        const tx = bx - ax, tz = bz - az, l = Math.hypot(tx, tz);
        // outward normal n satisfies t = (-nz, nx)
        const nx = tz / l, nz = -tx / l;
        ray.origin.set((ax + bx) / 2 + nx * 3, (ay + cy) / 2, (az + bz) / 2 + nz * 3);
        ray.direction.set(-nx, 0, -nz);
        const hit = bvh.raycastFirst(ray, THREE.DoubleSide, 0, 8);
        const key = hit ? (Math.round((hit.distance - 3) * 4) / 4).toFixed(2) : 'none';
        hist.set(key, (hist.get(key) || 0) + 1);
      }
    }
    console.log('wall behind window panel (m):', [...hist].sort((a, b) => parseFloat(a[0]) - parseFloat(b[0])).map(([k, v]) => `${k}:${v}`).join('  '));
  }
}

// ---------------------------------------------------------------- city map raster
// Highest building surface per pixel (so the dove cannot fly through a house) and what
// the ground is: 0 open land, 60 open ground inside the city, 110 lane, 255 building.
for (const [pos, idx] of footprints) {
  for (let t = 0; t < idx.length; t += 3) {
    const a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
    const ax = (pos[a] - CM.x0) / cmPx, az = (pos[a + 2] - CM.z0) / cmPx;
    const bx = (pos[b] - CM.x0) / cmPx, bz = (pos[b + 2] - CM.z0) / cmPx;
    const cx = (pos[c] - CM.x0) / cmPx, cz = (pos[c + 2] - CM.z0) / cmPx;
    const area = (bx - ax) * (cz - az) - (cx - ax) * (bz - az);
    const hi = Math.max(pos[a + 1], pos[b + 1], pos[c + 1]);
    const u0 = Math.max(0, Math.floor(Math.min(ax, bx, cx))), u1 = Math.min(CM.n - 1, Math.ceil(Math.max(ax, bx, cx)));
    const v0 = Math.max(0, Math.floor(Math.min(az, bz, cz))), v1 = Math.min(CM.n - 1, Math.ceil(Math.max(az, bz, cz)));
    if (Math.abs(area) < 1e-6) { // a wall seen edge-on: mark the pixels along it
      for (let v = v0; v <= v1; v++) for (let u = u0; u <= u1; u++) {
        if (u1 - u0 > 1 && v1 - v0 > 1) continue;
        const k = v * CM.n + u; kind[k] = 255; if (hi > top[k]) top[k] = hi;
      }
      continue;
    }
    for (let v = v0; v <= v1; v++) for (let u = u0; u <= u1; u++) {
      const px = u + 0.5, pz = v + 0.5;
      const w0 = ((bx - px) * (cz - pz) - (cx - px) * (bz - pz)) / area;
      const w1 = ((cx - px) * (az - pz) - (ax - px) * (cz - pz)) / area;
      const w2 = 1 - w0 - w1;
      if (w0 < -0.02 || w1 < -0.02 || w2 < -0.02) continue;
      const k = v * CM.n + u; kind[k] = 255; if (hi > top[k]) top[k] = hi;
    }
  }
}
{
  // open ground between houses counts as city ground where buildings are dense nearby
  const dens = new Float32Array(CM.n * CM.n);
  const R = 14;
  const rowAcc = new Float32Array(CM.n * CM.n);
  for (let v = 0; v < CM.n; v++) {
    let s = 0;
    for (let u = 0; u < CM.n; u++) {
      s += kind[v * CM.n + u] >= 110 ? 1 : 0;
      if (u >= 2 * R + 1) s -= kind[v * CM.n + u - 2 * R - 1] >= 110 ? 1 : 0;
      rowAcc[v * CM.n + Math.max(0, u - R)] = s;
    }
  }
  for (let u = 0; u < CM.n; u++) {
    let s = 0;
    for (let v = 0; v < CM.n; v++) {
      s += rowAcc[v * CM.n + u];
      if (v >= 2 * R + 1) s -= rowAcc[(v - 2 * R - 1) * CM.n + u];
      dens[Math.max(0, v - R) * CM.n + u] = s / ((2 * R + 1) ** 2);
    }
  }
  const px = new Uint8Array(CM.n * CM.n * 3);
  let nb = 0;
  for (let v = 0; v < CM.n; v++) for (let u = 0; u < CM.n; u++) {
    const k = v * CM.n + u;
    const x = CM.x0 + (u + 0.5) * cmPx, z = CM.z0 + (v + 0.5) * cmPx;
    const g = terrainAt(x, z);
    if (kind[k] === 0 && dens[k] > 0.12 && !inRing(x, z)) kind[k] = 60;
    if (kind[k] === 255) nb++;
    const e = enc(kind[k] === 255 ? Math.max(top[k], g) : g);
    px[k * 3] = e >> 8; px[k * 3 + 1] = e & 255; px[k * 3 + 2] = kind[k];
  }
  const bytes = writePng(path.join(OUT_ASSETS, 'citymap.png'), CM.n, CM.n, px);
  console.log(`citymap.png: ${(bytes / 1e3).toFixed(0)} kB, ${((nb / (CM.n * CM.n)) * 100).toFixed(0)}% built`);
}

fs.writeFileSync(path.join(OUT_DATA, 'site.json'), JSON.stringify({
  ring,
  roofs: roofItems,
  street: streetItems,
  terrain: { x0: +X0.toFixed(4), z0: +Z0.toFixed(4), step: STEP, n: N, lo: H_LO, span: H_SPAN },
  citymap: { ...CM, lo: H_LO, span: H_SPAN },
}));

// ---------------------------------------------------------------- write city.glb
if (!FAST) {
  const doc = new Document();
  doc.createBuffer();
  const scene = doc.createScene('city');
  for (const m of cityMeshes) {
    const col = m.col || new Float32Array(m.ao.length * 3);
    // red: baked shading. green: 1 on plain rebuilt walls and roofs, 0 on the detail shells. blue: a tone per house.
    if (!m.col) for (let i = 0; i < m.ao.length; i++) { col[i * 3] = m.ao[i]; col[i * 3 + 1] = m.flag ? 1 : 0; col[i * 3 + 2] = m.tint ? m.tint[i] : 0.5; }
    const prim = doc.createPrimitive()
      .setIndices(doc.createAccessor().setType('SCALAR').setArray(m.idx))
      .setAttribute('POSITION', doc.createAccessor().setType('VEC3').setArray(m.pos))
      .setAttribute('COLOR_0', doc.createAccessor().setType('VEC3').setArray(col));
    scene.addChild(doc.createNode(m.name).setMesh(doc.createMesh(m.name).addPrimitive(prim)));
  }
  doc.createExtension(KHRMeshQuantization).setRequired(true);
  doc.createExtension(EXTMeshoptCompression).setRequired(true)
    .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE });
  await doc.transform(quantize({ quantizePosition: 14, quantizeColor: 8 }), reorder({ encoder: MeshoptEncoder }), prune());
  const io = new NodeIO().registerExtensions([EXTMeshoptCompression, KHRMeshQuantization])
    .registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
  const glb = await io.writeBinary(doc);
  fs.writeFileSync(path.join(OUT_ASSETS, ONLY ? 'city-test.glb' : 'city.glb'), glb);
  console.log(`city.glb: ${triOut + fndTris + solidTris.count} triangles, ${(glb.length / 1e6).toFixed(2)} MB`);
}
