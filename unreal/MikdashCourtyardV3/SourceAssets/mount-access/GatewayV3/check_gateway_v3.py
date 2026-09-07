"""Independent stdlib validation of generated evidence and frozen source hashes."""
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]


def main():
    audit=json.loads((OUT/'gateway-approach-audit.json').read_text())
    routes=json.loads((OUT/'native-route-inputs.json').read_text())['routes']
    assert {r['direction'] for r in audit['directions']}=={'N','S','E','W'}
    assert json.loads((OUT/'gateway-v3.mesh.json').read_text())['meshes']==[]
    for source in audit['sources']:
        assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()==source['sha256']
    checked=0
    for r in audit['directions']:
        if r['direction']=='W':
            assert r['sourceElement']['name']=='Western court wall'
            assert r['sourceElement']['size']==[6,60,324]
            continue
        steps=r['measuredSteps']
        heights=[s['boundsUEcm']['max'][2] for s in steps]
        assert heights==[25*(i+1) for i in range(12 if r['direction']=='E' else 17)]
        assert r['bottomPlatformUncoveredAreaCm2']<.01
        assert r['routeProtectedBufferOverlapCm2']<.01
        pts=next(p for p in routes if p['direction']==r['direction'])['floorWaypoints']
        assert pts[0]['floorUEcm'][2]==0
        assert pts[-1]['floorUEcm'][2]==(300 if r['direction']=='E' else 425)
        checked+=len(steps)
    result={'status':'PASS','measuredExistingRisersChecked':checked,'newMeshes':0,
            'verified':['All four directions accounted for','46 existing risers maintain source heights',
                        'Generated route levels match source decisions','Source hashes unchanged','No duplicate geometry emitted'],
            'nativeExecuted':False}
    (OUT/'independent-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
