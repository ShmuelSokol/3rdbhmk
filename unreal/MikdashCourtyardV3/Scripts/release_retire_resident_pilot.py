"""Retire the superseded five-person pilot after the 24-person V3 population is bound.

The five original actors remain saved, hidden with collision disabled; nothing is deleted.
Use -RetirePilotTarget=Main50 or Candidate48 in a dedicated commandlet. Native jobs serial.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MAPS = {'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
        'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    import unreal as u
    assert Path(u.Paths.project_dir()).resolve() == ROOT
    m = re.search(r'-RetirePilotTarget=(Main50|Candidate48)', u.SystemLibrary.get_command_line())
    assert m, 'Specify exact target'
    key = m.group(1)
    package = MAPS[key]
    target = ROOT / 'Content' / (package[6:] + '.umap')
    ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    assert not ed.get_game_world(), 'PIE active'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Dirty maps'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Dirty content'
    assert levels.load_level(package)
    def find(label):
        found = [a for a in actors.get_all_level_actors() if a.get_actor_label() == label]
        assert len(found) == 1, 'Expected exactly one ' + label
        return found[0]
    owner = find('RELEASE_ResidentPopulation')
    current = find('RELEASE_PeopleV3Population')
    assert isinstance(owner, u.MikdashResidentPopulation) and isinstance(current, u.MikdashResidentPopulation)
    assert current.get_editor_property('spawn_authored_people_on_begin_play')
    assert len(current.get_editor_property('body_variants')) == 6, 'V3 binding must precede retirement'
    bodies = list(owner.get_editor_property('bodies'))
    assert len(bodies) == 5 and len({a.get_name() for a in bodies if a}) == 5
    assert all(isinstance(a, u.MikdashResidentCharacter) and a.get_actor_label().startswith('RELEASE_Resident_authored-outer-visitor-') for a in bodies)
    labels = [a.get_actor_label() for a in bodies]
    def readback():
        return dict(pilotStartup=bool(find('RELEASE_ResidentPopulation').get_editor_property('activate_reviewed_pilot_on_begin_play')),
                    bodies={label: dict(hidden=bool(find(label).get_editor_property('hidden')),
                                        collision=bool(find(label).get_actor_enable_collision())) for label in labels})
    excluded = {owner.get_name()} | {a.get_name() for a in bodies}
    def snapshot():
        return {a.get_name(): dict(label=a.get_actor_label(), transform=a.get_actor_transform().export_text(),
                                 hidden=bool(a.get_editor_property('hidden')), collision=bool(a.get_actor_enable_collision()))
                for a in actors.get_all_level_actors() if a.get_name() not in excluded}
    protected = {str(p): sha(p) for p in (ROOT / 'Content').rglob('*.umap') if p != target}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('RetirePilot-' + key + '-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(target, checkpoint / 'before.umap')
    before_hash = sha(target)
    assert sha(checkpoint / 'before.umap') == before_hash
    out = ROOT / 'SourceAssets/runtime-review/people' / ('retire-pilot-' + key + '-' + stamp + '.json')
    report = dict(status='checkpointed', target=key, map=package, mapShaBefore=before_hash,
                  checkpoint=str(checkpoint), before=readback(), errors=[], mapSaved=False)
    def write():
        out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    write()
    try:
        baseline = snapshot()
        owner.modify(True)
        owner.set_editor_property('activate_reviewed_pilot_on_begin_play', False)
        for body in bodies:
            body.modify(True)
            body.set_actor_hidden_in_game(True)
            body.set_actor_enable_collision(False)
        assert snapshot() == baseline, 'Unrelated actor change'
        report['after'] = readback()
        assert not report['after']['pilotStartup']
        assert all(v['hidden'] and not v['collision'] for v in report['after']['bodies'].values())
        assert levels.save_current_level(), 'Save failed'
        report.update(mapSaved=True, mapShaAfter=sha(target)); write()
        assert levels.load_level(package), 'Reopen failed'
        report['reopened'] = readback()
        assert report['reopened'] == report['after'], 'Reopened pilot differs'
        report['status'] = 'saved_reopened_native_movement_verification_pending'
    except Exception as exc:
        report['status'] = 'failed_checkpoint_available'
        report['errors'].append(repr(exc))
        raise
    finally:
        report['protectedMapsUnchanged'] = all(sha(Path(p)) == value for p, value in protected.items())
        write()
        assert report['protectedMapsUnchanged']


if __name__ == '__main__':
    run()
