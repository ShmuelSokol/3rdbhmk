# Kotel cut closure: runtime integration

Status: accepted for the tested Kotel visual gap and paired stair route. Final
Editor/Game gate10/10 passed; native-tested child SHA256
`3aee6ac4d129e6327a7077d59d83557a50c10ecb731aa94744e1eb612d02f087`.
See `runtime-acceptance.json` for precise evidence and remaining limits.

The earlier Entry study established that the Kotel terrain cut has no vertical face
between the lowered plaza edge and the retained hillside. This addition draws that
missing face from the pinned source terrain and the current 959-cell paving plan.
It is an authored retaining treatment for the reconstruction, not a claim about a
historically documented new wall or a change to the preserved Western Wall.

The compiled buffers preserve the canonical 841 triangles and 2,523 independent
vertices/normals/UVs. Native indices are A,C,B; the supplied cavity normals remain
unchanged. The 85 internal level-boundary edges, holes, concave notches, nine stair
treads and upper landing are excluded from this exterior closure.

Runtime guards require Candidate48, one enclosure, the exact V3 cut mesh identity,
identity world transforms, a unique KotelPlazaV1 deck component and all 959 pinned
instance transforms. Asset SHA values in the generated header document provenance;
they are not raw cooked-asset hashes verified inside the game.

The transient component follows the actual Kotel terrain visibility after the
enclosure's tagged-actor update: Modern and Overlay show it; Yechezkel hides it.
It uses the loaded PlazaAshlarMaterial, with world YZ/XZ projection for vertical
stone. The old cp24 cook uses MacroV3; current uncooked disk assets use MacroV4.
This thin visual shell has no collision or navigation. Existing deck and protected
Western Wall collision remain responsible for movement boundaries.

Reproduction:

- `Scripts/generate_kotel_closure_runtime.py --check` validates pinned inputs/header.
- `Tests/test_kotel_closure_runtime.py` exercises geometry, provenance and drift checks.
- `Scripts/Test-KotelClosureRuntime.ps1 -Archive <isolated archive> -ExpectedChildSha256 <hash>`
  captures four native state phases. Add `-DisableClosure` for the control process.
- `Scripts/Test-KotelStairRuntime.ps1` with the same archive/hash replays the cp22e
  route; run on and off. It requires all three actual reached events, zero stuck
  events and the correct grounded upper-deck endpoint. Its owned child is stopped
  after completion because that older walk diagnostic does not exit automatically.

The test archive is a copied cp24 cook with a replacement verified runtime binary.
No source map, original archive, user save or full cook is modified by these probes.
The saved ContextCoursingV2 material fix is not included in these cooked assets.

The first executable trial (`runtime-20260915T170601943Z.json`, child `f1012872...`)
failed before BeginPlay with an out-of-bounds unversioned Actor export. Five new
transient reflected fields had changed the schema indices. The fix removes those
five reflections, retaining the closure through the actor's OwnedComponents and
using ordinary weak references. All 70 prior reflected property declarations and
their ordering match the last working commit. Compilation is not evidence that
an executable can deserialize a previously cooked map; the native load is required.
The corrected child loads the same map and completes the four-state probes. The
failed child is checkpointed; the accepted child now occupies the isolated copy.

Two subsequent trials stopped at the wrapper's initial2GiB reserve, without OOM.
The settings subsystem had overridden ResX/ResY with1920 borderless defaults.
The final probe disables that existing configurable override, explicitly uses
1280x720 with High groups/77% screen percentage, and keeps1.25GiB system reserve
plus an8GiB process ceiling. Measured peak7.36GiB/minimum free1.80GiB; captured
PNGs are2560x1440. No restart or system paging/security change was required.

This visual acceptance does not establish a physical barrier at the new face:
it intentionally has NoCollision. A direct edge-walking probe is still owed.
