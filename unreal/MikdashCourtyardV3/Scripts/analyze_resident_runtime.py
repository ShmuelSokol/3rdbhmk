"""Verify a live review receipt and distinguish root continuity from history errors."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw
from analyze_crowd_motion_audit import analyze, fields, number, vector


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(folder):
    receipt = folder / 'run.json'
    result = json.loads(receipt.read_text(encoding='utf-8-sig'))
    assert result['status'] == 'captured-live-review-pending'
    assert result['exitCode'] == 0 and result['mapUnchanged']
    for name, value in dict(SeededAgents=48, RefusedSeeds=0,
                            GroundTraceMisses=0, ActivePoseCount=2).items():
        assert result['readbacks'][name] == value
    records = result['images']
    assert len(records) == 50
    assert [r['frame'] for r in records] == result['requestedScreenshots']
    for record in records:
        path = folder / Path(record['file']).name
        assert sha(path) == record['sha256']
        with Image.open(path) as im:
            assert im.size == (1280, 720)
    log = folder / 'runtime.log'
    audit = analyze(log)
    current = []
    for line in log.read_text(encoding='utf-8-sig').splitlines():
        if 'CrowdMotionAuditV1 sample=' not in line:
            continue
        data = fields(line)
        roots = []
        for prefix in ('old', 'new'):
            dt = min(number(data, prefix + 'Horizon'),
                     max(-.25, number(data, 'now') - number(data, prefix + 'Time')))
            roots.append(tuple(p + v * dt for p, v in
                               zip(vector(data[prefix + 'Pos']), vector(data[prefix + 'Vel']))))
        current.append(dict(sample=int(data['sample']), currentRootContinuityErrorCm=math.dist(*roots)))
    assert len(current) == len(audit['samples']) == 64
    native_max = audit['nativeSummary'].get('maxHeadingChangeDegrees')
    sampled_max = max(r['headingChangeDegrees'] for r in audit['samples'])
    if native_max is not None:
        assert math.isfinite(float(native_max)) and sampled_max <= float(native_max) + .001
    contacts = []
    for page in range(5):
        path = folder / f'overview-{page + 1}.jpg'
        assert not path.exists(), 'Fresh analysis output required'
        sheet = Image.new('RGB', (1280, 1900), '#303030')
        draw = ImageDraw.Draw(sheet)
        for index, record in enumerate(records[page * 10:page * 10 + 10]):
            with Image.open(folder / Path(record['file']).name) as im:
                tile = im.convert('RGB').resize((640, 360))
            x, y = (index % 2) * 640, (index // 2) * 380
            sheet.paste(tile, (x, y + 20))
            draw.text((x + 8, y + 3), 'frame ' + str(record['frame']), fill='white')
        sheet.save(path, quality=92)
        contacts.append(dict(file=path.name, sha256=sha(path)))
    report = dict(status='evidence-validated-visual-acceptance-separate',
                  receiptSha256=sha(receipt), rootHistoryAudit=audit,
                  currentRootSamples=current,
                  maxCurrentRootContinuityErrorCm=max(r['currentRootContinuityErrorCm'] for r in current),
                  maxLoggedHeadingChangeDegrees=sampled_max,
                  maxNativeHeadingChangeDegrees=float(native_max) if native_max else None,
                  logErrors=[line for line in log.read_text(encoding='utf-8-sig').splitlines() if ': Error:' in line],
                  contacts=contacts,
                  limitations=['Current root continuity is checked only for the 64 retained audit samples.',
                               'Heading summary covers 4096 updates only when the native maximum is present.',
                               'Overview sheets downsample 2:1; original screenshots remain hash-pinned.',
                               'No packaged, performance, long-run navigation or foot-contact acceptance.'])
    with (folder / 'runtime-analysis.json').open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    print(json.dumps({k: report[k] for k in ('status', 'maxCurrentRootContinuityErrorCm',
                                           'maxLoggedHeadingChangeDegrees', 'maxNativeHeadingChangeDegrees')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    run(parser.parse_args().folder)
