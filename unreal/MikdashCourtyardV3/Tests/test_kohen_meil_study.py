"""Source preservation for the outer-robe candidate; not rendered acceptance."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import build_kohen_meil_study as B


class MeilStudyTests(unittest.TestCase):
    def test_approved_face_rig_attributes_and_topology_survive(self):
        for follow_ephod in (False, True):
            with self.subTest(follow_ephod=follow_ephod):
                self.check_study(follow_ephod)

    def check_study(self, follow_ephod):
        before, binary = B.read_glb(B.SOURCE)
        saved_ease = B.K.MEIL_LOWER_EASE_CM
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'study.glb'
            receipt = B.build(path, 5, follow_ephod)
            after, result = B.read_glb(path)
            self.assertEqual(B.K.MEIL_LOWER_EASE_CM, saved_ease)
            self.assertEqual(receipt['matchedVertices'], 18074 if follow_ephod else 13170)
            self.assertGreater(receipt['changedVertices'], 0)
            doc = copy.deepcopy(after)
            changed = set()
            allowed_materials = {p['material'] for p in B.parts(0, follow_ephod)}
            for mesh in before['meshes']:
                for primitive in mesh['primitives']:
                    material = before['materials'][primitive['material']]['name']
                    for name, index in primitive['attributes'].items():
                        a = B.read_accessor(before, binary, index)
                        b = B.read_accessor(after, result, index)
                        if a != b:
                            self.assertIn(material, allowed_materials)
                            self.assertIn(name, ('POSITION', 'NORMAL'))
                            changed.add(index)
                            self.assertTrue(np.isfinite(b).all())
                            if name == 'POSITION':
                                self.assertEqual(after['accessors'][index]['min'], np.asarray(b).min(0).tolist())
                                self.assertEqual(after['accessors'][index]['max'], np.asarray(b).max(0).tolist())
                                doc['accessors'][index] = copy.deepcopy(before['accessors'][index])
                    index = primitive['indices']
                    self.assertEqual(B.read_accessor(before, binary, index), B.read_accessor(after, result, index))
            self.assertEqual(before, doc)
            for index in range(len(before['accessors'])):
                if index not in changed:
                    self.assertEqual(B.read_accessor(before, binary, index), B.read_accessor(after, result, index))
            with self.assertRaises(FileExistsError):
                B.build(path, 5)

    def test_rejects_unapproved_source_and_invalid_ease(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'out.glb'
            for ease in (0, -1, 6, float('nan')):
                with self.assertRaises(ValueError):
                    B.build(path, ease)
            source = Path(temp) / 'bad.glb'
            source.write_bytes(b'not approved')
            with patch.object(B, 'SOURCE', source), self.assertRaises(ValueError):
                B.build(path, 5)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
