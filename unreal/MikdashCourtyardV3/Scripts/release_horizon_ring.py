"""Guarded pass: place the HorizonRingV1 far-field terrain and move the SkyAtmosphere planet top
to 500 m below sea level (under the Dead Sea). Spec: Scripts/release_horizon_ring.spec.json. Geometry:
Scripts/generate_horizon_ring.py -> SourceAssets/horizon-review/HorizonRingV1.

Launch (hidden editor - the LOD build-settings call needs StaticMeshEditorSubsystem, which is
None in a -run=pythonscript commandlet):

  UnrealEditor.exe <uproject> -ExecutePythonScript=<this> -Candidate48 [-DryRun]
      -EnablePlugins=GeometryScripting -unattended -nosplash -nullrhi -abslog=<log>

  python Scripts/release_horizon_ring.py                  # offline check, no engine
  python Scripts/release_horizon_ring.py --revert=<receipt.json> [--dry-run]

Guard pattern (every mutation): refuse on a game world / dirty packages / an existing ring;
checkpoint the .umap into ReviewCheckpoints and hash it; hash every protected map; read every
value before it is written; winding and seam checked against the LIVE tiles before any asset is
created; save; byte-change check; reopen; numeric readback of every write; a whole-level
snapshot of every other actor must be identical; protected maps byte-identical; receipt.
"""
import array
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_targets as mt  # noqa: E402

ROOT = mt.ROOT
SPEC_PATH = ROOT / 'Scripts' / 'release_horizon_ring.spec.json'


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding='utf-8'))


def sha256_of(path):
    return mt.sha256_of(path)


def disk_path(asset_path, extension='uasset'):
    return mt.disk_path(asset_path, extension)


def load_ring(spec):
    folder = ROOT / spec['ringFolder']
    manifest = json.loads((folder / 'ring-manifest.json').read_text(encoding='utf-8'))
    data = (folder / manifest['buffers']).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != manifest['buffersSha256']:
        raise RuntimeError('ring-buffers.bin hashes %s, manifest says %s' % (digest, manifest['buffersSha256']))
    chunks = []
    for entry in manifest['chunks']:
        out = dict(entry)
        for label, code in (('positions', 'f'), ('normals', 'f'), ('colors', 'f'), ('indices', 'I')):
            arr = array.array(code)
            if arr.itemsize != 4:
                raise RuntimeError('array(%r) itemsize %d on this Python' % (code, arr.itemsize))
            start = entry[label + 'Offset']
            arr.frombytes(data[start:start + entry[label + 'Bytes']])
            out[label] = arr
        if len(out['positions']) != 3 * entry['vertices'] or len(out['indices']) != 3 * entry['triangles']:
            raise RuntimeError('chunk %s buffer sizes disagree with the manifest' % entry['name'])
        if max(out['indices']) >= entry['vertices']:
            raise RuntimeError('chunk %s indexes past its vertex buffer' % entry['name'])
        chunks.append(out)
    return manifest, chunks


def offline_check(spec=None):
    spec = spec or load_spec()
    manifest, chunks = load_ring(spec)
    report = {'specSha256': sha256_of(SPEC_PATH), 'manifestSha256': sha256_of(ROOT / spec['ringFolder'] / 'ring-manifest.json'),
              'buffersSha256': manifest['buffersSha256'], 'chunks': len(chunks),
              'vertices': sum(c['vertices'] for c in chunks), 'triangles': sum(c['triangles'] for c in chunks),
              'coverageSummary': manifest['coverage']['summary'], 'checks': []}

    def ok(name, cond, detail=''):
        report['checks'].append({'check': name, 'ok': bool(cond), 'detail': detail})
        if not cond:
            raise RuntimeError('offline check failed: %s %s' % (name, detail))

    ok('planet radius agrees', abs(manifest['planetRadiusMetres'] / 1000.0 - spec['atmosphere']['expectedBottomRadiusKm']) < 1e-6)
    ok('delta agrees with the planet top', abs(spec['atmosphere']['deltaKm'] * 100000.0 + spec['atmosphere']['planetTopZcm']) < 1e-6)
    # Height ABOVE THE SPHERE, not world Z: the ring carries the curvature drop d^2/2R (6.6 km at the
    # 289 km corner), so its lowest world-Z vertex says nothing. z + d^2/2R is the height above a
    # sphere whose top is at Z=0; it must clear the planet top by 20 m everywhere, or the ring there
    # is under the shell and UE shades it with the shell colour (frame cp21-P1, the Jordan rift).
    radius_cm = manifest['planetRadiusMetres'] * 100.0
    lowest_cm = min(min(c['positions'][3 * i + 2] + (c['positions'][3 * i] ** 2 + c['positions'][3 * i + 1] ** 2) / (2.0 * radius_cm)
                        for i in range(c['vertices'])) for c in chunks)
    ok('planet top 20 m below the lowest ring point above the sphere', spec['atmosphere']['planetTopZcm'] < lowest_cm - 2000.0,
       {'planetTopZcm': spec['atmosphere']['planetTopZcm'], 'lowestAboveSphereZcm': round(lowest_cm, 1)})
    ok('24 chunks', len(chunks) == 24, len(chunks))
    for name in ('temple-mount-ground', 'cp17b-P1-aerial'):
        row = [r for r in manifest['coverage']['cameras'] if r['camera'] == name][0]
        ok('no shell azimuth from ' + name, row['azimuthsWhereShellVisible'] == 0, row['azimuthsWhereShellVisible'])
    return report


