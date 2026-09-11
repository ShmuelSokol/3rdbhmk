# Overnight state — 9→10 September 2026

Twenty-six commits. Four playable checkpoint builds. Written for whoever picks this up next,
including Shmuel: it says what is *verified*, what is merely *placed*, and what is *blocked*,
because the difference is the whole story of the night.

## Use this build

```
C:\Mikdash\Builds\Checkpoint-cp04-20260910T035436Z\Windows\MikdashCourtyardV3.exe
```

3.92 GB, opens in 18 seconds. Earlier ones (cp01, cp02b, cp03) are kept on disk as fallbacks.
`Checkpoint-Build.ps1 -Label cpNN` makes another; `Smoke-Build.ps1 -Archive <dir>` re-tests one
without re-cooking. See `CHECKPOINTS.md`.

## The one thing to know before looking at it

Almost nothing below has been seen by anybody, and for most of the night that looked
unfixable. The **editor** cannot render here: a real-RHI editor on this map reserves ~19.9 GB of
address space against ~19.8 GB of commit headroom (Windows holds ~45 GB of a 63.9 GB limit before
any engine starts, `mc-fw-host` alone 11 GB and growing with uptime). Note the cause is the
Windows **commit limit**, not VRAM — D3D12 reports "out of video memory" while VRAM sits at
4,276 MB of a 7,238 MB budget. Diagnose with `Committed Bytes` against `Commit Limit`, never with
free RAM, which read 7–8 GB at moments when commit had no room at all.

**But the PACKAGED BUILD renders fine.** It peaks at **2,852 MB** — a seventh of the editor — and
opens a window in 18 seconds. That inference ("no frames possible") was drawn from the editor's
footprint and was simply wrong for the shipped exe, and it cost most of a night of visual
acceptance. The builds are Development config precisely so they keep the console. **Capture from
the packaged build, not the editor.** A reboot would recover the editor too, but it is no longer
a prerequisite for seeing the work.

## Landed and verified numerically

| | evidence |
|---|---|
| Precinct plaza, both maps | 34,741 instances, 7 draw calls, deck at the Temple's own datum |
| Terrain cut under it | max terrain above deck underside **7.1e-15 cm**, unchanged outside to 0.001 cm |
| Kotel plaza | 1,029/1,029, coverage 99.2% by area and 97.8% by station, 0 stations pierced |
| Approaches | head meets deck **0.00 cm**, foot meets ground within **14.5 cm** |
| Walk clip re-authored | planted-foot drift **4.572 → 0.019 cm**, step 35.98 → 71.93 cm |
| Walk imported | measured in engine: 71.97 cm step, drift 0.053 cm, 6/6 variants both maps |
| Kohen Gadol | 1.49× foot slide → 1.000, clip and speed moved together |
| Old City | 1,498 components retinted, 24 detail groups, both maps |
| MODERN restores | proven by state-switching and counting, not by reading code |
| Gates / decals / trees on the COOK map | 90 / 460 / 225,780 — none had ever been in a build |
| Sanctuary shell | 10 slots no pass had ever touched; floor tonal spread 38.3 → 67.6 |

## Placed but NOT seen

Everything above except the walk numbers is geometry and readback. The plaza, its terrain cut,
the Kotel plaza, the approaches and the sanctuary have no visual acceptance at all.

## Open, in priority order

1. **Vegetation materials.** 225,780 instances currently render as engine-default grey — the
   most visible defect in the shipping build. In progress.
2. **Anti-repetition on the walls: reverted.** Comb energy had gone 1.000 → 0.447, but the
   material was accepted under `-nullrhi` and had never drawn a pixel; an in-frame control later
   measured it dropping detail 3–4 mips, which on the ashlar means losing the drafted margins and
   proud bosses. The fix is written (`-AntiRepeatSampling=implicit`) and `do_apply` now REFUSES a
   non-default build receipt without frame evidence. Needs one frame.
3. ~~**Gate-stair yaw defect**~~ **FIXED** (e178fb97). Treads now run across the direction of
   travel: widthDotTravel 1.0 → 0.0 on 205 east and 10 west modules, spacing unchanged at 96.0 cm.
4. ~~**Approaches not wired to the state toggle**~~ **WIRED** (e178fb97). 1 visible in YECHEZKEL,
   0 in MODERN and OVERLAY, on both maps, with the other five tag families re-counted for
   regression.
5. ~~**No collision or navmesh**~~ **11 Sep: approaches and deck WALKED in the packaged build** (AGENTS.md
   collision pass). Kotel plaza walked on both levels in cp22b after a runtime fix (SetTaggedActorCollision, see AGENTS.md). No navmesh exists
   or is used by any system. Original note: no collision on the Kotel plaza or the approaches, so the crowd system cannot
   path over either — people cannot walk up the stairs they were built to walk up.
6. `resident-routes-v2-verify` has still never run on the shipping map (needs real RHI).
7. Soundscape adoption — blocked on a human listening to 29 files.
8. Rig geometry: the leg is 6.9 cm short (0.457 of stature against the generator's own 0.53), and
   the sandal sole carries no weight on `ball_*`, so the toe rocker pivots on the tip. Both cap
   how good the walk can get and both change the body, not the animation.

## Rules added tonight, both now enforced rather than remembered

- **A material is not accepted until a frame shows it**, with an in-frame control on the
  unmodified parent. `-nullrhi` is what makes a build possible on this box and what makes it
  unverifiable; state both halves. (`AGENTS.md`)
- **Never put author-written HLSL between per-instance custom data and the output.** It is
  hoisted into the vertex stage where a non-instanced factory has no instance data, and the
  shader compiler crashes with an access violation rather than failing cleanly. This blocked all
  packaging for hours. (`EnclosureMath.h` §6b)
- The parity gate counted receipt *existence*, so two crash reports cleared a warning without the
  pass running. It now requires a status that says the work landed. (`scripts/verify.py`)
