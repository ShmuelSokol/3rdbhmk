"""Harmless child: synthetic stdin only, no imports with network/process behavior."""
import ctypes as C
from ctypes import wintypes as W
import os
import sys
import threading
import time


def self_exit_watchdog():
    # Independent of the main thread's synchronous stdin reads. os._exit only
    # terminates THIS fixture child; it never signals a parent, job or other PID.
    time.sleep(40)
    os._exit(26)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('read', 'hold', 'ignore'):
        return 20
    threading.Thread(target=self_exit_watchdog, daemon=True,
                     name='fixture-self-exit').start()
    k = C.WinDLL('kernel32', use_last_error=True)
    k.GetHandleInformation.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
    k.GetHandleInformation.restype = W.BOOL
    flags = W.DWORD()
    # A deliberately inheritable parent event is absent from STARTUPINFOEX's list.
    # A numeric handle collision also fails closed instead of claiming isolation.
    if k.GetHandleInformation(int(sys.argv[2]), C.byref(flags)):
        return 21
    if sys.argv[1] == 'ignore':
        time.sleep(40)
        return 22
    prefix = os.read(0, 4)
    if len(prefix) != 4 or int.from_bytes(prefix, 'big') != 64:
        return 23
    body = b''
    for _ in range(64):
        chunk = os.read(0, 64 - len(body))
        if not chunk:
            return 24
        body += chunk
        if len(body) == 64:
            break
    if body != b'S' * 64:
        return 25
    if sys.argv[1] == 'hold':
        time.sleep(40)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
