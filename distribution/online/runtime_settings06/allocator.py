"""Bounded cooperative allocation, NOT an ACL sandbox or ownership assertion.

Real roots/handles/identity/CREATE_NEW journal and actual settings05 host seam.
DeploymentPremise remains mandatory: arbitrary same-account writers are outside
the supported threat model, and no affirmative production provider is supplied.
"""
from abc import ABC,abstractmethod
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import json,secrets,threading
from session_core import SessionError
from adapters.process04.host import check_owner
from adapters.receiver03_bootstrap import windows_qpc
from runtime_settings03.launcher_contract03 import launch_inputs
from runtime_settings03.owned_settings_host import ExclusiveOwnershipAuthority,ExclusiveAllocation,RetainedDirectories,_probe

class DeploymentPremise(ABC):
    @abstractmethod
    def validate(self,pool_root,pool_identity):
        """Raise unless controlled deployment writers/exclusivity remain established.

        Not a browser field, bool, JSON declaration or mere path check. Operator
        must supply actual deployment authority; fixture implementations are tests
        only. Return None on validated premise; no production implementation here.
        """

@dataclass(frozen=True)
class PoolSpec:
    root:str
    identity:tuple
    capacity:int=1
    max_allocations:int=16
    slots:int=2
    lifetime_seconds:float=3600

class Chain:
    def __init__(self,w):self.w=w;self.handles=[]
    def acquire(self,root):
        current=root[:3];paths=[current]
        for part in root[3:].split('/'):
            current=current.rstrip('/')+'/'+part;paths.append(current)
        if len(paths)>128:raise SessionError('Pool depth refused')
        for path in paths:
            h=self.w.open_attributes(path,share_delete=False,desired_access=0x80000000)
            self.handles.append((path,h,None))
            i=self.w.inspect_handle(h);self.handles[-1]=(path,h,tuple(i['identity']))
            self._check(path,h,tuple(i['identity']))
    def _check(self,path,h,identity):
        i=self.w.inspect_handle(h)
        if not i['got'] or not 0<i['n']<1024 or i['attrs']&0x400 or not i['attrs']&0x10 or \
           i['final'].casefold()!=path.casefold() or tuple(i['identity'])!=identity:
            raise SessionError('Pool path identity refused')
    def validate(self):
        if not self.handles:raise SessionError('Pool handles absent')
        for entry in self.handles:self._check(*entry)
    def close(self):
        remaining=[]
        for entry in reversed(self.handles):
            if not self.w.k.CloseHandle(entry[1]):remaining.append(entry)
        self.handles=list(reversed(remaining))
        if remaining:raise SessionError('Pool handle cleanup pending')

class Allocation(ExclusiveAllocation):
    def __init__(self,pool,owner,root):
        self.pool=pool;self.owner=owner;self._root=root;self.held=RetainedDirectories()
        self.issued=False;self.revoked=False;self.released=False;self.partial=True
    @property
    def root(self):return self._root
    @property
    def slot_count(self):return self.pool.spec.slots
    def revalidate(self,owner):
        with self.pool.lock:
            if owner!=self.owner or self.revoked or self.released or not self.issued or \
               self.pool.allocations.get(owner.process_key) is not self:
                raise SessionError('Allocation ownership unavailable')
            self.pool._admit()
            if self.pool.now()>=owner.expires_at:raise SessionError('Allocation expired')
            self.held.revalidate()
    def release_after_cleanup(self,owner):
        """Trusted host-only capability: called by frozen03 after exact Job/worker
        disposal and route revocation. Not exported through browser/RPC bindings.
        No deletion/reuse and no waiver of pending child cleanup is supported.
        """
        with self.pool.lock:
            if owner!=self.owner:raise SessionError('Wrong cleanup owner')
            if self.released:return
            self.revoked=True
            self.held.close_after_process_cleanup()
            self.pool._journal('released',self.owner,self.root)
            self.released=True
            # Retain tombstone, bounded by max_allocations; never reuse owner/root.

