"""Offline source-grid reduction experiment; never imports or overwrites native assets.

Only garment triangle indices change. Retained vertices keep their authored
positions and skin anchors. Dense original tunic vertices remain the mantle
probes, so reducing target geometry cannot quietly reduce probe coverage.
This uses the existing generator clearance rule, not native/VAT acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import create_pilgrim_v3 as C
import create_resident_v4 as R
import create_resident_v4_body as B
import measure_kohen_garment_clearance as M


def retained_rows(zs, stride):
    # Keep hem shaping and all waist/shoulder rows; decimate middle rows only.
    return [i for i, z in enumerate(zs)
            if i < 3 or i == len(zs) - 1 or z >= 95 or i % stride == 0]


def reduce_parts(parts, variant, row_stride, column_stride):
    """Return copied part dictionaries with source-index triangles and hem indices."""
    by_name = {p['name']: p for p in parts}
    tun = B.Tunic(variant)
    rows = retained_rows(tun.zs, row_stride)
    cols = list(range(0, B.TUNIC_SEGMENTS, column_stride))
    assert B.TUNIC_SEGMENTS % column_stride == 0 and len(cols) >= 8
    mapping = [r * B.TUNIC_SEGMENTS + c for r in rows for c in cols]
    _, faces = C.loft([(0, 1, 1, 0, 0)] * len(rows), len(cols), cap=False)
    reduced = dict(by_name['Tunic'])
    reduced['faces'] = [tuple(mapping[i] for i in f) for f in faces]
    replacements = {'Tunic': reduced}
    hems = {'Tunic': np.array(cols, dtype=np.int32)}
    selections = {'Tunic': {'rows': rows, 'columns': cols}}
    if 'Mantle' in by_name:
        _, _, _, _, grid, zs, width = B.mantle(variant, tun)
        mr = retained_rows(zs, row_stride)
        mc = sorted(set(range(0, width, column_stride)) | {width - 1})
        selected_grid = [[grid[r][c] for c in mc] for r in mr]
        _, panel_faces = C.cloth_panel(selected_grid, .36)
        _, original_faces = C.cloth_panel(grid, .36)
        part = by_name['Mantle']
        flip = tuple(part['faces'][0]) != tuple(original_faces[0])
        expected = [(a, c, b) for a, b, c in original_faces] if flip else original_faces
        assert part['faces'] == expected, 'Unexpected mantle topology'
        front = [r * width + c for r in mr for c in mc]
        mapping = front + [i + len(grid) * width for i in front]
        faces = [(a, c, b) for a, b, c in panel_faces] if flip else panel_faces
        reduced = dict(part)
        reduced['faces'] = [tuple(mapping[i] for i in f) for f in faces]
        replacements['Mantle'] = reduced
        hems['Mantle'] = np.array(mc, dtype=np.int32)
        selections['Mantle'] = {'rows': mr, 'columns': mc}
    result = [replacements.get(p['name'], p) for p in parts]
    counts = {}
    for p in result:
        if p['name'] not in replacements:
            continue
        original = by_name[p['name']]
        assert p['vertices'] is original['vertices']
        if 'anchors' in p:
            assert p['anchors'] is original['anchors']
        faces = np.asarray(p['faces'], dtype=np.int32)
        vertices = np.asarray(p['vertices'])
        triangle = vertices[faces]
        areas = np.linalg.norm(np.cross(triangle[:, 1] - triangle[:, 0],
                                       triangle[:, 2] - triangle[:, 0]), axis=1)
        assert faces.min() >= 0 and faces.max() < len(vertices)
        assert np.all(areas > 1e-10), p['name']
        counts[p['name']] = {
            'sourceTriangles': len(original['faces']), 'candidateTriangles': len(faces),
            'retainedVertices': len(np.unique(faces)), 'sourceVertices': len(vertices),
            'sourceIndicesSha256': hashlib.sha256(faces.astype('<i4').tobytes()).hexdigest(),
            **selections[p['name']],
        }
    return result, hems, counts


def measure(short, row_stride, column_stride, rate_scale):
    which = 'v4:V3_Pilgrim_' + short
    original_body, original_loft = M.body_parts, M.loft_triangles
    data = original_body(which)
    bones, index, parts, influence, robe, segments, outer, outer_segments = data
    candidate, hems, counts = reduce_parts(parts, R.variant(which[3:]), row_stride, column_stride)

    def body(_):
        return bones, index, candidate, influence, robe, segments, outer, outer_segments

    def loft(part, width):
        faces, wall, hem, nring = original_loft(part, width)
        return faces, wall, hems.get(part['name'], hem), nring

    try:
        M.body_parts, M.loft_triangles = body, loft
        result = M.run(which, rate_scale, clips=['walk'], keep_frames=True)
    finally:
        M.body_parts, M.loft_triangles = original_body, original_loft
    result.update(rowStride=row_stride, columnStride=column_stride, garmentCounts=counts)
    result['meilTestSampling'] = (
        'Dense source tunic vertices, every second original angular segment; '
        'rest z above source mantle hem +1.5 cm and below min(140, mantle max z -3); '
        'exclude front opening +10 degrees. Target garment faces/hem use retained grid indices.')
    result['scope'] = ('Offline generator indices/weights only. Accepted shoulder repairs and native '
                       'assets are not modified or assessed. All original leg and tunic probes '
                       'remain; retained source vertices are not an exported compact mesh. '
                       'No visual, continuous-time, VAT, whole-body or performance acceptance.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['Man_Elder', 'Woman_Young'], required=True)
    parser.add_argument('--row-stride', type=int, choices=[1, 2, 3], default=1)
    parser.add_argument('--column-stride', type=int, choices=[1, 2, 4], default=2)
    parser.add_argument('--rate-scale', type=float, default=1.0)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not np.isfinite(args.rate_scale) or args.rate_scale <= 0:
        parser.error('--rate-scale must be positive and finite')
    if args.out.exists():
        parser.error('Refusing to overwrite existing evidence')
    result = measure(args.variant, args.row_stride, args.column_stride, args.rate_scale)
    result['scriptSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['sourceScriptSha256'] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(R.__file__), Path(B.__file__), Path(C.__file__), Path(M.__file__)]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(result, indent=2) + '\n')
    print('Evidence:', args.out, flush=True)


if __name__ == '__main__':
    main()
