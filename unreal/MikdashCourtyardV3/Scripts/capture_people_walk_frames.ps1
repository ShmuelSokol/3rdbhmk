<#
    Capture SEQUENCES of the people walking, from a PACKAGED build, with no editor.

    Why a sequence and not a still: a still frame cannot show a sliding foot. This script
    parks a FIXED camera and then takes N photographs spaced IntervalSeconds apart of the
    RUNNING world, so foot placement can be compared against the same flagstones between
    consecutive frames.

    The mechanic that makes that possible: UMikdashPhotoMode::Enter() calls
    SetGamePaused(World, true) (MikdashPhotoMode.cpp:412) and Leave() unpauses
    (:491). So holding photo mode open and hammering F9 yields N IDENTICAL frames.
    Instead each shot is F2 (enter, pause) -> F9 (shoot) -> F2 (leave, unpause) -> wait.
    The photo camera respawns at Controller->GetPlayerViewPoint() every Enter (:381-390),
    and the Ghost pawn does not drift, so the camera is the same camera each cycle.
    Photo filenames carry %Y%m%d-%H%M%S (BuildPhotoBaseName, :958-969), so shots must be
    spaced >= 2 s or two of them collide on one name.

    Everything else is the proven recipe from Scripts/capture_vegetation_grove_frames.ps1:
      * -notraceserver stops a Windows Firewall prompt that would hold the foreground
      * bShowMainMenuOnBoot=False (NOT bEnabled=False, which opens the legacy menu)
      * Ghost before BugItGo so the pawn does not fall through unstreamed terrain
      * PostMessage delivers DISCRETE key bindings only; the camera is placed with BugItGo
      * -WorkingDirectory is LOAD-BEARING: photo mode writes MikdashPhotos/ under
        FPaths::LaunchDir() (MikdashPhotoMode.cpp:939), i.e. the process working directory.

    .\capture_people_walk_frames.ps1 -Archive C:\Mikdash\Builds\Checkpoint-cp11-<stamp> -Label cp11
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [string[]]$Only,
    [int]$SettleSeconds = 55,
    # Single-shot A/B mode. Two launches of the SAME camera at different settle times take
    # one photograph each; if the people are in different places the world ran and they
    # walk, and if they are pixel-identical they do not. This uses exactly ONE F2 press per
    # process, so it cannot be confounded by a toggle that failed to unpause.
    [int]$ShotsOverride = 0
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
$shotRoot = Split-Path (Split-Path (Split-Path $exe -Parent) -Parent) -Parent
$photos = Join-Path $shotRoot 'MikdashPhotos'
$outDir = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\visual-review'

# Camera placements. World centimetres in the cooked Candidate48 map
# (/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough).
# Resident world positions were derived from Content/Distribution/People/people-candidate48.json
# through the Selected48 decoder (fixed origin -6200,0,0; factor 0.96), and cross-checked
# against the per-resident decodedWaypoint0 in
# SourceAssets/runtime-review/people/resident-bodies-v3-verify-Candidate48-20260909T014551106415Z.json.
# Kohen Gadol station 0 is (-3320, 0, 888) per the 290 s PIE recording
# SourceAssets/service-review/candidate-runtime-20260909T070801049654Z.json.
$views = @(
    # Mount deck, five residents inside a 6.3 m wide band; ovadya-ben-ephrayim's leg runs
    # (8728,-1200) -> (9304,-1200), i.e. straight down this camera's axis, 2.3 m to 8 m out.
    @{ name = 'deck-close-axis';  go = '8500 -1200 150 -3 0 0';   shots = 9; interval = 3 },
    # Same band, oblique, whole 51 m of it in one frame: height / gait / phase variety.
    @{ name = 'deck-group-wide';  go = '8300 -3300 320 -6 52 0';  shots = 6; interval = 4 },
    # Outer court, north half: yoav, miryam, naftali, pinchas, uriel, chananel, elchanan,
    # shulamis all loop inside this cone.
    @{ name = 'court-crowd-wide'; go = '2400 500 520 -6 50 0';    shots = 6; interval = 4 },
    # Outer court, tight across two shared lanes: miryam's y=2640 edge at 4.4 m and yoav's
    # y=2784 lane at 5.8 m, both traversed end to end every lap.
    @{ name = 'court-lane-close'; go = '4000 2200 445 -4 90 0';   shots = 9; interval = 3 },
    # The Kohen Gadol at his authored station 0, full body at ~4.2 m. bStartOnBeginPlay is
    # false on this map, so this sequence also tests whether he moves at all unattended.
    @{ name = 'kohen-close';      go = '-3020 -300 1008 -16 135 0'; shots = 6; interval = 4 }
)
if ($Only) { $views = @($views | Where-Object { $Only -contains $_.name }) }
if ($views.Count -eq 0) { throw 'no views selected' }
if ($ShotsOverride -gt 0) { foreach ($v in $views) { $v.shots = $ShotsOverride } }

