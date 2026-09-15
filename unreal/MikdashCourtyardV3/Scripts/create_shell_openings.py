"""ShellOpeningsV1 - glass, shutter and door panels inside every OldCityFacadesV1 opening frame.

AUTHORED_OFFLINE_SOURCE: never imports `unreal`, never touches Content/ or a map, never rewrites the
shipped OldCityFacadesV1 outputs. Writes four unit OBJs, an instance plan and a manifest under
SourceAssets/context-review/ShellOpeningsV1/. Scripts/release_shell_openings.py is the guarded
native importer/placer.

WHY (measured, 11 Sep 2026)
---------------------------
98 of the 110 buildings a visitor sees within 300 m of the Kotel plaza carry OldCityFacadesV1 shells
(Scripts/measure_city_visibility.py). Every "window" and "door" in those shells is a picture-frame
solid standing proud of the wall, and NOTHING is cut: create_oldcity_facades.opening_solid says so
("the hole reads as a recess"). What shows inside each frame is the original extruded box wall, so
at walking height 62,306 openings read as blind stone panels (frame cfbefore-cp21c-K1, cropped).
This puts one flat panel behind each frame, 2 cm off the box wall, so every opening gets a 24 cm
reveal onto dark glass, a painted shutter or a door leaf.

HOW THE OPENINGS ARE RECOVERED - AND PROVED
-------------------------------------------
The shipped shells are regenerated, not re-imagined: create_oldcity_facades.generate() is re-run
with its output paths pointed at a scratch folder and three functions wrapped:
  * opening_solid        records every opening's WallFrame and profile, then builds it as before;
  * build_building_detail records each building's centroid (for the precinct zone rule);
  * write_obj            assigns everything recorded since the last call to that OBJ's actor.
The regeneration is deterministic (js_hash seeds; infill uses random.Random seeded per cell), and
this module PROVES it matched the frozen generation before it writes anything: every regenerated
OBJ's triangle count, vertex count and bounds must equal the frozen facades-manifest.json entry,
and the window / arched / door totals must equal its detail.counts. (OBJ bytes cannot match: the
header carries a generation timestamp.)

ZONES
-----
The precinct hides whole shell actors per 100 m cell under policy hide_if_any_inside (precinct-
Candidate48.json: 41 of 102 facade actors, 29 of 88 infill actors). The rule is re-applied to the
recorded centroids and MUST reproduce exactly those counts, or this module refuses. Panels behind a
hidden actor go in the precinct zone and carry the tag CityDetailZone_Precinct, which is already in
AMikdashEnclosure::HideWhileWallStandsTags (MikdashEnclosure.cpp:242); the rest carry
CityDetailZone_Kept. BuildingIdentityLabel and the explicit hide list are not touched.

SOURCED VERSUS AUTHORED
-----------------------
Positions are exactly the shipped frames'. The glass / shutter / door appearance is AUTHORED in the
style of the Old City: deep-set openings with dark glass or painted wooden shutters and doors. It
is not a survey of any building.

INTERPRETER: run with UE's bundled Python 3.11 (Engine/Binaries/ThirdParty/Python3/Win64/python.exe),
the one the frozen generation used. The system 32-bit Python 3.8 flips borderline js_hash arch
decisions (sin() differs in the last bit at large arguments): measured, 4+ OBJs off by +-16
triangles, i.e. one window changing between rectangular (32 tris) and arched (48 tris).

Usage: "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" Scripts/create_shell_openings.py
"""
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
sys.path.insert(0, str(ROOT / 'Scripts'))
import create_oldcity_facades as F                                    # noqa: E402

OUT = ROOT / 'SourceAssets' / 'context-review' / 'ShellOpeningsV1'
OBJ_OUT = OUT / 'obj'
SCRATCH = OUT / 'regen-scratch'
FROZEN_MANIFEST = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFacadesV1' / 'facades-manifest.json'
PRECINCT = ROOT / 'SourceAssets' / 'enclosure-review' / 'precinct-Candidate48.json'
MANIFEST_PATH = OUT / 'shell-openings-manifest.json'
PLAN_PATH = OUT / 'shell-openings-plan.json'

PANEL_D_CM = -4.0          # frame coordinates start on the 6 cm standoff ring: box wall is d = -6
MARGIN_CM = 4.0            # panel grows past the hole so its edge tucks behind the 14-18 cm frame
CULL_CM = 70000.0
EXPECTED_HIDDEN = {'facades': 41, 'infill': 29}

