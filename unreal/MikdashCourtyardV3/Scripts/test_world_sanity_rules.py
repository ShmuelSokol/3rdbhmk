"""Offline checks for the world sanity scan's decision rules."""
import unittest

import world_sanity_rules as rules


def placement(pid, mesh="/Game/A.A", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return {"id": pid, "mesh": mesh, "loc": loc, "rot": rot, "scale": scale}


class SupportTests(unittest.TestCase):
    def test_floating_tank_on_roof_is_flagged(self):
        f = rules.classify_support(bottom_z=1230, top_z=1350, surface_z=1200, intended_airborne=False)
        self.assertEqual(f["kind"], "floating")
        self.assertEqual(f["gap_cm"], 30)

    def test_small_gap_is_tolerated(self):
        self.assertIsNone(rules.classify_support(103, 200, 100, False))

    def test_birds_are_allowed_in_the_air(self):
        self.assertIsNone(rules.classify_support(5000, 5050, 0, True))
        self.assertIsNone(rules.classify_support(5000, 5050, None, True))

    def test_nothing_below(self):
        self.assertEqual(rules.classify_support(0, 100, None, False)["kind"], "no_ground_below")

    def test_stall_sunk_into_new_paving(self):
        f = rules.classify_support(bottom_z=-30, top_z=250, surface_z=0, intended_airborne=False)
        self.assertEqual(f["kind"], "sunk")

    def test_wall_footing_into_ground_is_fine(self):
        self.assertIsNone(rules.classify_support(-200, 1800, 0, False))

    def test_fully_buried(self):
        self.assertEqual(rules.classify_support(-500, -100, 0, False)["kind"], "buried")


class WordTests(unittest.TestCase):
    def test_camel_case_and_paths_split(self):
        w = rules.words("SM_KeruvFriezeV2_Study03", "/Game/MikdashV3/OldSquare/Wall")
        for expected in ("keruv", "frieze", "study03", "old", "square", "wall"):
            self.assertIn(expected, w)

    def test_whole_words_only(self):
        # "bold" must not match "old"; "domestic" must not match "dome".
        self.assertEqual(rules.matched(rules.words("BoldDomestic"), ["old", "dome"]), [])


class DuplicateTests(unittest.TestCase):
    def test_exact_duplicates_grouped(self):
        g = rules.duplicate_groups([placement(0), placement(1), placement(2, loc=(500, 0, 0))])
        self.assertEqual(g, [[0, 1]])

    def test_pair_straddling_cell_edge(self):
        g = rules.duplicate_groups([placement(0, loc=(49.9, 0, 0)), placement(1, loc=(50.4, 0, 0))])
        self.assertEqual(g, [[0, 1]])

    def test_different_mesh_or_rotation_not_duplicate(self):
        self.assertEqual(rules.duplicate_groups([placement(0), placement(1, mesh="/Game/B.B")]), [])
        self.assertEqual(rules.duplicate_groups([placement(0), placement(1, rot=(0, 90, 0))]), [])

    def test_yaw_wraparound(self):
        g = rules.duplicate_groups([placement(0, rot=(0, 179.8, 0)), placement(1, rot=(0, -179.9, 0))])
        self.assertEqual(g, [[0, 1]])


if __name__ == "__main__":
    unittest.main()
