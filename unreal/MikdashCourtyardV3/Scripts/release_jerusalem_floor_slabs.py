"""Fresh material first; separate acceptance-gated exact57 main component adoption."""
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'SourceAssets/visual-review/JerusalemPavingV1'
DEST='/Game/MikdashV3/MaterialReview/JerusalemFloorSlabsV1'
MATERIAL=DEST+'/M_JerusalemFloorSlabs_500cm'
TEXTURE='/Game/MikdashV3/MaterialReview/JerusalemPavingV2/T_JerusalemPaving_BaseColor'
SCOPE_SHA='8d7fd1ef5c8bfea6ac4769822cdb1015ef53ed5711ded15b4e8a482770c224c6'
TEXTURE_SHA='d3f46754c34de48e1642eb9efc215c7c752c2d1c3ae1fc863d4112adee09ded7'
UV='return float2(P.x,P.y)/500.0;'
BLEND='float t=smoothstep(0.85,0.98,N.z); return lerp(float3(0.58,0.55,0.48),C,t);'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def assetfile(p):return ROOT/'Content'/(p[6:]+'.uasset')
def helper(n):
    s=importlib.util.spec_from_file_location('slabs_'+n,ROOT/'Scripts'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def plan():
    p=FOLDER/'floor-scope.json'
    if sha(p)!=SCOPE_SHA or sha(assetfile(TEXTURE))!=TEXTURE_SHA:raise RuntimeError('Frozen scope/approved texture changed')
    rows=json.loads(p.read_text())['allowlist']
    if len(rows)!=57 or len({r['mesh'] for r in rows})!=57:raise RuntimeError('Expected57 unique exact meshes')
    return dict(status='OFFLINE_PREPARED',material=MATERIAL,texture=TEXTURE,scopeSha256=SCOPE_SHA,textureSha256=TEXTURE_SHA,rows=rows)
def graph(u,m):
    ml=u.MaterialEditingLibrary;rows={}
    for n in ml.get_material_expressions(m):
        r=dict(kind=n.get_class().get_name(),inputs=[v.get_name() if v else None for v in ml.get_inputs_for_material_expression(m,n)])
        if isinstance(n,u.MaterialExpressionCustom):r.update(code=n.get_editor_property('Code'),names=[str(v.get_editor_property('InputName')) for v in n.get_editor_property('Inputs')])
        if isinstance(n,u.MaterialExpressionConstant):r['r']=n.get_editor_property('R')
        if isinstance(n,u.MaterialExpressionTextureSample):
            t=n.get_editor_property('Texture');r.update(texture=t.get_path_name().split('.')[0],srgb=t.get_editor_property('srgb'))
        rows[n.get_name()]=r
    outputs={}
    for prop in ('MP_BASE_COLOR','MP_ROUGHNESS','MP_METALLIC'):
        n=ml.get_material_property_input_node(m,getattr(u.MaterialProperty,prop))
        if not n:raise RuntimeError('Missing output')
        outputs[prop]=n.get_name()
    if len(rows)!=7 or {r.get('code') for r in rows.values() if 'code'in r}!={UV,BLEND}:raise RuntimeError('Graph mismatch')
    uv=next(k for k,r in rows.items() if r.get('code')==UV);blend=outputs['MP_BASE_COLOR']
    sample=next(k for k,r in rows.items() if r.get('texture')==TEXTURE)
    world=next(k for k,r in rows.items() if r['kind']=='MaterialExpressionWorldPosition')
    normal=next(k for k,r in rows.items() if r['kind']=='MaterialExpressionVertexNormalWS')
    if rows[uv]['inputs']!=[world] or uv not in rows[sample]['inputs'] or not rows[sample]['srgb'] or rows[blend].get('code')!=BLEND or rows[blend]['inputs']!=[sample,normal]:raise RuntimeError('Graph links mismatch')
    if abs(rows[outputs['MP_ROUGHNESS']].get('r',-1)-.8)>1e-6 or rows[outputs['MP_METALLIC']].get('r')!=0:raise RuntimeError('Finish constants mismatch')
    if not ml.has_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE):raise RuntimeError('Nanite usage missing')
    return dict(nodes=rows,outputs=outputs,nanite=True)
