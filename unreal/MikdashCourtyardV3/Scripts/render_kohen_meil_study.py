"""Offline rest/walk silhouette comparison; native material review remains owed."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from measure_pilgrim_walk import read_glb, read_accessor, author
from render_face_v5 import render
from build_kohen_neck_tone_study import SOURCE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenMeilEaseV2'


def run(label, time=None, yaw=.65, source=None, output_dir=None, clip_name='walk', head_closeup=False):
    if not np.isfinite(yaw) or (time is not None and not np.isfinite(time)):
        raise ValueError('Pose time and yaw must be finite')
    if clip_name not in ('walk', 'tend', 'idle'):
        raise ValueError('Unknown animation clip')
    if (source is None) != (output_dir is None):
        raise ValueError('Custom source and output directory must be supplied together')
    folder = Path(output_dir) if output_dir is not None else OUT
    paths = {'before': SOURCE, 'candidate': OUT / 'SK_KohenGadol_MeilEase5_Study.glb',
             'layered-candidate': OUT / 'SK_KohenGadol_MeilEase5_LayeredStudy.glb'}
    for label, path in ((label, Path(source) if source is not None else paths[label]),):
        path = path.resolve()
        # Receipts use project-relative provenance. Reject external inputs before
        # rendering, so a path error cannot leave a PNG without its receipt.
        relative_source = path.relative_to(ROOT).as_posix()
        suffix = '' if time is None else '-%s-%dus-yaw%d' % (clip_name, round(time * 1e6), round(yaw * 1000))
        if head_closeup:
            suffix += '-head-yaw%d' % round(yaw * 1000)
        destination = folder / ('silhouette-' + label + suffix + '-offline.png')
        if destination.exists() or destination.with_suffix('.json').exists():
            raise FileExistsError('Fresh preview output required')
        doc, binary = read_glb(path)
        pose = None
        if time is not None:
            import measure_kohen_garment_clearance as M
            clip = next(c for c in M.CLIPS if c[0] == clip_name)
            rig = M.Rig(clip[1], clip[2])
            if not np.isfinite(time) or not 0 <= time <= rig.duration:
                raise ValueError('Time outside the selected clip')
            bones = M.C.skeleton()
            if [doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']] != [b['name'] for b in bones]:
                raise ValueError('Mesh/animation joint order differs')
            pose = M.joint_affines(rig, rig.pose(time), bones)
        parts = []
        for mesh in doc['meshes']:
            for primitive in mesh['primitives']:
                attrs = primitive['attributes']
                indices = read_accessor(doc, binary, primitive['indices'])
                vertices = [author(v) for v in read_accessor(doc, binary, attrs['POSITION'])]
                normals = [(v[0], -v[2], v[1]) for v in read_accessor(doc, binary, attrs['NORMAL'])]
                if pose is not None:
                    joints = np.asarray(read_accessor(doc, binary, attrs['JOINTS_0']), dtype=np.int32)
                    weights = np.asarray(read_accessor(doc, binary, attrs['WEIGHTS_0']))
                    a, b = pose
                    vertices = M.skin(np.asarray(vertices), joints, weights, a, b).tolist()
                    normals = M.skin(np.asarray(normals), joints, weights, a, np.zeros_like(b))
                    normals = (normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)).tolist()
                parts.append(dict(material=doc['materials'][primitive['material']]['name'],
                    vertices=vertices, normals=normals,
                    colours=read_accessor(doc, binary, attrs['COLOR_0']),
                    faces=[tuple(indices[i:i + 3]) for i in range(0, len(indices), 3)]))
        distance, target_cm = (.65, (0, 0, 167)) if head_closeup else (2.1, (0, 0, 90))
        supersampling = 2 if head_closeup else 1
        render(parts, destination, dist_m=distance, yaw=yaw, target=target_cm, width=600, height=900, ss=supersampling)
        receipt = {'scope': 'Offline source-geometry rasterizer only, not native or full-motion acceptance',
                   'glb': relative_source, 'glbSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'file': destination.name, 'pngSha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                   'walkTimeSeconds': time if clip_name == 'walk' else None,
                   'clip': clip_name if pose is not None else None, 'poseTimeSeconds': time,
                   'rendererSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'supersampling': supersampling,
                   'yawRadians': yaw, 'distanceMeters': distance, 'targetCm': list(target_cm)}
        if pose is not None:
            receipt['animationSha256'] = hashlib.sha256(clip[1].read_bytes()).hexdigest()
        destination.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(destination, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--view', choices=('before', 'candidate', 'layered-candidate'), required=True)
    parser.add_argument('--time', type=float)
    parser.add_argument('--yaw', type=float, default=.65)
    parser.add_argument('--glb', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--clip', choices=('walk', 'tend', 'idle'), default='walk')
    parser.add_argument('--head-closeup', action='store_true')
    args = parser.parse_args()
    run(args.view, args.time, args.yaw, args.glb, args.output_dir, args.clip, args.head_closeup)
