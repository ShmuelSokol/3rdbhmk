"""Source control-flow assertions only: NOT compiled C++ or UE execution."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
CPP = (ROOT / 'ServicedStoppedOwner.cpp').read_text()
HEADER = (ROOT / 'ServicedStoppedOwner.h').read_text()
POLICY = (ROOT / 'ExpiryWatch.h').read_text()


class Contracts(unittest.TestCase):
    def test_real_frame_and_exit_delegates(self):
        for name in ('OnBeginFrame', 'OnEnginePreExit'):
            self.assertIn(f'FCoreDelegates::{name}.AddLambda', CPP)
            self.assertIn(f'FCoreDelegates::{name}.Remove', CPP)

    def test_no_launch(self):
        for forbidden in ('StartStreaming(', 'Receiver->Start(', 'Server->Start(', 'Module.StopStreaming('):
            self.assertNotIn(forbidden, CPP + HEADER)

    def test_direct_reviewed_implementations(self):
        self.assertIn('RuntimeCandidate01::FOwnedStoppedStreamer Lease', HEADER)
        self.assertIn('TSharedRef<Receiver04::Bootstrap> Receiver', HEADER)
        self.assertIn('Receiver->Shutdown()', CPP)

    def test_shutdown_order(self):
        body = CPP.split('bool FServicedStoppedOwner::Shutdown()')[1].split('void FServicedStoppedOwner::Arm()')[0]
        order = ['RevokeRequested=true', 'if(Busy)', 'TGuardValue<bool>', 'const bool MediaObserved=',
                 'Receiver->Shutdown()', 'if(!ReceiverClosed||MediaObserved)', 'Lease.Close()', 'Disarm()']
        positions = [body.index(s) for s in order]
        self.assertEqual(positions, sorted(positions))

    def test_quarantine_no_retry(self):
        self.assertIn('if(Phase==State::Quarantined) return false;', CPP)
        self.assertIn('if(Phase!=State::Ready||Busy) return;', CPP)
        arm = CPP.split('void FServicedStoppedOwner::Arm()')[1].split('void FServicedStoppedOwner::Disarm()')[0]
        self.assertNotIn('Quarantined', arm)
        self.assertIn('[Self]', arm)
        self.assertEqual(arm.count('const auto KeepAlive=Self;'), 2)

    def test_exact_window_world(self):
        for s in ('Viewport->GetWorld()!=World.Get()', 'Viewport->GetWindow()!=Window.Pin()',
                  'Windows.Num()==1', 'GEngine->GameViewport!=Viewport.Get()'):
            self.assertIn(s, CPP)

    def test_native_clock_and_finite_lifetime(self):
        self.assertIn('Receiver03::QpcSeconds()', CPP)
        for s in ('Now>=Deadline', 'Now<LastObservation', 'Now-LastFrame>0.5', 'Bound>OwnerExpiry'):
            self.assertIn(s, POLICY)
        self.assertNotIn('FPlatformTime::', CPP)

    def test_borrow_cannot_extend_service(self):
        body = CPP.split('FServicedStoppedOwner::BorrowStopped(')[1].split('void FServicedStoppedOwner::ServiceFrame()')[0]
        self.assertNotIn('CompleteFrame(', body)
        self.assertIn('if(RevokeRequested||!ScopeAndTime()) Result.Reset()', body)
        self.assertIn('!(Identity==O)', body)

    def test_stopped_scope_still_checked_each_frame(self):
        body = CPP.split('void FServicedStoppedOwner::ServiceFrame()')[1].split('bool FServicedStoppedOwner::Shutdown()')[0]
        self.assertLess(body.index('BorrowStopped(Identity)'), body.index('Expiry.CompleteFrame('))
        self.assertIn('Lease.BorrowStopped(O)', CPP)

    def test_actual_policy_header_tested(self):
        self.assertIn('#include "ExpiryWatch.h"', HEADER)
        self.assertIn('ExpiryWatch Expiry;', HEADER)
        tests = (ROOT / 'ExpiryWatchTests.cpp').read_text()
        self.assertIn('#include "ExpiryWatch.h"', tests)
        self.assertEqual(tests.count('Case([]'), 13)

    def test_revocation_before_callbacks(self):
        body = CPP.split('bool FServicedStoppedOwner::Shutdown()')[1]
        self.assertLess(body.index('Expiry.Revoke()'), body.index('Receiver->Shutdown()'))


if __name__ == '__main__':
    unittest.main()
