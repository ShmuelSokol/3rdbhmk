<#
    Produce a checkpoint archive with bounded startup evidence, not quality acceptance.

    Why this exists: Shmuel asked (9 Sep) for periodic production-ready checkpoints so a
    session limit never leaves him without an updated playable version. This is the
    Attempt4 cook recipe (the only one that ever passed) generalised so it can run again
    and again. Record project dependency bytes before/after cook and reject changes;
    these scans do not isolate the filesystem from concurrent writers.

    Kept from Attempt4 because each line was paid for:
      * cmd /c RunUAT.bat from the BatchFiles directory (never Git Bash - UAT mangles paths)
      * -cookprocesscount=1 (a second cook process is what OOMs this 16 GB box)
      * -maxPartitionSize=1800000000 (keeps pak parts under the 2 GB GitHub asset limit)
      * hash the CHILD exe under Binaries\Win64, not the launcher stub in the archive root
      * refuse to start while any editor/UAT/game process holds the native slot

        .\Checkpoint-Build.ps1 -Label cp03            # cook, archive, smoke-test
        .\Checkpoint-Build.ps1 -Label cp03 -WaitMinutes 90
#>
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [int]$WaitMinutes = 60,
    [double]$NeedGB = 4.0,   # this box idles near 4.3 GB free; 6 GB never arrives and only DEFERs
    [switch]$SkipSmoke,
    [switch]$LowMemory,
    # Material-only checkpoint using the already verified binaries. Does NOT include
    # pending C++ changes; this distinction is recorded in the checkpoint receipt.
    [switch]$UseExistingBinaries,
    # Use filesystem cooked output if Zen staging reports missing op attachments.
    [switch]$SkipZenStore,
    # Additional workspace/growth headroom beyond TWO copies of the largest archive.
    [ValidateRange(1, 100000)][double]$DiskReserveGiB = 10
)
$ErrorActionPreference = 'Stop'

$project = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
$stamp   = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$job     = "C:\Mikdash\Working-5.8\Checkpoint-$Label-$stamp"
$archive = "C:\Mikdash\Builds\Checkpoint-$Label-$stamp"
$mapPkg  = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
$mapFile = Join-Path $project 'Content\MikdashV3\Amah48Candidate_20260908T144034771385Z\Maps\Walkthrough.umap'
$mainFile= Join-Path $project 'Content\MikdashV3\IntegratedReviewV2\Maps\Walkthrough.umap'

function Free-GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1) }
function Commit-Free-GB {
    $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    [math]::Round(($memory.CommitLimit - $memory.CommittedBytes) / 1GB, 2)
}

