# Windows12 checkpoint — 9 September 2026

Read AGENTS.md, RELEASE-NOTE-12.md and INTEGRATION-QUEUE.md first. Last committed
checkpoint when this handoff was prepared: **733f73c4**. Root coordinates the one
native engine/build slot and publication; do not overlap editor, UBT or cook jobs.

## Safe stopping point

Attempt4 cook, staging, strict startup and wrapped Main/Pause UI checks PASSED.
Owned UI process31484 quit normally; no native job remains. Original saves and maps
are unchanged. No ZIPs or release uploads started. Source checkpoint733f73c4; final
evidence/docs commit follows (discover with git log in publication clone).
Child SHA256: `329a2d910a531779f07721c0d978693d3fd50b57350d15a0465eed53b542bb63`.
Evidence: `SourceAssets/build-review/windows12-attempt4-{cook,staging,startup,ui}-20260909.json`.

Attempt4 job: `C:/Mikdash/Working-5.8/RuntimeBuild-12-Attempt4`.
Attempt4 archive: `C:/Mikdash/Builds/Walkthrough-12-Attempt4/Windows`.

## Already established

- Selected48 is configured for game/editor/cook, using 0.48 m amah; Main50 retained.
- Attempt3 cook, staging and startup passed after six original Kotel material
  Nanite usage flags and native menu lifecycle were repaired.
- Actual Attempt3 input review: Enter Begin, Space intro skip at18.9s, P pause,
  Escape resume, F dove, F return and mouse normal Quit passed. No full-route,
  settings, preparation lesson or audio acceptance follows from these checks.
- Attempt3 showed preparation-label overflow on Main and Pause. Shared menu labels
  now wrap within button width without shortening wording; Attempt4 passed the bounded
  packaged/render acceptance for this change.
- Earlier failures and originals remain preserved. Attempt2 is not releasable.

## Continue distribution only after the final package is accepted

From `C:/Mikdash/Working-5.8/MikdashCourtyardV3`, the following paths were absent
when this file was written. Helpers refuse overwrite; if any now exists, inspect
its receipt and use a new explicit output name rather than deleting it.

```powershell
python Scripts/prepare_windows_preview.py --archive-root C:/Mikdash/Builds/Walkthrough-12-Attempt4/Windows --output-dir C:/Mikdash/Working-5.8/Walkthrough12-Distribution --version Walkthrough-12
python Scripts/verify_windows_preview.py --manifest C:/Mikdash/Working-5.8/Walkthrough12-Distribution/manifest.json --destination C:/Mikdash/Working-5.8/Walkthrough12-LocalExtract --receipt C:/Mikdash/Working-5.8/Walkthrough12-LocalVerify.json --original C:/Mikdash/Builds/Walkthrough-12-Attempt4/Windows
```

Expected three ordinary ZIPs: `Mikdash-Walkthrough-12-App.zip`, `Data01.zip` and
`Data02.zip` with the same prefix. App includes the small global.ucas/global.utoc;
each large native UCAS partition goes in its own Data ZIP. Confirm actual manifest
inventory/sizes rather than assuming counts. Each release asset must stay below
2 GiB. All three extract into the same directory with their existing internal paths.
No binary concatenation, custom downloader or installer is required.

Draft external release body:
`C:/Mikdash/Working-5.8/Walkthrough12-release-body.md`.
Amend its pending-verification sentence only after evidence exists. No new release
has been published by this handoff. Use the authorized ShmuelSokol/3rdbhmk release
workflow; preserve existing releases, never force-push or sweep unrelated files.

After actual upload, substitute the real manifest URL and its locally computed SHA:

```powershell
$manifestPin = (Get-FileHash -LiteralPath C:/Mikdash/Working-5.8/Walkthrough12-Distribution/manifest.json -Algorithm SHA256).Hash.ToLower()
$publishedManifestUrl = 'REPLACE_WITH_ACTUAL_HTTPS_MANIFEST_ASSET_URL'
python Scripts/verify_windows_preview.py --manifest $publishedManifestUrl --manifest-sha256 $manifestPin --download-dir C:/Mikdash/Working-5.8/Walkthrough12-RemoteDownloads --destination C:/Mikdash/Working-5.8/Walkthrough12-RemoteExtract --receipt C:/Mikdash/Working-5.8/Walkthrough12-RemoteVerify.json --original C:/Mikdash/Builds/Walkthrough-12-Attempt4/Windows
```

Remote verification checks bounded downloads, ZIP paths, CRC, hashes and source-file
coverage; it does not launch the extracted game or prove every interaction.

## Remaining limitations

Sparse/simple people, paving and haze still need visual refinement. Kotel photo
projection has aspect/joint mismatch. Bird audio/perches are not accepted. The
transit bridge uses its own figures, not skeletal resident handover. Grounded service
completed18stations but stays startupOFF pending foot planting, authentic garments
and service animations. Candidate broad surface-wear parity is incomplete. Full
routes, settings, preparation lesson, audio and broad performance acceptance are
not established by the packaged input smoke. This remains an architectural
development preview, not production completion or practical halachic authority.

## Root final checkpoint update

Attempt4 results, receipt paths, child SHA and normal process cleanup are recorded
above. Quick gate passed6/6 after these evidence updates. The final evidence/docs
commit is discoverable as the latest commit in C:/Mikdash/GitHub/3rdbhmk; no code
changes followed source733f73c4.
