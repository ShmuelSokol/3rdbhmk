"""DRAFT source finding receipt. Native triangles/headroom/route audit unfinished.
User requested immediate wrap-up; no geometry or native operations.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'SourceAssets/mount-access/GatewayInteriorV4'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=Path('C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/cloud-unreal-v3/model-reference.json')
    manifest=ROOT/'SourceAssets/architecture-manifest.json'
    model=json.loads(source.read_text()); meshes=json.loads(manifest.read_text())['meshes']
    ids=list(range(3642,3653))
    items=[]
    for i in ids:
        e=model['elements'][i]
        matches=[m['assetName'] for m in meshes if i in m['sourceModelIndices']]
        items.append({'sourceIndex':i,'element':e,'nativeManifestAssetNames':matches})
    assert items[0]['element']['name']=='Western outer court paving'
    report={'status':'DRAFT_STOPPED_AT_USER_WRAP_UP','newGeometry':[],
        'finding':'N/S vestibules atZ425 meet Western outer court paving also atZ425; the supposed immediate125cm drop was an incomplete reading of the underlying300cm floor. Source contains five25cm transition steps per side further east, grouped into western-paving unionSM2632.',
        'sourceEvidence':items,
        'sourceFiles':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [source,manifest]],
        'remaining':['Exact union triangle extraction and native actor identification','Full width route and headroom checks','Bounded native route inputs and walking'],
        'limitations':'Source discovery only. No completed triangle/headroom validation or native walking claim. Preserve all previous frozen packages.'}
    (OUT/'draft-source-findings.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'])


if __name__=='__main__':main()
