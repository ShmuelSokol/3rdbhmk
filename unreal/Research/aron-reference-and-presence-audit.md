# Aron: source, presence and modeling audit

Checked 2026-09-07. The user has made the Aron a central priority. This audit inspected project files without launching Unreal or changing assets/maps. It distinguishes a missing implementation from uncertainty about future details.

## Actual project finding

**No dedicated Aron/Ark or kaporet-cherub mesh was found in the working assets or the preserved architecture manifests.** This is not evidence of an import failure: the earlier web specification deliberately omitted it. The immutable `Workspace/mikdash-walkthrough/lib/mikdash/spec.ts:32` describes its Kodesh interpretation with: “No speculative Ark has been supplied.” The new user priority changes that artistic scope; the old omission should not silently remain the design decision.

Three inspected architecture manifests each contain 2,633 mesh records, no matching Aron/Ark/covenant/cherub/cheruv/Hebrew-name records, and the identical SHA-256 `40c4a0feae391868c6c840f76bc72f0df0bab8c3be9406c6b5dbb6f508f9333d`:

- `C:/Mikdash/Working-5.8/MikdashCourtyardV3/SourceAssets/architecture-manifest.json`
- `C:/Mikdash/Mikdash-Windows-Transfer/EditorProject/MikdashCourtyardV3/SourceAssets/architecture-manifest.json`
- `C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/cloud-unreal-v3/architecture-manifest.json`

The working `Content` tree had 7,574 `.uasset` files at inspection; none had a true Aron/Ark/covenant/cherub/cheruv name match. Substring false positives such as `dark`, `Landmark` and cemetery `markers` were excluded. This filesystem/name audit does not inspect every unnamed binary object's interior or replace a live asset-registry/map inventory. It establishes no named dedicated asset and no exported source record, not a universal claim about arbitrary anonymous geometry.

The chamber floor is present at the exact native package:

`/Game/MikdashV3/Architecture/architecture_SM_0147_floor_Kodesh_clear_floor`

Its physical file exists at `C:/Mikdash/Working-5.8/MikdashCourtyardV3/Content/MikdashV3/Architecture/architecture_SM_0147_floor_Kodesh_clear_floor.uasset`. Manifest bounds are X −6,700 to −5,700 cm, Y −500 to 500 cm, top Z 925 cm. These provide a source-derived chamber envelope, **not an established Aron location**. Partition shoulders and lintel are source records SM_0142, SM_0143 and SM_0144.

The immutable `lib/mikdash/architecture.ts:63` contains a separate “Palm and two-faced cherub gold relief” construction. Such wall ornamentation is not the Aron or its kaporet figures; it cannot satisfy the missing vessel. The searched web `lib/mikdash` source contains the omission statement but no other Aron/Ark/covenant implementation match. `furnishings.ts` adds other curved vessel details; it does not add the Aron.

## What the sources establish

