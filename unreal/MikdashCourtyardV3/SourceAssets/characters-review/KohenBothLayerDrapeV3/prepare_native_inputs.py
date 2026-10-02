"""Source-only additive Chaos bridge derivation. Does not stage/build/launch UE."""
import sys
sys.dont_write_bytecode=True
import copy,json
import numpy as np
import inputs as I

PROJECT_FILES=[
 'KohenClothReview.uproject','Source/KohenClothReviewEditor.Target.cs',
 'Source/KohenClothReview/KohenClothReview.cpp','Source/KohenClothReview/KohenClothReview.Build.cs',
 'Plugins/KohenClothExecutable/KohenClothExecutable.uplugin',
 'Plugins/KohenClothExecutable/Source/KohenClothExecutable/KohenClothExecutable.Build.cs',
 'Plugins/KohenClothExecutable/Source/KohenClothExecutable/Public/KohenClothExecutableLibrary.h',
 'Plugins/KohenClothExecutable/Source/KohenClothExecutable/Private/KohenClothInternal.h',
 'Plugins/KohenClothExecutable/Source/KohenClothExecutable/Private/KohenClothBuilder.cpp',
 'Plugins/KohenClothExecutable/Source/KohenClothExecutable/Private/KohenClothWalk.cpp']

def once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

def main():
    model,bones,index,by,*_=I.load();old=I.s.OLD
    manifest=json.loads((old/'source-manifest.json').read_text());root=I.HERE.parents[2]
    output=I.HERE/'NativeBridge01';output.mkdir(exist_ok=False)
    m=copy.deepcopy(model);m['schema']='kohen-both-layer-v3-support';m['status']='native-support-input-uncompiled-unrun'
    proof=[];tethers=[]
    for p,original in zip(m['patterns'][:2],model['patterns'][:2]):
        c=I.s.Layer(original);p['maxDistanceCm']=np.where(c.pin,0.,1.).tolist()
        for j in np.flatnonzero(c.pin):p['boneInfluences'][int(j)]=[[index['chest'],1.]]
        assert p['verticesCm']==original['verticesCm'] and p['faces']==original['faces']
        for j in np.flatnonzero(~c.pin):assert p['boneInfluences'][int(j)]==original['boneInfluences'][int(j)]
        proof.append(dict(layer=p['name'],fixedIds=np.flatnonzero(c.pin).tolist(),supportBone='chest',
            freeVertices=int((~c.pin).sum()),restGeometryExact=True,freeOriginalWeightsExact=True))
        tethers.append(dict(layer=p['name'],diagnosticNearestAnchor=c.anchor.tolist(),restGraphGeodesicCm=c.tether.tolist(),
            note='Native GenerateTethers regenerates actual batches; read all native anchors/lengths. This array is an independent nearest-anchor check, not substituted native data.'))
    assert m['patterns'][2:]==model['patterns'][2:]
    m['nativeSupportContract']=dict(version=1,maxDistancePropertyEnabled=False,
        maxDistanceMapRole='0/1 mass classification and tether anchors ONLY; spherical constraint disabled',
        expectedDynamic=1936,expectedKinematic=1264,firstWalkFrames=72,rateHz=240,
        ornaments='Exact group/anchor input supplied separately; no shared-material retarget and no ornament dynamics claim')
    I.s.atomic(output/'prepared-input.json',m);I.s.atomic(output/'rest-tethers.json',tethers)
    anchors=json.loads((I.s.AUDIT/'attachment-anchor-map.json').read_text())
    assert len(anchors['rows'])==144
    I.s.atomic(output/'ornament-anchor-input.json',dict(sourceSha256=I.s.sha(I.s.AUDIT/'attachment-anchor-map.json'),
        rows=anchors['rows'],scope='Exact72+72 source group ownership/hem anchors. Native binding/rigid-body hanging not implemented; no full-character acceptance.'))
    changes=[]
    for rel in PROJECT_FILES:
        source=old/'ReviewProject'/rel
        key=source.relative_to(root).as_posix();assert I.s.sha(source)==manifest['inputs'][key]
        raw=source.read_text();text=raw
        if rel.endswith('KohenClothBuilder.cpp'):
            text=once(text,'/Game/KohenBothLayerDrapeV1/Import/','/Game/KohenBothLayerDrapeV3/Import/')
            text=once(text,'kohen-both-layer-v1','kohen-both-layer-v3-support')
            marker='    Chaos::Softs::FCollectionPropertyMutableFacade Properties(Collection);'
            text=once(text,marker,marker+'\n'
                '    // UE5.8 mass predicate reads MaxDistance values independently of enabled flag.\n'
                '    // Keep 0/1 map for exact pins/tethers; do NOT clamp free cloth to skin spheres.\n'
                '    REQUIRE(Properties.SetEnabled(FName(TEXT("MaxDistance")),false)!=INDEX_NONE,"Missing MaxDistance property");\n'
                '    REQUIRE(!Properties.IsEnabled(FName(TEXT("MaxDistance"))),"Free cloth spherical clamp unexpectedly enabled");')
            marker='    REQUIRE(BuildError.IsEmpty() && S.Cloth->HasValidClothSimulationModels(),"Cloth asset Build failed; no binding attempted");'
            text=once(text,marker,marker+'\n'
                '    const auto& BuiltCollections=static_cast<const UChaosClothAsset*>(S.Cloth.Get())->GetClothCollections();\n'
                '    REQUIRE(BuiltCollections.Num()==1,"Unexpected built collection count");\n'
                '    const Chaos::Softs::FCollectionPropertyConstFacade BuiltProperties(*BuiltCollections[0]);\n'
                '    REQUIRE(!BuiltProperties.IsEnabled(FName(TEXT("MaxDistance"))),"Built asset reenabled free spherical clamp");')
        if rel.endswith('KohenClothWalk.cpp'):
            text=once(text,'/Game/KohenBothLayerDrapeV1/Import/','/Game/KohenBothLayerDrapeV3/Import/')
            text=text.replace('288','72').replace('287.f/240.f','71.f/240.f').replace('Step==287','Step==71')
            marker='    Receipt->SetNumberField(TEXT("stepSeconds"),1.0/240.0);'
            text=once(text,marker,marker+'\n'
                '    Receipt->SetBoolField(TEXT("ornamentDynamicsImplemented"),false);\n'
                '    Receipt->SetBoolField(TEXT("settledEquilibriumProven"),false);\n'
                '    Receipt->SetStringField(TEXT("scope"),TEXT("First72actual-walk API/particle readbacks only. Fixed120settle steps are not equilibrium or collision acceptance."));')
        dest=output/'ReviewProject'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text,newline='\n')
        changes.append(dict(path=rel,parentSha256=I.s.sha(source),derivedSha256=I.s.sha(dest),changed=text!=raw))
    I.s.atomic(output/'derivation.json',dict(sourceOnly=True,native=False,V2Preserved=I.preserved(),support=proof,
        projectFiles=changes,bodyPatternsExact=True,expectedDynamic=1936,expectedKinematic=1264,
        originalPartitionedGLB=dict(path=(old/'SourcePartitionOnly.glb').relative_to(root).as_posix(),sha256=I.s.sha(old/'SourcePartitionOnly.glb')),
        inputSha256=I.s.sha(output/'prepared-input.json'),
        blocking='Uncompiled native bridge. Must external-stage reviewed launcher/import adapter with9/4/2guards. No automatic launch or fullcloth/ornament acceptance.'))
    print('Prepared10sourceprojectfiles, exact support/rest/body/144anchors; native uncompiled, no launch')

if __name__=='__main__':main()
