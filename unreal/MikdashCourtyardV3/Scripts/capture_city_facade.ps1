<#
    CityFacadeV1 acceptance frames from a PACKAGED build (no editor), plus a frame-time sample per view.

    Recipe is Scripts/capture_frame_defects.ps1 verbatim (working directory = <Archive>\Windows because
    photo mode writes to FPaths::LaunchDir()/MikdashPhotos; Ghost before BugItGo; wait on the game's own
    LoadMap line; PostMessage F2 then F9; poll for the PNG). Two additions:

      * FRAME TIME. -ExecCmds also runs "CsvProfile Frames=N". The CSV profiler is compiled into
        Development builds and writes <Archive>\Windows\MikdashCourtyardV3\Saved\Profiling\CSV\*.csv
        when the N frames are done. The receipt reports the MEDIAN and p90 FrameTime of the last half
        of the capture, so the first-launch PSO hitches are excluded. The camera is static, so this is
        a per-view number, not a walk.
      * SLOT WAIT. Refuses to launch while any UnrealEditor / UnrealEditor-Cmd / MikdashCourtyardV3 or a
        dotnet AutomationTool/UnrealBuildTool runs. Matches on process NAME and dotnet COMMAND LINE only,
        so this script's own powershell.exe can never match itself.

    .\capture_city_facade.ps1 -Archive C:\Mikdash\Builds\Checkpoint-cp21b-20260911T081957Z -Label cityfacade-before
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [string[]]$Only = @(),
    [switch]$IncludeRoofStateViews,
    [int]$SlotWaitMinutes = 120,
    [int]$MapWaitSeconds = 300,
    [int]$AfterMapSeconds = 25,
    [int]$ShotWaitSeconds = 120,
    [int]$CsvFrames = 700
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
$launchDir = Join-Path $Archive 'Windows'
$photos = Join-Path $launchDir 'MikdashPhotos'
$gameLog = Join-Path $Archive 'Windows\MikdashCourtyardV3\Saved\Logs\MikdashCourtyardV3.log'
$csvDir = Join-Path $Archive 'Windows\MikdashCourtyardV3\Saved\Profiling\CSV'
$outDir = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\visual-review\city-facade'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# Cameras. Candidate48 world cm. Sources in the receipt beside each.
$views = @(
    @{ name = 'K1-kotel-plaza-walking-facing-jewish-quarter'; go = '-15500 19500 -1060 7 180 0'; preKeys = @(0x56);
       why = 'lower Kotel deck (Z -1234.6 + 170 eye), MODERN state after one V (as cp05b-08), looking west across both decks at the Jewish Quarter escarpment' },
    # K1 above landed in an alley between shelled buildings, not on the open deck (cfbefore-cp21c-K1).
    # K2 is the PROVEN cp05b-08 / horizon-N3 deck position (upper Kotel deck, MODERN after one V),
    # turned from the Wall to face west at the Jewish Quarter houses ~27 m away.
    @{ name = 'K2-kotel-upper-deck-facing-jewish-quarter';    go = '-20732 19230 -814 6 175 0'; preKeys = @(0x56);
       why = 'cp05b-08 / N3 deck position (verified on the upper deck in MODERN), yaw turned west to the Jewish Quarter' },
    @{ name = 'A1-west-gate-approach-into-old-city';          go = '-33500 0 420 3 180 0';
       why = 'outside the at-grade West gate (threshold Z 223 + eye), YECHEZKEL default, looking west into the walled city' },
    @{ name = 'A2-south-approach-flight-facing-silwan';       go = '-5000 114600 -3100 -4 100 0';
       why = 'on the S1 approach flight below the south wall, YECHEZKEL, looking south over the plain-box city the viewshed ranked worst' },
    @{ name = 'D1-dove-height-over-old-city';                 go = '-75000 30000 12000 -20 15 0';
       why = 'about 100 m above the western Old City, looking east-north-east toward the precinct' },
    @{ name = 'P1-precinct-plaza-aerial-SW-corner';           go = '-95000 175000 30000 -9 -45 0';
       why = 'cp05b-04 / cp17b-P1 camera verbatim' }
)
if ($IncludeRoofStateViews) {
    $views += @(
        @{ name = 'A1-modern-roof-restoration'; go = '-33500 0 420 3 180 0'; preKeys = @(0x56);
           why = 'same west-gate camera as A1, MODERN after one V; original rooftop equipment must return with its buildings' },
        @{ name = 'A1-overlay-roof-restoration'; go = '-33500 0 420 3 180 0'; preKeys = @(0x56, 0x56);
           why = 'same west-gate camera as A1, OVERLAY after two V presses; original rooftop equipment must remain with its buildings' }
        # The restored buildings occlude the roofs from ground-level A1. These
        # elevated counterparts actually show roof equipment in all three states.
        @{ name = 'R1-roof-overview-yechezkel'; go = '-33500 0 6500 -25 180 0';
           why = 'elevated west-gate view; hidden-building roof equipment must be absent in YECHEZKEL' },
        @{ name = 'R1-roof-overview-modern'; go = '-33500 0 6500 -25 180 0'; preKeys = @(0x56);
           why = 'same elevated view in MODERN; inspect the actual restored rooftops and equipment' },
        @{ name = 'R1-roof-overview-overlay'; go = '-33500 0 6500 -25 180 0'; preKeys = @(0x56, 0x56);
           why = 'same elevated view in OVERLAY; inspect restored rooftop equipment' }
    )
}
if ($Only.Count) { $views = @($views | Where-Object { $n = $_.name; @($Only | Where-Object { $n -like "$_*" }).Count }) }
if (-not $views.Count) { throw 'No capture views matched -Only; refusing an empty acceptance run' }

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinCF {
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern IntPtr SetForegroundWindow(IntPtr h);
}
'@
function Send-Key([IntPtr]$hwnd, [int]$vk) {
    [void][WinCF]::PostMessage($hwnd, 0x0100, [IntPtr]$vk, [IntPtr]0)
    Start-Sleep -Milliseconds 140
    [void][WinCF]::PostMessage($hwnd, 0x0101, [IntPtr]$vk, [IntPtr]0)
}
function Get-Busy {
    $b = @(Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3 -ErrorAction SilentlyContinue |
           Select-Object -ExpandProperty ProcessName)
    $b += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' } | ForEach-Object { 'dotnet-UAT/UBT' })
    return $b
}

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:LeashRadiusCm=900000,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=CityFacade_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=CityFacade_' + $Label + '_Settings'

