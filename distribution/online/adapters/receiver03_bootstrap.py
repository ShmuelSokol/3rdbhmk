"""Receiver03 private bootstrap; no process or pipe opens at import time.

Caller owns process creation and must use only the returned read fd as child stdin
with close_fds=True, never shell=True. The child must already include receiver03.
No native executable is launched by this module. No secrets in args/env/files.
"""
from dataclasses import asdict
import ctypes
import json
import os
import re
import struct
from session_core import Ownership, SessionError, SessionCore, Limits
from adapters.bridge import BridgeStreams


def windows_qpc():
    if os.name != 'nt':
        raise SessionError('Windows clock required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    ticks, frequency = ctypes.c_longlong(), ctypes.c_longlong()
    if not kernel.QueryPerformanceCounter(ctypes.byref(ticks)) or not kernel.QueryPerformanceFrequency(ctypes.byref(frequency)) or frequency.value < 1000:
        raise SessionError('Native clock unavailable')
    return ticks.value / frequency.value


def create_qpc_core(processes, channel, limits=Limits()):
    """NEW session pool only; never migrate deadlines of a live default-clock core."""
    streams=BridgeStreams(channel,clock=windows_qpc,capacity=limits.capacity)
    return SessionCore(processes,streams,limits,clock=windows_qpc), streams


def make_record(owner, port, key, clock=None, qpc=None):
    if type(owner) is not Ownership or any(type(v) is not str or re.fullmatch(r'[A-Za-z0-9_-]{1,128}',v) is None
            for v in (owner.session_id,owner.process_key,owner.stream_id,owner.save_prefix,owner.settings_slot)):
        raise SessionError('Invalid bootstrap ownership')
    if type(port) is not int or not 1024 <= port <= 65535 or type(key) is not bytes or len(key)!=32:
        raise SessionError('Invalid bootstrap endpoint')
    # Only QPC-domain owners minted by create_qpc_core are supported. Injectable
    # probes are for offline tests; production defaults use the identical raw
    # Windows API on both sides, never Python's default monotonic/FPlatformTime.
    qpc=qpc or windows_qpc
    clock=clock or windows_qpc
    try:
        native_now, core_now, after = qpc(), clock(), qpc()
    except Exception:
        raise SessionError('Native clock unavailable') from None
    if any(type(v) not in (int,float) or not 0 <= v <= 2**40 for v in (native_now,core_now,after,owner.expires_at)):
        raise SessionError('Invalid bootstrap clock')
    if not native_now <= core_now <= after or after-native_now>0.05:
        raise SessionError('Unproved native clock mapping')
    remaining=owner.expires_at-core_now
    if not 0 < remaining <= 86400 or native_now+remaining>2**40:
        raise SessionError('Bootstrap expired')
    # Covers cross-thread QPC one-tick ambiguity plus double rounding. Production
    # QPC frequency is required >=1000 Hz. No lifetime extension, including a
    # freshly sampled clock falling on the opposite side of a counter tick.
    deadline=min(owner.expires_at,native_now+remaining)-0.002
    if deadline<=after:raise SessionError('Bootstrap expired')
    body=json.dumps(dict(version=1,clock_domain='windows-qpc-v1',owner=asdict(owner),qpc_deadline=deadline,
                         port=port,key_hex=key.hex()),sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    if len(body)>4092:
        raise SessionError('Bootstrap too large')
    return struct.pack('!I',len(body))+body


class PrivateBootstrapPipe:
    """Single-use private inherited-stdin pipe. No listener and no spawn.

    Parent preloads <=4096 bytes, closes write end, passes read_fd to subprocess
    stdin using normal Windows handle-list inheritance, then closes its read copy.
    Record is trusted-private bootstrap, not the public HMAC command protocol.
    """
    def __init__(self, record):
        if type(record) is not bytes or not 6<=len(record)<=4096 or struct.unpack('!I',record[:4])[0]!=len(record)-4:
            raise SessionError('Invalid bootstrap frame')
        self.read_fd = None
        read_fd = write_fd = None
        try:
            read_fd,write_fd=os.pipe()
            os.set_inheritable(read_fd,False)  # Popen explicitly duplicates stdin for child
            os.set_inheritable(write_fd,False)
            # <=4096 is within Windows anonymous-pipe default buffer. One preload,
            # before spawn; partial write is failure, never an unbounded retry.
            if os.write(write_fd,record)!=len(record):
                raise SessionError('Bootstrap transfer failed')
            os.close(write_fd);write_fd=None
            self.read_fd=read_fd;read_fd=None
        except Exception:
            raise SessionError('Bootstrap transfer failed') from None
        finally:
            for fd in (read_fd,write_fd):
                if fd is not None:os.close(fd)

    def close(self):
        if self.read_fd is not None:
            fd,self.read_fd=self.read_fd,None
            os.close(fd)

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
