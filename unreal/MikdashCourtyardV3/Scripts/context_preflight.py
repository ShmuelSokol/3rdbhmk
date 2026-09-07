"""Pure-Python frozen-context preflight. No Unreal imports or filesystem writes.

Hashes pin the independently reviewed batch. Changed assets require new review
and an explicit revision of these locks; no caller can silently bypass them.
"""
import copy
import hashlib
import json
import math
from pathlib import Path


class PreflightError(ValueError):
    pass


LOCKS = {
    'streets-manifest.json': 'cc9eb91e99298565db296ea52a4eef744944e3bac3014829b573e30235aea8da',
    'streets.fbx': 'f5d02a0d5f0b48e3ce2e28e83fd8924944e3da59edb1ab2e4f0b141ad4de17e1',
    'path-grounded-manifest.json': '1459da1f0c64675c8e64ee8892aced5830ba8a28062d334773cb36b1ad32e0f5',
    'path-grounded.fbx': 'a5b3db82b12404a17362d3ae7a9d15a4f27b3d9c6d13bec91fee5667f3a9f4d2',
    'roadbed-validation.json': 'f4b60ba3a13fe3bf60f0894140dd242ddc052fd556bbd83d0989d7e58fd0df5e',
    'roadbed-contact.json': '8b08f97fe88bcc83c3b6f9e9c793f60656a63e87a2945afbda76b53444644717',
}
SOURCE_MESH_SHA = 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb'
ARCHITECTURE_SHA = '61b20b85451fce18460540da44f447492e818be5949e5ed610042eaccf6f17cf'
HELD_NORTH = 'SM_Jerusalem_StonePaths_03_Grid_P000_N001_ReviewHeld'
HELD_SOUTH = 'SM_Jerusalem_StonePaths_03_Grid_P000_P000_ReviewHeld'
HELD = {HELD_NORTH, HELD_SOUTH}
PATCH_NAME = 'SM_Jerusalem_StonePaths_03_Grid_P000_N001_GroundedV3'
PATH_MATERIAL = 'M_Jerusalem_StonePaths_4755dbc9'
MATERIAL_CONTRACTS = {
    'M_Jerusalem_Asphalt_a167e3e4': ('jerusalemAsphalt', 1, True),
    PATH_MATERIAL: ('jerusalemStonePaths', 1, True),
    'M_Jerusalem_CityWalls_2b334de9': ('jerusalemCityWalls', .9, False),
    'M_Jerusalem_Landmark_dd3b1b60': ('jerusalemLandmark', .8, False),
    'M_Jerusalem_Landmark_0cb4c58a': ('jerusalemLandmark', .9, False),
    'M_Jerusalem_Landmark_b72a2dc5': ('jerusalemLandmark', .65, False),
}
SOURCE_TRIANGLES = {2:167862,3:109876,4:23424,5:552,6:12,7:12,8:552,9:552,10:552,11:552,12:552,13:552,14:552,15:552,16:552}


def _require(condition, message):
    if not condition:
        raise PreflightError(message)


def _read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'), parse_constant=lambda token: (_ for _ in ()).throw(PreflightError('Nonfinite JSON: '+token)))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError('Cannot read '+str(path)+': '+str(exc)) from exc


def _hash(path):
    digest=hashlib.sha256()
    try:
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    except OSError as exc:
        raise PreflightError('Missing/unreadable file: '+str(path)) from exc
    return digest.hexdigest()


def _vector(value, label, size=3):
    _require(isinstance(value,list) and len(value)==size, label+' must have '+str(size)+' values')
    _require(all(type(v) in (int,float) and math.isfinite(v) for v in value), label+' must be finite numeric values')
    return value


def _bounds(value, label):
    _require(isinstance(value,dict) and set(value)=={'min','max'},label+' invalid bounds')
    lo=_vector(value['min'],label+'.min');hi=_vector(value['max'],label+'.max')
    _require(all(a<=b for a,b in zip(lo,hi)),label+' inverted bounds')
    return value


