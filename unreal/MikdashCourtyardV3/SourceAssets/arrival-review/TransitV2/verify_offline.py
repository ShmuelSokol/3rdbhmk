"""Independent serialized-export checks; no Unreal, GUI or map mutation."""
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

FOLDER=Path(__file__).resolve().parent
ROOT=FOLDER.parents[2]
script=ROOT/'Scripts/create_transit_assets.py'
spec=importlib.util.spec_from_file_location('_transit_check',script)
module=importlib.util.module_from_spec(spec)
sys.dont_write_bytecode=True
spec.loader.exec_module(module)
report=json.loads((FOLDER/'offline-checks.json').read_text())
assemblies={}
for name in ('Bus','Station'):
    data=json.loads((FOLDER/(name.lower()+'-editable.mesh.json')).read_text())
    checked=module.check_parts(data['parts'])
    assert checked==report['assemblies'][name]
    assemblies[name]={p['name']:p for p in data['parts']}
for rec in report['imports']:
    path=FOLDER/rec['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==rec['sha256']
    vertices=[];uv=[];normal_count=0;faces=[]
    for line in path.read_text().splitlines():
        if line.startswith('v '):vertices.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):normal_count+=1
        elif line.startswith('f '):faces.append(line)
    assert len(faces)==rec['triangles'] and len(vertices)==3*len(faces)==len(uv)==normal_count
    actual=module.G.bounds([(x,-y,z) for x,y,z in vertices])
    assert max(abs(actual[k][i]-rec['bounds_cm'][k][i]) for k in actual for i in range(3))<1e-6
    for i in range(0,len(uv),3):
        a,b,c=uv[i:i+3]
        assert abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-10
bus=assemblies['Bus'];station=assemblies['Station']
assert not any(n.startswith(('WindowGasket_','EndUpper_','DoorFrame_')) for n in bus)
seat_names=[n for n in bus if n.startswith('PassengerSeat_') and n.endswith('_Cushion')]
assert len(seat_names)==20
assert all(abs(module.G.bounds(bus[n]['vertices'])['max'][1]-module.G.bounds(bus[n]['vertices'])['min'][1]-42)<1e-8 for n in seat_names)
assert 'DriverSeat_Cushion' in bus and 'SteeringWheel' in bus and 'DriverDashboard' in bus
inner=min(abs(v[1]) for n in seat_names for v in bus[n]['vertices'])
assert inner*2==54,'Authored bus aisle changed; not accepted for current pawn capsule'
left=module.G.bounds(station['Rail_-1_Head']['vertices']);right=module.G.bounds(station['Rail_1_Head']['vertices'])
gauge=right['min'][1]-left['max'][1];assert abs(gauge-143.5)<1e-6
for side in (-1,1):
    ramp=module.G.bounds(station['EndRamp_%s'%side]['vertices'])
    assert abs((ramp['max'][2]-ramp['min'][2])/(ramp['max'][0]-ramp['min'][0])-.05)<1e-9
assert len([n for n in station if n.startswith('Sleeper_')])==108
for path in [script,FOLDER/'render_preview.py',Path(__file__)]:ast.parse(path.read_text(),filename=str(path))
result=dict(status='offline_pass_native_not_executed',material_group_obj_count=len(report['imports']),bus_passenger_seats=20,driver_cockpit=True,human_driver=False,seat_width_cm=42,aisle_clear_width_between_cushions_cm=54,current_pawn_bus_boarding_accepted=False,rail_inner_gauge_cm=gauge,ramp_grade=.05,station_world_placement=None,checks=['Serialized indexed meshes rechecked for manifold edges, signed volumes, finite vertices and nondegenerate triangles','OBJ hashes, triangle/normal/UV counts, reflected coordinate bounds, UV triangle areas verified','Full opaque window/door backing removed; passenger seats and driver controls exist','143.5cm rail inner-edge gauge and5% ramps checked geometrically','Python scripts AST parsed'],limits=['No native import, render, collision, shader or gameplay verification','No actual driver/passengers, train carriage or vehicle rig','Station and route remain authored illustrative future design'])
(FOLDER/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
