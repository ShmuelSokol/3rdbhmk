"""Read-only editor mesh extraction against pinned packaged street contacts.

Run through run_crowd_street_ground_audit.ps1. No maps or assets are saved.
Source and render LOD0 are compared separately; neither is assumed to be the
collision mesh. A match is evidence, not automatic adoption of a ground model.
"""
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
from generate_kotel_retaining_wall import Terrain

CONTACTS = 'SourceAssets/perf-review/crowd-vat/crowd-sampler01-review.json'
CONTACT_SHA = '6009e6f9764d993ba28f8ca27e8b47f48b4618a369ee3b16c69114ca583965fa'
ACTORS = 'SourceAssets/birds-review/candidate-metric-birds-20260909T075232116207Z.json'
ACTOR_SHA = '1e1bfab5bf9813f671688f097322e46435324ab3e069f26d0176cba10e546f58'
NAMES = ('StaticMeshActor_2754', 'StaticMeshActor_4503')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned(name, digest):
    path = ROOT / name
    if sha(path) != digest:
        raise ValueError('Pinned evidence changed: ' + name)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def actor_records(value, out):
    if isinstance(value, str) and 'StaticMeshActor_2754' in value and value.lstrip().startswith(('{', '[')):
        actor_records(json.loads(value), out)
    elif isinstance(value, dict):
        for key, child in value.items():
            if key in NAMES:
                if key in out and out[key] != child:
                    raise ValueError('Conflicting actor snapshots: ' + key)
                out[key] = child
            else:
                actor_records(child, out)
    elif isinstance(value, list):
        for child in value:
            actor_records(child, out)


def extract(ue, mesh, lod_type):
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions()
    for key in ('apply_build_settings', 'request_tangents', 'use_build_scale'):
        options.set_editor_property(key, False)
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', lod_type)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
    if ue.GeometryScriptOutcomePins.SUCCESS not in result:
        raise RuntimeError('Mesh extraction failed: ' + str(lod_type))
    query = ue.GeometryScript_MeshQueries
    if query.get_has_triangle_id_gaps(dynamic):
        raise RuntimeError('Extraction needs explicit sparse triangle IDs')
    vertices, triangles = [], []
    for tid in range(dynamic.get_triangle_count()):
        positions = query.get_triangle_positions(dynamic, tid)
        vectors = [v for v in positions if isinstance(v, ue.Vector)]
        if True not in positions or len(vectors) != 3 or not all(math.isfinite(c) for v in vectors for c in (v.x, v.y, v.z)):
            raise RuntimeError('Invalid extracted triangle')
        start = len(vertices)
        vertices.extend([[v.x, v.y, v.z] for v in vectors])
        triangles.append([start, start+1, start+2])
    return dict(vertices=vertices, triangles=triangles)


def main():
    import unreal as ue
    contacts = [r for r in pinned(CONTACTS, CONTACT_SHA)['groundSamples'] if r['zone'] == 'StreetBateiMahase']
    actors = {}
    actor_records(pinned(ACTORS, ACTOR_SHA), actors)
    if len(contacts) != 32 or set(actors) != set(NAMES):
        raise ValueError('Incomplete reviewed street evidence')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'SourceAssets/perf-review/crowd-vat' / ('street-native-mesh-' + stamp + '.json')
    receipt = dict(status='running', contactSha256=CONTACT_SHA, actorSnapshotSha256=ACTOR_SHA,
                   scope='Read-only source/render LOD0 comparison against prior packaged contacts; no ground model adoption.', assets=[])
    try:
        for name in NAMES:
            row = actors[name]
            if row[3] != [0, 0, 0, 0, 0, 0, 1, 1, 1] or len(row[2]) != 1:
                raise ValueError('Expected reviewed identity actor transform')
            asset = row[2][0]
            asset_file = ROOT / ('Content/' + asset.removeprefix('/Game/') + '.uasset')
            before = sha(asset_file)
            mesh = ue.load_asset(asset)
            if not isinstance(mesh, ue.StaticMesh):
                raise ValueError('Not a static mesh: ' + asset)
            nanite = mesh.get_editor_property('nanite_settings')
            entry = dict(actor=name, asset=asset, assetSha256Before=before,
                         naniteEnabled=nanite.get_editor_property('enabled'),
                         naniteFallbackRelativeError=nanite.get_editor_property('fallback_relative_error'),
                         naniteFallbackPercentTriangles=nanite.get_editor_property('fallback_percent_triangles'),
                         collisionTraceFlag=str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
                         lodForCollision=mesh.get_editor_property('lod_for_collision'), geometry={}, samples=[])
            for key, mode in (('source', ue.GeometryScriptLODType.SOURCE_MODEL), ('render', ue.GeometryScriptLODType.RENDER_DATA)):
                entry['geometry'][key] = extract(ue, mesh, mode)
            surfaces = {key: Terrain(blob) for key, blob in entry['geometry'].items()}
            for contact in contacts:
                if contact['actor'].split('.')[-1] != name:
                    continue
                sample = dict(contact)
                for key, surface in surfaces.items():
                    height = surface.z(contact['x'], contact['y'])
                    sample[key+'Z'] = height
                    sample[key+'ResidualCm'] = None if height is None else contact['actual']-height
                entry['samples'].append(sample)
            entry['assetSha256After'] = sha(asset_file)
            if entry['assetSha256After'] != before:
                raise RuntimeError('Read-only audit changed asset bytes')
            receipt['assets'].append(entry)
        if sum(len(a['samples']) for a in receipt['assets']) != 32:
            raise ValueError('Not all contacts matched a reviewed actor')
        receipt['status'] = 'extracted-review-required'
    except Exception as error:
        receipt.update(status='failed', error=str(error))
        raise
    finally:
        with output.open('x', encoding='utf-8') as handle:
            json.dump(receipt, handle, indent=2)
            handle.write('\n')
        ue.log('Crowd street mesh audit: ' + str(output))


if __name__ == '__main__':
    main()
