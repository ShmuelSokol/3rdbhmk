"""READ-ONLY. Prove, on both maps in one editor session, where everything actually stands.

WHY
---
Three release passes were structurally Main50-only, and the map that ships is Candidate48.
Porting them is not a matter of changing a string: Candidate48 holds the same architecture under
a 0.96 similarity about the world origin plus the Aron re-pivot (-248, 0, 0), while the
FutureMountV1 terrain and the metric city were NOT rescaled and stand at identical coordinates
on both maps. So a port is only correct if it moves what moved and leaves alone what did not,
and that is a claim about the levels, not about a spec file.

This pass makes both halves of that claim numeric, in one editor session, without touching
anything:

  1. ARCHITECTURE. Every actor whose mesh resolves to SourceAssets/architecture-manifest.json is
     compared with its manifest AABB carried through the target's declared placement, and the
     placement is independently SOLVED back out of those same bounds. Main50 must come back as
     the identity; Candidate48 must come back as 0.96 and (-248, 0, 0).
  2. GROUND. Every SM_JerusalemTerrain_* actor's world AABB is recorded on both maps and
     compared tile by tile. The base tiles must agree to the last centimetre -- that is what
     licenses vegetation to be placed at IDENTICAL coordinates on the candidate. The eleven
     *_PrecinctCut twins legitimately differ, because the precinct square they are cut to is
     itself 4 per cent smaller on the candidate, and they are reported separately rather than
     averaged into the result.

It also inventories the three passes on both maps, so the gap is a number rather than a memory:
gate security actors, wear decals and the wear manager, vegetation components and instances.

The Main50 ground fingerprint is written to SourceAssets/scale-review/ground-fingerprint-Main50.json
and release_vegetation.py requires it before it will place a single instance on the candidate.

  "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
      "C:/Mikdash/Working-5.8/MikdashCourtyardV3/MikdashCourtyardV3.uproject"
      -run=pythonscript -unattended -nullrhi
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/candidate_placement_proof.py"
      -abslog="C:/Mikdash/Working-5.8/Placement-Proof.log"

Nothing here saves, spawns or destroys. Both .umap hashes are recorded before and after and the
run fails if either moved.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
sys.path.insert(0, str(ROOT / 'Scripts'))
import map_targets as mt  # noqa: E402

OUT = ROOT / 'SourceAssets' / 'scale-review'
GROUND_REFERENCE = OUT / 'ground-fingerprint-Main50.json'

# What the three ported passes leave in a level, by label prefix.
INVENTORY = {
    'gateSecurity': 'RELEASE_GateSecurity_',
    'surfaceWearDecals': 'SURFACEWEAR_Wear_',
    'vegetation': 'RELEASE_Vegetation_',
}
CUT_TWIN_TOKENS = ('PrecinctCut', 'KotelPlazaCut', 'FutureMountCut')


def _bounds(ue, actor):
    origin, extent = actor.get_actor_bounds(False)
    return {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
            'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}


def survey(ue, target_key):
    """Load one map and read it. No mutation of any kind."""
    config = mt.target_config(target_key)
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors_sub = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active')
    if not levels.load_level(config['map']):
        raise RuntimeError('load_level failed for ' + config['map'])
    world = editor.get_editor_world()
    if world.get_outermost().get_name() != config['map']:
        raise RuntimeError('Loaded world is not ' + config['map'])

    rows = []
    for actor in actors_sub.get_all_level_actors():
        if actor is None:
            continue
        meshes = []
        instances = 0
        for component in actor.get_components_by_class(ue.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            meshes.append(mesh.get_path_name() if mesh else None)
            if isinstance(component, ue.InstancedStaticMeshComponent):
                instances += int(component.get_instance_count())
        rows.append({'label': actor.get_actor_label(), 'name': actor.get_name(),
                     'meshes': meshes, 'instances': instances, 'bounds': _bounds(ue, actor)})

    scale, translation = mt.placement_of(target_key)
    by_key, manifest = mt.architecture_index(ROOT)
    proof = mt.prove_placement(rows, by_key, scale, translation)
    proof['manifestMeshes'] = len(manifest['meshes'])

    fingerprint = mt.terrain_fingerprint(rows)
    base = {k: v for k, v in fingerprint.items() if not any(t in k for t in CUT_TWIN_TOKENS)}
    twins = {k: v for k, v in fingerprint.items() if any(t in k for t in CUT_TWIN_TOKENS)}

    inventory = {}
    for name, prefix in INVENTORY.items():
        matched = [r for r in rows if r['label'].startswith(prefix)]
        inventory[name] = {'actors': len(matched),
                           'instances': sum(r['instances'] for r in matched),
                           'sampleLabels': sorted(r['label'] for r in matched)[:4]}
    inventory['surfaceWearManager'] = {
        'actors': sum(1 for r in rows if r['label'] == 'SURFACEWEAR_Manager'), 'instances': 0,
        'sampleLabels': []}

    return {'target': config['key'], 'map': config['map'],
            'mapSha256': mt.sha256_of(mt.disk_path(config['map'], 'umap')),
            'actorCount': len(rows), 'placementProof': proof,
            'groundTiles': len(base), 'groundCutTwins': len(twins),
            'inventory': inventory,
            '_fingerprintBase': base, '_fingerprintTwins': twins}


def run():
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Dirty packages present; a read-only survey must start clean')

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    OUT.mkdir(parents=True, exist_ok=True)
    before = {key: mt.sha256_of(mt.disk_path(config['map'], 'umap'))
              for key, config in mt.TARGETS.items()}

    surveys = {}
    for key in ('main50', 'candidate48'):          # authoring frame first
        surveys[key] = survey(ue, key)

    ground = mt.compare_fingerprints(surveys['main50']['_fingerprintBase'],
                                     surveys['candidate48']['_fingerprintBase'])
    twins = mt.compare_fingerprints(surveys['main50']['_fingerprintTwins'],
                                    surveys['candidate48']['_fingerprintTwins'])
    after = {key: mt.sha256_of(mt.disk_path(config['map'], 'umap'))
             for key, config in mt.TARGETS.items()}
    unchanged = all(before[k] == after[k] for k in before)

    GROUND_REFERENCE.write_text(json.dumps({
        'status': 'ground_fingerprint_read_from_the_live_main50_level',
        # 'readFromTarget', NOT 'target': verify.py check_map_parity buckets any JSON under
        # SourceAssets/ that carries a 'target' as a PASS that ran on that map, and this is a
        # reference table, not a pass. Naming it 'target' made the gate warn that a
        # 'ground-fingerprint' pass had run on the legacy map only.
        'stamp': stamp, 'readFromTarget': 'Main50', 'map': mt.TARGETS['main50']['map'],
        'mapSha256': surveys['main50']['mapSha256'],
        'note': ('World AABBs of every SM_JerusalemTerrain_* actor on Main50, EXCLUDING the '
                 'precinct/Kotel cut twins, whose cut region is legitimately different on the '
                 'two maps. The FutureMountV1 terrain was never rescaled by the 48 cm '
                 'migration, so these boxes are what vegetation stands on unchanged on both '
                 'maps, and release_vegetation.py checks the live level against this file '
                 'before it places an instance on the candidate.'),
        'tiles': surveys['main50']['_fingerprintBase'],
    }, indent=1), encoding='utf-8')

    written = []
    for key in ('main50', 'candidate48'):
        record = dict(surveys[key])
        record.pop('_fingerprintBase'), record.pop('_fingerprintTwins')
        record.update({
            'status': ('placement_proved_and_inventoried_map_unchanged' if unchanged
                       else 'placement_proved_but_a_map_changed_during_the_survey'),
            'stamp': stamp, 'mode': 'read_only_survey',
            'groundParityAgainstMain50': ground if key == 'candidate48' else None,
            'groundCutTwinDifference': twins if key == 'candidate48' else None,
            'otherTargetInventory': surveys['main50' if key == 'candidate48' else 'candidate48']['inventory'],
            'mapSha256Before': before[key], 'mapSha256After': after[key],
            'allMapsUnchanged': unchanged,
            'groundReferenceWritten': str(GROUND_REFERENCE),
        })
        path = OUT / ('candidate-placement-proof-%s-%s.json' % (record['target'], stamp))
        path.write_text(json.dumps(record, indent=1, default=str), encoding='utf-8')
        written.append(str(path))
        ue.log('placement proof [%s]: architecture %d/%d agree, worst %.4f cm, measured scale %s '
               'translation %s; inventory %s'
               % (record['target'], record['placementProof']['agreeing'],
                  record['placementProof']['sampled'], record['placementProof']['worstBoundsErrorCm'],
                  record['placementProof']['measured']['uniformScale'],
                  record['placementProof']['measured']['translationCm'],
                  json.dumps({k: v['actors'] for k, v in record['inventory'].items()})))

    ue.log('placement proof: ground tiles %d matched, worst %.6f cm; cut twins differ by %.4f cm; '
           'maps unchanged %s' % (ground['matchedLabels'], ground['worstBoundsErrorCm'],
                                  twins['worstBoundsErrorCm'], unchanged))
    if not unchanged:
        raise RuntimeError('A map changed during a read-only survey: %s -> %s' % (before, after))
    return written


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    try:
        for path in run():
            ue.log('placement proof receipt: ' + path)
    except Exception as error:  # noqa: BLE001
        ue.log_error('candidate_placement_proof failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps({'status': 'offline', 'targets': sorted(mt.TARGETS),
                          'groundReference': str(GROUND_REFERENCE),
                          'groundReferencePresent': GROUND_REFERENCE.is_file()}, indent=2))
elif _unreal_available():
    import unreal as _ue
    if 'candidate_placement_proof.py' in _ue.SystemLibrary.get_command_line().lower():
        _main()
