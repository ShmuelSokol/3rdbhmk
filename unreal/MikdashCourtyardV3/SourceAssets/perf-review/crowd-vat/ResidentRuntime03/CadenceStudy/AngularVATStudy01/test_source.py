"""Build/evaluate the ACTUAL generated stock graph with an offline recording backend.
No Unreal imports. This tests graph wiring/arithmetic, not native reflection/compilation.
"""
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import candidate_builder as b
from controller_adapter import AngularState, channels, translation_gate

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[5]
checks=0
def check(value):
    global checks
    checks+=1
    assert value

class Node:
    def __init__(self,kind): self.kind,self.props,self.inputs=kind,{},{}
    def set_editor_property(self,k,v): self.props[k]=v
    def get_editor_property(self,k): return self.props.get(k)
    def get_class(self): return SimpleNamespace(get_name=lambda:self.kind)
    def get_path_name(self): return '/Recording/'+self.kind

class ML:
    def __init__(self): self.nodes=[];self.outputs={}
    def create_material_expression(self,m,cls,x,y):
        n=cls();self.nodes.append(n);return n
    def get_material_expression_input_names(self,n):
        return ['A','B','Input','Alpha','Min','Max','VS','UVs','Current Frame','Previous Frame','A > B','A == B','A < B']
    def connect_material_expressions(self,src,out,dst,pin): dst.inputs[pin]=(src,out);return True
    def connect_material_property(self,src,out,prop): self.outputs[prop]=(src,out);return True
    def get_material_expressions(self,m): return self.nodes
    def get_material_expression_output_names(self,n): return ['RGB']
    def get_material_property_input_node(self,m,p): return self.outputs[p][0]

class UE:
    def __init__(self):
        self.MaterialEditingLibrary=ML()
        names=('MP_NORMAL','MP_WORLD_POSITION_OFFSET','MP_BASE_COLOR','MP_ROUGHNESS','MP_SPECULAR','MP_METALLIC','MP_SUBSURFACE_COLOR','MP_OPACITY')
        self.MaterialProperty=SimpleNamespace(**{x:x for x in names})
        self.MaterialSamplerType=SimpleNamespace(SAMPLERTYPE_LINEAR_COLOR=0,SAMPLERTYPE_NORMAL=1)
        self.TextureMipValueMode=SimpleNamespace(TMVM_MIP_LEVEL=0)
        self.MaterialVectorCoordTransformSource=SimpleNamespace(TRANSFORMSOURCE_LOCAL=0)
        self.MaterialVectorCoordTransform=SimpleNamespace(TRANSFORM_WORLD=1)
        self.EditorAssetLibrary=SimpleNamespace(does_asset_exist=lambda p:False)
        self.AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda:SimpleNamespace(create_asset=lambda *args:Node('Material')))
        self.Material=Node;self.MaterialFactoryNew=lambda:None
        self.LinearColor=lambda r,g,b,a:SimpleNamespace(r=r,g=g,b=b,a=a)
    def __getattr__(self,name):
        if not name.startswith('MaterialExpression'):raise AttributeError(name)
        cls=type(name,(Node,),{'__init__':lambda self:Node.__init__(self,name)})
        setattr(self,name,cls);return cls

def vecop(a,b,op):
    if isinstance(a,tuple) or isinstance(b,tuple):
        n=len(a) if isinstance(a,tuple) else len(b)
        a=a if isinstance(a,tuple) else (a,)*n;b=b if isinstance(b,tuple) else (b,)*n
        return tuple(op(x,y) for x,y in zip(a,b))
    return op(a,b)

def rot(v,d):
    c,s=math.cos(math.radians(d)),math.sin(math.radians(d))
    return(c*v[0]-s*v[1],s*v[0]+c*v[1],v[2])

