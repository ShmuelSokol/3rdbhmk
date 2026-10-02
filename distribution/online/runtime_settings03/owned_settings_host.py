"""Additive settings lifecycle composition with the actual process04 host.

No default ownership approval, launch, filesystem access, or thread at import.
No process launch is authorized by merely constructing this adapter.
"""
from abc import ABC, abstractmethod
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib
import importlib.util
import json
import re

from session_core import SessionError, SessionCore, Limits
from adapters.core_host import CoreAuthority
from adapters.process04.host import OwnedProcesses, OwnedStreams, check_owner
from adapters.process04.win32_child import WindowsChild
from runtime_candidate05.bootstrap_record import inspect_private_record
from runtime_settings03.launcher_contract03 import launch_inputs


class ExclusiveAllocation(ABC):
    """Capability from a trusted deployment allocator, NOT a JSON policy bit.

    Implementer must enforce the premise documented in integration.json. This
    package intentionally contains no affirmative production implementation.
    revalidate MUST raise on absent/revoked/unknown exclusivity; returns None only
    for an actually established allocation bound to the exact Ownership object.
    """
    @property
    @abstractmethod
    def root(self): ...
    @property
    @abstractmethod
    def slot_count(self): ...
    @abstractmethod
    def revalidate(self, owner): ...
    @abstractmethod
    def release_after_cleanup(self, owner): ...


class ExclusiveOwnershipAuthority(ABC):
    @abstractmethod
    def reserve(self, owner):
        """Return ExclusiveAllocation, or raise. No browser/request approval flags."""


