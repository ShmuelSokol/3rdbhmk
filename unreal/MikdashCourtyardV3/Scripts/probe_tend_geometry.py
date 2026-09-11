"""READ-ONLY geometry probe for the kohen lamp-tending clip. Saves nothing.

Measures, on Candidate48 then Main50, in the editor world:
  * the kohen actor's station anchors and pacing properties;
  * the FX director's seven lamp flame/light anchors (the flames he must reach);
  * every actor whose label or mesh names the menorah or the step stone, with bounds;
  * a line-trace profile of the three-step stone along the facing axis at three lamp Ys,
    so the top tread's real extent (where his feet can go) is known, not assumed;
  * vertical traces over each lamp to find the bowl top;
  * the V3 Man_Standard reference pose in component space (shoulder, pelvis, hand).
Receipt: SourceAssets/service-review/tend-geometry-probe-<stamp>.json

Launch (hidden editor, one engine at a time):
  UnrealEditor.exe <uproject> -ExecutePythonScript=C:/.../Scripts/probe_tend_geometry.py
      -unattended -nullrhi -NoSplash -abslog=<unique>
"""
import json, sys, traceback
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/service-review'
MAPS = [('Candidate48', '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
         'RELEASE_KohenGadolService_Selected48_V1'),
        ('Main50', '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough', 'RELEASE_KohenGadolService')]
BODY = ('/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/V3_Pilgrim_Man_Standard/'
        'SkeletalMeshes/V3_Pilgrim_Man_Standard.V3_Pilgrim_Man_Standard')
KOHEN_PROPS = ('tending_stone_point', 'menorah_point', 'doorway_point', 'ulam_approach_point',
               'golden_altar_point', 'per_lamp_seconds', 'approach_seconds', 'doorway_seconds',
               'stone_seconds', 'kuz_seconds', 'withdraw_seconds', 'altar_seconds',
               'walk_speed_cm_per_sec', 'repeat_interval_seconds', 'use_grounded_movement',
               'start_on_begin_play', 'sequence_enabled', 'idle_animation', 'walk_animation',
               'configured_mesh', 'configured_body_yaw_degrees')
BONES = ('root', 'pelvis', 'spine_01', 'spine_02', 'chest', 'neck_01', 'head', 'clavicle_r',
         'upperarm_r', 'lowerarm_r', 'hand_r', 'clavicle_l', 'upperarm_l', 'hand_l',
         'thigh_r', 'calf_r', 'foot_r', 'ball_r', 'foot_l', 'ball_l')
KEYS = ('menorah', 'stepstone', 'step_stone', 'stonestep', 'threestep', 'tendingstone', 'kuz')


def vec(v):
    try:
        return [round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]
    except Exception:                                                    # noqa: BLE001
        return None


def plain(v):
    if v is None:
        return None
    if hasattr(v, 'get_path_name'):
        return v.get_path_name()
    if hasattr(v, 'x') and hasattr(v, 'z'):
        return vec(v)
    if isinstance(v, (bool, int, float, str)):
        return v
    try:
        return [plain(x) for x in list(v)]
    except Exception:                                                    # noqa: BLE001
        return str(v)


def trace(ue, world, start, end):
    try:
        hit = ue.SystemLibrary.line_trace_single(
            world, ue.Vector(*start), ue.Vector(*end), ue.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True, [], ue.DrawDebugTrace.NONE, True)
    except Exception as error:                                           # noqa: BLE001
        return {'error': str(error)[:160]}
    if hit is None:
        return None
    t = hit.to_tuple()
    if not t[0]:
        return None
    actor, comp = t[9], t[10]
    return {'z': round(float(t[5].z), 2), 'x': round(float(t[5].x), 2), 'y': round(float(t[5].y), 2),
            'normalZ': round(float(t[7].z), 3),
            'actor': actor.get_actor_label() if actor else None,
            'component': comp.get_name() if comp else None}


