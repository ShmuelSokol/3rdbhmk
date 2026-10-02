# Stock-node implementation of CurvePacket.ush, embedded by generate.py.
def curve_if(g,a,b,greater,equal,less):
 n=g.make(g.ue.MaterialExpressionIf);n.set_editor_property('equals_threshold',0.0)
 for value,pin in [(a,'A'),(b,'B'),(greater,'A > B'),(equal,'A == B'),(less,'A < B')]:g.link(value,n,[pin])
 return n

def curve_choose(g,enabled,yes,no):return curve_if(g,enabled,g.const(1),no,yes,no)

def curve_eval(g,time,base):
 cache=getattr(g,'curve_cache',None)
 if cache is None:cache={};g.curve_cache=cache
 key=(id(time),base)
 if key in cache:return cache[key]
 e=g.ue;add=e.MaterialExpressionAdd;sub=e.MaterialExpressionSubtract;mul=e.MaterialExpressionMultiply;div=e.MaterialExpressionDivide
 A=lambda x,y:g.op(add,x,y);S=lambda x,y:g.op(sub,x,y);M=lambda x,y:g.op(mul,x,y);D=lambda x,y:g.op(div,x,y)
 V=lambda x,y,z:g.op(e.MaterialExpressionAppendVector,g.op(e.MaterialExpressionAppendVector,x,y),z)
 p=[g.custom_data(base+i,0,0,0) for i in range(23)];zero=g.const(0);one=g.const(1)
 R=g.op(e.MaterialExpressionMax,p[8],g.const(.001));duration=g.op(e.MaterialExpressionMax,p[13],g.const(.001))
 d=D(M(g.clamp(S(time,p[12]),zero,duration),p[11]),duration)
 arc=g.clamp(S(d,p[9]),zero,p[10]);theta=D(arc,R)
 def trig(kind,x):
  n=g.make(kind);n.set_editor_property('period',6.283185307179586);g.link(x,n,['Input']);return n
 along=A(g.op(e.MaterialExpressionMin,d,p[9]),M(R,trig(e.MaterialExpressionSine,theta)))
 across=A(M(R,S(one,trig(e.MaterialExpressionCosine,theta))),g.op(e.MaterialExpressionMax,S(S(d,p[9]),p[10]),zero))
 origin=V(p[1],p[2],p[3]);u=V(p[4],p[5],zero);v=V(p[6],p[7],zero);tail=V(p[17],p[18],p[19])
 root=A(A(origin,M(u,along)),M(v,across));endtheta=D(p[10],R)
 end=A(A(origin,M(u,A(p[9],M(R,trig(e.MaterialExpressionSine,endtheta))))),M(v,A(M(R,S(one,trig(e.MaterialExpressionCosine,endtheta))),g.op(e.MaterialExpressionMax,S(S(p[11],p[9]),p[10]),zero))))
 alpha=M(g.unary(e.MaterialExpressionSaturate,D(S(S(time,p[12]),duration),g.op(e.MaterialExpressionMax,p[20],g.const(.001)))),p[16])
 delta=S(tail,end);sq=M(delta,delta);norm=g.unary(e.MaterialExpressionSquareRoot,A(A(g.mask(sq,'r'),g.mask(sq,'g')),g.mask(sq,'b')))
 distance=A(d,M(norm,alpha));active=curve_if(g,p[0],one,curve_if(g,p[0],g.const(2),zero,one,zero),one,zero);enabled=curve_if(g,g.custom_data(30,0,0,0),g.const(9001),zero,active,zero)
 out={'root':g.lerp(root,tail,alpha),'yaw':A(p[14],M(M(p[15],theta),g.const(57.29577951308232))),'phase':g.unary(e.MaterialExpressionFrac,A(p[21],M(distance,p[22]))),'enabled':enabled}
 cache[key]=out;return out

def curve_wpo(g,time,base,rest,delta,to_world,legacy):
 q=curve_eval(g,time,base);posed=stock_posed_delta(g,rest,delta,q['yaw'])
 return curve_choose(g,q['enabled'],g.op(g.ue.MaterialExpressionAdd,q['root'],to_world(posed)),legacy)

def curve_previous_normal(g,time,current,clip,frames,uvw,defaults,idle_normal,idle_weight,blend,negdt,to_world):
 e=g.ue;add=e.MaterialExpressionAdd;sub=e.MaterialExpressionSubtract;mul=e.MaterialExpressionMultiply;div=e.MaterialExpressionDivide
 cd=lambda i:g.custom_data(i,1 if i==14 else 0,0,0)
 dt=g.clamp(g.op(sub,time,cd(17)),g.op(mul,negdt,g.const(-1)),cd(24))
 legacyphase=g.unary(e.MaterialExpressionFrac,g.op(add,cd(16),g.op(mul,dt,cd(18))))
 q=curve_eval(g,time,54);phase=curve_choose(g,q['enabled'],q['phase'],legacyphase)
 w=g.unary(e.MaterialExpressionSaturate,g.op(div,g.op(sub,time,cd(23)),blend))
 weight=g.lerp(g.unary(e.MaterialExpressionOneMinus,w),w,cd(22))
 walk=g.op(sub,g.op(mul,clip(phase,frames,uvw,'WalkNormalTexture',defaults['WalkNormalTexture']),g.const(2)),g.const(1))
 n=g.unary(e.MaterialExpressionNormalize,g.op(add,g.lerp(walk,idle_normal,weight),g.const3([0,0,1e-4])))
 old=stock_rotate(g,n,stock_angle(g,time,cd(28),cd(29)));x,y,z=[g.mask(old,c) for c in 'rgb']
 V=lambda a,b,c:g.op(e.MaterialExpressionAppendVector,g.op(e.MaterialExpressionAppendVector,a,b),c)
 old=V(g.op(sub,g.op(mul,cd(14),x),g.op(mul,cd(15),y)),g.op(add,g.op(mul,cd(15),x),g.op(mul,cd(14),y)),z)
 old=curve_choose(g,q['enabled'],stock_rotate(g,n,q['yaw']),old)
 old=g.unary(e.MaterialExpressionNormalize,to_world(old))
 selected=curve_if(g,time,cd(25),current,current,old)
 switch=g.make(e.MaterialExpressionPreviousFrameSwitch);g.link(current,switch,['Current Frame']);g.link(selected,switch,['Previous Frame']);return switch
