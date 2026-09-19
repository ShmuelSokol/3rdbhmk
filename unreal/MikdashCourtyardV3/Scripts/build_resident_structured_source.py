"""Export isolated grid-reduced residents from accepted shoulder-repaired GLBs.

Every retained attribute/morph row is copied as raw bytes from the accepted
source. Tunic/Mantle face indices change; optional head-stride2 also reduces the
head grid. Other parts keep their faces and vertices. Original buffers remain as provenance; imported mesh vertices are
compacted through new accessors. This is not native or visual acceptance.
"""
import argparse
import copy
import hashlib
import json
import struct
import tempfile
from pathlib import Path

import numpy as np
import create_resident_v4 as R
import create_pilgrim_v3 as C
from measure_pilgrim_walk import read_glb, read_accessor, COMPONENT, COUNT
from measure_resident_structured_reduction import reduce_parts

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def accessor_rows(doc, binary, index):
    a = doc['accessors'][index]
    assert 'sparse' not in a
    view = doc['bufferViews'][a['bufferView']]
    assert view['buffer'] == 0
    size = COMPONENT[a['componentType']][1] * COUNT[a['type']]
    stride = view.get('byteStride', size)
    base = view.get('byteOffset', 0) + a.get('byteOffset', 0)
    return [binary[base+i*stride:base+i*stride+size] for i in range(a['count'])]


def write_glb(path, doc, binary):
    doc['buffers'] = [{'byteLength': len(binary)}]
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary = bytes(binary) + b'\0' * (-len(binary) % 4)
    with path.open('xb') as handle:
        handle.write(struct.pack('<III', 0x46546c67, 2, 28+len(encoded)+len(binary)))
        handle.write(struct.pack('<II', len(encoded), 0x4e4f534a)+encoded)
        handle.write(struct.pack('<II', len(binary), 0x004e4942)+binary)


