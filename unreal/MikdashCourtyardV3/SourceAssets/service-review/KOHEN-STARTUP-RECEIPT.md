# The Kohen Gadol is in the shipped build (cp12). Frames, and what is still wrong.

Generated 2026-09-10 (local evening) by `Scripts/release_kohen_startup.py` + the cp12 packaged build
`C:\Mikdash\Builds\Checkpoint-cp12-20260911T001633Z` (status `checkpoint_playable`, Candidate48 map).
Not committed.

## Why he was absent, and why he had been switched off

`AMikdashServiceActor::ResolveBody()` runs only from `StartService()`; `BeginPlay` calls that only when
`bStartOnBeginPlay && bSequenceEnabled`. `bStartOnBeginPlay` was false on both maps. It is `EditAnywhere`
(per placed instance), not `config`, so it could only be fixed on the actor. No C++ change was needed.

It was off **deliberately**: "Placement and configuration only ... nothing animates before a visual review"
(`release_kohen_service.spec.json`), then kept off by `grounded-full-review-20260909.json` and
`grounded-service-visual-review-20260909.json` for **visual** findings: 7 stair centre-foot mismatches,
stand-in garments, idle hands with no lamp interaction. None was a crash, a refused route, or a walk through
geometry (18/18 stations, 0 blocked legs, 0 endpoint capsule hits). Those findings are now re-exposed on
purpose and listed below. They are not hidden.

## What changed (both maps, kohen actor only)

| | Candidate48 `RELEASE_KohenGadolService_Selected48_V1` | Main50 `RELEASE_KohenGadolService` |
|---|---|---|
| `start_on_begin_play` | false -> **true** | false -> **true** |
| `sequence_enabled` | true (unchanged) | true (unchanged) |
| `configured_mesh` | V3 Man_Standard (unchanged) | null -> **V3 Man_Standard** |
| `configured_body_yaw_degrees` | -90 (unchanged) | 0 -> **-90** |
| `idle_animation` | V3 idle (unchanged) | null -> **V3 idle** (the clip the hardcoded fallback loaded) |
| walk clip / speed | WalkV2 / 119.95 (unchanged) | WalkV2 / 119.95 (unchanged) |

Why Main50's body was pinned: with no mesh set, `FindBestMesh` scans `/Game/MetaHumans` **before** the
hardcoded `MeshFallbacks[0]`, and that folder has held `MH_Elder_Kohen` since another agent's MetaHuman
build (10 Sep 23:55Z). His body on Main50 would have been whatever that scan loaded. Now both maps resolve
the same body and idle, explicitly. The `AuthoredBody` refusal is kept in `release_walk_v2_finish.py` and
repeated in this script.

Receipts: `kohen-startup-apply-Candidate48-20260911T000145167148Z.json`,
`kohen-startup-apply-Main50-20260911T000459976796Z.json`, the revert that was actually run
`kohen-startup-revert-Candidate48-20260911T000923761482Z.json` (read back `start_on_begin_play=false`), and
the re-apply `kohen-startup-apply-Candidate48-20260911T001241003987Z.json`. Each run checkpointed the map
into `ReviewCheckpoints\KohenStartup-*`, and each saved, reopened and read back. Other map bytes unchanged,
`protectedChangedExcludingThisMap` empty. The cooked map hash `db6db904...` equals the re-apply's `mapAfterSha256`.

## Frames (packaged cp12, `-dumpmovie -benchmark -fps=10`, 0.1 s of game time per frame)

Camera `BugItGo -5250 -90 1070 -8 80 0`: side-on, about 4 m from the three-step stone. 1123 frames, i.e.
112.3 s of game time from world start. The folder keeps f240-f300 contiguous, plus every 25th frame.

* `visual-review/cp12-kohen-tending-lamp1-4m-t37.5s.png`: **the headline.** He stands on the stone at the menorah,
  about 4.1 m away (about 435 px tall at 1080p).
* `visual-review/cp12-kohen-on-stone-at-menorah-t29.0s.png`: arriving on the stone.
* `visual-review/cp12-kohen-walk-in-and-step-up-sheet.png`: t 24.6-29.0 s, walking across the Heikhal and climbing the stone.
* `visual-review/cp12-kohen-footplant-proof-3-stances.png`: world-fixed 3x crops of three stances.

**Feet.** In three consecutive stances (f252-254, f258-260, f270-272) the planted sandal holds the same
pixels for 0.2 s (±1 px, about ±0.4 cm) while the robe hem sweeps across it. Patch cross-correlation at
f258 gives dx 0, dy 0 at +0.1 s and (-1, +1) at +0.2 s, and the flagstone control holds 0, 0 at residual 0.2-0.4.
This is the same signature as the residents: the 1.49x skate is gone in play, not just in the data. Limits:
the plant is only visible about 0.2 s per step before the hem or the swing leg hides it, and 70x44 patches that
include the hem are unreliable here (two anchors landed on the swing foot).

## What is wrong with him, exactly

1. **He does not light anything.** From t 33 to 78 s he stands on the top tread in the idle pose, arms at
   his sides, shifting a few cm and turning between lamp stations. No hand goes to a lamp. **All seven
   flames already burn before he arrives** (empty frame at t 23 s), so nothing is kindled on screen.
   "Lighting the menorah" is only in the action text.
2. **Menorah scale versus figure and stone.** Standing on the stone, the lamps are at his hip. He looks
   down at them, where he should be reaching up or level. The menorah reads at about 1.37 m against his 1.8 m.
3. **Garments.** A white robe with a teal front panel and a gold belt: the stand-in, not the eight
   golden garments. Mid-stride the trailing bare shin pokes out through the robe. A dark orange square
   (the robe's back face) shows at the front shin, and the over-tunic edges are aliased cutouts.
4. **Stair step-up** (the 7 centre-foot mismatches) is visible in the sheet, but was not measured frame by frame here.

## Knock-on effects

* These scripts assert the service is OFF and **will now refuse** on these maps, which is expected:
  `probe_transit_bridge_runtime.py`, `probe_candidate_kotel_access.py`, `probe_candidate_metric_birds.py`,
  `probe_candidate_transit.py`, `probe_enclosure_collision_restore.py`, `probe_service_candidate48.py`,
  `configure_candidate_grounded_service.py`, `configure_service_body_v3.py`.
* `release_walk_v2_finish.py -FinishRevert -FinishTarget=Main50` now refuses, because Main50's
  `configured_mesh` differs from its apply receipt. Revert this pass first (`-KohenStartupRevert -KohenTarget=Main50`).
* Main50 was **not** cooked or captured. Its kohen runs in the non-grounded mode (`use_grounded_movement`
  false), which carries the "station XYZ interpolation ramps over flat floor" defect from
  `grounded-route-plan-20260909.json`.

To undo: `-KohenStartupRevert -KohenTarget=Candidate48|Main50` (hidden editor, one engine at a time).
