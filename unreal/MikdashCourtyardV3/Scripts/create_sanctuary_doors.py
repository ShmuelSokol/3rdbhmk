"""Original folding leaves and paroches study. Offline --export; no map actions.

Native import reuses the frozen palm helper and existing reviewed materials.
Source topology and fit are verified offline; motion and native acceptance pending.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT=ROOT/'SourceAssets/sanctuary-detail/DoorsParochesV1'
DEST='/Game/MikdashV3/MaterialReview/SanctuaryDoorsParochesV1'
MANIFEST_SHA='40c4a0feae391868c6c840f76bc72f0df0bab8c3be9406c6b5dbb6f508f9333d'


def module(name,filename):
    s=importlib.util.spec_from_file_location(name,ROOT/'Scripts'/filename)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def openings():
    path=ROOT/'SourceAssets/architecture-manifest.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==MANIFEST_SHA
    records=json.loads(path.read_text(encoding='utf-8-sig'))['meshes']
    house=next(r for r in records if r['assetName'].startswith('SM_2630'))
    e=json.loads(house['sourceProperties']['source_elements_json'])
    lintel=next(a for a in e if a['name']=='Heichal ten-amah doorway lintel')
    bottom=(lintel['position'][1]-lintel['size'][1]/2)*50
    floor=next(r['expectedBoundsUnrealCm']['max'][2] for r in records if r['sourceName']=='Heichal clear floor')
    shoulder=next(r['expectedBoundsUnrealCm'] for r in records if r['sourceName']=='Kodesh partition shoulder' and r['expectedBoundsUnrealCm']['min'][1]>0)
    kl=next(r['expectedBoundsUnrealCm'] for r in records if r['sourceName']=='Kodesh partition lintel')
    result=dict(Heichal=dict(width_cm=lintel['size'][2]*50,height_cm=bottom-floor,floor_z_cm=floor,x_min_cm=-3600,x_max_cm=-3300),
                Kodesh=dict(width_cm=shoulder['min'][1]*2,height_cm=kl['min'][2]-floor,floor_z_cm=floor,x_min_cm=kl['min'][0],x_max_cm=kl['max'][0]))
    assert result['Heichal']['height_cm']==2500 and result['Kodesh']['height_cm']==300
    return result


def cylinder(radius,height,center=(0,0,0),segments=24):
    vertices=[]
    for z in (-height/2,height/2):
        for i in range(segments):
            a=i*math.tau/segments
            vertices.append((center[0]+radius*math.cos(a),center[1]+radius*math.sin(a),center[2]+z))
    faces=[]
    for i in range(segments):
        j=(i+1)%segments
        faces.extend([(i,j,segments+j),(i,segments+j,segments+i)])
    for i in range(1,segments-1): faces.extend([(0,i+1,i),(segments,segments+i,segments+i+1)])
    return vertices,faces


def cloth_patch(x0,x1,z0,z1,nx,nz,offset=0,thickness=.6):
    """Sealed draped grid; 12 flowing folds with lower-edge weight variation."""
    vertices=[]
    def point(x,z,side):
        t=z/306
        y=7*math.cos((x+180)/360*math.tau*12+.18*math.sin(t*math.pi))*(.85+.15*(1-t))
        y+=1.8*math.sin(t*math.pi)*math.sin(x/40)
        sag=.6*(1-t)*math.sin((x+180)/360*math.tau*12)**2
        return (x,y+offset+side*thickness/2,z+sag)
    for side in (-1,1):
        for j in range(nz+1):
            for i in range(nx+1): vertices.append(point(x0+(x1-x0)*i/nx,z0+(z1-z0)*j/nz,side))
    faces=[]; size=(nx+1)*(nz+1)
    for j in range(nz):
        for i in range(nx):
            a=j*(nx+1)+i; b=a+1; c=b+nx+1; d=a+nx+1
            faces.extend([(a,b,c),(a,c,d),(a+size,c+size,b+size),(a+size,d+size,c+size)])
    boundary=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,nz+1)]+[nz*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(nz-1,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]): faces.extend([(a,a+size,b+size),(a,b+size,b)])
    palm=module('_door_orient','create_sanctuary_reliefs.py')
    if palm.volume(vertices,faces)<0: faces=[(a,c,b) for a,b,c in faces]
    return vertices,faces


def geometry():
    bevel=module('_door_bevel','create_heikhal_keilim.py')
    palm=module('_door_blade','create_sanctuary_reliefs.py')
    result={}
    for room,bay in openings().items():
        nominal=bay['width_cm']/4
        h=bay['height_cm']-4
        width=nominal-1
        body=[('SolidLeaf',bevel.bevel_box((nominal/2,0,h/2),(width,7,h),.6))]
        ornaments=[]; hardware=[]
        # 8 stacked fields on the tall Heichal leaf; one field on the low inner leaf.
        count=8 if room=='Heichal' else 1
        for j in range(count):
            z0=5+j*(h-10)/count; zh=(h-10)/count
            for front in (-1,1):
                for label,c,s in [('L',(7,front*4.2,z0+zh/2),(5,2,zh-4)),('R',(nominal-7,front*4.2,z0+zh/2),(5,2,zh-4)),
                                  ('B',(nominal/2,front*4.2,z0+4),(nominal-15,2,5)),('T',(nominal/2,front*4.2,z0+zh-4),(nominal-15,2,5))]:
                    body.append(('Field_%d_%d_%s'%(j,front,label),bevel.bevel_box(c,s,.4)))
                # Original palm in every field. Fine fronds are relief, not a traced pattern.
                scale=min((nominal-26)/100,(zh-25)/250)
                def blade(label,a,b,c,w,d):
                    v,f=palm.curved_blade(a,b,c,w,d,12)
                    v=[(nominal/2+x*scale,front*(4.6+y*scale),z0+(zh-250*scale)/2+z*scale) for x,y,z in v]
                    if front<0: f=[(a,c,b) for a,b,c in f]
                    ornaments.append(('Palm_%d_%d_%s'%(j,front,label),(v,f)))
                blade('Trunk',(0,0,8),(-2,1,95),(0,0,171),4,1.2)
                for sign in (-1,1):
                    for k,(reach,lift) in enumerate([(16,70),(31,52),(44,30),(47,2),(38,-23),(25,-40)]):
                        blade('Frond_%d_%d'%(sign,k),(0,0,166),(sign*reach*.55,1.8,195+lift*.5),(sign*reach,0,166+lift),3.2,.8)
        for j in range(5 if room=='Heichal' else 3):
            z=18+j*(h-36)/(4 if room=='Heichal' else 2)
            hardware.append(('HingeBarrel_%d'%j,cylinder(2,12,(0,8,z))))
            hardware.append(('HingeStrap_%d'%j,bevel.bevel_box((nominal*.22,4.4,z),(nominal*.38,1.2,5),.3)))
        # Handle mounts kept separately editable; exact hardware is artistic.
        hardware.append(('Handle',bevel.ring((nominal-15,7,min(h*.48,110)),major=4,minor=.65)))
        result['SM_'+room+'FoldingLeafV1']=body
        result['SM_'+room+'DoorPalmReliefV1']=ornaments
        result['SM_'+room+'DoorHardwareV1']=hardware
    result['SM_ParochesClothV1']=[('DrapedCloth',cloth_patch(-180,180,0,306,120,48))]
    hems=[]
    for name,args in [('Lower',(-180,180,0,7,120,2)),('Upper',(-180,180,299,306,120,2)),
                      ('Left',(-180,-173,7,299,3,48)),('Right',(173,180,7,299,3,48))]:
        hems.append((name,cloth_patch(*args,offset=.5,thickness=.25)))
    result['SM_ParochesHemV1']=hems
    fixings=[]
    v,f=cylinder(1.8,382,segments=32)
    fixings.append(('SupportRod',([(z,y+7,313-x) for x,y,z in v],f)))
    for i in range(13):
        x=-180+i*30
        v,f=bevel.ring((0,0,0),major=4,minor=.6)
        fixings.append(('SuspensionRing_%02d'%i,([(-y+x,x0+7,z+310) for x0,y,z in v],f)))
    result['SM_ParochesFixingsV1']=fixings
    return result


def export():
    assert not (OUT/'geometry-manifest.json').exists(), 'Frozen generation preserved'
    OUT.mkdir(parents=True,exist_ok=True)
    palm=module('_door_math','create_sanctuary_reliefs.py')
    report=dict(status='OFFLINE_SOURCE_EXPORTED_NATIVE_PENDING',namespace=DEST,openings=openings(),meshes=[],
                manifest_sha256=MANIFEST_SHA,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                native_helper_sha256=hashlib.sha256((ROOT/'Scripts/create_sanctuary_reliefs.py').read_bytes()).hexdigest())
    editable={}
    for name,parts in geometry().items():
        lines=['# Original sanctuary folding doors/paroches; Unreal legacy OBJ adapter','o '+name]
        index=1; allv=[]; checks=[]; edit=[]
        for part,(vertices,faces) in parts:
            if palm.volume(vertices,faces)<0: faces=[(a,c,b) for a,b,c in faces]
            keys=[tuple(round(x,6) for x in p) for p in vertices]; edges={}
            allv.extend(vertices); lines.append('g '+part)
            for a,b,c in faces:
                for i,j in ((a,b),(b,c),(c,a)):
                    key=tuple(sorted((keys[i],keys[j]))); edges[key]=edges.get(key,0)+1
                p,q,r=[(vertices[i][0],-vertices[i][1],vertices[i][2]) for i in (a,c,b)]
                ab=[q[i]-p[i] for i in range(3)]; ac=[r[i]-p[i] for i in range(3)]
                n=palm.cross(ab,ac); length=math.sqrt(sum(x*x for x in ab)); nl=math.sqrt(sum(x*x for x in n))
                assert nl>1e-8
                for v in (p,q,r): lines.append('v %.9f %.9f %.9f'%v)
                for uv in ((0,0),(length/10,0),(sum(ac[i]*ab[i]/length for i in range(3))/10,nl/length/10)): lines.append('vt %.9f %.9f'%uv)
                for _ in range(3): lines.append('vn %.9f %.9f %.9f'%tuple(x/nl for x in n))
                lines.append('f '+' '.join('%d/%d/%d'%(k,k,k) for k in range(index,index+3))); index+=3
            vol=palm.volume(vertices,faces)
            assert vol>0 and all(n==2 for n in edges.values()), part
            checks.append(dict(name=part,triangles=len(faces),closed=True,volume_cm3=vol))
            edit.append(dict(name=part,vertices_cm=vertices,triangles=faces))
        path=OUT/(name+'.obj'); path.write_text('\n'.join(lines)+'\n',encoding='ascii')
        report['meshes'].append(dict(name=name,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),triangles=(index-1)//3,
            parts=checks,bounds_cm={k:[fn(p[i] for p in allv) for i in range(3)] for k,fn in [('min',min),('max',max)]}))
        editable[name]=edit
    (OUT/'editable-meshes.json').write_text(json.dumps(editable,separators=(',',':'))+'\n')
    (OUT/'geometry-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'placement-and-articulation.json').write_text(json.dumps(placement_plan(),indent=2)+'\n')
    return report


def placement_plan():
    result=dict(status='SOURCE_FIT_PROPOSALS_NATIVE_CLEARANCE_AND_MOTION_PENDING',doors=[],
        convention='Leaf pivot at hinge, nominal local X=0..width/4; front local +Y; bottom Z=0. Paired wood, relief, hardware share every transform.',
        curtain=dict(meshes=['SM_ParochesClothV1','SM_ParochesHemV1','SM_ParochesFixingsV1'],location_cm=[-5585,0,928],yaw_degrees=-90,
            status='Optional closed interpreted veil on Heichal side of Kodesh opening. Blocks view; not a walk-through curtain. No collision/runtime behavior provided.'),
        replace_review_only=['SM_1948_detail_Open_Heichal_door','SM_1949_detail_Open_Heichal_door','SM_1950_detail_Open_Heichal_door','SM_1951_detail_Open_Heichal_door'])
    for room,bay in openings().items():
        nominal=bay['width_cm']/4
        # Heichal two recessed banks follow Rashi's discussed folding interpretation.
        # Kodesh has only100cm depth: one four-leaf bank; no claim of same double-bank recess.
        banks=[bay['x_max_cm']-25,bay['x_min_cm']+25] if room=='Heichal' else [(bay['x_min_cm']+bay['x_max_cm'])/2]
        for bank,x in enumerate(banks):
            for sign in (-1,1):
                yaw=-sign*90
                first=dict(mesh_family=room,bank=bank,side=sign,role='jamb_leaf',
                           closed_location_cm=[x,sign*bay['width_cm']/2,bay['floor_z_cm']+2],closed_yaw_degrees=yaw)
                second=dict(mesh_family=room,bank=bank,side=sign,role='fold_leaf',
                            parent_index=len(result['doors']),closed_local_location_cm=[nominal,0,0],closed_relative_yaw_degrees=0,
                            hinge_axis_in_parent_cm=[nominal,8,0],
                            folded_local_location_cm=[nominal,16,0],fold_target_relative_yaw_degrees=180,
                            fold_formula='For relative angle a: child translation=(nominal+8*sin(a),8-8*cos(a),0). This rotates about the offset barrel axis rather than the mesh origin.',
                            fold_limit='Closed/open endpoints are source-space design only. Jamb swing, shared knuckle manufacture, dynamic collision and animation require native review.')
                result['doors'].extend([first,second])
    result['limitations']=['No automatic placement or primitive removal','Heichal leaf height2496cm follows2500cm source opening, not2000cm veneer',
        'Kodesh leaf height296cm follows measured300cm opening','Hinges/pivots are editable production resources, not collision-tested functional doors',
        'Palms included, cherub relief/cloth weave absent; not final sourced ornamentation','Paroches dimensions are opening-fit interpretation, not historical full-room curtain dimensions']
    return result


def run_native(materials):
    """Root-only isolated import. Supply EXISTING material paths for all9 mesh names."""
    report=json.loads((OUT/'geometry-manifest.json').read_text())
    assert hashlib.sha256((ROOT/'Scripts/create_sanctuary_reliefs.py').read_bytes()).hexdigest()==report['native_helper_sha256']
    helper=module('_doors_isolated_import','create_sanctuary_reliefs.py')
    helper.OUT=OUT; helper.DEST=DEST
    return helper.run_native(materials)


if __name__=='__main__':
    if '--export' not in sys.argv: raise SystemExit('Explicit --export offline, or root-run run_native(materials) inside Unreal')
    report=export()
    print(json.dumps({r['name']:r['triangles'] for r in report['meshes']},indent=2))
