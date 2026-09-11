<#
    Produce a playable checkpoint build the user can download and run.

    Why this exists: Shmuel asked (9 Sep) for periodic production-ready checkpoints so a
    session limit never leaves him without an updated playable version. This is the
    Attempt4 cook recipe (the only one that ever passed) generalised so it can run again
    and again, with the reviewed-bytes pin replaced by a RECORD of whatever bytes were
    current - a checkpoint is meant to capture work in progress, not to refuse it.

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
    [switch]$SkipSmoke
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
    if (-not $busy -and (Free-GB) -ge $NeedGB) { break }
    if ((Get-Date) -gt $deadline) {
        $why = if ($busy) { 'native slot held by ' + (($busy | Select-Object -ExpandProperty ProcessName -Unique) -join ',') }
               else { 'only {0} GB free, need {1} GB' -f (Free-GB), $NeedGB }
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

New-Item -ItemType Directory -Path $job -ErrorAction Stop | Out-Null
# RunUAT is called by its FULL path, not by name after a cd. This machine has
# NoDefaultCurrentDirectoryInExePath=1 set, so cmd refuses to run an executable found only in
# the current directory: `if exist RunUAT.bat` reports FOUND and `call RunUAT.bat` on the very
# next line reports "is not recognized as an internal or external command". Every historical
# Astra-Cook-*.ps1 in this tree calls it bare and would fail the same way today.
$batchFiles = 'C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles'
$command = '"' + $batchFiles + '\RunUAT.bat" BuildCookRun -project="' + $project + '\MikdashCourtyardV3.uproject" -noP4 -platform=Win64 ' +
           '-clientconfig=Development -build -cook -map=' + $mapPkg + ' ' +
           '-AdditionalCookerOptions=-cookprocesscount=1 -AdditionalIoStoreOptions="-maxPartitionSize=1800000000" ' +
           '-stage -pak -iostore -archive -archivedirectory="' + $archive + '" -utf8output -unattended'

$r = [ordered]@{
    status = 'running'; label = $Label; stamp = $stamp
    startedUtc = (Get-Date).ToUniversalTime().ToString('o')
    command = $command; map = $mapPkg
    candidateSha256Before = $before; mainSha256Before = $mainBefore
    archive = $archive; freeGBAtStart = (Free-GB)
    scope = 'Cook + archive + bounded startup smoke. NOT route, audio or interaction acceptance.'
}
function Save-Receipt { $r | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $job 'checkpoint-receipt.json') -Encoding utf8 }
Save-Receipt

if (-not (Test-Path -LiteralPath (Join-Path $batchFiles 'RunUAT.bat'))) {
    throw "RunUAT.bat not found under $batchFiles - is UE 5.8 still installed there?"
}
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
    & $env:COMSPEC /d /c $bat *> (Join-Path $job 'uat.log')
    $r.exitCode = $LASTEXITCODE
} finally {
    $r.candidateSha256After = (Get-FileHash -LiteralPath $mapFile  -Algorithm SHA256).Hash.ToLower()
    $r.mainSha256After       = (Get-FileHash -LiteralPath $mainFile -Algorithm SHA256).Hash.ToLower()
    $child = Join-Path $archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
    $r.childExists = Test-Path -LiteralPath $child
    if ($r.childExists) {
        $r.child = $child
        $r.childSha256 = (Get-FileHash -LiteralPath $child -Algorithm SHA256).Hash.ToLower()
        $r.archiveBytes = [int64]((Get-ChildItem -LiteralPath (Join-Path $archive 'Windows') -Recurse -File |
                                   Measure-Object Length -Sum).Sum)
    }
    # Only the COOKED map's bytes are a correctness condition. Main50 is not cooked, and
    # guarding on it failed cp02b - a complete, valid 3.86 GB archive - because another agent
    # saved Main50 while the cook was running. Its hash is still recorded, as information.
    $r.mainMapChangedDuringCook = ($r.mainSha256After -ne $mainBefore)
    $cookOk = ($r.exitCode -eq 0 -and $r.childExists -and $r.candidateSha256After -eq $before)
    $r.status = if ($cookOk) { 'cook_archive_passed_smoke_pending' } else { 'failed' }
    Save-Receipt
}

# --- bounded startup smoke: does the thing the user double-clicks open? -----------------
# Delegated to Smoke-Build.ps1 so a build that already exists can be re-tested without paying
# for another cook - and because getting this right needs more care than it looks: the exe in
# the archive root is a launcher stub that spawns the real game and exits, so watching the
# Start-Process handle reports failure while the game is still loading.
if ($cookOk -and -not $SkipSmoke) {
    $smokeReceipt = Join-Path $job 'smoke-receipt.json'
    & (Join-Path $PSScriptRoot 'Smoke-Build.ps1') -Archive $archive -ReceiptPath $smokeReceipt | Out-Null
    if (Test-Path -LiteralPath $smokeReceipt) {
        $smoke = Get-Content -LiteralPath $smokeReceipt -Raw | ConvertFrom-Json
        $r.smoke = $smoke
        $r.status = if ($smoke.status -eq 'playable') { 'checkpoint_playable' }
                    else { 'cook_passed_but_smoke_' + $smoke.status }
    } else {
        $r.status = 'cook_passed_but_smoke_did_not_report'
    }
}
$r.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
Save-Receipt
Copy-Item -LiteralPath (Join-Path $job 'checkpoint-receipt.json') `
          -Destination (Join-Path $project ("SourceAssets\build-review\checkpoint-$Label-$stamp.json")) -Force

Write-Output ($r | ConvertTo-Json -Depth 6)
if ($r.status -eq 'failed') { exit 1 }
