# Lighting polish design - combined Walkthrough map (2026-09-07)

Target: `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`. Reviewed renders:
`SourceAssets/visual-review/release-capture-20260907T194843Z/` (map SHA-256 `504bf402...`).
Applied by `Scripts/release_lighting_polish.py` from `Scripts/release_lighting_polish.spec.json`;
this note explains the choices. Every value is a proposal for visual review, not an accepted look.

## Current state (from the receipts and live readback)

- One `DirectionalLight` 20,000 lux, atmosphere sun, movable; `SkyAtmosphere`; `SkyLight` real-time
  capture, intensity 1, lower hemisphere black; `VolumetricCloud` on the donor `MI_Cloud`; one
  `PostProcessVolume` with MANUAL exposure (ISO 100, 1/125 s, f/8 = EV 13) plus the reviewed +1 stop
  bias (effective EV 12), interior histogram fields carried over from the pilot, Lumen GI and reflections;
  virtual shadow maps; no `ExponentialHeightFog`. `RELEASE_KodeshInteriorLight` 1200 cd (kept).
- The gold veneers (`M_Sanctuary_gold`, `M_KeruvFrieze*`) have no emissive: constant gold, metallic 1,
  roughness 0.34-0.45. The white Heikhal end wall in render d is therefore not glow; it is the Kodesh
  partition (X -5700..-5600, Z 925..2925) lit directly through the 5 x 25 m doorway and clipped at EV 12.

## Problem -> decision, per render

| Render | Problem seen | Decision | Why it should work |
|---|---|---|---|
| a exterior wide, i overhead | Flat noon light, uniform cream terrain and city, no depth | Sun to 30 deg elevation (morning az 110 default; afternoon az 250 alternative); cloud shadows on the sun (0.6); height fog 0.005 with warm SkyAtmosphere tint, aerial perspective x1.8, Mie x1.25 | Low sun turns every parapet, stair and street edge into a shadow line; cloud patches break the terrain tone; fog and aerial perspective make the far city recede and separate the Mount from the ridge |
| b spawn west, c outer court | Washed-out bright walls, weak shadow shaping, blown stone | Histogram auto exposure bounded EV 8-14, bias 0; filmic slope 0.9 / toe 0.55 / shoulder 0.26; light source angle 0.5 deg; contact shadows 0.02; bloom 0.3 | Bright stone now meters near EV 13-14 instead of a hand-set EV 12; the shoulder rolls the highlights; the small source angle gives crisp VSM penumbrae; contact shadows seat the pilgrims and the stair nosings |
| d Heikhal west | Blown-out white end wall, noisy gold | Same exposure + shoulder; warm 25,000 cd rect fill just inside the doorway (Movable, shadows on, specular 0.25); Lumen reflection quality 1.5, final gather 1.25, scene detail 1.5 | The fill lifts the gold side walls so the meter sees a smaller ratio and the partition compresses instead of clipping; higher Lumen quality reduces speckle on metallic surfaces. The afternoon preset removes the direct beam entirely if the residual patch still reads as a fault |
| e Kodesh | Noisy gold, saturated flat gold | Lumen settings above; Kodesh point light untouched; min EV 8 | Kodesh is closed; metering floors at EV 8 so the room stays a warm interior rather than adapting to noon |
| g Mount platform approach | Facade flat, reveals without shadow, blue sky slot | Morning sun az 110 rakes the east facade; contact shadows; fog start 30 m so the court stays clear | East-facing gates were the reason for the morning default |

## Sun geometry

World frame: +X east, +Y south (west is UE -X per the capture receipt; the bus on Batei Mahase road sits at +Y).
Light travel direction `d = (-sin az cos el, cos az cos el, -sin el)`; actor rotator pitch = -el,
yaw = atan2(d.y, d.x). Morning az 110 / el 30 -> pitch -30, yaw -160. Afternoon az 250 / el 27 ->
pitch -27, yaw -20. The receipt records azimuth, elevation, rotator and the read-back forward vector
(dot >= 0.99999 required). 30 klux at 5000 K keeps physical sun/sky ratios; the absolute level is an
exposure-headroom choice, not a brightness claim.

## Exposure units

`r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange` reads 0 in this project, so
`auto_exposure_min/max_brightness` are raw scene luminance, not EV100
(`PostProcessEyeAdaptation.cpp`: extended -> `LuminanceMax * 2^EV`, else raw). The script reads the cvar
at run time, writes `2^EV` (256 / 16384) when it is 0 and `8 / 14` when it is 1, and records both forms.
Recommendation for a later config pass: set the cvar to 1 in `DefaultEngine.ini` and rerun so the map
carries EV values that are readable in the editor UI.

## Optional HDRI

`kiara_4_mid-morning_2k.hdr` (Poly Haven, CC0, Greg Zaal; provenance JSON alongside) for `-UseHdri`:
SkyLight to `SLS_SpecifiedCubemap`, intensity scaled to 2500 (relative HDRI vs 30 klux sun), real-time
capture off. Default off: it gives richer reflections on the gold but decouples the sky from the chosen
sun. `goegap` (midday desert) was rejected for its high sun.

## Costs and risks

- Cloud shadows, volumetric fog (200 m) and Lumen quality 1.5/1.25 add roughly 3-5 ms at 1080p on an
  RTX 2070 with software Lumen. Fallback order: final gather 1.0, reflection quality 1.0, volumetric fog
  distance 10000, cloud shadows off.
- Auto exposure in the interiors depends on the histogram percentiles carried over from the pilot
  (recorded, not changed). If the Kodesh reads dark, lower `minEV100` to 7 before touching lights.
- Fog density is scene-scale sensitive; if the Kotel plaza reads milky, halve `fog_density` before
  changing `fog_height_falloff`.
- The fill light is authored, not sourced; it is Movable so no lighting build is implied.
- Everything is reverted by `-LightingRevert` from the recorded before-values (created actors are
  destroyed; the duplicated cloud MI and any imported HDRI stay on disk in the lighting namespace and are
  listed in the revert receipt).
