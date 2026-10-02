"""Independent small numerical/negative cases; no Unreal invocation."""
import sys
sys.dont_write_bytecode=True
import json,io,unittest
import numpy as np
import inputs as I
from mapped_contact import point_triangle_distance_gap,hinge_angle,mapped_vertex
from test_witness import fd

class Operators(unittest.TestCase):
    def test_finite_triangle_interior_edge_vertex_derivatives(self):
        tri=np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.]])
        for point in (np.array([.5,.5,1.]),np.array([1.,-1.,1.]),np.array([-1.,-1.,1.])):
            geom=np.vstack((point,tri));_,J,_=point_triangle_distance_gap(point,tri)
            numeric=fd(lambda q:point_triangle_distance_gap(q[0],q[1:])[0],geom).ravel()
            self.assertLess(np.max(np.abs(J-numeric)),1e-7)

    def test_zero_distance_refuses_normal_invention(self):
        with self.assertRaises(ValueError):point_triangle_distance_gap(np.array([.5,.5,0.]),np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.]]))

    def test_hinge_angle_derivative(self):
        q=np.array([[0.,0.,0.],[2.,.1,0.],[.2,1.,.2],[1.,-1.,-.4]])
        _,J=hinge_angle(q);numeric=fd(lambda z:hinge_angle(z)[0],q).ravel()
        self.assertLess(np.max(np.abs(J-numeric)),1e-7)

    def test_rotation_covariance_nonzero_offset(self):
        q=np.array([[0.,0.,0.],[2.,.1,0.],[.2,1.,.2]]);w=np.array([.2,.3,.5]);r=np.array([.1,-.2,.3])
        R=I.s.Rotation.from_euler('xyz',[.4,-.2,.7]).as_matrix();t=np.array([2.,3.,4.])
        p,_=mapped_vertex(q,w,r);after,_=mapped_vertex(q@R.T+t,w,r)
        np.testing.assert_allclose(after,R@p+t,atol=1e-12)

    def test_preserved_failure_and_active_step_receipts(self):
        self.assertEqual(I.preserved(),33)
        r=json.loads((I.HERE/'closing_step01.json').read_text())
        self.assertTrue(r['optimizerSuccess']);self.assertEqual(r['activeContacts'],1)
        self.assertAlmostEqual(r['stepSeconds'],1/240,places=14)
        self.assertLess(min(r['gravityPredictorGaps']),0)
        self.assertGreaterEqual(min(r['contactGapMinusMarginAfter']),-1e-7)
        self.assertLess(r['stationarityMaxKgCmPerS2'],1e-5)
        self.assertLess(r['complementarityMax'],1e-7)
        self.assertFalse(r['garmentAcceptance']);self.assertFalse(r['restFractionUsed'])

def main():
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Operators))
    # Quantify nonrigid bending in the executed active step, not just energy code.
    run=np.load(I.HERE/'closing_step01.npz');model,*_=I.load();c=I.s.Layer(model['patterns'][1]);ids=run['coarseIds']
    selected=c.f[np.all(np.isin(c.f,ids),axis=1)];remap={int(v):i for i,v in enumerate(ids)}
    f=np.array([[remap[int(v)] for v in face] for face in selected]);adj={}
    for a,b,c0 in f:
        for i,j,k in ((a,b,c0),(b,c0,a),(c0,a,b)):adj.setdefault(tuple(sorted((i,j))),[]).append(k)
    changes=[]
    for (i,j),op in adj.items():
        if len(op)==2:
            q=[i,j,*op];a=hinge_angle(run['initial'][q])[0];b=hinge_angle(run['final'][q])[0]
            changes.append(abs(np.arctan2(np.sin(b-a),np.cos(b-a))))
    I.write('operator-tests01.json',dict(passed=result.wasSuccessful(),testsRun=result.testsRun,
        testOutput=stream.getvalue(),activeStepMaxDihedralChangeDegrees=float(np.rad2deg(max(changes))),
        V2FilesPreserved=I.preserved(),native=False,garmentAcceptance=False,
        sourceHashes={p.name:I.s.sha(p) for p in sorted(I.HERE.glob('*.py'))}))
    print(stream.getvalue());print('max bending angle change deg',np.rad2deg(max(changes)))
    assert result.wasSuccessful()

if __name__=='__main__':main()
