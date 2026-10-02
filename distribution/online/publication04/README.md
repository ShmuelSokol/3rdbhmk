# Receiver04 source publication preparation

Coordinator owns copying into `distribution/online`, repository gates and commits.
This folder prepares source only. It does not install, build, serve or launch UE,
IPC, a Windows child, or the staged harmless-child fixture.

`allowlist.json` enumerates every file, byte size, SHA256 and purpose group:

- 29 exact files pinned by Process04 receipt02.
- Receipt02 and historical receipt01.
- All 26 Source02 and 15 Receiver03 files plus their receipts. These are required
  by the frozen validator's hash checks, even where not imported by these tests.
- Seven explicit oracle source/test/receipt dependencies.
- Three publication helper/doc/test files.

That is **81 payload/dependency files + 3 preparation files**, plus the manifest
itself. No wildcard export, node_modules, downloaded upstream implementation,
binaries, remote credentials, raw logs or native build output is included.
The harmless child is text source pinned by receipt02 and is never executed.
Prior source03 public HMAC vectors intentionally use public test material.

Use the manifest SHA256 reported with the preparation evidence, not an unverified
replacement manifest. Commands below assume a fresh PowerShell terminal:

```text
python -I -B publication04/verify.py --root . --expect-manifest <SHA256>
python -I -B publication04/verify.py --root . --expect-manifest <SHA256> --copy-to C:/Mikdash/NEW-standalone-directory
python -I -B C:/Mikdash/NEW-standalone-directory/publication04/verify.py --expect-manifest <SHA256> --exact --run-tests
```

The exporter refuses an existing or overlapping destination and copies ONLY the
explicit list. It never deletes or overwrites. `--exact` rejects extra files in
the standalone tree; omit it on the existing publication root when unrelated
historical source receipts are intentionally retained. Those extras are not
exported and are not approved by this allowlist. Place the root at
`distribution/online`, separate from bookweb; retain all existing Source02/03 bytes.

The standalone replay uses only Python stdlib and the copied files, with isolated
Python imports, bytecode disabled and fail-fast guards on common runtime I/O
entry points. All 97 offline checks must pass. The verifier checks hashes before
and after replay, the dependency closure, receipt02's exact anchor, and that local
imports did not escape into the active tree. Windows Python 3.8+ is required by
the frozen tests' Windows absolute-path fixtures. No installed UE, Node, npm,
external cache, project or publication clone is needed for this replay.

This is not a browser bundle rebuild, native compile or runtime acceptance. The
14 staged native tests remain unexecuted. Native compilation belongs only to the
coordinator's reserved slot. See the frozen Process04 CONTRACT for missing runtime
integration and the precise limited meaning of semantic acknowledgments.
