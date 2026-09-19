"""Fresh repaired-mantle Man_Standard VAT candidate; no map or live crowd adoption.

Run in isolated commandlet through run_crowd_near_v2.ps1. Default only verifies
the persisted candidate. -CrowdNearBuild creates assets in a fresh namespace.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
import create_crowd_vat_v2 as vat

NS = '/Game/MikdashV3/Runtime/CrowdNearV2b'
OUT = ROOT / 'SourceAssets/perf-review/crowd-vat/NearV2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk(path):
    return ROOT / ('Content/' + path.split('.')[0].removeprefix('/Game/') + '.uasset')


def mesh_stats(mesh):
    stats = vat._mesh_stats(ue, mesh)
    if 'uvChannels' not in stats:
        # Commandlets have no StaticMeshEditorSubsystem. Read the saved source
        # model through GeometryScript instead; do not drop the UV invariant.
        dynamic = ue.DynamicMesh()
        lod = ue.GeometryScriptMeshReadLOD()
        lod.set_editor_property('lod_type',ue.GeometryScriptLODType.SOURCE_MODEL)
        lod.set_editor_property('lod_index',0)
        result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,dynamic,ue.GeometryScriptCopyMeshFromAssetOptions(),lod)
        assert vat._outcome_ok(ue,result)
        stats['uvChannels'] = int(ue.GeometryScript_MeshQueries.get_num_uv_sets(dynamic))
    return stats


def main():
    build = '-CrowdNearBuild' in ue.SystemLibrary.get_command_line()
    spec = vat.load_spec()
    variant = next(v for v in spec['variants'] if v['short'] == 'Man_Standard')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / ('native-' + stamp + '.json')
    report = dict(status='running', build=build, namespace=NS,
                  scope='One full-source VAT candidate; no map, renderer or crowd adoption')
    protected = list((ROOT / 'Content').rglob('*.umap'))
    protected += list((ROOT / 'Content/MikdashV3/Runtime/CrowdVATV1').rglob('*.uasset'))
    protected += list((ROOT / 'Content/MikdashV3/Runtime/CrowdNearV1').rglob('*.uasset'))
    protected += list((ROOT / 'Content/MikdashV3/Runtime/CrowdNearV2').rglob('*.uasset'))
    protected += [disk(variant[k]) for k in ('skeletalMesh', 'walk', 'idle')]
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    report['protectedBefore'] = before
    def write():
        path.write_text(json.dumps(report, indent=2, default=str) + '\n')
    write()
    try:
        assets = ue.EditorAssetLibrary
        if build:
            if assets.list_assets(NS, True, False):
                raise RuntimeError('Candidate namespace must be fresh')
            source = ROOT / 'SourceAssets/characters-review/CrowdMantleStudy05/V3_Pilgrim_Man_Standard_MantleStudy.glb'
            source_review = json.loads((source.parent/'acceptance01.json').read_text())
            assert sha(source) == source_review['candidateSha256']
            task = ue.AssetImportTask()
            pipeline = ue.InterchangeGenericAssetsPipeline()
            animation = pipeline.get_editor_property('animation_pipeline')
            report['importSampling'] = {}
            for key,value in dict(use30_hz_to_bake_bone_animation=False,custom_bone_animation_sample_rate=60).items():
                animation.set_editor_property(key,value)
                actual = animation.get_editor_property(key)
                assert actual == value
                report['importSampling'][key] = actual
            override = ue.InterchangePipelineStackOverride()
            override.add_pipeline(pipeline)
            for key,value in dict(filename=str(source),destination_path=NS+'/Source',automated=True,
                                  replace_existing=False,save=False,options=override).items():
                task.set_editor_property(key,value)
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            imported = [ue.load_asset(p) for p in assets.list_assets(NS+'/Source',True,False)]
            skeletal = [o for o in imported if isinstance(o,ue.SkeletalMesh)]
            assert len(skeletal) == 1, repr([o.get_path_name() for o in imported if o])
            skel = skeletal[0]
            clips = [o for o in imported if isinstance(o,ue.AnimSequence)]
            walk_clips = [o for o in clips if o.get_name().endswith('_Walk')]
            idle_clips = [o for o in clips if o.get_name().endswith('_Idle')]
            assert len(walk_clips) == len(idle_clips) == 1
            walk,idle = walk_clips[0],idle_clips[0]
            for obj in imported:
                assert obj and obj.get_path_name().startswith(NS+'/Source/')
                assert assets.save_loaded_asset(obj,False)
            report['sourceImport'] = dict(glb=str(source.relative_to(ROOT)),sha256=sha(source),
                                         skeletalMesh=skel.get_path_name(),walk=walk.get_path_name(),idle=idle.get_path_name(),
                                         assets=[o.get_path_name() for o in imported])
            row = report['variant'] = dict(id=variant['id'])
            for key, clip in [('walk', walk), ('idle', idle)]:
                row[key+'Import'] = dict(keys=ue.AnimationLibrary.get_num_keys(clip),
                                         length=ue.AnimationLibrary.get_sequence_length(clip))
                write()
                assert clip.get_editor_property('skeleton') == skel.get_editor_property('skeleton')
                assert ue.AnimationLibrary.get_num_keys(clip) == spec[key]['expectedKeys']
                assert abs(ue.AnimationLibrary.get_sequence_length(clip) - spec[key]['expectedLengthSec']) < .001
            # Target above source count keeps the full source topology.
            mesh = vat._convert(ue, skel, NS + '/Meshes/SM_CrowdNear_Man_Standard', 100000, row)
            assert row['decimation']['dynamicTrianglesBefore'] == row['decimation']['dynamicTrianglesAfter']
            assert ue.AnimToTextureBPLibrary.set_light_map_index(mesh, 0, 0, False)
            tools = ue.AssetToolsHelpers.get_asset_tools()
            textures = {}
            for clip_key in ('Walk', 'Idle'):
                for kind in ('Position', 'Normal'):
                    name = 'T_CrowdNear_Man_Standard_' + clip_key + kind
                    textures[clip_key + kind] = vat._texture(ue, tools, assets, NS + '/Textures', name)
            for key, clip in [('walk', walk), ('idle', idle)]:
                vat._bake_clip(ue, spec, mesh, skel, clip, spec[key], textures[key.title()+'Position'],
                               textures[key.title()+'Normal'], key+'Bake', row, allow_multiple_rows=True)
            settings = report['textureSettings'] = {}
            for tex in textures.values():
                vat._finish_texture(ue, tex, settings)
                assert tex.get_editor_property('address_x') == ue.TextureAddress.TA_WRAP and tex.get_editor_property('address_y') == ue.TextureAddress.TA_WRAP
                assert assets.save_loaded_asset(tex, False)
            defaults = {k+'Texture': v for k, v in textures.items()}
            for key in ('walk', 'idle'):
                defaults[key.title()+'MinBBox'] = row[key+'Bake']['minBBox']
                defaults[key.title()+'SizeBBox'] = row[key+'Bake']['sizeBBox']
            master = vat.build_master_v2(ue, spec, NS, 'M_CrowdNear_V2', defaults, report)
            mi_record = report['materialInstances'] = {}
            slots = []
            for index, slot in enumerate(mesh.get_editor_property('static_materials')):
                name = str(slot.get_editor_property('material_slot_name'))
                key = next(k for k in variant['slots'] if name.lower().startswith(k.lower()))
                s = variant['slots'][key]
                vectors = {k: v for k, v in defaults.items() if k.endswith(('MinBBox', 'SizeBBox'))}
                vectors['BaseColor'] = s['baseColor']
                mi = vat._mi(ue, tools, assets, NS+'/Materials', 'MI_CrowdNear_'+key, master,
                             {k: v for k, v in defaults.items() if k.endswith('Texture')}, vectors,
                             dict(Roughness=s['roughness'], PaletteMix=s['paletteMix'], SkinVariation=s['skinVariation']), mi_record)
                mesh.set_material(index, mi)
                slots.append([index, name, mi.get_path_name()])
            bounds = report['boundsExtensions'] = vat.BOUNDS_EXTENSION_CM
            for key in ('positive','negative'):
                mesh.set_editor_property(key+'_bounds_extension',ue.Vector(*bounds[key]))
                assert vat._v3(mesh.get_editor_property(key+'_bounds_extension')) == list(bounds[key])
            assert assets.save_loaded_asset(mesh, False)
            row.update(mesh=mesh.get_path_name(), textures={k: v.get_path_name() for k,v in textures.items()},
                       stats=mesh_stats(mesh), slots=slots)
            report['assets'] = {str(p.relative_to(ROOT)): sha(p) for p in disk(NS).with_suffix('').rglob('*.uasset')}
            assert report['assets']
            report['status'] = 'built-needs-fresh-readback-and-render'
        else:
            previous = [json.loads(p.read_text()) for p in OUT.glob('native-*.json') if p != path]
            prior = [r for r in previous if r.get('status') == 'built-needs-fresh-readback-and-render']
            assert len(prior) == 1, 'Expected one successful candidate build'
            source = prior[0]
            for p, digest in source['assets'].items():
                assert sha(ROOT/p) == digest, 'Candidate changed: '+p
                assert ue.load_asset('/Game/'+str(Path(p).relative_to('Content').with_suffix('')).replace('\\','/'))
            row = source['variant']; mesh = ue.load_asset(row['mesh'])
            ue.AutomationLibrary.finish_loading_before_screenshot()
            report['statsReadback'] = mesh_stats(mesh)
            report['statsExpected'] = row['stats']
            write()
            assert report['statsReadback'] == row['stats']
            for key in ('positive','negative'):
                assert vat._v3(mesh.get_editor_property(key+'_bounds_extension')) == source['boundsExtensions'][key]
            report['sourceImport'] = source['sourceImport']
            report['boundsExtensions'] = source['boundsExtensions']
            for i, _, mi in row['slots']:
                assert mesh.get_material(i).get_path_name() == mi
            for key, tex_path in row['textures'].items():
                tex = ue.load_asset(tex_path); layout = row['walkBake' if key.startswith('Walk') else 'idleBake']
                assert tex.blueprint_get_size_x() == layout['width'] and tex.blueprint_get_size_y() == layout['height']
                assert not tex.get_editor_property('srgb') and tex.get_editor_property('never_stream') and tex.get_editor_property('filter') == ue.TextureFilter.TF_NEAREST
                assert tex.get_editor_property('mip_gen_settings') == ue.TextureMipGenSettings.TMGS_NO_MIPMAPS
                assert tex.get_editor_property('address_x') == ue.TextureAddress.TA_WRAP and tex.get_editor_property('address_y') == ue.TextureAddress.TA_WRAP
            report.update(variant=row, assets=source['assets'], status='verified-fresh-candidate-not-rendered')
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
        raise
    finally:
        ue.AutomationLibrary.finish_loading_before_screenshot()
        report['protectedAfter'] = {str(p.relative_to(ROOT)): sha(p) for p in protected}
        if report['protectedAfter'] != before:
            report['status'] = 'failed-protected-assets-changed'
        write()
        # The commandlet exits after this script; do not initialize/tear down editor UI.


if __name__ == '__main__':
    main()
