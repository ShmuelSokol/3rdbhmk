// Fire on the altar, its column of smoke, the seven lamps of the Menorah and the
// incense on the golden altar. Everything is animated in the shaders from one clock.
import * as THREE from 'three';

const NOISE = /* glsl */ `
float h21(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float n2(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f);
  return mix(mix(h21(i), h21(i+vec2(1,0)), f.x), mix(h21(i+vec2(0,1)), h21(i+vec2(1,1)), f.x), f.y); }
float fbm2(vec2 p){ float a=.5, s=0.; for(int i=0;i<4;i++){ s+=a*n2(p); p=p*2.02+11.3; a*=.5; } return s; }
`;

const FLAME_VERT = /* glsl */ `
attribute vec4 aSeed;      // xyz = base position, w = phase
attribute vec2 aSize;      // width, height
uniform float uTime;
varying vec2 vUv;
varying float vPhase;
void main(){
  vUv = uv;
  vPhase = aSeed.w;
  vec3 c = aSeed.xyz;
  vec3 toCam = cameraPosition - c; toCam.y = 0.;
  vec3 right = normalize(cross(vec3(0,1,0), normalize(toCam + vec3(1e-4))));
  float sway = sin(uTime * 2.3 + aSeed.w * 6.28) * .06 * uv.y * aSize.x;
  vec3 p = c + right * ((uv.x - .5) * aSize.x + sway) + vec3(0, uv.y * aSize.y, 0);
  gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.);
}`;

