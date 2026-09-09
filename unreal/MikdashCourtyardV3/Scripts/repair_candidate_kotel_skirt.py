"""Candidate48-only create-once Skirt collision duplicate; source untouched.
Use -CandidateKotelSkirtExpectedHash=<reviewed candidate SHA256> to apply, or
-CandidateKotelSkirtVerify=<absolute apply receipt> from a fresh process.
Shallow local TRIM_INSIDE on duplicate only. Native two-way walk remains pending.
"""
import json
import math
import itertools
import os
from pathlib import Path
import re
import shutil
import struct
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
from release_surface_soft import sha, inventory, check_hashes
from release_place_assets import snapshot_row, numeric_baseline_rows, baseline_key

TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
EXPECTED = 'dcea5bf85498cabd519c182e3665792cbe732d358ebac94cdfcdec0032c0e7e1'
SOURCE = '/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Skirt'
NAMESPACE = '/Game/MikdashV3/CandidateKotelSkirtV2'
CLONE = NAMESPACE + '/SM_MountPlatform_Skirt_Notched'
SOURCE_SHA='5670ca80b81d7558890d8ea4bde8179a69ae37a7643ebe4f2325cd6b9ec73f96'
MANIFEST=ROOT/'SourceAssets/FutureMountV1/mount-platform.mesh.json'
MANIFEST_SHA='693d76b5bae73e4ed70f80e4fb48e19c3834ec4f505c873c622465c57b41c524'
CUT=[[-13650,19822.432518,-25],[-13540,20122.432518,10]]


def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def area(poly):
    return sum(math.sqrt(dot(v,v))*.5 for v in [cross(sub(poly[i],poly[0]),sub(poly[i+1],poly[0])) for i in range(1,len(poly)-1)]) if len(poly)>2 else 0.
def inside_polygon(poly,bounds=CUT):
    for axis in range(3):
        for bound,sign in ((bounds[0][axis],1),(bounds[1][axis],-1)):
            out=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                da=(a[axis]-bound)*sign;db=(b[axis]-bound)*sign
                if da>=0:out.append(a)
                if (da>=0)!=(db>=0):
                    t=da/(da-db);out.append([a[j]+t*(b[j]-a[j]) for j in range(3)])
            poly=out
            if not poly:return []
    return poly
def bary(p,tri):
    a,b,c=tri;v0=sub(b,a);v1=sub(c,a);v2=sub(p,a)
    den=dot(v0,v0)*dot(v1,v1)-dot(v0,v1)**2
    if abs(den)<1e-12:return None
    v=(dot(v1,v1)*dot(v2,v0)-dot(v0,v1)*dot(v2,v1))/den
    w=(dot(v0,v0)*dot(v2,v1)-dot(v0,v1)*dot(v2,v0))/den
    weights=[1-v-w,v,w];projection=[sum(weights[i]*tri[i][j] for i in range(3)) for j in range(3)]
    return weights if min(weights)>=-1e-5 and math.dist(projection,p)<.02 else None


def rows_with_attributes(native,dynamic):
    u=native.ue;q=native.query
    result=native.triangle_rows(dynamic)
    def triple(value,typ,fields):
        vals=[x for x in value if isinstance(x,typ)]
        valid=[x for x in value if isinstance(x,bool)]
        if valid!=[True] or len(vals)!=3:raise RuntimeError('Unsupported/missing triangle attribute return shape')
        return [[getattr(x,k) for k in fields] for x in vals]
    for r in result:
        tid=r['tid'];attrs={}
        material=u.GeometryScript_Materials.get_triangle_material_id(dynamic,tid)
        ids=[v for v in material if type(v) is int]
        flags=[v for v in material if type(v) is bool]
        if len(ids)!=1 or flags!=[True]:raise RuntimeError('Triangle material ID readback failed')
        r['materialId']=ids[0]
        for index in range(q.get_num_uv_sets(dynamic)):
            query_uv=getattr(q,'get_triangle_uvs',None) or getattr(q,'get_triangle_u_vs',None)
            if query_uv is None:raise RuntimeError('UV readback API unavailable; no mutation allowed')
            attrs['uv'+str(index)]=triple(query_uv(dynamic,index,tid),u.Vector2D,('x','y'))
        if q.get_has_triangle_normals(dynamic):attrs['normal']=triple(q.get_triangle_normals(dynamic,tid),u.Vector,('x','y','z'))
        if q.get_has_vertex_colors(dynamic):attrs['color']=triple(q.get_triangle_vertex_colors(dynamic,tid),u.LinearColor,('r','g','b','a'))
        r['attrs']=attrs
    return result


