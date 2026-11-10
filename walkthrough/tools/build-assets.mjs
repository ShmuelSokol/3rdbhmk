// Converts the measured source geometry in unreal/MikdashCourtyardV3/SourceAssets
// into the compact files the browser walkthrough loads:
//   public/assets/mikdash.glb   merged, quantized, meshopt-compressed geometry
//   src/data/objects.json       name / part of every source object (for tap-to-identify)
//   src/data/tour.json          the 18 tour stops, converted to metres
//   src/data/codex.json         the reference entries the stops link to
//
// World frame written here (three.js): +X east, +Y up, +Z south, metres.
// The Unreal frame is +X east, +Y south, +Z up, centimetres, so
// three = (ux / 100, uz / 100, uy / 100).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

globalThis.window = globalThis;
globalThis.self = globalThis;
globalThis.document = {
  createElementNS: () => ({ style: {}, addEventListener() {}, removeEventListener() {} }),
};

const THREE = await import('three');
const { FBXLoader } = await import('three/examples/jsm/loaders/FBXLoader.js');
const BGU = await import('three/examples/jsm/utils/BufferGeometryUtils.js');
const { Document, NodeIO } = await import('@gltf-transform/core');
const { EXTMeshoptCompression, KHRMeshQuantization } = await import('@gltf-transform/extensions');
const { weld, quantize, reorder, prune } = await import('@gltf-transform/functions');
const { MeshoptEncoder } = await import('meshoptimizer');

const here = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.resolve(here, '../../unreal/MikdashCourtyardV3/SourceAssets');
const OUT_ASSETS = path.resolve(here, '../public/assets');
const OUT_DATA = path.resolve(here, '../src/data');
fs.mkdirSync(OUT_ASSETS, { recursive: true });
fs.mkdirSync(OUT_DATA, { recursive: true });

const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^﻿/, ''));

// ---------------------------------------------------------------- architecture
const manifest = readJson(path.join(SRC, 'architecture-manifest.json'));
const byAsset = new Map(manifest.meshes.map((m) => [m.assetName, m]));

// Which shader family each source material key is drawn with.
const CLASS_OF = {
  stone: 'stone', blue: 'stone', trim: 'stone', altar: 'stone', unclassified: 'stone',
  paving: 'paving', innerPaving: 'paving', goldPaving: 'paving', ground: 'paving',
  gold: 'gold', copper: 'copper', water: 'water', cedar: 'wood',
  dark: 'dark', ash: 'dark', red: 'red',
};

const buf = fs.readFileSync(path.join(SRC, 'architecture.fbx'));
const root = new FBXLoader().parse(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), '');
root.updateMatrixWorld(true);

const buckets = new Map(); // class -> { pos:[], nor:[], col:[], oid:[] }
const bucket = (k) => {
  if (!buckets.has(k)) buckets.set(k, { pos: [], nor: [], col: [], oid: [] });
  return buckets.get(k);
};
const objects = []; // [name, part]
let boundsErr = 0;
let matched = 0;

