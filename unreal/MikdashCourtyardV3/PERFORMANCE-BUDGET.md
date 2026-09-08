# Performance budget

Target machine: **RTX 2070, 16 GB system RAM, 8 GB VRAM, 1080p.**
Target frame time: **16.7 ms (60 fps)** in the courts and sanctuary,
**22 ms (45 fps)** tolerated on the plaza looking out over the whole modern city,
which is the single heaviest view in the build.

**This document is no longer a plan.** On 2026-09-08 `Scripts/perf_probe.py` ran against
the combined Walkthrough map with a real RHI and the engine CSV profiler, and the
estimates below have been replaced with measurements. Rows still marked *estimated* are
the ones nothing has measured yet, and they say so.

Receipts, all under `SourceAssets/perf-review/`:

| Receipt | What it is |
|---|---|
| `perf-probe-20260908T102520Z.json` | the first run ever. Superseded: no warm-up, and its memory fields are all null because of a ctypes bug since fixed |
| `perf-probe-20260908T104900Z.json` | **the before-Nanite baseline**, warm-up 45 s, thread and GPU times, draw calls |
| `perf-optimize-analyze-20260908T103429Z.json` | the geometry census and the Nanite eligibility rule, with a full 7,519-row mesh index beside it |
| `perf-optimize-nanite-20260908T111035Z.json`, `...T111554Z.json` | the Nanite pass: 7,230 meshes, 0 failures |
| `perf-probe-20260908T112929Z.json` | the after-Nanite measurement, taken while the derived-data rebuild was still running |
| `perf-probe-20260908T115107Z.json` | **the current after-Nanite measurement**, 28 minutes of rebuild drained first |
| `perf-optimize-analyze-20260908T122328Z.json` | the final census: 7,420 of 7,519 meshes Nanite, 0 eligible remaining |
| `FAILED-*.json` | preserved failures. Read them before repeating their mistakes |

The combined map was **not modified**. Its SHA-256 is
`dae24e5e6005cfb87662bb8cf9bc074057c6c6bd655f1b02e9d8e815b4b624d8` before and after,
and it is checkpointed at `ReviewCheckpoints/PerfNanite-20260908T111554Z` and three
earlier stamps. This pass changed mesh assets only: no actor, transform, material or
vertex was touched.

## What the frame was actually doing

Measured, mean over the sampled walk, from the CSV profiler.

| | Before Nanite | After Nanite |
|---|---:|---:|
| Frame time | 31.6 ms | 30.2 ms (still carrying the rebuild below) |
| GPU time | **25.7 ms** | **17.0 ms** |
| Render thread | 3.0 ms | 3.6 ms |
| RHI thread | 0.8 ms | 0.7 ms |
| **Draw calls** | **10,414** | **3,140** |
| **Primitives drawn** | **7,510,812** | **434,305** |
| Peak system memory | 8,441 MB | 5,556 MB |
| Nanite root pages (always resident) | 5.9 MB | 230.3 MB |

The render thread was never the problem and never has been. It is 3 ms.

## Per-system GPU cost (measured, ms, mean over the walk)

This replaces the estimated table that used to be here. Anything not listed was below
0.2 ms. `-csvGpuStats` is required to reproduce it.

| GPU pass | Before | After | Note |
|---|---:|---:|---|
| **ShadowDepths** | **8.62** | **1.15** | virtual shadow map + shadow depth rendering. The single largest cost in the build, and view-independent, which is why frame time was flat everywhere |
| VolumetricCloudShadow | 3.66 | 4.52 | **now the single most expensive pass in the frame** |
| TemporalSuperResolution | 2.08 | 2.37 | TSR at 1080p |
| LumenScreenProbeGather | 2.07 | 2.08 | Lumen GI |
| VolumetricCloud | 1.32 | 1.53 | |
| Basepass | 1.57 | 0.28 | non-Nanite geometry |
| Prepass | 1.06 | 0.18 | non-Nanite geometry |
| NaniteBasePass | 0.21 | 0.56 | |
| NaniteVisBuffer | 0.45 | 0.40 | |
| SlateUI | 0.41 | 0.43 | editor overlay; absent in a packaged build |
| LumenSceneLighting | 0.37 | 0.39 | |
| GlobalDistanceFieldUpdate | 0.33 | 0.07 | |
| DistanceFieldShadows | 0.27 | 0.16 | |
| ShadowProjection | 0.28 | 0.29 | |
| PostProcessing | 0.25 | 0.26 | |
| RenderDeferredLighting | 0.23 | 0.23 | |
| Lights | 0.24 | 0.20 | |
| LumenReflections | 0.17 | 0.17 | |
| Unaccounted | 0.70 | 0.75 | |

