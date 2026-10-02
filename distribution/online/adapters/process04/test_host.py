"""Deterministic contract tests: no process, pipe, thread or socket is opened."""
from dataclasses import replace
import unittest

from session_core import Ownership, SessionError, SessionCore, Limits, InputEvent
from adapters.process04.host import LaunchRecipe, OwnedProcesses, OwnedStreams, check_owner
from adapters.process04.win32_child import WindowsChild


OWNER = Ownership('session', 'process', 'stream', 'save', 'settings', 100)
RECIPE = LaunchRecipe('C:/fixture.exe', '0'*64, 'C:/', ('--stream={stream_id}',), 'C:/Windows', 'C:/Temp')


class Clock:
    def __init__(self): self.value = 1
    def __call__(self): return self.value
    def sleep(self, n): self.value += n


class Child:
    def __init__(self):
        self.calls = []; self.fail_create = False; self.dead = False
        self.written = True; self.failed_write = False; self.stoppable = True
    def create(self, *args):
        self.calls.append('create')
        if self.fail_create: raise RuntimeError('SECRET')
    def resume_and_write(self, record): self.calls.append('write')
    def bootstrap_done(self): return self.written
    def bootstrap_failed(self): return self.failed_write
    def alive(self): return not self.dead
    def stop(self): self.calls.append('stop'); return self.stoppable


class Channel:
    def __init__(self, *args, **kwargs): self.calls = []; self.bad = False
    def exchange(self, owner, packet, timeout):
        self.calls.append(packet)
        if self.bad: raise RuntimeError('SECRET')
        return dict(version=1, owner=packet['owner'], sequence=packet['sequence'],
                    operation=packet['operation'], connection_id=packet['connection_id'], status='applied')


class HostTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock(); self.child = Child(); self.revoked = []
        self.p = OwnedProcesses(RECIPE, (19001,), self.revoked.append, clock=self.clock,
            child_factory=lambda: self.child, channel_factory=Channel,
            hint=lambda p,t: True, sleeper=self.clock.sleep, key_factory=lambda:b'0'*32,
            verify=lambda r: None, start_seconds=.2, write_seconds=.05, cleanup_seconds=.03, qpc=self.clock)
        self.p.prepare()

    def test_start_is_not_authenticated_ready(self):
        self.p.start(OWNER)
        self.assertEqual(self.child.calls, ['create', 'write'])
        self.assertEqual(self.p.record(OWNER).channel.calls, [])
        stream = OwnedStreams(self.p); stream.open(OWNER)
        self.assertEqual([p['operation'] for p in self.p.record(OWNER).channel.calls], ['open'])

    def test_blocked_bootstrap_has_deadline_and_owned_cleanup(self):
        self.child.written = False
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertLess(self.clock.value, 1.1)
        self.assertIn('stop', self.child.calls)
        self.assertEqual(self.p.records, {})

    def test_failed_writer_cleans_without_retry(self):
        self.child.failed_write = True
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertEqual(self.child.calls.count('write'), 1)
        self.assertEqual(self.p.records, {})

    def test_late_completed_writer_not_accepted(self):
        def write(record): self.clock.sleep(.051)
        self.child.resume_and_write = write
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertEqual(self.p.records, {})

    def test_frozen_clock_has_iteration_bound(self):
        self.p.sleep = lambda n: None
        self.p.hint = lambda p,t: False
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertIn('stop', self.child.calls)

    def test_failed_cleanup_retains_port_and_capacity(self):
        self.child.written = False; self.child.stoppable = False
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertEqual(len(self.p.records), 1)
        with self.assertRaises(SessionError): self.p.start(replace(OWNER, process_key='p2'))
        self.child.stoppable = True; self.p.stop(OWNER)
        self.assertEqual(self.p.records, {})

    def test_partial_create_keeps_lease(self):
        self.child.fail_create = True; self.child.stoppable = False
        with self.assertRaisesRegex(SessionError, '^Process startup unavailable$'): self.p.start(OWNER)
        self.assertEqual(len(self.p.records), 1)

    def test_readiness_timeout_no_unbounded_poll(self):
        count = [0]
        def hint(p,t): count[0] += 1; return False
        self.p.hint = hint
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertLess(count[0], 25)
        self.assertIn('stop', self.child.calls)

    def test_late_reachability_never_admits(self):
        def hint(p,t): self.clock.value = 110; return True
        self.p.hint = hint
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertEqual(self.p.records, {})

    def test_bad_qpc_after_start_still_stops(self):
        self.p.start(OWNER); self.clock.value = -1
        self.p.stop(OWNER)
        self.assertIn('stop', self.child.calls)

    def test_revoke_failure_does_not_prevent_process_stop(self):
        self.p.start(OWNER)
        self.p.revoke = lambda o: (_ for _ in ()).throw(RuntimeError('SECRET'))
        with self.assertRaisesRegex(SessionError, '^Owned cleanup pending$'): self.p.stop(OWNER)
        self.assertTrue(self.p.record(OWNER).disposed)
        self.p.revoke = self.revoked.append
        self.p.stop(OWNER)

    def test_synchronous_reentrant_revoke_no_recursion(self):
        self.p.start(OWNER); calls = []
        def revoke(o):
            calls.append(o)
            with self.assertRaises(SessionError): self.p.stop(o)
        self.p.revoke = revoke
        self.p.stop(OWNER)
        self.assertEqual(len(calls), 1)

    def test_double_stop_no_repeat_disposal(self):
        self.p.start(OWNER); self.p.stop(OWNER); self.p.stop(OWNER)
        self.assertEqual(self.child.calls.count('stop'), 1)

    def test_wrong_owner_cannot_stop(self):
        self.p.start(OWNER)
        with self.assertRaises(SessionError): self.p.stop(replace(OWNER, stream_id='foreign'))
        self.assertNotIn('stop', self.child.calls)

    def test_stream_close_waits_job_not_native_close_ack(self):
        self.p.start(OWNER); stream = OwnedStreams(self.p); stream.open(OWNER)
        self.child.stoppable = False
        with self.assertRaises(SessionError): stream.close(OWNER)
        self.assertIn(OWNER.stream_id, stream.records)
        self.child.stoppable = True; stream.close(OWNER)
        self.assertEqual(stream.records, {})

    def test_port_collision_bad_hmac_cannot_admit(self):
        self.p.start(OWNER); self.p.record(OWNER).channel.bad = True
        stream = OwnedStreams(self.p)
        with self.assertRaisesRegex(SessionError, '^Native acknowledgment failed$'): stream.open(OWNER)
        stream.close(OWNER)
        self.assertEqual(self.child.calls.count('stop'), 1)

    def test_core_capacity_cleanup_pending(self):
        streams = OwnedStreams(self.p)
        core = SessionCore(self.p, streams, Limits(capacity=1), clock=self.clock)
        ticket = core.request(); c = core.connect(ticket.session_id, ticket.credential)
        owner = next(iter(self.p.records.values())).owner
        streams.bind(owner, c.connection_id)
        core.submit(c, InputEvent('move', 0, 1))
        self.child.stoppable = False
        core.cancel(c.session_id, c.credential)
        self.assertEqual(len(self.p.records), 1)
        queued = core.request()
        self.assertEqual(core.status(queued.session_id, queued.credential).state.value, 'queued')
        self.child.stoppable = True
        core.tick()
        self.assertEqual(core.status(queued.session_id, queued.credential).state.value, 'active')

    def test_hostile_owner_and_deadlines(self):
        for value in ([], {}, None, replace(OWNER, process_key=[]), replace(OWNER, stream_id='x'*129),
                      replace(OWNER, expires_at=10**400), replace(OWNER, expires_at=float('nan'))):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(SessionError): check_owner(value)

    def test_secret_not_in_recipe_interpolation_or_repr(self):
        with self.assertRaises(SessionError): replace(RECIPE, args=('--secret={key}',)).validate()
        self.assertNotIn(RECIPE.executable, repr(RECIPE))

    def test_no_prepare_no_launch(self):
        self.p.verified = False
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertEqual(self.child.calls, [])

    def test_different_clock_domain_refused_before_create(self):
        self.p.qpc=lambda: 1000
        with self.assertRaises(SessionError): self.p.start(OWNER)
        self.assertNotIn('create', self.child.calls)


class Kernel:
    """Only cleanup calls, exercising the real WindowsChild state machine."""
    def __init__(self): self.calls=[]; self.signal=258; self.active=1; self.fail_close=None
    def CloseHandle(self, h): self.calls.append(('close',h)); return h != self.fail_close
    def WaitForSingleObject(self, h, ms): self.calls.append(('wait',h)); return self.signal
    def TerminateJobObject(self, h, code): self.calls.append(('kill_job',h)); return True
    def TerminateProcess(self, h, code): self.calls.append(('kill_root',h)); return True
    def CancelSynchronousIo(self, h): self.calls.append(('cancel',h)); return True
    def QueryInformationJobObject(self, h, kind, info, size, returned):
        info._obj.active = self.active; return True


