"""Read-only source diagnosis; evidence only in KohenHemStudyV1. Run with -B."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import create_kohen_gadol_v1 as K
import measure_kohen_garment_clearance as M
import verify_kohen_clearance_source as V

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenHemStudyV1'
SOURCE = ROOT / 'SourceAssets/characters-review/KohenCombinedV1/SK_Kohen_KneeHairStudy01.glb'
TIMES = (.295833, 1.166667)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def save(name, data):
    with (OUT / name).open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        f.write('\n')

def protected():
    paths = list((ROOT / 'Content').rglob('*.umap'))
    for subtree in ('MikdashV3/Characters/KohenGadolV1', 'MikdashV3/Characters/PilgrimRigV3'):
        paths.extend((ROOT / 'Content' / subtree).rglob('*.uasset'))
    paths.extend((ROOT / 'Scripts').glob('*.py'))
    paths.extend(ROOT / p for p in ('AGENTS.md', 'FINISH-LINE.md'))
    for folder in ('KohenCombinedV1', 'KohenHairV1', 'KohenKneeBlendV1', 'KohenGadolV1'):
        paths.extend((ROOT / 'SourceAssets/characters-review' / folder).rglob('*.glb'))
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(set(paths))
            if not p.name.startswith('study_kohen_hem_')}

def metrics(v):
    coef = np.linalg.lstsq(np.column_stack((v[:, :2], np.ones(len(v)))), v[:, 2], rcond=None)[0]
    residual = v[:, 2] - np.column_stack((v[:, :2], np.ones(len(v)))) @ coef
    return dict(minHeightCm=float(v[:, 2].min()), maxHeightCm=float(v[:, 2].max()),
                heightRangeCm=float(np.ptp(v[:, 2])), meanHeightCm=float(v[:, 2].mean()),
                sagittalTiltDeg=float(np.degrees(np.arctan(coef[1]))),
                fittedPlaneTiltDeg=float(np.degrees(np.arctan(np.linalg.norm(coef[:2])))),
                planeResidualRmsCm=float(np.sqrt(np.mean(residual ** 2))))

def diagnose():
    K.KNEE_TOP, K.KNEE_BOT = 65, 20
    assert digest(SOURCE) == 'b542efdc1a053fd5ae59720a578701355a4a6e5a203691d999755d6ee4f67535'
    provenance = V.verify(SOURCE)
    assert provenance['passed']
    bones, index, parts, influence, *_ = M.body_parts('kohen')
    rig = M.Rig(M.CLIPS[0][1], M.CLIPS[0][2])
    rows = []
    for p in parts:
        if p['name'] not in ('Ketonet', 'Meil'):
            continue
        v, j, w = M.skin_arrays(p, influence, index)
        n = K.KETONET_SEGMENTS
        for t in TIMES:
            a, b = M.joint_affines(rig, rig.pose(t), bones)
            posed = M.skin(v, j, w, a, b)
            contribution = {}
            for joint in ('pelvis', 'thigh_l', 'calf_l', 'foot_l', 'thigh_r', 'calf_r', 'foot_r'):
                jj = index[joint]
                contribution[joint] = dict(meanHemWeight=float(np.where(j[:n] == jj, w[:n], 0).sum(axis=1).mean()),
                    rigidSagittalTiltDeg=float(np.degrees(np.arctan2(a[jj, 2, 1], a[jj, 1, 1]))))
            rows.append(dict(part=p['name'], seconds=t, hem=metrics(posed[:n]), restHem=metrics(v[:n]),
                             boneContributions=contribution,
                             rings=[dict(restZ=float(v[i:i+n, 2].mean()), **metrics(posed[i:i+n]))
                                    for i in range(0, len(v), n) if v[i, 2] < 70 and len(v[i:i+n]) == n]))
    return dict(sourceProvenance=provenance, measurements=rows,
                definition='Least-squares z=ax+by+c hem plane; sagittal angle atan(b), full tilt atan(hypot(a,b)); authored cm.',
                scope='Source skinning diagnosis at exact requested times, not clearance acceptance.')

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=False)
    save('preservation-before.json', protected())
    result = diagnose()
    save('diagnosis.json', result)
    print(json.dumps(result, indent=2))