Draw calls by pass, same runs: ShadowDepths 3,565 -> 1,442; Basepass 2,928 -> 664;
Prepass 2,870 -> 639; BeginOcclusionTests 514 -> 38; Translucency 16 -> 0.4.

**The two things this table says.** First, the cost was shadow-depth rendering of
thousands of separate non-Nanite primitives, not pixels and not overdraw — which is
exactly why an enclosed sanctuary and an open view over the whole city cost the same.
Second, with that gone, **the volumetric clouds are now the most expensive thing in the
frame at about 6 ms for cloud plus cloud shadow**, and the old note in this document
that clouds "are inside the sky allowance, not separate" is no longer a defensible way
to account for them.

## Where the geometry is (measured, from the census)

7,767 actors, 7,742 non-instanced StaticMeshComponents, 5 instanced components carrying
44,217 instances, **7,519 unique static meshes**. Sections x components came to 10,391,
and the profiler independently measured 10,414 draw calls: the census and the renderer
agree, and the unique-mesh count IS the draw-call count.

| Category | Unique meshes | Components | LOD0 triangles, all instances |
|---|---:|---:|---:|
| `JerusalemContext/Streets` | 2,875 | 2,875 | 305,308 |
| `Architecture` (the Mikdash itself) | 2,633 | 2,633 | 86,760 |
| `JerusalemContext/Buildings` | 1,498 | 1,498 | 242,700 |
| `JerusalemContext/Terrain` (FutureMountV1) | 252 | 252 | 129,024 |
| `JerusalemContext/OldCityFacadesV1` | 190 | 190 | 3.4 M (Nanite; the 468,918 reported is the fallback) |
| `MaterialReview` (friezes, Kotel, keilim) | 39 | 260 | **26,757,452** |
| `ArrivalReview` (transit) | 16 | 16 | 30,180 |
| `ThirdParty` (the Aron) | 2 | 2 | 916,320 |
| `JerusalemContext/DecorativeInstancesV1` | 5 | 44,217 instances | 1,554,924 |
| other, engine content | 9 | 12 | 4,472 |

Two things in that table correct earlier claims in this file and in the handoffs:

* **The 190 Nanite meshes were the Old City facades, not the frieze panels.** The
  facades were imported with Nanite on and were already right. Everything else in the
  city and in the Mikdash was imported with `build_nanite=False` — see
  `import_buildings_ue58.py`, `import_streets_ue58.py`, `import_future_mount_terrain.py`.
* **The friezes were not Nanite-displaced. They were baked.** Six `SM_KeruvFriezeV2_*`
  meshes of 67 k-133 k triangles each, placed as 211 components, carrying 26.1 M of the
  scene's 30.5 M triangles, all of it rasterised the hard way and all of it re-rasterised
  into shadow depth. The "if fully displaced" row that used to be in this document
  described a cost the build was already paying.

The city and the Mikdash were never a triangle problem. All 2,875 street meshes together
are 305 k triangles; all 2,633 Mikdash architecture meshes together are 86 k, and 2,254
of those are 12-triangle boxes. They were a **draw-call** problem, one mesh and one actor
at a time.

## The Nanite pass (applied 2026-09-08)

`Scripts/perf_optimize.py -PerfMode=nanite` enabled Nanite on **7,230 meshes, 0 failures**,
under an eligibility rule written out in full in that file's docstring and recorded in
every receipt. Summary: drawn in the map, not already Nanite, no translucent/additive/
modulated material, category on a reviewed allowlist, no excluded word in path or name,
and matching on whole words rather than substrings. Masked materials are allowed.

Deliberately untouched: the Old City facades (already Nanite), the decorative HISMs
including the tree crowns and trunks, transit vehicles, crowd and characters, the
paroches and its fixings, the two translucent meshes, and the golden roof's anti-bird
points. **99 meshes remain non-Nanite by rule.**

