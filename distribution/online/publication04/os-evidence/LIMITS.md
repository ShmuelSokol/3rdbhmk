# Additive harmless-child OS evidence

The coordinator executed frozen fixture revision03: exit 0 (coordinator report),
six cases passed in 0.926 seconds, zero unresolved owned leases, sentinel closed.
The sanitized receipt preserves the original result fields and adds provenance
and the SHA256 of the original local receipt. No executable, raw log, machine
path, environment or bootstrap data is exported. Preparation does not rerun it.

The five exact fixture files are four reviewed source files plus manifest03.
Their historical `staged-not-executed` wording is deliberately unchanged. This
separate receipt supplies later execution evidence; it does not rewrite the
reviewed source. Prior fixture manifests01/02 are historical references only and
are not required by the current verifier or included in this append.

Observed scope: synthetic framed stdin; exclusion of the tested inheritable
sentinel; actual blocked WriteFile cancellation with error995; frozen host write
deadline; assignment/write/close failure injection; exact owned cleanup and
unrelated control survival. Injected failures are not naturally occurring OS
failures. The 0.926-second run did not exercise the 40-second self-exit watchdog.
The watchdog remains source-reviewed, not execution-proven by this receipt.
The sentinel test is not an exhaustive enumeration of every possible handle.
This is one installed CPython/Windows run, not general Windows compatibility.

No UE, UBT, native game, socket/listener, authenticated IPC, video, browser,
native gameplay consumption, admission or online delivery is proven. Source02,
Receiver03, receipt02's 29 files and its 97-check validation remain unchanged.
The standalone mailbox execution remains a separate append with its own limits.

`append-os-01.json` adds nine explicit files: fixture five, sanitized receipt,
this limits file, export verifier and four regression tests in one file. With
its own manifest, it adds ten files to the base+mailbox 90-file export: **100**.
All files are UTF-8 source/evidence; there are no wildcard exports or overwrites.
The existing base and mailbox manifests/verifiers are untouched.

After checking the externally supplied OS append SHA256, use:

```text
python -I -B publication04/verify_os_append.py --expect-os-append HASH --copy-to NEW_DIRECTORY
python -I -B NEW_DIRECTORY/publication04/verify_os_append.py --expect-os-append HASH --exact
python -I -B NEW_DIRECTORY/publication04/verify.py --expect-manifest a1d32b7bc5616f42b6a6566f296ca6fc408cff1bca0f58d3fa060f53a1d0b594 --run-tests
python -I -B NEW_DIRECTORY/publication04/test_os_append.py -q
python -I -B NEW_DIRECTORY/publication04/verify_os_append.py --expect-os-append HASH --exact
```

The fresh destination must not exist. The base/mailbox verifier's `--exact`
describes its older smaller export; use this new verifier for combined exactness.
Regression tests create and remove only isolated temporary source copies; they
never import or run the fixture. Existing `test_verify.py` can also run offline.
No command above compiles code or launches the OS fixture. Any later fixture
execution remains a separately approved coordinator action, not an export step.
