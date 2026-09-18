"""Source-only neck correction tests; engine lighting acceptance remains owed."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import build_kohen_neck_tone_study as N


class NeckTests(unittest.TestCase):
    def test_smooth_blend_preserves_face_alpha_and_neck_variation(self):
        heights = np.array([140, 145, 150, 153, 156, 160, 168])
        colors = np.array([[.6, .5, .4, 1], [.8, .7, .6, 1], [.7, .6, .5, 1],
                           [.7, .6, .5, 1], [.4, .3, .2, 1], [.5, .4, .3, 1],
                           [.6, .2, .1, 1]])
        result, report = N.correct(heights, colors)
        np.testing.assert_array_equal(result[heights >= 156], colors[heights >= 156])
        np.testing.assert_array_equal(result[:, 3], colors[:, 3])
        np.testing.assert_allclose(result[:2, :3].mean(axis=0), colors[4:6, :3].mean(axis=0))
        np.testing.assert_allclose(result[0, :3] / result[1, :3], colors[0, :3] / colors[1, :3])
        self.assertEqual(report['affectedVertices'], 4)

    def test_export_preserves_all_other_accessors_and_refuses_overwrite(self):
        before, binary_before = N.read_glb(N.SOURCE)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'study.glb'
            report = N.build(output)
            after, binary_after = N.read_glb(output)
            self.assertEqual(before, after)
            heads = [p for m in before['meshes'] for p in m['primitives']
                     if before['materials'][p['material']]['name'] == 'KG_MHHead']
            color_index = heads[0]['attributes']['COLOR_0']
            for index in range(len(before['accessors'])):
                if index != color_index:
                    self.assertEqual(N.read_accessor(before, binary_before, index),
                                     N.read_accessor(after, binary_after, index))
            self.assertTrue(report['onlyBelowJawHeadRGBBytesChanged'])
            self.assertEqual(report['affectedVertices'], 2139)
            with self.assertRaises(FileExistsError):
                N.build(output)

    def test_rejects_missing_regions_and_unapproved_source(self):
        with self.assertRaises(ValueError):
            N.correct([160, 170], [[.3, .2, .1, 1], [.3, .2, .1, 1]])
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'wrong.glb'
            source.write_bytes(b'not the approved face')
            with self.assertRaises(ValueError):
                N.build(Path(temporary) / 'out.glb', source)


if __name__ == '__main__':
    unittest.main()