**Torah vessel specification.** Exodus 25:10–22 describes an acacia-wood Aron, 2½ amot long, 1½ wide and 1½ high, gold-covered inside and outside, with a gold border, four rings, carrying poles retained in those rings, and a gold kaporet carrying two cherubim. Their wings spread upward over the cover and their faces are directed toward one another and the cover. This gives a substantial faithful modeling brief without inventing future prophecies. [Exodus 25 with Rashi](https://www.chabad.org/library/bible_cdo/aid/9886/jewish/Chapter-25.htm).

The one-tefach kaporet thickness is a rabbinic derivation, not an explicit thickness in the verse. Keep body height, cover thickness and figure height separately parameterized; do not accidentally label their combined height as the Torah's 1½-amah body height. [Sukkah 5a](https://www.chabad.org/torah-texts/5446543/Talmud/Sukkah/Chapter-1/5a).

**Earlier Temples.** Rambam describes the Aron on a stone in the western part of the Kodesh Hakodashim, its concealment under Yoshiyahu and its non-return in the Second Temple. This supports a historical distinction; a Second Temple scene without the Aron should not be indiscriminately used as the future scene. [Hilchot Beit HaBechirah 4:1](https://www.chabad.org/library/article_cdo/aid/1007197/jewish/Beit-Habechirah-Chapter-4.htm).

**Future interpretation.** The Temple Institute explicitly presents the tradition of the concealed Aron being restored when the Third Temple is built. That is a suitable named interpretive basis for including the Aron in the user's envisioned experience. It is not a verified modern excavation, recoverable 3D scan or measured inventory of the actual ancient object. [Temple Institute: Menorah mystery and daily service](https://templeinstitute.org/menorah-mystery-and-daily-service/).

**Prophetic text needs interpretation.** Yechezkel 41 describes the inner chamber and carved palm/cherub decoration, but does not supply an Aron design or placement measurement in that chapter. Its two-faced wall figures must not be copied onto the kaporet merely because both are called cherubim. [Yechezkel 41:3–4, 18–25](https://www.chabad.org/library/bible_cdo/aid/16139/jewish/Chapter-41.htm).

Yirmiyahu 3:16–17 also needs to be acknowledged: it describes a changed future relationship to the Aron and Jerusalem. Rashi explains the wider community's holiness and interprets the final clause concerning the former practice of taking the Aron to battle. The verse should not be flattened into a definitive prohibition on depicting a restored Aron, nor should its interpretive complexity be concealed. [Yirmiyahu 3:16–17 with Rashi](https://www.chabad.org/library/bible_cdo/aid/16000/jewish/Chapter-3.htm).

**Three different cherub contexts.** The Torah's two kaporet figures, Shlomo's large gold-covered olivewood figures and Yechezkel's carved wall figures are distinct source subjects. Shlomo's figures are ten amot high; that is not a dimension for the small figures on the cover. Do not merge all three into one hybrid model. [I Kings 6:23–28](https://www.chabad.org/library/bible_cdo/aid/15890/jewish/Chapter-6.htm).

## Bounded faithful production scope

Proceed with an original, separately versioned **Aron restoration interpretation**, preserving the measured architecture. The user has asked for its presence; source uncertainty should appear as precise attribution rather than an excuse for leaving a major empty focal point indefinitely.

1. Model the box, cover, border, four rings and two poles as an inspectable assembly with original-unit dimensions. At the project's illustrative 0.50 m amah, the Torah body dimensions convert to 125 × 75 × 75 cm. Record that conversion as the chosen modeling scale, not a discovered measurement of the ancient Aron. The cover and figures are additional dimensions requiring their own source/interpretation fields.
2. Model the two kaporet cherubim as a coherent selected interpretation, explicitly recording figure form, pose, wing arrangement and scale sources. Do not use generic fantasy angels, anonymous generated inscriptions or unrelated archaeological motifs as proof of accuracy. No figure anatomy is finalized by this audit.
3. Prepare one native review asset group with measured bounds, gold/wood material separation, named parts and a source manifest. Review silhouette and scale before polishing ornaments. A detailed reference painting can guide the selected interpretation but requires clear media identification and suitable rights if incorporated.
4. Place it only after checking the actual Kodesh floor, source room orientation, foundation-stone representation, pole clearance and sight lines. The manifest envelope above supports that check; an exact future standing coordinate is not established here. Keep placement attribution distinct from the chamber's measured dimensions.
5. Make the Aron visually and narratively central without turning it into a collectible, loot container or routine visitor interaction. A study view can reveal it while the embodied pilgrim experience respects its selected access rules. Review approach composition, parochet treatment and explanatory sequencing together rather than opening unrestricted access to obtain a screenshot.
6. Verify saved asset presence, map reference, correct dimensions/counts, close/wide material appearance, packaged loading and the intended visitor/study-view distinction. Do not report a finished Aron from a placeholder box, a design document or successful import alone.

Open items: selected detailed figure interpretation; exact cover/pole/ring dimensional profile; foundation-stone review; placement and orientation; native model creation; incorporation rights for any outside media; packaged visibility and source-label presentation. No engine assets or maps changed during this audit.
