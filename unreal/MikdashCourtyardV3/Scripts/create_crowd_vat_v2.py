"""Crowd VAT V1: bake WalkV2 + idle into vertex animation textures for AMikdashCrowdField.

WHY. Frames from the cp11 packaged build showed the instanced crowd is a field of frozen
statues: SM_CrowdFigure_P0..P5 are six rigid posed static meshes, so no limb can move, and a
cluster of seven was pixel-identical 37 s apart. Scripts/create_crowd_vat.py recorded in 2026-09
that a VAT bake was impossible because AnimToTexture "is not installed". That is stale: Epic's
AnimToTexture ships in UE 5.8 under Engine/Plugins/Experimental/AnimToTexture with prebuilt
Windows editor binaries, and UAnimToTextureBPLibrary::AnimationToTexture is BlueprintCallable, so
Python reaches it as unreal.AnimToTextureBPLibrary.animation_to_texture(data_asset).

WHAT IT DOES (new assets only, under spec.namespace; no map, no existing asset is written):
  per variant (six PilgrimRigV3 visitor bodies, the Kohen body is deliberately excluded):
    1. ConvertSkeletalMeshToStaticMesh (the plugin's own converter, LOD0) -> SM_CrowdVAT_<v>
    2. GeometryScript simplify to spec.mesh.targetTriangles (13-20k -> ~2.4k). AnimToTexture maps
       every static-mesh vertex onto the N closest skeletal (driver) triangles, so the static mesh
       does not need the skeletal topology; this is the plugin's documented use.
    3. Lightmap UV generation OFF (UV1/UV2 carry the VAT lookup; the HISM is movable, unlit-mapped).
    4. Two Vertex-mode 16-bit bakes on transient data assets (never saved: the data-asset class
       lives in the plugin's runtime module, which the packaged game does not load):
         walk: WalkV2 A_Pilgrim_Original_Walk, frames 0..71 at 60 Hz -> UV channel 1
         idle: A_Pilgrim_Original_Idle,        frames 0..95 at 30 Hz -> UV channel 2
       SampleRate MUST equal the clip's own key rate: the bake samples AnimNumFrames keys at
       1/SampleRate spacing, so a 60 fps clip baked at 30 Hz would read 2.4 s of a 1.2 s clip.
    5. Textures forced to nearest filtering, no mips, sRGB off, never-stream.
  once:
    6. M_CrowdVAT_V1: WPO = LocalToWorld(VAT delta) + velocity * clamp(t - T0); normal from the
       normal VAT through a vertex interpolator; base colour per slot with a per-figure garment
       palette and complexion variation, also through an interpolator (the route the tint fix
       proved on this HISM). Every per-figure quantity is per-instance custom data written by
       AMikdashCrowdField (spec.customData.layout). used_with_instanced_static_meshes is set and
       read back: without it the HISM draws the default material (the cardboard-vegetation bug).
    7. MI_CrowdVAT_<v>_<slot> per material slot, parameters from the bake readback, assigned to the
       mesh slots and read back.

NO SLIDING, BY CONSTRUCTION. The walk phase in the material advances at `rate` cycles/s and the
figure translates at `velocity`; AMikdashCrowdField writes rate = |velocity| / (143.94 cm * scale)
from the same number, 119.95 cm/s = the WalkV2 clip's measured ground speed at play rate 1
(MeasuredWalkClipGroundSpeedCm in MikdashResidentCharacter.h). Both are integrated from the same
anchor time T0 with the same clamp, so stride and ground travel cannot drift apart between CPU
updates. A figure that cannot move is switched to the idle clip; it never walks in place.

Launch (hidden editor, NOT the commandlet: the bake spawns a temp SkeletalMeshComponent in
GEditor's editor world):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject" /Engine/Maps/Entry
      -ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/create_crowd_vat_v2.py"
      -unattended -nosplash -nullrhi -EnablePlugins=AnimToTexture,GeometryScripting
      -CrowdVatBake -abslog="C:/Mikdash/Working-5.8/Fable-CrowdVat-Bake-01.log"
  -CrowdVatVerify instead of -CrowdVatBake: fresh-process readback of the saved assets.
  -CrowdVatNamespace=/Game/... builds to another namespace (the default refuses if it exists).

Offline:  python Scripts/create_crowd_vat_v2.py --offline-check
"""
import hashlib
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts' / 'create_crowd_vat_v2.spec.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp_now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def utc():
    return datetime.now(timezone.utc).isoformat()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']).resolve() != ROOT.resolve():
        raise RuntimeError('Spec project directory differs from the script root')
    return spec


def disk_uasset(object_path):
    return ROOT / 'Content' / (object_path.split('.')[0][len('/Game/'):] + '.uasset')


def disk_umap(package):
    return ROOT / 'Content' / (package[len('/Game/'):] + '.umap')


MAPS = {
    'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}


# =============================================================================================
# Offline
# =============================================================================================
def offline_check(spec=None):
    spec = spec or load_spec()
    problems = []
    walk, idle = spec['walk'], spec['idle']
    if walk['loopFrames'] != walk['expectedKeys'] - 1:
        problems.append('walk loopFrames must be expectedKeys - 1 (the last key repeats the first)')
    if idle['loopFrames'] != idle['expectedKeys'] - 1:
        problems.append('idle loopFrames must be expectedKeys - 1')
    if abs((walk['expectedKeys'] - 1) / walk['expectedLengthSec'] - walk['sampleRateHz']) > 1e-6:
        problems.append('walk sample rate is not the clip key rate')
    if abs((idle['expectedKeys'] - 1) / idle['expectedLengthSec'] - idle['sampleRateHz']) > 1e-6:
        problems.append('idle sample rate is not the clip key rate')
    if abs(walk['cycleDistanceCm'] - 2.0 * walk['stepCm']) > 0.01:
        problems.append('cycle distance is not two steps')
    if abs(walk['groundSpeedCmPerSecAtRate1'] * walk['expectedLengthSec'] - walk['cycleDistanceCm']) > 0.05:
        problems.append('ground speed x cycle time != cycle distance')
    if walk['uvChannel'] == idle['uvChannel'] or min(walk['uvChannel'], idle['uvChannel']) < 1:
        problems.append('walk and idle need distinct UV channels >= 1')
    if spec['customData']['count'] != len(spec['customData']['layout']):
        problems.append('customData count differs from the layout')
    if len(spec['material']['palette']) < 2:
        problems.append('palette needs at least two entries')
    shorts = [v['short'] for v in spec['variants']]
    if len(set(shorts)) != len(shorts) or len(shorts) > 6:
        problems.append('variants must be unique and at most MaxPoseComponents (6)')
    for v in spec['variants']:
        glb = ROOT / v['glb']
        if not glb.is_file():
            problems.append('missing GLB ' + v['glb'])
        for key in ('skeletalMesh', 'walk', 'idle'):
            if not disk_uasset(v[key]).is_file():
                problems.append('%s %s missing on disk: %s' % (v['id'], key, v[key]))
        if '/WalkV2/' not in v['walk']:
            problems.append('%s walk is not the WalkV2 clip' % v['id'])
        if 'Skin' not in v['slots'] or 'Linen' not in v['slots']:
            problems.append('%s slots lack Skin/Linen' % v['id'])
    return problems


# =============================================================================================
# Engine helpers
# =============================================================================================
def _switch(ue, name):
    return bool(ue.SystemLibrary.parse_param(ue.SystemLibrary.get_command_line(), name))


def _value(ue, name):
    m = re.search(r'-' + name + r'=(\S+)', ue.SystemLibrary.get_command_line())
    return m.group(1).strip('"') if m else None


def _doc_props(type_object):
    names = set()
    for line in (getattr(type_object, '__doc__', '') or '').splitlines():
        line = line.strip()
        if line.startswith('- ``'):
            end = line.find('``', 4)
            if end > 4:
                names.add(line[4:end])
    return names


def _prop(obj, *candidates):
    """First candidate property name the object actually exposes (5.8 name mangling is not
    guessable: bRail -> rail, VertexMinBBox -> ?). Raises with the real list."""
    names = _doc_props(type(obj))
    norm = {n.replace('_', '').lower(): n for n in names}
    for c in candidates:
        key = c.replace('_', '').lower()
        if key in norm:
            return norm[key]
    raise RuntimeError('%s exposes none of %r; it has %r' % (type(obj).__name__, candidates, sorted(names)))


def _set(obj, name, value, cmp=None):
    obj.set_editor_property(name, value)
    got = obj.get_editor_property(name)
    ok = cmp(got, value) if cmp else got == value
    if not ok:
        raise RuntimeError('Readback mismatch on %s.%s: wrote %r read %r' % (type(obj).__name__, name, value, got))
    return got


def _path(obj):
    return obj.get_path_name() if obj else None


def _v3(v):
    return [round(float(v.x), 6), round(float(v.y), 6), round(float(v.z), 6)]


def _outcome_ok(ue, result):
    pins = getattr(ue, 'GeometryScriptOutcomePins', None)
    if pins is None:
        return True
    if isinstance(result, (list, tuple)):
        return pins.SUCCESS in result or any(r == pins.SUCCESS for r in result)
    return result == pins.SUCCESS


def _api_dump(ue):
    out = {}
    for name in ('AnimToTextureBPLibrary', 'AnimToTextureDataAsset', 'AnimToTextureAnimSequenceInfo',
                 'AnimToTextureMode', 'AnimToTexturePrecision', 'GeometryScript_MeshSimplification',
                 'GeometryScriptSimplifyMeshOptions', 'GeometryScript_AssetUtils',
                 'GeometryScriptCopyMeshToAssetOptions', 'GeometryScriptCopyMeshFromAssetOptions',
                 'Texture2DFactoryNew', 'MaterialExpressionVertexInterpolator', 'MaterialExpressionTransform',
                 'StaticMeshEditorSubsystem', 'AnimationLibrary'):
        t = getattr(ue, name, None)
        out[name] = dict(present=t is not None,
                         props=sorted(_doc_props(t)) if t is not None else [],
                         members=sorted(n for n in dir(t) if not n.startswith('_'))[:120] if t is not None else [])
    return out


def _guards(ue):
    if Path(ue.Paths.project_dir()).resolve() != ROOT.resolve():
        raise RuntimeError('Wrong project directory')
    if ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Live PIE world; refuse')
    dirty = list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + \
        list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty:
        raise RuntimeError('Dirty packages present before the run: %r' % [p.get_name() for p in dirty][:10])


def protected_hashes(spec):
    out = {}
    for v in spec['variants']:
        for key in ('skeletalMesh', 'walk', 'idle'):
            f = disk_uasset(v[key])
            out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
        skel = disk_uasset(v['skeletalMesh']).parent / (v['id'] + '_Skeleton.uasset')
        if skel.is_file():
            out[str(skel.relative_to(ROOT)).replace('\\', '/')] = sha(skel)
    for key, package in MAPS.items():
        f = disk_umap(package)
        out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    for f in sorted((ROOT / 'Content/MikdashV3/Runtime/CrowdFieldV1').rglob('*.uasset')):
        out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    return out


# =============================================================================================
# Bake
# =============================================================================================
def _first_object(result, cls):
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, cls):
                return item
        return None
    return result if isinstance(result, cls) else None


