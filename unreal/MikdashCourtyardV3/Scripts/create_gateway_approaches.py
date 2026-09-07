"""Offline four-direction gateway audit; generate only genuinely missing links.

Current measured source already has E/N/S stairs and no western gateway.
Consequently the checked output mesh list is empty; do not duplicate architecture.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'SourceAssets/mount-access/GatewayV3'
sys.path.insert(0,str(ROOT/'SourceAssets/FutureMountV1/.tools'))
import shapely
from shapely.geometry import Polygon,box


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest_path=ROOT/'SourceAssets/architecture-manifest.json'
    model_path=Path('C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/cloud-unreal-v3/model-reference.json')
    platform_path=ROOT/'SourceAssets/FutureMountV1/mount-platform.mesh.json'
    inventory_path=ROOT/'SourceAssets/architecture-current-inventory.json'
    manifest=json.loads(manifest_path.read_text());model=json.loads(model_path.read_text())
    assert sha(model_path)==manifest['sourceModelSha256']
    inventory=json.loads(inventory_path.read_text())
    assert inventory['manifestSha256']==sha(manifest_path)
    native={r['assetName']:r for r in inventory['checks']}
    meshes=manifest['meshes'];elements=model['elements']
    platform=json.loads(platform_path.read_text())['surface']
    faces=platform.get('triangles',platform.get('faces'))
    assert faces
    vertices=platform['vertices']
    assert all(abs(p[2])<1e-8 for p in vertices)
    deck=shapely.union_all([Polygon([(vertices[i][0],vertices[i][1]) for i in tri]) for tri in faces])
    design=json.loads((ROOT/'SourceAssets/visual-review/mount-platform-design.json').read_text())
    guards=shapely.union_all([Polygon(p['nativeXYcm']).buffer(200) for p in design['protected']])
    def record(m):
        ids=m['sourceModelIndices'];assert len(ids)==1
        e=elements[ids[0]];assert e['shape']=='box'
        rawlo=[(e['position'][i]-e['size'][i]/2)*50 for i in [0,2,1]]
        rawhi=[(e['position'][i]+e['size'][i]/2)*50 for i in [0,2,1]]
        b=m['expectedBoundsUnrealCm']
        assert max(abs(a-c) for raw,end in [(rawlo,b['min']),(rawhi,b['max'])] for a,c in zip(raw,end))<.01
        assert not native[m['assetName']]['failures']
        return {'assetName':m['assetName'],'sourceModelIndex':ids[0],
                'boundsUEcm':b,'nativeHistoricalComponent':native[m['assetName']]['component'],
                'historicalNativeInventoryFailures':native[m['assetName']]['failures'],
                'nativeEvidenceScope':'Previously reconciled Courtyard component; current future-map actor presence and walking require native recheck.'}
    reports=[];routes=[]
    for direction,axis,sign in [('E',0,1),('N',1,-1),('S',1,1)]:
        prefix='Outer '+direction+' '
        flight=[m for m in meshes if m['sourceName'].startswith(prefix+'stair ')]
        terraces=[m for m in meshes if m['sourceName']==prefix+'mount approach terrace']
        stairs=sorted(flight+terraces,key=lambda m:m['expectedBoundsUnrealCm']['max'][2])
        assert len(stairs)==(12 if direction=='E' else 17)
        sections=[record(m) for m in stairs]
        previous_outer=None;previous_top=0
        for r in sections:
            b=r['boundsUEcm'];lo,hi=b['min'],b['max']
            outer=max(sign*lo[axis],sign*hi[axis]);inner=min(sign*lo[axis],sign*hi[axis])
            assert abs(outer-inner-50)<.01
            assert abs(hi[2]-previous_top-25)<.01
            if previous_outer is not None:assert abs(outer-previous_outer)<.01
            previous_outer=inner;previous_top=hi[2]
        landing=next(m for m in meshes if m['sourceName']==prefix+'cell access landing')
        threshold=next(m for m in meshes if m['sourceName']==prefix+'threshold')
        vestibule=next(m for m in meshes if m['sourceName']==prefix+'vestibule floor')
        landings=[record(m) for m in [landing,threshold,vestibule]]
        for r in landings:
            b=r['boundsUEcm'];outer=max(sign*b['min'][axis],sign*b['max'][axis]);inner=min(sign*b['min'][axis],sign*b['max'][axis])
            assert abs(outer-previous_outer)<.01 and abs(b['max'][2]-previous_top)<.01
            previous_outer=inner
        first=sections[0]['boundsUEcm'];outer=max(sign*first['min'][axis],sign*first['max'][axis])
        #200cm of Z0 deck immediately before the first measured riser.
        side=1-axis;width=first['max'][side]-first['min'][side]
        xy0=[0,0];xy1=[0,0]
        xy0[side]=-width/2;xy1[side]=width/2
        xy0[axis]=min(sign*outer,sign*(outer+200));xy1[axis]=max(sign*outer,sign*(outer+200))
        bottom=box(xy0[0],xy0[1],xy1[0],xy1[1])
        footprint=shapely.union_all([box(r['boundsUEcm']['min'][0],r['boundsUEcm']['min'][1],r['boundsUEcm']['max'][0],r['boundsUEcm']['max'][1]) for r in sections+landings]+[bottom])
        assert bottom.difference(deck).area<.01
        assert footprint.intersection(guards).area<.01
        waypoints=[]
        p=[0.,0.,0.];p[axis]=sign*(outer+100);waypoints.append({'floorUEcm':p,'surface':'Z0 platform'})
        for r in sections+landings:
            b=r['boundsUEcm'];p=[(b['min'][0]+b['max'][0])/2,(b['min'][1]+b['max'][1])/2,b['max'][2]]
            waypoints.append({'floorUEcm':p,'surface':r['assetName']})
        reports.append({'direction':direction,'decision':'NO_NEW_GEOMETRY_EXISTING_SOURCE_LINK_COMPLETE_TO_VESTIBULE',
            'stairCount':len(flight),'approachTerraceRiserCount':len(terraces),'totalRiserCount':len(stairs),
            'uniformRiseCm':25,'uniformRunCm':50,'startPlatformZcm':0,'vestibuleZcm':previous_top,
            'minimumMeasuredStairWidthCm':500,'approachTerraceWidthCm':800 if terraces else None,
            'cellAccessLandingRunCm':500,'cellAccessLandingWidthCm':1250,'thresholdWidthCm':500,
            'bottomPlatformFootprintUEcm':list(bottom.exterior.coords),
            'bottomPlatformUncoveredAreaCm2':bottom.difference(deck).area,
            'routeProtectedBufferOverlapCm2':footprint.intersection(guards).area,
            'measuredSteps':sections,'measuredLandingThresholdVestibule':landings,
            'note':'North/South425cm is the measured gateway level, not outer court300cm. This audit ends at vestibule; interior transitions/access remain separate native checks.'})
        routes.append({'direction':direction,'status':'NATIVE_TEST_INPUT_ONLY_NOT_EXECUTED','floorWaypoints':waypoints,
                       'suggestedCapsuleHalfHeightCm':96,'instruction':'Use bounded continuous input along route, never teleport between points; confirm floor/collision/mouse release first.'})
    western=[(i,e) for i,e in enumerate(elements) if e['name']=='Western court wall']
    assert len(western)==1
    wi,we=western[0]
    assert we['shape']=='box' and we['position']==[-159,38.5,0] and we['size']==[6,60,324]
    union=next(m for m in meshes if wi in m['sourceModelIndices'])
    assert 'outer_envelope' in union['assetName'] and not native[union['assetName']]['failures']
    assert not any(m['sourceName'].startswith('Outer W ') for m in meshes)
    reports.append({'direction':'W','decision':'NO_SOURCE_GATE_DO_NOT_INVENT_OPENING_OR_STAIRS',
        'sourceModelIndex':wi,'sourceElement':we,'wallBoundsUEcm':{'min':[-8100,-8100,425],'max':[-7800,8100,3425]},
        'nativeUnionAssetName':union['assetName'],'historicalNativeComponent':native[union['assetName']]['component'],
        'instruction':'Continuous source western wall is part of shared outer-envelope union. Preserve union and route around exterior platform to existingN/S/E gates. Do not cut wall or add a western doorway.'})
    # Recheck source package freeze boundaries; no prior authored outputs altered.
    preserved=[]
    for rel in ['SourceAssets/mount-access/frozen-files.json','SourceAssets/mount-access/OpeningV2/frozen-files.json']:
        frozen=json.loads((ROOT/rel).read_text())
        for entry in frozen['files']:assert sha(ROOT/entry['path'])==entry['sha256']
        preserved.append({'manifest':rel,'verifiedFileCount':len(frozen['files'])})
    out={'status':'PASS_OFFLINE_SOURCE_AND_PLATFORM_AUDIT','newMeshCount':0,'newGeometryNeeded':False,
         'directions':reports,'preservedPackages':preserved,
         'sources':[{'path':str(p),'sha256':sha(p)} for p in [manifest_path,model_path,platform_path,inventory_path]],
         'limitations':['Historical native inventory supports source identity, not current walking acceptance.',
                        'Platform coverage is against generated source triangle union, not live collision.',
                        'No new stairs/ramp geometry is justified by current source. Existing25cm risers are preserved measured design, not an accessibility certification.',
                        'North/South vestibule-to-court interior height transitions are outside this exterior approach audit.',
                        'Live headroom, capsule collision, gate presence and return walking require native review.']}
    (OUT/'gateway-approach-audit.json').write_text(json.dumps(out,indent=2)+'\n')
    (OUT/'native-route-inputs.json').write_text(json.dumps({'routes':routes},indent=2)+'\n')
    (OUT/'gateway-v3.mesh.json').write_text(json.dumps({'meshes':[],'reason':'All source outer gateways already connected to Z0 platform; west has no measured gate.'},indent=2)+'\n')
    print(json.dumps({'status':out['status'],'newMeshCount':0,'directions':[(r['direction'],r['decision']) for r in reports]},indent=2))


if __name__=='__main__':main()