def source_geometry(mesh,report=None):
    from release_fix_kotel_occlusion import Native
    if sha(MANIFEST)!=MANIFEST_SHA:raise RuntimeError('Frozen platform manifest differs')
    native=Native();dynamic=native.source_dynamic_mesh(mesh)
    rows=rows_with_attributes(native,dynamic)
    src=json.loads(MANIFEST.read_text())['skirt']
    expected=[sorted([src['vertices'][i] for i in t]) for t in src['triangles']]
    actual=sorted([sorted(r['positions']) for r in rows]);expected.sort()
    def bounds(triangles):
        vertices=[p for t in triangles for p in t]
        return [[min(p[j] for p in vertices) for j in range(3)],[max(p[j] for p in vertices) for j in range(3)]] if vertices else None
    mismatch=[i for i,(a,b) in enumerate(zip(actual,expected)) if any(math.dist(x,y)>.05 for x,y in zip(a,b))]
    diagnostic={'actualTriangles':len(actual),'sourceTriangles':len(expected),
                'actualBounds':bounds(actual),'sourceBounds':bounds(expected),
                'lexicographicMismatchCount':len(mismatch),'toleranceCm':.05,
                'extraction':{'lod':'SOURCE_MODEL','lodIndex':0,'applyBuildSettings':False,'useBuildScale':False,'requestTangents':False},
                'closestTriangleExamples':[]}
    if mismatch or len(actual)!=len(expected):
        # Retain nearest-coordinate diagnostics, but acceptance below requires
        # a complete one-to-one match, not independent nearest neighbours.
        for index in (mismatch or list(range(min(8,len(actual)))))[:8]:
            tri=actual[index]
            best=min((max(math.dist(a,b) for a,b in zip(tri,permutation)),j,permutation)
                     for j,other in enumerate(expected) for permutation in itertools.permutations(other))
            diagnostic['closestTriangleExamples'].append({'actualSortedIndex':index,'sourceSortedIndex':best[1],
                'maxCornerDistanceCm':best[0],'actual':tri,'closestSource':best[2],
                'cornerDeltasCm':[sub(a,b) for a,b in zip(tri,best[2])]})
    # Native float conversion made four equal-X triangles sort differently
    # (diagnostic092204: maximum nearest-corner error <0.001cm). Match the
    # remaining triangles one-to-one, retaining the original 0.05cm tolerance.
    # Never accept only a nearest match without accounting for multiplicity.
    matched={}
    choices={i:[j for j in mismatch if any(all(math.dist(a,b)<=.05 for a,b in zip(actual[i],perm))
               for perm in itertools.permutations(expected[j]))] for i in mismatch}
    def assign(i,seen):
        for j in choices[i]:
            if j in seen:continue
            seen.add(j)
            if j not in matched or assign(matched[j],seen):
                matched[j]=i
                return True
        return False
    geometry_matches=len(actual)==len(expected) and all(assign(i,set()) for i in mismatch)
    diagnostic['oneToOneResidualPairs']=[{'actualSortedIndex':i,'sourceSortedIndex':j} for j,i in sorted(matched.items())]
    diagnostic['permutationInvariantGeometryMatches']=geometry_matches
    if report is not None:report['sourceGeometryDiagnostic']=diagnostic
    if not geometry_matches:
        raise RuntimeError('Native SOURCE_MODEL triangles do not match frozen full skirt source')
    if len(rows)!=1824:raise RuntimeError('Unexpected skirt topology')
    return native,dynamic,rows


