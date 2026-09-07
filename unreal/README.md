# Native Unreal walkthrough

`MikdashCourtyardV3/` contains the native Unreal project, measured architecture,
Jerusalem context, runtime source, imported assets, and verification records.
The existing web and distribution projects remain at the repository root.

Use Unreal Engine **5.8.2**, Visual Studio 2022 C++ Build Tools (tested MSVC
14.44.35228), Windows SDK (tested 10.0.26100.0), and .NET Framework 4.8 SDK.
Open `MikdashCourtyardV3.uproject` and build the runtime module when requested.
Generated binaries, caches, Intermediate and Saved output are excluded.

## Verified on September 7, 2026

- Runtime plugin compiles for Editor Development, Game Development and Shipping.
- Courtyard saves and reloads with MikdashPlayerController and BP_MikdashWalker.
- Windows BuildCookRun completed build, cook, stage and archive successfully.
- Packaged executable starts and logs its paused, visible-cursor welcome menu.
- Credits are staged in `MikdashCourtyardV3/Content/Distribution/CREDITS.txt`.

The compiled package is local at `C:\Mikdash\Builds\Walkthrough-01\Windows`.
It is not included in Git and has not been published as a GitHub release.
Keyboard/mouse acceptance, audio audition, performance and final visual quality
are still under review. This is a development preview, not studio-quality acceptance.

The source scripts and historical AGENTS.md record paths from the production PC.
Review those path guards before running scripts on another machine. Do not rerun
architecture imports over the saved map. The original transfer remains preserved
separately on that PC; this folder contains the current working project.

Source geometry, modern context and artistic interpretation are distinguished in
the project credits and SourceAssets receipts. The previously rejected synthesized
ambience is preserved but disabled.
