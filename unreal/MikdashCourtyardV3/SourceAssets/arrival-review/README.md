# Original modern arrival study

BusStudyV1 is an original editable exterior mesh authored for this project. It has a formed roof/HVAC unit, curved tire profiles and tread, machined-style rims and bolts, lower body wheel openings, two twin-leaf doors, glazing, mirrors, lamps, markers, wipers, vents, bumpers and blank destination/plate panels. The ivory/teal livery is an artistic choice with no operator or manufacturer branding.

The depth-buffer PNG was inspected offline: the exterior reads as a modern bus, with doors, wheels and fixtures distinguishable. This is a first exterior study, not an accepted production vehicle. The PNG uses simple diffuse shading; it is not an Unreal screenshot. Native appearance, reflection response, collision, LODs, wheel motion, steering, passengers, opening doors and performance are unverified. Glass is intentionally opaque and there is no cabin/interior. The underfloor is simplified. Flat per-face normals may show faceting in native close views. No headlights emit light. No destination text implies an actual route.

## Rights and source distinction

- Geometry, palette and preview code were authored parametrically in this task; no downloaded model, texture, manufacturer CAD, trademark or licensed third-party mesh was used. No additional third-party asset license is introduced by the bus.
- 12.095 m length, approximately 2.50 m body width, 3.44 m mirror envelope and 3.318 m height are authored dimensions, not a certified road-legal specification or measured vehicle replica. Tires contact local Z0. Forward is local +X; door side is +Y; all units are centimeters.
- Existing source context is retained OpenStreetMap-derived project data. The placement document records its hash/date and references only a road segment. Keep the project's OSM/ODbL attribution. No assertion of current access permissions, bus route service, site suitability or future surveyed infrastructure is made.

## Reproduce and import

Offline creation: `python Scripts/create_arrival_assets.py --export`. The version guard refuses to overwrite this frozen study. Geometry is indexed in `BusStudyV1/bus-editable.mesh.json` and recoverable by named part/material; `bus-canonical.obj` is a DCC-editable canonical Unreal-XYZ export. Material colors are in `offline-checks.json`. The nine `SM_BusStudyV1_*.obj` files are native-only reflected-Y/reversed-winding legacy adapters with explicit normals and nondegenerate triangle UV charts; do not apply another Y reflection or unit conversion.

Root may load `Scripts/create_arrival_assets.py` in the correct idle Unreal editor and explicitly call `run_native()`. It imports nine material-group meshes plus nine original materials into `/Game/MikdashV3/ArrivalReview/BusStudyV1`, checks native bounds and triangle counts, saves only those assets and writes `BusStudyV1/native-import.json`. It never changes a map, spawns actors, launches an engine, deletes an existing namespace or commits. It refuses dirty editor work/existing namespaces; inspect preserved partial assets before retry after failure. **Native execution has not been performed here.**

All nine meshes share the same local origin. To assemble, root must use identical translation/rotation/scale for all groups, preferably nine static mesh components in one owned actor. Source vertices already contain vehicle-relative offsets. The helper adds no collision; root must select a reviewed collision proxy before making the vehicle navigable. Never use the detailed tread triangles as a moving vehicle collision solution. This combined export is a static display bus; a wheel/door rig must be generated from the named canonical parts for motion.

Offline preview: `python SourceAssets/arrival-review/render_offline_preview.py`. Standard-library depth-buffer rendering needs no Blender, paid service or GUI. `geometry-preview.png` is the authoritative offline preview; SVG wraps the PNG and adds its status caption.

## Arrival and proposed station scope

See `arrival-placement-spec.json`. The bus candidate is aligned to a real retained-context road segment south of both the inferred Mount enclosure and protected Kotel/plaza polygons. Its full rotated horizontal envelope is checked against their conservative bounding boxes plus the preserved 200 cm no-edit buffer. This proves horizontal separation only. Ground Z, road width, gradient, surrounding buildings, traffic, headroom and standing geometry are unknown until root traces and inspects the native scene; no automatic placement is supplied.

Future transit layout is an authored proposal. Reserve paved bus lanes/bays separately from cobblestone pedestrian approaches, with a smooth step-free pedestrian strip, raised curb/boarding transition, protected crossing and vehicle swept-path checks. The illustrative train/station module has no accepted world placement, geometry, timetable or operational rail route. Neither bus nor rail may enter the enclosed Mount or alter protected Kotel/plaza geometry. Complete the bus native review before building the station/train.