const v = new THREE.Vector3();
const n = new THREE.Vector3();
root.traverse((o) => {
  if (!o.isMesh) return;
  const info = byAsset.get(o.name);
  if (!info) throw new Error(`FBX mesh ${o.name} is not in the manifest`);
  matched++;
  const g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry;
  const P = g.attributes.position;
  const N = g.attributes.normal;
  const nm = new THREE.Matrix3().getNormalMatrix(o.matrixWorld);
  const mats = Array.isArray(o.material) ? o.material : [o.material];
  const groups = g.groups.length ? g.groups : [{ start: 0, count: P.count, materialIndex: 0 }];
  const oid = objects.length;
  objects.push([info.sourceName.replace(/\s+-?\d+(\s+-?\d+)*$/, ''), info.sourcePart]);

  const bb = new THREE.Box3();
  for (const grp of groups) {
    const fbxName = mats[grp.materialIndex]?.name;
    const slot = info.materialSlots.find((s) => s.fbxMaterialName === fbxName) || info.materialSlots[0];
    const key = slot.sourceMaterialKey;
    const def = slot.sourceMaterialDefinition;
    let cls = CLASS_OF[key] || 'stone';
    if (key === 'unclassified' && def && def.metalness > 0.5) cls = 'gold';
    if (key === 'unclassified' && def && def.color[0] < 0.05) cls = 'dark';
    const color = def && def.color ? def.color : [0.6, 0.75, 0.8];
    const b = bucket(cls);
    for (let i = grp.start; i < grp.start + grp.count; i++) {
      v.fromBufferAttribute(P, i).applyMatrix4(o.matrixWorld);
      bb.expandByPoint(v);
      b.pos.push(v.x, v.y, v.z);
      n.fromBufferAttribute(N, i).applyMatrix3(nm).normalize();
      b.nor.push(n.x, n.y, n.z);
      b.col.push(color[0], color[1], color[2]);
      b.oid.push(oid);
    }
  }
  // Cross-check against the bounds the manifest recorded (Blender metres, Z up, Y north).
  const mb = info.boundsBlenderMeters;
  const e = Math.max(
    Math.abs(bb.min.x - mb.min[0]), Math.abs(bb.max.x - mb.max[0]),
    Math.abs(bb.min.y - mb.min[2]), Math.abs(bb.max.y - mb.max[2]),
    Math.abs(bb.min.z + mb.max[1]), Math.abs(bb.max.z + mb.min[1]),
  );
  boundsErr = Math.max(boundsErr, e);
});
if (matched !== manifest.meshCount) throw new Error(`matched ${matched} of ${manifest.meshCount} meshes`);
if (boundsErr > 0.01) throw new Error(`architecture bounds differ from the manifest by ${boundsErr} m`);
console.log(`architecture: ${matched} meshes, worst bounds error ${(boundsErr * 1000).toFixed(3)} mm`);

// ---------------------------------------------------------------- vessels (OBJ)
function readObj(file) {
  const text = fs.readFileSync(file, 'utf8');
  const vs = [];
  const tris = [];
  for (const line of text.split('\n')) {
    if (line.startsWith('v ')) {
      const p = line.split(/\s+/);
      vs.push(+p[1], +p[2], +p[3]);
    } else if (line.startsWith('f ')) {
      const p = line.trim().split(/\s+/).slice(1).map((t) => parseInt(t, 10) - 1);
      for (let i = 1; i + 1 < p.length; i++) tris.push(p[0], p[i], p[i + 1]);
    }
  }
  return { vs, tris };
}

// Returns a non-indexed position array in the three.js world frame.
function placeObj(file, locCm, yawDeg) {
  const { vs, tris } = readObj(file);
  const c = Math.cos((yawDeg * Math.PI) / 180);
  const s = Math.sin((yawDeg * Math.PI) / 180);
  const out = new Float32Array(tris.length * 3);
  for (let i = 0; i < tris.length; i++) {
    const k = tris[i] * 3;
    const lx = vs[k];
    const ly = -vs[k + 1]; // the OBJ files carry Y reflected for the legacy Unreal importer
    const lz = vs[k + 2];
    const ux = lx * c - ly * s + locCm[0];
    const uy = lx * s + ly * c + locCm[1];
    const uz = lz + locCm[2];
    out[i * 3] = ux / 100;
    out[i * 3 + 1] = uz / 100;
    out[i * 3 + 2] = uy / 100;
  }
  // Make the winding outward (positive signed volume about the centroid).
  let cx = 0, cy = 0, cz = 0;
  for (let i = 0; i < out.length; i += 3) { cx += out[i]; cy += out[i + 1]; cz += out[i + 2]; }
  const cnt = out.length / 3;
  cx /= cnt; cy /= cnt; cz /= cnt;
  let vol = 0;
  for (let i = 0; i < out.length; i += 9) {
    const ax = out[i] - cx, ay = out[i + 1] - cy, az = out[i + 2] - cz;
    const bx = out[i + 3] - cx, by = out[i + 4] - cy, bz = out[i + 5] - cz;
    const dx = out[i + 6] - cx, dy = out[i + 7] - cy, dz = out[i + 8] - cz;
    vol += ax * (by * dz - bz * dy) - ay * (bx * dz - bz * dx) + az * (bx * dy - by * dx);
  }
  if (vol < 0) {
    for (let i = 0; i < out.length; i += 9) {
      for (let k = 0; k < 3; k++) {
        const t = out[i + 3 + k];
        out[i + 3 + k] = out[i + 6 + k];
        out[i + 6 + k] = t;
      }
    }
  }
  return out;
}

