"""Offline cut spec for the OSM "Western Wall Plaza" street ribbon that lies over the plaza.

THE DEFECT (cp26 review defect D3, the stray paving strip)
----------------------------------------------------------
`cp26-K2-kotel-upper-deck-facing-jewish-quarter.png` shows a tilted strip of paving with a
Z-shaped notch lying on the sand above the Kotel retaining face, in Modern AND in Yechezkel.
It is OSM way 26492734 ("Western Wall Plaza", highway=pedestrian) exported by the context
street pipeline as a ~145 cm road-centreline RIBBON draped on the original DEM, inside four
`SM_Jerusalem_StonePaths_*` batches. PlazaV1 already paves that same footprint properly, so
the ribbon is a duplicate: it overhangs the excavation, pokes through the deck, and the jog
in the way's own vertex list is the Z notch.

The street actors carry no state tag, which is why it survives every precinct state.

WHAT THIS WRITES
----------------
A reviewable spec listing, per street asset, the exact triangle indices whose centroid lies
inside the plaza polygon grown by BUFFER_CM. `Scripts/release_kotel_plaza_way_cut.py`
consumes it to build cut DUPLICATES in a new namespace and swap the actors, exactly as
`release_fix_kotel_occlusion.py` did for the city-wall batches in front of the Kotel.
Nothing outside those four assets is selected, and the originals are never edited.

python Scripts/generate_kotel_plaza_way_cut.py [--check]
No Unreal, no assets, no maps.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/context-review/KotelViewsV1/plaza-way-cut.json'
DESIGN = ROOT / 'SourceAssets/visual-review/mount-platform-design.json'
WORKSPACE = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace')
MESHES = WORKSPACE / 'output/architecture-review/jerusalem-meshes.json'
STREETS = WORKSPACE / 'output/cloud-unreal-v3/context-review/streets-manifest.json'
MESHES_SHA = 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb'
STREETS_SHA = 'cc9eb91e99298565db296ea52a4eef744944e3bac3014829b573e30235aea8da'
PLAZA_OSM_ID = 26492734
BUFFER_CM = 300.0
NAMESPACE = '/Game/MikdashV3/FutureMountV1/KotelApproach'
SUFFIX = '_PlazaWayCut'
# source amot: X east, Y up, Z south -> Unreal cm, identical to release_fix_kotel_occlusion.spec.json
TX, TZ = 17.509700315687695, -0.5513496449385334


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def to_unreal(p):
    return [(p[0] + TX) * 50.0, (p[2] + TZ) * 50.0, p[1] * 50.0]


def point_in_polygon(p, poly):
    inside = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x > p[0]:
                inside = not inside
    return inside


def distance_to_polygon(p, poly):
    best = float('inf')
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        best = min(best, math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy))
    return best


def build():
    for path, expected in ((MESHES, MESHES_SHA), (STREETS, STREETS_SHA)):
        actual = sha_file(path)
        if actual != expected:
            raise ValueError('Frozen source changed: %s (%s)' % (path, actual))
    design = json.loads(DESIGN.read_text(encoding='utf-8-sig'))
    entries = design.get('protected', []) + design.get('features', []) + design.get('context', [])
    plaza = None
    for group in design.values():
        if isinstance(group, list):
            for row in group:
                if isinstance(row, dict) and row.get('osmId') == PLAZA_OSM_ID and row.get('nativeXYcm'):
                    plaza = row
    if plaza is None:
        raise ValueError('Plaza way %d with nativeXYcm not found in the design file' % PLAZA_OSM_ID)
    poly = [(float(x), float(y)) for x, y in plaza['nativeXYcm']]
    if poly[0] == poly[-1]:
        poly = poly[:-1]

    meshes = json.loads(MESHES.read_text(encoding='utf-8-sig'))
    streets = json.loads(STREETS.read_text(encoding='utf-8-sig'))
    mesh = next(m for m in meshes['meshes'] if m['name'].lower().startswith('stone paths 3'))
    # Flat buffers: positions are xyz triples, indices are 3 vertex indices per triangle, and a
    # batch names its own source triangles ("Use original mesh indices[sourceTriangleIndex*3+corner]").
    positions, indices_flat = mesh['positions'], mesh['indices']

    def corner(triangle_index, k):
        v = indices_flat[triangle_index * 3 + k]
        return positions[v * 3:v * 3 + 3]

    assets = []
    for batch in streets['meshes']:
        name = batch.get('assetName')
        if not name or not name.startswith('SM_Jerusalem_StonePaths_03_Grid_'):
            continue
        indices = batch['sourceTriangleIndices']
        cut, kept, bounds = [], 0, None
        for index in indices:
            tri = [corner(index, k) for k in range(3)]
            centre = [sum(to_unreal(p)[axis] for p in tri) / 3.0 for axis in range(3)]
            inside = point_in_polygon((centre[0], centre[1]), poly) or distance_to_polygon((centre[0], centre[1]), poly) <= BUFFER_CM
            if inside:
                cut.append(index)
                for c in [to_unreal(p) for p in tri]:
                    bounds = [list(c), list(c)] if bounds is None else [
                        [min(bounds[0][a], c[a]) for a in range(3)], [max(bounds[1][a], c[a]) for a in range(3)]]
            else:
                kept += 1
        if cut:
            assets.append({'asset': '/Game/MikdashV3/JerusalemContext/Streets/' + name,
                           'duplicate': NAMESPACE + '/' + name + SUFFIX,
                           'expectedActorLabel': name, 'sourceTriangleIndices': indices[:0],
                           'cutSourceTriangleIndices': cut, 'cutTriangleCount': len(cut),
                           'keptTriangleCount': kept, 'cutBoundsUEcm': bounds})
    if not assets:
        raise ValueError('No StonePaths_03 batch carries plaza-polygon triangles')
    return {
        'status': 'offline_spec_native_application_pending',
        'purpose': 'Remove the duplicated "Western Wall Plaza" road ribbon from inside the plaza PlazaV1 paves.',
        'plazaOsmId': PLAZA_OSM_ID, 'plazaPolygonXYcm': [list(p) for p in poly], 'bufferCm': BUFFER_CM,
        'rule': 'Cut every triangle of the listed street assets whose UE centroid is inside the plaza polygon or within bufferCm of it. Everything else in those assets is kept.',
        'namespace': NAMESPACE, 'duplicateSuffix': SUFFIX,
        'sourceHashesSha256': {str(MESHES): MESHES_SHA, str(STREETS): STREETS_SHA,
                               'SourceAssets/visual-review/mount-platform-design.json': sha_file(DESIGN)},
        'assets': assets,
        'totalCutTriangles': sum(a['cutTriangleCount'] for a in assets),
        'totalKeptTriangles': sum(a['keptTriangleCount'] for a in assets),
        'generatorSha256': hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
        'limits': 'Offline selection only. Native duplication, deletion, actor swap and a rendered frame are separate.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    spec = build()
    text = json.dumps(spec, indent=1) + '\n'
    if args.check:
        if OUT.read_bytes() != text.encode('utf-8'):
            raise SystemExit('plaza-way-cut.json differs from a fresh generation')
        print('PASS: plaza-way-cut.json reproduced')
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(text.encode('utf-8'))
    print('%d assets, %d triangles cut, %d kept' % (len(spec['assets']), spec['totalCutTriangles'], spec['totalKeptTriangles']))
