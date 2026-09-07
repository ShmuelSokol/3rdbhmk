# Folding doors and paroches V1 — original source geometry

These nine editable assets supply framed double-sided door leaves, palm relief,
hinge/handle components, a thickened draped curtain, contoured hems, and a rod
with suspension rings. They are production studies, not accepted final Temple
ornamentation or functional runtime doors.

## Text, commentary and authored interpretation

Sources checked 2026-09-07:

- [Yechezkel 41:23–25 with Rashi](https://www.chabad.org/library/bible_cdo/aid/16139/jewish/Chapter-41.htm): doors are described for both sacred rooms; their panels and palm/cherub ornament are described. Rashi discusses folding leaves using Middot. The double-bank Heichal proposal follows that commentary discussion; individual hinge hardware and carving layout remain authored.
- [Mishnah Middot 4:1](https://www.sefaria.org/Mishnah_Middot.4.1-2?lang=en): identifies the folding-door interpretation with Rabbi Yehudah. This is a specific interpretive choice, not the only historical door arrangement.
- [Rambam, Beit Habechirah 4:2–3](https://www.chabad.org/library/article_cdo/aid/1007197/jewish/Beit-Habechirah-Chapter-4.htm): describes the First/Second Temple partition distinction and the Second Temple curtain solution. It does not make that Second Temple arrangement a measured requirement for this future reconstruction.
- [Shemot 26:31](https://www.chabad.org/library/bible_cdo/aid/9887/jewish/Chapter-26.htm): Mishkan curtain materials/colors and woven cherub design inform the textile reference vocabulary. This is a Mishkan reference, not a direct Third Temple specification.
- [Mishnah Shekalim 8:5](https://www.sefaria.org/Mishnah_Shekalim.8.5?with=all): historical curtain dimensions/thickness are documented there. They are deliberately not presented as the dimensions of this opening-fitted study.

No sacred words or copied images are placed on the models. All mesh shapes are
original curves, bevels or cloth surfaces. Existing project-authored mathematical
helpers are reused; no paid or externally licensed models/textures were used.
Text translations are linked, not bundled as asset content.

The number of framed fields, simplified palm outlines, relief depth, wood/gold
appearance, barrel hinges, handles, cloth fold count, rod, suspension rings,
hem arrangement and colors are artistic choices. **Cherub relief and woven
cherub design are absent.** Their absence prevents these assets from being a
complete realization of the cited ornament descriptions. The curtain is a
single closed cloth study with no draw animation, simulated textile, historical
weave, measured future fabric thickness or authority claim.

## Measured openings and fit

The frozen `architecture-manifest.json` SHA256 is
`40c4a0feae391868c6c840f76bc72f0df0bab8c3be9406c6b5dbb6f508f9333d`.
Source conversion uses the existing 50cm/amah reconstruction, not a new
halachic measurement decision.

Heichal: the House-union source element `Heichal ten-amah doorway lintel`
has underside Z3425cm. The clear floor is Z925cm, giving a **500 × 2500cm**
opening at X−3600..−3300cm and Y±250cm. The existing four `Open Heichal door`
primitives also reach Z3425. The 2000cm entrance veneer in
`build_sanctuary_finishes.py` is not the opening height. This distinction is
preserved because confusing veneer dimensions with door dimensions would leave
a five-metre gap above new leaves.

Kodesh: `SM_0142/0143` partition shoulders leave Y±175cm; `SM_0144` lintel
underside is Z1225cm. With floor Z925cm, the opening is **350 × 300cm**, with
partition depth X−5700..−5600cm. This follows the existing source interpretation
of Yechezkel41:3; it does not adjudicate alternative readings of that passage.

Door leaf bodies are 1cm narrower than nominal quarter-opening width, with 2cm
top/bottom clearances: Heichal124 ×2496cm; Kodesh86.5 ×296cm. Each geometry
family has wood/frame, palm carving and hardware meshes sharing the same pivot.
Instantiate all three together. Tall Heichal leaves have eight framed fields;
Kodesh leaves have one. Those subdivisions are artistic.

The paroches cloth is360cm wide and306cm tall, placed optionally at
`[-5585,0,928]`cm, yaw−90. It covers the350cm opening on the Heichal side with
5cm side overlap and clearance above the floor. Its fabric ends Z1234cm; rod
and rings rise above it. Closed curtain placement hides the inner room: the
root must choose an appropriate review/access view and cannot treat it as a
walk-through surface. This is an opening-sized interpretation, not the
historical full-room curtain dimensions. It is unplaced by the helper.

## Folding and integration

`placement-and-articulation.json` supplies closed-state parent/child transforms,
two proposed Heichal banks and one Kodesh bank. Four quarter-width leaves form
each bank. The Kodesh's100cm wall depth is not falsely treated as a300cm Heichal
recess. Existing door primitives are identified for the root's review-copy-only
replacement decision; the helper never hides/deletes them.

The child fold axis is offset8cm in localY. For angle a its relative translation
is `(nominal+8*sin(a), 8-8*cos(a), 0)`, with relative yaw a. The180-degree endpoint
separates the two folded mesh centerplanes by16cm. A simple rotation about the
unshifted mesh origin would intersect the decorated panels. This is a kinematic
resource, not proof of manufactured shared hinge knuckles, collision-safe
motion or clearance when both jamb leaves swing. Native swept-volume checks,
top/bottom pivot support, opening sequence and functional access remain pending.

All OBJ files use the existing legacy Unreal adapter: reflect canonicalY and
reverse triangle winding. Editable JSON preserves canonical UnrealXYZ cm,
named parts, vertices and triangles. Imported UVs are nondegenerate per-face
charts for plain materials; production texture UVs/smoothing and LOD remain
needed. Assembly overlaps are intentional; each component is closed but the
whole object is not a Boolean-unioned manufacture mesh.

## Entry points and evidence

Offline regeneration (refuses an existing geometry manifest):

    python Scripts/create_sanctuary_doors.py --export

Independent source readback and previews:

    python SourceAssets/sanctuary-detail/DoorsParochesV1/verify_and_preview.py

Root-only native import, after loading `Scripts/create_sanctuary_doors.py`:

    module.run_native(materials)

`materials` must map all nine mesh names in `geometry-manifest.json` to existing
reviewed material asset paths. Native import checks the frozen helper hash,
geometry hashes, mesh count, bounds and triangles, then saves only unique assets
under `/Game/MikdashV3/MaterialReview/SanctuaryDoorsParochesV1/Meshes`. It creates
no materials, actors, map changes or engine processes. Existing namespaces and
partial failures are preserved. Root owns native operations and publishing.

Offline checks cover closed welded component edges, positive volume, valid OBJ
indices, nondegenerate geometry/UVs, unit normals, winding agreement, bounds,
source opening fit and leaf clearances. The three previews are software renders
of the actual source meshes with illustrative colors, not native visual proof.
Engine shading/materials, cloth realism, runtime door motion, collision, walking,
performance, complete sourced ornament and packaged acceptance are pending.

Next bounded production candidate: develop a source-reviewed two-faced cherub
relief with an explicit interpretation sheet and a single editable prototype,
then compare it beside the existing palm module before repeating a full scheme.
