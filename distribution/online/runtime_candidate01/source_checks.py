"""Offline source-contract checks only, not C++/UE behavior tests."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
POLICY=(ROOT/'StoppedLease.h').read_text()
HEADER=(ROOT/'OwnedStoppedStreamer.h').read_text()
CPP=(ROOT/'OwnedStoppedStreamer.cpp').read_text()


class SourceContracts(unittest.TestCase):
    def test_no_start_or_module_wide_stop(self):
        self.assertNotIn('StartStreaming(',POLICY+HEADER+CPP)
        self.assertNotIn('Module.StopStreaming(',HEADER+CPP)

    def test_presence_refusal_before_create(self):
        self.assertLess(POLICY.index('P.Registered(Expected.stream_id)'),POLICY.index('S=P.Create('))
        self.assertIn('Module.GetStreamerIds().Contains(Name)',CPP)

    def test_pointer_only_removal(self):
        self.assertIn('Module.DeleteStreamer(S)',HEADER)
        self.assertNotIn('DeleteStreamer(Id',HEADER+CPP)
        self.assertIn('P.Find(Expected.stream_id)==S',POLICY)

    def test_no_duplicate_capture(self):
        self.assertNotIn('CreateVideoProducerBackBuffer(',CPP+HEADER)
        self.assertIn('GetVideoProducer().Pin()',HEADER)

    def test_no_bootstrap_launch(self):
        self.assertNotIn('Bootstrap::Start',CPP+HEADER)
        self.assertNotIn('Server->Start',CPP+HEADER)

    def test_busy_guard_precedes_callbacks(self):
        close=POLICY[POLICY.index('bool Close()'):]
        self.assertLess(close.index('if(Busy)return false'),close.index('P.Stop(S)'))
        self.assertLess(close.index('Guard Lock(Busy)'),close.index('P.Remove(S)'))

    def test_owned_window_scope(self):
        for s in ('World->WorldType!=EWorldType::Game','GetNumGamePlayers(World)!=1','Windows.Num()!=1'):
            self.assertIn(s,CPP)

    def test_production_policy_used_by_tests(self):
        text=(ROOT/'OwnershipTests.cpp').read_text()
        self.assertIn('#include "StoppedLease.h"',text)
        self.assertEqual(text.count('Case([]'),14)


if __name__=='__main__':unittest.main()
