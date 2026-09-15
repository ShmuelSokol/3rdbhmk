"""Read-only native PNG comparison; writes an evidence report, never edits images."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / 'SourceAssets/context-review/KotelCutClosureV1'
RUNS = ('20260915T180109788Z', '20260915T180340505Z', '20260915T180619560Z')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows, pixels = [], []
    baseline = None
    for stamp in RUNS:
        path = REVIEW / ('runtime-' + stamp + '.json')
        run = read(path)
        if (run['status'] != 'native-state-passed-visual-review-pending'
                or run['exitCode'] != 0 or not run['mapsUnchanged']
                or not run['native']['passed'] or not run['native']['finalReadback']['passed']):
            raise ValueError('Native run did not pass: ' + stamp)
        states = run['native']['states']
        if [s['state'] for s in states] != ['Modern', 'Yechezkel', 'Overlay', 'Modern-again']:
            raise ValueError('Incomplete state round trip')
        if not all(s['passed'] for s in states):
            raise ValueError('Failed native state')
        cameras = [{k: s[k] for k in ('cameraLocationCm', 'cameraRotation', 'cameraFov')} for s in states]
        identity = {'child': run['childSha256'], 'cameras': cameras,
                    'viewport': run['viewport'], 'maps': run['mapHashesBefore']}
        if baseline is None:
            baseline = identity
        if identity != baseline:
            raise ValueError('Camera/executable/source identity changed')
        photo = REVIEW / run['photos'][0]['file']
        if sha(photo) != run['photos'][0]['sha256']:
            raise ValueError('Native photograph hash changed')
        with Image.open(photo) as im:
            if im.size != (1920, 1080):
                raise ValueError('Unexpected capture resolution')
            pixels.append(np.asarray(im.convert('RGB'), dtype=np.int16))
        rows.append({'receipt': path.name, 'receiptSha256': sha(path), 'photo': photo.name,
                     'photoSha256': sha(photo), 'peakPrivateBytes': run['peakPrivateBytes'],
                     'minimumFreeCommitBytes': run['minimumFreeCommitBytes']})
    comparisons = {}
    # Fixed wall-only interior rectangle, avoiding ground and photograph watermark.
    for label, i, j in [('A_to_B', 0, 1), ('A_to_A_return', 0, 2)]:
        diff = np.abs(pixels[i][100:850, 100:1820] - pixels[j][100:850, 100:1820])
        comparisons[label] = {'meanAbsoluteChannelDifference': float(diff.mean()),
                              'fractionPixelsAnyChannelOver8': float((diff.max(axis=2) > 8).mean())}
    result = {'status': 'native-ABA-identity-verified', 'runs': rows,
              'patchSequence': ['absent', 'CityWall-master-only', 'absent'],
              'identity': baseline, 'pixelROI': [100, 100, 1820, 850], 'comparisons': comparisons,
              'visualReview': 'Coordinator inspected all three phase-0 native images: vertical courses, horizontal courses, vertical courses restored.',
              'limits': ['Only CityWall master tested, not all context material families.',
                         'Small texture repeats and low-relief surface still need visual refinement.',
                         'Pixel differences measure repeatability, not production quality.']}
    out = Path(__file__).with_name('citywall-patch-aba.json')
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(out), 'comparisons': comparisons}, indent=2))


if __name__ == '__main__':
    main()