def comp_rows(ue, actor):
    rows = []
    for comp in actor.get_components_by_class(ue.StaticMeshComponent):
        row = {'name': comp.get_name()}
        try:
            mesh = comp.get_editor_property('static_mesh')
            row['mesh'] = mesh.get_path_name() if mesh else None
        except Exception:                                                # noqa: BLE001
            pass
        try:
            lo, hi = comp.get_local_bounds()
            xf = comp.get_world_transform()
            corners = [ue.MathLibrary.transform_location(xf, ue.Vector(x, y, z))
                       for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
            row['worldMin'] = [round(min(c.x for c in corners), 2), round(min(c.y for c in corners), 2),
                               round(min(c.z for c in corners), 2)]
            row['worldMax'] = [round(max(c.x for c in corners), 2), round(max(c.y for c in corners), 2),
                               round(max(c.z for c in corners), 2)]
            row['collision'] = str(comp.get_collision_enabled())
        except Exception as error:                                       # noqa: BLE001
            row['boundsError'] = str(error)[:160]
        rows.append(row)
    return rows


def probe_map(ue, key, path, label):
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if editor.get_editor_world().get_outermost().get_name() != path and not levels.load_level(path):
        raise RuntimeError('load failed ' + path)
    world = editor.get_editor_world()
    out = {'map': path}
    everything = actors.get_all_level_actors()
    kohen = [a for a in everything if a.get_actor_label() == label]
    if len(kohen) != 1:
        raise RuntimeError('kohen %s count %d' % (label, len(kohen)))
    kohen = kohen[0]
    props = {}
    for p in KOHEN_PROPS:
        try:
            props[p] = plain(kohen.get_editor_property(p))
        except Exception as error:                                       # noqa: BLE001
            props[p] = 'unavailable: ' + str(error)[:80]
    out['kohen'] = {'label': label, 'location': vec(kohen.get_actor_location()), 'props': props}
    out['fxDirectors'] = []
    for a in everything:
        if a.get_class().get_name() != 'MikdashFXDirector':
            continue
        row = {'label': a.get_actor_label(), 'location': vec(a.get_actor_location())}
        for p in ('lamp_flame_cm', 'lamp_light_cm', 'follow_service_actor', 'effects_quality'):
            try:
                row[p] = plain(a.get_editor_property(p))
            except Exception as error:                                   # noqa: BLE001
                row[p] = 'unavailable: ' + str(error)[:80]
        out['fxDirectors'].append(row)
    near = []
    for a in everything:
        lab = a.get_actor_label()
        rows = comp_rows(ue, a)
        text = (lab + ' ' + ' '.join(r.get('mesh') or '' for r in rows)).lower().replace(' ', '')
        if any(k in text for k in KEYS):
            o, e = a.get_actor_bounds(False)
            rot = a.get_actor_rotation()
            near.append({'label': lab, 'class': a.get_class().get_name(),
                         'location': vec(a.get_actor_location()),
                         'rotation': [round(rot.roll, 3), round(rot.pitch, 3), round(rot.yaw, 3)],
                         'scale': vec(a.get_actor_scale3d()),
                         'boundsMin': [round(o.x - e.x, 2), round(o.y - e.y, 2), round(o.z - e.z, 2)],
                         'boundsMax': [round(o.x + e.x, 2), round(o.y + e.y, 2), round(o.z + e.z, 2)],
                         'components': rows})
    out['menorahAndStone'] = near
    flames = out['fxDirectors'][0].get('lamp_flame_cm') if out['fxDirectors'] else None
    out['frameNote'] = ('kohen properties are LEGACY-50 anchors decoded once at runtime; '
                        'traces below are in the map world frame')
    profiles = {}
    if isinstance(flames, list) and flames and isinstance(flames[0], list):
        ys = sorted({round(f[1], 1) for f in flames})
        mid_x = sum(f[0] for f in flames) / len(flames)
        for y in (ys[0], ys[len(ys) // 2], ys[-1]):
            rows = []
            x = mid_x - 60.0
            while x <= mid_x + 200.0:
                rows.append(dict(xq=round(x, 1), hit=trace(ue, world, (x, y, 1400.0), (x, y, 700.0))))
                x += 2.0
            profiles['y=%.1f' % y] = rows
        for dx in (60.0, 90.0, 120.0):
            rows = []
            y = ys[0] - 80.0
            while y <= ys[-1] + 80.0:
                rows.append(dict(yq=round(y, 1), hit=trace(ue, world, (mid_x + dx, y, 1400.0),
                                                           (mid_x + dx, y, 700.0))))
                y += 4.0
            profiles['x=lamps+%d' % dx] = rows
        out['lampTopTraces'] = [dict(flame=f, down=trace(ue, world, (f[0], f[1], f[2] + 40.0),
                                                         (f[0], f[1], f[2] - 60.0))) for f in flames]
        out['floorEastOfLamps'] = trace(ue, world, (mid_x + 250.0, ys[len(ys) // 2], 1400.0),
                                        (mid_x + 250.0, ys[len(ys) // 2], 600.0))
    out['stoneProfiles'] = profiles
    return out


def probe_skeleton(ue):
    mesh = ue.load_asset(BODY)
    skel = mesh.get_editor_property('skeleton')
    pose = ue.AnimPoseExtensions.get_reference_pose(skel)
    names = [str(n) for n in ue.AnimPoseExtensions.get_bone_names(pose)]
    rows = {}
    for b in BONES:
        if b in names:
            xf = ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.WORLD)
            rows[b] = vec(xf.translation)
    return {'mesh': BODY, 'skeleton': skel.get_path_name(), 'boneCount': len(names),
            'boneSet': sorted(names), 'componentSpaceCm': rows}


def main():
    import unreal as ue
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = OUT / ('tend-geometry-probe-%s.json' % stamp)
    r = {'status': 'running', 'readOnly': True, 'stamp': stamp, 'maps': {}, 'errors': []}
    try:
        r['skeleton'] = probe_skeleton(ue)
        for key, mp, label in MAPS:
            try:
                r['maps'][key] = probe_map(ue, key, mp, label)
            except Exception:                                            # noqa: BLE001
                r['errors'].append({key: traceback.format_exc()})
            path.write_text(json.dumps(r, indent=1, default=str), encoding='utf-8')
        dirty = list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + \
            list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        r['dirtyPackagesAtEnd'] = [p.get_name() for p in dirty]
        r['status'] = 'done' if not r['errors'] else 'done_with_errors'
    except Exception:                                                    # noqa: BLE001
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
    finally:
        path.write_text(json.dumps(r, indent=1, default=str), encoding='utf-8')
        ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    main()
