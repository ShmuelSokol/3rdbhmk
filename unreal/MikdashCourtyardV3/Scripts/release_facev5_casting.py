"""FaceV5 casting: dump each shortlisted MetaHuman preset's face so the Kohen Gadol can be CAST by eye.

  UnrealEditor.exe <uproject> -ExecutePythonScript=Scripts/release_facev5_casting.py
      -FaceV5CastRun -unattended -nullrhi -NoSplash
      -NoMetaHumanAccountPortalLoginFallback -EnablePlugins=GeometryScripting -abslog=<log>

ONE preset per invocation. `casting-progress.json` decides which is next, so a crash costs one
preset and never the batch, and peak memory stays bounded - assemble_for_preview builds the groom
card meshes and this box was down to 0.3 GB free during the probe.

Two things come out per preset, and neither calls an Epic cloud service:
  * `coefficients`: the 1397-value face model vector (GetFaceModelCoefficients). This is the blend
    lever - the approved Walter-toward-Lorenzo/Jorge blend is a weighted average of these.
  * `mesh`: the preview face mesh as OBJ, via AssembleForPreview -> SpawnMetaHumanActor ->
    GeometryScript CopyMeshFromSkeletalMesh. Rendered offline by Scripts/render_face_v5.py at one
    matched camera and light, which is the only way a comparison sheet is actually comparable.

Switches:
  -FaceV5CastRun            do the work (without it, print the plan and change nothing)
  -FaceV5CastOnly=<name>    do exactly this preset
  -FaceV5CastNoMesh         coefficients only (cheap; skips the groom build)
"""
import json
import os
import time
import traceback

import unreal as ue

ROOT = 'C:/Mikdash/Working-5.8/MikdashCourtyardV3'
OUT = ROOT + '/SourceAssets/characters-review/FaceV5/casting'
MESH_OUT = OUT + '/meshes'
PROGRESS = OUT + '/casting-progress.json'
PRESET_ROOT = '/MetaHumanCharacter/Optional/Presets'
CAST_ROOT = '/Game/MetaHumans/Casting'

# Shortlisted offline from the 29 albedo maps: mid, warm skin tone plus real weathering.
# Walter is the primary (the only preset carrying genuine age in its texture); Lorenzo and Jorge
# are the Levantine-structure blend partners; Victor and Bruce are lighter runners-up; Orlando is
# the smoother fallback. Excluded: East Asian presets (requirement), and tones too dark or too fair.
SHORTLIST = ['Walter', 'Lorenzo', 'Jorge', 'Victor', 'Bruce', 'Orlando']


def switch(name):
    return name.lower() in ue.SystemLibrary.get_command_line().lower()


def switch_value(name):
    cl = ue.SystemLibrary.get_command_line()
    key = name.lower() + '='
    low = cl.lower()
    if key not in low:
        return None
    tail = cl[low.index(key) + len(key):]
    for sep in (' ', '\t'):
        if sep in tail:
            tail = tail.split(sep)[0]
    return tail.strip('"').strip()


def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return json.load(f)
    return {'completed': [], 'failed': {}}


def save_progress(p):
    with open(PROGRESS, 'w') as f:
        f.write(json.dumps(p, indent=2) + '\n')


def find_fn(method):
    """UE 5.8 does not expose UGeometryScriptLibrary_* under the names the C++ headers use
    (the probe's `unreal.GeometryScriptLibrary_StaticMeshFunctions` raised AttributeError), and the
    exposed name depends on each class's ScriptName meta. Discover it instead of hard-coding, and
    record what was found so the receipt says which binding actually did the work."""
    for nm in dir(ue):
        try:
            cls = getattr(ue, nm)
        except Exception:
            continue
        if isinstance(cls, type) and hasattr(cls, method):
            return nm, getattr(cls, method)
    return None, None


