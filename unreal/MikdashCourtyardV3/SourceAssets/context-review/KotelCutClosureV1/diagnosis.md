# K2 western excavation: open boundary diagnosis

15 September 2026. **Offline diagnosis only. No production geometry, asset, map or runtime change.**

The Kotel terrain-cut generator leaves a vertical opening where the lowered plaza meets the
higher western hillside. This is a demonstrated geometry defect and a strong explanation for
the opening in the cp24 K2 frame. Exclusive attribution of the distant-city-looking pixels to
that defect remains pending a native A/B capture.

## Evidence and its limits

The inspected image is
`SourceAssets/visual-review/city-facade/cfafter-cp24-K2-kotel-upper-deck-facing-jewish-quarter.png`.
It shows foreground paving, higher terrain and buildings beyond it, and a wide opening with
distant scene fragments between them. Calling those fragments a reflection or a mirrored city
would be an interpretation; no reflection capture or screen-space reflection test was performed.

The requested K2 camera in `Scripts/capture_city_facade.ps1` is
`BugItGo -20732 19230 -814 6 175 0`, in MODERN after one V press. Its position is
**170.594 cm above the upper deck**, whose top is Z -984.594 cm. The source terrain at the
camera XY is Z -1115.605 cm. The requested camera therefore is not underground at its starting
position. These are plan/source calculations, not fresh PlayerCameraManager readback.

`Scripts/release_precinct_terrain_cut.py`, `clip_and_clamp` and `build_twin` (approximately
lines 258-332), preserve outside terrain and lower inside pieces to the deck underside.
They do not emit a face joining those different heights at a cut boundary. The output loop
rejects triangles with effectively zero XY area, which also excludes vertical closure faces.
The 2D area-preservation check cannot detect a missing vertical face.

`Scripts/create_kotel_plaza.py`, perimeter generation (approximately lines 512-555), adds
retaining bands only when `deck_z - ground_z > 0`. That closes elevated fill, but does not
close excavation where the surrounding ground is higher than the deck. The current plan
has 22 such bands; their existence is not evidence of cut-sidewall coverage.

The current V3 asset SHA256 remains
`ed26cb8d2710b4a425985fed31c095fe59c13cc1f0068454bc7d53092aa78211`, matching
`SourceAssets/enclosure-review/native-terrain-cut-assets-Candidate48-20260911T121133563106Z.json`.
That native receipt reports 566 source triangles, 2,714 saved twin triangles, winding agreement
for all 2,714, and maximum saved-normal error about 2.98e-8. It also verifies outside terrain
height preservation to approximately 0.00033 cm. These checks support faithful saved surface
geometry and argue against a wholesale flipped-normal explanation. They do not test closure,
camera visibility, or all scene actors.

## Reproducible source-geometry measurement

[measure_boundary.py](measure_boundary.py) and [boundary-samples.json](boundary-samples.json)
record the calculation and exact input SHA256 values. The measurement reads the frozen
`SM_JerusalemTerrain_07_08_FutureMountCut.mesh.json` containing the actual 566 triangles.
Its SHA256 is `abc6152db1d10b80476870ac843bfde232b30ccac90733994e3ecf743579095a`, matching
the FutureMount terrain manifest. Heights use barycentric interpolation on those triangles,
not the different bilinear 25 m DEM approximation.

For the cut footprint, the script reconstructs the 959 deck rectangles and applies the same
0.01 cm edge lattice as V3 `kotel_job`. It intersects horizontal rays with their union
analytically. It also reports the corresponding unsnapped deck edge, treating gaps up to
0.01 cm as numeric cell seams rather than the exterior boundary. The deck module bounds
(-625,-625,-50) to (625,625,0) cm are checked against `plaza-manifest.json`.

At K2 yaw 175 degrees the exact analytic result is:

- Cut boundary distance: **1762.6474 cm**; boundary XY **(-22487.94, 19383.62484) cm**.
- Boundary source triangle: **279**, with original ground at **Z -622.59324 cm**.
- Inside upper deck: **Z -984.594 cm**; inside cut target: **Z -1034.594 cm**.
- Missing vertical connection: **412.00076 cm**, of which **362.00076 cm is above paving**.
- The ray with the requested +6-degree camera pitch reaches **Z -628.73829 cm**,
  **6.14506 cm below the original outside ground** at this edge.
- The uncovered interval above the deck spans geometric elevations **-5.528 to +6.197 degrees**
  from the camera. This is not a pixel projection or full-scene occlusion result.

Seven sampled directions, yaw 150/160/170/175/180/190/200 degrees, leave the cut between
17.35 and 22.55 m from the camera and have uncovered above-deck heights between
**3.207 and 4.331 m**. Two centre-pitch rays are above the source edge at their directions;
their lower rays can still cross the opening. The receipt records signed distances rather
than asserting that every centre ray enters the opening.

This is a sampled west-edge diagnosis, **not an exhaustive perimeter coverage calculation**.
The script does not intersect buildings, road ribbons, other terrain tiles, or reflected
objects. It does not assert which distant actors supply the image fragments.

Run from the project root using Python 3.8 or newer:

```powershell
python -B SourceAssets/context-review/KotelCutClosureV1/measure_boundary.py
python -B SourceAssets/context-review/KotelCutClosureV1/measure_boundary.py --check
```

The first command writes only the JSON receipt in this folder. `--check` reads the same frozen
inputs, recomputes all seven samples and requires exact equality with the existing receipt.
Both commands have no Unreal dependency. Input, script and recipe hashes are part of the
receipt; changed inputs must be reviewed instead of quietly accepting a new baseline.

## Next discriminating native test

After the current native slot is free, load only the saved V3 terrain mesh and a simple upper
deck stand-in in an empty Entry scene, at their recorded identity transforms. Use and read back
the exact K2 camera. Capture the open edge, add a temporary opaque closure strip joining the
cut underside to the original boundary height, and recapture from the same camera/exposure.
Do not save the scene. This tests the causal geometry with a small asset load. A later actual
packaged K2 before/after comparison must establish whether it removes the entire visible band
or exposes another independent defect.

A production closure should derive its segments from the **actual cut-region union and
source-triangle intersections**, including holes and varying clamp levels. It should not use
a guessed rectangle, the smooth OSM polygon in place of the stepped cells, or a large wall
covering the view. Preserve the existing platform hole and Kotel wall guard. Verify seam
coverage, face winding, surface preservation, collision and native pixels separately.

No safe material-only correction is established: two-sided rendering cannot add a missing
vertical surface. A new corrected terrain asset is plausible, but applying it needs a
map-reference change or a reviewed runtime substitution. Overwriting V3 in place conflicts
with the project's existing-namespace protection. No such change is made or claimed here.