def verify_geometry(native,original,dynamic,serialized=False):
    current=rows_with_attributes(native,dynamic)
    # Persisted MeshDescription positions are float32. Receipt100352 shows
    # upperY20122.432518 serializes exactly to20122.431640625 (0.000877375cm).
    # Use that exact representation for saved-boundary intersection only;
    # retain the same area threshold and all source/attribute checks.
    boundary = [[struct.unpack('f',struct.pack('f',v))[0] for v in side] for side in CUT] if serialized else CUT
    removed=sum(area(inside_polygon(r['positions'])) for r in original)
    expected=sum(area(r['positions']) for r in original)-removed
    actual=sum(area(r['positions']) for r in current)
    if not 7400<removed<7900 or abs(actual-expected)>1.0:raise RuntimeError('Clipped area differs from exact box/triangle intersection')
    # Every output fragment must lie on a single original triangle and carry
    # its interpolated UVs/normals/colors. No invented caps, shifted surface,
    # or collapsed whole-skirt rebuild is accepted.
    bounded=[(old,[min(p[j] for p in old['positions'])-.02 for j in range(3)],
                    [max(p[j] for p in old['positions'])+.02 for j in range(3)]) for old in original]
    fragments={}
    for r in current:
        face=cross(sub(r['positions'][1],r['positions'][0]),sub(r['positions'][2],r['positions'][0]))
        if dot(face,face)<1e-12:raise RuntimeError('Degenerate output triangle')
        intrusion = area(inside_polygon(r['positions'],boundary))
        if intrusion>.01:
            raise RuntimeError('Geometry remains inside notch: '+json.dumps({'triangle':r['tid'],
                'positions':r['positions'],'intersection':inside_polygon(r['positions'],boundary),
                'insideAreaCm2':intrusion,'cut':boundary,'resultTriangles':len(current)}))
        candidates=[]
        for old,lo,hi in bounded:
            if any(p[j]<lo[j] or p[j]>hi[j] for p in r['positions'] for j in range(3)):continue
            weights=[bary(p,old['positions']) for p in r['positions']]
            if all(w is not None for w in weights):candidates.append((old,weights))
        valid=False
        for old,weights in candidates:
            source_face=cross(sub(old['positions'][1],old['positions'][0]),sub(old['positions'][2],old['positions'][0]))
            if dot(face,source_face)<=0 or r['materialId']!=old['materialId']:continue
            if set(old['attrs'])!=set(r['attrs']):continue
            okay=True
            for name,values in old['attrs'].items():
                for i,w in enumerate(weights):
                    wanted=[sum(w[j]*values[j][k] for j in range(3)) for k in range(len(values[0]))]
                    if name=='normal':
                        length=math.sqrt(dot(wanted,wanted))
                        if length:wanted=[v/length for v in wanted]
                    if math.dist(wanted,r['attrs'][name][i])>.002:okay=False
            if okay:
                fragments.setdefault(old['tid'],[]).append(r['positions'])
                valid=True
                break
        if not valid:raise RuntimeError('Output fragment geometry/attributes differ from source')
    # Unaffected triangles must survive exactly, irrespective of triangle IDs.
    def key(p):return tuple(sorted(tuple(round(x,3) for x in v) for v in p))
    keys={key(r['positions']) for r in current}
    unchanged=[r for r in original if area(inside_polygon(r['positions']))<1e-6]
    numeric_fallback=[]
    missing=[]
    for r in unchanged:
        if key(r['positions']) in keys:continue
        pieces=fragments.get(r['tid'],[])
        # Boolean identity transforms move a few half-rounding coordinates by
        # ~1e-12cm (diagnostic093247). Require the SAME single triangle within
        # 1e-6cm, much tighter than a rounded millimetre key; no subdivisions.
        if len(pieces)==1 and any(all(math.dist(a,b)<=1e-6 for a,b in zip(r['positions'],perm))
                                 for perm in itertools.permutations(pieces[0])):
            numeric_fallback.append(r['tid'])
        else:missing.append(r)
    if missing:
        examples=[{'tid':r['tid'],'positions':r['positions'],
                   'originalArea':area(r['positions']),
                   'matchedFragmentArea':sum(area(p) for p in fragments.get(r['tid'],[])),
                   'fragments':fragments.get(r['tid'],[])} for r in missing[:4]]
        raise RuntimeError('Unrelated triangle topology changed: '+json.dumps({'count':len(missing),'examples':examples}))
    return {'originalTriangles':len(original),'resultTriangles':len(current),'removedAreaCm2':removed,
            'boundaryRepresentation':'float32 persisted' if serialized else 'double precision operation',
            'checkedBoundaryCm':boundary,
            'retainedAreaDifferenceCm2':actual-expected,'unchangedTriangles':len(unchanged),
            'unchangedTriangleNumericFallbacks':numeric_fallback,'numericFallbackToleranceCm':1e-6,
            'attributeChecks':'Every output corner checked against source interpolation; all untouched triangle geometry retained',
            'runtimeAcceptance':'Pending real two-way walking; geometry/collision persistence is not traversal proof'}


