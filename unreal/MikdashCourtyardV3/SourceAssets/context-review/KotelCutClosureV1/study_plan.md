# Unsaved Entry-scene test of the Kotel exterior cut seam

Prepared 15 September 2026. **Study recipe and offline buffers only; native A/B not run.**
This tests the missing vertical connection established in `diagnosis.md`. It does not
create a production asset or assert that every cp24 K2 image defect has the same cause.

## Exact study geometry already prepared

`generate_study_closure.py` writes `closure-study.json` in this folder. Run:

```powershell
python -B SourceAssets/context-review/KotelCutClosureV1/generate_study_closure.py
python -B SourceAssets/context-review/KotelCutClosureV1/generate_study_closure.py --check
```

The generator uses only the pinned inputs and module checks from `measure_boundary.py`.
It imports no Unreal or third-party library. `--check` writes nothing. The geometry is
world-centimetre triangle buffers with normals, metric UVs and per-piece source-triangle
provenance. It is **not an asset interchange import instruction**.

The present result contains **841 triangles**, from **562 exterior atomic edges**; all seven
measured west-edge samples have matching lower and upper closure heights. **85 internal
level-boundary edges are counted and excluded.** They are a different study, often hidden
under the flight/deck. No exterior length lacks source terrain for these particular inputs.

Boundary semantics are precise:

1. Reconstruct all 959 deck rectangles from the verified 1250 cm module dimensions and
   saved transforms. Snap their edges to the V3 0.01 cm lattice, exactly as `kotel_job`.
2. Build the rectilinear arrangement of all unique X/Y edges. For a covered arrangement
   cell, its target is the **minimum deck underside** of every overlapping rectangle.
   Thus duplicate/overlapping cells never produce duplicate exterior walls.
3. Select only edges with covered terrain on one side and no cut region on the other.
   Adjacencies between two covered cells, even when targets differ, are excluded here.
   This preserves concave notches and internal uncut islands; it does not replace the
   footprint with an AABB, convex hull, centre-tested polygon, or smooth OSM outline.
4. Intersect each edge segment with the XY projection of every one of the actual 566
   source triangles. Clip its line parameter against the three barycentric halfplanes.
   Split overlapping intervals at all their endpoints, choose one source interpolation
   per interval, and require any coincident source-triangle heights to agree. A source
   diagonal therefore does not produce two coincident curtains.
5. On each interval, source height is linear along the segment. If the whole source
   segment is below the target, emit nothing. If it crosses the target, solve and split
   at the crossing exactly. Otherwise connect target Z to source Z. No extrapolation
   across absent source terrain is allowed; the existing platform hole remains a hole.
6. Emit one quad/two triangles, or one triangle at a height-zero endpoint. Normals face
   into the lower cut region. Mathematical cross products agree with those normals.
   UVs use distance along the segment and vertical height, avoiding degenerate world-XY
   UVs on vertical faces. Native winding/front-face verification is still owed.

The generator tests touching rectangle unions, minimum-target overlaps and a known flat
terrain square crossing a shared source diagonal (exact expected curtain area, no double
faces). It checks every earlier west-edge sample against the generated pieces. This is
not a proof that the entire terrain is a closed solid: no bottom shell, platform-hole
wall, internal-step closure, access stair or city building is invented.

## Native slot and memory gate

`native_study.py` now implements the basic A0/B/A1 sequence. It has been prepared from
installed UE5.8 headers and the earlier ContextCoursing capture helper; it has **not yet
been run natively**. The coordinator must review it, then launch the owned GPU editor on
`/Engine/Maps/Entry` with `-KotelClosureStudy -ExecCmds="py <absolute native_study.py>"`.
The explicit marker is required. A wrong project/world, absent marker or active PIE is
refused; an unvalidated editor is never automatically quit. No subprocess launch is
performed by the script.

The script hashes all 20 `.umap` files and all `.uasset`/external-bulk sidecars in Content
before/after, not merely the two study mesh files. Current census is 20 maps and 9,212 assets,
about 2.2 GB total; hashing streams one MiB blocks. It also rejects dirty production packages,
records memory at each phase, validates all 959 deck transforms and every dynamic triangle,
then flushes the final receipt before requesting a normal quit of the validated owned editor.
It leaves image interpretation pending rather than equating PNG creation with acceptance.

Run only after the coordinator releases the native slot and records fresh commit headroom.
Use an owned editor starting at `/Engine/Maps/Entry`, with the existing project's plugins,
GPU rendering and serialized async asset compilation. Do not load Candidate48, Main50,
the source city map, or their external actor packages. Do not use `-nullrhi` for frames.

The target is **less than 2 GiB of editor private working set**, motivated by the earlier
material-only Entry studies around 1.6 GiB. This is an execution budget, **not a verified
prediction**. Record process working set/private bytes and system committed bytes before
launch and after each load. If this small scene exceeds the budget or approaches system
commit exhaustion, stop the owned study normally and retain the failure receipt. Do not
respond by loading the full map or changing services. Checkpoint no production assets
because this recipe never saves or edits them.

