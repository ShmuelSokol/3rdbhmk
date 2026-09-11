"""Instance-level Nanite usage repair for the three MI_SanctuaryV2_Gold* shell instances. No map, no graph, no parent.

WHY: the cooked log says these three "missing usage flag Nanite! Default Material will be used in game".
M_PBR_Tiled (protected) has no bUsedWithNanite; the nine repaired MI_PBR_* instances carry the repair as an
INSTANCE override (BasePropertyOverrides.bOverride_UsageFlags, UE5.8). release_sanctuary_finish_v2.py copied
MI_PBR_GoldHammered's textures but not that override. In game the Nanite material audit then fails, so
ShouldCreateNaniteProxy() is false and the 10 shell components render through a classic FStaticMeshSceneProxy
with the correct MI (frames cp15shell-*.png): no visual fallback, but no Nanite either. This copies exactly
GoldHammered's usage overrides onto the three instances, as release_lighting_v3.py already does.

Modes (commandlet, -nullrhi):  -SanctV2NaniteApply | -SanctV2NaniteVerify=<apply receipt>
Offline (plain python):        no args = check pins; --revert <apply receipt> restores the checkpoint.
"""
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets' / 'sanctuary-detail' / 'SanctuaryFinishV2'
CKPT_ROOT = ROOT.parent / 'ReviewCheckpoints'
PARENT = '/Game/MikdashV3/Materials/PBR/M_PBR_Tiled'
SOURCE = '/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_GoldHammered'
TARGETS = {
    '/Game/MikdashV3/SanctuaryFinishV2/MI_SanctuaryV2_GoldWall': '3091bc8de97202592877f71b6b546cdcc98f275fbadde976dcaa57c0e43e7277',
    '/Game/MikdashV3/SanctuaryFinishV2/MI_SanctuaryV2_GoldFloor': 'a9a3bfc24c5da0cf638c99fd25a563cf1dd07533221d296db78f99a1dc69fdb4',
    '/Game/MikdashV3/SanctuaryFinishV2/MI_SanctuaryV2_GoldCeiling': '182d2ab7e376d5aa8d44b9bbc8ec2abb6fa3a4ad9bb9a8ae87013578166a3849',
}
ANCHORS = {
    PARENT: '7a1aaf9db94dd1865ed1ca6ca94e7fc3439db0dd688e03cfedaa1da62da2fb34',
    SOURCE: '298f28933d0df6d53687559d695871f216a350eee046c5a94fab4394242fcd04',
}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def rel(pkg):
    return 'Content/' + pkg[6:] + '.uasset'


def content_hashes():
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT / 'Content').rglob('*') if p.is_file()}


def no_other_engine():
    out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, timeout=30).stdout
    names = ('unrealeditor.exe', 'unrealeditor-cmd.exe', 'mikdashcourtyardv3.exe', 'automationtool.exe')
    bad = [r[:2] for r in csv.reader(io.StringIO(out))
           if len(r) > 1 and r[0].lower() in names and int(r[1]) != os.getpid()]
    if bad:
        raise RuntimeError('Another engine/game process is running: %r' % bad)


def revert(receipt_path):
    no_other_engine()
    r = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
    ck = Path(r['checkpoint'])
    for pkg, orig in r['originalSha256'].items():
        if sha(ck / rel(pkg)) != orig:
            raise RuntimeError('Checkpoint bytes changed: ' + pkg)
    done = []
    for pkg, orig in r['originalSha256'].items():
        shutil.copy2(ck / rel(pkg), ROOT / rel(pkg))
        if sha(ROOT / rel(pkg)) != orig:
            raise RuntimeError('Revert readback mismatch: ' + pkg)
        done.append(pkg)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = OUT / ('sanctuary-v2-nanite-usage-revert-%s.json' % stamp)
    out.write_text(json.dumps({'status': 'reverted', 'applyReceipt': str(receipt_path), 'restored': done},
                              indent=2) + '\n', encoding='utf-8')
    print('reverted', done, '->', out)