def trim_clone(native,dynamic,original,clone):
    u=native.ue
    cutter=u.DynamicMesh();center=[(a+b)*.5 for a,b in zip(*CUT)];size=sub(CUT[1],CUT[0])
    u.GeometryScript_Primitives.append_box(cutter,u.GeometryScriptPrimitiveOptions(),
        u.Transform(location=u.Vector(*center)),*size,origin=u.GeometryScriptPrimitiveOriginMode.CENTER)
    options=u.GeometryScriptMeshBooleanOptions()
    for k,v in [('fill_holes',False),('simplify_output',False),('allow_empty_result',False)]:options.set_editor_property(k,v)
    u.GeometryScript_MeshBooleans.apply_mesh_boolean(dynamic,u.Transform(),cutter,u.Transform(),u.GeometryScriptBooleanOperation.TRIM_INSIDE,options)
    result=verify_geometry(native,original,dynamic)
    # Preserve normal/UV/color overlays and existing material slots; no Nanite fallback.
    copy=u.GeometryScriptCopyMeshToAssetOptions()
    for k,v in [('enable_recompute_normals',False),('enable_recompute_tangents',False),('enable_remove_degenerates',False),
                ('use_original_vertex_order',False),('replace_materials',False),('apply_nanite_settings',False),
                ('emit_transaction',False),('defer_mesh_post_edit_change',False)]:copy.set_editor_property(k,v)
    lod=u.GeometryScriptMeshWriteLOD();lod.set_editor_property('write_hi_res_source',False);lod.set_editor_property('lod_index',0)
    outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,clone,copy,lod)
    if u.GeometryScriptOutcomePins.SUCCESS not in outcome:raise RuntimeError('Clone mesh write failed')
    return result


def disk(package):
    return ROOT/'Content'/(package[6:]+'.uasset')


