"""Offline OpeningV2: audit actual wall heights before any selective deletion.

No Unreal dependency or scene write. Preserves frozen V1, imports its Mesh writer
read-only and writes ONLY SourceAssets/mount-access/OpeningV2.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'SourceAssets/mount-access/OpeningV2'
SOURCE=Path('C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/architecture-review/jerusalem-meshes.json')
MANIFEST=Path('C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/cloud-unreal-v3/context-review/streets-manifest.json')


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    writer_path=ROOT/'Scripts/create_mount_access.py'
    loader=importlib.util.spec_from_file_location('mount_access_frozen_writer',writer_path)
    writer=importlib.util.module_from_spec(loader)
    sys.dont_write_bytecode=True
    loader.loader.exec_module(writer)
    writer.OUT=OUT
    from shapely.geometry import Polygon,box,MultiPoint
    import shapely
    frozen=json.loads((ROOT/'SourceAssets/mount-access/frozen-files.json').read_text())
    for item in frozen['files']:
        assert sha(ROOT/item['path'])==item['sha256'],'Frozen V1 changed'
    assert sha(SOURCE)==writer.EXPECTED
    assert sha(MANIFEST)=='cc9eb91e99298565db296ea52a4eef744944e3bac3014829b573e30235aea8da'
    source=json.loads(SOURCE.read_text())
    wall=source['meshes'][4]
    assert wall['name']=='Mapped city walls 4'
    positions=wall['positions']; indices=wall['indices']
    def vertex(i):
        return [(positions[3*i]+17.509700315687695)*50,
                (positions[3*i+2]-.5513496449385334)*50,positions[3*i+1]*50]
    manifests=json.loads(MANIFEST.read_text())['meshes']
    source_boxes=[]
    for first in range(0,len(indices)//3,12):
        verts=[vertex(i) for i in set(indices[first*3:(first+12)*3])]
        footprint=MultiPoint([(p[0],p[1]) for p in verts]).convex_hull
        source_boxes.append({'first':first,'footprint':footprint,'zmin':min(p[2] for p in verts),'zmax':max(p[2] for p in verts),'vertices':verts})
    v1=json.loads((ROOT/'SourceAssets/mount-access/mount-access-spec.json').read_text())
    y=v1['stairs']['centerYCm']
    cross=(-13709.15354946573,y)
    crossing_region=box(cross[0]-200,y-180,cross[0]+200,y+180)
    crossing_boxes=[b for b in source_boxes if b['footprint'].intersects(crossing_region)]
    assert crossing_boxes
    records=[]
    for b in crossing_boxes:
        matches=[m for m in manifests if m['sourceMeshIndex']==4 and b['first'] in m['sourceTriangleIndices']]
        assert len(matches)==1
        m=matches[0]
        records.append({'sourceMeshIndex':4,'sourceMeshName':wall['name'],
                        'sourceTriangleIndices':list(range(b['first'],b['first']+12)),
                        'sourceVertexIndices':sorted(set(indices[b['first']*3:(b['first']+12)*3])),
                        'boxBoundsUEcm':[[min(p[i] for p in b['vertices']) for i in range(3)],[max(p[i] for p in b['vertices']) for i in range(3)]],
                        'nativeAssetPath':'/Game/MikdashV3/JerusalemContext/Streets/'+m['assetName'],
                        'expectedActorLabel':m['assetName'],'nativeActorInstanceId':None,
                        'nativeActorInstanceIdReason':'Live instance identity requires root native lookup by exact static mesh path.',
                        'nativeBatchExpectedBoundsUEcm':m['expectedBoundsUnrealCm'],
                        'nativeBatchTriangleCount':m['triangles'],
                        'sourceFootprintUEcm':list(b['footprint'].exterior.coords),
                        'nativeTransformContract':{'translation':[0,0,0],'rotation':[0,0,0],'scale':[1,1,1]}})
    deck=writer.Mesh('KotelApproach_ElevatedDeck_V2','replacement_for_V1_stair_and_landings')
    rails=writer.Mesh('KotelApproach_ElevatedGuards_V2','replacement_for_V1_parapets')
    portal=writer.Mesh('KotelApproach_AboveWallPortal_V2','original_future_portal')
    solids=[]
    def solid(mesh,x0,y0,z0,x1,y1,z1):
        mesh.cuboid(x0,y0,z0,x1,y1,z1)
        solids.append({'mesh':mesh.name,'min':[x0,y0,z0],'max':[x1,y1,z1]})
    segments=[dict(s) for s in v1['stairs']['segments']]
    # Retain all measured V1 walking surfaces and replace deep box fill with
    # overlapping45cm deck slabs. At17.47cm risers adjacent solids overlap27.53cm.
    # Extend top landing east on Z0 to give the above-wall portal a level corridor.
    segments[-1]['xEndCm']=-12500
    for s in segments:
        a,b,z=s['xStartCm'],s['xEndCm'],s['topZcm']
        solid(deck,a,y-150,z-45,b,y+150,z)
        for lo,hi in [(y-180,y-150),(y+150,y+180)]:
            solid(rails,a,lo,z-45,b,hi,z+110)
    # Simple original stone lintel gate, explicitly an above-wall scenic portal.
    # Clear opening300cm wide,320cm high; no arch claims/historic decoration.
    for lo,hi in [(y-240,y-150),(y+150,y+240)]:
        solid(portal,-13440,lo,-45,-13260,hi,320)
        caplo,captop=(lo-10,hi) if hi<y else (lo,hi+10)
        solid(portal,-13460,caplo,300,-13240,captop,340)
    solid(portal,-13460,y-250,320,-13240,y+250,400)
    design=json.loads((ROOT/'SourceAssets/visual-review/mount-platform-design.json').read_text())
    protected=[Polygon(p['nativeXYcm']).buffer(200) for p in design['protected']]
    guards=shapely.union_all(protected)
    footprint=shapely.union_all([box(s['min'][0],s['min'][1],s['max'][0],s['max'][1]) for s in solids])
    assert footprint.intersection(guards).area < .01
    collisions=[]
    for s in solids:
        p=box(s['min'][0],s['min'][1],s['max'][0],s['max'][1])
        for b in source_boxes:
            if b['zmax']<=s['min'][2] or b['zmin']>=s['max'][2]: continue
            if p.intersection(b['footprint']).area > .01:
                collisions.append({'newMesh':s['mesh'],'newBounds':[s['min'],s['max']],'wallFirstTriangle':b['first']})
    # This is a true rotated-box XY + vertical interval test, not AABB-only proof.
    assert not collisions,'Elevated replacement intersects retained source walls'
    topwall=max(b['zmax'] for b in crossing_boxes)
    underside=min(s['topZcm']-45 for s in segments if s['xStartCm']<cross[0]+200 and s['xEndCm']>cross[0]-200)
    assert underside-topwall > 800
    meshes=[m.save() for m in [deck,rails,portal]]
    (OUT/'mount-access.mtl').write_text((ROOT/'SourceAssets/mount-access/mount-access.mtl').read_text())
    (OUT/'opening-v2.mesh.json').write_text(json.dumps({'units':'Unreal centimetres east/south/up','meshes':meshes},indent=2)+'\n')
    check={'status':'PASS_OFFLINE_ONLY','allRetainedWallBoxesTested':len(source_boxes),
           'newSolidsVsRetainedWallIntersections':collisions,'protectedBufferOverlapCm2':footprint.intersection(guards).area,
           'crossingWallHighestTopZcm':topwall,'crossingReplacementDeckLowestUndersideZcm':underside,
           'minimumCrossingDeckToWallGapCm':underside-topwall,'portalClearWidthCm':300,
           'portalMinimumHeadroomCm':320,'currentPawnCapsuleHeightCm':192,'capsuleVerticalMarginCm':128,
           'portalLevelLandingZcm':0,'portalLevelLandingExtentXcm':[segments[-1]['xStartCm'],segments[-1]['xEndCm']],
           'portalBeforeLevelLandingCm':-13460-segments[-1]['xStartCm'],
           'portalAfterLevelLandingCm':segments[-1]['xEndCm']-(-13240),
           'originalWallTrianglesRemoved':0,'originalSourceFilesEdited':False,'nativeExecuted':False}
    spec={'status':'FROZEN_OFFLINE_SOURCE_NOT_NATIVE_ACCEPTED',
          'finding':'The source enclosure is approximately10m BELOW the V1 upper walking landing. No retained wall opening/deletion is needed. OpeningV2 is an above-wall gateway and thin elevated replacement deck; it eliminates the V1 deep solid footing intersection with original city walls.',
          'scenario':'Original illustrative future access, no claim of existing bridge, engineering certification or halachic future layout.',
          'crossingXYcm':cross,'sourceWallOSMWayId':137726908,
          'sourceWallSegmentEndpointsEastSouthAmot':[[-296.08,375.69],[-279.65,466.73]],
          'wallIdentification':records,
          'protectedWesternWallBuilding':{'osmId':817206833,'asset':'/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001','sourceComponentId':7085,'instruction':'Do not confuse Buildings Grid_N002_P001 with Streets CityWalls Grid_N002_P001. Both remain unchanged.'},
          'selectiveOpeningPlan':{'sourceTrianglesToDelete':[],'nativeActorsToDelete':[],'nativeMeshesToModify':[],
                                 'sourceWallInstructions':'Retain both identified CityWalls batch actors and all original triangles. Match current mesh path, bounds and identity transform natively before relying on source clearance.',
                                 'ownedV1Replacements':['KotelApproach_StairAndLandings','KotelApproach_Parapets'],
                                 'replacementInstructions':'Place V2 deck and guards instead of these TWO owned V1 generated meshes, never overlay duplicate floor collision. Preserve frozen V1 source assets. Add portal. Keep V1 infill/apron review holds unchanged.'},
          'coordinateContract':'JSON UEcm with baked world positions, identity actors; OBJ metres east/north/up; convert handedness/units once. Mesh normals and UVs exported explicitly.',
          'walkingSegments':segments,'checks':check,
          'sources':[{'path':str(p),'sha256':sha(p)} for p in [SOURCE,MANIFEST,writer_path,ROOT/'SourceAssets/mount-access/mount-access-spec.json']],
          'requiredNativeGates':['Verify live transforms and exact source batch identities, no whole-batch deletion.',
             'V2 deck and guards replace only owned V1 stair/parapet actors if already present; no duplicate floors.',
             'Check source buildings, paths and live scenario terrain/skirt against full route. All1952retained wall boxes checked offline, but no general building/terrain clearance claim.',
             'The45cm continuous elevated deck and stone guards are concept geometry; structural spans/supports are unsurveyed, not load-certified.',
             'Portal opening floorZ0, headroom320cm,width300cm; verify actual live capsule/continuous walking and platform contact seam.',
             'Native import, save/reopen, visual review of below-bridge gap/support treatment, fresh cook and package remain required.']}
    (OUT/'opening-v2-spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    (OUT/'opening-v2-checks.json').write_text(json.dumps(check,indent=2)+'\n')
    print(json.dumps(check,indent=2))


if __name__=='__main__': main()
