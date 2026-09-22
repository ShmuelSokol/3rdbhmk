"""Combine hash-pinned hair and cleared knee studies without regenerating the head."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from build_kohen_neck_tone_study import SOURCE, SOURCE_SHA
from measure_pilgrim_walk import read_glb
import create_kohen_gadol_v1 as K
import measure_kohen_garment_clearance as M
import study_kohen_knee_blend as S
import verify_kohen_clearance_source as V

ROOT = Path(__file__).resolve().parents[1]
KNEE = ROOT / 'SourceAssets/characters-review/KohenKneeBlendV1/SK_Kohen_Knee65_20.glb'
HAIR = ROOT / 'SourceAssets/characters-review/KohenHairV1/SK_Kohen_HairStudy03.glb'
CLEARANCE = KNEE.parent / 'knee65-20-all-full.json'


def validate_clearance(clearance):
    if (clearance['candidate']['kneeTopCm'], clearance['candidate']['kneeBottomCm']) != (65, 20):
        raise ValueError('Wrong measured skin field')
    for module in (K, M, S):
        path = Path(module.__file__)
        if clearance['sourceHashes'][path.name] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Measured source changed: ' + path.name)
    if (clearance['candidate']['lowerEaseCm'], clearance['candidate']['hemBandCm']) != (0, 6):
        raise ValueError('Unexpected robe geometry or hem skin field')
    if set(clearance['clips']) != {'walk', 'tend', 'idle'}:
        raise ValueError('Expected all three measured clips')
    clips = {name: (path, rate) for name, path, _, rate in M.CLIPS}
    for clip, frames in [('walk', 288), ('tend', 601), ('idle', 97)]:
        row = clearance['clips'][clip]
        path, rate = clips[clip]
        if row['sampleRateHz'] != rate or row['animationSourceSha256'] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Animation source or sample rate differs: ' + clip)
        # Maxima are rounded to millimetre fractions. Positive-hit counters and
        # worst timestamps detect even a penetration too small to survive rounding.
        if (row['framesSampled'] != frames or row['maxLegOutsideRobeCm']
                or row['maxKetonetOutsideMeilCm'] or row['framesWithAnyClipping']
                or row['worst']['t'] is not None or row['worstKetonetOutsideMeil']['t'] is not None
                or len(row['perFrameMaxCm']) != frames or any(row['perFrameMaxCm'])):
            raise ValueError('Full configured clearance failed: ' + clip)


def build(destination):
    destination = Path(destination)
    if destination.exists() or destination.with_suffix('.json').exists():
        raise FileExistsError('Fresh combined study required')
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (SOURCE, KNEE, HAIR, CLEARANCE)}
    expected = (SOURCE_SHA, '5ef4f2e777db7d71e2a7f204cc17e877bca128864f31ca57591425248c22c984',
                'ed3adda3860c84a9a864ef7e49eb73f037b3444e39f4fabb9f34878f09625b1f')
    if tuple(hashes.values())[:3] != expected:
        raise ValueError('Source study hash mismatch')
    clearance = json.loads(CLEARANCE.read_text())
    validate_clearance(clearance)
    base, original = read_glb(SOURCE)
    knee, knee_binary = read_glb(KNEE)
    hair, hair_binary = read_glb(HAIR)
    if knee != base or len(knee_binary) != len(original) or hair_binary[:len(original)] != original:
        raise ValueError('Source layouts differ')
    allowed = np.zeros(len(original), dtype=bool)
    for mesh in base['meshes']:
        for p in mesh['primitives']:
            if base['materials'][p['material']]['name'] not in ('KG_Linen', 'KG_Meil', 'KG_Ephod', 'KG_Gold'):
                continue
            for name, size in [('JOINTS_0', 8), ('WEIGHTS_0', 16)]:
                a = base['accessors'][p['attributes'][name]]
                view = base['bufferViews'][a['bufferView']]
                for i in range(a['count']):
                    start = view.get('byteOffset', 0) + a.get('byteOffset', 0) + i * view.get('byteStride', size)
                    allowed[start:start + size] = True
    changed = np.frombuffer(original, dtype=np.uint8) != np.frombuffer(knee_binary, dtype=np.uint8)
    if np.any(changed & ~allowed):
        raise ValueError('Knee study changed non-garment bytes')
    output = knee_binary + hair_binary[len(original):]
    encoded = json.dumps(hair, separators=(',', ':')).encode(); encoded += b' ' * (-len(encoded) % 4)
    payload = struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(output))
    payload += struct.pack('<I4s', len(encoded), b'JSON') + encoded
    payload += struct.pack('<I4s', len(output), b'BIN\0') + output
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream: stream.write(payload)
    before = K.KNEE_TOP, K.KNEE_BOT
    try:
        K.KNEE_TOP, K.KNEE_BOT = 65, 20
        measured = V.verify(destination)
    finally:
        K.KNEE_TOP, K.KNEE_BOT = before
    if not measured['passed']:
        raise ValueError('Combined measured geometry mismatch; diagnostic output retained')
    report = dict(status='combined-source-study-native-review-pending', sourceHashes=hashes,
        outputSha256=hashlib.sha256(payload).hexdigest(), measuredGeometry=measured,
        builderSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Full configured leg/ketonet and ketonet/meil source clearance; additive head hair. Not all-layer or native visual acceptance; no production asset changes.')
    destination.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.out)