def evaluate(root,cd,time,basis,scale=1,previous=False,prevtime=0):
    cache={}
    def ev(ref,t,prev):
        node,out=ref if isinstance(ref,tuple) else (ref,'')
        key=(id(node),out,t,prev)
        if key in cache:return cache[key]
        k=node.kind.removeprefix('MaterialExpression');p=node.props
        get=lambda pin:ev(node.inputs[pin],t,prev)
        if k=='PreviousFrameSwitch':v=ev(node.inputs['Previous Frame' if prev else 'Current Frame'],t,prev)
        elif k=='If':v=get('A < B' if get('A')<get('B') else 'A > B' if get('A')>get('B') else 'A == B')
        elif k=='Time':v=t
        elif k=='PerInstanceCustomData':v=cd.get(p['data_index'],p['const_default_value'])
        elif k in ('Constant','ScalarParameter'):v=p['r'] if k=='Constant' else p['default_value']
        elif k in ('Constant3Vector','VectorParameter'):
            q=p['constant'] if k=='Constant3Vector' else p['default_value'];v=(q.r,q.g,q.b)
        elif k=='PreSkinnedPosition':v=(20.,7.,170.)
        elif k=='TextureCoordinate':v=(.2,.3)
        elif k=='TextureSampleParameter2D':v=(1.,.5,.5) if 'Normal' in p['parameter_name'] else (.1,.2,.3)
        elif k=='ComponentMask':
            a=get('Input');v=tuple(a[i] for i,c in enumerate('rgba') if p[c]);v=v[0] if len(v)==1 else v
        elif k=='AppendVector':
            a,z=get('A'),get('B');v=(a if isinstance(a,tuple) else (a,))+(z if isinstance(z,tuple) else (z,))
        elif k in ('Add','Subtract','Multiply','Divide','Min','Max'):
            op={'Add':lambda a,b:a+b,'Subtract':lambda a,b:a-b,'Multiply':lambda a,b:a*b,'Divide':lambda a,b:a/b,'Min':min,'Max':max}[k]
            v=vecop(get('A'),get('B'),op)
        elif k=='Clamp':v=min(max(get('Input'),get('Min')),get('Max'))
        elif k=='LinearInterpolate':v=vecop(get('A'),vecop(vecop(get('B'),get('A'),lambda a,b:a-b),get('Alpha'),lambda a,b:a*b),lambda a,b:a+b)
        elif k=='Transform':v=tuple(x*scale for x in rot(get('Input'),basis))
        elif k=='VertexInterpolator':v=get('VS')
        elif k=='Normalize':
            a=get('Input');l=math.sqrt(sum(x*x for x in a));v=tuple(x/l for x in a)
        else:
            a=get('Input')
            fn={'Abs':abs,'Sign':lambda x:(x>0)-(x<0),'Frac':lambda x:x-math.floor(x),'Floor':math.floor,
                'Saturate':lambda x:min(max(x,0),1),'OneMinus':lambda x:1-x,
                'Sine':lambda x:math.sin(x*2*math.pi/p['period']),'Cosine':lambda x:math.cos(x*2*math.pi/p['period'])}[k]
            v=tuple(fn(x) for x in a) if isinstance(a,tuple) else fn(a)
        cache[key]=v;return v
    return ev(root,prevtime if previous else time,previous)

def dependencies(ref):
    result=set();seen=set()
    def visit(ref):
        n=ref[0] if isinstance(ref,tuple) else ref
        if id(n) in seen:return
        seen.add(id(n))
        if n.kind=='MaterialExpressionPerInstanceCustomData':result.add(n.props['data_index'])
        for child in n.inputs.values():visit(child)
    visit(ref);return result

