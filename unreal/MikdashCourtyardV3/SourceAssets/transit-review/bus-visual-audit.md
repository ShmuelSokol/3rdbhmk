# Release bus visual audit

Reviewed actual `../visual-review/release-capture-20260907T211742Z/h_bus_street_level.png`. The bus is dark gray with a visible fine grid on lower panels and large triangles on windows. This is not visual acceptance. Bright surrounding surfaces do not establish the bus lighting or material is correct.

## Actionable diagnosis

`Scripts/create_transit_assets.py::run_native` combines original OBJ groups into one mesh per palette entry, then calls **only `mesh.set_material(0, ...)`**. Multiple native slots, if produced by that import, therefore leave the other groups with their import defaults. The image's gray grid suggests that possibility strongly; it is not yet confirmed by a native material inventory. Inspect all 13 mesh components and every effective slot before changing normals or lighting. The accompanying helper does this and records the actual slot paths.

Expected materials are `/Game/MikdashV3/ArrivalReview/TransitV2/Materials/M_TransitV2_<palette>`. IvoryPaint is base color [0.78,0.75,0.65], metallic0.25, roughness0.28; TealPaint [0.025,0.19,0.20], metallic0.3, roughness0.3. Glass is translucent, opacity0.18, base [0.16,0.28,0.32], metallic0, roughness0.08. These are original artistic paint values, not manufacturer specifications.

## Winding and faceting evidence

Offline validation checks all 13 frozen imported OBJ hashes, 26,880 triangles, explicit face normals, and UVs. Minimum dot between OBJ right-handed geometric face normal and supplied normal exceeds0.9999999993; UV triangle area is nonzero. `create_arrival_assets.py::write_obj` reflects Y and reverses winding together before constructing the normals, matching its documented legacy importer adapter. Do not apply the GeometryScript left-handed winding rule directly to these pre-import OBJ files. Native winding and normal-buffer validation remain pending if material repair does not resolve the image.

The generator deliberately exports hard face normals (`s off`) and per-face UV seams. Tires have64 angular segments; their faceting is a distinct modeling limitation. Flat window polygons should not exhibit changing flat normals inside a coplanar fan. The visible grid and triangles could come from import-default material rendering; this is a hypothesis pending the native slot audit. No blanket face flip or mesh smoothing is implemented.

## Road contact

Current source tire centers are X ±360, Y ±108, Z50cm, radius50cm, local minimum Z0. Tires extend across Y94..122cm on each side. Placement probe Y±96 lies inside tread width but is not a complete inclined-tire contact analysis. Source candidate1 is Batei Mahase, XY[-37951.473,46854.779], yaw-15.979516, road crossfall5.649 degrees and gradient3.141 degrees. Plane placement deliberately pitches/rolls the whole assembly.

The earlier `native-placement-20260907T173220192861Z.json` reports approximately0.10cm engine probe error but status `failed_placing_map_unchanged`; the next receipt remains `running` with no pose. Neither establishes current saved wheel contact. The image suggests a rear-wheel gap, but shadow and slope do not provide a metric. No bus lowering is justified yet. The new audit records current numeric pose and collision profile. Root should trace the actual transformed tire lower vertices in PIE against the asphalt after the material pass; commandlet traces are not valid evidence. Boarding remains unsupported.

## Guarded helper

Offline: `py -3.8-64 Scripts/release_bus_visual_audit.py --offline`.

In a root-controlled dedicated Unreal editor, execute the file with a named scope, then call `native(apply=False)`. Example: `scope={'__file__':r'C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_bus_visual_audit.py','__name__':'bus_audit'}; exec(compile(open(scope['__file__']).read(),scope['__file__'],'exec'),scope); scope['native'](apply=False)`.

Only if the receipt shows mismatches, call `scope['native'](apply=True)`. It checkpoints the source main/protected maps and all TransitV2 assets outside the project, creates the unique `/Game/MikdashV3/MaterialReview/BusVisualAuditV1/Maps/Walkthrough` review map, and changes only mismatched **component** slots to the matching existing palette material. It preserves each bus mesh, numeric transform and collision profile, saves/reopens the review map and checks readback. It never edits native meshes, materials, main map, exposure, or lighting. Existing review destination and dirty packages block application. Exceptions preserve partial review work and write a failure receipt. Root handles any cleanup/retry; the helper does not overwrite partial maps.

Receipts go to `SourceAssets/transit-review/bus-visual-audit-<UTC>.json` and contain all protected before/after hashes, material inventory and correction evidence. If all effective slots already match, no correction is made: next inspect native normals, material compilation readiness and opaque/translucent rendering, not global exposure. Native execution and visual acceptance remain pending. Recapture at the actual saved bus pose with identical lighting/readiness, checking visible ivory and teal, transparent glazing, coherent panel normals and all four tire contacts.
