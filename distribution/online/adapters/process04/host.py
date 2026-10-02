"""Owned host wiring. No launch, socket, filesystem write or thread at import.

All entry points are synchronous and serialized by the host/core. Construction
does not authorize launch. A reviewed executable recipe and route authority are
required; there is deliberately no default packaged-game recipe.
"""
from dataclasses import dataclass
import hashlib
import os
import re
import secrets
import socket
import time

from session_core import Ownership, SessionError, SessionCore, Limits
from adapters.bridge import BridgeStreams
from adapters.core_host import CoreAuthority
from adapters.loopback_channel import LoopbackChannel
from adapters.receiver03_bootstrap import windows_qpc, make_record
from adapters.process04.win32_child import WindowsChild
from adapters.process04.consumption_channel import ConsumptionChannel


def check_owner(owner):
    if type(owner) is not Ownership or any(type(x) is not str or
            re.fullmatch(r'[A-Za-z0-9_-]{1,128}', x) is None for x in
            (owner.session_id, owner.process_key, owner.stream_id, owner.save_prefix, owner.settings_slot)):
        raise SessionError('Invalid process ownership')
    if type(owner.expires_at) not in (int, float) or not 0 <= owner.expires_at <= 2**40:
        raise SessionError('Invalid process ownership')


@dataclass(frozen=True, repr=False)
class LaunchRecipe:
    """Trusted deployment input, NEVER browser/RPC fields.

    args is a tuple of public arguments. Only five identity placeholders allowed;
    no arbitrary caller substitution and no port/key/credential placeholder.
    This artifact must implement receiver03 startup, input gate, save/settings
    ownership and stopped-streamer initialization before being approved for use.
    """
    executable: str
    sha256: str
    cwd: str
    args: tuple
    system_root: str
    temporary: str
    memory_bytes: int = 8 * 1024**3

    def validate(self):
        for path in (self.executable, self.cwd, self.system_root, self.temporary):
            if type(path) is not str or not 1 <= len(path) <= 1024 or '\0' in path or not os.path.isabs(path):
                raise SessionError('Invalid trusted launch recipe')
        if type(self.sha256) is not str or re.fullmatch('[a-f0-9]{64}', self.sha256) is None:
            raise SessionError('Invalid trusted launch recipe')
        if type(self.args) is not tuple or len(self.args) > 32 or any(
                type(a) is not str or not 1 <= len(a) <= 512 or any(c in a for c in ('\0', '\n', '\r')) for a in self.args):
            raise SessionError('Invalid trusted launch recipe')
        if type(self.memory_bytes) is not int or not 256*1024**2 <= self.memory_bytes <= 32*1024**3:
            raise SessionError('Invalid trusted launch recipe')
        # No secrets can be interpolated; static args themselves are deployment-
        # reviewed public data. Do not accept recipes from an admission request.
        try:
            self.arguments(Ownership('s', 'p', 'v', 'save', 'settings', 1))
        except Exception:
            raise SessionError('Invalid trusted launch recipe') from None

    def arguments(self, owner):
        values = {k: getattr(owner, k) for k in ('session_id', 'process_key', 'stream_id', 'save_prefix', 'settings_slot')}
        # Only exact {name} substitutions; reject Python format attribute/index
        # traversal, conversion flags, format specs, and escaped braces.
        result = []
        for arg in self.args:
            for key, value in values.items():
                arg = arg.replace('{' + key + '}', value)
            if '{' in arg or '}' in arg:
                raise SessionError('Invalid trusted launch recipe')
            result.append(arg)
        return tuple(result)

    def environment(self):
        return dict(SystemRoot=self.system_root, WINDIR=self.system_root,
                    TEMP=self.temporary, TMP=self.temporary)


def verify_artifact(recipe):
    """Pin launch input. Trusted deployment directory must deny untrusted writes.

    This hash check is not an ACL/TOCTOU defense; deployment immutability is a
    prerequisite. Fixed 2 GiB maximum and 2048 chunks bound host-side hash work.
    """
    recipe.validate()
    try:
        size = os.path.getsize(recipe.executable)
        if not 0 < size <= 2*1024**3:
            raise ValueError()
        digest = hashlib.sha256()
        with open(recipe.executable, 'rb') as src:
            for _ in range(2049):
                chunk = src.read(1024**2)
                if not chunk:
                    break
                digest.update(chunk)
            else:
                raise ValueError()
        if digest.hexdigest() != recipe.sha256:
            raise ValueError()
    except Exception:
        raise SessionError('Trusted executable verification failed') from None


