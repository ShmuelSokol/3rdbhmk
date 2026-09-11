<#
    Frames for the precinct retaining-face MACRO pass and the Heikhal ceiling soot decal, from a PACKAGED build.
    Derived line-for-line from Scripts\capture_frame_ashlar.ps1 (same launch flags, LaunchDir photo path,
    map-loaded poll, window poll, PostMessage F2 then F9). Only the view list differs.

      P1  cp05b-04 aerial camera verbatim: the whole platform over the SW corner (~0.9-2 km to the faces)
      P2  south retaining face from ~70 m out, above the modern roofs
      P3  east retaining face from ~60 m out
      02  the 4 m Herodian jamb (MI_HerodianV4_Ashlar - NOT touched by this pass; the no-regression control)
      S2  cp16shell-S2 camera: Heikhal ceiling over the golden altar (the soot decal)
      07  cp05b-07 north gate approach: plaza stone (MI_PrecinctPlaza_Ashlar) at walking range, macro faded out

      .\capture_frame_precinct_macro.ps1 -Archive C:\Mikdash\Builds\Checkpoint-cp17-<stamp> -Label cp17 -Views P1,P2,P3,02,S2,07
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [string[]]$Views = @('P1', 'P2', 'P3', '02', 'S2', '07'),
    [int]$MapWaitSeconds = 300,
    [int]$AfterMapSeconds = 25,
    [int]$ShotWaitSeconds = 120,
    [int]$WindowWaitSeconds = 240,
    [int]$Attempts = 2,
    [switch]$ListOnly
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
$launchDir = Join-Path $Archive 'Windows'
$photos = Join-Path $launchDir 'MikdashPhotos'
$gameLog = Join-Path $Archive 'Windows\MikdashCourtyardV3\Saved\Logs\MikdashCourtyardV3.log'
$outDir = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\visual-review'

