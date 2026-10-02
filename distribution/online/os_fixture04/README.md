# Staged harmless-child OS fixture — NOT RUN

Coordinator review and explicit execution approval are still required. This new
folder does not alter Source02, Receiver03, Receiver04 receipt02 or its 97-check
freeze. It is separate from the publication04 source/mailbox allowlists.

`run_reviewed.py` exercises the exact frozen `adapters/process04/win32_child.py`
using a trusted installed 64-bit Windows CPython `python.exe`. No UE, bootstrap
download, compiler, socket/listener, named IPC, hosting or project config is used.
Each child is suspended, assigned to its own one-process kill-on-close job, then
resumed by the frozen backend. Output goes to NUL; environment is four explicit
Windows/temp paths; command lines contain only source paths, modes and a public
sentinel handle number. Bootstrap is a public 64-byte `S` body, never a credential.

Six proposed OS cases:

1. Child reads the synthetic framed stdin, reports success by exit code, and
   rejects inheritance of an extra deliberately inheritable parent event. A
   numeric handle collision fails the test rather than claiming isolation.
2. An API probe fills the actual anonymous pipe to its OS-reported capacity on
   the backend's owned writer thread. The original frame then blocks in real
   WriteFile. Direct CancelSynchronousIo must complete it with error 995 before
   job termination. This distinguishes cancellation from broken-pipe completion.
3. The frozen OwnedProcesses.start loop enforces its 0.5-second write deadline
   against another filled pipe, revokes the exact owner and cleans its job.
   `make_record` is explicitly replaced with synthetic bytes; key factory uses
   public zero bytes; channel constructor has no I/O; readiness/socket creation
   raises immediately. The inert allocator port number is never opened. This
   checks the real host deadline loop, not authentication or clock calibration.
4. Injected assignment failure leaves the child suspended; cleanup must terminate
   only the retained exact root. This is an injected failure, not proof of an OS
   naturally refusing assignment.
5. Injected WriteFile failure must yield failed bootstrap and exact job cleanup.
6. Injected CloseHandle failure must retain the root identity, return false, then
   close successfully on retry. Completed cleanup is idempotent.

An unrelated control child owns a separate job and must remain alive after every
case. All acquired subjects are retained before create and cleaned in finally,
including the control. Each cleanup allows three seconds / at most 1001 polls;
parent polling loops have elapsed and iteration bounds. Before any stdin read,
the child starts one independent daemon watchdog. After 40 seconds the watchdog
calls `os._exit(26)` on its own child process, including when the main thread is
blocked reading stdin. It has no parent, job or other process termination API.
Ordinary child exit ends the daemon automatically. This secondary bound starts
when the child's main function runs; interpreter startup/suspended creation still
depends on parent/job cleanup. As with every timeout, OS scheduling must progress.
There are at most seven subject children plus the
control, never more than control + one live test child during successful runs.
Both direct backend creation and the frozen host-start case use the same
`guard_acquisition()` check and refuse to start after 25 seconds.
These are application bounds, not
hard real-time guarantees for kernel calls or a frozen OS. Pending cleanup causes
a failed receipt with unresolved lease count, never a false cleanup claim. Job
kill-on-close also applies at harness exit; it is not counted as observed cleanup.

The fill probe is intentionally test instrumentation: it adds one synthetic
WriteFile before forwarding the backend's exact original WriteFile. Pipe capacity
must be 1..65536 bytes; unsupported behavior fails closed. A non-reading child
alone cannot prove a <=4096-byte bootstrap write blocks. Production source and
pipe creation are unchanged. Other probes delegate real API calls except the
explicit failure being tested. No claim of production authentication, UE startup,
stream routing, video, native input consumption, or online delivery follows.

The writer's entered event precedes WriteFile. The 0.1-second pause cannot prove
the thread entered the kernel call. CancelSynchronousIo ERROR_NOT_FOUND therefore
remains a failed test followed by cleanup; only actual error 995 satisfies the
direct cancellation case. Do not weaken that assertion to tolerate a scheduling
race. Revision03 adds the independent child watchdog and a shared acquisition
guard. `allowlist-01.json` and `allowlist-02.json` are retained as prior evidence;
`allowlist-03.json` pins the current four files and is used by the source verifier.
No OS execution evidence exists for this revision; watchdog and cleanup behavior
remain for coordinator execution after independent review.

## Coordinator-only execution recipe (not run during preparation)

First review the four listed files, the pinned backend, and verify all hashes.
Choose an existing trusted CPython installation, its independently checked binary
SHA256, an existing temporary directory, and a NEW receipt filename outside the
source/export tree. Do not use a launcher shim, venv redirector or downloaded code.
From a fresh terminal after approval:

```text
python -I -B os_fixture04/verify_source.py --expect-fixture FIXTURE_MANIFEST_SHA256
python -I -B os_fixture04/run_reviewed.py --coordinator-approved-os-fixture --expect-fixture FIXTURE_MANIFEST_SHA256 --python C:/trusted/python.exe --python-sha256 REVIEWED_BINARY_SHA256 --system-root C:/Windows --temporary C:/existing/test-temp --receipt C:/new-receipt.json
```

The explicit switch records intent; it is not an authorization/security boundary.
The second command starts OS processes and MUST NOT be run by the preparing agent.
It emits only fixed case names, status/counts, hashes and elapsed time. Exceptions
are not dumped. No raw logs, executable or receipts containing bootstrap values
are written. A receipt is created exclusively and never overwrites prior evidence.
Unsupported job policy/CPython/pipe behavior is a failed fixture, not a workaround
that relaxes ownership. The source-only verifier parses Python ASTs and hashes
text; its success is not an OS test pass. Coordinator may append an actual later
receipt separately after review. Do not merge this fixture into the current
publication allowlist without a separate review.
