"""cp15: the menorah's light follows the lamps. Switch off the static map-level cheat light.

WHY. Through cp14 nobody could see a lamp light. What read as "flames burning" from frame 0
was the gold lids lit by RELEASE_SanctuaryV2_MenorahLamps, a static-placed movable PointLight
at 90 cd / 1900 K that release_sanctuary_finish_v2 spawned as "a deliberate cinematic cheat"
because the FX director's own seven lamp lights were invisible. They were invisible because
ULocalLightComponent's constructor leaves a NewObject light UNITLESS, so SetIntensity(1.4)
was ~0.002 cd, not 1.4 cd. The C++ (cp15) now builds them in CANDELAS at LampLightCandela
(1 cd, about a candle) and switches each on at its own lamp's kindling; the flame cards'
emissive is raised to flame luminance (LampFlameEmissiveScale). With that, the static light
is the one thing that still lights the lamps before he kindles them, so it is switched off.

It is DISABLED, not deleted: intensity 0 and component visibility False, both read back.
The actor stays, so -LampLightRevert restores the two recorded values exactly.

MODES (hidden editor, one engine at a time; every mode writes a receipt):
  -LampLightApply  -LampTarget=Candidate48|Main50
  -LampLightRevert -LampTarget=...      restore intensity/visible from the newest saved apply.
  -LampLightProveAll                    Candidate48: apply, revert, re-apply; then Main50 apply.
Guard pattern per map: checkpoint the .umap into ReviewCheckpoints/LampLight-*, protected
hashes before/after, whole-scene snapshot (nothing may move), write, save, REOPEN, numeric
readback of the light AND of every MikdashFXDirector's lamp numbers, other map unchanged.

Receipts: SourceAssets/service-review/lamp-light-<mode>-<target>-<stamp>.json
"""
import importlib.util, json, re, shutil, sys, traceback
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/service-review'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
LIGHT_LABEL = 'RELEASE_SanctuaryV2_MenorahLamps'
# Expected pre-apply values, from Scripts/release_sanctuary_finish_v2.spec.json.
SPEC_INTENSITY = 90.0
FX_FIELDS = ('lamps_follow_service', 'lamp_kindle_ramp_seconds', 'lamp_light_candela',
             'lamp_light_source_radius_cm', 'lamp_flame_emissive_scale', 'flame_lamp_material', 'card_mesh')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIN = _load('release_walk_v2_finish_for_lamp_light', 'Scripts/release_walk_v2_finish.py')
sha, stamp_now, utc = FIN.sha, FIN.stamp_now, FIN.utc
_same, _find, _read_props = FIN._same, FIN._find, FIN._read_props
disk_umap, _targets, _guards = FIN.disk_umap, FIN._targets, FIN._guards


def receipt_path(kind, key, stamp):
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / ('lamp-light-%s-%s-%s.json' % (kind, key, stamp))


def _light(ue, actors):
    actor = _find(actors, LIGHT_LABEL)
    if not isinstance(actor, ue.PointLight):
        raise RuntimeError('%s is %s, not a PointLight' % (LIGHT_LABEL, actor.get_class().get_name()))
    return actor, actor.get_component_by_class(ue.PointLightComponent)


def _read_light(ue, actors):
    actor, comp = _light(ue, actors)
    loc = actor.get_actor_location()
    return {
        'intensity': float(comp.get_editor_property('intensity')),
        'visible': bool(comp.get_editor_property('visible')),
        'intensity_units': str(comp.get_editor_property('intensity_units')),
        'mobility': str(comp.get_editor_property('mobility')),
        'temperature': float(comp.get_editor_property('temperature')),
        'attenuation_radius': float(comp.get_editor_property('attenuation_radius')),
        'location': [round(float(loc.x), 3), round(float(loc.y), 3), round(float(loc.z), 3)],
    }


def _fx_readback(ue, actors):
    rows = []
    for a in actors.get_all_level_actors():
        if a.get_class().get_name() == 'MikdashFXDirector':
            row = dict(label=a.get_actor_label(), **_read_props(ue, a, FX_FIELDS))
            try:
                row['lamp_flame_cm'] = [[round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]
                                        for v in a.get_editor_property('lamp_flame_cm')]
                row['lamp_light_cm'] = [[round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]
                                        for v in a.get_editor_property('lamp_light_cm')]
            except Exception as error:                                   # noqa: BLE001
                row['anchorsError'] = str(error)[:200]
            rows.append(row)
    return rows


