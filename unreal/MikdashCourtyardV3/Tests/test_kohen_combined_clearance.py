"""Regression: rounded-zero penetrations must not authorize study composition."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import combine_kohen_studies as C


class ClearanceReceiptTests(unittest.TestCase):
    def setUp(self):
        frames = dict(walk=288, tend=601, idle=97)
        self.report = dict(candidate=dict(kneeTopCm=65, kneeBottomCm=20, lowerEaseCm=0, hemBandCm=6),
            sourceHashes={Path(m.__file__).name: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
                          for m in (C.K, C.M, C.S)}, clips={})
        for name, path, _, rate in C.M.CLIPS:
            self.report['clips'][name] = dict(framesSampled=frames[name], sampleRateHz=rate,
                animationSourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                maxLegOutsideRobeCm=0.0, maxKetonetOutsideMeilCm=0.0, framesWithAnyClipping=0,
                worst=dict(cm=0.0, t=None), worstKetonetOutsideMeil=dict(cm=0.0, t=None),
                perFrameMaxCm=[0.0] * frames[name])

    def test_clean_receipt(self):
        C.validate_clearance(self.report)

    def test_subrounding_leg_hit(self):
        # The real checker preserves the hit count/time when 0.0004cm rounds to0.
        row = self.report['clips']['walk']
        row['framesWithAnyClipping'] = 1
        row['worst']['t'] = .3
        with self.assertRaises(ValueError):
            C.validate_clearance(self.report)

    def test_subrounding_outer_hit(self):
        self.report['clips']['walk']['worstKetonetOutsideMeil']['t'] = .3
        with self.assertRaises(ValueError):
            C.validate_clearance(self.report)

    def test_different_measurement_sources_or_configuration(self):
        cases = [(['sourceHashes', Path(C.M.__file__).name], '0' * 64),
                 (['clips', 'walk', 'animationSourceSha256'], '0' * 64),
                 (['clips', 'walk', 'sampleRateHz'], 24),
                 (['candidate', 'lowerEaseCm'], 5),
                 (['candidate', 'hemBandCm'], 20)]
        for path, value in cases:
            report = copy.deepcopy(self.report)
            target = report
            for key in path[:-1]: target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                C.validate_clearance(report)


if __name__ == '__main__':
    unittest.main()
