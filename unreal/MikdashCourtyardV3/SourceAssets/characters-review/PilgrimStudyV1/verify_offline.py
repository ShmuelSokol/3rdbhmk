"""Read-only original-source/native-adapter validation; writes only its receipt."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
spec = importlib.util.spec_from_file_location('pilgrim_author', ROOT/'Scripts/create_pilgrim_character.py')
author = importlib.util.module_from_spec(spec)
spec.loader.exec_module(author)


def read_obj(path):
    vertices=[];normals=[];uvs=[];faces=[];names=[]
    for line in path.read_text().splitlines():
        tokens=line.split()
        if not tokens:continue
        if tokens[0]=='v':vertices.append(tuple(map(float,tokens[1:])))
        elif tokens[0]=='vn':normals.append(tuple(map(float,tokens[1:])))
        elif tokens[0]=='vt':uvs.append(tuple(map(float,tokens[1:])))
        elif tokens[0]=='o':names.append(tokens[1])
        elif tokens[0]=='f':faces.append([tuple(int(s)-1 for s in field.split('/')) for field in tokens[1:]])
    assert all(math.isfinite(x) for item in vertices+normals+uvs for x in item)
    assert len(vertices)==len(normals)
    for face in faces:
        assert len(face)==3
        for v,t,n in face:assert 0<=v<len(vertices) and 0<=t<len(uvs) and 0<=n<len(normals)
        a,b,c=[uvs[t] for v,t,n in face]
        assert abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-10
    return vertices,normals,uvs,faces,names


def main():
    manifest=json.loads((FOLDER/'geometry-manifest.json').read_text())
    assert hashlib.sha256((ROOT/'Scripts/create_pilgrim_character.py').read_bytes()).hexdigest()==manifest['script_sha256']
    parts=author.assembly();author.check(parts)
    originals=read_obj(FOLDER/'PilgrimStudyV1-editable.obj')
    assert len(originals[3])==manifest['triangles']
    assert originals[4]==[p['name'] for p in parts]
    native_checks=[]
    for item in manifest['native_files']:
        path=FOLDER/item['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        v,n,uv,f,names=read_obj(path)
        selected=[p for p in parts if p['material']==item['material']]
        expected=[(x,-y,z) for p in selected for x,y,z in p['vertices']]
        assert len(v)==len(expected) and len(f)==item['triangles']
        assert max(abs(a[k]-b[k]) for a,b in zip(v,expected) for k in range(3))<1e-6
        expected_faces=[];offset=0
        for p in selected:
            expected_faces.extend([(offset+a,offset+c,offset+b) for a,b,c in p['faces']]);offset+=len(p['vertices'])
        assert [tuple(k[0] for k in face) for face in f]==expected_faces
        assert max(abs(math.sqrt(sum(x*x for x in normal))-1) for normal in n)<1e-6
        native_checks.append({'file':path.name,'triangles':len(f),'reflection_winding_verified':True,'nondegenerate_uv_charts':True})
    result={'status':'passed','native_execution':False,'components_checked':len(parts),'total_triangles':len(originals[3]),
            'checks':['finite numeric coordinates','closed component index topology','positive signed volumes','nondegenerate mesh triangles',
                      'exact adapter reflection and reversed winding','finite unit vertex normals','nondegenerate UV charts','frozen OBJ/script hashes'],
            'native_files':native_checks,'limits':['No native import/render/animation test','No self-intersection or production skinning certification']}
    (FOLDER/'offline-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
