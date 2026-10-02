import math,struct
from types import SimpleNamespace

def f32(x):
 if isinstance(x,tuple):return tuple(f32(v) for v in x)
 return struct.unpack("f",struct.pack("f",x))[0]

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
        k=node.kind[len('MaterialExpression'):] if node.kind.startswith('MaterialExpression') else node.kind;p=node.props
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
            fn={'SquareRoot':math.sqrt,'Abs':abs,'Sign':lambda x:(x>0)-(x<0),'Frac':lambda x:x-math.floor(x),'Floor':math.floor,
                'Saturate':lambda x:min(max(x,0),1),'OneMinus':lambda x:1-x,
                'Sine':lambda x:math.sin(x*2*math.pi/p['period']),'Cosine':lambda x:math.cos(x*2*math.pi/p['period'])}[k]
            v=tuple(fn(x) for x in a) if isinstance(a,tuple) else fn(a)
        v=f32(v);cache[key]=v;return v
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