$report = [ordered]@{
    status = 'waiting_for_slot'; label = $Label; archive = $Archive; exe = $exe
    recipe = 'capture_frame_defects.ps1 + CsvProfile frame time'; startedUtc = (Get-Date).ToUniversalTime().ToString('o')
    frames = @(); errors = @()
}
$receipt = Join-Path $outDir ("city-facade-frames-$Label.json")
function Save-Receipt { ($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $receipt -Encoding utf8 }
Save-Receipt

foreach ($v in $views) {
    # Two agents polling at the same cadence both saw a free slot in the same second on 11 Sep and
    # launched two games from the same archive (shared Saved\Logs); one died with code -1. So: wait for
    # free, then settle a RANDOM 10-40 s and require the slot to still be free before launching.
    $deadline = (Get-Date).AddMinutes($SlotWaitMinutes)
    $clear = $false
    while ((Get-Date) -lt $deadline) {
        while (@(Get-Busy).Count -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 20 }
        Start-Sleep -Seconds (Get-Random -Minimum 10 -Maximum 40)
        if (-not @(Get-Busy).Count) { $clear = $true; break }
    }
    if (-not $clear) { $report.errors += "$($v.name): slot never freed"; Save-Receipt; continue }
    $report.status = 'capturing'; Save-Receipt

    $arguments = "-windowed -ResX=1600 -ResY=900 -nosplash -nosteam -notraceserver -notrace -noverifygc " +
                 "$iniArgs -ExecCmds=`"Ghost,BugItGo $($v.go),CsvProfile Frames=$CsvFrames`""
    if (Test-Path -LiteralPath $gameLog) { Remove-Item -LiteralPath $gameLog -Force -EA SilentlyContinue }
    $csvBefore = @(); if (Test-Path -LiteralPath $csvDir) { $csvBefore = @(Get-ChildItem -LiteralPath $csvDir -Filter *.csv | Select-Object -ExpandProperty FullName) }
    $before = @(); if (Test-Path -LiteralPath $photos) { $before = @(Get-ChildItem -LiteralPath $photos -Filter *.png | Select-Object -ExpandProperty FullName) }
    $proc = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru -WorkingDirectory $launchDir
    $entry = [ordered]@{ view = $v.name; why = $v.why; bugItGo = $v.go; pid = $proc.Id }
    try {
        $deadline = (Get-Date).AddSeconds($MapWaitSeconds); $mapUp = $false
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 5; $proc.Refresh()
            if ($proc.HasExited) { throw "exited early, code $($proc.ExitCode)" }
            if (Test-Path -LiteralPath $gameLog) {
                $text = Get-Content -LiteralPath $gameLog -Raw -EA SilentlyContinue
                if ($text -and ($text -match 'LogLoad: Took .* to LoadMap' -or $text -match 'Bringing World .* up for play')) { $mapUp = $true; break }
            }
        }
        if (-not $mapUp) { throw "map never reported loaded within $MapWaitSeconds s" }
        Start-Sleep -Seconds $AfterMapSeconds
        $proc.Refresh()
        $hwnd = $proc.MainWindowHandle
        if ($hwnd -eq [IntPtr]::Zero) { throw 'no main window handle' }
        [void][WinCF]::SetForegroundWindow($hwnd)
        if ($v.preKeys) {
            foreach ($k in $v.preKeys) { Send-Key $hwnd $k; Start-Sleep -Seconds 4 }
            $entry.preKeysSent = ($v.preKeys | ForEach-Object { '0x{0:X2}' -f $_ }) -join ','
            Start-Sleep -Seconds 8
        }
        # frame time: wait for the CSV the profiler writes when its N frames are done
        $csv = $null; $csvDeadline = (Get-Date).AddSeconds(150)
        while ((Get-Date) -lt $csvDeadline) {
            Start-Sleep -Seconds 4
            if (Test-Path -LiteralPath $csvDir) {
                $csv = Get-ChildItem -LiteralPath $csvDir -Filter *.csv | Where-Object { $csvBefore -notcontains $_.FullName } |
                       Sort-Object LastWriteTime | Select-Object -Last 1
                if ($csv) { Start-Sleep -Seconds 3; break }
            }
        }
        if ($csv) {
            # Manual parse: the packaged CSV repeats column names (NumInstanceTransformUpdates), which
            # makes Import-Csv throw. A frame-time failure must never cost the photo, so it has its own try.
            try {
                $lines = Get-Content -LiteralPath $csv.FullName
                $head = $lines[0].Split(',')
                $iFt = [array]::IndexOf($head, 'FrameTime')
                $iGpu = -1
                foreach ($cand in @('GPU/Total', 'GPUTime', 'RHI/GPUFrameTime')) { if ($iGpu -lt 0) { $iGpu = [array]::IndexOf($head, $cand); if ($iGpu -ge 0) { $entry.gpuColumn = $cand } } }
                $ft = New-Object System.Collections.Generic.List[double]
                $gp = New-Object System.Collections.Generic.List[double]
                foreach ($ln in $lines[1..($lines.Count - 1)]) {
                    $c = $ln.Split(',')
                    $num = 0.0
                    if ($iFt -ge 0 -and $c.Count -gt $iFt -and [double]::TryParse($c[$iFt], [ref]$num)) { $ft.Add($num) }
                    if ($iGpu -ge 0 -and $c.Count -gt $iGpu -and [double]::TryParse($c[$iGpu], [ref]$num)) { $gp.Add($num) }
                }
                $tail = @($ft | Select-Object -Last ([int]($ft.Count / 2)) | Sort-Object)
                if ($tail.Count) {
                    $entry.frameTimeMsMedian = [math]::Round($tail[[int]($tail.Count / 2)], 2)
                    $entry.frameTimeMsP90 = [math]::Round($tail[[int]([math]::Min($tail.Count - 1, $tail.Count * 0.9))], 2)
                    $entry.frameSamples = $tail.Count
                }
                $gt = @($gp | Select-Object -Last ([int]($gp.Count / 2)) | Sort-Object)
                if ($gt.Count) { $entry.gpuMsMedian = [math]::Round($gt[[int]($gt.Count / 2)], 2) }
                $entry.csv = $csv.FullName
            } catch { $entry.frameTimeNote = 'CSV parse failed: ' + $_.Exception.Message }
        } else { $entry.frameTimeNote = 'no CSV appeared within 150 s' }

        Send-Key $hwnd 0x71; Start-Sleep -Seconds 6     # F2 photo mode
        Send-Key $hwnd 0x78                               # F9 2x PNG
        $shot = $null; $shotDeadline = (Get-Date).AddSeconds($ShotWaitSeconds)
        while ((Get-Date) -lt $shotDeadline) {
            Start-Sleep -Seconds 3
            $cand = Get-ChildItem -LiteralPath $photos -Filter *.png -EA SilentlyContinue | Where-Object { $before -notcontains $_.FullName } |
                    Sort-Object LastWriteTime | Select-Object -Last 1
            if ($cand -and $cand.Length -gt 200000) { Start-Sleep -Seconds 2; $shot = $cand; break }
        }
        if (-not $shot) { throw "no new PNG in $photos within $ShotWaitSeconds s" }
        $entry.shotSource = $shot.FullName
        $entry.peakWorkingSetMB = [int]($proc.PeakWorkingSet64 / 1MB)
        if (Test-Path -LiteralPath $gameLog) {
            $entry.materialWarnings = @(Select-String -LiteralPath $gameLog -Pattern 'CityFacade.*(usage|default material|fallback)|Missing.*CityFacade' |
                                        Select-Object -First 5 | ForEach-Object { $_.Line })
        }
    } catch {
        $entry.error = $_.Exception.Message; $report.errors += "$($v.name): $($_.Exception.Message)"
    } finally {
        if (-not $proc.HasExited) { $proc.CloseMainWindow() | Out-Null; Start-Sleep -Seconds 6 }
        $proc.Refresh(); if (-not $proc.HasExited) { $proc | Stop-Process -Force }
        Start-Sleep -Seconds 4
    }
    if ($entry.shotSource -and (Test-Path -LiteralPath $entry.shotSource)) {
        $dest = Join-Path $outDir ("$Label-$($v.name).png")
        Move-Item -LiteralPath $entry.shotSource -Destination $dest -Force
        $entry.file = $dest; $entry.bytes = (Get-Item -LiteralPath $dest).Length
    }
    $report.frames += $entry; Save-Receipt
}
$got = @($report.frames | Where-Object { $_.file }).Count
$report.status = if ($got -eq $views.Count) { 'frames_captured_visual_review_pending' } else { 'incomplete' }
$report.capturedCount = $got
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
Save-Receipt
Write-Output ("captured {0}/{1} -> {2}" -f $got, $views.Count, $receipt)
