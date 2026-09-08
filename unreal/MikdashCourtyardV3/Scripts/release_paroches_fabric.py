"""Explicit opt-in material-only paroches adoption. No engine action on import."""
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'SourceAssets/sanctuary-detail/ParochesFabricV9'
DEST = '/Game/MikdashV3/MaterialReview/ParochesFabricV9'
MESHES = ['/Game/MikdashV3/MaterialReview/DoorsParochesV1/Meshes/SM_Paroches' + n + 'V1' for n in ('Cloth','Hem')]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def helper(filename):
    spec = importlib.util.spec_from_file_location('fabric_' + filename, ROOT / 'Scripts' / (filename + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preflight():
    frozen = json.loads((FOLDER / 'source-receipt.json').read_text(encoding='utf-8-sig'))
    paths = [FOLDER / 'third-temple-single-keruv-v9.png']
    for p in paths:
        if p.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Expected PNG: ' + str(p))
        if sha(p) != frozen['files'][p.name]['sha256']:
            raise ValueError('Frozen artwork hash mismatch: ' + str(p))
    return dict(status='SOURCE_READY_NATIVE_VISUAL_PENDING', sources={p.name:sha(p) for p in paths},
                integrationState=frozen.get('integrationState'), sourceReceiptSha256=sha(FOLDER/'source-receipt.json'),
                namespace=DEST, exactMeshes=MESHES, uv='float2((P.x+180)/360,1-P.z/306)',
                interpretation='User-selected artistic synthesis: one keruv between two palms, raised wings and shared-head human/lion faces; not exact Yechezkel')


def graph_snapshot(u, material):
    ml=u.MaterialEditingLibrary
    expressions=list(ml.get_material_expressions(material))
    rows={}
    for expression in expressions:
        row={'class':expression.get_class().get_name(),
             'inputs':[n.get_name() if n else None for n in ml.get_inputs_for_material_expression(material,expression)]}
        property_names={'code':'Code','output_type':'OutputType','parameter_name':'ParameterName',
                        'default_value':'DefaultValue','r':'R','transform_source_type':'TransformSourceType',
                        'transform_type':'TransformType','sampler_type':'SamplerType'}
        for key, raw_name in property_names.items():
            try:
                value=expression.get_editor_property(raw_name)
                row[key]=value if isinstance(value,(float,int,str,bool)) else str(value)
            except Exception:pass
        if isinstance(expression,u.MaterialExpressionTextureSample):
            texture=expression.get_editor_property('texture')
            row['texture']={'path':texture.get_path_name(),'srgb':texture.get_editor_property('srgb'),
                            'address_x':str(texture.get_editor_property('address_x')),
                            'address_y':str(texture.get_editor_property('address_y'))}
        rows[expression.get_name()]=row
    outputs={}
    for key in ('MP_BASE_COLOR','MP_ROUGHNESS','MP_METALLIC'):
        node=ml.get_material_property_input_node(material,getattr(u.MaterialProperty,key))
        if node is None:raise RuntimeError('Missing material output '+key)
        outputs[key]=node.get_name()
    if any(r.get('parameter_name')=='ServiceAmount' for r in rows.values()):
        raise RuntimeError('V9 must not contain a service tint parameter')
    if abs(rows[outputs['MP_ROUGHNESS']].get('r',-1)-.9)>1e-6 or rows[outputs['MP_METALLIC']].get('r')!=0.0:
        raise RuntimeError('Linked roughness/metal constants mismatch')
    samples=[r for r in rows.values() if 'texture' in r]
    expected_textures={DEST+'/T_BaseColor.T_BaseColor':True}
    if len(samples)!=1 or {r['texture']['path']:r['texture']['srgb'] for r in samples}!=expected_textures:
        raise RuntimeError('Texture path/sRGB readback mismatch')
    for row in samples:
        if not row['inputs'] or any(row['texture'][k]!=str(u.TextureAddress.TA_CLAMP) for k in ('address_x','address_y')):
            raise RuntimeError('Texture UV link/clamp mismatch')
    codes={r.get('code') for r in rows.values() if 'code' in r}
    if codes!={'return float2((P.x+180.0)/360.0,1.0-P.z/306.0);'}:
        raise RuntimeError('Custom mapping code mismatch')
    if rows[outputs['MP_BASE_COLOR']]!=samples[0]:
        raise RuntimeError('Base texture must connect directly to base color')
    return {'expressions':rows,'outputs':outputs,'two_sided':material.get_editor_property('two_sided'),
            'nanite':ml.has_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE)}


def run(apply=False):
    report = preflight()
    if not apply:
        return report
    if json.loads((FOLDER / 'source-receipt.json').read_text(encoding='utf-8-sig')).get('integrationState') != 'READY_FOR_NATIVE_REVIEW':
        raise RuntimeError('Artwork revision is on hold; refusing superseded design')
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Live/dirty world; refuse before load')
    units=helper('release_amah48_candidate'); protected=units.offline_plan()
    target=protected['source']; mapfile=units.disk(target)
    for folder in ('__ExternalActors__','__ExternalObjects__'):
        if (ROOT/'Content'/folder/target[6:]).exists():
            raise RuntimeError('External actor/object folders require expanded checkpoint support')
    if editor.get_editor_world().get_path_name().split('.')[0] != target:
        raise RuntimeError('Main must already be loaded')
    if u.EditorAssetLibrary.does_directory_exist(DEST):
        raise RuntimeError('Fresh namespace required; refusing existing assets')
    h=helper('release_resident_crowd'); baseline=h._scene_snapshot(u,actors)
    selected=[]; hashes={}
    for actor in actors.get_all_level_actors():
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if h._path(mesh) in MESHES:
                selected.append((actor,c))
                for asset in [mesh]+[c.get_material(i) for i in range(c.get_num_materials())]:
                    if asset and h._path(asset).startswith('/Game/'):
                        path=ROOT/'Content'/(h._path(asset)[6:]+'.uasset'); hashes[str(path)]=sha(path)
    if len(selected)!=2 or {h._path(c.get_editor_property('static_mesh')) for _,c in selected}!=set(MESHES):
        raise RuntimeError('Need exactly cloth and hem components')
    selected_names=[a.get_name() for a,_ in selected]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('ParochesFabric-'+stamp)
    checkpoint.mkdir(parents=True,exist_ok=False)
    shutil.copy2(mapfile,checkpoint/'Main.umap')
    if sha(checkpoint/'Main.umap')!=protected['sourceSha256']:raise RuntimeError('Checkpoint mismatch')
    report.update(status='STARTED',main=target,mainSha256Before=protected['sourceSha256'],checkpoint=str(checkpoint),protectedAssets=hashes)
    receipt=FOLDER/('native-'+stamp+'.json')
    def write():receipt.write_text(json.dumps(report,indent=2),encoding='utf8')
    write()
    try:
        fresh=preflight()
        if units.offline_plan()!=protected or any(fresh[k]!=report[k] for k in ('sources','integrationState','sourceReceiptSha256')) or fresh['integrationState']!='READY_FOR_NATIVE_REVIEW':
            raise RuntimeError('Inputs/main changed before mutation')
        textures=[]
        for index,name in enumerate(report['sources']):
            task=u.AssetImportTask(); task.filename=str(FOLDER/name); task.destination_path=DEST
            task.destination_name='T_BaseColor'; task.automated=True
            task.replace_existing=False; task.save=False
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            imported=task.get_objects()
            if len(imported)!=1 or not isinstance(imported[0],u.Texture2D):raise RuntimeError('Texture import failed')
            texture=imported[0]; texture.set_editor_property('srgb',index==0)
            texture.set_editor_property('address_x',u.TextureAddress.TA_CLAMP); texture.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
            textures.append(texture)
        material=u.AssetToolsHelpers.get_asset_tools().create_asset('M_ParochesFabric',DEST,u.Material,u.MaterialFactoryNew())
        material.set_editor_property('two_sided',True)
        ml=u.MaterialEditingLibrary
        def node(cls):return ml.create_material_expression(material,cls)
        def wire(a,b,p):
            if not ml.connect_material_expressions(a,'',b,p):raise RuntimeError('Wire failed: '+p)
        def custom(code,names,kind):
            n=node(u.MaterialExpressionCustom)
            n.set_editor_property('Code',code); n.set_editor_property('OutputType',kind)
            inputs=[]
            for name in names:
                item=u.CustomInput();item.set_editor_property('InputName',name);inputs.append(item)
            n.set_editor_property('Inputs',inputs);return n
        world=node(u.MaterialExpressionWorldPosition);local=node(u.MaterialExpressionTransformPosition)
        local.set_editor_property('TransformSourceType',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
        local.set_editor_property('TransformType',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        wire(world,local,'')
        uv=custom('return float2((P.x+180.0)/360.0,1.0-P.z/306.0);',['P'],u.CustomMaterialOutputType.CMOT_FLOAT2);wire(local,uv,'P')
        samples=[]
        for texture in textures:
            n=node(u.MaterialExpressionTextureSample);n.set_editor_property('Texture',texture);wire(uv,n,'UVs');samples.append(n)
        rough=node(u.MaterialExpressionConstant);rough.set_editor_property('R',.9)
        metal=node(u.MaterialExpressionConstant);metal.set_editor_property('R',0.0)
        for n,p in ((samples[0],u.MaterialProperty.MP_BASE_COLOR),(rough,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)):
            if not ml.connect_material_property(n,'',p):raise RuntimeError('Output wire failed')
        ml.set_base_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE,True)
        ml.recompile_material(material)
        for asset in textures+[material]:
            if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed')
        graph_before=graph_snapshot(u,material)
        report['savedGraphBeforeReopen']=graph_before
        for actor,c in selected:
            actor.modify(True);c.modify(True)
            for i in range(c.get_num_materials()):c.set_material(i,material)
        expected=h._scene_snapshot(u,actors)
        normalized=json.loads(json.dumps(expected))
        for actor,_ in selected:
            name=actor.get_name()
            for before,after in zip(baseline[name]['components'],normalized[name]['components']):
                if 'materials' in after:after['materials']=before['materials']
        if normalized!=baseline:raise RuntimeError('Unexpected scene change beyond selected materials')
        if not levels.save_current_level() or not levels.load_level(target):raise RuntimeError('Save/reopen failed')
        if editor.get_editor_world().get_path_name().split('.')[0]!=target or h._scene_snapshot(u,actors)!=expected:raise RuntimeError('Scene readback mismatch')
        material=u.EditorAssetLibrary.load_asset(DEST+'/M_ParochesFabric')
        graph_after=graph_snapshot(u,material)
        report['savedGraphAfterReopen']=graph_after
        if graph_after!=graph_before:raise RuntimeError('Saved material graph changed after reopen')
        if not material.get_editor_property('two_sided') or not ml.has_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE):raise RuntimeError('Material readback mismatch')
        report.update(status='SAVED_REOPENED_VISUAL_PENDING',material=h._path(material),selected=selected_names)
    except Exception as error:
        report.update(status='FAILED_CHECKPOINT_AVAILABLE',error=repr(error));raise
    finally:
        after=units.offline_plan()
        report['protectedUnchanged']=all(after[k]==protected[k] for k in ('assets','configSha256','manifestSha256','protectedMapHashes')) and all(sha(Path(p))==v for p,v in hashes.items()) and preflight()['sources']==report['sources']
        report['mainSha256After']=sha(mapfile)
        if not report['protectedUnchanged']:report['status']='FAILED_PROTECTED_HASH_MISMATCH'
        write()
        if not report['protectedUnchanged']:raise RuntimeError('Protected source changed')
    return report
