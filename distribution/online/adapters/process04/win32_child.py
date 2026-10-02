"""Explicit-launch Windows backend. Import performs no OS calls or thread starts.

One process per job: use the real game executable, not a launcher that forks it.
No PID/name-based operations. Every partially acquired handle stays in this lease.
"""
import ctypes as C
from ctypes import wintypes as W
import os
import subprocess
import threading
import time

from session_core import SessionError


H = W.HANDLE
SZ = C.c_size_t


class Security(C.Structure):
    _fields_ = [('length', W.DWORD), ('descriptor', C.c_void_p), ('inherit', W.BOOL)]


class Startup(C.Structure):
    _fields_ = [('cb', W.DWORD), ('reserved', W.LPWSTR), ('desktop', W.LPWSTR),
                ('title', W.LPWSTR), ('x', W.DWORD), ('y', W.DWORD),
                ('xs', W.DWORD), ('ys', W.DWORD), ('xc', W.DWORD), ('yc', W.DWORD),
                ('fill', W.DWORD), ('flags', W.DWORD), ('show', W.WORD),
                ('reserved2', W.WORD), ('bytes', C.c_void_p),
                ('stdin', H), ('stdout', H), ('stderr', H)]


class StartupEx(C.Structure):
    _fields_ = [('startup', Startup), ('attributes', C.c_void_p)]


class ProcessInfo(C.Structure):
    _fields_ = [('process', H), ('thread', H), ('pid', W.DWORD), ('tid', W.DWORD)]


class BasicLimit(C.Structure):
    _fields_ = [('process_time', C.c_longlong), ('job_time', C.c_longlong),
                ('flags', W.DWORD), ('minimum', SZ), ('maximum', SZ),
                ('active', W.DWORD), ('affinity', SZ), ('priority', W.DWORD),
                ('scheduling', W.DWORD)]


class IO(C.Structure):
    _fields_ = [(n, C.c_ulonglong) for n in ('ro', 'wo', 'oo', 'rb', 'wb', 'ob')]


class ExtendedLimit(C.Structure):
    _fields_ = [('basic', BasicLimit), ('io', IO), ('process_memory', SZ),
                ('job_memory', SZ), ('peak_process', SZ), ('peak_job', SZ)]


class Accounting(C.Structure):
    _fields_ = [(n, C.c_longlong) for n in ('user', 'kernel', 'period_user', 'period_kernel')] + [
        (n, W.DWORD) for n in ('faults', 'total', 'active', 'terminated')]


def require(value):
    if not value:
        raise SessionError('Owned Windows operation failed')


def kernel_api():
    if os.name != 'nt' or C.sizeof(C.c_void_p) != 8:
        raise SessionError('64-bit Windows host required')
    k = C.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': (H, [C.c_void_p, W.LPCWSTR]),
        'SetInformationJobObject': (W.BOOL, [H, C.c_int, C.c_void_p, W.DWORD]),
        'QueryInformationJobObject': (W.BOOL, [H, C.c_int, C.c_void_p, W.DWORD, C.c_void_p]),
        'AssignProcessToJobObject': (W.BOOL, [H, H]),
        'TerminateJobObject': (W.BOOL, [H, W.UINT]),
        'TerminateProcess': (W.BOOL, [H, W.UINT]),
        'ResumeThread': (W.DWORD, [H]),
        'CloseHandle': (W.BOOL, [H]),
        'WaitForSingleObject': (W.DWORD, [H, W.DWORD]),
        'CreatePipe': (W.BOOL, [C.POINTER(H), C.POINTER(H), C.POINTER(Security), W.DWORD]),
        'SetHandleInformation': (W.BOOL, [H, W.DWORD, W.DWORD]),
        'CreateFileW': (H, [W.LPCWSTR, W.DWORD, W.DWORD, C.POINTER(Security), W.DWORD, W.DWORD, H]),
        'InitializeProcThreadAttributeList': (W.BOOL, [C.c_void_p, W.DWORD, W.DWORD, C.POINTER(SZ)]),
        'UpdateProcThreadAttribute': (W.BOOL, [C.c_void_p, W.DWORD, SZ, C.c_void_p, SZ, C.c_void_p, C.c_void_p]),
        'DeleteProcThreadAttributeList': (None, [C.c_void_p]),
        'CreateProcessW': (W.BOOL, [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL,
                                  W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(StartupEx), C.POINTER(ProcessInfo)]),
        'WriteFile': (W.BOOL, [H, C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.c_void_p]),
        'GetCurrentProcess': (H, []), 'GetCurrentThread': (H, []),
        'DuplicateHandle': (W.BOOL, [H, H, H, C.POINTER(H), W.DWORD, W.BOOL, W.DWORD]),
        'CancelSynchronousIo': (W.BOOL, [H]),
    }
    for name, (result, args) in signatures.items():
        f = getattr(k, name)
        f.restype, f.argtypes = result, args
    return k


