"""Offline CRC/pixel audit of preserved threshold07 PNGs; never alters inputs."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/context-review/HaramThresholdSidesV1'


from haram_threshold_png import decode


def main():
    result = dict(scope='Offline preserved07 image audit; no new render or adoption acceptance', images={}, comparisons={})
    hashes = {}
    for mode in ('build','verify'):
        receipt = json.loads((OUT/'threshold-sides07'/mode/'native.json').read_text(encoding='utf-8'))
        expected = {c['file']:c['sha256'] for c in receipt['captures']}
        for view in ('accepted','edge-oblique','top'):
            pixels = []
            for label in ('baseline','candidate','baseline-return'):
                name = view+'-'+label+'.png'
                rgba, info = decode(OUT/'threshold-sides07'/mode/name)
                assert info['fileSha256'] == expected[name]
                result['images'][mode+'/'+name] = info
                hashes[mode+'/'+name] = info['rgbaSha256']
                pixels.append(rgba)
            result['comparisons'][mode+'/'+view] = dict(
                baselineReturnExact=pixels[0] == pixels[2],
                baselineCandidateExact=pixels[0] == pixels[1],
                changedRgbChannels=sum(a != b for i,(a,b) in enumerate(zip(pixels[0],pixels[1])) if i%4 != 3))
    result['buildVerifyAllPixelsExact'] = all(hashes['build/'+name] == hashes['verify/'+name] for name in expected)
    result['exportSourceEvidence'] = 'UE5.8 Engine/Source/Runtime/Engine/Private/ImageUtils.cpp:1281 serializes CompressedData.GetAllocatedSize(), including bytes beyond valid PNG IEND.'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
