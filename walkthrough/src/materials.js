// Procedural materials. Nothing here is a photo texture: every block of stone gets its
// own tone from a hash of its position, so no tile ever repeats across a wall.
import * as THREE from 'three';

export const ROOF_EXTENT = 100; // metres either side of the origin covered by roof.png
export const ROOF_MAX_H = 80;

const COMMON_VERT_PARS = /* glsl */ `
varying vec3 vWPos;
varying vec3 vWNrm;
`;

const COMMON_FRAG_PARS = /* glsl */ `
varying vec3 vWPos;
varying vec3 vWNrm;
uniform sampler2D uRoof;
uniform float uSkyTaps;
uniform float uDetail;

float hash11(float p){ p = fract(p * .1031); p *= p + 33.33; p *= p + p; return fract(p); }
float hash21(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float hash31(vec3 p){ p = fract(p * .1031); p += dot(p, p.zyx + 31.32); return fract((p.x + p.y) * p.z); }
float vnoise(vec3 p){
  vec3 i = floor(p), f = fract(p);
  f = f * f * (3. - 2. * f);
  return mix(mix(mix(hash31(i), hash31(i + vec3(1,0,0)), f.x),
                 mix(hash31(i + vec3(0,1,0)), hash31(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(hash31(i + vec3(0,0,1)), hash31(i + vec3(1,0,1)), f.x),
                 mix(hash31(i + vec3(0,1,1)), hash31(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float fbm(vec3 p){
  float a = .5, s = 0.;
  for (int i = 0; i < 4; i++){ s += a * vnoise(p); p = p * 2.03 + 17.1; a *= .5; }
  return s;
}

float roofHeight(vec2 xz){
  vec2 uv = xz / ${(ROOF_EXTENT * 2).toFixed(1)} + .5;
  if (uv.x < 0. || uv.x > 1. || uv.y < 0. || uv.y > 1.) return -100.;
  return texture2D(uRoof, uv).r;
}
// How much open sky this point sees, 0..1, from a top-down height map of the building.
float skyTap(vec2 xz, float y){ return smoothstep(-.9, .5, y - roofHeight(xz)); }
float skyVisibility(vec3 p, vec3 n){
  vec2 base = p.xz + n.xz * 1.1;
  float y = p.y + .45;
  float s = skyTap(base, y);
  s += skyTap(base + vec2( 1.7,  .6), y);
  s += skyTap(base + vec2(-1.1, 1.5), y);
  s += skyTap(base + vec2( -.7,-1.8), y);
  s += skyTap(base + vec2( 1.3,-1.2), y);
  if (uSkyTaps > 5.5) {
    s += skyTap(base + vec2( 3.4,  .2), y);
    s += skyTap(base + vec2(-3.1,  .9), y);
    s += skyTap(base + vec2(  .4, 3.3), y);
    s += skyTap(base + vec2( -.6,-3.4), y);
    return s / 9.;
  }
  return s / 5.;
}

// 1 inside the Heikhal and the Kodesh HaKodashim, whose walls were overlaid with gold.
float inHouse(vec3 p){
  return step(-67.3, p.x) * step(p.x, -35.9) * step(abs(p.z), 5.06) * step(9.2, p.y) * step(p.y, 29.5);
}
float sdSeg(vec2 p, vec2 a, vec2 b){
  vec2 pa = p - a, ba = b - a;
  return length(pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0., 1.));
}
// Height of a palm tree in low relief (Yechezkel 41:18), 0..1, in a panel 2.5 m wide.
float palmRelief(vec2 p){
  if (abs(p.x) > 1.05 || p.y < .5 || p.y > 4.5) return 0.;
  float d = sdSeg(p, vec2(0., .6), vec2(0., 3.05)) - mix(.085, .055, clamp((p.y - .6) / 2.4, 0., 1.));
  // scales on the trunk
  float h = smoothstep(.02, -.02, d) * (.75 + .25 * sin(p.y * 34. + abs(p.x) * 30.));
  vec2 c = vec2(0., 3.05);
  for (int i = 0; i < 9; i++){
    float a = (float(i) - 4.) * .37;
    float L = 1.12 - .05 * abs(float(i) - 4.);
    vec2 dir = vec2(sin(a), cos(a));
    vec2 p1 = c + dir * L * .45;
    vec2 p2 = c + dir * L * .8 + vec2(0., -.10 - .16 * abs(sin(a)));
    vec2 p3 = c + dir * L + vec2(sign(a) * .05, -.34 - .36 * abs(sin(a)));
    float fd = min(min(sdSeg(p, c, p1), sdSeg(p, p1, p2)), sdSeg(p, p2, p3));
    float along = clamp(distance(p, c) / L, 0., 1.);
    // a leaf-shaped blade: widest a third of the way out, feathered along its edge
    float w = .035 + .085 * sin(3.14159 * pow(along, .7)) * (.82 + .18 * sin(along * 46.));
    h = max(h, smoothstep(w, w - .04, fd));
  }
  // cluster of dates under the crown
  h = max(h, smoothstep(.13, .08, length((p - vec2(0., 2.86)) * vec2(1., 1.5))) * .8);
  return h;
}

// Returns block id in xy and distance to the nearest joint (metres) in z.
vec3 ashlar(vec2 uv, float courseH, float blockL){
  float row = floor(uv.y / courseH);
  float len = blockL * (.75 + .6 * hash11(row * 7.13 + 3.7));
  float x = uv.x + len * hash11(row * 3.31 + 1.9);
  float col = floor(x / len);
  float fx = (x / len - col) * len;
  float fy = uv.y - row * courseH;
  float d = min(min(fx, len - fx), min(fy, courseH - fy));
  return vec3(col, row, d);
}

vec3 bumpNormal(vec3 N, vec3 viewPos, float h, float strength){
  vec3 dpdx = dFdx(viewPos), dpdy = dFdy(viewPos);
  float dhdx = dFdx(h), dhdy = dFdy(h);
  vec3 r1 = cross(dpdy, N), r2 = cross(N, dpdx);
  float det = dot(dpdx, r1);
  vec3 grad = sign(det) * (dhdx * r1 + dhdy * r2);
  return normalize(abs(det) * N - strength * grad);
}
`;