function Get-DependencyManifest([string]$ProjectRoot, [bool]$ExistingBinaries) {
    # Authoritative project inputs, including native plugin source and all content
    # (not just the selected map). Engine/SDK installations are outside this scope.
    # This is change detection, NOT a filesystem snapshot or a lock against writers.
    $base = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\', '/')
    Assert-PackagingInputs $base
    $files = [Collections.Generic.List[object]]::new()
    $pending = [Collections.Generic.Stack[string]]::new()
    foreach ($name in @('Content', 'Config', 'Source', 'Build', 'Shaders', 'Plugins')) {
        $path = Join-Path $base $name
        if (Test-Path -LiteralPath $path) { $pending.Push($path) }
    }
    if ($ExistingBinaries -and (Test-Path -LiteralPath (Join-Path $base 'Binaries'))) {
        $pending.Push((Join-Path $base 'Binaries'))
    }
    $descriptor = Join-Path $base 'MikdashCourtyardV3.uproject'
    $projectSettings = Get-Content -LiteralPath $descriptor -Raw | ConvertFrom-Json
    if ($projectSettings.AdditionalPluginDirectories -or $projectSettings.AdditionalRootDirectories) {
        throw 'External project/plugin roots require an explicit manifest policy; refusing incomplete dependency coverage.'
    }
    $files.Add((Get-Item -LiteralPath $descriptor))
    while ($pending.Count) {
        $dir = Get-Item -LiteralPath $pending.Pop() -Force
        if ($dir.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Dependency reparse point: $($dir.FullName)" }
        foreach ($item in Get-ChildItem -LiteralPath $dir.FullName -Force) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Dependency reparse point: $($item.FullName)" }
            if ($item.PSIsContainer) {
                $relative = $item.FullName.Substring($base.Length + 1).Replace('\', '/')
                if ($relative -like 'Plugins/*' -and
                    ($item.Name -in @('Intermediate', 'Saved', 'DerivedDataCache', '.git') -or
                     ($item.Name -eq 'Binaries' -and -not $ExistingBinaries))) { continue }
                $pending.Push($item.FullName)
            } else { $files.Add($item) }
        }
    }
    foreach ($file in ($files | Sort-Object FullName)) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Dependency reparse point: $($file.FullName)" }
        [ordered]@{
            path = $file.FullName.Substring($base.Length + 1).Replace('\', '/')
            bytes = $file.Length
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
}

function Assert-PackagingInputs([string]$ProjectRoot) {
    # Non-asset staging roots are relative to Content in the packaging INIs.
    # All Content bytes (JSON, fonts, audio, etc.) are in the manifest. Do not
    # silently accept absolute/traversing roots outside that coverage.
    $contentRoot = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'Content')).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    $iniFiles = @(Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'Config') -Recurse -File -Filter '*.ini')
    $pluginsRoot = Join-Path $ProjectRoot 'Plugins'
    if (Test-Path -LiteralPath $pluginsRoot) {
        $iniFiles += @(Get-ChildItem -LiteralPath $pluginsRoot -Recurse -File -Filter '*.ini' |
            Where-Object { $_.FullName -match '[\\/]Config[\\/]' })
    }
    foreach ($ini in $iniFiles) {
        foreach ($line in Get-Content -LiteralPath $ini.FullName) {
            if ($line -notmatch '^\s*[+.!-]?DirectoriesToAlwaysStageAs\w+\s*=\s*(.*)$') { continue }
            $value = $Matches[1]
            if ($value -notmatch '^\(Path="([^"]*)"\)\s*(?:;.*)?$') {
                throw "Unsupported non-asset staging declaration in $($ini.FullName): $line"
            }
            $relative = $Matches[1]
            if (-not $relative) { continue }
            if ($relative -match '[$%{}]') { throw "Unresolved staging path expression is unsupported: $relative" }
            $resolved = [IO.Path]::GetFullPath((Join-Path $contentRoot $relative))
            if ([IO.Path]::IsPathRooted($relative) -or
                -not ($resolved + [IO.Path]::DirectorySeparatorChar).StartsWith($contentRoot, [StringComparison]::OrdinalIgnoreCase)) {
                throw "External non-asset staging root is not covered by the manifest: $relative"
            }
        }
    }
}

function Get-DiskRequirement([long]$ArchiveBytes, [double]$ReserveGiB) {
    if ($ArchiveBytes -le 0 -or $ReserveGiB -lt 1 -or [double]::IsNaN($ReserveGiB) -or [double]::IsInfinity($ReserveGiB)) {
        throw 'A nonempty archive baseline and at least 1 GiB explicit reserve are required.'
    }
    [long][math]::Ceiling(2.0 * $ArchiveBytes + $ReserveGiB * 1GB)
}

function Assert-DiskHeadroom([long]$FreeBytes, [long]$ArchiveBytes, [double]$ReserveGiB) {
    $required = Get-DiskRequirement $ArchiveBytes $ReserveGiB
    if ($FreeBytes -lt $required) {
        throw "Insufficient disk headroom: $FreeBytes bytes free; need $required (two archive copies plus $ReserveGiB GiB reserve). No archives deleted."
    }
    return $required
}

function Assert-FreshDestination([string]$Path) {
    if (Test-Path -LiteralPath $Path) { throw "Refusing existing destination (including hardlinked archives): $Path" }
    $parent = [IO.DirectoryInfo][IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Path))
    while ($parent) {
        if ($parent.Exists -and ($parent.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing destination through reparse point: $($parent.FullName)"
        }
        $parent = $parent.Parent
    }
}

function Test-CheckpointSuccess([string]$Status, [bool]$SmokeSkipped) {
    # Legacy receipt compatibility only; new runs never emit a playable claim.
    ($Status -in @('checkpoint_startup_verified', 'checkpoint_playable') -or
        ($SmokeSkipped -and $Status -eq 'cook_archive_passed_smoke_skipped'))
}

