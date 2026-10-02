"""Private event receipt replaces reachability hint, NOT authenticated open.

Source only; constructors/import perform no OS acquisition. Real Windows handles
are acquired only in the authorized create path. Frozen host owns Job/writer cleanup.
"""
import ctypes as C
from ctypes import wintypes as W
from session_core import SessionError
from runtime_settings05.owned_host import PrivateSettingsChild,PrivateSettingsProcesses
from runtime_settings05.codec import encode as encode_v2
from runtime_readiness01.codec import encode

class StoppedChild(PrivateSettingsChild):
    def __init__(self,record,clock):
        super().__init__(record,clock)
        self.ready_event=None;self.remote_ready=None;self.ready_binding=None;self.observed=False;self.ready_last=-1
    def create(self,*args):
        super().create(*args) # actual suspended PID/creation, Job, revocation event
        k=self.inner.k
        self.ready_event=k.CreateEventW(None,True,False,None) # unnamed, not inherited
        if not self.ready_event:raise SessionError('Stopped receipt allocation failed')
        target=W.HANDLE()
        if not k.DuplicateHandle(k.GetCurrentProcess(),self.ready_event,self.inner.root,C.byref(target),0x0002,False,0):
            raise SessionError('Stopped receipt transfer failed')
        self.remote_ready=target.value # EVENT_MODIFY_STATE only, never SYNCHRONIZE/full access
        self.ready_binding=(self.record.owner,self.process_identity,self.generation)
        self._admit()
    def resume_and_write(self,record):
        self._admit()
        if self.delivered or not self.ready_binding or not self.remote_ready or not self.remote_event or not self.inner.assigned:
            raise SessionError('Stopped transfer unavailable')
        self._identity()
        r=self.record
        d=dict(root=r.held.root,volume=r.held.identity[0],file_id=r.held.identity[1],
               pid=self.process_identity[0],created=self.process_identity[1],event=self.remote_event,
               slots=r.allocation.slot_count,generation=self.generation)
        v2=encode_v2(record,r.owner,self.clock(),d)
        frame=encode(v2,r.owner,self.clock(),self.remote_ready,self.generation)
        self._admit();self._identity()
        self.delivered=True
        self.inner.resume_and_write(frame) # existing owned cancellable writer, <=4096
    def _identity(self):
        if self.ready_binding!=(self.record.owner,self.process_identity,self.generation):raise SessionError('Stopped binding changed')
        k=self.inner.k;times=[W.FILETIME() for _ in range(4)]
        pid=k.GetProcessId(self.inner.root)
        if not pid or not k.GetProcessTimes(self.inner.root,*[C.byref(t) for t in times]):raise SessionError('Stopped identity unavailable')
        if (pid,(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)!=self.process_identity:raise SessionError('Stopped identity changed')
    def stopped_admitted(self,deadline):
        # Recheck AFTER observation and callbacks. Event is a historical receipt,
        # not a live streaming capability; no replay or lifetime renewal.
        if self.observed or not self.delivered or not self.ready_event:return False
        self._admit()
        if not self.alive():return False
        self._identity()
        if not self._fresh(deadline):return False
        result=self.inner.k.WaitForSingleObject(self.ready_event,0)
        if result==258:return False
        if result!=0:raise SessionError('Stopped receipt unavailable')
        self._admit()
        if not self.alive():return False
        self._identity()
        if not self._fresh(deadline):return False
        self.observed=True
        return True
    def _fresh(self,deadline):
        n=self.clock()
        if type(deadline) not in (int,float) or not 0<=deadline<=2**40 or type(n) not in (int,float) or not 0<=n<=2**40 or n<self.ready_last:
            raise SessionError('Stopped clock refused')
        self.ready_last=n
        return n<min(deadline,self.record.owner.expires_at)
    def stop(self):
        disposed=super().stop() # revoke first; exact Job/process/writer disposal
        if disposed and self.ready_event:
            if not self.inner.k.CloseHandle(self.ready_event):return False
            self.ready_event=None
        return disposed # failed CloseHandle retains parent handle and occupied capacity

class StoppedProcesses(PrivateSettingsProcesses):
    def __init__(self,*args,**kwargs):
        if 'hint' in kwargs:raise SessionError('Private readiness cannot be replaced')
        super().__init__(*args,hint=self._hint,**kwargs)
    def _child(self):
        if self._creating is None:raise SessionError('No bound allocation')
        self._creating.child=StoppedChild(self._creating,self.qpc)
        return self._creating.child
    def _hint(self,port,timeout):
        # process04 passes a deadline-clamped timeout and checks fresh startup
        # deadline again after this callback. There is deliberately no socket.
        candidates=[r for r in self.records.values() if r.port==port and not r.stopping]
        if len(candidates)!=1:raise SessionError('Stopped route mismatch')
        r=candidates[0]
        return r.child.stopped_admitted(min(r.owner.expires_at,self.now()+timeout))
    def exchange(self,owner,packet,timeout):
        raise SessionError('Authenticated receiver attachment unimplemented')
        # Core request must fail/clean up here; never mark browser/stream ACTIVE.