def _check_fx(rows):
    if len(rows) != 1:
        raise RuntimeError('expected exactly one MikdashFXDirector, found %d' % len(rows))
    fx = rows[0]
    for f, v in (('lamp_light_candela', 1.0), ('lamp_flame_emissive_scale', 5000.0),
                 ('lamps_follow_service', True)):
        if not _same(fx.get(f), v):
            raise RuntimeError('FX director %s is %r, expected %r: is the cp15 editor module built?'
                               % (f, fx.get(f), v))
    if not fx.get('flame_lamp_material') or not fx.get('card_mesh'):
        raise RuntimeError('FX director has no flame_lamp_material/card_mesh: the lamp cards would never build')


def _plan_apply(before):
    if before['mobility'].upper().find('MOVABLE') < 0:
        raise RuntimeError('%s mobility %s: a static/stationary light would keep baked light after '
                           'being hidden' % (LIGHT_LABEL, before['mobility']))
    if not (_same(before['intensity'], SPEC_INTENSITY) or _same(before['intensity'], 0.0)):
        raise RuntimeError('%s intensity is %r, neither the spec 90 nor already 0; refuse to guess'
                           % (LIGHT_LABEL, before['intensity']))
    wanted = dict(before)
    wanted['intensity'] = 0.0
    wanted['visible'] = False
    return wanted


def _write(ue, actors, wanted):
    actor, comp = _light(ue, actors)
    actor.modify(True)
    comp.modify(True)
    comp.set_editor_property('intensity', float(wanted['intensity']))
    comp.set_editor_property('visible', bool(wanted['visible']))


def _apply(key, kind, plan_fn):
    stamp = stamp_now()
    targets = _targets()
    MAP = targets[key]['map']
    map_file = disk_umap(MAP)
    others = {k: disk_umap(t['map']) for k, t in targets.items() if k != key}
    out = receipt_path(kind, key, stamp)
    r = dict(status='starting', mode=kind, target=key, map=MAP, utc=utc(), stamp=stamp,
             mapBeforeSha256=sha(map_file), otherMapsBefore={k: sha(v) for k, v in others.items()},
             errors=[])

    def write():
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    import unreal as ue
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    try:
        r['editorProcesses'] = _guards(ue)
        protected_before = FIN.protected_hashes()
        r['protectedBefore'] = protected_before
        cp = CHECKPOINT_ROOT / ('LampLight-%s-%s-%s' % (kind, key, stamp))
        cp.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, cp / 'BeforeLampLight.umap')
        if sha(cp / 'BeforeLampLight.umap') != r['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy mismatch')
        r['checkpoint'] = str(cp)
        write()
        if editor.get_editor_world().get_outermost().get_name() != MAP and not levels.load_level(MAP):
            raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Unexpected editor world')
        crowd = _load('lamp_light_snapshot', 'Scripts/release_resident_crowd.py')
        baseline = crowd._scene_snapshot(ue, actors)
        before = _read_light(ue, actors)
        r['before'] = before
        r['fxBefore'] = _fx_readback(ue, actors)
        _check_fx(r['fxBefore'])
        wanted, notes = plan_fn(before)
        r['wanted'], r['notes'] = wanted, notes
        write()
        changed = not _same(wanted, before)
        if changed:
            _write(ue, actors, wanted)
        after_set = _read_light(ue, actors)
        if not _same(after_set, wanted):
            raise RuntimeError('Did not read back as planned before save: %r' % after_set)
        after_scene = crowd._scene_snapshot(ue, actors)
        moved = sorted(k for k in set(baseline) | set(after_scene) if baseline.get(k) != after_scene.get(k))
        r['sceneChanges'] = moved
        light_name = _light(ue, actors)[0].get_name()
        r['sceneChangeAllowed'] = light_name
        r['lightSnapshotBefore'] = baseline.get(light_name)
        r['lightSnapshotAfter'] = after_scene.get(light_name)
        if set(moved) - ({light_name} if changed else set()):
            raise RuntimeError('Unexpected scene changes beyond %s: %r' % (light_name, moved[:20]))
        if changed:
            if not levels.save_current_level():
                raise RuntimeError('Level save failed (zombie editor holding the map?)')
            r.update(mapSaved=True, mapAfterSha256=sha(map_file), status='saved_reopen_pending')
            write()
            if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP:
                raise RuntimeError('Reopen failed')
        else:
            r.update(mapSaved=False, mapAfterSha256=sha(map_file))
        readback = _read_light(ue, actors)
        r['readbackAfterReopen'] = readback
        r['fxAfterReopen'] = _fx_readback(ue, actors)
        _check_fx(r['fxAfterReopen'])
        if not _same(readback, wanted):
            raise RuntimeError('Readback after reopen differs: %r' % readback)
        r['otherMapsAfter'] = {k: sha(v) for k, v in others.items()}
        r['otherMapsUnchanged'] = r['otherMapsAfter'] == r['otherMapsBefore']
        if not r['otherMapsUnchanged']:
            raise RuntimeError('Another map changed bytes during the run')
        protected_after = FIN.protected_hashes()
        this_map = str(map_file.relative_to(ROOT)).replace('\\', '/')
        r['protectedAfter'] = protected_after
        r['protectedChangedExcludingThisMap'] = sorted(
            k for k in set(protected_before) | set(protected_after)
            if protected_before.get(k) != protected_after.get(k) and k != this_map)
        if r['protectedChangedExcludingThisMap']:
            raise RuntimeError('Protected assets changed: %r' % r['protectedChangedExcludingThisMap'])
        r['status'] = ('%s_saved_reopened_readback_frame_pending' % kind) if changed \
            else ('%s_no_change_needed' % kind)
        write()
    except Exception:
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
        try:
            r['mapAfterSha256'] = sha(map_file)
        except Exception:                                             # noqa: BLE001
            pass
        write()
        raise
    return r


