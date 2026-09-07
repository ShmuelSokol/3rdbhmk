"""Offline regression checks; no Unreal import, native run or asset mutation."""
import ast
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
checks = []
def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

source = (ROOT / 'Scripts/create_incense_smoke_study.py').read_text(encoding='utf-8')
inspect_source = (ROOT / 'Scripts/inspect_incense_particles.py').read_text(encoding='utf-8')
for name, text in [('authoring', source), ('inspection', inspect_source)]:
    ast.parse(text)
    check(True, name + ' Python syntax')
check('incense-smoke-study-spec.json' not in source, 'No historical spec write path')
check("IncenseSmokeV4'" in source and 'IncenseSmokeV4/' in inspect_source, 'V4 namespaces match')
check("'init': [1, 0]" in source, 'Proven initializer version retained')
check(source.index("init = module(e") < source.index("shape = module(e") < source.index("velocity_script = module(e"), 'Module creation order init then location then velocity')
check("set_parameter_directly(" not in source, 'No overwritten direct particle assignments')
check("'UsePositionOffset', fx.create_script_input_bool(False)" in source, 'Ineffective init offset disabled')
check("'Sphere Radius', fx.create_script_input_float(0.01)" in source, 'Nonzero near-point radius')
check("'Offset Coordinate Space', fx.create_script_input_enum(ENUMS['space'], 'Local')" in source, 'Explicit local offset')
spec = json.loads((OUT / 'spec.json').read_text())
check(hashlib.sha256((ROOT / 'SourceAssets/vessels-review/incense-smoke-study-spec.json').read_bytes()).hexdigest() == spec['historical_spec_sha256'], 'Historical spec byte hash unchanged')
# Compile only the pure check function: no import of unreal or engine execution.
fn = next(n for n in ast.parse(inspect_source).body if isinstance(n, ast.FunctionDef) and n.name == 'check_wisp_origins')
ns = {'math': math}
exec(compile(ast.Module(body=[fn], type_ignores=[]), '<isolated-check>', 'exec'), ns)
validate = ns['check_wisp_origins']
base = {'cache_valid': True, 'cache_start_seconds': 6.000023, 'emitters': [
    {'name': 'CeilingWisp_%02d' % i, 'positions': [[0,0,865],[80,0,853],[150,0,841.12]], 'ages': [0,1,1.99]} for i in range(8)]}
check(validate(base)['status'] == 'pass_attributes_only', 'Expected alive ceiling trajectory passes')
for kind in ['floor', 'missing', 'nan', 'wrong_age', 'invalid_cache', 'missing_positions']:
    case = json.loads(json.dumps(base))
    if kind == 'floor': case['emitters'][0]['positions'][0][2] = 0
    if kind == 'missing': case['emitters'].pop()
    if kind == 'nan': case['emitters'][0]['positions'][0][2] = float('nan')
    if kind == 'wrong_age': case['cache_start_seconds'] = 3
    if kind == 'invalid_cache': case['cache_valid'] = False
    if kind == 'missing_positions': case['emitters'][0]['positions'] = []
    check(validate(case)['status'] != 'pass_attributes_only', kind + ' rejected or unassessed')
prior = json.loads((ROOT / 'SourceAssets/vessels-review/incense-particle-inspection.json').read_text())
actual6 = next(s for s in prior['samples'] if s.get('cache_valid') and abs(s.get('cache_start_seconds',0)-6)<0.05)
check(validate(actual6)['status'] == 'fail', 'Actual V2 floor-wisp receipt fails new acceptance')
receipt = {'status': 'offline_checks_pass_native_pending', 'checks': checks, 'count':len(checks), 'limits':'Source ordering and pure receipt checks only; no Niagara compile/runtime/render acceptance'}
(OUT / 'offline-verification.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
