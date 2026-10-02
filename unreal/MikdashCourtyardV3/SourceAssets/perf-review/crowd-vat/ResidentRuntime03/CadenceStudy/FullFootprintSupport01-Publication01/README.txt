FullFootprintSupport01 -- isolated C++ static-patch support study

Scope
This study proves coverage only for the explicit rational patches supplied to it.
It does not load UE, a map, assets, cooked collision, or a physics scene. No loaded
world equivalence, obstacle clearance, actual cloth penetration, native acceptance,
or controller adoption is claimed. MeasuredBodyAdapter02/03 are not modified.

Measured input
MeasuredProfiles.h is a byte-identical copy from frozen MeasuredBodyAdapter02.
Its six profiles are the two actual Study13 variants at .92/1/1.08 scale, from
MeasuredResidentEnvelopes02/results.json, hash
141148270e83f5c0a9eb1854320e27f71e78a50657530090a65b302d967d8932.
The upstream measurement's UV2/Wrap and rendering assumptions remain premises;
this kernel does not improve or replace that evidence. Scale is already applied.
Radius and signed minZ/maxZ are copied exactly; minZ is never clamped to zero.

Coverage algorithm and conservative footprint
Coordinates are local centimetres, with exact rational input. The origin must be
chosen by a future bridge; there is no implicit float-to-rational conversion or
silent quantization of UE geometry. At each endpoint the measured horizontal
disc is enclosed by an axis-aligned square with half-width ceil(radius) cm.
The convex hull of both squares encloses every disc along the straight segment.
This is an explicitly conservative circumscribed footprint, not four sampled
body points, not a tight polygonal approximation of the circle, and not a fitted
synthetic body. Rounded half-widths are 55/59/64 cm at .92/1/1.08.
The existing 100 cm step bound is enforced. The caller's stricter playable step
cap remains upstream. In-place turning is covered because the measured radius
already bounds all yaw. Root height is an explicit affine plane over XY.

Patches are closed, strictly convex CCW triangles or quadrilaterals (rectangles
are the tested four-vertex input); each carries an affine height plane. The
Triangle factory derives that plane from actual rational XYZ vertices. Vertical
faces cannot be expressed as support height graphs and are refused by that
factory. A future bridge must retain them separately as obstacles, not drop them.
All patches are validated, including patches encountered after coverage closes.
Duplicate face identities are refused. A support-eligible patch must satisfy a
conservative L1 slope bound and height agreement with the requested root plane
over the ENTIRE footprint. This deliberately over-refuses some partial patches.
Defaults: maximum L1 slope .5; height agreement .01 cm. These are explicit study
policies, not a claim about existing UE character walkability settings.

Starting with the complete footprint, subtract each eligible convex patch by
half-plane clipping. Retain all uncovered convex fragments. Success requires no
two-dimensional residual fragment. No vertex sampling or area summation decides
coverage. Adjacent closed faces share their exact boundary. Degenerate residual
lines can be discarded: if a full-dimensional closed footprint has an uncovered
point outside a finite union of closed patches, it also has uncovered relative
interior with positive area. Predicates and intersections are exact rationals;
there is no epsilon that erases a narrow hole. Area() only tests non-collinearity.

Arithmetic/storage/work bounds
Every reduced rational numerator magnitude and denominator is <= 1,000,000,000.
Checked construction refuses larger reduced results; intermediate products/sums
of valid rationals fit signed int64 (maximum magnitude 2e18). Rational objects
must retain their constructor invariants; direct mutation of their public fields
is outside the trusted C++ API contract. ArithmeticRange means unknown/refused,
not covered. Default limits:128 patches,512 residual fragments,8192 live vertices
per fragment collection,200000 metered operations. Arithmetic bit width is fixed.
Old and new fragment collections coexist during subtraction, each within limits;
small working polygons and <=128 copied support patches are additional storage.
Bad allocation also refuses. Input vectors are caller-owned; allocation of those
inputs is outside this kernel. All non-success outcomes clear the support set.