const fineOids = [];
function addVessel(cls, name, part, files, locCm, yawDeg, crease = 42, fine = true) {
  const oid = objects.length;
  if (fine) fineOids.push(oid);
  objects.push([name, part]);
  const b = bucket(cls);
  const box = new THREE.Box3();
  let triCount = 0;
  for (const f of files) {
    const pos = placeObj(path.join(SRC, f), locCm, yawDeg);
    let g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g = BGU.mergeVertices(g, 1e-5);
    g = BGU.toCreasedNormals(g, (crease * Math.PI) / 180);
    const P = g.attributes.position;
    const N = g.attributes.normal;
    for (let i = 0; i < P.count; i++) {
      b.pos.push(P.getX(i), P.getY(i), P.getZ(i));
      b.nor.push(N.getX(i), N.getY(i), N.getZ(i));
      b.col.push(1, 1, 1);
      b.oid.push(oid);
      box.expandByPoint(v.fromBufferAttribute(P, i));
    }
    triCount += P.count / 3;
  }
  console.log(`vessel ${name}: ${triCount} triangles`);
  return box;
}

const V = 'vessels-review';
const D = 'sanctuary-detail/DoorsParochesV1';
const FLOOR = 925;
const boxes = {};
const menorahAt = [-5330, 315, FLOOR];
boxes.menorah = addVessel('vgold', 'Menorah', 'heichal',
  ['Base', 'Shaft', 'BranchesL', 'BranchesR', 'Lamps', 'Ornaments'].map((p) => `${V}/MenorahV4/SM_MenorahV4_${p}.obj`),
  menorahAt, -90);
boxes.menorahStep = addVessel('stone', 'Stone of three steps before the Menorah', 'heichal',
  [`${V}/MenorahV4/SM_MenorahV4_StepStone.obj`], menorahAt, -90, 20, false);
const shulchanAt = [-5300, -350, FLOOR];
boxes.shulchan = addVessel('vgold', 'Shulchan', 'heichal',
  ['Table', 'Rings', 'Snifim', 'Kanim', 'Bazichin'].map((p) => `${V}/ShulchanV2/SM_ShulchanV2_${p}.obj`),
  shulchanAt, 0);
addVessel('bread', 'Lechem HaPanim', 'heichal',
  ['LoavesEast', 'LoavesWest'].map((p) => `${V}/ShulchanV2/SM_ShulchanV2_${p}.obj`), shulchanAt, 0);
boxes.goldenAltar = addVessel('vgold', 'Golden altar', 'heichal',
  ['Body', 'Poles'].map((p) => `${V}/IncenseAltarV2/SM_IncenseAltarV2_${p}.obj`), [-4650, 0, FLOOR], 0);
const curtainAt = [-5585, 0, 928];
boxes.paroches = addVessel('cloth', 'Paroches', 'kodesh', [`${D}/SM_ParochesClothV1.obj`], curtainAt, -90, 60);
addVessel('vgold', 'Paroches hem and fixings', 'kodesh',
  [`${D}/SM_ParochesHemV1.obj`, `${D}/SM_ParochesFixingsV1.obj`], curtainAt, -90);