def run_apply(key):
    return _apply(key, 'apply', lambda before: (_plan_apply(before), dict(
        why='static cheat light off; the FX director lights each lamp at 1 cd from its own kindling')))


def run_revert(key):
    previous = sorted(p for p in OUT.glob('lamp-light-apply-%s-*.json' % key)
                      if json.loads(p.read_text(encoding='utf-8-sig')).get('mapSaved'))
    if not previous:
        raise RuntimeError('No saved apply receipt for %s to revert' % key)
    src = json.loads(previous[-1].read_text(encoding='utf-8-sig'))

    def plan(before):
        for f in ('location', 'mobility', 'temperature', 'attenuation_radius'):
            if not _same(before.get(f), src['before'].get(f)):
                raise RuntimeError('%s moved since the apply (%r -> %r); refuse to revert blind'
                                   % (f, src['before'].get(f), before.get(f)))
        restore = dict(before)
        restore['intensity'] = src['before']['intensity']
        restore['visible'] = src['before']['visible']
        return restore, dict(revertSource=previous[-1].name, revertSourceSha256=sha(previous[-1]))
    return _apply(key, 'revert', plan)


def _key(cmd):
    m = re.search(r'-LampTarget=(Main50|Candidate48)', cmd)
    if not m:
        raise RuntimeError('Pass -LampTarget=Main50|Candidate48')
    return m.group(1)


def _main():
    import unreal
    cmd = unreal.SystemLibrary.get_command_line()
    try:
        if '-LampLightProveAll' in cmd:
            run_apply('Candidate48')
            run_revert('Candidate48')
            run_apply('Candidate48')
            run_apply('Main50')
        elif '-LampLightApply' in cmd:
            run_apply(_key(cmd))
        elif '-LampLightRevert' in cmd:
            run_revert(_key(cmd))
        else:
            raise RuntimeError('release_lamp_light: pass a -LampLight* mode')
    except Exception:
        receipt_path('failure', 'any', stamp_now()).write_text(
            json.dumps(dict(commandLine=cmd, error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise
    finally:
        if '-executepythonscript' in cmd.lower() and '-run=pythonscript' not in cmd.lower():
            unreal.SystemLibrary.quit_editor()


if __name__ == '__main__':
    _main()
