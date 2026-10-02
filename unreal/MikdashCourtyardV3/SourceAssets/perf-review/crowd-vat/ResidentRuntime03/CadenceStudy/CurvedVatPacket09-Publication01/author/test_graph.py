from pathlib import Path
import csv,gzip,json,math,hashlib,sys
import candidate_builder as b
from graph_backend import UE,Node,evaluate,dependencies,rot,f32
base=Path(__file__).resolve().parent
checks=0;maxerr=0.;errors={}
def check(x,label):
 global checks
 checks+=1
 assert x,label
def near(actual,expected,label,tolerance=.002):
 global maxerr
 if not isinstance(actual,tuple):actual=(actual,);expected=(expected,)
 error=max(abs(a-z) for a,z in zip(actual,expected));maxerr=max(maxerr,error);errors[label]=max(errors.get(label,0),error);check(error<tolerance,(label,error,actual,expected))
rows=list(csv.DictReader(gzip.open(base/'samples.csv.gz','rt')))
# Test the emitted helper graph directly against the float-only C++ compilation
# of the EXACT .ush, including dynamic nonzero VAT position and normal samples.
ue=UE();g=b.StockGraph(ue,Node('Material'),{});t=g.make(ue.MaterialExpressionTime);rest=g.make(ue.MaterialExpressionPreSkinnedPosition)
q=[b.curve_eval(g,t,k) for k in [31,54]]
for row in rows:
 cd={i:f32(float(row['p'+str(i)])) for i in range(77)};time=f32(float(row['time']));basis=f32(float(row['basis']));scale=f32(float(row['scale']));prev=int(row['previous']);which=1 if prev and time<cd[25] else 0;out=q[which]
 for key,columns in [('root',['rootx','rooty','rootz']),('yaw',['yaw']),('phase',['phase'])]:
  actual=evaluate(out[key],cd,time,basis,scale);expected=tuple(float(row[k]) for k in columns)
  near(actual,expected[0] if len(expected)==1 else expected,key)
 d=g.const3([f32(4+f32(math.sin(time))),2,3]);posed=b.curve_wpo(g,t,54 if which else 31,rest,d,lambda x:b._transform(g,x),g.const3([0,0,0]))
 near(evaluate(posed,cd,time,basis,scale),tuple(float(row[k]) for k in ['wpx','wpy','wpz']),'posed')
 norm=math.sqrt(f32(f32(.3*.3)+f32(.4*.4)+f32(.866*.866)));n=g.const3([f32(.3/norm),f32(.4/norm),f32(.866/norm)])
 nn=g.unary(ue.MaterialExpressionNormalize,b._transform(g,b.stock_rotate(g,n,out['yaw'])))
 near(evaluate(nn,cd,time,basis,scale),tuple(float(row[k]) for k in ['nx','ny','nz']),'normal',.0001)
# Actual material generator consumption, not a disconnected expression demo.
ue=UE();spec=json.loads((base/'spec.json').read_text());defaults={k:object() for k in ('WalkPositionTexture','IdlePositionTexture','WalkNormalTexture','IdleNormalTexture')}
defaults.update(WalkMinBBox=[4,2,3],IdleMinBBox=[4,2,3],WalkSizeBBox=[0,0,0],IdleSizeBBox=[0,0,0])
material=b._build(ue,spec,b.NAMESPACE,'M_Curved09_Offline',defaults,{})
ml=ue.MaterialEditingLibrary;wpo=ml.outputs['MP_WORLD_POSITION_OFFSET'];normal=ml.outputs['MP_NORMAL']
indices={n.props['data_index'] for n in ml.nodes if n.kind=='MaterialExpressionPerInstanceCustomData'}
check(indices==set(range(77)),'actual generated material consumes77channels')
check(not any(n.kind=='MaterialExpressionCustom' for n in ml.nodes),'no Custom node')
check({30,31,53,54,76}.issubset(dependencies(wpo)),'both curve root/phase versions reach WPO')
check({30,31,45,54,68,53,76}.issubset(dependencies(normal)),'current/previous curve orientation and VAT phase reach normals')
for row in rows:
 cd={i:f32(float(row['p'+str(i)])) for i in range(77)};time=f32(float(row['time']));basis=float(row['basis']);scale=float(row['scale']);prev=bool(int(row['previous']));yaw=float(row['yaw']);offset=tuple(float(row[k]) for k in ['rootx','rooty','rootz'])
 expected=tuple(o+v*scale for o,v in zip(offset,rot(tuple(a-z for a,z in zip(rot((24,9,173),yaw),(20,7,170))),basis)))
 near(evaluate(wpo,cd,time,basis,scale,prev,time),expected,'full builder WPO')
 n=rot((1,0,.0001),yaw+basis);length=math.sqrt(sum(v*v for v in n));near(evaluate(normal,cd,time,basis,scale,prev,time),tuple(v/length for v in n),'full builder previous/current normal',.0001)
