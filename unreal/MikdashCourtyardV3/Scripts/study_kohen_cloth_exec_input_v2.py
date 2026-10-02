"""Publish explicit study physics input without replacing historical prepared evidence."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from pathlib import Path
from study_kohen_cloth_exec_readback import atomic

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenClothExecutableV1'

def prepare():
    previous = OUT.parent / 'KohenClothFeasibilityV1/prepared-input.json'
    model = json.loads(previous.read_text())
    model['studyPhysics'] = dict(densityKgM2=.35, minParticleMassKg=.0001,
        massBasis='Authored feasibility choice:350g/m2 and0.1g particle floor. Not measured or historical textile data. Density distributes mass by area, avoiding uniform mass on unequal triangles.',
        tetherGenerator='UE5.8 FClothEngineTools::GenerateTethers', geodesicTethers=True,
        tetherStiffness=1., tetherScale=1., frameSchemaVersion=2,
        control='Exact solver physical binding plus identical render mapping/blend, without integration; original rig remains separate preservation reference')
    path = OUT / 'prepared-study-input-v2.json'
    atomic(path, model)
    manifest = json.loads((OUT / 'source-manifest.json').read_text())
    manifest['inputs'].pop(manifest['preparedInput'])
    manifest['preparedInput'] = str(path.relative_to(ROOT)).replace('\\', '/')
    manifest['inputs'][manifest['preparedInput']] = hashlib.sha256(path.read_bytes()).hexdigest()
    atomic(OUT / 'source-manifest-v2.json', manifest)

if __name__ == '__main__':
    prepare()
