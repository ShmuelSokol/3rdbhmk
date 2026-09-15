"""CityFacadeV1 - Jerusalem-stone facades with deep-set openings on the 11,405 extruded city buildings.

WHAT IT DOES
------------
One new master material, M_CityFacadeV1, and one instance, MI_CityFacade_CityStone, under
/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials. The instance replaces
MI_CityDetail_CityStone as the per-COMPONENT override on exactly the SM_JerusalemBuildings_*
components that carry MI_CityDetail_CityStone now (the CityDetail meleke retint), and on nothing
else. Its stone colour is the retint's colour: every CityStone parameter is copied across and read
back, so the 1918 stone-ordinance tint is kept, not replaced.

WHY A MATERIAL AND NOT GEOMETRY (see PERFORMANCE-BUDGET.md)
----------------------------------------------------------
The buildings are 1,498 merged 100 m cell meshes (not instances), all Nanite. The measured frame
is GPU-bound in cloud and shadow passes, and the census showed the city was a draw-call problem,
never a triangle problem. A material layer costs ZERO triangles, ZERO draw calls, ZERO actors and
zero shadow-depth work: it changes only pixel-shader arithmetic on wall pixels. Per-building
geometry of the OldCityFacadesV1 kind costs about 1,600 triangles per building (3.4 M for 2,106)
and 190 more meshes; the 561 plain boxes a visitor sees within 300 m would add about 0.9 M
triangles and would still leave the other 8,000 boxes blank from the air. The measured visibility
(Scripts/measure_city_visibility.py) is what makes the material the right tool: 901 buildings are
seen within 300 m, 340 already have geometric shells, and the rest need openings, depth and
variation more than they need silhouette.

THE GRAPH, AND THE SAFETY RULES IT OBEYS
---------------------------------------
  base  = the M_Context_Building triplanar surface and normal Custom nodes, VERBATIM (imported
          from Scripts/release_context_materials.py, not retyped), with the same inputs.
  facade = two more Custom nodes that take the base result and add: ashlar coursing with
          per-stone tone, window / arched window / door / balcony-door openings on a per-wall
          grid, a VIEW-DEPENDENT RECESS (the back plane of each opening is found by offsetting
          along the camera vector by the wall thickness over cos(theta), so the side reveals,
          soffit and sill appear and move with the viewer, with their own world normals so the
          sun lights them), painted shutters (some half open), iron grilles, balcony rails,
          wooden lattice screens on a few windows of the older style, stone lintels / voussoir
          rings / sills, rain stains under sills, and per-roof tone variation for the air.
  Rules:
  * EnclosureMath.h 6b: no author HLSL between PER-INSTANCE CUSTOM DATA and the output. These
    components are plain StaticMeshComponents with no per-instance data; nothing here reads
    PerInstanceCustomData. Variation comes from the per-building VERTEX COLOUR (the same hash
    source M_Context_Building already uses), the object position, the wall's plane offset
    (dot(P.xy, n.xy) is constant along one wall) and the roof height (constant on one roof).
  * nullrhi-cannot-verify-materials: the new code samples NO texture and computes NO
    derivatives. Anti-aliasing is analytic from PixelDepth (pixel footprint ~ depth x 0.0012),
    and every sub-pixel feature fades out with distance to its average, so there is no mip or
    ddx path for Nanite to break.
  * ComponentMask trap: both masks set r, g, b and a explicitly (the shared Graph.finish()).
  * Usage flags: used_with_nanite AND used_with_instanced_static_meshes are set and READ BACK
    from disk after reload, because a missing flag makes the cook substitute the default
    material silently.

MODES (tokens on the command line)
----------------------------------
  -CityFacadeTarget=candidate|main   (default candidate)
  -CityFacadeBuild                   create the master + instance if missing (assets only)
  -CityFacadeApply                   retarget the retint components to MI_CityFacade_CityStone
  -CityFacadeRebuild                 rewire M_CityFacadeV1 IN PLACE with the current HLSL (assets only;
                                     both .uassets checkpointed first; MI and every component override
                                     untouched, parameters bind by name)
  -CityFacadeRevert                  put MI_CityDetail_CityStone back on every component that
                                     carries MI_CityFacade_CityStone
Build and Apply may be combined. Every map mutation is guarded: checkpoint into
ReviewCheckpoints, protected-map hashes before/after, dirty-package refusal, save, REOPEN,
numeric readback, receipt written at start and in finally.

Launch (commandlet, -nullrhi):
  UnrealEditor-Cmd.exe <uproject> -run=pythonscript
      -script=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_city_facade.py
      -CityFacadeBuild -CityFacadeApply -CityFacadeTarget=candidate -unattended -nullrhi -abslog=...
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
sys.path.insert(0, str(ROOT / 'Scripts'))
SCRIPT_TOKEN = 'release_city_facade.py'

TARGETS = {
    'candidate': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'main': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
PROTECTED = [
    '/Game/MikdashV3/Maps/Courtyard',
    '/Game/MikdashV3/FutureMountV1/L_FutureMount',
    '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold',
    '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
    '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
]
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
RECEIPTS = ROOT / 'SourceAssets' / 'context-review' / 'CityFacadeV1'
FOLDER = '/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials'
MASTER_NAME = 'M_CityFacadeV1'
MI_NAME = 'MI_CityFacade_CityStone'
MASTER = FOLDER + '/' + MASTER_NAME
MI = FOLDER + '/' + MI_NAME
RETINT_MI = '/Game/MikdashV3/JerusalemContext/CityDetailV1/Materials/MI_CityDetail_CityStone'
CONTEXT_BUILDING = '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building'
ACTOR_PREFIX = 'SM_JerusalemBuildings_'

# Base parameters: M_Context_Building defaults overlaid with the MI_CityDetail_CityStone readback
# (native-city-detail-candidate-20260909T223929718568Z.json). Copied, then read back in-engine
# from the live CityStone instance, which wins if it differs.
BASE_SCALARS = {
    'TileCm': 420.0, 'RoofScale': 0.5, 'RoofStart': 0.6, 'RoofEnd': 0.85, 'RoofFlatten': 0.72,
    'RoughScale': 1.0, 'RoughBias': 0.0, 'RoughVar': 0.14, 'NormalStrength': 1.0,
    'VCInfluence': 0.5, 'VCMeanLum': 0.38, 'HashObjectWeight': 1.0, 'HashVertexColorWeight': 1.0,
}
BASE_VECTORS = {
    'Tint0': [1.2, 1.16, 1.07], 'Tint1': [1.12, 1.06, 0.96], 'Tint2': [1.26, 1.21, 1.1],
    'Tint3': [1.16, 1.12, 1.02], 'RoofTint': [0.94, 0.93, 0.89],
}
# Facade parameters. All AUTHORED: typical Jerusalem numbers, not a survey of any building.
FACADE_SCALARS = {
    'FloorCm': 330.0,        # storey height; varied +-9 % per building
    'PitchCm': 340.0,        # opening pitch along a wall; varied -20..+25 % per building
    'DepthCm': 34.0,         # recess depth (60-80 cm stone walls; the glass/shutter sits inside)
    'FadeStartCm': 22000.0,  # openings at full strength to 220 m ...
    'FadeEndCm': 80000.0,    # ... and averaged out by 800 m (the far read keeps FarDark)
    'FacadeStrength': 1.0,
    'CourseCm': 34.0,        # ashlar course height
    'JointDark': 0.35,
    'StoneVar': 0.12,        # per-stone tone variation
    'ShutterMix': 0.45,
    'FarDark': 0.10,         # mean darkening the openings contribute, kept past the fade
    'RoofVar': 1.0,
}

# ----------------------------------------------------------------------------- HLSL
# Shared geometry prelude. Inputs: P, N, VC, ObjPos, Cam, PD and the FACADE_SCALARS.
HLSL_PRELUDE = r'''
float3 n = normalize(N.xyz);
float wallM = 1.0 - smoothstep(0.35, 0.65, abs(n.z));
float roofM = smoothstep(0.6, 0.85, n.z);
float2 nh = n.xy / max(length(n.xy), 1e-4);
float2 t2 = float2(-nh.y, nh.x);
float3 Pw = P.xyz;
float u = dot(Pw.xy, t2);
float plane = dot(Pw.xy, nh);
float hb = frac(dot(VC.rgb, float3(12.9898, 78.233, 37.719)) + dot(ObjPos.xyz * 0.001, float3(0.7548, 0.5698, 0.3176)) + 0.1731);
float hw = frac(sin(floor(plane / 35.0 + 0.5) * 12.9898 + hb * 78.233) * 43758.5453);
float fp = PD * 0.0012 + 0.3;
float fadeRaw = 1.0 - smoothstep(FadeStartCm, FadeEndCm, PD);
float fade = fadeRaw * wallM * FacadeStrength;
float gf = 1.0 - smoothstep(3000.0, 7000.0, PD);
float floorH = FloorCm * (0.92 + 0.18 * frac(hb * 5.13));
float pitch = PitchCm * (0.8 + 0.45 * frac(hb * 9.71 + hw * 0.37));
float uu = u / pitch + hw * 7.0;
float zz = Pw.z / floorH + frac(hb * 3.7);
float2 cellId = floor(float2(uu, zz));
float x = (frac(uu) - 0.5) * pitch;
float y = frac(zz) * floorH;
float ho = frac(sin(dot(cellId + hb * 17.0, float2(127.1, 311.7))) * 43758.5453);
float ho2 = frac(ho * 13.37 + 0.21);
float ho3 = frac(ho * 71.13 + 0.77);
float style = frac(hb * 2.31);
float pBlank = 0.18 + 0.2 * hw;
float isOpen = step(pBlank, ho);
float tall = isOpen * step(ho, pBlank + 0.13);
float arched = step(ho2, 0.2 + 0.55 * style);
float hx = lerp(lerp(36.0, 50.0, ho3), 55.0, tall);
float oh = lerp(lerp(105.0, 150.0, ho2), 235.0, tall);
float sillY = lerp(lerp(85.0, 105.0, ho3), 4.0, tall);
float topR = (arched > 0.5) ? (oh - hx) : oh;
float3 C = normalize(Cam.xyz);
float vN = max(dot(C, n), 0.08);
float vT = dot(C, float3(t2, 0.0));
float vZ = C.z;
float Dp = DepthCm * (0.75 + 0.5 * hw);
float2 q0 = float2(x, y - sillY);
float2 q1 = q0 - float2(vT, vZ) * (Dp / vN);
float sdR0 = max(abs(q0.x) - hx, max(-q0.y, q0.y - topR));
float sdA0 = max(length(float2(q0.x, q0.y - topR)) - hx, topR - q0.y);
float sd0 = (arched > 0.5) ? min(sdR0, sdA0) : sdR0;
float sdR1 = max(abs(q1.x) - hx, max(-q1.y, q1.y - topR));
float sdA1 = max(length(float2(q1.x, q1.y - topR)) - hx, topR - q1.y);
float sd1 = (arched > 0.5) ? min(sdR1, sdA1) : sdR1;
float m0 = isOpen * (1.0 - smoothstep(-fp, fp, sd0));
float m1 = 1.0 - smoothstep(-0.5, 0.5, sd1);
float ex = abs(q1.x) - hx;
float et = q1.y - ((arched > 0.5) ? (topR + sqrt(max(hx * hx - q1.x * q1.x, 0.0))) : topR);
float eb = -q1.y;
float rk = (ex > max(et, eb)) ? 0.0 : ((et > eb) ? 1.0 : 2.0);
float3 rn = (rk < 0.5) ? float3(t2 * (-sign(q1.x)), 0.0) : ((rk < 1.5) ? float3(0.0, 0.0, -1.0) : float3(0.0, 0.0, 1.0));
'''

HLSL_SURFACE_TAIL = r'''
float course = CourseCm * (0.9 + 0.25 * frac(hb * 4.7));
float zc = Pw.z / course;
float row = floor(zc);
float hr = frac(sin(row * 91.7 + hb * 47.3) * 43758.5453);
float slen = lerp(45.0, 95.0, hr);
float us = (u + hr * 173.0) / slen;
float sidx = floor(us);
float hs = frac(sin(sidx * 12.9898 + row * 4.1414 + hb * 7.7) * 43758.5453);
float dzJ = min(frac(zc), 1.0 - frac(zc)) * course;
float duJ = min(frac(us), 1.0 - frac(us)) * slen;
float jf = 1.0 - smoothstep(2500.0, 9000.0, PD);
float joint = (1.0 - smoothstep(0.7, 0.7 + fp, min(dzJ, duJ))) * jf;
float3 stone = Base.rgb * (1.0 + (hs - 0.5) * StoneVar) * (1.0 - JointDark * joint);
float3 rc = stone * ((rk < 0.5) ? 0.90 : ((rk < 1.5) ? 0.74 : 1.04));
float pk = floor(frac(hb * 6.91) * 4.0);
float3 paint = (pk < 0.5) ? float3(0.09, 0.20, 0.16) : ((pk < 1.5) ? float3(0.10, 0.17, 0.27) : ((pk < 2.5) ? float3(0.20, 0.12, 0.06) : float3(0.20, 0.23, 0.20)));
float shutter = step(ho3, ShutterMix) * (1.0 - tall);
float leafOpen = step(0.7, frac(ho3 * 5.3));
shutter *= (leafOpen > 0.5) ? step(q1.x, 0.0) : 1.0;
float lv = min(frac(q1.y / 6.0), 1.0 - frac(q1.y / 6.0)) * 6.0;
float louvre = 1.0 - 0.45 * gf * (1.0 - smoothstep(0.8, 0.8 + fp, lv));
float3 glass = float3(0.022, 0.026, 0.030);
float3 inCol = lerp(glass, paint * louvre, shutter);
float inR = lerp(0.12, 0.70, shutter);
float pd = min(abs(abs(q1.x) - hx * 0.55), abs(q1.y - oh * 0.5));
float3 doorCol = paint * (1.0 - 0.3 * gf * (1.0 - smoothstep(1.0, 1.0 + fp, pd)));
float glazed = step(0.55, ho3) * step(110.0, q1.y);
inCol = lerp(inCol, lerp(doorCol, glass, glazed), tall);
inR = lerp(inR, lerp(0.65, 0.12, glazed), tall);
inCol *= 0.75;
float lattice = (1.0 - tall) * step(0.94 - 0.06 * style, ho2) * isOpen;
float2 lq = frac(q0 / 7.0);
float hole = step(0.22, lq.x) * step(lq.x, 0.78) * step(0.22, lq.y) * step(lq.y, 0.78);
float3 latCol = lerp(float3(0.19, 0.11, 0.06), float3(0.02, 0.02, 0.02), hole * gf);
float grille = (1.0 - tall) * step(0.55, frac(ho * 3.9)) * (1.0 - lattice);
float gb = min(abs(frac(q0.x / 12.0 + 0.5) - 0.5) * 12.0, abs(q0.y - oh * 0.45));
float bar = grille * gf * (1.0 - smoothstep(0.9, 0.9 + fp, gb));
float rail = tall * step(0.4, ho2) * step(q0.y, 100.0) * gf;
float rb = min(abs(frac(q0.x / 11.0 + 0.5) - 0.5) * 11.0, abs(q0.y - 98.0));
bar = max(bar, rail * (1.0 - smoothstep(0.9, 0.9 + fp, rb)));
float3 openCol = lerp(rc, inCol, m1);
float openR = lerp(Base.a, inR, m1);
openCol = lerp(openCol, latCol, lattice);
openR = lerp(openR, 0.75, lattice);
openCol = lerp(openCol, float3(0.03, 0.03, 0.035), bar);
openR = lerp(openR, 0.45, bar);
float rr = length(float2(q0.x, q0.y - topR));
float lintel = (arched > 0.5) ? (step(topR, q0.y) * step(hx, rr) * step(rr, hx + 20.0))
                              : (step(abs(q0.x), hx + 16.0) * step(oh, q0.y) * step(q0.y, oh + 24.0));
float sillSlab = step(abs(q0.x), hx + 10.0) * step(-9.0, q0.y) * step(q0.y, 0.0);
float trim = isOpen * max(lintel, sillSlab);
float stain = isOpen * (1.0 - tall) * step(abs(q0.x), hx - 4.0) * smoothstep(-70.0, -10.0, q0.y) * step(q0.y, -9.0);
float3 wallCol = stone * (1.0 + 0.10 * trim) * (1.0 - 0.10 * stain);
float3 fac = lerp(wallCol, openCol, m0);
float facR = lerp(Base.a, openR, m0);
float3 col = lerp(Base.rgb, fac, fade);
float rough = lerp(Base.a, facR, fade);
col *= 1.0 - FarDark * wallM * FacadeStrength * (1.0 - fadeRaw);
float hr2 = frac(sin(floor(Pw.z / 9.0) * 17.13 + hb * 91.7) * 43758.5453);
float3 roofTone = (hr2 < 0.45) ? float3(1.0, 1.0, 1.0) : ((hr2 < 0.75) ? float3(0.80, 0.81, 0.82) : ((hr2 < 0.93) ? float3(0.93, 0.87, 0.76) : float3(0.50, 0.49, 0.47)));
float2 g = Pw.xy / 480.0;
float2 gi = floor(g);
float2 gq = frac(g);
gq = gq * gq * (3.0 - 2.0 * gq);
float a0 = frac(sin(dot(gi, float2(127.1, 311.7))) * 43758.5453);
float b0 = frac(sin(dot(gi + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float c0 = frac(sin(dot(gi + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float d0 = frac(sin(dot(gi + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float grime = lerp(lerp(a0, b0, gq.x), lerp(c0, d0, gq.x), gq.y);
float3 roofCol = col * roofTone * (0.9 + 0.2 * grime);
col = lerp(col, roofCol, roofM * RoofVar);
return float4(col, saturate(rough));
'''

HLSL_NORMAL_TAIL = r'''
float3 inside = lerp(rn, n, m1);
float3 fn = lerp(BaseN.xyz, inside, m0);
return normalize(lerp(BaseN.xyz, fn, fade));
'''

# EARLY-OUT (added after the first frame-time pair, cp21c -> cp21d at the P1 aerial: GPU median
# 16.62 -> 17.75 ms). Every roof pixel and every wall pixel past FadeEndCm has fade == 0, so the whole
# opening grid, recess and trim maths contributes nothing there but was still being evaluated - and
# in a wide aerial that is most of the city. The prelude is therefore split at the first
# opening-grid line: the cheap half (normals, hashes, fade) always runs; the far branch returns the
# base colour with only the averaged far darkening and the per-roof tone, and the normal node returns
# the base normal. The branch is on distance, so it is spatially coherent across a wave.
_SPLIT = 'float floorH'
HLSL_PRELUDE_A, _rest = HLSL_PRELUDE.split(_SPLIT, 1)
HLSL_PRELUDE_B = _SPLIT + _rest
_ROOF_START = 'float hr2'
_ROOF_END = 'col = lerp(col, roofCol, roofM * RoofVar);'
HLSL_ROOF = (HLSL_SURFACE_TAIL[HLSL_SURFACE_TAIL.index(_ROOF_START):
                               HLSL_SURFACE_TAIL.index(_ROOF_END) + len(_ROOF_END)] + '\n')
HLSL_SURFACE_EARLY = ('if (fade <= 0.0005)\n{\n'
                      'float3 col = Base.rgb * (1.0 - FarDark * wallM * FacadeStrength * (1.0 - fadeRaw));\n'
                      + HLSL_ROOF +
                      'return float4(col, Base.a);\n}\n')
HLSL_NORMAL_EARLY = 'if (fade <= 0.0005)\n{\nreturn normalize(BaseN.xyz);\n}\n'
SURFACE_CODE = HLSL_PRELUDE_A + HLSL_SURFACE_EARLY + HLSL_PRELUDE_B + HLSL_SURFACE_TAIL
NORMAL_CODE = HLSL_PRELUDE_A + HLSL_NORMAL_EARLY + HLSL_PRELUDE_B + HLSL_NORMAL_TAIL

GEOM_INPUTS = ('P', 'N', 'VC', 'ObjPos', 'Cam', 'PD')
FACADE_PARAM_NAMES = ('FloorCm', 'PitchCm', 'DepthCm', 'FadeStartCm', 'FadeEndCm', 'FacadeStrength')
SURFACE_PARAM_NAMES = FACADE_PARAM_NAMES + ('CourseCm', 'JointDark', 'StoneVar', 'ShutterMix', 'FarDark', 'RoofVar')


def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.' + extension)


def _asset_path(obj):
    if obj is None:
        return None
    name = obj.get_path_name()
    return name.split('.')[0]


def offline_check():
    """Engine-free: the HLSL strings are balanced and every input they name is supplied."""
    import re
    problems = []
    for label, code in (('surface', SURFACE_CODE), ('normal', NORMAL_CODE)):
        if code.count('(') != code.count(')'):
            problems.append(label + ': unbalanced parentheses')
        if 'Texture2D' in code or 'ddx' in code or 'ddy' in code or 'PerInstance' in code:
            problems.append(label + ': samples a texture, takes a derivative or reads per-instance data')
    for name in SURFACE_PARAM_NAMES:
        if not re.search(r'\b%s\b' % name, SURFACE_CODE):
            problems.append('surface param unused: ' + name)
    return {'ok': not problems, 'problems': problems,
            'surfaceSha256': hashlib.sha256((SURFACE_CODE).encode()).hexdigest(),
            'normalSha256': hashlib.sha256((NORMAL_CODE).encode()).hexdigest()}


# ============================================================================ engine side
class Facade:
    def __init__(self, ue):
        import release_context_materials as RCM
        self.ue = ue
        self.RCM = RCM
        self.ml = ue.MaterialEditingLibrary
        self.assets = ue.EditorAssetLibrary
        self.receipt = None
        self.receipt_path = None

    def write(self):
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1, default=str), encoding='utf-8')

    # ---------------------------------------------------------------- nodes
    def node(self, material, cls, x, y, record, **props):
        e = self.ml.create_material_expression(material, cls, x, y)
        if e is None:
            raise RuntimeError('create_material_expression failed for ' + cls.__name__)
        for k, v in props.items():
            e.set_editor_property(k, v)
        record['nodes'] += 1
        return e

    def wire(self, src, dst, name, record):
        if not self.ml.connect_material_expressions(src, '', dst, name):
            raise RuntimeError('connect %s -> %s.%s failed' % (src.get_class().get_name(), dst.get_class().get_name(), name))
        record['connections'] += 1

    def custom(self, material, code, inputs, out_type, x, y, desc, record):
        ue = self.ue
        slots = []
        for name in inputs:
            s = ue.CustomInput()
            s.set_editor_property('input_name', name)
            slots.append(s)
        e = self.node(material, ue.MaterialExpressionCustom, x, y, record, inputs=slots, code=code.strip(),
                      output_type=out_type, description=desc)
        for name, src in inputs.items():
            self.wire(src, e, name, record)
        record['customNodes'].append({'description': desc, 'inputs': list(inputs),
                                      'codeSha256': hashlib.sha256(code.strip().encode()).hexdigest()})
        return e

    def live_retint_values(self):
        """Read the live CityStone instance so the copy is of what is ON the buildings now."""
        ue = self.ue
        mi = self.assets.load_asset(RETINT_MI)
        if mi is None:
            raise RuntimeError('MI_CityDetail_CityStone missing: ' + RETINT_MI)
        scalars, vectors = dict(BASE_SCALARS), dict(BASE_VECTORS)
        for name in list(scalars):
            try:
                scalars[name] = float(self.ml.get_material_instance_scalar_parameter_value(mi, name))
            except Exception:                                          # noqa: BLE001
                pass
        for name in list(vectors):
            try:
                c = self.ml.get_material_instance_vector_parameter_value(mi, name)
                vectors[name] = [round(c.r, 5), round(c.g, 5), round(c.b, 5)]
            except Exception:                                          # noqa: BLE001
                pass
        return scalars, vectors, _asset_path(mi.get_editor_property('parent'))

    def set_usage(self, material):
        ue = self.ue
        out = {}
        for prop, usage in (('used_with_nanite', 'MATUSAGE_NANITE'),
                            ('used_with_instanced_static_meshes', 'MATUSAGE_INSTANCED_STATIC_MESHES')):
            try:
                material.set_editor_property(prop, True)
            except Exception:                                          # noqa: BLE001
                self.ml.set_material_usage(material, getattr(ue.MaterialUsage, usage))
            out[prop] = bool(material.get_editor_property(prop))
            if not out[prop]:
                raise RuntimeError('usage flag %s did not take' % prop)
        return out

    def build(self, rebuild=False):
        ue = self.ue
        RCM = self.RCM
        rec = {'master': MASTER, 'instance': MI, 'nodes': 0, 'connections': 0, 'customNodes': []}
        self.receipt['material'] = rec
        exists = self.assets.does_asset_exist(MASTER)
        if exists and not rebuild:
            rec['status'] = 'already_exists_not_rebuilt'
            return rec
        if rebuild and not exists:
            raise RuntimeError('nothing to rebuild: ' + MASTER)
        spec = RCM.load_spec()
        cfg = spec['materials']['building']
        if cfg['name'] != 'M_Context_Building':
            raise RuntimeError('context spec building entry is not M_Context_Building')
        tex = {}
        for key in ('diffuse', 'roughness', 'normal'):
            path = RCM.texture_asset_path(spec, cfg['set'], key)
            t = self.assets.load_asset(path)
            if t is None:
                raise RuntimeError('texture missing: ' + path)
            tex[key] = t
            rec.setdefault('textures', {})[key] = path
        scalars, vectors, retint_parent = self.live_retint_values()
        if retint_parent != CONTEXT_BUILDING:
            raise RuntimeError('MI_CityDetail_CityStone parent is %s, expected M_Context_Building' % retint_parent)
        rec['copiedFromRetint'] = {'scalar': scalars, 'vector': vectors}

        if rebuild:
            material = self.assets.load_asset(MASTER)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            ck = CHECKPOINT_ROOT / ('CityFacade-rebuild-' + stamp)
            ck.mkdir(parents=True, exist_ok=False)
            for asset in (MASTER, MI):
                shutil.copy2(disk_path(asset), ck / disk_path(asset).name)
            rec['rebuildCheckpoint'] = str(ck)
            rec['preRebuildSha256'] = {a: sha256_of(disk_path(a)) for a in (MASTER, MI)}
            self.ml.delete_all_material_expressions(material)
        else:
            material = ue.AssetToolsHelpers.get_asset_tools().create_asset(MASTER_NAME, FOLDER, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Material factory failed')
        M = material
        n = lambda cls, x, y, **kw: self.node(M, cls, x, y, rec, **kw)                         # noqa: E731
        albedo = n(ue.MaterialExpressionTextureObject, -2000, -600, texture=tex['diffuse'])
        rough = n(ue.MaterialExpressionTextureObject, -2000, -450, texture=tex['roughness'])
        ntex = n(ue.MaterialExpressionTextureObject, -2000, -300, texture=tex['normal'])
        pos = n(ue.MaterialExpressionWorldPosition, -2000, -150)
        vnorm = n(ue.MaterialExpressionVertexNormalWS, -2000, -50)
        opos = n(ue.MaterialExpressionObjectPositionWS, -2000, 50)
        vcol = n(ue.MaterialExpressionVertexColor, -2000, 150)
        cam = n(ue.MaterialExpressionCameraVectorWS, -2000, 250)
        depth = n(ue.MaterialExpressionPixelDepth, -2000, 350)
        params = {}
        for i, (name, value) in enumerate(scalars.items()):
            params[name] = n(ue.MaterialExpressionScalarParameter, -1700, 400 + i * 70, parameter_name=name, default_value=float(value))
        for i, (name, value) in enumerate(FACADE_SCALARS.items()):
            params[name] = n(ue.MaterialExpressionScalarParameter, -1400, 400 + i * 70, parameter_name=name, default_value=float(value))
        vecs = {}
        for i, (name, rgb) in enumerate(vectors.items()):
            vecs[name] = n(ue.MaterialExpressionVectorParameter, -1700, -700 + i * 120, parameter_name=name,
                           default_value=ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
        base_in = {'Albedo': albedo, 'Rough': rough, 'P': pos, 'N': vnorm, 'ObjPos': opos, 'VC': vcol}
        for k in ('Tint0', 'Tint1', 'Tint2', 'Tint3', 'RoofTint'):
            base_in[k] = vecs[k]
        for k in ('TileCm', 'RoofScale', 'RoofStart', 'RoofEnd', 'RoofFlatten', 'RoughScale', 'RoughBias', 'RoughVar',
                  'VCInfluence', 'VCMeanLum', 'HashObjectWeight', 'HashVertexColorWeight'):
            base_in[k] = params[k]
        COT = ue.CustomMaterialOutputType
        base = self.custom(M, RCM.HLSL_TRIPLANAR_SURFACE, base_in, COT.CMOT_FLOAT4, -900, -400,
                           'M_Context_Building triplanar surface, verbatim', rec)
        green = n(ue.MaterialExpressionConstant, -1700, 200, r=float(RCM.NORMAL_GREEN_SIGN))
        base_n = self.custom(M, RCM.HLSL_TRIPLANAR_NORMAL,
                             {'Nrm': ntex, 'P': pos, 'N': vnorm, 'TileCm': params['TileCm'], 'RoofScale': params['RoofScale'],
                              'NormalStrength': params['NormalStrength'], 'NormalGreenSign': green},
                             COT.CMOT_FLOAT3, -900, 300, 'M_Context_Building triplanar normal, verbatim', rec)
        geo = {'P': pos, 'N': vnorm, 'VC': vcol, 'ObjPos': opos, 'Cam': cam, 'PD': depth}
        s_in = {'Base': base}
        s_in.update(geo)
        s_in.update({k: params[k] for k in SURFACE_PARAM_NAMES})
        surface = self.custom(M, SURFACE_CODE, s_in, COT.CMOT_FLOAT4, -300, -400,
                              'CityFacadeV1 surface: coursing, recessed openings, shutters, grilles, roofs', rec)
        n_in = {'BaseN': base_n}
        n_in.update(geo)
        n_in.update({k: params[k] for k in FACADE_PARAM_NAMES})
        normal = self.custom(M, NORMAL_CODE, n_in, COT.CMOT_FLOAT3, -300, 300,
                             'CityFacadeV1 normal: reveal and soffit normals inside the recess', rec)
        rgb = n(ue.MaterialExpressionComponentMask, 200, -400, r=True, g=True, b=True, a=False)
        alpha = n(ue.MaterialExpressionComponentMask, 200, -250, r=False, g=False, b=False, a=True)
        self.wire(surface, rgb, '', rec)
        self.wire(surface, alpha, '', rec)
        metal = n(ue.MaterialExpressionConstant, 200, 100, r=0.0)
        for src, prop in ((rgb, 'MP_BASE_COLOR'), (alpha, 'MP_ROUGHNESS'), (normal, 'MP_NORMAL'), (metal, 'MP_METALLIC')):
            if not self.ml.connect_material_property(src, '', getattr(ue.MaterialProperty, prop)):
                raise RuntimeError('connect_material_property failed: ' + prop)
        masks = {'rgb': [bool(rgb.get_editor_property(c)) for c in 'rgba'],
                 'alpha': [bool(alpha.get_editor_property(c)) for c in 'rgba']}
        if masks != {'rgb': [True, True, True, False], 'alpha': [False, False, False, True]}:
            raise RuntimeError('ComponentMask channels wrong: %s' % masks)
        rec['componentMasks'] = masks
        M.set_editor_property('tangent_space_normal', False)
        M.set_editor_property('two_sided', False)
        rec['usageSet'] = self.set_usage(M)
        self.ml.recompile_material(M)
        if not self.assets.save_loaded_asset(M, only_if_is_dirty=False):
            raise RuntimeError('save master failed')

        if self.assets.does_asset_exist(MI):
            mi = self.assets.load_asset(MI)
        else:
            mi = ue.AssetToolsHelpers.get_asset_tools().create_asset(MI_NAME, FOLDER, ue.MaterialInstanceConstant,
                                                                     ue.MaterialInstanceConstantFactoryNew())
        if mi is None:
            raise RuntimeError('MI factory failed')
        self.ml.set_material_instance_parent(mi, M)
        for name, value in list(scalars.items()) + list(FACADE_SCALARS.items()):
            self.ml.set_material_instance_scalar_parameter_value(mi, name, float(value))
        for name, rgb in vectors.items():
            self.ml.set_material_instance_vector_parameter_value(mi, name, ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
        self.ml.update_material_instance(mi)
        if not self.assets.save_loaded_asset(mi, only_if_is_dirty=False):
            raise RuntimeError('save instance failed')
        rec['status'] = 'rebuilt_in_place' if rebuild else 'created'
        return rec

    def readback_assets(self):
        """Reload both assets from disk and read back what matters to the cook."""
        ue = self.ue
        M = self.assets.load_asset(MASTER)
        mi = self.assets.load_asset(MI)
        if M is None or mi is None:
            raise RuntimeError('facade assets not found on disk')
        out = {'masterSha256': sha256_of(disk_path(MASTER)), 'instanceSha256': sha256_of(disk_path(MI)),
               'usage': {p: bool(M.get_editor_property(p)) for p in ('used_with_nanite', 'used_with_instanced_static_meshes')},
               'instanceParent': _asset_path(mi.get_editor_property('parent')),
               'wired': {}}
        for prop in ('MP_BASE_COLOR', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_METALLIC', 'MP_WORLD_POSITION_OFFSET'):
            w = self.ml.get_material_property_input_node(M, getattr(ue.MaterialProperty, prop))
            out['wired'][prop] = w.get_class().get_name() if w else None
        if not all(out['usage'].values()):
            raise RuntimeError('usage flag missing on disk: %s' % out['usage'])
        if out['instanceParent'] != MASTER:
            raise RuntimeError('instance parent is %s' % out['instanceParent'])
        if out['wired']['MP_WORLD_POSITION_OFFSET'] is not None or not out['wired']['MP_BASE_COLOR'] or not out['wired']['MP_NORMAL']:
            raise RuntimeError('unexpected wiring %s' % out['wired'])
        sc = {}
        for name in list(BASE_SCALARS) + list(FACADE_SCALARS):
            sc[name] = round(float(self.ml.get_material_instance_scalar_parameter_value(mi, name)), 5)
        vc = {}
        for name in BASE_VECTORS:
            c = self.ml.get_material_instance_vector_parameter_value(mi, name)
            vc[name] = [round(c.r, 5), round(c.g, 5), round(c.b, 5)]
        out['instanceScalars'] = sc
        out['instanceVectors'] = vc
        want_s, want_v, _ = self.live_retint_values()
        for name, value in want_s.items():
            if abs(sc[name] - value) > 1e-4:
                raise RuntimeError('instance %s = %s, retint has %s' % (name, sc[name], value))
        for name, value in want_v.items():
            if max(abs(a - b) for a, b in zip(vc[name], value)) > 1e-4:
                raise RuntimeError('instance %s = %s, retint has %s' % (name, vc[name], value))
        for name, value in FACADE_SCALARS.items():
            if abs(sc[name] - value) > 1e-4:
                raise RuntimeError('instance %s = %s, want %s' % (name, sc[name], value))
        out['matchesRetintColour'] = True
        return out

    # ---------------------------------------------------------------- map
    def census(self, actors):
        ue = self.ue
        counts = {}
        for actor in actors.get_all_level_actors():
            if not actor.get_actor_label().startswith(ACTOR_PREFIX):
                continue
            for comp in actor.get_components_by_class(ue.StaticMeshComponent):
                ov = comp.get_editor_property('override_materials')
                key = _asset_path(ov[0]) if ov else 'none'
                counts[key] = counts.get(key, 0) + 1
        return counts

    def retarget(self, actors, src_path, dst_asset, dst_path):
        ue = self.ue
        touched, labels = 0, []
        for actor in actors.get_all_level_actors():
            label = actor.get_actor_label()
            if not label.startswith(ACTOR_PREFIX):
                continue
            for comp in actor.get_components_by_class(ue.StaticMeshComponent):
                ov = comp.get_editor_property('override_materials')
                if not ov or _asset_path(ov[0]) != src_path:
                    continue
                comp.set_material(0, dst_asset)
                if _asset_path(comp.get_material(0)) != dst_path:
                    raise RuntimeError('override did not take on ' + label)
                touched += 1
                labels.append(label)
        return touched, labels


def run(target, do_build, do_apply, do_revert, do_rebuild=False):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('wrong project')
    f = Facade(ue)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    mode = 'revert' if do_revert else ('apply' if do_apply else ('rebuild' if do_rebuild else 'build'))
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    f.receipt_path = RECEIPTS / ('native-city-facade-%s-%s-%s.json' % (mode, target, stamp))
    f.receipt = {'status': 'started', 'stamp': stamp, 'target': target, 'mode': {'build': do_build, 'apply': do_apply, 'revert': do_revert},
                 'scriptSha256': sha256_of(Path(__file__)), 'offlineCheck': offline_check(),
                 'engineVersion': ue.SystemLibrary.get_engine_version(), 'errors': [], 'mapSaved': False}
    f.write()
    if not f.receipt['offlineCheck']['ok']:
        raise RuntimeError('offline check failed: %s' % f.receipt['offlineCheck'])
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('a game world is active')
    map_path = TARGETS[target]
    map_file = disk_path(map_path, 'umap')
    protected_before = {p: sha256_of(disk_path(p, 'umap')) for p in PROTECTED if p != map_path and disk_path(p, 'umap').exists()}
    f.receipt['protectedMapSha256Before'] = protected_before
    map_before = sha256_of(map_file)
    f.receipt['mapSha256Before'] = map_before
    saved = False
    try:
        if do_build or do_rebuild:
            f.build(rebuild=do_rebuild)
            f.write()
        if not (do_apply or do_revert):
            f.receipt['assetReadback'] = f.readback_assets()
            f.receipt['status'] = ('assets_rebuilt_read_back_map_untouched' if do_rebuild
                                   else 'assets_built_read_back_map_untouched')
            return f.receipt
        f.receipt['assetReadback'] = f.readback_assets()
        if not levels.load_level(map_path):
            raise RuntimeError('load_level failed')
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != map_path:
            raise RuntimeError('loaded world is not the target')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('dirty map packages before mutation')
        checkpoint = CHECKPOINT_ROOT / ('CityFacade-%s-%s-%s' % (mode, target, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_before:
            raise RuntimeError('checkpoint copy hash differs')
        f.receipt['checkpoint'] = str(checkpoint)
        before = f.census(actors)
        f.receipt['overrideCensusBefore'] = before
        if do_revert:
            dst = ue.EditorAssetLibrary.load_asset(RETINT_MI)
            touched, labels = f.retarget(actors, MI, dst, RETINT_MI)
            want_path = RETINT_MI
        else:
            dst = ue.EditorAssetLibrary.load_asset(MI)
            touched, labels = f.retarget(actors, RETINT_MI, dst, MI)
            want_path = MI
        f.receipt['componentsRetargeted'] = touched
        f.receipt['actorsRetargeted'] = len(set(labels))
        f.write()
        if touched == 0:
            f.receipt['status'] = 'nothing_to_do_map_unchanged'
            return f.receipt
        if not ue.EditorLoadingAndSavingUtils.save_map(world, map_path):
            raise RuntimeError('save_map failed')
        saved = True
        f.receipt['mapSaved'] = True
        f.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        f.write()
        if not levels.load_level(map_path):
            raise RuntimeError('reopen failed')
        after = f.census(actors)
        f.receipt['overrideCensusAfterReopen'] = after
        expect_moved = before.get(MI if do_revert else RETINT_MI, 0)
        if after.get(want_path, 0) != before.get(want_path, 0) + expect_moved or after.get(MI if do_revert else RETINT_MI, 0) != 0:
            raise RuntimeError('reopen census %s does not match expected move of %d' % (after, expect_moved))
        total_before = sum(before.values())
        if sum(after.values()) != total_before:
            raise RuntimeError('component count changed across the reopen')
        f.receipt['status'] = ('city_facade_%s_saved_reopened_read_back_visual_acceptance_pending' % mode)
        f.receipt['revertCommand'] = ('-CityFacadeRevert -CityFacadeTarget=%s' % target) if not do_revert else None
        return f.receipt
    except Exception as error:                                          # noqa: BLE001
        f.receipt['errors'].append(repr(error))
        f.receipt['status'] = 'failed_after_save_checkpoint_available' if saved else 'failed_before_save_map_unchanged'
        raise
    finally:
        f.receipt['mapSha256After'] = sha256_of(map_file)
        f.receipt['mapBytesChanged'] = f.receipt['mapSha256After'] != map_before
        f.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(p, 'umap')) == h for p, h in protected_before.items())
        f.write()


def _main():
    import unreal as ue
    cl = ue.SystemLibrary.get_command_line()
    low = cl.lower()
    target = 'candidate'
    for tok in cl.split():
        if tok.lower().startswith('-cityfacadetarget='):
            target = tok.split('=', 1)[1].strip('"').lower()
    if target not in TARGETS:
        raise RuntimeError('unknown target ' + target)
    do_revert = '-cityfacaderevert' in low
    do_apply = '-cityfacadeapply' in low and not do_revert
    do_build = '-cityfacadebuild' in low
    do_rebuild = '-cityfacaderebuild' in low
    try:
        r = run(target, do_build, do_apply, do_revert, do_rebuild)
        ue.log('release_city_facade: %s retargeted %s' % (r['status'], r.get('componentsRetargeted')))
    except Exception as error:                                          # noqa: BLE001
        ue.log_error('release_city_facade failed: ' + repr(error))
        raise


def _in_engine():
    try:
        import unreal  # noqa: F401
    except ImportError:
        return False
    return True


if _in_engine():
    import unreal as _ue
    if SCRIPT_TOKEN in _ue.SystemLibrary.get_command_line().lower():
        _main()
elif __name__ == '__main__':
    print(json.dumps(offline_check(), indent=2))