def _to_ue(value):
    lo,hi=value['min'],value['max']
    return {'min':[lo[0]*100,-hi[1]*100,lo[2]*100],'max':[hi[0]*100,-lo[1]*100,hi[2]*100]}


def _identity(record,label):
    for field,want in [('spawnLocationUnrealCm',[0,0,0]),('spawnRotationDegrees',[0,0,0]),('spawnScale',[1,1,1])]:
        _require(_vector(record.get(field),label+'.'+field)==want,label+' has nonidentity '+field+'; alignment is already baked')
    if 'objectTransformIdentity' in record:
        _require(record['objectTransformIdentity'] is True,label+' object transform is not identity')


def _validate_original(document):
    _require(document.get('version')=='jerusalem-streets-v1','Unexpected streets version')
    _require(document.get('sourceMeshSha256')==SOURCE_MESH_SHA,'Frozen source hash changed')
    _require(document.get('fbxSha256')==LOCKS['streets.fbx'],'Street declared FBX hash changed')
    alignment=document.get('alignment',{})
    _require(alignment.get('degrees')==0 and alignment.get('bakedOnce') is True,'Default alignment must be baked exactly once')
    _require(alignment.get('translationSourceAmos')==[17.509700315687695,0,-.5513496449385334],'Default city alignment changed')
    options=document.get('coordinateConvention',{}).get('importOptions',{})
    for k,v in {'combine_meshes':False,'transform_vertex_to_absolute':True,'bake_pivot_in_vertex':False,
                'convert_scene':True,'convert_scene_unit':True,'force_front_x_axis':False,'import_uniform_scale':1}.items():
        _require(options.get(k)==v,'Unsafe coordinate import option '+k)
    records=document.get('meshes',[])
    _require(isinstance(records,list) and len(records)==2879==document.get('meshCount'),'Expected2879 original street meshes')
    names=[r.get('assetName') for r in records]
    _require(len(names)==len(set(names)),'Duplicate original asset names')
    _require(all(isinstance(n,str) and n.startswith('SM_Jerusalem_') for n in names),'Invalid source asset names')
    _require(set(document.get('reviewHeldAssets',[]))==HELD,'Held asset inventory changed')
    materials=document.get('materials',[])
    _require(len(materials)==6 and {m.get('fbxMaterialName') for m in materials}==set(MATERIAL_CONTRACTS),'Six exact material names required')
    for material in materials:
        name=material['fbxMaterialName'];key,rough,two=MATERIAL_CONTRACTS[name]
        _require(material.get('sourceMaterialKey')==key and material.get('metalness')==0 and material.get('roughness')==rough,'Material contract changed: '+name)
        _require(material.get('twoSided') is two and material.get('usesVertexColors') is False,'Material sidedness/color mode changed: '+name)
        color=_vector(material.get('color'),name+'.color')
        _require(all(0<=c<=1 for c in color) and material.get('colorSpace')=='linear RGB','Invalid linear material color: '+name)
        _require(color==material.get('sourceMaterial',{}).get('color'),'Material color differs from source profile: '+name)
    coverage={si:[] for si in SOURCE_TRIANGLES}
    for record in records:
        name=record['assetName'];_identity(record,name)
        _require(record.get('objectTransformIdentity') is True,name+' missing baked identity contract')
        b=_bounds(record.get('boundsBlenderMeters'),name+'.Blender')
        u=_bounds(record.get('expectedBoundsUnrealCm'),name+'.Unreal');expected=_to_ue(b)
        _require(all(abs(u[k][i]-expected[k][i])<1e-6 for k in ('min','max') for i in range(3)),name+' bounds double-transformed or mirrored')
        held=name in HELD
        _require(record.get('reviewHeld') is held and record.get('recommendedEnabled') is (not held),'Held group enabling/flag drift: '+name)
        slots=record.get('materialSlots',[])
        _require(len(slots)==1 and slots[0].get('slot')==0 and slots[0].get('fbxMaterialName') in MATERIAL_CONTRACTS,name+' invalid material slot')
        _require(slots[0].get('sourceMaterialKey')==MATERIAL_CONTRACTS[slots[0]['fbxMaterialName']][0],name+' material key mismatch')
        si=record.get('sourceMeshIndex');tids=record.get('sourceTriangleIndices')
        _require(si in coverage and isinstance(tids,list) and len(tids)==record.get('triangles'),name+' source triangle mapping invalid')
        _require(all(type(i) is int and 0<=i<SOURCE_TRIANGLES[si] for i in tids),name+' triangle index out of range')
        coverage[si].extend(tids)
    for si,tids in coverage.items():
        _require(sorted(tids)==list(range(SOURCE_TRIANGLES[si])),'Missing/duplicate source triangles in mesh '+str(si))
    _require(sum(r['triangles'] for r in records)==306706==document.get('triangles'),'Original triangle total changed')
    _require(sum(r['triangles'] for r in records if r['reviewHeld'])==22,'Held triangle count changed')


