"""Real parser/TransportChild method tests with writer adapter replaced, no OS I/O."""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from session_core import Ownership,SessionError
from adapters.receiver03_bootstrap import make_record
from runtime_readiness01.owned_host import StoppedChild
from runtime_transport01.owned_host import TransportChild

class DeadlineTests(unittest.TestCase):
    def setUp(self):
        self.owner=Ownership('session','process','stream','save','settings',200)
        self.frame=make_record(self.owner,19000,b'x'*32,clock=lambda:100,qpc=lambda:100)
        # Exercise the actual additive method, not OS construction/acquisition.
        self.child=TransportChild.__new__(TransportChild)
        self.child.record=SimpleNamespace(owner=self.owner)
        self.child.clock=lambda:100
        self.child._native_descriptor=None
        self.child.delivered=False

    def test_exact_frame_forwarded_and_original_bound_retained(self):
        seen=[]
        def writer(child,frame):
            seen.append(frame);child.delivered=True
        with patch.object(StoppedChild,'resume_and_write',writer):
            self.child.resume_and_write(self.frame)
        self.assertEqual(seen,[self.frame])
        self.assertAlmostEqual(self.child.native_deadline,199.998)
        self.child.clock=lambda:150
        self.assertAlmostEqual(self.child.native_deadline,199.998)
        self.assertEqual(set(vars(self.child._native_descriptor)),{'owner','deadline','port'})

    def test_expired_frame_never_reaches_writer(self):
        self.child.clock=lambda:200
        with patch.object(StoppedChild,'resume_and_write') as writer:
            with self.assertRaises(SessionError):self.child.resume_and_write(self.frame)
            writer.assert_not_called()

    def test_wrong_owner_never_reaches_writer(self):
        self.child.record.owner=Ownership('other','process','stream','save','settings',200)
        with patch.object(StoppedChild,'resume_and_write') as writer:
            with self.assertRaises(SessionError):self.child.resume_and_write(self.frame)
            writer.assert_not_called()

    def test_failed_write_cannot_retry_or_claim_delivery(self):
        with patch.object(StoppedChild,'resume_and_write',side_effect=SessionError('writer failure')) as writer:
            with self.assertRaises(SessionError):self.child.resume_and_write(self.frame)
            with self.assertRaises(SessionError):self.child.resume_and_write(self.frame)
            with self.assertRaises(SessionError):_=self.child.native_deadline
            self.assertEqual(writer.call_count,1)

    def test_unset_descriptor_refuses(self):
        with self.assertRaises(SessionError):_=self.child.native_deadline

if __name__=='__main__':unittest.main(verbosity=2)
