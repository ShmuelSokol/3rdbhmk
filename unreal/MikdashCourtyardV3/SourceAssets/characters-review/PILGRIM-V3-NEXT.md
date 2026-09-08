# Believable people: next bounded visual step

The current courtyard164151 screenshot contains simple robed figures. It cannot identify each body class from appearance alone. There are two separate systems: the24 authored skeletal profiles and the instanced CrowdFigureV1 field; changing one does not upgrade the other.

## Recorded placed skeletal system

`runtime-review/people-v3/native-apply-20260908T025912331054Z.json` records saved/reopened `MikdashResidentPopulation_1`, label `RELEASE_PeopleV3Population`, with one earlier pilot population preserved. It uses `/Game/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2` and adjacent `PilgrimRigV2A_Pilgrim_Original_Idle`/`..._Walk`. Material slots are Skin,Linen,Mantle,Headwrap,Leather,Hair,Eyes,Trim. `release_people_v3.spec.json` assigns garment instances under `/Game/MikdashV3/Runtime/PeopleV3` only to Mantle; this diversifies color, not face/body anatomy.

The24 profiles are authored directory entries staged in `Content/Distribution/People/people.json`; they are spawned by BeginPlay, not24 saved skeletal actor meshes. Current `MikdashResidentPopulation::SpawnAuthoredBody` uses a single `ResidentMesh` for everyone, physical capsule halfheight96, mesh relativeZ−96/yaw90 and one shared idle/walk pair. There is no per-person anatomical mesh/clip/visual-scale selector in that path. The existing pilot bodies are a separate earlier five-person assembly and need their own exact inventory if swapped.

## Available V3 source assets, not placed assets

Nine authored GLBs plus nine static OBJ/MTL copies exist in `PilgrimRigV3/meshes`; matching front/side/three-quarter images and a lineup exist. No `Content/MikdashV3/CharacterReview/PilgrimRigV3` directory or V3 native import receipt was found during this audit. `Scripts/release_pilgrim_v3.py` is an import-only preparation helper, not a swap script. Its intended namespace is `/Game/MikdashV3/CharacterReview/PilgrimRigV3`; static assets would be `<variant>/StaticMeshes/SM_<variant>`. Exact skeletal/animation package names must come from real import readback, not assumed naming.

The spec's recommended scales are: Man_Standard1.00, Man_Heavy1.04, Man_Elder0.97, Woman_Young0.93, Woman_Elder0.90, Youth0.84, Kohen_White1.01, Visitor_Camera1.02, Visitor_Phone0.96 (all IDs carry `V3_Pilgrim_` except Kohen/Visitor). These are metric artistic stature differences, not amah dimensions. Do not multiply them by0.96 during architecture migration. Do not blindly scale the whole Character actor: that also changes its capsule and route clearance assumptions. Prefer calibrated skeletal-component visual scale and measured sole alignment while leaving the reviewed physical capsule unchanged; any capsule redesign requires actual movement/clearance review.

The rig spec has27 joints, matching hierarchy/order, but `identical_rest_pose=false` and moved joints. It argues rotation-only curves remain usable because pelvis translation is unchanged. That is source compatibility reasoning, not native Skeleton identity. The importer deliberately creates a new Skeleton; use its imported GLB clips or a separately verified retarget, never directly substitute V2 animations without checking UE skeleton equality and visible foot/hand motion.

I viewed lineup.png: variants add visible facial features, hair/headwear, garment variation and dedicated phone/camera poses, but remain visibly stylized, faceted figures with simple cloth and faces. This is a plausible bounded improvement over anonymous silhouettes, not film-quality humans. Kohen clothing and modern camera/phone props are authored interpretations, not proof of exact priestly vestment compliance or unrestricted device use.

## Safe next sequence

1. Run the importer offline checks first; root then imports a small batch in the isolated fresh namespace. Preserve main, source hashes and failed receipts. Native readback must establish exact SkeletalMesh/Skeleton/clip/material identities, dimensions and available slots. Its resume logic and importer/API assumptions still need native proof.
2. In a new review map, compare one standard adult and one scaled variant beside the current V2 body at the same grounded camera. Verify sole alignment, capsule relationship, idle/walk/contact, garment slot matching, facial read at visitor distance and lit/shadow appearance. Keep profile IDs, goals and routes intact.
3. Add an explicit per-profile visual mapping to the population owner only after native assets are known: mesh, matching idle/walk clips, garment slot mapping and visual scale/foot offset. Current single ResidentMesh API cannot represent all nine variants simultaneously. A single global mesh replacement would make all24 the same anatomical variant and is insufficient.
4. Review CrowdFigureV1 independently. `release_crowd_field.py` imports static pose meshes from its own frozen manifest and drives instanced bodies/zones. V3 static camera/phone stances cannot simply share a generic idle; preserve per-pose identity, instance sizing, grounding, bounds and the existing behavior worker's ownership. No evidence here establishes completed V3 VAT/motion integration.

Missing acceptance: V3 native import, mesh and clip compatibility, material slot retention,24-profile mapping, appropriate ages/roles, modest animation/deformation, sole/capsule clearance, photo pose use, performance at intended density, PIE and packaged readback. No C++, assets, maps or shared scripts were changed by this audit.