class WindowsChild:
    """Retain on any failure. stop() returns True only after OS proof and closes.

    create() deliberately does not auto-clean on failure: the host already stores
    this lease before calling it, so a failed cleanup cannot lose its ownership.
    All methods except the private writer run on one serialized host thread.
    """
    def __init__(self, api=None):
        self.k = api  # lazily initialize only on explicit create
        self.job = self.root = self.thread = self.reader = self.writer = self.null = None
        self.assigned = False
        self._worker = None
        self._worker_handle = None
        self._worker_lock = threading.Lock()
        self._cancel = threading.Event()
        self._done = threading.Event()
        self._write_ok = False
        self._write_closed = False
        self._closing = False

    def _close(self, name):
        h = getattr(self, name)
        if h:
            require(self.k.CloseHandle(h))
            setattr(self, name, None)

    def create(self, executable, args, cwd, environment, memory_bytes):
        if self.job or self.root or self._closing:
            raise SessionError('Owned child already used')
        self.k = self.k or kernel_api()
        k = self.k
        self.job = k.CreateJobObjectW(None, None)
        require(self.job)
        limits = ExtendedLimit()
        # Kill-on-close, one active process, process/job memory limits. NO breakaway.
        limits.basic.flags = 0x2000 | 0x8 | 0x100 | 0x200
        limits.basic.active = 1
        limits.process_memory = limits.job_memory = memory_bytes
        require(k.SetInformationJobObject(self.job, 9, C.byref(limits), C.sizeof(limits)))
        sa = Security(C.sizeof(Security), None, True)
        r, w = H(), H()
        require(k.CreatePipe(C.byref(r), C.byref(w), C.byref(sa), 4096))
        self.reader, self.writer = r.value, w.value
        require(k.SetHandleInformation(self.writer, 1, 0))
        self.null = k.CreateFileW('NUL', 0x40000000, 3, C.byref(sa), 3, 0x80, None)
        if self.null == C.c_void_p(-1).value:
            self.null = None
        require(self.null)
        si = StartupEx()
        si.startup.cb = C.sizeof(si)
        si.startup.flags = 0x101  # USESTDHANDLES | USESHOWWINDOW, hidden
        si.startup.stdin, si.startup.stdout, si.startup.stderr = self.reader, self.null, self.null
        size = SZ()
        k.InitializeProcThreadAttributeList(None, 1, 0, C.byref(size))
        require(0 < size.value <= 65536)
        storage = C.create_string_buffer(size.value)
        si.attributes = C.cast(storage, C.c_void_p)
        require(k.InitializeProcThreadAttributeList(si.attributes, 1, 0, C.byref(size)))
        try:
            handles = (H * 2)(self.reader, self.null)
            require(k.UpdateProcThreadAttribute(si.attributes, 0, 0x20002, handles,
                                                C.sizeof(handles), None, None))
            command = C.create_unicode_buffer(subprocess.list2cmdline([executable] + list(args)))
            # Caller supplies a tiny trusted environment; never inherit host credentials.
            env = C.create_unicode_buffer('\0'.join(k + '=' + v for k, v in sorted(environment.items())) + '\0\0')
            pi = ProcessInfo()
            require(k.CreateProcessW(executable, command, None, None, True,
                    0x4 | 0x08000000 | 0x80000 | 0x400, env, cwd, C.byref(si), C.byref(pi)))
            self.root, self.thread = pi.process, pi.thread
        finally:
            k.DeleteProcThreadAttributeList(si.attributes)
        # Parent copies must close before writer starts: killing the child then
        # guarantees no remaining read handle can keep a blocked write alive.
        self._close('reader')
        self._close('null')
        require(k.AssignProcessToJobObject(self.job, self.root))
        self.assigned = True

    def resume_and_write(self, record):
        if not self.assigned or self._closing or self._worker is not None:
            raise SessionError('Owned bootstrap refused')
        require(type(record) is bytes and 6 <= len(record) <= 4096)
        # Never preload a synchronous pipe on the host thread. Resume only after
        # assignment; one owned writer per capacity slot, never abandoned/replaced.
        require(self.k.ResumeThread(self.thread) != 0xffffffff)
        self._close('thread')
        self._worker = threading.Thread(target=self._write, args=(record,), daemon=True,
                                        name='private-bootstrap')
        try:
            self._worker.start()
        except Exception:
            self._worker = None  # no worker owns writer; stop() must close it
            raise SessionError('Bootstrap writer unavailable') from None

    def _write(self, record):
        buffer = C.create_string_buffer(record)
        try:
            duplicate = H()
            process = self.k.GetCurrentProcess()
            with self._worker_lock:
                require(self.k.DuplicateHandle(process, self.k.GetCurrentThread(), process,
                                                C.byref(duplicate), 0, False, 2))
                self._worker_handle = duplicate.value
            if not self._cancel.is_set():
                written = W.DWORD()
                good = self.k.WriteFile(self.writer, buffer, len(record), C.byref(written), None)
                self._write_ok = bool(good and written.value == len(record) and not self._cancel.is_set())
        except Exception:
            self._write_ok = False  # never propagate native errors or record contents
        finally:
            C.memset(buffer, 0, C.sizeof(buffer))
            # The writer exclusively owns this handle once started; never close
            # it concurrently with a pending WriteFile from a different thread.
            try:
                self._close('writer')
                self._write_closed = True
            except Exception:
                self._write_ok = False
            self._done.set()

    def bootstrap_done(self):
        return self._done.is_set() and self._write_ok and self._write_closed

    def bootstrap_failed(self):
        return self._done.is_set() and not self.bootstrap_done()

    def alive(self):
        if not self.root or self._closing:
            return False
        result = self.k.WaitForSingleObject(self.root, 0)
        if result not in (0, 258):
            raise SessionError('Owned process wait failed')
        return result == 258

    def stop(self):
        """One nonblocking cleanup step; caller bounds retry count and elapsed time.

        One-process job makes active=0 plus retained root signal sufficient; no
        descendant PID census race. Failed query/close/cancellation quarantines.
        """
        self._closing = True
        self._cancel.set()
        good = True
        # Complete every independent cleanup step even if one fails.
        for name in ('reader', 'null', 'thread'):
            try:
                self._close(name)
            except Exception:
                good = False
        if self.root:
            try:
                signaled = self.k.WaitForSingleObject(self.root, 0)
                require(signaled in (0, 258))
                if signaled != 0:
                    if self.assigned:
                        require(self.k.TerminateJobObject(self.job, 0xdead))
                    else:
                        require(self.k.TerminateProcess(self.root, 0xdead))
                    good = False  # prove signal on a later step
            except Exception:
                good = False
        # Exact duplicated thread handle, no OpenThread(TID) reuse window. The
        # job is killed before cancellation, covering cancel-before-WriteFile.
        with self._worker_lock:
            if self._worker_handle and not self._done.is_set():
                self.k.CancelSynchronousIo(self._worker_handle)
                good = False
        if self._worker is not None and not self._done.is_set():
            return False
        # Thread may still be leaving its finally block after setting the event.
        if self._worker is not None and self._worker.is_alive():
            return False
        if self.job:
            try:
                info = Accounting()
                require(self.k.QueryInformationJobObject(self.job, 1, C.byref(info), C.sizeof(info), None))
                require(info.active == 0)
            except Exception:
                good = False
        if not good:
            return False
        for name in ('writer', '_worker_handle', 'root', 'job'):
            try:
                self._close(name)
            except Exception:
                return False
        return True
