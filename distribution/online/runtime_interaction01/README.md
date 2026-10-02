# Portable interaction01 review closure

This is a portable derivative of the frozen interaction01 review snapshot, not an
applied production change. The original manifest and provenance are recorded in
../interaction_publication01/publication-context.json. Original authoring files
remain unchanged. Only path-bound metadata/tooling and this README were adapted;
production candidate code, baseline snapshots, C++ tests and patch overlay are exact.

The project API preserves Blueprint void TalkToNearbyResident and adds native
TryTalkToNearbyResident with Applied / NoOp / Rejected / Unknown outcomes. It scans
first, executes the actual remote fence at the last branch before PressTalk, then
checks ownership, pause and possession after callbacks. The real conversation bool
determines consumption, including one-line advance and wrapping. Changed context
after consumption is Unknown, never a false rejection or automatic replay.
Post-callback validation does not refresh the pre-consumption authorization time;
the frozen mailbox suppresses ACKs after expiry.

review-overlay/project maps to the project's
Plugins/MikdashRuntime/Source/MikdashRuntime directory. review-overlay/online maps
to distribution/online (or the active OnlineWalkthrough source root). These are
review overlays, not complete standalone UE projects. Do not apply automatically.
The patched receiver routes interact through the explicit adapter instead of the
legacy injected interaction callback; that parameter remains for source compatibility.

Run `python -I -B test_source_patch.py` from any working directory using its path.
prepare_patch.py verifies the supplied exact snapshots and produces the same patch
without looking up the authoring machine's project paths. Optional --export writes
only a NEW direct child of this candidate directory. Before eventual live application,
compare the target files to the pinned baselines; this portable tool does not perform
an implicit live-project check or apply patches to production.

Ten actual-header C++ cases passed with MSVC, 28 checks; see ../runtime_interaction01_evidence01.
The copied C++ source's STAGED comment and prior-source-receipt.json describe the
original snapshot before subsequent execution. They are preserved as prior evidence.
No fake UE classes were used. The real UE controller adapter remains uncompiled.

Pure test compile recipe: use the unchanged tests/ResidentTalkActionTests.cpp with
the snapshots/project/Public include directory, C++17, /EHsc /W4. Frozen mailbox has
an unused Before parameter warning; /WX rejects it. Use an independently authorized
bounded owned Job and fresh output directory, not this source tree. No UE, listener,
media or production configuration activation is included in this publication.

Existing scan maintenance can update holds/observations before remote consumption;
this patch does not claim to roll back background maintenance on rejection.
