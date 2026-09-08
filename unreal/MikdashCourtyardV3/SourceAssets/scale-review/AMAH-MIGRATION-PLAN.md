# Selected 48 cm amah migration â€” foundation only

The user explicitly approved using the book-selected **48 cm amah** and asked for exact dimensions. That choice is not awaiting permission. It is the project's selected interpretation, not a claim that all opinions agree. The active scene remains at the legacy **50 cm architecture scale** until a coordinated migration is verified and accepted. This foundation changes no existing runtime defaults, source decoders, native assets or maps.

## Evidence and invariant

`SourceAssets/architecture-manifest.json` records 2,633 meshes, 52,511 vertices and 86,760 triangles, imported from source amot by `[x*50,z*50,y*50]`. World coordinates are baked in mesh vertices; original actor transforms are identity at origin. The expected bounds are `[-8100,-9450,0]` through `[9200,9450,6129.999923706055]` cm. At .96 they become `[-7776,-9072,0]` through `[8832,9072,5884.799926757812]`. The tiny noninteger height is retained mesh precision, not a new measurement.

`architecture-current-inventory.json` verifies the older `/Game/MikdashV3/Maps/Courtyard`, not the currently integrated map. Root must enumerate active actors and reconcile native mesh identity, transforms, attachments and overrides before constructing the migration allowlist. Do not blindly replay an old inventory.

New `MikdashUnits.h` has explicit legacy50 and selected48 constants, amah/tefach helpers, transactional point conversion about a supplied fixed origin, and floor placement with an unscaled physical height. Nothing includes it into active behavior in this batch. No global `ActiveAmah` alias silently changes the world.

## Architecture-derived geometry and placement inventory

- **Base architecture:** exact manifest mesh identities, including walls, courts, floors, steps, gates and sanctuary. Scale once about the confirmed Temple reference origin; preserve triangle counts, material identities and collision settings. World-baked meshes can use actor transforms in a duplicated candidate map; shared assets need not be rewritten.
- **Sanctuary additions:** doors/paroches, gold veneers, keruv/palm relief and friezes fitted to walls. Inspect `release_import_doors.spec.json`, `release_keruv_frieze.spec.json`, `release_frieze_v2.spec.json` and their source manifests. Their room-relative positions, fitted dimensions, masks and wall tolerances must agree with the resized shell.
- **Vessels:** inspect active mesh identities before choosing among older studies and current models. `SourceAssets/vessels-review/KeilimTIV1/geometry-manifest.json` expressly uses amah50, tefach8.3333, and five-tefach amah41.6667. Its book table100x50x150 becomes96x48x144cm; five-tefach altar41.667x41.667x83.333 becomes40x40x80cm. Apply this to the corresponding active assets/placements through `release_import_keilim_ti`, `release_scale_keilim`, shulchan/menorah/Aron specs. Sizes derived from book ratios scale; independently measured physical props require their own metadata, not an automatic .96 pass.
- **Book enclosure:** `EnclosureMath.h::ProjectCmPerAmah=50` and `create_enclosure.py` use the old unit. The latter also hard-codes1250cm module/overlay spacing for25amot; changing the constant alone misses these. Update `release_enclosure`/`release_import_enclosure` specs and regenerated instance origins/lengths. A3000-amah side becomes144000cm. Keep the modern mapped Mount boundary separate.
- **Water:** `WaterFlowMath.h::ProjectAmahCm`, prescribed channel dimensions/distances and `create_water_geometry.py`/`release_water.spec.json` need explicit selected units. Geographically surveyed water/terrain anchors, where present, stay metric; reconnect the authored stream rather than shrinking the geographic terrain.

## Runtime and mixed-unit dependencies

