"""Offline input and installed-API audit for ONE me'il cloth feasibility proof.

No Unreal import, solver, build, GLB export, production write, or simulation claim.
"""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import uuid
from pathlib import Path
import numpy as np
import create_kohen_gadol_v1 as K
import measure_kohen_garment_clearance as M
from measure_pilgrim_walk import read_glb, read_accessor
from study_kohen_hem_diagnose import SOURCE, digest, protected

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenClothFeasibilityV1'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine')

def save(name, obj):
    payload=json.dumps(obj, indent=2)+'\n'
    target = OUT / name
    if target.exists():
        raise FileExistsError(target)
    temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8') as f:
        f.write(payload)
    # Windows rename refuses an existing destination; never replace evidence.
    temporary.rename(target)

def api_evidence():
    specs = {
      'Source/Runtime/ClothingSystemRuntimeCommon/Public/ClothingAsset.h': ['virtual bool BindToSkeletalMesh', '#if WITH_EDITOR'],
      'Source/Runtime/ClothingSystemRuntimeCommon/Private/ClothingAsset.cpp': ['Error_LodMapped', 'bMeshClothingAssetsWasFound'],
      'Source/Editor/ClothingSystemEditorInterface/Public/ClothingAssetFactoryInterface.h': ['Clothing file import is no longer supported', 'CreateFromSkeletalMesh'],
      'Plugins/ChaosClothAsset/Source/ChaosClothAssetEngine/Public/ChaosClothAsset/ClothAsset.h': ['void Build(', 'SetClothCollections', 'SetReferenceSkeleton is deprecated'],
      'Plugins/ChaosClothAsset/Source/ChaosClothAssetEngine/Public/ChaosClothAsset/ClothAssetSKMClothingAsset.h': ['void SetAsset(', 'private:', 'virtual bool BindToSkeletalMesh'],
      'Plugins/ChaosClothAsset/Source/ChaosClothAssetEngine/Private/ChaosClothAsset/ClothAssetSKMClothingAsset.cpp': ['Must return true, this is to avoid breaking the binding', 'MatchingDeformerSectionIndex', 'GenerateMeshToMeshVertData'],
      'Plugins/ChaosClothAsset/Source/ChaosClothAsset/Public/ChaosClothAsset/CollectionClothSimPatternFacade.h': ['void Initialize(const TArray<FVector2f>'],
      'Plugins/ChaosCloth/Source/ChaosCloth/Public/ChaosCloth/ChaosClothingSimulationConfig.h': ['void Initialize(const UChaosClothConfig', 'GetPropertyCollection(int32'],
      'Plugins/ChaosCloth/Source/ChaosCloth/Private/ChaosCloth/ChaosClothingSimulationConfig.cpp': ['UseSelfCollisionsName', 'MaxDistanceName'],
      'Source/Runtime/Experimental/Chaos/Public/Chaos/PBDTriangleMeshCollisions.h': ['GetSelfCollideAgainstAllKinematicVertices(PropertyCollection, false)', 'GetUseSelfCollisions(PropertyCollection, false)'],
      'Source/Runtime/Experimental/Chaos/Private/Chaos/PBDTriangleMeshCollisions.cpp': ['bCollideAgainstAllKinematicVertices || InEnabledKinematicFaces.Contains', 'KinematicColliderSubMesh.Init'],
      'Plugins/ChaosCloth/Source/ChaosCloth/Private/ChaosCloth/ChaosClothConstraints.cpp': ['CreateSelfCollisionConstraints', 'TriangleMesh,'],
      'Plugins/ChaosCloth/ChaosCloth.uplugin': ['"EnabledByDefault": true'],
      'Plugins/ChaosClothAsset/ChaosClothAsset.uplugin': ['"EnabledByDefault": false'],
    }
    rows=[]
    for rel, terms in specs.items():
        path=ENGINE/rel
        lines=path.read_text(encoding='utf-8-sig').splitlines()
        hits=[]
        for term in terms:
            found=[dict(line=i+1,text=line.strip()) for i,line in enumerate(lines) if term in line]
            assert found,(rel,term)
            hits.append(dict(term=term,matches=found))
        rows.append(dict(path=str(path),sha256=digest(path),references=hits))
    return rows

