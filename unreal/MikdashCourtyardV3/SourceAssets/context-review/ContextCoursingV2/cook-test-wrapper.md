# Isolated material cook wrapper — 15 September 2026

`Scripts/Test-ContextMaterialCook.ps1` prepares one unique study under
`C:/Mikdash/Working-5.8/ContextPatchStudies`. Its default explicit request is only
`M_Context_CityWall`, with hard dependencies retained. The optional `-Material`
accepts one of the three edited masters, never a map or arbitrary package list.
No asset mutation, staging, container creation, or deployment is implemented.

Coordinator recipe, after the serial native slot is released:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Scripts/Test-ContextMaterialCook.ps1 -PlanOnly
powershell -NoProfile -ExecutionPolicy Bypass -File Scripts/Test-ContextMaterialCook.ps1
```

The default launch requires at least 9 GiB free system commit. A one-second
watchdog stops at a 2 GiB reserve, **6.5 GiB aggregate private memory for the
entire owned job**, or 600 seconds. The timeout can be shortened, never raised
above 600. Free commit uses Windows `GetPerformanceInfo` commit limit minus
commit total, multiplied by page size. This is a sampled guard, not an assertion
that a workload cannot allocate between samples.

An explicit `-Constrained` profile is available for this single-material
experiment after two preflights refused the default threshold without launching
Unreal (observed baseline approximately 8.9 GiB). It requires 8.5 GiB free commit,
caps aggregate owned private memory at 5.5 GiB, and retains **2.5 GiB** of system
commit. Its 8.5 - 5.5 - 2.5 = 0.5 GiB initial cushion accompanies a 1 GiB smaller
job budget and 0.5 GiB larger reserve. It is a tighter workload allocation;
it does not change the default 9/6.5/2 profile or any full-cook guard. The selected
profile drives the printed plan, receipt, preflight and watchdog through the same
limits object. Example: append `-Constrained -PlanOnly` to inspect it, then the
coordinator may launch with `-Constrained` alone. Native memory behavior remains
to be measured.

The process starts suspended and hidden, enters a non-breakaway Windows job with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, then resumes. All child shader workers are
included in the job; job membership and process birth times are recorded.
Closing the wrapper/job kills remaining owned processes even after an error.
No UAC, service operation, machine restart, or unrelated process termination is
used. All Unreal executables, ShaderCompileWorker, UBT/UAT and **all dotnet**
processes block launch; the dotnet check is deliberately conservative.

Before and after the attempt, the study retains full SHA256 values for all 20
project maps and all three source masters, plus names/sizes/UTC modification
ticks for every file in project `Content`. It records engine version, executable
SHA256, exact argument vector, memory high-water marks, output file SHA256s,
package-output census, package/request log rows, and failures. It does not hash
every large source asset: unchanged Content metadata is weaker evidence than a
whole-content byte comparison. DDC and project Saved/Intermediate changes are
outside this production-Content comparison.

`cook-passed-package-review-pending` requires exit zero, the engine's zero-error
success summary, no fatal/error log, requested material in the cooker log and
filesystem outputs, one local shader worker confirmed by log, no observed map
request/load, no `.umap` output, and unchanged protected source evidence.
Dependency expansion is listed for review; success does not approve shipping
all resulting packages. Logs are evidence for observed requests, not proof that
an unlogged code path never accessed a map. No packaged shader or visual
acceptance is inferred. Failed study folders are retained.

Installed UE source supports the selected options:

- `CookCommandlet.cpp:334–367,425–474`: OutputDir, Package, SkipZenStore,
  CookSinglePackage and CookSkipRequests; see `asset-patch-plan.md`.
- `CookOnTheFlyServer.cpp:6479–6490`: `cookshowpackagenames` and
  `cookshowinstigators`; `CookSavePackage.cpp:408–420`: exact `Cooking /Package`
  logging; `CookOnTheFlyServer.cpp:411`: verbose request filename logging.
- `LaunchEngineLoop.cpp:4203–4208`: success/failure summary text.
- `AsyncPackageLoader.cpp:135–147`: `NoAsyncLoadingThread` in editor settings.
- `ShaderCompiler.cpp:1224–1266`: unused-thread settings and commandlet handling.
  Reserve 999 threads to select one worker; <=4-core hosts are refused because
  that engine branch overrides the setting. Memory-pressure thread recalculation
  is explicitly disabled; no shader-format/global-renderer configuration changes.
- Each comma-delimited command-line INI assignment repeats its section prefix;
  omitting it for subsequent keys is not a valid override recipe here.

Offline verification command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Scripts/Test-ContextMaterialCook.ps1 -SelfTest
```

It compiles the C# interop helper and checks both memory profiles and the constrained
cushion/reserve, quoting, positive cook census,
long-package map detection, filename map detection, map-load detection, and
shader-error detection. `-PlanOnly` was also exercised. Ten offline assertions and both default/constrained plans passed. Neither mode starts
Unreal or any helper process. Actual Windows job launch/child cleanup and the
single-material cook remain native experiment checks for the coordinator.

## Explicit audited family cook

`-AllCoursingFamilies -Constrained -DependencyAuditReceipt <path>` opts into
exactly 13 explicit `-Package=` requests (three masters plus ten native-audited
instances, joined with `+`). The default remains one master; `-Material` cannot
be combined with this opt-in. No directory or map cook is introduced, and the
8.5/5.5/2.5 GiB profile and 600-second bound remain unchanged.

The wrapper calls the offline builder's shared `--validate-audit` validator.
It pins dependency receipt SHA256
`091504419cf3faaa97213b259c5d2cf208550e3ee552066a5d3e06fa331c6467`
and audit script SHA256
`379c87445600ded87af57532fee67945329ca60fcdb4ace06fea5eb5fa7704ce`.
The validator requires passing native status, preserved source evidence, exactly
three roots and ten matching descendants from both native discovery methods,
and all 13 current source hashes matching the audit. Other unknown-parent
instances are excluded. Validation runs for the plan and again immediately
before launch. The receipt records the pinned audit, every requested package,
and before/after hashes of all requested sources. Every requested `.uasset`
and `.uexp` must appear in the output census before cook acceptance.

Example plan (offline Python validation only; no Unreal):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Scripts/Test-ContextMaterialCook.ps1 -AllCoursingFamilies -Constrained -DependencyAuditReceipt SourceAssets/context-review/ContextCoursingV2/dependency-audit-20260915T174543Z-34988.json -PlanOnly
```

The expanded recipe is prepared for coordinator use after the first-master A/B/A
test; it was not launched during implementation. Default and family plans,
10 wrapper assertions, and 20 builder/audit tests passed offline.
