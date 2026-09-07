"""Guarded Jerusalem-context materials: CC0 PBR sets -> world-aligned materials -> asset-level assignment.

Scope (owned here): the 1,499 OSM building meshes, the 2,877 enabled street meshes
(asphalt / stone paths / city walls), the 256 terrain tiles and the 4 FutureMountV1 cut
tiles. Measured architecture, Release/* actors, sanctuary, vessels, landmarks and the
44,793 decorative instances are never mutated. Every number comes from
Scripts/release_context_materials.spec.json.

Stages
  0. Offline fetch (plain Python + curl, no engine): Poly Haven API -> six 2K PNG sets
     (Diffuse, nor_dx, Rough) into SourceAssets/materials-context/<slug>/ with a
     provenance.json (URLs, Poly Haven md5, our sha256, authors, CC0).
  1. Engine import: 18 textures (T_Ctx_<slug>_<D|N|R>) with the right compression/sRGB.
  2. Materials (MaterialExpressionCustom HLSL fed by TextureObject / WorldPosition /
     VertexNormalWS / ObjectPositionWS / VertexColor / parameters; tangent_space_normal off,
     world-space normals):
       M_Context_Building   triplanar, 400 cm tile, 4 warm tints picked by a hash of the
                            per-building vertex colour + ObjectPositionWS, roughness jitter,
                            roof faces fade to a flat plaster tint.
       M_Context_CityWall   same triplanar builder, old stone wall set, subtle tints.
       M_Context_Terrain    world XY 400 cm, dry ground vs scrub by vertex-colour luminance
                            and slope, two-octave macro value noise (6000 cm) against repetition.
       M_Context_Asphalt    world XY 300 cm + macro noise, two-sided like the source.
       M_Context_StonePath  world XY 400 cm + macro noise, two-sided like the source.
  3. Assignment (asset level, StaticMesh.set_material slot 0) to every mesh of the five
     categories after verifying each mesh currently carries the expected original material.
     Originals are recorded per mesh in the receipt. Meshes are saved; the map is saved only
     if the engine reports it dirty.
  4. Checkpoint (map + every touched .uasset copied to ReviewCheckpoints/ContextMaterials-<stamp>/),
     reopen the map, read back per-category component materials (all actors) plus N detailed
     samples, receipt SourceAssets/materials-context/native-apply-<stamp>.json.

Commandlet invocation (serial; never while another native job is running; editor closed):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_context_materials.py"
      -ContextApply -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-ContextMaterials-01.log"

Switches (exactly one mode):
  -ContextImportOnly           textures + materials into the fresh namespace; no assignment, no map load.
  -ContextApply                import if the namespace is missing, then assign + save + reopen + readback.
  -ContextRevert[=<receipt>]   restore the recorded original material on every mesh of the latest
                               (or named) native-apply receipt; textures/materials are kept.
  -ContextCategories=a,b       subset of buildings,asphalt,paths,walls,terrain,terraincut (apply/revert).
  -ContextSamples=<n>          detailed readback samples per category (default spec value).

Offline (no engine):
  python Scripts/release_context_materials.py --fetch      download the six CC0 sets (curl)
  python Scripts/release_context_materials.py --check      spec / files / on-disk inventory consistency

Byte-exact alternative to -ContextRevert: with the editor closed copy the .uasset files back
from the checkpoint folder recorded in the receipt.
"""
import argparse
import hashlib
import json
import random
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_context_materials.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
CATEGORY_ORDER = ('buildings', 'asphalt', 'paths', 'walls', 'terrain', 'terraincut')
MAP_KEYS = ('diffuse', 'normal', 'roughness')
MAP_SUFFIX = {'diffuse': 'D', 'normal': 'N', 'roughness': 'R'}


# --------------------------------------------------------------------------
# Spec and pure helpers (no unreal import)
# --------------------------------------------------------------------------

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    if set(spec['categories']) != set(CATEGORY_ORDER):
        raise RuntimeError('Spec categories differ from %s' % (CATEGORY_ORDER,))
    return spec


def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def md5_of(path):
    digest = hashlib.md5()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def stamp_now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def set_by_slug(spec, slug):
    for entry in spec['sets']:
        if entry['slug'] == slug:
            return entry
    raise RuntimeError('Unknown set slug ' + slug)


def set_folder(spec, slug):
    return ROOT / spec['sourceFolder'] / slug


def texture_asset_name(spec, slug, key):
    return spec['texturePrefix'] + slug.replace('-', '_') + '_' + MAP_SUFFIX[key]


def texture_asset_path(spec, slug, key):
    return spec['textureFolder'] + '/' + texture_asset_name(spec, slug, key)


def material_asset_path(spec, key):
    return spec['materialFolder'] + '/' + spec['materials'][key]['name']


def normalise_categories(value):
    if isinstance(value, str):
        value = value.split(',')
    wanted = [v.strip().lower() for v in value if v.strip()]
    unknown = [v for v in wanted if v not in CATEGORY_ORDER]
    if unknown:
        raise RuntimeError('Unknown categories %s; valid %s' % (unknown, list(CATEGORY_ORDER)))
    if not wanted:
        raise RuntimeError('No categories requested')
    return tuple(c for c in CATEGORY_ORDER if c in wanted)


def category_disk_inventory(spec, category):
    """Sorted asset paths of the meshes this category will touch, plus the skipped ones (disk only)."""
    cfg = spec['categories'][category]
    folder = disk_path(cfg['folder'] + '/x').parent
    touched, skipped = [], []
    for file in sorted(folder.glob('*.uasset')):
        name = file.stem
        if not name.startswith(cfg['namePrefix']):
            continue
        if cfg.get('nameSuffix') and not name.endswith(cfg['nameSuffix']):
            continue
        if any(name.endswith(s) for s in cfg.get('skipSuffixes', [])):
            skipped.append(cfg['folder'] + '/' + name)
            continue
        touched.append(cfg['folder'] + '/' + name)
    return touched, skipped


def provenance_path(spec, slug):
    return set_folder(spec, slug) / 'provenance.json'


def local_texture_files(spec, slug):
    """{key: Path} from provenance.json (raises if missing)."""
    prov_file = provenance_path(spec, slug)
    if not prov_file.exists():
        raise RuntimeError('Missing provenance (run --fetch): ' + str(prov_file))
    prov = json.loads(prov_file.read_text(encoding='utf-8-sig'))
    files = {}
    for key in MAP_KEYS:
        record = prov['files'][key]
        path = set_folder(spec, slug) / record['fileName']
        if not path.exists():
            raise RuntimeError('Missing texture file: ' + str(path))
        if sha256_of(path) != record['sha256']:
            raise RuntimeError('Texture sha256 differs from provenance: ' + str(path))
        files[key] = path
    return files, prov


# --------------------------------------------------------------------------
# Stage 0: Poly Haven fetch (offline)
# --------------------------------------------------------------------------

