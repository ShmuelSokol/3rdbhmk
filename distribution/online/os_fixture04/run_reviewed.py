"""STAGED, NOT EXECUTED. Explicit coordinator-only Windows OS fixture.

Uses frozen WindowsChild and OwnedProcesses. No game, socket, credentials,
shell, process discovery or PID-based termination. See README before approval.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.process04.win32_child import WindowsChild, Security, kernel_api
from adapters.process04.host import OwnedProcesses, LaunchRecipe
from session_core import Ownership, SessionError

FRAME = (64).to_bytes(4, 'big') + b'S' * 64
BASE = 'a1d32b7bc5616f42b6a6566f296ca6fc408cff1bca0f58d3fa060f53a1d0b594'


def require(ok):
    if not ok:
        raise AssertionError('Fixture assertion failed')


def until(predicate, seconds=3):
    deadline = time.perf_counter() + seconds
    for _ in range(1001):
        if time.perf_counter() >= deadline:
            return False
        if predicate():
            return True
        time.sleep(.005)
    return False


def configure(k):
    specs = {
        'CreateEventW': (W.HANDLE, [C.POINTER(Security), W.BOOL, W.BOOL, W.LPCWSTR]),
        'GetExitCodeProcess': (W.BOOL, [W.HANDLE, C.POINTER(W.DWORD)]),
        'GetNamedPipeInfo': (W.BOOL, [W.HANDLE, C.POINTER(W.DWORD), C.POINTER(W.DWORD), C.POINTER(W.DWORD), C.POINTER(W.DWORD)]),
    }
    for name, (result, args) in specs.items():
        f = getattr(k, name)
        f.restype, f.argtypes = result, args


class Probe:
    """Pass-through real API; explicitly labelled fault injection where selected.

    fill: on the OWNED writer thread, first fill exactly the OS-reported pipe
    capacity with synthetic bytes. Then issue the backend's original WriteFile.
    This forces a real blocked synchronous write even on a 4 KiB pipe; simply
    launching a non-reader would not prove it. No pre-spawn/host-thread write.
    """
    def __init__(self, k, mode='normal'):
        self.k, self.mode = k, mode
        self.entered = threading.Event()
        self.returned = threading.Event()
        self.error = None
        self.entered_at = self.returned_at = None
        self.assigned_job = None
        self.cancel_calls = 0
        self.job_kills, self.root_kills = [], []
        self.close_failure = None

    def __getattr__(self, name):
        return getattr(self.k, name)

    def AssignProcessToJobObject(self, job, root):
        if self.mode == 'assign-fail':
            return 0
        result = self.k.AssignProcessToJobObject(job, root)
        if result:
            self.assigned_job = job
        return result

    def CloseHandle(self, handle):
        if handle == self.close_failure:
            self.close_failure = None
            return 0
        return self.k.CloseHandle(handle)

    def TerminateJobObject(self, job, code):
        self.job_kills.append(job)
        return self.k.TerminateJobObject(job, code)

    def TerminateProcess(self, root, code):
        self.root_kills.append(root)
        return self.k.TerminateProcess(root, code)

    def CancelSynchronousIo(self, handle):
        self.cancel_calls += 1
        return self.k.CancelSynchronousIo(handle)

    def WriteFile(self, handle, buffer, size, written, overlap):
        if self.mode == 'write-fail':
            return 0
        if self.mode == 'fill':
            capacity = W.DWORD()
            require(self.k.GetNamedPipeInfo(handle, None, C.byref(capacity), None, None))
            require(0 < capacity.value <= 65536)
            pad = C.create_string_buffer(b'P' * capacity.value)
            filled = W.DWORD()
            require(self.k.WriteFile(handle, pad, capacity.value, C.byref(filled), None))
            require(filled.value == capacity.value)
        self.entered_at = time.perf_counter()
        self.entered.set()
        result = self.k.WriteFile(handle, buffer, size, written, overlap)
        self.error = 0 if result else C.get_last_error()
        self.returned_at = time.perf_counter()
        self.returned.set()
        return result


class NoChannel:
    """No IPC. Startup failure must never reach a signaling/admission channel."""
    def __init__(self, *args, **kwargs):
        pass


def forbidden(*args, **kwargs):
    raise AssertionError('Network/IPC forbidden in fixture')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coordinator-approved-os-fixture', action='store_true', required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--python-sha256', required=True)
    parser.add_argument('--system-root', type=Path, required=True)
    parser.add_argument('--temporary', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--expect-fixture', required=True)
    args = parser.parse_args()
    require(os.name == 'nt' and C.sizeof(C.c_void_p) == 8)
    executable = args.python.resolve(strict=True)
    require(executable.name.lower() == 'python.exe')
    # Coordinator supplies an existing trusted, installed CPython, not a shim.
    require(executable.stat().st_size <= 32 * 1024**2)
    require(hashlib.sha256(executable.read_bytes()).hexdigest() == args.python_sha256)
    require(not args.receipt.exists())
    receipt_path = args.receipt.resolve()
    require(ROOT not in receipt_path.parents and receipt_path.parent.is_dir())
    sys.path.insert(0, str(ROOT / 'os_fixture04'))
    from verify_source import verify as verify_fixture
    fixture_hash = verify_fixture(args.expect_fixture)
    sys.path.insert(0, str(ROOT / 'publication04'))
    from verify import verify_tree
    verify_tree(ROOT, BASE)
    k = kernel_api()
    configure(k)
    children, results = [], []
    started = time.perf_counter()
    env = dict(SystemRoot=str(args.system_root.resolve(strict=True)),
               WINDIR=str(args.system_root.resolve(strict=True)),
               TEMP=str(args.temporary.resolve(strict=True)), TMP=str(args.temporary.resolve(strict=True)))
    sa = Security(C.sizeof(Security), None, True)
    sentinel = k.CreateEventW(C.byref(sa), True, False, None)
    require(sentinel)

    def guard_acquisition():
        require(time.perf_counter() - started < 25)

    def new(mode, probe=None):
        guard_acquisition()
        child = WindowsChild(probe or k)
        children.append(child)  # retain BEFORE any acquisition
        child.create(str(executable), ('-I', '-B', str(ROOT / 'os_fixture04/child.py'), mode, str(sentinel)),
                     str(ROOT), env, 512 * 1024**2)
        return child

    def cleanup(child):
        require(until(child.stop, 3))
        require(child.stop())
        require(all(getattr(child, n) is None for n in
                    ('job', 'root', 'thread', 'reader', 'writer', 'null', '_worker_handle')))
        require(child._worker is None or not child._worker.is_alive())

    control = None
    failed = False
    try:
        # Even accidental use of the host's default readiness probe is refused.
        with patch('socket.socket', forbidden), patch('adapters.process04.host.make_record', lambda *a, **kw: FRAME):
            control = new('hold')
            control.resume_and_write(FRAME)
            require(until(control.bootstrap_done))
            require(control.alive())

            child = new('read')
            child.resume_and_write(FRAME)
            require(until(lambda: k.WaitForSingleObject(child.root, 0) == 0))
            code = W.DWORD()
            require(k.GetExitCodeProcess(child.root, C.byref(code)) and code.value == 0)
            require(until(child.bootstrap_done))
            cleanup(child)
            require(control.alive())
            results.append('synthetic-read-and-inherited-handle-exclusion')

            probe = Probe(k, 'fill')
            child = new('ignore', probe)
            child.resume_and_write(FRAME)
            require(until(probe.entered.is_set))
            time.sleep(.1)
            require(not probe.returned.is_set() and not child._done.is_set())
            require(probe.CancelSynchronousIo(child._worker_handle))
            require(until(child._done.is_set))
            # Direct cancellation proof: ERROR_OPERATION_ABORTED, not merely
            # broken-pipe completion after killing the read end.
            require(probe.error == 995 and child.bootstrap_failed())
            job = child.job
            cleanup(child)
            require(probe.job_kills and set(probe.job_kills) == {job} and not probe.root_kills)
            require(control.alive())
            results.append('real-blocked-write-cancelled-995-owned-job-cleaned')

            guard_acquisition()
            probe = Probe(k, 'fill')
            child = WindowsChild(probe)
            children.append(child)
            recipe = LaunchRecipe(str(executable), args.python_sha256, str(ROOT),
                ('-I', '-B', str(ROOT / 'os_fixture04/child.py'), 'ignore', str(sentinel)),
                env['SystemRoot'], env['TEMP'], 512 * 1024**2)
            revoked = []
            host = OwnedProcesses(recipe, (49151,), revoked.append, clock=time.perf_counter,
                child_factory=lambda: child, channel_factory=NoChannel, hint=forbidden,
                key_factory=lambda: b'\0' * 32, qpc=time.perf_counter,
                write_seconds=.5, start_seconds=2, cleanup_seconds=1)
            # 49151 is inert allocator data: no bind/connect/reservation occurs.
            host.prepare()
            owner = Ownership('fixture-s', 'fixture-p', 'fixture-v', 'fixture-save', 'fixture-settings', time.perf_counter()+5)
            begin = time.perf_counter()
            guard_acquisition()
            try:
                host.start(owner)
                raise AssertionError('Blocked bootstrap was admitted')
            except SessionError:
                pass
            elapsed = time.perf_counter() - begin
            require(probe.entered.is_set() and elapsed >= .5 and elapsed < 3)
            require(probe.returned_at is not None and probe.returned_at - probe.entered_at >= .4)
            require(probe.error in (995, 109, 232))
            require(probe.job_kills and set(probe.job_kills) == {probe.assigned_job} and not probe.root_kills)
            host.stop(owner)
            require(not host.records and revoked == [owner])
            cleanup(child)
            require(control.alive())
            results.append('frozen-host-write-deadline-and-stalled-job-cleanup')

            probe = Probe(k, 'assign-fail')
            try:
                new('ignore', probe)
                raise AssertionError('Injected assignment failure ignored')
            except SessionError:
                pass
            child = children[-1]
            root = child.root
            require(root and not child.assigned)
            cleanup(child)
            require(probe.root_kills and set(probe.root_kills) == {root} and not probe.job_kills)
            require(control.alive())
            results.append('injected-assignment-failure-suspended-root-cleanup')

            probe = Probe(k, 'write-fail')
            child = new('ignore', probe)
            child.resume_and_write(FRAME)
            require(until(child.bootstrap_failed))
            cleanup(child)
            require(control.alive())
            results.append('injected-write-failure-job-cleanup')

            probe = Probe(k)
            child = new('read', probe)
            child.resume_and_write(FRAME)
            require(until(lambda: k.WaitForSingleObject(child.root, 0) == 0))
            require(until(child.bootstrap_done))
            require(until(lambda: not child._worker.is_alive()))
            root = child.root
            probe.close_failure = root
            require(child.stop() is False and child.root == root)
            cleanup(child)
            require(control.alive())
            results.append('injected-close-failure-retains-handle-retry-proof')
    except Exception:
        failed = True  # no exception text, argv, environment or raw OS logs
    finally:
        unresolved = 0
        for child in reversed(children):
            try:
                cleanup(child)
            except Exception:
                unresolved += 1
        sentinel_closed = bool(k.CloseHandle(sentinel))
    verify_tree(ROOT, BASE)
    verify_fixture(args.expect_fixture)
    report = dict(status='passed' if not failed and not unresolved and sentinel_closed else 'failed',
        scope='Harmless CPython WindowsChild OS fixture only; no UE/IPC/media/admission proof',
        cases=results, completedCases=len(results), expectedCases=6,
        unresolvedOwnedLeases=unresolved, sentinelClosed=sentinel_closed,
        nativeGameLaunches=0, socketOperations=0, productionCredentials=0,
        pythonSha256=args.python_sha256, baseManifestSha256=BASE, fixtureManifestSha256=fixture_hash,
        seconds=round(time.perf_counter()-started, 3))
    with args.receipt.open('x', encoding='utf-8') as out:
        json.dump(report, out, indent=2)
        out.write('\n')
    print(json.dumps(report))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    try:
        status = main()
    except Exception:
        print('{"status":"failed","reason":"fixture-setup-or-verification-failed"}')
        status = 1
    raise SystemExit(status)
