"""Offline frozen-table guards. These do not claim native engine/visual acceptance."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('roof_generator', ROOT/'Scripts/generate_legacy_roof_runtime.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

class RuntimeRoofDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = gen.PLAN.read_bytes()
        cls.plan = json.loads(cls.raw.decode('utf-8-sig'))
        cls.generated = gen.OUTPUT.read_text(encoding='utf-8')

    def test_pinned_hash_and_reproducibility(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), gen.PLAN_SHA)
        self.assertEqual(self.generated, gen.render(self.plan))

    def test_all_12014_translations_survive_cpp_float_roundtrip(self):
        body = self.generated.split('TranslationCm[PairCount][6] = {\n')[1].split('\n};')[0]
        rows = re.findall(r'\{([^{}]+)\}', body)
        self.assertEqual(len(rows), 6007)
        max_error = 0.0
        for text, expected in zip(rows, self.plan['owners']):
            actual = [struct.unpack('<f', struct.pack('<f',float(v[:-1])))[0] for v in text.split(',')]
            for offset,key in ((0,'tankTranslationCm'),(3,'panelTranslationCm')):
                error = sum((actual[offset+i]-v)**2 for i,v in enumerate(expected[key]))**.5
                max_error = max(max_error,error)
                self.assertLessEqual(error,.1)
        self.assertEqual(max_error, 0.0)

    def test_precinct_indices_resolve_to_exact_owner_and_kept_complement(self):
        owners = re.findall(r'"(SM_JerusalemBuildings_[^"]+)"', self.generated)
        self.assertEqual(len(owners), 179)
        body = self.generated.split('PrecinctPairs[PrecinctCount] = {\n')[1].split('\n};')[0]
        rows = [tuple(map(int,m)) for m in re.findall(r'\{(\d+),(\d+)\}',body)]
        self.assertEqual(len(rows), 1263)
        self.assertEqual(len(set(i for i,_ in rows)),1263)
        for i,owner in rows:
            self.assertEqual(self.plan['owners'][i]['zone'],'precinct')
            self.assertEqual(owners[owner], self.plan['owners'][i]['buildingLabel'])
        kept = set(range(6007))-set(i for i,_ in rows)
        self.assertEqual(len(kept),4744)
        self.assertTrue(all(self.plan['owners'][i]['zone']=='kept' for i in kept))

    def test_duplicate_or_reordered_source_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['owners'][1]['sourceIndex'] = 0
        with self.assertRaisesRegex(ValueError, 'order/count'): gen.render(plan)

    def test_nonfinite_translation_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['owners'][0]['panelTranslationCm'][1] = float('nan')
        with self.assertRaisesRegex(ValueError, 'Nonfinite'): gen.render(plan)

    def test_float_precision_regression_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['owners'][0]['tankTranslationCm'][0] = 10000000.2
        with self.assertRaisesRegex(ValueError, 'precision'): gen.render(plan)

    def test_unknown_owner_or_zone_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['owners'][0]['buildingLabel'] = 'Actor_Guess'
        with self.assertRaisesRegex(ValueError, 'family'): gen.render(plan)
        plan = copy.deepcopy(self.plan)
        plan['owners'][0]['zone'] = 'other'
        with self.assertRaisesRegex(ValueError, 'count'): gen.render(plan)

    def test_owner_membership_cannot_cross_zones(self):
        plan = copy.deepcopy(self.plan)
        kept = next(r for r in plan['owners'] if r['zone']=='kept')
        inside = next(r for r in plan['owners'] if r['zone']=='precinct')
        inside['buildingLabel'] = kept['buildingLabel']
        with self.assertRaisesRegex(ValueError, 'both zones'): gen.render(plan)

    def test_hide_policy_fingerprint_matches_native_audit(self):
        audit=json.loads((ROOT/'SourceAssets/enclosure-review/modern-restore-audit-Candidate48-20260911T123409921279Z.json').read_text())
        self.assertEqual(audit['hideList']['fingerprint'],gen.HIDE_FINGERPRINT)
        self.assertEqual((audit['hideList']['found'],audit['hideList']['missing'],audit['hideList']['duplicated']),(269,0,0))

if __name__ == '__main__': unittest.main(verbosity=2)
