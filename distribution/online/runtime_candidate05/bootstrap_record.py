"""Production host-side preflight for the existing private-stdin format.

Syntax/identity validation is NOT authentication. Only the reviewed owned child's
private inherited handle conveys trusted provisioning. No network or process I/O.
"""
import json
import re
import struct
from dataclasses import dataclass
from session_core import Ownership, SessionError
from adapters.receiver03_bootstrap import make_record

_ID = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_OWNER = {'session_id', 'process_key', 'stream_id', 'save_prefix', 'settings_slot', 'expires_at'}
_FIELDS = {'version', 'clock_domain', 'owner', 'qpc_deadline', 'port', 'key_hex'}


@dataclass(frozen=True)
class PrivateDescriptor:
    owner: Ownership
    deadline: float
    port: int
    # No key or authentication/ready bit is returned to callers or receipts.


def _pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError()
        result[name] = value
    return result


def _number(value):
    return type(value) in (int, float) and 0 <= value <= 2**40


def inspect_private_record(frame, expected_owner, now):
    """Validate ONE exact frame against the caller's existing allocation identity."""
    try:
        if type(frame) is not bytes or not 6 <= len(frame) <= 4096:
            raise ValueError()
        if struct.unpack('!I', frame[:4])[0] != len(frame)-4:
            raise ValueError()
        if any(c < 32 or c > 126 for c in frame[4:]):
            raise ValueError()
        record = json.loads(frame[4:].decode('ascii'), object_pairs_hook=_pairs)
        if type(record) is not dict or set(record) != _FIELDS:
            raise ValueError()
        owner = record['owner']
        if type(owner) is not dict or set(owner) != _OWNER or type(expected_owner) is not Ownership:
            raise ValueError()
        for field in _OWNER-{'expires_at'}:
            if type(owner[field]) is not str or _ID.fullmatch(owner[field]) is None:
                raise ValueError()
            expected = getattr(expected_owner, field)
            if type(expected) is not str or _ID.fullmatch(expected) is None:
                raise ValueError()
        if not _number(expected_owner.expires_at):
            raise ValueError()
        if not all(_number(v) for v in (now, owner['expires_at'], record['qpc_deadline'])):
            raise ValueError()
        parsed = Ownership(**owner)
        if parsed != expected_owner or type(record['version']) is not int or record['version'] != 1:
            raise ValueError()
        if record['clock_domain'] != 'windows-qpc-v1':
            raise ValueError()
        if type(record['port']) is not int or not 1024 <= record['port'] <= 65535:
            raise ValueError()
        if type(record['key_hex']) is not str or re.fullmatch('[0-9a-f]{64}', record['key_hex']) is None:
            raise ValueError()
        deadline = record['qpc_deadline']
        if not now < deadline <= parsed.expires_at or deadline-now > 86400:
            raise ValueError()
        return PrivateDescriptor(parsed, deadline, record['port'])
    except Exception:
        raise SessionError('Private bootstrap record refused') from None


def make_private_record(owner, port, key, clock=None, qpc=None):
    """Additive preflight writer API; returns the existing format, starts nothing.

    Use only with process04 WindowsChild.resume_and_write, never the obsolete
    synchronous preloaded PrivateBootstrapPipe helper.
    """
    try:
        record = make_record(owner, port, key, clock=clock, qpc=qpc)
        # Native performs a fresh actual QPC check before and after admission.
        from adapters.receiver03_bootstrap import windows_qpc
        now = (qpc or windows_qpc)()
        inspect_private_record(record, owner, now)
        return record
    except Exception:
        raise SessionError('Private bootstrap record refused') from None