ue=UE();spec=json.loads((ROOT/'Scripts/create_crowd_vat_v2.spec.json').read_text())
defaults={k:object() for k in ('WalkPositionTexture','IdlePositionTexture','WalkNormalTexture','IdleNormalTexture')}
defaults.update(WalkMinBBox=[4,2,3],IdleMinBBox=[4,2,3],WalkSizeBBox=[0,0,0],IdleSizeBBox=[0,0,0])
material=b._build(ue,spec,b.NAMESPACE,'M_Angular_Offline',defaults,{})
ml=ue.MaterialEditingLibrary;wpo=ml.outputs['MP_WORLD_POSITION_OFFSET'];normal=ml.outputs['MP_NORMAL']
check(dependencies(wpo)==set(range(30))-{1})
check({26,27}.issubset(dependencies(normal)))
check(not {28,29}.intersection(dependencies(normal)))
check(not any(n.kind=='MaterialExpressionCustom' for n in ml.nodes))
base={0:.1,2:1,3:10,4:0,5:0,6:0,7:0,8:0,9:.3,10:0,11:0,12:0,13:0,14:1,15:0,16:.1,17:10,18:0,19:0,20:0,21:0,22:1,23:0,24:0,25:10,26:10,27:180,28:10,29:180}
for scale in (.92,1.08):
    for angle in (-180,-20,0,20,180):
        for frame in range(181):
            t=10+frame/60;cd=dict(base,**{})
            cd[27]=cd[29]=angle
            phi=math.copysign(min((t-10)*90,abs(angle)),angle)
            actual=evaluate(wpo,cd,t,35,scale)
            expected=tuple(x*scale for x in rot(tuple(a-r for a,r in zip(rot((24,9,173),phi),(20,7,170))),35))
            check(max(abs(a-z) for a,z in zip(actual,expected))<1e-8)
            n=evaluate(normal,cd,t,35,scale)
            expectedn=rot((1,0,1e-4),phi+35);ln=math.sqrt(sum(x*x for x in expectedn))
            check(max(abs(a-z/ln) for a,z in zip(n,expectedn))<1e-8)
        # Rebase at end or later: old angular motion reconstructed in new basis.
        cd=base.copy();cd.update({25:12.,26:12.,27:0.,28:10.,29:angle,14:math.cos(math.radians(-angle)),15:math.sin(math.radians(-angle))})
        for tp in (9.99,10,10.01,10.5,11.99,12,12.01):
            actual=evaluate(wpo,cd,12.1,35+angle,scale,True,tp)
            world=tuple(a+r*scale for a,r in zip(actual,rot((20,7,170),35+angle)))
            phi=math.copysign(min(max(tp-10,0)*90,abs(angle)),angle)
            expected=tuple(x*scale for x in rot((24,9,173),35+phi))
            check(max(abs(a-z) for a,z in zip(world,expected))<1e-8)
# Zero angular delta must retain original world drift (not rotate velocity).
for dt in (-.5,-.1,0,.2,.8):
    cd=base.copy();cd.update({27:0,29:0,3:10,5:60,6:-10,7:2,10:.7})
    value=evaluate(wpo,cd,10+dt,35)
    local=rot((4,2,3),35);d=min(max(dt,-.25),.7)
    check(max(abs(a-(v+d*s)) for a,v,s in zip(value,local,(60,-10,2)))<1e-8)
# Shared-controller adapter: entire cadence matrix, no physical calls during turn.
for population in (2500,5000,10000):
    for budget in (125,500):
        for fps in (30,60):
            state=AngularState(10.,180.)
            check(channels(state,AngularState())=={26:10.,27:180.,28:0.,29:0.})
            calls=[]
            def gate():calls.append(1);return True
            for frame in range(2*fps):
                check(not translation_gate(state,10+frame/fps,linear_reservation_live=False,ground_gate=gate,sweep_gate=gate,can_reserve=gate))
            check(not calls)
            sweep=(population+budget-1)//budget
            t=12+sweep/fps
            check(translation_gate(state,t,linear_reservation_live=False,ground_gate=gate,sweep_gate=gate,can_reserve=gate))
            check(len(calls)==3)
            check(not translation_gate(state,t,linear_reservation_live=True,ground_gate=gate,sweep_gate=gate,can_reserve=gate))
            check(len(calls)==3)
            check(not translation_gate(state,t,linear_reservation_live=False,ground_gate=lambda:False,sweep_gate=gate,can_reserve=gate))
            check(len(calls)==3)
# Resident surface is genuinely generated and connected; no VAT/normal override lost.
b._surface(ue,material,{},dict(Mottle=object(),DetailNormal=object()))
check({26,27}.issubset(dependencies(ml.outputs['MP_NORMAL'])))
check(any(n.kind=='MaterialExpressionDDX' for n in ml.nodes))
check(any(n.kind=='MaterialExpressionTextureSampleParameter2D' and n.props.get('parameter_name')=='DetailNormal' for n in ml.nodes))
manifest=json.loads((BASE/'generation.json').read_text())
check(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in manifest['inputs'].items()))
result={'status':'passed','checks':checks,'scope':'actual generated stock graph recorded/evaluated offline, NOT native compile/render',
        'sourceSha256':hashlib.sha256((BASE/'candidate_builder.py').read_bytes()).hexdigest(),'nodeCountWithResidentSurface':len(ml.nodes),
        'preservedInputs':True,'nativeLaunched':False,
        'testSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'controllerAdapterSha256':hashlib.sha256((BASE/'controller_adapter.py').read_bytes()).hexdigest()}
(BASE/'source-tests.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
