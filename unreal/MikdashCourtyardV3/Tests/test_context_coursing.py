"""Projection invariants against the actual HLSL swizzles, without Unreal."""
import importlib.util
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('context_materials', ROOT / 'Scripts/release_context_materials.py')
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)


def swizzle(vector, pattern):
    return tuple(vector['xyz'.index(c)] for c in pattern)


class ProjectionTests(unittest.TestCase):
    def test_courses_stay_horizontal_on_both_wall_axes(self):
        code = context.HLSL_TRIPLANAR_SURFACE
        for axis, horizontal in (('X', (0, 1, 0)), ('Y', (1, 0, 0))):
            uv = re.search(r'uv' + axis + r' = p\.([xyz]{2});', code)[1]
            self.assertEqual(swizzle((0, 0, 1), uv), (0, 1))
            self.assertEqual(swizzle(horizontal, uv), (1, 0))

    def test_roughness_and_albedo_use_identical_coordinates(self):
        code = context.HLSL_TRIPLANAR_SURFACE
        for axis in 'XYZ':
            self.assertIn('AlbedoSampler, uv' + axis + ')', code)
            self.assertIn('RoughSampler, uv' + axis + ')', code)

    def test_normals_sample_the_same_wall_coordinates(self):
        for axis in 'XY':
            surface = re.search(r'uv' + axis + r' = p\.([xyz]{2});', context.HLSL_TRIPLANAR_SURFACE)[1]
            normal = re.search(r's' + axis + r' = Texture2DSample\(Nrm, NrmSampler, p\.([xyz]{2})\)', context.HLSL_TRIPLANAR_NORMAL)[1]
            self.assertEqual(surface, normal)

    def test_normal_tangent_axes_match_texture_axes(self):
        code = context.HLSL_TRIPLANAR_NORMAL
        for axis, outward, horizontal in (('X', (1, 0, 0), (0, 1, 0)), ('Y', (0, 1, 0), (1, 0, 0))):
            output = re.search(r't' + axis + r'\.([xyz]{3}) \* w\.' + axis.lower(), code)[1]
            # A tangent-space U bump must point along the wall; V must point up.
            self.assertEqual(swizzle((1, 0, 0), output), horizontal)
            self.assertEqual(swizzle((0, 1, 0), output), (0, 0, 1))
            self.assertEqual(swizzle((0, 0, 1), output), outward)
            self.assertEqual(swizzle((0, 0, -1), output), tuple(-v for v in outward))
            n_components = re.search(r't' + axis + r'\.xy \+ n\.([xyz]{2})', code)[1]
            # An unperturbed tilted normal must reassemble in world space.
            n = (0.3, 0.4, 0.5)
            t = swizzle(n, n_components) + (n['XYZ'.index(axis)],)
            self.assertEqual(swizzle(t, output), n)

    def test_roof_projection_is_unchanged(self):
        self.assertIn('uvZ = p.xy * RoofScale;', context.HLSL_TRIPLANAR_SURFACE)
        self.assertIn('NrmSampler, p.xy * RoofScale)', context.HLSL_TRIPLANAR_NORMAL)
        self.assertIn('tZ.xyz * w.z', context.HLSL_TRIPLANAR_NORMAL)


if __name__ == '__main__':
    unittest.main()
