"""TransitV2 hero bus/station (frozen) and TransitSystemV1 instanced traffic.

Two independent sections in two namespaces:
  --export         TransitV2: the offline bus cabin and illustrative future station.
                   Preserves frozen V1. run_native() imports it.
  --export-system  TransitSystemV1: original low-poly car/bus/tram bodies authored
                   for HISM instancing, a bus shelter, a rail platform, and
                   routes.json derived from the retained OSM context roads plus ONE
                   authored future light-rail line. run_native_system() imports it.
  --routes-only    Rewrite TransitSystemV1/routes.json without touching geometry.

Neither native entry point is ever reached by import; root invokes them explicitly.
No map, actor, terrain or road is modified by this file. All geometry is authored in
Unreal XYZ centimetres. TransitV2 bus is +X forward, +Y door side; TransitSystemV1
vehicles are +X forward, +Y left, Z0 at tyre or railhead contact.
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

# ===========================================================================
# TransitSystemV1 -- instanced low-poly traffic, stop furniture and routes.
#
# Everything above this line is the frozen TransitV2 hero bus and station and is
# untouched. What follows is a SEPARATE namespace and a separate output folder: the
# TransitV2 bus is 26,880 triangles across 1,004 parts and 13 material-group meshes,
# which is a fine hero prop and completely unsuitable for a Hierarchical Instanced
# Static Mesh crowd of vehicles. Merging its 13 material groups into one instanced
# mesh is not possible offline without authoring a texture atlas, so this section
# authors NEW low-poly bodies for instancing and leaves TransitV2 as the hero.
#
# Local axes for every vehicle: +X forward, +Y left, Z0 at tyre/railhead contact.
# Units are centimetres throughout. Canonical OBJ/JSON is Unreal XYZ; the
# SM_*.obj adapters are reflected-Y / reversed-winding, per the project convention
# recorded in SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json.
# ===========================================================================

SYSTEM_OUT = ROOT / 'SourceAssets/arrival-review/TransitSystemV1'
SYSTEM_DEST = '/Game/MikdashV3/ArrivalReview/TransitSystemV1'
CONTEXT_ROADS = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\mikdash-walkthrough\public\context\jerusalem.json')

# Alignment from the context road data (amot, +x east, +z south, y up) to Unreal cm.
# Verified against the placed RELEASE_Bus_* at [-37951, 46855, 973]: the terrain grid
# gives 955.5 cm there, 17.5 cm below the placed pivot.
AMOT_TO_UE = dict(x_offset=17.5097, z_offset=0.55135, scale=50.0)

# Four vehicle material groups, deliberately not more. Every extra group is another
# HISM component and another transform write per vehicle per update; four keeps a car
# at four writes. Paint is the only group that varies per instance.
SYSTEM_PALETTE = {
    'Paint':    ([.52, .53, .55], .30, .30),
    'Glass':    ([.045, .075, .09], .0, .08),
    'Dark':     ([.030, .033, .036], .15, .55),
    'Lens':     ([.86, .87, .82], .10, .16),
    'Concrete': ([.52, .51, .47], .0, .90),
    'Steel':    ([.44, .46, .48], .85, .32),
    'Wood':     ([.29, .16, .07], .0, .78),
    'Safety':   ([.88, .62, .06], .0, .55),
}

# Vertex colour carries two authored masks, one per group that uses it:
#   Paint group: R = paint mask (1 = takes the per-instance body colour, 0 = keeps the
#                material base), G = baked panel shade (roof lighter, sills darker).
#   Lens group:  R = 1 on red lamps, 0 on white ones, so head and tail lamps share one
#                mesh, one material and one HISM.
# Per-instance body colour itself is NOT vertex colour -- it is per-instance custom
# data floats 0..2 on the Paint HISM, which is the only way one mesh can give many
# differently coloured cars. See PaintColourFor in TransitMath.h.
NO_COLOUR = (0.0, 0.0, 0.0)


def system_builders(parts):
    """add/box/pole/wheel that also carry a per-part constant vertex colour."""
    def add(name, material, mesh, colour=NO_COLOUR):
        parts.append(dict(name=name, material=material, colour=[float(c) for c in colour],
                          vertices=mesh[0], triangles=mesh[1]))

    def box(name, material, centre, size, bevel=1.5, colour=NO_COLOUR):
        add(name, material, G.box(centre, size, bevel), colour)

    def pole(name, material, a, b, radius=1.8, segments=8, colour=NO_COLOUR):
        add(name, material, rod(a, b, radius, segments), colour)

    def wheel(name, centre, radius, width, segments=12):
        """Low-poly tyre about Y plus an offset hub disc, both in the Dark group."""
        x, y, z = centre
        add(name + '_Tyre', 'Dark', rod((x, y - width / 2, z), (x, y + width / 2, z), radius, segments))
        outer = y + width / 2 if y > 0 else y - width / 2
        inner = outer - 2.0 if y > 0 else outer + 2.0
        add(name + '_Hub', 'Dark', rod((x, inner, z), (x, outer, z), radius * 0.55, 8))

    return add, box, pole, wheel


def paint_shade(z, low, high):
    """Baked vertical panel shade into vertex colour G: sills dark, roof light."""
    span = max(1.0, high - low)
    return (1.0, round(min(1.0, max(0.0, 0.35 + 0.65 * (z - low) / span)), 4), 0.0)


# ---------------------------------------------------------------------------
# Road vehicles
# ---------------------------------------------------------------------------

CAR_VARIANTS = [
    dict(key='Hatchback', length=396.0, width=172.0, roof_z=146.0, wheelbase=250.0,
         wheel_radius=30.0, wheel_width=20.0, boot=False, rails=False),
    dict(key='Sedan', length=452.0, width=180.0, roof_z=144.0, wheelbase=272.0,
         wheel_radius=32.0, wheel_width=21.0, boot=True, rails=False),
    dict(key='Crossover', length=442.0, width=188.0, roof_z=170.0, wheelbase=266.0,
         wheel_radius=36.0, wheel_width=24.0, boot=True, rails=True),
]


def car(spec):
    """One original low-poly passenger car. No manufacturer form, badge or livery."""
    parts = []
    add, box, pole, wheel = system_builders(parts)
    L, W = spec['length'], spec['width']
    R = spec['wheel_radius']
    belt = R + 52.0                     # window line
    roof = spec['roof_z']
    sill = R + 4.0
    half = W / 2.0
    axle = spec['wheelbase'] / 2.0

    def painted(z):
        return paint_shade(z, sill, roof)

    # Body masses.
    box('LowerBody', 'Paint', (0, 0, (sill + belt) / 2), (L * 0.94, W, belt - sill), 9, painted((sill + belt) / 2))
    add('Cabin', 'Paint', G.prism([(-L * 0.40, belt), (L * 0.26, belt), (L * 0.17, roof), (-L * 0.30, roof)],
                                  W * 0.86, 1), painted(roof - 10))
    box('RoofPanel', 'Paint', (-L * 0.06, 0, roof), (L * 0.30, W * 0.80, 6), 3, painted(roof))
    box('Hood', 'Paint', (L * 0.32, 0, belt - 5), (L * 0.30, W * 0.94, 12), 5, painted(belt))
    if spec['boot']:
        box('Boot', 'Paint', (-L * 0.40, 0, belt - 3), (L * 0.16, W * 0.94, 14), 5, painted(belt))

    # Dark structure.
    box('BumperFront', 'Dark', (L * 0.485, 0, sill + 16), (L * 0.05, W * 0.98, 34), 6)
    box('BumperRear', 'Dark', (-L * 0.485, 0, sill + 16), (L * 0.05, W * 0.98, 34), 6)
    box('Grille', 'Dark', (L * 0.48, 0, belt - 14), (6, W * 0.52, 20), 3)
    for side in (-1, 1):
        box('Sill_%d' % side, 'Dark', (0, side * half * 0.97, sill), (L * 0.58, 10, 14), 3)
        box('MirrorArm_%d' % side, 'Dark', (L * 0.16, side * (half + 7), belt + 8), (14, 18, 10), 3)
        for label, x in (('F', axle), ('R', -axle)):
            box('Arch_%s_%d' % (label, side), 'Dark', (x, side * half * 0.95, R + 12), (R * 2.4, 12, 28), 5)
            wheel('Wheel_%s_%d' % (label, side), (x, side * (half - spec['wheel_width'] / 2 - 3), R),
                  R, spec['wheel_width'])
        box('PillarA_%d' % side, 'Dark', (L * 0.20, side * half * 0.86, (belt + roof) / 2), (9, 8, roof - belt), 2)
        box('PillarC_%d' % side, 'Dark', (-L * 0.28, side * half * 0.86, (belt + roof) / 2), (11, 8, roof - belt), 2)
    pole('Exhaust', 'Dark', (-L * 0.47, -W * 0.20, sill + 6), (-L * 0.52, -W * 0.20, sill + 6), 3.2, 8)
    if spec['rails']:
        for side in (-1, 1):
            box('RoofRail_%d' % side, 'Dark', (-L * 0.06, side * W * 0.33, roof + 5), (L * 0.30, 7, 5), 2)

    # Glazing.
    add('Windscreen', 'Glass', G.prism([(L * 0.26, belt), (L * 0.17, roof), (L * 0.10, roof), (L * 0.19, belt)],
                                       W * 0.80, 1))
    add('RearScreen', 'Glass', G.prism([(-L * 0.40, belt), (-L * 0.34, belt), (-L * 0.26, roof), (-L * 0.30, roof)],
                                       W * 0.78, 1))
    for side in (-1, 1):
        box('WindowFront_%d' % side, 'Glass', (L * 0.06, side * half * 0.84, (belt + roof) / 2 + 2),
            (L * 0.22, 3, roof - belt - 10), 2)
        box('WindowRear_%d' % side, 'Glass', (-L * 0.17, side * half * 0.84, (belt + roof) / 2 + 2),
            (L * 0.16, 3, roof - belt - 10), 2)

    # Lamps: vertex colour R marks the red ones so both share one mesh and material.
    for side in (-1, 1):
        box('Headlamp_%d' % side, 'Lens', (L * 0.485, side * W * 0.34, belt - 4), (8, W * 0.20, 14), 3)
        box('Taillamp_%d' % side, 'Lens', (-L * 0.485, side * W * 0.34, belt - 2), (8, W * 0.18, 13), 3, (1.0, 0.0, 0.0))
    return parts


def city_bus():
    """Original low-floor city bus authored for instancing, not the TransitV2 hero."""
    parts = []
    add, box, pole, wheel = system_builders(parts)
    L, W, roof = 1180.0, 252.0, 306.0
    R, sill, belt = 47.0, 34.0, 178.0
    half = W / 2.0

    def painted(z):
        return paint_shade(z, sill, roof)

    box('Skirt', 'Paint', (0, 0, (sill + 96) / 2), (L * 0.97, W, 96 - sill), 8, painted(sill + 20))
    box('LowerBody', 'Paint', (0, 0, (96 + belt) / 2), (L, W, belt - 96), 9, painted(belt - 40))
    box('UpperBody', 'Paint', (0, 0, (belt + roof) / 2), (L, W * 0.99, roof - belt), 9, painted(roof - 30))
    box('RoofPanel', 'Paint', (0, 0, roof), (L * 0.98, W * 0.94, 8), 4, painted(roof))
    box('FrontCap', 'Paint', (L * 0.495, 0, (96 + roof) / 2), (14, W * 0.96, roof - 96), 8, painted(belt))
    box('RearCap', 'Paint', (-L * 0.495, 0, (96 + roof) / 2), (14, W * 0.96, roof - 96), 8, painted(belt))

    box('BumperFront', 'Dark', (L * 0.505, 0, 74), (16, W, 62), 8)
    box('BumperRear', 'Dark', (-L * 0.505, 0, 74), (16, W, 62), 8)
    box('RoofPack', 'Dark', (L * 0.16, 0, roof + 14), (L * 0.34, W * 0.62, 22), 6)
    for side in (-1, 1):
        box('Mirror_%d' % side, 'Dark', (L * 0.45, side * (half + 16), belt + 66), (12, 34, 26), 4)
        for label, x in (('F', L * 0.335), ('M', -L * 0.24), ('R', -L * 0.345)):
            box('Arch_%s_%d' % (label, side), 'Dark', (x, side * half * 0.97, R + 22), (R * 2.6, 12, 44), 6)
            wheel('Wheel_%s_%d' % (label, side), (x, side * (half - 16), R), R, 26)
        # Window band, split by pillars so the body reads as a bus and not a box.
        for i, x in enumerate((-L * 0.40, -L * 0.28, -L * 0.16, -L * 0.04, L * 0.08, L * 0.20)):
            box('SideWindow_%d_%d' % (i, side), 'Glass', (x, side * half * 0.985, (belt + roof) / 2 + 6),
                (L * 0.098, 3, roof - belt - 34), 3)
            box('Pillar_%d_%d' % (i, side), 'Dark', (x + L * 0.06, side * half * 0.99, (belt + roof) / 2),
                (10, 6, roof - belt), 2)
    add('Windscreen', 'Glass', G.prism([(L * 0.50, belt - 6), (L * 0.50, roof - 22), (L * 0.44, roof - 14),
                                        (L * 0.44, belt - 10)], W * 0.90, 1))
    add('RearScreen', 'Glass', G.prism([(-L * 0.50, belt), (-L * 0.44, belt - 4), (-L * 0.44, roof - 30),
                                        (-L * 0.50, roof - 34)], W * 0.88, 1))
    for side in (-1, 1):
        box('Headlamp_%d' % side, 'Lens', (L * 0.508, side * W * 0.36, 104), (9, W * 0.20, 22), 4)
        box('Taillamp_%d' % side, 'Lens', (-L * 0.508, side * W * 0.36, 112), (9, W * 0.18, 30), 4, (1.0, 0.0, 0.0))
        box('Indicator_%d' % side, 'Lens', (L * 0.508, side * W * 0.20, 104), (9, 22, 14), 3, (1.0, 0.0, 0.0))
    # Door apertures on the +Y (kerb) side only: the leaves are a separate mesh so the
    # actor can slide them, and the frame is authored recessed so a shut leaf sits flush.
    for label, x in (('Front', L * 0.36), ('Middle', -L * 0.06)):
        box('DoorFrame_%s' % label, 'Dark', (x, half - 2, (96 + belt + roof - 40) / 2),
            (150, 8, roof - 130), 3)
    return parts


def door_leaf(width, height):
    """One sliding leaf: a painted frame and a glass pane. Instanced per doorway."""
    parts = []
    add, box, pole, wheel = system_builders(parts)
    box('LeafFrame', 'Paint', (0, 0, 0), (width, 7, height), 3, (1.0, 0.72, 0.0))
    box('LeafGlass', 'Glass', (0, 1.5, 6), (width - 18, 3, height - 26), 3)
    return parts


def tram_car(is_cab):
    """One articulated light-rail car. Cab cars sit at both ends of the consist; the
    rear cab is posed with a 180 degree yaw by the actor."""
    parts = []
    add, box, pole, wheel = system_builders(parts)
    L = 1020.0 if is_cab else 900.0
    W, roof = 262.0, 348.0
    floor, belt = 38.0, 214.0
    half = W / 2.0

    def painted(z):
        return paint_shade(z, floor, roof)

    box('Underframe', 'Dark', (0, 0, 26), (L * 0.96, W * 0.90, 34), 6)
    box('LowerBody', 'Paint', (0, 0, (floor + belt) / 2 + 8), (L, W, belt - floor - 16), 9, painted(belt - 60))
    box('UpperBody', 'Paint', (0, 0, (belt + roof) / 2), (L, W * 0.99, roof - belt), 9, painted(roof - 30))
    box('RoofPanel', 'Paint', (0, 0, roof), (L * 0.98, W * 0.92, 9), 4, painted(roof))
    box('RoofPack', 'Dark', (0, 0, roof + 16), (L * 0.62, W * 0.66, 24), 6)
    for side in (-1, 1):
        for i, x in enumerate((-L * 0.34, -L * 0.18, -L * 0.02, L * 0.14)):
            box('SideWindow_%d_%d' % (i, side), 'Glass', (x, side * half * 0.985, (belt + roof) / 2 + 4),
                (L * 0.12, 3, roof - belt - 36), 3)
        box('Skirt_%d' % side, 'Dark', (0, side * half * 0.98, floor + 22), (L * 0.90, 8, 40), 3)
        box('DoorFrame_%d' % side, 'Dark', (L * 0.30 if is_cab else L * 0.24, side * (half - 2),
                                            (floor + roof - 30) / 2), (140, 8, roof - 120), 3)
        # Bogies: two low-poly wheel pairs per car, inset from the ends.
        for label, x in (('F', L * 0.32), ('R', -L * 0.32)):
            wheel('Wheel_%s_%d' % (label, side), (x, side * (half - 34), 34), 34.0, 18.0, 10)
    if is_cab:
        box('CabNose', 'Paint', (L * 0.50, 0, (floor + roof) / 2 + 20), (18, W * 0.94, roof - floor - 70), 10,
            painted(belt))
        add('Windscreen', 'Glass', G.prism([(L * 0.50, belt - 20), (L * 0.50, roof - 26), (L * 0.40, roof - 16),
                                            (L * 0.40, belt - 26)], W * 0.86, 1))
        for side in (-1, 1):
            box('Headlamp_%d' % side, 'Lens', (L * 0.512, side * W * 0.34, 120), (9, W * 0.18, 20), 4)
            box('Taillamp_%d' % side, 'Lens', (L * 0.512, side * W * 0.34, 92), (9, W * 0.16, 14), 3, (1.0, 0.0, 0.0))
    else:
        for end in (-1, 1):
            box('Gangway_%d' % end, 'Dark', (end * L * 0.50, 0, (floor + belt) / 2 + 30), (16, W * 0.80,
                belt - floor + 40), 8)
    return parts


# ---------------------------------------------------------------------------
# Stop furniture
# ---------------------------------------------------------------------------

def bus_shelter():
    """A compact modern kerbside shelter, local origin at the kerb face, +Y toward the
    road. Authored generic street furniture, no municipal design is reproduced."""
    parts = []
    add, box, pole, wheel = system_builders(parts)
    width, depth, height = 420.0, 150.0, 250.0
    for x in (-width / 2 + 8, width / 2 - 8):
        for y in (-depth / 2 + 6, depth / 2 - 6):
            pole('Post_%d_%d' % (int(x), int(y)), 'Steel', (x, y, 0), (x, y, height), 5.0, 8)
    box('CanopyRoof', 'Steel', (0, 0, height + 8), (width + 30, depth + 26, 12), 5)
    box('CanopyFascia', 'Steel', (0, depth / 2 + 12, height + 2), (width + 30, 8, 22), 3)
    box('BackPanel', 'Glass', (0, -depth / 2 + 4, height / 2 + 10), (width - 30, 4, height - 40), 3)
    for x in (-width / 2 + 10, width / 2 - 10):
        box('SidePanel_%d' % int(x), 'Glass', (x, 0, height / 2 + 10), (4, depth - 26, height - 40), 3)
    box('BenchSeat', 'Wood', (0, -depth / 2 + 34, 46), (width - 90, 40, 8), 3)
    for x in (-width / 2 + 50, width / 2 - 50):
        box('BenchLeg_%d' % int(x), 'Steel', (x, -depth / 2 + 34, 23), (7, 36, 46), 2)
    pole('SignPost', 'Steel', (width / 2 + 26, 0, 0), (width / 2 + 26, 0, 240), 4.0, 8)
    box('SignPanel', 'Steel', (width / 2 + 26, 0, 218), (6, 46, 62), 3)
    box('SignBand', 'Safety', (width / 2 + 22, 0, 218), (2, 40, 10), 1)
    return parts


def rail_platform():
    """A compact side platform module, local origin at the platform face at track level,
    +Y away from the track. An illustrative future module, NOT a surveyed station and
    not an accessibility specification: the tactile band and safety line are geometry,
    not compliance."""
    parts = []
    add, box, pole, wheel = system_builders(parts)
    length, depth, top = 3600.0, 420.0, 96.0
    box('Slab', 'Concrete', (0, depth / 2, top / 2), (length, depth, top), 6)
    box('EdgeCoping', 'Concrete', (0, 14, top + 3), (length, 28, 6), 2)
    box('SafetyLine', 'Safety', (0, 46, top + 6.4), (length - 20, 12, 1.2), 0.4)
    for i in range(12):
        box('TactileRib_%02d' % i, 'Safety', (-length / 2 + 150 + i * (length - 300) / 11.0, 70, top + 6.6),
            (60, 26, 1.6), 0.5)
    for x in (-length / 3, 0, length / 3):
        pole('CanopyPost_%d' % int(x), 'Steel', (x, depth - 40, top), (x, depth - 40, top + 300), 7.0, 8)
        pole('CanopyArm_%d' % int(x), 'Steel', (x, depth - 40, top + 296), (x, 60, top + 286), 5.0, 8)
    box('CanopyRoof', 'Steel', (0, depth / 2 + 20, top + 306), (length * 0.92, depth - 40, 12), 5)
    box('CanopyFascia', 'Steel', (0, 60, top + 300), (length * 0.92, 8, 24), 3)
    for x in (-length / 4, length / 4):
        box('BenchSeat_%d' % int(x), 'Wood', (x, depth - 90, top + 46), (240, 44, 9), 3)
        for dx in (-96, 96):
            box('BenchLeg_%d_%d' % (int(x), dx), 'Steel', (x + dx, depth - 90, top + 23), (8, 40, 46), 2)
    pole('SignPost', 'Steel', (length / 2 - 120, depth - 60, top), (length / 2 - 120, depth - 60, top + 250), 5.0, 8)
    box('SignPanel', 'Steel', (length / 2 - 120, depth - 60, top + 226), (8, 120, 54), 3)
    box('SignBand', 'Safety', (length / 2 - 120, depth - 66, top + 226), (3, 110, 9), 1)
    return parts


ASSEMBLIES = (
    [('Car' + spec['key'], lambda spec=spec: car(spec)) for spec in CAR_VARIANTS]
    + [('Bus', city_bus),
       ('TramCab', lambda: tram_car(True)),
       ('TramMid', lambda: tram_car(False)),
       ('BusDoorLeaf', lambda: door_leaf(132.0, 196.0)),
       ('TramDoorLeaf', lambda: door_leaf(124.0, 210.0)),
       ('Shelter', bus_shelter),
       ('Platform', rail_platform)]
)


# ---------------------------------------------------------------------------
# Routes derived from the retained OSM context roads
# ---------------------------------------------------------------------------

# Every route is an out-and-back closed circuit: the decimated centreline, a
# turnaround cap, then the same centreline reversed. Because a lane offset is always
# applied to the DRIVER'S RIGHT (TransitMath::ApplyLaneOffset), the outbound half runs
# down one side of the road and the return half down the other, which is two-way
# traffic on a single closed loop with no extra machinery. The only artifact is the
# U-turn at each end, which the turnaround cap rounds off.
ROAD_ROUTES = [
    dict(id='road_batei_mahase', label='Batei Mahase', ways=[496167693],
         lane_offset_cm=300.0, speed_cm_s=560.0, vehicle_weight=1.0, bus_share=0.30,
         stop_fractions=[0.14, 0.36, 0.63, 0.86], smoothing=4,
         note='The bus road already carrying the placed RELEASE_Bus_* hero bus.'),
    dict(id='road_maale_hashalom', label='Maale HaShalom', ways=[771909616],
         lane_offset_cm=340.0, speed_cm_s=780.0, vehicle_weight=1.5, bus_share=0.20,
         stop_fractions=[0.18, 0.55, 0.82], smoothing=4,
         note='Tertiary approach climbing north-west from the Dung Gate side.'),
    dict(id='road_ir_david_ophel', label="Ma'alot Ir David and HaOfel", ways=[157676832, 34244965],
         lane_offset_cm=340.0, speed_cm_s=830.0, vehicle_weight=1.8, bus_share=0.22,
         stop_fractions=[0.10, 0.28, 0.52, 0.74, 0.92], smoothing=4,
         note='Two ways sharing the endpoint [-4017.5, 35263.4]; the main eastern spine.'),
    dict(id='road_hativat_yerushalayim', label='Hativat Yerushalayim', ways=[984820251],
         lane_offset_cm=380.0, speed_cm_s=1000.0, vehicle_weight=1.3, bus_share=0.18,
         stop_fractions=[0.20, 0.46, 0.74], smoothing=4,
         note='Trunk road west of the Old City; the flattest corridor in range.'),
]

# ONE light-rail line. This is an AUTHORED FUTURE INTERPRETATION laid along an existing
# trunk-road corridor because that corridor is the flattest ground in range. It is not
# a surveyed alignment, not an approved route, not a real service and not an
# engineering specification. No rail infrastructure is claimed to exist here.
RAIL_ROUTE = dict(
    id='rail_line_1', label='Authored future light-rail line 1 (interpretation)',
    ways=[984820251], lane_offset_cm=240.0, speed_cm_s=1400.0, smoothing=8,
    station_fractions=[0.12, 0.30, 0.44],
    station_names=['Authored station A', 'Authored station B', 'Authored station C'],
    note='Authored future proposal along the Hativat Yerushalayim corridor. Not surveyed.')


def _terrain_height_amot(terrain, x, z):
    """Bilinear sample of the context terrain grid, row-major heights[j * size + i]
    with i on x and j on z. Returns amot above the reference elevation."""
    size, step, origin = terrain['size'], terrain['step'], terrain['origin']
    heights = terrain['heights']
    fi = (x - origin) / step
    fj = (z - origin) / step
    i0 = min(size - 1, max(0, int(math.floor(fi))))
    j0 = min(size - 1, max(0, int(math.floor(fj))))
    i1, j1 = min(size - 1, i0 + 1), min(size - 1, j0 + 1)
    tx = min(1.0, max(0.0, fi - i0))
    tz = min(1.0, max(0.0, fj - j0))
    h00, h10 = heights[j0 * size + i0], heights[j0 * size + i1]
    h01, h11 = heights[j1 * size + i0], heights[j1 * size + i1]
    return (h00 * (1 - tx) + h10 * tx) * (1 - tz) + (h01 * (1 - tx) + h11 * tx) * tz


def _to_unreal(point, terrain):
    x, z = point[0], point[1]
    return [round((x + AMOT_TO_UE['x_offset']) * AMOT_TO_UE['scale'], 2),
            round((z - AMOT_TO_UE['z_offset']) * AMOT_TO_UE['scale'], 2),
            round(_terrain_height_amot(terrain, x, z) * AMOT_TO_UE['scale'], 2)]


def _planar(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _stitch(chains):
    """Join ways end to end, reversing where that shortens the join. Returns the joined
    polyline and the residual join gaps in cm, which the caller records rather than
    hides: a large gap means the chain is not actually continuous."""
    joined = list(chains[0])
    gaps = []
    for chain in chains[1:]:
        options = [(_planar(joined[-1], chain[0]), chain),
                   (_planar(joined[-1], chain[-1]), list(reversed(chain)))]
        gap, best = min(options, key=lambda o: o[0])
        gaps.append(round(gap, 2))
        joined.extend(best[1:] if gap < 1.0 else best)
    return joined, gaps


def _decimate(points, minimum_cm):
    kept = [points[0]]
    for point in points[1:-1]:
        if _planar(kept[-1], point) >= minimum_cm:
            kept.append(point)
    kept.append(points[-1])
    return kept


def _turnaround(points, radius_cm):
    """A rounded U at the end of an out-and-back leg, so the reversal is a turning
    manoeuvre rather than an infinitely sharp cusp."""
    a, b = points[-2], points[-1]
    length = max(1e-6, _planar(a, b))
    fx, fy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    lx, ly = -fy, fx
    return [[b[0] + fx * radius_cm * 0.9 + lx * radius_cm * 0.5,
             b[1] + fy * radius_cm * 0.9 + ly * radius_cm * 0.5],
            [b[0] + fx * radius_cm * 0.2 + lx * radius_cm * 1.0,
             b[1] + fy * radius_cm * 0.2 + ly * radius_cm * 1.0]]


def _out_and_back(points, radius_cm):
    forward = list(points)
    cap_end = _turnaround(forward, radius_cm)
    cap_start = _turnaround(list(reversed(forward)), radius_cm)
    # Drop the shared endpoints so the reversal is a clean U rather than a backtrack.
    return forward + cap_end + list(reversed(forward))[1:-1] + cap_start


def _cumulative(points):
    totals = [0.0]
    for a, b in zip(points, points[1:]):
        totals.append(totals[-1] + math.dist(a, b))
    return totals


def _point_at_fraction(points, fraction):
    totals = _cumulative(points)
    target = totals[-1] * min(1.0, max(0.0, fraction))
    for i in range(1, len(totals)):
        if totals[i] >= target:
            span = totals[i] - totals[i - 1]
            t = (target - totals[i - 1]) / span if span > 1e-9 else 0.0
            return [round(points[i - 1][k] + (points[i][k] - points[i - 1][k]) * t, 2) for k in range(3)], target
    return list(points[-1]), totals[-1]


def build_routes():
    """Derive drivable centrelines and the authored rail line, in Unreal cm."""
    if not CONTEXT_ROADS.exists():
        raise RuntimeError('Context road source not found: %s' % CONTEXT_ROADS)
    source = json.loads(CONTEXT_ROADS.read_text(encoding='utf-8'))
    terrain = source['terrain']
    by_id = {f['id']: f for f in source['features'] if f.get('kind') == 'road'}

    def polyline(definition, decimate_cm=1200.0):
        chains = []
        tags = []
        for way in definition['ways']:
            feature = by_id.get(way)
            if feature is None:
                raise RuntimeError('Context road id %s is not present' % way)
            chains.append([list(p) for p in feature['points']])
            tags.append(dict(osmWayId=way, highway=feature['tags'].get('highway'),
                             name=feature['tags'].get('name:en') or feature['tags'].get('name')))
        joined, gaps = _stitch(chains)
        return _decimate(joined, decimate_cm / AMOT_TO_UE['scale']), gaps, tags

    routes = []
    for definition in ROAD_ROUTES:
        centre, gaps, tags = polyline(definition)
        circuit = _out_and_back(centre, 900.0 / AMOT_TO_UE['scale'])
        points = [_to_unreal(p, terrain) for p in circuit]
        totals = _cumulative(points)
        stops = []
        for index, fraction in enumerate(definition['stop_fractions']):
            world, distance = _point_at_fraction(points, fraction)
            stops.append(dict(
                name='%s stop %d' % (definition['label'], index + 1),
                worldCm=world, advisoryDistanceCm=round(distance, 2),
                dwellMinSeconds=14.0, dwellMaxSeconds=28.0,
                boardingMinPeople=5, boardingMaxPeople=20,
                shelter=True,
                shelterOffsetCm=definition['lane_offset_cm'] + 260.0))
        routes.append(dict(
            id=definition['id'], kind='road', label=definition['label'],
            authored='derived_from_retained_osm_context_road_centreline',
            sourceWays=tags, stitchGapsCm=gaps,
            closed=True, outAndBack=True, smoothingPerSegment=definition['smoothing'],
            laneOffsetCm=definition['lane_offset_cm'], rideHeightCm=6.0,
            speedLimitCmPerSecond=definition['speed_cm_s'],
            vehicleWeight=definition['vehicle_weight'], busShare=definition['bus_share'],
            controlPointCount=len(points), lengthCm=round(totals[-1], 2),
            points=points, stops=stops, note=definition['note']))

    centre, gaps, tags = polyline(RAIL_ROUTE, decimate_cm=2500.0)
    circuit = _out_and_back(centre, 2400.0 / AMOT_TO_UE['scale'])
    points = [_to_unreal(p, terrain) for p in circuit]
    totals = _cumulative(points)
    stations = []
    for index, fraction in enumerate(RAIL_ROUTE['station_fractions']):
        world, distance = _point_at_fraction(points, fraction)
        stations.append(dict(
            name=RAIL_ROUTE['station_names'][index],
            worldCm=world, advisoryDistanceCm=round(distance, 2),
            dwellMinSeconds=20.0, dwellMaxSeconds=40.0,
            boardingMinPeople=18, boardingMaxPeople=60,
            platform=True, platformOffsetCm=RAIL_ROUTE['lane_offset_cm'] + 250.0))
    routes.append(dict(
        id=RAIL_ROUTE['id'], kind='rail', label=RAIL_ROUTE['label'],
        authored='AUTHORED_FUTURE_INTERPRETATION_NOT_SURVEYED_INFRASTRUCTURE',
        sourceWays=tags, stitchGapsCm=gaps,
        closed=True, outAndBack=True, smoothingPerSegment=RAIL_ROUTE['smoothing'],
        laneOffsetCm=RAIL_ROUTE['lane_offset_cm'], rideHeightCm=28.0,
        speedLimitCmPerSecond=RAIL_ROUTE['speed_cm_s'],
        headwayMinSeconds=120.0, headwayMaxSeconds=300.0,
        consist=[dict(car='TramCab', yawOffsetDegrees=0.0), dict(car='TramMid', yawOffsetDegrees=0.0),
                 dict(car='TramCab', yawOffsetDegrees=180.0)],
        carLengthCm=1020.0, couplingGapCm=40.0, bogieInsetCm=280.0,
        controlPointCount=len(points), lengthCm=round(totals[-1], 2),
        points=points, stops=stations, note=RAIL_ROUTE['note']))

    document = dict(
        schema='MikdashTransitRoutesV1',
        units='unreal_centimetres',
        alignment='UEcm = ((x + 17.5097) * 50, (z - 0.55135) * 50, bilinear_terrain(x, z) * 50)',
        source=dict(file=str(CONTEXT_ROADS), sha256=hashlib.sha256(CONTEXT_ROADS.read_bytes()).hexdigest(),
                    provenance=source.get('provenance'),
                    attribution='Retained OSM context; existing project ODbL attribution applies. No new geographic claim.'),
        geometryConvention=[
            'Every route is a CLOSED out-and-back circuit: centreline, turnaround cap, reversed centreline, turnaround cap.',
            'Lane offsets are applied to the driver\u2019s right, so the outbound half runs on one side of the road and the return half on the other. That is the two-way traffic; there is no second route.',
            'Stops are authored as world positions. The runtime projects them onto the arc table it builds itself (TransitMath::ProjectOntoRoute), so nothing depends on the generator and the runtime densifying identically. advisoryDistanceCm is the generator\u2019s own unsmoothed figure, for comparison only.',
        ],
        limitations=[
            'RAIL IS AUTHORED FUTURE INTERPRETATION. The light-rail line, its stations and its platforms are an illustrative proposal laid along an existing road corridor. They are not surveyed infrastructure, not an approved alignment, not a real service and not an engineering or accessibility specification.',
            'Road centrelines are OSM ways, not lane geometry. Lane counts, one-way restrictions, junction control, kerb lines and road widths are NOT in the source data (only 8 of 5,944 ways carry a width tag), so lane offsets are authored, not surveyed.',
            'Z comes from the 25 m context terrain grid, not from a trace against the placed landscape. Expect several metres of error on steep ground. release_transit.py records a downward-trace comparison where traces are available; nothing here is a verified ground contact.',
            'No junction, signal, right of way, pedestrian crossing or collision behaviour is modelled. Vehicles follow the vehicle ahead of them on their own route and nothing else.',
            'Turnaround caps are a geometric device to close an open road into a circuit. They are not real turning circles and may not lie on drivable ground.',
        ],
        routes=routes)
    return document


# ---------------------------------------------------------------------------
# Offline export
# ---------------------------------------------------------------------------

def write_system_obj(path, parts, native):
    """Project OBJ adapter convention, plus per-vertex colour on the 'v' lines.

    native=True writes the reflected-Y / reversed-winding legacy adapter; native=False
    writes canonical Unreal XYZ. Vertex colour is the widely supported 'v x y z r g b'
    extension. Whether the UE 5.8 import path preserves it is NOT assumed here: the
    native step reads the colours back off the imported mesh and records the answer,
    and the material falls back to a flat instance colour if they did not survive."""
    lines = ['# Original TransitSystemV1; cm; ' +
             ('Unreal legacy reflected-Y adapter' if native else 'canonical Unreal XYZ') +
             '; vertex colour r g b on each v line']
    n = 1
    for part in parts:
        colour = part.get('colour') or [0.0, 0.0, 0.0]
        lines.append('g ' + part['name'])
        lines.append('s off')
        for face in part['triangles']:
            a, b, c = [part['vertices'][i] for i in face]
            if native:
                a, b, c = [(v[0], -v[1], v[2]) for v in (a, c, b)]
            ab = tuple(b[i] - a[i] for i in range(3))
            ac = tuple(c[i] - a[i] for i in range(3))
            normal = G.cross(ab, ac)
            length = math.sqrt(G.dot(normal, normal))
            edge = math.sqrt(G.dot(ab, ab))
            uv = [(0, 0), (edge / 100, 0), (G.dot(ac, ab) / edge / 100, length / edge / 100)]
            for v in (a, b, c):
                lines.append('v %.8f %.8f %.8f %.6f %.6f %.6f' % (v[0], v[1], v[2], colour[0], colour[1], colour[2]))
            lines.extend('vt %.8f %.8f' % v for v in uv)
            lines.extend(['vn %.9f %.9f %.9f' % tuple(v / length for v in normal)] * 3)
            lines.append('f ' + ' '.join('%d/%d/%d' % (i, i, i) for i in range(n, n + 3)))
            n += 3
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def render_system_preview(assemblies):
    """Stdlib depth-buffer contact sheet. Geometry inspection only: this is NOT an
    Unreal render and establishes no lighting, material or visual quality."""
    columns, rows = 3, 4
    cell_w, cell_h = 440, 300
    w, h = columns * cell_w, rows * cell_h
    pixels = bytearray(bytes((198, 205, 210)) * w * h)
    depth = [-1e30] * (w * h)
    for index, (label, parts) in enumerate(assemblies):
        if index >= columns * rows:
            break
        ox, oy = (index % columns) * cell_w, (index // columns) * cell_h
        raw = [v for p in parts for v in p['vertices']]
        extent = max(max(abs(v[i]) for v in raw) for i in range(3)) or 1.0
        scale = min(cell_w, cell_h) * 0.36 / extent

        def project(v):
            x, y, z = v
            return (ox + cell_w / 2 + scale * (0.82 * x - 0.70 * y),
                    oy + cell_h / 2 + 26 + scale * (0.18 * x + 0.34 * y - 0.95 * z),
                    0.665 * x + 0.779 * y + 0.4048 * z)
        faces = []
        for part in parts:
            base = SYSTEM_PALETTE[part['material']][0]
            for face in part['triangles']:
                tri = [part['vertices'][i] for i in face]
                a, b, c = tri
                ab = [b[i] - a[i] for i in range(3)]
                ac = [c[i] - a[i] for i in range(3)]
                nrm = G.cross(ab, ac)
                nl = math.sqrt(G.dot(nrm, nrm)) or 1.0
                light = 0.38 + 0.62 * max(0.0, sum(nrm[i] * (0.30, 0.50, 0.81)[i] for i in range(3)) / nl)
                colour = bytes(max(0, min(255, round(255 * (v * light) ** (1 / 2.2)))) for v in base)
                faces.append((part['material'] == 'Glass', [project(v) for v in tri], colour))
        for transparent, pts, colour in sorted(faces, key=lambda f: (f[0], sum(v[2] for v in f[1]))):
            top = max(oy, math.ceil(min(v[1] for v in pts)))
            bottom = min(oy + cell_h, math.ceil(max(v[1] for v in pts)))
            for y in range(top, bottom):
                yy = y + 0.5
                cuts = []
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    if min(a[1], b[1]) <= yy < max(a[1], b[1]):
                        t = (yy - a[1]) / (b[1] - a[1])
                        cuts.append((a[0] + t * (b[0] - a[0]), a[2] + t * (b[2] - a[2])))
                if len(cuts) != 2:
                    continue
                cuts.sort()
                (x0, d0), (x1, d1) = cuts
                if x1 - x0 < 1e-9:
                    continue
                for x in range(max(ox, math.ceil(x0)), min(ox + cell_w, math.ceil(x1))):
                    z = d0 + (x + 0.5 - x0) * (d1 - d0) / (x1 - x0)
                    idx = y * w + x
                    if z > depth[idx]:
                        if transparent:
                            for k in range(3):
                                pixels[idx * 3 + k] = round(0.22 * colour[k] + 0.78 * pixels[idx * 3 + k])
                        else:
                            depth[idx] = z
                            pixels[idx * 3:idx * 3 + 3] = colour

    def chunk(kind, data):
        import struct
        import zlib
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    import struct
    import zlib
    raw = b''.join(b'\0' + pixels[y * w * 3:(y + 1) * w * 3] for y in range(h))
    (SYSTEM_OUT / 'geometry-preview.png').write_bytes(
        b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', w, h, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def export_system():
    """Author the instanced vehicle set, the stop furniture and routes.json offline."""
    if (SYSTEM_OUT / 'frozen-file-manifest.json').exists():
        raise RuntimeError('Frozen TransitSystemV1 exists; author another version')
    SYSTEM_OUT.mkdir(parents=True, exist_ok=True)
    built = [(label, builder()) for label, builder in ASSEMBLIES]
    manifest = dict(
        status='offline_checked_native_pending',
        namespace=SYSTEM_DEST,
        units='centimetres',
        axes='+X forward, +Y left, Z0 at tyre or railhead contact',
        objConvention='SM_*.obj adapters are reflected-Y with reversed winding; canonical JSON/OBJ is Unreal XYZ. Never apply a second reflection or unit conversion.',
        vertexColour=dict(
            paintGroup='R = paint mask (1 takes the per-instance body colour), G = baked panel shade',
            lensGroup='R = 1 on red lamps, 0 on white lamps',
            perInstanceColour='NOT vertex colour: HISM per-instance custom data floats 0..2, written by the actor from TransitMath::PaintColourFor',
            importPreservationVerified=False),
        palette=SYSTEM_PALETTE, assemblies={}, imports=[])
    for label, parts in built:
        checks = check_parts(parts)
        manifest['assemblies'][label] = checks
        (SYSTEM_OUT / (label.lower() + '-editable.mesh.json')).write_text(
            json.dumps(dict(units='cm', axes='Unreal XYZ, +X forward, +Y left', parts=parts),
                       separators=(',', ':')) + '\n')
        write_system_obj(SYSTEM_OUT / (label.lower() + '-canonical.obj'), parts, False)
        for material in SYSTEM_PALETTE:
            selected = [p for p in parts if p['material'] == material]
            if not selected:
                continue
            name = 'SM_TransitSystemV1_' + label + '_' + material
            path = SYSTEM_OUT / (name + '.obj')
            write_system_obj(path, selected, True)
            manifest['imports'].append(dict(
                assembly=label, name=name, material=material, file=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                triangles=sum(len(p['triangles']) for p in selected),
                bounds_cm=G.bounds([v for p in selected for v in p['vertices']])))
    routes = build_routes()
    (SYSTEM_OUT / 'routes.json').write_text(json.dumps(routes, indent=2) + '\n', encoding='utf-8')
    manifest['routes'] = dict(
        file='routes.json', sha256=hashlib.sha256((SYSTEM_OUT / 'routes.json').read_bytes()).hexdigest(),
        count=len(routes['routes']),
        summary=[dict(id=r['id'], kind=r['kind'], lengthCm=r['lengthCm'], stops=len(r['stops']),
                      points=r['controlPointCount']) for r in routes['routes']])
    manifest['limitations'] = [
        'Offline geometry only. No Unreal import, material, lighting, collision, LOD, Nanite, instancing cost or visual acceptance is established here.',
        'These are original generic vehicle forms. No manufacturer body, badge, livery or municipal design is reproduced, and no external model or texture was used.',
        'The rail line and every station is AUTHORED FUTURE INTERPRETATION, not surveyed infrastructure. See routes.json limitations.',
        'The preview PNG is a stdlib depth-buffer inspection image, not an Unreal render.',
        'Vertex-colour survival through the UE 5.8 OBJ import path is unverified offline; the native step reads it back and records the result.',
    ]
    render_system_preview(built)
    (SYSTEM_OUT / 'offline-checks.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(
        assemblies={k: dict(parts=v['parts'], triangles=v['triangles']) for k, v in manifest['assemblies'].items()},
        meshes=len(manifest['imports']),
        routes=manifest['routes']['summary']), indent=2))
    return manifest


def run_native_system():
    """ROOT ONLY: creates isolated materials and static meshes under SYSTEM_DEST.

    No actor, map, terrain or road is touched. Refuses an existing namespace, a game
    world and dirty packages. release_transit.py performs the placement separately."""
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve() == ROOT
    assert not ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    assert not assets.does_directory_exist(SYSTEM_DEST), 'Preserve previous partial assets'
    manifest = json.loads((SYSTEM_OUT / 'offline-checks.json').read_text())
    receipt = dict(status='started', created=[], vertexColourPreserved={}, materialConnections={})
    try:
        tools = ue.AssetToolsHelpers.get_asset_tools()
        ml = ue.MaterialEditingLibrary
        materials = {}
        for name in sorted(set(record['material'] for record in manifest['imports'])):
            colour, metal, rough = manifest['palette'][name]
            material = tools.create_asset('M_TransitSystemV1_' + name, SYSTEM_DEST + '/Materials',
                                          ue.Material, ue.MaterialFactoryNew())
            base = ml.create_material_expression(material, ue.MaterialExpressionConstant3Vector)
            base.set_editor_property('constant', ue.LinearColor(*colour, 1))
            connections = {}
            if name == 'Paint':
                # Body colour = lerp(base, per-instance custom data 0..2, vertex colour R),
                # then shaded by vertex colour G. One mesh, one material, many colours.
                vertex = ml.create_material_expression(material, ue.MaterialExpressionVertexColor)
                instance = ml.create_material_expression(material, ue.MaterialExpressionVertexInterpolator) \
                    if False else None
                custom = []
                for index in range(3):
                    node = ml.create_material_expression(material, ue.MaterialExpressionPerInstanceCustomData)
                    node.set_editor_property('data_index', index)
                    node.set_editor_property('default_value', 0.5)
                    custom.append(node)
                append = ml.create_material_expression(material, ue.MaterialExpressionAppendVector)
                ml.connect_material_expressions(custom[0], '', append, 'A')
                ml.connect_material_expressions(custom[1], '', append, 'B')
                append2 = ml.create_material_expression(material, ue.MaterialExpressionAppendVector)
                ml.connect_material_expressions(append, '', append2, 'A')
                ml.connect_material_expressions(custom[2], '', append2, 'B')
                blend = ml.create_material_expression(material, ue.MaterialExpressionLinearInterpolate)
                ml.connect_material_expressions(base, '', blend, 'A')
                ml.connect_material_expressions(append2, '', blend, 'B')
                ml.connect_material_expressions(vertex, 'R', blend, 'Alpha')
                shade = ml.create_material_expression(material, ue.MaterialExpressionMultiply)
                ml.connect_material_expressions(blend, '', shade, 'A')
                ml.connect_material_expressions(vertex, 'G', shade, 'B')
                connections['base_colour'] = ml.connect_material_property(shade, '', ue.MaterialProperty.MP_BASE_COLOR)
            elif name == 'Lens':
                # Vertex colour R selects the red lamps, so head and tail share one mesh.
                vertex = ml.create_material_expression(material, ue.MaterialExpressionVertexColor)
                red = ml.create_material_expression(material, ue.MaterialExpressionConstant3Vector)
                red.set_editor_property('constant', ue.LinearColor(0.52, 0.02, 0.012, 1))
                blend = ml.create_material_expression(material, ue.MaterialExpressionLinearInterpolate)
                ml.connect_material_expressions(base, '', blend, 'A')
                ml.connect_material_expressions(red, '', blend, 'B')
                ml.connect_material_expressions(vertex, 'R', blend, 'Alpha')
                connections['base_colour'] = ml.connect_material_property(blend, '', ue.MaterialProperty.MP_BASE_COLOR)
                connections['emissive'] = ml.connect_material_property(blend, '', ue.MaterialProperty.MP_EMISSIVE_COLOR)
            else:
                connections['base_colour'] = ml.connect_material_property(base, '', ue.MaterialProperty.MP_BASE_COLOR)
            properties = [(metal, ue.MaterialProperty.MP_METALLIC), (rough, ue.MaterialProperty.MP_ROUGHNESS)]
            if name == 'Glass':
                material.set_editor_property('blend_mode', ue.BlendMode.BLEND_TRANSLUCENT)
                material.set_editor_property('translucency_lighting_mode',
                                             ue.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
                properties.append((.22, ue.MaterialProperty.MP_OPACITY))
            for value, prop in properties:
                node = ml.create_material_expression(material, ue.MaterialExpressionConstant)
                node.set_editor_property('r', value)
                connections[str(prop)] = ml.connect_material_property(node, '', prop)
            ml.recompile_material(material)
            assert assets.save_loaded_asset(material, only_if_is_dirty=False)
            # UE 5.8: connect_material_property returns False even when it succeeded, so
            # the booleans above are RECORDED, never asserted. Verify structurally instead.
            receipt['materialConnections'][name] = {k: bool(v) for k, v in connections.items()}
            reloaded = assets.load_asset(material.get_path_name())
            assert reloaded is not None
            if name == 'Glass':
                assert reloaded.get_editor_property('blend_mode') == ue.BlendMode.BLEND_TRANSLUCENT
            materials[name] = material
            receipt['created'].append(material.get_path_name())

        for record in manifest['imports']:
            path = SYSTEM_OUT / record['file']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
            options = ue.FbxImportUI()
            for key, value in dict(automated_import_should_detect_type=False,
                                   mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                                   import_as_skeletal=False, import_mesh=True, import_animations=False,
                                   import_materials=False, import_textures=False,
                                   create_physics_asset=False).items():
                options.set_editor_property(key, value)
            data = options.get_editor_property('static_mesh_import_data')
            for key, value in dict(combine_meshes=True, transform_vertex_to_absolute=True, bake_pivot_in_vertex=False,
                                   convert_scene=False, convert_scene_unit=False, force_front_x_axis=False,
                                   import_uniform_scale=1.0, auto_generate_collision=False, build_nanite=False,
                                   generate_lightmap_u_vs=False, remove_degenerates=True,
                                   vertex_color_import_option=ue.VertexColorImportOption.REPLACE,
                                   normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
                try:
                    data.set_editor_property(key, value)
                except Exception as error:
                    receipt.setdefault('importOptionWarnings', []).append(dict(key=key, error=str(error)))
            task = ue.AssetImportTask()
            for key, value in dict(filename=str(path), destination_path=SYSTEM_DEST + '/' + record['assembly'],
                                   destination_name=record['name'], automated=True, async_=False,
                                   replace_existing=False, save=False, options=options,
                                   factory=ue.FbxFactory()).items():
                task.set_editor_property(key, value)
            tools.import_asset_tasks([task])
            objects = list(task.get_objects())
            assert len(objects) == 1 and isinstance(objects[0], ue.StaticMesh), record['name']
            mesh = objects[0]
            box = mesh.get_bounding_box()
            actual = dict(min=[box.min.x, box.min.y, box.min.z], max=[box.max.x, box.max.y, box.max.z])
            assert max(abs(actual[k][i] - record['bounds_cm'][k][i]) for k in actual for i in range(3)) < .05, record['name']
            # 5.8: a Nanite mesh reports only fallback triangles at LOD0, so build_nanite
            # is off above and this count is the real authored count.
            assert mesh.get_num_triangles(0) == record['triangles'], record['name']
            mesh.set_material(0, materials[record['material']])
            assert assets.save_loaded_asset(mesh, only_if_is_dirty=False)
            receipt['created'].append(mesh.get_path_name())
        receipt['status'] = 'assets_saved_unplaced_native_visual_collision_motion_pending'
        receipt['note'] = ('Vertex-colour preservation is not asserted. If the material shows flat paint, the OBJ '
                           'path dropped vertex colours and the Paint material must fall back to the per-instance '
                           'custom data alone (drop the vertex-colour lerp and shade multiply).')
    except Exception as error:
        receipt.update(status='failed_partial_assets_preserved', error=str(error))
        raise
    finally:
        (SYSTEM_OUT / 'native-import.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', action='store_true', help='TransitV2 hero bus and station geometry')
    parser.add_argument('--export-system', action='store_true',
                        help='TransitSystemV1 instanced vehicles, stop furniture and routes.json')
    parser.add_argument('--routes-only', action='store_true', help='Rewrite TransitSystemV1/routes.json only')
    arguments = parser.parse_args()
    if arguments.export:
        export()
    elif arguments.export_system:
        export_system()
    elif arguments.routes_only:
        SYSTEM_OUT.mkdir(parents=True, exist_ok=True)
        document = build_routes()
        (SYSTEM_OUT / 'routes.json').write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
        print(json.dumps([dict(id=r['id'], kind=r['kind'], lengthCm=r['lengthCm'], stops=len(r['stops']))
                          for r in document['routes']], indent=2))
    else:
        parser.error('Use --export / --export-system / --routes-only offline; '
                     'root invokes run_native() or run_native_system() separately')
