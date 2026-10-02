MeasuredBodyAdapter03 — authoritative storage-cell relocation

Fixes the independent review's boundary corruption in frozen02. Caller From is
accepted within 1e-6 cm of stored Anchor; the two may occupy different200cm cells.
Relocate now derives its old cell from stored Anchor and validates exactly one
membership before any mutation. std::map insertion preserves the old bucket and
its vector iterator. Destination capacity/allocation precede removal; successful
removal prunes only an empty old bucket. No collision permission is broadened.

Actual MSVC:11040 checks,0 failures,2000 long-traversal moves. Added40 boundary
cases spanning X/Y,negative/zero/positive edges,both correction directions,and
same/cross-cell destinations. Each proves all63 remaining slots stay available,
cap64 unchanged,and motion/refusal state unchanged. Existing batch,callback,
capacity,identity,turn and measured-envelope cases remain.

This is an isolated source adapter, NOT installed in MikdashRuntime. It does not
prove current loaded-world support or collision. The WorldPort fixtures are
geometry doubles. Frozen02 remains unchanged; the old bug is not accepted.

verify.py checks this portable source closure and recorded execution pins without
launching. --local-receipt additionally validates the local owned-job receipt.
Run-SourceTests.ps1 is a machine-specific bounded owned MSVC runner; engine and
compiler prerequisites remain external, and no engine/vendor source is included.
inputs.json retains historical local provenance references, not bundled files.
