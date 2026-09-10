<#
    Capture the cp05b acceptance frames from a PACKAGED build, with no editor.

    WHY THIS EXISTS, AND WHY IT IS NOT capture_vegetation_frames.ps1
    A real-RHI editor cannot start on this box; the packaged Development exe renders fine at
    ~3 GB. A frame is the only artefact that catches a material falling back to the default in a
    cooked build, because the editor silently repairs a missing usage flag at runtime and every
    offline readback therefore stays green.

    TWO FIXES OVER THE cp07 ATTEMPT, WHICH CAPTURED NOTHING:

    1. THE PHOTO DIRECTORY. MikdashPhotoMode.cpp:939 writes to
           FPaths::ConvertRelativePathToFull(FPaths::LaunchDir()) / "MikdashPhotos"
       LaunchDir is the process WORKING DIRECTORY, not the exe folder. The frames that actually
       worked, cp05b, landed in <Archive>\Windows\MikdashPhotos - one level ABOVE the
       <Archive>\Windows\MikdashCourtyardV3\MikdashPhotos that capture_vegetation_frames.ps1
       computed and then searched. This script pins the working directory to <Archive>\Windows
       and looks there, which is exactly what produced the ten cp05b frames.

    2. FIXED SLEEPS BECOME POLLS. A freshly cooked build spends its first launch compiling
       pipeline state objects, so a 55 s settle can land before the map is up. This waits for the
       packaged game's own log to report the map loaded, then polls for the PNG to appear on disk
       instead of assuming a fixed shot time.

    The rest of the recipe is SourceAssets/visual-review/cp05b-frames-20260910.json, verbatim:
      * -notraceserver stops a Windows Firewall prompt that would hold the foreground
      * bShowMainMenuOnBoot=False (NOT bEnabled=False, which opens the legacy menu instead)
      * Ghost before BugItGo so the pawn does not fall through unstreamed terrain
      * PostMessage delivers DISCRETE key bindings only: F2 photo mode, F9 writes a 2x PNG.
        It cannot drive WASD or console text, so the camera is placed with BugItGo.

    .\capture_frame_defects.ps1 -Archive C:\Mikdash\Builds\Checkpoint-cp08-<stamp> -Label cp08
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [int]$MapWaitSeconds = 240,
    [int]$AfterMapSeconds = 20,
    [int]$ShotWaitSeconds = 90
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
$launchDir = Join-Path $Archive 'Windows'
$photos = Join-Path $launchDir 'MikdashPhotos'
$gameLog = Join-Path $Archive 'Windows\MikdashCourtyardV3\Saved\Logs\MikdashCourtyardV3.log'
$outDir = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\visual-review'

# The SAME cameras as cp05b, so an after-frame is comparable with the before-frame it answers.
# Source: SourceAssets/visual-review/cp05b-frames-20260910.json.
$views = @(
    @{ name = '04-precinct-plaza-aerial-SW-corner';        go = '-95000 175000 30000 -9 -45 0';
       answers = 'defect 3: the flat blue sea band on the horizon behind the city' },
    @{ name = '05-vegetation-hillside-above-canopy';       go = '68000 -9000 6400 -22 205 0';
       answers = 'defect 1: vegetation standing on the paved precinct deck' },
    @{ name = '07-north-gate-approach-meets-deck-and-ground'; go = '1500 -36500 -427 2 113 0';
       answers = 'defect 2: the bird flock rendering as flat black quads' },
    @{ name = '08-kotel-plaza-upper-deck-flight-to-wall';  go = '-20732 19230 -814 -6 -12 0';
       # cp05b-08 was taken AFTER ONE PRESS OF V, in the modern state, where the precinct deck is
       # hidden and the Kotel plaza is the visible surface. Without this the same BugItGo puts the
       # camera UNDER the precinct deck and the frame is not comparable with the one it answers.
       # V is a discrete binding (MikdashPlayerController.cpp:259 -> CyclePrecinctView), so
       # PostMessage drives it, exactly as F2 and F9.
       preKeys = @(0x56);
       answers = 'defects 1 and 2: the plant on the Kotel deck, and birds over the plaza' }
)

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinFD {
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern IntPtr SetForegroundWindow(IntPtr h);
}
'@

function Send-Key([IntPtr]$hwnd, [int]$vk) {
    # 0x0100 WM_KEYDOWN / 0x0101 WM_KEYUP. These route through UGameViewportClient::InputKey,
    # which is why discrete bindings work and text entry does not.
    [void][WinFD]::PostMessage($hwnd, 0x0100, [IntPtr]$vk, [IntPtr]0)
    Start-Sleep -Milliseconds 140
    [void][WinFD]::PostMessage($hwnd, 0x0101, [IntPtr]$vk, [IntPtr]0)
}

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:LeashRadiusCm=900000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:FlySpeedCmPerSecond=3000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:SprintMultiplier=12.0,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FrameDefects_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FrameDefects_' + $Label + '_Settings'

