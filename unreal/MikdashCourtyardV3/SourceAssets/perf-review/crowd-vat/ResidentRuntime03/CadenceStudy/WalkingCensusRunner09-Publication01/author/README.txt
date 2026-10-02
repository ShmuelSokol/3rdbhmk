WalkingCensusRunner09 -- additive source candidate, 2 October 2026

REVIEW ONLY. UE/UBT/editor has NOT run.08 remains frozen (manifest
3f4b9a8cf1090f7aff0e0e089ab74353ec40fd5039c21bbccc501af4523954da).
The independent08 source compile blocker is corrected ONLY in09:
WalkingQuery.cpp includes Physics/Experimental/PhysScene_Chaos.h, providing
the FPhysScene_Chaos : FChaosScene inheritance required by the filter builder.
This was found by source review, not by an observed native compiler failure.
include-fix.patch records the exact one-line change; changes-from08.json records
all inherited-file changes/additions. Collector, strict ABI/library, arithmetic,
measured profiles and12 prepared filter assertions are unchanged.

Bounded implementation
----------------------
runner.py stages an exact fresh external source closure plus explicit asset and
MikdashRuntime source allowlists. inputs.json records the exact isolated48-person
RuntimeReview.umap, two Study13 mesh/material/texture families, Study12 default
texture dependencies, native authoring receipts and current plugin sources.
It rejects sidecars not listed, missing/changed inputs, extra staged payload,
reparse ancestors, path escapes and overwrites. Source packages are streamed into
separate files, never hardlinked. Active project input hashes are checked before
and after; this is change detection, NOT filesystem snapshot isolation.
No active-project Content/Config/Saved/DDC is used as a write destination.

Run-Reviewed.ps1 has one policy for Build and Census:9GiB entry,4GiB owned Job,
2GiB reserve,180s owned-execution deadline including a reserved cleanup window.
Preparation and post-exit offline hash/result validation are outside that native
execution clock and cannot launch UE. Disk staging requires payload plus2GiB;
each fresh run requires4GiB available. No archive deletion or guard adjustment.
The existing reviewed suspended owned-Job helper is unchanged. Durable shared
sentinel precedes its constructor; constructor uncertainty retains the sentinel.
Only the owned tree is stopped. Natural root0 AND Job0 are required for success,
with terminal poll/count/drain evidence. StopWithinFiveSeconds verifies retained
owned handles plus Job0. Cleanup uncertainty retains the shared blocked marker.
Busy-name scanning is supplemental; the coordinator must serialize all native
writers with the same slot protocol. Never kill a foreign process or Zen server.

Build copies the exact source/assets/plugin into its fresh external project and
uses serial UBT -MaxParallelActions=1 with the pinned strict library. Census cannot
build: it requires a seal of a successful cleanup-confirmed Build receipt and the
two exact compiled module DLL/module-descriptor pairs. Seal checks their engine
BuildId. It copies these into another fresh project, verifies hashes, and launches
the fixed map only. No arbitrary map, executable or project argument is accepted.
Hidden ProcessStartInfo launches occur only inside the already-owned shim Job.
UserDir, DDC and logs are run-local. Both existing Game INI save/settings overrides
use the recorded fresh WalkingCensus09_<nonce> prefix; no user save slot is reused.

Native driver -- new, uncompiled
-------------------------------
CensusDriver.cpp calls the ACTUAL InspectWalkingBox and DescribeWalkingCapture.
It requires exactly one48-person, two-pose Study13 crowd,24 instances each, source
scale1, identity actor/component frame, no VAT body collision, exact pose/material
slots and texture bindings. It scans at most48 agents for an idle zero-velocity,
zero-rate agent, reads the interleaved instance, and checks the stored float32
anchor against the CPU anchor. The request origin is the actual read-back rendered
anchor. A unit-scale yaw-only instance is required; other matrix representations
refuse. Compatibility of this strict check with actual UE instance decomposition
is UNTESTED. It may refuse all candidates; do not relax it to claim a body proof.
The whole-clip radial/vertical measured profile retains its signed negative minZ;
root plane is local z0 at the instance anchor, not a fabricated penetration test.
Only one stationary selected-box capture is attempted. This is not motion approval.

The stack-local owner publisher resolves the same live agent during synchronous
capture. Its invocation-local generation is NOT a persistent production generation
or universal writer fence. No IFence implementation/default-true fence is supplied.
Loaded /Game packages must be in the exact allowlist; engine packages/modules come
from installed UE. Receipt-derived package dependency closure is NOT a proven
complete linker/dependency census. Missing dependencies can still make native load
fail; logs and failed receipt must be kept. This is deliberately an isolated map,
not the production S5 map or a current main-map cooked-shape census. Its Engine
Plane may refuse as a primitive; the runner must record that actual refusal.

The measured Study13 UV2/source correspondence remains conditional. No GPU-render
equivalence, real publisher fence, future dynamics or solid containment is proved.
Output always says worldReady=false and measuredCorrespondenceConditional=true.
An actual native observation can be validated even with a geometric Budget/Shape
refusal; it never becomes complete-world evidence. Partial capture cannot claim
exhaustion or an available geometry copy. Preincrement counter sentinels are accepted
only for Budget refusal: payload65, node2049, bounds/source-face4097. Actual collector
budgets remain64/2048/4096/4096.65 with any non-Budget status is rejected.

Review / future execution entrypoints
------------------------------------
1. Read manifest.json, inputs.json, include-fix.patch, changes-from08.json,
   Run-Reviewed.ps1, runner.py, support.ps1 and new CensusDriver.cpp.
   Run python -B verify.py; this runs only offline validators/policy/parser tests.
2. python -B runner.py stage --name <fresh-name>
   creates C:/Mikdash/Verification/WalkingCensusRunner09-review-<fresh-name>.
   Verify there with python -B verify.py. Review the exact manifest hash externally.
3. ONLY after coordinator authorization, independent review and9GiB entry:
   pwsh -NoProfile -File Run-Reviewed.ps1 -Mode Build -RunId <fresh-build>
       -ExpectedManifest <reviewed SHA256>
   Inspect actual compiler/linker result. python -B runner.py seal --name <fresh-build>
   creates an exclusive build-seal.json only from a successful preserved build.
4. Independently review compiled build receipt/seal before coordinator authorizes:
   pwsh -NoProfile -File Run-Reviewed.ps1 -Mode Census -RunId <fresh-census>
       -BuildRun <fresh-build> -ExpectedBuildSeal <reviewed seal SHA256>
       -ExpectedManifest <same SHA256>
   One attempt only; preserve failures. No auto retry. Validate native.json AND
   receipt.json terminal root/Job0, source preservation and cleanup. Offline checker
   writes validated-result.json, including the actual native-result hash.

No native command above has been executed. Offline test receipts are not live IPC,
cooked geometry or UE compile evidence. Logs, DLLs, assets and fresh run directories
are excluded from the source manifest/publication. Publish source and sanitized
review evidence only through coordinator review.08 and all failed predecessors stay
unchanged. Current world/adoption readiness remains HOLD.
