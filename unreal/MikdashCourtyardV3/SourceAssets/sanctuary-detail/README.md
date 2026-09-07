# Sanctuary palm carving: partial original architectural study

This deliverable is an actual editable relief assembly with a separate backing,
not a complete sanctuary wall or a claim of finished production art. All geometry
was authored from mathematical curves and bevels for this project. No external
mesh, photo, texture, paid service or generated image was used. The original
project bevel helper `Scripts/create_heikhal_keilim.py` is reused; its hash is in
the geometry manifest. Text translations and commentary are referenced, not
included as reusable asset content. Original authored asset files may be used
and edited with the project; no third-party model license is introduced.

## Source and interpretation

Sources accessed 2026-09-07:

- [Yechezkel 41, Hebrew text, English translation and Rashi](https://www.chabad.org/library/bible_cdo/aid/16139/jewish/Chapter-41.htm), especially verses 16–20 and 25. The text describes wooden covering and alternating palm/cherub ornament. Rashi's explanation of verse 16 identifies the wood as cedar. Species is therefore recorded as commentary, rather than an explicit species specification in that verse.
- [Sefaria, Ezekiel 41](https://www.sefaria.org/Ezekiel.41): cross-reference for the wall/door ornament and the uncertainty of architectural terms in the door description.

The precise palm silhouette, frond count, leaflet spacing, relief depth, border,
120cm width, 260cm height and low placement are original artistic choices. This
is NOT a traced historical motif. Gold appearance in the software preview is an
illustrative material choice; it does not establish an Ezekiel gold mandate.
No cherub is modeled. The module therefore cannot serve as the completed
alternating palm-and-cherub scheme described in the text. Doors and paroches
are also not included. Keep those missing items visible in the production plan.

## Files and use

`PalmReliefV1/editable-meshes.json` preserves canonical Unreal XYZ centimetre
vertices and triangles, with every carving component named. The two OBJ files
also have named groups, normals and nondegenerate per-triangle UV charts. Their
Y coordinates and winding are adapted for the project's verified legacy Unreal
OBJ importer. For a DCC using the canonical coordinates, load the editable JSON
or reflect OBJ Y and reverse its winding. Do not apply the adapter twice.

The paired meshes share a bottom-center pivot. Their width lies along local X,
height along Z and relief projects along +Y. `geometry-manifest.json` supplies
two measured-face review proposals: one each on the Heichal's ±500cm side walls.
These are two isolated panel studies, NOT an authored continuous decorative
scheme. Back surfaces sit 0.25cm inside the room, clear of existing 0.1cm-proud
veneers. Root must verify native faces, openings and material appearance before
placing. Do not replace or reassign the shared House union: it contains exterior
surfaces as well as interior ones.

Offline export entry point (existing V1 preserved; generation refuses overwrite):

    python Scripts/create_sanctuary_reliefs.py --export

Repeatable independent readback and source preview:

    python SourceAssets/sanctuary-detail/verify_and_preview.py

Root-only native entrypoint, once the source module is loaded:

    module.run_native({
        'SM_CedarPalmBackingV1': '/Game/.../ExistingReviewedWoodMaterial',
        'SM_PalmCarvingV1': '/Game/.../ExistingReviewedCarvingMaterial',
    })

Supply real reviewed material paths; these examples are intentionally placeholders.
The helper imports and saves isolated assets into
`/Game/MikdashV3/MaterialReview/SanctuaryPalmReliefV1/Meshes`, verifies triangle
counts/bounds, and creates no material or actor. It refuses an existing namespace.
On failure it preserves partial assets and writes `native-import.json`; do not
blindly rerun. The importing root owns scene placement, noncollision settings,
save/reopen, visual review and publishing.

## Acceptance limits

Offline checks cover positive signed component volume, welded closed edges,
nondegenerate triangles/UVs, unit normals, normal/winding agreement, OBJ index
validity and exact canonical bounds after adapter reversal. Intersections
between carving pieces are intentional; this is not a Boolean-unioned solid.
The orthographic software preview displays authored geometry with illustrative
colors, without native shadows, Lumen or production wood texture. Native import,
grazing-angle shading, human-scale readability, material appearance, LOD,
performance, collision and packaged acceptance are pending. The many separate
editable groups are combined on native import; they are not separate actors.