const FLAME_FRAG = /* glsl */ `
uniform float uTime;
uniform float uGain;
varying vec2 vUv;
varying float vPhase;
${NOISE}
void main(){
  vec2 uv = vUv;
  float t = uTime * 1.5 + vPhase * 17.;
  float n = fbm2(vec2(uv.x * 3.2 + vPhase * 9., uv.y * 2.6 - t));
  float n2_ = fbm2(vec2(uv.x * 7. - vPhase * 4., uv.y * 5. - t * 1.7));
  float x = abs(uv.x - .5 + (n - .5) * .22 * uv.y) * 2.;
  float body = 1. - smoothstep(0., 1., x * (1. + uv.y * 1.6) + uv.y * .9 - .15);
  float f = body * (.72 + .7 * n) - (1. - n2_) * .32 * uv.y;
  f *= smoothstep(0., .08, uv.y);
  float a = smoothstep(.12, .62, f);
  vec3 col = mix(vec3(.9, .13, .02), vec3(1., .5, .07), smoothstep(.15, .5, f));
  col = mix(col, vec3(1., .86, .45), smoothstep(.45, .85, f));
  col = mix(col, vec3(1., .97, .85), smoothstep(.8, 1.1, f));
  gl_FragColor = vec4(col * a * uGain, a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

const SMOKE_VERT = /* glsl */ `
attribute vec4 aSeed;      // x,z jitter, phase, size jitter
uniform float uTime;
uniform vec3 uBase;
uniform vec4 uShape;       // rise speed, lifetime, start radius, end radius
uniform vec2 uDrift;
varying vec2 vUv;
varying float vAge;
varying float vSeed;
void main(){
  vUv = uv;
  float age = fract(uTime / uShape.y + aSeed.z);
  vAge = age;
  vSeed = aSeed.z;
  float h = age * uShape.y * uShape.x;
  float size = mix(uShape.z, uShape.w, pow(age, .8)) * (.75 + .5 * aSeed.w);
  float spread = age * age * uShape.w * .35;
  vec3 c = uBase + vec3(aSeed.x * (uShape.z * .7 + spread), h, aSeed.y * (uShape.z * .7 + spread));
  c.xz += uDrift * h * age;
  c.x += sin(h * .21 + aSeed.z * 30.) * .12 * size;
  vec3 camRight = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
  vec3 camUp = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
  float rot = aSeed.z * 40. + uTime * .08 * (aSeed.w - .5);
  vec2 q = (uv - .5) * size;
  q = vec2(q.x * cos(rot) - q.y * sin(rot), q.x * sin(rot) + q.y * cos(rot));
  vec3 p = c + camRight * q.x + camUp * q.y;
  gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.);
}`;

const SMOKE_FRAG = /* glsl */ `
uniform vec3 uLit;
uniform vec3 uShade;
uniform float uOpacity;
varying vec2 vUv;
varying float vAge;
varying float vSeed;
${NOISE}
void main(){
  vec2 d = vUv - .5;
  float r = length(d) * 2.;
  float n = fbm2(vUv * 3. + vSeed * 50.);
  float a = smoothstep(1., .25, r + (n - .5) * .7);
  a *= smoothstep(0., .08, vAge) * (1. - smoothstep(.55, 1., vAge));
  vec3 col = mix(uShade, uLit, clamp(.55 + d.y * .9 + (n - .5) * .5, 0., 1.));
  gl_FragColor = vec4(col, a * uOpacity);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

function flames(list, gain) {
  const quad = new THREE.PlaneGeometry(1, 1).translate(0.5, 0.5, 0);
  const g = new THREE.InstancedBufferGeometry();
  g.index = quad.index;
  g.setAttribute('position', quad.attributes.position);
  g.setAttribute('uv', quad.attributes.uv);
  const seed = new Float32Array(list.length * 4);
  const size = new Float32Array(list.length * 2);
  list.forEach((f, i) => {
    seed.set([f.x, f.y, f.z, f.phase], i * 4);
    size.set([f.w, f.h], i * 2);
  });
  g.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seed, 4));
  g.setAttribute('aSize', new THREE.InstancedBufferAttribute(size, 2));
  g.instanceCount = list.length;
  const m = new THREE.ShaderMaterial({
    vertexShader: FLAME_VERT, fragmentShader: FLAME_FRAG,
    uniforms: { uTime: { value: 0 }, uGain: { value: gain } },
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(g, m);
  mesh.frustumCulled = false;
  mesh.renderOrder = 5;
  return mesh;
}

function smoke(count, base, shape, opacity) {
  const quad = new THREE.PlaneGeometry(1, 1).translate(0.5, 0.5, 0);
  const g = new THREE.InstancedBufferGeometry();
  g.index = quad.index;
  g.setAttribute('position', quad.attributes.position);
  g.setAttribute('uv', quad.attributes.uv);
  const seed = new Float32Array(count * 4);
  let s = 12345;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < count; i++) seed.set([rnd() * 2 - 1, rnd() * 2 - 1, (i + rnd() * 0.6) / count, rnd()], i * 4);
  g.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seed, 4));
  g.instanceCount = count;
  const m = new THREE.ShaderMaterial({
    vertexShader: SMOKE_VERT, fragmentShader: SMOKE_FRAG,
    uniforms: {
      uTime: { value: 0 }, uBase: { value: base }, uShape: { value: shape }, uDrift: { value: new THREE.Vector2(0, 0) },
      uLit: { value: new THREE.Color(0.8, 0.78, 0.75) }, uShade: { value: new THREE.Color(0.3, 0.3, 0.32) },
      uOpacity: { value: opacity },
    },
    transparent: true, depthWrite: false,
  });
  const mesh = new THREE.Mesh(g, m);
  mesh.frustumCulled = false;
  mesh.renderOrder = 4;
  return mesh;
}