Final state, verified by a fresh census (`perf-optimize-analyze-20260908T122328Z.json`):
**7,420 of 7,519 unique meshes are Nanite, 0 eligible meshes remain**, and all 99
exclusions are attributed to a named clause: 70 anti-bird points and 5 paroches parts
and 1 cloth by word, 21 by category (transit, decorative HISMs, an engine plane), 2 by
translucent blend mode.

Reverting is one command and does not need a receipt:
`-PerfMode=revert_nanite` turns Nanite off for every Nanite mesh in the allowlisted
categories, which is exactly the set this pass created. Reverting is also *cheap*: it
restores the previous derived-data keys, and the old cache entries are still there, so
nothing rebuilds.

### The bill this pass ran up

Enabling Nanite invalidates each mesh's derived data, so the engine rebuilds its
distance field and its Lumen card representation. Measured: **mean 2.6 s per mesh,
p50 1.6 s, max 10.6 s**, at roughly 0.5-0.7 meshes per second because the asset compiler
throttles itself on a 16 GB machine with 5 GB free. Across ~7,200 meshes that is a
**one-time cost of several hours**, and until it is paid the game thread carries it.
Measured on the way down: with the queue cold, frame time was 30-64 ms per station; after
28 minutes of draining it was 24-31 ms, back to parity with the pre-Nanite baseline,
while the GPU stayed at 17 ms throughout. Roughly 1,100 of about 7,200 rebuilds were done
at that point, so the queue has hours left in it and the steady-state frame time has not
been measured yet.

Two consequences worth writing down. The cost is unavoidable rather than wasted — a cook
would pay it too — but it is far larger than it should be, because a 12-triangle box
gets a 126x126x63 distance field. And **a measurement taken while that queue is draining
is not a measurement of the scene**; check the log for `Finished distance field build`
before trusting a frame time.

## Where it stands against budget

Measured p50 and p95 frame time, 1080p, editor PIE, warm-up held before sampling.
"before" is `perf-probe-20260908T104900Z`. "now" is `perf-probe-20260908T115107Z`, taken
after 28 minutes of derived-data draining and with that queue still running.

| Station | Budget | p50 before | p50 now | p95 before | p95 now | GPU before | GPU now |
|---|---:|---:|---:|---:|---:|---:|---:|
| outer_court_east | 16.7 | 25.6 | **24.1** | 40.1 | 45.1 | 24.6 | **16.9** |
| court_toward_sanctuary | 16.7 | 27.1 | 29.1 | 53.1 | 51.1 | 26.5 | **16.9** |
| altar_approach | 16.7 | 26.6 | **24.6** | 40.6 | 41.6 | 25.5 | **17.0** |
| heikhal_doorway | 16.7 | 25.6 | 27.6 | 36.6 | 42.1 | 24.4 | **16.8** |
| menorah | 16.7 | 26.1 | 26.6 | 38.1 | 43.1 | 24.5 | **16.9** |
| golden_altar | 16.7 | 27.6 | 30.6 | 62.3 | 61.2 | 25.6 | **17.1** |
| paroches | 16.7 | 28.6 | **26.6** | 54.1 | 44.6 | 26.6 | **17.1** |
| mount_platform_deck | 16.7 | 28.1 | **24.1** | 49.1 | 36.1 | 25.9 | **17.0** |
| plaza_over_city | 22.0 | 28.1 | **26.6** | 58.1 | 39.1 | - | - |

**Every station is over budget, before and after.** Nothing here should be read as a
frame-time win yet. What the Nanite pass bought is 8.6 ms of GPU headroom and 7,275
draw calls, and what it has not yet bought is a faster frame, because **the frame is now
game-thread bound**: game thread 28.7 ms against a GPU of 17.1 ms. Some of that game
thread is still the one-time derived-data rebuild described above, which was measurably
running throughout this very sample.

The honest reading: the shape of the problem has changed from "the GPU is redrawing
thousands of separate primitives into shadow maps" to "the CPU is carrying 7,767 actors",
and the second problem is the one that is now binding. The first was worth fixing on its
own terms and the fix is measured. The second needs fewer actors, not different flags.


## The look has not been visually verified