def _convert(ue, skel, package, target, row):
    """Skeletal LOD0 -> DynamicMesh -> simplify -> new StaticMesh asset, all GeometryScript.

    MEASURED 2026-09-11 (crowd-vat-bake-20260911T042112123114Z.json): the plugin's own
    ConvertSkeletalMeshToStaticMesh returns None under -nullrhi with nothing in the log --
    MeshUtilities::ConvertMeshesToStaticMesh gathers geometry from the component's render
    MeshObject, which a NullRHI editor never creates. GeometryScript reads the asset's source
    model instead. Same reference pose, same component space as the driver mesh the bake skins,
    which is all the plugin's closest-triangle mapping needs.
    """
    utils = ue.GeometryScript_AssetUtils
    dynamic = ue.DynamicMesh()
    read = ue.GeometryScriptCopyMeshFromAssetOptions()
    for key, value in (('apply_build_settings', False), ('request_tangents', False), ('use_build_scale', True)):
        try:
            read.set_editor_property(key, value)
        except Exception:                                           # noqa: BLE001
            pass
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    result = utils.copy_mesh_from_skeletal_mesh(skel, dynamic, read, lod)
    if not _outcome_ok(ue, result):
        raise RuntimeError('copy_mesh_from_skeletal_mesh failed: %r' % (result,))
    before = int(dynamic.get_triangle_count())
    box = ue.GeometryScript_MeshQueries.get_mesh_bounding_box(dynamic)
    row['sourceDynamic'] = dict(triangles=before, boundsMin=_v3(box.min), boundsMax=_v3(box.max))
    if before < 1000 or (float(box.max.z) - float(box.min.z)) < 100.0:
        raise RuntimeError('Skeletal copy looks wrong: %d triangles, height %.1f cm' % (before, float(box.max.z) - float(box.min.z)))
    options = ue.GeometryScriptSimplifyMeshOptions()
    applied = {}
    for key, value in (('auto_compact', True), ('allow_seam_collapse', True)):
        try:
            options.set_editor_property(key, value)
            applied[key] = value
        except Exception:                                           # noqa: BLE001
            pass
    ue.GeometryScript_MeshSimplification.apply_simplify_to_triangle_count(dynamic, int(target), options)
    after = int(dynamic.get_triangle_count())
    if after <= 0 or after > before:
        raise RuntimeError('Simplification produced %d triangles from %d' % (after, before))
    row['decimation'] = dict(dynamicTrianglesBefore=before, dynamicTrianglesAfter=after, target=int(target),
                             simplifyOptionsApplied=applied)
    create = ue.GeometryScriptCreateNewStaticMeshAssetOptions()
    for key, value in (('enable_nanite', False), ('enable_collision', False), ('enable_recompute_normals', False),
                       ('enable_recompute_tangents', False)):
        try:
            create.set_editor_property(key, value)
        except Exception:                                           # noqa: BLE001
            pass
    made = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic, package, create)
    mesh = _first_object(made, ue.StaticMesh)
    if not mesh or not _outcome_ok(ue, made):
        raise RuntimeError('create_new_static_mesh_asset_from_mesh failed: %r' % (made,))
    # Material slots: the dynamic mesh's MaterialIDs index the skeletal mesh's material list.
    skel_materials = list(skel.get_editor_property('materials'))
    current = list(mesh.get_editor_property('static_materials'))
    if len(current) > len(skel_materials):
        raise RuntimeError('Static mesh has %d slots, skeletal mesh only %d' % (len(current), len(skel_materials)))
    slots = []
    for index in range(max(len(current), 1) if current else len(skel_materials)):
        src = skel_materials[index]
        slot = ue.StaticMaterial()
        slot.set_editor_property('material_interface', src.get_editor_property('material_interface'))
        slot.set_editor_property('material_slot_name', src.get_editor_property('material_slot_name'))
        slots.append(slot)
    mesh.set_editor_property('static_materials', slots)
    row['skeletalSlots'] = [str(m.get_editor_property('material_slot_name')) for m in skel_materials]
    row['convertRoute'] = 'GeometryScript copy_mesh_from_skeletal_mesh + create_new_static_mesh_asset_from_mesh'
    return mesh


def _mesh_stats(ue, mesh):
    stats = dict(lods=int(mesh.get_num_lods()), triangles=int(mesh.get_num_triangles(0)),
                 vertices=int(mesh.get_num_vertices(0)), sections=int(mesh.get_num_sections(0)))
    box = mesh.get_bounding_box()
    stats['boundsMin'] = _v3(box.min)
    stats['boundsMax'] = _v3(box.max)
    stats['slots'] = [str(m.get_editor_property('material_slot_name')) for m in mesh.get_editor_property('static_materials')]
    subsystem = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) if hasattr(ue, 'StaticMeshEditorSubsystem') else None
    if subsystem:
        try:
            stats['uvChannels'] = int(subsystem.get_num_uv_channels(mesh, 0))
        except Exception as exc:                                    # noqa: BLE001
            stats['uvChannelsError'] = str(exc)
    return stats


def _decimate(ue, mesh, target, row):
    utils = ue.GeometryScript_AssetUtils
    dynamic = ue.DynamicMesh()
    read = ue.GeometryScriptCopyMeshFromAssetOptions()
    for key, value in (('apply_build_settings', False), ('request_tangents', False), ('use_build_scale', False)):
        try:
            read.set_editor_property(key, value)
        except Exception:                                           # noqa: BLE001
            pass
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    reader = getattr(utils, 'copy_mesh_from_static_mesh_v2', None) or utils.copy_mesh_from_static_mesh
    result = reader(mesh, dynamic, read, lod)
    if not _outcome_ok(ue, result):
        raise RuntimeError('copy_mesh_from_static_mesh failed: %r' % (result,))
    before = int(dynamic.get_triangle_count())
    options = ue.GeometryScriptSimplifyMeshOptions()
    applied = {}
    for key, value in (('auto_compact', True), ('allow_seam_collapse', True)):
        try:
            options.set_editor_property(key, value)
            applied[key] = value
        except Exception:                                           # noqa: BLE001
            pass
    ue.GeometryScript_MeshSimplification.apply_simplify_to_triangle_count(dynamic, int(target), options)
    after = int(dynamic.get_triangle_count())
    if after <= 0 or after > before:
        raise RuntimeError('Simplification produced %d triangles from %d' % (after, before))
    write = ue.GeometryScriptCopyMeshToAssetOptions()
    for key, value in (('enable_recompute_normals', False), ('enable_recompute_tangents', False),
                       ('replace_materials', False), ('emit_transaction', False)):
        try:
            write.set_editor_property(key, value)
        except Exception:                                           # noqa: BLE001
            pass
    wlod = ue.GeometryScriptMeshWriteLOD()
    wlod.set_editor_property('write_hi_res_source', False)
    wlod.set_editor_property('lod_index', 0)
    result = utils.copy_mesh_to_static_mesh(dynamic, mesh, write, wlod)
    if not _outcome_ok(ue, result):
        raise RuntimeError('copy_mesh_to_static_mesh failed: %r' % (result,))
    row['decimation'] = dict(dynamicTrianglesBefore=before, dynamicTrianglesAfter=after, target=int(target),
                             simplifyOptionsApplied=applied)


def _texture(ue, tools, assets, folder, name):
    path = folder + '/' + name
    if assets.does_asset_exist(path):
        raise RuntimeError('Texture already exists (build to new names): ' + path)
    tex = tools.create_asset(name, folder, ue.Texture2D, ue.Texture2DFactoryNew())
    if not tex:
        raise RuntimeError('Texture2DFactoryNew failed for ' + path)
    return tex