def port_hint(port, timeout):
    """Reachability ONLY, not readiness/authentication. Sends no bytes.

    No listen/bind and no port reservation fiction. A collision is detected by
    the subsequent HMAC open failure and never authorizes killing the squatter.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer:
        peer.settimeout(timeout)
        try:
            peer.connect(('127.0.0.1', port))
            return True
        except (ConnectionRefusedError, TimeoutError, socket.timeout):
            return False


@dataclass(repr=False)
class Lease:
    owner: Ownership
    port: int
    child: object
    channel: object = None
    reachable: bool = False
    stopping: bool = False
    revoked: bool = False
    disposed: bool = False


class OwnedProcesses:
    def __init__(self, recipe, ports, revoke, *, clock=windows_qpc, child_factory=WindowsChild,
                 channel_factory=ConsumptionChannel, hint=port_hint, sleeper=time.sleep,
                 key_factory=lambda: secrets.token_bytes(32), verify=verify_artifact,
                 start_seconds=30.0, write_seconds=2.0, cleanup_seconds=1.0, qpc=windows_qpc):
        recipe.validate()
        if type(ports) is not tuple or not 1 <= len(ports) <= 16 or any(
                type(p) is not int or not 1024 <= p <= 65535 for p in ports) or len(set(ports)) != len(ports):
            raise SessionError('Invalid process port pool')
        for value, upper in ((start_seconds, 60), (write_seconds, 5), (cleanup_seconds, 5)):
            if type(value) not in (int, float) or not 0 < value <= upper:
                raise SessionError('Invalid process deadline')
        self.recipe, self.ports, self.revoke = recipe, ports, revoke
        self.clock, self.child_factory, self.channel_factory = clock, child_factory, channel_factory
        self.qpc = qpc  # independent raw-QPC probe; never assume an injected clock's domain
        self.hint, self.sleep, self.key_factory, self.verify = hint, sleeper, key_factory, verify
        self.start_seconds, self.write_seconds, self.cleanup_seconds = start_seconds, write_seconds, cleanup_seconds
        self.records = {}
        self.last = -1.0
        self.verified = False

    def now(self):
        try:
            n = self.clock()
            if type(n) not in (int, float) or not self.last <= n <= 2**40 or n < 0:
                raise ValueError()
            self.last = n
            return n
        except Exception:
            raise SessionError('Invalid host clock') from None

    def record(self, owner):
        check_owner(owner)
        r = self.records.get(owner.process_key)
        if r is None or r.owner != owner:
            raise SessionError('Process ownership mismatch')
        return r

    def prepare(self):
        """Explicit offline artifact verification, before admitting any sessions."""
        self.verified = False
        try:
            self.verify(self.recipe)
            self.verified = True
        except Exception:
            raise SessionError('Trusted executable verification failed') from None

    def start(self, owner):
        check_owner(owner)
        start = self.now()
        if not self.verified or owner.process_key in self.records or len(self.records) >= len(self.ports) or start >= owner.expires_at:
            raise SessionError('Process admission refused')
        if any(any(getattr(r.owner, field) == getattr(owner, field) for field in
                   ('session_id', 'stream_id', 'save_prefix', 'settings_slot')) for r in self.records.values()):
            raise SessionError('Process identity collision')
        used = {r.port for r in self.records.values()}
        port = next(p for p in self.ports if p not in used)
        # Store BEFORE any OS acquisition. The constructor contract forbids I/O.
        try:
            r = Lease(owner, port, self.child_factory())
        except Exception:
            raise SessionError('Owned child allocation unavailable') from None
        self.records[owner.process_key] = r
        try:
            key = self.key_factory()
            record = make_record(owner, port, key, clock=self.now, qpc=self.qpc)
            r.channel = self.channel_factory(owner, port, key, clock=self.now)
            del key
            r.child.create(self.recipe.executable, self.recipe.arguments(owner), self.recipe.cwd,
                           self.recipe.environment(), self.recipe.memory_bytes)
            deadline = min(start + self.start_seconds, owner.expires_at)
            if self.now() >= deadline:
                raise SessionError('Process startup expired')
            write_deadline = min(deadline, self.now() + self.write_seconds)
            r.child.resume_and_write(record)
            del record
            write_confirmed = False
            # Both elapsed time and iteration count are bounded (frozen clocks
            # in an injected adapter cannot turn this into an infinite loop).
            for _ in range(6001):
                n = self.now()
                if n >= deadline or not r.child.alive() or r.child.bootstrap_failed():
                    break
                if not write_confirmed:
                    # A completion first observed after its deadline is not
                    # accepted, even if the worker raced the host's next poll.
                    if n >= write_deadline:
                        break
                    write_confirmed = r.child.bootstrap_done()
                if write_confirmed and self.hint(port, min(0.05, deadline-n)):
                    if self.now() >= deadline or not r.child.alive():
                        break
                    r.reachable = True
                    return  # NOT admission: BridgeStreams.open still needs HMAC ACK
                self.sleep(min(0.01, max(0, deadline-self.now())))
            raise SessionError('Process startup unavailable')
        except Exception:
            r.stopping = True
            # Core cleanup calls both stream.close and process.stop. Make a
            # bounded best effort now too, without dropping a failed lease.
            try:
                self.stop(owner)
            except Exception:
                pass
            raise SessionError('Process startup unavailable') from None

    def exchange(self, owner, packet, timeout):
        try:
            r = self.record(owner)
            if r.stopping or not r.reachable or not r.child.alive() or self.now() >= owner.expires_at:
                raise SessionError('Owned channel unavailable')
            return r.channel.exchange(owner, packet, timeout)
        except Exception:
            raise SessionError('Owned channel unavailable') from None

    def stop(self, owner):
        check_owner(owner)
        if owner.process_key not in self.records:
            return
        r = self.record(owner)
        r.stopping = True
        # Revoke exact stream authority independently of process cleanup. A
        # synchronous close callback may reenter: return failure, never recurse.
        if getattr(r, '_cleaning', False):
            raise SessionError('Owned cleanup pending')
        r._cleaning = True
        try:
            if not r.revoked:
                try:
                    r.revoked = self.revoke(owner) is None
                except Exception:
                    pass
            # Bad clock/revoke must not prevent at least one exact-job stop.
            try:
                deadline = self.now() + self.cleanup_seconds
            except SessionError:
                deadline = None
            for _ in range(501):
                if not r.disposed:
                    try:
                        r.disposed = r.child.stop() is True
                    except Exception:
                        pass
                if r.disposed or deadline is None:
                    break
                if self.now() >= deadline:
                    break
                self.sleep(0.01)
            if not (r.revoked and r.disposed):
                raise SessionError('Owned cleanup pending')
            del self.records[owner.process_key]
        except Exception:
            raise SessionError('Owned cleanup pending') from None
        finally:
            r._cleaning = False


class OwnedStreams(BridgeStreams):
    """Frozen bridge API, stronger close proof: native ACK alone is insufficient."""
    def __init__(self, processes):
        super().__init__(processes, clock=processes.now, timeout=1.0, capacity=len(processes.ports))
        self.processes = processes

    def close(self, owner):
        with self.lock:
            self._owner(owner)
            r = self.records.get(owner.stream_id)
            if r is not None:
                if r['owner'] != owner:
                    raise SessionError('Bridge ownership mismatch')
                r['closing'] = True
            # Termination makes release unconditional even if native ACK failed.
            # Only remove the bridge allocation after route revocation AND exact
            # process/job/writer disposal; a failed close retains core capacity.
            self.processes.stop(owner)
            if r is not None:
                del self.records[owner.stream_id]


def make_host(recipe, ports, revoke, limits=Limits()):
    """No I/O. Call processes.prepare() before core.request(). QPC-only new pool."""
    if limits.capacity != len(ports):
        raise SessionError('Host capacity mismatch')
    processes = OwnedProcesses(recipe, ports, revoke)
    streams = OwnedStreams(processes)
    core = SessionCore(processes, streams, limits, clock=processes.now)
    return core, CoreAuthority(core, streams), processes
