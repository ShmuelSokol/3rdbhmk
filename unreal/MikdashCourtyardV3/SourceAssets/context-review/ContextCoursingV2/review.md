# Horizontal Old City stone courses — 15 September 2026

The source limestone images have horizontal courses. The X-facing context projection
used `(world Z, world Y)`, rotating those courses vertically, while Y-facing walls
used `(world X, world Z)`. Corrected X projection: `(world Y, world Z)`.
Albedo and roughness share the corrected coordinates; the normal map uses the same
projection plus the matching world-space reorientation. Y-facing walls and roofs
retain their prior mapping, scale, textures and settings. No new source measurements
or Temple construction claims are introduced.

Scope: M_Context_Building, M_Context_CityWall, and M_CityFacadeV1. Five offline tests
check height/horizontal UV directions, matching albedo/roughness/normal coordinates,
the normal basis on both wall axes, and unchanged roof projection. Independent
verification also exercised 10,000 unperturbed normal directions and signed slopes.

## Native review

Six duplicate review materials were saved in ContextCoursingV2 under MaterialReview.
The native study job used about 1.6 GiB and left all three original masters and all
20 project maps byte-identical. Source textures are existing CC0 Poly Haven assets;
all six relevant texture assets match the publishing clone byte-for-byte. Family
reference photographs are neither included nor used as textures.

Native GPU captures use two cubes: **before on the left, corrected on the right**,
showing both +X and +Y faces. The owned editor opens Engine Entry only, pilots an
explicit camera and checks its actual pose. It destroys the temporary actors and
exits without saving a map. These are material studies, not a packaged city tour.

Rejected captures are retained locally as evidence:
- 135519Z: black frames; no usable visual verification.
- 135927Z: misoriented camera from positional Rotator arguments; no acceptance.
- 140235Z: correctly aimed, but the study's zero exposure bounds blew out the image.

The corrected study uses named Rotator angles, checked camera pose, equal positive
exposure bounds, and zero bloom/vignette. All three 140516Z frames were inspected:
building, old city wall, and CityFacade show vertical courses on the before cube's
X face and horizontal courses on both after faces. The CityFacade procedural openings
still have noisy details in this cube study; that separate shader's visual quality
is not approved here. Different world positions also change its procedural pattern.

The accepted capture log contains a nonfatal viewport realtime-override ensure
(`!bCheckMissingOverride || bRemoved`); the editor completed all captures, checked
maps, and exited normally. The 141449Z rerun also completed all three inspected
images with the checked camera and unchanged maps, but retained that warning.
Installed UE source identifies the cause: EditorSetViewportRealtime(True) removes
a named override; it does not enable realtime, and ensures when none exists. That
unnecessary call is removed. The final helper uses viewport invalidation and an
explicit screenshot camera, with an optional -CoursingSingle smoke mode.
There were no material shader compilation failures in the studies.

Final capture-helper smoke passed: `capture-20260915T141809Z.json` and its building
PNG. The native image was visually inspected, requested camera pose read back,
all20 maps stayed unchanged, and the owned editor exited normally. The smoke log
has no realtime-override ensure, Python error, or material compile failure.
This tests the final helper revision's first-image/cleanup path; the prior three
image runs establish all three material comparisons. AST and five tests passed again
after this helper-only cleanup; no C++ changed after the full gate.

Actual project application succeeded in `native-apply-20260915T140838780528Z.json`:
all three masters saved, exactly two connected code nodes changed per master,
all other nodes/connections unchanged, all20 project maps byte-identical. Backup:
`C:/Mikdash/Working-5.8/ReviewCheckpoints/ContextCoursing-20260915T140838780528Z`.
Fresh-process readback passed in `native-verify-20260915T140917908097Z.json`:
all three masters loaded from disk with corrected connected code, all maps and
masters unchanged by verification. Apply and verify commandlets exited0 with no
errors and the pre-existing Python enum/name warning.

Project verification passed: 7/7 checks, 32/32 standalone math suites, and 5/5
coursing tests. Gate log: verify-final-20260915T141048Z.log.

## Application guards and limitations

The release helper traverses live output connections, because a prior CityFacade
rebuild left disconnected copies of its old graph. It edits only the two connected
Custom-node code strings per master and proves other nodes/connections unchanged.
It checkpoints each master and hashes all project maps before mutation. A separate
fresh process must verify corrected code after saving.

This fixes a surface orientation defect. Floating rooftop fixtures, the apparent
Kotel/Jewish Quarter ground opening, walking routes, stone scale, and full scene
lighting still need their own reviews. No new packaged build or full city visual
acceptance is claimed by this material study.
