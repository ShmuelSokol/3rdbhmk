"""Lighting V3: checkpointed, reversible adoption of ONE reviewed variant on the main map.

Consumes Scripts/release_lighting_v3.spec.json. What a variant may change:
  * scalar parameters (NormalStrength, RoughnessScale) and Tint on the two limestone instances
    MI_PBR_LimestoneAshlar / MI_PBR_LimestoneTrim (instance-level, parent untouched, Nanite usage
    flags read back before/after and required identical);
  * post-process fields on the single unbound PostProcessVolume of the map (local exposure);
  * optionally the sun rotation (only variants that carry a 'sun' block).
Everything else (fog tune, skylight, exposure bounds/bias/film curve, other instances, master
material, protected maps) is hashed or read back and required unchanged.

Commandlet (strictly serial; check Get-Process UnrealEditor,UnrealEditor-Cmd first):
  UnrealEditor-Cmd.exe <uproject> -run=pythonscript -unattended -nullrhi -abslog=<unique>
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_lighting_v3.py"
      -LightingV3Apply=<variant>            checkpoint, apply, save, reopen, read back  -> lighting-v3-apply-<stamp>.json
      -LightingV3Verify=<apply receipt>     fresh-process readback only, no save         -> lighting-v3-verify-<stamp>.json
      -LightingV3Revert=<apply receipt>     restore checkpointed bytes / before-values   -> lighting-v3-revert-<stamp>.json
Offline:  python Scripts/release_lighting_v3.py   -> offline_check(): spec sanity and the planned table.

UE 5.8 pitfalls honoured: MaterialEditingLibrary setters return False even on success, so every set is
verified by readback; enum values are set by member name; the receipt is written at start, after each
stage and in finally so partial/failed state is preserved; a save returning False raises.
"""
import hashlib
import json
import re
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_lighting_v3.spec.json'


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk(asset, ext='uasset'):
    assert asset.startswith('/Game/') and '.' not in asset
    return ROOT / 'Content' / (asset[6:] + '.' + ext)


def resolve_variant(spec, name):
    v = dict(spec['variants'][name])
    if 'inherits' in v:
        merged = resolve_variant(spec, v['inherits'])
        merged.update({k: val for k, val in v.items() if k != 'inherits'})
        return merged
    return v


def close(a, b, tol=1e-4):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol * max(1.0, abs(a), abs(b))
    return a == b


def offline_check(spec=None):
    spec = spec or load_spec()
    problems = []
    for name in spec['editableInstances']:
        if not disk(spec['instanceFolder'] + name).exists():
            problems.append('missing instance ' + name)
    for asset in spec['protectedAssets']:
        if not disk(asset).exists():
            problems.append('missing protected asset ' + asset)
    for asset in spec['protectedMaps']:
        if not disk(asset, 'umap').exists():
            problems.append('missing protected map ' + asset)
    for name in spec['variants']:
        v = resolve_variant(spec, name)
        for inst in v.get('instances', {}):
            if inst not in spec['editableInstances']:
                problems.append('variant %s edits non-editable instance %s' % (name, inst))
        if 'sun' in v:
            p, y, r = v['sun']['rotatorPitchYawRoll']
            if abs(p + v['sun']['elevationDeg']) > 1e-6:
                problems.append('variant %s: pitch must equal -elevation' % name)
    for name in ('fog_density', 'fog_height_falloff', 'start_distance'):
        if name not in spec['fogTuneMustStay']:
            problems.append('fog guard missing ' + name)
    return {'status': 'offline_ok' if not problems else 'offline_problems', 'problems': problems,
            'variants': {n: resolve_variant(spec, n) for n in spec['variants']}, 'mapSha256Now': sha(ROOT / spec['targetMapFile'])}


