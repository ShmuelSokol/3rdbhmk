"""Original paired keruvim study; offline export. Explicit run_native imports assets only.
Not a manufactured-object replica or a certified future-Temple prediction.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FOLDER=ROOT/'SourceAssets/vessels-review/KeruvimStudyV1'
SPEC=FOLDER/'model-spec.json'
ARK=ROOT/'SourceAssets/vessels-review/aron-study-v1-spec.json'
DEST='/Game/MikdashV3/MaterialReview/KeruvimStudyV1'


def helpers():
    path=ROOT/'Scripts/create_menorah_study.py'
    spec=importlib.util.spec_from_file_location('_keruvim_geometry',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def ellipsoid(center,radii,pitch=0):
    h=helpers()
    profile=[(math.sin(math.pi*i/24),-math.cos(math.pi*i/24)) for i in range(25)]
    profile[0]=(0,-1);profile[-1]=(0,1)
    v,f=h.lathe(profile,segments=48)
    angle=math.radians(pitch);co=math.cos(angle);si=math.sin(angle)
    scaled=[]
    for x,y,z in v:
        x*=radii[0];y*=radii[1];z*=radii[2]
        scaled.append((center[0]+co*x+si*z,center[1]+y,center[2]-si*x+co*z))
    return h.orient((scaled,f))


def feather(start,end,width,thickness):
    # Closed curved lenticular feather with distinct poles; no paper planes.
    dx=end[0]-start[0];dy=end[1]-start[1];length=math.hypot(dx,dy)
    nx=-dy/length;ny=dx/length
    vertices=[];rings=[];faces=[]
    for i in range(17):
        t=i/16;ring=[];r=math.sin(math.pi*t)**.65 if i not in (0,16) else 0
        for j in range(1 if r==0 else 12):
            a=j*math.tau/12
            ring.append(len(vertices));vertices.append((start[0]+dx*t+nx*width*r*math.cos(a),start[1]+dy*t+ny*width*r*math.cos(a),start[2]+(end[2]-start[2])*t+2*math.sin(math.pi*t)+thickness*r*math.sin(a)))
        rings.append(ring)
    for a,b in zip(rings,rings[1:]):
        for i in range(12):
            j=(i+1)%12
            if len(a)==1:faces.append((a[0],b[j],b[i]))
            elif len(b)==1:faces.append((a[i],a[j],b[0]))
            else:faces.extend([(a[i],a[j],b[j]),(a[i],b[j],b[i])])
    return helpers().orient((vertices,faces))


def assembly():
    ark=json.loads(ARK.read_text());h=helpers()
    assert ark['bodyCm']==[125,75,75] and ark['coverCm'][:2]==[125,75]
    cover=ark['bodyCm'][2]+ark['coverCm'][2];tefach=ark['chosenIllustrativeScale']['tefachCm']
    local=[]
    def add(name,kind,mesh):local.append(dict(name=name,kind=kind,mesh=h.orient(mesh)))
    # Body is an explicitly modest draped sculptural interpretation; no exposed torso.
    add('DrapedBody','body',h.lathe([(0,0),(10,0),(11,2),(10,9),(8,28),(6.5,50),(8,69),(10,77),(8,85),(4.5,88),(0,88)],segments=64,lobes=16,amplitude=.06))
    add('ChildlikeHead','head',ellipsoid((1,0,95),(8,8.5,10.5),18))
    add('Nose','nose',ellipsoid((9,0,92.5),(2.5,1.4,2.0),18))
    for sign in (-1,1):
        add('Cheek'+str(sign),'cheek',ellipsoid((7.7,sign*4.0,91.8),(1.7,2.2,2.0),18))
        add('Eyelid'+str(sign),'eyelid',ellipsoid((8.1,sign*3.9,95.9),(.65,1.9,.42),18))
        add('Ear'+str(sign),'ear',ellipsoid((-.2,sign*8.1,94.0),(1.8,1.1,2.5),18))
    add('MouthRelief','mouth',ellipsoid((8.5,0,89.5),(.65,1.8,.38),18))
    for side in (-1,1):
        for i in range(13):
            t=i/12
            add('Wing%sPrimary%02d'%(side,i),'primary_feather',feather((0,side*6,85),(9+29*t,side*(12+20*math.sin(math.pi*t/2)),101+11*t),3.0,.65))
        for i in range(7):
            t=i/6
            add('Wing%sCovert%02d'%(side,i),'covert_feather',feather((-.8,side*5.5,85.5),(7+18*t,side*(10+13*t),98+7*t),2.8,.8))
    wings=[p for p in local if 'feather' in p['kind']]
    zmin=min(v[2] for p in wings for v in p['mesh'][0]);shift=10*tefach-zmin
    for p in wings:p['mesh']=([(x,y,z+shift) for x,y,z in p['mesh'][0]],p['mesh'][1])
    parts=[]
    for anchor in ark['keruvimAnchorsCm']:
        sign=1 if anchor['facesToward']=='+X' else -1
        x,y,z=anchor['position'];assert abs(z-cover)<1e-6
        for p in local:
            v,f=p['mesh'];mesh=h.orient(([(x+sign*a,y+sign*b,z+c) for a,b,c in v],list(f)))
            parts.append(dict(name=anchor['name'].replace('Reserved','')+'_'+p['name'],kind=p['kind'],mesh=mesh))
    return parts


def export():
    if FOLDER.exists():raise RuntimeError('Existing study preserved; author new version for revisions')
    ark=json.loads(ARK.read_text());parts=assembly();cover=ark['bodyCm'][2]+ark['coverCm'][2]
    FOLDER.mkdir(parents=True)
    source=dict(status='ORIGINAL_INTERPRETIVE_STUDY_NATIVE_AND_VISUAL_REVIEW_PENDING',
        sources=[dict(id='EX25-18-20',url='https://www.chabad.org/library/bible_cdo/aid/9886/jewish/Chapter-25.htm',claim='Two gold figures arise from cover ends, face inward and toward cover, with raised wings over cover.'),
                 dict(id='RASHI25-18',url='https://www.chabad.org/library/bible_cdo/aid/9886/jewish/Chapter-25.htm#v18',claim='Selected childlike facial interpretation.'),
                 dict(id='RASHI25-20',url='https://www.chabad.org/library/bible_cdo/aid/9886/jewish/Chapter-25.htm#v20',claim='Ten tefachim clearance beneath spread wings, citing Sukkah 5b.')],
        ark_spec_sha256=hashlib.sha256(ARK.read_bytes()).hexdigest(),body_cm=ark['bodyCm'],cover_cm=ark['coverCm'],cover_top_cm=cover,
        ten_tefachim_cm=10*ark['chosenIllustrativeScale']['tefachCm'],anchors=ark['keruvimAnchorsCm'],
        pose='Paired faces inward with 18 degree downward inclination. Four raised feathered wing fans shade cover; no embrace.',
        rendering_parts_not_manufacturing='Separate editable intersecting meshes are computer representation only. Torah describes cover and keruvim as one hammered work; no soldered manufacture is asserted.',
        artistic_choices=['Body silhouette, modest full-length drapery, facial anatomy and 105.5cm nominal body/head height above cover are unmeasured interpretation',
                          'Two wings per figure, feather count, fan silhouette and inward reach are authored choices, not exact source dimensions',
                          'Anchors are inherited provisional +/-40cm reservations; no exact ancient placement certification',
                          'Gold roughness .28 is artistic; no third-party textures or meshes incorporated'],
        exclusions=['No halo, fantasy armor, nude body, generic angel asset, or sexual pose','Solomon monumental olivewood keruvim and Yechezkel wall relief forms are not merged into this cover assembly'],
        limitations=['Not a Temple Institute scanned or measured replica','No rabbinic design approval; face, drapery, wing anatomy, stance and future-restoration mapping need review','Meshes overlap at sculptural joins; not a watertight boolean-unioned manufacturing object','No luchot or completed Aron interior','No native import, rendered likeness, cook, packaged acceptance or collision established by offline checks'])
    SPEC.write_text(json.dumps(source,indent=2)+'\n')
    report=dict(status='offline_geometry_validated_native_pending',dimension_status='Ark and ten-tefach clearance coupled to source scale; anatomy and feather layout illustrative',source_spec_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parts=[],triangles=0,namespace=DEST)
    lines=['# Original interpretive paired keruvim; assembly-local cm','o SM_KeruvimStudyV1'];index=1;all_vertices=[]
    for part in parts:
        vertices,faces=part['mesh'];all_vertices.extend(vertices);edges={};volume=0
        keys=[tuple(round(x,6) for x in v) for v in vertices]
        lines.append('g '+part['name'])
        for a,b,c in faces:
            va,vb,vc=vertices[a],vertices[b],vertices[c]
            volume+=sum(va[i]*[vb[1]*vc[2]-vb[2]*vc[1],vb[2]*vc[0]-vb[0]*vc[2],vb[0]*vc[1]-vb[1]*vc[0]][i] for i in range(3))/6
            for i,j in [(a,b),(b,c),(c,a)]:
                edge=tuple(sorted([keys[i],keys[j]]));edges[edge]=edges.get(edge,0)+1
            adapted=[(v[0],-v[1],v[2]) for v in (va,vc,vb)]
            aa,bb,cc=adapted;ab=[bb[i]-aa[i] for i in range(3)];ac=[cc[i]-aa[i] for i in range(3)]
            n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
            length=math.sqrt(sum(q*q for q in ab));area=math.sqrt(sum(q*q for q in n));assert area>1e-8
            normal=[q/area for q in n];uv=[(0,0),(length/10,0),(sum(ac[i]*ab[i]/length for i in range(3))/10,area/length/10)]
            for v in adapted:lines.append('v %.9f %.9f %.9f'%v)
            for v in uv:lines.append('vt %.9f %.9f'%v)
            for _ in range(3):lines.append('vn %.9f %.9f %.9f'%tuple(normal))
            lines.append('f '+' '.join('%d/%d/%d'%(i,i,i) for i in range(index,index+3)));index+=3
        assert volume>0 and all(n==2 for n in edges.values()),part['name']
        report['parts'].append(dict(name=part['name'],kind=part['kind'],triangles=len(faces),first_triangle=report['triangles'],closed_welded_edges=True,signed_volume_cm3=volume));report['triangles']+=len(faces)
    report['counts']={k:sum(p['kind']==k for p in parts) for k in sorted(set(p['kind'] for p in parts))}
    assert report['counts']['body']==2 and report['counts']['head']==2 and report['counts']['primary_feather']==52 and report['counts']['covert_feather']==28
    report['bounds_cm']={k:[fn(v[i] for v in all_vertices) for i in range(3)] for k,fn in [('min',min),('max',max)]}
    assert abs(report['bounds_cm']['min'][2]-cover)<1e-6
    assert max(abs(v[0]) for v in all_vertices)<62.5 and max(abs(v[1]) for v in all_vertices)<37.5
    wingmin=min(v[2] for p in parts if 'feather' in p['kind'] for v in p['mesh'][0]);assert abs(wingmin-cover-source['ten_tefachim_cm'])<1e-6
    report['wing_underside_clearance_cm']=wingmin-cover
    report['pose_checks']={'paired_bodies':True,'all_geometry_over_cover_xy':True,'body_contacts_cover':True,'minimum_wing_clearance_ten_tefachim':True,'inward_downward_faces_by_construction':True}
    path=FOLDER/'SM_KeruvimStudyV1.obj';path.write_text('\n'.join(lines)+'\n',encoding='ascii')
    report['file']=path.name;report['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    # Editable indexed canonical geometry preserves semantic pieces and source axes.
    (FOLDER/'editable-assembly.json').write_text(json.dumps(parts,separators=(',',':'))+'\n')
    (FOLDER/'geometry-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def run_native():
    """Root-run asset import only; reviewed keilim OBJ adapter settings."""
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve()!=ROOT or ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Use the intended editor outside gameplay')
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_directory_exist(DEST):raise RuntimeError('Existing native namespace preserved')
    report=json.loads((FOLDER/'geometry-manifest.json').read_text())
    path=FOLDER/report['file']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=report['sha256']:raise RuntimeError('Geometry hash changed')
    if hashlib.sha256(SPEC.read_bytes()).hexdigest()!=report['source_spec_sha256']:raise RuntimeError('Reference spec changed')
    source=json.loads(SPEC.read_text())
    if hashlib.sha256(ARK.read_bytes()).hexdigest()!=source['ark_spec_sha256']:raise RuntimeError('Coupled Aron dimensions changed')
    receipt=dict(status='import_started',created=[],assigned=False,map_saved=False,dimension_status=report['dimension_status'])
    try:
        tools=ue.AssetToolsHelpers.get_asset_tools();ml=ue.MaterialEditingLibrary
        gold=tools.create_asset('M_KeruvimStudyGold',DEST,ue.Material,ue.MaterialFactoryNew())
        if not gold:raise RuntimeError('Material factory failed')
        color=ml.create_material_expression(gold,ue.MaterialExpressionConstant3Vector)
        color.set_editor_property('constant',ue.LinearColor(1.0,.766,.336,1))
        assert ml.connect_material_property(color,'',ue.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(1.0,ue.MaterialProperty.MP_METALLIC),(.28,ue.MaterialProperty.MP_ROUGHNESS)]:
            node=ml.create_material_expression(gold,ue.MaterialExpressionConstant);node.set_editor_property('r',value)
            assert ml.connect_material_property(node,'',prop)
        ml.recompile_material(gold);assert assets.save_loaded_asset(gold,only_if_is_dirty=False)
        receipt['created'].append(gold.get_path_name())
        ui=ue.FbxImportUI()
        for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
            import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(key,value)
        data=ui.get_editor_property('static_mesh_import_data')
        for key,value in dict(combine_meshes=True,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,
            convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,import_uniform_scale=1.0,
            auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,
            normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(key,value)
        task=ue.AssetImportTask()
        for key,value in dict(filename=str(path),destination_path=DEST+'/Meshes',destination_name='SM_KeruvimStudyV1',
            automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=ue.FbxFactory()).items():task.set_editor_property(key,value)
        tools.import_asset_tasks([task]);objects=list(task.get_objects())
        assert len(objects)==1 and isinstance(objects[0],ue.StaticMesh)
        mesh=objects[0];box=mesh.get_bounding_box()
        actual={'min':[box.min.x,box.min.y,box.min.z],'max':[box.max.x,box.max.y,box.max.z]}
        error=max(abs(actual[k][i]-report['bounds_cm'][k][i]) for k in actual for i in range(3))
        assert error<.05 and mesh.get_num_triangles(0)==report['triangles']
        mesh.set_material(0,gold);assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
        receipt['created'].append(mesh.get_path_name())
        receipt.update(status='native_asset_saved_unassigned_visual_review_pending',bounds_cm=actual,bounds_error_cm=error,triangles=mesh.get_num_triangles(0))
    except Exception as error:
        receipt.update(status='failed_partial_assets_preserved',error=str(error));raise
    finally:(FOLDER/'native-import.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__' and '--export' in sys.argv:
    result=export();print(json.dumps({k:result[k] for k in ['triangles','counts','bounds_cm','wing_underside_clearance_cm']}))
