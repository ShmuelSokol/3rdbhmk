"""StreamAdapter contract over an injected bounded native channel.

No socket/process implementation. exchange MUST return after game-thread ACK,
not after enqueue, and must enforce its timeout independently of the core lock.
"""
from dataclasses import asdict
import threading
import time
from session_core import Ownership, InputEvent, SessionError

SUPPORTED = frozenset(('move', 'look', 'interact', 'pause', 'mute'))


class BridgeStreams:
    def __init__(self, channel, clock=time.monotonic, timeout=1.0, capacity=1):
        if type(timeout) not in (int, float) or not 0 < timeout <= 5:
            raise ValueError('Invalid timeout')
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError('Invalid capacity')
        self.channel, self.clock, self.timeout, self.capacity = channel, clock, timeout, capacity
        self.records = {}
        self.lock = threading.RLock()
        self.last = -1.0

    def _now(self):
        n = self.clock()
        if type(n) not in (int, float) or not 0 <= n <= 2**40 or n < self.last:
            raise SessionError('Invalid bridge clock')
        self.last = n
        return n

    @staticmethod
    def _owner(owner):
        if type(owner) is not Ownership or any(type(v) is not str or not 1 <= len(v) <= 128
                for v in (owner.session_id, owner.process_key, owner.stream_id, owner.save_prefix, owner.settings_slot)):
            raise SessionError('Invalid bridge ownership')
        if type(owner.expires_at) not in (float, int) or not 0 <= owner.expires_at <= 2**40:
            raise SessionError('Invalid bridge ownership')

    def _record(self, owner):
        self._owner(owner)
        r = self.records.get(owner.stream_id)
        if r is None or r['owner'] != owner:
            raise SessionError('Bridge ownership mismatch')
        return r

    def _exchange(self, r, op, connection='', event=None):
        owner = r['owner']
        start = self._now()
        if op not in ('release', 'close') and start >= owner.expires_at:
            raise SessionError('Bridge expired')
        r['sequence'] += 1
        packet = dict(version=1, owner=asdict(owner), sequence=r['sequence'],
                      operation=op, connection_id=connection, event=event)
        # channel maps deadline conservatively into native monotonic domain during
        # authenticated process bootstrap. Raw Python timestamps MUST NOT be assumed
        # comparable to FPlatformTime/steady_clock in a separate process.
        try:
            ack = self.channel.exchange(owner, packet, self.timeout)
        except Exception:
            raise SessionError('Native acknowledgment failed') from None
        now = self._now()
        if (type(ack) is not dict or type(ack.get('version')) is not int or type(ack.get('sequence')) is not int
                or ack != dict(version=1, owner=asdict(owner),
                sequence=r['sequence'], operation=op, connection_id=connection, status='applied')
                or now - start >= self.timeout or (op not in ('release','close') and now >= owner.expires_at)):
            raise SessionError('Native acknowledgment failed')

    def open(self, owner):
        with self.lock:
            self._owner(owner)
            if owner.stream_id in self.records or len(self.records) >= self.capacity:
                raise SessionError('Bridge capacity unavailable')
            r = dict(owner=owner, sequence=0, connection='', closing=False)
            self.records[owner.stream_id] = r  # retain partial acquisition
            self._exchange(r,'open')

    def bind(self, owner, connection_id):
        """Trusted host extension, after core.connect; never an unauthenticated endpoint."""
        with self.lock:
            r = self._record(owner)
            if r['closing'] or r['connection'] or type(connection_id) is not str or not 1 <= len(connection_id) <= 128:
                raise SessionError('Bridge attachment refused')
            self._exchange(r,'bind',connection_id)
            r['connection'] = connection_id

    def send_input(self, owner, connection_id, event):
        with self.lock:
            r = self._record(owner)
            if r['closing'] or not r['connection'] or connection_id != r['connection'] or type(event) is not InputEvent:
                raise SessionError('Bridge input refused')
            event.validate()
            if event.action not in SUPPORTED:
                raise SessionError('Unsupported native action')
            self._exchange(r,'input',connection_id,asdict(event))

    def release_inputs(self, owner, connection_id):
        with self.lock:
            self._owner(owner)
            if owner.stream_id not in self.records:
                return  # no open ever attempted for this owner
            r = self._record(owner)
            if connection_id is not None and r['connection'] not in ('', connection_id):
                raise SessionError('Bridge attachment mismatch')
            self._exchange(r,'release',r['connection'])
            r['connection'] = ''

    def neutralize(self, owner, connection_id):
        """Blur release without detach: real move-zero via the core host submit path."""
        self.send_input(owner, connection_id, InputEvent('move', 0, 0))

    def close(self, owner):
        with self.lock:
            self._owner(owner)
            if owner.stream_id not in self.records:
                return
            r = self._record(owner)
            r['closing'] = True
            self._exchange(r,'close',r['connection'])
            del self.records[owner.stream_id]
