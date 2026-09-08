# Bounded48cm dependency preparation

`release_amah48_dependencies.py` generates an explicit plan from the historical native-scale inventory, not a substring-driven automatic rescale. It identifies seven fitted veneer panels plus211 exact receipt-matched frieze panels;23 door/curtain and vessel actors still require reconciliation. New or replaced actors after that inventory are unknown; this is not exhaustive current coverage.

The original seven exact `SanctuaryFinishesV1/SM_InteriorVeneerCube` actors have a native apply path, now extended to211 frieze panels. They use local cube geometry with world placement and nonuniform scale. Their wall-fitted in-plane dimensions and centres multiply by .96. Their thin local axis remains scale.002 (physical.2cm veneer thickness), avoiding needless shrinking of a visual surface treatment. Locations1925 are925floor+1000wall half-height; uniform location conversion appropriately gives1848. This is a fitted wall dimension, unlike a person's eye/capsule offset.

Doors are local leaf meshes with articulated placement, not world-baked architecture. Door base927 comprises floor925 plus2cm clearance; preserving that clearance gives890cm, not889.92. Curtain base928 gives891 after floor migration with3cm retained clearance; its art is on user HOLD and never changed here. Hinge8/16cm fabrication offsets, hardware and curtain opening overlaps require explicit policy before dimension/pose changes. KeilimTIV1 book dimensions have a .96 basis, but later versions, physical details and baked food proportions require identity/spec reconciliation. Frieze module spacing follows walls;1.6cm standoff and relief depth must be handled separately. The remaining23 rows are reported, never applied.

Source architecture stairs are world-baked and already included in the successful architecture48 candidate; scaling them again is forbidden. Modern Kotel access stair geometry/people/context remain metric. Candidate joins still need grounded native review.

Offline invocation: engine Python `Scripts/release_amah48_dependencies.py` emits JSON. Checks passed: AST, 218 exact fitted proposals,23 explicitly deferred actors, exactly one physical thickness axis retained per panel.

Root-only native invocation, candidate already loaded without dirty packages or PIE:

```python
import release_amah48_dependencies
report=release_amah48_dependencies.run(
    candidate_receipt=r'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\scale-review\amah48-candidate-20260908T144034771385Z.json',
    apply=True)
```

Requires a successful candidate receipt and exact original veneer mesh/pose/attachment state. Refuses main and noncandidate namespaces, repeated application and external actor/object layouts. Checkpoints candidate before mutation, marks actors modified, compares all unrelated actors and full saved/reopened scene. Main/config/original architecture/protected maps plus veneer mesh/material hashes remain unchanged. No promotion method exists. This worker performed no Unreal/UBT execution; native API, actual veneer alignment and complete48cm acceptance remain pending.


## Source-resolved frieze extension and door fabrication

Native apply now covers218 panels atomically (7 veneers+211 friezes). Each frieze exact label, mesh and pose matches the successful V2 import receipt, including its named wall. Generator plan_wall() places localY back plane at veneer room face plus1.5cm standoff; veneer half-thickness is0.1cm. Preserve this1.6cm total offset from the wall centre while migrating that centre by.96. Scale localX andZ by.96; keep localY thickness/displacement unchanged. Full module250 becomes240cm; fitted row/column positions track the wall. No blanket depth scaling. Existing seven-only application would fail the original-pose guard; use a fresh original architecture candidate or a separately reviewed resume, never double-apply.

Door source inspection resolves actual target dimensions: Kodesh opening350x300 becomes336x288; quarter nominal87.5 becomes84; solid leaf nominal-minus1 becomes83cm wide, height-minus4 becomes284cm, bottom925+2 becomes888+2=890. Preserve7cm slab thickness,2cm barrel radius,12cm barrel length,8cm barrel offset and1cm jamb gap. Folded child translation becomes(84,16,0), preserving the physical barrel offset. Source geometry combines slab, frame margins, carved palms and hardware; hinges are distributed at18+j*(h-36)/2, while handle geometry has fixed physical dimensions. An actor-scale shortcut changes these dimensions or leaves centres incorrect. Correct door application therefore requires new candidate-only part-level mesh generation and rerunning the existing envelope/jamb solver. This is a concrete geometry limitation, not unresolved unit arithmetic. Curtain geometry/art remains unchanged under HOLD. No native jobs run.

Door regeneration is now implemented in Doors48V1 (see its README/spec): three actual OBJ meshes, twelve exact candidate replacements, preserved metric hardware and43-box clearance PASS. The prior statement that regeneration was required is resolved by these source artifacts; native application remains pending. Curtain/art remains unchanged.