export function install(material, { fragPars = '', color = '', rough = '', normal = '', sky = true, uniforms }) {
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\n${COMMON_VERT_PARS}`)
      .replace('#include <beginnormal_vertex>', '#include <beginnormal_vertex>\n vWNrm = normalize(mat3(modelMatrix) * objectNormal);')
      .replace('#include <project_vertex>', '#include <project_vertex>\n vWPos = (modelMatrix * vec4(transformed, 1.)).xyz;');
    let f = shader.fragmentShader
      .replace('#include <common>', `#include <common>\n${COMMON_FRAG_PARS}\n${fragPars}`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n float mkBump = 0.; float mkBumpK = 0.; float mkRough = 0.; float mkMetal = 0.;\n vec3 wN = normalize(vWNrm);\n float camDist = length(vViewPosition);\n${color}`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>\n roughnessFactor = clamp(roughnessFactor + mkRough, .04, 1.);\n${rough}`)
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\n metalnessFactor = mix(metalnessFactor, 1., mkMetal);')
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>\n if (mkBumpK > 0.) normal = bumpNormal(normal, -vViewPosition, mkBump, mkBumpK);\n${normal}`);
    if (sky) {
      f = f.replace('#include <aomap_fragment>', `#include <aomap_fragment>
        float mkSky = skyVisibility(vWPos, wN);
        float mkAmb = mix(.10, 1., mkSky * mkSky);
        reflectedLight.indirectDiffuse *= mkAmb;
        reflectedLight.indirectSpecular *= mix(vec3(.34, .24, .12), vec3(1.), mkSky);`);
    }
    shader.fragmentShader = f;
  };
  material.customProgramCacheKey = () => color.length + ':' + fragPars.length + ':' + rough.length;
  return material;
}

export function createMaterials(roofTexture, quality) {
  const uniforms = {
    uRoof: { value: roofTexture },
    uSkyTaps: { value: quality === 'low' ? 5 : 9 },
    uDetail: { value: quality === 'low' ? 0.6 : 1 },
    uTime: { value: 0 },
  };

  // ---- wall stone: coursed ashlar with drafted margins
  const stone = install(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.86, metalness: 0 }), {
    uniforms,
    color: /* glsl */ `
      {
        vec3 base = diffuseColor.rgb;
        // steer the flat source tints toward warm Jerusalem limestone
        float lum = dot(base, vec3(.3, .5, .2));
        vec3 lime = vec3(.80, .64, .43) * (.5 + .8 * lum);
        base = mix(base, lime, .7);
        float up = wN.y;
        vec3 ash;
        float tone;
        vec2 uv;
        if (abs(up) < .6) {
          uv = abs(wN.x) > abs(wN.z) ? vec2(vWPos.z, vWPos.y) : vec2(vWPos.x, vWPos.y);
          ash = ashlar(uv, .75, 1.7);
          tone = hash21(ash.xy + floor(uv.x * .013) * 7.);
        } else {
          uv = vWPos.xz;
          ash = ashlar(uv.yx, 1.0, 1.5);
          tone = hash21(ash.xy + 91.);
        }
        // metres covered by one pixel: joints and block tones melt away before they can shimmer
        float px = max(length(fwidth(uv)), 1e-4);
        float fade = 1. - smoothstep(.05, .32, px);
        float joint = (1. - smoothstep(.008, .008 + px * 1.6, ash.z)) * clamp(.05 / (px * 1.6 + .012), 0., 1.) * (1. - smoothstep(.3, .8, px));
        tone = mix(.5, tone, 1. - smoothstep(.08, .35, px));
        float aa = px;
        float margin = smoothstep(.05, .05 + aa * 2., ash.z);   // 0 on the drafted margin, 1 on the boss
        float grain = fbm(vWPos * 5.5);
        float coarse = fbm(vWPos * .32 + 4.);
        float fine = vnoise(vWPos * 42.);
        // block-to-block variation: brightness and a slight swing between cream and honey
        vec3 warm = base * vec3(1.03, .98, .90);
        vec3 cool = base * vec3(.98, .99, 1.02);
        vec3 c = mix(cool, warm, tone) * (.93 + .14 * mix(.5, hash11(tone * 91.7), 1. - smoothstep(.08, .35, px)));
        c *= .94 + .12 * fbm(vWPos * 1.1 + tone * 20.);
        c *= mix(1., .8 + .4 * grain, .55 * fade + .15);
        c *= .9 + .2 * coarse;
        c *= mix(1.045, 1., margin * fade);
        // rain streaks and dust settle low on walls
        float streak = fbm(vec3(vWPos.x * 1.6 + vWPos.z * 1.6, vWPos.y * .12, 3.));
        c *= 1. - .16 * smoothstep(.5, .8, streak) * (1. - abs(up));
        c = mix(c, c * vec3(.42, .38, .33), joint * .85);
        c *= .97 + .06 * fine * fade;
        diffuseColor.rgb = c;
        mkBump = (margin * (.35 + .65 * grain) - joint * 1.4) * .012 + fine * .0012;
        mkBumpK = fade * uDetail;
        mkRough = (grain - .5) * .16 + joint * .08;
        bool nearWall = abs(vWPos.z) > 4.9 || vWPos.x < -66.8 || vWPos.x > -36.2 || (vWPos.x < -56.9 && vWPos.x > -57.2) || vWPos.y > 28.;
        if (inHouse(vWPos) > .5 && nearWall) {
          if (up < -.5) {
            // cedar ceiling in coffers
            vec2 q = fract(vWPos.xz / 2.5) - .5;
            float rib = smoothstep(.36, .42, max(abs(q.x), abs(q.y)));
            float g2 = fbm(vec3(vWPos.x * 8., vWPos.z * .8, 2.));
            diffuseColor.rgb = mix(vec3(.20, .095, .045), vec3(.34, .17, .08), g2) * mix(.62, 1., rib);
            mkBump = rib * .03; mkBumpK = fade; mkRough = -.2;
          } else {
            // gilded panels, a palm between frame and frame
            float along = abs(wN.x) > abs(wN.z) ? vWPos.z + 5. : vWPos.x + 67.;
            float pu = along / 2.5;
            float col = floor(pu);
            vec2 pp = vec2((pu - col - .5) * 2.5, mod(vWPos.y - 9.25, 5.));
            float tier = floor((vWPos.y - 9.25) / 5.);
            float edge = min(min(pp.x + 1.25, 1.25 - pp.x), min(pp.y, 5. - pp.y));
            float frame = smoothstep(.10, .14, edge) - .5 * smoothstep(.20, .24, edge);
            float palm = (mod(col, 2.) < .5 && tier < 2.5) ? palmRelief(pp) : 0.;
            float hammer = vnoise(vWPos * 30.) * .6 + vnoise(vWPos * 70.) * .4;
            float pat = fbm(vWPos * 1.7);
            diffuseColor.rgb = vec3(1., .77, .34) * (.96 + .05 * pat) * (1. - .22 * (1. - smoothstep(.0, .03, edge)));
            diffuseColor.rgb *= 1. + .10 * palm;
            mkMetal = 1.;
            mkBump = frame * .012 + palm * .02 + hammer * .0012;
            mkBumpK = 1. - smoothstep(.02, .12, px);
            mkRough = -.46 + (pat - .5) * .06 - palm * .05;
          }
        }
      }`,
  });

  // ---- paving: large honed slabs
  const paving = install(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.74, metalness: 0 }), {
    uniforms,
    color: /* glsl */ `
      {
        vec3 base = diffuseColor.rgb;
        float lum = dot(base, vec3(.3, .5, .2));
        base = mix(base, vec3(.80, .68, .49) * (.5 + .8 * lum), .7);
        vec2 uv = abs(wN.y) > .5 ? vWPos.xz : (abs(wN.x) > abs(wN.z) ? vec2(vWPos.z, vWPos.y * 2.) : vec2(vWPos.x, vWPos.y * 2.));
        vec3 ash = ashlar(uv, 1.0, 1.5);
        float px = max(length(fwidth(uv)), 1e-4);
        float fade = 1. - smoothstep(.05, .32, px);
        float tone = mix(.5, hash21(ash.xy + 5.), 1. - smoothstep(.12, .5, px));
        float joint = (1. - smoothstep(.006, .006 + px * 1.6, ash.z)) * clamp(.04 / (px * 1.6 + .01), 0., 1.) * (1. - smoothstep(.3, .8, px));
        float grain = fbm(vWPos * 4.);
        float veins = fbm(vec3(vWPos.xz * .7, tone * 8.));
        float coarse = fbm(vWPos * .12 + 9.);
        vec3 c = base * (.9 + .2 * tone) * mix(vec3(1.03, 1., .95), vec3(.98, 1., 1.03), hash11(tone * 37.));
        c *= .9 + .2 * grain * fade;
        c *= .93 + .14 * coarse;
        c *= 1. - .1 * smoothstep(.55, .7, veins) * fade;
        c = mix(c, c * vec3(.5, .46, .40), joint * .6);
        diffuseColor.rgb = c;
        mkBump = -joint * .012 + grain * .002;
        mkBumpK = fade * uDetail;
        mkRough = (veins - .5) * .25 - .08 * tone;
        if (inHouse(vWPos + vec3(0., .1, 0.)) > .5) {
          diffuseColor.rgb = mix(c, vec3(.86, .64, .30) * (.8 + .3 * veins), .78);
          mkMetal = .3;
          mkRough = -.50 + (veins - .5) * .12;
          mkBump *= .4;
        }
      }`,
  });

  // ---- architectural gold: hammered sheet, takes its tint from the source colour
  const goldCode = /* glsl */ `
      {
        float hammer = vnoise(vWPos * 26.) * .6 + vnoise(vWPos * 61.) * .4;
        float patina = fbm(vWPos * 1.3);
        diffuseColor.rgb = vec3(1.0, .76, .33) * (.92 + .14 * patina);
        float fade = 1. - smoothstep(8., 40., camDist);
        mkBump = hammer * .0016;
        mkBumpK = fade * uDetail;
        mkRough = (patina - .5) * .22;
      }`;
  const gold = install(new THREE.MeshStandardMaterial({ roughness: 0.3, metalness: 1, envMapIntensity: 1.25 }), {
    uniforms, color: goldCode,
  });
  const vgold = install(new THREE.MeshStandardMaterial({ roughness: 0.2, metalness: 1, envMapIntensity: 1.5 }), {
    uniforms,
    color: /* glsl */ `
      {
        float patina = fbm(vWPos * 9.);
        diffuseColor.rgb = vec3(1.0, .78, .36) * (.94 + .1 * patina);
        mkRough = (patina - .5) * .14;
      }`,
  });

  const copper = install(new THREE.MeshStandardMaterial({ roughness: 0.3, metalness: 1, envMapIntensity: 1.2 }), {
    uniforms,
    color: /* glsl */ `
      {
        float patina = fbm(vWPos * 6.);
        diffuseColor.rgb = mix(vec3(.93, .52, .33), vec3(.72, .36, .22), patina);
        mkRough = (patina - .45) * .3;
      }`,
  });

  const wood = install(new THREE.MeshStandardMaterial({ roughness: 0.62, metalness: 0 }), {
    uniforms,
    color: /* glsl */ `
      {
        // cedar boards: grain runs along the longer horizontal axis, vertical on leaves
        vec3 q = abs(wN.y) > .5 ? vWPos.xzy : (abs(wN.x) > abs(wN.z) ? vWPos.zyx : vWPos.xyz);
        float board = floor(q.x / .32);
        float rings = fbm(vec3(q.x * 9., q.y * .55, board * 3.1));
        float line = sin((q.y * .6 + rings * 2.2) * 34.) * .5 + .5;
        vec3 c = mix(vec3(.36, .17, .085), vec3(.56, .30, .15), rings);
        c *= .82 + .22 * line;
        c *= .88 + .24 * hash11(board * 1.7);
        float gap = smoothstep(.0, .012, abs(fract(q.x / .32) - .5) * .32 - .147);
        c *= 1. - .5 * gap;
        diffuseColor.rgb = c;
        mkBump = line * .0012 - gap * .004;
        mkBumpK = (1. - smoothstep(6., 30., camDist)) * uDetail;
      }`,
  });

  // ---- the soreg: a lattice of cedar, ten handbreadths high
  const soreg = install(new THREE.MeshStandardMaterial({ roughness: 0.6, metalness: 0, side: THREE.DoubleSide }), {
    uniforms, sky: false,
    color: /* glsl */ `
      {
        float u = abs(wN.x) > abs(wN.z) ? vWPos.z : vWPos.x;
        float v = vWPos.y;
        if (abs(wN.y) < .5) {
          vec2 g = vec2(u, v) / .21;
          vec2 cell = abs(fract(vec2(g.x + g.y, g.x - g.y) * .5) - .5);
          float bar = min(cell.x, cell.y);
          float post = abs(fract(u / 2.5) - .5) * 2.5;
          bool rail = v < .07 || v > .76 || post < .06;
          if (!rail && bar > .1) discard;
        }
        float rings = fbm(vec3(u * 3., v * 14., vWPos.x + vWPos.z));
        diffuseColor.rgb = mix(vec3(.30, .14, .07), vec3(.50, .27, .13), rings);
      }`,
  });

  const dark = install(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0 }), {
    uniforms,
    color: /* glsl */ `
      { diffuseColor.rgb = diffuseColor.rgb * 1.6 + .012 * fbm(vWPos * 7.); }`,
  });

  const red = new THREE.MeshStandardMaterial({ color: 0x7a1010, roughness: 0.7 });

  const bread = install(new THREE.MeshStandardMaterial({ roughness: 0.82, metalness: 0 }), {
    uniforms,
    color: /* glsl */ `
      {
        float bake = fbm(vWPos * 22.);
        diffuseColor.rgb = mix(vec3(.80, .58, .30), vec3(.55, .33, .14), bake * .8 + max(wN.y, 0.) * .15);
      }`,
  });

  // ---- paroches: blue, purple and crimson wool with twisted linen and gold thread
  const cloth = install(new THREE.MeshStandardMaterial({ roughness: 0.92, metalness: 0, side: THREE.DoubleSide }), {
    uniforms,
    color: /* glsl */ `
      {
        vec2 uv = vec2(vWPos.z, vWPos.y - 9.28);
        vec3 techeles = vec3(.022, .060, .26);
        vec3 argaman = vec3(.15, .022, .17);
        vec3 shani = vec3(.30, .018, .03);
        // a blue field, bordered in purple and crimson
        float border = min(min(uv.x + 1.75, 1.75 - uv.x), min(uv.y, 3.06 - uv.y));
        vec3 c = techeles;
        c = mix(argaman, c, smoothstep(.34, .38, border));
        c = mix(shani, c, smoothstep(.14, .18, border));
        // fine lozenge of gold thread over the field, twisted linen at the crossings
        vec2 g = uv * 4.;
        vec2 cell = abs(fract(vec2(g.x + g.y, g.x - g.y) * .5) - .5);
        float px = max(length(fwidth(uv)), 1e-4);
        float show = 1. - smoothstep(.01, .05, px);
        float lattice = (1. - smoothstep(.012, .012 + px * 4., min(cell.x, cell.y))) * smoothstep(.36, .42, border);
        float knot = (1. - smoothstep(.03, .05, length(cell))) * smoothstep(.36, .42, border);
        c = mix(c, vec3(.72, .52, .17), lattice * (.25 + .5 * show));
        c = mix(c, vec3(.80, .76, .64), knot * show);
        float edgeLine = (1. - smoothstep(.0, .012, abs(border - .36))) + (1. - smoothstep(.0, .012, abs(border - .16)));
        c = mix(c, vec3(.74, .54, .18), clamp(edgeLine, 0., 1.) * .8);
        float weave = sin(uv.x * 1100.) * sin(uv.y * 1100.);
        c *= 1. + .10 * weave * (1. - smoothstep(.0008, .004, px));
        diffuseColor.rgb = c;
      }`,
  });

  const water = install(new THREE.MeshStandardMaterial({
    color: 0x2f5f66, roughness: 0.06, metalness: 0.1, transparent: true, opacity: 0.82, envMapIntensity: 1.6,
  }), {
    uniforms,
    fragPars: 'uniform float uTime;',
    color: /* glsl */ `
      {
        float w = vnoise(vec3(vWPos.xz * 9., uTime * .8)) + vnoise(vec3(vWPos.xz * 21. + 3., uTime * 1.3)) * .5;
        mkBump = w * .004;
        mkBumpK = 1.;
      }`,
  });

  // ---- ground outside the building: paved plaza that weathers into bare earth
  const ground = install(new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9, metalness: 0 }), {
    uniforms, sky: false,
    color: /* glsl */ `
      {
        float r = length(vWPos.xz);
        vec3 ash = ashlar(vWPos.xz, 1.5, 2.2);
        float px = max(length(fwidth(vWPos.xz)), 1e-4);
        float fade = 1. - smoothstep(.06, .4, px);
        float tone = mix(.5, hash21(ash.xy + 13.), 1. - smoothstep(.15, .7, px));
        float joint = (1. - smoothstep(.006, .006 + px * 1.6, ash.z)) * clamp(.024 / (px * 1.6 + .006), 0., 1.) * (1. - smoothstep(.25, .8, px));
        float grain = fbm(vWPos * 3.);
        float coarse = fbm(vec3(vWPos.xz * .02, 2.));
        vec3 slab = vec3(.78, .63, .43) * (.88 + .22 * tone) * (.9 + .2 * grain * fade);
        slab = mix(slab, slab * .5, joint * .8);
        float paved = 1.;
        vec3 c = slab * (.86 + .28 * coarse);
        diffuseColor.rgb = c;
        mkBump = -joint * .012 * paved + grain * .003;
        mkBumpK = fade * uDetail;
      }`,
  });

  const byClass = { stone, paving, gold, vgold, copper, wood, dark, red, bread, cloth, water, soreg };
  return { byClass, ground, uniforms };
}
