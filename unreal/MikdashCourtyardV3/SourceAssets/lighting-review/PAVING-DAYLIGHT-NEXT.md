# Next bounded daylight comparison

**Recommendation: compare a cooler sun with modest sky fill while keeping sun energy, sun angle and exposure at their recorded baseline.** This is a proposed test, not an accepted lighting fix.

I viewed `runtime-diagnostic-20260908T164151Z.png`: paving joints remain legible, but the sunlit background walls are strongly cream/amber with broad areas of little visible detail; the left wall/figure remain much darker. This supports testing color and direct-to-indirect contrast. It does not prove numerical HDR clipping: the screenshot is tone-mapped and bright wall material may itself have little detail.

I also viewed Heikhal155837 and155859. The second is the existing 6500K/45000lux/pitch−50/sky1.3 study. Both remain gold/amber; the second makes the rear wall and table visibly brighter while leaving the curtain and menorah readable. The retained warm gold material and the interior fill are plausible contributors; cooling sunlight alone did not remove the interior cast. Do not desaturate gold materials to make limestone white.

Evidence: `native-frontend-flight-20260908T155753209529Z.json` (Heikhal),154924406605Z (Mount),160218568196Z (Kotel) record identical baseline sun30000lux,5000K,useTemperature=true,rotation[−30,−160,0],sky1.0 and identical candidate45000lux,6500K,[−50,−160,0],sky1.3. Each has empty errors, PIE ended and unchanged map bytes. They establish a completed comparison, not acceptance; increasing direct sun1.5× simultaneously with its angle obscured which change improved the view.

## Exact next preset

In PIE only, require exactly one DirectionalLight and one SkyLight, as `release_reviewed_daylight.py` does. Record their native names before changing anything; the inventory names the sun `V3 daylight sun - 30000 lux 5000 K morning az 110 el 30` (its label is descriptive, not an authoritative current rotation).

- DirectionalLightComponent: `use_temperature=True`, `temperature=6500`, `intensity=30000`; actor rotation `pitch=-30,yaw=-160,roll=0` after matching the live recorded baseline. These preserve actual baseline direct energy/angle and isolate the cooler source.6500 is already tested, not an ephemeris claim.
- SkyLightComponent: `intensity=1.3`, reusing the already-tested modest fill. Preserve its existing source/cubemap, capture settings and color; do not add another sky or interior light.
- Global postprocess: preserve current settings exactly in this first comparison. The14:07 inventory records histogram, min1,max16384,bias0,unbound=true,priority1000. These are serialized property values; the legacy label saying EV0–14 is not sufficient evidence to reinterpret them. Read them live and include the readback in the comparison. Do not switch to manual camera exposure.
- Diagnostic CameraComponent `post_process_blend_weight=0` is essential: the probe already does this. Historical four review cameras instead override manual exposure at blend1 and are unsuitable for judging walking exposure.
- Preserve `RELEASE_KodeshInteriorLight` and the other existing fill.14:07 recorded1200 intensity, temperature disabled and a warm color on the former; later live values must be read rather than assumed. Existing fill-highlight005404 receipt changed a fill25000→15000 and film shoulder.26→.30/whiteclip.04→.02; do not undo those historical changes casually.

Render the same new floor courtyard view, Heikhal westward view and Kotel join with matched poses/FOV and identical bounded warmup in baseline/candidate. Accept only if pale limestone is less amber, highlighted wall detail remains distinguishable, the red curtain/menorah/table/room boundaries remain readable, and dark masonry/figures retain useful contrast. Keep the current architecture/materials fixed. The actual baseline may differ after root's ongoing work: mismatch means record/rebase, not force old values.

If this preset still has washed-out highlights, perform a **separate** comparison changing only global `auto_exposure_bias` from its live0 to−0.3, leaving the above light settings fixed. That is an authored hypothesis (about19% less exposure), not measured calibration. Review all three views again; reject if interior readability deteriorates. The current daylight adoption helper persists only sun/sky, so it cannot adopt an exposure change without separately expanded guards. Do not mix this conditional test into the first preset or promise that it fixes material-level brightness.

No native run, shared script change, asset mutation or new research was performed for this note.
