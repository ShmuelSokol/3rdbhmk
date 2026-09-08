# The intro enters through the east gate — source and what is authored

Date 2026-09-08. Offline: no editor launched, nothing committed.

## What is sourced

The intro approaches the precinct from the east and enters through the east gate of the
3,000-amah wall. That direction is not taste; it is the text:

* **Yechezkel 43:1** — "Then he brought me to the gate, the gate that faces toward the east."
* **Yechezkel 43:2** — "And behold, the glory of the God of Israel came from the way of the
  east; and His voice was like the sound of many waters, and the earth shone with His glory."
* **Yechezkel 43:4** — "And the glory of the LORD came into the House by the way of the gate
  whose face is toward the east."
* **Yechezkel 42:15** — the measuring of the outer precinct is completed by going *out*
  through the east gate ("he brought me out by the way of the gate that faces east, and
  measured it round about"), which is why the enclosure author put the E gate on the Temple's
  east–west axis in the first place (`SourceAssets/enclosure-review/sources.md`, gates table).
* **Yechezkel 44:1-2** — context only: after the glory has entered, the east gate is shut,
  "because the LORD, the God of Israel, has entered by it." The visitor's arrival re-enacts
  the direction of that entry; it does not depict the glory.

Everything else about the approach is a consequence of geometry already in receipts:

| fact | value | receipt |
|---|---|---|
| E gate position | UE (116 900, 0), on the axis Y 0 | `enclosure-review/precinct-Main50.json` gates[E] |
| gate module | opening 10 x 50 amot = 500 x 2500 cm, piers 10 amot, total 60 amot = 3000 cm, depth 6 amot; mesh bounds local X ±780, Y −171..+180, Z 0..3000 | `enclosure-review/geometry-manifest.json` meshes[SM_EnclosureV2_Gate]; `native-enclosure-Main50-20260908T211423791852Z.json` reopenedReadback |
| gate plinth (threshold) | Z 3551.4 cm reconstructed from the baked ground profile with `GroundSpan` over the 1500 cm gate block (receipt states 783.6 m a.s.l. = 3560 cm; the 9 cm difference is subsample count and is inside every margin below) | `precinct-Main50.json` groundProfile side 1; `EnclosureMath.h` `GroundSpan` |
| gate module in world | X 116 549 .. 116 900 (wall centre 116 720), piers at \|Y\| 250..780 to Z 6551, lintel Z 6051..6551 over \|Y\| < 250 | derived from the above |
| axis west of the gate | Mount of Olives ridge, ground to ≈5100 cm at X 78–86 k; Kidron floor ≈ −6000 cm at X 26–32 k; Mount platform deck Z 0 to X ≈14 953 | `jerusalem.json` DEM (sha 76a2b76c…), `FutureMountV1/mount-platform.mesh.json` |
| court east gate on the axis | perimeter/lintel band X 7800..8100 top 3425, vestibule walls to 2800 at \|Y\| 325..625 | `architecture-manifest.json` |
| arrival | Mikdash_PlayerStart [2100, 0], eye 668 | `visual-review/release-capture-20260908T023600Z/receipt.json` view b |

## What is AUTHORED (the camera choreography)

The verses give a direction and a gate. They do not give a camera. All of the following is
this project's authoring and is labelled so in `Scripts/release_intro_sequence.spec.json`:

* the start point over the eastern slope of the Mount of Olives and its height;
* the descent to gate height so the 30 m gate reads as a threshold, and the height through
  the opening (mid-opening, 1250 cm above the threshold, 1250 cm below the lintel);
* the climb over the Olives ridge and the descent across the Kidron to the platform;
* passing OVER the court's own east gate (its opening is 6.5 m wide with open leaves at
  ±2.6 m — too narrow to thread at speed with a 150 cm margin) and the dive to the inner
  eastern gate, which IS threaded on the axis as before;
* all timings, eases, the aim points and the field of view.

## Modern state

When the enclosure is toggled to MODERN the wall and gate vanish and the modern buildings
inside the precinct return. The path is checked against the modern building tops along the
axis corridor (real extruded geometry from `jerusalem-meshes.json`, sha cec2748b…, not the
sparse OSM height tags) as well as against the wall, so the same path is valid in both
states. The numbers are in the design receipt beside this file.
