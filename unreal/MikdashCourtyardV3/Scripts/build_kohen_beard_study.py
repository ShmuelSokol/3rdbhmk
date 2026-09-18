"""Trim the neck-covering beard in a fresh GLB, with its new rim below the skin.

Consumes only the approved published GLB. Other primitives, rig and original
binary bytes are preserved; new beard accessors are appended. Native review is
required before adoption.
"""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from build_kohen_neck_tone_study import SOURCE, SOURCE_SHA
from measure_pilgrim_walk import read_glb, read_accessor, COMPONENT, COUNT


def build(destination, cutoff=154.0, blend_top=156.0):
    destination = Path(destination)
    if destination.exists() or destination.with_suffix('.json').exists():
        raise FileExistsError('Fresh study output required')
    if not (150 <= cutoff < blend_top <= 156):
        raise ValueError('Invalid beard transition heights')
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Approved source changed')
    doc, binary = read_glb(SOURCE)
    original = copy.deepcopy(doc)
    primitives = [p for m in doc['meshes'] for p in m['primitives']]
    def primitive(name):
        matches = [p for p in primitives if doc['materials'][p['material']]['name'] == name]
        if len(matches) != 1:
            raise ValueError('Expected one primitive: ' + name)
        return matches[0]
    hair, head = primitive('KG_Hair'), primitive('KG_MHHead')
    arrays = {k: np.asarray(read_accessor(doc, binary, v)) for k, v in hair['attributes'].items()}
    positions = arrays['POSITION'].copy()
    faces = np.asarray(read_accessor(doc, binary, hair['indices']), dtype=int).reshape(-1, 3)
    heights = positions[:, 1] * 100
    retained = faces[np.all(heights[faces] >= cutoff, axis=1)]
    used = np.unique(retained)
    edges = np.sort(np.concatenate((retained[:, [0, 1]], retained[:, [1, 2]], retained[:, [2, 0]])), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    rim = np.unique(unique[counts == 1])
    # Only alter the lower transition. Existing cheek/moustache rims are intact.
    lower = used[heights[used] < blend_top]
    lower_rim = np.intersect1d(rim, lower)
    head_pos = np.asarray(read_accessor(doc, binary, head['attributes']['POSITION']))
    head_norm = np.asarray(read_accessor(doc, binary, head['attributes']['NORMAL']))
    # Limit nearest-point work to the neck/jaw, retaining all nearby source vertices.
    region = (head_pos[:, 1] * 100 < blend_top + 3) & (head_pos[:, 1] * 100 > cutoff - 3)
    head_pos, head_norm = head_pos[region], head_norm[region]
    if not len(lower_rim) or not len(head_pos) or len(retained) == len(faces):
        raise ValueError('No valid lower beard boundary')
    max_snap = 0.0
    for start in range(0, len(lower), 64):
        ids = lower[start:start + 64]
        distance = np.sum((positions[ids, None, :] - head_pos[None, :, :]) ** 2, axis=2)
        nearest = distance.argmin(axis=1)
        max_snap = max(max_snap, float(np.sqrt(distance[np.arange(len(ids)), nearest]).max()) * 100)
        normals = head_norm[nearest]
        normals = normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
        # Project onto the local skin tangent plane, preserving tangential spacing.
        # Snapping to the nearest vertex collapses neighbouring rim vertices.
        signed = np.sum((positions[ids] - head_pos[nearest]) * normals, axis=1)
        submerged = positions[ids] - normals * (signed[:, None] + .0006)
        amount = np.clip((blend_top - heights[ids]) / (blend_top - cutoff), 0, 1)
        amount = amount * amount * (3 - 2 * amount)
        amount[np.isin(ids, lower_rim)] = 1
        positions[ids] += (submerged - positions[ids]) * amount[:, None]
    if max_snap > 2.0:
        raise ValueError('Unexpected head/beard separation: %.3f cm' % max_snap)
    # Recompute normals only where the lower geometry changed or touches it.
    normals = np.zeros_like(positions)
    face_normals = np.cross(positions[retained[:, 1]] - positions[retained[:, 0]],
                            positions[retained[:, 2]] - positions[retained[:, 0]])
    for corner in range(3):
        np.add.at(normals, retained[:, corner], face_normals)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    affected = np.unique(retained[np.any(np.isin(retained, lower), axis=1)])
    # Preserve the imported normal orientation, independently of glTF winding.
    if np.median(np.sum(normals[used] * arrays['NORMAL'][used], axis=1)) < 0:
        normals *= -1
    arrays['NORMAL'][affected] = normals[affected]
    arrays['POSITION'] = positions
    if (not np.isfinite(positions[used]).all()
            or np.any(np.linalg.norm(arrays['NORMAL'][used], axis=1) < .99)):
        raise ValueError('Invalid beard geometry or collapsed normals; no output written')
    output = bytearray(binary)
    def append(rows, template):
        rows = np.asarray(rows)
        accessor = {k: v for k, v in template.items() if k not in ('bufferView', 'byteOffset', 'min', 'max', 'sparse')}
        accessor['count'] = len(rows)
        fmt = COMPONENT[accessor['componentType']][0]
        width = COUNT[accessor['type']]
        output.extend(b'\0' * (-len(output) % 4))
        start = len(output)
        for row in rows.reshape(-1, width):
            output.extend(struct.pack('<' + fmt * width, *row))
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(output) - start})
        accessor['bufferView'] = len(doc['bufferViews']) - 1
        if 'min' in template:
            accessor['min'], accessor['max'] = rows.min(axis=0).tolist(), rows.max(axis=0).tolist()
        doc['accessors'].append(accessor)
        return len(doc['accessors']) - 1
    hair['attributes'] = {k: append(v[used], original['accessors'][hair['attributes'][k]]) for k, v in arrays.items()}
    remap = np.full(len(positions), -1, dtype=int)
    remap[used] = np.arange(len(used))
    hair['indices'] = append(remap[retained].reshape(-1), original['accessors'][hair['indices']])
    output.extend(b'\0' * (-len(output) % 4))
    doc['buffers'][0]['byteLength'] = len(output)
    if output[:len(binary)] != binary:
        raise ValueError('Original binary modified')
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    payload = struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(output))
    payload += struct.pack('<I4s', len(encoded), b'JSON') + encoded
    payload += struct.pack('<I4s', len(output), b'BIN\0') + output
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(payload)
    report = {'status': 'beard-study-native-review-pending', 'sourceSha256': SOURCE_SHA,
              'outputSha256': hashlib.sha256(payload).hexdigest(), 'cutoffCm': cutoff,
              'unchangedPositionAtAndAboveCm': blend_top, 'originalFaces': len(faces),
              'retainedFaces': len(retained), 'retainedVertices': len(used),
              'transitionVertices': len(lower), 'submergedLowerRimVertices': len(lower_rim),
              'maximumNearestHeadDistanceCm': max_snap,
              'projection': 'nearest-head-vertex tangent plane; 0.06 cm submerged rim',
              'preserved': 'Original binary prefix, all non-beard primitives and all rig data; retained beard colors/UVs/weights.',
              'limits': 'Local tangent-plane projection study, not native acceptance or production adoption.'}
    destination.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--cutoff', type=float, default=154)
    parser.add_argument('--blend-top', type=float, default=156)
    args = parser.parse_args()
    print(json.dumps(build(args.out, args.cutoff, args.blend_top), indent=2))
