"""Retain the exact private wire bound for the owned media attachment.

No public API changes to frozen process04/readiness/flight implementations. The
existing parser returns non-secret metadata; the reviewed private writer still
owns delivery and cleanup. No launch or OS handle acquisition occurs on import.
"""
from runtime_candidate05.bootstrap_record import inspect_private_record
from runtime_readiness01.owned_host import StoppedChild
from runtime_flight01.host import FlightProcesses
from session_core import SessionError
from adapters.process04.host import OwnedProcesses


class TransportChild(StoppedChild):
    def __init__(self, record, clock):
        super().__init__(record, clock)
        self._native_descriptor = None

    @property
    def native_deadline(self):
        if self._native_descriptor is None or not self.delivered:
            raise SessionError('Private media bound unavailable')
        return self._native_descriptor.deadline

    def resume_and_write(self, record):
        if self._native_descriptor is not None:
            raise SessionError('Private media bound already established')
        # This is the exact original v1 frame which StoppedChild wraps in MKS2
        # and MKR1. Do not recompute from current time or extend Owner expiry.
        descriptor = inspect_private_record(record, self.record.owner, self.clock())
        self._native_descriptor = descriptor
        super().resume_and_write(record)


class TransportProcesses(FlightProcesses):
    def prepare(self):
        # Frozen settings03/05 prepare methods only check author-path source pins
        # then call OwnedProcesses.prepare. Replace those source checks with the
        # exact portable closure pins, not their runtime ownership/lease methods.
        from runtime_transport01.integrity import verify_host_sources
        self.verified=False
        verify_host_sources()
        OwnedProcesses.prepare(self)
    def _child(self):
        if self._creating is None:
            raise SessionError('No bound allocation')
        self._creating.child = TransportChild(self._creating, self.qpc)
        return self._creating.child
