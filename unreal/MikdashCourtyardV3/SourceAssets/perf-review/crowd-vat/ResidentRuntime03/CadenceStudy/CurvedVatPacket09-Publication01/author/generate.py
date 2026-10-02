from pathlib import Path
import hashlib,json
b=Path(__file__).resolve().parent
s=(b/'frozen/candidate_builder.py').read_text()
assert hashlib.sha256((b/'frozen/candidate_builder.py').read_bytes()).hexdigest()=='7e85710b87fa479a22a9ff6d9d2df14b912f3f5d6dcc2e7451b657a8071f371f'
def change(old,new):
 global s
 assert s.count(old)==1,(old,s.count(old));s=s.replace(old,new)
change('def previous_wpo(', (b/'stock_curve.py').read_text()+'\n\ndef previous_wpo(')
anchor="    old_phase = g.unary(e.MaterialExpressionFrac, g.op(add, data[16], g.op(mul, old_dt, data[18])))"
change(anchor,anchor+"\n    q=curve_eval(g,time,54);old_phase=curve_choose(g,q['enabled'],q['phase'],old_phase)")
anchor='    history_wpo = g.op(add, g.op(add, offset, correction), drift)'
change(anchor,anchor+'\n    history_wpo=curve_wpo(g,time,54,rest,old_delta,to_world,history_wpo)')
anchor='    walk_phase = g.unary(E.MaterialExpressionFrac, g.op(A, cd[0], g.op(M, dt, cd[4])))'
change(anchor,anchor+"\n    q=curve_eval(g,t,31);walk_phase=curve_choose(g,q['enabled'],q['phase'],walk_phase)")
anchor='    wpo = g.op(A, to_world(stock_posed_delta(g, rest, delta, angle)), drift)'
change(anchor,anchor+'\n    wpo=curve_wpo(g,t,31,rest,delta,to_world,wpo)')
anchor="    g.link(g.unary(E.MaterialExpressionNormalize, to_world(stock_rotate(g, normal, angle))), n_interp, ['VS'])"
change(anchor,"    angle=curve_choose(g,q['enabled'],q['yaw'],angle)\n    current_normal=g.unary(E.MaterialExpressionNormalize,to_world(stock_rotate(g,normal,angle)))\n    history_normal=curve_previous_normal(g,t,current_normal,clip,walk_frames,uvw,defaults,idle_n,idle_w,blend,negdt,to_world)\n    g.link(history_normal,n_interp,['VS'])")
s=s.replace('AngularVATStudy01','CurvedVatPacket09').replace('M_Angular_','M_Curved09_').replace('set(range(30))','set(range(77))').replace('30-float stock graph','77-float v9001 stock graph').replace("'customFloats':30","'customFloats':77,'packetVersion':9001")
(b/'candidate_builder.py').write_text(s)
(b/'generation.json').write_text(json.dumps({'inputSha256':hashlib.sha256((b/'frozen/candidate_builder.py').read_bytes()).hexdigest(),'outputSha256':hashlib.sha256((b/'candidate_builder.py').read_bytes()).hexdigest(),'customFloats':77,'version':9001,'prefixPreserved':30,'nativeInvoked':False},indent=2)+'\n')
