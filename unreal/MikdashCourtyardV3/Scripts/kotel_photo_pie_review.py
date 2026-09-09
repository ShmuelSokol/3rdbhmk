"""Four-slot PIE-only photo-on-depth trial. No imports, saves or asset edits.
Caller owns capture, teardown and broader map/save guards. Call restore before ending PIE.
"""
import hashlib
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
PHOTO='/Game/MikdashV3/MaterialReview/KotelPhotoSurfaceV2'
STONE='/Game/MikdashV3/MaterialReview/KotelStoneV2'
ORIGINAL=STONE+'/M_KotelAshlarV2'
EDGES=(24,25,0,1)
HASHES={
 'M_PhotoFace_0':'42306c15084ad019f38fb26bf79463cdea85c7264ee84d53496ff5a0ccf3211a',
 'M_PhotoFace_1':'f95bedcb6a2e972f325908000c0b52fe9d18f86a074ff12aa7189686048a6679',
 'M_PhotoFace_24':'21e679104ac983ca62d315b077e19b16bd6826ef680e551b7ea9f7dce411cacb',
 'M_PhotoFace_25':'3c99ebe16a7ec2cf1f997e770755e8461575fde5135e9f868f803cf3300fc1ca',
 'T_KotelWallPhoto':'1bdef650c131a0fa42dbecb51002b793fba009d724e0eb5c6b8650c6fbe07ce0'}
MAPS={'/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
      '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'}
_active=None


def _hashes():
    result={}
    for name,expected in HASHES.items():
        path=ROOT/'Content'/(PHOTO[6:]+'/'+name+'.uasset')
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=expected:raise RuntimeError('Photo asset hash differs: '+name)
        result[PHOTO+'/'+name]=actual
    return result


def _guard(world):
    import unreal as u
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if Path(u.Paths.project_dir()).resolve()!=ROOT or world is None or ed.get_game_world()!=world:
        raise RuntimeError('Exact active PIE game world required')
    package=world.get_outermost().get_name()
    if not re.search(r'UEDPIE_\d+_',package) or re.sub(r'UEDPIE_\d+_','',package) not in MAPS:
        raise RuntimeError('Unsupported or non-PIE world package')
    return package


def _path(obj):return obj.get_path_name().split('.')[0] if obj else None


def _state(actor,component):
    p=actor.get_actor_location();r=actor.get_actor_rotation();s=actor.get_actor_scale3d()
    body=component.get_editor_property('body_instance')
    return {'pose':[p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z],
            'actorHidden':bool(actor.get_editor_property('hidden')),
            'actorCollision':actor.get_actor_enable_collision(),
            'visible':bool(component.get_editor_property('visible')),
            'hiddenInGame':bool(component.get_editor_property('hidden_in_game')),
            'collisionProfile':str(component.get_collision_profile_name()),
            'configuredCollision':str(body.get_editor_property('collision_enabled')),
            'mesh':_path(component.get_editor_property('static_mesh'))}


def apply(world):
    """Assign existing face-specific world-projected photo materials to visible V2 depth."""
    global _active
    import unreal as u
    if _active is not None:raise RuntimeError('Photo trial already active; restore first')
    package=_guard(world);hashes=_hashes()
    aa=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
    targets=[]
    for edge in EDGES:
        mesh_path=STONE+'/Meshes/SM_KotelAshlarV2_E'+str(edge)
        found=[(a,c) for a in aa for c in a.get_components_by_class(u.StaticMeshComponent)
               if _path(c.get_editor_property('static_mesh'))==mesh_path]
        if len(found)!=1:raise RuntimeError('Exactly one V2 component required: '+mesh_path)
        a,c=found[0]
        if a.get_outermost().get_name()!=package or a.get_actor_label()!='RELEASE_KotelStoneV2_E'+str(edge):
            raise RuntimeError('V2 actor ownership/label differs')
        original=[c.get_material(i) for i in range(c.get_num_materials())]
        if len(original)!=1 or _path(original[0])!=ORIGINAL:raise RuntimeError('Expected single original V2 material slot')
        before=_state(a,c)
        if before['pose']!=[0,0,0,0,0,0,1,1,1] or before['actorHidden'] or not before['visible'] or before['hiddenInGame']:
            raise RuntimeError('Expected visible identity-posed V2 geometry')
        material=u.load_asset(PHOTO+'/M_PhotoFace_'+str(edge))
        if not isinstance(material,u.MaterialInterface) or _path(material)!=PHOTO+'/M_PhotoFace_'+str(edge):
            raise RuntimeError('Photo material missing/wrong class')
        targets.append((a,c,original,material,before))
    # Retained layers must remain hidden, rather than being blended accidentally.
    layers=[]
    for a in aa:
        if a.get_actor_label().startswith('REVIEW_KotelPhoto_') or any((_path(c.get_editor_property('static_mesh')) or '').startswith('/Game/MikdashV3/MaterialReview/KotelStoneV1/Meshes/SM_KotelFace_Tint') for c in a.get_components_by_class(u.StaticMeshComponent)):
            for c in a.get_components_by_class(u.StaticMeshComponent):
                old=_state(a,c)
                if not (old['actorHidden'] or not old['visible'] or old['hiddenInGame']):raise RuntimeError('Retained photo/V1 layer unexpectedly visible')
                layers.append((a,c,old))
    _active={'world':world,'targets':targets,'layers':layers,
             'overrides':{c.get_path_name():list(c.get_editor_property('override_materials')) for a,c,original,material,before in targets}}
    try:
        for a,c,original,material,before in targets:
            c.set_material(0,material)
            if c.get_material(0)!=material or _state(a,c)!=before:raise RuntimeError('PIE material readback/state preservation failed')
        for a,c,before in layers:
            if _state(a,c)!=before:raise RuntimeError('Retained layer changed')
        _hashes()
        return {'status':'pie_photo_materials_applied','world':package,'slots':4,'assetHashes':hashes,
                'components':[{'actor':a.get_name(),'component':c.get_name(),'original':_path(original[0]),'trial':_path(material)} for a,c,original,material,before in targets],
                'limitations':['Cleaned user-photo derivative only; no original private photo copied.',
                    'World-projected panorama bypasses V2 tint/jitter UV0; no image repetition.',
                    'Photo aspect2.985 fitted to wall aspect4.523; photographed joints may disagree with authored3D courses.',
                    'Captured photo lighting plus scene lighting; no photogrammetry or visual acceptance claim.']}
    except Exception:
        restore()
        raise


def restore():
    """Restore exact original arrays in the same live PIE world; refuse silent teardown loss."""
    global _active
    if _active is None:return {'status':'no_active_trial','slots':0}
    _guard(_active['world'])
    errors=[]
    for a,c,original,material,before in _active['targets']:
        try:
            for i,value in enumerate(original):c.set_material(i,value)
            overrides=_active['overrides'][c.get_path_name()]
            c.set_editor_property('override_materials',overrides)
            if list(c.get_editor_property('override_materials'))!=overrides:
                raise RuntimeError('Original override array readback differs')
            if c.get_num_materials()!=len(original) or any(c.get_material(i)!=v for i,v in enumerate(original)) or _state(a,c)!=before:
                raise RuntimeError('Original slot/state readback differs')
        except Exception as error:errors.append(str(error))
    for a,c,before in _active['layers']:
        if _state(a,c)!=before:errors.append('Retained layer changed')
    _hashes()
    if errors:raise RuntimeError('Photo trial restoration failed: '+repr(errors))
    _active=None
    return {'status':'original_pie_material_arrays_restored','slots':4}
