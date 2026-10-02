"""Concrete browser-session core composition; no listener or media activation.

Trusted deployment code owns this object. A gateway receives tickets/bindings,
never a root, allocation, premise-provider or process ownership constructor.
"""
import hashlib,json,threading
from pathlib import Path
from session_core import SessionCore,Limits,SessionError
from adapters.core_host import CoreAuthority
from adapters.process04.host import OwnedStreams
from runtime_settings05.owned_host import PrivateSettingsProcesses
from runtime_settings06.allocator import OwnedAllocator

def verify_sources():
    root=Path(__file__).resolve().parent.parent
    m=root/'runtime_settings05/manifest.json'
    if hashlib.sha256(m.read_bytes()).hexdigest()!='a55433d1efce797539c46c8f20f93f79b63e93139fc7b495791f5cc41e13e4ac':
        raise SessionError('Frozen settings05 manifest changed')
    for name,h in json.loads(m.read_text()).items():
        if hashlib.sha256((m.parent/name).read_bytes()).hexdigest()!=h:raise SessionError('Frozen settings05 source changed')

class AllocatedHost:
    def __init__(self,recipe,ports,revoke,spec,premise,limits=Limits()):
        if limits.capacity!=len(ports) or spec.capacity!=len(ports):raise SessionError('Pool capacity mismatch')
        self.lock=threading.RLock();self.ready=False;self.stopping=False
        self.allocator=OwnedAllocator(spec,premise)
        self.processes=PrivateSettingsProcesses(recipe,ports,revoke,ownership_authority=self.allocator)
        streams=OwnedStreams(self.processes)
        self.core=SessionCore(self.processes,streams,limits,clock=self.processes.now)
        self.authority=CoreAuthority(self.core,streams)
        # One gateway serialization domain for browser callbacks, allocation
        # maintenance and shutdown; never stop a child concurrently with submit.
        self.authority.lock=self.lock
    def prepare(self):
        with self.lock:
            if self.ready or self.stopping:raise SessionError('Host preparation refused')
            verify_sources();self.processes.prepare();self.allocator.open();self.ready=True
    def request(self):
        # Browser gateway calls only this zero-argument operation. SessionCore
        # generates exact owner/slot IDs; no browser-controlled directory accepted.
        with self.lock:
            if not self.ready or self.stopping:raise SessionError('Host unavailable')
            self.tick()
            return self.core.request()
    def tick(self):
        """Trusted serialized gateway event loop calls regularly, before requests.
        Deployment provider must also notify premise_lost immediately on revocation;
        polling is not instantaneous security against an undisclosed writer.
        """
        with self.lock:
            invalid=self.allocator.invalid_owners()
            for owner in invalid:
                try:self.processes.revoke_settings(owner)
                except Exception:pass # exact cleanup below remains mandatory
            error=False
            for owner in invalid:
                try:self.core.report_crash(owner)
                except Exception:error=True
                # Covers partial starts whose SessionCore entry is already gone.
                try:self.processes.stop(owner)
                except Exception:error=True
            if error:raise SessionError('Revoked owner cleanup pending')
            self.core.tick()
    def premise_lost(self):
        # Pool-wide premise loss closes admission first. No policy JSON/boolean
        # can renew it; caller retains object if any cleanup remains uncertain.
        with self.lock:
            self.stopping=True;self.ready=False
            for r in tuple(self.processes.settings_records.values()):
                try:self.processes.revoke_settings(r.owner)
                except Exception:pass
            self.shutdown()
    def shutdown(self):
        with self.lock:
            self.stopping=True;self.ready=False
            error=False
            try:self.core.shutdown()
            except Exception:error=True
            for r in tuple(self.processes.settings_records.values()):
                try:self.processes.stop(r.owner)
                except Exception:error=True
            if error or self.processes.records or self.processes.settings_records:
                raise SessionError('Host cleanup pending; retain allocator')
            self.allocator.retire()

def make_allocated_settings_host(recipe,ports,revoke,spec,premise,limits=Limits()):
    return AllocatedHost(recipe,ports,revoke,spec,premise,limits)
