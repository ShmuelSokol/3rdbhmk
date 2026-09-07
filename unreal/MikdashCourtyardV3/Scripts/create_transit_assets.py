"""Original TransitV2 offline bus cabin + illustrative future station/track.

Preserves frozen V1. Only explicit run_native() imports assets; no map operations.
All geometry authored in Unreal XYZ centimeters. Bus +X forward, +Y door side.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'SourceAssets/arrival-review/TransitV2'
DEST='/Game/MikdashV3/ArrivalReview/TransitV2'
HELPER=ROOT/'Scripts/create_arrival_assets.py'
spec=importlib.util.spec_from_file_location('_arrival_v1_readonly',HELPER)
G=importlib.util.module_from_spec(spec)
_old_bytecode=sys.dont_write_bytecode
try:
    sys.dont_write_bytecode=True;spec.loader.exec_module(G)
finally:sys.dont_write_bytecode=_old_bytecode
PALETTE=dict(G.PALETTE)
PALETTE.update({
    'Glass':([.16,.28,.32],0,.08),
    'SeatFabric':([.055,.16,.18],0,.83),
    'CabinFloor':([.12,.13,.135],0,.92),
    'CabinLining':([.68,.67,.6],0,.72),
    'SafetyYellow':([.9,.63,.06],0,.58),
    'PlatformStone':([.56,.50,.40],0,.87),
    'TrackSteel':([.25,.27,.29],.85,.35),
    'SleeperConcrete':([.36,.35,.31],0,.93),
    'Ballast':([.20,.18,.15],0,.98),
    'CanopyMetal':([.61,.64,.60],.5,.42),
    'BenchWood':([.26,.12,.045],0,.8),
})


def rod(a,b,r,segments=12):
    axis=tuple(b[i]-a[i] for i in range(3));length=math.sqrt(G.dot(axis,axis));axis=tuple(v/length for v in axis)
    ref=(0,0,1) if abs(axis[2])<.9 else (0,1,0)
    u=G.cross(axis,ref);ul=math.sqrt(G.dot(u,u));u=tuple(v/ul for v in u);v=G.cross(axis,u)
    vertices=[]
    for center in (a,b):
        for j in range(segments):
            t=j*math.tau/segments;vertices.append(tuple(center[i]+r*(math.cos(t)*u[i]+math.sin(t)*v[i]) for i in range(3)))
    faces=[]
    for j in range(1,segments-1):faces.extend([(0,j+1,j),(segments,segments+j,segments+j+1)])
    for j in range(segments):
        k=(j+1)%segments;faces.extend([(j,k,segments+k),(j,segments+k,segments+j)])
    return G.orient(vertices,faces)


def ring(center,radius,tube,segments=32):
    # Steering wheel lies in YZ plane, faces driver along -X.
    vertices=[];faces=[]
    for j in range(segments):
        a=j*math.tau/segments
        for k in range(8):
            b=k*math.tau/8;r=radius+tube*math.cos(b)
            vertices.append((center[0]+tube*math.sin(b),center[1]+r*math.cos(a),center[2]+r*math.sin(a)))
    for j in range(segments):
        for k in range(8):
            a=j*8+k;b=((j+1)%segments)*8+k;c=((j+1)%segments)*8+(k+1)%8;d=j*8+(k+1)%8
            faces.extend([(a,b,c),(a,c,d)])
    return G.orient(vertices,faces)


def builders(parts):
    def add(name,mat,mesh):parts.append(dict(name=name,material=mat,vertices=mesh[0],triangles=mesh[1]))
    def box(name,mat,c,s,bevel=1.5):add(name,mat,G.box(c,s,bevel))
    def pole(name,mat,a,b,r=1.8,segments=12):add(name,mat,rod(a,b,r,segments))
    return add,box,pole


def bus():
    # Full window backing and opaque door leaves must be removed, not hidden
    # behind translucent glass. This is a complete replacement bus, not an overlay.
    removed=('WindowGasket_','EndUpper_','DoorFrame_')
    parts=[p for p in G.assembly() if not p['name'].startswith(removed)]
    add,b,pole=builders(parts)
    for side in (-1,1):
        for z in (159,265):b('OpenFrameRail_%s_%s'%(side,z),'DarkTrim',(0,side*122,z),(1152,6,8),1)
        for x in (-570,-402,-234,-66,102,270,438,570):b('OpenFramePost_%s_%s'%(side,x),'DarkTrim',(x,side*122,212),(9,6,110),1)
    for front in (-1,1):
        for z in (164,273,296):b('EndFrameHorizontal_%s_%s'%(front,z),'DarkTrim',(front*587,0,z),(19,230,10),1)
        for side in (-1,1):
            add('EndCornerFrame_%s_%s'%(front,side),'DarkTrim',G.prism([(side*112,157),(side*124,157),(side*119,284),(side*107,299),(side*100,291)],19,0,(front*583,0,0)))
        b('DestinationBacking_%s'%front,'DarkTrim',(front*587,0,284),(17,162,23),2)
    for door,x,w in [('Front',506,116),('Middle',18,142)]:
        for px in (x-w/2-2,x,x+w/2+2):b('DoorVerticalFrame_%s_%s'%(door,px),'Rubber',(px,127,163),(5,5,199),1)
        for z in (65,260):b('DoorHorizontalFrame_%s_%s'%(door,z),'Rubber',(x,127,z),(w+8,5,5),1)
    b('CabinFloor','CabinFloor',(0,0,91),(1130,226,4),3)
    b('InteriorCeiling','CabinLining',(0,0,293),(1130,218,4),4)
    for side in (-1,1):
        b('InteriorLowerSide_%s'%side,'CabinLining',(0,side*115,125),(1130,3,61),1)
        for x in (-360,360):b('Wheelhouse_%s_%s'%(side,x),'CabinLining',(x,side*96,110),(136,41,34),8)
    def seat(name,x,y,width=42):
        b(name+'_Base','DarkTrim',(x,y,119),(37,width-5,6),3)
        b(name+'_Cushion','SeatFabric',(x+1,y,127),(43,width,10),5)
        # Reclined seat back: bottom at x-19, head at x-31.
        add(name+'_Back','SeatFabric',G.prism([(x-20,129),(x-12,130),(x-24,205),(x-34,209),(x-37,201)],width,1,(0,y,0)))
        for dx in (-12,12):pole(name+'_Leg_%s'%dx,'Aluminium',(x+dx,y,94),(x+dx,y,118),2)
        pole(name+'_Grab','Aluminium',(x-34,y-width/2+4,211),(x-34,y+width/2-4,211),1.4)
    for row,x in enumerate((-480,-240,-150,135,225)):
        for side in (-1,1):
            for col,y in enumerate((48,92)):seat('PassengerSeat_%s_%s_%s'%(row,side,col),x,side*y)
    seat('DriverSeat',451,-67,43)
    b('DriverPedestal','DarkTrim',(449,-67,107),(42,43,26),3)
    b('DriverDashboard','DarkTrim',(547,-63,149),(56,96,30),9)
    b('DriverInstrumentPanel','Rubber',(517,-66,166),(4,60,19),2)
    for i,y in enumerate((-85,-66,-47)):
        add('DriverGauge_%s'%i,'Glass',rod((513,y,167),(514,y,167),6,24))
        pole('GaugeNeedle_%s'%i,'Headlamp',(512,y,167),(512,y+2,171),.45,8)
    pole('SteeringColumn','DarkTrim',(526,-64,131),(501,-64,172),3)
    add('SteeringWheel','Rubber',ring((500,-64,177),18,1.6))
    for j in range(3):
        a=j*math.tau/3;pole('SteeringSpoke_%s'%j,'DarkTrim',(500,-64,177),(500,-64+17*math.cos(a),177+17*math.sin(a)),1.5)
    for y in (-76,-58):b('DriverPedal_%s'%y,'Rubber',(505,y,97),(13,9,3),1)
    b('DriverPartitionLower','CabinLining',(416,-70,132),(4,90,75),1)
    b('DriverPartitionGlass','Glass',(416,-70,216),(2,90,91),1)
    for x in (-270,-90,100,285):
        for side in (-1,1):pole('AislePole_%s_%s'%(x,side),'SafetyYellow',(x,side*38,94),(x,side*38,286),1.6)
    for side in (-1,1):pole('OverheadRail_%s'%side,'SafetyYellow',(-520,side*37,253),(330,side*37,253),1.7)
    for x in (-405,-195,15,225):
        for side in (-1,1):
            pole('HandholdDrop_%s_%s'%(x,side),'DarkTrim',(x,side*37,253),(x,side*37,235),.8)
            pole('HandholdGrip_%s_%s'%(x,side),'DarkTrim',(x-5,side*37,234),(x+5,side*37,234),1.2)
    return parts


def station():
    parts=[];add,b,pole=builders(parts)
    # Authored modular future station. Local top datum Z55, no world placement.
    b('PlatformFoundation','SleeperConcrete',(0,300,24),(6000,600,48),5)
    # Individually named large paving units give editable joint layout.
    for ix in range(40):
        for iy in range(4):b('Paving_%s_%s'%(ix,iy),'PlatformStone',(-2925+150*ix,75+150*iy,51.5),(149,149,7),1)
    b('EdgeCoping','PlatformStone',(0,10,51.5),(6000,20,7),1)
    b('SafetyLine','SafetyYellow',(0,36,55.15),(5998,10,.3),.1)
    # Tactile rib band is geometric/artistic, no accessibility certification.
    for i in range(200):
        for y in (56,69):b('TactileRib_%s_%s'%(i,y),'SafetyYellow',(-2985+30*i,y,55.8),(13,5,1.6),1)
    for side in (-1,1):
        x0=side*3000;x1=side*4100
        add('EndRamp_%s'%side,'PlatformStone',G.prism([(x0,0),(x1,0),(x0,55)],180,1,(0,300,0)))
        for y in (202,398):
            pole('RampRail_%s_%s'%(side,y),'Aluminium',(x0,y,151),(x1,y,96),2.4)
            for t in (0,.25,.5,.75,1):
                x=x0+(x1-x0)*t;z=55*(1-t)
                pole('RampPost_%s_%s_%s'%(side,y,t),'Aluminium',(x,y,z),(x,y,z+96),2.2)
    # Rear columns leave the front platform unobstructed, clear headroom 350cm.
    for x in (-2250,-1350,-450,450,1350,2250):
        b('ColumnFoot_%s'%x,'Aluminium',(x,500,61),(34,34,12),2)
        pole('CanopyColumn_%s'%x,'CanopyMetal',(x,500,67),(x,500,422),9,16)
        pole('CanopyCantilever_%s'%x,'CanopyMetal',(x,500,420),(x,55,420),7,12)
        pole('CanopyBrace_%s'%x,'CanopyMetal',(x,500,320),(x,285,419),5,12)
    add('CanopyRoof','CanopyMetal',G.prism([(30,428),(545,436),(545,447),(30,439)],4700,0))
    b('CanopyFascia','TealPaint',(0,30,436),(4700,8,24),2)
    b('CanopyGutter','DarkTrim',(0,548,431),(4700,13,10),2)
    for x in (-2250,2250):pole('Downpipe_%s'%x,'DarkTrim',(x,550,431),(x,550,57),3,12)
    for x in (-1500,0,1500):
        for k in range(5):b('BenchSlat_%s_%s'%(x,k),'BenchWood',(x,443+k*10,102),(180,8,5),1)
        for dx in (-66,66):
            b('BenchLeg_%s_%s'%(x,dx),'DarkTrim',(x+dx,464,78),(7,49,42),1)
            pole('BenchBackPost_%s_%s'%(x,dx),'DarkTrim',(x+dx,489,99),(x+dx,505,151),2.5)
        for z in (124,137,150):b('BenchBackSlat_%s_%s'%(x,z),'BenchWood',(x,495+(z-124)*.3,z),(180,5,10),1)
    # Windbreaks behind benches; real glazing avoids a blank solid wall.
    for i,x in enumerate((-1650,-1150,-650,650,1150,1650)):
        b('WindScreen_%s'%i,'Glass',(x,585,174),(475,2,230),1)
        for px in (x-244,x+244):pole('WindScreenPost_%s_%s'%(i,px),'Aluminium',(px,585,55),(px,585,295),3)
    for x in (-2300,2300):
        pole('InfoPost_%s'%x,'Aluminium',(x,485,55),(x,485,276),4)
        b('InfoPanelFrame_%s'%x,'DarkTrim',(x,482,238),(112,8,85),4)
        b('InfoPanelBlank_%s'%x,'Headlamp',(x,477,238),(99,1,73),1)
    b('TicketCabinet','TealPaint',(-2700,500,135),(55,55,160),5)
    b('TicketDisplay','Glass',(-2700,471,166),(40,2,40),2)
    b('TicketSlot','DarkTrim',(-2700,471,130),(22,2,3),.5)
    # Track: one illustrative standard-gauge dimension (143.5cm), no real route.
    b('BallastBed','Ballast',(0,-240,1.5),(7000,330,3),5)
    for i in range(108):
        x=-3475+i*65
        b('Sleeper_%03d'%i,'SleeperConcrete',(x,-240,7),(23,250,11),2)
        for y in (-315.25,-164.75):
            b('RailSeat_%s_%s'%(i,y),'DarkTrim',(x,y,13),(21,24,2),1)
            for side in (-1,1):b('RailClip_%s_%s_%s'%(i,y,side),'TrackSteel',(x,y+side*9,16),(10,4,4),.5)
    for side in (-1,1):
        # Railhead inner edges are exactly 143.5cm apart.
        y=-240+side*(71.75+3.5)
        profile=[(y-7,14),(y+7,14),(y+7,16),(y+1.5,17),(y+1.5,24),(y+3.5,25),(y+3.5,28),(y-3.5,28),(y-3.5,25),(y-1.5,24),(y-1.5,17),(y-7,16)]
        # Concave I cross-section split into three closed convex strips.
        for label,poly in [('Foot',[(y-7,14),(y+7,14),(y+7,16),(y-7,16)]),('Web',[(y-1.5,16),(y+1.5,16),(y+1.5,25),(y-1.5,25)]),('Head',[(y-3.5,25),(y+3.5,25),(y+3.5,28),(y-3.5,28)])]:
            add('Rail_%s_%s'%(side,label),'TrackSteel',G.prism(poly,7000,0))
    # Move the full track toward the platform: center Y-150, proposed 280cm
    # carriage width would leave a 10cm body-to-platform gap. Vehicle not built.
    for part in parts:
        if part['name'].startswith(('BallastBed','Sleeper_','RailSeat_','RailClip_','Rail_')):
            part['vertices']=[(x,y+90,z) for x,y,z in part['vertices']]
    return parts


def check_parts(parts):
    names=set();minimum=1e30;minvolume=1e30
    for p in parts:
        assert p['name'] not in names,p['name'];names.add(p['name']);v=p['vertices'];edges={}
        for a,b,c in p['triangles']:
            ab=[v[b][i]-v[a][i] for i in range(3)];ac=[v[c][i]-v[a][i] for i in range(3)]
            n=G.cross(ab,ac);area=math.sqrt(G.dot(n,n))/2;assert area>1e-8,p['name'];minimum=min(minimum,area)
            for i,j in [(a,b),(b,c),(c,a)]:
                key=tuple(sorted((i,j)));edges[key]=edges.get(key,0)+1
        assert all(n==2 for n in edges.values()),p['name']
        volume=sum(G.dot(v[a],G.cross(v[b],v[c])) for a,b,c in p['triangles'])/6
        assert volume>0 and all(math.isfinite(c) for pt in v for c in pt),p['name'];minvolume=min(minvolume,volume)
    return dict(parts=len(parts),triangles=sum(len(p['triangles']) for p in parts),closed_parts=True,min_triangle_area_cm2=minimum,min_signed_volume_cm3=minvolume,bounds_cm=G.bounds([v for p in parts for v in p['vertices']]))


def export():
    if (OUT/'frozen-file-manifest.json').exists():raise RuntimeError('Frozen generated version exists; preserve it')
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='offline_checked_native_pending',palette=PALETTE,imports=[],assemblies={},source_v1_helper_sha256=hashlib.sha256(HELPER.read_bytes()).hexdigest())
    for label,parts in [('Bus',bus()),('Station',station())]:
        report['assemblies'][label]=check_parts(parts)
        (OUT/(label.lower()+'-editable.mesh.json')).write_text(json.dumps(dict(units='cm',parts=parts),separators=(',',':'))+'\n')
        G.write_obj(OUT/(label.lower()+'-canonical.obj'),parts,False)
        for mat in PALETTE:
            selected=[p for p in parts if p['material']==mat]
            if not selected:continue
            name='SM_TransitV2_'+label+'_'+mat;path=OUT/(name+'.obj');G.write_obj(path,selected,True)
            report['imports'].append(dict(assembly=label,name=name,material=mat,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),triangles=sum(len(p['triangles']) for p in selected),bounds_cm=G.bounds([v for p in selected for v in p['vertices']])))
    (OUT/'offline-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['assemblies'],indent=2))
    return report


def run_native():
    """Root-only isolated assets; no map/actor/engine jobs. Never rerun blindly."""
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve()==ROOT
    assert not ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem);assert not assets.does_directory_exist(DEST),'Preserve previous partial assets'
    report=json.loads((OUT/'offline-checks.json').read_text());receipt=dict(status='started',created=[])
    try:
        tools=ue.AssetToolsHelpers.get_asset_tools();ml=ue.MaterialEditingLibrary;materials={}
        for name in sorted(set(r['material'] for r in report['imports'])):
            color,metal,rough=report['palette'][name]
            mat=tools.create_asset('M_TransitV2_'+name,DEST+'/Materials',ue.Material,ue.MaterialFactoryNew())
            node=ml.create_material_expression(mat,ue.MaterialExpressionConstant3Vector);node.set_editor_property('constant',ue.LinearColor(*color,1))
            assert ml.connect_material_property(node,'',ue.MaterialProperty.MP_BASE_COLOR)
            properties=[(metal,ue.MaterialProperty.MP_METALLIC),(rough,ue.MaterialProperty.MP_ROUGHNESS)]
            if name=='Glass':
                mat.set_editor_property('blend_mode',ue.BlendMode.BLEND_TRANSLUCENT)
                mat.set_editor_property('translucency_lighting_mode',ue.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
                properties.append((.18,ue.MaterialProperty.MP_OPACITY))
            for value,prop in properties:
                node=ml.create_material_expression(mat,ue.MaterialExpressionConstant);node.set_editor_property('r',value)
                assert ml.connect_material_property(node,'',prop)
            ml.recompile_material(mat);assert assets.save_loaded_asset(mat,only_if_is_dirty=False)
            if name=='Glass':assert mat.get_editor_property('blend_mode')==ue.BlendMode.BLEND_TRANSLUCENT
            materials[name]=mat;receipt['created'].append(mat.get_path_name())
        for rec in report['imports']:
            path=OUT/rec['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==rec['sha256']
            ui=ue.FbxImportUI()
            for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(key,value)
            data=ui.get_editor_property('static_mesh_import_data')
            for key,value in dict(combine_meshes=True,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,import_uniform_scale=1.0,auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(key,value)
            task=ue.AssetImportTask()
            for key,value in dict(filename=str(path),destination_path=DEST+'/'+rec['assembly'],destination_name=rec['name'],automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=ue.FbxFactory()).items():task.set_editor_property(key,value)
            tools.import_asset_tasks([task]);objects=list(task.get_objects());assert len(objects)==1 and isinstance(objects[0],ue.StaticMesh)
            mesh=objects[0];box=mesh.get_bounding_box();actual=dict(min=[box.min.x,box.min.y,box.min.z],max=[box.max.x,box.max.y,box.max.z])
            assert max(abs(actual[k][i]-rec['bounds_cm'][k][i]) for k in actual for i in range(3))<.05
            assert mesh.get_num_triangles(0)==rec['triangles']
            mesh.set_material(0,materials[rec['material']]);assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
            receipt['created'].append(mesh.get_path_name())
        receipt['status']='assets_saved_unplaced_native_visual_collision_motion_pending'
    except Exception as exc:receipt.update(status='failed_partial_assets_preserved',error=str(exc));raise
    finally:(OUT/'native-import.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--export',action='store_true');a=p.parse_args()
    if a.export:export()
    else:p.error('Use --export offline; root invokes run_native() separately')