# Unit panels in local (x along the wall, z up), origin at the bottom centre, y = 0 (flat, two-sided).
def _arch(half, spring, segments=F.ARCH_SEGMENTS):
    pts = []
    for step in range(segments + 1):
        a = math.pi * step / segments
        pts.append((round(half * math.cos(a), 3), round(spring + half * math.sin(a), 3)))
    return pts


def _panel_shapes():
    ww = F.WINDOW_W - 2 * F.WINDOW_FRAME_CM          # 72 cm hole
    wh = F.WINDOW_H - 2 * F.WINDOW_FRAME_CM          # 152 cm hole
    dw = F.DOOR_W - 2 * F.DOOR_FRAME_CM              # 84 cm hole
    dh = F.DOOR_H - 2 * F.DOOR_FRAME_CM              # 194 cm hole
    wr = F.WINDOW_W / 2.0                            # outer arch radius of the frame
    dr = F.DOOR_W / 2.0
    w_spring = (F.WINDOW_H - wr) - F.WINDOW_FRAME_CM + MARGIN_CM   # above the panel bottom
    d_spring = (F.DOOR_H - dr) - F.DOOR_FRAME_CM + MARGIN_CM
    hw, hd = ww / 2.0 + MARGIN_CM, dw / 2.0 + MARGIN_CM
    return {
        'WinRect': [(-hw, 0.0), (hw, 0.0), (hw, wh + 2 * MARGIN_CM), (-hw, wh + 2 * MARGIN_CM)],
        'WinArch': [(-hw, 0.0), (hw, 0.0)] + _arch(hw, w_spring),
        'DoorRect': [(-hd, 0.0), (hd, 0.0), (hd, dh + 2 * MARGIN_CM), (-hd, dh + 2 * MARGIN_CM)],
        'DoorArch': [(-hd, 0.0), (hd, 0.0)] + _arch(hd, d_spring),
    }


def _panel_solid(loop_xz):
    solid = F.Solid()
    idx = [solid.add((x, 0.0, z)) for x, z in loop_xz]
    solid.fan(idx)
    return solid