def _vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def _path(obj):
    return obj.get_path_name().split('.')[0] if obj is not None else None


class Run(object):
    def __init__(self, ue, spec, target_key):
        self.ue = ue
        self.spec = spec
        self.config = mt.target_config(target_key)
        self.map = self.config['map']
        self.label = self.config['key']
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.sme = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
        self.receipt = {}
        self.receipt_path = None

    def write_receipt(self):
        if self.receipt_path is not None:
            self.receipt_path.write_text(json.dumps(self.receipt, indent=2), encoding='utf-8')

    def all_actors(self):
        return list(self.actors.get_all_level_actors())

    @staticmethod
    def mesh_of(actor):
        try:
            component = actor.get_editor_property('static_mesh_component')
        except Exception:  # noqa: BLE001
            component = None
        if component is None:
            return None, None
        return component, component.get_editor_property('static_mesh')

    def is_ring(self, actor):
        return self.ue.Name(self.spec['actors']['tag']) in list(actor.tags)

    # -- a whole-level snapshot of everything this pass must NOT touch ------------------------
    def snapshot(self, actors):
        edited = set(self.spec['atmosphere']['edited'])
        out = {}
        for actor in actors:
            if self.is_ring(actor) or actor.get_class().get_name() in edited:
                continue
            t = actor.get_actor_transform()
            r = t.rotation.rotator()
            _, mesh = self.mesh_of(actor)
            out[actor.get_path_name()] = [
                actor.get_actor_label(), actor.get_class().get_name(), _path(mesh),
                [round(v, 2) for v in _vec(t.translation)],
                [round(float(r.pitch), 3), round(float(r.yaw), 3), round(float(r.roll), 3)],
                [round(v, 4) for v in _vec(t.scale3d)]]
        return out

    # -- terrain tiles ----------------------------------------------------------------------
    def terrain_tiles(self, actors):
        t = self.spec['terrain']
        rows = []
        for actor in actors:
            component, mesh = self.mesh_of(actor)
            path = _path(mesh)
            if path and t['meshPathToken'] in path and t['meshNameToken'] in path:
                origin, extent = actor.get_actor_bounds(False)
                rows.append({'actor': actor, 'component': component, 'mesh': mesh, 'label': actor.get_actor_label(),
                             'meshPath': path, 'min': [round(a - b, 3) for a, b in zip(_vec(origin), _vec(extent))],
                             'max': [round(a + b, 3) for a, b in zip(_vec(origin), _vec(extent))]})
        return rows

    def tile_triangles(self, mesh):
        ue = self.ue
        dynamic = ue.DynamicMesh()
        options = ue.GeometryScriptCopyMeshFromAssetOptions()
        options.set_editor_property('apply_build_settings', False)
        options.set_editor_property('request_tangents', False)
        options.set_editor_property('use_build_scale', False)
        lod = ue.GeometryScriptMeshReadLOD()
        lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
        lod.set_editor_property('lod_index', 0)
        result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
        if ue.GeometryScriptOutcomePins.SUCCESS not in result:
            raise RuntimeError('copy_mesh_from_static_mesh_v2 failed for ' + _path(mesh))
        tris = []
        for tid in range(dynamic.get_triangle_count()):
            res = ue.GeometryScript_MeshQueries.get_triangle_positions(dynamic, tid)
            pts = [_vec(v) for v in res if isinstance(v, ue.Vector)]
            if len(pts) == 3:
                tris.append(pts)
        return tris

    def check_winding_and_seam(self, tiles, chunks):
        """Before any asset exists: which winding the live tiles use, and whether every live DEM
        edge vertex has a ring seam vertex exactly seamDropCm under it and a skirt top on it."""
        t = self.spec['terrain']
        edge = t['demEdgeCm']
        tol = t['edgeToleranceCm']

        def on_edge(p):
            return (abs(p[0] - edge['xMin']) < tol or abs(p[0] - edge['xMax']) < tol or
                    abs(p[1] - edge['yMin']) < tol or abs(p[1] - edge['yMax']) < tol)

        ring = {}
        for c in chunks:
            if c['zone'] != 'A':
                continue
            p = c['positions']
            for i in range(c['vertices']):
                x, y, z = p[3 * i], p[3 * i + 1], p[3 * i + 2]
                if on_edge((x, y)):
                    ring.setdefault((int(round(x)), int(round(y))), []).append(z)

        def ring_z(x, y):
            found = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    found += ring.get((int(round(x)) + dx, int(round(y)) + dy), [])
            return found

        positive = negative = 0
        seen = {}
        edge_tiles = 0
        for row in tiles:
            lo, hi = row['min'], row['max']
            touches = (lo[0] < edge['xMin'] + tol or hi[0] > edge['xMax'] - tol or
                       lo[1] < edge['yMin'] + tol or hi[1] > edge['yMax'] - tol)
            tris = self.tile_triangles(row['mesh']) if (touches or positive + negative == 0) else []
            if touches:
                edge_tiles += 1
            for a, b, c in tris:
                e1 = [b[k] - a[k] for k in range(3)]
                e2 = [c[k] - a[k] for k in range(3)]
                cz = e1[0] * e2[1] - e1[1] * e2[0]
                if cz > 0:
                    positive += 1
                elif cz < 0:
                    negative += 1
                if touches:
                    for p in (a, b, c):
                        if on_edge(p):
                            seen[(round(p[0], 1), round(p[1], 1))] = p[2]
        if positive and negative:
            raise RuntimeError('live terrain tiles disagree on winding: %d +z / %d -z' % (positive, negative))
        flip = negative > 0
        drop = t['seamDropCm']
        worst_seam = worst_skirt = 0.0
        missing = []
        for (x, y), z in seen.items():
            zs = ring_z(x, y)
            if not zs:
                missing.append([x, y])
                continue
            worst_seam = max(worst_seam, min(abs((z - drop) - v) for v in zs))
            worst_skirt = max(worst_skirt, min(abs(z - v) for v in zs))
        report = {'tileTrianglesPositiveZ': positive, 'tileTrianglesNegativeZ': negative,
                  'ringGeneratedWith': '+z (right-handed cross)', 'flipRingTriangles': flip,
                  'edgeTilesRead': edge_tiles, 'liveEdgeVertices': len(seen),
                  'edgeVerticesWithoutRingVertex': len(missing), 'missingSample': missing[:8],
                  'worstSeamErrorCm': round(worst_seam, 3), 'worstSkirtTopErrorCm': round(worst_skirt, 3),
                  'seamDropCm': drop}
        if len(seen) < 1024 or missing or worst_seam > t['seamToleranceCm'] or worst_skirt > t['seamToleranceCm']:
            raise RuntimeError('seam check failed: %s' % json.dumps(report))
        return report

    # -- assets -----------------------------------------------------------------------------
    def build_or_reuse_assets(self, manifest, chunks, material, flip, dry_run):
        ue = self.ue
        a = self.spec['assets']
        rows = []
        for c in chunks:
            path = '%s/%s' % (a['folder'], c['name'])
            row = {'asset': path, 'vertices': c['vertices'], 'triangles': c['triangles']}
            if self.assets.does_asset_exist(path):
                mesh = self.assets.load_asset(path)
                tag = ue.EditorAssetLibrary.get_metadata_tag(mesh, a['metadataTag'])
                if tag != manifest['buffersSha256']:
                    raise RuntimeError('%s exists but was built from %r, not %s; refusing to overwrite'
                                       % (path, tag, manifest['buffersSha256']))
                row['action'] = 'reused_verified_by_metadata_tag'
            elif dry_run:
                row['action'] = 'would_create'
                rows.append(row)
                continue
            else:
                p, n, col, idx = c['positions'], c['normals'], c['colors'], c['indices']
                nv = c['vertices']
                buffers = ue.GeometryScriptSimpleMeshBuffers()
                buffers.set_editor_property('vertices', [ue.Vector(p[3 * i], p[3 * i + 1], p[3 * i + 2]) for i in range(nv)])
                buffers.set_editor_property('normals', [ue.Vector(n[3 * i], n[3 * i + 1], n[3 * i + 2]) for i in range(nv)])
                buffers.set_editor_property('vertex_colors', [ue.LinearColor(col[4 * i], col[4 * i + 1], col[4 * i + 2], col[4 * i + 3]) for i in range(nv)])
                # metric UVs only so tangents are well defined; M_Context_Terrain is world-aligned
                buffers.set_editor_property('uv0', [ue.Vector2D(p[3 * i] / 100.0, p[3 * i + 1] / 100.0) for i in range(nv)])
                if flip:
                    tris = [ue.IntVector(idx[k], idx[k + 2], idx[k + 1]) for k in range(0, len(idx), 3)]
                else:
                    tris = [ue.IntVector(idx[k], idx[k + 1], idx[k + 2]) for k in range(0, len(idx), 3)]
                buffers.set_editor_property('triangles', tris)
                dynamic = ue.DynamicMesh()
                ue.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic, buffers)
                if dynamic.get_triangle_count() != c['triangles']:
                    raise RuntimeError('%s: dynamic mesh has %d triangles, expected %d'
                                       % (path, dynamic.get_triangle_count(), c['triangles']))
                options = ue.GeometryScriptCreateNewStaticMeshAssetOptions()
                for key, value in dict(enable_recompute_normals=False, enable_recompute_tangents=True,
                                       enable_nanite=bool(a['nanite']), enable_collision=False,
                                       use_original_vertex_order=True).items():
                    options.set_editor_property(key, value)
                result = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic, path, options)
                meshes = [v for v in result if isinstance(v, ue.StaticMesh)]
                if len(meshes) != 1 or ue.GeometryScriptOutcomePins.SUCCESS not in result:
                    raise RuntimeError('create_new_static_mesh_asset_from_mesh failed for ' + path)
                mesh = meshes[0]
                mesh.set_material(0, material)
                settings = self.sme.get_lod_build_settings(mesh, 0)
                settings.set_editor_property('distance_field_resolution_scale', 0.0)
                settings.set_editor_property('generate_lightmap_u_vs', False)
                self.sme.set_lod_build_settings(mesh, 0, settings)
                setup = mesh.get_editor_property('body_setup')
                if setup is not None:
                    setup.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
                ue.EditorAssetLibrary.set_metadata_tag(mesh, a['metadataTag'], manifest['buffersSha256'])
                if not self.assets.save_loaded_asset(mesh, False):
                    raise RuntimeError('save_loaded_asset failed for ' + path)
                row['action'] = 'created'
            # readback, for created and reused alike
            mesh = self.assets.load_asset(path)
            tris = self.tile_triangles(mesh)
            if len(tris) != c['triangles']:
                raise RuntimeError('%s reads back %d triangles, expected %d' % (path, len(tris), c['triangles']))
            e1 = [tris[0][1][k] - tris[0][0][k] for k in range(3)]
            e2 = [tris[0][2][k] - tris[0][0][k] for k in range(3)]
            cz = e1[0] * e2[1] - e1[1] * e2[0]
            row['firstTriangleCrossZSign'] = 1 if cz > 0 else -1
            mat = mesh.get_material(0)
            row['material'] = _path(mat)
            if row['material'] != _path(material):
                raise RuntimeError('%s material reads back %s' % (path, row['material']))
            settings = self.sme.get_lod_build_settings(mesh, 0)
            row['distanceFieldResolutionScale'] = float(settings.get_editor_property('distance_field_resolution_scale'))
            if row['distanceFieldResolutionScale'] != 0.0:
                raise RuntimeError('%s distance field scale reads back %r' % (path, row['distanceFieldResolutionScale']))
            row['nanite'] = bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
            box = mesh.get_bounding_box()
            row['boundsCm'] = _vec(box.min) + _vec(box.max)
            worst = max(abs(u - v) for u, v in zip(row['boundsCm'], c['boundsCm']))
            if worst > 5.0:
                raise RuntimeError('%s bounds %r disagree with the manifest %r' % (path, row['boundsCm'], c['boundsCm']))
            row['boundsErrorCm'] = round(worst, 3)
            rows.append(row)
        return rows

    # -- actors -----------------------------------------------------------------------------
    def place_actors(self, chunks):
        ue = self.ue
        s = self.spec
        placed = []
        for c in chunks:
            mesh = self.assets.load_asset('%s/%s' % (s['assets']['folder'], c['name']))
            actor = self.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(0, 0, 0), ue.Rotator(), transient=False)
            if actor is None:
                raise RuntimeError('spawn failed for ' + c['name'])
            label = s['actors']['labelPrefix'] + c['zone'] + '_' + c['octant']
            actor.set_actor_label(label)
            actor.set_folder_path(s['actors']['folder'])
            actor.set_editor_property('tags', [ue.Name(s['actors']['tag'])])
            component = actor.get_editor_property('static_mesh_component')
            component.set_mobility(ue.ComponentMobility.STATIC)
            component.set_static_mesh(mesh)
            component.set_collision_profile_name('NoCollision')
            component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
            flags = {}
            for prop, value in s['actors']['componentFlags'].items():
                try:
                    component.set_editor_property(prop, value)
                    flags[prop] = 'set'
                except Exception as error:  # noqa: BLE001
                    if prop in s['actors']['mandatoryFlags']:
                        raise
                    flags[prop] = 'unavailable: %s' % error
            placed.append({'label': label, 'mesh': _path(mesh), 'flags': flags})
        return placed

    def read_ring_actors(self, actors):
        s = self.spec
        rows = []
        for actor in actors:
            if not self.is_ring(actor):
                continue
            component, mesh = self.mesh_of(actor)
            row = {'label': actor.get_actor_label(), 'mesh': _path(mesh),
                   'material': _path(component.get_material(0)),
                   'collision': str(component.get_collision_enabled()),
                   'transform': _vec(actor.get_actor_location())}
            for prop in s['actors']['componentFlags']:
                try:
                    row[prop] = component.get_editor_property(prop)
                except Exception:  # noqa: BLE001
                    row[prop] = None
            rows.append(row)
        return sorted(rows, key=lambda r: r['label'])

    # -- atmosphere -------------------------------------------------------------------------
    def atmosphere(self, actors):
        found = {}
        for actor in actors:
            name = actor.get_class().get_name()
            if name in ('SkyAtmosphere', 'VolumetricCloud', 'MikdashTimeOfDay', 'MikdashWeather'):
                found.setdefault(name, []).append(actor)
        return found

    def read_atmosphere(self, found):
        ue = self.ue
        out = {}
        skies = found.get('SkyAtmosphere', [])
        if len(skies) != 1:
            raise RuntimeError('expected exactly one SkyAtmosphere, found %d' % len(skies))
        comp = skies[0].get_editor_property('sky_atmosphere_component')
        tent = comp.get_editor_property('other_tent_distribution')
        albedo = comp.get_editor_property('ground_albedo')
        out['sky'] = {'label': skies[0].get_actor_label(),
                      'transform_mode': str(comp.get_editor_property('transform_mode')),
                      'location': _vec(skies[0].get_actor_location()),
                      'bottom_radius': float(comp.get_editor_property('bottom_radius')),
                      'atmosphere_height': float(comp.get_editor_property('atmosphere_height')),
                      'rayleigh_exponential_distribution': float(comp.get_editor_property('rayleigh_exponential_distribution')),
                      'mie_exponential_distribution': float(comp.get_editor_property('mie_exponential_distribution')),
                      'rayleigh_scattering_scale': float(comp.get_editor_property('rayleigh_scattering_scale')),
                      'mie_scattering_scale': float(comp.get_editor_property('mie_scattering_scale')),
                      'mie_absorption_scale': float(comp.get_editor_property('mie_absorption_scale')),
                      'other_tent_tip_altitude': float(tent.get_editor_property('tip_altitude')),
                      'ground_albedo': [int(albedo.r), int(albedo.g), int(albedo.b)],
                      'aerial_pespective_view_distance_scale': float(comp.get_editor_property('aerial_pespective_view_distance_scale'))}
        clouds = found.get('VolumetricCloud', [])
        out['clouds'] = [{'label': c.get_actor_label(),
                          'layer_bottom_altitude': float(c.get_editor_property('volumetric_cloud_component').get_editor_property('layer_bottom_altitude')),
                          'layer_height': float(c.get_editor_property('volumetric_cloud_component').get_editor_property('layer_height'))}
                         for c in clouds]
        out['timeOfDay'] = []
        for tod in found.get('MikdashTimeOfDay', []):
            presets = tod.get_editor_property('presets')
            out['timeOfDay'].append({'label': tod.get_actor_label(), 'presetCount': len(presets),
                                     'drive_sky_atmosphere': bool(tod.get_editor_property('drive_sky_atmosphere')),
                                     'mie_scattering_scale': [float(p.get_editor_property('mie_scattering_scale')) for p in presets],
                                     'aerial_perspective_view_distance_scale': [float(p.get_editor_property('aerial_perspective_view_distance_scale')) for p in presets]})
        out['weatherActors'] = [w.get_actor_label() for w in found.get('MikdashWeather', [])]
        return out

    def plan_atmosphere(self, before):
        a = self.spec['atmosphere']
        sky = before['sky']
        if not sky['transform_mode'].endswith(a['expectedTransformModeBefore'] + ': 0>') and a['expectedTransformModeBefore'] not in sky['transform_mode']:
            raise RuntimeError('SkyAtmosphere transform mode is %s, expected %s; refusing (already applied?)'
                               % (sky['transform_mode'], a['expectedTransformModeBefore']))
        if abs(sky['bottom_radius'] - a['expectedBottomRadiusKm']) > 0.5:
            raise RuntimeError('bottom_radius %.3f km; the ring curvature was baked for %.1f'
                               % (sky['bottom_radius'], a['expectedBottomRadiusKm']))
        d = a['deltaKm']
        f_r = math.exp(d / sky['rayleigh_exponential_distribution'])
        f_m = math.exp(d / sky['mie_exponential_distribution'])
        plan = {'deltaKm': d, 'rayleighFactor': f_r, 'mieFactor': f_m,
                'sky': {'transform_mode': a['transformModeAfter'], 'location': [0.0, 0.0, a['planetTopZcm']],
                        'rayleigh_scattering_scale': sky['rayleigh_scattering_scale'] * f_r,
                        'mie_scattering_scale': sky['mie_scattering_scale'] * f_m,
                        'mie_absorption_scale': sky['mie_absorption_scale'] * f_m,
                        'other_tent_tip_altitude': sky['other_tent_tip_altitude'] + d,
                        'ground_albedo': list(a['groundAlbedoRevertTo'])},
                'clouds': [{'label': c['label'], 'layer_bottom_altitude': c['layer_bottom_altitude'] + d} for c in before['clouds']],
                'timeOfDay': [{'label': t['label'], 'mie_scattering_scale': [v * f_m for v in t['mie_scattering_scale']]}
                              for t in before['timeOfDay']]}
        return plan

    def apply_atmosphere(self, found, plan):
        ue = self.ue
        sky_actor = found['SkyAtmosphere'][0]
        comp = sky_actor.get_editor_property('sky_atmosphere_component')
        sky_actor.modify()
        comp.modify()
        p = plan['sky']
        comp.set_editor_property('transform_mode', getattr(ue.SkyAtmosphereTransformMode, p['transform_mode']))
        sky_actor.set_actor_location(ue.Vector(*p['location']), False, False)
        for prop in ('rayleigh_scattering_scale', 'mie_scattering_scale', 'mie_absorption_scale'):
            comp.set_editor_property(prop, float(p[prop]))
        tent = comp.get_editor_property('other_tent_distribution')
        tent.set_editor_property('tip_altitude', float(p['other_tent_tip_altitude']))
        comp.set_editor_property('other_tent_distribution', tent)
        colour = ue.Color()
        # named fields: unreal.Color's positional constructor is B, G, R, A (frame-defect trap 7)
        colour.set_editor_property('r', int(p['ground_albedo'][0]))
        colour.set_editor_property('g', int(p['ground_albedo'][1]))
        colour.set_editor_property('b', int(p['ground_albedo'][2]))
        colour.set_editor_property('a', 255)
        comp.set_editor_property('ground_albedo', colour)
        for actor, want in zip(found.get('VolumetricCloud', []), plan['clouds']):
            actor.modify()
            cc = actor.get_editor_property('volumetric_cloud_component')
            cc.modify()
            cc.set_editor_property('layer_bottom_altitude', float(want['layer_bottom_altitude']))
        for actor, want in zip(found.get('MikdashTimeOfDay', []), plan['timeOfDay']):
            actor.modify()
            # UE Python struct-array trap: iterating an unreal.Array of structs yields COPIES, so
            # `for preset in presets: preset.set_editor_property(...)` changed nothing and the
            # before-save readback refused the first apply. Take each element by index, edit that
            # copy, collect, and assign the whole new list back.
            presets = actor.get_editor_property('presets')
            rebuilt = []
            for i in range(len(presets)):
                preset = presets[i]
                if i < len(want['mie_scattering_scale']):
                    preset.set_editor_property('mie_scattering_scale', float(want['mie_scattering_scale'][i]))
                rebuilt.append(preset)
            actor.set_editor_property('presets', rebuilt)

    def verify_atmosphere(self, after, plan):
        errors = []

        def close(name, got, want, tol):
            if abs(got - want) > tol:
                errors.append('%s read back %r, planned %r' % (name, got, want))

        sky, p = after['sky'], plan['sky']
        if p['transform_mode'] not in sky['transform_mode']:
            errors.append('transform_mode read back %s' % sky['transform_mode'])
        for k in range(3):
            close('sky location[%d]' % k, sky['location'][k], p['location'][k], 0.01)
        for prop in ('rayleigh_scattering_scale', 'mie_scattering_scale', 'mie_absorption_scale'):
            close(prop, sky[prop], p[prop], max(1e-7, abs(p[prop]) * 1e-5))
        close('other_tent_tip_altitude', sky['other_tent_tip_altitude'], p['other_tent_tip_altitude'], 1e-4)
        if sky['ground_albedo'] != p['ground_albedo']:
            errors.append('ground_albedo read back %r' % sky['ground_albedo'])
        for got, want in zip(after['clouds'], plan['clouds']):
            close('cloud layer_bottom_altitude', got['layer_bottom_altitude'], want['layer_bottom_altitude'], 1e-4)
        for got, want in zip(after['timeOfDay'], plan['timeOfDay']):
            for i, (g, w) in enumerate(zip(got['mie_scattering_scale'], want['mie_scattering_scale'])):
                close('ToD preset %d mie' % i, g, w, max(1e-7, abs(w) * 1e-5))
        if errors:
            raise RuntimeError('atmosphere readback: ' + '; '.join(errors))
        return 'all planned atmosphere values read back within tolerance'