$report = [ordered]@{
    status = 'starting'; label = $Label; archive = $Archive; exe = $exe
    launchDir = $launchDir; photoDir = $photos
    recipe = 'SourceAssets/visual-review/cp05b-frames-20260910.json, same cameras as the before-frames'
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); frames = @(); errors = @()
}
$receipt = Join-Path $outDir ("frame-defects-frames-$Label.json")
function Save-Receipt { ($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $receipt -Encoding utf8 }

if (Test-Path -LiteralPath $photos) { Remove-Item -LiteralPath $photos -Recurse -Force }

foreach ($v in $views) {
    $arguments = "-windowed -ResX=1600 -ResY=900 -nosplash -nosteam -notraceserver -notrace -noverifygc " +
                 "$iniArgs -ExecCmds=`"Ghost,BugItGo $($v.go)`""
    if (Test-Path -LiteralPath $gameLog) { Remove-Item -LiteralPath $gameLog -Force -EA SilentlyContinue }
    $before = @()
    if (Test-Path -LiteralPath $photos) {
        $before = @(Get-ChildItem -LiteralPath $photos -Filter *.png -EA SilentlyContinue |
                    Select-Object -ExpandProperty FullName)
    }
    $proc = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru -WorkingDirectory $launchDir
    $entry = [ordered]@{ view = $v.name; answers = $v.answers; bugItGo = $v.go; pid = $proc.Id }
    try {
        # Wait for the game's OWN log to say the map is up, rather than guessing a settle time.
        $deadline = (Get-Date).AddSeconds($MapWaitSeconds)
        $mapUp = $false
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 5
            $proc.Refresh()
            if ($proc.HasExited) { throw "exited early, code $($proc.ExitCode)" }
            if (Test-Path -LiteralPath $gameLog) {
                $text = Get-Content -LiteralPath $gameLog -Raw -EA SilentlyContinue
                if ($text -and ($text -match 'LogLoad: Took .* to LoadMap' -or $text -match 'Bringing World .* up for play')) {
                    $mapUp = $true; break
                }
            }
        }
        $entry.mapReported = $mapUp
        if (-not $mapUp) { throw "map never reported loaded within $MapWaitSeconds s" }
        Start-Sleep -Seconds $AfterMapSeconds

        $proc.Refresh()
        $entry.peakWorkingSetMB = [int]($proc.PeakWorkingSet64 / 1MB)
        $hwnd = $proc.MainWindowHandle
        $entry.hwnd = [string]$hwnd
        if ($hwnd -eq [IntPtr]::Zero) { throw 'no main window handle' }
        [void][WinFD]::SetForegroundWindow($hwnd)
        if ($v.preKeys) {
            foreach ($k in $v.preKeys) { Send-Key $hwnd $k; Start-Sleep -Seconds 4 }
            $entry.preKeysSent = ($v.preKeys | ForEach-Object { '0x{0:X2}' -f $_ }) -join ','
            Start-Sleep -Seconds 6   # let the state swap settle before the shot
        }
        Send-Key $hwnd 0x71          # F2 - photo mode (hides the HUD)
        Start-Sleep -Seconds 6
        Send-Key $hwnd 0x78          # F9 - HighResShot 2x -> PNG

        # Poll for the file instead of assuming how long a 3840x2160 shot takes to encode.
        $shot = $null
        $shotDeadline = (Get-Date).AddSeconds($ShotWaitSeconds)
        while ((Get-Date) -lt $shotDeadline) {
            Start-Sleep -Seconds 3
            $candidate = Get-ChildItem -LiteralPath $photos -Filter *.png -EA SilentlyContinue |
                         Where-Object { $before -notcontains $_.FullName } |
                         Sort-Object LastWriteTime | Select-Object -Last 1
            if ($candidate -and $candidate.Length -gt 200000) { $shot = $candidate; break }
        }
        if (-not $shot) { throw "no new PNG appeared in $photos within $ShotWaitSeconds s" }
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
    } else {
        $entry.file = $null
    }
    $report.frames += $entry
    Save-Receipt
}

$got = @($report.frames | Where-Object { $_.file }).Count
$report.status = if ($got -eq $views.Count) { 'frames_captured_visual_review_pending' } else { 'incomplete' }
$report.capturedCount = $got
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
Save-Receipt
Write-Output ("captured {0}/{1} -> {2}" -f $got, $views.Count, $receipt)
