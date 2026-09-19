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

match = re.search(r'-ResidentCrowdStudy=(01|02|03|04|05|06|07|08|09)\b', ue.SystemLibrary.get_command_line())
STUDY = match.group(1) if match else '03'
NS = '/Game/MikdashV3/Runtime/CrowdResidentStudy'+STUDY
OUT = ROOT/('SourceAssets/perf-review/crowd-vat/ResidentStudy'+STUDY)
variant_match=re.search(r'-ResidentCrowdVariant=(\w+)',ue.SystemLibrary.get_command_line())
VARIANT=variant_match.group(1) if variant_match else 'Man_Standard'
assert VARIANT in ('Man_Standard','Man_Heavy','Man_Elder','Woman_Young','Woman_Elder','Youth')
if VARIANT!='Man_Standard':
    NS+='/Cast/'+VARIANT
    OUT=OUT/'Cast'/VARIANT
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
    if STUDY in ('03','04','05','06','07','08','09'):
        # Reconstruct the tangent frame from the deformed position and UV0 in
        # the pixel shader; a rest-pose tangent would not follow VAT animation.
        M,A=ue.MaterialExpressionMultiply,ue.MaterialExpressionAdd
        cross=ue.MaterialExpressionCrossProduct
        dot=ue.MaterialExpressionDotProduct
        normal=g.unary(ue.MaterialExpressionNormalize,ml.get_material_property_input_node(master,mp.MP_NORMAL))
        position=g.make(ue.MaterialExpressionWorldPosition)
        uv0=g.make(ue.MaterialExpressionTextureCoordinate,coordinate_index=0)
        dp1=g.unary(ue.MaterialExpressionDDX,position)
        dp2=g.unary(ue.MaterialExpressionDDY,position)
        duv1=g.unary(ue.MaterialExpressionDDX,uv0)
        duv2=g.unary(ue.MaterialExpressionDDY,uv0)
        p2=g.op(cross,dp2,normal);p1=g.op(cross,normal,dp1)
        tangent=g.op(A,g.op(M,p2,g.mask(duv1,'r')),g.op(M,p1,g.mask(duv2,'r')))
        bitangent=g.op(A,g.op(M,p2,g.mask(duv1,'g')),g.op(M,p1,g.mask(duv2,'g')))
        length2=g.op(ue.MaterialExpressionMax,g.op(dot,tangent,tangent),g.op(dot,bitangent,bitangent))
        scale=g.op(ue.MaterialExpressionDivide,g.const(1.),g.unary(ue.MaterialExpressionSquareRoot,
                   g.op(ue.MaterialExpressionMax,length2,g.const(1e-12))))
        detail=g.make(ue.MaterialExpressionTextureSampleParameter2D)
        detail.set_editor_property('parameter_name','DetailNormal')
        detail.set_editor_property('texture',ue.load_asset(resident.TEX_FOLDER+'/T_RV4_WeaveN'))
        detail.set_editor_property('sampler_type',ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        g.link(g.op(M,uv0,g.scalar('DetailTiling',10.,0,0)),detail,['UVs'])
        n=g.lerp(g.const3([0,0,1]),(detail,'RGB'),g.scalar('DetailStrength',.6,0,0))
        world=g.op(A,g.op(M,g.op(A,g.op(M,tangent,g.mask(n,'r')),g.op(M,bitangent,g.mask(n,'g'))),scale),
                   g.op(M,normal,g.mask(n,'b')))
        g.prop(g.unary(ue.MaterialExpressionNormalize,world),mp.MP_NORMAL)
        g.prop(g.mask(g.vector('SubsurfaceColor',[.62,.20,.11],0,0),'rgb'),mp.MP_SUBSURFACE_COLOR)
        g.prop(g.scalar('SubsurfaceAmount',.38,0,0),mp.MP_OPACITY)
    assert ml.get_material_property_input_node(master, mp.MP_BASE_COLOR) == final
    assert not any(isinstance(n, ue.MaterialExpressionCustom) for n in ml.get_material_expressions(master))
    ml.recompile_material(master)
    assert ue.EditorAssetLibrary.save_loaded_asset(master, False)
    report['residentSurface'] = dict(linearVertexColor=STUDY!='01', uvChannel=0, mottle=True,
                                    derivativeNormalDetail=STUDY in ('03','04','05','06','07','08','09'),skinSubsurface=STUDY in ('03','04','05','06','07','08','09'),
                                    limitations=['Visual pilot, not runtime acceptance'])


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


def surface_readback(material):
    ml=ue.MaterialEditingLibrary
    mp=ue.MaterialProperty
    def upstream(prop):
        root=ml.get_material_property_input_node(material,prop)
        assert root
        pending=[root];nodes={}
        while pending:
            node=pending.pop()
            if node.get_path_name() in nodes:continue
            nodes[node.get_path_name()]=node
            pending.extend(n for n in ml.get_inputs_for_material_expression(material,node) if n)
        return root,list(nodes.values())
    root,nodes=upstream(mp.MP_NORMAL)
    assert isinstance(root,ue.MaterialExpressionNormalize)
    counts={}
    for node in nodes:
        key=node.get_class().get_name();counts[key]=counts.get(key,0)+1
    assert counts.get('MaterialExpressionDDX')==2 and counts.get('MaterialExpressionDDY')==2
    world=[n for n in nodes if isinstance(n,ue.MaterialExpressionWorldPosition)]
    assert len(world)==1
    assert world[0].get_editor_property('world_position_shader_offset')==ue.WorldPositionIncludedOffsets.WPT_DEFAULT
    detail=[n for n in nodes if isinstance(n,ue.MaterialExpressionTextureSampleParameter2D)
            and str(n.get_editor_property('parameter_name'))=='DetailNormal']
    assert len(detail)==1 and detail[0].get_editor_property('sampler_type')==ue.MaterialSamplerType.SAMPLERTYPE_NORMAL
    assert counts.get('MaterialExpressionVertexInterpolator',0)>=1
    _,base=upstream(mp.MP_BASE_COLOR)
    assert any(isinstance(n,ue.MaterialExpressionVertexColor) for n in base)
    opacity,_=upstream(mp.MP_OPACITY)
    assert isinstance(opacity,ue.MaterialExpressionScalarParameter)
    assert str(opacity.get_editor_property('parameter_name'))=='SubsurfaceAmount'
    assert abs(opacity.get_editor_property('default_value')-.38)<1e-6
    _,subsurface=upstream(mp.MP_SUBSURFACE_COLOR)
    tint=[n for n in subsurface if isinstance(n,ue.MaterialExpressionVectorParameter)]
    assert len(tint)==1 and str(tint[0].get_editor_property('parameter_name'))=='SubsurfaceColor'
    value=tint[0].get_editor_property('default_value')
    assert all(abs(a-b)<1e-6 for a,b in zip((value.r,value.g,value.b),(.62,.20,.11)))
    assert not material.get_editor_property('tangent_space_normal')
    assert material.get_editor_property('used_with_instanced_static_meshes')
    return dict(normalConnectedNodes=counts, worldPositionIncludesWPO=True,
                detailNormalConnected=True, vertexColorConnected=True, subsurfaceConnected=True)


def run():
    build = '-ResidentCrowdBuild' in ue.SystemLibrary.get_command_line()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = OUT/('native-'+stamp+'.json')
    report = dict(status='running', namespace=NS, castVariant=VARIANT, variants=[],
                  scope='Full source topology VAT diagnostic; no scene adoption' if STUDY=='09'
                        else '8000/2400-triangle crowd candidates; no scene adoption')
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
            if STUDY=='05':
                spec['mesh']['numDriverTriangles']=1
            report['numDriverTriangles']=spec['mesh']['numDriverTriangles']
            variant = next(v for v in spec['variants'] if v['short']==VARIANT)
            skel = ue.load_asset('/Game/MikdashV3/Characters/ResidentV4/'+VARIANT+'/SK_RV4_'+VARIANT)
            assert skel
            report['sourceMeshSha256'] = sha(disk(skel.get_path_name()))
            report['sourceMesh'] = skel.get_path_name()
            clips = {k:ue.load_asset(variant[k]) for k in ('walk','idle')}
            for key, clip in clips.items():
                assert clip and clip.get_editor_property('skeleton') == skel.get_editor_property('skeleton')
                assert ue.AnimationLibrary.get_num_keys(clip) == spec[key]['expectedKeys']
            report['clips'] = {k:v.get_path_name() for k,v in clips.items()}
            tools = ue.AssetToolsHelpers.get_asset_tools()
            for target in ((None,) if STUDY=='09' else (8000,2400)):
                row = dict(target='full-source' if target is None else target)
                report['variants'].append(row)
                label = 'ResidentSourceTopology' if target is None else 'Resident'+str(target)
                ns = NS+'/'+label
                budgets = None
                if STUDY == '08':
                    values = (2200,200,500,3600,1200,300) if target == 8000 else (800,80,160,960,280,120)
                    budgets = dict(zip(('RV4_Skin','RV4_Eye','RV4_Hair','RV4_Cloth','RV4_Garment','RV4_Leather'),values))
                mesh = vat._convert(ue, skel, ns+'/SM_'+label, target, row, linear_source_colors=STUDY!='01',
                                    preserve_vertex_positions=STUDY in ('04','05','07'),
                                    resident_attribute_metric=STUDY in ('06','07'),resident_material_budgets=budgets,
                                    preserve_source_topology=STUDY=='09')
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
                skin_master=master
                if STUDY in ('03','04','05','06','07','08','09'):
                    skin_master=assets.duplicate_asset(master.get_path_name(),ns+'/Materials/M_ResidentVAT_Skin')
                    assert isinstance(skin_master,ue.Material)
                    skin_master.set_editor_property('shading_model',ue.MaterialShadingModel.MSM_SUBSURFACE)
                    ue.MaterialEditingLibrary.recompile_material(skin_master)
                    assert assets.save_loaded_asset(skin_master,False)
                    row['skinMaster']=skin_master.get_path_name()
                bindings=[]
                row['materialInstances']={}
                for i,slot in enumerate(mesh.static_materials):
                    name=str(slot.material_slot_name)
                    kind,rough,specular,params=resident.SLOT_MI[name]
                    vectors={k:v for k,v in defaults.items() if k.endswith(('MinBBox','SizeBBox'))}
                    vectors['BaseColor']=resident.DEFAULT_GARMENT_TINT if name=='RV4_Garment' else [1,1,1]
                    tex_params={k:v for k,v in defaults.items() if k.endswith('Texture')}
                    scalars=dict(Roughness=rough,Specular=specular,PaletteMix=0.,SkinVariation=0.,
                                 MottleTiling=params['MottleTiling'],MottleStrength=params['MottleStrength'])
                    if STUDY in ('03','04','05','06','07','08','09'):
                        prefix='Pore' if kind=='skin' else 'Weave'
                        tex_params['DetailNormal']=ue.load_asset(resident.TEX_FOLDER+'/'+params['Pores' if kind=='skin' else 'WeaveNormal'])
                        scalars.update(DetailTiling=params[prefix+'Tiling'],DetailStrength=params[prefix+'Strength'])
                    mi=vat._mi(ue,tools,assets,ns+'/Materials','MI_'+name,skin_master if kind=='skin' else master,
                               tex_params,vectors,scalars,row['materialInstances'])
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
            report['surfaceReadback']={}
            for row in source['variants']:
                mesh=ue.load_asset(row['mesh'])
                assert mesh_stats(mesh)==row['stats']
                report['colorReadback'][str(row['target'])]=color_readback(mesh)
                for key in ('positive','negative'):
                    assert vat._v3(mesh.get_editor_property(key+'_bounds_extension'))==list(vat.BOUNDS_EXTENSION_CM[key])
                for i,_,path in row['slots']:
                    assert mesh.get_material(i).get_path_name()==path
                if STUDY in ('03','04','05','06','07','08','09'):
                    skin=ue.load_asset(row['skinMaster'])
                    assert skin.get_editor_property('shading_model')==ue.MaterialShadingModel.MSM_SUBSURFACE
                    ml=ue.MaterialEditingLibrary
                    for i,name,path in row['slots']:
                        mi=mesh.get_material(i)
                        parent=mi.get_editor_property('parent')
                        if parent.get_path_name() not in report['surfaceReadback']:
                            report['surfaceReadback'][parent.get_path_name()]=surface_readback(parent)
                        if name=='RV4_Skin':assert mi.get_editor_property('parent')==skin
                        expected=row['materialInstances'][mi.get_name()]
                        for key,value in expected.items():
                            if isinstance(value,str):
                                actual=ml.get_material_instance_texture_parameter_value(mi,key)
                                assert actual and actual.get_path_name()==value
                            elif isinstance(value,list):
                                actual=ml.get_material_instance_vector_parameter_value(mi,key)
                                assert all(abs(a-b)<1e-5 for a,b in zip((actual.r,actual.g,actual.b),value))
                            else:
                                assert abs(ml.get_material_instance_scalar_parameter_value(mi,key)-value)<1e-5
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
