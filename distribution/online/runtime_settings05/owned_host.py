"""Actual process04/settings03 composition; no default ownership authority."""
import ctypes as C
from ctypes import wintypes as W
import secrets
import hashlib,json
from pathlib import Path
from runtime_settings03.owned_settings_host import SettingsChild,SettingsOwnedProcesses
from runtime_settings05.codec import encode
from session_core import SessionError,SessionCore,Limits
from adapters.core_host import CoreAuthority
from adapters.process04.host import OwnedStreams

class PrivateSettingsChild(SettingsChild):
    def __init__(self,record,clock):
        super().__init__(record,clock)
        self.event=None;self.remote_event=None;self.generation=secrets.token_hex(16);self.delivered=False
        self.revoked=False
    def _admit(self):
        if self.revoked:raise SessionError('Private settings generation revoked')
        return super()._admit()
    def create(self,*args):
        super().create(*args) # suspended, assigned Job, actual PID + FILETIME verified
        k=self.inner.k
        k.CreateEventW.argtypes=[C.c_void_p,W.BOOL,W.BOOL,W.LPCWSTR];k.CreateEventW.restype=W.HANDLE
        k.SetEvent.argtypes=[W.HANDLE];k.SetEvent.restype=W.BOOL
        self.event=k.CreateEventW(None,True,False,None)
        if not self.event:raise SessionError('Private revocation allocation failed')
        target=W.HANDLE()
        # Child receives SYNCHRONIZE only, cannot reset/revoke this event. It is
        # duplicated directly into our retained suspended process, never a PID lookup.
        if not k.DuplicateHandle(k.GetCurrentProcess(),self.event,self.inner.root,C.byref(target),0x100000,False,0):
            raise SessionError('Private revocation transfer failed')
        self.remote_event=target.value
        self._admit()
    def resume_and_write(self,record):
        self._admit()
        if self.delivered or not self.process_identity or not self.remote_event or not self.inner.assigned:
            raise SessionError('Private settings transfer unavailable')
        r=self.record
        d=dict(root=r.held.root,volume=r.held.identity[0],file_id=r.held.identity[1],
               pid=self.process_identity[0],created=self.process_identity[1],event=self.remote_event,
               slots=r.allocation.slot_count,generation=self.generation)
        frame=encode(record,r.owner,self.clock(),d)
        self._admit() # fresh premise/path validation immediately before delivery
        self.delivered=True
        self.inner.resume_and_write(frame)
    def revoke(self):
        self.revoked=True
        return not self.event or bool(self.inner.k.SetEvent(self.event))
    def alive(self):
        good=super().alive()
        if not good:self.revoke()
        return good
    def stop(self):
        # Always try exact Job cleanup even if SetEvent fails; failed event cleanup
        # never reports free capacity. Child-side duplicate dies with owned process.
        revoked=self.revoke()
        disposed=super().stop()
        if disposed and self.event:
            if not self.inner.k.CloseHandle(self.event):return False
            self.event=None
        return disposed and revoked

class PrivateSettingsProcesses(SettingsOwnedProcesses):
    def revoke_settings(self,owner):
        """Trusted allocator/host notification; irreversible, never releases capacity.

        The deployment authority must notify on premise loss, then call stop().
        No browser route and no provider silently assumed to enforce this contract.
        """
        self.record(owner)
        r=self.settings_records.get(owner.process_key)
        if r is None or r.owner!=owner or not r.child or not r.child.revoke():
            raise SessionError('Private revocation unconfirmed; exact cleanup required')
    def prepare(self):
        self.verified=False
        base=Path(__file__).resolve().parent
        for name,digest in json.loads((base/'prerequisites.json').read_text()).items():
            if hashlib.sha256((base.parent/name).read_bytes()).hexdigest()!=digest:
                raise SessionError('Private settings prerequisite changed')
        super().prepare()
    def _child(self):
        r=self._creating
        if r is None:raise SessionError('No bound allocation')
        r.child=PrivateSettingsChild(r,self.qpc)
        return r.child
    def stop(self,owner):
        r=self.settings_records.get(owner.process_key)
        if r is not None and r.owner==owner and r.child:r.child.revoke()
        return super().stop(owner)

def make_private_settings_host(recipe,ports,revoke,ownership_authority=None,limits=Limits()):
    if limits.capacity!=len(ports):raise SessionError('Host capacity mismatch')
    p=PrivateSettingsProcesses(recipe,ports,revoke,ownership_authority=ownership_authority)
    streams=OwnedStreams(p);core=SessionCore(p,streams,limits,clock=p.now)
    return core,CoreAuthority(core,streams),p
