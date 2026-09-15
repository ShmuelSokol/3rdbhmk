"""Generate pinned Kotel closure buffers; no Unreal, imports, assets or map writes.

--check compares exact LF header bytes without writing. Canonical winding is kept;
the native consumer must import (A,C,B), retaining the supplied cavity normals.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / 'SourceAssets/context-review/KotelCutClosureV1/closure-study.json'
PLAN = ROOT / 'SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json'
OUTPUT = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Private/KotelClosureRuntimeData.h'
CLOSURE_SHA = 'f35defeaaea9f53095bc2555250c34114c70f84e7249fae557de7cf31e8ea35f'
PLAN_SHA = 'f3483bff589169159bc99200761d90230e4726ec248226c948f0ead6dedca69c'
SOURCE_SHA = 'abc6152db1d10b80476870ac843bfde232b30ccac90733994e3ecf743579095a'
TERRAIN_SHA = 'ed26cb8d2710b4a425985fed31c095fe59c13cc1f0068454bc7d53092aa78211'
CANONICAL_GENERATOR_SHA = '24ee95e508339981e42b0dea946a32e4bc7d8cb0d1712908110172bb6ce36029'
MAP_SHA = '3f986fb62e889db59b01d956d4ab63718f58366874e7e64b7ec4fd0fa62e3df1'
TERRAIN_PACKAGE = '/Game/MikdashV3/KotelPlazaCutV3/SM_JerusalemTerrain_07_08_FutureMountCut_KotelPlazaCut'
DECK_PACKAGE = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes/SM_PlazaV1_DeckTile'


def read_pinned(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Pinned input bytes changed: ' + str(path))
    return json.loads(raw)


def vector(value, length, name):
    if (not isinstance(value, list) or len(value) != length
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) for v in value)):
        raise ValueError('Invalid finite vector: ' + name)


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def validate(closure, plan):
    if closure['units'] != 'world centimeters':
        raise ValueError('Closure coordinate frame changed')
    if (closure['exteriorAtomicEdges'] != 562 or closure['internalLevelEdgesExcluded'] != 85
            or closure['exteriorLengthWithoutSourceTerrainCm'] != 0
            or closure['westSamplesCovered'] != 7 or len(closure['pieces']) != 425):
        raise ValueError('Closure scope/coverage changed')
    hashes = closure['sourceHashesSha256']
    expected = {
        'SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json': PLAN_SHA,
        'SourceAssets/FutureMountV1/terrain-generated/SM_JerusalemTerrain_07_08_FutureMountCut.mesh.json': SOURCE_SHA,
        'Content' + TERRAIN_PACKAGE[5:] + '.uasset': TERRAIN_SHA,
    }
    if any(hashes.get(p) != h for p, h in expected.items()):
        raise ValueError('Closure source provenance changed')
    if closure['generatorSha256'] != CANONICAL_GENERATOR_SHA:
        raise ValueError('Canonical generator provenance changed')
    for key, width in [('vertices', 3), ('normals', 3), ('uv0', 2)]:
        if len(closure[key]) != 2523:
            raise ValueError('Closure buffer count changed: ' + key)
        for row in closure[key]:
            vector(row, width, key)
    if len(closure['triangles']) != 841:
        raise ValueError('Closure triangle count changed')
    used = set()
    for tri in closure['triangles']:
        if (len(tri) != 3 or any(type(i) is not int or not 0 <= i < 2523 for i in tri)
                or len(set(tri)) != 3):
            raise ValueError('Invalid triangle indices')
        used.update(tri)
        a, b, c = [closure['vertices'][i] for i in tri]
        area = cross([b[j]-a[j] for j in range(3)], [c[j]-a[j] for j in range(3)])
        size = math.sqrt(sum(v*v for v in area))
        if size <= 1e-8:
            raise ValueError('Degenerate closure triangle')
        for i in tri:
            normal = closure['normals'][i]
            if (abs(sum(v*v for v in normal)-1) > 1e-8
                    or sum(area[j]*normal[j] for j in range(3))/size < 1-1e-8):
                raise ValueError('Canonical winding/normal disagreement')
    if used != set(range(2523)):
        raise ValueError('Unreferenced closure vertex')
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


def render(closure, plan):
    validate(closure, plan)
    # Normalize only this generator's text for provenance across Git autocrlf.
    generator_sha = hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    strings = {
        'PlanSha256': PLAN_SHA, 'ClosureSha256': CLOSURE_SHA,
        'GeneratorSha256': generator_sha, 'CanonicalGeneratorSha256': CANONICAL_GENERATOR_SHA,
        'TerrainSha256': TERRAIN_SHA, 'SourceTerrainSha256': SOURCE_SHA, 'MapSha256': MAP_SHA,
        'ExpectedMapPackage': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
        'TerrainMeshPath': TERRAIN_PACKAGE + '.' + TERRAIN_PACKAGE.rsplit('/', 1)[1],
        'DeckMeshPath': DECK_PACKAGE + '.' + DECK_PACKAGE.rsplit('/', 1)[1],
        'ExpectedTerrainTag': 'KotelPlazaCutTwin',
        'ExpectedTerrainTileTag': 'SM_JerusalemTerrain_07_08',
        'ExpectedDeckTag': 'KotelPlazaV1',
    }
    lines = ['// Generated by Scripts/generate_kotel_closure_runtime.py. Do not edit.',
             '// World centimetres; native indices must be (A,C,B), normals unchanged.',
             '// GeneratorSha256 hashes LF-normalized generator text; input hashes are raw bytes.',
             '// Offline geometry provenance only: runtime/native acceptance is separate.',
             '#pragma once', 'namespace KotelClosureRuntimeData {']
    lines += ['static constexpr const char* ' + k + ' = "' + v + '";' for k, v in strings.items()]
    lines += ['struct FVec3 { double X, Y, Z; };', 'struct FVec2 { double X, Y; };',
              'struct FTriangle { int A, B, C; };',
              '// Rotation is Pitch,Yaw,Roll; pinned deck rotations are all zero.',
              'struct FDeckTransform { FVec3 Location, Rotation, Scale; };',
              'static constexpr int VertexCount = 2523, TriangleCount = 841, DeckCount = 959;',
              'static constexpr FDeckTransform ExpectedTerrainTransform = {{0,0,0},{0,0,0},{1,1,1}};']
    for name, key, typ in [('Vertices', 'vertices', 'FVec3'), ('Normals', 'normals', 'FVec3'), ('UVs', 'uv0', 'FVec2')]:
        lines += ['static constexpr ' + typ + ' ' + name + '[VertexCount] = {']
        lines += [vec(row) + ',' for row in closure[key]]
        lines += ['};']
    lines += ['static constexpr FTriangle Triangles[TriangleCount] = {']
    lines += ['{' + ','.join(str(i) for i in row) + '},' for row in closure['triangles']]
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
    header = render(read_pinned(CLOSURE, CLOSURE_SHA), read_pinned(PLAN, PLAN_SHA))
    if args.check:
        check_output(OUTPUT, header)
    else:
        OUTPUT.write_bytes(header)
    print('PASS: 841 canonical triangles, 2523 vertices, 959 deck transforms; header SHA256 ' + hashlib.sha256(header).hexdigest())


if __name__ == '__main__':
    main()
