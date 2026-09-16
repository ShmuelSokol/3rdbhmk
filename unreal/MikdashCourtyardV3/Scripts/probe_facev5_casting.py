"""FaceV5 casting PROBE: what can be read off a MetaHuman preset WITHOUT any cloud call?

Run:
  UnrealEditor.exe <uproject> -ExecutePythonScript=Scripts/probe_facev5_casting.py
      -unattended -nullrhi -NoSplash -NoMetaHumanAccountPortalLoginFallback
      -EnablePlugins=GeometryScripting -abslog=<log>

Why: choosing the Kohen Gadol's face needs the head SHAPE of six presets side by side. A full
build costs two Epic cloud calls per character (auto-rig + texture sources). If AssembleForPreview
plus SpawnMetaHumanActor yields a face SkeletalMesh, the shape can be read for free and the cloud
paid only for the winner. This script decides that question and writes the answer to a receipt.
It changes no map, saves no character, and calls no cloud service.
"""
import json
import time
import traceback

import unreal as ue

OUT = ('C:/Mikdash/Working-5.8/MikdashCourtyardV3/SourceAssets/characters-review/FaceV5/'
       'casting/probe-casting.json')
PRESET_ROOT = '/MetaHumanCharacter/Optional/Presets'
CAST_ROOT = '/Game/MetaHumans/Casting'
SUBJECT = 'Walter'

r = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'subject': SUBJECT,
     'cloudCalled': False, 'steps': [], 'errors': []}


def step(name, **kw):
    kw['step'] = name
    r['steps'].append(kw)
    ue.log('PROBE %s %s' % (name, json.dumps(kw, default=str)[:400]))


def write():
    with open(OUT, 'w') as f:
        f.write(json.dumps(r, indent=2, default=str) + '\n')


try:
    sub = ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
    step('subsystem', ok=sub is not None)

    src_path = '%s/%s.%s' % (PRESET_ROOT, SUBJECT, SUBJECT)
    src = ue.load_asset(src_path)
    step('loadPreset', path=src_path, loaded=src is not None, cls=type(src).__name__ if src else None)
    if src is None:
        raise RuntimeError('preset did not load: %s' % src_path)

    # what does the preset already know, with no cloud?
    step('presetState',
         rigged=str(sub.get_rigging_state(src)) if hasattr(sub, 'get_rigging_state') else 'n/a',
         hasHiRes=bool(src.has_high_resolution_textures),
         canBuild=bool(sub.can_build_meta_human(src, False)))

    dst_path = '%s/MH_Cast_%s' % (CAST_ROOT, SUBJECT)
    if ue.EditorAssetLibrary.does_asset_exist(dst_path):
        ue.EditorAssetLibrary.delete_asset(dst_path)
    dup = ue.EditorAssetLibrary.duplicate_asset(src_path, dst_path)
    step('duplicate', to=dst_path, ok=dup is not None)
    if dup is None:
        raise RuntimeError('duplicate_asset returned None')

    added = sub.try_add_object_to_edit(dup)
    step('tryAddObjectToEdit', ok=bool(added))

    # face model coefficients: the blend lever (Walter -> Lorenzo/Jorge) if this reads back
    try:
        coeffs = sub.get_face_model_coefficients(dup)
        step('getFaceModelCoefficients', count=len(coeffs),
             first8=[round(float(c), 5) for c in list(coeffs)[:8]])
    except Exception as exc:
        step('getFaceModelCoefficients', error=repr(exc))

    # clear the modern T-shirt every preset selects
    try:
        dup.internal_collection.default_instance.set_single_slot_selection(
            slot_name='Outfits', item_key=ue.MetaHumanPaletteItemKey())
        step('clearOutfits', ok=True)
    except Exception as exc:
        step('clearOutfits', error=repr(exc))

    # the question: does a preview assembly exist without the cloud, and does it carry a face mesh?
    try:
        sub.assemble_for_preview(dup)
        step('assembleForPreview', ok=True)
    except Exception as exc:
        step('assembleForPreview', error=repr(exc))

    try:
        coll = sub.get_preview_collection(dup)
        step('getPreviewCollection', ok=coll is not None, cls=type(coll).__name__ if coll else None)
    except Exception as exc:
        step('getPreviewCollection', error=repr(exc))

    actor = None
    try:
        actor = sub.spawn_meta_human_actor(dup, True)
        step('spawnMetaHumanActor', ok=actor is not None, cls=type(actor).__name__ if actor else None)
    except Exception as exc:
        step('spawnMetaHumanActor', error=repr(exc))

    if actor is not None:
        found = []
        for comp in actor.get_components_by_class(ue.SkeletalMeshComponent):
            m = comp.get_editor_property('skeletal_mesh')
            found.append({'component': str(comp.get_name()),
                          'mesh': m.get_path_name() if m else None,
                          'skeleton': (m.get_editor_property('skeleton').get_path_name()
                                       if m and m.get_editor_property('skeleton') else None)})
        step('skeletalMeshComponents', count=len(found), components=found)

        # can GeometryScript read one of them? that is the bake-down path too.
        face = None
        for f in found:
            if f['mesh'] and 'face' in f['mesh'].lower():
                face = f['mesh']
                break
        if face is None and found:
            face = found[0]['mesh']
        step('chosenFaceMesh', mesh=face)
        if face:
            try:
                sm = ue.load_asset(face)
                dm = ue.DynamicMesh()
                opts = ue.GeometryScriptCopyMeshFromAssetOptions()
                lod = ue.GeometryScriptMeshReadLOD()
                lod.lod_index = 0
                dm, _ = ue.GeometryScriptLibrary_StaticMeshFunctions.copy_mesh_from_skeletal_mesh(
                    sm, dm, opts, lod)
                step('copyMeshFromSkeletalMesh', ok=True,
                     vertices=int(dm.get_vertex_count()), triangles=int(dm.get_triangle_count()))
            except Exception as exc:
                step('copyMeshFromSkeletalMesh', error=repr(exc))

    try:
        sub.remove_object_to_edit(dup)
    except Exception:
        pass
    r['status'] = 'probe_complete'
except Exception:
    r['status'] = 'failed'
    r['errors'].append(traceback.format_exc())
finally:
    write()
    ue.log('PROBE wrote %s' % OUT)
