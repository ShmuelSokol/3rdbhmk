"""Preserve source roof pairs while retargeting visibility to the Haram hide set."""
import json
import unittest

import generate_legacy_roof_runtime as generator


class HaramRoofTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(generator.PLAN.read_text(encoding='utf-8-sig'))
        self.labels = generator.haram_labels()
        self.rows, self.owners = generator.repartition(self.plan, self.labels)

    def test_all_geometry_and_owner_assignments_preserved(self):
        for before, after in zip(self.plan['owners'], self.rows):
            self.assertEqual({k: v for k, v in before.items() if k != 'zone'},
                             {k: v for k, v in after.items() if k != 'zone'})

    def test_visibility_follows_exact_owner_membership(self):
        for row in self.rows:
            self.assertEqual(row['zone'] == 'precinct', row['buildingLabel'] in self.labels)
        self.assertEqual(len(self.owners), 18)
        self.assertEqual(sum(r['zone'] == 'precinct' for r in self.rows), 118)

    def test_surrounding_city_roofs_restored(self):
        restored = [after for before, after in zip(self.plan['owners'], self.rows)
                    if before['zone'] == 'precinct' and after['zone'] == 'kept']
        self.assertEqual(len(restored), 1145)
        self.assertEqual(self.rows[2096]['zone'], 'precinct')

    def test_wrong_policy_rejected(self):
        with self.assertRaises(ValueError):
            generator.repartition(self.plan, set())


if __name__ == '__main__':
    unittest.main()