class WindowsCleanupTests(unittest.TestCase):
    def setUp(self):
        self.k=Kernel(); self.c=WindowsChild(self.k)
        self.c.job=11; self.c.root=12; self.c.assigned=True

    def test_termination_not_confirmation(self):
        self.assertFalse(self.c.stop())
        self.assertEqual(self.c.root,12)
        self.k.signal=0; self.k.active=0
        self.assertTrue(self.c.stop()); self.assertTrue(self.c.stop())

    def test_accounting_zero_alone_insufficient(self):
        self.k.active=0
        self.assertFalse(self.c.stop())

    def test_partial_assignment_uses_retained_root(self):
        self.c.assigned=False
        self.assertFalse(self.c.stop())
        self.assertIn(('kill_root',12), self.k.calls)
        self.assertNotIn(('kill_job',11), self.k.calls)

    def test_failed_close_retained(self):
        self.k.signal=0; self.k.active=0; self.k.fail_close=12
        self.assertFalse(self.c.stop()); self.assertEqual(self.c.root,12)
        self.k.fail_close=None; self.assertTrue(self.c.stop())

    def test_job_kill_precedes_writer_cancel(self):
        self.c._worker_handle=13
        self.assertFalse(self.c.stop())
        self.assertLess(self.k.calls.index(('kill_job',11)),self.k.calls.index(('cancel',13)))
        self.assertNotIn(('close',13), self.k.calls)

    def test_query_failure_keeps_handles(self):
        self.k.signal=0
        self.k.QueryInformationJobObject=lambda *a:False
        self.assertFalse(self.c.stop())
        self.assertEqual(self.c.job,11)


class CreationKernel(Kernel):
    def __init__(self): super().__init__(); self.flags=None; self.command=None; self.limits=None
    def CreateJobObjectW(self,*a): self.calls.append(('job',)); return 11
    def SetInformationJobObject(self,h,kind,p,size):
        self.limits=(p._obj.basic.flags,p._obj.basic.active); return True
    def CreatePipe(self,r,w,sa,size):
        r._obj.value=20; w._obj.value=21; self.calls.append(('pipe',size)); return True
    def SetHandleInformation(self,h,mask,flags): self.calls.append(('inherit',h,flags)); return True
    def CreateFileW(self,*a): return 22
    def InitializeProcThreadAttributeList(self,p,count,flags,size): size._obj.value=128; return bool(p)
    def UpdateProcThreadAttribute(self,p,flags,kind,handles,size,*rest):
        self.calls.append(('handle_list',tuple(handles))); return True
    def DeleteProcThreadAttributeList(self,*a): pass
    def CreateProcessW(self,exe,command,pa,ta,inherit,flags,env,cwd,si,pi):
        self.calls.append(('spawn_suspended',)); self.flags=flags; self.command=command.value
        pi._obj.process=12; pi._obj.thread=13; return True
    def AssignProcessToJobObject(self,j,p): self.calls.append(('assign',j,p)); return True
    def ResumeThread(self,t): self.calls.append(('resume',t)); return 1
    def GetCurrentProcess(self): return -1
    def GetCurrentThread(self): return -2
    def DuplicateHandle(self,p,t,p2,out,access,inherit,options): out._obj.value=23; return True
    def WriteFile(self,h,buffer,size,written,overlapped):
        self.calls.append(('write',h,size)); written._obj.value=size; return True


class WindowsCreationTests(unittest.TestCase):
    def test_real_creation_control_flow_uses_handle_list_and_job_before_resume(self):
        k=CreationKernel(); c=WindowsChild(k)
        c.create(RECIPE.executable,RECIPE.arguments(OWNER),RECIPE.cwd,RECIPE.environment(),RECIPE.memory_bytes)
        self.assertEqual(k.limits,(0x2000|8|0x100|0x200,1))
        self.assertTrue(k.flags&4); self.assertTrue(k.flags&0x80000)
        self.assertIn(('handle_list',(20,22)),k.calls)
        self.assertIn(('inherit',21,0),k.calls)
        self.assertNotIn(('resume',13),k.calls)
        self.assertLess(k.calls.index(('close',20)),k.calls.index(('assign',11,12)))
        self.assertFalse(any(x[0]=='write' for x in k.calls))
        # Call actual writer function directly with fake APIs. NO real thread.
        c._write(b'public-fixture-frame')
        self.assertTrue(c.bootstrap_done())
        self.assertIn(('close',21),k.calls)

    def test_cancel_before_writer_never_writes(self):
        k=CreationKernel(); c=WindowsChild(k); c.writer=21; c._cancel.set()
        c._write(b'public-fixture-frame')
        self.assertFalse(any(x[0]=='write' for x in k.calls))
        self.assertTrue(c.bootstrap_failed())

    def test_partial_write_no_success(self):
        k=CreationKernel(); c=WindowsChild(k); c.writer=21
        def partial(h,b,n,w,o): w._obj.value=n-1; return True
        k.WriteFile=partial
        c._write(b'public-fixture-frame')
        self.assertTrue(c.bootstrap_failed())


if __name__ == '__main__': unittest.main()