def load_streets(context_dir, patch_dir):
    """Return verified import assets and2878 effective spawn records; read only.

    context_dir has streets.fbx/manifest. patch_dir has grounded V3 FBX,
    manifest and both independent roadbed JSON reports. No asset is imported.
    """
    context_dir=Path(context_dir).expanduser().resolve();patch_dir=Path(patch_dir).expanduser().resolve()
    original=_read(context_dir/'streets-manifest.json');_validate_original(original)
    patch=_read(patch_dir/'path-grounded-manifest.json')
    validation=_read(patch_dir/'roadbed-validation.json');contact=_read(patch_dir/'roadbed-contact.json')
    _require(patch.get('version')=='path-grounded-v3' and patch.get('assetName')==PATCH_NAME,'Unexpected V3 patch identity')
    _require(patch.get('replacesOnlyAsset')==HELD_NORTH and patch.get('doNotEnableAlongsideOriginalOrV2') is True,'Ambiguous V3 replacement contract')
    _require(patch.get('triangles')==76 and patch.get('vertices')==42 and patch.get('topTriangles')==17,'V3 topology count changed')
    _identity(patch,PATCH_NAME)
    _require(patch.get('fbxSha256')==LOCKS['path-grounded.fbx'],'V3 declared FBX hash changed')
    _require(validation.get('status')=='PASS_LOCAL_GROUNDED_ROADBED_FBX' and validation.get('errors')==[],'V3 solid audit did not pass')
    _require(validation.get('fbxSha256')==patch['fbxSha256'] and validation.get('triangles')==76,'Solid audit belongs to different FBX')
    _require(validation.get('closedManifold') is True and validation.get('connectedComponentCount')==2,'V3 solid audit is incomplete')
    _require(validation.get('maximumTopDifferenceFromV2Meters')==0 and validation.get('materialUnchangedFromV2') is True,'V3 source top/material changed')
    _require(contact.get('status')=='PASS_LOCAL_SOLID_CONTACT_AND_EXTERIOR' and contact.get('errors')==[],'V3 architecture contact audit did not pass')
    _require(contact.get('roadbedFbxSha256')==patch['fbxSha256'] and contact.get('architectureFbxSha256')==ARCHITECTURE_SHA,'Contact evidence hash does not match reviewed scene')
    _require(contact.get('roadAsset')==PATCH_NAME and contact.get('roadTriangles')==76,'Contact evidence asset/count mismatch')
    for k in ('contacts','containmentHits','uncertainQueries'):_require(contact.get(k)==[],'Contact audit has unresolved '+k)
    bounds_raw=contact.get('roadBoundsBlenderM')
    _require(isinstance(bounds_raw,list) and len(bounds_raw)==2,'Actual road bounds missing')
    b=_bounds({'min':bounds_raw[0],'max':bounds_raw[1]},'Actual V3')
    _require(b['min'][1]>=81.0199 and abs(b['min'][2]+.030)<.0001 and abs(b['max'][2]-.175)<.0001,'Actual V3 clearance/datum bounds invalid')
    materials=copy.deepcopy(original['materials'])
    path_material=next(m for m in materials if m['fbxMaterialName']==PATH_MATERIAL)
    _require(patch.get('material')==path_material,'V3 native material differs from original exact profile')
    patch_record={'assetName':PATCH_NAME,'semantic':'corrected-roadbed','category':'Stone paths',
        'triangles':76,'vertices':42,'boundsBlenderMeters':b,'expectedBoundsUnrealCm':_to_ue(b),
        'spawnLocationUnrealCm':[0,0,0],'spawnRotationDegrees':[0,0,0],'spawnScale':[1,1,1],
        'objectTransformIdentity':True,'reviewHeld':False,'recommendedEnabled':True,
        'materialSlots':[{'slot':0,'fbxMaterialName':PATH_MATERIAL,'sourceMaterialKey':'jerusalemStonePaths'}],
        'replacesOnlyAsset':HELD_NORTH,'sourceFbx':'path-grounded.fbx'}
    records=copy.deepcopy(original['meshes'])
    for record in records:record['sourceFbx']='streets.fbx'
    effective=[copy.deepcopy(r) for r in records if r['assetName'] not in HELD]+[copy.deepcopy(patch_record)]
    _require(len(effective)==2878 and sum(r['triangles'] for r in effective)==306760,'Effective enabled inventory wrong')
    _require(len({r['assetName'] for r in effective})==2878,'Duplicate effective asset names')
    _require(not(HELD & {r['assetName'] for r in effective}),'Original held asset remains enabled alongside V3')
    source_files={}
    for name,want in LOCKS.items():
        directory=context_dir if name.startswith('streets') else patch_dir
        actual=_hash(directory/name)
        _require(actual==want,'File SHA256 mismatch: '+name)
        source_files[name]=actual
    return {'context_dir':context_dir,'patch_dir':patch_dir,'original_manifest':original,'patch_manifest':patch,
        'original_records':records,'patch_record':patch_record,'effective_records':effective,'materials':materials,
        'source_files':source_files,'summary':{'originalMeshCount':2879,'importedAssetCount':2880,'enabledMeshCount':2878,
            'originalTriangles':306706,'unspawnedHeldTriangles':22,'patchTriangles':76,'enabledTriangles':306760,
            'unspawnedHeldAssets':sorted(HELD),'materialCount':6,'alignmentAlreadyBaked':True,
            'nativeImportTested':False,'nativeCollisionTested':False}}


