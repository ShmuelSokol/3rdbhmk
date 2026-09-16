# Handoff — 16 September 2026, 03:00 UTC (Claude session ends here)

Written for whoever picks this up next (Codex/Astra expected). Everything below is either a
receipt-backed fact or an explicitly flagged open question. Where a claim is not proven, it says so.

## 1. What to open

**Playable builds, newest first.** All are `checkpoint_playable` with a passed smoke test:

| archive | contains |
|---|---|
| `Checkpoint-plateau-S4c-*` (see `SourceAssets/enclosure-review/HideSetV1/`) | **221 Old City buildings restored around the Temple**, plaza deck off, split cells placed |
| `Checkpoint-plateau-S0-20260916T055906Z` | insurance build taken before any plateau mutation |
| `Checkpoint-people02-20260916T053459Z` | Kohen Gadol with the new MetaHuman-derived head, real eyes, grey beard |
| `Checkpoint-streets01-20260916T022910Z` | Old City lane paving |
| `Checkpoint-trees01d-20260916T024213Z` | real trees (foliage fixed) |
| `Checkpoint-kotel01-20260916T003146Z` | Kotel views fixed; no white staircase; dressed retaining wall |

`Checkpoint-cp26-20260915T214343Z` was the first full recook after the McAfee/memory outage and is the
baseline the later archives build on.

## 2. Decisions the owner made this session — do not silently reopen these

1. **The plateau is TODAY'S TEMPLE MOUNT OUTLINE**, the real trapezoid on four mapped OSM walls
   (26554724, 137726908 reversed, 1080613976, 391433907), 14.24 ha, closure gap 0.0 cm. He was offered
   the cheaper 500-amah Middot square, which the code already implements and which keeps a sourced
   number, and chose the real outline anyway. The Yechezkel 42:15-20 3,000-amah sourcing STAYS in
   `sources.md`, recorded as a deliberate departure, never deleted. Both readings remain implemented.
2. **The Kohen Gadol's face is the Walter preset**, baked onto his existing `head` bone. His eight
   golden garments, his 27-bone rig and his three clips are unchanged. He must not be East Asian:
   the old asset was an Aoi duplicate, which nobody had chosen deliberately.
3. **Groom is enabled** and both targets were rebuilt for it (grey beard).
4. **The old 2.07 km2 plaza deck is switched off** (`bBuildPlaza=false`) as the artefact of a replaced
   boundary. Previous value recorded; revert payload on disk.

## 3. Open questions that are HIS to answer, not yours

- **The rock is buried.** At deck datum Z 0 (748 m) the published Even HaShetiya summit (743.70 m
  +/-1 m) sits **4.3 m below the Kodesh HaKodashim floor**. Putting the floor on the rock needs the whole
  Temple 13.6 m lower, which puts the deck 5.6 m below the real esplanade and invalidates the Kotel
  decks and every Z-bearing receipt. The honest alternative (everything lower, rock rising as an
  outcrop into the Holy of Holies, per Ritmeyer) pierces measured architecture from his book.
  Recorded in `HARAM-OUTLINE-20260915.md`. **Do not act on it either way.**
- **Disk**: 71 build archives, ~253 GB, and the drive fell from 89 GB to ~48 GB free in one night. He
  was offered a prune of superseded archives (keeping the published download builds and the recent
  checkpoints, ~150 GB recoverable) and has not answered. Never delete without his word.

## 4. Immediate next steps, in the order I would take them

1. **Fix the Kotel plaza regression (S5, one line, needs both targets rebuilt).**
   `HideWhileWallStandsTags` contains `KotelPlazaCutTwin` (`MikdashEnclosure.cpp:247`). That was correct
   when the 2.07 km2 deck covered the plaza; with the ring boundary and `bBuildPlaza=false` it hides the
   cut twin, uncut terrain returns, and **the Kotel prayer plaza renders as bare dirt with worshippers
   standing on it** (frame `HideSetV1/S4c-K1-*`). Contradicts PLAZA-DESIGN section 7, which says the
   Kotel plaza stays.
2. **S5 proper**: re-plan wall ring, gates, ground profile and plaza on `FPrecinctRing`. The header and
   the standalone test already carry the ring; `create_enclosure.py` and `release_enclosure.py` plan the
   ring hide set but still build the SQUARE wall. Gates should move onto the real mapped Haram gates,
   which upgrades them from authored to sourced. Approaches (696 steps) lose their reason to exist.
3. **The Kohen Gadol's skin and garments.** Priority order agreed with him: head-skin master (normal +
   cavity through the `TEXCOORD_0` already in the shipped GLB, with the pale-neck fix riding along) ->
   garments as one pass (weave, mitznefet as cloth, choshen as real gems) -> the six residents using the
   proven submerged-shell recipe. **Do not re-author the mitznefet before looking at a real frame** - it
   reads better in engine than in any offline preview.
4. **Finish the clearance gates** (idle and tend unmeasured) and fix the tool: it skins 48k head/beard
   vertices per frame for a measurement that only tests shin/foot vs ketonet.
