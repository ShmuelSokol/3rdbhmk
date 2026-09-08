# Believable people: PilgrimRigV3 — state, first native batch, resident swap plan

Updated 2026-09-08 (Fable). Two separate systems: the 24 authored skeletal residents
(`MikdashResidentPopulation`, one shared V2 body — the "balloons") and the instanced CrowdFigureV1
field. This note covers the skeletal residents. Nothing below has been applied natively; no C++, map,
population file or shared script was changed. Owned files only: `Scripts/release_pilgrim_v3_review.py`
(+spec), `Scripts/release_pilgrim_v3.py` (+spec), `PilgrimRigV3/`, this note.

## What run() says (offline, 2026-09-08)

`run()` → `PREPARED_NOT_NATIVE`; base `sourceCheck.status = READY_FOR_NATIVE_IMPORT`, problems `[]`
(all 9 GLB/OBJ/MTL hashes match, decode OK, 27 joints each, inverse-bind matrices match rest pose,
weights sum to 1 within 4.5e-8, distinct static geometry, all under the 25k triangle budget);
`restPoseProof.status = REST_POSE_PROVEN_FROM_GLB`; `residentSwapPlan.status =
SWAP_PLAN_ONLY_NOTHING_APPLIED`; `resume.completed = []`. Receipts: `PilgrimRigV3/rest-pose-proof.json`,
`PilgrimRigV3/resident-swap-plan.json`.

Fixed today so the gate could pass natively rather than refuse itself (see `PilgrimRigV3/REVIEW-HELPER.md`):
the native rest-pose compare frame (Interchange maps glTF (X,Y,Z)→UE (X,Z,Y); Y-asymmetric bones would
have read back ~23 cm off), the bone readout (an unregistered `SkeletalMeshComponent` returns identity;
now `AnimPoseExtensions.get_reference_pose`), a native per-clip rotation-only proof, a real resume marker,
a zombie-editor guard, per-slot material readback, the `/Characters/PilgrimRigV3` namespace, and the
scale wording (component scale, never actor/capsule/amah).

## Rest-pose proof per variant (from the GLB bytes vs the V2 GLB)

| Variant | joints | names/hierarchy/order = V2 | moved joints | pelvis moved | whole-arm drift | max segment drift | clips (name / s / keys / rot targets / translation) |
|---|---|---|---|---|---|---|---|
| Man_Standard, Man_Heavy, Man_Elder, Woman_Young, Woman_Elder, Youth, Kohen_White, Visitor_Camera, Visitor_Phone (identical on all nine) | 27 | yes | 10 declared (clavicle ±2.0 cm, upperarm 0.5, lowerarm 8.235, hand 5.471, ball 2.5) | 0.0 cm | 0.1217° (limit 0.13) | 4.96° elbow, 4.32° wrist, 3.81° toe (lengthened segments) | Original_Idle 3.2/97/9/none; Original_Walk 1.2/37/17/pelvis only (Z 95.55–96.05); V3_PhotoCamera 4.0/121/10/none; V3_PhotoPhone 3.6/109/10/none |

Idle/Walk targets and timing are byte-identical in intent to the V2 GLB clips; nothing animates scale.
This proves the V2 motion is well-defined on every V3 skeleton. It is not native Skeleton identity —
Interchange creates one Skeleton per variant, and the native gate re-proves names, rest pose (within
0.05 cm, Interchange frame) and rotation-only clips before saving.

## Batch 1 attempt 04 result (21:16 UTC)

Import itself succeeded in memory and every native number was right (27 bones, Interchange-frame rest
pose exact, clips rotation-only except pelvis 2.45 cm in Walk); the gate refused because it required the
generator's bone ORDER while UE lists the Skeleton depth-first. Fixed to name-keyed identity. Nothing was
saved; no folder exists on disk, so the rerun needs no cleanup (`clean_partial=True` exists if a later
attempt saves a partial folder). Confirmed natively: the mesh faces UE **+Y** (ball_r y +11.5), so the
swap must use mesh relative yaw **−90**, not the current +90.

## Batch 1 attempt 05 result (21:41 UTC)

