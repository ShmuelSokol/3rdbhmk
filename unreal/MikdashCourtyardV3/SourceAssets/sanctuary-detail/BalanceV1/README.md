# Sanctuary balance V1 (gold, partition, floor, highlights)

Design notes for `Scripts/release_sanctuary_balance.py` + `release_sanctuary_balance.spec.json`.
Receipts land in this folder (`native-balance-*.json`, `native-balance-dryrun-*.json`,
`native-balance-revert-*.json`). Nothing here is visually accepted; every number is a proposal
read back numerically. Authored 2026-09-07 against the renders in
`SourceAssets/visual-review/release-capture-20260907T214622Z` (d_heikhal_west_vessels,
e_kodesh_aron_keruvim).

## What the renders show and what causes it

| Symptom | Cause found in the receipts | Change |
|---|---|---|
| Heikhal rear wall (Kodesh partition, X -5600 face) blows out to white | The three measured partition pieces (SM_0142/0143 shoulders, SM_0144 lintel) carry `MI_PBR_GoldHammered` since the PBR pass ran with `-PbrIncludeGold` (materials-pbr/native-apply-20260907T204439966864Z). That instance samples the scratched-metal ARM whose roughness mean is 0.285, so the 24 klux morning-sun patch (30 klux sun, 30 deg elevation, wall normal +X) is a broad specular lobe 7-8 stops above the fill-lit interior. Histogram metering 10-90 % lets it clip. | Component-level override to the veneer gold (`M_Sanctuary_gold`, roughness 0.46 with variation); bilateral local exposure highlight contrast 0.8; white clip 0.04 -> 0.02; shoulder 0.26 -> 0.30. Book basis: 41:16-17 (p.222, p.231): gold-over-cedar on ALL Heikhal/Kodesh walls, floor to ceiling, above and behind the doors. |
| Gold floor mirrors like glass | `MI_PBR_GoldFloor` RoughnessScale 1.1 x ARM mean 0.285 = 0.31 roughness; metallic 0.8; pale tint [0.578, 0.509, 0.328] | RoughnessScale 1.755 (0.5 / 0.2849 -> mean 0.50, p10 0.40, p90 0.60), Tint -> gold, Metallic 1.0 |
| Walls and vessels read as flat synthetic yellow | Study colour 1.0/0.766/0.336, roughness 0.28 (vessels), 0.34 (veneer), 0.45/0.35 (frieze relief lerp) | Measured gold reflectance 1.0/0.71/0.29, metallic 1; roughness 0.42 (vessels), 0.46 (veneer), 0.50 ground / 0.42 raised relief (frieze) |
| Frieze panels repeat mechanically | 196 identical 250 cm mirror-tiled panels sharing one constant-colour material | World-space Perlin (gradient ALU) noise at 10 m: roughness +-0.06, tint +-3 % on the frieze and veneer materials, so neighbouring panels differ without touching the geometry or the relief lerp |
| Harsh highlights | Fill 25,000 cd with specular scale 0.25 on metallic gold; no local exposure | Fill 15,000 cd (threshold 15,000, -0.74 stop); the local-exposure/tonemapper changes above |

## Measurement used for the floor

`SourceAssets/materials-pbr/scratched-metal/blue_metal_plate_arm_2k.jpg`
(sha256 64991aa1...a04e4, CC0 Poly Haven "Blue Metal Plate"), G channel (roughness, imported
TC_MASKS linear), every 4th pixel (262,144 samples) via System.Drawing on 2026-09-07:
mean 0.2849, p10 0.2275, p50 0.2824, p90 0.3412. The separate roughness map gives 0.2845.
The master `M_PBR_Tiled` multiplies ARM.G by `RoughnessScale`, so 0.5 / 0.2849 = 1.755.
`offline_check()` re-hashes the JPG and recomputes the scale; a changed texture fails the check.

## Safety and revert

* All discovery and guards run before any mutation (plain study graphs required; a BaseColor fed
  by a Multiply means the pass is already applied -> refuse; a saved unreverted receipt -> refuse).
* Checkpoint `ReviewCheckpoints/SanctuaryBalance-<stamp>/` holds the map, One-File-Per-Actor
  folders and `Assets/<content path>.uasset` copies (SHA-256 verified) of every material and
  instance edited.
* `-BalanceRevert` restores the asset bytes BEFORE the map loads (hash-verified against the
  receipt), then restores the component overrides, fill intensity, post-process fields and label
  from the receipt's before-values, saves, reopens and reads back. If a material package was
  already in memory before the file restore, the in-memory readback can be stale; the receipt
  says so and `-BalanceDryRun` in a fresh process is the confirmation.
* `-BalanceDryRun` after an apply compares the live state with the receipt's after-values
  (fresh-process verification, the lesson from the interior-exposure fix).
* Protected: the four donor maps, `M_PBR_Tiled`, `MI_PBR_GoldHammered` (587 exterior gold
  components keep it) and the two canonical golds; hashed before and after.

## Known limits / follow-ups

* The partition receives plain gold; the keruv/palm relief the book requires on that wall
  (p.238) is still missing because frieze V2 skipped the wall (no veneer actor at X -5600).
* Shared-asset edit: `CourtyardGold`, `CourtyardPolish` and other review maps that reference
  `M_Sanctuary_gold`, the frieze materials or `MI_PBR_GoldFloor` look different afterwards
  although their .umap bytes are unchanged (same caveat as the PBR pass).
* The fill reduction does not fix the partition patch (the sun does that); it trims the fill's
  rectangle reflection. If the recapture still clips, the next knobs are
  `auto_exposure_high_percent` 90 -> 95-98 (lets the patch pull the meter) or the afternoon sun
  preset in the lighting spec, both outside this script.
* Recapture views d and e with `Scripts/release_capture_views.py` after applying; nothing here
  claims visual acceptance.