foreach ($n in @('UnrealEditor','UnrealEditor-Cmd','AutomationTool','MikdashCourtyardV3')) {
    $p = Get-Process -Name $n -ErrorAction SilentlyContinue
    if ($p) { throw "refusing to launch: $n already running (pid $($p.Id -join ','))" }
}

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinPW {
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern IntPtr SetForegroundWindow(IntPtr h);
}
'@

function Send-Key([IntPtr]$hwnd, [int]$vk) {
    [void][WinPW]::PostMessage($hwnd, 0x0100, [IntPtr]$vk, [IntPtr]0)
    Start-Sleep -Milliseconds 120
    [void][WinPW]::PostMessage($hwnd, 0x0101, [IntPtr]$vk, [IntPtr]0)
}

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:LeashRadiusCm=900000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:FlySpeedCmPerSecond=3000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:SprintMultiplier=12.0,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FablePeopleProbe_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FablePeopleProbe_' + $Label + '_Settings'

$report = [ordered]@{
    status = 'starting'; label = $Label; archive = $Archive; exe = $exe
    map = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
    method = 'fixed camera, N photographs of the RUNNING world, F2/F9/F2 per shot because photo mode pauses'
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); views = @(); errors = @()
}
$receipt = Join-Path $outDir ("people-walk-frames-$Label.json")

foreach ($v in $views) {
    if (Test-Path -LiteralPath $photos) { Remove-Item -LiteralPath $photos -Recurse -Force }
    $argline = "-windowed -ResX=1600 -ResY=900 -nosplash -nosteam -notraceserver -notrace -noverifygc " +
               "$iniArgs -ExecCmds=`"Ghost,BugItGo $($v.go)`""
    $proc = Start-Process -FilePath $exe -ArgumentList $argline -PassThru -WorkingDirectory $shotRoot
    $entry = [ordered]@{ view = $v.name; bugItGo = $v.go; shotsRequested = $v.shots
                         intervalSeconds = $v.interval; pid = $proc.Id; shotTimes = @(); files = @() }
    try {
        Start-Sleep -Seconds $SettleSeconds
        $proc.Refresh()
        if ($proc.HasExited) { throw "exited early, code $($proc.ExitCode)" }
        $hwnd = $proc.MainWindowHandle
        $entry.hwnd = [string]$hwnd
        if ($hwnd -eq [IntPtr]::Zero) { throw 'no main window handle' }
        [void][WinPW]::SetForegroundWindow($hwnd)
        for ($i = 0; $i -lt $v.shots; $i++) {
            Send-Key $hwnd 0x71                  # F2 enter photo mode (pauses the world)
            Start-Sleep -Seconds 3               # view blend 0.25 s + HUD settle
            $entry.shotTimes += (Get-Date).ToUniversalTime().ToString('o')
            Send-Key $hwnd 0x78                  # F9 -> 2x PNG, serviced on a later draw
            Start-Sleep -Seconds 6
            Send-Key $hwnd 0x71                  # F2 leave photo mode (unpauses)
            Start-Sleep -Seconds $v.interval     # the world runs; people walk
            $proc.Refresh()
            if ($proc.HasExited) { throw "exited during shot $i, code $($proc.ExitCode)" }
        }
        $entry.peakWorkingSetMB = [int]($proc.PeakWorkingSet64 / 1MB)
    } catch {
        $entry.error = $_.Exception.Message
        $report.errors += "$($v.name): $($_.Exception.Message)"
    } finally {
        if (-not $proc.HasExited) { $proc.CloseMainWindow() | Out-Null; Start-Sleep -Seconds 4 }
        if (-not $proc.HasExited) { $proc | Stop-Process -Force }
    }
    Start-Sleep -Seconds 2
    $shots = @(Get-ChildItem -LiteralPath $photos -Filter *.png -EA SilentlyContinue | Sort-Object Name)
    $k = 0
    foreach ($s in $shots) {
        $k++
        $dest = Join-Path $outDir ("$Label-people-$($v.name)-{0:d2}.png" -f $k)
        Move-Item -LiteralPath $s.FullName -Destination $dest -Force
        $entry.files += @{ file = $dest; bytes = (Get-Item -LiteralPath $dest).Length; source = $s.Name }
    }
    $entry.shotsCaptured = $k
    if ($k -eq 0) { $report.errors += "$($v.name): no PNG produced (looked in $photos)" }
    $report.views += $entry
    ($report | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $receipt -Encoding utf8
    Write-Output ("{0}: {1}/{2} frames" -f $v.name, $k, $v.shots)
}

$got = ($report.views | ForEach-Object { $_.shotsCaptured } | Measure-Object -Sum).Sum
$want = ($views | ForEach-Object { $_.shots } | Measure-Object -Sum).Sum
$report.status = if ($got -eq $want) { 'frames_captured_visual_review_pending' } else { 'partial' }
$report.framesCaptured = $got; $report.framesRequested = $want
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
($report | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $receipt -Encoding utf8
Write-Output ("captured {0}/{1} -> {2}" -f $got, $want, $receipt)