def _arch_survives(s0, s1, z0, z1, width):
    """Same fallback test as create_oldcity_facades.frame_profile_arch."""
    radius = (s1 - s0) / 2.0
    spring = z1 - radius
    return not (spring <= z0 + width * 2.0 or radius <= width * 1.6)


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def regenerate():
    """Re-run the frozen generation into SCRATCH, recording openings and centroids per actor."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    F.OUT = SCRATCH
    F.OBJ_DIR = SCRATCH / 'obj'
    F.MANIFEST_PATH = SCRATCH / 'facades-manifest.regen.json'
    F.PREVIEW_PATH = SCRATCH / 'preview.regen.png'
    if F.MANIFEST_PATH.exists():
        F.MANIFEST_PATH.unlink()

    pending_openings, pending_centres = [], []
    inside = [0]
    skipped = {'openingsOutsideABuilding': 0}
    per_object = {}
    original_opening = F.opening_solid
    original_detail = F.build_building_detail
    original_write = F.write_obj

    def opening_solid(frame, s0, s1, z0, z1, width, d0, d1, arched):
        # generate() calls self_test() first, which builds one test opening before any building:
        # record only openings built INSIDE build_building_detail, or it becomes a stray panel.
        if inside[0] <= 0:
            skipped['openingsOutsideABuilding'] += 1
            return original_opening(frame, s0, s1, z0, z1, width, d0, d1, arched)
        pending_openings.append({'o': (frame.ox, frame.oy), 'u': (frame.ux, frame.uy), 'n': (frame.nx, frame.ny),
                                 's0': s0, 's1': s1, 'z0': z0, 'z1': z1, 'width': width, 'arched': bool(arched)})
        return original_opening(frame, s0, s1, z0, z1, width, d0, d1, arched)

    def build_building_detail(record, neighbours, street_index, pitch_cm):
        pending_centres.append(tuple(record['centreCm']))
        inside[0] += 1
        try:
            return original_detail(record, neighbours, street_index, pitch_cm)
        finally:
            inside[0] -= 1

    def write_obj(path, object_name, solids, provenance_lines):
        info = original_write(path, object_name, solids, provenance_lines)
        per_object[object_name] = {'openings': list(pending_openings), 'centres': list(pending_centres),
                                   'info': {k: info.get(k) for k in ('triangles', 'vertices', 'boundsCm', 'bounds', 'file')}}
        del pending_openings[:]
        del pending_centres[:]
        return info

    F.opening_solid, F.build_building_detail, F.write_obj = opening_solid, build_building_detail, write_obj
    try:
        F.generate(force=True, preview=False)
    finally:
        F.opening_solid, F.build_building_detail, F.write_obj = original_opening, original_detail, original_write
    if pending_openings:
        raise RuntimeError('%d openings were recorded after the last OBJ was written' % len(pending_openings))
    per_object['__skipped__'] = skipped
    return per_object, json.loads(F.MANIFEST_PATH.read_text(encoding='utf-8'))


def prove(per_object, regen_manifest):
    frozen = json.loads(FROZEN_MANIFEST.read_text(encoding='utf-8-sig'))

    def index(manifest):
        out = {}
        for batch in manifest['batches']:
            for role in ('facades', 'infill'):
                info = batch.get(role)
                if info:
                    name = Path(info.get('file') or info.get('obj') or '').stem or (
                        ('SM_OldCityFacades_' if role == 'facades' else 'SM_OldCityInfill_') + batch['name'])
                    out[name] = info
        return out

    fz, rg = index(frozen), index(regen_manifest)
    problems = []
    if set(fz) != set(rg):
        problems.append('object sets differ: frozen-only %s regen-only %s'
                        % (sorted(set(fz) - set(rg))[:5], sorted(set(rg) - set(fz))[:5]))
    compared = 0
    for name in sorted(set(fz) & set(rg)):
        a, b = fz[name], rg[name]
        for key in ('triangles', 'vertices'):
            if a.get(key) != b.get(key):
                problems.append('%s %s frozen %s regen %s' % (name, key, a.get(key), b.get(key)))
        ba = a.get('boundsCm') or a.get('bounds')
        bb = b.get('boundsCm') or b.get('bounds')
        if json.dumps(ba, sort_keys=True) != json.dumps(bb, sort_keys=True):
            problems.append('%s bounds differ' % name)
        compared += 1
    # The frozen detail.counts adds doors ONLY in the facade loop (the infill loop never counts its
    # wing doors), so doors are compared on facade objects and infill doors are reported separately.
    counts = {'windows': 0, 'arched': 0, 'doors': 0}
    infill_doors = 0
    for name, obj in per_object.items():
        for o in obj['openings']:
            if abs(o['width'] - F.WINDOW_FRAME_CM) < 1e-6:
                counts['windows'] += 1
                counts['arched'] += 1 if o['arched'] else 0
            elif name.startswith('SM_OldCityFacades_'):
                counts['doors'] += 1
            else:
                infill_doors += 1
    fc = frozen['detail']['counts']
    for key in counts:
        if counts[key] != fc[key]:
            problems.append('%s recorded %d, frozen manifest %d' % (key, counts[key], fc[key]))
    if problems:
        raise RuntimeError('Regeneration does NOT reproduce the shipped shells: %s' % problems[:8])
    return {'interpreter': sys.version, 'infillDoorsNotCountedByFrozenManifest': infill_doors,
            'objectsCompared': compared, 'openingCounts': counts, 'frozenDetailCounts': {k: fc[k] for k in counts},
            'rule': 'per-OBJ triangles, vertices and bounds equal; window/arched/door totals equal'}


def zones(per_object):
    """Exactly the precinct's own decision: create_enclosure.hide_set, the function that wrote the 41/29
    in precinct-Candidate48.json. Facade cells hide if ANY of their OSM buildings has its AREA centroid
    inside the (inclusive) square; an infill actor follows its cell's facade decision; an infill-only
    cell is decided on its OBJ bounds centre. Re-implementing it from wing centroids gave 28 infill
    actors, not 29 - so this calls the original rather than approximating it."""
    import create_enclosure as E
    p = json.loads(PRECINCT.read_text(encoding='utf-8-sig'))
    f = p['square']['outerFacesCm']
    sq = {'west': f['xWest'], 'east': f['xEast'], 'north': f['yNorth'], 'south': f['ySouth']}
    labels = set(E.hide_set(sq, 'hide_if_any_inside')['labels'])
    hidden = {}
    counts = {'facades': 0, 'infill': 0}
    for name in per_object:
        label = 'RELEASE_' + name[len('SM_'):]
        role = 'facades' if name.startswith('SM_OldCityFacades_') else 'infill'
        hidden[name] = label in labels
        counts[role] += 1 if hidden[name] else 0
    if counts != EXPECTED_HIDDEN:
        raise RuntimeError('create_enclosure.hide_set gives hidden %s, the precinct receipt records %s' % (counts, EXPECTED_HIDDEN))
    return hidden, counts


def main():
    t0 = time.time()
    shapes = _panel_shapes()
    per_object, regen_manifest = regenerate()
    skipped = per_object.pop('__skipped__')
    proof = prove(per_object, regen_manifest)
    proof['skipped'] = skipped
    hidden, hidden_counts = zones(per_object)

    rows = {(mesh, zone): [] for mesh in shapes for zone in ('kept', 'precinct')}
    fallback = 0
    for name, obj in sorted(per_object.items()):
        zone = 'precinct' if hidden[name] else 'kept'
        for o in obj['openings']:
            door = abs(o['width'] - F.WINDOW_FRAME_CM) > 1e-6
            arched = o['arched'] and _arch_survives(o['s0'], o['s1'], o['z0'], o['z1'], o['width'])
            if o['arched'] and not arched:
                fallback += 1
            mesh = ('Door' if door else 'Win') + ('Arch' if arched else 'Rect')
            sc = (o['s0'] + o['s1']) / 2.0
            ox, oy = o['o']
            ux, uy = o['u']
            nx, ny = o['n']
            x = ox + ux * sc + nx * PANEL_D_CM
            y = oy + uy * sc + ny * PANEL_D_CM
            z = o['z0'] + o['width'] - MARGIN_CM
            yaw = math.degrees(math.atan2(uy, ux))
            rows[(mesh, zone)].append([round(x, 3), round(y, 3), round(z, 3), round(yaw, 5), 0.0, 0.0, 1.0, 1.0, 1.0])

    OBJ_OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    provenance = ['ShellOpeningsV1 %s' % stamp, 'flat two-sided panel, local x along wall, z up, origin bottom centre',
                  'AUTHORED appearance; positions are the shipped OldCityFacadesV1 frames']
    meshes = []
    for key, loop in shapes.items():
        path = OBJ_OUT / ('SM_ShellOpening_%s.obj' % key)
        info = F.write_obj(path, 'SM_ShellOpening_%s' % key, [_panel_solid(loop)], provenance)
        xs = [p[0] for p in loop]
        zs = [p[1] for p in loop]
        meshes.append({'key': key, 'file': path.name, 'assetName': 'SM_ShellOpening_%s' % key,
                       'sha256': sha256_of(path), 'triangles': len(loop) - 2, 'loopCm': loop,
                       'canonicalBoundsCm': {'min': [min(xs), 0.0, min(zs)], 'max': [max(xs), 0.0, max(zs)]},
                       'materialKey': 'door' if key.startswith('Door') else 'window'})
    groups = []
    for (mesh, zone), r in sorted(rows.items()):
        if not r:
            continue
        groups.append({'label': 'RELEASE_ShellOpenings_%s_%s' % (zone.capitalize(), mesh), 'mesh': mesh, 'zone': zone,
                       'zoneTag': 'CityDetailZone_%s' % zone.capitalize(), 'instances': len(r), 'cullDistanceCm': CULL_CM,
                       'castShadow': False, 'rows': r})
    plan = {'stamp': stamp, 'groups': groups}
    PLAN_PATH.write_text(json.dumps(plan) + '\n', encoding='utf-8')
    tri = {m['key']: m['triangles'] for m in meshes}
    manifest = {
        'status': 'AUTHORED_OFFLINE_SOURCE_NATIVE_IMPORT_PENDING', 'stamp': stamp,
        'generatorSha256': sha256_of(Path(__file__)),
        'facadesGeneratorSha256': sha256_of(ROOT / 'Scripts' / 'create_oldcity_facades.py'),
        'frozenManifestSha256': sha256_of(FROZEN_MANIFEST),
        'proof': proof,
        'zones': {'hiddenActors': hidden_counts, 'expected': EXPECTED_HIDDEN,
                  'rule': 'create_enclosure.hide_set(sq, hide_if_any_inside) labels - the function that wrote precinct-Candidate48.json'},
        'panel': {'depthFromBoxWallCm': PANEL_D_CM + F.SHELL_STANDOFF_CM, 'revealFromFrameFaceCm':
                  F.SHELL_STANDOFF_CM + F.WINDOW_PROUD_CM - PANEL_D_CM, 'marginBehindFrameCm': MARGIN_CM,
                  'archFallbacks': fallback},
        'meshes': meshes,
        'groups': [{k: v for k, v in g.items() if k != 'rows'} for g in groups],
        'totals': {'instances': sum(g['instances'] for g in groups),
                   'triangles': sum(g['instances'] * tri[g['mesh']] for g in groups),
                   'actors': len(groups), 'uniqueMeshes': len(meshes)},
        'planSha256': sha256_of(PLAN_PATH),
        'seconds': round(time.time() - t0, 1),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: manifest[k] for k in ('status', 'proof', 'zones', 'panel', 'groups', 'totals', 'seconds')}, indent=1))


if __name__ == '__main__':
    main()
