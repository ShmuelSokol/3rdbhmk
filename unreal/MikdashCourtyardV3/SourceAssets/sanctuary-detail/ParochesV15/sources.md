# ParochesV15 — approved artwork, source basis and authored choices

Approved artwork: `third-temple-handwoven-v15.png` (frozen copy of
`C:\Users\shmue\Documents\Codex\2026-09-08\what-color-is-the-paroches-of\output\paroches\third-temple-handwoven-v15.png`),
SHA-256 `f48ccf055c8f051ccf9bc2702c003d84d1b74eeda54231d2be9ced157232df89`, 1355 x 1161 px, 24-bit RGB.
Shmuel explicitly approved V15 (HANDOFF-FOR-FABLE-20260908.md, "Approved paroches — do not lose this asset").
The design note `PRIVATE-REVIEW-v15.md` beside the original explains the intent; its preapproval wording is
superseded by that approval. V1/V7/V8/V9 (ParochesFabricV1/V7/V8/V9, `Scripts/release_paroches_fabric.py`)
are HELD earlier work, preserved untouched and never read by the V15 scripts.

What the image shows (read 2026-09-08): a landscape woven panel, 7:6, deep blue field with visible warp/weft
texture; a geometric ivory/red diamond border; two stylised palms (ivory, scarlet, purple) left and right; one
central keruv with wings arched upward, a feathered body that conceals the feet, and a single head that reads
as a lion in right profile (mane, one lion ear) with a youthful human face on the left/back of the same skull;
four yarn colours only — blue, purple, scarlet, ivory — and a few near-invisible brown flecks at the centre.

## Sourced (with the citation the project already holds)

| Element | Source | Status |
| --- | --- | --- |
| Four materials: techelet (blue), argaman (purple), tolaat shani (scarlet), shesh (fine linen, ivory) | Shemot 26:31 — Mishkan paroches; linked in `DoorsParochesV1/SOURCE-PROFILE.md` | certain for the Mishkan; used here as the textile vocabulary for the future paroches (not a direct Third Temple specification) |
| Keruvim woven into the fabric ("maaseh choshev ... keruvim") | Shemot 26:31 | certain (Mishkan); a keruv motif on the paroches is therefore sourced, its drawing is not |
| Hung on pillars with hooks (vavim) | Shemot 26:32 — four acacia pillars overlaid with gold, gold hooks | certain for the Mishkan; the Third Temple has a 2-amah stone partition with doors, so a rod/rings/bracket fixing is an interpretation (see authored) |
| Size 7 x 6 amot = exactly the size of the Kodesh HaKodashim gate | Yechezkel 41:3 (entrance 6 high, 7 wide); book pp. 184-186 "paroches exactly the size of the gate"; Lishchno Tidreshu pp. 59-60 "on the Heichal side" — `SourceAssets/research/book-scene-requirements-20260907.md` section 4 | certain per the book; 48 cm amah -> 336 x 288 cm (handoff figure agrees); 50 cm legacy architecture -> 350 x 300 cm |
| Position: Heichal face of the partition, centred on the gate, hanging from the top | same pages (Heichal side; Aron poles press the paroches, Yoma 54a) | placement line sourced; standoff and hem clearance authored |
| Palm and keruv as the sanctuary's ornament vocabulary | Yechezkel 41:18-19 (wall reliefs); book p. 238 figure "paroches kodesh hakodashim" shows a palm and keruvim woven into the curtain | the vocabulary is sourced; that figure shows TWO keruvim and a palm — V15's single keruv between two palms is a different, authored composition |

## Authored (approved artistic choices — NOT certified reconstruction)

- The whole composition of V15: one central keruv, palm–keruv–palm arrangement, the geometric border, the palette
  distribution, the weave scale (the design note calls it illustrative, not measured textile data).
- The single head reading as a lion (right profile) with a youthful human face on the back of the shared skull,
  one lion ear and no human ear; wings arched upward; feathers concealing the feet. Yechezkel 41:19 describes a
  two-faced keruv (man toward the palm on one side, young lion toward the palm on the other) for the wall
  reliefs; applying that reading to a single woven keruv, and every anatomical detail, is the artist's choice.
- The subtle central brown flecks ("blood detail") — an artistic reference, not a sourced feature of the curtain.
- The hanging drape: six S-curve folds between seven rings, +-4 cm at the rod softening to +-2 cm at the hem,
  a small incommensurate irregularity, 0.8 cm cloth thickness. Sourced texts give no fold count or depth
  (Mishnah Shekalim 8:5 gives the Second Temple curtain's thickness of a tefach; deliberately not used).
- The fixings: gold rod 1.75 cm radius with 10 cm overhang, seven rings, two wall brackets, two finials, all
  at 5.5 cm above the cloth. The Torah's pillar-and-hook arrangement belongs to the tent Mishkan; the Third Temple
  partition is stone with doors, and no text describes how its paroches was fixed.
- Standoff 12 cm before the wall face and 3 cm hem clearance (the old study used 15 cm / 3 cm).
- The soft fabric normal map `third-temple-handwoven-v15_normal.png`: derived offline from the artwork's
  high-passed luminance at low amplitude (slope scale 2.5, tilt clamp 0.35, DirectX green). It is a shading aid
  that makes the woven yarn catch light; it is not measured textile relief.
- Whole-panel UV chart, arc-length parameterised, both faces sharing the chart (the back reads mirrored, as a
  woven back does). The material is two-sided so the panel also reads from inside the Kodesh HaKodashim.
- Texture import: the 1355 x 1161 PNG is not a power of two. Imported as-is Unreal keeps every pixel but cannot
  build mip maps; the release script therefore stretches to 2048 x 2048 at import (whole image, UV 0..1 unchanged)
  unless `-ParochesV15KeepNPOT` is passed. Either way the source pixels are the approved file.

## Files

- `geometry-manifest.json` — hashes, triangles, bounds, volumes, drape/normal parameters (frozen in
  `Scripts/release_paroches_v15.spec.json` as `frozenManifestSha256`).
- `SM_ParochesV15_Cloth_50.obj`, `SM_ParochesV15_Fixings_50.obj` — 350 x 300 cm for the current main map.
- `SM_ParochesV15_Cloth_48.obj`, `SM_ParochesV15_Fixings_48.obj` — 336 x 288 cm for the 48 cm candidate.
- Creator: `Scripts/create_paroches_v15.py --export` (refuses an existing manifest without `--force`).
- Release: `Scripts/release_paroches_v15.py` with `-Main50` or `-Candidate48`; offline mode prints the plan.
- Receipts: `native-import-<target>-<stamp>.json` in this folder after each native run.

Old curtain: the release hides (never deletes) `RELEASE_Doors_37_Paroches_Cloth`, `_38_Paroches_Hem`,
`_39_Paroches_Fixings` by serialized visibility flags and tags them `ParochesV15HiddenOldCurtain`; the
checkpoint `.umap` under `C:\Mikdash\Working-5.8\ReviewCheckpoints\ParochesV15-<target>-<stamp>` is the full
rollback. In the 48 cm candidate those three actors were never converted and sit inside the scaled Kodesh
HaKodashim, through the Doors48V1 leaves; hiding them removes a stale 50 cm object there.