// The approach ring around the courts: the open cheil, its wall, and the soreg beyond it.
// Placements and openings come from the enclosure design; the measured stairs are already
// in the architecture, so the design's own stand-in steps are left out, as it says.
{
  const E = 'FutureMountV1/EnclosureV1';
  const design = readJson(path.join(SRC, E, 'enclosure-design.json'));
  const label = { Cheilslab: ['Cheil', 'paving'], Cheilwall: ['Wall of the cheil', 'stone'], Soreg: ['Soreg', 'soreg'] };
  for (const pl of design.placements) {
    const kind = /EnclosureV1_(Cheilslab|Cheilwall|Soreg)_/.exec(pl.mesh);
    if (!kind || !pl.placeByDefault) continue;
    const [name, cls] = label[kind[1]];
    const box = addVessel(cls, name, 'mount', [`${E}/${pl.mesh}.obj`], pl.location, pl.rotation[1], 20, false);
    const b = pl.plannedWorldBoundsCm;
    const err = Math.max(Math.abs(box.min.x - b.min[0] / 100), Math.abs(box.max.x - b.max[0] / 100),
      Math.abs(box.min.z - b.min[1] / 100), Math.abs(box.max.z - b.max[1] / 100), Math.abs(box.max.y - b.max[2] / 100));
    if (err > 0.02) throw new Error(`${pl.mesh} is ${err} m away from its planned bounds`);
  }
  var precinct = { faces: design.enclosure.outerFacesCm, gates: design.enclosure.gates, block: design.enclosure.gateBlockAmot,
    thicknessCm: design.enclosure.wallThicknessCm, heightCm: design.enclosure.wallHeightCm, cmPerAmah: design.cmPerAmah };
}

// The seven lamp positions, found by splitting the lamp mesh along the lamp row.
function lampTops() {
  const pos = placeObj(path.join(SRC, `${V}/MenorahV4/SM_MenorahV4_Lamps.obj`), menorahAt, -90);
  let zmin = Infinity, zmax = -Infinity;
  for (let i = 2; i < pos.length; i += 3) { zmin = Math.min(zmin, pos[i]); zmax = Math.max(zmax, pos[i]); }
  const cells = Array.from({ length: 7 }, () => ({ x: 0, z: 0, n: 0, y: -Infinity }));
  for (let i = 0; i < pos.length; i += 3) {
    const k = Math.min(6, Math.floor(((pos[i + 2] - zmin) / (zmax - zmin)) * 7));
    cells[k].x += pos[i]; cells[k].z += pos[i + 2]; cells[k].n++;
    cells[k].y = Math.max(cells[k].y, pos[i + 1]);
  }
  return cells.map((c) => [c.x / c.n, c.y, c.z / c.n].map((t) => +t.toFixed(4)));
}
const lamps = lampTops();