def export_obj(dyn, path, name, row):
    """Write a DynamicMesh out as OBJ. Offline rendering only - no engine reads this back."""
    nv = int(dyn.get_vertex_count())
    nt = int(dyn.get_triangle_count())
    lines = ['# FaceV5 casting preview mesh: %s' % name,
             '# %d vertices, %d triangles' % (nv, nt)]
    # positions are in the actor's local centimetres, which is what render_face_v5 expects.
    # Prefer a bulk read: a per-vertex call would be ~72k Python->C++ round trips on a face LOD0.
    # UE 5.8 exposes these as DynamicMesh METHODS that return plain tuples, not as the
    # UGeometryScriptLibrary_* free functions the C++ headers use, and not as FVector. Measured:
    # get_all_vertex_positions() takes no extra args, and get_vertex_position() returns a tuple.
    def unwrap(p):
        # UE returns (value, bool) when a BlueprintCallable has an output param:
        # measured, get_vertex_position(i) -> (Vector, bIsValidVertex).
        while isinstance(p, (tuple, list)) and len(p) == 2 and isinstance(p[1], bool):
            p = p[0]
        return p

    def xyz(p):
        p = unwrap(p)
        if isinstance(p, (tuple, list)):
            return (float(p[0]), float(p[1]), float(p[2]))
        return (float(p.x), float(p.y), float(p.z))

    positions = None
    if hasattr(dyn, 'get_all_vertex_positions'):
        try:
            # measured: skip_gaps is a REQUIRED positional argument
            res = unwrap(dyn.get_all_vertex_positions(False))
            cand = list(getattr(res, 'list', res))
            if len(cand) >= nv:
                positions = cand
                row['vertexBinding'] = 'DynamicMesh.get_all_vertex_positions(False) bulk'
        except Exception as exc:
            row.setdefault('errors', []).append('bulk vertex read failed: %r' % (exc,))
    if positions is None:
        positions = [dyn.get_vertex_position(i) for i in range(nv)]
        row['vertexBinding'] = 'DynamicMesh.get_vertex_position(per-vertex)'
    for p in positions[:nv]:
        x, y, z = xyz(p)
        lines.append('v %.5f %.5f %.5f' % (x, y, z))
    row['triangleBinding'] = 'DynamicMesh.get_triangle_indices'
    tri_idx = []
    for i in range(nt):
        t = dyn.get_triangle_indices(i)
        a, b, c = xyz(t)
        tri_idx.append((int(a), int(b), int(c)))

    # UVs. The head has to be TEXTURED with the MetaHuman face albedo, so the unwrap must come out
    # with it; without UVs the baked head can only be flat-shaded. Per-corner UVs are written as a
    # `vt` list with f v/vt indices, which is what create_kohen_gadol_head_v5.load_obj reads.
    uvs, uv_tris, uv_mode = [], [], None
    # like copy_mesh_from_skeletal_mesh, this lives on a GeometryScript_* class rather than on
    # DynamicMesh, so hasattr(dyn, ...) is False and the binding has to be discovered.
    # UE Python exposes classes LAZILY, so dir(unreal) does not enumerate them all and the
    # discovery helper missed this one twice. The header gives the class its ScriptName directly:
    # UCLASS(meta = (ScriptName = "GeometryScript_MeshQueries")) on
    # UGeometryScriptLibrary_MeshQueryFunctions. Ask for it by name first, then fall back.
    uvfn_name, uvfn = None, None
    seen_names = {}
    for cname in ('GeometryScript_MeshQueries', 'GeometryScript_MeshQueryFunctions', 'DynamicMesh'):
        cls = getattr(ue, cname, None) if cname != 'DynamicMesh' else type(dyn)
        if cls is None:
            continue
        # UE snake-cases C++ names and mangles runs of capitals, so GetTriangleUVs can land as
        # get_triangle_u_vs rather than get_triangle_uvs. Scan the class rather than guess.
        cands = [n for n in dir(cls) if 'triangle' in n.lower() and 'uv' in n.lower().replace('_', '')]
        seen_names[cname] = cands[:8]
        if cands:
            pick = sorted(cands, key=len)[0]
            fn = getattr(cls, pick)
            uvfn_name = '%s.%s' % (cname, pick)
            uvfn = (lambda m, s, t, _f=fn: _f(m, s, t)) if cname != 'DynamicMesh' else \
                   (lambda m, s, t, _f=fn: _f(m, s, t))
            break
    row['uvNameScan'] = seen_names
    try:
        if uvfn is not None:
            qcls = getattr(ue, 'GeometryScript_MeshQueries', None)
            if qcls is not None:
                for nm in dir(qcls):
                    if 'uv' in nm.lower().replace('_', '') and 'num' in nm.lower():
                        try:
                            row['uvSets'] = int(unwrap(getattr(qcls, nm)(dyn)))
                            row['uvSetsBinding'] = nm
                        except Exception as exc:
                            row.setdefault('errors', []).append('%s failed: %r' % (nm, exc))
                        break
            for i in range(nt):
                res = uvfn(dyn, 0, i)          # (UV1, UV2, UV3, bHaveValidUVs)
                if res is None:
                    raise RuntimeError('get_triangle_uvs returned nothing')
                trio = list(res)
                corner = []
                for q in trio[:3]:
                    q = unwrap(q)
                    u, vv_ = (q[0], q[1]) if isinstance(q, (tuple, list)) else (q.x, q.y)
                    uvs.append((float(u), float(vv_)))
                    corner.append(len(uvs))
                uv_tris.append(tuple(corner))
            uv_mode = '%s.get_triangle_uvs(mesh, 0, i)' % uvfn_name
    except Exception as exc:
        row.setdefault('errors', []).append('triangle uv read failed: %r' % (exc,))
        uvs, uv_tris, uv_mode = [], [], None
    row['uvBinding'] = uv_mode
    row['uvCount'] = len(uvs)

    for t in uvs:
        lines.append('vt %.6f %.6f' % t)
    if uv_tris and len(uv_tris) == nt:
        for (a, b, c), (ua, ub, uc) in zip(tri_idx, uv_tris):
            lines.append('f %d/%d %d/%d %d/%d' % (a + 1, ua, b + 1, ub, c + 1, uc))
    else:
        for a, b, c in tri_idx:
            lines.append('f %d %d %d' % (a + 1, b + 1, c + 1))
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return nv, nt


