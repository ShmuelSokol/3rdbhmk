# cinematics-review

Evidence for the two release features added on 2026-09-08: the cinematic intro and photo
mode.

* `INTRO-EAST-GATE-SOURCE-20260908.md` — why the intro enters from the east through the
  precinct east gate (Yechezkel 43:1-4), what is sourced and what is authored.

* `cinematics-design-eastgate-*.json` — offline design evidence for the shipped east-gate route;
  `cinematics-design-20260908T111148Z.json` is the superseded west route.

* `cinematics-design-*.json` — offline design evidence, produced with no engine running.
  The intro spline is rebuilt in pure Python and measured: total length, even-speed
  spread, the single crossing of the inner court wall line, the arrival error at
  Mikdash_PlayerStart, and the largest uniform inflation of the eighteen blocking boxes
  the path still clears. The photo mode leash battery is in the same file.

* `release-intro-sequence-*.json` — written by `Scripts/release_intro_sequence.py` when it
  runs in the editor. Records the checkpoint, the authored Level Sequence assets, the
  camera cut binding, and the numeric readback of every transform key out of the reopened
  asset.

* `release-photo-mode-*.json` — written by `Scripts/release_photo_mode.py`. Records the
  measured world bounds, the writability probe of the photo directory, and for each
  reference still the PNG signature, IHDR dimensions against the expected multiplier, and
  a flat-frame probe.

* `photo-mode-stills/` — the reference PNGs those runs produce, at 1x, 2x and 4x.

Nothing in this folder is a visual acceptance. Every file here says what it measured and
what it did not.
