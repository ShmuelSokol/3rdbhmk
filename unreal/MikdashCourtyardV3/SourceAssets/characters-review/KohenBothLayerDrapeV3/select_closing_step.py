"""Deterministic source-kinematic selection, not cloth parameter tuning."""
import sys
sys.dont_write_bytecode=True
import numpy as np
import inputs as I

def main():
    model,bones,index,by,c,rest,faces,mp,rig=I.load();rows=[];previous=None
    for frame in range(73):
        a,b=I.pose(rig,bones,frame/240);v,f,_=I.s.body_arrays(model,a,b);tri=v[f[2039]]
        if previous is not None:
            n=np.cross(previous[1]-previous[0],previous[2]-previous[0]);n/=np.linalg.norm(n)
            rows.append(dict(frame0=frame-1,frame1=frame,t0=(frame-1)/240,t1=frame/240,
                             outwardNormalMotionCm=float((tri.mean(0)-previous.mean(0))@n)))
        previous=tri
    # Latest closing step before the first target, threshold only distinguishes
    # moving toward an exterior sample vs numerical noise. Not a cloth pass gate.
    candidates=[r for r in rows if r['frame1']<=71 and r['outwardNormalMotionCm']>.02]
    selected=candidates[-1] if candidates else None
    I.write('kinematic-step-selection01.json',dict(selected=selected,rows=rows,rule='Latest closing FootL231 step <=71/240 with outward motion >.02cm',
        noPhysicalParametersTuned=True,native=False,V2FilesPreserved=I.preserved()))
    print(selected)

if __name__=='__main__':main()
