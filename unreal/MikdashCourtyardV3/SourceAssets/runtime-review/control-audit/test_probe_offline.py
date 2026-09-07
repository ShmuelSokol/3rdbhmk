"""Offline boundary tests: no Unreal module or process required."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class ProbeBoundaryTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('control_probe_under_test', Path(__file__).with_name('native_control_probe.py'))
        self.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.probe)
        self.previous = sys.modules.get('unreal')
        sys.modules['unreal'] = types.ModuleType('unreal')

    def tearDown(self):
        if self.previous is None:
            sys.modules.pop('unreal', None)
        else:
            sys.modules['unreal'] = self.previous

    def test_out_of_bound_duration_rejected_before_editor_access(self):
        for value in [-1, 0, 4, 91, 1000000]:
            with self.assertRaises(ValueError):
                self.probe.start(value)
            self.assertIsNone(self.probe.ACTIVE)

    def test_concurrent_probe_rejected_before_editor_access(self):
        existing = {'handle': 'existing'}
        self.probe.ACTIVE = existing
        with self.assertRaises(RuntimeError):
            self.probe.start(90)
        self.assertIs(self.probe.ACTIVE, existing)

    def test_import_does_not_start_native_probe(self):
        self.assertIsNone(self.probe.ACTIVE)


if __name__ == '__main__':
    unittest.main()
