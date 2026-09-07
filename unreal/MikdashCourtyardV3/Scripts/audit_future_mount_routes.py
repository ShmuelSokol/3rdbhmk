"""Offline source plan and explicit native floor/render audit. Never starts/stops PIE.

prepare() uses isolated pinned Shapely. audit(map_path) uses saved plan in Unreal;
no actor, mesh, collision, camera, sequence, material or map-save mutation.
Sparse static traces are diagnostics, not continuous CharacterMovement acceptance.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
from datetime import datetime,timezone
ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
BASE=ROOT/'SourceAssets/FutureMountV1'
OUTPUT=BASE/'route-review'
SOURCE=Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\architecture-review\jerusalem-meshes.json')
CONTEXT=Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\cloud-unreal-v3\context-review')
FEATURES=Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\mikdash-walkthrough\public\context\jerusalem.json')
MAPS=['/Game/MikdashV3/FutureMountV1/L_FutureMount','/Game/MikdashV3/IntegratedReviewV1/Maps/Walkthrough','/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def convert(p):return [(p[0]+17.509700315687695)*50,(p[2]-.5513496449385334)*50,p[1]*50]


def prepare():
    sys.path.insert(0,str(BASE/'.tools'))
    import shapely
    from shapely.geometry import Polygon,Point,box
    assert shapely.__version__=='2.1.2'
    source=read(SOURCE);assert sha(SOURCE)=='cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb'
    geometry=read(BASE/'mount-platform.mesh.json');deck=Polygon(geometry['allowedBoundaryRingsXYcm'][0]);assert deck.is_valid
    terrain=source['meshes'][0]['positions']
    grid={(terrain[i],terrain[i+2]):terrain[i+1] for i in range(0,len(terrain),3)}
    def height(x,y):
        x=x/50-17.509700315687695;y=y/50+.5513496449385334
        x0=math.floor(x/50)*50;y0=math.floor(y/50)*50;a=(x-x0)/50;b=(y-y0)/50
        p,q,r,s=grid[x0,y0],grid[x0+50,y0],grid[x0,y0+50],grid[x0+50,y0+50]
        return 50*(p+(q-p)*a+(r-p)*b if a+b<=1 else s+(r-s)*(1-a)+(q-s)*(1-b))
    routes=[]
    def point(label,x,y,z,source_surface,**extra):return dict(label=label,expectedFloorCm=[x,y,z],sourceSurface=source_surface,**extra)
    gate=[point('Platform east gate approach',x,0,0,'Exact deck top Z0') for x in [10000,9750,9500,9300]]
    architecture=read(ROOT/'SourceAssets/architecture-manifest.json')['meshes']
    stairs=sorted([r for r in architecture if r['sourceName'].startswith('Outer E stair ')],key=lambda r:int(r['sourceName'].rsplit(' ',1)[1]))
    assert len(stairs)==12
    for stair in stairs:
        b=stair['expectedBoundsUnrealCm'];x=(b['min'][0]+b['max'][0])/2
        # This is the known horizontal tread top, not the solid's volume center.
        gate.append(point(stair['sourceName']+' tread top',x,0,b['max'][2],stair['assetName'],staticCapsuleAtStepIsDiagnostic=True))
    for x in [8500,8250,7950,7600]:gate.append(point('Outer gate floor x'+str(x),x,0,300,'Measured Outer E floor/threshold Z300'))
    assert all(deck.covers(Point(p['expectedFloorCm'][:2])) for p in gate)
    routes.append(dict(name='Platform to measured outer eastern gate',continuity='Candidate walking route; no user movement generated',points=gate))
    inset=deck.buffer(-300);assert inset.geom_type=='Polygon'
    ring=inset.exterior;count=math.ceil(ring.length/2000)
    perimeter=[]
    for i in range(count):
        p=ring.interpolate(ring.length*i/count)
        perimeter.append(point('Inside perimeter '+str(i),p.x,p.y,0,'Deck top, 300cm inset from exact cut edge'))
    routes.append(dict(name='Mount perimeter clearance probes',continuity='Sparse perimeter samples; not a validated navigation circuit',points=perimeter))
    transitions=[]
    boundary=deck.exterior
    for i in range(12):
        distance=boundary.length*(i+.37)/12;p=boundary.interpolate(distance)
        left=boundary.interpolate((distance-10)%boundary.length);right=boundary.interpolate((distance+10)%boundary.length)
        dx=right.x-left.x;dy=right.y-left.y;length=math.hypot(dx,dy);nx=-dy/length;ny=dx/length
        if not deck.covers(Point(p.x+nx*200,p.y+ny*200)):nx=-nx;ny=-ny
        for sign,label in [(1,'inside'),(-1,'outside')]:
            x=p.x+sign*nx*200;y=p.y+sign*ny*200
            assert deck.covers(Point(x,y))==(sign==1)
            transitions.append(point('Edge '+str(i)+' '+label,x,y,0 if sign==1 else height(x,y),
                'Deck top' if sign==1 else 'Preserved original DEM triangle interpolation',edgePair=i,continuity='Retaining edge may be a drop; this pair is NOT an intended walk across the boundary'))
    routes.append(dict(name='Deck/retained terrain transition controls',continuity='Comparison pairs only; no missing stairs treated as walking links',points=transitions))
    design=read(ROOT/'SourceAssets/visual-review/mount-platform-design.json')
    approach=[point('Kotel approach candidate '+str(i),x,y,0 if deck.covers(Point(x,y)) else height(x,y),
        'Deck top or preserved DEM; missing approach stair geometry',stairsPending=True) for i,(x,y) in enumerate(design['kotelApproach']['candidateNativeXYcm'])]
    routes.append(dict(name='Kotel plaza to Mount approach',continuity='PENDING stairs/bridge/access design; never infer connectivity from these samples',points=approach))
    cameras=[dict(name='outer_gate_from_platform',groundPointLabel=gate[1]['label'],target=[8000,0,450],eyeHeightCm=165),
        dict(name='Kotel_plaza_preserved_lower_level',groundPointLabel=approach[0]['label'],target=[-14400,14000,300],eyeHeightCm=165)]
    for index in [0,len(perimeter)//3,2*len(perimeter)//3]:
        cameras.append(dict(name='mount_perimeter_'+str(index),groundPointLabel=perimeter[index]['label'],target=[0,0,500],eyeHeightCm=165))
    # Source-level obstacles: exact native asset + retained source triangle IDs.
    # This never authorizes deleting a shared chunk.
    streets=read(CONTEXT/'streets-manifest.json');street_candidates=[]
    for record in streets['meshes']:
        bounds=record['expectedBoundsUnrealCm']
        if bounds['max'][2]<=2 or not box(bounds['min'][0],bounds['min'][1],bounds['max'][0],bounds['max'][1]).intersects(deck):continue
        mesh=source['meshes'][record['sourceMeshIndex']];positions=mesh['positions'];ids=mesh['indices'];selected=[]
        for tid in record['sourceTriangleIndices']:
            points=[convert(positions[3*v:3*v+3]) for v in ids[3*tid:3*tid+3]]
            if max(p[2] for p in points)<=2:continue
            shape=Polygon([p[:2] for p in points])
            if shape.area>1e-8 and shape.intersection(deck).area>1:
                selected.append(tid)
        if selected:street_candidates.append(dict(nativeAsset='/Game/MikdashV3/JerusalemContext/Streets/'+record['assetName'],
            category=record['category'],sourceMeshIndex=record['sourceMeshIndex'],sourceTriangleIndices=selected,
            maxSourceZcm=bounds['max'][2],reviewHeld=record.get('reviewHeld',False),
            action='Inspect only listed source triangles in native view; preserve remaining triangles/chunk. These may be roofs/walls or road ribbons, not automatically removable.'))
    buildings=read(CONTEXT/'buildings-manifest.json');features=read(FEATURES)['features']
    def key(points):return tuple(round(fn(p[i] for p in points),2) for fn in (min,max) for i in (0,1))
    features_by_bounds={}
    for feature in features:
        if feature['kind']=='building' and len(feature['points'])>=3:features_by_bounds.setdefault(key(feature['points']),[]).append(feature)
    component_asset={cid:'/Game/MikdashV3/JerusalemContext/Buildings/'+m['assetName'] for m in buildings['meshes'] for cid in m['sourceComponentIds']}
    building_candidates=[]
    for component in buildings['components']:
        b=component['sourceBoundsAmos']
        if b['max'][1]*50<=2:continue
        bboxkey=(round(b['min'][0],2),round(b['min'][2],2),round(b['max'][0],2),round(b['max'][2],2))
        for feature in features_by_bounds.get(bboxkey,[]):
            footprint=Polygon([[(p[0]+17.509700315687695)*50,(p[1]-.5513496449385334)*50] for p in feature['points']])
            if not footprint.is_valid or footprint.intersection(deck).area<=1:continue
            building_candidates.append(dict(sourceOsmId=feature['id'],componentId=component['componentId'],
                sourceRootVertexId=component['sourceRootVertexId'],nativeAsset=component_asset[component['componentId']],
                sourceTopZcm=b['max'][1]*50,footprintOverlapM2=footprint.intersection(deck).area/10000,
                action='Exact source footprint/component candidate. Native presence and visual obstruction must be checked. Never remove its shared mesh wholesale.'))
    report=dict(status='source_plan_ready_native_audit_pending',sourceHashes={str(p):sha(p) for p in [SOURCE,FEATURES,ROOT/'SourceAssets/architecture-manifest.json',BASE/'mount-platform.mesh.json']},
        routes=routes,cameras=cameras,streetCandidates=street_candidates,buildingCandidates=building_candidates,
        capsuleEvidence=read(ROOT/'SourceAssets/runtime-review/bounded-route-check.json')['snapshot'],
        limits=['No guessed AABB-center spawn. Cameras use traced horizontal floor plus165cm eye height and require capsule clearance.',
        'Native actor presence filters source candidates; mapped source features do not prove the fragments remain in the edited scenario.',
        'Kotel access is pending stairs, not passed. No breach of protected Western Wall/plaza geometry is proposed.',
        'This is a sparse diagnostic audit, not continuous walking or final rendered visual acceptance.'])
    OUTPUT.mkdir(exist_ok=True);(OUTPUT/'route-source-plan.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def audit(map_path=MAPS[0]):
    import unreal as ue
    assert map_path in MAPS and Path(ue.Paths.project_dir()).resolve()==ROOT
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    assert not editor.get_game_world(),'User PIE preserved: this audit never ends or modifies gameplay'
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    plan=read(OUTPUT/'route-source-plan.json')
    assert all(sha(Path(p))==value for p,value in plan['sourceHashes'].items())
    map_file=ROOT/('Content/'+map_path[6:]+'.umap');before=sha(map_file)
    levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem);actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    assert levels.load_level(map_path);world=editor.get_editor_world()
    half=plan['capsuleEvidence']['capsuleHalfHeightCm'];radius=plan['capsuleEvidence']['capsuleRadiusCm']
    report=dict(status='auditing',map=map_path,mapSha256=before,capsuleHalfHeightCm=half,capsuleRadiusCm=radius,
        capsuleEvidence='Previously recorded native BP_MikdashWalker capsule; this run does not create a pawn',routes=[],renderMeshes=[],cameraSpecs=[],obstacleCandidates=[],limits=plan['limits'])
    def trace(start,end,capsule=False):
        args=dict(world_context_object=world,start=ue.Vector(*start),end=ue.Vector(*end),profile_name='Pawn',trace_complex=True,
            actors_to_ignore=[],draw_debug_type=ue.DrawDebugTrace.NONE,ignore_self=False)
        hit=(ue.SystemLibrary.capsule_trace_single_by_profile(radius=radius,half_height=half,**args) if capsule else ue.SystemLibrary.line_trace_single_by_profile(**args))
        if hit is None:return None
        split=ue.GameplayStatics.break_hit_result(hit);assert len(split)==18
        actor=split[9];component=split[10]
        mesh=component.get_editor_property('static_mesh') if isinstance(component,ue.StaticMeshComponent) else None
        p=split[5];n=split[7]
        return dict(blocking=split[0],initialOverlap=split[1],pointCm=[p.x,p.y,p.z],normal=[n.x,n.y,n.z],
            actor=actor.get_actor_label() if actor else None,component=component.get_path_name() if component else None,
            mesh=mesh.get_path_name().split('.')[0] if mesh else None,faceIndex=split[15],item=split[13])
    try:
        points_by_label={}
        for route in plan['routes']:
            rows=[]
            for point in route['points']:
                x,y,z=point['expectedFloorCm'];floor=trace([x,y,z+65],[x,y,z-65])
                item=dict(point,floorHit=floor)
                if not floor:item['status']='NO_EXPECTED_FLOOR'
                else:
                    actual=floor['pointCm'][2];error=actual-z
                    clearance=trace([x,y,actual+half+2.1],[x,y,actual+half+2],True)
                    item.update(floorErrorCm=error,capsuleHit=clearance,status='FLOOR_AND_STATIC_CLEARANCE_PASS' if abs(error)<=2 and not clearance else 'REVIEW_FLOOR_OR_STATIC_CAPSULE')
                    if abs(error)<=2 and not clearance:item['cameraGroundCm']=[x,y,actual]
                rows.append(item);points_by_label[point['label']]=item
            report['routes'].append(dict(name=route['name'],continuity=route['continuity'],points=rows))
        for camera in plan['cameras']:
            point=points_by_label[camera['groundPointLabel']]
            if 'cameraGroundCm' in point:
                x,y,z=point['cameraGroundCm'];report['cameraSpecs'].append(dict(camera,camera=[x,y,z+camera['eyeHeightCm']],status='ground_and_capsule_checked_capture_pending'))
            else:report['cameraSpecs'].append(dict(camera,status='camera_blocked_requires_review'))
        by_mesh={}
        for actor in actors.get_all_level_actors():
            for c in actor.get_components_by_class(ue.StaticMeshComponent):
                mesh=c.get_editor_property('static_mesh')
                if mesh:by_mesh.setdefault(mesh.get_path_name().split('.')[0],[]).append((actor,c,mesh))
        tile_manifest=read(BASE/'terrain-generated/terrain-cut-manifest.json')
        for tile in tile_manifest['tiles']:
            path='/Game/MikdashV3/FutureMountV1/Terrain/'+tile['replacementAssetName']
            matching=by_mesh.get(path,[]);assert len(matching)==1
            actor,c,mesh=matching[0];bounds=mesh.get_bounding_box();triangles=mesh.get_num_triangles(0)
            colors=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem).has_vertex_colors(mesh)
            item=dict(asset=path,expectedRenderTriangles=tile['outputTriangles'],actualRenderTriangles=triangles,
                renderVertices=mesh.get_num_vertices(0),vertexColorsPresent=colors,
                boundsCm={'min':[bounds.min.x,bounds.min.y,bounds.min.z],'max':[bounds.max.x,bounds.max.y,bounds.max.z]},
                material=c.get_material(0).get_path_name() if c.get_material(0) else None,
                collisionProfile=str(c.get_collision_profile_name()),passed=triangles==tile['outputTriangles'] and triangles>0 and colors)
            report['renderMeshes'].append(item)
        for candidate in plan['streetCandidates']+plan['buildingCandidates']:
            matching=by_mesh.get(candidate['nativeAsset'],[])
            report['obstacleCandidates'].append(dict(candidate,nativePresent=bool(matching),nativeActorLabels=[a.get_actor_label() for a,c,m in matching]))
        report.update(status='source_floor_render_audit_recorded_visual_and_continuous_walking_pending',
            renderTriangleCountsPassed=all(r['passed'] for r in report['renderMeshes']),
            floorOrCapsuleReviewCount=sum(p['status']!='FLOOR_AND_STATIC_CLEARANCE_PASS' for r in report['routes'] for p in r['points']))
    except Exception as error:
        report.update(status='audit_failed',error=str(error));raise
    finally:
        report['mapBytesUnchanged']=sha(map_file)==before
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        (OUTPUT/('native-route-audit-'+stamp+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        assert report['mapBytesUnchanged']
    return report


if __name__=='__main__':
    r=prepare();print(json.dumps(dict(points=sum(len(route['points']) for route in r['routes']),streetCandidates=len(r['streetCandidates']),buildingCandidates=len(r['buildingCandidates']))))
