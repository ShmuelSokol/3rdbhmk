# Handoff to Astra — 8 September 2026, evening

Written by Claude (Fable 5.1) at the moment an account-wide session limit (resets 9:10 pm
New York) killed five agents mid-work. Read this, then `HANDOFF-FOR-ASTRA.md` (this morning's,
still valid for traps and rules), then `INTEGRATION-QUEUE.md`.

Last pushed commit before this file: **9f3b5404** on ShmuelSokol/3rdbhmk main. Editor target
compiled green at 18:27 (Build-W12-12.log) including the east-gate cinematics.

## FIRST THING — verified at handoff, no action needed

One killed agent had been about to edit `Scripts/release_place_assets.py`, the shared
placement helper nearly every release script imports. I checked immediately after the kill:
**the helper is byte-identical to commit 9f3b5404 — it was never written to** — and all seven
scripts the killed agents were touching (`release_place_assets`, `release_gate_security`,
`release_water`, `release_sky_tod`, `release_resident_bodies_v3`, `release_surface_detail`,
`release_soundscape_v2`) parse under the bundled Python. So nothing is half-written. Still run
`python scripts\verify.py --quick` first, as always; the shared-helper change described below
remains TO DO, cleanly, from scratch.

## Pacing — still the rule that matters most

Two limit outages in one day, each killing 5-14 agents. Run 3-5 agents, not more. Let a
wave finish before the next. Commit as things land (everything below that says "committed"
survived because of that). Exhausting the window is not speed.

## State of the maps

**Main** `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`, hash **bc4aa9e0…** (after
the Kohen service). Placed and saved today, all `visual acceptance pending`:
- Approved paroches V15 at the Kodesh opening (old curtain hidden, not deleted). Confirmed in
  a real PIE frame: right way up, correct colours.
- Yechezkel 3,000-amot precinct wall, default state Yechezkel, 279 actors hidden by
  visibility. **BUT SEE THE OPEN DEFECT BELOW — it does not render at runtime.**
- Limestone V3 on 1,490 wall components (accepted from a PIE frame at walking distance).
- Crowd tint fix: 8-colour muted palette, skin and wrap materials per slot.
- Transit: 7 routes, 15 stops, vehicles on traced road surface. Runtime acceptance pending.
- Four bird flocks. Gate security (90 actors, saved; its post-reopen check misfired on
  runtime-constructed actors — the actors ARE in the map). Kohen Gadol service actor.
- Residents: routes V2 verified in PIE, 24 of 24 spawn and walk, all legs clear.
- Water normal texture asset imported (T_Water_Normal); water itself NOT placed.

**Candidate 48 cm** `/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough`,
hash after the Aron re-pivot **ae363a2c…** (further saves may have moved it; check receipts).
Placed today: paroches V15, precinct wall, and the **Aron re-pivot applied**: 2,917 actors
translated (-248, 0, 0) and FixedArchitectureOriginCm set to (-6200, 0, 0), so the Aron sits
over the Dome of the Rock on both maps (main was already within 1 m). Shmuel's instruction.

## Shmuel's decisions today (all recorded in memory and receipts)
- Amah = **48 cm**. Build the precinct **exactly as Yechezkel states** (3,000 amot, default
  view). **The Aron directly over the rock in the Dome of the Rock** — done on both maps.
- He wants the enclosure explained by a map, not a question: published at
  https://claude.ai/code/artifact/9714b10f-8943-4bc2-b6e9-03b56b07cea8 (OSM tiles, correct
  units). Coverage is the eastern ~40% of the Old City plus Kidron, Olives slope, City of
  David, Silwan; about 1,914 buildings inside. He does not want to be asked questions; show him.
- 24 flagged Hebrew strings were sent to him (needs-author-review.json); awaiting his edits.

## OPEN DEFECT 1 — the precinct wall does not render at runtime

Two PIE frames 40 m from the east gate (a 30 m gate) show terrain and sky only:
`SourceAssets/visual-review/lighting-v3-20260908T220658Z-varA__A_relief_local_exposure__v7*.png`
and `v8*.png`. The actor builds its HISM instances in BeginPlay (RebuildPrecinct) with no
OnConstruction and no opt-in flag. Candidates: mesh assets not resolved by path so HISMs have
no mesh; instance Z from an empty ground profile; component hidden-in-game; material lacking
`used_with_instanced_static_meshes` (MI_PBR_LimestoneAshlar); actor state starting Modern.
The enclosure agent was writing `Scripts/diagnose_enclosure_runtime.py` (a PIE probe dumping
the actor's own readback API: GetPrecinctState, GetInstanceCounts, GetOuterFacesCm,
GetWallBaseZRangeCm, GetGroundProfileStatus, GetHideListResolution, per-HISM mesh/material/
visibility) when it was killed. Check whether the file exists; finish or write it; run it.
Do not trust the receipt's "saved, reopened" for anything built at BeginPlay.

## OPEN DEFECT 2 — the blown-out Ulam facade and Kodesh partition (measured, fix ready)

