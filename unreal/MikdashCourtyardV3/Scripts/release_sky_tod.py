"""Checkpointed placement of the runtime time-of-day actor; native jobs serial.
Run from a dedicated editor on the integrated map via -ExecutePythonScript.
No weather actor is assumed: none is present in the current source inventory.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
LABEL = 'RELEASE_SkyTimeV1'
PROTECTED = [
    'Content/MikdashV3/Maps/Courtyard.umap',
    'Content/MikdashV3/FutureMountV1/L_FutureMount.umap',
    'Content/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold.umap',
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'SourceAssets/lighting-review' / ('sky-time-adoption-' + stamp + '.json')
    report = {'status': 'started', 'map': MAP, 'label': LABEL, 'visualAcceptance': 'pending'}
    map_file = ROOT / 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
    report['mapBeforeSha256'] = sha(map_file)
    protected = {p: sha(ROOT / p) for p in PROTECTED}
    def write():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    write()
    try:
        if Path(u.Paths.project_dir()).resolve() != ROOT.resolve():
            raise RuntimeError('Wrong project')
        ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if ed.get_game_world() is not None:
            raise RuntimeError('PIE is active')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages; refusing placement')
        if ed.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Open integrated map before placement')
        cls = u.load_class(None, '/Script/MikdashRuntime.MikdashTimeOfDay')
        if cls is None:
            raise RuntimeError('Compile the time-of-day class before placement')
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        before = list(actors.get_all_level_actors())
        if any(a.get_class() == cls or a.get_actor_label() == LABEL for a in before):
            raise RuntimeError('Time-of-day actor already present; do not duplicate')
        checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('SkyTime-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'Walkthrough.umap')
        if sha(checkpoint / 'Walkthrough.umap') != report['mapBeforeSha256']:
            raise RuntimeError('Checkpoint mismatch')
        report['checkpoint'] = str(checkpoint)
        actor = actors.spawn_actor_from_class(cls, u.Vector(0, 0, 0))
        if actor is None:
            raise RuntimeError('Spawn failed')
        actor.set_actor_label(LABEL)
        actor.set_editor_property('tags', [u.Name(LABEL)])
        actor.set_folder_path('Release/Sky')
        # Runtime controls drive lighting; editor placement itself never applies a preset.
        settings = {'frozen': True, 'rate_multiplier': 0.0,
                    'apply_start_preset_on_begin_play': True, 'restore_on_end_play': True}
        for key, value in settings.items():
            actor.set_editor_property(key, value)
            if actor.get_editor_property(key) != value:
                raise RuntimeError('Property readback failed: ' + key)
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if not levels.save_current_level():
            raise RuntimeError('Map save failed; inspect process ownership before retry')
        report['mapSaved'] = True
        report['mapAfterSha256'] = sha(map_file)
        write()
        if not levels.load_level(MAP):
            raise RuntimeError('Map reopen failed')
        matches = [a for a in actors.get_all_level_actors() if a.get_actor_label() == LABEL]
        if len(matches) != 1 or matches[0].get_class() != cls:
            raise RuntimeError('Reopened actor mismatch')
        report['readback'] = {key: matches[0].get_editor_property(key) for key in settings}
        if report['readback'] != settings:
            raise RuntimeError('Reopened properties mismatch')
        report['protectedMapsUnchanged'] = all(sha(ROOT / p) == value for p, value in protected.items())
        if not report['protectedMapsUnchanged']:
            raise RuntimeError('Protected map changed')
        report['status'] = 'saved_reopened_runtime_lighting_review_pending'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = repr(error)
        raise
    finally:
        report['mapAfterSha256'] = sha(map_file)
        write()
    return report

if __name__ == '__main__':
    import unreal
    try:
        run()
    finally:
        unreal.SystemLibrary.quit_editor()
