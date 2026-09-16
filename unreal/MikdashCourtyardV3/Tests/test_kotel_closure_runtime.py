"""Bounded engine-free input drift and generated C++ data fidelity checks (KotelRetainingWallV2)."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = load('kotel_data', 'Scripts/generate_kotel_closure_runtime.py')
W = load('kotel_wall', 'Scripts/generate_kotel_retaining_wall.py')


class KotelClosureRuntimeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wall = G.read_pinned(G.WALL, G.WALL_SHA)
        cls.plan = G.read_pinned(G.PLAN, G.PLAN_SHA)

    def test_pinned_header_and_canonical_input_unchanged(self):
        rendered = G.render(self.wall, self.plan)
        G.check_output(G.OUTPUT, rendered)
        self.assertNotIn(b'\r', rendered)
        self.assertEqual(G.read_pinned(G.WALL, G.WALL_SHA), self.wall)

    def test_wall_generator_reproduces_its_pinned_output(self):
        fresh = W.generate()
        self.assertEqual(json.dumps(fresh, separators=(',', ':')) + '\n',
                         G.WALL.read_text(encoding='utf-8'))

    def test_every_cpp_buffer_material_id_and_deck_transform_round_trips(self):
        # Parse the actual generated C++ initializers independently of the formatter.
        text = G.OUTPUT.read_text(encoding='utf-8')
        for name, key in [('Vertices', 'vertices'), ('Normals', 'normals'),
                          ('UVs', 'uv0'), ('Triangles', 'triangles')]:
            body = re.search(r'\b' + name + r'\[\w+\] = \{\n(.*?)\n\};', text, re.S).group(1)
            rows = json.loads('[' + body.replace('{', '[').replace('}', ']').rstrip(',') + ']')
            self.assertEqual(rows, self.wall[key], name)
        body = re.search(r'\bMaterialIds\[\w+\] = \{\n(.*?)\n\};', text, re.S).group(1)
        self.assertEqual(json.loads('[' + body.replace('\n', '').rstrip(',') + ']'), self.wall['materialIds'])
        body = re.search(r'\bDeckTransforms\[\w+\] = \{\n(.*?)\n\};', text, re.S).group(1)
        rows = json.loads('[' + body.replace('{', '[').replace('}', ']').rstrip(',') + ']')
        self.assertEqual(rows, [[r[k] for k in ('loc', 'rot', 'scale')] for r in self.plan['deck']])

    def test_header_carries_the_two_material_slots_and_probe_lane(self):
        text = G.OUTPUT.read_text(encoding='utf-8')
        self.assertIn('LimestoneMaterialPath = "' + G.LIMESTONE_PACKAGE, text)
        self.assertIn('MaterialCount = 2', text)
        self.assertIn('LegacyTriangleCount = %d' % self.wall['legacyTriangles'], text)
        self.assertIn('VertexColourByte = %d' % G.VERTEX_COLOUR_BYTE, text)
        lane = re.search(r'ProbeLaneFootingFrontXCm = (-?[\d.]+)', text)
        self.assertAlmostEqual(float(lane.group(1)), self.wall['probeLane']['footingFrontXcm'], places=6)

    def test_legacy_pieces_are_copied_from_the_v1_closure_unchanged(self):
        legacy = json.loads((ROOT / 'SourceAssets/context-review/KotelCutClosureV1/closure-study.json')
                            .read_text(encoding='utf-8'))
        count = self.wall['legacyTriangles']
        self.assertGreater(count, 0)
        legacy_vertices = {tuple(round(v, 6) for v in legacy['vertices'][i])
                           for face in legacy['triangles'] for i in face}
        for face in self.wall['triangles'][:count]:
            for i in face:
                self.assertIn(tuple(round(v, 6) for v in self.wall['vertices'][i]), legacy_vertices)

    def test_the_v1_liner_is_retained_in_full_behind_the_dressed_face(self):
        # Occlusion is >= V1 by construction only while every V1 triangle is still present:
        # 148 on the ashlar slot in front of the Western Wall, the rest as limestone liner.
        self.assertGreater(self.wall['linerTriangles'], 0)
        self.assertEqual(self.wall['legacyTriangles'] + self.wall['linerTriangles'], 841)
        first = self.wall['legacyTriangles'] + self.wall['linerTriangles']
        self.assertTrue(all(m == 0 for m in self.wall['materialIds'][self.wall['legacyTriangles']:first]))
        for kind in ('missing', 'partial'):
            wall = copy.deepcopy(self.wall)
            wall['linerTriangles'] = 0 if kind == 'missing' else wall['linerTriangles'] - 1
            with self.assertRaises(ValueError):
                G.validate(wall, self.plan)

    def test_native_reversal_faces_opposite_cross_product_without_normal_change(self):
        # Canonical cross agrees with supplied normals; UE (A,C,B) must reverse it.
        for a, b, c in self.wall['triangles']:
            p, q, r = [self.wall['vertices'][i] for i in (a, c, b)]
            area = G.cross([q[j]-p[j] for j in range(3)], [r[j]-p[j] for j in range(3)])
            normal = self.wall['normals'][a]
            self.assertLess(sum(area[j]*normal[j] for j in range(3)), 0)

    def test_byte_drift_even_equivalent_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'changed.json'
            path.write_bytes(G.PLAN.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'Pinned input bytes changed'):
                G.read_pinned(path, G.PLAN_SHA)

    def test_wrong_wall_provenance_is_rejected(self):
        wall = copy.deepcopy(self.wall)
        wall['sourceHashesSha256']['SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'source provenance changed'):
            G.validate(wall, self.plan)

    def test_reversed_canonical_face_or_out_of_range_index_is_rejected(self):
        for kind in ('winding', 'index'):
            wall = copy.deepcopy(self.wall)
            a, b, c = wall['triangles'][0]
            wall['triangles'][0] = [a, c, b] if kind == 'winding' else [a, b, len(wall['vertices'])]
            with self.assertRaises(ValueError):
                G.validate(wall, self.plan)

    def test_bad_material_ids_are_rejected(self):
        for kind in ('range', 'count', 'order'):
            wall = copy.deepcopy(self.wall)
            if kind == 'range':
                wall['materialIds'][-1] = 2
            elif kind == 'count':
                wall['materialIds'].pop()
            else:
                wall['materialIds'][0] = 0
            with self.assertRaises(ValueError):
                G.validate(wall, self.plan)

    def test_nonfinite_uv_and_degenerate_face_are_rejected(self):
        for kind in ('uv', 'face'):
            wall = copy.deepcopy(self.wall)
            if kind == 'uv':
                wall['uv0'][0][0] = float('nan')
            else:
                a, b, _ = wall['triangles'][0]
                wall['vertices'][b] = wall['vertices'][a][:]
            with self.assertRaises(ValueError):
                G.validate(wall, self.plan)

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
                G.validate(self.wall, plan)

    def test_header_edit_or_crlf_is_rejected_without_rewriting(self):
        expected = G.render(self.wall, self.plan)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'header.h'
            for changed in (expected + b'//edit\n', expected.replace(b'\n', b'\r\n')):
                path.write_bytes(changed)
                with self.assertRaisesRegex(ValueError, 'header bytes drifted'):
                    G.check_output(path, expected)
                self.assertEqual(path.read_bytes(), changed)


if __name__ == '__main__':
    unittest.main()