def run(expected=None, verify=None):
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / 'SourceAssets/lighting-review'
    folder.mkdir(parents=True, exist_ok=True)
    receipt = folder / ('candidate-kotel-skirt-' + stamp + '.json')
    mapfile = ROOT / 'Content' / (TARGET[6:] + '.umap')
    report = {'status':'started', 'map':TARGET, 'pid':os.getpid(), 'errors':[],
              'mapSaved':False, 'review':'Collision experiment only; native runtime/visual acceptance pending',
              'source':SOURCE, 'clone':CLONE}
    protected = {}
    before = sha(mapfile)
    report['mapSha256Before'] = before
    def write():
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    write()
    try:
        if bool(expected) == bool(verify):
            raise RuntimeError('Choose explicit expected-hash apply or fresh verify')
        inventory()
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        earlier = json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
        if earlier:
            # Exact preserved post-save failure: misspelled reflected property,
            # not a failed geometry/preservation check. Recovery is read-only.
            recovery = (sha(Path(verify)) == '8d19260e4e46c8f3506e5d08f9efb14927596335d134535f8c04c2ba26e6502a'
                        and earlier.get('status') == 'failed' and earlier.get('mapSaved') is True
                        and earlier.get('protectedDifferences') == [] and earlier.get('unexpectedNewContent') == [])
            if (earlier.get('status') != 'saved_reopened' and not recovery) or earlier.get('map') != TARGET or type(earlier.get('pid')) is not int or earlier.get('pid',0)<=0 or earlier.get('pid') == os.getpid():
                raise RuntimeError('Invalid fresh verification receipt')
            if recovery: report['recoveredReadbackReceipt'] = str(Path(verify).resolve())
            if earlier.get('source') != SOURCE or earlier.get('clone') != CLONE:
                raise RuntimeError('Receipt scope differs')
            if check_hashes(earlier['protected']):
                raise RuntimeError('Protected content changed since apply')
            if earlier.get('cutBoundsCm') != CUT: raise RuntimeError('Cut scope differs')
            expected = earlier['mapSha256After']
        elif expected != EXPECTED:
            raise RuntimeError('Explicit hash must match reviewed candidate state')
        if not re.fullmatch('[0-9a-f]{64}', expected or '') or before != expected:
            raise RuntimeError('Map hash mismatch')
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        def clean():
            if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('PIE or dirty packages')
        clean()
        protected = {str(p):sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p != mapfile}
        report['protected'] = protected
        if not levels.load_level(TARGET):
            raise RuntimeError('Load failed')
        clean()
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Wrong world')
        source_mesh = u.load_asset(SOURCE)
        if source_mesh is None: raise RuntimeError('Skirt source absent')
        source_body=source_mesh.get_editor_property('body_setup')
        if source_body is None or source_body.get_editor_property('collision_trace_flag') != u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
            raise RuntimeError('Original skirt must already use complex-as-simple; whole-skirt physics changes are out of scope')
        report['sourceSha256'] = sha(disk(SOURCE))
        if report['sourceSha256'] != SOURCE_SHA: raise RuntimeError('Pinned skirt source changed')
        native, original_dynamic, original_rows = source_geometry(source_mesh,report)
        report['cutBoundsCm'] = CUT
        assets = u.EditorAssetLibrary
        if verify:
            if sha(disk(CLONE)) != earlier['cloneSha256']: raise RuntimeError('Clone changed since apply')
        elif assets.does_directory_exist(NAMESPACE) or disk(CLONE).parent.exists():
            raise RuntimeError('Create-once namespace already exists; do not overwrite')
        descriptor_class = u.load_class(None, '/Script/MikdashRuntime.MikdashSceneUnits')
        if descriptor_class is None:
            raise RuntimeError('Scene descriptor class absent')
        def validate_frame():
            descriptors = [a for a in actors.get_all_level_actors()
                           if u.MathLibrary.class_is_child_of(a.get_class(), descriptor_class)]
            if len(descriptors) != 1:
                raise RuntimeError('Exactly one scene descriptor class/subclass required')
            descriptor = descriptors[0]
            pivot = descriptor.get_editor_property('fixed_architecture_origin_cm')
            if descriptor.get_actor_label() != 'RELEASE_SceneUnits_Selected48_V1' or descriptor.get_outermost().get_name() != TARGET:
                raise RuntimeError('Descriptor label/ownership mismatch')
            if int(descriptor.get_editor_property('descriptor_schema_version')) != 1 or int(descriptor.get_editor_property('coordinate_revision').value) != 1 or str(descriptor.get_editor_property('scene_revision')) != 'Selected48.v1' or [pivot.x,pivot.y,pivot.z] != [-6200,0,0]:
                raise RuntimeError('Selected48 version/pivot mismatch')
            report['sceneFrame'] = {'schema':1, 'revision':'Selected48.v1', 'pivot':[-6200,0,0]}
        def discover():
            validate_frame()
            found = []
            for actor in actors.get_all_level_actors():
                for comp in actor.get_components_by_class(u.StaticMeshComponent):
                    mesh = comp.get_editor_property('static_mesh')
                    if mesh and mesh.get_path_name().split('.')[0] in (SOURCE,CLONE):
                        if actor.get_outermost().get_name() != TARGET: raise RuntimeError('Wrong owner')
                        found.append((actor,comp))
            if len(found) != 1: raise RuntimeError('Exactly one Skirt component required')
            from kotel_photo_pie_review import _state
            if _state(*found[0])['pose'] != [0,0,0,0,0,0,1,1,1]: raise RuntimeError('Skirt must retain metric identity transform')
            return found
        def identity(found):
            return [[a.get_name(),c.get_name()] for a,c in found]
        def snapshot():
            aa = list(actors.get_all_level_actors())
            rows = [snapshot_row(u,a,TARGET) for a in aa]
            for row in rows:
                # snapshot_row uses _asset_path(), which returns package-only paths.
                row['meshes'] = [SOURCE if p == CLONE else p for p in row['meshes']]
            result = numeric_baseline_rows(rows, strict=True)
            # Receipt093726: only this mesh's derived bounds tightened after
            # source-model copy (old maxZ64.9932 -> source maxZ0). UE StaticMesh
            # CalculateExtendedBounds prefers CachedMeshDescriptionBounds over
            # RenderData->Bounds. Retain strict bounds on every OTHER actor;
            # this exact target is instead checked by full source/trim geometry,
            # identity pose, materials and raw collision state.
            target_names={a.get_name() for a,c in discover()}
            for row in rows:
                if row['name'] in target_names:
                    result[row['name']]=baseline_key(row,strict=False)
                    observed={'actor':row['name'],'bounds':row['bounds']}
                    history=report.setdefault('targetDerivedBoundsReadbacks',[])
                    if not history or history[-1]!=observed:history.append(observed)
            for actor in aa:
                if actor.get_outermost().get_name() != TARGET:
                    continue
                for comp in actor.get_components_by_class(u.StaticMeshComponent):
                    mesh = comp.get_editor_property('static_mesh')
                    package = mesh.get_path_name().split('.')[0] if mesh else None
                    for slot in range(comp.get_num_materials()):
                        mat = comp.get_material(slot)
                        result['material:' + comp.get_path_name() + ':' + str(slot)] = mat.get_path_name() if mat else None
            from kotel_photo_pie_review import _state
            for a,c in discover():
                state=_state(a,c);state['mesh']=SOURCE
                result['targetState']=state
            return json.loads(json.dumps(result))
        found = discover()
        identities = identity(found)
        if earlier and earlier['components'] != identities:
            raise RuntimeError('Fresh component identity differs')
        report['components'] = identities
        baseline = snapshot()
        if earlier and baseline != earlier['baseline']: raise RuntimeError('Unrelated persisted baseline changed')
        report['baseline'] = baseline
        clean()
        if not levels.load_level(TARGET):
            raise RuntimeError('Pristine reload failed')
        clean()
        found = discover()
        if identity(found) != identities or snapshot() != baseline:
            raise RuntimeError('Pristine reload churn: review before mutation')
        if not verify:
            if found[0][1].get_editor_property('static_mesh') != source_mesh:
                raise RuntimeError('Original component binding required')
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('CandidateKotelSkirtV1-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            shutil.copy2(mapfile, checkpoint/mapfile.name)
            if sha(checkpoint/mapfile.name) != before:
                raise RuntimeError('Checkpoint hash mismatch')
            for name in ('__ExternalActors__','__ExternalObjects__'):
                source = ROOT/'Content'/name/TARGET[6:]
                if source.exists():
                    shutil.copytree(source, checkpoint/name/TARGET[6:])
            report['checkpoint'] = str(checkpoint)
            write()
            clone = assets.duplicate_asset(SOURCE,CLONE)
            if clone is None: raise RuntimeError('Duplicate failed')
            body = clone.get_editor_property('body_setup')
            if body is None: raise RuntimeError('Duplicated mesh has no BodySetup')
            if body == source_mesh.get_editor_property('body_setup') or body.get_outer() != clone:
                raise RuntimeError('Duplicate must own an independent BodySetup before mutation')
            report['geometry'] = trim_clone(native, original_dynamic, original_rows, clone)
            body = clone.get_editor_property('body_setup')
            if body is None or body == source_mesh.get_editor_property('body_setup') or body.get_outer() != clone: raise RuntimeError('Post-copy BodySetup ownership differs')
            body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            if body.get_editor_property('collision_trace_flag') != u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
                raise RuntimeError('Collision flag readback failed')
            # Existing project importer uses BodySetup setter + save_loaded_asset.
            # Fresh process and real traces still must verify physics cook behavior.
            if not assets.save_loaded_asset(clone,only_if_is_dirty=False): raise RuntimeError('Clone save failed')
            report['cloneSha256'] = sha(disk(CLONE))
            write()
            actor,comp = found[0]
            actor.modify(True); comp.modify(True)
            comp.set_static_mesh(clone)
            if comp.get_editor_property('static_mesh') != clone: raise RuntimeError('Binding failed')
            current_snapshot = snapshot()
            if current_snapshot != baseline or check_hashes(protected):
                changed = [k for k in sorted(set(baseline)|set(current_snapshot)) if baseline.get(k)!=current_snapshot.get(k)]
                report['snapshotDifferenceCountBeforeSave'] = len(changed)
                report['snapshotDifferencesBeforeSave'] = {k:{'before':baseline.get(k),'after':current_snapshot.get(k)}
                    for k in changed[:20]}
                write()
                raise RuntimeError('Unrelated state changed before save')
            if not levels.save_current_level():
                raise RuntimeError('Save refused')
            report['mapSaved'] = True
            report['mapSha256After'] = sha(mapfile)
            write()
            if not levels.load_level(TARGET):
                raise RuntimeError('Reopen failed')
        found = discover()
        if identity(found) != identities or snapshot() != baseline:
            raise RuntimeError('Unrelated state or component identity changed')
        clone = found[0][1].get_editor_property('static_mesh')
        if clone.get_path_name().split('.')[0] != CLONE: raise RuntimeError('Saved clone binding differs')
        saved_body = clone.get_editor_property('body_setup')
        if saved_body is None or saved_body == source_mesh.get_editor_property('body_setup') or saved_body.get_outer() != clone:
            raise RuntimeError('Saved BodySetup ownership differs')
        if clone.get_editor_property('body_setup').get_editor_property('collision_trace_flag') != u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
            raise RuntimeError('Saved collision flag differs')
        for prop in ('double_sided_geometry',):
            if saved_body.get_editor_property(prop) != source_mesh.get_editor_property('body_setup').get_editor_property(prop):
                raise RuntimeError('BodySetup setting changed: '+prop)
        # BodySetup.BuildScale3D is protected in Python (fresh receipt095611).
        # Compare its authored source, the public static-mesh LOD build setting.
        mesh_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
        source_scale = mesh_editor.get_lod_build_settings(source_mesh,0).get_editor_property('BuildScale3D')
        clone_scale = mesh_editor.get_lod_build_settings(clone,0).get_editor_property('BuildScale3D')
        report['authoredBuildScale'] = {'source':[source_scale.x,source_scale.y,source_scale.z],
                                        'clone':[clone_scale.x,clone_scale.y,clone_scale.z],
                                        'scope':'LOD0 authored scale; protected BodySetup scale not directly readable'}
        if clone_scale != source_scale: raise RuntimeError('Authored LOD0 build scale differs')
        if clone.get_editor_property('lod_for_collision') != source_mesh.get_editor_property('lod_for_collision'):
            raise RuntimeError('Collision LOD changed')
        report['geometryReadback'] = verify_geometry(native, original_rows, native.source_dynamic_mesh(clone),serialized=True)
        def material_signature(mesh):
            return [(str(v.get_editor_property('material_slot_name')),
                     v.get_editor_property('material_interface').get_path_name() if v.get_editor_property('material_interface') else None)
                    for v in mesh.get_editor_property('static_materials')]
        if material_signature(clone) != material_signature(source_mesh):
            raise RuntimeError('Render materials differ')
        report['cloneSha256'] = sha(disk(CLONE))
        clean()
        report['runtimeCollisionAcceptance'] = 'PENDING; saved flag is not a physics trace'
        report['status'] = 'fresh_verified' if verify else 'saved_reopened'
    except Exception as error:
        report['status'] = 'failed'
        report['errors'].append(repr(error))
        raise
    finally:
        report['mapSha256After'] = sha(mapfile)
        report['protectedDifferences'] = check_hashes(protected)
        allowed_new={str(disk(CLONE))}
        report['unexpectedNewContent']=[str(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p != mapfile and str(p) not in protected and str(p) not in allowed_new] if protected else []
        if report['protectedDifferences'] or report['unexpectedNewContent'] or (verify and report['mapSha256After'] != before):
            report['status'] = 'failed_preservation'
        write()
    if report['status'].startswith('failed'):
        raise RuntimeError(report['status'])
    return report


if __name__ == '__main__':
    try:
        import unreal as u
    except ImportError:
        print('Prepared helper only; no native execution')
    else:
        command = u.SystemLibrary.get_command_line()
        args = {x.split('=',1)[0].lower():x.split('=',1)[1].strip('"') for x in command.split() if '=' in x}
        try:
            run(expected=args.get('-candidatekotelskirtexpectedhash'), verify=args.get('-candidatekotelskirtverify'))
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower():
                u.SystemLibrary.quit_editor()