Native rest-pose and clip proofs passed; the OBJ crowd copy came in as 62 StaticMeshes (default Interchange
OBJ pipeline: one per `o` group). Nothing saved, nothing on disk. Fixed by an Interchange pipeline override
(CombineStaticMeshesBehavior=All, Nanite off) plus a pre-save assertion of one mesh with the authored
triangle count. See `PilgrimRigV3/REVIEW-HELPER.md`.

## Exact commands (coordinator, one serial native job each, fresh editor, main loaded, no PIE, no dirty packages)

```python
import runpy; m = runpy.run_path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3\Scripts\release_pilgrim_v3_review.py')
m['run']()                                                          # offline gate, must be PREPARED_NOT_NATIVE
m['run'](import_assets=True, variants=['V3_Pilgrim_Man_Standard'])  # first batch
# following eight, in two batches (each in a fresh editor; the marker decides what is next):
m['next_batch'](4)                                                  # shows what the next call imports
m['run'](import_assets=True, batch=4)                               # Man_Heavy, Man_Elder, Woman_Young, Woman_Elder
m['run'](import_assets=True, batch=4)                               # Youth, Kohen_White, Visitor_Camera, Visitor_Phone
```

Success status is `IMPORTED_NO_PLACEMENT_VISUAL_REVIEW_PENDING`; the receipt
`PilgrimRigV3/review-native-<stamp>.json` carries native bone positions, per-clip translated bones,
material slots per variant, the mesh **facing** and the read-back asset names; the marker
`review-native-progress.json` lists completed variants. A failure leaves the partial folder and a
`FAILED_PRESERVE_PARTIAL_INSPECT_RECEIPT` receipt — inspect, do not rerun over it. `Get-Process
UnrealEditor` must show one process before believing a save failure.

## Resident swap plan (for the population owner; NOT applied)

Rules: neighbours (start points within 26 m) never share a scale; where five mutually adjacent men
outnumber the four male variants they share a variant only with ≥0.02 scale gap; every scale inside a
variant is distinct and inside 0.84–1.04. Kohanim are cast in ordinary dress because the directory says
they are off duty (Yechezkel 42:14), so `V3_Kohen_White` is not used. `V3_Visitor_Camera/_Phone` carry
baked photo stances and need a clip role the population cannot select; they go to the crowd field or a
later reviewed photo-visitor population. Casting is authored characterisation.

| Resident | Role | Variant | Visual scale | Stature | Garment slot |
|---|---|---|---|---|---|
| yoav-ben-shimi | pilgrim | V3_Pilgrim_Man_Standard | 1.00 | 179.4 | Mantle |
| miryam-bas-elyakim | pilgrim | V3_Pilgrim_Woman_Young | 0.93 | 166.9 | Mantle |
| naftali-ben-chagai | pilgrim | V3_Pilgrim_Man_Heavy | 1.04 | 189.2 | Mantle |
| tzipporah-bas-menachem | pilgrim | V3_Pilgrim_Woman_Elder | 0.90 | 161.3 | Mantle |
| elchanan-ben-uriya | pilgrim | V3_Pilgrim_Man_Elder | 0.97 | 173.7 | Mantle |
| shulamis-bas-yechiel | pilgrim | V3_Pilgrim_Woman_Young | 0.95 | 170.5 | Mantle |
| gad-ben-peleth | pilgrim | V3_Pilgrim_Man_Heavy | 1.02 | 185.6 | Mantle |
| devorah-bas-amram | pilgrim | V3_Pilgrim_Woman_Young | 0.92 | 165.1 | Mantle |
| yigal-ben-zerach | pilgrim | V3_Pilgrim_Man_Standard | 0.99 | 177.6 | Mantle |
| techiya-bas-nadav | pilgrim | V3_Pilgrim_Woman_Young | 0.90 | 161.5 | Mantle |
| amitai-ben-kalev | pilgrim | V3_Pilgrim_Youth | 0.84 | 150.3 | Linen (no Mantle slot) |
| yehudis-bas-ovadya | pilgrim | V3_Pilgrim_Woman_Elder | 0.91 | 163.1 | Mantle |
| pinchas-ben-achituv | kohen (off duty) | V3_Pilgrim_Man_Heavy | 0.96 | 174.7 | Mantle |
| yedidya-ben-chilkiya | kohen (off duty) | V3_Pilgrim_Man_Elder | 0.96 | 171.9 | Mantle |
| uriel-ben-shemaya | kohen (off duty) | V3_Pilgrim_Man_Standard | 1.02 | 183.0 | Mantle |
| assaf-ben-berachya | levite | V3_Pilgrim_Man_Standard | 1.01 | 181.2 | Mantle |
| chananel-ben-mattisyahu | levite | V3_Pilgrim_Man_Standard | 0.98 | 175.9 | Mantle |
| rivka-bas-yoezer | host | V3_Pilgrim_Woman_Elder | 0.89 | 159.5 | Mantle |
| nechemya-ben-tzuriel | guide | V3_Pilgrim_Man_Elder | 0.94 | 168.3 | Mantle |
| shmaya-ben-nachshon | host (deck) | V3_Pilgrim_Man_Heavy | 1.01 | 183.8 | Mantle |
| aviela-bas-refael | guide (deck) | V3_Pilgrim_Woman_Young | 0.94 | 168.7 | Mantle |
| ovadya-ben-ephrayim | vendor (deck) | V3_Pilgrim_Man_Elder | 0.95 | 170.1 | Mantle |
| machla-bas-yiftach | vendor (deck) | V3_Pilgrim_Woman_Elder | 0.86 | 154.2 | Mantle |
| elad-ben-yishai | vendor (deck) | V3_Pilgrim_Youth | 0.87 | 155.7 | Linen (no Mantle slot) |