5. **Old City ground**: pave the NEGATIVE SPACE between footprints using the lane network as its spine.
   58.7% of walkable ground inside the walls is still bare earth, and the current paved/unpaved boundary
   is a hard diagonal that reads worse than uniform dirt did.

## 5. Traps learned this session - all in AGENTS.md as hard rules 11-16

- **11** A material saved with an empty graph passes every property check and renders black. Assert the
  expression count and the wired opacity mask.
- **12** Textures imported with `save=False` are live in that session but never written to disk; the cook
  resolves them to nothing. Assert the `.uasset` exists from a FRESH process.
- **13** A UE array property mutated in place writes to a discarded copy. `meshSlotsAssigned: 138` was
  reported while every mesh still wore `WorldGridMaterial`. Read slots back and refuse `WorldGridMaterial`.
- **14** A hash is current only if taken after every other writer finished. Print the timestamp beside it.
- **15** Identical binaries do not mean identical content - compare the archive, not the exe
  (people01/people02 shared an exe hash; the delta was 26,624 bytes of re-cooked mesh).
- **16** An offline previewer that does not back-face cull cannot find an inside-out mesh, and will
  quietly dim every render while you "fix" the symptom.
- **A count that matches is not a thing that matches.** Slicing a cell's triangle list by component order
  produced correct triangle counts, vertex counts and bounds - and would have shipped buildings made of
  other buildings' walls, 80 m out of place. Verify by position or identity, never by count.

**Two engine-memory invariants worth more than any of the above on this 16 GB box:**

- **Load assets BEFORE the map, never after.** `load_asset` on a static mesh with the map resident blocks
  on `FStaticMeshCompilingManager` and drags all 7,860 level meshes through compilation at once. The same
  call with no map loaded is free. This killed seven consecutive runs and was invisible in every log
  except as `Waiting for static meshes to be ready 4,280/7,860`.
- **Launch cooks and engine jobs DETACHED via `Start-Process`, and poll receipts.** The harness watchdog
  kills *tracked* background commands under system physical pressure, and the cook's own log looks
  perfectly healthy right up to the kill (`VirtualMemory=1670MiB` of `28640MiB` available). Also:
  `-asyncstaticmeshcompilationmaxconcurrency=1` is the real flag (`AsyncCompilationHelpers.cpp:306`
  parses `-async<Name>compilationmaxconcurrency=`, `StaticMeshCompiler` registers the name `staticmesh`).

## 6. Known defects, ranked by how badly they break the illusion

1. **Kotel prayer plaza is bare dirt** in the Temple view (new, caused by S4, one-line fix - item 4.1).
2. **The square wall still runs through the restored city** (2.9 m high) until S5 re-plans it.
3. **The Kohen Gadol's garments are flat cartoon shading** around a photoreal head - the mismatch now
   reads worse than the old head did. Choshen stones are flat coloured rectangles.
4. **58.7% of the Old City ground is bare earth**, with a hard diagonal where paving stops.
5. **Massing is one box per plot** - no party walls, no arches over the lane, no depth at openings.
6. **The city stone reads as one wallpaper** - one tile, one tint, one course height citywide.
7. **Plaza retaining walls**: faces read dirty (pitting right in amount, wrong in character), drafted
   margins not visible at 22 m, bed joints too deep. Measurements in `INTEGRATION-QUEUE.md` (V8 section).
8. **Trees**: foliage tint too fresh a green, crowns too sparse, Aleppo pine reads as a broadleaf, and
   **the 1.1 M-triangle OSM placeholder trees still ship** (instances zeroed, meshes still referenced).
9. **200 souq arches and 82 stalls sit 10-45 cm below the new paving.**
10. **Al-Aqsa's label has no actor in Candidate48** - the hide set has always computed 270 and placed 269.
    Nothing renders it, so it is inert, but the cause is unexplained.
11. **An unidentified pale blue-grey slab on the NE horizon** in frame `S4c-C1`.

## 7. Standing constraints

- **One engine or game process at a time.** 16 GB, RTX 2070. Serialise with `SLOT-<pass>-done.txt`
  sentinel files; check for `UnrealEditor`, `UnrealEditor-Cmd`, `MikdashCourtyardV3` and any `dotnet`
  whose command line contains `AutomationTool` or `UnrealBuildTool`.
- **McAfee `mc-fw-host` leaks**, reaching 16.3 GB and blocking every cook between 11 and 15 September.
  A restart is the only fix that works - tamper protection blocks killing it. It was at ~2.5 GB and
  climbing at the end of this session. **Do not run McAfee's "junk files" cleanup**: it would wipe the
  shader cache and force a full recompile.
- **Publication**: commits go from the clone `C:\Mikdash\GitHub\3rdbhmk`. Stage explicit files by name,
  never `git add -A` and never a whole directory. Never publish raw `.log` files, movie frame sequences,
  `__pycache__`, `ParochesFabricV1`, `codex-entries.json`, or private photographs. Maps are copied under a
  hash-stability check and only when a reviewed receipt describes those exact bytes.
- **A material or a fix is not accepted until a frame shows it.** Receipts prove existence, never
  appearance. Three separate cooks shipped cardboard foliage while every property check passed.
