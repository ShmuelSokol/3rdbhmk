"""ResidentV4 instanced crowd pilot: two detail levels, no runtime adoption."""
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import sys
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Scripts'))
import create_crowd_vat_v2 as vat
import release_resident_v4 as resident
from build_crowd_near_v2 import mesh_stats

match = re.search(r'-ResidentCrowdStudy=(01|02)\b', ue.SystemLibrary.get_command_line())
STUDY = match.group(1) if match else '02'
NS = '/Game/MikdashV3/Runtime/CrowdResidentStudy'+STUDY
OUT = ROOT/('SourceAssets/perf-review/crowd-vat/ResidentStudy'+STUDY)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
disk = lambda p: ROOT/('Content/'+p.split('.')[0].removeprefix('/Game/')+'.uasset')


def surface(master, report):
    """Use linear source colors and UV0 mottle with the existing VAT deformation."""
    ml = ue.MaterialEditingLibrary
    g = vat.StockGraph(ue, master, report)
    mp = ue.MaterialProperty
    base = ml.get_material_property_input_node(master, mp.MP_BASE_COLOR)
    rough = ml.get_material_property_input_node(master, mp.MP_ROUGHNESS)
    assert base and rough
    vc = g.mask(g.make(ue.MaterialExpressionVertexColor), 'rgb')
    uv = g.make(ue.MaterialExpressionTextureCoordinate, coordinate_index=0)
    uv = g.op(ue.MaterialExpressionMultiply, uv, g.scalar('MottleTiling', .5, 0, 0))
    tex = g.make(ue.MaterialExpressionTextureSampleParameter2D)
    tex.set_editor_property('parameter_name', 'Mottle')
    tex.set_editor_property('texture', ue.load_asset(resident.TEX_FOLDER+'/T_RV4_SlubMottle'))
    tex.set_editor_property('sampler_type', ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    g.link(uv, tex, ['UVs'])
    centered = g.op(ue.MaterialExpressionSubtract, (tex,'R'), g.const(.5))
    mottle = g.op(ue.MaterialExpressionAdd, g.const(1.),
                  g.op(ue.MaterialExpressionMultiply, centered,
                       g.op(ue.MaterialExpressionMultiply, g.const(2.), g.scalar('MottleStrength', .3, 0, 0))))
    final = g.op(ue.MaterialExpressionMultiply, g.op(ue.MaterialExpressionMultiply, base, vc), mottle)
    g.prop(final, mp.MP_BASE_COLOR)
    g.prop(g.op(ue.MaterialExpressionAdd, rough, g.op(ue.MaterialExpressionMultiply, centered, g.const(.15))), mp.MP_ROUGHNESS)
    assert ml.get_material_property_input_node(master, mp.MP_BASE_COLOR) == final
    assert not any(isinstance(n, ue.MaterialExpressionCustom) for n in ml.get_material_expressions(master))
    ml.recompile_material(master)
    assert ue.EditorAssetLibrary.save_loaded_asset(master, False)
    report['residentSurface'] = dict(linearVertexColor=True, uvChannel=0, mottle=True,
                                    limitations=['No pore/weave normal detail or skin subsurface yet; visual pilot only'])


def color_readback(mesh):
    dynamic = ue.DynamicMesh()
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh, dynamic, ue.GeometryScriptCopyMeshFromAssetOptions(), lod)
    assert vat._outcome_ok(ue, result)
    colors = set()
    for tid in range(dynamic.get_triangle_count()):
        result = ue.GeometryScript_MeshQueries.get_triangle_vertex_colors(dynamic, tid)
        rgb = [(float(c.r), float(c.g), float(c.b)) for c in result if isinstance(c, ue.LinearColor)]
        assert True in result and len(rgb)==3, 'Missing triangle vertex colors'
        colors.update(rgb)
    assert len(colors)>20, 'Resident color variation lost'
    return dict(uniqueRGB=len(colors), minimum=[min(c[i] for c in colors) for i in range(3)],
                maximum=[max(c[i] for c in colors) for i in range(3)], triangles=dynamic.get_triangle_count())