# Old30 layout gets legacy path; new shader does not interpret absent tag as curve.
cd={i:0 for i in range(30)};cd.update({3:600,10:.7,5:60,6:-10,7:2,8:-1000,14:1,25:600,26:600,27:0})
for time in [599.9,600,600.2,601]:
 dt=min(max(time-600,-.25),.7);expected=tuple(x+v*dt for x,v in zip(rot((4,2,3),35),(60,-10,2)))
 near(evaluate(wpo,cd,time,35),expected,'legacy30 fallback')
# Mixed history: current legacy/idle, previous curve must remain reconstructible.
import importlib.util
loader=importlib.util.spec_from_file_location('frozen_angular09',base/'frozen/candidate_builder.py');legacy=importlib.util.module_from_spec(loader);loader.loader.exec_module(legacy)
lu=UE();legacy._build(lu,spec,legacy.NAMESPACE,'M_Angular_OfflineControl',defaults,{})
for row in rows[:26]:
 cd={i:f32(float(row['p'+str(i)])) for i in range(77)};cd[31]=0;time=f32(float(row['time']));basis=float(row['basis']);scale=float(row['scale'])
 # Current inactive record follows original angular/linear prefix, including phase.
 near(evaluate(wpo,cd,time,basis,scale),evaluate(lu.MaterialEditingLibrary.outputs['MP_WORLD_POSITION_OFFSET'],cd,time,basis,scale),'mixed current legacy')
 if int(row['previous']) and time<cd[25]:
  yaw=float(row['yaw']);offset=tuple(float(row[k]) for k in ['rootx','rooty','rootz'])
  expected=tuple(o+v*scale for o,v in zip(offset,rot(tuple(a-z for a,z in zip(rot((24,9,173),yaw),(20,7,170))),basis)))
  near(evaluate(wpo,cd,time,basis,scale,True,time),expected,'mixed old curve survives current idle')
# Current curve, previous angular legacy: old normal follows OLD angular state.
cd={i:f32(float(rows[0]['p'+str(i)])) for i in range(77)};cd.update({54:0,14:1,15:0,28:600,29:-30,25:601.2})
time=f32(600.2);angle=-min(f32(f32(time-600)*90),30);expected=rot((1,0,.0001),35+angle);ln=math.sqrt(sum(v*v for v in expected))
near(evaluate(normal,cd,time,35,1,True,time),tuple(v/ln for v in expected),'mixed old angular normal',.0001)
b._surface(ue,material,{},dict(Mottle=object(),DetailNormal=object()))
check({30,45,68}.issubset(dependencies(ml.outputs['MP_NORMAL'])),'resident normal detail retains curve history')
check(any(n.kind=='MaterialExpressionDDX' for n in ml.nodes),'actual resident derivative surface generated')
# Execute the authored create_candidate API through the recording backend.
# This is an offline UE double, not an import or invocation of Unreal.
from types import SimpleNamespace
api=UE();api.Texture=type('Texture',(),{});assets=[];compiles=[]
api.EditorLevelLibrary=SimpleNamespace(get_editor_world=lambda:SimpleNamespace(get_outermost=lambda:SimpleNamespace(get_name=lambda:'/Engine/Maps/Entry')),get_pie_worlds=lambda x:[])
api.find_object=lambda *a:None
api.MaterialEditingLibrary.recompile_material=lambda material:compiles.append(material)
def make_asset(name,folder,*args):
 obj=Node('Material');obj.get_path_name=lambda:folder+'/'+name+'.'+name;assets.append(obj);return obj
api.AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda:SimpleNamespace(create_asset=make_asset))
apidefaults=dict(defaults)
for name in ('WalkPositionTexture','IdlePositionTexture','WalkNormalTexture','IdleNormalTexture'):apidefaults[name]=api.Texture()
try:b.create_candidate(api,spec,apidefaults,{},name='M_Angular_WrongLayout')
except ValueError:pass
else:raise AssertionError('legacy namespace accepted')
check(not assets,'legacy name refusal before asset creation')
receipt={};b.create_candidate(api,spec,apidefaults,receipt,name='M_Curved09_OfflineAPI')
check(receipt['angularCandidate']['customFloats']==77 and receipt['angularCandidate']['packetVersion']==9001,'authored API enforces77float version')
check(len(assets)==1 and len(compiles)==1 and not receipt['angularCandidate']['saved'],'fresh API only requests compile and defaults unsaved')
result={'checks':checks,'failures':0,'cppHlslSamples':len(rows),'maxAbsoluteGraphDifference':maxerr,'maxErrorByCheck':errors,'nodesWithResidentSurface':len(ml.nodes),'builderSha256':hashlib.sha256((base/'candidate_builder.py').read_bytes()).hexdigest(),'nativeLaunched':False,'scope':'Float32-recording stock graph vs same .ush compiled as C++ and double analytic reference; NOT GPU execution, material compilation or render acceptance.'}
if '--replay' in sys.argv:check(result==json.loads((base/'graph-receipt.json').read_text()),'exact graph receipt')
else:(base/'graph-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