Lighting agent's census: the Ulam facade union mesh SM_2630 carries
`M_StonePilot_Vertical_Pilot01_blue` (albedo 0.69, 1.2 stops brighter than the limestone,
skipped by the PBR pass); the Kodesh partition SM_0142-0144 carries `M_Sanctuary_gold` at
roughness ~0.34, a near-mirror reflecting the sunlit court. Local exposure (variant A) gained
only 11-18 luma levels. **Variant C** swaps both on component slots (facade to
MI_PBR_LimestoneAshlar; partition to a new matte gold, RoughnessScale 2.1). Commands are in
the lighting agent's last report and `Scripts/release_lighting_v3.spec.json`:
capture C with `-LightingV3Variants=C_facade_partition_materials -LightingV3ReuseBaseline=<213613Z receipt>`,
look, then `release_lighting_v3.py -LightingV3Apply=C_facade_partition_materials`, then
`-LightingV3Verify`. Also run the `base78` command for the two east-gate views.

## Ready to run (scripts fixed by their authors; not yet re-run)
- `release_soundscape_v2.py` (readback of unreal.Array fixed; self-heals two leftover assets).
- `release_intro_sequence.py -IntroReplace` — intro now enters through the precinct east gate
  per Yechezkel 43:1-4; compiled green. 68 s, gate clearance 243 cm, arrival 0.0 cm.
- Resident bodies V3: compiled green; `-BodiesApply` refused on a package-path vs object-path
  string compare of the skeleton (`…_Skeleton` vs `…_Skeleton.V3_Pilgrim_Man_Elder_Skeleton`)
  in `Scripts/release_resident_bodies_v3.py` — the population agent was fixing it when killed.
  Fix that compare (compare by object or normalise both), rerun apply on candidate then main,
  then `-BodiesVerify` (PIE). Its candidate verify against V2 fallbacks showed 23/24 spawned,
  Chananel skipped, 0 moved — establish whether "0 moved" is a verify artefact or a real
  regression from the Aron re-pivot before trusting the candidate.
- Water: `Scripts/release_water.py` failed on `Material.Expressions` being protected in 5.8
  (its leftover-material clearing counts expressions). Use
  `MaterialEditingLibrary.get_num_material_expressions` or skip the count. The live host
  identification fix (architecture_ prefix) is in and self-tested. Spec hash needs bc4aa9e0…
  with provenance.
- Sky/time of day: `release_sky_tod.py` refuses "Open integrated map before placement" — it
  must load the map itself like every other commandlet script. Fix, then run.
- Decals (`release_surface_detail.py`) and gate security `-Verify`: blocked on the
  shared-helper fix below.
- Vegetation: `release_vegetation.py` in batches (697), never run. Bridge:
  `release_transit_bridge.py` after transit (placed) — never run.

## Shared-helper fix (the killed edit)

Both `release_gate_security.py` (after save) and `release_surface_detail.py` (before save)
refused on "pre-existing actors changed": `Actor_0..Actor_4`, `MikdashCrowdField_0`,
`MikdashBirdFlock_0..3`. These are runtime-constructed changes (transient load-time actors,
HISM previews rebuilt on construction), not damage. Intended fix, once, in
`release_place_assets.py` Placement snapshot/baseline: exclude actors flagged transient or not
owned by the map package; compare HISM actors by existence and root transform, not instance
counts; keep refusing on genuine persistent-actor changes; add the exact churn set as a
regression case. Verify the file parses before anything else (see FIRST THING).

## Traps learned today (add to the morning list)
- The OSM export is in AMOT with a baked alignment; the inventory `assetName` drops the
  `architecture_` prefix the real assets carry; specs pin map hashes that go stale after every
  save (update with provenance, never blindly).
- UE Python: `bRail` is `rail`; `MaterialExpressionPerInstanceCustomData` has
  `const_default_value`; `Material.Expressions` is protected; enum readback needs `.name`, not
  `str()`; `unreal.Array` is not a list. UE stores skeletons depth-first — compare bone sets.
- Interchange OBJ import makes one mesh per `o` group unless the pipeline is overridden to
  combine; it adds a folder level named after the file; imported PilgrimRigV3 faces +Y (yaw -90).
- Long editor jobs: launch DETACHED (`Start-Process`) and watch by PID with PowerShell; the
  harness memory guard kills shells and their children. PIE probes require the isolated
  `-TestSavePrefix=FableProbe_<stamp>` + Game ini overrides or they refuse.
- Editor-world captures (`run-release-capture-views.py`) cannot show anything built at
  BeginPlay; use the PIE capture (`lighting_capture_v3.py`) for enclosure, crowd, residents.
- Yechezkel 40:5: the precinct wall is one reed high (6 amot, ~3 m) — a hairline from a
  kilometre; judge it at a gate.

## What "done" means
Unchanged from the morning: everything present looking deliberate, nothing obviously wrong,
every claim traceable with its confidence label. Codex 76 entries: 33 certain, 33 disputed,
10 authored. Never promote an authored claim to a sourced one. No cook has been produced
today; nothing here is a release.
