# Performance budget

Target machine: **RTX 2070, 16 GB system RAM, 8 GB VRAM, 1080p.**
Target frame time: **16.7 ms (60 fps)** in the courts and sanctuary,
**22 ms (45 fps)** tolerated on the plaza looking out over the whole modern city,
which is the single heaviest view in the build.

Everything below is marked **measured** or **estimated**. Nothing here has been
confirmed against a running frame yet — `Scripts/perf_probe.py` exists to replace the
estimates with numbers, and until it has run this document is a plan, not a result.

## Where the triangles already are (measured, from release receipts)

| Element | Triangles | Source receipt |
|---|---:|---|
| Old City facades, authored budget | 6,000,000 | `facades-manifest.json` |
| Largest single import batch | 3,416,580 | `native-import-20260908T032216Z.json` |
| Aron | ~1,092,044 | `third-party-manifest.json`, `provenance.json` |
| Vessels group | 715,248 | `native-import-vessels-20260907T190204Z.json` |
| Kotel ashlar detail | 330,480 | `release-placement-20260907T161402Z.json` |
| Frieze panels if fully displaced | 29,819,328 | `native-import-20260907T194656Z.json` |

That last row is why the friezes are Nanite-displaced rather than baked: at authored
density they would exceed everything else in the scene combined. Note that with Nanite
on, `get_num_triangles(0)` returns the **fallback** count, not the real one — this
project has already been misled by that once.

Cook size for Walkthrough-11: **8,245 packages, 0 errors, 220 s.**

## Per-system allowance

Frame budget apportioned at 16.7 ms. GPU and game-thread are tracked separately because
on this machine the crowd is CPU-bound and the city is GPU-bound.

| System | GPU ms | Game thread ms | VRAM | Basis |
|---|---:|---:|---:|---|
| Architecture, Nanite | 4.0 | 0.5 | 1.2 GB | estimated from triangle counts above |
| Old City facades + infill | 3.5 | 0.5 | 1.0 GB | estimated; 3,620 buildings, instanced |
| Lumen GI + reflections | 3.0 | 0.3 | 0.9 GB | estimated; the default cost on this class of card |
| Shadows (virtual shadow maps) | 1.5 | 0.2 | 0.4 GB | estimated |
| Crowd field | 0.8 | 1.0 | 0.3 GB | **measured design limit**: 500 instance updates/frame, one sweep every 20 frames, does not grow with head count |
| Vegetation | 1.2 | 0.3 | 0.6 GB | estimated; budget set by the vegetation pass |
| Transit (trams, buses, cars) | 0.6 | 0.4 | 0.3 GB | estimated |
| Fire, smoke, plumes, dust | 1.0 | 0.2 | 0.2 GB | estimated; material-card effects, not Niagara sims |
| Water (the Yechezkel stream) | 0.7 | 0.1 | 0.2 GB | estimated; translucency and refraction dominate |
| Birds | 0.2 | 0.2 | 0.05 GB | estimated; HISM, a few hundred instances |
| Decals and surface wear | 0.5 | 0.1 | 0.3 GB | estimated |
| Enclosure wall (1.4 km, instanced) | 0.6 | 0.1 | 0.2 GB | estimated; only in the Yechezkel and overlay states |
| MetaHuman near-camera characters | 1.5 | 1.2 | 0.5 GB | estimated; ~50 MB unique texture each at Medium/2K, plus RigLogic per visible character |
| UI, tour, codex | 0.1 | 0.2 | 0.05 GB | estimated |
| **Total** | **19.2** | **5.3** | **6.2 GB** | |

**The GPU column already exceeds the 16.7 ms target.** That is deliberate: it is the
honest sum of what is being built, and it says the work is over budget before it is
measured. What gives, in order:

1. Lumen quality drops a tier on the plaza view only.
2. Crowd `-CrowdCount` thins from 10,000 to 2,500 proportionally across zones — the
   crowd system already supports this and thins every zone rather than emptying the far ones.