## Minimal scene and buffers

Create the following actors/components **transiently in the editor world**; do not enter PIE
and do not run the project game mode. Keep collision, navigation and overlaps disabled on
every study primitive. Never invoke SaveAll, save_level, AssetTools import, or a static-mesh
asset creation function.

- One StaticMeshActor with the saved V3 mesh
  `/Game/MikdashV3/KotelPlazaCutV3/SM_JerusalemTerrain_07_08_FutureMountCut_KotelPlazaCut`,
  at identity transform. Require its SHA256 to match the diagnosis/native receipt.
  This supplies the actual saved discontinuous surface, not an offline approximation of it.
- One transient deck HISM using the existing `SM_PlazaV1_DeckTile` from
  `/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes`, with all 959 transforms from
  the pinned plan verbatim. This is only 11,508 module triangles at LOD0, avoids a guessed
  stand-in edge and preserves the small original-versus-snapped edge differences.
- One transient DynamicMeshComponent/actor carrying `closure-study.json`. Populate a
  `GeometryScriptSimpleMeshBuffers` with `vertices`, `normals`, `uv0`, and `triangles`,
  then use `GeometryScript_MeshEdits.append_buffers_to_mesh` on its DynamicMesh.
  `release_precinct_terrain_cut.Native.create_twin` demonstrates the buffer APIs; **stop
  before that method's static-mesh asset creation/save path**. Resolve the actor/component's
  exact installed API before execution; do not fall back to saving a temporary asset if
  component creation fails. Maintain an owned reference so garbage collection cannot
  remove it between frames. Start this component hidden.
- One piloted CameraActor at **(-20732,19230,-814)**, constructed with
  `unreal.Rotator(pitch=6, yaw=175, roll=0)` using named arguments. Read back actual location,
  rotation and FOV before each frame. Use a fixed recorded FOV (90 degrees is acceptable
  for this isolated geometry test) and a fixed viewport resolution. Original packaged
  FOV was not read back by the old capture receipt; do not call this pixel-identical K2.

For the first pass, use simple **transient opaque unlit, one-sided** materials with visibly
different constant colors on terrain, deck and closure. This eliminates lighting, textures,
SS reflections, Lumen and exposure as explanations for a closed opening. Use a uniform
contrasting viewport background or a distant study backdrop, fixed throughout A/B. The
closure can be magenta to distinguish the new face from original surface. Material creation
must remain in the transient package. Do not rebuild the shared context material graphs.

An optional later lit pass can retain V3's original material and use neutral rough stone
on the closure. That is not material acceptance: `M_Context_Terrain` projects world XY,
which is unsuitable as a final vertical-wall appearance. No rock strata, modern retaining
wall or historical masonry design is implied by this diagnostic surface.

## A / B / A sequence and discrimination

1. Verify all loaded inputs and transient component counts. Read back the V3 transform,
   959 deck transforms and closure triangle count. Both terrain/deck stay visible.
   Lock camera, resolution, exposure and materials; capture **A0: closure hidden**.
2. Make **only the closure component visible**. Invalidate the viewport, capture
   **B: closure visible**, and read back the unchanged camera/settings. No camera movement,
   light change, source-mesh swap or added solid rectangle is permitted between A0 and B.
3. Hide the closure again, capture **A1**, and verify it restores the opening. If A0/A1
   differ materially, resolve the capture instability before attributing B to geometry.
4. **Follow-up, not implemented in the initial native script:** repeat a second fixed camera
   aimed at a side edge. Verify the one-sided front face is
   visible from inside the cut and culled from the high-ground side. Two-sided material
   can be a separate diagnostic, but must not be used to conceal incorrect winding.

The baseline should expose the backdrop between the deck edge and higher original terrain.
The B frame should replace precisely that interval with the source-derived closure color,
while retaining the skyline/terrain surface and deck footprint. At yaw175 the closure top
must hit **Z -622.59324**, the bottom **Z -1034.594**, at XY
**(-22487.94,19383.62484)**. The interval above paving is **362.00076 cm**. Use the seven
receipt samples to check the silhouette extent; do not accept disappearance caused by a
wall extending above the original ground or across an access notch.

This A/B establishes that the missing connection permits looking through the excavated
surface and that the exact derived face closes it. The isolated scene contains no distant
city, road ribbons or player meshes. It therefore **cannot establish which actors account
for every band pixel in cp24**, cannot explain the separate thin rod, and cannot prove
walking/collision behavior. A subsequent same-camera packaged scene A/B is still required
before selecting a production integration.

## Receipts and cleanup

Record unique capture paths, source and generator hashes, engine version, PID, process/system
memory, actual camera/exposure/resolution, transient object paths, triangle/instance readback,
visibility states and pass/fail reasons. Record map/asset hashes before and after. Destroy only
owned study actors or close the owned Entry editor without saving; restore any viewport
settings changed by the study. Any accidentally dirty production package is a failure,
not permission to save it. No performance, collision, visual-material or production-fix
claim follows merely from buffer construction or successful screenshots.
