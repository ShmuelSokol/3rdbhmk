# Walkthrough-12 — development preview, release acceptance pending

Windows12 Attempt2 cooked and archived successfully on 9 September 2026 at
10:43 UTC. The configured game/editor/cook map is Selected48, using the exact
0.48 m amah. Legacy Main50 remains retained. Both map files were unchanged by cook.

The loose-file staging gate passed: distribution help/credits and localisation
match their source bytes, executables exist, and native IoStore parts meet the
1.8 GB partition bound. This establishes staging, not usable gameplay or sharing.

Packaged startup loaded the correct Selected48 default, but **failed acceptance**:
six original KotelSurfacePolishV2 materials (`M_KotelSurface_0` through `_5`)
warned that Nanite usage was missing and default material would be used. A narrow
source repair is being verified; the existing package still contains the defect.
The five original photo assets and four candidate photo cook clones are separate.

The actual packaged UI review also showed an invisible menu. Source diagnosis:
native menu construction ran in NativeConstruct after Unreal had already captured
an empty Slate spacer. The RebuildWidget lifecycle fix passes both editor and game compilation,
**not yet packaged-verified** at this checkpoint. Escape/P on the logical title screen
being ignored is consistent with the existing title-screen input policy.

Before release: material fresh-process verification and dual-target compilation passed; recook to a fresh reviewed output, repeat staging/startup, and physically verify
Begin, pause/resume, dove/return and Quit with visible UI. Then prepare ordinary ZIPs,
verify extraction and payload hashes, and verify the authorized download method.
No downloadable Windows12 release or production-quality completion is claimed.

Known limitations remain: sparse/simple people, unfinished paving/haze and broad
visual polish; Kotel photo aspect/joint mismatch; bird audio/perch visuals not
accepted; bridge figures are separate from skeletal residents. The grounded service
completed its bounded route but remains startupOFF pending foot planting, garments
and service animation review. This is an architectural development preview, not
halachic certification or a claim of a fully sourced future reconstruction.

Evidence:
- `SourceAssets/build-review/windows12-attempt2-cook-20260909T104356.json`
- `SourceAssets/build-review/windows12-staging-20260909.json`
- `SourceAssets/build-review/windows12-attempt2-startup-failed-20260909T104532.json`
- Cook log retained locally: `C:/Mikdash/Working-5.8/RuntimeBuild-12-Attempt2/uat.log`,
  SHA256 `ccefe26beddfa4abc8e08a409775fd16dc6f544f24ebf5b16dfd696dad0a3a37`.
- Startup log retained locally: `C:/Mikdash/Working-5.8/RuntimeBuild-12-Attempt2/StartupSmoke/runtime.log`,
  SHA256 `600635f25818db91aa419bb3f6be453714d3cbaefdc297ce9ba1851e35e6ceea`.
