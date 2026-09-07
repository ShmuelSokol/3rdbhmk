# Pilgrim Study V1: original civilian character source

Authored 2026-09-07. This is a concrete editable full-body static character study,
with a long pleated tunic, sleeves, sash, open outer mantle, wrapped head covering,
sculpted head and facial features, separate fingers, covered calves and sandals.
It is a first art-production source, not a finished cinematic person. The two BMP
images show the actual generated geometry through an offline shaded rasterizer;
they are not Unreal screenshots and do not establish native visual acceptance.

## Files and coordinates

- `PilgrimStudyV1-editable.obj` plus `PilgrimStudyV1.mtl`: canonical centimeters,
  Z up, front toward -Y, soles at Z0, cap height approximately 182cm. Named objects
  retain separate garment and anatomical editing regions. Eight material groups.
- `SM_PilgrimStudyV1_*.obj`: native legacy-import adapters, one combined shell
  assembly per material. Y is reflected and triangle winding reversed, following
  the already-tested keilim import convention. All eight share the same origin.
- `geometry-manifest.json`: component topology, exact bounds, triangles and hashes.
- `source-front.bmp`, `source-three-quarter.bmp`: actual mesh reviews.
- `verify_offline.py`, `offline-checks.json`: independent file/adapter checks.
- `integration-plan.json`: resident and animation handoff, with source hashes.

The mesh has 29,592 triangles. Each authored component is a closed indexed shell;
the combined character is deliberately not a Boolean union. Overlapping cloth
and anatomical shells, cap seams and hidden internal surfaces remain. Smooth
vertex normals and face-local UV charts are supplied. The UV charts overlap:
material colors work, but production fabric/skin maps require a real unwrap.
The geometry contains no skeleton, weights, shape keys or animations.

## Offline entrypoints

From the working project, `python Scripts/create_pilgrim_character.py --check`
rebuilds and checks geometry in memory without writing assets. The original export
used `--export`, which refuses to overwrite the frozen source directory.
`python SourceAssets/characters-review/PilgrimStudyV1/verify_offline.py` checks the
delivered source files, native reflection/winding, UV charts and hashes.

## Native import: integrating root only

After resolving other native work, load `Scripts/create_pilgrim_character.py` as
an importlib module inside the intended editor and explicitly call `run_native()`.
It imports only under `/Game/MikdashV3/CharacterReview/PilgrimStudyV1`, checks exact
triangles and bounds to 0.05cm, creates eight study materials, and saves those
assets. It refuses an existing namespace. It never spawns actors or saves maps.
Partial native failures are preserved with `native-import.json`; do not rerun
blindly into a partially populated namespace.

For a static review only, the integrating root can assemble the returned eight
meshes at identical transforms. They must remain an explicitly labeled static
study outside the live population. Keep collision off on the clothing and body
shells; later locomotion uses an appropriate character capsule. Native rendering,
material smoothness, correct handedness, save/reopen, collision and performance
remain unverified until the root runs and reviews them.

## Art review and remaining production work

The source views establish recognizable clothed full-body silhouette, hands and
face; they also expose simplified skin, rigid sash/mantle, uniform fabric and
stylized headwrap/beard. Shoulder mantle joins and garment thickness need further
sculpting. No photorealism, film-quality result or finished population is claimed.
Before close cameras, sculpt ears/eyes/lips and cloth folds, fix all garment seam
intersections, retopologize shared joints, unwrap, bake and author original skin
and textile detail. Rig only after this silhouette/topology review. Test garment
clearance through a full gait cycle; a closed long skirt cannot simply inherit
independent leg weights without stretch and interpenetration.

## Provenance and rights

All delivered mesh positions, faces, garment shapes, facial shapes, material
colors and preview pixels were authored procedurally in this task from original
code. No downloaded mesh, photographic texture, scanned person, paid generation,
recognizable real person, weapon, or third-party costume design is included.
The design is an artistic civilian/pilgrim option, not sourced ancient dress,
kohen vestments, a claim about future clothing, or halachic certification.
The project owner controls publication terms for these new project assets.

Existing `SK_Mannequin` and `BS_Idle_Walk_Run` packages were inspected for presence
and hashed, but no mannequin vertices or animations were extracted or copied
into this study. They remain separately supplied project technical resources;
their existing Epic/project provenance and terms still apply. Skeleton names,
rest pose and retarget settings were not guessed from these binary packages.

No Unreal process, map changes, C++ changes, external spending, commits or pushes
were performed by this worker. The coordinating root owns native integration and
publishing verification.