- Resident support planes/routes: `ResidentRouteLoop.h::FloorZ=300`, `MikdashResidentPopulation.cpp` positions, extended-route plans and attached actor placement. Outer-court support Z300 becomes288; capsule half-height96 stays96, so centreZ396 becomes384, **not380.16**. Eye height, speed, radius, gravity and physical margins stay metric.
- Crowd zone/keep-out polygons: migrate only Temple-derived zones in `SourceAssets/runtime-review/crowd-field/zones.json` and `release_crowd_field.spec.json`; leave geographic street/plaza zones fixed. Regenerate their ground references and review boundaries used by the transit coordinator.
- Preparation/access/security/service: reconcile actual native bounds and semantic waypoints in `PreparationJourney.h`, `MikdashGateSecurity`, `MikdashServiceActor`, `release_gate_security.spec.json` and `release_kohen_service.spec.json`. Ritual state does not change with geometry; its spatial triggers do.
- Camera/tour: `MikdashCinematics.cpp`, `MikdashTourGuide`, and `release_tour.spec.json` contain architecture targets. Move room/door targets with architecture; preserve lens FOV and physical eye/clearance offsets. A literal48-degree FOV is not an amah constant.
- FX/audio: `MikdashFXDirector` room bounds, source anchors and ceiling constraints; `release_fx.spec.json`; `MikdashSoundscape` room/portal/ground bounds and `release_soundscape_v2.spec.json`. Migrate architecture-bound anchors/extents. Preserve physical wind/particle speeds, loudness, rates and optical parameters. Geographic emitters remain fixed.
- Save positions: `SaveMigrationMath.h` documents the historical50cm source decoder. Keep this decoder and introduce a distinct scene/unit migration version. Temple-relative support locations can migrate with floor revalidation; saved geographic positions cannot be multiplied blindly. Preserve prior saves and refuse ambiguous placement or use a documented safe spawn while preserving progress.

## Explicitly excluded from blanket scaling

Modern Jerusalem/OSM buildings, roads, terrain, Kotel/plaza and photograph panels, mapped Mount perimeter/deck/terrain cuts, city facade details, geographic vegetation placement, vehicles and their metric routes, human/bird meshes, capsules and movement parameters remain real-world sized. The context importer alignment is already baked from `[17.509700315687695,0,-0.5513496449385334]` source-coordinate offsets. `import_buildings_ue58.py` and `import_instances_ue58.py` validate that bake. Their historical50 conversion is not the selected architectural amah and must remain unchanged.

Connections between the resized Temple and fixed geographic Mount/plaza must be regenerated locally (stairs, transitions, route ends). Do not shrink the entire FutureMount deck or protected Kotel geometry to force alignment. Moving a character's Temple-relative feet does not authorize shrinking its body or moving an independently geographic character location.

## Materials

`release_pbr_architecture.spec.json` explicitly computes triplanar UVs from WorldPosition/TilingCm. Keep physical texture grain/photographic tiling sizes, roughness, metalness and colors. Architectural block courses or relief dimensions expressly based on amot scale separately. Surface masks/bounds following the Temple need matching coordinate updates. Do not mutate shared context materials just because the target actor belongs to the Temple.

## Minimal safe execution and verification

1. Capture current main-map and dependency hashes and a native actor/component inventory keyed by stable actor names plus mesh identity. Checkpoint map/config/unit-dependent sources and any assets that will change. Produce an exact allowlist classified as architecture, metric-context or mixed support-plus-offset; reject ambiguous entries.
2. Duplicate the active scene to a unique48cm candidate namespace. Apply `origin + .96*(point-origin)` only to approved architectural coordinates; scale local geometry dimensions once, respecting attachments. Rebuild mixed placements from migrated support points plus unchanged physical offsets. Preserve source manifests as legacy evidence and write a new versioned expected inventory.
3. Update dependent specs/runtime coordinates in a coherent batch. Keep the default main map legacy50 until candidate verification passes. No half-migrated default scene.
4. Save/reopen: check measured bounds and exemplar dimensions, exact expected actor/mesh/triangle counts, child attachment behavior, material/collision readback, context transforms and protected file hashes. Check selected48, legacy50 and five-tefach conversions independently.
5. In actual gameplay: floor/doorway/capsule traces, stairs and fixed-context connections, resident and transit routes, preparation/service triggers, tours/camera framing, FX ceilings and acoustic boundaries. Test pause and versioned saves, then cook and test the candidate executable. Visual comparison and source accuracy remain separate acceptance gates.
6. Roll back by restoring the checkpointed coherent map/config/source set; original/shared geometry stays untouched when possible. Retain candidate receipts and failures. Root owns native execution, adoption and publication.

Standalone tests cover dimensions, a nonzero fixed origin, axis ordering, unscaled capsule/eye offsets, double-scaling prevention, unchanged metric context and transactional invalid/overflow refusals. Passing these tests proves helper math only; it does not prove the active scene has migrated.

## Foundation verification result

Compiled `Plugins/MikdashRuntime/Tests/MikdashUnitsTest.cpp` with installed MSVC using `/std:c++14 /EHsc /W4 /WX`, including the plugin Public directory. The standalone executable returned exit0: **26 checks, 0 failures**. Compiler artifacts were written under the existing `Intermediate/TransitCrowdStandalone` directory. No Unreal/UBT, native map mutation or publishing occurred. Only the new header, test source and this plan are source deliverables.