def _bake_clip(ue, spec, mesh, skel, clip, clip_spec, pos, nrm, row_key, row):
    att = ue.AnimToTextureBPLibrary
    da = ue.new_object(ue.AnimToTextureDataAsset)
    names = {}
    for logical, candidates in (('skeletal_mesh', ('skeletal_mesh',)), ('static_mesh', ('static_mesh',)),
                                ('skeletal_lod', ('skeletal_lod_index',)), ('static_lod', ('static_lod_index',)),
                                ('uv', ('uv_channel',)), ('drivers', ('num_driver_triangles',)), ('sigma', ('sigma',)),
                                ('max_h', ('max_height',)), ('max_w', ('max_width',)), ('pow2', ('enforce_power_of_two',)),
                                ('precision', ('precision',)), ('mode', ('mode',)),
                                ('vpos', ('vertex_position_texture',)), ('vnrm', ('vertex_normal_texture',)),
                                ('rate', ('sample_rate',)), ('anims', ('anim_sequences',)),
                                ('frames', ('num_frames',)), ('rows', ('vertex_rows_per_frame',)),
                                ('min', ('vertex_min_b_box', 'vertex_min_bbox', 'min_b_box')),
                                ('size', ('vertex_size_b_box', 'vertex_size_bbox', 'size_b_box')),
                                ('animations', ('animations',))):
        names[logical] = _prop(da, *candidates)
    da.set_editor_property(names['skeletal_mesh'], skel)
    da.set_editor_property(names['static_mesh'], mesh)
    _set(da, names['skeletal_lod'], 0)
    _set(da, names['static_lod'], 0)
    _set(da, names['uv'], int(clip_spec['uvChannel']))
    _set(da, names['drivers'], int(spec['mesh']['numDriverTriangles']))
    _set(da, names['sigma'], float(spec['mesh']['sigma']), lambda a, b: abs(a - b) < 1e-6)
    _set(da, names['max_h'], 4096)
    _set(da, names['max_w'], int(spec['mesh']['maxTextureWidth']))
    _set(da, names['pow2'], False)
    _set(da, names['precision'], ue.AnimToTexturePrecision.SIXTEEN_BITS)
    _set(da, names['mode'], ue.AnimToTextureMode.VERTEX)
    da.set_editor_property(names['vpos'], pos)
    da.set_editor_property(names['vnrm'], nrm)
    _set(da, names['rate'], float(clip_spec['sampleRateHz']), lambda a, b: abs(a - b) < 1e-4)
    info = ue.AnimToTextureAnimSequenceInfo()
    info.set_editor_property(_prop(info, 'enabled', 'b_enabled'), True)
    info.set_editor_property(_prop(info, 'anim_sequence'), clip)
    info.set_editor_property(_prop(info, 'use_custom_range', 'b_use_custom_range'), True)
    info.set_editor_property(_prop(info, 'start_frame'), 0)
    info.set_editor_property(_prop(info, 'end_frame'), int(clip_spec['loopFrames']) - 1)
    da.set_editor_property(names['anims'], [info])
    if not att.animation_to_texture(da):
        raise RuntimeError('animation_to_texture returned False for %s (see LogAnimToTextureEditor)' % clip.get_name())
    frames = int(da.get_editor_property(names['frames']))
    rows = int(da.get_editor_property(names['rows']))
    vmin = _v3(da.get_editor_property(names['min']))
    vsize = _v3(da.get_editor_property(names['size']))
    if frames != int(clip_spec['loopFrames']):
        raise RuntimeError('%s baked %d frames, expected %d' % (clip.get_name(), frames, clip_spec['loopFrames']))
    if min(vsize) <= 0.0:
        raise RuntimeError('%s delta bounding box is degenerate: %r' % (clip.get_name(), vsize))
    width, height = int(pos.blueprint_get_size_x()), int(pos.blueprint_get_size_y())
    if height != frames * rows:
        raise RuntimeError('%s position texture height %d != frames %d x rows %d' % (clip.get_name(), height, frames, rows))
    row[row_key] = dict(clip=_path(clip), frames=frames, rowsPerFrame=rows, minBBox=vmin, sizeBBox=vsize,
                        width=width, height=height, uvChannel=int(clip_spec['uvChannel']),
                        sampleRateHz=float(clip_spec['sampleRateHz']), dataAssetProps=names)
    if rows != 1:
        raise RuntimeError('%s needs %d rows per frame; the material assumes 1 (mesh too dense for a 4096 row)' %
                           (clip.get_name(), rows))
    return row[row_key]


def _finish_texture(ue, tex, record):
    changes = {}
    for key, value in (('srgb', False), ('filter', ue.TextureFilter.TF_NEAREST),
                       ('mip_gen_settings', ue.TextureMipGenSettings.TMGS_NO_MIPMAPS), ('never_stream', True)):
        tex.set_editor_property(key, value)
        got = tex.get_editor_property(key)
        if got != value:
            raise RuntimeError('Texture %s %s did not take %r (read %r)' % (tex.get_name(), key, value, got))
        changes[key] = str(got)
    changes['compression'] = str(tex.get_editor_property('compression_settings'))
    record[tex.get_name()] = changes


# ------------------------------------------------------------------------------ material
CODE_DELTA = """
float dt = clamp(T - T0, -NegDt, Horizon);
float wph = frac(Phase0 + dt * Rate);
float irate = 0.92 + 0.16 * frac(IdleOff * 7.31);
float iph = frac(IdleOff + T * irate / max(IdleSeconds, 0.01));
float w = saturate((T - TSwitch) / max(Blend, 0.001));
float idleW = (IdleTarget > 0.5) ? w : (1.0 - w);
float3 r = float3(0.0, 0.0, 0.0);
if (idleW < 0.999)
{
    float fr = wph * WalkFrames; float f0 = floor(fr); float a = fr - f0;
    float f1 = (f0 + 1.0 >= WalkFrames) ? 0.0 : f0 + 1.0;
    float3 p0 = WalkTex.SampleLevel(WalkTexSampler, float2(UVW.x, UVW.y + f0 / WalkFrames), 0).rgb;
    float3 p1 = WalkTex.SampleLevel(WalkTexSampler, float2(UVW.x, UVW.y + f1 / WalkFrames), 0).rgb;
    r += (1.0 - idleW) * DECODE_WALK;
}
if (idleW > 0.001)
{
    float fr = iph * IdleFrames; float f0 = floor(fr); float a = fr - f0;
    float f1 = (f0 + 1.0 >= IdleFrames) ? 0.0 : f0 + 1.0;
    float3 p0 = IdleTex.SampleLevel(IdleTexSampler, float2(UVI.x, UVI.y + f0 / IdleFrames), 0).rgb;
    float3 p1 = IdleTex.SampleLevel(IdleTexSampler, float2(UVI.x, UVI.y + f1 / IdleFrames), 0).rgb;
    r += idleW * DECODE_IDLE;
}
return RESULT;
"""

CODE_DRIFT = """
float dt = clamp(T - T0, -NegDt, Horizon);
return float3(VX, VY, VZ) * dt;
"""


def _colour_code(palette):
    entries = ', '.join('float3(%.4f, %.4f, %.4f)' % tuple(c) for c in palette)
    last = len(palette) - 1
    return ("""
float3 pal[%d] = { %s };
int i = (int)round(saturate(Tint) * %d.0);
float3 g = pal[i];
float b = 0.90 + 0.20 * frac(IdleOff * 13.7);
float3 c = lerp(Base.rgb, g, PaletteMix) * b;
float s = 0.72 + 0.50 * frac(IdleOff * 5.3);
return lerp(c, Base.rgb * s, SkinVariation);
""" % (len(palette), entries, last))


