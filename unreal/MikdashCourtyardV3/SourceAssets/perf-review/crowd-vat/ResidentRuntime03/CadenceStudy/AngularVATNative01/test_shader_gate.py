"""Exercise actual compile_graph via AST extraction; no Unreal/native import."""
import ast,json,hashlib
from pathlib import Path
from types import SimpleNamespace
BASE=Path(__file__).resolve().parent
source=(BASE/'native.py').read_text()
tree=ast.parse(source)
code=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('require','compile_graph')],type_ignores=[])
fields=('num_vertex_shader_instructions','num_pixel_shader_instructions','num_vertex_texture_samples','num_pixel_texture_samples','num_samplers',
        'num_uv_scalars','num_interpolator_scalars','num_virtual_texture_samples')
good=dict(zip(fields,(200,250,12,2,6,6,6,0)))
cases=[]
def run(name,values,errors_before=(),errors_after=(),missing_api=False,expect=False):
    calls=[]
    def recompile(material):
        calls.append('compile');return errors_before if calls.count('compile')==1 else errors_after
    def statistics(material):
        calls.append('statistics');return SimpleNamespace(get_editor_property=lambda k:values[k])
    ml=SimpleNamespace(recompile_material=recompile)
    if not missing_api:ml.get_statistics=statistics
    ns={'ue':SimpleNamespace(MaterialEditingLibrary=ml)}
    exec(compile(code,'actual-native-compile-graph','exec'),ns)
    report={};accepted=False
    try:
        ns['compile_graph'](SimpleNamespace(get_path_name=lambda:'/Candidate'),report,'test')
        accepted=True
    except (RuntimeError,KeyError):pass
    assert accepted==expect,(name,report)
    assert report.get('compilers'),name
    if accepted:
        assert report['compilers'][0]['positiveResourceShaderEvidence']
        assert calls==['compile','statistics','compile']
    cases.append({'case':name,'accepted':accepted,'expected':expect,'calls':calls})
run('positive representative shader statistics',good,expect=True)
run('null resource all zeros',{k:0 for k in fields})
for field in fields[:5]:
    bad=good.copy();bad[field]=0;run('zero '+field,bad)
bad=good.copy();bad['num_vertex_shader_instructions']=-1;run('negative unavailable instructions',bad)
run('initial compiler error',good,errors_before=['compiler diagnostic'])
run('compiler error after statistics jobs',good,errors_after=['late diagnostic'])
run('statistics API unavailable',good,missing_api=True)
bad=good.copy();del bad['num_pixel_shader_instructions'];run('missing reflected statistics field',bad)
result={'passed':True,'count':len(cases),'cases':cases,'nativeLaunches':0,
        'nativeSourceSha256':hashlib.sha256((BASE/'native.py').read_bytes()).hexdigest(),
        'scope':'Actual gate control-flow fault tests with mock reflected stats; not native shader compilation'}
(BASE/'shader-gate-tests.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(cases),'nativeLaunches':0}))
