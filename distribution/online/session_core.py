"""Transport-independent, bounded lifecycle authority. No I/O adapters included."""
from collections import deque
from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac
import secrets
import threading
import time
from typing import Callable, Dict, Optional, Protocol


# Finite, precisely usable operational range, with one day's deadline headroom.
# Compare before any float conversion: math.isfinite(10**400) itself overflows.
MAX_TIME_SECONDS = 2 ** 40


def _bounded_number(value, minimum, maximum):
    return type(value) in (int, float) and minimum <= value <= maximum


class SessionError(Exception):
    """Safe, fixed-message rejection; never includes credentials or adapter errors."""


class State(str, Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    CLOSING = "closing"


@dataclass(frozen=True)
class Ownership:
    session_id: str
    process_key: str
    stream_id: str
    save_prefix: str
    settings_slot: str
    expires_at: float


class ProcessAdapter(Protocol):
    def start(self, owner: Ownership) -> None:
        """Acquire exactly this process_key; retain ownership even on partial failure."""

    def stop(self, owner: Ownership) -> None:
        """Idempotently confirm ONLY this owner's process/resources are gone."""


class StreamAdapter(Protocol):
    def open(self, owner: Ownership) -> None:
        """Bind this stream exclusively to this owned process; retain partial ownership."""

    def release_inputs(self, owner: Ownership, connection_id: Optional[str]) -> None:
        """Clear all held inputs for this binding (None means all owner inputs)."""

    def close(self, owner: Ownership) -> None:
        """Idempotently revoke this owner's stream and confirm its resources are gone."""

    def send_input(self, owner: Ownership, connection_id: str, event: "InputEvent") -> None:
        """Dispatch only through this exact live binding; never broadcast."""


@dataclass(frozen=True)
class Limits:
    capacity: int = 1
    max_queue: int = 8
    queue_seconds: float = 60.0
    reconnect_seconds: float = 20.0
    lifetime_seconds: float = 900.0
    event_limit: int = 128

    def __post_init__(self):
        for name, minimum in (("capacity", 1), ("max_queue", 0), ("event_limit", 1)):
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= 10000:
                raise ValueError("Invalid bounded count")
        for value in (self.queue_seconds, self.reconnect_seconds, self.lifetime_seconds):
            if not _bounded_number(value, 0, 86400) or value == 0:
                raise ValueError("Durations must be finite, positive and at most one day")


@dataclass(frozen=True, repr=False)
class Ticket:
    session_id: str
    credential: str


@dataclass(frozen=True, repr=False)
class Connection:
    session_id: str
    connection_id: str
    credential: str


@dataclass(frozen=True)
class Snapshot:
    session_id: str
    state: State
    connected: bool
    expires_at: float
    queue_position: Optional[int]


@dataclass(frozen=True)
class Event:
    session_id: str
    kind: str


@dataclass(frozen=True)
class InputEvent:
    action: str
    x: float = 0.0
    y: float = 0.0

    def validate(self):
        if type(self.action) is not str or self.action not in ("move", "look", "interact", "pause", "reset", "dove", "mute"):
            raise SessionError("Unsupported input")
        if any(not _bounded_number(v, -1, 1) for v in (self.x, self.y)):
            raise SessionError("Invalid input values")
        if self.action not in ("move", "look") and (self.x != 0 or self.y != 0):
            raise SessionError("Action does not accept axes")


@dataclass
class _Session:
    identity: Ownership
    credential_hash: bytes
    created: float
    expires: float
    queue_expires: float
    state: State = State.QUEUED
    connection_id: Optional[str] = None
    reconnect_until: Optional[float] = None
    stream_closed: bool = False
    process_stopped: bool = False
    release_done: bool = False


class SessionCore:
    """One serialized authority per worker pool; all times are monotonic seconds.

    Call tick regularly. Adapters must be bounded, non-reentrant, synchronous ownership
    operations. They may enqueue bounded work only if completion still satisfies each
    method's contract. Never return successful stop/close before disposal is confirmed.
    """

    def __init__(self, processes: ProcessAdapter, streams: StreamAdapter,
                 limits: Limits = Limits(), clock: Callable[[], float] = time.monotonic):
        self._processes = processes
        self._streams = streams
        self.limits = limits
        self._clock = clock
        self._last_time = float("-inf")
        self._sessions: Dict[str, _Session] = {}
        self._events = deque(maxlen=limits.event_limit)
        self._lock = threading.RLock()
        self._in_adapter = False
        self._shutdown = False
        self._namespace = secrets.token_hex(16)
        self._sequence = 0

    def _now(self):
        if self._in_adapter:
            raise SessionError("Adapter reentry forbidden")
        value = self._clock()
        if not _bounded_number(value, 0, MAX_TIME_SECONDS - 86400) or value < self._last_time:
            raise SessionError("Invalid monotonic clock")
        self._last_time = value
        return value

    def _id(self, kind):
        self._sequence += 1
        return "{}_{}_{}".format(kind, self._namespace, self._sequence)

    @staticmethod
    def _hash(credential):
        if type(credential) is not str or not 32 <= len(credential) <= 128:
            raise SessionError("Invalid session credential")
        try:
            return hashlib.sha256(credential.encode("ascii")).digest()
        except UnicodeEncodeError:
            raise SessionError("Invalid session credential") from None

    def _auth(self, session_id, credential):
        if type(session_id) is not str or not 1 <= len(session_id) <= 128:
            raise SessionError("Invalid session credential")
        digest = self._hash(credential)
        session = self._sessions.get(session_id)
        if session is None or not hmac.compare_digest(session.credential_hash, digest):
            raise SessionError("Invalid session credential")
        if session.state == State.CLOSING:
            raise SessionError("Session closing")
        self._require_live(session)
        return session

    def _record(self, session, kind):
        self._events.append(Event(session.identity.session_id, kind))

    def _call(self, method, *args):
        self._in_adapter = True
        try:
            method(*args)
            return True
        except Exception:
            # Adapter exceptions can contain URLs/credentials; never retain them.
            return False
        finally:
            self._in_adapter = False

    def _terminate(self, session, reason):
        if session.state == State.CLOSING:
            return
        self._record(session, reason)
        if session.state == State.QUEUED:
            del self._sessions[session.identity.session_id]
            return
        session.state = State.CLOSING
        # Revoke before callbacks, including after partial provisioning.
        session.credential_hash = b""
        session.reconnect_until = None

    def _cleanup(self, session):
        owner = session.identity
        if not session.release_done:
            session.release_done = self._call(self._streams.release_inputs, owner, session.connection_id)
        if not session.stream_closed:
            session.stream_closed = self._call(self._streams.close, owner)
        if not session.process_stopped:
            session.process_stopped = self._call(self._processes.stop, owner)
        if session.stream_closed and session.process_stopped:
            # Confirmed stream + process destruction also guarantees no held input survives.
            del self._sessions[owner.session_id]
            self._record(session, "disposed")
        else:
            self._record(session, "cleanup_pending")

    def _occupied(self):
        return sum(s.state != State.QUEUED for s in self._sessions.values())

    def _expire(self, session, now):
        """Revoke using one fresh timestamp, without invoking adapters."""
        if session.state == State.CLOSING:
            return True
        if now >= session.expires:
            self._terminate(session, "lifetime_expired")
        elif session.state == State.QUEUED and now >= session.queue_expires:
            self._terminate(session, "queue_expired")
        elif (session.state == State.ACTIVE and session.connection_id is None
              and now >= session.reconnect_until):
            self._terminate(session, "reconnect_expired")
        else:
            return False
        return True

    def _require_live(self, session):
        # Adapter work elsewhere in a sweep may have consumed this lease. Do not
        # recursively sweep: one target check suffices to reject stale authority.
        if (session.identity.session_id not in self._sessions
                or self._expire(session, self._now())):
            raise SessionError("Session expired or closing")

    def _acquisition_time(self, session):
        """Invalid clock after acquisition must also revoke partial resources."""
        try:
            return self._now()
        except SessionError:
            self._terminate(session, "clock_invalid")
            self._cleanup(session)
            raise

    def _advance(self):
        for session in list(self._sessions.values()):
            self._expire(session, self._now())
        for session in list(self._sessions.values()):
            if session.state == State.CLOSING:
                self._cleanup(session)
        for session in list(self._sessions.values()):
            if self._shutdown or self._occupied() >= self.limits.capacity:
                break
            if session.state != State.QUEUED:
                continue
            # Prior cleanup/provisioning callbacks can consume queue or lifetime.
            if self._expire(session, self._now()):
                continue
            session.state = State.ACTIVE  # Reserve capacity BEFORE acquisition.
            # Initial attachment grace starts only when ready; provisioning still
            # consumes absolute lifetime, and no attachment can occur under this lock.
            session.reconnect_until = session.expires
            owner = session.identity
            if not self._call(self._processes.start, owner):
                self._terminate(session, "provision_failed")
                self._cleanup(session)
                continue
            if self._expire(session, self._acquisition_time(session)):
                self._cleanup(session)
                continue
            if not self._call(self._streams.open, owner):
                self._terminate(session, "provision_failed")
                self._cleanup(session)
                continue
            ready_at = self._acquisition_time(session)
            if self._expire(session, ready_at):
                self._cleanup(session)
                continue
            session.reconnect_until = min(session.expires, ready_at + self.limits.reconnect_seconds)
            self._record(session, "ready")
        # One final callback-free revocation pass catches leases consumed by any
        # callback above. Newly closing resources are quarantined until next sweep.
        # No drain-until-stable/retry loop, even when every callback advances time.
        for session in list(self._sessions.values()):
            self._expire(session, self._now())

    def request(self):
        with self._lock:
            self._now()
            self._advance()
            if self._shutdown:
                raise SessionError("Core shut down")
            queued = sum(s.state == State.QUEUED for s in self._sessions.values())
            if self._occupied() >= self.limits.capacity and queued >= self.limits.max_queue:
                raise SessionError("Queue full")
            now = self._now()  # Admission time, after maintenance callbacks.
            owner = Ownership(*(self._id(kind) for kind in ("session", "process", "stream", "save", "settings")),
                              expires_at=now + self.limits.lifetime_seconds)
            credential = secrets.token_urlsafe(32)
            session = _Session(owner, self._hash(credential), now, now + self.limits.lifetime_seconds,
                               min(now + self.limits.queue_seconds, now + self.limits.lifetime_seconds))
            self._sessions[owner.session_id] = session
            self._record(session, "requested")
            self._advance()
            if owner.session_id not in self._sessions or session.state == State.CLOSING:
                raise SessionError("Provision failed")
            self._require_live(session)
            return Ticket(owner.session_id, credential)

    def connect(self, session_id, credential):
        with self._lock:
            self._now()
            self._advance()
            session = self._auth(session_id, credential)
            if session.state != State.ACTIVE or session.connection_id is not None:
                raise SessionError("Session not available for attachment")
            rotated = secrets.token_urlsafe(32)
            self._require_live(session)  # Fresh check immediately before attachment.
            session.credential_hash = self._hash(rotated)
            session.connection_id = self._id("connection")
            session.reconnect_until = None
            self._record(session, "connected")
            return Connection(session_id, session.connection_id, rotated)

    def _connection(self, connection):
        if type(connection) is not Connection:
            raise SessionError("Invalid connection")
        if type(connection.connection_id) is not str or not 1 <= len(connection.connection_id) <= 128:
            raise SessionError("Invalid connection")
        session = self._auth(connection.session_id, connection.credential)
        if (session.state != State.ACTIVE or session.connection_id is None
                or session.connection_id != connection.connection_id):
            raise SessionError("Stale connection")
        return session

    def submit(self, connection, event):
        with self._lock:
            self._now()
            self._advance()
            session = self._connection(connection)
            if type(event) is not InputEvent:
                raise SessionError("Invalid input")
            event.validate()
            self._require_live(session)  # No adapter callback between this and dispatch.
            if not self._call(self._streams.send_input, session.identity, connection.connection_id, event):
                self._terminate(session, "input_adapter_failed")
                self._cleanup(session)
                raise SessionError("Input adapter failed")

    def disconnect(self, connection):
        with self._lock:
            self._now()
            self._advance()
            session = self._connection(connection)
            now = self._now()
            if self._expire(session, now):
                raise SessionError("Session expired or closing")
            session.connection_id = None  # Revoke old input binding before release.
            session.reconnect_until = min(session.expires, now + self.limits.reconnect_seconds)
            if not self._call(self._streams.release_inputs, session.identity, connection.connection_id):
                self._terminate(session, "release_failed")
                self._cleanup(session)
                raise SessionError("Input release failed")
            self._require_live(session)  # Release time consumes, never renews, grace.
            self._record(session, "disconnected")

    def cancel(self, session_id, credential):
        with self._lock:
            self._now()
            self._advance()
            session = self._auth(session_id, credential)
            self._terminate(session, "cancelled")
            self._advance()

    def report_crash(self, owner):
        """Trusted adapter entry point, NEVER a browser endpoint. Exact ownership required."""
        with self._lock:
            self._now()
            self._advance()
            if type(owner) is not Ownership:
                raise SessionError("Invalid ownership")
            if (any(type(value) is not str or not 1 <= len(value) <= 128
                    for value in (owner.session_id, owner.process_key, owner.stream_id,
                                  owner.save_prefix, owner.settings_slot))
                    or not _bounded_number(owner.expires_at, 0, MAX_TIME_SECONDS)):
                raise SessionError("Invalid ownership")
            session = self._sessions.get(owner.session_id)
            if session is None:
                return False  # Delayed/double report cannot target a replacement.
            if session.identity != owner or session.state == State.QUEUED:
                raise SessionError("Ownership mismatch")
            self._terminate(session, "crashed")
            self._advance()
            return True

    def status(self, session_id, credential):
        with self._lock:
            self._now()
            self._advance()
            session = self._auth(session_id, credential)
            queue = [s.identity.session_id for s in self._sessions.values() if s.state == State.QUEUED]
            return Snapshot(session_id, session.state, session.connection_id is not None,
                            session.expires, queue.index(session_id) + 1 if session_id in queue else None)

    def tick(self):
        with self._lock:
            self._now()
            self._advance()

    def events(self):
        with self._lock:
            self._now()
            return tuple(self._events)

    def shutdown(self):
        with self._lock:
            self._now()
            self._shutdown = True
            for session in list(self._sessions.values()):
                self._terminate(session, "shutdown")
            self._advance()

    def cleanup_pending(self):
        with self._lock:
            self._now()
            return sum(s.state == State.CLOSING for s in self._sessions.values())