// ---------------------------------------------------------------- roof map and plan
// A top-down height map of the architecture. The shaders use it to know how much
// open sky a surface sees (so roofed rooms are dim and courts are bright), and the
// same pass paints the plan shown on the map screen.
const { MeshBVH } = await import('three-mesh-bvh');
import zlib from 'node:zlib';
function writePng(file, w, h, channels, data) {
  const stride = w * channels;
  const raw = Buffer.alloc((stride + 1) * h);
  for (let y = 0; y < h; y++) {
    raw[y * (stride + 1)] = 0;
    Buffer.from(data.buffer, data.byteOffset + y * stride, stride).copy(raw, y * (stride + 1) + 1);
  }
  const chunk = (type, body) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(body.length);
    const td = Buffer.concat([Buffer.from(type), body]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(zlib.crc32(td) >>> 0);
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; ihdr[9] = channels === 4 ? 6 : 2;
  fs.writeFileSync(file, Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0)),
  ]));
}
{
  const EXTENT = 100; // metres either side of the origin
  const SIZE = 1024;
  const MAXH = 80;
  const classes = ['stone', 'paving', 'gold', 'wood', 'dark', 'copper', 'red'];
  const fineSet = new Set(fineOids);
  const all = [];
  const triClass = [];
  for (const cls of classes) {
    const b = buckets.get(cls);
    if (!b) continue;
    // Only the architecture belongs here: vessels were appended after it.
    for (let i = 0; i < b.pos.length; i += 9) {
      if (fineSet.has(b.oid[i / 3]) || objects[b.oid[i / 3]][1] === 'heichal' && b.oid[i / 3] >= manifest.meshCount) continue;
      for (let k = 0; k < 9; k++) all.push(b.pos[i + k]);
      triClass.push(classes.indexOf(cls));
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(all), 3));
  const bvh = new MeshBVH(g, { indirect: true });
  const ray = new THREE.Ray(new THREE.Vector3(), new THREE.Vector3(0, -1, 0));
  const height = new Float32Array(SIZE * SIZE);
  const cls = new Uint8Array(SIZE * SIZE).fill(255);
  for (let j = 0; j < SIZE; j++) {
    for (let i = 0; i < SIZE; i++) {
      ray.origin.set(-EXTENT + ((i + 0.5) / SIZE) * 2 * EXTENT, 200, -EXTENT + ((j + 0.5) / SIZE) * 2 * EXTENT);
      const hit = bvh.raycastFirst(ray, THREE.DoubleSide);
      if (hit) {
        height[j * SIZE + i] = hit.point.y;
        cls[j * SIZE + i] = triClass[hit.faceIndex];
      }
    }
  }
  const roof = new Uint8Array(SIZE * SIZE * 3);
  for (let k = 0; k < SIZE * SIZE; k++) {
    const q = Math.max(0, Math.min(65535, Math.round((height[k] / MAXH) * 65535)));
    roof[k * 3] = q >> 8; roof[k * 3 + 1] = q & 255; roof[k * 3 + 2] = 0;
  }
  writePng(path.join(OUT_ASSETS, 'roof.png'), SIZE, SIZE, 3, roof);

  const tint = [[214, 196, 160], [232, 220, 192], [212, 168, 74], [120, 84, 56], [70, 62, 54], [176, 106, 64], [150, 50, 40]];
  const plan = new Uint8Array(SIZE * SIZE * 4);
  for (let j = 0; j < SIZE; j++) {
    for (let i = 0; i < SIZE; i++) {
      const k = j * SIZE + i;
      if (cls[k] === 255) continue; // transparent outside the building
      const h = height[k];
      const hx = height[j * SIZE + Math.min(SIZE - 1, i + 1)] - height[j * SIZE + Math.max(0, i - 1)];
      const hz = height[Math.min(SIZE - 1, j + 1) * SIZE + i] - height[Math.max(0, j - 1) * SIZE + i];
      const edge = Math.min(1, Math.hypot(hx, hz) / 1.5);
      const lift = 0.62 + 0.38 * Math.min(1, h / 36);
      const shade = lift * (1 - 0.55 * edge) * (1 - Math.max(-0.12, Math.min(0.12, (hx + hz) * 0.02)));
      const t = tint[cls[k]];
      plan[k * 4] = Math.min(255, t[0] * shade);
      plan[k * 4 + 1] = Math.min(255, t[1] * shade);
      plan[k * 4 + 2] = Math.min(255, t[2] * shade);
      plan[k * 4 + 3] = 255;
    }
  }
  writePng(path.join(OUT_ASSETS, 'plan.png'), SIZE, SIZE, 4, plan);
  console.log('roof.png and plan.png written');
}

// ---------------------------------------------------------------- write GLB
await MeshoptEncoder.ready;
const doc = new Document();
doc.createBuffer();
const scene = doc.createScene('mikdash');
let totalTris = 0;
for (const [cls, b] of buckets) {
  const prim = doc.createPrimitive()
    .setAttribute('POSITION', doc.createAccessor().setType('VEC3').setArray(new Float32Array(b.pos)))
    .setAttribute('NORMAL', doc.createAccessor().setType('VEC3').setArray(new Float32Array(b.nor)))
    .setAttribute('COLOR_0', doc.createAccessor().setType('VEC3').setArray(new Float32Array(b.col)))
    .setAttribute('_OID', doc.createAccessor().setType('SCALAR').setArray(new Uint16Array(b.oid)));
  const mesh = doc.createMesh(cls).addPrimitive(prim);
  scene.addChild(doc.createNode(cls).setMesh(mesh));
  totalTris += b.pos.length / 9;
  console.log(`  ${cls.padEnd(8)} ${String(b.pos.length / 9).padStart(7)} triangles`);
}
doc.createExtension(KHRMeshQuantization).setRequired(true);
doc.createExtension(EXTMeshoptCompression).setRequired(true)
  .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE });
await doc.transform(
  weld(),
  quantize({ quantizePosition: 16, quantizeNormal: 10, quantizeColor: 8 }),
  reorder({ encoder: MeshoptEncoder }),
  prune(),
);
const io = new NodeIO()
  .registerExtensions([EXTMeshoptCompression, KHRMeshQuantization])
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
const glb = await io.writeBinary(doc);
fs.writeFileSync(path.join(OUT_ASSETS, 'mikdash.glb'), glb);
console.log(`mikdash.glb: ${totalTris} triangles, ${(glb.length / 1e6).toFixed(2)} MB`);

// ---------------------------------------------------------------- data
// Deduplicate object names: most of the 2,633 objects share a few hundred names.
const names = [];
const nameIdx = new Map();
const objIdx = objects.map(([nm, part]) => {
  const key = `${nm}|${part}`;
  if (!nameIdx.has(key)) { nameIdx.set(key, names.length); names.push([nm, part]); }
  return nameIdx.get(key);
});
const boxOut = {};
for (const [k, bx] of Object.entries(boxes)) {
  boxOut[k] = { min: bx.min.toArray().map((t) => +t.toFixed(3)), max: bx.max.toArray().map((t) => +t.toFixed(3)) };
}
fs.writeFileSync(path.join(OUT_DATA, 'objects.json'), JSON.stringify({ names, index: objIdx, boxes: boxOut, lamps, fine: fineOids, precinct }));

const cm = ([x, y, z]) => [x / 100, z / 100, y / 100];
const tour = readJson(path.join(SRC, 'tour-review/tour-stops.json'));
const stops = tour.stops
  .slice()
  .sort((a, b) => a.order - b.order)
  .map((s) => ({
    key: s.key,
    name: s.name.en,
    he: s.name.he,
    subtitle: s.subtitle.en,
    stand: cm(s.stand),
    look: cm(s.look),
    approach: (s.approach || []).map((p) => cm(Array.isArray(p) ? p : p.point || p.position)),
    confidence: s.confidence,
    what: s.whatHappensHere.en,
    explanation: s.explanation.en,
    measurements: s.measurements.map((m) => ({
      label: m.label.en, amot: m.amot, cm: m.cm, source: m.source, confidence: m.confidence,
    })),
    sources: s.sources,
    codex: s.codexEntries,
  }));
fs.writeFileSync(path.join(OUT_DATA, 'tour.json'), JSON.stringify({
  name: tour.route.name.en,
  description: tour.route.description.en,
  limitations: tour.route.limitations,
  confidenceLabels: tour.confidenceLabels,
  stops,
}));

const codex = readJson(path.join(SRC, 'tour-review/codex-entries.json'));
const txt = (t) => (t && typeof t === 'object' ? t.en : t) || '';
fs.writeFileSync(path.join(OUT_DATA, 'codex.json'), JSON.stringify({
  categories: codex.categories,
  entries: codex.entries.map((e) => ({
    id: e.id,
    category: e.category,
    name: txt(e.name),
    he: e.name.he || '',
    confidence: e.confidence,
    summary: txt(e.summary),
    measurements: (e.measurements || []).map((m) => ({ label: txt(m.label), value: m.value, source: m.source })),
    dispute: e.dispute && e.dispute.positions ? e.dispute.positions.map((p) => ({ who: p.who, holds: p.holds })) : [],
    sources: e.sources || [],
  })),
}));
console.log(`data: ${stops.length} stops, ${codex.entries.length} codex entries, ${names.length} object names`);