# ------------------------------------------------------------------------------------------ native
class Native:
    PP_ORDER = None

    def __init__(self, ue, spec, mode, stamp):
        self.u = ue
        self.spec = spec
        self.mode = mode
        self.stamp = stamp
        self.ed = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.map_file = ROOT / spec['targetMapFile']
        self.receipt_path = ROOT / spec['receiptFolder'] / ('lighting-v3-%s-%s.json' % (mode, stamp))
        assert not self.receipt_path.exists()
        self.report = {'status': 'STARTED', 'mode': mode, 'stamp': stamp, 'map': spec['targetMap'], 'specSha256': sha(SPEC_PATH),
                       'engineVersion': ue.SystemLibrary.get_engine_version(), 'errors': [], 'stages': []}
        self.write()

    def write(self):
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.report, indent=2, default=str) + '\n', encoding='utf-8')

    def stage(self, name, **extra):
        row = {'stage': name}
        row.update(extra)
        self.report['stages'].append(row)
        self.write()

    # -- encoding
    def enc(self, v):
        u = self.u
        if isinstance(v, (bool, int, float, str)) or v is None:
            return v
        if isinstance(v, u.EnumBase):
            m = re.match(r"<(\w+)\.(\w+): (-?\d+)>", repr(v))
            return {'$enum': '%s.%s' % (m.group(1), m.group(2))} if m else str(v)
        if isinstance(v, u.Rotator):
            return [float(v.pitch), float(v.yaw), float(v.roll)]
        if isinstance(v, u.Vector):
            return [float(v.x), float(v.y), float(v.z)]
        if isinstance(v, u.LinearColor):
            return [float(v.r), float(v.g), float(v.b), float(v.a)]
        if isinstance(v, u.Object):
            return v.get_path_name()
        return str(v)

    def dec(self, raw):
        u = self.u
        if isinstance(raw, dict) and '$enum' in raw:
            cls, member = raw['$enum'].split('.')
            return getattr(getattr(u, cls), member)
        return raw

    # -- hashes
    def protected_hashes(self):
        h = {a: sha(disk(a)) for a in self.spec['protectedAssets']}
        h.update({m: sha(disk(m, 'umap')) for m in self.spec['protectedMaps']})
        return h

    def instance_files(self):
        return {n: disk(self.spec['instanceFolder'] + n) for n in self.spec['editableInstances']}

    # -- guards
    def guard_world(self):
        u = self.u
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project directory')
        if self.ed.get_game_world():
            raise RuntimeError('Game world active')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages before load')
        if not self.levels.load_level(self.spec['targetMap']):
            raise RuntimeError('load_level failed')
        world = self.ed.get_editor_world()
        if world.get_outermost().get_name() != self.spec['targetMap']:
            raise RuntimeError('Wrong map loaded')
        for folder in ('__ExternalActors__', '__ExternalObjects__'):
            if (ROOT / 'Content' / folder / self.spec['targetMap'][6:]).exists():
                raise RuntimeError('One-file-per-actor map needs expanded checkpoint support')
        return world

    def find_scene(self):
        u = self.u
        found = {'sun': [], 'sky': [], 'pp': [], 'fog': []}
        for a in self.actors.get_all_level_actors():
            if isinstance(a, u.DirectionalLight):
                found['sun'].append(a)
            elif isinstance(a, u.SkyLight):
                found['sky'].append(a)
            elif isinstance(a, u.PostProcessVolume):
                found['pp'].append(a)
            elif isinstance(a, u.ExponentialHeightFog):
                found['fog'].append(a)
        for k, v in found.items():
            if len(v) != 1:
                raise RuntimeError('Expected exactly one %s actor, found %d' % (k, len(v)))
        return {k: v[0] for k, v in found.items()}

    def scene_snapshot(self, exclude):
        rows = {}
        for a in self.actors.get_all_level_actors():
            n = a.get_name()
            if n in exclude:
                continue
            loc, rot, sc = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
            rows[n] = (a.get_actor_label(), round(loc.x, 3), round(loc.y, 3), round(loc.z, 3), round(rot.pitch, 3), round(rot.yaw, 3), round(rot.roll, 3),
                       round(sc.x, 4), round(sc.y, 4), round(sc.z, 4))
        return rows

    # -- readbacks
    def guard_values(self, scene):
        """Fog tune, skylight and exposure bounds that must stay exactly as reviewed."""
        u = self.u
        fog = scene['fog'].get_component_by_class(u.ExponentialHeightFogComponent)
        sky = scene['sky'].get_component_by_class(u.SkyLightComponent)
        sun = scene['sun'].get_component_by_class(u.DirectionalLightComponent)
        s = scene['pp'].get_editor_property('settings')
        return {
            'fog': {k: fog.get_editor_property(k) for k in ('fog_density', 'fog_height_falloff', 'start_distance', 'enable_volumetric_fog')},
            'skyLight': {'intensity': sky.get_editor_property('intensity'), 'lower_hemisphere_is_black': sky.get_editor_property('lower_hemisphere_is_black')},
            'sun': {'intensity': sun.get_editor_property('intensity'), 'temperature': sun.get_editor_property('temperature'), 'use_temperature': sun.get_editor_property('use_temperature'),
                    'rotation': self.enc(scene['sun'].get_actor_rotation())},
            'exposure': {k: self.enc(s.get_editor_property(k)) for k in ('auto_exposure_method', 'auto_exposure_min_brightness', 'auto_exposure_max_brightness', 'auto_exposure_bias',
                                                                        'auto_exposure_low_percent', 'auto_exposure_high_percent', 'film_slope', 'film_toe', 'film_shoulder', 'film_white_clip')},
        }

    def pp_values(self, volume, keys):
        s = volume.get_editor_property('settings')
        return {k: {'value': self.enc(s.get_editor_property(k)), 'override': bool(s.get_editor_property('override_' + k))} for k in keys}

    def instance_values(self, inst, names=('TilingCm', 'NormalStrength', 'RoughnessScale', 'Metallic', 'AlbedoFlatness')):
        u = self.u
        ml = u.MaterialEditingLibrary
        row = {'parent': self.enc(inst.get_editor_property('parent')),
               'scalars': {n: ml.get_material_instance_scalar_parameter_value(inst, n) for n in names},
               'Tint': self.enc(ml.get_material_instance_vector_parameter_value(inst, 'Tint')),
               'textures': {t: self.enc(ml.get_material_instance_texture_parameter_value(inst, t)) for t in ('Albedo', 'Normal', 'ARM')},
               'naniteUsage': {'enabled': bool(ml.has_material_usage(inst, u.MaterialUsage.MATUSAGE_NANITE)),
                               'explicitlyOverridden': bool(ml.has_material_usage_override(inst, u.MaterialUsage.MATUSAGE_NANITE))}}
        other = {}
        for name in dir(u.MaterialUsage):
            if name.startswith('MATUSAGE_') and name not in ('MATUSAGE_NANITE', 'MATUSAGE_MAX'):
                usage = getattr(u.MaterialUsage, name)
                other[name] = [bool(ml.has_material_usage(inst, usage)), bool(ml.has_material_usage_override(inst, usage))]
        row['otherUsage'] = other
        return row

    # -- mutation
    def set_instance_params(self, inst, block):
        u = self.u
        ml = u.MaterialEditingLibrary
        for name, value in block.get('scalars', {}).items():
            ml.set_material_instance_scalar_parameter_value(inst, name, float(value))   # returns False even on success
            got = ml.get_material_instance_scalar_parameter_value(inst, name)
            if abs(got - float(value)) > 1e-5:
                raise RuntimeError('Scalar readback mismatch %s: %r vs %r' % (name, got, value))
        if 'tint' in block:
            ml.set_material_instance_vector_parameter_value(inst, 'Tint', u.LinearColor(*block['tint']))
            got = self.enc(ml.get_material_instance_vector_parameter_value(inst, 'Tint'))
            if not close(got, list(block['tint'])):
                raise RuntimeError('Tint readback mismatch %r vs %r' % (got, block['tint']))
        ml.update_material_instance(inst)

    def set_pp(self, volume, fields, override_flags=None):
        s = volume.get_editor_property('settings')
        for k, raw in fields.items():
            s.set_editor_property(k, self.dec(raw))
            s.set_editor_property('override_' + k, True if override_flags is None else bool(override_flags[k]))
        volume.set_editor_property('settings', s)
        back = self.pp_values(volume, list(fields))
        for k, raw in fields.items():
            want = raw if not (isinstance(raw, dict) and '$enum' in raw) else raw
            if not close(back[k]['value'], want):
                raise RuntimeError('PP readback mismatch %s: %r vs %r' % (k, back[k]['value'], want))
        return back

    def save_asset(self, obj):
        u = self.u
        if not u.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset returned False for ' + obj.get_path_name())

    def save_map(self):
        u = self.u
        if u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty content packages before map save: %s' % [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
        if not self.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Map still dirty after save')

    # ---------------------------------------------------------------------------------- APPLY
    def apply(self, variant_name):
        u = self.u
        spec = self.spec
        variant = resolve_variant(spec, variant_name)
        r = self.report
        r.update(variant=variant_name, variantResolved=variant)
        protected_before = self.protected_hashes()
        r['protectedBefore'] = protected_before
        r['mapSha256Before'] = sha(self.map_file)
        files = self.instance_files()
        r['instanceSha256Before'] = {n: sha(p) for n, p in files.items()}
        world = self.guard_world()
        scene = self.find_scene()
        r['guardValuesBefore'] = self.guard_values(scene)
        fog = r['guardValuesBefore']['fog']
        must = spec['fogTuneMustStay']
        if not (close(fog['fog_density'], must['fog_density']) and close(fog['fog_height_falloff'], must['fog_height_falloff'])
                and close(fog['start_distance'], must['start_distance']) and fog['enable_volumetric_fog'] == must['enable_volumetric_fog']
                and r['guardValuesBefore']['skyLight']['lower_hemisphere_is_black'] == must['skyLight_lower_hemisphere_is_black']):
            raise RuntimeError('Fog/skylight tune differs from the reviewed values; stop and rebase')
        # instances
        instances = {}
        for name in variant.get('instances', {}):
            inst = u.load_asset(spec['instanceFolder'] + name)
            if inst is None:
                raise RuntimeError('Missing instance ' + name)
            instances[name] = inst
        r['instancesBefore'] = {n: self.instance_values(i) for n, i in instances.items()}
        pp_keys = list(variant.get('postProcess', {}))
        r['postProcessBefore'] = self.pp_values(scene['pp'], pp_keys) if pp_keys else {}
        r['sunBefore'] = {'rotation': self.enc(scene['sun'].get_actor_rotation())}
        self.stage('discovered')
        # checkpoint
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + self.stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(self.map_file, checkpoint / self.map_file.name)
        if sha(checkpoint / self.map_file.name) != r['mapSha256Before']:
            raise RuntimeError('Map checkpoint hash differs')
        (checkpoint / 'Assets').mkdir()
        for n, p in files.items():
            shutil.copy2(p, checkpoint / 'Assets' / p.name)
            if sha(checkpoint / 'Assets' / p.name) != r['instanceSha256Before'][n]:
                raise RuntimeError('Instance checkpoint hash differs ' + n)
        r['checkpoint'] = str(checkpoint)
        self.stage('checkpointed')
        exclude = {scene['pp'].get_name(), scene['sun'].get_name()}
        before_scene = self.scene_snapshot(exclude)
        # mutate instances
        for n, inst in instances.items():
            inst.modify(True)
            self.set_instance_params(inst, variant['instances'][n])
            self.save_asset(inst)
        r['instancesAfterSave'] = {n: self.instance_values(i) for n, i in instances.items()}
        for n in instances:
            b, a = r['instancesBefore'][n], r['instancesAfterSave'][n]
            if b['naniteUsage'] != a['naniteUsage'] or b['otherUsage'] != a['otherUsage'] or b['textures'] != a['textures'] or b['parent'] != a['parent']:
                raise RuntimeError('Usage flags / textures / parent changed on ' + n)
        r['instanceSha256After'] = {n: sha(p) for n, p in files.items()}
        self.stage('instances_saved')
        # mutate map
        if pp_keys:
            scene['pp'].modify(True)
            r['postProcessAfter'] = self.set_pp(scene['pp'], variant['postProcess'])
        if 'sun' in variant:
            scene['sun'].modify(True)
            p, y, rr = variant['sun']['rotatorPitchYawRoll']
            scene['sun'].set_actor_rotation(u.Rotator(pitch=p, yaw=y, roll=rr), True)
            r['sunAfter'] = {'rotation': self.enc(scene['sun'].get_actor_rotation())}
            if not close(r['sunAfter']['rotation'], [p, y, rr], 1e-3):
                raise RuntimeError('Sun rotation readback mismatch')
        if self.scene_snapshot(exclude) != before_scene:
            raise RuntimeError('Unrelated scene change detected before save')
        after_guard = self.guard_values(scene)
        for k in ('fog', 'skyLight', 'exposure'):
            if not close(after_guard[k], r['guardValuesBefore'][k]):
                raise RuntimeError('Guarded %s values changed' % k)
        if 'sun' not in variant and not close(after_guard['sun'], r['guardValuesBefore']['sun']):
            raise RuntimeError('Sun changed without a sun block')
        self.save_map()
        r['mapSaved'] = True
        r['mapSha256AfterSave'] = sha(self.map_file)
        self.stage('map_saved')
        # reopen and read back
        if not self.levels.load_level(spec['targetMap']):
            raise RuntimeError('Reopen failed')
        scene2 = self.find_scene()
        r['reopened'] = {'postProcess': self.pp_values(scene2['pp'], pp_keys) if pp_keys else {},
                         'sun': {'rotation': self.enc(scene2['sun'].get_actor_rotation())},
                         'guardValues': self.guard_values(scene2),
                         'instances': {n: self.instance_values(u.load_asset(spec['instanceFolder'] + n)) for n in instances},
                         'sceneUnchanged': self.scene_snapshot(exclude) == before_scene}
        for k, raw in variant.get('postProcess', {}).items():
            if not close(r['reopened']['postProcess'][k]['value'], raw) or not r['reopened']['postProcess'][k]['override']:
                raise RuntimeError('Reopened PP mismatch ' + k)
        for n, block in variant.get('instances', {}).items():
            for pname, pval in block.get('scalars', {}).items():
                if abs(r['reopened']['instances'][n]['scalars'][pname] - float(pval)) > 1e-5:
                    raise RuntimeError('Reopened instance scalar mismatch %s.%s' % (n, pname))
            if r['reopened']['instances'][n]['naniteUsage'] != r['instancesBefore'][n]['naniteUsage']:
                raise RuntimeError('Reopened Nanite usage differs on ' + n)
        if not r['reopened']['sceneUnchanged']:
            raise RuntimeError('Reopened scene differs')
        r['status'] = 'APPLIED_SAVED_REOPENED_VISUAL_REVIEW_PENDING'
        return r

    # ---------------------------------------------------------------------------------- VERIFY
    def verify(self, receipt_path):
        u = self.u
        spec = self.spec
        prior = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
        r = self.report
        r['applyReceipt'] = str(receipt_path)
        r['applyReceiptSha256'] = sha(receipt_path)
        r['mapSha256Now'] = sha(self.map_file)
        r['mapMatchesApplyAfter'] = r['mapSha256Now'] == prior.get('mapSha256AfterSave')
        files = self.instance_files()
        r['instanceSha256Now'] = {n: sha(p) for n, p in files.items()}
        r['instancesMatchApplyAfter'] = r['instanceSha256Now'] == prior.get('instanceSha256After')
        variant = prior['variantResolved']
        r['instances'] = {n: self.instance_values(u.load_asset(spec['instanceFolder'] + n)) for n in variant.get('instances', {})}
        self.guard_world()
        scene = self.find_scene()
        r['postProcess'] = self.pp_values(scene['pp'], list(variant.get('postProcess', {})))
        r['guardValues'] = self.guard_values(scene)
        r['protectedNow'] = self.protected_hashes()
        r['protectedUnchangedSinceApply'] = r['protectedNow'] == prior.get('protectedBefore')
        ok = r['mapMatchesApplyAfter'] and r['instancesMatchApplyAfter'] and r['protectedUnchangedSinceApply']
        for k, raw in variant.get('postProcess', {}).items():
            ok = ok and close(r['postProcess'][k]['value'], raw) and r['postProcess'][k]['override']
        for n, block in variant.get('instances', {}).items():
            for pname, pval in block.get('scalars', {}).items():
                ok = ok and abs(r['instances'][n]['scalars'][pname] - float(pval)) <= 1e-5
            ok = ok and r['instances'][n]['naniteUsage'] == prior['instancesBefore'][n]['naniteUsage']
        r['status'] = 'FRESH_PROCESS_VERIFIED' if ok else 'FRESH_PROCESS_MISMATCH'
        return r

    # ---------------------------------------------------------------------------------- REVERT
    def revert(self, receipt_path):
        u = self.u
        spec = self.spec
        prior = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
        r = self.report
        r['applyReceipt'] = str(receipt_path)
        checkpoint = Path(prior['checkpoint'])
        files = self.instance_files()
        r['mapSha256Before'] = sha(self.map_file)
        r['instanceSha256Before'] = {n: sha(p) for n, p in files.items()}
        # 1. instance bytes: restore from checkpoint BEFORE anything loads them
        for n, p in files.items():
            src = checkpoint / 'Assets' / p.name
            if sha(src) != prior['instanceSha256Before'][n]:
                raise RuntimeError('Checkpoint instance bytes do not match the apply receipt: ' + n)
            shutil.copy2(src, p)
        r['instanceSha256Restored'] = {n: sha(p) for n, p in files.items()}
        if r['instanceSha256Restored'] != prior['instanceSha256Before']:
            raise RuntimeError('Instance restore hash mismatch')
        self.stage('instances_restored_bytes')
        # 2. map: exact bytes if nobody else saved since; otherwise property-level restore
        if r['mapSha256Before'] == prior.get('mapSha256AfterSave'):
            src = checkpoint / self.map_file.name
            if sha(src) != prior['mapSha256Before']:
                raise RuntimeError('Checkpoint map bytes do not match the apply receipt')
            shutil.copy2(src, self.map_file)
            r['mapRestoreMode'] = 'checkpoint_bytes'
        else:
            r['mapRestoreMode'] = 'property_level_before_values'
        self.guard_world()
        scene = self.find_scene()
        if r['mapRestoreMode'] == 'property_level_before_values':
            pp_before = prior.get('postProcessBefore', {})
            if pp_before:
                scene['pp'].modify(True)
                self.set_pp(scene['pp'], {k: v['value'] for k, v in pp_before.items()}, {k: v['override'] for k, v in pp_before.items()})
            if 'sunAfter' in prior:
                p, y, rr = prior['sunBefore']['rotation']
                scene['sun'].modify(True)
                scene['sun'].set_actor_rotation(u.Rotator(pitch=p, yaw=y, roll=rr), True)
            self.save_map()
            if not self.levels.load_level(spec['targetMap']):
                raise RuntimeError('Reopen failed')
            scene = self.find_scene()
        r['mapSha256After'] = sha(self.map_file)
        pp_keys = list(prior.get('postProcessBefore', {}))
        r['reopened'] = {'postProcess': self.pp_values(scene['pp'], pp_keys) if pp_keys else {},
                         'sun': {'rotation': self.enc(scene['sun'].get_actor_rotation())},
                         'guardValues': self.guard_values(scene),
                         'instances': {n: self.instance_values(u.load_asset(spec['instanceFolder'] + n)) for n in prior.get('instancesBefore', {})}}
        ok = close(r['reopened']['postProcess'], prior.get('postProcessBefore', {})) and close(r['reopened']['sun'], prior['sunBefore'], 1e-3)
        for n, before in prior.get('instancesBefore', {}).items():
            ok = ok and close(r['reopened']['instances'][n]['scalars'], before['scalars']) and r['reopened']['instances'][n]['naniteUsage'] == before['naniteUsage']
        r['status'] = 'REVERTED_SAVED_REOPENED' if ok else 'REVERT_READBACK_MISMATCH'
        return r