Use: Man_Standard 5, Woman_Young 5, Man_Heavy 4, Man_Elder 4, Woman_Elder 4, Youth 2. 49 neighbour
pairs checked; the only same-variant neighbours are Yoav/Uriel (gap 0.02) and Elchanan/Nechemya (0.03).

### What the population owner must change (their files, not mine)

1. `people.json` (staged by `release_people_v3`): per-person `body = {variant, visualScale}` from
   `resident-swap-plan.json`; `MikdashPeople` parser reads it.
2. `MikdashResidentPopulation`: replace the single `ResidentMesh/IdleAnimation/WalkAnimation` with an
   `EditInstanceOnly` array of body variants `{Id, SkeletalMesh, Idle, Walk, GarmentSlots, MeshRelativeYaw}`;
   the skeleton-equality guards (≈ lines 231–235 and 415–416) become per variant.
3. `SpawnAuthoredBody`: `SetSkeletalMeshAsset(variant mesh)`, `SetRelativeScale3D(FVector(visualScale))`,
   keep `SetRelativeLocation(0,0,-96)`; relative yaw from the import receipt's `facing`
   (natively confirmed: the mesh faces +Y, so −90; the current +90 assumes −Y); `PlayAnimation` with the variant's
   own idle; the Tick walk/idle switch (≈ line 610) uses the body's variant clips, not the shared pair.
4. Garment override on `Mantle` for robe variants and `Linen` for Youth; keep the `MI_Garment_*` instances.
5. Untouched: capsule 34/96, spawn offset +96, actor scale, MaxWalkSpeed, the pilot bridge, the player
   pawn, every eye-height/hardware offset, the amah frame.

### Verify after (PIE in a review copy first, then main)

Capsule radius 34 / half-height 96 and actor scale (1,1,1) on every body; mesh relative location
(0,0,−96), relative scale = planned, relative yaw = receipt facing; ball_r/ball_l world Z within 3 cm of
the floor (300 outer court, 0 deck) in idle and at walk contact for the 0.84 and 1.04 bodies; head bone
≈ floor + 166×scale; toes ahead of pelvis along actor forward and walkers moving toward their toes;
garment MI reads back on the intended slot with no "no named slot matched" note; the same residents
spawn/refuse as before (the nine capsule refusals are a separate open issue); player eye height and
hardware offsets unchanged; frame time before/after recorded, not assumed.

## Ceiling and blockers

Stylised, faceted figures with flat PBR colour and static cloth — correct at 5–30 m, not film-quality
humans; no facial animation, finger rig or hair strands. MetaHuman Core Data **is** installed; the first
Epic cloud auto-rig still needs the editor GUI. Blockers for acceptance, in order: native import + gate
(coordinator, serial), PIE facing/sole/capsule check of one standard and one scaled body beside a V2 body,
population owner's per-profile body mapping, then the crowd-field owner's V3 static poses. Import success
alone is not believable-human acceptance.
