// Downloads the scanned people for the lanes of the Old City and fits them for the browser.
//
// The scans are by Renderpeople (renderpeople.com), published on Sketchfab under the Creative
// Commons Attribution licence, which allows publishing them with credit. Sketchfab gives
// downloads only to signed-in accounts, so this needs a free account's API token:
//
//   SKETCHFAB_TOKEN=... node tools/fetch-people.mjs
//
// Output: public/assets/people/<name>.glb (slimmed: fewer triangles, 1024 px textures, meshopt)
// and public/assets/people/people.json, which the walkthrough reads. With no people.json the
// walkthrough simply has no people.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { simplify, weld, textureCompress, prune, dedup, reorder, quantize } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptSimplifier, MeshoptDecoder } from 'meshoptimizer';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '../public/assets/people');
const TMP = process.env.PEOPLE_TMP || path.join(HERE, '../.people-tmp');
const TOKEN = process.env.SKETCHFAB_TOKEN;

const PEOPLE = [
  { name: 'dennis', uid: 'e211ffd52a96416e89c0cc415a388d61', title: 'Dennis Posed 004', pose: 'standing', tris: 14000 },
  { name: 'mei', uid: '07f308b81bc045c8917104a72ce2ffe4', title: 'Mei Posed 001', pose: 'walking-still', tris: 14000 },
  { name: 'fabienne-percy', uid: '8c9bfd4fb8a444b3a42a4fc31935a2fb', title: 'Fabienne & Percy 001', pose: 'standing', tris: 20000 },
  { name: 'nathan', uid: '143a2b1ea5eb4385ae90a73657aca3bc', title: 'Nathan Animated 003', pose: 'walk-animated', tris: 0 },
  { name: 'sophia', uid: 'dc448c3be0e74f96a55fb475a13433cf', title: 'Sophia Animated 003', pose: 'animated', tris: 0 },
  { name: 'eric', uid: 'a46bc9f67aaa415bb4f3241eef900e7f', title: 'Eric Rigged 001', pose: 'rigged', tris: 0 },
  { name: 'claudia', uid: 'c659bd0accab47c6bbe390cf822a2b92', title: 'Claudia Rigged 002', pose: 'rigged', tris: 0 },
  { name: 'carla', uid: 'acf520f450d14dd799f98a6fede3edf5', title: 'Carla Rigged 001', pose: 'rigged', tris: 0 },
];

if (!TOKEN) { console.error('Set SKETCHFAB_TOKEN (a free Sketchfab account API token) to download the scans.'); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(TMP, { recursive: true });
await MeshoptEncoder.ready; await MeshoptDecoder.ready; await MeshoptSimplifier.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
let sharp = null;
try { sharp = (await import('sharp')).default; } catch { console.warn('sharp is not installed: textures keep their full size'); }

const manifest = [];
for (const p of PEOPLE) {
  try {
    const dir = path.join(TMP, p.name);
    fs.mkdirSync(dir, { recursive: true });
    let glb = fs.readdirSync(dir).find((f) => f.endsWith('.glb'));
    if (!glb) {
      const r = await fetch(`https://api.sketchfab.com/v3/models/${p.uid}/download`, { headers: { Authorization: `Token ${TOKEN}` } });
      if (!r.ok) throw new Error(`download link refused: ${r.status} ${await r.text()}`);
      const links = await r.json();
      if (links.glb?.url) {
        fs.writeFileSync(path.join(dir, 'model.glb'), Buffer.from(await (await fetch(links.glb.url)).arrayBuffer()));
      } else if (links.gltf?.url) {
        const zip = path.join(dir, 'model.zip');
        fs.writeFileSync(zip, Buffer.from(await (await fetch(links.gltf.url)).arrayBuffer()));
        execFileSync('unzip', ['-o', '-q', zip, '-d', dir]);
      } else throw new Error('no glb or gltf offered');
      glb = fs.readdirSync(dir).find((f) => f.endsWith('.glb')) || 'scene.gltf';
    }
    const doc = await io.read(path.join(dir, glb));
    const before = doc.getRoot().listMeshes().reduce((s, m) => s + m.listPrimitives().reduce((t, q) => t + (q.getIndices()?.getCount() || q.getAttribute('POSITION').getCount()) / 3, 0), 0);
    const steps = [dedup(), prune()];
    if (p.tris && before > p.tris * 1.2) steps.push(weld(), simplify({ simplifier: MeshoptSimplifier, ratio: p.tris / before, error: 0.004 }));
    if (sharp) steps.push(textureCompress({ encoder: sharp, targetFormat: 'jpeg', resize: [1024, 1024], quality: 82, slots: /baseColor|emissive/ }), textureCompress({ encoder: sharp, resize: [512, 512], slots: /normal|metallicRoughness|occlusion/ }));
    steps.push(quantize({ quantizePosition: 14, quantizeTexcoord: 12 }), reorder({ encoder: MeshoptEncoder }), prune());
    await doc.transform(...steps);
    doc.createExtension(ALL_EXTENSIONS.find((e) => e.EXTENSION_NAME === 'EXT_meshopt_compression')).setRequired(true).setEncoderOptions({ method: 'filter' });
    const file = path.join(OUT, `${p.name}.glb`);
    await io.write(file, doc);
    const after = doc.getRoot().listMeshes().reduce((s, m) => s + m.listPrimitives().reduce((t, q) => t + (q.getIndices()?.getCount() || 0) / 3, 0), 0);
    console.log(`${p.name}: ${Math.round(before)} -> ${Math.round(after)} triangles, ${(fs.statSync(file).size / 1e6).toFixed(2)} MB, animations: ${doc.getRoot().listAnimations().map((a) => a.getName()).join(', ') || 'none'}`);
    manifest.push({ name: p.name, file: `${p.name}.glb`, pose: p.pose, credit: `"${p.title}" by Renderpeople (sketchfab.com/renderpeople), CC BY 4.0`, source: `https://sketchfab.com/3d-models/${p.uid}` });
  } catch (e) {
    console.error(`${p.name}: skipped, ${e.message}`);
  }
}
fs.writeFileSync(path.join(OUT, 'people.json'), JSON.stringify(manifest, null, 1));
console.log(`${manifest.length} of ${PEOPLE.length} people ready in ${OUT}`);