def _native_main():
    import unreal as ue
    cmd = ue.SystemLibrary.get_command_line()
    spec = load_spec()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    apply_m = re.search(r'-LightingV3Apply=([A-Za-z0-9_]+)', cmd)
    verify_m = re.search(r'-LightingV3Verify=([^\s"]+)', cmd)
    revert_m = re.search(r'-LightingV3Revert=([^\s"]+)', cmd)
    mode = 'apply' if apply_m else 'verify' if verify_m else 'revert' if revert_m else None
    if mode is None:
        raise RuntimeError('Pass -LightingV3Apply=<variant>, -LightingV3Verify=<receipt> or -LightingV3Revert=<receipt>')
    native = Native(ue, spec, mode, stamp)
    protected_before = native.protected_hashes()
    try:
        if mode == 'apply':
            if apply_m.group(1) not in spec['variants'] or apply_m.group(1) == 'baseline':
                raise RuntimeError('Unknown or non-applicable variant ' + apply_m.group(1))
            native.apply(apply_m.group(1))
        elif mode == 'verify':
            native.verify(verify_m.group(1))
        else:
            native.revert(revert_m.group(1))
    except Exception as exc:
        native.report['status'] = 'FAILED_' + mode.upper() + ('_CHECKPOINT_AVAILABLE' if native.report.get('checkpoint') else '')
        native.report['errors'].append(repr(exc))
        native.report['traceback'] = traceback.format_exc()
        raise
    finally:
        native.report['protectedAfter'] = native.protected_hashes()
        native.report['protectedUnchanged'] = native.report['protectedAfter'] == protected_before
        native.report['mapSha256Final'] = sha(native.map_file)
        if not native.report['protectedUnchanged']:
            native.report['status'] = 'FAILED_PROTECTED_HASH_MISMATCH'
        native.write()
        ue.log('LIGHTING_V3_%s %s status=%s' % (mode.upper(), native.receipt_path, native.report['status']))


if __name__ == '__main__':
    try:
        import unreal  # noqa: F401
        _native_main()
    except ImportError:
        print(json.dumps(offline_check(), indent=2, default=str))