def run():
    build = '-ResidentCrowdBuild' in ue.SystemLibrary.get_command_line()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = OUT/('native-'+stamp+'.json')
    report = dict(status='running', namespace=NS, variants=[], scope='Man_Standard 8000/2400-triangle crowd candidates; no scene adoption')
    protected = list((ROOT/'Content').rglob('*.umap'))
    for folder in ('Characters/ResidentV4','Characters/PilgrimRigV3','Runtime/CrowdVATV1'):
        protected += list((ROOT/'Content/MikdashV3'/folder).rglob('*.uasset'))
    before = {str(p.relative_to(ROOT)):sha(p) for p in protected}
    report['protectedBefore'] = before
    write = lambda: receipt.write_text(json.dumps(report, indent=2, default=str)+'\n')
    try:
        assets = ue.EditorAssetLibrary
        if build:
            assert not assets.list_assets(NS, True, False), 'Fresh namespace required'
            spec = vat.load_spec()
            variant = next(v for v in spec['variants'] if v['short']=='Man_Standard')
            skel = ue.load_asset('/Game/MikdashV3/Characters/ResidentV4/Man_Standard/SK_RV4_Man_Standard')
            assert skel
            report['sourceMeshSha256'] = sha(disk(skel.get_path_name()))
            report['sourceMesh'] = skel.get_path_name()
            clips = {k:ue.load_asset(variant[k]) for k in ('walk','idle')}
            for key, clip in clips.items():
                assert clip and clip.get_editor_property('skeleton') == skel.get_editor_property('skeleton')
                assert ue.AnimationLibrary.get_num_keys(clip) == spec[key]['expectedKeys']
            report['clips'] = {k:v.get_path_name() for k,v in clips.items()}
            tools = ue.AssetToolsHelpers.get_asset_tools()
            for target in (8000,2400):
                row = dict(target=target)
                report['variants'].append(row)
                label = 'Resident'+str(target)
                ns = NS+'/'+label
                mesh = vat._convert(ue, skel, ns+'/SM_'+label, target, row, linear_source_colors=STUDY=='02')
                assert ue.AnimToTextureBPLibrary.set_light_map_index(mesh,0,0,False)
                textures = {key+kind:vat._texture(ue,tools,assets,ns+'/Textures','T_'+key+kind)
                            for key in ('Walk','Idle') for kind in ('Position','Normal')}
                for key, clip in clips.items():
                    vat._bake_clip(ue,spec,mesh,skel,clip,spec[key],textures[key.title()+'Position'],
                                   textures[key.title()+'Normal'],key+'Bake',row,allow_multiple_rows=True)
                settings = row['textureSettings'] = {}
                for tex in textures.values():
                    vat._finish_texture(ue,tex,settings)
                    assert assets.save_loaded_asset(tex,False)
                defaults = {k+'Texture':v for k,v in textures.items()}
                for key in clips:
                    defaults[key.title()+'MinBBox']=row[key+'Bake']['minBBox']
                    defaults[key.title()+'SizeBBox']=row[key+'Bake']['sizeBBox']
                master = vat.build_master_v2(ue,spec,ns,'M_ResidentVAT',defaults,row)
                surface(master,row)
                bindings=[]
                row['materialInstances']={}
                for i,slot in enumerate(mesh.static_materials):
                    name=str(slot.material_slot_name)
                    kind,rough,specular,params=resident.SLOT_MI[name]
                    vectors={k:v for k,v in defaults.items() if k.endswith(('MinBBox','SizeBBox'))}
                    vectors['BaseColor']=resident.DEFAULT_GARMENT_TINT if name=='RV4_Garment' else [1,1,1]
                    mi=vat._mi(ue,tools,assets,ns+'/Materials','MI_'+name,master,
                               {k:v for k,v in defaults.items() if k.endswith('Texture')},vectors,
                               dict(Roughness=rough,Specular=specular,PaletteMix=0.,SkinVariation=0.,
                                    MottleTiling=params['MottleTiling'],MottleStrength=params['MottleStrength']),row['materialInstances'])
                    mesh.set_material(i,mi)
                    bindings.append([i,name,mi.get_path_name()])
                assert len(bindings)==6
                for key in ('positive','negative'):
                    mesh.set_editor_property(key+'_bounds_extension',ue.Vector(*vat.BOUNDS_EXTENSION_CM[key]))
                assert assets.save_loaded_asset(mesh,False)
                row.update(mesh=mesh.get_path_name(),slots=bindings,stats=mesh_stats(mesh),
                           textures={k:v.get_path_name() for k,v in textures.items()})
                write()
            report['assets']={str(p.relative_to(ROOT)):sha(p) for p in disk(NS).with_suffix('').rglob('*.uasset')}
            report['status']='built-needs-fresh-readback-and-render'
        else:
            prior=[json.loads(p.read_text()) for p in OUT.glob('native-*.json') if p!=receipt]
            built=[r for r in prior if r['status']=='built-needs-fresh-readback-and-render']
            assert len(built)==1
            source=built[0]
            for p,digest in source['assets'].items():
                assert sha(ROOT/p)==digest
                assert ue.load_asset('/Game/'+str(Path(p).relative_to('Content').with_suffix('')).replace('\\','/'))
            report['colorReadback']={}
            for row in source['variants']:
                mesh=ue.load_asset(row['mesh'])
                assert mesh_stats(mesh)==row['stats']
                report['colorReadback'][str(row['target'])]=color_readback(mesh)
                for key in ('positive','negative'):
                    assert vat._v3(mesh.get_editor_property(key+'_bounds_extension'))==list(vat.BOUNDS_EXTENSION_CM[key])
                for i,_,path in row['slots']:
                    assert mesh.get_material(i).get_path_name()==path
                for key,path in row['textures'].items():
                    texture=ue.load_asset(path)
                    layout=row['walkBake' if key.startswith('Walk') else 'idleBake']
                    assert texture.blueprint_get_size_x()==layout['width'] and texture.blueprint_get_size_y()==layout['height']
                    assert not texture.get_editor_property('srgb') and texture.get_editor_property('never_stream')
                    assert texture.get_editor_property('filter')==ue.TextureFilter.TF_NEAREST
                    assert texture.get_editor_property('mip_gen_settings')==ue.TextureMipGenSettings.TMGS_NO_MIPMAPS
                    assert texture.get_editor_property('address_x')==texture.get_editor_property('address_y')==ue.TextureAddress.TA_WRAP
            report.update(variants=source['variants'],assets=source['assets'],status='verified-fresh-candidate-not-rendered')
    except Exception as error:
        report.update(status='failed',error=repr(error))
        raise
    finally:
        report['protectedUnchanged']=before=={str(p.relative_to(ROOT)):sha(p) for p in protected}
        if not report['protectedUnchanged']:report['status']='failed-protected-changed'
        write()


if __name__=='__main__':run()
