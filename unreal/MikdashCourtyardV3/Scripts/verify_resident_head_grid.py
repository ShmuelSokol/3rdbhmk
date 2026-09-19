"""Independently compare compact head-grid GLBs with accepted and Study10 source data."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from build_resident_structured_source import accessor_rows
from measure_pilgrim_walk import read_glb,read_accessor
import create_resident_v4 as R
import measure_kohen_garment_clearance as M

ROOT=Path(__file__).resolve().parents[1]
def verify(folder):
    folder=Path(folder);report=json.loads((folder/'review.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    target=folder/report['candidate'];source=ROOT/report['source']
    assert sha(target)==report['candidateSha256'] and sha(source)==report['sourceSha256']
    doc,data=read_glb(target);original,original_data=read_glb(source)
    baseline_folder=ROOT/'SourceAssets/characters-review/ResidentStructured01'/report['variant']
    baseline_report=json.loads((baseline_folder/'review.json').read_text())
    baseline,baseline_data=read_glb(baseline_folder/baseline_report['candidate'])
    assert sha(baseline_folder/baseline_report['candidate'])==baseline_report['candidateSha256']
    for field in ('nodes','skins','materials'):assert doc[field]==original[field]==baseline[field]
    parts=R.finalize(R.assembly(R.variant('V3_Pilgrim_'+report['variant'])),R.variant('V3_Pilgrim_'+report['variant']))
    head=next(p for p in parts if p['name']=='Head');head_count=len(head['vertices'])
    results=[];metrics=[]
    for p,op,bp,proof,bproof in zip(doc['meshes'][0]['primitives'],original['meshes'][0]['primitives'],baseline['meshes'][0]['primitives'],report['primitives'],baseline_report['primitives']):
        used=proof['sourceVertexIndices'];old_used=bproof['sourceVertexIndices']
        material=original['materials'][op['material']]['name'];assert material==proof['material']==bproof['material']
        for group,ogroup in [(p['attributes'],op['attributes'])]+list(zip(p.get('targets',[]),op.get('targets',[]))):
            assert set(group)==set(ogroup)
            for name,index in group.items():
                source_rows=accessor_rows(original,original_data,ogroup[name])
                assert accessor_rows(doc,data,index)==[source_rows[i] for i in used]
        faces=np.asarray(read_accessor(doc,data,p['indices']),dtype=int).reshape(-1,3)
        original_ids=np.array(used)[faces]
        baseline_ids=np.array(old_used)[np.asarray(read_accessor(baseline,baseline_data,bp['indices']),dtype=int).reshape(-1,3)]
        if material!='RV4_Skin':assert np.array_equal(original_ids,baseline_ids)
        else:
            mask=np.all(original_ids<head_count,axis=1);old_mask=np.all(baseline_ids<head_count,axis=1)
            assert np.array_equal(original_ids[~mask],baseline_ids[~old_mask]),'Non-head skin faces changed'
            assert mask.sum()==report['headReduction']['candidateTriangles']
            vertices=np.asarray(read_accessor(original,original_data,op['attributes']['POSITION']))[:head_count]
            variants=[('rest',vertices)]
            for i,t in enumerate(op.get('targets',[])):
                if 'POSITION' in t:variants.append(('morph'+str(i),vertices+np.asarray(read_accessor(original,original_data,t['POSITION']))[:head_count]))
            for label,points in variants:
                tri=points[original_ids[mask]];distances=[]
                for start in range(0,len(points),32):
                    batch=points[start:start+32];selected=M.distance_candidates(batch,tri,np.arange(len(tri)))
                    distances.extend(M.point_tri_distance(batch,tri[selected]).tolist())
                # Exported glTF positions and morph deltas are meters, while
                # authoring and Unreal evidence use centimeters.
                distances=np.asarray(distances)*100.;assert np.isfinite(distances).all()
                metrics.append(dict(shape=label,sampledSourceVertices=len(points),maximumDistanceCm=float(distances.max()),p95DistanceCm=float(np.percentile(distances,95)),meanDistanceCm=float(distances.mean())))
        results.append(dict(material=material,retainedAttributeRows=len(used),nonHeadFacesMatchStudy10=True))
    output=folder/'verified-head-source.json';assert not output.exists()
    result=dict(status='verified-source-needs-native-visual-review',candidateSha256=sha(target),sourceSha256=sha(source),baselineSha256=sha(baseline_folder/baseline_report['candidate']),primitives=results,headDistances=metrics,scope='Source vertices to closest reduced-head triangles at rest and each individual full-strength facial morph. Not a bidirectional surface Hausdorff bound, combined morph, animation, appearance or collision acceptance.')
    output.write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder');verify(parser.parse_args().folder)
