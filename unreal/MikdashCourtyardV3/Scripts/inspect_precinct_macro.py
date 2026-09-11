"""READ-ONLY inspection for the precinct retaining-face macro pass and the Heikhal ceiling card.

Loads the Candidate48 map and SAVES NOTHING. Writes one JSON receipt under
SourceAssets/enclosure-review/PrecinctMacroV1/inspect-<stamp>.json.

Commandlet (one engine process at a time):
  UnrealEditor-Cmd.exe <uproject> -run=pythonscript -unattended -nullrhi
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/inspect_precinct_macro.py"
"""
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

import unreal as u

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1'
MAP = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
ml = u.MaterialEditingLibrary
r = {'status': 'started', 'mode': 'inspect_read_only', 'map': MAP, 'errors': []}
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
receipt = OUT / ('inspect-%s.json' % stamp)


def P(o):
    try:
        return o.get_path_name().split('.')[0] if o else None
    except Exception:
        return str(o)


def v3(v):
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def mi_values(mi):
    d = {'path': P(mi), 'class': mi.get_class().get_name()}
    try:
        d['parent'] = P(mi.get_editor_property('parent'))
    except Exception:
        d['parent'] = None
    try:
        d['base'] = P(mi.get_base_material())
    except Exception:
        pass
    try:
        d['scalars'] = {str(n): ml.get_material_instance_scalar_parameter_value(mi, n) for n in ml.get_scalar_parameter_names(mi)}
        d['vectors'] = {}
        for n in ml.get_vector_parameter_names(mi):
            c = ml.get_material_instance_vector_parameter_value(mi, n)
            d['vectors'][str(n)] = [c.r, c.g, c.b, c.a]
        d['textures'] = {str(n): P(ml.get_material_instance_texture_parameter_value(mi, n)) for n in ml.get_texture_parameter_names(mi)}
    except Exception as e:
        d['paramError'] = repr(e)
    try:
        d['usage'] = {k: bool(ml.has_material_usage(mi, getattr(u.MaterialUsage, k)))
                      for k in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES')}
    except Exception as e:
        d['usageError'] = repr(e)
    return d


USAGE_PROPS = ('used_with_nanite', 'used_with_instanced_static_meshes', 'used_with_static_lighting',
               'used_with_skeletal_mesh', 'used_with_spline_meshes', 'used_with_morph_targets',
               'used_with_particle_sprites', 'used_with_mesh_particles', 'used_with_niagara_sprites',
               'used_with_niagara_meshes', 'used_with_geometry_cache', 'used_with_geometry_collections',
               'used_with_editor_compositing', 'used_with_clothing', 'used_with_water', 'used_with_hair_strands',
               'used_with_lidar_point_cloud', 'used_with_virtual_heightfield_mesh', 'used_with_beam_trails',
               'used_with_landscape')


def material_info(m):
    d = {'path': P(m)}
    for k in ('blend_mode', 'shading_model', 'two_sided', 'tangent_space_normal') + USAGE_PROPS:
        try:
            d[k] = str(m.get_editor_property(k))
        except Exception:
            pass
    try:
        d['numExpressions'] = ml.get_num_material_expressions(m)
    except Exception as e:
        d['numExpressionsError'] = repr(e)
    return d


def section(name, fn):
    try:
        r[name] = fn()
    except Exception:
        r['errors'].append({name: traceback.format_exc()})


def assets():
    out = {}
    for a in ('/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/MI_PrecinctPlaza_Ashlar',
              '/Game/MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_Ashlar'):
        out[a] = mi_values(u.load_asset(a))
    out['M_PBR_Tiled'] = material_info(u.load_asset('/Game/MikdashV3/Materials/PBR/M_PBR_Tiled'))
    reg = u.AssetRegistryHelpers.get_asset_registry()
    hits = [str(x.package_name) for x in reg.get_assets_by_path('/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1', True)
            if 'RetainingBand' in str(x.asset_name)]
    out['retainingBandSearch'] = hits
    for h in hits:
        m = u.load_asset(h)
        if isinstance(m, u.StaticMesh):
            b = m.get_bounds()
            out['retainingBand'] = {'path': P(m), 'nanite': bool(m.get_editor_property('nanite_settings').enabled),
                                    'boxExtent': v3(b.box_extent), 'origin': v3(b.origin),
                                    'materials': [P(s.material_interface) for s in m.get_editor_property('static_materials')]}
    t = u.load_asset('/Game/MikdashV3/MaterialReview/HerodianAshlarV4/Textures/T_HerodianV5b_Ashlar_Albedo')
    if t:
        out['T_HerodianV5b_Ashlar_Albedo'] = {k: str(t.get_editor_property(k)) for k in (
            'compression_settings', 'srgb', 'lod_group', 'address_x', 'address_y', 'filter',
            'mip_gen_settings', 'virtual_texture_streaming', 'never_stream')}
    ceiling = u.load_asset('/Game/MikdashV3/FX/Materials/MI_FX_Smoke_Ceiling')
    if ceiling is None:
        found = [str(x.package_name) for x in reg.get_assets_by_path('/Game/MikdashV3', True) if str(x.asset_name) == 'MI_FX_Smoke_Ceiling']
        out['smokeCeilingSearch'] = found
        ceiling = u.load_asset(found[0]) if found else None
    if ceiling is not None:
        out['MI_FX_Smoke_Ceiling'] = mi_values(ceiling)
        out['MI_FX_Smoke_Ceiling']['baseInfo'] = material_info(ceiling.get_base_material())
    return out


def transform_row(x):
    rot = x.rotation.rotator()
    return {'t': v3(x.translation), 'pyr': [round(rot.pitch, 2), round(rot.yaw, 2), round(rot.roll, 2)], 's': v3(x.scale3d)}


def world_scan():
    les = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not les.load_level(MAP):
        raise RuntimeError('load_level failed')
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    res = {'actorCount': len(actors), 'ceilingZone': [], 'heikhalTranslucent': [], 'fxDirector': [], 'enclosure': [],
           'serviceActors': []}
    zone = ((-6600, -2400), (-800, 800), (2200, 3100))
    heik = ((-6600, -2400), (-800, 800), (700, 3100))

    def inter(o, e, box):
        return all(o[i] + e[i] >= box[i][0] and o[i] - e[i] <= box[i][1] for i in range(3))

    for a in actors:
        try:
            label = a.get_actor_label()
            cls = a.get_class().get_name()
        except Exception:
            continue
        if 'FXDirector' in cls or 'FXDirector' in label:
            d = {'label': label, 'class': cls, 'location': v3(a.get_actor_location())}
            for k in ('heikhal_ceiling_z_cm', 'golden_altar_top_cm', 'smoke_ceiling_material', 'smoke_ketores_material',
                      'light_shaft_material', 'dust_mote_material', 'heat_haze_material', 'card_mesh',
                      'follow_service_actor', 'lamps_follow_service', 'effects_quality', 'shaft_transforms',
                      'heat_haze_cm', 'service_incense_cue', 'service_actor'):
                try:
                    val = a.get_editor_property(k)
                    if isinstance(val, u.Vector):
                        val = v3(val)
                    elif isinstance(val, u.Object):
                        val = P(val)
                    elif isinstance(val, (list, tuple, u.Array)):
                        val = [transform_row(x) if isinstance(x, u.Transform) else (v3(x) if isinstance(x, u.Vector) else str(x)) for x in val]
                    d[k] = val if isinstance(val, (int, float, bool, str, list, type(None))) else str(val)
                except Exception as e:
                    d[k + 'Error'] = repr(e)[:160]
            res['fxDirector'].append(d)
        if 'Enclosure' in cls:
            d = {'label': label, 'class': cls}
            for k in ('plaza_ashlar_material', 'plaza_retaining_band_mesh', 'wall_material'):
                try:
                    d[k] = P(a.get_editor_property(k))
                except Exception as e:
                    d[k + 'Error'] = repr(e)[:160]
            res['enclosure'].append(d)
        if 'Service' in cls:
            res['serviceActors'].append({'label': label, 'class': cls, 'location': v3(a.get_actor_location())})
        try:
            o, e = a.get_actor_bounds(False)
        except Exception:
            continue
        o = [o.x, o.y, o.z]
        e = [e.x, e.y, e.z]
        if max(e) > 20000:
            continue
        in_zone = inter(o, e, zone)
        in_heik = inter(o, e, heik)
        if not (in_zone or in_heik):
            continue
        comps = []
        translucent = False
        for c in a.get_components_by_class(u.PrimitiveComponent):
            cd = {'name': c.get_name(), 'class': c.get_class().get_name()}
            if isinstance(c, u.StaticMeshComponent):
                cd['mesh'] = P(c.static_mesh)
                mats = []
                for m in c.get_materials():
                    bm = None
                    try:
                        bm = str(m.get_base_material().get_editor_property('blend_mode')) if m else None
                    except Exception:
                        pass
                    if bm and 'OPAQUE' not in bm.upper() and 'MASKED' not in bm.upper():
                        translucent = True
                    mats.append([P(m), bm])
                cd['materials'] = mats
                try:
                    cd['visible'] = bool(c.get_editor_property('visible'))
                    cd['hiddenInGame'] = bool(c.get_editor_property('hidden_in_game'))
                except Exception:
                    pass
            comps.append(cd)
        entry = {'label': label, 'class': cls, 'origin': [round(x, 1) for x in o], 'extent': [round(x, 1) for x in e],
                 'components': comps[:12], 'translucent': translucent}
        try:
            entry['actorHiddenInGame'] = bool(a.get_editor_property('hidden'))
        except Exception:
            pass
        if in_zone and min(e) < 150:
            res['ceilingZone'].append(entry)
        if in_heik and translucent:
            res['heikhalTranslucent'].append(entry)
    return res


section('assets', assets)
section('world', world_scan)
r['status'] = 'ok' if not r['errors'] else 'partial'
r['finishedUtc'] = datetime.now(timezone.utc).isoformat()
OUT.mkdir(parents=True, exist_ok=True)
receipt.write_text(json.dumps(r, indent=1, default=str), encoding='utf-8')
print('INSPECT RECEIPT ' + str(receipt))
