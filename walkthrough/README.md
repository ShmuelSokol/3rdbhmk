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
npm run build    # bundle into ../docs
npm run serve    # preview at http://localhost:4173/
npm test         # headless browser: walks all 18 stops, checks walls, panels and the phone layout
```

`../docs` is the finished site. To put it online for free, turn on GitHub Pages for the
`docs` folder of `main` (repository Settings, Pages).

## Where things are

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
