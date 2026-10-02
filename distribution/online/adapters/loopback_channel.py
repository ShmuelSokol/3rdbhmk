"""Concrete authenticated TCP loopback client source; import opens nothing.

Not a complete native adapter: the matching UE receiver, process bootstrap,
clock-domain handshake and host wiring are NOT implemented. The channel takes a
per-process endpoint/key only from that future trusted bootstrap, never a browser.
"""
import hashlib
import hmac
import json
import socket
import struct
import time
from dataclasses import asdict
from session_core import Ownership, SessionError

MAX_FRAME = 4096


def encode_frame(value, key, direction):
    body = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')
    if not 1 <= len(body) <= MAX_FRAME:
        raise SessionError('Invalid native frame')
    signature = hmac.new(key, direction + body, hashlib.sha256).digest()
    return struct.pack('!I', len(body)) + body + signature


def decode_frame(body, signature, key, direction):
    if not 1 <= len(body) <= MAX_FRAME or len(signature) != 32 or not hmac.compare_digest(
            signature, hmac.new(key, direction + body, hashlib.sha256).digest()):
        raise SessionError('Native authentication failed')
    try:
        def pairs(items):
            result = {}
            for k, v in items:
                if k in result:
                    raise ValueError()
                result[k] = v
            return result
        value = json.loads(body.decode('ascii'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if type(value) is not dict:
            raise ValueError()
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise SessionError('Invalid native frame') from None


class LoopbackChannel:
    """One immutable endpoint/capability per exact native Ownership.

    One request per TCP connection, at most one request outstanding, no reconnect
    or command retry. OS/socket failure is ambiguous; core must revoke and clean
    up. Fresh-sequence release/close retries remain safe. Absolute timeout covers
    connect, complete request, and complete ACK, not each individual read.
    """
    def __init__(self, owner, port, key, clock=time.monotonic):
        if type(owner) is not Ownership or type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Invalid native endpoint')
        if type(key) is not bytes or len(key) != 32:
            raise ValueError('Invalid native capability')
        self.owner, self.port, self._key, self.clock = owner, port, key, clock
        self._sequence = 0
        self._busy = False

    def exchange(self, owner, packet, timeout):
        # Caller is BridgeStreams under its lock. No process names/PIDs/addresses
        # or raw secrets cross browser control or signalling messages.
        if owner != self.owner or type(packet) is not dict or packet.get('owner') != asdict(owner):
            raise SessionError('Native ownership mismatch')
        seq = packet.get('sequence')
        if self._busy or type(seq) is not int or not self._sequence < seq <= 2**53-1:
            raise SessionError('Native sequence refused')
        if type(timeout) not in (int,float) or not 0 < timeout <= 5:
            raise SessionError('Invalid native timeout')
        self._sequence = seq
        self._busy = True
        try:
            frame = encode_frame(packet, self._key, b'mikdash-request-v1\0')
            start = self.clock()
            if type(start) not in (int,float) or not 0 <= start <= 2**40:
                raise SessionError('Invalid native clock')
            deadline = start + timeout
            last = start
            def remaining():
                nonlocal last
                now = self.clock()
                if type(now) not in (int,float) or not last <= now < deadline:
                    raise SessionError('Native acknowledgment timed out')
                last = now
                return deadline - now
            # Literal loopback only: no DNS, remotely supplied host, or listen().
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer:
                peer.settimeout(remaining())
                peer.connect(('127.0.0.1', self.port))
                peer.settimeout(remaining())
                peer.sendall(frame)
                def exact(size):
                    result = bytearray()
                    while len(result) < size:
                        peer.settimeout(remaining())
                        block = peer.recv(size-len(result))
                        if not block:
                            raise SessionError('Native acknowledgment incomplete')
                        result.extend(block)
                    return bytes(result)
                size = struct.unpack('!I', exact(4))[0]
                if not 1 <= size <= MAX_FRAME:
                    raise SessionError('Invalid native frame')
                body, signature = exact(size), exact(32)
                remaining()
                return decode_frame(body, signature, self._key, b'mikdash-response-v1\0')
        except Exception:
            raise SessionError('Native channel unavailable') from None
        finally:
            self._busy = False
