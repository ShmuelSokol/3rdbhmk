"""Focused numerical/admission regressions; no native imports or launches."""
import copy
import unittest
from unittest.mock import patch
import numpy as np
import measurement as M


class Envelopes(unittest.TestCase):
    def layout(self, frames=3):
        return dict(width=3, height=frames*2, rowsPerFrame=2, frames=frames,
                    sizeBBox=[2., 4., 6.], minBBox=[-1., -2., -3.], uvChannel=2)

    def test_roundtrip_vertex_ids_multiple_rows(self):
        d=self.layout(); ids=np.arange(6)
        np.testing.assert_array_equal(M.vertex_ids(M.derived_uv(ids,d),d),ids)

    def test_wrong_center_refused(self):
        d=self.layout(); uv=M.derived_uv(np.arange(6),d);uv[0,0]=0
        with self.assertRaises(ValueError):M.vertex_ids(uv,d)

    def test_duplicate_address_refused(self):
        d=self.layout();uv=M.derived_uv(np.arange(6),d);uv[1]=uv[0]
        with self.assertRaises(ValueError):M.vertex_ids(uv,d)

    def test_out_of_frame_refused(self):
        d=self.layout();uv=M.derived_uv(np.arange(6),d);uv[0,1]=.9
        with self.assertRaises(ValueError):M.vertex_ids(uv,d)

    def test_atlas_layout_refused(self):
        d=self.layout();d['height']+=1
        with self.assertRaises(ValueError):M.vertex_ids(np.zeros((2,2)),d)

    def test_actual_dimensions_all_frames_and_loop_seam(self):
        for width,rows in [(3589,5),(3647,4)]:
            for frames in (72,192):
                d=dict(width=width,height=rows*frames,rowsPerFrame=rows,frames=frames)
                ids=np.arange(width*rows);uv=M.derived_uv(ids,d)
                for frame in range(frames+1):
                    x,y=M.sample_addresses(uv,d,frame)
                    np.testing.assert_array_equal(x,ids%width)
                    np.testing.assert_array_equal(y,ids//width+(frame%frames)*rows)

    def test_idle_uv_requires_rescaling_height(self):
        walk=self.layout(3);idle=self.layout(8);ids=np.arange(6)
        x,y=M.sample_addresses(M.derived_uv(ids,walk),idle,0)
        self.assertFalse(np.array_equal(y,ids//3))
        x,y=M.sample_addresses(M.derived_uv(ids,idle),idle,0)
        np.testing.assert_array_equal(y,ids//3)

    def test_frame_decode_stride_and_reference(self):
        d=self.layout();t=np.zeros((6,3,4));t[2:4,:,:3]=.5
        reference=np.array([[7.,8.,9.]]*6);ids=np.arange(6)
        np.testing.assert_array_equal(M.decode_frame(t,reference,ids,d,1),reference)
        np.testing.assert_array_equal(M.decode_frame(t,reference,ids,d,0),reference+[-1,-2,-3])

    def test_wrong_texture_shape_refused(self):
        with self.assertRaises(ValueError):M.decode_frame(np.zeros((2,3,4)),np.zeros((6,3)),np.arange(6),self.layout(),0)

    def test_wrong_frame_refused(self):
        with self.assertRaises(ValueError):M.decode_frame(np.zeros((6,3,4)),np.zeros((6,3)),np.arange(6),self.layout(),3)

    def test_convex_interpolation_blending_triangles_and_yaw(self):
        # Random testing supports the written convexity proof; it is not the proof.
        rng=np.random.default_rng(81302);points=rng.normal(size=(24,3))*[60,40,90]
        bound=M.extrema(points)
        for _ in range(150):
            weights=rng.random(24);weights/=weights.sum();p=weights@points
            yaw=rng.uniform(-np.pi,np.pi);c,s=np.cos(yaw),np.sin(yaw)
            rotated=np.array([c*p[0]-s*p[1],s*p[0]+c*p[1],p[2]])
            self.assertLessEqual(np.linalg.norm(rotated[:2]),bound['radiusCm']+1e-10)
            self.assertGreaterEqual(rotated[2],bound['minZCm']);self.assertLessEqual(rotated[2],bound['maxZCm'])

    def test_negative_min_z_and_scale_exactly_once(self):
        b=dict(radiusCm=60.,minZCm=-.5,maxZCm=180.)
        for s in M.SCALES:
            r=M.scale_bound(b,s);self.assertEqual(r['minZCm'],-.5*s)
            self.assertEqual(r['radiusCm'],60*s)
            self.assertEqual(r['enclosingCapsuleHalfHeightCm'],r['heightCm']/2+r['radiusCm'])

    def test_different_root_blend_needs_both_trajectories(self):
        # A local body disc cannot absorb an arbitrary transport root displacement.
        p=np.array([[10.,0.,0.]]);q=p+[100,0,0]
        self.assertGreater(np.linalg.norm(((p+q)/2)[0,:2]),M.extrema(p)['radiusCm'])

    def test_nonfinite_or_negative_allowance_refused(self):
        for p,m in [(np.array([[np.nan,0,0]]),0),(np.zeros((1,3)),-1)]:
            with self.assertRaises(ValueError):M.extrema(p,m)

    def test_scale_refusals(self):
        for scale in (0,-1,float('inf')):
            with self.assertRaises(ValueError):M.scale_bound(dict(radiusCm=1,minZCm=0,maxZCm=2),scale)

    def test_current_accepted_export_and_failed_receipt_refusal(self):
        config=M.read(M.HERE/'inputs.json');native=M.accepted_export(config)
        self.assertEqual(len(native['textures']),2)
        original=M.read
        def altered(path):
            value=original(path)
            if str(path).endswith('accepted-export.json'):
                value=copy.deepcopy(value);value['wrapper']['status']='failed'
            return value
        with patch.object(M,'read',altered),self.assertRaises(ValueError):M.accepted_export(config)

    def test_incomplete_drain_refused_even_with_cleanup(self):
        config=M.read(M.HERE/'inputs.json');original=M.read
        def altered(path):
            value=original(path)
            if str(path).endswith('accepted-export.json'):
                value=copy.deepcopy(value);value['wrapper']['terminalPoll']['activeProcesses']=1
            return value
        with patch.object(M,'read',altered),self.assertRaises(ValueError):M.accepted_export(config)

    def test_all_archived_input_pins(self):
        M.check_pins(M.read(M.HERE/'inputs.json'))


class InputFailures(unittest.TestCase):
    def test_missing(self):
        with self.assertRaises(ValueError):M.check_pins({'inputs':{'absent.png':{'bytes':0,'sha256':'bad'}}})
    def test_corrupt(self):
        with self.assertRaises(ValueError):M.check_pins({'inputs':{'data/Man_Elder/idle-position.png':{'bytes':0,'sha256':'bad'}}})
    def test_traversal(self):
        with self.assertRaises(ValueError):M.check_pins({'inputs':{'../escape':{'bytes':0,'sha256':'bad'}}})

if __name__=='__main__':unittest.main(verbosity=2)