Versioned WorldPort seam
Certificate schema1 carries request serial, world/geometry/binding versions,
profile, exact measured bounds, footprint, contact policy and a bounded face set.
Face keys include component, instance, shape, geometry revision and face index.
Zero-based face and instance IDs are valid. The bridge must define stable IDs and
collision-face remapping; do not equate render triangle IDs with Chaos hit IDs.
Certificates are trusted in-process values, not tamper-resistant wire objects.
The returned set includes all eligible supplied patches, not only minimal cover.
Capture a static scene epoch before extraction; revalidate all epochs and exact
mesh/shape transforms before committing the reservation. Any geometry change,
streaming/unload, binding change or unsupported shape must invalidate/refuse.
Adapter02's single support-face field cannot represent this set without a future
explicit bridge revision. Nothing here edits Adapter03's urgent reservation fix.

Contact is not obstacle clearance
SupportPointCandidate classifies only one exact surface point at a specified
fraction of the root segment. It requires matching epochs, full coverage, exact
face identity, membership in that face and instantaneous circumscribed footprint,
point height equal to the face plane, and height within .01 cm of that instant's
root. Signed measured minZ must also satisfy explicit contactBelowRoot (default
.5 cm). A stricter caller policy can refuse. No value is clamped or called actual
penetration. The allowance is policy, not a measured contact/penetration result.
This function is NOT permission to discard an overlap, manifold, entire face or
component. A future obstacle query must account for every other contact/surface;
risers on the same component and uphill surfaces above the root remain obstacles
or unknown. Coverage success can coexist with an obstacle. No obstacle-clear
certificate or component ignore list is provided in this study.

Execution and evidence
Run-SourceTests.ps1 is the previously reviewed Adapter02 standalone MSVC runner
with only study/test names changed. It pins the existing OwnedChildJob helper,
uses a fresh Verification folder, hidden owned Job, serial sentinel, 4 GiB owned
private cap, 2 GiB free-commit reserve, 60 s total/5 s cleanup. No UE/UBT command
exists in this runner. UE's 9 GiB start guard is unchanged and has not been used.
Run with a fresh -RunId. Existing run folders cannot be overwritten.
Compile01 passed188 checks; compile02 passed193 after tightening timed contact
classification and enforcing the100 cm segment bound. Both receipts stay local.
Current source result is source-test-result.json. Compiler logs/objects/executables
remain under Verification and are excluded from this source capsule.
verify.py checks capsule hashes, original input pins and source/result consistency;
--local-evidence additionally rechecks the local receipt/log hashes. It does not
compile or substitute for executing the C++ fixture. No Python geometry adapter.

Future UE work is separate
Compile an isolated bridge/API probe only under the existing9 GiB start guard and
owned cleanup policy. Cooked shape extraction, instance transforms, read locking,
terrain holes, collision trace flags and face maps need actual UE validation.
Unsupported geometry or inability to represent it exactly must refuse. A future
enclosure scheme for floating input must prove conservative direction separately.
The present static explicit-patch oracle is not a fabricated geometry certificate.

Portable publication derivative
The three C++ sources are byte-identical to independently tested FullFootprintSupport01.
The exact measured-results file is included. Machine-specific runner and raw logs
are not bundled; historical source/receipt hashes are provenance. verify.py checks
all pinned files, all six profile literals against measurements, and the two
actual MSVC execution receipts. It performs no compiler or engine launch.

To recompile in a configured MSVC developer shell, copy the three C++ sources to
a fresh build directory and run:
cl /nologo /std:c++17 /EHsc /W4 /O2 SupportCoverageTest.cpp
SupportCoverageTest.exe
Expected: checks=193 failures=0. Compiler/tools are external prerequisites.
The coordinator uses a bounded owned-job runner, kept outside this portable closure.
