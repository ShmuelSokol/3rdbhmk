"""In-process authority seam for a future authenticated gateway RPC host.

No core API changes and no network implementation. Transport bindings are opaque
objects created here, never deserialized browser ownership fields.
"""
from dataclasses import dataclass
from functools import wraps
import threading
from session_core import Connection, InputEvent, SessionError, State


@dataclass(frozen=True, repr=False, eq=False)
class Binding:
    connection: Connection
    owner: object


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return call


class CoreAuthority:
    def __init__(self, core, streams):
        self.core, self.streams = core, streams
        self.bindings = set()
        self.lock = threading.RLock()

    @serialized
    def attach(self, ticket):
        if len(self.bindings) >= self.streams.capacity:
            raise SessionError('Attachment capacity unavailable')
        c = self.core.connect(ticket.session_id, ticket.credential)
        try:
            owners = [r['owner'] for r in self.streams.records.values()
                      if r['owner'].session_id == c.session_id]
            if len(owners) != 1:
                raise SessionError('Attachment unavailable')
            self.streams.bind(owners[0], c.connection_id)
            binding = Binding(c, owners[0])
            self.bindings.add(binding)
            return binding
        except Exception:
            try:
                self.core.cancel(c.session_id, c.credential)
            except SessionError:
                pass
            raise SessionError('Attachment unavailable') from None

    @serialized
    def validate(self, binding):
        if type(binding) is not Binding or binding not in self.bindings:
            raise SessionError('Attachment unavailable')
        c = binding.connection
        s = self.core.status(c.session_id, c.credential)
        r = self.streams._record(binding.owner)
        if s.state != State.ACTIVE or not s.connected or r['connection'] != c.connection_id:
            raise SessionError('Attachment unavailable')
        return True

    @serialized
    def submit(self, binding, event):
        self.validate(binding)
        if type(event) is not dict or set(event) != {'action','x','y'}:
            raise SessionError('Invalid semantic input')
        self.core.submit(binding.connection, InputEvent(**event))

    @serialized
    def release(self, binding):
        self.validate(binding)
        self.core.submit(binding.connection, InputEvent('move', 0, 0))

    @serialized
    def disconnect(self, binding):
        if type(binding) is not Binding:
            raise SessionError('Attachment unavailable')
        if binding not in self.bindings:
            return  # exact server-owned binding already released
        try:
            self.core.disconnect(binding.connection)
        except SessionError:
            self.core.tick()
            # Bridge close ACK proves this input path destroyed. Process cleanup
            # can still be pending and stays charged to capacity in SessionCore.
            if binding.owner.stream_id in self.streams.records:
                raise SessionError('Input cleanup pending') from None
        self.bindings.remove(binding)