3. Vegetation instance cap halves.
4. The enclosure wall renders only in its own two states, never in MODERN.
5. Decals fade at distance before anything structural is cut.

Nothing on that list touches the Mikdash itself. The building is the subject; the city,
the crowd and the weather are the frame around it, and they yield first.

## Memory

16 GB with an 8 GB card is the real constraint, and it has already bitten this project:
background cooks were killed by the memory guard once the pilgrims' skeletal mesh and the
1M-triangle Aron were in the map, peaking about **8.4 GB** (measured). Hence:

- Cooks run in the **foreground** from PowerShell with `-cookprocesscount=1`.
- Engine jobs run **strictly serial**. One editor process at a time.
- MetaHuman auto-rigging refuses below **10 GiB free RAM**, so joints-only is the setting
  on this machine regardless of preference.

## What is not budgeted, and why

- Facial animation and lip sync: not built, so no allowance.
- Ray-traced reflections beyond Lumen's: not planned for this card.
- Volumetric clouds are inside the sky allowance, not separate, because the time-of-day
  system turns them down with the same lever.

## How to replace the estimates

```
Scripts\perf_probe.py
```
runs a bounded PIE walk over a fixed route and records frame time, draw calls, primitive
count, triangle count and memory at each station, then writes a receipt with a pass/fail
against this table. It must run in a **real RHI** editor — line traces and frame timings
both return nothing under `-nullrhi` and in commandlets. Invocation is in the file's
docstring. Until that receipt exists, treat every "estimated" row above as a guess made
by someone who had read the receipts but not watched the frame.

---

## First measurement, 8 September 2026 (receipt `perf-probe-20260908T102520Z.json`)

The estimates above were made before anything had been measured. Here is the first real
run, on the Walkthrough-11 map, before any of the new systems are placed. **It fails.**

| Station | p50 ms | p95 ms | worst ms | implied fps | budget | within |
|---|---:|---:|---:|---:|---:|---|
| court toward sanctuary | 23.0 | 51.1 | 553.2 | 32 | 16.7 | no |
| altar approach | 17.6 | 24.1 | 244.0 | 48 | 16.7 | no |
| Heikhal doorway | 17.5 | 26.1 | 37.6 | 51 | 16.7 | no |
| menorah | 24.1 | 27.1 | 34.6 | 41 | 16.7 | no |
| golden altar | 24.4 | 27.1 | 47.1 | 41 | 16.7 | no |
| paroches | 24.6 | 27.6 | 39.6 | 41 | 16.7 | no |
| Mount platform deck | 24.6 | 28.1 | 33.1 | 40 | 16.7 | no |
| plaza over the city | 24.6 | 28.6 | 232.9 | 39 | 22.0 | no |

Census at the same moment: **7,767 actors, 44,217 instances, 7,520 unique static meshes,
190 Nanite meshes, 30,514,170 triangles (lower bound).**

**The diagnosis the numbers point to.** The frame time is essentially flat — about 24 ms
whether the camera is sealed inside the Heikhal or looking out over the entire modern
city. A GPU-bound scene does not behave that way; an enclosed interior should be far
cheaper than a panorama. A cost that does not change with the view is a per-draw CPU
cost, and 7,520 unique meshes across 7,767 actors is exactly that: unique meshes cannot
batch, so nearly every object is its own draw call regardless of what is on screen.

Only 190 meshes have Nanite, and those are the frieze panels. The Old City, which is
most of the mesh count, does not.

So the budget table above apportions a GPU problem the build does not currently have,
while the actual bottleneck — draw calls — is not in it at all. That is what a first
measurement is for. An optimization pass is under way to confirm the diagnosis with
evidence rather than inference, enable Nanite in bulk where it is eligible, instance what
shares a mesh, and re-measure. The estimated rows above stay marked estimated until that
returns with before-and-after numbers.

Caveat on this run: the first station recorded no samples because the probe's teleport
window closed before PIE produced a pawn. Fixed, and the memory readback (which returned
null here) was fixed at the same time. Neither affects the eight stations that did record.
