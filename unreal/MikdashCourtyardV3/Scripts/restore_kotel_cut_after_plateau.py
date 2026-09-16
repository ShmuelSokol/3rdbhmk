"""Restore the Kotel V3 actor accidentally removed by the S4 terrain revert.

Run in an empty editor with -ExecutePythonScript and either -KotelRestoreApply
or -KotelRestoreVerify. Preload assets before loading Candidate48, cap static
mesh compilation concurrency at 1, and run verify in a fresh process.
No asset is regenerated. Apply refuses any map except the inspected S4 bytes.
"""
import hashlib
import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
BASELINE = 'f1939fe0839a6c3b14b0bac0af5a0825adde4e80dca042fb47c3f011168cda42'
TWIN = '/Game/MikdashV3/KotelPlazaCutV3/SM_JerusalemTerrain_07_08_FutureMountCut_KotelPlazaCut'
ORIGINAL = '/Game/MikdashV3/FutureMountV1/Terrain/SM_JerusalemTerrain_07_08_FutureMountCut'
MATERIAL = '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Terrain'
LABEL = 'RELEASE_KotelPlazaCut_07_08'
REVIEW = ROOT / 'SourceAssets/enclosure-review/HideSetV1'


def disk(package, suffix='.uasset'):
    return ROOT / 'Content' / (package[6:] + suffix)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import unreal as ue
    command = ue.SystemLibrary.get_command_line()
    apply = '-KotelRestoreApply' in command
    assert apply != ('-KotelRestoreVerify' in command), 'Choose apply or verify'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    mode = 'apply' if apply else 'verify'
    output = REVIEW / ('kotel-cut-restore-%s-%s.json' % (mode, stamp))
    map_file = disk(MAP, '.umap')
    protected = sorted(p for p in (ROOT / 'Content').rglob('*.umap') if p != map_file)
    protected += [disk(TWIN), disk(ORIGINAL), disk(MATERIAL)]
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    report = dict(status='started', mode=mode, timestampUtc=stamp, map=MAP,
                  mapSha256Before=sha(map_file), protectedBefore=before,
                  scriptSha256=sha(Path(__file__)))
    try:
        if apply:
            assert report['mapSha256Before'] == BASELINE, 'Unreviewed source map'
        # Never resolve assets after loading the large map.
        mesh = ue.load_asset(TWIN)
        material = ue.load_asset(MATERIAL)
        assert mesh and material
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        assert levels.load_level(MAP)
        all_actors = list(actors.get_all_level_actors())
        def unique(label):
            found = [a for a in all_actors if a.get_actor_label() == label]
            assert len(found) == 1, (label, len(found))
            return found[0]
        original = unique('SM_JerusalemTerrain_07_08')
        plaza = unique('RELEASE_KotelPlaza')
        enclosure = unique('RELEASE_EnclosureV2_Precinct')
        assert not enclosure.get_editor_property('build_plaza')
        assert 'KotelPlazaCutTwin' in [str(t) for t in plaza.tags]
        component = original.get_component_by_class(ue.StaticMeshComponent)
        assert component.static_mesh.get_path_name().split('.')[0] == ORIGINAL
        assert component.get_material(0) == material
        identity = ue.Transform()
        def at_identity(actor):
            t = actor.get_actor_transform()
            return (t.translation == identity.translation and t.rotation == identity.rotation
                    and t.scale3d == identity.scale3d)
        assert at_identity(original) and at_identity(plaza)
        if apply:
            assert not any(a.get_actor_label() == LABEL for a in all_actors)
            assert [str(t) for t in original.tags] == ['MikdashJerusalemTerrainV1']
            assert not original.get_editor_property('hidden') and original.get_actor_enable_collision()
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('KotelCutRestore-' + stamp)
            checkpoint.mkdir(parents=True)
            shutil.copy2(map_file, checkpoint / 'Walkthrough.umap')
            assert sha(checkpoint / 'Walkthrough.umap') == BASELINE
            report['checkpoint'] = str(checkpoint)
            twin = actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(), ue.Rotator())
            assert twin
            twin.set_actor_label(LABEL)
            tc = twin.get_component_by_class(ue.StaticMeshComponent)
            tc.set_editor_property('mobility', ue.ComponentMobility.STATIC)
            assert tc.set_static_mesh(mesh)
            tc.set_material(0, material)
            tc.set_collision_profile_name(component.get_collision_profile_name())
            twin.set_editor_property('tags', [ue.Name('KotelPlazaCutTwin'), ue.Name('SM_JerusalemTerrain_07_08')])
            twin.set_actor_hidden_in_game(False)
            twin.set_actor_enable_collision(True)
            # The Kotel twin now replaces this original in EVERY state. Both phase
            # tags are needed: one hides it with the wall, the other with the city.
            original.set_editor_property('tags', [ue.Name(t) for t in
                ('MikdashJerusalemTerrainV1', 'PrecinctCutOriginal', 'KotelPlazaCutOriginal')])
            original.set_actor_hidden_in_game(True)
            original.set_actor_enable_collision(False)
        else:
            twin = unique(LABEL)
            tc = twin.get_component_by_class(ue.StaticMeshComponent)
        assert at_identity(twin) and tc.static_mesh == mesh and tc.get_material(0) == material
        assert str(tc.get_collision_profile_name()) == 'BlockAll'
        assert not twin.get_editor_property('hidden') and twin.get_actor_enable_collision()
        assert original.get_editor_property('hidden') and not original.get_actor_enable_collision()
        assert {'PrecinctCutOriginal', 'KotelPlazaCutOriginal'} <= {str(t) for t in original.tags}
        assert 'KotelPlazaCutTwin' in [str(t) for t in twin.tags]
        report['readback'] = dict(twinLabel=LABEL, twinMesh=TWIN, atIdentity=True,
            material=MATERIAL, profile='BlockAll', twinVisible=True, twinCollision=True,
            originalHidden=True, originalCollision=False,
            originalTags=[str(t) for t in original.tags], bBuildPlaza=False)
        if apply:
            assert levels.save_current_level(), 'Save failed'
        report['status'] = 'saved-fresh-verify-pending' if apply else 'fresh-readback-passed'
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
        raise
    finally:
        report['mapSha256After'] = sha(map_file)
        report['protectedAfter'] = {str(p.relative_to(ROOT)): sha(p) for p in protected}
        report['protectedUnchanged'] = before == report['protectedAfter']
        report['mapUnchanged'] = report['mapSha256Before'] == report['mapSha256After']
        if not report['protectedUnchanged'] or (not apply and not report['mapUnchanged']):
            report['status'] = 'failed-hash-guard'
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    main()
