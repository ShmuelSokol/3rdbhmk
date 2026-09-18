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
    [Parameter(Mandatory = $true)][ValidatePattern('\A-?[0-9]+(?:\.[0-9]+)?(?: -?[0-9]+(?:\.[0-9]+)?){5}\z')][string]$Go,
    [ValidateRange(-1,60000)][int]$CrowdCount = -1,
    [ValidateRange(30,120)][int]$SettleSeconds = 45,
    [ValidateRange(30,300)][int]$RecordSeconds = 60,
    [ValidateRange(640,1920)][int]$ResX = 1280,
    [ValidateRange(360,1080)][int]$ResY = 720,
    [switch]$CsvOnGameThread
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
$stageRoot = Split-Path (Split-Path (Split-Path $exe -Parent) -Parent) -Parent
$csvDir = Join-Path $stageRoot 'Saved\Profiling\CSV'
$tag = if ($CrowdCount -ge 0) { "crowd$CrowdCount" } else { 'crowdDefault' }
$project = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $project "SourceAssets/perf-review/crowd-vat/frametime-$Label-$View-$tag"

foreach ($n in @('UnrealEditor','UnrealEditor-Cmd','AutomationTool','MikdashCourtyardV3','UnrealBuildTool')) {
    $p = Get-Process -Name $n -ErrorAction SilentlyContinue
    if ($p) { throw "refusing to launch: $n already running (pid $($p.Id -join ','))" }
}
$busyBuild = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if ($busyBuild.Count) { throw 'Native build slot occupied' }
if (([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 9GB) { throw 'Crowd capture requires 9 GiB free commit' }
if (Test-Path -LiteralPath $outDir) { throw 'Fresh capture label/view/count required; previous evidence is preserved' }
$priorCsv = @(Get-ChildItem -LiteralPath $csvDir -Filter '*.csv' -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
New-Item -ItemType Directory -Path $outDir | Out-Null

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FablePerfProbe_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FablePerfProbe_' + $Label + '_Settings,' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False'
$crowdArg = if ($CrowdCount -ge 0) { "-CrowdCount=$CrowdCount " } else { '' }
$frames = [int](($SettleSeconds + $RecordSeconds) * 120)
$inspectionFrame = $frames - 120
$photo = (Join-Path $outDir 'crowd.png').Replace('\','/')
$inspection = @('SeededAgents','RefusedSeeds','GroundTraceMisses','ActivePoseCount','bUseVertexAnimation') | ForEach-Object { "${inspectionFrame}:getall MikdashCrowdField $_" }
$inspection += "${inspectionFrame}:Shot filename=$photo -nosuffix"
$inspectionArgs = '-csvExecCmds="' + ($inspection -join ',') + '"'
$argline = "-windowed -ResX=$ResX -ResY=$ResY -nosplash -nosteam -notraceserver -notrace -noverifygc " +
           "-csvCaptureFrames=$frames -csvGpuStats -ExitAfterCsvProfiling $inspectionArgs $crowdArg$iniArgs " +
           "-ExecCmds=`"sg.ViewDistanceQuality 2,sg.ShadowQuality 2,sg.GlobalIlluminationQuality 2,sg.ReflectionQuality 2,sg.PostProcessQuality 2,sg.TextureQuality 2,sg.EffectsQuality 2,sg.FoliageQuality 2,sg.ShadingQuality 2,r.ScreenPercentage 77,r.SetRes ${ResX}x${ResY}w,Ghost,BugItGo $Go,t.MaxFPS 0,r.VSync 0,csv.ForceExit 0`""
$log = Join-Path $outDir 'runtime.log'
$argline += (' -abslog="'+$log+'"')
if($CsvOnGameThread){$argline += ' -csvNoProcessingThread'}

$report = [ordered]@{
    status = 'starting'; label = $Label; view = $View; bugItGo = $Go; archive = $Archive
    crowdCount = if ($CrowdCount -ge 0) { $CrowdCount } else { 'map default' }
    method = 'CSV profiler boot capture, real-time pacing, vsync off, t.MaxFPS 0; engine exits after CSV finalization'
    captureFrames = $frames; timeoutSeconds = ($SettleSeconds+$RecordSeconds)*10
    inspectionFrame = $inspectionFrame; inspectionScope = 'Late-frame reflected crowd counts and viewport image; analysis must exclude inspection frame and later'
    csvOnGameThread = [bool]$CsvOnGameThread
    resolution = "$ResX x $ResY"; settleSeconds = $SettleSeconds; recordSeconds = $RecordSeconds
    quality = 'High (all scalability groups 2), screen percentage 77; saved graphics overrides disabled'
    commandLine = $argline
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); errors = @()
    childSha256 = (Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant()
    initialRequiredFreeCommitBytes = 9GB; maximumPrivateBytes = 8GB; reserveCommitBytes = 1.25GB
    peakPrivateBytes = [long]0; minimumFreeCommitBytes = [long]::MaxValue
}
$receipt = Join-Path $outDir 'frametime-receipt.json'
function Save-Receipt { $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receipt -Encoding utf8 }
Save-Receipt
$proc = $null
try {
    $proc = Start-Process -FilePath $exe -ArgumentList $argline -PassThru -WorkingDirectory $stageRoot -WindowStyle Hidden
    $report.pid=$proc.Id; $report.status='running'; Save-Receipt
    $deadline=(Get-Date).AddSeconds(($SettleSeconds+$RecordSeconds)*10)
    while((Get-Date) -lt $deadline){
        Start-Sleep -Seconds 2
        $proc.Refresh()
        if($proc.HasExited){break}
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $report.peakPrivateBytes=[Math]::Max([long]$report.peakPrivateBytes,[long]$proc.PrivateMemorySize64)
        $report.minimumFreeCommitBytes=[Math]::Min([long]$report.minimumFreeCommitBytes,$free)
        if($proc.PrivateMemorySize64 -gt 8GB -or $free -lt 1.25GB){throw 'Owned crowd capture hit memory reserve'}
    }
    if(-not $proc.HasExited){throw 'CSV completion watchdog expired'}
    $finalized = @(Select-String -LiteralPath $log -Pattern 'CSV finalize time :')
    if($finalized.Count -ne 1){throw 'Expected one engine CSV finalization before exit'}
    $report.csvFinalized=$true
    $counts = @(Select-String -LiteralPath $log -Pattern '\d+\)\s+MikdashCrowdField\s+(.+?:PersistentLevel\.[^.]+)\.SeededAgents = (\d+)\s*$')
    if($counts.Count -ne 1){throw 'Expected exactly one live crowd field seeded-count readback'}
    $report.crowdActor=$counts[0].Matches[0].Groups[1].Value
    $report.seededAgents=[int]$counts[0].Matches[0].Groups[2].Value
    if($CrowdCount -ge 0 -and $report.seededAgents -ne $CrowdCount){throw 'Seeded crowd differs from requested count'}
    if(-not (Test-Path -LiteralPath $photo)){throw 'Missing late-frame viewport image'}
    $report.photo=$photo; $report.photoSha256=(Get-FileHash -LiteralPath $photo).Hash.ToLowerInvariant()
} catch {
    $report.errors += $_.Exception.Message
} finally {
    if($proc){
        try {
            $proc.Refresh()
            if(-not $proc.HasExited){[void]$proc.CloseMainWindow(); [void]$proc.WaitForExit(15000)}
        } catch { $report.errors += ('Graceful close failed: '+$_.Exception.Message) }
        # A graceful-close exception must not skip the independent owned-child cleanup.
        try {
            $proc.Refresh()
            if(-not $proc.HasExited){
                $proc | Stop-Process -Force
                $report.errors += 'Owned game required termination; CSV may be incomplete'
            } else {$report.exitCode=$proc.ExitCode; if($proc.ExitCode -ne 0){$report.errors+='Nonzero game exit'}}
        } catch { $report.errors += ('Owned process cleanup failed: '+$_.Exception.Message) }
    }
}
try {
    Start-Sleep -Seconds 2
    $csv = @(Get-ChildItem -LiteralPath $csvDir -Filter *.csv -ErrorAction SilentlyContinue | Where-Object {$priorCsv -notcontains $_.FullName} | Sort-Object LastWriteTime)
    if ($csv.Count -ne 1) { $report.errors += "Expected one fresh CSV in $csvDir; found $($csv.Count)" }
    else {
        $dest = Join-Path $outDir ("frametime-$Label-$View-$tag.csv")
        Copy-Item -LiteralPath $csv[0].FullName -Destination $dest
        $report.csv = $dest
        $report.csvSha256 = (Get-FileHash -LiteralPath $dest).Hash.ToLowerInvariant()
    }
} catch { $report.errors += ('CSV collection failed: '+$_.Exception.Message) }
finally {
    $report.status = if ($report.csv -and $report.errors.Count -eq 0 -and $report.csvFinalized) { 'csv_captured_analysis_pending' } else { 'failed_capture' }
    $report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
    Save-Receipt
}
Write-Output ("{0}: {1}" -f $report.status, $outDir)
if($report.status -eq 'failed_capture'){exit 1}
