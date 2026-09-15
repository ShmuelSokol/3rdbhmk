# LegacyRoofRuntimeV1 — runtime preparation, 15 September 2026

The saved Candidate48 map remains unchanged. This bounded runtime repair preserves
both original 6,007-instance rooftop components and prepares two transient plain ISMs,
4,744 instances each, from their existing local transforms in original order. At the
same `ShouldHardHide(Weights.ModernInside)` boundary as their owning buildings, the
controller switches visibility to those kept components. Modern, Overlay and partial
transitions display the originals. RestoreAll destroys only the owned transients and
restores original component flags; Rebuild restores first and then prepares anew.

Every operation is restricted to a Candidate48 game/PIE world with one enclosure,
269/0/0 hide-list resolution and actual native fingerprint `add1b55da3535d53`.
The older frozen precinct JSON has a different fingerprint; the current value is
recorded by the September 11 native Modern restore audit. Each of the 179 precinct
owner identities must resolve exactly once through the existing audited mesh identity
resolver and belong to SelectedBuildingIndices. No bounds or actor-name guess decides
which rooftop instance is removed.

The compiled table comes only from pinned plan SHA256
`4c259972edda978d3163485e1a9f3780d74cc81673b71b3fc5c9edb1dec1137b`:
6 float translations per pair, 1,263 source-index/owner-index rows, and 179 owner
strings. Generator tests prove decimal C++ float round trips reproduce all 12,014
translations with zero error. Runtime verifies all these positions within 0.1 cm,
finite full transforms, mesh identity, plain class, counts, visible originals,
NoCollision/navigation-off/overlap-off/custom-data-zero, and no conflicting zone tags.
Already editor-partitioned or changed groups are refused, leaving originals intact.

New components use NewObject and RF_Transient, retained by a transient UPROPERTY.
Only the release script's bounded render settings are copied by exact reflected
native property names; material pointers, component world transforms and local
instance order are retained. No DuplicateObject, asset loading, map saving, source
instance removal or collision change is involved. After registration, full local and
world transforms, materials, settings and counts are checked before a visibility swap.
Original full transforms/materials/render settings are snapshotted for later checks.

`GetLegacyRoofRuntimeStatus` and `GetLegacyRoofRuntimeCounts` expose native readback.
An explicit `-MikdashLegacyRoofDiagnostic` launch flag runs ten states after BeginPlay:
Yechezkel, Modern, Overlay, Yechezkel, half transition to Modern, Modern, half transition
to Yechezkel, Yechezkel, RestoreAll, Rebuild. It records actual per-component flags,
counts, transform/material/settings invariants and total visible instances to log and
`Saved/Diagnostics/LegacyRoofRuntimeV1-<UTC>.json`. The diagnostic does not launch another process. Adding the separate explicit
`-MikdashLegacyRoofDiagnosticExit` requests normal engine exit only after the JSON
is successfully saved and completion is logged; it is ignored without the diagnostic
flag. Interactive diagnostic runs remain open by default. Expected visible counts are 9,488 in Yechezkel and 12,014 in
Modern/Overlay/partial transitions/RestoreAll. Rebuild must return to 9,488.

Offline checks completed:

- `python Scripts/generate_legacy_roof_runtime.py --check`: exact table parity.
- `python Plugins/MikdashRuntime/Tests/test_legacy_roof_runtime.py`: 9/9, including
  independent all-position round trips, exact owner/index complement and rejection
  of duplicate indices, nonfinite/low precision positions, unknown owners/zones and
  conflicting owner memberships.

Coordinator acceptance: Editor and Game compiled and linked successfully after the
corrections below; 32/32 math suites and 9/9 runtime roof tests passed. Two isolated
packaged native runs passed all ten state phases with zero positional error and all
20 source maps unchanged. Latest receipt: packaged-20260915T153939Z.json; native
receipt: native-LegacyRoofRuntimeV1-20260915T153955Z.json. Both exited normally.

Six GPU frames were visually inspected: A1 shows the formerly floating tank/panel
pairs removed; elevated R1 shows them absent in Yechezkel and restored on the visible
buildings in Modern/Overlay. Ground Modern/Overlay alone cannot establish rooftop
restoration because restored walls obscure the roofs. See visual-acceptance.json
for frame hashes and limitations. The retained neighborhood remains populated.

The isolated Checkpoint-roofruntime01-20260915 archive uses old cp24 cooked assets
plus game binary f5e973d2693578c29da54163088aa340ec2e143dada07f897cf1a90c5ad4b2a6.
This is a verified runtime test copy, not a complete recook or public release. The
new saved stone shader is absent. Full cooks still fail at current commit headroom.
The Kotel terrain opening, occasional thin camera obstruction and remaining visual
quality work are not accepted as fixed by this bounded roof repair.

Verifier correction before first native compilation: UE 5.8 `ExportText_Direct`
returns false for a zero/false value identical to a null default. That result does
not mean the property is absent. The original null-Delta snapshot would therefore
have refused valid originals. CaptureProperties now obtains the actual property
value pointer and supplies that same pointer as both Data and Delta, which the
installed `Property.cpp` explicitly treats as forced export. All values, including
false/zero settings, are captured. Declaration verified in `UnrealType.h`; this
correction was found by source review, before a native runtime acceptance claim.

First Editor and Game compile attempts both rejected two `Owner` locals with C4458,
because they shadow the inherited AActor::Owner member. They are now
`OwnerLabelUtf8` and `SourceActor`, including all references. No introduced Owner,
Instigator or RootComponent local remains. The serial compilation retry passed both
targets (verify-runtime-build-retry-20260915T152453Z.log in LegacyRoofZonesV1).