def run(*,import_material=False,apply=False,acceptance_receipt=None):
    report=plan()
    if not import_material and not apply:return report
    if import_material and apply:raise RuntimeError('Import and adoption must be separate runs with PIE review between')
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Live/dirty editor')
    units=helper('release_amah48_candidate');protected=units.offline_plan();target=protected['source'];mapfile=units.disk(target)
    if apply and ed.get_editor_world().get_path_name().split('.')[0]!=target:raise RuntimeError('Current main must already be loaded for adoption')
    h=helper('release_resident_crowd');baseline=h._scene_snapshot(u,actors);selected=[]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');checkpoint=ROOT.parent/'ReviewCheckpoints'/('FloorSlabs-'+stamp)
    hashes={str(assetfile(TEXTURE)):TEXTURE_SHA};accepted=None
    if import_material:
        if u.EditorAssetLibrary.does_directory_exist(DEST) or (ROOT/'Content'/DEST[6:]).exists():raise RuntimeError('Fresh namespace required')
    else:
        if not acceptance_receipt:raise RuntimeError('Actual PIE acceptance receipt required')
        accepted=Path(acceptance_receipt);a=json.loads(accepted.read_text(encoding='utf-8-sig'))
        if a.get('status')!='ACCEPTED_ACTUAL_PIE' or a.get('material')!=MATERIAL or a.get('materialSha256')!=sha(assetfile(MATERIAL)) or a.get('mainSha256')!=protected['sourceSha256']:raise RuntimeError('Acceptance is absent/stale/wrong material or main')
        comparison_path=Path(a.get('nativeComparison',''))
        if not comparison_path.is_file() or sha(comparison_path)!=a.get('nativeComparisonSha256'):raise RuntimeError('Acceptance comparison receipt hash mismatch')
        comparison=json.loads(comparison_path.read_text(encoding='utf-8-sig'))
        if comparison.get('errors')!=[] or comparison.get('pieEnded') is not True or comparison.get('mapBytesUnchanged') is not True or comparison.get('mapShaBefore')!=protected['sourceSha256']:raise RuntimeError('Native comparison failed or changed map')
        if comparison.get('floorMaterialCandidate')!=MATERIAL+'.'+MATERIAL.rsplit('/',1)[1]:raise RuntimeError('Native comparison material identity mismatch')
        expected_meshes={r['mesh'] for r in report['rows']}
        compared_meshes=comparison.get('floorMeshes',[])
        if len(compared_meshes)!=57 or set(compared_meshes)!=expected_meshes:raise RuntimeError('Native comparison did not cover exact57 meshes')
        asset_hashes={str(assetfile(p).resolve()):sha(assetfile(p)) for p in (MATERIAL,TEXTURE)}
        compared_hashes={str(Path(p).resolve()):value for p,value in comparison.get('floorAssetHashes',{}).items()}
        if compared_hashes!=asset_hashes or a.get('textureSha256')!=TEXTURE_SHA:raise RuntimeError('Compared material/texture hashes changed')
        screenshots=comparison.get('floorComparison',[])
        if len(screenshots)!=2 or len({r.get('file') for r in screenshots})!=2:raise RuntimeError('Expected two distinct native comparison images')
        image_hashes={}
        for image in screenshots:
            image_path=Path(image['file'])
            if not image_path.is_file() or sha(image_path)!=image.get('sha256'):raise RuntimeError('Native screenshot hash mismatch')
            image_hashes[str(image_path.resolve())]=image['sha256']
        if {str(Path(p).resolve()):value for p,value in a.get('screenshotHashes',{}).items()}!=image_hashes:raise RuntimeError('Root acceptance screenshot hashes differ from native comparison')
        hashes.update(asset_hashes);hashes.update(image_hashes);hashes[str(comparison_path)]=sha(comparison_path)
        hashes[str(accepted)]=sha(accepted);hashes[str(assetfile(MATERIAL))]=sha(assetfile(MATERIAL))
        for folder in ('__ExternalActors__','__ExternalObjects__'):
            if (ROOT/'Content'/folder/target[6:]).exists():raise RuntimeError('External map objects require expanded checkpoint')
        byname={a.get_name():a for a in actors.get_all_level_actors()}
        for row in report['rows']:
            a=byname.get(row['actorName'])
            if not a or a.get_actor_label()!=row['actorLabel']:raise RuntimeError('Actor identity changed')
            cs=a.get_components_by_class(u.StaticMeshComponent)
            if len(cs)!=1 or cs[0].get_name()!=row['componentName'] or h._path(cs[0].get_editor_property('static_mesh'))!=row['mesh']:raise RuntimeError('Exact floor component mismatch')
            c=cs[0]
            originals=[p.split('.')[0] for p in row['nativeMaterials']]
            if c.get_num_materials()!=1 or len(originals)!=1 or h._path(c.get_material(0))!=originals[0]:raise RuntimeError('Floor no longer has exact recorded per-row material; refuse')
            for path in (row['mesh'],originals[0]):hashes[str(assetfile(path))]=sha(assetfile(path))
            selected.append((a,c))
    checkpoint.mkdir(parents=True,exist_ok=False)
    shutil.copy2(mapfile,checkpoint/'Main.umap')
    if sha(checkpoint/'Main.umap')!=protected['sourceSha256']:raise RuntimeError('Checkpoint hash mismatch')
    receipt=FOLDER/('native-floor-slabs-'+stamp+'.json');report.update(status='STARTED',checkpoint=str(checkpoint),mainSha256Before=protected['sourceSha256'],protectedAssets=hashes)
    def write():receipt.write_text(json.dumps(report,indent=2),encoding='utf8')
    write()
    try:
        if plan()['scopeSha256']!=SCOPE_SHA or units.offline_plan()!=protected or any(sha(Path(p))!=v for p,v in hashes.items()):raise RuntimeError('Pre-mutation input changed')
        ml=u.MaterialEditingLibrary
        if import_material:
            m=u.AssetToolsHelpers.get_asset_tools().create_asset(MATERIAL.rsplit('/',1)[1],DEST,u.Material,u.MaterialFactoryNew())
            if not m:raise RuntimeError('Material creation failed')
            def node(cls):return ml.create_material_expression(m,cls)
            def custom(code,names,kind):
                n=node(u.MaterialExpressionCustom);n.set_editor_property('Code',code);n.set_editor_property('OutputType',kind);pins=[]
                for name in names:
                    pin=u.CustomInput();pin.set_editor_property('InputName',name);pins.append(pin)
                n.set_editor_property('Inputs',pins);return n
            def wire(a,b,p):
                if not ml.connect_material_expressions(a,'',b,p):raise RuntimeError('Wire failed '+p)
            world=node(u.MaterialExpressionWorldPosition);normal=node(u.MaterialExpressionVertexNormalWS)
            uv=custom(UV,['P'],u.CustomMaterialOutputType.CMOT_FLOAT2);wire(world,uv,'P')
            sample=node(u.MaterialExpressionTextureSample);sample.set_editor_property('Texture',u.load_asset(TEXTURE));wire(uv,sample,'UVs')
            blend=custom(BLEND,['C','N'],u.CustomMaterialOutputType.CMOT_FLOAT3);wire(sample,blend,'C');wire(normal,blend,'N')
            rough=node(u.MaterialExpressionConstant);rough.set_editor_property('R',.8)
            metal=node(u.MaterialExpressionConstant);metal.set_editor_property('R',0.)
            for n,p in ((blend,u.MaterialProperty.MP_BASE_COLOR),(rough,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)):
                if not ml.connect_material_property(n,'',p):raise RuntimeError('Output wire failed')
            ml.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE,True)
            compile_errors=list(ml.recompile_material(m))
            report['compileErrors']=compile_errors
            if compile_errors:raise RuntimeError('Material compilation failed: '+repr(compile_errors))
            report['graph']=graph(u,m)
            if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Save failed')
            if graph(u,u.load_asset(MATERIAL))!=report['graph']:raise RuntimeError('Saved graph mismatch')
            report.update(status='IMPORTED_ONLY_PIE_ACCEPTANCE_PENDING',materialSha256=sha(assetfile(MATERIAL)))
        else:
            m=u.load_asset(MATERIAL);report['graph']=graph(u,m)
            for a,c in selected:a.modify(True);c.modify(True);c.set_material(0,m)
            expected=h._scene_snapshot(u,actors);normalized=json.loads(json.dumps(expected))
            for a,c in selected:
                for before,after in zip(baseline[a.get_name()]['components'],normalized[a.get_name()]['components']):
                    if 'materials'in after:after['materials']=before['materials']
            if normalized!=baseline:raise RuntimeError('Unexpected changes beyond57 floor materials')
            if not levels.save_current_level() or not levels.load_level(target) or ed.get_editor_world().get_path_name().split('.')[0]!=target or h._scene_snapshot(u,actors)!=expected:raise RuntimeError('Save/reopen mismatch')
            report.update(status='57_FLOOR_OVERRIDES_SAVED_REOPENED',acceptanceReceipt=str(accepted))
    except Exception as error:report.update(status='FAILED_CHECKPOINT_AVAILABLE',error=repr(error));raise
    finally:
        after=units.offline_plan();report['mainSha256After']=sha(mapfile)
        report['protectedUnchanged']=all(after[k]==protected[k] for k in ('assets','configSha256','manifestSha256','protectedMapHashes')) and all(sha(Path(p))==v for p,v in hashes.items()) and plan()['scopeSha256']==SCOPE_SHA
        if import_material:report['protectedUnchanged']=report['protectedUnchanged'] and after['sourceSha256']==protected['sourceSha256'] and h._scene_snapshot(u,actors)==baseline
        if not report['protectedUnchanged']:report['status']='FAILED_PROTECTION'
        write()
        if not report['protectedUnchanged']:raise RuntimeError('Protected input changed')
    return report
