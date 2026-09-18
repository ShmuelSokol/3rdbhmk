"""Regression checks for accepting real CSV performance windows."""
import csv
import tempfile
import unittest
from pathlib import Path

from analyze_crowd_frametime import summarise


class FrameWindowTests(unittest.TestCase):
    def capture(self, rows, settle=1, record=2):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.csv'
            with path.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream)
                writer.writerow(['EVENTS', 'FrameTime', 'GPUTime'])
                writer.writerows(rows)
            return summarise(path, settle, record)

    def test_fixed_window_ignores_later_slow_frames(self):
        result = self.capture([['', 100, 25]] * 40 + [['', 500, 400]] * 10)
        self.assertEqual(result['frame']['median'], 100)
        self.assertAlmostEqual(result['recordSeconds'], 2, delta=0.11)

    def test_truncated_capture_rejected(self):
        with self.assertRaises(RuntimeError):
            self.capture([['', 100, 25]] * 20)

    def test_invalid_frame_rejected(self):
        for value in ('oops', 'nan', 'inf', -1, 0):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.capture([['', value, 25]] + [['', 100, 25]] * 40)

    def test_invalid_window_metric_rejected(self):
        for value in ('nan', 'inf', 'oops', -1):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.capture([['', 100, value]] * 40)

    def test_settle_crossing_stall_is_not_a_recording(self):
        with self.assertRaises(RuntimeError):
            self.capture([['', 3000, 25]])


if __name__ == '__main__':
    unittest.main()