def coarse(part, dynamic):
    v=np.asarray(part['vertices'],dtype=float)
    cols=176
    assert len(v)%cols==0
    rings=len(v)//cols
    # One fixed topology, no parameter sweep. Keep both end rings and every second row.
    rr=sorted(set(range(0,rings,2))|{rings-1})
    cc=list(range(0,cols,4))
    pick=np.array([r*cols+c for r in rr for c in cc],dtype=int)
    vertices=v[pick]
    faces=[]
    # Match the authored tube winding using its first corresponding quad.
    for r in range(len(rr)-1):
        for c in range(len(cc)):
            a=r*len(cc)+c; b=r*len(cc)+(c+1)%len(cc)
            d=a+len(cc); e=b+len(cc)
            faces.extend([(a,b,d),(b,e,d)])
    faces=np.array(faces,dtype=int)
    normal=np.cross(vertices[faces[0,1]]-vertices[faces[0,0]],vertices[faces[0,2]]-vertices[faces[0,0]])
    first=v[np.asarray(part['faces'][0])]
    ref=np.cross(first[1]-first[0],first[2]-first[0])
    if normal@ref<0: faces=faces[:,[0,2,1]]
    bones=K.C.skeleton(); index={b['name']:i for i,b in enumerate(bones)}
    influences=[]
    for p in vertices:
        if dynamic:
            # Reference/support follows torso/pelvis, never ankle rotation.
            raw=K.C.torso_skin(tuple(p)) if p[2]>=K.F_TOP else {'pelvis':1.}
            values=[(index[n],float(w)) for n,w in raw.items() if w>0]
        else:
            values=[(int(j),float(w)) for j,w in K.influence(part,tuple(p),index) if w>0]
        influences.append(values)
    md=np.where(vertices[:,2]>=99,0.,60.) if dynamic else np.zeros(len(vertices))
    # Barycentric correspondence is restricted to the OUTER source topology.
    # Three coefficients may extrapolate; rest residual retains authored folds.
    bindings=[]; worst=0.
    for i,p in enumerate(v):
        r,c=divmod(i,cols)
        ri=int(min(np.searchsorted(rr,r,side='right')-1,len(rr)-2))
        ci=c//4
        f=(r-rr[ri])/(rr[ri+1]-rr[ri]); g=(c%4)/4
        ids=[ri*len(cc)+ci,ri*len(cc)+(ci+1)%len(cc),(ri+1)*len(cc)+ci]
        weights=[1-f-g,g,f]
        if f+g>1:
            ids=[ri*len(cc)+(ci+1)%len(cc),(ri+1)*len(cc)+(ci+1)%len(cc),(ri+1)*len(cc)+ci]
            weights=[1-f,f+g-1,1-g]
        base=np.asarray(weights)@vertices[ids]
        residual=p-base
        worst=max(worst,float(np.linalg.norm(residual)))
        bindings.append(dict(indices=ids,bary=weights,restResidualCm=residual.tolist()))
        assert np.linalg.norm(base+residual-p)<1e-10
    return dict(name=part['name'],dynamic=dynamic,verticesCm=vertices.tolist(),
        faces=faces.tolist(),sourceVertexIndices=pick.tolist(),boneInfluences=influences,
        maxDistanceCm=md.tolist(),sourceVertices=len(v),sourceFaces=len(part['faces']),
        sourceRingIndices=rr,sourceColumnIndices=cc,
        maxRestInterpolationResidualCm=worst),bindings

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    save('preservation-before.json',protected())
    assert digest(SOURCE)=='b542efdc1a053fd5ae59720a578701355a4a6e5a203691d999755d6ee4f67535'
    K.KNEE_TOP,K.KNEE_BOT=65,20
    bones,index,parts,influence,*_=M.body_parts('kohen')
    by={p['name']:p for p in parts}
    doc,binary=read_glb(SOURCE)
    inventory=[]
    for mi,mesh in enumerate(doc['meshes']):
        for pi,prim in enumerate(mesh['primitives']):
            mat=doc['materials'][prim['material']]['name']
            inventory.append(dict(mesh=mi,primitive=pi,material=mat,
                vertices=doc['accessors'][prim['attributes']['POSITION']]['count'],
                triangles=doc['accessors'][prim['indices']]['count']//3,
                generatedPartNames=[p['name'] for p in parts if p['material']==mat],
                nativeSectionIndex=None))
    save('material-inventory.json',dict(sourceSha256=digest(SOURCE),sourcePrimitives=inventory,
        warning='GLB primitives are NOT confirmed native LOD section IDs. Native bridge resolves material names and exact source position multiset; refuses ambiguous/split sections.',
        selectedMaterial='KG_Meil',selectedParts=['Meil','MeilHemBinding','MeilNeckBinding'],
        excluded='All other sections remain unbound, including face/hair/turban, linen, gold and wool ornaments. Decoration response remains outside this first shell feasibility proof.'))
    outer,bindings=coarse(by['Meil'],True)
    inner,_=coarse(by['Ketonet'],False)
    save('outer-correspondence.json',dict(scope='Topological reference map, NOT claimed native interpolation or collision fidelity.',vertices=bindings))
    selected=next(p for p in doc['meshes'][0]['primitives'] if doc['materials'][p['material']]['name']=='KG_Meil')
    author=lambda v:[v[0]*100,-v[2]*100,v[1]*100]
    renderpoints=[author(v) for v in read_accessor(doc,binary,selected['attributes']['POSITION'])]
    model=dict(schema='kohen-cloth-feasibility-v1',status='offline-input-only',sourceSha256=digest(SOURCE),
        units='author cm; bridge must establish source-to-native axis mapping from all27bind bones',
        bones=[dict(name=b['name'],positionCm=b['position_cm']) for b in bones],
        patterns=[outer,inner],selectedMaterial='KG_Meil',selectedSourceRenderPositionsCm=renderpoints,
        settings=dict(selfCollisions=True,selfCollideAgainstAllKinematicVertices=True,
                      selfCollisionThicknessCm=.5,gravityCmS2=[0,0,-980.665],lowerAnimDrive=0),
        walk=dict(glb=str(M.CLIPS[0][1].relative_to(ROOT)),clip=M.CLIPS[0][2],animationSha256=digest(M.CLIPS[0][1]),
                  diagnosticTimeSeconds=.295833,onlyClip='walk',futureDurationSeconds=1.2),
        limits=dict(maxSimulationVertices=4096,maxRenderVertices=20000,noSave=True,noProductionBinding=True))
    save('prototype-input.json',model)
    # Evaluate the kinematic proxy's fidelity at ONE requested pose, not a clip sweep.
    rig=M.Rig(M.CLIPS[0][1],M.CLIPS[0][2]); a,b=M.joint_affines(rig,rig.pose(.295833),bones)
    errors=[]
    for p,coarse_data in [(by['Ketonet'],inner)]:
        v,j,w=M.skin_arrays(p,influence,index); actual=M.skin(v,j,w,a,b)
        _,map_=coarse(p,False)
        cv=actual[coarse_data['sourceVertexIndices']]
        for i,row in enumerate(map_):
            approximate=np.asarray(row['bary'])@cv[row['indices']]
            errors.append(float(np.linalg.norm(approximate-actual[i])))
    save('offline-checks.json',dict(passed=True,outerVertices=len(outer['verticesCm']),innerVertices=len(inner['verticesCm']),
        totalSimulationVertices=len(outer['verticesCm'])+len(inner['verticesCm']),
        correspondenceRestReconstructionMaxCm=1e-10,kinematicProxyOnePoseMaxErrorCm=max(errors),
        kinematicProxyOnePoseP95ErrorCm=float(np.percentile(errors,95)),
        coarseCollisionProxyAccepted=max(errors)<.5,
        notes=['Rest correspondence is exact only with stored residuals; solver collision triangles do not include those residuals.',
               'No solver ran; no drape/clearance acceptance. If proxy error exceeds0.5cm, coordinator must resolve topology/contact representation before collision claims.']))
    save('api-evidence.json',api_evidence())
    print('Prepared',len(outer['verticesCm'])+len(inner['verticesCm']),'simulation vertices; one-pose proxy maximum error',max(errors))

if __name__=='__main__': run()