def do_preset(sub, name, want_mesh, row):
    src_path = '%s/%s.%s' % (PRESET_ROOT, name, name)
    src = ue.load_asset(src_path)
    if src is None:
        raise RuntimeError('preset did not load: %s' % src_path)
    dst_path = '%s/MH_Cast_%s' % (CAST_ROOT, name)
    if ue.EditorAssetLibrary.does_asset_exist(dst_path):
        ue.EditorAssetLibrary.delete_asset(dst_path)
    dup = ue.EditorAssetLibrary.duplicate_asset(src_path, dst_path)
    if dup is None:
        raise RuntimeError('duplicate_asset returned None for %s' % name)
    row['asset'] = dup.get_path_name()
    if not sub.try_add_object_to_edit(dup):
        raise RuntimeError('try_add_object_to_edit failed for %s' % name)
    try:
        coeffs = [float(c) for c in sub.get_face_model_coefficients(dup)]
        row['coefficientCount'] = len(coeffs)
        with open('%s/coeffs-%s.json' % (OUT, name), 'w') as f:
            f.write(json.dumps({'preset': name, 'coefficients': coeffs}) + '\n')
        row['coefficients'] = 'coeffs-%s.json' % name
        # every preset selects WI_DefaultGarment, a modern T-shirt and shorts
        dup.internal_collection.default_instance.set_single_slot_selection(
            slot_name='Outfits', item_key=ue.MetaHumanPaletteItemKey())
        row['clearedOutfits'] = True
        if want_mesh:
            sub.assemble_for_preview(dup)
            actor = sub.spawn_meta_human_actor(dup, True)
            if actor is None:
                raise RuntimeError('spawn_meta_human_actor returned None')
            comps = []
            for comp in actor.get_components_by_class(ue.SkeletalMeshComponent):
                m = comp.get_editor_property('skeletal_mesh')
                if m:
                    comps.append((str(comp.get_name()), m))
            row['components'] = [c[0] for c in comps]
            face = None
            for cname, m in comps:
                if 'face' in cname.lower() or 'face' in m.get_name().lower():
                    face = m
                    break
            if face is None and comps:
                face = comps[0][1]
            if face is None:
                raise RuntimeError('no skeletal mesh on the spawned actor')
            row['faceMesh'] = face.get_path_name()
            copy_name, copy_fn = find_fn('copy_mesh_from_skeletal_mesh')
            row['copyBinding'] = copy_name
            if copy_fn is None:
                raise RuntimeError('no GeometryScript copy_mesh_from_skeletal_mesh binding found')
            dyn = ue.DynamicMesh()
            opts = ue.GeometryScriptCopyMeshFromAssetOptions()
            lod = ue.GeometryScriptMeshReadLOD()
            lod.lod_index = 0
            res = copy_fn(face, dyn, opts, lod)
            dyn = res[0] if isinstance(res, tuple) else dyn
            if not os.path.isdir(MESH_OUT):
                os.makedirs(MESH_OUT)
            obj = '%s/%s.obj' % (MESH_OUT, name)
            nv, nt = export_obj(dyn, obj, name, row)
            row['objFile'] = 'meshes/%s.obj' % name
            row['vertices'], row['triangles'] = nv, nt
    finally:
        if sub.is_object_added_for_editing(dup):
            sub.remove_object_to_edit(dup)
    return row


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    only = switch_value('-FaceV5CastOnly')
    want_mesh = not switch('-FaceV5CastNoMesh')
    prog = load_progress()
    if only:
        todo = [only]
    else:
        # skip ones that already failed: the caller loops this script once per preset, and a preset
        # that keeps failing would otherwise be retried forever instead of letting the batch finish
        todo = [n for n in SHORTLIST if n not in prog['completed'] and n not in prog['failed']]
    if not switch('-FaceV5CastRun'):
        ue.log('FaceV5 casting PLAN: shortlist=%r remaining=%r wantMesh=%s' % (SHORTLIST, todo, want_mesh))
        return
    if not todo:
        ue.log('FaceV5 casting: nothing left to do')
        return
    name = todo[0]
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    row = {'preset': name, 'utc': stamp, 'wantMesh': want_mesh, 'errors': []}
    sub = ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
    try:
        do_preset(sub, name, want_mesh, row)
        row['status'] = 'done'
        prog['completed'] = sorted(set(prog['completed'] + [name]))
        prog['failed'].pop(name, None)
    except Exception:
        row['status'] = 'failed'
        row['errors'].append(traceback.format_exc())
        prog['failed'][name] = row['errors'][-1][-1200:]
    with open('%s/cast-%s-%s.json' % (OUT, name, stamp), 'w') as f:
        f.write(json.dumps(row, indent=2, default=str) + '\n')
    prog['last'] = row
    save_progress(prog)
    ue.log('FaceV5 casting %s -> %s' % (name, row['status']))


main()
