# Browser walkthrough

A light version of the Mikdash that runs in any current phone or desktop browser. Nothing is
installed and nothing is streamed: the visitor's own device draws it, so it costs nothing to
host and any number of people can walk at once.

It is built from the same measured sources as the Unreal project:

| Shown | Source |
| --- | --- |
| The building, 2,633 parts | `unreal/MikdashCourtyardV3/SourceAssets/architecture.fbx` and its manifest |
| Menorah, Shulchan, golden altar, paroches | `SourceAssets/vessels-review`, `SourceAssets/sanctuary-detail/DoorsParochesV1` |
| The 18 tour stops and their text | `SourceAssets/tour-review/tour-stops.json` |
| The 76 source notes | `SourceAssets/tour-review/codex-entries.json` |

It does not have the city, the people or sound. Those stay in the Windows build.

## Commands

```
npm install
npm run assets   # rebuild public/assets and src/data from SourceAssets (only after a source change)
npm run city     # rebuild the Old City, terrain and Mount platform (city.glb, terrain.png, citymap.png, site.json)
npm run build    # bundle into ../docs
npm run serve    # preview at http://localhost:4173/
npm test         # headless browser: walks all 18 stops, checks walls, panels and the phone layout
```

`../docs` is the finished site. To put it online for free, turn on GitHub Pages for the
`docs` folder of `main` (repository Settings, Pages).

## Where things are

- `tools/build-city.mjs` turns the Old City facade shells, lane surfaces, surveyed terrain tiles, Mount
  platform and stepped precinct wall into what the browser loads. The facade exports are detail only
  (windows, doors, cornices), so the script rebuilds each house as a solid with its own roof height,
  replaces every opening with one shader-drawn panel, and lists what stands on the roofs (water tanks
  with solar panels, domes, planters).
- `tools/build-assets.mjs` converts the FBX and OBJ sources into one compressed `mikdash.glb`,
  a top-down height map (`roof.png`, used for soft sky shadowing) and the plan (`plan.png`).
- `src/materials.js` draws stone, paving, gold, cedar and the paroches procedurally, so no
  block of stone repeats and no texture files are downloaded.
- `src/player.js` is walking and dove flight with collision. `src/input.js` is keyboard,
  mouse, touch joystick and gamepad.
- `src/ui.js` and `public/styles.css` are the welcome screen, tour card, plan and panels.

Two things are this version's own choices and not in the source model: the gilded palm panels
on the Heikhal walls (Yechezkel 41:18-20 describes them; the model leaves the walls plain)
and the cedar coffers of its ceiling. The paroches is closed and nothing is modelled behind it.

## Credits

The stone surface scans in `public/assets/stone_*.jpg` and `brick_*.jpg` are the Poly Haven textures
`worn_rock_natural_01` and `white_sandstone_bricks_03` (CC0, public domain, polyhaven.com). All sound is
synthesised in the browser (`src/sound.js`); there are no recordings.
