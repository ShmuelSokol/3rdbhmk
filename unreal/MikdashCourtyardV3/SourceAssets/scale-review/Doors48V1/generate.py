"""Fresh source-only Kodesh48 geometry, reusing original editable part generator."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST='/Game/MikdashV3/MaterialReview/Doors48V1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):
    spec=importlib.util.spec_from_file_location('doors48_'+name,ROOT/'Scripts'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def box(vertices):return {k:[fn(v[i] for v in vertices) for i in range(3)] for k,fn in [('min',min),('max',max)]}
def scaled(b):return dict(b,min=[x*.96 for x in b['min']],max=[x*.96 for x in b['max']])

def generate():
    if (HERE/'spec.json').exists():raise RuntimeError('Frozen source exists; no overwrite')
    source=load('create_sanctuary_doors');solver=load('release_import_doors')
    openings=source.openings()
    source.openings=lambda: {'Kodesh':{k:v*.96 for k,v in openings['Kodesh'].items()}}
    geometry={k:v for k,v in source.geometry().items() if k.startswith('SM_Kodesh')}
    math=source.module('doors48_math','create_sanctuary_reliefs.py')
    rows=[];bounds={};editable={}
    for old,parts in geometry.items():
        name=old.replace('V1','48V1');lines=['# UE OBJ: reflected Y and reversed winding; cm'];idx=1;allvertices=[]
        for label,(vertices,faces) in parts:
            if math.volume(vertices,faces)<0:faces=[(a,c,b) for a,b,c in faces]
            allvertices+=vertices;lines.append('g '+label)
            for a,b,c in faces:
                p,q,r=[(vertices[i][0],-vertices[i][1],vertices[i][2]) for i in (a,c,b)]
                normal=math.cross([q[i]-p[i] for i in range(3)],[r[i]-p[i] for i in range(3)])
                length=sum(x*x for x in normal)**.5
                if length<=1e-10:raise RuntimeError('Degenerate triangle')
                normal=[x/length for x in normal]
                for v in (p,q,r):lines.append('v %.9f %.9f %.9f'%v)
                for v in (p,q,r):lines.append('vn %.9f %.9f %.9f'%tuple(normal))
                lines.append('f %d//%d %d//%d %d//%d'%(idx,idx,idx+1,idx+1,idx+2,idx+2));idx+=3
        path=HERE/(name+'.obj');path.write_text('\n'.join(lines)+'\n',encoding='ascii')
        bounds[old]=box(allvertices);editable[name]=parts
        rows.append(dict(oldMesh='/Game/MikdashV3/MaterialReview/DoorsParochesV1/Meshes/'+old,
                         newMesh=DEST+'/'+name,file=path.name,sha256=sha(path),triangles=(idx-1)//3,bounds=bounds[old]))
    spec=solver.load_spec();original=copy.deepcopy(spec)
    placement=solver.load_placement_json(spec)
    for d in placement['doors']:
        if d['mesh_family']!='Kodesh':continue
        if d['role']=='jamb_leaf':d['closed_location_cm']=[d['closed_location_cm'][0]*.96,d['closed_location_cm'][1]*.96,890]
        else:
            d['closed_local_location_cm'][0]*=.96;d['hinge_axis_in_parent_cm'][0]*=.96
    for family in spec['doorPlan']['families']:
        if family['family']=='Kodesh':
            for bank in family['banks']:bank['jsonHingeX']*=.96
    architecture=solver.load_architecture_manifest(spec)
    op,manifest_boxes=solver.openings_from_manifest(spec,architecture)
    op={k:{p:v*.96 for p,v in row.items()} for k,row in op.items()}
    plan=solver.plan_doors(spec,placement,op,bounds,families=['kodesh'])
    walls=solver.wall_boxes_for_clearance(spec,manifest_boxes,solver.veneer_boxes_from_spec(spec)+solver.open_door_primitive_boxes(spec,architecture))
    clearance=solver.check_plan_clearance(spec,plan['leaves'],[],[scaled(w) for w in walls],scaled(solver.corridor_box(spec)))
    if any(clearance[k] for k in ('leafWallIntersections','corridorLeafIntersections','leafPairIntersections')):raise RuntimeError(str(clearance))
    original_rows={r['index']:r for r in original['derivedPlan']['actors']}
    replacements=[]
    for r in plan['leaves']:
        old=original_rows[r['index']]
        replacements.append(dict(label='RELEASE_Doors_%d_%s'%(r['index'],r['roleTag']),
            oldMesh='/Game/MikdashV3/MaterialReview/DoorsParochesV1/Meshes/'+r['meshName'],
            newMesh=DEST+'/'+r['meshName'].replace('V1','48V1'),oldLocation=old['location'],oldRotation=old['rotation'],
            location=r['location'],rotation=r['rotation'],bounds=r['plannedWorldBoundsCm']))
    fit=plan['families']['Kodesh']['fit'];assert fit['leafHeightCm']==284 and abs(fit['leafWidthCm']-83)<1e-6
    assert len(replacements)==12
    (HERE/'editable-parts.json').write_text(json.dumps(editable),encoding='utf8')
    result=dict(status='OFFLINE_GEOMETRY_AND_CLEARANCE_PASS_NATIVE_PENDING',namespace=DEST,meshes=rows,replacements=replacements,
        fit=fit,clearance=clearance,generatorSha256=sha(Path(__file__)),
        sourceGeneratorSha256=sha(ROOT/'Scripts/create_sanctuary_doors.py'),solverSha256=sha(ROOT/'Scripts/release_import_doors.py'),
        limits=['No curtain/art changes','Only Kodesh; original architecture supplies Heichal leaves',
                'Clearance uses scaled architecture and historical veneer boxes; current candidate must be reviewed',
                'Hardware radius/length/thickness retained by regeneration; strap span follows nominal width; no collision/native proof'])
    (HERE/'spec.json').write_text(json.dumps(result,indent=2),encoding='utf8');return result
if __name__=='__main__':
    r=generate();print(r['status'],len(r['meshes']),len(r['replacements']))