Nanite changes how a mesh is drawn, not what it is. The evidence that nothing about the
build's appearance changed is structural, not visual: the map file is byte-identical, no
material, transform, section or vertex was written, every setter was verified by
readback, and the two translucent meshes plus the paroches were excluded by two
independent clauses of the rule.

That is not the same as looking at it. The probe's per-station screenshots were meant to
be the visual A/B and **they are not usable**: under `-unattended` the `HighResShot`
console command captures the editor viewport rather than the PIE pawn's camera, so the
before/after frames are aerials from unrelated angles at different times of day. The
limitation is now written into `perf_probe.py`. **A human or a proper capture pass should
look at the sanctuary and the frieze wall before this change is considered accepted**,
because a flattened frieze relief is exactly the regression this project has had before.

## What to do next, in order

1. **Finish the derived-data rebuild.** Hours of exclusive editor time, and until it is
   done every frame-time measurement on this map is measuring the compiler as well as
   the scene. Nothing below can be evaluated before it.
2. **Merge the small architecture meshes.** 2,254 of the 2,633 `Architecture` meshes are
   12-triangle boxes, each its own asset and its own actor, together 27 k triangles.
   They cost 2,254 actors of game-thread work and about 70 MB of Nanite root pages, and
   they are the largest single block of the 7,767 actors that now bind the frame. The
   census records 3,102 meshes in duplicate-geometry groups
   (`possibleInstancingGroups` in the analyze receipt). They cannot be instanced as they
   stand, because `import_*_ue58.py` imported them with
   `transform_vertex_to_absolute=True` and their vertices are baked to world space; they
   have to be merged, or re-imported at origin with per-instance transforms.
3. **Look at the volumetric clouds.** At 4.52 + 1.53 ms they are now the most expensive
   thing the GPU does, more than Lumen GI and TSR combined.
4. **Leave distance culling alone until 1-3 are done.** The census found **zero**
   components with a draw distance, no HLOD, and no World Partition. That is worth
   knowing, but it is not the bottleneck: the 252 FutureMountV1 terrain tiles are 512
   triangles each, 129 k triangles for the whole set, and they are Nanite now, so they
   already LOD themselves. Adding cull distances would trade pop-in for a saving nothing
   has shown to exist.

## Memory

16 GB with an 8 GB card is the real constraint. Measured on the baseline walk: editor
working set 5.7-6.2 GB, peak 7.5 GB, and the engine's own `SystemMaxMB` 8,441 MB. After
Nanite the same figures are 4.1-4.8 GB, peak 5.1 GB, `SystemMaxMB` 5,556 MB.

Against that, Nanite added **224 MB of always-resident root pages** (5.9 MB -> 230.3 MB),
about 31 KB per mesh. That is the price of putting Nanite on 7,230 separate assets, and
it is the strongest argument for merging the small ones.

Operational rules, unchanged:

- Cooks run in the **foreground** from PowerShell with `-cookprocesscount=1`.
- Engine jobs run **strictly serial**. One editor process at a time.
- MetaHuman auto-rigging refuses below **10 GiB free RAM**, so joints-only is the setting
  on this machine regardless of preference.

## What is still estimated, and why

- Crowd field: **measured design limit** of 500 instance updates/frame, one sweep every
  20 frames, does not grow with head count. Not separately profiled in a frame.
- Vegetation, birds, water, fire and smoke, decals, MetaHuman characters, UI: not
  separable from the passes above without a per-object GPU capture. The CSV gives cost
  per *pass*, not per *system*, and this document will not invent the split.
- Facial animation and lip sync: not built, so no allowance.
- Ray-traced reflections beyond Lumen's: not planned for this card.

## How to reproduce any of this

```
Scripts\perf_probe.py      # real RHI, PIE, per-station frame/thread/GPU/draw-call times
Scripts\perf_optimize.py   # census, Nanite eligibility rule, Nanite pass, revert
```

Both files carry their exact invocation in their docstring. Three things that will waste
an hour if they are not read first: the probe needs a real-RHI editor launched with
`-ExecCmds="py ..."` and `-csvGpuStats`; the CSV profiler holds its file open until the
process exits, so thread times are merged afterwards with
`python Scripts/perf_probe.py --merge-csv <receipt.json>`; and a warm-up longer than
`MIKDASH_PERF_LIMIT_SECONDS` means the run ends in warm-up having measured nothing.
