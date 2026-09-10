<#
    Capture a FILMSTRIP of the people walking from a PACKAGED build, using -dumpmovie.

    Why this and not Scripts/capture_people_walk_frames.ps1: photo mode PAUSES the world
    (UMikdashPhotoMode::Enter -> SetGamePaused(true), MikdashPhotoMode.cpp:412), so every
    photograph is of a frozen world and nothing about a moving foot can be read out of a
    set of them. -dumpmovie writes EVERY rendered frame of the RUNNING world to
    Saved/Screenshots/Windows, which is the only instrument here that can show a foot
    sliding against the flagstones between consecutive frames.

    Same launch recipe otherwise (see Scripts/capture_vegetation_grove_frames.ps1):
      * -notraceserver stops a Windows Firewall prompt that would hold the foreground
      * bShowMainMenuOnBoot=False (NOT bEnabled=False)
      * Ghost before BugItGo so the pawn does not fall through unstreamed terrain
      * no PostMessage at all: nothing has to be keyed, the engine dumps by itself

    .\capture_people_walk_movie.ps1 -Archive <archive> -Label cp11 -View court-lane-close
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [Parameter(Mandatory = $true)][string]$View,
    [Parameter(Mandatory = $true)][string]$Go,
    [int]$SettleSeconds = 45,
    [int]$RecordSeconds = 60,
    [int]$ResX = 1280,
    [int]$ResY = 720,
    [int]$KeepEvery = 1,
    # Fixed timestep. PNG encoding throttles a -dumpmovie run to about 1.1 real frames per
    # second, so at real-time pacing consecutive frames are ~0.9 s apart -- most of a 1.2 s
    # stride, which is useless for reading a planted foot. -benchmark -fps=N makes the
    # engine advance exactly 1/N of a game second per frame however long the frame took to
    # write, so the filmstrip is an exact 1/N-second sequence of the walk.
    [int]$FixedFps = 0
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
$stageRoot = Split-Path (Split-Path (Split-Path $exe -Parent) -Parent) -Parent
$shots = Join-Path $stageRoot 'Saved\Screenshots\Windows'
$outDir = "C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\visual-review\movie-$Label-$View"

foreach ($n in @('UnrealEditor','UnrealEditor-Cmd','AutomationTool','MikdashCourtyardV3')) {
    $p = Get-Process -Name $n -ErrorAction SilentlyContinue
    if ($p) { throw "refusing to launch: $n already running (pid $($p.Id -join ','))" }
}
if (Test-Path -LiteralPath $shots) { Remove-Item -LiteralPath $shots -Recurse -Force }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FableMovieProbe_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FableMovieProbe_' + $Label + '_Settings'

# -dumpmovie starts writing at the first frame, so the settle period is recorded too and
# thinned out afterwards by first-write time.
$fixed = if ($FixedFps -gt 0) { "-benchmark -fps=$FixedFps " } else { '' }
$argline = "-windowed -ResX=$ResX -ResY=$ResY -nosplash -nosteam -notraceserver -notrace -noverifygc " +
           "-dumpmovie $fixed$iniArgs -ExecCmds=`"Ghost,BugItGo $Go,ShowHUD`""

$report = [ordered]@{
    status = 'starting'; label = $Label; view = $View; bugItGo = $Go; archive = $Archive
    map = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
    method = '-dumpmovie: every rendered frame of the RUNNING world, no pause, no photo mode'
    resolution = "$ResX x $ResY"; settleSeconds = $SettleSeconds; recordSeconds = $RecordSeconds
    fixedFps = $FixedFps
    gameSecondsPerFrame = if ($FixedFps -gt 0) { [math]::Round(1.0 / $FixedFps, 4) } else { $null }
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); errors = @()
}
$receipt = Join-Path $outDir 'movie-receipt.json'
$proc = Start-Process -FilePath $exe -ArgumentList $argline -PassThru -WorkingDirectory $stageRoot
try {
    Start-Sleep -Seconds ($SettleSeconds + $RecordSeconds)
    $proc.Refresh()
    if ($proc.HasExited) { throw "exited early, code $($proc.ExitCode)" }
    $report.peakWorkingSetMB = [int]($proc.PeakWorkingSet64 / 1MB)
} catch {
    $report.errors += $_.Exception.Message
} finally {
    if (-not $proc.HasExited) { $proc.CloseMainWindow() | Out-Null; Start-Sleep -Seconds 5 }
    if (-not $proc.HasExited) { $proc | Stop-Process -Force }
}
Start-Sleep -Seconds 3

$all = @(Get-ChildItem -LiteralPath $shots -Filter *.png -EA SilentlyContinue | Sort-Object LastWriteTime)
$report.framesDumped = $all.Count
if ($all.Count -eq 0) { $report.errors += "no dumped frames in $shots" }
else {
    $t0 = $all[0].LastWriteTime
    $report.dumpSpanSeconds = [math]::Round(($all[-1].LastWriteTime - $t0).TotalSeconds, 2)
    $report.effectiveFps = [math]::Round($all.Count / [math]::Max(1, ($all[-1].LastWriteTime - $t0).TotalSeconds), 2)
    # keep only frames after the settle window, then thin
    $keep = @($all | Where-Object { ($_.LastWriteTime - $t0).TotalSeconds -ge $SettleSeconds })
    if ($keep.Count -eq 0) { $keep = $all }
    $kept = @(); $i = 0
    foreach ($f in $keep) {
        if (($i % $KeepEvery) -eq 0) {
            $dest = Join-Path $outDir ("{0}-{1}-{2:d4}.png" -f $Label, $View, $kept.Count)
            Copy-Item -LiteralPath $f.FullName -Destination $dest -Force
            $kept += @{ file = $dest; dumpedAtSeconds = [math]::Round(($f.LastWriteTime - $t0).TotalSeconds, 3); source = $f.Name }
        }
        $i++
    }
    $report.framesKept = $kept.Count
    $report.frames = $kept
}
$report.status = if ($report.framesDumped -gt 0) { 'movie_captured_visual_review_pending' } else { 'failed_no_frames' }
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $receipt -Encoding utf8
if (Test-Path -LiteralPath $shots) { Remove-Item -LiteralPath $shots -Recurse -Force }
Write-Output ("dumped {0} frames over {1}s ({2} fps), kept {3} -> {4}" -f `
    $report.framesDumped, $report.dumpSpanSeconds, $report.effectiveFps, $report.framesKept, $outDir)
