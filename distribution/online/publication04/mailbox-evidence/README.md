# Separate mailbox execution evidence

The coordinator supplied this reviewed standalone driver and independent MSVC
receipt: 12 cases, 64 checks, zero failures. The driver bytes are preserved;
the sanitized receipt retains only scope, counts, source hashes, driver hash,
exit status and the original receipt hash. Local paths, commands and binary/log
artifact entries are omitted. Receipt02 and the base publication manifest are
unchanged. This append adds no UE, IPC, process-host or gameplay acceptance.

For a later approved reproduction, use a separate build directory and MSVC C++17,
with `native` as the include directory. Do not put compiled outputs in this tree.
No compilation or driver execution is part of the append verifier.

Verify/copy with `python -I -B publication04/verify_append.py --expect-append HASH`
and optionally `--copy-to NEW_DIRECTORY`. The destination must not exist.
`--exact` checks the combined 90-file tree. The original verifier's `--exact`
continues to describe only the original 85-file base export. To replay its 97
offline checks in a combined tree, omit `--exact`; then run this verifier with
`--exact` again. The reviewed driver must never be counted as an executed check
merely because this hash verifier passes.
