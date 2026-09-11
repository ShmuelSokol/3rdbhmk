<#
    Cook a FRAME-TRIAL build for the anti-repeat pass: Candidate48 (unchanged) AND its frame-trial copy
    (FrameTrial_Candidate48, carrying the candidate material) in ONE archive.

    This is NOT a checkpoint. It is never handed over and is archived under C:\Mikdash\Builds\FrameTrial-*,
    not Checkpoint-*. It exists so the before and after frames come from ONE build, one camera and one
    exposure pipeline, with the untouched paving in both as the in-frame control - the evidence
    release_antirepeat.py's apply gate asks for before a new sampling mode may reach Candidate48.

    Derived from Checkpoint-Build.ps1 (same wait-for-slot loop, same RunUAT-by-full-path .bat, same
    cooker flags), with two differences: two maps, and NO -build. It stages the binaries already in the
    project (the same ones cp12 staged) and never invokes UnrealBuildTool.

      Start-Process powershell -ArgumentList '-NoProfile -File <this> -Label cp13t' -WindowStyle Hidden
#>
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [int]$WaitMinutes = 90,
    [double]$NeedGB = 4.0
)
$ErrorActionPreference = 'Stop'

$project   = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
$stamp     = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$job       = "C:\Mikdash\Working-5.8\FrameTrial-$Label-$stamp"
$archive   = "C:\Mikdash\Builds\FrameTrial-$Label-$stamp"
$candPkg   = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
$trialPkg  = '/Game/MikdashV3/MaterialReview/AntiRepeatV1/Maps/FrameTrial_Candidate48'
$candFile  = Join-Path $project 'Content\MikdashV3\Amah48Candidate_20260908T144034771385Z\Maps\Walkthrough.umap'
$trialFile = Join-Path $project 'Content\MikdashV3\MaterialReview\AntiRepeatV1\Maps\FrameTrial_Candidate48.umap'
$mainFile  = Join-Path $project 'Content\MikdashV3\IntegratedReviewV2\Maps\Walkthrough.umap'
$batchFiles = 'C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles'

function Free-GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1) }
function Hash($f) { (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLower() }

$deadline = (Get-Date).AddMinutes($WaitMinutes)
while ($true) {
    $busy = Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3, AutomationTool, UnrealBuildTool -ErrorAction SilentlyContinue
    if (-not $busy -and (Free-GB) -ge $NeedGB) { break }
    if ((Get-Date) -gt $deadline) { Write-Output 'DEFERRED'; exit 2 }
    Start-Sleep -Seconds 30
}
foreach ($f in @($candFile, $trialFile, $mainFile)) { if (-not (Test-Path -LiteralPath $f)) { throw "Missing map: $f" } }
if (Select-String -LiteralPath (Join-Path $project 'Config\DefaultEngine.ini'), (Join-Path $project 'Config\DefaultGame.ini') `
        -Pattern ([regex]::Escape($trialPkg)) -Quiet) {
    throw 'The frame-trial map appears in the project config; it must never be a shipping map'
}
New-Item -ItemType Directory -Path $job -ErrorAction Stop | Out-Null

$command = '"' + $batchFiles + '\RunUAT.bat" BuildCookRun -project="' + $project + '\MikdashCourtyardV3.uproject" -noP4 -platform=Win64 ' +
           '-clientconfig=Development -cook -map=' + $candPkg + '+' + $trialPkg + ' ' +
           '-AdditionalCookerOptions=-cookprocesscount=1 -AdditionalIoStoreOptions="-maxPartitionSize=1800000000" ' +
           '-stage -pak -iostore -archive -archivedirectory="' + $archive + '" -utf8output -unattended'
$r = [ordered]@{
    status = 'running'; label = $Label; stamp = $stamp; kind = 'FRAME_TRIAL_NOT_A_CHECKPOINT'
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); command = $command
    maps = @($candPkg, $trialPkg); archive = $archive; freeGBAtStart = (Free-GB)
    candidateSha256Before = (Hash $candFile); trialSha256Before = (Hash $trialFile); mainSha256Before = (Hash $mainFile)
}
function Save-Receipt { $r | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $job 'frame-trial-receipt.json') -Encoding utf8 }
Save-Receipt
$bat = Join-Path $job 'cook.bat'
@('@echo off', ('cd /d "' + $batchFiles + '"'), ('call ' + $command), 'exit /b %ERRORLEVEL%') |
    Set-Content -LiteralPath $bat -Encoding ascii
try {
    & $env:COMSPEC /d /c $bat *> (Join-Path $job 'uat.log')
    $r.exitCode = $LASTEXITCODE
} finally {
    $r.candidateSha256After = Hash $candFile
    $r.trialSha256After = Hash $trialFile
    $r.mainSha256After = Hash $mainFile
    $child = Join-Path $archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
    $r.childExists = Test-Path -LiteralPath $child
    $log = Join-Path $job 'uat.log'
    if (Test-Path -LiteralPath $log) {
        $r.antiRepeatLogLines = @(Select-String -LiteralPath $log -Pattern 'AntiRepeat' |
            Where-Object { $_.Line -match 'rror|arning|fail' } | Select-Object -First 40 | ForEach-Object { $_.Line.Trim() })
        $r.shaderErrorLines = @(Select-String -LiteralPath $log -Pattern 'Shader.*[Ee]rror|error X[0-9]|Failed to compile' |
            Select-Object -First 40 | ForEach-Object { $_.Line.Trim() })
    }
    $ok = ($r.exitCode -eq 0 -and $r.childExists -and $r.candidateSha256After -eq $r.candidateSha256Before -and
           $r.trialSha256After -eq $r.trialSha256Before)
    $r.status = if ($ok) { 'frame_trial_cooked' } else { 'failed' }
    $r.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
    Save-Receipt
}
Write-Output ("{0} {1}" -f $r.status, $archive)
