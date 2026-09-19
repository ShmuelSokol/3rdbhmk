"""Fresh, offline-only correction of the covered court-channel outlet.

Preserves V1 files and route coordinates. Native import, material binding, map
integration and rendered/walking acceptance are separate required steps.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import create_water_geometry as water

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'SourceAssets/water-review/MikdashWaterV1/obj'
PINNED = {
    'CourtChannel': '192d73f7b0a496bb104994e4c6435470976257cb3bb9518c90a99c9174ac6496',
    'CourtWater': '342ddc99cac89513c58ae25f335677950cbbe548068507cb0a3c867356688003',
}


def triangle_key(points):
    # Cyclic permutation preserves winding; reflection/reversal does not.
    points = tuple(tuple(round(c, 4) for c in p) for p in points)
    return min(points, points[1:] + points[:1], points[2:] + points[:2])


def triangles(parts):
    return Counter(triangle_key([vertices[i] for i in face])
                   for _, (vertices, faces) in parts for face in faces)


def frozen_triangles(path):
    vertices, result = [], Counter()
    for line in path.read_text(encoding='ascii').splitlines():
        tokens = line.split()
        if tokens and tokens[0] == 'v':
            x, y, z = map(float, tokens[1:])
            vertices.append((x, -y, z))
        elif tokens and tokens[0] == 'f':
            indices = [int(t.split('/')[0]) - 1 for t in tokens[1:]]
            if len(indices) != 3:
                raise ValueError('Expected frozen triangulated OBJ')
            a, c, b = indices  # Reverse the documented OBJ adapter winding.
            result[triangle_key([vertices[a], vertices[b], vertices[c]])] += 1
    return result


def candidate():
    route = deepcopy(water.COURT_ROUTE)
    indices = [i for i, row in enumerate(route) if row['x'] == 3600 and row['y'] == 1050]
    if len(indices) != 1 or route[indices[0]].get('cover') is not True:
        raise ValueError('Expected exactly one covered wall outlet')
    index = indices[0]
    route[index]['cover'] = False
    for i, (before, after) in enumerate(zip(water.COURT_ROUTE, route)):
        if i == index:
            after = dict(after, cover=True)
        if before != after:
            raise ValueError('Unexpected route edit')
    old_points, old_flags, _ = water.court_path(water.COURT_ROUTE)
    new_points, new_flags, _ = water.court_path(route)
    if old_points != new_points:
        raise ValueError('Channel bed or route changed')
    changed = [i for i, pair in enumerate(zip(old_flags, new_flags)) if pair[0] != pair[1]]
    if len(changed) != 1 or new_points[changed[0]] != (3600.0, 1050.0, 442.0):
        raise ValueError('Unexpected cover interval change')
    return route


def build(output):
    if output.exists():
        raise FileExistsError('Fresh destination required; previous evidence is preserved')
    route = candidate()
    records, generated = [], []
    for suffix, builder in (
        ('CourtChannel', lambda r: water.build_court_channel(r, 'Court')[0]),
        ('CourtWater', water.build_court_water),
    ):
        source = BASE / ('SM_MikdashWaterV1_' + suffix + '.obj')
        if hashlib.sha256(source.read_bytes()).hexdigest() != PINNED[suffix]:
            raise ValueError('Frozen source hash changed: ' + suffix)
        before, after = builder(water.COURT_ROUTE), builder(route)
        old_triangles, new_triangles = triangles(before), triangles(after)
        if old_triangles != frozen_triangles(source):
            raise ValueError('Generator no longer reproduces frozen source triangles: ' + suffix)
        removed, added = old_triangles - new_triangles, new_triangles - old_triangles
        if not removed or not added:
            raise ValueError('Expected a local geometry correction')
        # Junction normals touch the adjacent segment. Nothing beyond this small
        # canonical interval may move, change winding, appear or disappear.
        for tri in list(removed) + list(added):
            if not all(3500 <= p[0] <= 3750 and 950 <= p[1] <= 1150 for p in tri):
                raise ValueError('Geometry edit escaped the outlet patch')
        for name, (vertices, faces) in after:
            if not water.closed(vertices, faces) or water.volume(vertices, faces) <= 0:
                raise ValueError('Invalid closed solid: ' + name)
        generated.append((suffix, after))
        records.append(dict(suffix=suffix, sourceSha256=PINNED[suffix],
                            baselineTriangles=sum(old_triangles.values()),
                            preservedTriangles=sum((old_triangles & new_triangles).values()),
                            removedTriangles=sum(removed.values()), addedTriangles=sum(added.values())))
    output.mkdir(parents=True)
    for record, (suffix, parts) in zip(records, generated):
        name = 'SM_CourtOutletV2_' + suffix
        path = output / (name + '.obj')
        record['candidate'] = water.write_obj(name, parts, path, [
            'OFFLINE CANDIDATE: cover ends at the wall outlet; exposed descent is open.',
            'V1 source geometry and route coordinates preserved outside the outlet patch.',
            'Native import, materials, map integration and rendered acceptance pending.',
        ])
        water.readback(path, record['candidate'])
    report = dict(status='offline-validated-native-and-visual-pending',
                  destination='/Game/MikdashV3/MaterialReview/CourtOutletV2',
                  routeChange={'point': [3600, 1050, 442], 'coverBefore': True, 'coverAfter': False},
                  selected48Transform={'scale': 0.96, 'translationCm': [-248, 0, 0]},
                  explanation='The covered run included the exposed 3600-to-3660 descent and suppressed its water surface.',
                  records=records,
                  limitations=['No native assets or maps changed', 'Walking, collision, materials and rendered flow unverified'])
    (output / 'candidate.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    print(json.dumps(build(parser.parse_args().out.resolve()), indent=2))