def build(short, folder, head_stride=1):
    folder.mkdir(parents=True, exist_ok=True)
    assert not any(folder.iterdir()), 'Fresh empty output directory required'
    variant = R.variant('V3_Pilgrim_'+short)
    raw = R.assembly(variant)
    reduced, _, counts = reduce_parts(raw, variant, 2, 2)
    if head_stride!=1:
        from reduce_resident_head_grid import reduce_head
        replacement,head_counts=reduce_head(next(p for p in raw if p['name']=='Head'),variant,head_stride)
        reduced=[replacement if p['name']=='Head' else p for p in reduced]
        counts['Head']=head_counts
    parts = R.finalize(raw, variant)
    source = ROOT/'SourceAssets/characters-review/ResidentShoulderAdopt01'/('SK_RV4_'+short+'.glb')
    original = ROOT/'SourceAssets/characters-review/ResidentV4/meshes'/source.name
    original_doc, original_bin = read_glb(original)
    doc, binary = read_glb(source)
    bones = C.skeleton()
    with tempfile.TemporaryDirectory(prefix='resident-layout-') as temp:
        baseline = Path(temp)/'baseline.glb'
        R.export_glb(baseline, parts, bones, {b['name']: i for i, b in enumerate(bones)}, variant)
        generated_doc, generated_bin = read_glb(baseline)
    assert generated_doc == original_doc, 'Original generator layout changed'
    normal_indices = {p['attributes']['NORMAL'] for p in original_doc['meshes'][0]['primitives']}
    normal_indices.update(t['NORMAL'] for p in original_doc['meshes'][0]['primitives']
                          for t in p.get('targets', []) if 'NORMAL' in t)
    for i in range(len(original_doc['accessors'])):
        a, b = read_accessor(original_doc, original_bin, i), read_accessor(generated_doc, generated_bin, i)
        assert np.allclose(a, b, rtol=0, atol=1e-12) if i in normal_indices else a == b, i
    assert doc['meshes'] == original_doc['meshes']
    assert doc['skins'] == original_doc['skins'] and doc['nodes'] == original_doc['nodes']
    assert doc['materials'] == original_doc['materials']
    outdoc, output = copy.deepcopy(doc), bytearray(binary)

    def append(data, accessor, target):
        output.extend(b'\0' * (-len(output) % 4))
        offset = len(output)
        output.extend(data)
        view = {'buffer': 0, 'byteOffset': offset, 'byteLength': len(data), 'target': target}
        accessor = copy.deepcopy(accessor)
        accessor.pop('byteOffset', None)
        accessor['bufferView'] = len(outdoc['bufferViews'])
        outdoc['bufferViews'].append(view)
        outdoc['accessors'].append(accessor)
        return len(outdoc['accessors'])-1

    checks, totals = [], {'sourceTriangles': 0, 'candidateTriangles': 0}
    for old, new in zip(doc['meshes'][0]['primitives'], outdoc['meshes'][0]['primitives']):
        material = doc['materials'][old['material']]['name']
        members = [p for p in parts if p['material'] == material]
        offset, original_indices, candidate_indices = 0, [], []
        for p in members:
            original_indices.extend(offset+i for face in p['faces'] for i in face)
            if p['name'] in counts:
                candidate = R.split_seams2(next(q for q in reduced if q['name'] == p['name']))
                lookup = {(tuple(v), tuple(uv)): i for i, (v, uv) in enumerate(zip(p['vertices'], p['uv']))}
                assert len(lookup) == len(p['vertices']), 'Ambiguous garment vertex mapping'
                mapping = [lookup[(tuple(v), tuple(uv))] for v, uv in zip(candidate['vertices'], candidate['uv'])]
                candidate_indices.extend(offset+mapping[i] for face in candidate['faces'] for i in face)
            else:
                candidate_indices.extend(offset+i for face in p['faces'] for i in face)
            offset += len(p['vertices'])
        assert original_indices == read_accessor(doc, binary, old['indices'])
        assert offset == doc['accessors'][old['attributes']['POSITION']]['count']
        used = sorted(set(candidate_indices))
        remap = {old_index: i for i, old_index in enumerate(used)}
        indices = [remap[i] for i in candidate_indices]
        new['indices'] = append(struct.pack('<'+'I'*len(indices), *indices),
                                {'componentType': 5125, 'count': len(indices), 'type': 'SCALAR'}, 34963)
        groups = [(old['attributes'], new['attributes'])] + list(zip(old.get('targets', []), new.get('targets', [])))
        for old_group, new_group in groups:
            for name, index in old_group.items():
                source_rows = accessor_rows(doc, binary, index)
                assert len(source_rows) == offset
                selected = [source_rows[i] for i in used]
                accessor = copy.deepcopy(doc['accessors'][index])
                accessor['count'] = len(used)
                if 'min' in accessor or 'max' in accessor:
                    values = np.asarray(read_accessor(doc, binary, index))[used]
                    accessor['min'], accessor['max'] = values.min(axis=0).tolist(), values.max(axis=0).tolist()
                new_index = append(b''.join(selected), accessor, 34962)
                new_group[name] = new_index
                assert accessor_rows(outdoc, output, new_index) == selected
        checks.append(dict(material=material, sourceVertices=offset, candidateVertices=len(used),
                           sourceTriangles=len(original_indices)//3, candidateTriangles=len(indices)//3,
                           sourceVertexIndices=used))
        totals['sourceTriangles'] += len(original_indices)//3
        totals['candidateTriangles'] += len(indices)//3
    target = folder/('SK_RV4_'+short+('_HeadGrid' if head_stride!=1 else '_Structured')+'.glb')
    write_glb(target, outdoc, output)
    loaded, loaded_bin = read_glb(target)
    assert loaded == outdoc and loaded_bin[:len(output)] == output
    assert totals['sourceTriangles'] - totals['candidateTriangles'] == sum(
        v['sourceTriangles']-v['candidateTriangles'] for v in counts.values())
    report = dict(status='source-export-needs-native-review', variant=short,
                  source=source.relative_to(ROOT).as_posix(), sourceSha256=sha(source),
                  candidate=target.name, candidateSha256=sha(target), totals=totals,
                  garmentCounts={k:v for k,v in counts.items() if k!='Head'}, primitives=checks,
                  preserved='Every retained attribute/morph row byte-for-byte from accepted shoulder source; all faces outside the explicitly reduced parts, skeleton and material slots.',
                  scope='Index-only source-grid reduction; compact referenced vertex accessors. Original binary payload retained. No native, animation or visual acceptance.')
    if head_stride!=1:report['headReduction']=counts['Head']
    (folder/'review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(short, totals, target, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['Man_Elder', 'Woman_Young'], required=True)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--head-stride',type=int,choices=(1,2),default=1)
    args = parser.parse_args()
    build(args.variant, args.folder,args.head_stride)