def params(ml, inst):
    rec = {'scalar': {}, 'vector': {}, 'texture': {}}
    for n in sorted(str(x) for x in ml.get_scalar_parameter_names(inst)):
        rec['scalar'][n] = round(float(ml.get_material_instance_scalar_parameter_value(inst, n)), 6)
    for n in sorted(str(x) for x in ml.get_vector_parameter_names(inst)):
        c = ml.get_material_instance_vector_parameter_value(inst, n)
        rec['vector'][n] = [round(float(c.r), 6), round(float(c.g), 6), round(float(c.b), 6), round(float(c.a), 6)]
    for n in sorted(str(x) for x in ml.get_texture_parameter_names(inst)):
        t = ml.get_material_instance_texture_parameter_value(inst, n)
        rec['texture'][n] = t.get_path_name() if t else None
    return rec


def run(apply, verify):
    import unreal as u
    ml = u.MaterialEditingLibrary
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / ('sanctuary-v2-nanite-usage-%s-%s.json' % ('apply' if apply else 'verify', stamp))
    rep = {'status': 'started', 'processId': os.getpid(), 'errors': [], 'targets': list(TARGETS),
           'scope': ('Instance usage overrides on three MIs only. M_PBR_Tiled, maps and every other asset are '
                     'hash-guarded. Visual acceptance is a packaged frame, not this receipt.')}

    def write():
        out.write_text(json.dumps(rep, indent=2, default=str) + '\n', encoding='utf-8')

    write()
    before = None
    ar = None
    targets_rel = {rel(p) for p in TARGETS}
    try:
        if bool(apply) == bool(verify):
            raise RuntimeError('Choose apply or verify')
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        no_other_engine()
        if (u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                or u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):
            raise RuntimeError('Dirty packages before operation')
        before = content_hashes()
        for pkg, h in ANCHORS.items():
            if before.get(rel(pkg)) != h:
                raise RuntimeError('Protected anchor bytes differ from pin: ' + pkg)
        protected = {p: h for p, h in before.items() if p not in targets_rel}
        rep['protectedCount'] = len(protected)
        rep['protectedSha256OfSet'] = hashlib.sha256(json.dumps(protected, sort_keys=True).encode()).hexdigest()
        rep['anchorSha256'] = {pkg: before[rel(pkg)] for pkg in ANCHORS}
        rep['mapHashesBefore'] = {p: h for p, h in before.items() if p.endswith('.umap')}
        if verify:
            ar = json.loads(Path(verify).read_text(encoding='utf-8-sig'))
            if ar.get('status') != 'saved' or ar.get('errors') or ar.get('processId') in (None, os.getpid()):
                raise RuntimeError('Not a successful apply receipt from a distinct process')
            if ar['protectedSha256OfSet'] != rep['protectedSha256OfSet']:
                raise RuntimeError('Protected content changed since apply')
            for pkg in TARGETS:
                if before[rel(pkg)] != ar['savedSha256'][pkg]:
                    raise RuntimeError('Target bytes differ from apply receipt: ' + pkg)
            rep['applyReceipt'] = str(Path(verify).resolve())
        else:
            for pkg, h in TARGETS.items():
                if before.get(rel(pkg)) != h:
                    raise RuntimeError('Target bytes differ from pinned plan: ' + pkg)
            ck = CKPT_ROOT / ('SanctuaryV2NaniteUsage-' + stamp)
            ck.mkdir(parents=True, exist_ok=False)
            for pkg in TARGETS:
                d = ck / rel(pkg)
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel(pkg), d)
                if sha(d) != TARGETS[pkg]:
                    raise RuntimeError('Checkpoint mismatch ' + pkg)
            rep['checkpoint'] = str(ck)
            rep['originalSha256'] = dict(TARGETS)
            rep['revert'] = 'python Scripts/repair_sanctuary_v2_nanite_usage.py --revert <this receipt>  (no engine running)'
        write()
        src = u.load_asset(SOURCE)
        parent = u.load_asset(PARENT)
        usages = [n for n in dir(u.MaterialUsage) if n.startswith('MATUSAGE_') and n != 'MATUSAGE_MAX']
        src_over = {n: bool(ml.has_material_usage(src, getattr(u.MaterialUsage, n))) for n in usages
                    if ml.has_material_usage_override(src, getattr(u.MaterialUsage, n))}
        rep['sourceUsageOverrides'] = src_over
        rep['parentNaniteUsage'] = bool(ml.has_material_usage(parent, u.MaterialUsage.MATUSAGE_NANITE))
        if src_over.get('MATUSAGE_NANITE') is not True:
            raise RuntimeError('Source does not carry an explicit Nanite override; the premise is wrong')
        rep['instances'] = {}
        rep['savedSha256'] = {}
        for pkg in TARGETS:
            inst = u.load_asset(pkg)
            if not isinstance(inst, u.MaterialInstanceConstant):
                raise RuntimeError('Not a MaterialInstanceConstant: ' + pkg)
            if inst.get_editor_property('parent').get_path_name().split('.')[0] != PARENT:
                raise RuntimeError('Unexpected parent for ' + pkg)
            row = {'paramsBefore': params(ml, inst),
                   'naniteBefore': bool(ml.has_material_usage(inst, u.MaterialUsage.MATUSAGE_NANITE)),
                   'naniteOverrideBefore': bool(ml.has_material_usage_override(inst, u.MaterialUsage.MATUSAGE_NANITE))}
            if apply:
                for n, val in src_over.items():
                    ml.set_material_usage_override(inst, getattr(u.MaterialUsage, n), val, True)
            row['usageAfter'] = {n: bool(ml.has_material_usage(inst, getattr(u.MaterialUsage, n))) for n in src_over}
            row['overrideAfter'] = {n: bool(ml.has_material_usage_override(inst, getattr(u.MaterialUsage, n)))
                                    for n in src_over}
            row['paramsAfter'] = params(ml, inst)
            if row['usageAfter'] != src_over or not all(row['overrideAfter'].values()):
                raise RuntimeError('Usage readback differs from source overrides: ' + pkg)
            if row['paramsAfter'] != row['paramsBefore']:
                raise RuntimeError('Parameter parity broken: ' + pkg)
            if verify and row['paramsAfter'] != ar['instances'][pkg]['paramsAfter']:
                raise RuntimeError('Parameters differ from apply receipt: ' + pkg)
            if apply and not u.EditorAssetLibrary.save_loaded_asset(inst, only_if_is_dirty=False):
                raise RuntimeError('Save refused: ' + pkg)
            rep['savedSha256'][pkg] = sha(ROOT / rel(pkg))
            rep['instances'][pkg] = row
            write()
        rep['status'] = 'saved' if apply else 'fresh_verified'
    except Exception as exc:
        rep['status'] = 'failed'
        rep['errors'].append(repr(exc))
    finally:
        if before is not None:
            after = content_hashes()
            changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
            rep['changedFiles'] = changed
            rep['mapHashesAfter'] = {p: h for p, h in after.items() if p.endswith('.umap')}
            rep['allMapsUnchanged'] = rep['mapHashesAfter'] == rep.get('mapHashesBefore')
            rep['protectedContentUnchanged'] = all(p in targets_rel for p in changed)
            rep['anchorsAfter'] = {pkg: after.get(rel(pkg)) for pkg in ANCHORS}
            if (not rep['protectedContentUnchanged'] or not rep['allMapsUnchanged'] or (verify and changed)
                    or rep['anchorsAfter'] != ANCHORS):
                rep['status'] = 'failed'
                rep['errors'].append('Unexpected disk mutation')
        write()
        u.log('SANCTV2_NANITE_USAGE ' + rep['status'] + ' ' + str(out))


if __name__ == '__main__':
    try:
        import unreal
    except ImportError:
        if len(sys.argv) == 3 and sys.argv[1] == '--revert':
            revert(sys.argv[2])
        else:
            cur = {p: sha(ROOT / rel(p)) for p in list(TARGETS) + list(ANCHORS)}
            print(json.dumps({'targetsMatchPin': all(cur[p] == h for p, h in TARGETS.items()),
                              'anchorsMatchPin': all(cur[p] == h for p, h in ANCHORS.items())}, indent=2))
    else:
        cmd = unreal.SystemLibrary.get_command_line()
        m = re.search(r'-SanctV2NaniteVerify=(?:"([^"]+)"|(\S+))', cmd, re.I)
        run(apply='-sanctv2naniteapply' in cmd.lower(), verify=(m.group(1) or m.group(2)) if m else None)