class Graph:
    def __init__(self, ue, material, receipt):
        self.ue, self.m, self.ml = ue, material, ue.MaterialEditingLibrary
        self.pins = receipt.setdefault('resolvedPins', [])

    def make(self, cls, x=0, y=0, **props):
        node = self.ml.create_material_expression(self.m, cls, x, y)
        if not node:
            raise RuntimeError('create_material_expression failed for ' + cls.__name__)
        for key, value in props.items():
            node.set_editor_property(key, value)
        return node

    def wire(self, src, dst, wanted, out=''):
        live = [str(n) for n in self.ml.get_material_expression_input_names(dst)]
        target = None
        for name in live:
            if name.lower() == wanted.lower():
                target = name
        if target is None and len(live) == 1:
            target = live[0]
        if target is None:
            raise RuntimeError('%s has no input %r (live %r)' % (dst.get_class().get_name(), wanted, live))
        if not self.ml.connect_material_expressions(src, out, dst, target):
            raise RuntimeError('connect %s -> %s.%s failed' % (src.get_class().get_name(), dst.get_class().get_name(), target))
        self.pins.append([dst.get_class().get_name(), wanted, target])

    def prop(self, src, prop):
        if not self.ml.connect_material_property(src, '', prop):
            raise RuntimeError('connect_material_property failed for %s' % prop)

    def custom(self, code, inputs, x, y, desc):
        ue = self.ue
        node = self.make(ue.MaterialExpressionCustom, x, y)
        node.set_editor_property('code', code)
        node.set_editor_property('output_type', ue.CustomMaterialOutputType.CMOT_FLOAT3)
        node.set_editor_property('description', desc)
        pins = []
        for name in inputs:
            pin = ue.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        node.set_editor_property('inputs', pins)
        got = [str(p.get_editor_property('input_name')) for p in node.get_editor_property('inputs')]
        if got != list(inputs):
            raise RuntimeError('Custom inputs did not take: %r' % got)
        return node

    def scalar(self, name, value, x, y):
        return self.make(self.ue.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(value))

    def vector(self, name, rgb, x, y):
        node = self.make(self.ue.MaterialExpressionVectorParameter, x, y, parameter_name=name)
        node.set_editor_property('default_value', self.ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
        return node

    def custom_data(self, index, default, x, y):
        node = self.make(self.ue.MaterialExpressionPerInstanceCustomData, x, y)
        _set(node, 'data_index', int(index))
        _set(node, 'const_default_value', float(default), lambda a, b: abs(a - b) < 1e-6)
        return node

    def texture_param(self, name, texture, x, y):
        ue = self.ue
        node = self.make(ue.MaterialExpressionTextureObjectParameter, x, y, parameter_name=name)
        node.set_editor_property('texture', texture)
        node.set_editor_property('sampler_type', ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        return node


def build_master(ue, spec, ns, defaults, receipt):
    tools = ue.AssetToolsHelpers.get_asset_tools()
    assets = ue.EditorAssetLibrary
    name = spec['material']['master']
    folder = ns + '/Materials'
    if assets.does_asset_exist(folder + '/' + name):
        raise RuntimeError('Master material already exists (build to a new namespace): ' + name)
    material = tools.create_asset(name, folder, ue.Material, ue.MaterialFactoryNew())
    g = Graph(ue, material, receipt)
    mp = ue.MaterialProperty
    time = g.make(ue.MaterialExpressionTime, -2400, 0)
    cd_defaults = {0: 0.0, 1: 0.5, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: -1000.0, 9: 0.5, 10: 0.0}
    cd = {i: g.custom_data(i, d, -2400, 150 + i * 90) for i, d in cd_defaults.items()}
    uvw = g.make(ue.MaterialExpressionTextureCoordinate, -2400, 1300, coordinate_index=int(spec['walk']['uvChannel']))
    uvi = g.make(ue.MaterialExpressionTextureCoordinate, -2400, 1400, coordinate_index=int(spec['idle']['uvChannel']))
    if int(uvw.get_editor_property('coordinate_index')) != spec['walk']['uvChannel']:
        raise RuntimeError('TextureCoordinate index did not take')
    tex = {k: g.texture_param(k, defaults[k], -2400, 1500 + i * 150)
           for i, k in enumerate(('WalkPositionTexture', 'WalkNormalTexture', 'IdlePositionTexture', 'IdleNormalTexture'))}
    walk_frames = g.scalar('WalkFrames', spec['walk']['loopFrames'], -2000, 1500)
    idle_frames = g.scalar('IdleFrames', spec['idle']['loopFrames'], -2000, 1580)
    idle_seconds = g.scalar('IdleSeconds', spec['idle']['loopFrames'] / spec['idle']['sampleRateHz'], -2000, 1660)
    blend = g.scalar('BlendSeconds', spec['material']['blendSeconds'], -2000, 1740)
    negdt = g.scalar('NegativeDtSeconds', spec['material']['negativeDtSeconds'], -2000, 1820)
    wmin = g.vector('WalkMinBBox', defaults['WalkMinBBox'], -2000, 1900)
    wsize = g.vector('WalkSizeBBox', defaults['WalkSizeBBox'], -2000, 1980)
    imin = g.vector('IdleMinBBox', defaults['IdleMinBBox'], -2000, 2060)
    isize = g.vector('IdleSizeBBox', defaults['IdleSizeBBox'], -2000, 2140)
    base = g.vector('BaseColor', [0.7, 0.65, 0.55], -2000, 2300)
    rough = g.scalar('Roughness', 0.85, -2000, 2380)
    spec_node = g.scalar('Specular', spec['material']['specular'], -2000, 2460)
    mix = g.scalar('PaletteMix', 0.0, -2000, 2540)
    skinvar = g.scalar('SkinVariation', 0.0, -2000, 2620)

    common = ['T', 'Phase0', 'IdleTarget', 'T0', 'Rate', 'TSwitch', 'IdleOff', 'Horizon', 'UVW', 'UVI',
              'WalkTex', 'IdleTex', 'WalkFrames', 'IdleFrames', 'IdleSeconds', 'Blend', 'NegDt']

    def feed(node, walk_tex, idle_tex, extra):
        g.wire(time, node, 'T')
        g.wire(cd[0], node, 'Phase0')
        g.wire(cd[2], node, 'IdleTarget')
        g.wire(cd[3], node, 'T0')
        g.wire(cd[4], node, 'Rate')
        g.wire(cd[8], node, 'TSwitch')
        g.wire(cd[9], node, 'IdleOff')
        g.wire(cd[10], node, 'Horizon')
        g.wire(uvw, node, 'UVW')
        g.wire(uvi, node, 'UVI')
        g.wire(walk_tex, node, 'WalkTex')
        g.wire(idle_tex, node, 'IdleTex')
        g.wire(walk_frames, node, 'WalkFrames')
        g.wire(idle_frames, node, 'IdleFrames')
        g.wire(idle_seconds, node, 'IdleSeconds')
        g.wire(blend, node, 'Blend')
        g.wire(negdt, node, 'NegDt')
        for src, pin in extra:
            g.wire(src, node, pin)

    delta_code = (CODE_DELTA.replace('DECODE_WALK', '(lerp(p0, p1, a) * WalkSize.xyz + WalkMin.xyz)')
                  .replace('DECODE_IDLE', '(lerp(p0, p1, a) * IdleSize.xyz + IdleMin.xyz)')
                  .replace('RESULT', 'r'))
    delta = g.custom(delta_code, common + ['WalkMin', 'WalkSize', 'IdleMin', 'IdleSize'], -1400, 0,
                     'VAT local position delta: walk/idle crossfade, per-instance phase anchor')
    feed(delta, tex['WalkPositionTexture'], tex['IdlePositionTexture'],
         [(wmin, 'WalkMin'), (wsize, 'WalkSize'), (imin, 'IdleMin'), (isize, 'IdleSize')])
    normal_code = (CODE_DELTA.replace('DECODE_WALK', '(lerp(p0, p1, a) * 2.0 - 1.0)')
                   .replace('DECODE_IDLE', '(lerp(p0, p1, a) * 2.0 - 1.0)')
                   .replace('RESULT', 'normalize(r + float3(0.0, 0.0, 1e-4))'))
    normal = g.custom(normal_code, common, -1400, 600, 'VAT local normal')
    feed(normal, tex['WalkNormalTexture'], tex['IdleNormalTexture'], [])

    def to_world(src, x, y):
        node = g.make(ue.MaterialExpressionTransform, x, y)
        node.set_editor_property('transform_source_type', ue.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
        node.set_editor_property('transform_type', ue.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        g.wire(src, node, 'Input')
        return node
    delta_ws = to_world(delta, -1000, 0)
    drift = g.custom(CODE_DRIFT, ['T', 'T0', 'Horizon', 'NegDt', 'VX', 'VY', 'VZ'], -1400, -400,
                     'extrapolated ground travel since the anchor; same clamp as the walk phase')
    for src, pin in ((time, 'T'), (cd[3], 'T0'), (cd[10], 'Horizon'), (negdt, 'NegDt'), (cd[5], 'VX'), (cd[6], 'VY'), (cd[7], 'VZ')):
        g.wire(src, drift, pin)
    wpo = g.make(ue.MaterialExpressionAdd, -700, 0)
    g.wire(delta_ws, wpo, 'A')
    g.wire(drift, wpo, 'B')
    g.prop(wpo, mp.MP_WORLD_POSITION_OFFSET)

    normal_ws = to_world(normal, -1000, 600)
    normal_interp = g.make(ue.MaterialExpressionVertexInterpolator, -700, 600)
    g.wire(normal_ws, normal_interp, 'VS')
    g.prop(normal_interp, mp.MP_NORMAL)

    colour = g.custom(_colour_code(spec['material']['palette']), ['Base', 'PaletteMix', 'SkinVariation', 'Tint', 'IdleOff'],
                      -1400, 1200, 'per-figure garment palette + complexion (vertex stage)')
    for src, pin in ((base, 'Base'), (mix, 'PaletteMix'), (skinvar, 'SkinVariation'), (cd[1], 'Tint'), (cd[9], 'IdleOff')):
        g.wire(src, colour, pin)
    colour_interp = g.make(ue.MaterialExpressionVertexInterpolator, -700, 1200)
    g.wire(colour, colour_interp, 'VS')
    g.prop(colour_interp, mp.MP_BASE_COLOR)
    g.prop(rough, mp.MP_ROUGHNESS)
    g.prop(spec_node, mp.MP_SPECULAR)
    metallic = g.make(ue.MaterialExpressionConstant, -700, 2000, r=0.0)
    g.prop(metallic, mp.MP_METALLIC)

    _set(material, 'tangent_space_normal', False)
    _set(material, 'used_with_instanced_static_meshes', True)
    ml = ue.MaterialEditingLibrary
    ml.recompile_material(material)
    if not assets.save_loaded_asset(material, False):
        raise RuntimeError('Master material save failed')
    receipt['master'] = dict(path=_path(material), expressions=len(ml.get_material_expressions(material))
                             if hasattr(ml, 'get_material_expressions') else None,
                             usedWithInstancedStaticMeshes=bool(material.get_editor_property('used_with_instanced_static_meshes')),
                             tangentSpaceNormal=bool(material.get_editor_property('tangent_space_normal')))
    return material


def _mi(ue, tools, assets, folder, name, parent, textures, vectors, scalars, record):
    ml = ue.MaterialEditingLibrary
    if assets.does_asset_exist(folder + '/' + name):
        raise RuntimeError('Material instance already exists: ' + name)
    mi = tools.create_asset(name, folder, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
    ml.set_material_instance_parent(mi, parent)
    if mi.get_editor_property('parent') != parent:
        raise RuntimeError('MI parent did not take: ' + name)
    got = {}
    for key, value in textures.items():
        ml.set_material_instance_texture_parameter_value(mi, key, value)
        read = ml.get_material_instance_texture_parameter_value(mi, key)
        if _path(read) != _path(value):
            raise RuntimeError('%s texture %s read %s' % (name, key, _path(read)))
        got[key] = _path(read)
    for key, rgb in vectors.items():
        ml.set_material_instance_vector_parameter_value(mi, key, ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
        read = ml.get_material_instance_vector_parameter_value(mi, key)
        if any(abs(float(a) - float(b)) > 1e-4 for a, b in zip((read.r, read.g, read.b), rgb)):
            raise RuntimeError('%s vector %s read %r' % (name, key, (read.r, read.g, read.b)))
        got[key] = [round(float(read.r), 6), round(float(read.g), 6), round(float(read.b), 6)]
    for key, value in scalars.items():
        ml.set_material_instance_scalar_parameter_value(mi, key, float(value))
        read = ml.get_material_instance_scalar_parameter_value(mi, key)
        if abs(float(read) - float(value)) > 1e-5:
            raise RuntimeError('%s scalar %s read %r' % (name, key, read))
        got[key] = round(float(read), 6)
    if not assets.save_loaded_asset(mi, False):
        raise RuntimeError('MI save failed: ' + name)
    record[name] = got
    return mi


def run_bake(ue, spec, receipt, write):
    ns = _value(ue, 'CrowdVatNamespace') or spec['namespace']
    receipt['namespace'] = ns
    assets = ue.EditorAssetLibrary
    tools = ue.AssetToolsHelpers.get_asset_tools()
    if assets.does_directory_exist(ns) and list(assets.list_assets(ns, True, False)):
        raise RuntimeError('Namespace %s already holds assets; build to new names with -CrowdVatNamespace=' % ns)
    receipt['protectedBefore'] = protected_hashes(spec)
    write()
    textures_record = {}
    baked = []
    for v in spec['variants']:
        row = dict(id=v['id'], short=v['short'])
        receipt['variants'].append(row)
        skel = ue.load_asset(v['skeletalMesh'])
        walk = ue.load_asset(v['walk'])
        idle = ue.load_asset(v['idle'])
        if not (skel and walk and idle):
            raise RuntimeError('%s: source asset failed to load' % v['id'])
        skeleton = skel.get_editor_property('skeleton')
        for clip, key in ((walk, 'walk'), (idle, 'idle')):
            clip_skel = clip.get_editor_property('skeleton')
            keys = int(ue.AnimationLibrary.get_num_keys(clip))
            length = float(ue.AnimationLibrary.get_sequence_length(clip))
            row[key + 'Source'] = dict(path=_path(clip), keys=keys, lengthSec=round(length, 6),
                                       skeleton=_path(clip_skel), onBodySkeleton=_path(clip_skel) == _path(skeleton))
            if not row[key + 'Source']['onBodySkeleton']:
                raise RuntimeError('%s %s clip is not on the body skeleton' % (v['id'], key))
            if keys != spec[key]['expectedKeys'] or abs(length - spec[key]['expectedLengthSec']) > 1e-3:
                raise RuntimeError('%s %s clip has %d keys / %.4f s, spec expects %d / %.4f' %
                                   (v['id'], key, keys, length, spec[key]['expectedKeys'], spec[key]['expectedLengthSec']))
        mesh_package = ns + '/Meshes/SM_CrowdVAT_' + v['short']
        mesh = _convert(ue, skel, mesh_package, spec['mesh']['targetTriangles'], row)
        row['converted'] = _mesh_stats(ue, mesh)
        write()
        if not ue.AnimToTextureBPLibrary.set_light_map_index(mesh, 0, 0, False):
            raise RuntimeError('set_light_map_index failed')
        row['decimated'] = _mesh_stats(ue, mesh)
        write()
        folder = ns + '/Textures'
        tex = {}
        for clip_key in ('Walk', 'Idle'):
            for kind in ('Position', 'Normal'):
                tex[clip_key + kind] = _texture(ue, tools, assets, folder, 'T_CrowdVAT_%s_%s%s' % (v['short'], clip_key, kind))
        _bake_clip(ue, spec, mesh, skel, walk, spec['walk'], tex['WalkPosition'], tex['WalkNormal'], 'walkBake', row)
        _bake_clip(ue, spec, mesh, skel, idle, spec['idle'], tex['IdlePosition'], tex['IdleNormal'], 'idleBake', row)
        for t in tex.values():
            _finish_texture(ue, t, textures_record)
            if not assets.save_loaded_asset(t, False):
                raise RuntimeError('Texture save failed: ' + t.get_name())
        row['baked'] = _mesh_stats(ue, mesh)
        row['textures'] = {k: _path(t) for k, t in tex.items()}
        if not assets.save_loaded_asset(mesh, False):
            raise RuntimeError('Mesh save failed: ' + mesh.get_name())
        row['mesh'] = _path(mesh)
        baked.append((v, row, mesh, tex))
        write()
    receipt['textureSettings'] = textures_record
    first = baked[0][1]
    defaults = dict(WalkPositionTexture=baked[0][3]['WalkPosition'], WalkNormalTexture=baked[0][3]['WalkNormal'],
                    IdlePositionTexture=baked[0][3]['IdlePosition'], IdleNormalTexture=baked[0][3]['IdleNormal'],
                    WalkMinBBox=first['walkBake']['minBBox'], WalkSizeBBox=first['walkBake']['sizeBBox'],
                    IdleMinBBox=first['idleBake']['minBBox'], IdleSizeBBox=first['idleBake']['sizeBBox'])
    master = build_master(ue, spec, ns, defaults, receipt)
    write()
    mi_record = {}
    for v, row, mesh, tex in baked:
        slots = mesh.get_editor_property('static_materials')
        assigned = []
        for index, slot in enumerate(slots):
            slot_name = str(slot.get_editor_property('material_slot_name'))
            key = next((k for k in v['slots'] if slot_name.lower() == k.lower() or slot_name.lower().startswith(k.lower())), None)
            if key is None:
                raise RuntimeError('%s slot %r has no entry in the spec' % (v['id'], slot_name))
            s = v['slots'][key]
            mi = _mi(ue, tools, assets, ns + '/Materials', 'MI_CrowdVAT_%s_%s' % (v['short'], key), master,
                     dict(WalkPositionTexture=tex['WalkPosition'], WalkNormalTexture=tex['WalkNormal'],
                          IdlePositionTexture=tex['IdlePosition'], IdleNormalTexture=tex['IdleNormal']),
                     dict(WalkMinBBox=row['walkBake']['minBBox'], WalkSizeBBox=row['walkBake']['sizeBBox'],
                          IdleMinBBox=row['idleBake']['minBBox'], IdleSizeBBox=row['idleBake']['sizeBBox'],
                          BaseColor=s['baseColor']),
                     dict(Roughness=s['roughness'], PaletteMix=s['paletteMix'], SkinVariation=s['skinVariation']),
                     mi_record)
            mesh.set_material(index, mi)
            if _path(mesh.get_material(index)) != _path(mi):
                raise RuntimeError('%s slot %d did not take %s' % (v['id'], index, mi.get_name()))
            assigned.append([index, slot_name, _path(mi)])
        row['slotMaterials'] = assigned
        if not assets.save_loaded_asset(mesh, False):
            raise RuntimeError('Mesh save after material assignment failed: ' + mesh.get_name())
        write()
    receipt['materialInstances'] = mi_record
    after = protected_hashes(spec)
    receipt['protectedAfter'] = after
    moved = sorted(k for k in set(after) | set(receipt['protectedBefore'])
                   if after.get(k) != receipt['protectedBefore'].get(k))
    receipt['protectedChanged'] = moved
    if moved:
        raise RuntimeError('Protected assets changed bytes: %r' % moved)
    receipt['status'] = 'baked_saved_verify_pending'


BOUNDS_EXTENSION_CM = dict(positive=(110.0, 110.0, 25.0), negative=(110.0, 110.0, 15.0))


def run_bounds(ue, spec, receipt, write):
    """Widen the six VAT meshes' bounds so culling never drops a visible figure.

    AnimationToTexture's SetBoundsExtensions treats the delta box as positions, which left the
    meshes +/-22 cm wide laterally (crowd-vat-verify-20260911T043359089799Z.json) while a stride
    swings the feet ~45 cm and the material extrapolates the body up to Speed x Horizon (< 1 m)
    past its instance transform between visits. 110 cm each way covers both."""
    ns = _value(ue, 'CrowdVatNamespace') or spec['namespace']
    folder = ROOT / spec['receiptFolder']
    bake = None
    for f in sorted(folder.glob('crowd-vat-bake-*.json'), reverse=True):
        data = json.loads(f.read_text(encoding='utf-8-sig'))
        if data.get('status') == 'baked_saved_verify_pending' and data.get('namespace') == ns:
            bake = (f, data)
            break
    if not bake:
        raise RuntimeError('No successful bake receipt for ' + ns)
    receipt['bakeReceipt'] = bake[0].name
    pos = ue.Vector(*BOUNDS_EXTENSION_CM['positive'])
    neg = ue.Vector(*BOUNDS_EXTENSION_CM['negative'])
    rows = []
    for row in bake[1]['variants']:
        mesh = ue.load_asset(row['mesh'])
        before = dict(positive=_v3(mesh.get_editor_property('positive_bounds_extension')),
                      negative=_v3(mesh.get_editor_property('negative_bounds_extension')),
                      box=[_v3(mesh.get_bounding_box().min), _v3(mesh.get_bounding_box().max)])
        mesh.set_editor_property('positive_bounds_extension', pos)
        mesh.set_editor_property('negative_bounds_extension', neg)
        got_p = _v3(mesh.get_editor_property('positive_bounds_extension'))
        got_n = _v3(mesh.get_editor_property('negative_bounds_extension'))
        if got_p != list(BOUNDS_EXTENSION_CM['positive']) or got_n != list(BOUNDS_EXTENSION_CM['negative']):
            raise RuntimeError('%s bounds extension read back %r / %r' % (row['id'], got_p, got_n))
        if not ue.EditorAssetLibrary.save_loaded_asset(mesh, False):
            raise RuntimeError('Mesh save failed: ' + row['mesh'])
        rows.append(dict(id=row['id'], mesh=row['mesh'], before=before, after=dict(positive=got_p, negative=got_n),
                         triangles=int(mesh.get_num_triangles(0))))
        write()
    receipt['variants'] = rows
    receipt['status'] = 'bounds_extended_saved'


def run_verify(ue, spec, receipt, write):
    ns = _value(ue, 'CrowdVatNamespace') or spec['namespace']
    bakes = sorted((ROOT / spec['receiptFolder']).glob('crowd-vat-bake-*.json'))
    source = None
    for f in reversed(bakes):
        data = json.loads(f.read_text(encoding='utf-8-sig'))
        if data.get('status') == 'baked_saved_verify_pending' and data.get('namespace') == ns:
            source = (f, data)
            break
    if not source:
        raise RuntimeError('No successful bake receipt for ' + ns)
    receipt['bakeReceipt'] = source[0].name
    master_path = source[1]['master']['path']
    swap = _newest(spec, 'crowd-vat-removev1-*.json', 'material_v2_saved', ns) or         _newest(spec, 'crowd-vat-materialv2-*.json', 'material_v2_saved', ns)
    if swap:
        # The V2 stock-node master replaced V1 on every slot; verify against it.
        receipt['materialV2Receipt'] = swap[0].name
        master_path = swap[1]['masterV2']['path']
        slots_by_id = {v['id']: v['slotMaterials'] for v in swap[1]['variants']}
        for row in source[1]['variants']:
            row['slotMaterials'] = slots_by_id[row['id']]
    master = ue.load_asset(master_path)
    if not master or not master.get_editor_property('used_with_instanced_static_meshes'):
        raise RuntimeError('Master material missing or not flagged for instanced static meshes')
    rows = []
    for row in source[1]['variants']:
        mesh = ue.load_asset(row['mesh'])
        stats = _mesh_stats(ue, mesh)
        check = dict(id=row['id'], stats=stats, problems=[])
        if stats['triangles'] != row['baked']['triangles']:
            check['problems'].append('triangle count moved')
        if stats.get('uvChannels') is not None and stats['uvChannels'] < 3:
            check['problems'].append('fewer than 3 UV channels after reopen')
        for index, slot_name, mi_path in row['slotMaterials']:
            mat = mesh.get_material(index)
            if _path(mat) != mi_path:
                check['problems'].append('slot %d is %s' % (index, _path(mat)))
            elif _path(mat.get_editor_property('parent')) != _path(master):
                check['problems'].append('slot %d parent is not the master' % index)
        for key, path in row['textures'].items():
            t = ue.load_asset(path)
            if not t:
                check['problems'].append('texture %s missing' % key)
                continue
            if t.get_editor_property('srgb') or t.get_editor_property('filter') != ue.TextureFilter.TF_NEAREST:
                check['problems'].append('texture %s settings reverted' % key)
            bake = row['walkBake' if key.startswith('Walk') else 'idleBake']
            if int(t.blueprint_get_size_y()) != bake['height'] or int(t.blueprint_get_size_x()) != bake['width']:
                check['problems'].append('texture %s size moved' % key)
        rows.append(check)
    receipt['variants'] = rows
    bad = [r for r in rows if r['problems']]
    receipt['status'] = 'verified_after_reopen' if not bad else 'verify_failed'
    if bad:
        raise RuntimeError('Verify found problems: %r' % [(r['id'], r['problems']) for r in bad])


# =============================================================================================
# M_CrowdVAT_V2: the same contract in STOCK NODES ONLY
# =============================================================================================
# WHY V2 EXISTS. M_CrowdVAT_V1 fed PerInstanceCustomData into author-written HLSL (Custom nodes)
# that drives WPO and two vertex interpolators. That is exactly the combination EnclosureMath.h
# section 6b forbids: the plaza paving master did it and crashed ShaderCompileWorker at cook time
# (-1073741819, FLocalVertexFactory, no diagnostic). V1 did the same on 2026-09-11: the cp19 cook
# died on an SCW access violation with three M_CrowdVAT_V1 jobs in the dead batch, and the bake
# log Fable-CrowdVat-Bake-02 shows it too. Per 6b-ii an access violation alone does not prove the
# graph guilty, but the rule stands and V1 broke other agents' cooks, so V2 removes the Custom
# nodes entirely. Nothing about the anchor contract changes; only how the arithmetic is spelled.

class StockGraph(Graph):
    def pin(self, dst, candidates):
        live = [str(n) for n in self.ml.get_material_expression_input_names(dst)]
        for c in candidates:
            for name in live:
                if name.lower() == str(c).lower():
                    return name
        if len(live) == 1:
            return live[0]
        raise RuntimeError('%s has none of %r (live %r)' % (dst.get_class().get_name(), candidates, live))

    def link(self, src, dst, candidates):
        node, out = src if isinstance(src, tuple) else (src, '')
        name = self.pin(dst, candidates)
        if not self.ml.connect_material_expressions(node, out, dst, name):
            raise RuntimeError('connect %s.%r -> %s.%s failed' % (node.get_class().get_name(), out, dst.get_class().get_name(), name))
        self.pins.append([dst.get_class().get_name(), name, out])

    def const(self, value):
        node = self.make(self.ue.MaterialExpressionConstant)
        _set(node, 'r', float(value), lambda a, b: abs(a - b) < 1e-6)
        return node

    def const3(self, rgb):
        node = self.make(self.ue.MaterialExpressionConstant3Vector)
        node.set_editor_property('constant', self.ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
        got = node.get_editor_property('constant')
        if any(abs(float(x) - float(y)) > 1e-4 for x, y in zip((got.r, got.g, got.b), rgb)):
            raise RuntimeError('Constant3Vector did not take %r' % (rgb,))
        return node

    def op(self, cls, a, b):
        node = self.make(cls)
        self.link(a, node, ['A'])
        self.link(b, node, ['B'])
        return node

    def unary(self, cls, a):
        node = self.make(cls)
        self.link(a, node, ['Input', 'None', '', 'VectorInput', 'X'])
        return node

    def lerp(self, a, b, alpha):
        node = self.make(self.ue.MaterialExpressionLinearInterpolate)
        self.link(a, node, ['A'])
        self.link(b, node, ['B'])
        self.link(alpha, node, ['Alpha'])
        return node

    def clamp(self, x, lo, hi):
        node = self.make(self.ue.MaterialExpressionClamp)
        self.link(x, node, ['Input', 'None', ''])
        self.link(lo, node, ['Min'])
        self.link(hi, node, ['Max'])
        return node

    def mask(self, x, channels):
        # 5.8 trap: a new ComponentMask starts with R, G and B ticked. Set all four, read back.
        node = self.make(self.ue.MaterialExpressionComponentMask)
        for ch in 'rgba':
            _set(node, ch, ch in channels)
        self.link(x, node, ['Input', 'None', ''])
        return node

    def tex(self, name, texture, uv):
        ue = self.ue
        node = self.make(ue.MaterialExpressionTextureSampleParameter2D)
        _set(node, 'parameter_name', name, lambda a, b: str(a) == str(b))
        node.set_editor_property('texture', texture)
        _set(node, 'sampler_type', ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        # Vertex-stage sampling needs an explicit mip: MipLevel mode, level 0 (the VAT has no mips).
        _set(node, 'mip_value_mode', ue.TextureMipValueMode.TMVM_MIP_LEVEL)
        _set(node, 'const_mip_value', 0)
        self.link(uv, node, ['UVs', 'Coordinates'])
        outs = [str(n) for n in self.ml.get_material_expression_output_names(node)] \
            if hasattr(self.ml, 'get_material_expression_output_names') else ['RGB']
        if 'RGB' not in outs:
            raise RuntimeError('TextureSampleParameter2D has no RGB output: %r' % outs)
        return (node, 'RGB')


def build_master_v2(ue, spec, ns, name, defaults, receipt):
    tools = ue.AssetToolsHelpers.get_asset_tools()
    assets = ue.EditorAssetLibrary
    folder = ns + '/Materials'
    if assets.does_asset_exist(folder + '/' + name):
        raise RuntimeError('%s already exists (build to a new name)' % name)
    material = tools.create_asset(name, folder, ue.Material, ue.MaterialFactoryNew())
    g = StockGraph(ue, material, receipt)
    E = ue
    mp = ue.MaterialProperty
    t = g.make(E.MaterialExpressionTime)
    cd_defaults = {0: 0.0, 1: 0.5, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: -1000.0, 9: 0.5, 10: 0.0}
    cd = {i: g.custom_data(i, d, 0, 0) for i, d in cd_defaults.items()}
    uvw = g.make(E.MaterialExpressionTextureCoordinate, coordinate_index=int(spec['walk']['uvChannel']))
    uvi = g.make(E.MaterialExpressionTextureCoordinate, coordinate_index=int(spec['idle']['uvChannel']))
    walk_frames = g.scalar('WalkFrames', spec['walk']['loopFrames'], 0, 0)
    idle_frames = g.scalar('IdleFrames', spec['idle']['loopFrames'], 0, 0)
    idle_seconds = g.scalar('IdleSeconds', spec['idle']['loopFrames'] / spec['idle']['sampleRateHz'], 0, 0)
    blend = g.scalar('BlendSeconds', spec['material']['blendSeconds'], 0, 0)
    negdt = g.scalar('NegativeDtSeconds', spec['material']['negativeDtSeconds'], 0, 0)
    rgb = lambda node: g.mask(node, 'rgb')
    wmin = rgb(g.vector('WalkMinBBox', defaults['WalkMinBBox'], 0, 0))
    wsize = rgb(g.vector('WalkSizeBBox', defaults['WalkSizeBBox'], 0, 0))
    imin = rgb(g.vector('IdleMinBBox', defaults['IdleMinBBox'], 0, 0))
    isize = rgb(g.vector('IdleSizeBBox', defaults['IdleSizeBBox'], 0, 0))
    base = rgb(g.vector('BaseColor', [0.7, 0.65, 0.55], 0, 0))
    rough = g.scalar('Roughness', 0.85, 0, 0)
    spec_node = g.scalar('Specular', spec['material']['specular'], 0, 0)
    mix = g.scalar('PaletteMix', 0.0, 0, 0)
    skinvar = g.scalar('SkinVariation', 0.0, 0, 0)
    M, A, S, D = E.MaterialExpressionMultiply, E.MaterialExpressionAdd, E.MaterialExpressionSubtract, E.MaterialExpressionDivide

    # dt = clamp(t - T0, -NegDt, Horizon): the SAME clamp for travel and stride.
    dt = g.clamp(g.op(S, t, cd[3]), g.op(M, negdt, g.const(-1.0)), cd[10])
    walk_phase = g.unary(E.MaterialExpressionFrac, g.op(A, cd[0], g.op(M, dt, cd[4])))
    idle_rate = g.op(A, g.const(0.92), g.op(M, g.const(0.16), g.unary(E.MaterialExpressionFrac, g.op(M, cd[9], g.const(7.31)))))
    idle_phase = g.unary(E.MaterialExpressionFrac, g.op(A, cd[9], g.op(D, g.op(M, t, idle_rate), idle_seconds)))
    w = g.unary(E.MaterialExpressionSaturate, g.op(D, g.op(S, t, cd[8]), blend))
    idle_w = g.lerp(g.unary(E.MaterialExpressionOneMinus, w), w, cd[2])

    def clip(phase, frames, uv, tex_name, tex_obj):
        fr = g.op(M, phase, frames)
        f0 = g.unary(E.MaterialExpressionFloor, fr)
        a = g.unary(E.MaterialExpressionFrac, fr)
        u = g.mask(uv, 'r')
        v = g.mask(uv, 'g')
        # Row f sits at V + f/N (one row per frame, height = N). Frame N wraps to frame 0 through the
        # texture's Wrap addressing, so the last-to-first interpolation needs no branch.
        v0 = g.op(A, v, g.op(D, f0, frames))
        v1 = g.op(A, v, g.op(D, g.op(A, f0, g.const(1.0)), frames))
        s0 = g.tex(tex_name, tex_obj, g.op(E.MaterialExpressionAppendVector, u, v0))
        s1 = g.tex(tex_name, tex_obj, g.op(E.MaterialExpressionAppendVector, u, v1))
        return g.lerp(s0, s1, a)

    walk_p = g.op(A, g.op(M, clip(walk_phase, walk_frames, uvw, 'WalkPositionTexture', defaults['WalkPositionTexture']), wsize), wmin)
    idle_p = g.op(A, g.op(M, clip(idle_phase, idle_frames, uvi, 'IdlePositionTexture', defaults['IdlePositionTexture']), isize), imin)
    delta = g.lerp(walk_p, idle_p, idle_w)
    to_world = lambda src: _transform(g, src)
    drift = g.op(M, g.op(E.MaterialExpressionAppendVector, g.op(E.MaterialExpressionAppendVector, cd[5], cd[6]), cd[7]), dt)
    wpo = g.op(A, to_world(delta), drift)
    g.prop(wpo, mp.MP_WORLD_POSITION_OFFSET)

    decode = lambda x: g.op(S, g.op(M, x, g.const(2.0)), g.const(1.0))
    walk_n = decode(clip(walk_phase, walk_frames, uvw, 'WalkNormalTexture', defaults['WalkNormalTexture']))
    idle_n = decode(clip(idle_phase, idle_frames, uvi, 'IdleNormalTexture', defaults['IdleNormalTexture']))
    normal = g.unary(E.MaterialExpressionNormalize, g.op(A, g.lerp(walk_n, idle_n, idle_w), g.const3([0.0, 0.0, 1e-4])))
    n_interp = g.make(E.MaterialExpressionVertexInterpolator)
    g.link(to_world(normal), n_interp, ['VS'])
    g.prop(n_interp, mp.MP_NORMAL)

    palette = spec['material']['palette']
    index = g.op(M, cd[1], g.const(len(palette) - 1))
    total = None
    for k, entry in enumerate(palette):
        weight = g.unary(E.MaterialExpressionSaturate, g.unary(E.MaterialExpressionOneMinus,
                         g.unary(E.MaterialExpressionAbs, g.op(S, index, g.const(k)))))
        term = g.op(M, weight, g.const3(entry))
        total = term if total is None else g.op(A, total, term)
    bright = g.op(A, g.const(0.90), g.op(M, g.const(0.20), g.unary(E.MaterialExpressionFrac, g.op(M, cd[9], g.const(13.7)))))
    garment = g.op(M, g.lerp(base, total, mix), bright)
    complexion = g.op(A, g.const(0.72), g.op(M, g.const(0.50), g.unary(E.MaterialExpressionFrac, g.op(M, cd[9], g.const(5.3)))))
    colour = g.lerp(garment, g.op(M, base, complexion), skinvar)
    c_interp = g.make(E.MaterialExpressionVertexInterpolator)
    g.link(colour, c_interp, ['VS'])
    g.prop(c_interp, mp.MP_BASE_COLOR)
    g.prop(rough, mp.MP_ROUGHNESS)
    g.prop(spec_node, mp.MP_SPECULAR)
    g.prop(g.const(0.0), mp.MP_METALLIC)

    _set(material, 'tangent_space_normal', False)
    _set(material, 'used_with_instanced_static_meshes', True)
    ml = ue.MaterialEditingLibrary
    census = {}
    for node in ml.get_material_expressions(material):
        census[node.get_class().get_name()] = census.get(node.get_class().get_name(), 0) + 1
    if census.get('MaterialExpressionCustom'):
        raise RuntimeError('A Custom node is in M_CrowdVAT_V2; the stock-node rule (EnclosureMath.h 6b) refuses it')
    ml.recompile_material(material)
    if not assets.save_loaded_asset(material, False):
        raise RuntimeError('V2 master save failed')
    receipt['masterV2'] = dict(path=_path(material), census=census, customNodes=census.get('MaterialExpressionCustom', 0),
                               usedWithInstancedStaticMeshes=bool(material.get_editor_property('used_with_instanced_static_meshes')),
                               tangentSpaceNormal=bool(material.get_editor_property('tangent_space_normal')))
    return material


def _transform(g, src):
    ue = g.ue
    node = g.make(ue.MaterialExpressionTransform)
    _set(node, 'transform_source_type', ue.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
    _set(node, 'transform_type', ue.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    g.link(src, node, ['Input', 'None', ''])
    return node


def _newest(spec, pattern, status_prefix, ns):
    for f in sorted((ROOT / spec['receiptFolder']).glob(pattern), reverse=True):
        data = json.loads(f.read_text(encoding='utf-8-sig'))
        if str(data.get('status', '')).startswith(status_prefix) and data.get('namespace') == ns:
            return f, data
    return None


def run_material_v2(ue, spec, receipt, write):
    import shutil
    ns = _value(ue, 'CrowdVatNamespace') or spec['namespace']
    receipt['namespace'] = ns
    found = _newest(spec, 'crowd-vat-bake-*.json', 'baked_saved_verify_pending', ns)
    if not found:
        raise RuntimeError('No successful bake receipt for ' + ns)
    bake_file, bake = found
    receipt['bakeReceipt'] = bake_file.name
    maps_before = {k: sha(disk_umap(p)) for k, p in MAPS.items()}
    receipt['mapsBefore'] = maps_before
    assets = ue.EditorAssetLibrary
    tools = ue.AssetToolsHelpers.get_asset_tools()
    first = bake['variants'][0]
    defaults = dict(WalkPositionTexture=ue.load_asset(first['textures']['WalkPosition']),
                    WalkNormalTexture=ue.load_asset(first['textures']['WalkNormal']),
                    IdlePositionTexture=ue.load_asset(first['textures']['IdlePosition']),
                    IdleNormalTexture=ue.load_asset(first['textures']['IdleNormal']),
                    WalkMinBBox=first['walkBake']['minBBox'], WalkSizeBBox=first['walkBake']['sizeBBox'],
                    IdleMinBBox=first['idleBake']['minBBox'], IdleSizeBBox=first['idleBake']['sizeBBox'])
    master = build_master_v2(ue, spec, ns, 'M_CrowdVAT_V2', defaults, receipt)
    write()
    mi_record, variants = {}, []
    v1_materials = set()
    bake_spec_by_id = {v['id']: v for v in spec['variants']}
    for row in bake['variants']:
        v = bake_spec_by_id[row['id']]
        mesh = ue.load_asset(row['mesh'])
        tex = {k: ue.load_asset(p) for k, p in row['textures'].items()}
        assigned = []
        for index, slot in enumerate(mesh.get_editor_property('static_materials')):
            slot_name = str(slot.get_editor_property('material_slot_name'))
            old = mesh.get_material(index)
            if old and _path(old).startswith(ns + '/Materials/MI_CrowdVAT_'):
                v1_materials.add(_path(old))
            key = next((k for k in v['slots'] if slot_name.lower() == k.lower() or slot_name.lower().startswith(k.lower())), None)
            if key is None:
                raise RuntimeError('%s slot %r has no spec entry' % (row['id'], slot_name))
            s = v['slots'][key]
            mi = _mi(ue, tools, assets, ns + '/Materials', 'MI_CrowdVAT2_%s_%s' % (v['short'], key), master,
                     dict(WalkPositionTexture=tex['WalkPosition'], WalkNormalTexture=tex['WalkNormal'],
                          IdlePositionTexture=tex['IdlePosition'], IdleNormalTexture=tex['IdleNormal']),
                     dict(WalkMinBBox=row['walkBake']['minBBox'], WalkSizeBBox=row['walkBake']['sizeBBox'],
                          IdleMinBBox=row['idleBake']['minBBox'], IdleSizeBBox=row['idleBake']['sizeBBox'],
                          BaseColor=s['baseColor']),
                     dict(Roughness=s['roughness'], PaletteMix=s['paletteMix'], SkinVariation=s['skinVariation']),
                     mi_record)
            mesh.set_material(index, mi)
            if _path(mesh.get_material(index)) != _path(mi):
                raise RuntimeError('%s slot %d did not take %s' % (row['id'], index, mi.get_name()))
            assigned.append([index, slot_name, _path(mi)])
        if not assets.save_loaded_asset(mesh, False):
            raise RuntimeError('Mesh save failed: ' + row['mesh'])
        variants.append(dict(id=row['id'], mesh=row['mesh'], slotMaterials=assigned))
        write()
    receipt['variants'] = variants
    receipt['materialInstancesV2'] = mi_record
    # Take V1 out of Content so no cook compiles it again. Copies first: restore = copy back.
    v1_master = bake['master']['path']
    doomed = sorted(v1_materials) + [v1_master]
    checkpoint = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints') / ('CrowdVATMatV1-' + receipt['stamp'])
    checkpoint.mkdir(parents=True, exist_ok=False)
    removed = []
    for path in doomed:
        f = disk_uasset(path)
        shutil.copy2(f, checkpoint / f.name)
        if sha(checkpoint / f.name) != sha(f):
            raise RuntimeError('checkpoint copy mismatch for ' + path)
    for path in doomed:
        refs = [str(r) for r in assets.find_package_referencers_for_asset(path.split('.')[0], False)]
        outside = [r for r in refs if not (r.startswith(ns + '/Materials/MI_CrowdVAT_') or r == v1_master.split('.')[0])]
        if outside:
            raise RuntimeError('%s is still referenced by %r; not deleting' % (path, outside))
    for path in doomed:
        if not assets.delete_asset(path.split('.')[0]):
            raise RuntimeError('delete_asset failed for ' + path)
        if disk_uasset(path).exists():
            raise RuntimeError('deleted asset still on disk: ' + path)
        removed.append(path)
    receipt['v1Removed'] = dict(checkpoint=str(checkpoint), assets=removed)
    maps_after = {k: sha(disk_umap(p)) for k, p in MAPS.items()}
    receipt['mapsAfter'] = maps_after
    if maps_after != maps_before:
        raise RuntimeError('A map changed bytes during the material swap')
    receipt['status'] = 'material_v2_saved_verify_pending'


def _find_refs(value, needle, path, hits, depth=0, seen=None):
    """Every property path under `value` that holds an object whose path contains `needle`."""
    seen = seen if seen is not None else set()
    if depth > 7 or value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if needle in value:
            hits.append('%s = %s' % (path, value))
        return
    if hasattr(value, 'get_path_name'):
        try:
            p = value.get_path_name()
        except Exception:                                            # noqa: BLE001
            return
        if needle in p:
            hits.append('%s -> %s' % (path, p))
        return
    if isinstance(value, (list, tuple, set)):
        for i, item in enumerate(value):
            _find_refs(item, needle, '%s[%d]' % (path, i), hits, depth + 1, seen)
        return
    if id(value) in seen:
        return
    seen.add(id(value))
    for name in sorted(_doc_props(type(value))):
        try:
            child = value.get_editor_property(name)
        except Exception:                                            # noqa: BLE001
            continue
        _find_refs(child, needle, path + '.' + name, hits, depth + 1, seen)


def _file_names(path_obj, pattern):
    return sorted(set(m.decode() for m in re.findall(pattern, disk_uasset(path_obj).read_bytes())))


def run_remove_v1(ue, spec, receipt, write):
    """Finish the V1 -> V2 swap: prove the six meshes hold no V1 material, then delete V1.

    MEASURED 2026-09-11 (crowd-vat-materialv2-20260911T051456863013Z.json): after every slot was
    re-pointed to MI_CrowdVAT2_* and saved, each mesh package STILL named all of its V1 instances
    (offline name-table read), so the referencer guard refused the delete. This mode finds the
    property that holds them, clears it, and deletes V1 only when the saved bytes are clean."""
    import shutil
    ns = _value(ue, 'CrowdVatNamespace') or spec['namespace']
    receipt['namespace'] = ns
    folder = ROOT / spec['receiptFolder']
    swap = None
    for f in sorted(folder.glob('crowd-vat-materialv2-*.json'), reverse=True):
        data = json.loads(f.read_text(encoding='utf-8-sig'))
        if data.get('namespace') == ns and data.get('masterV2') and data.get('variants'):
            swap = (f, data)
            break
    if not swap:
        raise RuntimeError('No V2 material receipt with a built master and assigned variants')
    receipt['swapReceipt'] = swap[0].name
    receipt['bakeReceipt'] = swap[1]['bakeReceipt']
    receipt['masterV2'] = swap[1]['masterV2']
    receipt['materialInstancesV2'] = swap[1].get('materialInstancesV2', {})
    bake = json.loads((folder / swap[1]['bakeReceipt']).read_text(encoding='utf-8-sig'))
    maps_before = {k: sha(disk_umap(p)) for k, p in MAPS.items()}
    receipt['mapsBefore'] = maps_before
    assets = ue.EditorAssetLibrary
    v1_prefix = ns + '/Materials/MI_CrowdVAT_'
    v1_master = bake['master']['path']
    pat_v1 = rb'MI_CrowdVAT_[A-Za-z_]+|M_CrowdVAT_V1'
    rows = []
    for v in swap[1]['variants']:
        mesh = ue.load_asset(v['mesh'])
        slots = [_path(mesh.get_material(i)) for i in range(len(mesh.get_editor_property('static_materials')))]
        expected = [s[2] for s in v['slotMaterials']]
        row = dict(id=v['id'], mesh=v['mesh'], slotsNow=slots, slotsMatchV2=(slots == expected),
                   fileV1NamesBefore=_file_names(v['mesh'], pat_v1))
        if not row['slotsMatchV2']:
            for index, _, mi_path in v['slotMaterials']:
                mesh.set_material(index, ue.load_asset(mi_path))
        hits = []
        for name in sorted(_doc_props(type(mesh))):
            try:
                _find_refs(mesh.get_editor_property(name), v1_prefix, name, hits)
                _find_refs(mesh.get_editor_property(name), v1_master.split('.')[0], name, hits)
            except Exception:                                        # noqa: BLE001
                continue
        row['pythonVisibleV1Refs'] = hits
        rows.append(row)
        write()
    receipt['variants'] = rows
    # Second witness: the engine's own reference chain for one V1 instance, into the log.
    probe = rows[1]['fileV1NamesBefore'][0] if rows and rows[1]['fileV1NamesBefore'] else None
    if probe and probe.startswith('MI_'):
        target = '%s%s.%s' % (v1_prefix, probe[len('MI_CrowdVAT_'):], probe)
        ue.load_asset(target)
        ue.SystemLibrary.collect_garbage()
        ue.SystemLibrary.execute_console_command(None, 'obj refs name=' + target)
        receipt['objRefsProbe'] = target
    write()
    # Re-save every mesh from scratch state, then read the saved bytes: the ground truth.
    for row in rows:
        mesh = ue.load_asset(row['mesh'])
        # 5.8 Python StaticMesh has no post_edit_change (measured: AttributeError,
        # crowd-vat-removev1-20260911T053300343749Z.json). modify() + a forced save is enough: the
        # property walk and `obj refs` both showed no in-memory V1 referencer.
        mesh.modify()
        if not assets.save_loaded_asset(mesh, False):
            raise RuntimeError('Mesh save failed: ' + row['mesh'])
        row['fileV1NamesAfterResave'] = _file_names(row['mesh'], pat_v1)
    write()
    dirty = [r['id'] for r in rows if r['fileV1NamesAfterResave']]
    if dirty:
        receipt['status'] = 'v1_still_referenced_not_deleted'
        raise RuntimeError('Meshes still name V1 materials after re-save: %r (see pythonVisibleV1Refs and the obj refs log)' % dirty)
    doomed = sorted(p for p in (str(a) for a in assets.list_assets(ns + '/Materials', False, False))
                    if p.split('/')[-1].split('.')[0].startswith('MI_CrowdVAT_')) + [v1_master.split('.')[0]]
    checkpoint = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints') / ('CrowdVATMatV1-remove-' + receipt['stamp'])
    checkpoint.mkdir(parents=True, exist_ok=False)
    for path in doomed:
        f = disk_uasset(path)
        shutil.copy2(f, checkpoint / f.name)
    removed = []
    for path in doomed:
        if not assets.delete_asset(path.split('.')[0]):
            raise RuntimeError('delete_asset failed for ' + path)
        if disk_uasset(path).exists():
            raise RuntimeError('deleted asset still on disk: ' + path)
        removed.append(path)
    receipt['v1Removed'] = dict(checkpoint=str(checkpoint), count=len(removed), assets=removed)
    receipt['variants'] = [dict(r, slotMaterials=next(v['slotMaterials'] for v in swap[1]['variants'] if v['id'] == r['id']))
                           for r in rows]
    maps_after = {k: sha(disk_umap(p)) for k, p in MAPS.items()}
    receipt['mapsAfter'] = maps_after
    if maps_after != maps_before:
        raise RuntimeError('A map changed bytes during the V1 removal')
    receipt['status'] = 'material_v2_saved_verify_pending'


def _main():
    try:
        import unreal as ue
    except ImportError:
        problems = offline_check()
        print(json.dumps(dict(offlineCheck='pass' if not problems else 'fail', problems=problems), indent=2))
        sys.exit(1 if problems else 0)
    spec = load_spec()
    mode = 'bake' if _switch(ue, 'CrowdVatBake') else ('verify' if _switch(ue, 'CrowdVatVerify') else
                                                        ('bounds' if _switch(ue, 'CrowdVatBounds') else
                                                         ('materialv2' if _switch(ue, 'CrowdVatMaterialV2') else
                                                          ('removev1' if _switch(ue, 'CrowdVatRemoveV1') else None))))
    stamp = stamp_now()
    out_dir = ROOT / spec['receiptFolder']
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / ('crowd-vat-%s-%s.json' % (mode or 'nomode', stamp))
    receipt = dict(status='starting', mode=mode, utc=utc(), stamp=stamp, commandLine=ue.SystemLibrary.get_command_line(),
                   variants=[], errors=[])

    def write():
        out.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        problems = offline_check(spec)
        if problems:
            raise RuntimeError('Offline check failed: %r' % problems)
        receipt['api'] = _api_dump(ue)
        write()
        if mode is None:
            raise RuntimeError('Pass -CrowdVatBake or -CrowdVatVerify')
        if not getattr(ue, 'AnimToTextureBPLibrary', None):
            raise RuntimeError('AnimToTexture is not loaded: launch with -EnablePlugins=AnimToTexture,GeometryScripting')
        _guards(ue)
        if mode == 'bake':
            run_bake(ue, spec, receipt, write)
        elif mode == 'bounds':
            run_bounds(ue, spec, receipt, write)
        elif mode == 'materialv2':
            run_material_v2(ue, spec, receipt, write)
        elif mode == 'removev1':
            run_remove_v1(ue, spec, receipt, write)
        else:
            run_verify(ue, spec, receipt, write)
    except Exception:
        receipt['status'] = 'failed'
        receipt['errors'].append(traceback.format_exc())
        raise
    finally:
        receipt['finishedUtc'] = utc()
        write()


if __name__ == '__main__':
    _main()