$all = [ordered]@{
    'P1' = @{ name = 'P1-precinct-plaza-aerial-SW-corner'; go = '-95000 175000 30000 -9 -45 0'
              answers = 'cp05b-04 camera verbatim: do the 90-137 m retaining faces read as coursed masonry at 0.9-2 km' }
    'P2' = @{ name = 'P2-retaining-south-face-70m'; go = '10000 118900 -1500 -18 -90 0'
              answers = 'south retaining face from ~70 m: courses, stone-to-stone tone, bed joints at mid range' }
    'P3' = @{ name = 'P3-retaining-east-face-60m'; go = '117900 60000 -1500 -15 180 0'
              answers = 'east retaining face from ~60 m' }
    '02' = @{ name = '02-herodian-ashlar-inner-east-gate-jamb-walkingheight'; go = '1752 1200 580 5 0 0'
              answers = '4 m Herodian jamb: close-up look must be unchanged (this pass never touches MI_HerodianV4_*)' }
    'S2' = @{ name = 'S2-heichal-ceiling-golden-altar'; go = '-4200 0 1300 48 180 0'
              answers = 'cp16shell-S2 camera: the grey card (soot decal) must be gone' }
    '07' = @{ name = '07-north-gate-approach-plaza-stone-near'; go = '1500 -36500 -427 2 113 0'
              answers = 'plaza stone at walking range: macro must be faded out, look unchanged' }
}
# powershell -File passes "-Views P1,P2,P3" as ONE string, not an array; split it here or every view is
# "unknown" and the script throws before its first receipt write (that is what the first cp16before run did).
$Views = @($Views | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
# The [string] cast is belt-and-braces only; tested offline, the plain lookup resolves fine. The real cause of the
# second cp16before failure (three launches at spawn, no camera) is the case-insensitive variable noted below.
# -File parses "-Views P1,02,07" as an array literal, so 02 arrives as the NUMBER 2. Pad digit-only keys back.
$viewList = @($Views | ForEach-Object { $k = [string]$_; if ($k -match '^\d+$') { $k = $k.PadLeft(2, '0') }
                                        if (-not $all.Contains($k)) { throw "unknown view $k" }; $all[$k] })
# $viewList, NOT $views: PowerShell variables are case-insensitive, so "$views = ..." wrote the hashtables back into
# the [string[]]$Views parameter as "System.Collections.Hashtable" and every view lost its name and camera.
foreach ($v in $viewList) { if (-not $v -or -not $v.name -or -not $v.go) { throw "view table lookup produced an empty view; refusing" } }
if ($ListOnly) { $viewList | ForEach-Object { "{0}  BugItGo {1}" -f $_.name, $_.go }; return }

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinPM {
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern IntPtr SetForegroundWindow(IntPtr h);
}
'@

function Send-Key([IntPtr]$hwnd, [int]$vk) {
    [void][WinPM]::PostMessage($hwnd, 0x0100, [IntPtr]$vk, [IntPtr]0)
    Start-Sleep -Milliseconds 140
    [void][WinPM]::PostMessage($hwnd, 0x0101, [IntPtr]$vk, [IntPtr]0)
}

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:LeashRadiusCm=900000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:FlySpeedCmPerSecond=3000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:SprintMultiplier=12.0,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=PMacro_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=PMacro_' + $Label + '_Settings'

$report = [ordered]@{
    status = 'starting'; label = $Label; archive = $Archive; exe = $exe
    launchDir = $launchDir; photoDir = $photos; map = 'GameDefaultMap'
    recipe = 'capture_frame_ashlar.ps1 verbatim; cameras from cp05b-frames-20260910.json (P1, 02, 07), cp16shell (S2), new (P2, P3)'
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); frames = @(); errors = @()
}
$receipt = Join-Path $outDir ("frame-precinct-macro-$Label.json")
function Save-Receipt { ($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $receipt -Encoding utf8 }

foreach ($n in @('UnrealEditor', 'UnrealEditor-Cmd', 'AutomationTool', 'MikdashCourtyardV3')) {
    if (Get-Process -Name $n -EA SilentlyContinue) { $report.status = "refused: $n is running"; Save-Receipt; throw "refused: $n is running" }
}
if (Test-Path -LiteralPath $photos) { Remove-Item -LiteralPath $photos -Recurse -Force }

foreach ($v in $viewList) {
  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    $arguments = "-windowed -ResX=1600 -ResY=900 -nosplash -nosteam -notraceserver -notrace -noverifygc $iniArgs"
    if ($v.go) { $arguments += " -ExecCmds=`"Ghost,BugItGo $($v.go)`"" }
    if (Test-Path -LiteralPath $gameLog) { Remove-Item -LiteralPath $gameLog -Force -EA SilentlyContinue }
    $before = @()
    if (Test-Path -LiteralPath $photos) {
        $before = @(Get-ChildItem -LiteralPath $photos -Filter *.png -EA SilentlyContinue | Select-Object -ExpandProperty FullName)
    }
    $proc = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru -WorkingDirectory $launchDir
    $entry = [ordered]@{ view = $v.name; answers = $v.answers; bugItGo = $v.go; pid = $proc.Id; attempt = $attempt }
    try {
        $deadline = (Get-Date).AddSeconds($MapWaitSeconds)
        $mapUp = $false
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 5
            $proc.Refresh()
            if ($proc.HasExited) { throw "exited early, code $($proc.ExitCode)" }
            if (Test-Path -LiteralPath $gameLog) {
                $text = Get-Content -LiteralPath $gameLog -Raw -EA SilentlyContinue
                if ($text -and ($text -match 'LogLoad: Took .* to LoadMap' -or $text -match 'Bringing World .* up for play')) { $mapUp = $true; break }
            }
        }
        $entry.mapReported = $mapUp
        if (-not $mapUp) { throw "map never reported loaded within $MapWaitSeconds s" }
        Start-Sleep -Seconds $AfterMapSeconds
        $hwnd = [IntPtr]::Zero
        $hwndDeadline = (Get-Date).AddSeconds($WindowWaitSeconds)
        while ((Get-Date) -lt $hwndDeadline) {
            $proc.Refresh()
            if ($proc.HasExited) { throw "exited while waiting for a window, code $($proc.ExitCode)" }
            $h = $proc.MainWindowHandle
            if ($null -ne $h -and [IntPtr]$h -ne [IntPtr]::Zero) { $hwnd = [IntPtr]$h; break }
            Start-Sleep -Seconds 5
        }
        $proc.Refresh()
        $entry.peakWorkingSetMB = [int]($proc.PeakWorkingSet64 / 1MB)
        if ($hwnd -eq [IntPtr]::Zero) { throw "no main window handle after $WindowWaitSeconds s" }
        [void][WinPM]::SetForegroundWindow($hwnd)
        Send-Key $hwnd 0x71          # F2 - photo mode
        Start-Sleep -Seconds 6
        Send-Key $hwnd 0x78          # F9 - HighResShot 2x
        $shot = $null
        $shotDeadline = (Get-Date).AddSeconds($ShotWaitSeconds)
        while ((Get-Date) -lt $shotDeadline) {
            Start-Sleep -Seconds 3
            $candidate = Get-ChildItem -LiteralPath $photos -Filter *.png -EA SilentlyContinue |
                         Where-Object { $before -notcontains $_.FullName } | Sort-Object LastWriteTime | Select-Object -Last 1
            if ($candidate -and $candidate.Length -gt 200000) { $shot = $candidate; break }
        }
        if (-not $shot) { throw "no new PNG appeared in $photos within $ShotWaitSeconds s" }
        Start-Sleep -Seconds 2
        $entry.shotSource = $shot.FullName
    } catch {
        $entry.error = $_.Exception.Message
        $report.errors += "$($v.name): $($_.Exception.Message)"
    } finally {
        if (-not $proc.HasExited) { $proc.CloseMainWindow() | Out-Null; Start-Sleep -Seconds 5 }
        $proc.Refresh()
        if (-not $proc.HasExited) { $proc | Stop-Process -Force }
        Start-Sleep -Seconds 3
    }
    if ($entry.shotSource -and (Test-Path -LiteralPath $entry.shotSource)) {
        $dest = Join-Path $outDir ("$Label-$($v.name).png")
        Move-Item -LiteralPath $entry.shotSource -Destination $dest -Force
        $entry.file = $dest; $entry.bytes = (Get-Item -LiteralPath $dest).Length
    } else { $entry.file = $null }
    if (Test-Path -LiteralPath $gameLog) {
        $log = Get-Content -LiteralPath $gameLog -Raw -EA SilentlyContinue
        $entry.materialWarnings = @([regex]::Matches($log, '(?m)^.*LogMaterial:\s*(Warning|Error).*$') |
                                    ForEach-Object { $_.Value.Trim() } | Select-Object -Unique)
        $entry.precinctFallback = @($entry.materialWarnings | Where-Object { $_ -match 'PrecinctPlaza|PrecinctMacro|HerodianV[45]|PBR_Tiled' })
    }
    $report.frames += $entry
    Save-Receipt
    if (-not $entry.file -and $attempt -lt $Attempts) { Start-Sleep -Seconds 15; continue }
    break
  }
}
$got = @($report.frames | Where-Object { $_.file }).Count
$report.status = if ($got -eq $viewList.Count) { 'frames_captured_visual_review_pending' } else { 'incomplete' }
$report.capturedCount = $got
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
Save-Receipt
Write-Output ("captured {0}/{1} -> {2}" -f $got, $viewList.Count, $receipt)