INSTANCE_LOCKS={
    'instances-manifest.json':'5b80379b80b891dc20809a025bb69a15c5219123d23f6a25e0bc1de81199ec33',
    'instance-prototypes.fbx':'0a2bbfd308041fcbbb4d3b71eea77f03b94a9050bd2fdd8cde03a22b70a494da',
}
INSTANCE_GROUPS={
    'SM_JerusalemInstance_Rooftop_tanks':(0,'Rooftop tanks',6007,52,32),
    'SM_JerusalemInstance_Rooftop_panels':(1,'Rooftop panels',6007,24,12),
    'SM_JerusalemInstance_Tree_crowns':(2,'Tree crowns',13227,240,80),
    'SM_JerusalemInstance_Tree_trunks':(3,'Tree trunks',4409,34,20),
    'SM_JerusalemInstance_Cemetery_markers':(4,'Cemetery markers',15143,24,12),
}


def _validate_instances(document):
    """Validate frozen decompositions, without performing any axis conversion."""
    _require(document.get('fbxSha256')==INSTANCE_LOCKS['instance-prototypes.fbx'],'Instance FBX hash contract changed')
    _require(document.get('prototypeCount')==5 and document.get('instanceCount')==44793,'Instance/prototype count changed')
    _require(document.get('alignment')=={'translationSourceAmos':[17.509700315687695,0,-.5513496449385334],
        'degrees':0,'bakedIntoInstanceTranslationOnce':True},'Instance alignment changed or requested twice')
    groups=document.get('groups',[])
    _require(len(groups)==5 and {g.get('assetName') for g in groups}==set(INSTANCE_GROUPS),'Instance names missing/duplicated/changed')
    max_matrix_error=0.
    for group in groups:
        name=group['assetName'];gid,category,count,vertices,triangles=INSTANCE_GROUPS[name]
        _require(group.get('sourceGroupIndex')==gid and group.get('sourceCategory')==category,name+' source identity changed')
        _require(group.get('instanceCount')==count and len(group.get('instances',[]))==count,name+' instance count mismatch')
        _require(group.get('prototypeVertices')==vertices and group.get('prototypeTriangles')==triangles,name+' prototype topology changed')
        _require(group.get('fbxMaterialName')==name.replace('SM_','M_',1),name+' material name changed')
        b=_bounds(group.get('prototypeBoundsBlenderMeters'),name+'.prototype Blender')
        u=_bounds(group.get('prototypeExpectedBoundsUnrealCm'),name+'.prototype Unreal');expected=_to_ue(b)
        _require(all(abs(u[k][i]-expected[k][i])<1e-6 for k in ('min','max') for i in range(3)),name+' prototype bounds axes changed')
        for index,instance in enumerate(group['instances']):
            label=name+'['+str(index)+']'
            _require(instance.get('sourceInstanceIndex')==index,label+' source instance order changed')
            translation=_vector(instance.get('translationUnrealCm'),label+'.translation')
            q=_vector(instance.get('quaternionXYZW'),label+'.quaternion',4)
            scale=_vector(instance.get('scale'),label+'.scale')
            matrix=_vector(instance.get('matrixUnrealRowMajor'),label+'.matrix',16)
            tint=_vector(instance.get('linearTint'),label+'.tint')
            _require(abs(sum(v*v for v in q)-1)<1e-5 and min(scale)>0,label+' nonunit quaternion or nonpositive scale')
            _require(all(0<=v<=1 for v in tint),label+' invalid linear tint')
            _require(matrix[12:]==[0,0,0,1],label+' matrix is not affine')
            _require(all(abs(matrix[i*4+3]-translation[i])<1e-6 for i in range(3)),label+' translation/matrix mismatch; possible double alignment')
            x,y,z,w=q
            rotation=((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),
                      (2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),
                      (2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)))
            error=max(abs(rotation[r][c]*scale[c]-matrix[r*4+c]) for r in range(3) for c in range(3))
            _require(error<1e-5,label+' quaternion/scale matrix mismatch')
            max_matrix_error=max(max_matrix_error,error)
    return max_matrix_error


def load_instances(context_dir):
    """Optional pure preflight for water agent's already-converted instance data.

    Returns context_dir, manifest, groups, source_files and summary. Does not
    import the Unreal-dependent importer or recalculate/modify any transform.
    """
    context_dir=Path(context_dir).expanduser().resolve()
    document=_read(context_dir/'instances-manifest.json')
    maximum_error=_validate_instances(document)
    source_files={}
    for name,want in INSTANCE_LOCKS.items():
        actual=_hash(context_dir/name)
        _require(actual==want,'File SHA256 mismatch: '+name)
        source_files[name]=actual
    return {'context_dir':context_dir,'manifest':document,'groups':document['groups'],'source_files':source_files,
        'summary':{'prototypeCount':5,'instanceCount':44793,'maximumMatrixDecompositionElementError':maximum_error,
            'alignmentAlreadyBaked':True,'nativeImportTested':False}}
