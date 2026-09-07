# Walkthrough-08 — Astra takeover verification

Verified 2026-09-07. This is an intermediate development build, not a completed cinematic experience or a certified reconstruction. No scene changes were made during this baseline assessment.

## Package and source

- Launch: `C:\Mikdash\Builds\Walkthrough-08\Windows\MikdashCourtyardV3.exe`.
- Actual game: `Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe`, SHA-256 `feffd5582dead64e340c4ff48bba0ecae274c4bbe22a9559e06ef47e99b03b2d`.
- Claude's fresh cook/archive log `C:\Mikdash\Working-5.8\RuntimeBuild-08\uat.log` ends BUILD SUCCESSFUL, AutomationTool exit 0; BuildCookRun 184.64 seconds. This verifies packaging, not runtime completeness.
- Source handoff commit `45218d0`; main implementation commit `445f72f`.
- Baseline working map `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough` SHA-256 `f1568d0aa3cdf017507ac856aa86958867c41928eea9946734949b231c32a3d6`.

## What changed since 07

Claude's handoff and native receipts record Frieze V2, architecture PBR materials, Shulchan V2 with loaves/supports/rods, IncenseAltar V2, separate east-west Aron poles, and a paroches pattern. Baseline rendered views visibly confirm the fuller vessels, long poles and relief walls. Exact dimensions and source interpretation were not independently revalidated in this takeover pass. Five simplified idle pilgrims remain; this is not an autonomous population.

## Verification performed

- The packaged game launched into the welcome menu with a visible cursor. Start resumed the scene. P reopened the paused menu. Preparation opened; P returned to the paused menu rather than falling through into gameplay. Quit closed both game and launcher processes. These were deliberate computer-use inputs, not a passive startup test. Corresponding log markers agree with the observed sequence. Receipt: `SourceAssets/runtime-review/walkthrough-08-astra/launch-receipt.json`. Raw log stays local beside that receipt.
- Current-map native capture: `SourceAssets/visual-review/release-capture-20260907T210550Z/receipt.json`; ten image files, saved map unchanged, editor camera and throttling restored. These are editor renders, not ten packaged-game screenshots.
- Images reviewed: exterior, courtyard/pilgrims, Heikhal vessels, Kodesh/Aron, Kotel face, Mount approach and overhead city. The original bus-labelled view was INVALID as bus evidence: it used an obsolete proposed location and shows a wall. The capture script is being corrected to derive its view from the actual saved bus actors.
- Fresh bounded PIE walking: `SourceAssets/IntegratedReviewV2/release-walk-20260907T211526Z.json`, completed all east-gate and Mount-platform route legs, zero recorded errors, 43.625 seconds, map bytes unchanged. No teleport/flying. This is synthetic CharacterMovement evidence, not continuous physical keyboard or packaged-route acceptance.

## Visual findings and remaining checks

- Kotel detail is hidden by the city-wall slab. Both Kotel diagnostic views identify the occluder; the ground image shows a plain wall. The prepared duplicate-mesh occlusion repair is the first next scene change.
- Gold rooms and vessels are visible, but bright highlights and the Heikhal rear wall are washed out. Relief repetition/seams remain visible; Kodesh rendering is grainy. Lighting polish requires before/after visual review rather than acceptance by parameter readback alone.
- Temple masonry has texture, while much of the city, roads and broad platform remains plain. The prepared city/terrain materials have not been applied in this baseline.
- Five pilgrims look like repeated simplified figures, not a living crowd. Native animation/AI quality was not tested here.
- Audio was not auditioned. Escape, sustained mouse-look, all chambers and packaged continuous walking remain unverified in this pass. No new download/share artifact was certified.
- Enclosure V1 remains on hold because it intersects the modern-city scenario. Do not place it as part of the three prepared cosmetic/occlusion steps.

The next build should be Walkthrough-09 after guarded Kotel repair, lighting and context-material work, new renders/walk checks, fresh cook and packaged verification. Walkthrough-08 is preserved as the baseline.

## Corrected bus view

The capture fix was verified in a real-RHI editor run: SourceAssets/visual-review/release-capture-20260907T211742Z/h_bus_street_level.png now shows the actual saved bus. It looks very dark and faceted, and the wheel/road contact needs review; this is visibility evidence, not visual acceptance. The focused receipt also retains Kotel diagnostics from building the full view inventory; those findings do not mean another map edit occurred. The map remained unchanged.
