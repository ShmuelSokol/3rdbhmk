"""Generate the pinned Kotel retaining-wall buffers; no Unreal, imports, assets or map writes.

V2 (15 Sep 2026): the source is now KotelRetainingWallV2
(`Scripts/generate_kotel_retaining_wall.py` -> retaining-wall-v2.json), a dressed retaining
wall on a one-sided simplification of the deck sawtooth, instead of the V1 per-edge curtain.
Two material slots: 0 is the Old City limestone the neighbouring Jewish Quarter infill uses,
1 is the loaded plaza ashlar carried by the legacy pieces in front of the Western Wall, which
are copied unchanged from closure-study.json.

--check compares exact LF header bytes without writing. Canonical winding is kept; the native
consumer must import (A,C,B), retaining the supplied outward normals.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WALL = ROOT / 'SourceAssets/context-review/KotelViewsV1/retaining-wall-v2.json'
PLAN = ROOT / 'SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json'
OUTPUT = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Private/KotelClosureRuntimeData.h'
WALL_SHA = '6bee5323782fd7d9e9c36ef6979b664e3fd431495ca8dbe7fbdc92ce9085d8e9'
LEGACY_SHA = 'f35defeaaea9f53095bc2555250c34114c70f84e7249fae557de7cf31e8ea35f'
PLAN_SHA = 'f3483bff589169159bc99200761d90230e4726ec248226c948f0ead6dedca69c'
SOURCE_SHA = 'abc6152db1d10b80476870ac843bfde232b30ccac90733994e3ecf743579095a'
TERRAIN_SHA = 'ed26cb8d2710b4a425985fed31c095fe59c13cc1f0068454bc7d53092aa78211'
MAP_SHA = '3f986fb62e889db59b01d956d4ab63718f58366874e7e64b7ec4fd0fa62e3df1'
TERRAIN_PACKAGE = '/Game/MikdashV3/KotelPlazaCutV3/SM_JerusalemTerrain_07_08_FutureMountCut_KotelPlazaCut'
DECK_PACKAGE = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes/SM_PlazaV1_DeckTile'
LIMESTONE_PACKAGE = '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building'
# VCMeanLum of M_Context_Building is 0.38 (release_context_materials.spec.json), so a constant
# 97/255 grey colour overlay makes the wall's vertex-colour modulation exactly 1.0, i.e. the
# same tone as the neighbouring infill rather than 15% brighter.
VERTEX_COLOUR_BYTE = 97


def read_pinned(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Pinned input bytes changed: ' + str(path))
    return json.loads(raw.decode('utf-8-sig'))


def vector(value, length, name):
    if (not isinstance(value, list) or len(value) != length
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) for v in value)):
        raise ValueError('Invalid finite vector: ' + name)


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def validate(wall, plan):
    if wall['units'] != 'world centimeters' or wall['name'] != 'KotelRetainingWallV2':
        raise ValueError('Wall coordinate frame or identity changed')
    hashes = wall['sourceHashesSha256']
    expected = {
        'SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json': PLAN_SHA,
        'SourceAssets/FutureMountV1/terrain-generated/SM_JerusalemTerrain_07_08_FutureMountCut.mesh.json': SOURCE_SHA,
        'SourceAssets/context-review/KotelCutClosureV1/closure-study.json': LEGACY_SHA,
    }
    if any(hashes.get(p) != h for p, h in expected.items()):
        raise ValueError('Wall source provenance changed')
    count = len(wall['vertices'])
    faces = wall['triangles']
    if count != len(wall['normals']) or count != len(wall['uv0']) or count != 3 * len(faces):
        raise ValueError('Wall buffers are not one independent vertex per triangle corner')
    if len(wall['materialIds']) != len(faces) or set(wall['materialIds']) - {0, 1}:
        raise ValueError('Wall material ids are missing or out of range')
    if wall['legacyTriangles'] != sum(1 for m in wall['materialIds'] if m == 1):
        raise ValueError('Legacy triangle count disagrees with the material ids')
    if wall['materialIds'][:wall['legacyTriangles']] != [1] * wall['legacyTriangles']:
        raise ValueError('Legacy triangles must come first')
    # The dressed face stands inside the sawtooth, so the retained V1 curtain behind it is what
    # makes this wall occlude at least as much as the accepted V1 closure did. Losing it would
    # reopen the excavation sightlines silently, so it is a hard requirement of the data.
    if wall.get('linerTriangles', 0) <= 0:
        raise ValueError('The V1 liner behind the dressed face is missing')
    if wall['legacyTriangles'] + wall['linerTriangles'] != 841:
        raise ValueError('Legacy plus liner triangles must reproduce all 841 V1 closure triangles')
    for key, width in [('vertices', 3), ('normals', 3), ('uv0', 2)]:
        for row in wall[key]:
            vector(row, width, key)
    used = set()
    for index, tri in enumerate(faces):
        if (len(tri) != 3 or any(type(i) is not int or not 0 <= i < count for i in tri)
                or len(set(tri)) != 3):
            raise ValueError('Invalid triangle indices')
        used.update(tri)
        a, b, c = [wall['vertices'][i] for i in tri]
        area = cross([b[j]-a[j] for j in range(3)], [c[j]-a[j] for j in range(3)])
        size = math.sqrt(sum(v*v for v in area))
        if size <= 1e-8:
            raise ValueError('Degenerate wall triangle')
        for i in tri:
            normal = wall['normals'][i]
            if (abs(sum(v*v for v in normal)-1) > 1e-8
                    or sum(area[j]*normal[j] for j in range(3))/size < 1-1e-6):
                raise ValueError('Canonical winding/normal disagreement')
    if used != set(range(count)):
        raise ValueError('Unreferenced wall vertex')
    lane = wall['probeLane']
    for key in ('yCm', 'footLineXcm', 'footingFrontXcm', 'faceAtCapsuleCentreXcm', 'wallTopZcm', 'deckTopZcm'):
        if not isinstance(lane[key], (int, float)) or not math.isfinite(lane[key]):
            raise ValueError('Probe lane is incomplete: ' + key)
    if len(plan['deck']) != 959:
        raise ValueError('Deck count changed')
    for row in plan['deck']:
        for key in ('loc', 'rot', 'scale'):
            vector(row[key], 3, 'deck ' + key)
        # Source rot convention is immaterial only because all deck rotations are zero.
        # Refuse future rotated cells instead of silently reinterpreting Euler ordering.
        if row['rot'] != [0, 0, 0]:
            raise ValueError('Deck rotation changed')
        if row['scale'][2] != 1 or min(row['scale']) <= 0:
            raise ValueError('Deck scale changed')
        if row['loc'][2] not in (-984.594, -1234.594):
            raise ValueError('Deck height changed')


def number(value):
    # Binary64 round-trip, avoiding output-side coordinate quantization.
    result = format(value, '.17g')
    return result if '.' in result or 'e' in result else result + '.0'


def vec(values):
    return '{' + ','.join(number(v) for v in values) + '}'


def render(wall, plan):
    validate(wall, plan)
    # Normalize only this generator's text for provenance across Git autocrlf.
    generator_sha = hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    lane = wall['probeLane']
    strings = {
        'PlanSha256': PLAN_SHA, 'WallSha256': WALL_SHA, 'LegacyClosureSha256': LEGACY_SHA,
        'GeneratorSha256': generator_sha, 'WallGeneratorSha256': wall['generatorSha256'],
        'TerrainSha256': TERRAIN_SHA, 'SourceTerrainSha256': SOURCE_SHA, 'MapSha256': MAP_SHA,
        'ExpectedMapPackage': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
        'TerrainMeshPath': TERRAIN_PACKAGE + '.' + TERRAIN_PACKAGE.rsplit('/', 1)[1],
        'DeckMeshPath': DECK_PACKAGE + '.' + DECK_PACKAGE.rsplit('/', 1)[1],
        'LimestoneMaterialPath': LIMESTONE_PACKAGE + '.' + LIMESTONE_PACKAGE.rsplit('/', 1)[1],
        'ExpectedTerrainTag': 'KotelPlazaCutTwin',
        'ExpectedTerrainTileTag': 'SM_JerusalemTerrain_07_08',
        'ExpectedDeckTag': 'KotelPlazaV1',
    }
    lines = ['// Generated by Scripts/generate_kotel_closure_runtime.py. Do not edit.',
             '// World centimetres; native indices must be (A,C,B), normals unchanged.',
             '// Geometry source: KotelRetainingWallV2 (Scripts/generate_kotel_retaining_wall.py).',
             '// Material 0 is Old City limestone; material 1 is the loaded plaza ashlar on the',
             '// legacy pieces in front of the Western Wall, copied unchanged from V1.',
             '// GeneratorSha256 hashes LF-normalized generator text; input hashes are raw bytes.',
             '// Offline geometry provenance only: runtime/native acceptance is separate.',
             '#pragma once', 'namespace KotelClosureRuntimeData {']
    lines += ['static constexpr const char* ' + k + ' = "' + v + '";' for k, v in strings.items()]
    lines += ['struct FVec3 { double X, Y, Z; };', 'struct FVec2 { double X, Y; };',
              'struct FTriangle { int A, B, C; };',
              '// Rotation is Pitch,Yaw,Roll; pinned deck rotations are all zero.',
              'struct FDeckTransform { FVec3 Location, Rotation, Scale; };',
              'static constexpr int VertexCount = %d, TriangleCount = %d, DeckCount = %d;'
              % (len(wall['vertices']), len(wall['triangles']), len(plan['deck'])),
              'static constexpr int MaterialCount = 2, LegacyTriangleCount = %d;' % wall['legacyTriangles'],
              'static constexpr int VertexColourByte = %d;' % VERTEX_COLOUR_BYTE,
              'static constexpr double ProbeLaneYCm = %s, ProbeLaneFootXCm = %s, ProbeLaneFootingFrontXCm = %s;'
              % (number(lane['yCm']), number(lane['footLineXcm']), number(lane['footingFrontXcm'])),
              'static constexpr FDeckTransform ExpectedTerrainTransform = {{0,0,0},{0,0,0},{1,1,1}};']
    for name, key, typ in [('Vertices', 'vertices', 'FVec3'), ('Normals', 'normals', 'FVec3'), ('UVs', 'uv0', 'FVec2')]:
        lines += ['static constexpr ' + typ + ' ' + name + '[VertexCount] = {']
        lines += [vec(row) + ',' for row in wall[key]]
        lines += ['};']
    lines += ['static constexpr FTriangle Triangles[TriangleCount] = {']
    lines += ['{' + ','.join(str(i) for i in row) + '},' for row in wall['triangles']]
    lines += ['};', 'static constexpr int MaterialIds[TriangleCount] = {']
    lines += [','.join(str(m) for m in wall['materialIds'][i:i + 40]) + ',' for i in range(0, len(wall['materialIds']), 40)]
    lines += ['};', 'static constexpr FDeckTransform DeckTransforms[DeckCount] = {']
    lines += ['{' + ','.join(vec(row[k]) for k in ('loc', 'rot', 'scale')) + '},' for row in plan['deck']]
    return '\n'.join(lines + ['};', '} // namespace KotelClosureRuntimeData', '']).encode('utf-8')


def check_output(path, expected):
    if not path.is_file() or path.read_bytes() != expected:
        raise ValueError('Generated header bytes drifted; regenerate: ' + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    wall = read_pinned(WALL, WALL_SHA)
    header = render(wall, read_pinned(PLAN, PLAN_SHA))
    if args.check:
        check_output(OUTPUT, header)
    else:
        OUTPUT.write_bytes(header)
    print('PASS: %d canonical triangles (%d legacy), %d vertices, 959 deck transforms; header SHA256 %s'
          % (len(wall['triangles']), wall['legacyTriangles'], len(wall['vertices']), hashlib.sha256(header).hexdigest()))


if __name__ == '__main__':
    main()
