"""Offline measurement regressions; these do not certify rendered clothing."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import measure_kohen_garment_clearance as M


def original_skin(v, joints, weights, matrices, offsets):
    out = np.zeros_like(v)
    for slot in range(4):
        out += weights[:, slot:slot + 1] * (
            np.einsum('nij,nj->ni', matrices[joints[:, slot]], v)
            + offsets[joints[:, slot]])
    return out


class ClearanceTests(unittest.TestCase):
    def test_signed_distance_is_independent_of_face_winding(self):
        triangle = np.array([[[0., 0., 0.], [10., 0., 0.], [0., 10., 0.]]])
        points = np.array([[2., 2., 1.], [2., 2., -1.], [-2., 0., 1.]])
        expected = np.array([1., -1., np.sqrt(5.)])
        np.testing.assert_allclose(M.nearest_signed(points, triangle, np.array([1.])), expected)
        np.testing.assert_allclose(M.nearest_signed(points, triangle, np.array([-1.])), -expected)
        np.testing.assert_allclose(
            M.nearest_signed(points, triangle[:, [0, 2, 1]], np.array([-1.])), expected)

    def test_skin_reference_on_actual_garments(self):
        bones, index, parts, influence, robe, _, outer, _ = M.body_parts('kohen')
        selected = [p for p in parts if p['name'] in (robe, outer)
                    or p['name'].startswith(M.LEG_PREFIXES)]
        arrays = [M.skin_arrays(p, influence, index) for p in selected]
        for _, path, clip, _ in M.CLIPS:
            rig = M.Rig(path, clip)
            for fraction in (0, .17, .5, .83, 1):
                matrices, offsets = M.joint_affines(rig, rig.pose(rig.duration * fraction), bones)
                for vertices, joints, weights in arrays:
                    np.testing.assert_array_equal(
                        M.skin(vertices, joints, weights, matrices, offsets),
                        original_skin(vertices, joints, weights, matrices, offsets))

    def test_dense_and_empty_influences_match_original(self):
        rng = np.random.default_rng(861)
        vertices = rng.normal(size=(17, 3))
        joints = rng.integers(0, 5, size=(17, 4))
        weights = rng.random((17, 4))
        weights /= weights.sum(axis=1)[:, None]
        matrices = rng.normal(size=(5, 3, 3))
        offsets = rng.normal(size=(5, 3))
        for w in (weights, np.zeros_like(weights)):
            np.testing.assert_array_equal(M.skin(vertices, joints, w, matrices, offsets),
                                          original_skin(vertices, joints, w, matrices, offsets))

    def test_resident_policy_does_not_leak_to_other_bodies(self):
        def resident(*args):
            M.LEG_PREFIXES = ('Leg', 'Foot', 'Toe')
            M.OUTER_TOP_CAP_CM = 140.0
            M.OUTER_ANGLE = (4.7, .3)
        for body in ('current', 'kohen'):
            with patch.object(M, '_v4_body', side_effect=resident):
                M.body_parts('v4:fixture')
            M.body_parts(body)
            self.assertEqual(M.LEG_PREFIXES, ('Shin', 'Foot'))
            self.assertEqual(M.OUTER_TOP_CAP_CM, 80.0)
            self.assertIsNone(M.OUTER_ANGLE)

    def test_pruning_matches_unpruned_signed_distance(self):
        rng = np.random.default_rng(508)
        centres = rng.uniform(-30, 30, (500, 1, 3))
        triangles = centres + rng.normal(size=(500, 3, 3))
        triangles[0, 1:] = triangles[0, 0]  # Degenerate face is still a point/edge.
        triangles[1] = triangles[2]       # Preserve first-index ties.
        signs = rng.choice([-1., 1.], 500)
        points = np.concatenate([rng.uniform(-25, 25, (150, 3)), triangles[:3, 0]])
        with patch.object(M, 'distance_candidates', side_effect=lambda p, t, s: s):
            reference = M.nearest_signed(points, triangles, signs)
        np.testing.assert_array_equal(M.nearest_signed(points, triangles, signs), reference)

    def test_pruning_matches_actual_posed_garments(self):
        bones, index, parts, influence, robe, segments, _, _ = M.body_parts('kohen')
        garment = next(p for p in parts if p['name'] == robe)
        v, j, w = M.skin_arrays(garment, influence, index)
        _, faces, _, _ = M.loft_triangles(garment, segments)
        signs = M.tube_signs(v, faces)
        _, path, clip, _ = M.CLIPS[0]
        rig = M.Rig(path, clip)
        a, b = M.joint_affines(rig, rig.pose(.52), bones)
        posed = M.skin(v, j, w, a, b)
        points = posed[::181] + np.array([.1, -.2, .05])
        with patch.object(M, 'distance_candidates', side_effect=lambda p, t, s: s):
            reference = M.nearest_signed(points, posed[faces], signs)
        np.testing.assert_array_equal(M.nearest_signed(points, posed[faces], signs), reference)


if __name__ == '__main__':
    unittest.main()
