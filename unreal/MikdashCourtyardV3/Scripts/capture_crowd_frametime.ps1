<#
    Frame-time capture of a PACKAGED build at a fixed camera, for the crowd before/after.

    Instrument: the engine's CSV profiler (-csvCaptureFrames, boot capture, -csvGpuStats). It
    writes one row per frame with FrameTime, GameThreadTime, RenderThreadTime and GPU time to
    <stage>\Saved\Profiling\CSV. The capture starts at boot, so the settle window is recorded too
    and discarded afterwards by cumulative frame time (Scripts/analyze_crowd_frametime.py).
    Real-time pacing (NO -benchmark, NO -dumpmovie): -benchmark decouples game time from wall time
    and -dumpmovie throttles the run to the PNG encoder, so neither can say anything about cost.

    Isolation of the crowd's own cost: run the same build and camera with -CrowdCount=0
    (AMikdashCrowdField::ParseCrowdCountSwitch) and subtract.

    Same launch recipe as capture_people_walk_movie.ps1: -notraceserver, main menu off by ini,
    isolated save slots, Ghost before BugItGo, one process at a time.

    .\capture_crowd_frametime.ps1 -Archive <archive> -Label cp17 -View court -Go "3300 2434 380 -4 90 0" [-CrowdCount 0]
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$View,
    [Parameter(Mandatory = $true)][string]$Go,
    [int]$CrowdCount = -1,
    [int]$SettleSeconds = 45,
    [int]$RecordSeconds = 60,
    [int]$ResX = 1280,
    [int]$ResY = 720
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
$stageRoot = Split-Path (Split-Path (Split-Path $exe -Parent) -Parent) -Parent
$csvDir = Join-Path $stageRoot 'Saved\Profiling\CSV'
$tag = if ($CrowdCount -ge 0) { "crowd$CrowdCount" } else { 'crowdDefault' }
$outDir = "C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\perf-review\crowd-vat\frametime-$Label-$View-$tag"

foreach ($n in @('UnrealEditor','UnrealEditor-Cmd','AutomationTool','MikdashCourtyardV3','UnrealBuildTool')) {
    $p = Get-Process -Name $n -ErrorAction SilentlyContinue
    if ($p) { throw "refusing to launch: $n already running (pid $($p.Id -join ','))" }
}
if (Test-Path -LiteralPath $csvDir) { Remove-Item -LiteralPath $csvDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FablePerfProbe_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FablePerfProbe_' + $Label + '_Settings'
$crowdArg = if ($CrowdCount -ge 0) { "-CrowdCount=$CrowdCount " } else { '' }
$frames = [int](($SettleSeconds + $RecordSeconds) * 240)
$argline = "-windowed -ResX=$ResX -ResY=$ResY -nosplash -nosteam -notraceserver -notrace -noverifygc " +
           "-csvCaptureFrames=$frames -csvGpuStats $crowdArg$iniArgs " +
           "-ExecCmds=`"Ghost,BugItGo $Go,t.MaxFPS 0,r.VSync 0`""

$report = [ordered]@{
    status = 'starting'; label = $Label; view = $View; bugItGo = $Go; archive = $Archive
    crowdCount = if ($CrowdCount -ge 0) { $CrowdCount } else { 'map default' }
    method = 'CSV profiler boot capture, real-time pacing, vsync off, t.MaxFPS 0'
    resolution = "$ResX x $ResY"; settleSeconds = $SettleSeconds; recordSeconds = $RecordSeconds
    commandLine = $argline
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); errors = @()
}
$receipt = Join-Path $outDir 'frametime-receipt.json'
$proc = Start-Process -FilePath $exe -ArgumentList $argline -PassThru -WorkingDirectory $stageRoot
try {
    Start-Sleep -Seconds ($SettleSeconds + $RecordSeconds)
    $game = Get-Process -Name MikdashCourtyardV3 -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $game) { throw 'game process not running at the end of the record window' }
    $report.peakWorkingSetMB = [int]($game.PeakWorkingSet64 / 1MB)
} catch {
    $report.errors += $_.Exception.Message
} finally {
    $game = Get-Process -Name MikdashCourtyardV3 -ErrorAction SilentlyContinue
    foreach ($g in @($game)) { if ($g) { $g.CloseMainWindow() | Out-Null } }
    Start-Sleep -Seconds 8
    $game = Get-Process -Name MikdashCourtyardV3 -ErrorAction SilentlyContinue
    if ($game) { $game | Stop-Process -Force }
}
Start-Sleep -Seconds 2
$csv = @(Get-ChildItem -LiteralPath $csvDir -Filter *.csv -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)
if ($csv.Count -eq 0) { $report.errors += "no CSV in $csvDir" }
else {
    $dest = Join-Path $outDir ("frametime-$Label-$View-$tag.csv")
    Copy-Item -LiteralPath $csv[-1].FullName -Destination $dest -Force
    $report.csv = $dest
}
$report.status = if ($report.csv) { 'csv_captured_analysis_pending' } else { 'failed_no_csv' }
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
($report | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $receipt -Encoding utf8
Write-Output ("{0}: {1}" -f $report.status, $outDir)
