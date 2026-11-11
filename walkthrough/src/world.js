import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { Sky } from 'three/examples/jsm/objects/Sky.js';
import { MeshBVH } from 'three-mesh-bvh';
import { createMaterials, ROOF_MAX_H } from './materials.js';
import { createEffects } from './effects.js';
import objectsData from './data/objects.json';
import { createSite } from './site.js';

// The four times of day offered in settings. Azimuth is measured from north toward
// east; the House faces east, so the morning sun lights its front.
export const TIMES = {
  morning: { label: 'Morning', elevation: 24, azimuth: 108, exposure: 0.62, turbidity: 3.2, rayleigh: 1.3 },
  midday: { label: 'Midday', elevation: 62, azimuth: 168, exposure: 0.52, turbidity: 2.4, rayleigh: 0.9 },
  afternoon: { label: 'Late afternoon', elevation: 20, azimuth: 248, exposure: 0.64, turbidity: 4.5, rayleigh: 1.6 },
  dusk: { label: 'Dusk', elevation: 6, azimuth: 262, exposure: 0.95, turbidity: 6, rayleigh: 2.6 },
};

const loadTexture = (url) =>
  new Promise((resolve, reject) => new THREE.TextureLoader().load(url, resolve, undefined, reject));

export async function createWorld(renderer, quality, onProgress) {
  const scene = new THREE.Scene();

  // roof.png packs a 16-bit height into red and green. Unpack it into a half-float texture
  // so the GPU can blend neighbouring heights; sampled raw, wall edges came out stair-stepped.
  const roofImg = (await loadTexture('assets/roof.png')).image;
  const cv = document.createElement('canvas');
  cv.width = roofImg.width; cv.height = roofImg.height;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  cx.drawImage(roofImg, 0, 0);
  const px = cx.getImageData(0, 0, cv.width, cv.height).data;
  const heights = new Uint16Array(cv.width * cv.height);
  for (let i = 0; i < heights.length; i++) {
    heights[i] = THREE.DataUtils.toHalfFloat(((px[i * 4] * 256 + px[i * 4 + 1]) / 65535) * ROOF_MAX_H);
  }
  const roofTex = new THREE.DataTexture(heights, cv.width, cv.height, THREE.RedFormat, THREE.HalfFloatType);
  roofTex.magFilter = roofTex.minFilter = THREE.LinearFilter;
  roofTex.needsUpdate = true;
  onProgress(0.08);

  const mats = createMaterials(roofTex, quality);
  // Scanned stone (CC0, Poly Haven) gives the procedural masonry the surface of the real thing.
  await Promise.all([['uStoneD', 'stone_d', true], ['uStoneN', 'stone_n', false], ['uBrickD', 'brick_d', true], ['uBrickN', 'brick_n', false]].map(async ([u, f, colour]) => {
    const t = await loadTexture(`assets/${f}.jpg`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = colour ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = quality === 'low' ? 2 : 8;
    mats.uniforms[u].value = t;
  }));

  // ---------------------------------------------------------------- geometry
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const gltf = await new Promise((resolve, reject) =>
    loader.load('assets/mikdash.glb', resolve, (e) => {
      if (e.total) onProgress(0.08 + 0.72 * (e.loaded / e.total));
    }, reject));
  onProgress(0.82);

  const building = new THREE.Group();
  const pickParts = []; // { positions, oid } for the collider and tap-to-identify
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    const cls = o.name;
    const mesh = new THREE.Mesh(o.geometry, mats.byClass[cls] || mats.byClass.stone);
    mesh.name = cls;
    mesh.castShadow = cls !== 'water' && cls !== 'soreg';
    mesh.receiveShadow = true;
    mesh.matrixAutoUpdate = false;
    // The decoded attributes are quantized integers; the node carries the dequantizing matrix.
    o.updateWorldMatrix(true, false);
    mesh.matrix.copy(o.matrixWorld);
    mesh.matrixWorld.copy(o.matrixWorld);
    if (cls === 'water') mesh.renderOrder = 2;
    building.add(mesh);
    pickParts.push(mesh);
  });
  scene.add(building);

  // ---------------------------------------------------------------- collider
  // One merged triangle soup of the architecture, plus simple boxes for the vessels so
  // nobody walks through the Menorah or behind the paroches.
  const soup = [];
  const soupOid = [];
  const v = new THREE.Vector3();
  const fine = new Set(objectsData.fine); // finely modelled vessels: collide with a box instead
  for (const mesh of pickParts) {
    if (mesh.name === 'water') continue;
    const g = mesh.geometry;
    const P = g.attributes.position;
    const O = g.attributes._oid;
    const idx = g.index;
    const count = idx ? idx.count : P.count;
    for (let i = 0; i < count; i += 3) {
      const a = idx ? idx.getX(i) : i;
      const oid = O ? O.getX(a) : 0;
      if (fine.has(oid)) continue;
      for (let k = 0; k < 3; k++) {
        const j = idx ? idx.getX(i + k) : i + k;
        v.fromBufferAttribute(P, j).applyMatrix4(mesh.matrixWorld);
        soup.push(v.x, v.y, v.z);
      }
      soupOid.push(oid);
    }
  }
  const vesselName = { menorah: 'Menorah', shulchan: 'Shulchan', goldenAltar: 'Golden altar', paroches: 'Paroches' };
  const nameToOid = (nm) => objectsData.index.findIndex((ni) => objectsData.names[ni][0] === nm);
  for (const [key, bx] of Object.entries(objectsData.boxes)) {
    if (!vesselName[key]) continue;
    const min = new THREE.Vector3(...bx.min);
    const max = new THREE.Vector3(...bx.max);
    if (key === 'paroches') { min.x -= 0.25; max.x += 0.25; min.z -= 0.3; max.z += 0.3; max.y += 0.4; }
    const box = new THREE.BoxGeometry(max.x - min.x, max.y - min.y, max.z - min.z).toNonIndexed();
    box.translate((max.x + min.x) / 2, (max.y + min.y) / 2, (max.z + min.z) / 2);
    const oid = nameToOid(vesselName[key]);
    const bp = box.attributes.position;
    for (let i = 0; i < bp.count; i++) soup.push(bp.getX(i), bp.getY(i), bp.getZ(i));
    for (let i = 0; i < bp.count / 3; i++) soupOid.push(oid);
  }
  onProgress(0.9);

  // ---------------------------------------------------------------- surroundings
  // The Mount as it lies today: real ground, the platform and its edge, the Old City.
  const wallMat = mats.byClass.stone.clone();
  wallMat.onBeforeCompile = mats.byClass.stone.onBeforeCompile;
  wallMat.customProgramCacheKey = mats.byClass.stone.customProgramCacheKey;
  wallMat.vertexColors = false;
  wallMat.color.set(0xd9c9a4);
  const site = await createSite(scene, mats, quality, soup, soupOid, wallMat);

  const colliderGeo = new THREE.BufferGeometry();
  colliderGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(soup), 3));
  const bvh = new MeshBVH(colliderGeo, { indirect: true });
  colliderGeo.boundsTree = bvh;
  const collider = new THREE.Mesh(colliderGeo, new THREE.MeshBasicMaterial());

  // Far hills in three ranges, each paler and bluer than the one before, so the land has depth.
  for (const [R, H0, seed, tint] of [[3300, 170, 0, [0.60, 0.58, 0.50]], [4600, 300, 2.1, [0.63, 0.65, 0.65]], [6200, 440, 4.7, [0.66, 0.72, 0.80]]]) {
    const ring = new THREE.CylinderGeometry(R, R, 1, 220, 7, true);
    const P = ring.attributes.position;
    const col = new Float32Array(P.count * 3);
    const ridge = (a, f, ph) => 1 - Math.abs(Math.sin(a * f + ph));
    const crest = (a) => 0.42 * ridge(a, 2.5, seed) + 0.27 * ridge(a, 6.5, seed * 2.3 + 1) + 0.17 * ridge(a, 14.5, seed + 3) + 0.09 * ridge(a, 33.5, seed * 1.7) + 0.05 * ridge(a, 71.5, seed + 0.4);
    for (let i = 0; i < P.count; i++) {
      const a = Math.atan2(P.getZ(i), P.getX(i));
      const t = P.getY(i) + 0.5; // 0 bottom .. 1 top
      const h = H0 * (0.45 + 0.75 * crest(a));
      const r = R - (1 - t) * 1300 + 60 * Math.sin(a * 23 + t * 5 + seed);
      P.setXYZ(i, Math.cos(a) * r, t * t * h - 300 * (1 - t) - 20, Math.sin(a) * r);
      const c = 0.72 + 0.34 * t + 0.1 * Math.sin(a * 57 + t * 9 + seed);
      col.set([tint[0] * c, tint[1] * c, tint[2] * c], i * 3);
    }
    ring.setAttribute('color', new THREE.BufferAttribute(col, 3));
    ring.computeVertexNormals();
    const hills = new THREE.Mesh(ring, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false }));
    scene.add(hills);
  }

  // ---------------------------------------------------------------- sky and light
  const sky = new Sky();
  sky.scale.setScalar(20000);
  sky.material.uniforms.mieCoefficient.value = 0.004;
  sky.material.uniforms.mieDirectionalG.value = 0.82;
  scene.add(sky);

  // Fair-weather clouds: one high sheet of drifting noise, lit from the sun's side.
  const cloudMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false,
    uniforms: { uSun: { value: new THREE.Vector3(0, 1, 0) }, uLit: { value: new THREE.Color(1, 1, 1) }, uShade: { value: new THREE.Color(0.7, 0.75, 0.82) }, uTime: { value: 0 }, uCover: { value: 0.5 } },
    vertexShader: /* glsl */ `
      varying vec3 vP;
      void main(){ vec4 w = modelMatrix * vec4(position, 1.); vP = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; gl_Position.z = gl_Position.w * .99999; }`,
    fragmentShader: /* glsl */ `
      varying vec3 vP;
      uniform vec3 uSun, uLit, uShade; uniform float uTime, uCover;
      float h2(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
      float n2(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
        return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y); }
      float fbm(vec2 p){ float a = .5, s = 0.; for (int i = 0; i < 5; i++){ s += a * n2(p); p = p * 2.07 + 11.3; a *= .5; } return s; }
      float dens(vec2 p){ float b = fbm(p), w = fbm(p * .27 + 40.); return b * .7 + .3 * w - .14 * (1. - smoothstep(.35, .6, w)); }
      void main(){
        vec2 p = vP.xz * .00095 + vec2(uTime * .0016, uTime * .0006);
        float d = dens(p);
        float a = smoothstep(uCover, uCover + .1, d);
        // thinner toward the sun means brighter: a cheap stand-in for light through the cloud
        float d2 = dens(p + normalize(uSun.xz + 1e-4) * .09);
        float lit = clamp(.62 + (d - d2) * 3.2 + (1. - a) * .35, 0., 1.);
        vec3 c = mix(uShade, uLit, lit);
        float r = length(vP.xz - cameraPosition.xz);
        a *= .92 * (1. - smoothstep(4500., 12500., r));
        if (a < .004) discard;
        gl_FragColor = vec4(c, a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const clouds = new THREE.Mesh(new THREE.CircleGeometry(13000, 40).rotateX(Math.PI / 2), cloudMat);
  clouds.position.y = 1500;
  clouds.renderOrder = 1;
  clouds.frustumCulled = false;
  scene.add(clouds);

  const sun = new THREE.DirectionalLight(0xffffff, 3);
  sun.castShadow = true;
  const smap = quality === 'high' ? 4096 : quality === 'medium' ? 2048 : 1024;
  sun.shadow.mapSize.set(smap, smap);
  const SH = quality === 'low' ? 55 : 80;
  Object.assign(sun.shadow.camera, { left: -SH, right: SH, top: SH, bottom: -SH, near: 10, far: 520 });
  const shadowTexel = (2 * SH) / smap;
  sun.shadow.normalBias = shadowTexel * 1.6;
  scene.add(sun, sun.target);

  const hemi = new THREE.HemisphereLight(0xcfe0ff, 0x9a7f58, 0.6);
  scene.add(hemi);

  scene.fog = new THREE.FogExp2(0xd8dde0, 0.00032);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const envScene = new THREE.Scene();
  const envSky = new Sky();
  envSky.scale.setScalar(1000);
  envScene.add(envSky);
  // a warm floor under the env sky, so metal reflects stone below rather than a black void
  const envFloor = new THREE.Mesh(new THREE.CircleGeometry(900, 24).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x8a7a5c }));
  envFloor.position.y = -2;
  envScene.add(envFloor);
  let envTarget = null;

  const sunDir = new THREE.Vector3();
  let timeKey = 'morning';
  function setTime(key) {
    const t = TIMES[key] || TIMES.morning;
    timeKey = TIMES[key] ? key : 'morning';
    const phi = THREE.MathUtils.degToRad(90 - t.elevation);
    // azimuth from north (-Z) toward east (+X)
    const az = THREE.MathUtils.degToRad(t.azimuth);
    sunDir.set(Math.sin(phi) * Math.sin(az), Math.cos(phi), -Math.sin(phi) * Math.cos(az));
    for (const s of [sky, envSky]) {
      const u = s.material.uniforms;
      u.sunPosition.value.copy(sunDir);
      u.turbidity.value = t.turbidity;
      u.rayleigh.value = t.rayleigh;
    }
    const warmth = THREE.MathUtils.clamp(1 - t.elevation / 45, 0, 1);
    sun.color.setRGB(1, 1 - 0.28 * warmth, 1 - 0.55 * warmth);
    sun.intensity = 3.4 * THREE.MathUtils.clamp(t.elevation / 9, 0.12, 1);
    sun.shadow.bias = -Math.min(0.004, ((shadowTexel / Math.tan(THREE.MathUtils.degToRad(t.elevation))) / 510) * 1.5);
    hemi.intensity = 0.62 + 0.2 * (1 - warmth);
    hemi.color.setRGB(0.97 + 0.03 * warmth, 0.95 - 0.02 * warmth, 0.97 - 0.15 * warmth);
    scene.fog.color.setRGB(0.70 + 0.16 * warmth, 0.72 - 0.02 * warmth, 0.72 - 0.16 * warmth);
    cloudMat.uniforms.uSun.value.copy(sunDir);
    cloudMat.uniforms.uLit.value.setRGB(1.3, 1.3 - 0.3 * warmth, 1.3 - 0.62 * warmth);
    cloudMat.uniforms.uShade.value.setRGB(0.62 + 0.2 * warmth, 0.68 - 0.05 * warmth, 0.8 - 0.2 * warmth);
    cloudMat.uniforms.uCover.value = t.cover ?? 0.52;
    baseExposure = t.exposure;
    renderer.toneMappingExposure = baseExposure * (1 + 1.5 * adapt);
    if (envTarget) envTarget.dispose();
    envTarget = pmrem.fromScene(envScene, 0, 1, 2000);
    scene.environment = envTarget.texture;
    scene.environmentIntensity = 0.3;
    effects.setSun(sunDir, t);
  }

  const effects = createEffects(scene, objectsData, quality);

  // Keep the shadow box centred near the visitor, snapped to texels so edges do not crawl.
  const texel = (2 * SH) / smap;
  // The eye adapts: under a roof the exposure opens up, in the open courts it closes.
  const upRay = new THREE.Ray(new THREE.Vector3(), new THREE.Vector3(0, 1, 0));
  let adapt = 0;
  let curS = SH;
  let baseExposure = 0.6;
  function update(dt, time, camPos) {
    mats.uniforms.uTime.value = time;
    cloudMat.uniforms.uTime.value = time;
    clouds.position.x = camPos.x; clouds.position.z = camPos.z;
    upRay.origin.copy(camPos);
    const roofed = bvh.raycastFirst(upRay, THREE.DoubleSide, 0, 70) ? 1 : 0;
    adapt += (roofed - adapt) * Math.min(1, dt * 1.6);
    renderer.toneMappingExposure = baseExposure * (1 + 1.5 * adapt);
    // From far off or high up one wide box covers the whole House; close by a tight one follows the visitor.
    const S = camPos.y > 35 || Math.hypot(camPos.x, camPos.z) > 150 ? 215 : SH;
    if (S !== curS) {
      curS = S;
      Object.assign(sun.shadow.camera, { left: -S, right: S, top: S, bottom: -S });
      sun.shadow.camera.updateProjectionMatrix();
      sun.shadow.normalBias = ((2 * S) / smap) * 1.6;
    }
    const tx = (2 * S) / smap;
    const cx = S > SH ? -20 : Math.round(camPos.x / tx) * tx;
    const cz = S > SH ? 0 : Math.round(camPos.z / tx) * tx;
    sun.target.position.set(cx, 0, cz);
    sun.position.copy(sun.target.position).addScaledVector(sunDir, 260);
    sun.target.updateMatrixWorld();
    effects.update(dt, time, camPos);
  }

  // ---------------------------------------------------------------- queries
  const ray = new THREE.Ray();
  const down = new THREE.Vector3(0, -1, 0);
  /** Height of the highest walkable surface at or below `fromY`, or null. */
  function groundBelow(x, fromY, z) {
    ray.origin.set(x, fromY, z);
    ray.direction.copy(down);
    const hit = bvh.raycastFirst(ray, THREE.DoubleSide);
    return hit ? hit.point.y : null;
  }
  function segmentClear(a, b) {
    const d = v.subVectors(b, a);
    const len = d.length();
    if (len < 1e-4) return true;
    ray.origin.copy(a);
    ray.direction.copy(d).divideScalar(len);
    const hit = bvh.raycastFirst(ray, THREE.DoubleSide, 0, len);
    return !hit;
  }
  /** Name of the object under a camera ray, for tap-to-identify. */
  function identify(raycasterRay, maxDist = 250) {
    const hit = bvh.raycastFirst(raycasterRay, THREE.DoubleSide, 0, maxDist);
    if (!hit) return null;
    const oid = soupOid[hit.faceIndex];
    if (oid <= -2) return { name: 'Wall of the Mount', part: 'mount', point: hit.point, distance: hit.distance };
    if (oid == null || oid < 0) return { name: 'Paving of the Mount', part: 'mount', point: hit.point, distance: hit.distance };
    const [name, part] = objectsData.names[objectsData.index[oid]];
    return { name, part, point: hit.point, distance: hit.distance };
  }

  setTime('morning');
  onProgress(1);

  return {
    get roofed() { return adapt; },
    scene, collider, bvh, mats, effects, setTime, update, groundBelow, segmentClear, identify,
    terrainAt: site.terrainAt, topAt: site.topAt, onDeck: site.onDeck, loadCity: site.loadCity,
    get timeKey() { return timeKey; },
    triangles: soup.length / 9,
  };
}
