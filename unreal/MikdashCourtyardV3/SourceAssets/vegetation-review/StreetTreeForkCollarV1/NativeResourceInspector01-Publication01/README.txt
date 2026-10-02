NativeResourceInspector01-Publication01: portable author-source review closure

Six generic Editor plugin files are byte-identical to frozen inspector01.
source-accounting.json accounts for all14 original payload files: six included,
eight omitted with explicit reasons. This is a scoped source closure, not the
complete local evidence bundle. No engine source, installed source paths, tree
textures, binaries, raw logs or unrelated predecessor dependencies are included.

Standalone test (Windows, Python3.9+, Visual Studio C++ x64 Build Tools):
  python verify_publication.py
  python run_decision.py --output <fresh-directory-outside-this-source-tree>
The output directory must not already exist. The runner discovers vswhere/MSVC,
compiles the unchanged decision header through tests/decision_test.cpp using
/std:c++17 /EHsc /W4, and records version, command, includes, exits and output in
the external directory. It does not fetch dependencies. Discovery timeout10s,
compile60s, executable10s; timeout cleanup targets only that owned invocation
tree, with5s taskkill and5s root-wait bounds. These are sequential phase bounds,
not a single70s total budget. Cleanup failure remains failure; no UE supervision
capability is claimed for this small standalone runner.

The compiled test has18 focused cases,16384 exhaustive readiness assignments
and4 quality cases with hand-written expectations, not parsed/evaluated source.
The one include-line portability change and both hashes are recorded in
test-provenance.json and decision-test-portability.patch. No fake UE types.

UNCOMPILED UE ADAPTER: compiling this portable decision test does not compile the
Editor module, run UHT, link Engine exports, verify reflection/Python names, or
inspect a live shader resource. All those native adapter checks remain pending.
The plugin is disabled by default and has no content. A future separately
admitted isolated Editor project must compile/load it; no project is supplied.
The Run23 Python bridge is explicitly omitted as a local dependent proposal.
The generic reflected method accepts any existing live UMaterial in-process:
NativeMaterialResourceInspectionLibrary::InspectExistingMaterial(Material,
 TargetPlatform, TargetQuality, bAllowSharedQualityResource, bSupervisorAdmitted).

Required method behavior: game-thread guard, strong material retain, explicit
SM5/SM6 and quality selection, wait for existing compilation, reacquire resource,
compare pointer and StateId, report final errors/platform/quality/finished/map
present/valid/complete. Shared-quality fallback requires explicit caller opt-in.
No automatic graph recompile, save or load-by-path. FinishCompilation can finish
pending cache callbacks and block. External admitted ownership/deadline supervisor
and unchanged9GiB native admission guard remain mandatory for any future UE
build/run/wait. The admission boolean is only a misuse fuse, not a resource check,
permission grant or cancellation mechanism. This closure provides no UE runner.

READY means requested GAME-THREAD RESOURCE ONLY. It does not prove active render-
thread selection, absence of fallback, binding, appearance, mip safety, GPU cost,
shipping/adoption eligibility or saved asset validity. Originals remain frozen.
No installed public API/export blocker was identified in local source review;
actual UHT/link/live behavior remain unverified. No production changes authorized.

manifest.json is the exact publication allowlist/hash index; include it plus all
listed files. verify_publication.py refuses extras and scans for absolute machine
paths and non-source payloads. Fresh unpack/replay receipts are local verification
evidence outside this publication closure, intentionally not distributed logs.
