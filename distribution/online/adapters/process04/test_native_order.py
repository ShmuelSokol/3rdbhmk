"""Executable scheduling specification for inspected UE ordering, not C++ proof.

These cases supplement Wegener's frozen oracle without editing its files.
"""
import unittest


class Ordering:
    def __init__(self):
        self.now=0; self.session_end=10000; self.reply_end=500; self.hold_end=2000
        self.generation=1; self.pending='move'; self.ack=False; self.remote_commits=0
        self.local=(2,0); self.shapes=[]; self.result=None
    def walker(self, skip=False, jump_until=0, scale_until=0, asynchronous=False):
        consumed_local=self.local  # engine ConsumeInputVector happens first
        if skip or asynchronous: return consumed_local
        self.now=max(self.now,jump_until)  # CheckJumpInput can stall before acceleration
        if self.now>=min(self.reply_end,self.session_end): return consumed_local
        self.now=max(self.now,scale_until)  # virtual Constrain/Scale can stall
        if self.now>=min(self.reply_end,self.session_end): return consumed_local
        self.remote_commits+=1; self.ack=True
        return (consumed_local[0]+1,consumed_local[1])
    def shape(self, remote, until):
        self.shapes.append(remote); self.now=max(self.now,until)
        # Distinct remote obstacle direction AND speed-scale/sliding provenance.
        return ((0,1),.25,True) if remote else (self.local,.8,False)
    def dove(self, sweep_until, *, held=False, cancel=False, configured=True):
        if not configured:
            self.result=self.shape(False,sweep_until)  # base obstacle reduction retained
            return self.result
        end=min(self.session_end,self.hold_end,self.reply_end if not held else self.hold_end)
        if self.now>=end:
            self.result=self.shape(False,sweep_until); return self.result
        generation=self.generation
        candidate=self.shape(True,sweep_until)
        if cancel:self.generation+=1
        if self.now>=end or generation!=self.generation:
            self.result=self.shape(False,self.now)  # one complete fallback, no remote reuse
        else:
            self.result=candidate; self.remote_commits+=1; self.ack=not held
        return self.result


class NativeOrderTests(unittest.TestCase):
    def test_walker_skip_after_early_consume_has_no_ack(self):
        m=Ordering(); self.assertEqual(m.walker(skip=True),m.local); self.assertFalse(m.ack)
    def test_walker_jump_and_virtual_scale_stalls_recheck(self):
        for kwargs in (dict(jump_until=500),dict(scale_until=500)):
            m=Ordering(); self.assertEqual(m.walker(**kwargs),m.local); self.assertFalse(m.ack)
    def test_walker_async_no_remote_but_local_preserved(self):
        m=Ordering(); self.assertEqual(m.walker(asynchronous=True),m.local); self.assertFalse(m.ack)
    def test_walker_fresh_acceleration_ack(self):
        m=Ordering(); self.assertEqual(m.walker(jump_until=499),(3,0)); self.assertTrue(m.ack)
    def test_dove_expired_sweep_discards_direction_scale_sliding(self):
        m=Ordering(); self.assertEqual(m.dove(500),(m.local,.8,False))
        self.assertEqual(m.shapes,[True,False]); self.assertFalse(m.ack)
    def test_queued_look_cannot_extend_held_move_through_sweep(self):
        m=Ordering(); m.now=1990; m.pending='look'; m.reply_end=2400
        self.assertEqual(m.dove(2010,held=True),(m.local,.8,False)); self.assertEqual(m.remote_commits,0)
    def test_dove_generation_change_during_sweep_preserves_local(self):
        m=Ordering(); self.assertEqual(m.dove(100,cancel=True),(m.local,.8,False))
        self.assertEqual(m.shapes,[True,False]); self.assertFalse(m.ack)
    def test_unconfigured_dove_preserves_base_obstacle_slowdown(self):
        m=Ordering(); self.assertEqual(m.dove(100,configured=False)[1],.8)
    def test_native_order_boundary_grid(self):
        for now in (0,499,500,501):
            for stall in (0,499,500,501):
                m=Ordering(); m.now=now; m.dove(stall)
                self.assertEqual(m.remote_commits,int(max(now,stall)<500))


if __name__=='__main__':unittest.main()