def _probe():
    source=Path(__file__).resolve().parent.parent/'runtime_settings02'
    manifest=source/'manifest.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest()!='c42a8257ee837aa7c458e5c40ed0e26ef28075c3ccd90764a9a8fe4b6814ba3b':
        raise SessionError('Settings02 source changed')
    pins=json.loads(manifest.read_text())
    p=source/'win32_predicate.py'
    if hashlib.sha256(p.read_bytes()).hexdigest()!=pins[p.name]:
        raise SessionError('Settings02 predicate changed')
    spec=importlib.util.spec_from_file_location('settings03_win32',p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class RetainedDirectories:
    """Real GENERIC_READ/no-delete-sharing handles; does NOT establish exclusivity.

    Caller stores this object BEFORE acquire. Partial failures retain handles.
    Never close implicitly in __del__: cleanup failure must remain observable.
    """
    def __init__(self):
        self.probe=None;self.entries=[];self.root=None;self.identity=None;self.ready=False

    def acquire(self, root):
        if self.entries or self.ready:raise SessionError('Directory lease already used')
        self.probe=w=_probe()
        root=w.lex.canonical(root)
        # process04 uses CRT list2cmdline; avoid whole-token quoting ambiguity with
        # UE FParse::Value by supporting no whitespace in this revision's root.
        if any(c.isspace() for c in root):raise SessionError('Session root whitespace unsupported')
        dirs=[root,root+'/User',root+'/User/Saved',root+'/User/Saved/Config',
              root+'/User/Saved/Config/Windows',root+'/User/Saved/SaveGames',root+'/User/Temp']
        paths=[]
        for directory in dirs:
            current=directory[:3]
            for part in ['']+directory[3:].split('/'):
                if part:current=current.rstrip('/')+'/'+part
                if current.casefold() not in {p.casefold() for p in paths}:paths.append(current)
        if len(paths)>128:raise SessionError('Directory depth limit')
        self.root=root
        for path in paths:
            # Drive root included; no creation, reparse traversal or ACL changes.
            h=w.open_attributes(path,share_delete=False,desired_access=0x80000000)
            self.entries.append((path,h,None)) # own immediately even if readback fails
            info=w.inspect_handle(h)
            self.entries[-1]=(path,h,info['identity'])
            if not info['got'] or not 0<info['n']<1024 or not info['attrs']&0x10 or info['attrs']&0x400 or \
                info['final'].casefold()!=path.casefold():
                raise SessionError('Retained directory identity/reparse refused')
            if path.casefold()==root.casefold():self.identity=info['identity']
        if w.k.GetDriveTypeW(root[:3])!=3 or not self.identity:raise SessionError('Local root required')
        self.ready=True
        self.revalidate()

    def revalidate(self):
        if not self.ready:raise SessionError('Directory lease not ready')
        w=self.probe
        for path,h,identity in self.entries:
            info=w.inspect_handle(h)
            if not info['got'] or not 0<info['n']<1024 or info['identity']!=identity or \
                info['attrs']&0x400 or not info['attrs']&0x10 or info['final'].casefold()!=path.casefold():
                raise SessionError('Retained directory changed')
        return None

    def close_after_process_cleanup(self):
        # Private lifecycle caller must first establish process/job/writer disposal.
        # Close deepest first; keep unclosed handles on failure for bounded retry.
        remaining=[]
        for entry in reversed(self.entries):
            if not self.probe.k.CloseHandle(entry[1]):remaining.append(entry)
        self.entries=list(reversed(remaining));self.ready=False
        if remaining:raise SessionError('Directory handle cleanup pending')


def _require_premise(allocation, owner):
    if not isinstance(allocation,ExclusiveAllocation):raise SessionError('Exclusive allocation absent')
    if allocation.revalidate(owner) is not None:raise SessionError('Exclusive premise unconfirmed')


def _arguments(base, held, owner, slot_count):
    # Fixed deployment recipe only. No hidden argument fragments, INI redirects,
    # command files, console commands, extra userdir or saved suffix accepted.
    forbidden=('userdir','savedir','saveddir','ini','exec','cmdline','sandbox','responsefile')
    for arg in base:
        if not re.fullmatch(r'[-/A-Za-z0-9_.=:]+',arg) or any(x in arg.lower() for x in forbidden):
            raise SessionError('Ambiguous/settings-changing base arguments')
    generated=launch_inputs(held.root,owner.settings_slot,owner.save_prefix,slot_count)
    return tuple(base)+tuple(generated['tokens'])


class _RootRecord:
    def __init__(self,owner):
        self.owner=owner;self.allocation=None;self.held=RetainedDirectories()
        self.child=None;self.creation_attempted=False;self.process_disposed=False
        self.cleaning=False


class SettingsChild:
    """Wraps, never replaces, the proven create/assign/resume/stop implementation."""
    def __init__(self, record, clock):
        self.record=record;self.clock=clock;self.inner=WindowsChild();self.process_identity=None
    def _admit(self):
        _require_premise(self.record.allocation,self.record.owner)
        self.record.held.revalidate()
    def create(self,executable,args,cwd,environment,memory_bytes):
        self._admit();r=self.record
        args=_arguments(args,r.held,r.owner,r.allocation.slot_count)
        environment=dict(environment,TEMP=r.held.root+'/User/Temp',TMP=r.held.root+'/User/Temp')
        r.creation_attempted=True # before partial process/Job acquisition
        self.inner.create(executable,args,cwd,environment,memory_bytes)
        # Bind real retained process identity; PID alone is not reused as ownership.
        k=self.inner.k
        k.GetProcessId.argtypes=[W.HANDLE];k.GetProcessId.restype=W.DWORD
        k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.GetProcessTimes.restype=W.BOOL
        times=[W.FILETIME() for _ in range(4)]
        pid=k.GetProcessId(self.inner.root)
        if not pid or not k.GetProcessTimes(self.inner.root,*[C.byref(t) for t in times]):
            raise SessionError('Owned process identity unavailable')
        self.process_identity=(pid,(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
        self._admit()
    def resume_and_write(self,record):
        self._admit()
        # Existing exact private frame, unchanged. No ownership=true or settings
        # capability injected into JSON; the native settings predicate is still required.
        inspect_private_record(record,self.record.owner,self.clock())
        self.inner.resume_and_write(record)
    def alive(self):
        try:self._admit()
        except Exception:return False
        return self.inner.alive()
    def bootstrap_done(self):return self.inner.bootstrap_done()
    def bootstrap_failed(self):return self.inner.bootstrap_failed()
    def stop(self):
        good=self.inner.stop() is True
        if good:self.record.process_disposed=True
        # Parent root handles deliberately NOT closed here: host route revocation
        # and capacity cleanup must succeed as well.
        return good


class SettingsOwnedProcesses(OwnedProcesses):
    def __init__(self,recipe,ports,revoke,*,ownership_authority=None,**options):
        if 'child_factory' in options:raise SessionError('Settings child factory cannot be replaced')
        self.ownership_authority=ownership_authority
        self.settings_records={};self._creating=None
        super().__init__(recipe,ports,revoke,child_factory=self._child,**options)
    def prepare(self):
        path=Path(__file__).resolve().parent/'prerequisite-pins.json'
        for source,expected in json.loads(path.read_text()).items():
            if hashlib.sha256(Path(source).read_bytes()).hexdigest()!=expected:
                self.verified=False
                raise SessionError('Settings integration prerequisite changed')
        super().prepare()
    def _child(self):
        r=self._creating
        if r is None:raise SessionError('No bound settings allocation')
        r.child=SettingsChild(r,self.qpc)
        return r.child
    def start(self,owner):
        check_owner(owner)
        # No boolean, config field, absent callback or default grants permission.
        if not isinstance(self.ownership_authority,ExclusiveOwnershipAuthority):
            raise SessionError('Exclusive ownership premise absent; launch refused')
        if not self.verified or self.now()>=owner.expires_at:
            raise SessionError('Prepared artifact and fresh owner required')
        if self._creating is not None or owner.process_key in self.settings_records or \
            len(self.settings_records)>=len(self.ports):raise SessionError('Settings capacity unavailable')
        for r in self.settings_records.values():
            if any(getattr(r.owner,f)==getattr(owner,f) for f in
                   ('session_id','stream_id','save_prefix','settings_slot')):
                raise SessionError('Settings identity still retained')
        r=_RootRecord(owner);self.settings_records[owner.process_key]=r
        try:
            r.allocation=self.ownership_authority.reserve(owner)
            _require_premise(r.allocation,owner)
            # P2: bound ALL derived paths before opening handles or creating a child.
            launch_inputs(r.allocation.root,owner.settings_slot,owner.save_prefix,r.allocation.slot_count)
            r.held.acquire(r.allocation.root)
            for other in self.settings_records.values():
                if other is not r and other.held.identity==r.held.identity:
                    raise SessionError('Shared settings root refused')
            self._creating=r
            super().start(owner)
        except Exception:
            try:self.stop(owner)
            except Exception:pass # quarantine record/handles; never falsely free capacity
            raise SessionError('Settings launch refused or cleanup pending') from None
        finally:self._creating=None
    def stop(self,owner):
        check_owner(owner)
        r=self.settings_records.get(owner.process_key)
        if r is None:return super().stop(owner)
        if r.owner!=owner:raise SessionError('Settings ownership mismatch')
        if r.cleaning:raise SessionError('Settings cleanup reentry refused')
        r.cleaning=True
        try:
            super().stop(owner) # deletes underlying record ONLY after revoke+Job/root/writer proof
            if r.creation_attempted and not r.process_disposed:
                raise SessionError('Settings process disposal unconfirmed')
            r.held.close_after_process_cleanup()
            if r.allocation is not None:
                if r.allocation.release_after_cleanup(owner) is not None:
                    raise SessionError('Exclusive allocation release pending')
            del self.settings_records[owner.process_key]
        finally:r.cleaning=False
    def private_settings_descriptor(self,owner):
        """Trusted in-process integration only. NOT a new wire format or ready bit.

        McClintock's possession binding can use this contract for its separately
        reviewed private native handoff. Never accept this dictionary from a client.
        Current v1 private bootstrap is intentionally unchanged and does not carry it.
        """
        r=self.settings_records.get(owner.process_key)
        if r is None or r.owner!=owner or r.cleaning or not r.child or not r.child.alive():
            raise SessionError('Settings descriptor unavailable')
        record=self.record(owner)
        if record.stopping or record.disposed:raise SessionError('Settings descriptor stopping')
        return {'root':r.held.root,'root_volume':r.held.identity[0],'root_file_id':r.held.identity[1],
                'process_id':r.child.process_identity[0],'process_created_filetime':r.child.process_identity[1],
                'settings_slot':owner.settings_slot,'save_prefix':owner.save_prefix,
                'slot_count':r.allocation.slot_count,'process_key':owner.process_key}


def make_settings_host(recipe,ports,revoke,ownership_authority=None,limits=Limits()):
    """Concrete replacement for process04.make_host at approved deployment composition.

    Returned processes.prepare() still verifies executable before core.request().
    No ownership provider supplied => every start refuses before filesystem/child IO.
    """
    if limits.capacity!=len(ports):raise SessionError('Host capacity mismatch')
    processes=SettingsOwnedProcesses(recipe,ports,revoke,ownership_authority=ownership_authority)
    streams=OwnedStreams(processes)
    core=SessionCore(processes,streams,limits,clock=processes.now)
    return core,CoreAuthority(core,streams),processes
