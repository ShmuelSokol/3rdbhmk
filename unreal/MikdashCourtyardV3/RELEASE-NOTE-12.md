# Walkthrough-12 — published Windows development preview

Public release: https://github.com/ShmuelSokol/3rdbhmk/releases/tag/walkthrough-12-preview

Windows12 Attempt4 cook/archive, staging and packaged startup passed on
9 September 2026. The configured game/editor/cook map is Selected48, using the exact
0.48 m amah. Legacy Main50 remains retained. Both map files were unchanged by cook.

The loose-file staging gate passed: distribution help/credits and localisation
match their source bytes, executables exist, and native IoStore parts meet the
1.8 GB partition bound. Local and anonymous remote download/extraction verification
passed63payloads with byte coverage of59original packaged files. The downloaded
child passed bounded startup, exited0 and preserved original saves.

Historical Attempt2 startup loaded the correct Selected48 default but failed:
six original KotelSurfacePolishV2 materials (`M_KotelSurface_0` through `_5`)
warned that Nanite usage was missing and default material would be used. The narrow
source repair passed fresh-process verification and Attempt3 startup passed.
The five original photo assets and four candidate photo cook clones are separate.

Attempt2 UI review also showed an invisible menu. Source diagnosis:
native menu construction ran in NativeConstruct after Unreal had already captured
an empty Slate spacer. The RebuildWidget lifecycle fix now passes both compilation
and bounded actual packaged interaction: Enter activated Begin, Space skipped the
intro at 18.9 seconds, P opened pause, Escape resumed, F entered dove flight, F
returned to walking, and mouse Quit closed normally. This does not establish full
route, settings, preparation lesson or audio acceptance.

Attempt3 screenshots showed the full preparation label overflowing its Main/Pause
button. The wrapping/width constraint fix passes both compilation and Attempt4 Main/Pause
rendered verification at observed1920x1080; wording and text scaling are preserved.

The App and two Data ZIPs are published. Extract all three into the same directory
with their internal paths intact. Production-quality completion is not claimed.
The scheduled heartbeat is paused; this is the requested publication/handoff stop.

Known limitations remain: sparse/simple people, unfinished paving/haze and broad
visual polish; Kotel photo aspect/joint mismatch; bird audio/perch visuals not
accepted; bridge figures are separate from skeletal residents. The grounded service
completed its bounded route but remains startupOFF pending foot planting, garments
and service animation review. This is an architectural development preview, not
halachic certification or a claim of a fully sourced future reconstruction.

Evidence:
- `SourceAssets/build-review/windows12-download-manifest.json`
- `SourceAssets/build-review/windows12-download-local.json`
- `SourceAssets/build-review/windows12-download-remote.json`
- `SourceAssets/build-review/windows12-downloaded-startup.json`
- Downloaded child SHA256: `329a2d910a531779f07721c0d978693d3fd50b57350d15a0465eed53b542bb63`.
- `SourceAssets/build-review/windows12-attempt2-cook-20260909T104356.json`
- `SourceAssets/build-review/windows12-staging-20260909.json`
- `SourceAssets/build-review/windows12-attempt2-startup-failed-20260909T104532.json`
- Cook log retained locally: `C:/Mikdash/Working-5.8/RuntimeBuild-12-Attempt2/uat.log`,
  SHA256 `ccefe26beddfa4abc8e08a409775fd16dc6f544f24ebf5b16dfd696dad0a3a37`.
- Startup log retained locally: `C:/Mikdash/Working-5.8/RuntimeBuild-12-Attempt2/StartupSmoke/runtime.log`,
  SHA256 `600635f25818db91aa419bb3f6be453714d3cbaefdc297ce9ba1851e35e6ceea`.