class OwnedAllocator(ExclusiveOwnershipAuthority):
    def __init__(self,spec,premise,*,clock=windows_qpc):
        if type(spec) is not PoolSpec or not isinstance(premise,DeploymentPremise):
            raise SessionError('Deployment ownership premise required')
        if type(spec.identity) is not tuple or len(spec.identity)!=2 or any(type(x) is not int for x in spec.identity) or \
           not 0<=spec.identity[0]<2**32 or not 0<=spec.identity[1]<2**64 or \
           type(spec.capacity) is not int or not 1<=spec.capacity<=16 or \
           type(spec.max_allocations) is not int or not spec.capacity<=spec.max_allocations<=256 or \
           type(spec.slots) is not int or not 1<=spec.slots<=64 or \
           type(spec.lifetime_seconds) not in (int,float) or not 0<spec.lifetime_seconds<=86400:
            raise SessionError('Bounded pool specification required')
        self.spec=spec;self.premise=premise;self.clock=clock;self.last=-1;self.end=None
        self.w=None;self.chain=None;self.marker=None;self.marker_identity=None
        self.used=False;self.opened=False;self.retired=False;self.allocations={};self.journal_handles=[]
        self.lock=threading.RLock();self.sequence=0
    def now(self):
        n=self.clock()
        if type(n) not in (int,float) or not 0<=n<=2**40 or n<self.last:
            raise SessionError('Pool clock refused')
        self.last=n;return n
    def _premise(self):
        if self.premise.validate(self.spec.root,self.spec.identity) is not None:
            raise SessionError('Deployment premise unconfirmed')
    def open(self):
        with self.lock:
            if self.used:raise SessionError('Pool already attempted')
            self.used=True
            self._premise() # refuse BEFORE any filesystem write/open
            self.w=w=_probe()
            if w.lex.canonical(self.spec.root)!=self.spec.root or any(c.isspace() for c in self.spec.root):
                raise SessionError('Canonical pool root required')
            if w.k.GetDriveTypeW(self.spec.root[:3])!=3:raise SessionError('Fixed local pool required')
            # Reject too-long derived paths before acquisition/mutation.
            launch_inputs(self.spec.root+'/s_'+'0'*32,'settings','save',self.spec.slots)
            self.chain=Chain(w);self.chain.acquire(self.spec.root)
            if self.chain.handles[-1][2]!=self.spec.identity:raise SessionError('Pool identity mismatch')
            k=w.k
            k.CreateDirectoryW.argtypes=[W.LPCWSTR,C.c_void_p];k.CreateDirectoryW.restype=W.BOOL
            k.WriteFile.argtypes=[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p];k.WriteFile.restype=W.BOOL
            k.FlushFileBuffers.argtypes=[W.HANDLE];k.FlushFileBuffers.restype=W.BOOL
            self.end=self.now()+self.spec.lifetime_seconds
            # CREATE_NEW + share0 refuses concurrent host AND any previous pool
            # incarnation. Marker is never deleted, including clean shutdown.
            self.marker=self._new_file(self.spec.root+'/allocator.lock')
            self.marker_identity=tuple(w.inspect_handle(self.marker)['identity'])
            self._write(self.marker,dict(schema=1,kind='pool_claim',volume=f'{self.spec.identity[0]:08x}',
                                         file_id=f'{self.spec.identity[1]:016x}',restart='refused_fresh_pool_required'))
            self.opened=True;self._admit()
    def _new_file(self,path):
        h=self.w.k.CreateFileW(path,0xc0000000,0,None,1,0x00200000,None)
        if h==self.w.INVALID:raise SessionError('Owned journal create refused')
        # Own immediately: even a subsequent write/flush failure is retained.
        self.journal_handles.append(h)
        return h
    def _write(self,h,value):
        raw=(json.dumps(value,separators=(',',':'),sort_keys=True)+'\n').encode('ascii')
        if len(raw)>2048:raise SessionError('Journal bound')
        buf=C.create_string_buffer(raw);n=W.DWORD()
        if not self.w.k.WriteFile(h,buf,len(raw),C.byref(n),None) or n.value!=len(raw) or not self.w.k.FlushFileBuffers(h):
            raise SessionError('Durable ownership receipt failed')
    def _journal(self,kind,owner,root):
        self.sequence+=1
        if self.sequence>self.spec.max_allocations*2:raise SessionError('Journal count bound')
        path=self.spec.root+'/receipt_'+format(self.sequence,'04d')+'.json'
        h=self._new_file(path)
        self._write(h,dict(schema=1,kind=kind,process_key=owner.process_key,session_id=owner.session_id,
                           root_leaf=root.rsplit('/',1)[-1]))
        # Keep all receipt handles through pool retirement. This is bounded to
        # 2*max_allocations+1 and prevents cooperative alteration/replacement.
    def _admit(self):
        if not self.opened or self.retired or self.now()>=self.end:raise SessionError('Pool unavailable')
        self._premise();self.chain.validate()
        i=self.w.inspect_handle(self.marker)
        if not i['got'] or i['attrs']&(0x10|0x400) or i['links']!=1 or tuple(i['identity'])!=self.marker_identity:
            raise SessionError('Pool marker identity refused')
    def reserve(self,owner):
        check_owner(owner)
        with self.lock:
            self._admit()
            if owner.expires_at<=self.now() or owner.expires_at>self.end or owner.process_key in self.allocations or \
               len(self.allocations)>=self.spec.max_allocations or \
               sum(not a.released for a in self.allocations.values())>=self.spec.capacity:
                raise SessionError('Allocation lifetime/capacity unavailable')
            if any(any(getattr(a.owner,k)==getattr(owner,k) for k in
                       ('session_id','stream_id','save_prefix','settings_slot')) for a in self.allocations.values()):
                raise SessionError('Prior allocation identity reused')
            root=self.spec.root+'/s_'+secrets.token_hex(16)
            contract=launch_inputs(root,owner.settings_slot,owner.save_prefix,self.spec.slots)
            a=Allocation(self,owner,root);self.allocations[owner.process_key]=a
            try:
                # No exist_ok, no adopt-existing or path supplied by browser.
                for path in [root]+contract['precreate_directories']:
                    self._admit()
                    if not self.w.k.CreateDirectoryW(path,None):raise SessionError('Fresh directory creation refused')
                a.held.acquire(root)
                self._journal('allocated',owner,root)
                a.partial=False;a.issued=True;a.revalidate(owner)
                return a
            except Exception:
                a.revoked=True;a.issued=False
                # No capability returned/no child authorized. Partial directories
                # and retained handles remain charged/quarantined, never deleted.
                raise SessionError('Allocation failed; pool quarantine retained') from None
    def invalid_owners(self):
        with self.lock:
            invalid=[]
            for a in self.allocations.values():
                if a.released:continue
                try:a.revalidate(a.owner)
                except Exception:a.revoked=True;invalid.append(a.owner)
            return tuple(invalid)
    def retire(self):
        """Close only after all issued allocations confirm host disposal. Never
        delete root/journal/marker or reopen a crashed pool. Partial unissued
        reservations can close handles because reserve never returned them.
        """
        with self.lock:
            self.retired=True
            if any(a.issued and not a.released for a in self.allocations.values()):
                raise SessionError('Owned allocations still pending')
            for a in self.allocations.values():
                if not a.issued:a.held.close_after_process_cleanup()
            remaining=[]
            for h in reversed(self.journal_handles):
                if not self.w.k.CloseHandle(h):remaining.append(h)
            self.journal_handles=list(reversed(remaining))
            if remaining:raise SessionError('Journal cleanup pending')
            self.marker=None
            if self.chain:self.chain.close()
