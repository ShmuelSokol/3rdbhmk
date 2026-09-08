"""Regression tests for the guard that must prevent overlapping Unreal jobs."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('mikdash_verify', Path(__file__).resolve().parents[1] / 'verify.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class ProcessGuardTests(unittest.TestCase):
    def result(self, stdout='', returncode=0, stderr=''):
        gate.results.clear()
        with patch.object(gate.subprocess, 'run', return_value=subprocess.CompletedProcess([], returncode, stdout, stderr)) as run:
            gate.check_no_stray_editor()
            self.assertEqual(run.call_args.args[0], ['tasklist', '/FO', 'CSV', '/NH'])
        return gate.results[-1][1]

    def test_inventory_failure_is_not_no_editor(self):
        self.assertFalse(self.result(returncode=1, stderr='The search filter cannot be recognized.'))

    def test_empty_inventory_fails_closed(self):
        self.assertFalse(self.result())

    def test_malformed_inventory_fails_closed(self):
        self.assertFalse(self.result('ERROR: access denied'))

    def test_editor_is_detected(self):
        self.assertFalse(self.result('"UnrealEditor.exe","2316","Console","1","9,000 K"'))

    def test_commandlet_is_detected(self):
        self.assertFalse(self.result('"UnrealEditor-Cmd.exe","42","Console","1","9,000 K"'))

    def test_unrelated_processes_pass(self):
        self.assertTrue(self.result('"python.exe","10","Console","1","9,000 K"\n"MikdashCourtyardV3.exe","20","Console","1","9,000 K"'))

    def test_inventory_timeout_fails_closed(self):
        gate.results.clear()
        with patch.object(gate.subprocess, 'run', side_effect=subprocess.TimeoutExpired('tasklist', 30)):
            gate.check_no_stray_editor()
        self.assertFalse(gate.results[-1][1])

    def test_failed_precheck_never_launches_build(self):
        gate.results.clear()
        with patch.object(gate.sys, 'argv', ['verify.py', '--quick', '--build']), \
             patch.object(gate, 'check_no_stray_editor', lambda: gate.check('editor precondition', False)), \
             patch.object(gate, 'check_security_token'), patch.object(gate, 'check_map'), \
             patch.object(gate, 'check_python_scripts'), patch.object(gate, 'check_specs'), \
             patch.object(gate, 'check_receipts'), patch.object(gate, 'run_build') as build:
            self.assertEqual(gate.main(), 1)
            build.assert_not_called()

if __name__ == '__main__':
    unittest.main()
