"""Bounded engine-free input drift and generated C++ data fidelity checks."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('kotel_data', ROOT / 'Scripts/generate_kotel_closure_runtime.py')
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)


class KotelClosureRuntimeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = G.read_pinned(G.CLOSURE, G.CLOSURE_SHA)
        cls.plan = G.read_pinned(G.PLAN, G.PLAN_SHA)

    def test_pinned_header_and_canonical_input_unchanged(self):
        rendered = G.render(self.closure, self.plan)
        G.check_output(G.OUTPUT, rendered)
        self.assertNotIn(b'\r', rendered)
        self.assertEqual(G.read_pinned(G.CLOSURE, G.CLOSURE_SHA), self.closure)

    def test_every_cpp_buffer_and_deck_transform_round_trips(self):
        # Parse the actual generated C++ initializers independently of the formatter.
        text = G.OUTPUT.read_text(encoding='utf-8')
        for name, key in [('Vertices', 'vertices'), ('Normals', 'normals'),
                          ('UVs', 'uv0'), ('Triangles', 'triangles')]:
            body = re.search(r'\b' + name + r'\[\w+\] = \{\n(.*?)\n\};', text, re.S).group(1)
            rows = json.loads('[' + body.replace('{', '[').replace('}', ']').rstrip(',') + ']')
            self.assertEqual(rows, self.closure[key], name)
        body = re.search(r'\bDeckTransforms\[\w+\] = \{\n(.*?)\n\};', text, re.S).group(1)
        rows = json.loads('[' + body.replace('{', '[').replace('}', ']').rstrip(',') + ']')
        self.assertEqual(rows, [[r[k] for k in ('loc', 'rot', 'scale')] for r in self.plan['deck']])

    def test_native_reversal_faces_opposite_cross_product_without_normal_change(self):
        # Canonical cross agrees with supplied normals; UE (A,C,B) must reverse it.
        for a, b, c in self.closure['triangles']:
            p, q, r = [self.closure['vertices'][i] for i in (a, c, b)]
            area = G.cross([q[j]-p[j] for j in range(3)], [r[j]-p[j] for j in range(3)])
            normal = self.closure['normals'][a]
            self.assertLess(sum(area[j]*normal[j] for j in range(3)), 0)

    def test_byte_drift_even_equivalent_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'changed.json'
            path.write_bytes(G.PLAN.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'Pinned input bytes changed'):
                G.read_pinned(path, G.PLAN_SHA)

    def test_wrong_plan_provenance_is_rejected(self):
        closure = copy.deepcopy(self.closure)
        closure['sourceHashesSha256']['SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'source provenance changed'):
            G.validate(closure, self.plan)

    def test_reversed_canonical_face_or_out_of_range_index_is_rejected(self):
        for kind in ('winding', 'index'):
            closure = copy.deepcopy(self.closure)
            a, b, c = closure['triangles'][0]
            closure['triangles'][0] = [a, c, b] if kind == 'winding' else [a, b, 2523]
            with self.assertRaises(ValueError):
                G.validate(closure, self.plan)

    def test_nonfinite_uv_and_degenerate_face_are_rejected(self):
        for kind in ('uv', 'face'):
            closure = copy.deepcopy(self.closure)
            if kind == 'uv':
                closure['uv0'][0][0] = float('nan')
            else:
                a, b, _ = closure['triangles'][0]
                closure['vertices'][b] = closure['vertices'][a][:]
            with self.assertRaises(ValueError):
                G.validate(closure, self.plan)

    def test_changed_deck_count_rotation_height_are_rejected(self):
        for kind in ('count', 'rotation', 'height'):
            plan = copy.deepcopy(self.plan)
            if kind == 'count':
                plan['deck'].pop()
            elif kind == 'rotation':
                plan['deck'][0]['rot'][2] = 90
            else:
                plan['deck'][0]['loc'][2] += 1
            with self.assertRaisesRegex(ValueError, 'Deck .* changed'):
                G.validate(self.closure, plan)

    def test_lost_exterior_coverage_or_internal_closure_is_rejected(self):
        for key, value in [('exteriorLengthWithoutSourceTerrainCm', 1), ('internalLevelEdgesExcluded', 0)]:
            closure = copy.deepcopy(self.closure)
            closure[key] = value
            with self.assertRaisesRegex(ValueError, 'scope/coverage changed'):
                G.validate(closure, self.plan)

    def test_header_edit_or_crlf_is_rejected_without_rewriting(self):
        expected = G.render(self.closure, self.plan)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'header.h'
            for changed in (expected + b'//edit\n', expected.replace(b'\n', b'\r\n')):
                path.write_bytes(changed)
                with self.assertRaisesRegex(ValueError, 'header bytes drifted'):
                    G.check_output(path, expected)
                self.assertEqual(path.read_bytes(), changed)


if __name__ == '__main__':
    unittest.main()