def _http_json(url):
    # The Poly Haven API answers 403 to urllib's default User-Agent; curl is accepted.
    result = subprocess.run(['curl', '-sS', '-L', '--fail', '--retry', '3', url], capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        raise RuntimeError('curl failed for %s: %s' % (url, result.stderr.strip()))
    return json.loads(result.stdout)


def _curl(url, destination):
    result = subprocess.run(['curl', '-sS', '-L', '--fail', '--retry', '3', '-o', str(destination), url],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError('curl failed for %s: %s' % (url, result.stderr.strip()))


def fetch_sets(spec, only=None, force=False):
    """Download every set (or `only` slugs). Returns the fetch report. Skips files already verified."""
    cfg = spec['polyHaven']
    report = {'sets': [], 'totalBytes': 0, 'budgetBytes': cfg['totalBudgetBytes']}
    for entry in spec['sets']:
        slug = entry['slug']
        if only and slug not in only:
            continue
        asset_id = entry['polyHavenId']
        folder = set_folder(spec, slug)
        folder.mkdir(parents=True, exist_ok=True)
        info = _http_json('%s/info/%s' % (cfg['api'], asset_id))
        files_index = _http_json('%s/files/%s' % (cfg['api'], asset_id))
        record = {'slug': slug, 'polyHavenId': asset_id, 'name': info.get('name'), 'authors': info.get('authors'),
                  'assetPage': 'https://polyhaven.com/a/' + asset_id, 'license': cfg['license'],
                  'licenseNote': cfg['licenseNote'], 'use': entry['use'],
                  'realSizeCm': entry['realSizeCm'], 'polyHavenDimensionsMm': info.get('dimensions'),
                  'tags': info.get('tags'), 'categories': info.get('categories'), 'description': info.get('description'),
                  'datePublished': info.get('date_published'), 'resolution': cfg['resolution'], 'formats': {k: cfg.get('formats', {}).get(k, cfg['format']) for k in MAP_KEYS},
                  'fetched': datetime.now(timezone.utc).isoformat(), 'files': {}}
        for key in MAP_KEYS:
            map_name = cfg['maps'][key]
            if map_name not in files_index:
                raise RuntimeError('%s has no %s map' % (asset_id, map_name))
            variants = files_index[map_name][cfg['resolution']]
            fmt = cfg.get('formats', {}).get(key, cfg['format'])
            if fmt not in variants:
                raise RuntimeError('%s %s lacks %s %s' % (asset_id, map_name, cfg['resolution'], fmt))
            variant = variants[fmt]
            url = variant['url']
            if not url.startswith(cfg['cdnFileRoot']):
                raise RuntimeError('Unexpected download host: ' + url)
            destination = folder / url.rsplit('/', 1)[1]
            if destination.exists() and not force and md5_of(destination) == variant['md5']:
                status = 'already_present_md5_verified'
            else:
                _curl(url, destination)
                status = 'downloaded'
            actual_md5 = md5_of(destination)
            if actual_md5 != variant['md5']:
                raise RuntimeError('md5 mismatch for %s: %s != %s' % (destination, actual_md5, variant['md5']))
            size = destination.stat().st_size
            if size != variant['size']:
                raise RuntimeError('size mismatch for %s: %d != %d' % (destination, size, variant['size']))
            record['files'][key] = {'polyHavenMap': map_name, 'format': fmt, 'url': url, 'fileName': destination.name, 'bytes': size,
                                    'polyHavenMd5': variant['md5'], 'sha256': sha256_of(destination), 'status': status}
            report['totalBytes'] += size
        record['polyHavenInfoSnapshot'] = info
        provenance_path(spec, slug).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        report['sets'].append(dict({k: record[k] for k in ('slug', 'polyHavenId', 'name', 'authors')}, files=record['files']))
    if report['totalBytes'] > cfg['totalBudgetBytes']:
        raise RuntimeError('Downloaded %d bytes exceed the budget %d' % (report['totalBytes'], cfg['totalBudgetBytes']))
    return report


# --------------------------------------------------------------------------
# Offline consistency check
# --------------------------------------------------------------------------

def offline_check(spec=None, require_textures=True):
    spec = spec or load_spec()
    report = {'sets': {}, 'categories': {}, 'untouched': {}}
    total_bytes = 0
    for entry in spec['sets']:
        slug = entry['slug']
        try:
            files, prov = local_texture_files(spec, slug)
            report['sets'][slug] = {'present': True, 'files': {k: str(v) for k, v in files.items()},
                                    'bytes': sum(v.stat().st_size for v in files.values()), 'polyHavenId': prov['polyHavenId']}
            total_bytes += report['sets'][slug]['bytes']
        except RuntimeError as error:
            if require_textures:
                raise
            report['sets'][slug] = {'present': False, 'error': str(error)}
    report['totalTextureBytes'] = total_bytes
    if total_bytes > spec['polyHaven']['totalBudgetBytes']:
        raise RuntimeError('Texture bytes exceed the budget')
    for key, material in spec['materials'].items():
        slugs = [material.get('set'), material.get('groundSet'), material.get('scrubSet')]
        for slug in [s for s in slugs if s]:
            set_by_slug(spec, slug)
        if material['kind'] == 'triplanar' and len(material['tints']) != 4:
            raise RuntimeError('Triplanar material %s needs exactly four tints' % key)
    planned = 0
    for category in CATEGORY_ORDER:
        cfg = spec['categories'][category]
        if cfg['material'] not in spec['materials']:
            raise RuntimeError('Category %s names unknown material %s' % (category, cfg['material']))
        touched, skipped = category_disk_inventory(spec, category)
        if len(touched) != cfg['expectedCount']:
            raise RuntimeError('%s: %d meshes on disk, spec expects %d' % (category, len(touched), cfg['expectedCount']))
        if len(skipped) != cfg.get('expectedSkipped', 0):
            raise RuntimeError('%s: %d skipped meshes on disk, spec expects %d' % (category, len(skipped), cfg.get('expectedSkipped', 0)))
        if not disk_path(cfg['expectedOriginalMaterial']).exists():
            raise RuntimeError('Original material missing on disk: ' + cfg['expectedOriginalMaterial'])
        planned += len(touched)
        report['categories'][category] = {'meshes': len(touched), 'skipped': skipped, 'material': spec['materials'][cfg['material']]['name']}
    if planned != spec['plannedAssignments']:
        raise RuntimeError('Planned assignments %d differ from spec %d' % (planned, spec['plannedAssignments']))
    report['plannedAssignments'] = planned
    landmarks = spec['untouched']['landmarks']
    folder = disk_path(landmarks['folder'] + '/x').parent
    count = len([f for f in folder.glob('*.uasset') if f.stem.startswith(landmarks['namePrefix'])])
    if count != landmarks['expectedCount']:
        raise RuntimeError('Landmark mesh count %d differs from %d' % (count, landmarks['expectedCount']))
    report['untouched']['landmarks'] = count
    map_file = ROOT / spec['targetMapFile']
    if not map_file.exists():
        raise RuntimeError('Target map missing: ' + str(map_file))
    report['targetMapSha256'] = sha256_of(map_file)
    report['targetMapMatchesLastKnown'] = report['targetMapSha256'] == spec['lastKnownMapSha256']
    namespace_disk = disk_path(spec['namespace'] + '/x').parent
    report['namespaceOnDisk'] = namespace_disk.exists() and any(namespace_disk.rglob('*.uasset'))
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# HLSL for the Custom nodes (static; every tunable arrives through a Custom input)
# --------------------------------------------------------------------------

# Inputs: Albedo, Rough (texture objects), P (WorldPosition), N (VertexNormalWS), ObjPos (ObjectPositionWS),
# VC (VertexColor), Tint0..Tint3, RoofTint (vector params), scalars TileCm, RoofScale, RoofStart, RoofEnd,
# RoofFlatten, RoughScale, RoughBias, RoughVar, VCInfluence, VCMeanLum, HashObjectWeight, HashVertexColorWeight.
HLSL_TRIPLANAR_SURFACE = r'''
float3 p = P.xyz / TileCm;
float3 n = normalize(N.xyz);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 1e-4);
float2 uvX = p.zy;
float2 uvY = p.xz;
float2 uvZ = p.xy * RoofScale;
float3 aX = Texture2DSample(Albedo, AlbedoSampler, uvX).rgb;
float3 aY = Texture2DSample(Albedo, AlbedoSampler, uvY).rgb;
float3 aZ = Texture2DSample(Albedo, AlbedoSampler, uvZ).rgb;
float rX = Texture2DSample(Rough, RoughSampler, uvX).r;
float rY = Texture2DSample(Rough, RoughSampler, uvY).r;
float rZ = Texture2DSample(Rough, RoughSampler, uvZ).r;
float3 wallAlbedo = aX * w.x + aY * w.y + aZ * w.z;
float wallRough = rX * w.x + rY * w.y + rZ * w.z;
float hv = dot(VC.rgb, float3(12.9898, 78.233, 37.719)) * HashVertexColorWeight;
float ho = dot(ObjPos.xyz * 0.001, float3(0.7548, 0.5698, 0.3176)) * HashObjectWeight;
float h = frac(hv + ho + 0.1731);
float idx = floor(h * 4.0);
float3 tint = (idx < 0.5) ? Tint0.rgb : ((idx < 1.5) ? Tint1.rgb : ((idx < 2.5) ? Tint2.rgb : Tint3.rgb));
float h2 = frac(h * 7.31 + 0.37);
float vcl = dot(VC.rgb, float3(0.3333, 0.3333, 0.3333)) / max(VCMeanLum, 1e-3);
float vcMod = lerp(1.0, clamp(vcl, 0.7, 1.3), VCInfluence);
float roofMix = smoothstep(RoofStart, RoofEnd, n.z);
float3 roofAlbedo = lerp(aZ, RoofTint.rgb, RoofFlatten);
float3 color = lerp(wallAlbedo * tint, roofAlbedo, roofMix) * vcMod;
float rough = saturate(lerp(wallRough, rZ, roofMix) * RoughScale + RoughBias + (h2 - 0.5) * RoughVar);
return float4(color, rough);
'''

# Inputs: Nrm (texture object), P, N, TileCm, RoofScale, NormalStrength, NormalGreenSign.
HLSL_TRIPLANAR_NORMAL = r'''
float3 p = P.xyz / TileCm;
float3 n = normalize(N.xyz);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 1e-4);
float3 sX = Texture2DSample(Nrm, NrmSampler, p.zy).xyz;
float3 sY = Texture2DSample(Nrm, NrmSampler, p.xz).xyz;
float3 sZ = Texture2DSample(Nrm, NrmSampler, p.xy * RoofScale).xyz;
float3 tX; float3 tY; float3 tZ;
tX.xy = (sX.xy * 2.0 - 1.0) * float2(1.0, NormalGreenSign) * NormalStrength;
tY.xy = (sY.xy * 2.0 - 1.0) * float2(1.0, NormalGreenSign) * NormalStrength;
tZ.xy = (sZ.xy * 2.0 - 1.0) * float2(1.0, NormalGreenSign) * NormalStrength;
tX.z = sqrt(saturate(1.0 - dot(tX.xy, tX.xy)));
tY.z = sqrt(saturate(1.0 - dot(tY.xy, tY.xy)));
tZ.z = sqrt(saturate(1.0 - dot(tZ.xy, tZ.xy)));
tX = float3(tX.xy + n.zy, abs(tX.z) * n.x);
tY = float3(tY.xy + n.xz, abs(tY.z) * n.y);
tZ = float3(tZ.xy + n.xy, abs(tZ.z) * n.z);
return normalize(tX.zyx * w.x + tY.xzy * w.y + tZ.xyz * w.z);
'''

# Inputs: GroundA, GroundR, ScrubA, ScrubR (texture objects), P, N, VC, GroundTint, ScrubTint, TileCm, ScrubTileCm,
# MaskLumLow, MaskLumHigh, SlopeStart, SlopeEnd, MacroCm, MacroAmp, RoughScale, RoughBias.
HLSL_TERRAIN_SURFACE = r'''
float2 uv = P.xy / TileCm;
float2 uvS = P.xy / ScrubTileCm;
float3 ga = Texture2DSample(GroundA, GroundASampler, uv).rgb * GroundTint.rgb;
float gr = Texture2DSample(GroundR, GroundRSampler, uv).r;
float3 sa = Texture2DSample(ScrubA, ScrubASampler, uvS).rgb * ScrubTint.rgb;
float sr = Texture2DSample(ScrubR, ScrubRSampler, uvS).r;
float lum = dot(VC.rgb, float3(0.2126, 0.7152, 0.0722));
float scrub = 1.0 - smoothstep(MaskLumLow, MaskLumHigh, lum);
float slope = smoothstep(SlopeStart, SlopeEnd, normalize(N.xyz).z);
scrub *= slope;
float2 q = P.xy / MacroCm;
float2 i0 = floor(q); float2 f0 = frac(q); f0 = f0 * f0 * (3.0 - 2.0 * f0);
float a0 = frac(sin(dot(i0, float2(127.1, 311.7))) * 43758.5453);
float b0 = frac(sin(dot(i0 + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float c0 = frac(sin(dot(i0 + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float d0 = frac(sin(dot(i0 + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float n0 = lerp(lerp(a0, b0, f0.x), lerp(c0, d0, f0.x), f0.y);
float2 q1 = q * 4.3 + float2(17.0, 9.0);
float2 i1 = floor(q1); float2 f1 = frac(q1); f1 = f1 * f1 * (3.0 - 2.0 * f1);
float a1 = frac(sin(dot(i1, float2(127.1, 311.7))) * 43758.5453);
float b1 = frac(sin(dot(i1 + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float c1 = frac(sin(dot(i1 + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float d1 = frac(sin(dot(i1 + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float n1 = lerp(lerp(a1, b1, f1.x), lerp(c1, d1, f1.x), f1.y);
float nse = n0 * 0.65 + n1 * 0.35;
float macro = 1.0 + (nse - 0.5) * 2.0 * MacroAmp;
scrub = saturate(scrub + (nse - 0.5) * 0.3 * (scrub > 0.02 ? 1.0 : 0.0));
float3 color = lerp(ga, sa, scrub) * macro;
float rough = saturate(lerp(gr, sr, scrub) * RoughScale + RoughBias);
return float4(color, rough);
'''

# Inputs: GroundN, ScrubN (texture objects), P, N, VC, TileCm, ScrubTileCm, MaskLumLow, MaskLumHigh, SlopeStart,
# SlopeEnd, NormalStrength, NormalGreenSign.
HLSL_TERRAIN_NORMAL = r'''
float2 uv = P.xy / TileCm;
float2 uvS = P.xy / ScrubTileCm;
float3 n = normalize(N.xyz);
float lum = dot(VC.rgb, float3(0.2126, 0.7152, 0.0722));
float scrub = (1.0 - smoothstep(MaskLumLow, MaskLumHigh, lum)) * smoothstep(SlopeStart, SlopeEnd, n.z);
float3 sg = Texture2DSample(GroundN, GroundNSampler, uv).xyz;
float3 ss = Texture2DSample(ScrubN, ScrubNSampler, uvS).xyz;
float2 txy = lerp(sg.xy, ss.xy, scrub) * 2.0 - 1.0;
txy *= float2(1.0, NormalGreenSign) * NormalStrength;
float tz = sqrt(saturate(1.0 - dot(txy, txy)));
float3 t = float3(txy + n.xy, abs(tz) * n.z);
return normalize(t);
'''

# Inputs: Albedo, Rough (texture objects), P, Tint, TileCm, MacroCm, MacroAmp, RoughScale, RoughBias.
HLSL_FLAT_SURFACE = r'''
float2 uv = P.xy / TileCm;
float3 a = Texture2DSample(Albedo, AlbedoSampler, uv).rgb * Tint.rgb;
float r = Texture2DSample(Rough, RoughSampler, uv).r;
float2 q = P.xy / MacroCm;
float2 i0 = floor(q); float2 f0 = frac(q); f0 = f0 * f0 * (3.0 - 2.0 * f0);
float a0 = frac(sin(dot(i0, float2(127.1, 311.7))) * 43758.5453);
float b0 = frac(sin(dot(i0 + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float c0 = frac(sin(dot(i0 + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float d0 = frac(sin(dot(i0 + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float nse = lerp(lerp(a0, b0, f0.x), lerp(c0, d0, f0.x), f0.y);
float macro = 1.0 + (nse - 0.5) * 2.0 * MacroAmp;
return float4(a * macro, saturate(r * RoughScale + RoughBias));
'''

# Inputs: Nrm (texture object), P, N, TileCm, NormalStrength, NormalGreenSign.
HLSL_FLAT_NORMAL = r'''
float2 uv = P.xy / TileCm;
float3 n = normalize(N.xyz);
float3 s = Texture2DSample(Nrm, NrmSampler, uv).xyz;
float2 txy = (s.xy * 2.0 - 1.0) * float2(1.0, NormalGreenSign) * NormalStrength;
float tz = sqrt(saturate(1.0 - dot(txy, txy)));
return normalize(float3(txy + n.xy, abs(tz) * n.z));
'''

NORMAL_GREEN_SIGN = 1.0  # nor_dx with V = +world axis; set -1.0 if raking light reads inverted (see spec limitations)


def graph_descriptions(spec):
    """Human-readable graph summaries for the receipt / report."""
    m = spec['materials']
    return {
        m['building']['name']: 'TextureObject(D,R,N) + WorldPosition + VertexNormalWS + ObjectPositionWS + VertexColor + 4 tint VectorParameters + RoofTint + %d ScalarParameters -> Custom(HLSL triplanar surface, float4 rgb+rough) -> ComponentMask RGB -> BaseColor, A -> Roughness; Custom(HLSL triplanar whiteout normal, float3 world) -> Normal; Constant 0 -> Metallic; tangent_space_normal off' % len(m['building']['params']),
        m['citywall']['name']: 'Same builder as M_Context_Building with the old stone wall set, subtle tints, no vertex-colour hash (HashVertexColorWeight 0)',
        m['terrain']['name']: 'TextureObject(ground D,R,N; scrub D,R,N) + WorldPosition + VertexNormalWS + VertexColor + GroundTint/ScrubTint + %d ScalarParameters -> Custom(HLSL: XY projection, scrub = 1-smoothstep(lum) * slope, two-octave value noise macro) -> BaseColor/Roughness; Custom(normal lerp by the same mask) -> Normal' % len(m['terrain']['params']),
        m['asphalt']['name']: 'TextureObject(D,R,N) + WorldPosition + VertexNormalWS + Tint + %d ScalarParameters -> Custom(HLSL: XY projection + value-noise macro) -> BaseColor/Roughness; Custom(normal) -> Normal; two-sided' % len(m['asphalt']['params']),
        m['stonepath']['name']: 'As M_Context_Asphalt with the cobble set; two-sided',
    }


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _enum(ue, enum_name, *candidates):
    enum = getattr(ue, enum_name)
    for name in candidates:
        if name and hasattr(enum, name):
            return getattr(enum, name), name
    raise RuntimeError('%s has none of %s' % (enum_name, candidates))


class Engine:
    """Engine handles, texture import, material graphs, assignment, readback."""

    def __init__(self, ue, spec, receipt, receipt_path):
        self.ue = ue
        self.spec = spec
        self.receipt = receipt
        self.receipt_path = receipt_path
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.ml = ue.MaterialEditingLibrary

    def write(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- guards ---------------------------------------------------------------

    def common_guards(self):
        ue = self.ue
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
        if self.editor.get_game_world():
            raise RuntimeError('A game world is active; never mutate during play')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present before the run')

    def namespace_exists(self):
        namespace = self.spec['namespace']
        on_disk = disk_path(namespace + '/x').parent
        return bool(self.assets.does_directory_exist(namespace)) or (on_disk.exists() and any(on_disk.rglob('*.uasset')))

    # -- textures ---------------------------------------------------------------

    def import_texture(self, slug, key, png_path):
        ue = self.ue
        cfg = self.spec['textureImport'][key]
        name = texture_asset_name(self.spec, slug, key)
        folder = self.spec['textureFolder']
        if self.assets.does_asset_exist(folder + '/' + name):
            raise RuntimeError('Texture already exists; namespace must be fresh: ' + folder + '/' + name)
        task = ue.AssetImportTask()
        for prop, value in dict(filename=str(png_path), destination_path=folder, destination_name=name, automated=True,
                                replace_existing=False, save=False).items():
            task.set_editor_property(prop, value)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects = list(task.get_objects())
        if len(objects) != 1 or not isinstance(objects[0], ue.Texture2D):
            raise RuntimeError('Texture import of %s produced %s' % (png_path, [type(o).__name__ for o in objects]))
        tex = objects[0]
        compression, compression_name = _enum(ue, 'TextureCompressionSettings', cfg['compression'], cfg.get('compressionFallback'))
        tex.set_editor_property('compression_settings', compression)
        tex.set_editor_property('srgb', bool(cfg['srgb']))
        if key == 'normal':
            tex.set_editor_property('flip_green_channel', bool(cfg['flipGreenChannel']))
        if not self.assets.save_loaded_asset(tex, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + name)
        size = None
        for getter in ('blueprint_get_size_x', 'get_size_x'):
            if hasattr(tex, getter):
                try:
                    size = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
                except Exception:
                    size = None
                break
        record = {'asset': _asset_path(tex), 'sourcePng': str(png_path), 'sourceSha256': sha256_of(png_path),
                  'compression': compression_name, 'srgb': bool(tex.get_editor_property('srgb')), 'size': size,
                  'uassetSha256': sha256_of(disk_path(_asset_path(tex)))}
        if key == 'normal':
            record['flipGreenChannel'] = bool(tex.get_editor_property('flip_green_channel'))
        self.receipt['textures'][slug + '/' + key] = record
        return tex

    def import_all_textures(self):
        textures = {}
        for entry in self.spec['sets']:
            slug = entry['slug']
            files, prov = local_texture_files(self.spec, slug)
            textures[slug] = {key: self.import_texture(slug, key, files[key]) for key in MAP_KEYS}
            self.receipt['provenance'][slug] = {'polyHavenId': prov['polyHavenId'], 'authors': prov.get('authors'),
                                                'license': prov['license'], 'assetPage': prov['assetPage']}
            self.write()
        return textures

    def load_textures(self):
        """Textures already saved in the namespace (apply after import-only)."""
        ue = self.ue
        textures = {}
        for entry in self.spec['sets']:
            slug = entry['slug']
            textures[slug] = {}
            for key in MAP_KEYS:
                path = texture_asset_path(self.spec, slug, key)
                tex = ue.load_asset(path)
                if not isinstance(tex, ue.Texture2D):
                    raise RuntimeError('Saved texture missing or wrong class: ' + path)
                textures[slug][key] = tex
        return textures

    # -- materials --------------------------------------------------------------

    class Graph:
        """Node builder bound to one UMaterial."""

        def __init__(self, engine, material, record):
            self.engine = engine
            self.ue = engine.ue
            self.ml = engine.ml
            self.material = material
            self.record = record
            self.row = 0

        def node(self, cls, x, y, **props):
            expression = self.ml.create_material_expression(self.material, cls, x, y)
            if expression is None:
                raise RuntimeError('create_material_expression failed for ' + cls.__name__)
            for key, value in props.items():
                expression.set_editor_property(key, value)
            self.record['nodes'].append({'class': cls.__name__, 'position': [x, y],
                                         'properties': {k: (v if isinstance(v, (int, float, bool, str)) else str(v)) for k, v in props.items() if k != 'code'}})
            return expression

        def wire(self, source, target, input_name, output=''):
            if not self.ml.connect_material_expressions(source, output, target, input_name):
                names = [str(n) for n in self.ml.get_material_expression_input_names(target)]
                raise RuntimeError('Connection %s -> %s.%s failed (inputs %s)' % (source.get_class().get_name(), target.get_class().get_name(), input_name, names))
            self.record['connections'].append('%s -> %s.%s' % (source.get_class().get_name(), target.get_class().get_name(), input_name))

        def to_property(self, source, prop_name, output=''):
            prop = getattr(self.ue.MaterialProperty, prop_name)
            if not self.ml.connect_material_property(source, output, prop):
                raise RuntimeError('connect_material_property %s -> %s failed' % (source.get_class().get_name(), prop_name))
            self.record['connections'].append('%s -> %s' % (source.get_class().get_name(), prop_name))

        def texture_object(self, tex, x, y):
            return self.node(self.ue.MaterialExpressionTextureObject, x, y, texture=tex)

        def scalar(self, name, value, x, y):
            return self.node(self.ue.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(value))

        def vector(self, name, rgb, x, y):
            return self.node(self.ue.MaterialExpressionVectorParameter, x, y, parameter_name=name,
                             default_value=self.ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))

        def custom(self, code, inputs, output_type, x, y, description):
            ue = self.ue
            slots = []
            for name in inputs:
                slot = ue.CustomInput()
                slot.set_editor_property('input_name', name)
                slots.append(slot)
            expression = self.node(ue.MaterialExpressionCustom, x, y, inputs=slots, code=code.strip(), output_type=output_type, description=description)
            for name, source in inputs.items():
                self.wire(source, expression, name)
            self.record['customNodes'].append({'description': description, 'inputs': list(inputs), 'codeSha256': hashlib.sha256(code.encode()).hexdigest()})
            return expression

        def finish(self, surface, normal, two_sided):
            ue = self.ue
            rgb = self.node(ue.MaterialExpressionComponentMask, 200, -300, r=True, g=True, b=True, a=False)
            alpha = self.node(ue.MaterialExpressionComponentMask, 200, -100, r=False, g=False, b=False, a=True)
            self.wire(surface, rgb, '')
            self.wire(surface, alpha, '')
            metallic = self.node(ue.MaterialExpressionConstant, 200, 300, r=0.0)
            self.to_property(rgb, 'MP_BASE_COLOR')
            self.to_property(alpha, 'MP_ROUGHNESS')
            self.to_property(normal, 'MP_NORMAL')
            self.to_property(metallic, 'MP_METALLIC')
            self.material.set_editor_property('tangent_space_normal', False)
            self.material.set_editor_property('two_sided', bool(two_sided))
            if self.ml.get_material_property_input_node(self.material, ue.MaterialProperty.MP_WORLD_POSITION_OFFSET) is not None:
                raise RuntimeError('WorldPositionOffset unexpectedly connected')

    def _new_material(self, key):
        ue = self.ue
        cfg = self.spec['materials'][key]
        path = material_asset_path(self.spec, key)
        if self.assets.does_asset_exist(path):
            raise RuntimeError('Material already exists; namespace must be fresh: ' + path)
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(cfg['name'], self.spec['materialFolder'], ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Material factory failed for ' + path)
        record = {'asset': path, 'kind': cfg['kind'], 'nodes': [], 'connections': [], 'customNodes': [], 'status': 'started'}
        self.receipt['materials'][key] = record
        return material, record

    def _save_material(self, key, material, record):
        ue = self.ue
        self.ml.recompile_material(material)
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + record['asset'])
        record['inputsWired'] = {}
        for prop_name in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_WORLD_POSITION_OFFSET'):
            wired = self.ml.get_material_property_input_node(material, getattr(ue.MaterialProperty, prop_name))
            record['inputsWired'][prop_name] = wired.get_class().get_name() if wired else None
        record['twoSided'] = bool(material.get_editor_property('two_sided'))
        record['tangentSpaceNormal'] = bool(material.get_editor_property('tangent_space_normal'))
        record['uassetSha256'] = sha256_of(disk_path(record['asset']))
        record['status'] = 'saved'
        self.write()
        return material

    def build_triplanar(self, key, textures):
        ue = self.ue
        cfg = self.spec['materials'][key]
        tex = textures[cfg['set']]
        material, record = self._new_material(key)
        g = self.Graph(self, material, record)
        albedo = g.texture_object(tex['diffuse'], -1400, -600)
        rough = g.texture_object(tex['roughness'], -1400, -450)
        normal_tex = g.texture_object(tex['normal'], -1400, -300)
        position = g.node(ue.MaterialExpressionWorldPosition, -1400, -150)
        vertex_normal = g.node(ue.MaterialExpressionVertexNormalWS, -1400, -50)
        object_position = g.node(ue.MaterialExpressionObjectPositionWS, -1400, 50)
        vertex_color = g.node(ue.MaterialExpressionVertexColor, -1400, 150)
        params = {}
        for index, (name, value) in enumerate(cfg['params'].items()):
            params[name] = g.scalar(name, value, -1400, 300 + index * 80)
        tints = {'Tint%d' % i: g.vector('Tint%d' % i, rgb, -1100, -600 + i * 120) for i, rgb in enumerate(cfg['tints'])}
        roof_tint = g.vector('RoofTint', cfg['roofTint'], -1100, -100)
        surface_inputs = {'Albedo': albedo, 'Rough': rough, 'P': position, 'N': vertex_normal, 'ObjPos': object_position, 'VC': vertex_color}
        surface_inputs.update(tints)
        surface_inputs['RoofTint'] = roof_tint
        for name in ('TileCm', 'RoofScale', 'RoofStart', 'RoofEnd', 'RoofFlatten', 'RoughScale', 'RoughBias', 'RoughVar',
                     'VCInfluence', 'VCMeanLum', 'HashObjectWeight', 'HashVertexColorWeight'):
            surface_inputs[name] = params[name]
        surface = g.custom(HLSL_TRIPLANAR_SURFACE, surface_inputs, ue.CustomMaterialOutputType.CMOT_FLOAT4, -400, -300,
                           'Context triplanar surface (rgb, roughness); hashed per-object tint; roof fade')
        green_sign = g.node(ue.MaterialExpressionConstant, -1100, 100, r=float(NORMAL_GREEN_SIGN))
        normal = g.custom(HLSL_TRIPLANAR_NORMAL, {'Nrm': normal_tex, 'P': position, 'N': vertex_normal, 'TileCm': params['TileCm'],
                                                  'RoofScale': params['RoofScale'], 'NormalStrength': params['NormalStrength'],
                                                  'NormalGreenSign': green_sign},
                          ue.CustomMaterialOutputType.CMOT_FLOAT3, -400, 200, 'Context triplanar whiteout world normal')
        g.finish(surface, normal, cfg['twoSided'])
        return self._save_material(key, material, record)

    def build_terrain(self, key, textures):
        ue = self.ue
        cfg = self.spec['materials'][key]
        ground = textures[cfg['groundSet']]
        scrub = textures[cfg['scrubSet']]
        material, record = self._new_material(key)
        g = self.Graph(self, material, record)
        ground_a = g.texture_object(ground['diffuse'], -1400, -700)
        ground_r = g.texture_object(ground['roughness'], -1400, -580)
        ground_n = g.texture_object(ground['normal'], -1400, -460)
        scrub_a = g.texture_object(scrub['diffuse'], -1400, -340)
        scrub_r = g.texture_object(scrub['roughness'], -1400, -220)
        scrub_n = g.texture_object(scrub['normal'], -1400, -100)
        position = g.node(ue.MaterialExpressionWorldPosition, -1400, 20)
        vertex_normal = g.node(ue.MaterialExpressionVertexNormalWS, -1400, 120)
        vertex_color = g.node(ue.MaterialExpressionVertexColor, -1400, 220)
        params = {}
        for index, (name, value) in enumerate(cfg['params'].items()):
            params[name] = g.scalar(name, value, -1400, 340 + index * 80)
        ground_tint = g.vector('GroundTint', cfg['groundTint'], -1100, -600)
        scrub_tint = g.vector('ScrubTint', cfg['scrubTint'], -1100, -480)
        surface_inputs = {'GroundA': ground_a, 'GroundR': ground_r, 'ScrubA': scrub_a, 'ScrubR': scrub_r, 'P': position, 'N': vertex_normal,
                          'VC': vertex_color, 'GroundTint': ground_tint, 'ScrubTint': scrub_tint}
        for name in ('TileCm', 'ScrubTileCm', 'MaskLumLow', 'MaskLumHigh', 'SlopeStart', 'SlopeEnd', 'MacroCm', 'MacroAmp', 'RoughScale', 'RoughBias'):
            surface_inputs[name] = params[name]
        surface = g.custom(HLSL_TERRAIN_SURFACE, surface_inputs, ue.CustomMaterialOutputType.CMOT_FLOAT4, -400, -300,
                           'Context terrain: dry ground vs scrub by vertex-colour luminance and slope, macro noise')
        green_sign = g.node(ue.MaterialExpressionConstant, -1100, -300, r=float(NORMAL_GREEN_SIGN))
        normal_inputs = {'GroundN': ground_n, 'ScrubN': scrub_n, 'P': position, 'N': vertex_normal, 'VC': vertex_color, 'NormalGreenSign': green_sign}
        for name in ('TileCm', 'ScrubTileCm', 'MaskLumLow', 'MaskLumHigh', 'SlopeStart', 'SlopeEnd', 'NormalStrength'):
            normal_inputs[name] = params[name]
        normal = g.custom(HLSL_TERRAIN_NORMAL, normal_inputs, ue.CustomMaterialOutputType.CMOT_FLOAT3, -400, 200, 'Context terrain world normal')
        g.finish(surface, normal, cfg['twoSided'])
        return self._save_material(key, material, record)

    def build_flat(self, key, textures):
        ue = self.ue
        cfg = self.spec['materials'][key]
        tex = textures[cfg['set']]
        material, record = self._new_material(key)
        g = self.Graph(self, material, record)
        albedo = g.texture_object(tex['diffuse'], -1400, -500)
        rough = g.texture_object(tex['roughness'], -1400, -380)
        normal_tex = g.texture_object(tex['normal'], -1400, -260)
        position = g.node(ue.MaterialExpressionWorldPosition, -1400, -140)
        vertex_normal = g.node(ue.MaterialExpressionVertexNormalWS, -1400, -40)
        params = {}
        for index, (name, value) in enumerate(cfg['params'].items()):
            params[name] = g.scalar(name, value, -1400, 80 + index * 80)
        tint = g.vector('Tint', cfg['tint'], -1100, -500)
        surface = g.custom(HLSL_FLAT_SURFACE, {'Albedo': albedo, 'Rough': rough, 'P': position, 'Tint': tint, 'TileCm': params['TileCm'],
                                               'MacroCm': params['MacroCm'], 'MacroAmp': params['MacroAmp'], 'RoughScale': params['RoughScale'],
                                               'RoughBias': params['RoughBias']},
                           ue.CustomMaterialOutputType.CMOT_FLOAT4, -400, -300, 'Context flat world-XY surface with macro noise')
        green_sign = g.node(ue.MaterialExpressionConstant, -1100, -300, r=float(NORMAL_GREEN_SIGN))
        normal = g.custom(HLSL_FLAT_NORMAL, {'Nrm': normal_tex, 'P': position, 'N': vertex_normal, 'TileCm': params['TileCm'],
                                             'NormalStrength': params['NormalStrength'], 'NormalGreenSign': green_sign},
                          ue.CustomMaterialOutputType.CMOT_FLOAT3, -400, 200, 'Context flat world normal')
        g.finish(surface, normal, cfg['twoSided'])
        return self._save_material(key, material, record)

    def build_all_materials(self, textures):
        materials = {}
        for key, cfg in self.spec['materials'].items():
            builder = {'triplanar': self.build_triplanar, 'terrain': self.build_terrain, 'flat': self.build_flat}[cfg['kind']]
            materials[key] = builder(key, textures)
        return materials

    def load_materials(self):
        ue = self.ue
        materials = {}
        for key in self.spec['materials']:
            path = material_asset_path(self.spec, key)
            material = ue.load_asset(path)
            if not isinstance(material, ue.Material):
                raise RuntimeError('Saved material missing or wrong class: ' + path)
            materials[key] = material
        return materials

    # -- assignment -------------------------------------------------------------

    def assign_category(self, category, material, dry_run=False):
        """Verify + assign slot 0 on every mesh of the category. Returns per-mesh rows."""
        ue = self.ue
        cfg = self.spec['categories'][category]
        touched, skipped = category_disk_inventory(self.spec, category)
        new_path = _asset_path(material)
        rows = []
        for asset_path in touched:
            mesh = ue.load_asset(asset_path)
            if not isinstance(mesh, ue.StaticMesh):
                raise RuntimeError('Not a StaticMesh: ' + asset_path)
            slots = mesh.get_editor_property('static_materials')
            if len(slots) != self.spec['verification']['materialSlotCountExpected']:
                raise RuntimeError('%s has %d material slots' % (asset_path, len(slots)))
            current = _asset_path(mesh.get_material(0))
            row = {'asset': asset_path, 'original': current}
            if current == new_path:
                row['action'] = 'already_context_material'
                rows.append(row)
                continue
            if current != cfg['expectedOriginalMaterial']:
                raise RuntimeError('%s carries %s, expected %s; refusing to overwrite an unexpected material' % (asset_path, current, cfg['expectedOriginalMaterial']))
            if dry_run:
                row['action'] = 'planned'
                rows.append(row)
                continue
            mesh.set_material(0, material)
            if _asset_path(mesh.get_material(0)) != new_path:
                raise RuntimeError('set_material readback differs for ' + asset_path)
            if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + asset_path)
            row['action'] = 'assigned_saved'
            row['uassetSha256After'] = sha256_of(disk_path(asset_path))
            rows.append(row)
        return rows, skipped

    def revert_rows(self, rows, context_material_paths):
        ue = self.ue
        out = []
        for row in rows:
            asset_path = row['asset']
            mesh = ue.load_asset(asset_path)
            if not isinstance(mesh, ue.StaticMesh):
                raise RuntimeError('Not a StaticMesh: ' + asset_path)
            current = _asset_path(mesh.get_material(0))
            entry = {'asset': asset_path, 'before': current, 'original': row['original']}
            if current == row['original']:
                entry['action'] = 'already_original'
            elif current not in context_material_paths:
                raise RuntimeError('%s carries %s, neither the context material nor the recorded original' % (asset_path, current))
            else:
                original = ue.load_asset(row['original'])
                if not isinstance(original, ue.MaterialInterface):
                    raise RuntimeError('Original material missing: ' + row['original'])
                mesh.set_material(0, original)
                if _asset_path(mesh.get_material(0)) != row['original']:
                    raise RuntimeError('revert readback differs for ' + asset_path)
                if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                    raise RuntimeError('save_loaded_asset failed for ' + asset_path)
                entry['action'] = 'reverted_saved'
            out.append(entry)
        return out

    # -- map / readback ---------------------------------------------------------

    def load_target(self):
        if not self.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = self.editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        return world

    def component_readback(self, expected_by_category, samples_per_category):
        """Walk every actor; classify StaticMeshComponents by the mesh folder/prefix; verify materials."""
        ue = self.ue
        spec = self.spec
        per_category = {c: {'components': 0, 'matching': 0, 'mismatched': [], 'overridden': 0, 'meshes': set()} for c in expected_by_category}
        candidates = {c: [] for c in expected_by_category}
        ism = []
        landmarks = 0
        actor_count = 0
        for actor in self.actors.get_all_level_actors():
            actor_count += 1
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                mesh = component.get_editor_property('static_mesh')
                if mesh is None:
                    continue
                mesh_path = _asset_path(mesh)
                folder, name = mesh_path.rsplit('/', 1)
                if isinstance(component, ue.InstancedStaticMeshComponent):
                    if folder.startswith(spec['untouched']['decorativeInstances']['folder']):
                        ism.append({'actor': actor.get_actor_label(), 'component': component.get_name(), 'mesh': mesh_path,
                                    'instances': int(component.get_instance_count()), 'material': _asset_path(component.get_material(0))})
                    continue
                if folder == spec['untouched']['landmarks']['folder'] and name.startswith(spec['untouched']['landmarks']['namePrefix']):
                    landmarks += 1
                    continue
                for category, expected in expected_by_category.items():
                    cfg = spec['categories'][category]
                    if folder != cfg['folder'] or not name.startswith(cfg['namePrefix']):
                        continue
                    if cfg.get('nameSuffix') and not name.endswith(cfg['nameSuffix']):
                        continue
                    if category == 'terrain' and name.endswith('_FutureMountCut'):
                        continue
                    if any(name.endswith(s) for s in cfg.get('skipSuffixes', [])):
                        continue
                    stats = per_category[category]
                    stats['components'] += 1
                    stats['meshes'].add(mesh_path)
                    overrides = [m for m in component.get_editor_property('override_materials') if m is not None]
                    if overrides:
                        stats['overridden'] += 1
                    actual = _asset_path(component.get_material(0))
                    if actual == expected:
                        stats['matching'] += 1
                    elif len(stats['mismatched']) < 20:
                        stats['mismatched'].append({'actor': actor.get_actor_label(), 'mesh': mesh_path, 'material': actual})
                    candidates[category].append((actor, component, mesh_path, actual, len(overrides)))
                    break
        rng = random.Random(20260907)
        samples = {}
        for category, rows in candidates.items():
            picked = rng.sample(rows, min(samples_per_category, len(rows))) if rows else []
            samples[category] = [{'actor': a.get_actor_label(), 'component': c.get_path_name(), 'mesh': m, 'material': mat, 'overrideMaterials': o,
                                  'mobility': str(c.get_editor_property('mobility'))} for a, c, m, mat, o in picked]
        summary = {c: {'components': s['components'], 'distinctMeshes': len(s['meshes']), 'matching': s['matching'],
                       'mismatched': s['mismatched'], 'mismatchedCount': s['components'] - s['matching'], 'componentsWithOverrides': s['overridden']}
                   for c, s in per_category.items()}
        return {'actorCount': actor_count, 'perCategory': summary, 'samples': samples, 'landmarkComponentsUntouched': landmarks,
                'decorativeInstanceComponents': ism, 'decorativeInstancesTotal': sum(r['instances'] for r in ism)}


# --------------------------------------------------------------------------
# Runs
# --------------------------------------------------------------------------

def _receipt_path(spec, prefix, stamp):
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ('%s-%s.json' % (prefix, stamp))
    if path.exists():
        raise RuntimeError('Receipt already exists: ' + str(path))
    return path


def _protected_hashes(spec):
    return {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}


def _checkpoint(spec, stamp, map_file, asset_paths):
    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != sha256_of(map_file):
        raise RuntimeError('Checkpoint map copy hash differs')
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
    copied = 0
    for asset_path in asset_paths:
        source = disk_path(asset_path)
        destination = checkpoint / 'Content' / (asset_path[6:] + '.uasset')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return checkpoint, copied


def run(mode, categories=CATEGORY_ORDER, samples=None, revert_receipt=None):
    import unreal as ue
    spec = load_spec()
    categories = normalise_categories(categories)
    samples = int(samples if samples is not None else spec['sampleReadbackPerCategory'])
    offline = offline_check(spec, require_textures=(mode != 'revert'))
    stamp = stamp_now()
    prefix = {'import': 'native-import', 'apply': 'native-apply', 'revert': 'native-revert'}[mode]
    receipt_path = _receipt_path(spec, prefix, stamp)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = _protected_hashes(spec)
    receipt = {
        'status': 'started', 'mode': mode, 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'], 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'scriptSha256': sha256_of(globals().get('__file__') or (ROOT / 'Scripts' / 'release_context_materials.py')),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'categoriesRequested': list(categories), 'offlineCheck': offline,
        'graphs': graph_descriptions(spec), 'provenance': {}, 'textures': {}, 'materials': {}, 'assignments': {}, 'skipped': {},
        'errors': [], 'mapSaved': False, 'limitations': list(spec['limitations']),
    }
    engine = Engine(ue, spec, receipt, receipt_path)
    engine.write()
    saved_anything = False
    try:
        engine.common_guards()
        namespace_exists = engine.namespace_exists()
        receipt['namespaceExistedBefore'] = namespace_exists

        if mode == 'revert':
            source = Path(revert_receipt) if revert_receipt else _latest_apply_receipt(spec)
            prior = json.loads(source.read_text(encoding='utf-8-sig'))
            receipt['revertSource'] = str(source)
            if not prior.get('assignments'):
                raise RuntimeError('Apply receipt has no assignments: ' + str(source))
            context_paths = {material_asset_path(spec, k) for k in spec['materials']}
            touched = [row['asset'] for category in categories for row in prior['assignments'].get(category, []) if row.get('action') == 'assigned_saved']
            checkpoint, copied = _checkpoint(spec, stamp, map_file, touched)
            receipt['checkpoint'] = str(checkpoint)
            receipt['checkpointAssetCopies'] = copied
            world = engine.load_target()
            receipt['actorCountBefore'] = len(engine.actors.get_all_level_actors())
            for category in categories:
                rows = [row for row in prior['assignments'].get(category, []) if row.get('action') == 'assigned_saved']
                receipt['assignments'][category] = engine.revert_rows(rows, context_paths)
                saved_anything = saved_anything or any(r['action'] == 'reverted_saved' for r in receipt['assignments'][category])
                engine.write()
            expected = {c: spec['categories'][c]['expectedOriginalMaterial'] for c in categories}
        else:
            if mode == 'import' and namespace_exists:
                raise RuntimeError('Existing native namespace preserved; refusing import into ' + spec['namespace'])
            if not namespace_exists:
                textures = engine.import_all_textures()
                materials = engine.build_all_materials(textures)
                saved_anything = True
            else:
                engine.load_textures()
                materials = engine.load_materials()
                receipt['materialsReused'] = {k: _asset_path(v) for k, v in materials.items()}
            engine.write()
            if mode == 'import':
                receipt['status'] = 'textures_and_materials_saved_no_assignment_no_map_change'
                return receipt

            # apply: dry-run verification first (every mesh must carry its expected original), then checkpoint, then mutate
            planned = {}
            for category in categories:
                material = materials[spec['categories'][category]['material']]
                rows, skipped = engine.assign_category(category, material, dry_run=True)
                planned[category] = rows
                receipt['skipped'][category] = skipped
            touched = [row['asset'] for rows in planned.values() for row in rows if row['action'] == 'planned']
            receipt['plannedAssignmentCount'] = len(touched)
            receipt['alreadyContextMaterialCount'] = sum(1 for rows in planned.values() for row in rows if row['action'] == 'already_context_material')
            checkpoint, copied = _checkpoint(spec, stamp, map_file, touched)
            receipt['checkpoint'] = str(checkpoint)
            receipt['checkpointAssetCopies'] = copied
            engine.write()
            world = engine.load_target()
            receipt['actorCountBefore'] = len(engine.actors.get_all_level_actors())
            if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
                raise RuntimeError('Map dirty right after load; resolve before assignment')
            for category in categories:
                material = materials[spec['categories'][category]['material']]
                rows, _ = engine.assign_category(category, material, dry_run=False)
                receipt['assignments'][category] = rows
                saved_anything = True
                engine.write()
            expected = {c: material_asset_path(spec, spec['categories'][c]['material']) for c in categories}

        # map: save only if the engine reports it dirty (asset-level assignment normally leaves it clean)
        dirty_maps = [str(p.get_name()) for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        receipt['dirtyMapPackagesAfterAssignment'] = dirty_maps
        if dirty_maps:
            if not engine.levels.save_current_level():
                raise RuntimeError('save_current_level returned False')
            receipt['mapSaved'] = True
            receipt['mapSha256AfterSave'] = sha256_of(map_file)
        dirty_content = [str(p.get_name()) for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
        receipt['dirtyContentPackagesAfterSave'] = dirty_content[:50]
        engine.write()

        # reopen + readback
        engine.load_target()
        readback = engine.component_readback(expected, samples)
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = readback['actorCount']
        mismatched = {c: v['mismatchedCount'] for c, v in readback['perCategory'].items() if v['mismatchedCount']}
        if mismatched:
            raise RuntimeError('Components still carry another material after reopen: %s' % mismatched)
        counts = {c: len([r for r in receipt['assignments'][c] if r['action'] in ('assigned_saved', 'reverted_saved')]) for c in categories}
        receipt['savedMeshCounts'] = counts
        receipt['status'] = ('context_materials_applied_saved_reopened_visual_acceptance_pending' if mode == 'apply'
                             else 'context_materials_reverted_saved_reopened')
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved_anything:
            receipt['status'] = 'failed_after_saves_checkpoint_available' if receipt.get('checkpoint') else 'failed_after_namespace_saves_map_unchanged'
        else:
            receipt['status'] = 'failed_before_any_save_nothing_changed'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v for m, v in protected.items())
        receipt['assignedMeshCount'] = sum(len([r for r in rows if r.get('action') in ('assigned_saved', 'reverted_saved')]) for rows in receipt['assignments'].values())
        engine.write()


def _latest_apply_receipt(spec):
    folder = ROOT / spec['receiptFolder']
    rows = []
    for path in sorted(folder.glob('native-apply-*.json')):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if data.get('assignments') and str(data.get('status', '')).startswith('context_materials_applied'):
            rows.append(path)
    if not rows:
        raise RuntimeError('No successful native-apply receipt in ' + str(folder))
    return rows[-1]


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_context_materials.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    tokens = command_line.split()
    lowered = [t.lower() for t in tokens]
    modes = [m for flag, m in (('-contextimportonly', 'import'), ('-contextapply', 'apply')) if flag in lowered]
    revert_receipt = None
    categories = CATEGORY_ORDER
    samples = None
    for token in tokens:
        low = token.lower()
        if low == '-contextrevert' or low.startswith('-contextrevert='):
            modes.append('revert')
            if '=' in token:
                revert_receipt = token.split('=', 1)[1].strip('"')
        elif low.startswith('-contextcategories='):
            categories = normalise_categories(token.split('=', 1)[1].strip('"'))
        elif low.startswith('-contextsamples='):
            samples = int(token.split('=', 1)[1])
    if len(modes) != 1:
        raise RuntimeError('Pass exactly one of -ContextImportOnly, -ContextApply, -ContextRevert (got %s)' % modes)
    try:
        receipt = run(modes[0], categories=categories, samples=samples, revert_receipt=revert_receipt)
        ue.log('release_context_materials: %s assigned %s map_changed %s' % (receipt['status'], receipt.get('assignedMeshCount'), receipt.get('mapBytesChanged')))
    except Exception as error:
        ue.log_error('release_context_materials failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


def _offline_main():
    parser = argparse.ArgumentParser(description='Offline fetch / consistency check for the Jerusalem context materials')
    parser.add_argument('--fetch', action='store_true', help='download the CC0 sets listed in the spec (curl)')
    parser.add_argument('--only', help='comma-separated set slugs for --fetch')
    parser.add_argument('--force', action='store_true', help='re-download even if md5 already matches')
    parser.add_argument('--check', action='store_true', help='offline consistency check (default when no flag)')
    args = parser.parse_args()
    spec = load_spec()
    if args.fetch:
        only = set(args.only.split(',')) if args.only else None
        print(json.dumps(fetch_sets(spec, only=only, force=args.force), indent=2))
    else:
        print(json.dumps(offline_check(spec, require_textures=True), indent=2))


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        _offline_main()
elif _invoked_as_native_script():
    _main()
