<#
    Acceptance frames for the far-field horizon ring (HorizonRingV1, Scripts/release_horizon_ring.py), from a
    PACKAGED build. Derived line-for-line from Scripts/capture_frame_precinct_macro.ps1 (same launch flags,
    LaunchDir photo path, map-loaded poll, window poll, PostMessage F2 then F9); only the view list differs,
    plus preKeys: V (0x56, CyclePrecinctView) switches to the MODERN state before the shot.

      P1   cp05b-04 / cp17b-P1 / cp20-P1 aerial camera verbatim (YECHEZKEL state): before = cp20-P1
      P1M  the same camera in the MODERN state
      D1   dove at 1,500 m above the plaza, under the 1.8 km cloud base (cp21 at 2,400 m was INSIDE the cloud layer), looking WEST
      D2   dove at 1,500 m looking EAST: the rift, the Dead Sea at -432 m, the Moab plateau
      G1   ground on the Mount, YECHEZKEL: western deck 35 m inside the wall, eye 4.5 m, looking west
      G2   ground on the Mount, MODERN: on the Haram 90 m west of the Kodesh, eye 2 m, looking west

      .\capture_frame_horizon.ps1 -Archive C:\Mikdash\Builds\Checkpoint-cp21-<stamp> -Label cp21 -Views P1,P1M,D1,D2,G1,G2
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [string[]]$Views = @('P1', 'P1M', 'D1', 'D2', 'G1', 'G2'),
    [int]$MapWaitSeconds = 300,
    [int]$AfterMapSeconds = 25,
    [int]$ShotWaitSeconds = 120,
    [int]$WindowWaitSeconds = 240,
    [int]$Attempts = 2,
    # Extra console commands appended to every view's -ExecCmds, e.g.
    # "mikdash.Haze.Enable 0" or "mikdash.TimeOfDay.ForcePreset 3,mikdash.Haze.MaxOpacity 0.5".
    [string]$ExtraExec = '',
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
    'P1'  = @{ name = 'P1-precinct-plaza-aerial-SW-corner'; go = '-95000 175000 30000 -9 -45 0'; preKeys = @()
               answers = 'cp20-P1 camera verbatim: does the horizon still read as a sea (YECHEZKEL)' }
    'P1M' = @{ name = 'P1M-precinct-plaza-aerial-SW-corner-MODERN'; go = '-95000 175000 30000 -9 -45 0'; preKeys = @(0x56)
               answers = 'same camera, MODERN state: the ring holds in both states' }
    'D1'  = @{ name = 'D1-dove-1500m-horizon-west'; go = '0 0 150000 -3 180 0'; preKeys = @()
               answers = 'highest proven dove height looking at the Mediterranean side: no shell band' }
    'D2'  = @{ name = 'D2-dove-1500m-horizon-east-dead-sea'; go = '0 0 150000 -5 0 0'; preKeys = @()
               answers = 'looking east: the rift falling to the Dead Sea far below, Moab beyond' }
    'G1'  = @{ name = 'G1-ground-temple-mount-west-YECHEZKEL'; go = '-28000 0 450 0 180 0'; preKeys = @()
               answers = 'from the Mount looking west over the wall: hills, not sea' }
    'G2'  = @{ name = 'G2-ground-temple-mount-west-MODERN'; go = '-9000 0 200 0 180 0'; preKeys = @(0x56)
               answers = 'MODERN state from the Haram looking west: hills, not sea' }
    'N1'  = @{ name = 'N1-azarah-spawn-facing-heichal'; go = '1768 0 578 0 180 0'; preKeys = @()
               answers = 'cp05b-01 camera: near-range look must not move' }
    'N2'  = @{ name = 'N2-herodian-jamb-walkingheight'; go = '1752 1200 580 5 0 0'; preKeys = @()
               answers = 'cp05b-02 camera: near-range look must not move' }
    'N3'  = @{ name = 'N3-kotel-plaza-upper-deck-MODERN'; go = '-20732 19230 -814 -6 -12 0'; preKeys = @(0x56)
               answers = 'cp05b-08 camera in the MODERN state: near-range look must not move' }
    'N4'  = @{ name = 'N4-heichal-interior'; go = '-3992 0 1058 8 180 0'; preKeys = @()
               answers = 'cp05b-09 camera: near-range look must not move' }
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
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=Horizon_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=Horizon_' + $Label + '_Settings'

$report = [ordered]@{
    status = 'starting'; label = $Label; archive = $Archive; exe = $exe
    launchDir = $launchDir; photoDir = $photos; map = 'GameDefaultMap'
    recipe = 'capture_frame_precinct_macro.ps1 verbatim; P1 from cp05b-04/cp20-P1, D/G new'
    extraExec = $ExtraExec
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); frames = @(); errors = @()
}
$receipt = Join-Path $outDir ("frame-horizon-$Label.json")
function Save-Receipt { ($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $receipt -Encoding utf8 }

if (@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -EA SilentlyContinue | Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' }).Count) {
    $report.status = 'refused: dotnet UAT/UBT is running'; Save-Receipt; throw 'refused: dotnet UAT/UBT is running' }
foreach ($n in @('UnrealEditor', 'UnrealEditor-Cmd', 'AutomationTool', 'MikdashCourtyardV3')) {
    if (Get-Process -Name $n -EA SilentlyContinue) { $report.status = "refused: $n is running"; Save-Receipt; throw "refused: $n is running" }
}
if (Test-Path -LiteralPath $photos) { Remove-Item -LiteralPath $photos -Recurse -Force }

foreach ($v in $viewList) {
  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    $arguments = "-windowed -ResX=1600 -ResY=900 -nosplash -nosteam -notraceserver -notrace -noverifygc $iniArgs"
    if ($v.go) {
        $exec = "Ghost,BugItGo $($v.go)"
        if ($ExtraExec) { $exec += ',' + $ExtraExec }
        $arguments += " -ExecCmds=`"$exec`""
    }
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
        if ($v.preKeys) {
            foreach ($k in $v.preKeys) { Send-Key $hwnd $k; Start-Sleep -Seconds 4 }
            $entry.preKeysSent = ($v.preKeys | ForEach-Object { '0x{0:X2}' -f $_ }) -join ','
            Start-Sleep -Seconds 8   # let the precinct state swap settle before the shot
        }
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
        $entry.terrainFallback = @($entry.materialWarnings | Where-Object { $_ -match 'Context_Terrain|HorizonRing|JerusalemTerrain' })
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