def run(target_key, dry_run=False):
    import unreal as ue
    spec = load_spec()
    offline = offline_check(spec)
    manifest, chunks = load_ring(spec)

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    for name in ('GeometryScript_MeshEdits', 'GeometryScript_NewAssetUtils', 'GeometryScript_AssetUtils', 'GeometryScript_MeshQueries'):
        if not hasattr(ue, name):
            raise RuntimeError('Launch with -EnablePlugins=GeometryScripting: missing ' + name)
    session = Run(ue, spec, target_key)
    if session.sme is None:
        raise RuntimeError('StaticMeshEditorSubsystem is None: use the hidden-editor recipe, not a commandlet')
    if session.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if not session.levels.load_level(session.map):
        raise RuntimeError('load_level failed for ' + session.map)
    loaded = session.editor.get_editor_world().get_outermost().get_name()
    if loaded != session.map:
        raise RuntimeError('Loaded world %s is not %s' % (loaded, session.map))
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Dirty packages present; resolve before a checkpointed pass')

    map_file = disk_path(session.map, 'umap')
    map_sha_before = sha256_of(map_file)
    protected_paths = list(spec['protectedMaps']) + [
        c['map'] for c in mt.TARGETS.values() if c['map'] != session.map]
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in protected_paths if disk_path(m, 'umap').exists()}

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + session.label + '-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / session.map[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / session.map[6:])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    session.receipt_path = receipt_folder / (spec['receiptPrefix'] + session.label + '-' + stamp + '.json')
    session.receipt = {
        'status': 'horizon_ring_pass_started', 'stamp': stamp, 'target': session.label,
        'targetRole': session.config['role'], 'map': session.map, 'mapFile': str(map_file),
        'mapSha256Before': map_sha_before, 'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied, 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'offlineCheck': offline,
        'ringManifest': str(ROOT / spec['ringFolder'] / 'ring-manifest.json'),
        'ringBuffersSha256': manifest['buffersSha256'], 'ringTotals': manifest['totals'],
        'coverage': manifest['coverage']['summary'],
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'dryRun': bool(dry_run),
        'acceptance': spec['acceptance'], 'errors': [], 'mapSaved': False,
    }
    session.write_receipt()

    saved = False
    try:
        actors = session.all_actors()
        session.receipt['levelActorCount'] = len(actors)
        existing = [a.get_actor_label() for a in actors if session.is_ring(a)]
        if existing:
            raise RuntimeError('A HorizonRingV1 actor is already on this map: %s' % existing[:4])
        snap_before = session.snapshot(actors)
        tiles = session.terrain_tiles(actors)
        # The 256-tile square is NOT 256 JerusalemContext meshes on every map: interior tiles have
        # been swapped for cut twins that live in other folders (FutureMountV1/Terrain, the precinct
        # cut). A first dry run found 252 here and refused. Count every SM_JerusalemTerrain_ mesh in
        # any folder for the census; the seam check (>= 1,024 live DEM-edge vertices, all original
        # edge tiles) is the guard that actually matters for this pass.
        token = spec['terrain']['meshNameToken']
        any_folder = []
        for actor in actors:
            _, mesh = session.mesh_of(actor)
            path = _path(mesh)
            if path and token in path:
                any_folder.append(path)
        session.receipt['terrainTiles'] = {'jerusalemContextCount': len(tiles),
                                           'anyFolderCount': len(any_folder),
                                           'otherFolders': sorted(set(p.rsplit('/', 1)[0] for p in any_folder
                                                                      if spec['terrain']['meshPathToken'] not in p))}
        if len(any_folder) < 256 or len(tiles) < 240:
            raise RuntimeError('terrain census: %d JerusalemContext tiles, %d SM_JerusalemTerrain_ meshes in any folder'
                               % (len(tiles), len(any_folder)))
        materials = sorted(set(_path(r['component'].get_material(0)) for r in tiles))
        session.receipt['terrainTiles']['materials'] = materials
        want_mat = spec['terrain']['expectedMaterial']
        edge_mat = [r['component'].get_material(0) for r in tiles if _path(r['component'].get_material(0)) == want_mat]
        if not edge_mat:
            raise RuntimeError('no tile carries %s (found %s)' % (want_mat, materials))
        material = edge_mat[0]
        session.receipt['terrainTiles']['nanite'] = sorted(set(
            bool(r['mesh'].get_editor_property('nanite_settings').get_editor_property('enabled')) for r in tiles))
        session.receipt['seam'] = session.check_winding_and_seam(tiles, chunks)
        session.write_receipt()

        found = session.atmosphere(actors)
        atmo_before = session.read_atmosphere(found)
        plan = session.plan_atmosphere(atmo_before)
        session.receipt['atmosphere'] = {'why': spec['atmosphere']['why'],
                                         'densityCompensation': spec['atmosphere']['densityCompensation'],
                                         'cloudCompensation': spec['atmosphere']['cloudCompensation'],
                                         'timeOfDayCompensation': spec['atmosphere']['timeOfDayCompensation'],
                                         'aerialPerspectiveNote': spec['atmosphere']['aerialPerspectiveNote'],
                                         'before': atmo_before, 'plan': plan}
        session.receipt['assets'] = session.build_or_reuse_assets(manifest, chunks, material,
                                                                  session.receipt['seam']['flipRingTriangles'], dry_run)
        session.write_receipt()

        if dry_run:
            session.receipt['status'] = 'dry_run_measured_nothing_written'
            session.receipt['mapSha256After'] = sha256_of(map_file)
            if session.receipt['mapSha256After'] != map_sha_before:
                raise RuntimeError('Dry run changed the map on disk')
            return session.receipt

        session.receipt['placed'] = session.place_actors(chunks)
        session.apply_atmosphere(found, plan)
        session.receipt['atmosphere']['afterWrite'] = session.read_atmosphere(session.atmosphere(session.all_actors()))
        session.verify_atmosphere(session.receipt['atmosphere']['afterWrite'], plan)
        session.write_receipt()

        if not session.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        session.receipt['mapSaved'] = True
        session.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        if session.receipt['mapSha256AfterSave'] == map_sha_before:
            raise RuntimeError('save_current_level reported success but the .umap is byte-identical')
        if not session.levels.load_level(session.map):
            raise RuntimeError('Reopen failed for ' + session.map)

        reopened = session.all_actors()
        ring = session.read_ring_actors(reopened)
        session.receipt['reopenedRing'] = ring
        if len(ring) != len(chunks):
            raise RuntimeError('reopen found %d ring actors, expected %d' % (len(ring), len(chunks)))
        for row in ring:
            if row['cast_shadow'] is not False or row['never_distance_cull'] is not True:
                raise RuntimeError('%s flags read back %r' % (row['label'], row))
            if 'NO_COLLISION' not in row['collision'].upper():
                raise RuntimeError('%s collision reads back %s' % (row['label'], row['collision']))
            if row['material'] != want_mat or max(abs(v) for v in row['transform']) > 0.001:
                raise RuntimeError('%s reads back %r' % (row['label'], row))
        atmo_after = session.read_atmosphere(session.atmosphere(reopened))
        session.receipt['atmosphere']['afterReopen'] = atmo_after
        session.receipt['atmosphere']['readback'] = session.verify_atmosphere(atmo_after, plan)

        snap_after = session.snapshot(reopened)
        changed = [k for k in snap_before if snap_after.get(k) != snap_before[k]]
        added = [k for k in snap_after if k not in snap_before]
        session.receipt['untouched'] = {'actorsCompared': len(snap_before), 'changed': len(changed),
                                        'changedSample': [[k, snap_before[k], snap_after.get(k)] for k in changed[:6]],
                                        'addedOtherThanRing': added[:6]}
        if changed or added:
            raise RuntimeError('actors outside this pass changed on reopen: %d changed, %d added' % (len(changed), len(added)))
        tiles_after = session.terrain_tiles(reopened)
        a_fp = {r['label']: {'min': r['min'], 'max': r['max']} for r in tiles}
        b_fp = {r['label']: {'min': r['min'], 'max': r['max']} for r in tiles_after}
        session.receipt['terrainFingerprint'] = mt.compare_fingerprints(a_fp, b_fp)
        if session.receipt['terrainFingerprint']['worstBoundsErrorCm'] > 0.01 or len(a_fp) != len(b_fp):
            raise RuntimeError('terrain tiles moved: %r' % session.receipt['terrainFingerprint'])

        session.receipt['mapSha256After'] = sha256_of(map_file)
        unchanged = {m: sha256_of(disk_path(m, 'umap')) == sha for m, sha in protected.items()}
        session.receipt['protectedMapsUnchanged'] = unchanged
        if not all(unchanged.values()):
            raise RuntimeError('A protected map changed: %s' % [m for m, ok in unchanged.items() if not ok])
        session.receipt['status'] = 'horizon_ring_applied_saved_reopened_frame_acceptance_pending'
        return session.receipt
    except Exception as error:  # noqa: BLE001
        session.receipt['errors'].append('%s: %s' % (type(error).__name__, error))
        session.receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                                     else 'failed_before_save_map_unchanged')
        raise
    finally:
        session.write_receipt()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _flag(name):
    tokens = [t.lower().strip('"') for t in sys.argv]
    try:
        import unreal as ue
        tokens += [t.lower().strip('"') for t in ue.SystemLibrary.get_command_line().split()]
    except Exception:  # noqa: BLE001
        pass
    return ('-' + name.lower()) in tokens or ('--' + name.lower()) in tokens


def _main():
    action = mt.revert_from_command_line()
    if action:
        print(json.dumps(mt.restore_checkpoint(action['receipt'], dry_run=action['dryRun']), indent=2))
        return
    if not _unreal_available():
        print(json.dumps(offline_check(), indent=2))
        return
    import unreal as ue
    target = mt.target_from_command_line()
    try:
        receipt = run(target, dry_run=_flag('DryRun'))
        print('STATUS ' + receipt['status'])
    except Exception as error:  # noqa: BLE001
        print('FAILED %s: %s' % (type(error).__name__, error))
    finally:
        ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    _main()