export function createEffects(scene, objectsData, quality) {
  const group = new THREE.Group();
  scene.add(group);

  // ---- the fire of the ma'arachah on the altar
  const ALTAR_TOP = 10.9;
  const altarFlames = [];
  let s = 7;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 11; i++) {
    const big = i < 4;
    altarFlames.push({
      x: (rnd() - 0.5) * 2.9, y: ALTAR_TOP - 0.05, z: (rnd() - 0.5) * 2.1,
      w: big ? 1.9 + rnd() * 0.7 : 1.0 + rnd() * 0.6, h: big ? 2.6 + rnd() * 1.1 : 1.3 + rnd() * 0.8, phase: rnd(),
    });
  }
  const altarFire = flames(altarFlames, 3.6);
  group.add(altarFire);

  // The pillar of smoke rose straight, and no wind bent it (Avos 5:5).
  const altarSmoke = smoke(quality === 'low' ? 50 : 120, new THREE.Vector3(0, ALTAR_TOP + 1.6, 0), new THREE.Vector4(2.8, 44, 1.8, 22), 0.46);
  group.add(altarSmoke);

  const altarLight = new THREE.PointLight(0xff8a3c, 0, 55, 1.6);
  altarLight.position.set(0, ALTAR_TOP + 1.4, 0);
  group.add(altarLight);

  // ---- the seven lamps
  const lampFlames = objectsData.lamps.map(([x, y, z], i) => ({ x, y: y + 0.004, z, w: 0.05, h: 0.11, phase: i * 0.137 + 0.2 }));
  const menorahFire = flames(lampFlames, 3.2);
  group.add(menorahFire);
  const mid = objectsData.lamps[3];
  const menorahLight = new THREE.PointLight(0xffc27a, 0, 34, 1.5);
  menorahLight.position.set(mid[0] + 0.25, mid[1] + 0.25, mid[2]);
  group.add(menorahLight);

  // Soft fill for the Heikhal and the Ulam: the bounce of that lamplight off gold walls,
  // which a real-time renderer on a phone cannot compute.
  const heikhalFill = new THREE.PointLight(0xffd9a0, 0, 60, 1.2);
  heikhalFill.position.set(-40, 25, 0);
  group.add(heikhalFill);

  // ---- incense on the golden altar
  const ga = objectsData.boxes.goldenAltar;
  const gaTop = new THREE.Vector3((ga.min[0] + ga.max[0]) / 2, ga.max[1] - 0.03, (ga.min[2] + ga.max[2]) / 2);
  const incense = smoke(quality === 'low' ? 14 : 26, gaTop, new THREE.Vector4(0.34, 11, 0.07, 0.62), 0.13);
  incense.material.uniforms.uLit.value.setRGB(0.62, 0.55, 0.45);
  incense.material.uniforms.uShade.value.setRGB(0.3, 0.26, 0.2);
  group.add(incense);
  const ember = flames([{ x: gaTop.x, y: gaTop.y - 0.02, z: gaTop.z, w: 0.16, h: 0.09, phase: 0.4 }], 1.4);
  group.add(ember);

  const mats = [altarFire, menorahFire, ember, altarSmoke, incense].map((m) => m.material);

  function update(dt, time) {
    for (const m of mats) m.uniforms.uTime.value = time;
    const flick = 0.82 + 0.18 * Math.sin(time * 11.3) * Math.sin(time * 7.1 + 1.3) + 0.06 * Math.sin(time * 23.7);
    altarLight.intensity = altarLight.userData.base * flick;
    menorahLight.intensity = menorahLight.userData.base * (0.95 + 0.05 * Math.sin(time * 9.1 + 0.4));
  }

  function setSun(sunDir, t) {
    const day = THREE.MathUtils.clamp(t.elevation / 20, 0.15, 1);
    altarSmoke.material.uniforms.uLit.value.setRGB(0.86 * day + 0.1, 0.82 * day + 0.06, 0.78 * day + 0.04);
    altarSmoke.material.uniforms.uShade.value.setRGB(0.3 * day + 0.03, 0.3 * day + 0.03, 0.33 * day + 0.03);
    // firelight reads stronger as daylight falls away
    altarLight.userData.base = 14 + 150 * (1 - day);
    menorahLight.userData.base = 13;
    heikhalFill.intensity = 11;
  }

  return { update, setSun, group };
}