# --- wait for the native slot, do not fight the feature agents for it -------------------
$deadline = (Get-Date).AddMinutes($WaitMinutes)
while ($true) {
    $busy = @(Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3, AutomationTool, UnrealBuildTool -ErrorAction SilentlyContinue)
    # UE 5.8 runs AutomationTool and UnrealBuildTool as dotnet.exe, so the names above never match
    # another agent's cook or build. Two UATs cannot overlap (they share ErrorLog.txt) and UBT is
    # single-instance, so a dotnet process running either one means the slot is taken.
    $busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -ErrorAction SilentlyContinue |
               Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' } |
               ForEach-Object { [pscustomobject]@{ ProcessName = 'dotnet(' + $(if ($_.CommandLine -match 'AutomationTool') { 'UAT' } else { 'UBT' }) + ')' } })
    if (-not $busy.Count) { $busy = $null }
    $commitFree = Commit-Free-GB
    # 10-11 GiB headroom still OOMed both tested profiles on this scene. Require a
    # larger reserve before another attempt; 16 GiB is a guard, not a proven peak.
    if (-not $busy -and (Free-GB) -ge $NeedGB -and (-not $LowMemory -or $commitFree -ge 16)) { break }
    if ((Get-Date) -gt $deadline) {
        $why = if ($busy) { 'native slot held by ' + (($busy | Select-Object -ExpandProperty ProcessName -Unique) -join ',') }
               else { 'physical free {0} GB (need {1}); commit free {2} GiB (LowMemory needs 16)' -f (Free-GB), $NeedGB, $commitFree }
        Write-Output "DEFERRED: $why"
        exit 2
    }
    Start-Sleep -Seconds 30
}

