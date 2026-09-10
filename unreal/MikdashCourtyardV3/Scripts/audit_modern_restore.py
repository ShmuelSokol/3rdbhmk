"""READ-ONLY audit: does the MODERN state actually restore present-day Jerusalem?

Two passes landed on 9 September 2026 that the precinct state machine was written before:
the precinct plaza (34,653 HISM instances on the AMikdashEnclosure actor itself) and
CityDetailV1 (91,625 HISM instances across up to 24 new actors labelled
RELEASE_CityDetail_Kept_* and RELEASE_CityDetail_Precinct_*). The CityDetail receipt records
as an open item that the precinct hide set was never taught the two new labels.

This script does not reason about that from the source. It switches the state in the editor
world and COUNTS what is visible, three times, then puts the level back and proves the .umap
came out byte-identical.

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/audit_modern_restore.py"
      -Candidate48 -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Audit-ModernRestore-01.log"

SAVES NOTHING. Refuses on a game world, the wrong project or dirty packages, hashes the
target map and every protected map before and after, and reloads the level at the end so the
transient hidden flags this audit sets are discarded rather than written.

The Kotel census counts what stands over the Western Wall Plaza polygon - OSM way 26492734,
'Western Wall Plaza', highway=pedestrian - taken from the project's own georeferenced
mount-platform-design.json, not authored here.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
RECEIPT_FOLDER = ROOT / 'SourceAssets/enclosure-review'
DESIGN = ROOT / 'SourceAssets/visual-review/mount-platform-design.json'

TARGETS = {
    'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
PROTECTED = [
    '/Game/MikdashV3/Maps/Courtyard',
    '/Game/MikdashV3/FutureMountV1/L_FutureMount',
    '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold',
    '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
    '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
]
FAMILIES = [
    ('osmBuildings', 'SM_JerusalemBuildings_'),
    ('oldCityFacades', 'RELEASE_OldCityFacades_'),
    ('oldCityInfill', 'RELEASE_OldCityInfill_'),
    ('cityDetailKept', 'RELEASE_CityDetail_Kept_'),
    ('cityDetailPrecinct', 'RELEASE_CityDetail_Precinct_'),
    ('precinctCutTwins', 'RELEASE_PrecinctCut_'),
    ('kotelPlazaCutTwins', 'RELEASE_KotelPlazaCut_'),
    ('terrain', 'SM_JerusalemTerrain_'),
    ('streets', 'SM_Jerusalem_'),
    ('enclosure', 'RELEASE_Enclosure'),
]
# The actor TAGS the precinct state machine drives, written by
# Scripts/release_precinct_terrain_cut.py (the terrain twins and the hillside they replace)
# and Scripts/release_city_detail.py (the roofscape zones). These are the strings the C++
# HideWhileWallStandsTags / HideWhileModernCityStandsTags defaults carry; this audit does not
# read that source, it switches state and counts what carries each tag.
STATE_TAGS = [
    'PrecinctCutTwin',            # expected visible in YECHEZKEL only
    'PrecinctCutOriginal',        # expected hidden in YECHEZKEL; see the 07_08 tag overlap
    'KotelPlazaCutTwin',          # expected visible in MODERN and OVERLAY only
    'KotelPlazaCutOriginal',      # overlaps PrecinctCutOriginal on one tile: hidden always
    'CityDetailZone_Precinct',    # roofscape over the hidden buildings: never in YECHEZKEL
    'CityDetailZone_Kept',        # decorates buildings that stay: visible in every state
]

PLAZA_COMPONENTS = ['PlazaDeckInstances', 'PlazaWayInstances', 'PlazaRibInstances',
                    'PlazaKerbInstances', 'PlazaChannelInstances', 'PlazaRetainingInstances',
                    'PlazaScarpInstances', 'PlazaStepInstances']
RING_COMPONENTS = ['WallInstances', 'GateInstances', 'CornerInstances', 'FoundationInstances',
                   'OverlayInstances']


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def kotel_plaza_polygon():
    """The georeferenced Western Wall Plaza. SOURCED: OSM way 26492734, carried in this
    project's own mount-platform-design.json as a `protected` entry."""
    design = json.loads(DESIGN.read_text(encoding='utf-8-sig'))
    for entry in design['protected']:
        if entry.get('osmId') == 26492734:
            return [(float(x), float(y)) for x, y in entry['nativeXYcm']], entry
    raise RuntimeError('Western Wall Plaza polygon not found in mount-platform-design.json')