# --- the map that actually ships must still be the configured default -------------------
if (-not (Select-String -LiteralPath (Join-Path $project 'Config\DefaultEngine.ini') `
        -Pattern ('^GameDefaultMap=' + [regex]::Escape($mapPkg) + '$') -Quiet)) {
    throw 'Candidate48 is no longer the configured GameDefaultMap; refusing to ship a build of the wrong map'
}
foreach ($f in @($mapFile, $mainFile)) { if (-not (Test-Path -LiteralPath $f)) { throw "Missing map: $f" } }
$before     = (Get-FileHash -LiteralPath $mapFile  -Algorithm SHA256).Hash.ToLower()
$mainBefore = (Get-FileHash -LiteralPath $mainFile -Algorithm SHA256).Hash.ToLower()

Assert-FreshDestination $job
Assert-FreshDestination $archive
# Read existing archives only. Never prune, overwrite or cook into an old archive:
# its Paks may be hardlinked into a known-good build.
$baseline = $null
foreach ($directory in Get-ChildItem -LiteralPath (Split-Path $archive) -Directory) {
    $windows = Join-Path $directory.FullName 'Windows'
    if (-not (Test-Path -LiteralPath (Join-Path $windows 'MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'))) { continue }
    $bytes = [long]((Get-ChildItem -LiteralPath $windows -Recurse -File -Force | Measure-Object Length -Sum).Sum)
    if (-not $baseline -or $bytes -gt $baseline.bytes) { $baseline = @{ path = $directory.FullName; bytes = $bytes } }
}
if (-not $baseline) { throw 'No existing packaged archive found for disk estimation; refusing an unbounded cook.' }
$volume = [IO.Path]::GetPathRoot($archive)
if ($volume -ne [IO.Path]::GetPathRoot($project)) { throw 'Disk policy requires project workspace and archive on the same volume.' }
$freeBytes = ([IO.DriveInfo]::new($volume)).AvailableFreeSpace
$requiredBytes = Assert-DiskHeadroom $freeBytes $baseline.bytes $DiskReserveGiB
New-Item -ItemType Directory -Path $job -ErrorAction Stop | Out-Null
New-Item -ItemType Directory -Path $archive -ErrorAction Stop | Out-Null
# RunUAT is called by its FULL path, not by name after a cd. This machine has
# NoDefaultCurrentDirectoryInExePath=1 set, so cmd refuses to run an executable found only in
# the current directory: `if exist RunUAT.bat` reports FOUND and `call RunUAT.bat` on the very
# next line reports "is not recognized as an internal or external command". Every historical
# Astra-Cook-*.ps1 in this tree calls it bare and would fail the same way today.
$batchFiles = 'C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles'
# UE 5.8 CookOnTheFlyServer reads these from GEditorIni. They trigger collection
# earlier and bound queued shader work, without changing project/user INI files.
# This is a collection threshold, NOT a hard process memory cap.
$cookerOptions = '-cookprocesscount=1'
if ($SkipZenStore) { $cookerOptions += ' -SkipZenStore' }
if ($LowMemory) {
    # The cooker's memory-triggered full GC has a hardcoded 60-second cooldown.
    # PackagesPerGC takes an earlier path, so a fast cook can still release completed
    # packages inside that minute. Synchronous loading reduces preload breadth 256 ->32.
    $cookerOptions += ' -NoAsyncLoadingThread -ini:Editor:[CookSettings]:MemoryMinFreeVirtual=4096,[CookSettings]:MemoryMinFreePhysical=2048,[CookSettings]:MaxConcurrentShaderJobs=64,[CookSettings]:MaxPrecacheShaderJobs=8,[CookSettings]:SoftGCMinimumPeriodSeconds=5,[CookSettings]:SoftGCTimeFractionBudget=0.15,[CookSettings]:PackagesPerGC=100'
}
$buildOption = if ($UseExistingBinaries) { '' } else { '-build ' }
$command = '"' + $batchFiles + '\RunUAT.bat" BuildCookRun -project="' + $project + '\MikdashCourtyardV3.uproject" -noP4 -platform=Win64 ' +
           '-clientconfig=Development ' + $buildOption + '-cook -map=' + $mapPkg + ' ' +
           '-AdditionalCookerOptions="' + $cookerOptions + '" -AdditionalIoStoreOptions="-maxPartitionSize=1800000000" ' +
           '-stage -pak -iostore -archive -archivedirectory="' + $archive + '" -utf8output -unattended'

$r = [ordered]@{
    status = 'running'; label = $Label; stamp = $stamp
    startedUtc = (Get-Date).ToUniversalTime().ToString('o')
    command = $command; map = $mapPkg
    candidateSha256Before = $before; mainSha256Before = $mainBefore
    archive = $archive; freeGBAtStart = (Free-GB)
    lowMemory = [bool]$LowMemory; commitFreeGiBAtStart = (Commit-Free-GB)
    usesExistingBinaries = [bool]$UseExistingBinaries
    skipZenStore = [bool]$SkipZenStore
    diskPreflight = @{ baselineArchive = $baseline.path; baselineBytes = $baseline.bytes; reserveGiB = $DiskReserveGiB; requiredBytes = $requiredBytes; freeBytes = $freeBytes }
    dependencyScope = 'Project descriptor, Content, Config, Source, Build, Shaders, project Plugins; Binaries included only with UseExistingBinaries. Excludes generated caches and installed engine/SDK. Before/after change detection, NOT filesystem snapshot isolation; transient edits restored between scans may evade detection.'
    binaryScope = $(if ($UseExistingBinaries) { 'Existing binaries only; pending C++ changes are NOT included.' } else { 'BuildCookRun build step requested.' })
    scope = 'Cook + archive + bounded direct-child startup smoke. NOT bootstrap, route, audio or interaction acceptance.'
}
function Save-Receipt { $r | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $job 'checkpoint-receipt.json') -Encoding utf8 }
Save-Receipt

# Written to a .bat rather than passed as a cmd /c string: PowerShell re-quotes any argument
# containing spaces and cmd then strips quotes from what is already a quoted path, so the
# nested quoting collapses. A batch file has no such layer, and it leaves an exact record on
# disk of the command that ran.
$bat = Join-Path $job 'cook.bat'
@(
    '@echo off'
    'cd /d "' + $batchFiles + '"'
    'call ' + $command
    'exit /b %ERRORLEVEL%'
) | Set-Content -LiteralPath $bat -Encoding ascii
$r.batFile = $bat
try {
    if (-not (Test-Path -LiteralPath (Join-Path $batchFiles 'RunUAT.bat'))) {
        throw "RunUAT.bat not found under $batchFiles - is UE 5.8 still installed there?"
    }
    $manifestBefore = Join-Path $job 'dependencies-before.json'
    @(Get-DependencyManifest $project ([bool]$UseExistingBinaries)) | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestBefore -Encoding utf8
    $r.dependenciesBefore = $manifestBefore
    $r.dependenciesSha256Before = (Get-FileHash -LiteralPath $manifestBefore -Algorithm SHA256).Hash.ToLowerInvariant()
    $r.dependenciesCapturedUtc = (Get-Date).ToUniversalTime().ToString('o')
    Save-Receipt
    # Hashing all project content may take time. Recheck the established guards
    # immediately before launch; neither this inventory nor the manifest is a lock.
    $busy = @(Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3, AutomationTool, UnrealBuildTool -ErrorAction SilentlyContinue)
    $busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" |
        Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' })
    if ($busy.Count -or (Free-GB) -lt $NeedGB -or ($LowMemory -and (Commit-Free-GB) -lt 16)) {
        throw 'Native slot or established memory headroom changed during preflight; refusing cook.'
    }
    $r.diskPreflight.freeBytesBeforeCook = ([IO.DriveInfo]::new($volume)).AvailableFreeSpace
    Assert-DiskHeadroom $r.diskPreflight.freeBytesBeforeCook $baseline.bytes $DiskReserveGiB | Out-Null
    if (@(Get-ChildItem -LiteralPath $archive -Force).Count) { throw 'Fresh archive is no longer empty; refusing overwrite.' }
    Save-Receipt
    & $env:COMSPEC /d /c $bat *> (Join-Path $job 'uat.log')
    $r.exitCode = $LASTEXITCODE
} catch {
    $r.error = $_.Exception.Message
    $r.exitCode = 1
} finally {
  try {
    $r.candidateSha256After = (Get-FileHash -LiteralPath $mapFile -Algorithm SHA256).Hash.ToLower()
    $r.mainSha256After = (Get-FileHash -LiteralPath $mainFile -Algorithm SHA256).Hash.ToLower()
    $r.mainMapChangedDuringCook = ($r.mainSha256After -ne $mainBefore)
    $manifestAfter = Join-Path $job 'dependencies-after.json'
    @(Get-DependencyManifest $project ([bool]$UseExistingBinaries)) | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestAfter -Encoding utf8
    $r.dependenciesAfter = $manifestAfter
    $r.dependenciesSha256After = (Get-FileHash -LiteralPath $manifestAfter -Algorithm SHA256).Hash.ToLowerInvariant()
    $r.dependenciesVerifiedUtc = (Get-Date).ToUniversalTime().ToString('o')
    $r.dependenciesUnchanged = ($r.dependenciesSha256Before -and $r.dependenciesSha256Before -eq $r.dependenciesSha256After)
    $child = Join-Path $archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
    $r.childExists = Test-Path -LiteralPath $child
    if ($r.childExists) {
        $r.child = $child
        $r.childSha256 = (Get-FileHash -LiteralPath $child -Algorithm SHA256).Hash.ToLower()
        $r.archiveBytes = [int64]((Get-ChildItem -LiteralPath (Join-Path $archive 'Windows') -Recurse -File |
                                   Measure-Object Length -Sum).Sum)
    }
    $cookOk = ($r.exitCode -eq 0 -and $r.childExists -and $r.candidateSha256After -eq $before -and
               $r.mainSha256After -eq $mainBefore -and $r.dependenciesUnchanged)
    $r.status = if ($cookOk) { 'cook_archive_passed_smoke_pending' } else { 'failed' }
  } catch {
    $cookOk = $false
    $r.status = 'failed'
    $r.verificationError = $_.Exception.Message
  }
    Save-Receipt
}

# --- bounded direct-child startup smoke (does not test the bootstrap launcher) -----------
if ($cookOk -and -not $SkipSmoke) {
  try {
    $smokeReceipt = Join-Path $job 'smoke-receipt.json'
    $global:LASTEXITCODE = 0
    & (Join-Path $PSScriptRoot 'Smoke-Build.ps1') -Archive $archive -ReceiptPath $smokeReceipt | Out-Null
    $r.smokeExitCode = $global:LASTEXITCODE
    if (Test-Path -LiteralPath $smokeReceipt) {
        $smoke = Get-Content -LiteralPath $smokeReceipt -Raw | ConvertFrom-Json
        $r.smoke = $smoke
        $r.status = if ($smoke.status -in @('startup_verified', 'playable') -and $r.smokeExitCode -eq 0) { 'checkpoint_startup_verified' }
                    else { 'cook_passed_but_smoke_' + $smoke.status }
    } else {
        $r.status = 'cook_passed_but_smoke_did_not_report'
    }
  } catch {
    $r.status = 'cook_passed_but_smoke_error'
    $r.smokeError = $_.Exception.Message
  }
} elseif ($cookOk -and $SkipSmoke) {
    $r.status = 'cook_archive_passed_smoke_skipped'
}
$r.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
Save-Receipt
Copy-Item -LiteralPath (Join-Path $job 'checkpoint-receipt.json') `
          -Destination (Join-Path $project ("SourceAssets\build-review\checkpoint-$Label-$stamp.json"))

Write-Output ($r | ConvertTo-Json -Depth 6)
if (-not (Test-CheckpointSuccess $r.status ([bool]$SkipSmoke))) { exit 1 }
exit 0