def bbox_of(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _family(label):
    for name, prefix in FAMILIES:
        if label.startswith(prefix):
            return name
    return 'other'


def census(ue, actors, plaza_bbox):
    """One pass over every actor: family, hidden flag, and whether its bounds overlap the
    Western Wall Plaza footprint in plan."""
    minx, miny, maxx, maxy = plaza_bbox
    total = 0
    hidden_by_family = {}
    visible_by_family = {}
    over_plaza_visible = []
    over_plaza_hidden = []
    for actor in actors:
        if actor is None:
            continue
        total += 1
        label = str(actor.get_actor_label())
        family = _family(label)
        is_hidden = bool(actor.get_editor_property('hidden'))
        bucket = hidden_by_family if is_hidden else visible_by_family
        bucket[family] = bucket.get(family, 0) + 1
        try:
            origin, extent = actor.get_actor_bounds(False)
        except Exception:                                             # noqa: BLE001
            continue
        if extent.x <= 0.0 and extent.y <= 0.0:
            continue
        # An actor whose AABB swallows the city is not "over the plaza"; cap at 400 m so the
        # terrain tiles and the city-wide ISM actors do not drown the census.
        if extent.x > 20000.0 or extent.y > 20000.0:
            continue
        if origin.x + extent.x < minx or origin.x - extent.x > maxx:
            continue
        if origin.y + extent.y < miny or origin.y - extent.y > maxy:
            continue
        row = dict(label=label, family=family,
                   centreCm=[round(origin.x, 1), round(origin.y, 1), round(origin.z, 1)],
                   extentCm=[round(extent.x, 1), round(extent.y, 1), round(extent.z, 1)])
        if is_hidden:
            over_plaza_hidden.append(row)
        else:
            over_plaza_visible.append(row)
    return dict(totalActors=total,
                hiddenByFamily=hidden_by_family, visibleByFamily=visible_by_family,
                hiddenTotal=sum(hidden_by_family.values()),
                overPlazaVisible=len(over_plaza_visible),
                overPlazaHidden=len(over_plaza_hidden),
                overPlazaVisibleActors=sorted(over_plaza_visible, key=lambda r: r['label'])[:40],
                overPlazaHiddenActors=sorted(over_plaza_hidden, key=lambda r: r['label'])[:40])


def tag_census(ue, actors):
    """Per tag: how many actors carrying it are visible, how many hidden, and their labels.
    Counted from the live world, never from the receipt that placed them."""
    out = {}
    for tag in STATE_TAGS:
        out[tag] = dict(visible=0, hidden=0, visibleLabels=[], hiddenLabels=[])
    for actor in actors:
        if actor is None:
            continue
        try:
            tags = [str(t) for t in actor.get_editor_property('tags')]
        except Exception:                                             # noqa: BLE001
            continue
        if not tags:
            continue
        is_hidden = bool(actor.get_editor_property('hidden'))
        label = str(actor.get_actor_label())
        for tag in tags:
            entry = out.get(tag)
            if entry is None:
                continue
            if is_hidden:
                entry['hidden'] += 1
                entry['hiddenLabels'].append(label)
            else:
                entry['visible'] += 1
                entry['visibleLabels'].append(label)
    for entry in out.values():
        entry['visibleLabels'] = sorted(entry['visibleLabels'])
        entry['hiddenLabels'] = sorted(entry['hiddenLabels'])
    return out


def component_state(ue, actor, names):
    out = {}
    by_name = {}
    for component in list(actor.get_components_by_class(
            ue.HierarchicalInstancedStaticMeshComponent)):
        by_name[str(component.get_name())] = component
    for name in names:
        component = by_name.get(name)
        if component is None:
            out[name] = None
            continue
        mesh = component.get_editor_property('static_mesh')
        mesh_path = mesh.get_path_name() if mesh is not None else None
        out[name] = dict(visible=bool(component.get_editor_property('visible')),
                         instances=int(component.get_instance_count()),
                         mesh=mesh_path,
                         meshOnDisk=(disk_path(mesh_path.split('.')[0]).exists()
                                     if mesh_path else False))
    out['_componentNamesSeen'] = sorted(by_name)
    return out


def find_enclosure(ue, actors):
    found = []
    for actor in actors:
        if actor is None:
            continue
        if actor.get_class().get_name().startswith('MikdashEnclosure'):
            found.append(actor)
    if len(found) != 1:
        raise RuntimeError('Expected exactly one AMikdashEnclosure, found %d' % len(found))
    return found[0]


EXPECTED = {
    # tag: (visible in Yechezkel, visible in Modern, visible in Overlay)
    'PrecinctCutTwin':         (True,  False, False),
    'PrecinctCutOriginal':     (False, None,  None),   # 07_08 is also a Kotel original
    'KotelPlazaCutTwin':       (False, True,  True),
    'KotelPlazaCutOriginal':   (False, False, False),
    'CityDetailZone_Precinct': (False, True,  True),
    'CityDetailZone_Kept':     (True,  True,  True),
}


def acceptance(receipt):
    """Pass/fail straight off the counted states. A None in EXPECTED means the tag overlaps
    another one on at least one actor, so the per-tag total is not a clean expectation; those
    are reported with their labels rather than judged."""
    states = receipt['states']
    order = ('Yechezkel', 'Modern', 'Overlay')
    rows = {}
    ok = True
    for tag, expected in EXPECTED.items():
        counted = []
        for name in order:
            entry = states[name]['tagCensus'][tag]
            counted.append(dict(state=name, visible=entry['visible'], hidden=entry['hidden'],
                                visibleLabels=entry['visibleLabels']))
        verdict = []
        for index, want in enumerate(expected):
            total = counted[index]['visible'] + counted[index]['hidden']
            if want is None:
                verdict.append('unjudged')
            elif total == 0:
                verdict.append('NO ACTORS CARRY THIS TAG')
                ok = False
            elif want and counted[index]['hidden'] > 0:
                verdict.append('FAIL: %d hidden that should be visible' % counted[index]['hidden'])
                ok = False
            elif (not want) and counted[index]['visible'] > 0:
                verdict.append('FAIL: %d visible that should be hidden' % counted[index]['visible'])
                ok = False
            else:
                verdict.append('ok')
        rows[tag] = dict(counted=counted, expected=list(expected), verdict=verdict)
    hide = receipt.get('hideList', {})
    hide_ok = (int(hide.get('missing', -1)) == 0 and int(hide.get('duplicated', -1)) == 0)
    if not hide_ok:
        ok = False
    return dict(passed=bool(ok), tags=rows,
                hideList=dict(found=hide.get('found'), missing=hide.get('missing'),
                              duplicated=hide.get('duplicated'), ok=hide_ok),
                restoredToAsFound=(receipt.get('afterRestoreCensus', {}).get('hiddenTotal')
                                   == receipt.get('asFoundCensus', {}).get('hiddenTotal')))


def run(target_name):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    actor_sub = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never audit over a running game')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
       ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before the audit')

    target_map = TARGETS[target_name]
    map_file = disk_path(target_map, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {}
    for name in PROTECTED:
        if disk_path(name, 'umap').exists():
            protected[name] = sha256_of(disk_path(name, 'umap'))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    polygon, polygon_entry = kotel_plaza_polygon()
    plaza_bbox = bbox_of(polygon)

    RECEIPT_FOLDER.mkdir(parents=True, exist_ok=True)
    receipt_path = RECEIPT_FOLDER / ('modern-restore-audit-%s-%s.json' % (target_name, stamp))
    receipt = {
        'status': 'started',
        'readOnly': True,
        'stamp': stamp, 'target': target_name, 'map': target_map,
        'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'protectedMapSha256Before': protected,
        'scriptSha256': sha256_of(Path(__file__)),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'kotelPlazaPolygon': {
            'sourced': 'OSM way 26492734 "Western Wall Plaza", highway=pedestrian, carried in '
                       'SourceAssets/visual-review/mount-platform-design.json',
            'osmId': polygon_entry.get('osmId'), 'vertices': len(polygon),
            'bboxCm': [round(v, 1) for v in plaza_bbox],
            'designSha256': sha256_of(DESIGN)},
        'states': {}, 'errors': [],
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=1), encoding='utf-8')

    write()
    try:
        if not levels.load_level(target_map):
            raise RuntimeError('load_level failed for ' + target_map)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != target_map:
            raise RuntimeError('Loaded world is not the target map')

        all_actors = list(actor_sub.get_all_level_actors())
        enclosure = find_enclosure(ue, all_actors)
        receipt['enclosure'] = dict(
            label=str(enclosure.get_actor_label()),
            klass=enclosure.get_class().get_name(),
            hasPlazaApi=hasattr(enclosure, 'get_plaza_status'))
        if hasattr(enclosure, 'get_plaza_status'):
            receipt['enclosure']['plazaStatus'] = str(enclosure.get_plaza_status())
        receipt['asFoundCensus'] = census(ue, all_actors, plaza_bbox)
        receipt['asFoundTagCensus'] = tag_census(ue, all_actors)
        write()

        # Gather WITHOUT hiding first, so the counts below are the state machine's own and
        # not an artefact of an editor world that never ran BeginPlay.
        enclosure.measure_without_hiding()
        found, missing, duplicated = enclosure.get_hide_list_resolution()
        receipt['hideList'] = dict(
            found=int(found), missing=int(missing), duplicated=int(duplicated),
            explicitLabels=len(list(enclosure.get_editor_property('explicit_hide_labels'))),
            explicitMeshNames=len(list(enclosure.get_editor_property('explicit_hide_mesh_names'))),
            modernPrefixes=[str(s) for s in
                            enclosure.get_editor_property('modern_building_label_prefixes')],
            excludedPrefixes=[str(s) for s in
                              enclosure.get_editor_property('excluded_label_prefixes')],
            countInside=int(enclosure.count_modern_buildings_inside()),
            fingerprint=str(enclosure.get_hide_set_fingerprint()))
        if hasattr(enclosure, 'get_state_tagged_counts'):
            matched, with_wall, with_city = enclosure.get_state_tagged_counts()
            receipt['stateTagged'] = dict(
                matched=int(matched), hiddenWhileWallStands=int(with_wall),
                hiddenWhileModernCityStands=int(with_city),
                hideWhileWallStandsTags=[str(t) for t in enclosure.get_editor_property(
                    'hide_while_wall_stands_tags')],
                hideWhileModernCityStandsTags=[str(t) for t in enclosure.get_editor_property(
                    'hide_while_modern_city_stands_tags')])
        else:
            receipt['stateTagged'] = dict(
                matched=0, note='This build predates the tagged-state-actor hook')
        write()

        # SetPrecinctStateOver returns without applying anything when asked for the state it
        # is already in. The actor is saved in YECHEZKEL, so an unprimed sequence counts its
        # first entry off the level as it sits on disk rather than off an apply - which is
        # how an earlier run of this audit reported 0 hidden buildings in YECHEZKEL and 307
        # in 'Yechezkel_again'. Prime with a state that is NOT the first one counted, and
        # keep every consecutive pair in the sequence different for the same reason.
        primed_from = str(enclosure.get_precinct_state())
        prime = (ue.MikdashPrecinctState.OVERLAY if 'MODERN' in primed_from.upper()
                 else ue.MikdashPrecinctState.MODERN)
        enclosure.set_precinct_state_over(prime, 0.0)
        receipt['primedFrom'] = primed_from
        receipt['primedWith'] = str(enclosure.get_precinct_state())

        sequence = (('Yechezkel', ue.MikdashPrecinctState.YECHEZKEL),
                    ('Modern', ue.MikdashPrecinctState.MODERN),
                    ('Overlay', ue.MikdashPrecinctState.OVERLAY),
                    ('Yechezkel_again', ue.MikdashPrecinctState.YECHEZKEL))
        for state_name, state_value in sequence:
            enclosure.set_precinct_state_over(state_value, 0.0)
            entry = census(ue, all_actors, plaza_bbox)
            entry['reportedState'] = str(enclosure.get_precinct_state())
            entry['plazaComponents'] = component_state(ue, enclosure, PLAZA_COMPONENTS)
            entry['ringComponents'] = component_state(ue, enclosure, RING_COMPONENTS)
            entry['tagCensus'] = tag_census(ue, all_actors)
            receipt['states'][state_name] = entry
            write()

        # Leave nothing hidden, then throw the whole transient world away.
        enclosure.restore_all_modern_buildings()
        receipt['afterRestoreCensus'] = census(ue, all_actors, plaza_bbox)
        write()
        if not levels.load_level(target_map):
            raise RuntimeError('Reload failed')
        receipt['reloadedWithoutSaving'] = True
        receipt['acceptance'] = acceptance(receipt)
        receipt['status'] = 'audited_read_only'
    except Exception as error:                                        # noqa: BLE001
        receipt['errors'].append(repr(error))
        receipt['status'] = 'FAILED'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        unchanged = True
        for name, value in protected.items():
            if sha256_of(disk_path(name, 'umap')) != value:
                unchanged = False
        receipt['protectedMapsUnchanged'] = unchanged
        if receipt['mapBytesChanged']:
            receipt['errors'].append('READ-ONLY AUDIT CHANGED THE MAP - investigate')
        receipt['dirtyMapPackagesAtEnd'] = [
            str(p.get_name()) for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        write()
    return receipt


def _main():
    import unreal as ue
    line = ' %s ' % ue.SystemLibrary.get_command_line().lower()
    chosen = []
    for name in TARGETS:
        if (' -%s ' % name.lower()) in line:
            chosen.append(name)
    if len(chosen) != 1:
        raise RuntimeError('Choose exactly one of -Candidate48 / -Main50')
    receipt = run(chosen[0])
    ue.log('AUDIT-MODERN-RESTORE status=%s pass=%s' % (
        receipt['status'], receipt.get('acceptance', {}).get('passed')))


if __name__ == '__main__':
    _main()
