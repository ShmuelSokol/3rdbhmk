<#
    Capture vegetation frames from a PACKAGED build, with no editor.

    Why this exists: a real-RHI EDITOR cannot start on this box (~19.9 GB reserved against ~20 GB
    of commit headroom), but the packaged Development exe renders fine at ~2.9 GB. That is the
    only way this project can get a frame, and a frame is the only thing that catches a material
    that falls back to WorldGridMaterial in a cooked build while every editor readback stays green.

    The recipe is SourceAssets/visual-review/cp05b-frames-20260910.json, reused verbatim:
      * -notraceserver stops a Windows Firewall prompt that would hold the foreground
      * bShowMainMenuOnBoot=False (NOT bEnabled=False, which opens the legacy menu instead)
      * Ghost before BugItGo so the pawn does not fall through unstreamed terrain
      * PostMessage delivers DISCRETE key bindings only: F2 photo mode, F9 writes a 2x PNG.
        It cannot drive WASD or console text, so the camera is placed with BugItGo.

    .\capture_vegetation_frames.ps1 -Archive C:\Mikdash\Builds\Checkpoint-cp07-<stamp> -Label cp07
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [int]$SettleSeconds = 55,
    [int]$ShotSeconds = 22
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
# Photo mode writes into <working directory>/MikdashPhotos, so the working directory is chosen
# here and the launch below is pinned to it.
$shotRoot = Split-Path (Split-Path (Split-Path $exe -Parent) -Parent) -Parent
$photos = Join-Path $shotRoot 'MikdashPhotos'
$outDir = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\visual-review'

# Views chosen to put the vegetation and a KNOWN-GOOD control (precinct deck, city, sky) in the
# same frame, so a fallback material is unmistakable rather than a matter of opinion.
$views = @(
    @{ name = 'hillside-near-mid-far-yaw198'; go = '64498 -13260 3175 -10 198 0' },
    @{ name = 'hillside-above-canopy';        go = '68000 -9000 6400 -22 205 0' },
    @{ name = 'olive-midrange-25m';           go = '62900 -12700 2600 -6 180 0' }
)

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win {
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern IntPtr SetForegroundWindow(IntPtr h);
}
'@

function Send-Key([IntPtr]$hwnd, [int]$vk) {
    # 0x0100 WM_KEYDOWN / 0x0101 WM_KEYUP. These route through UGameViewportClient::InputKey,
    # which is why discrete bindings work and text entry does not.
    [void][Win]::PostMessage($hwnd, 0x0100, [IntPtr]$vk, [IntPtr]0)
    Start-Sleep -Milliseconds 120
    [void][Win]::PostMessage($hwnd, 0x0101, [IntPtr]$vk, [IntPtr]0)
}

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:LeashRadiusCm=900000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:FlySpeedCmPerSecond=3000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:SprintMultiplier=12.0,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FableVegProbe_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FableVegProbe_' + $Label + '_Settings'

$report = [ordered]@{
    status = 'starting'; label = $Label; archive = $Archive; exe = $exe
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); frames = @(); errors = @()
}
$receipt = Join-Path $outDir ("vegetation-frames-$Label.json")

if (Test-Path -LiteralPath $photos) { Remove-Item -LiteralPath $photos -Recurse -Force }

foreach ($v in $views) {
    $args = "-windowed -ResX=1600 -ResY=900 -nosplash -nosteam -notraceserver -notrace -noverifygc " +
            "$iniArgs -ExecCmds=`"Ghost,BugItGo $($v.go)`""
    # -WorkingDirectory IS LOAD-BEARING. Photo mode writes MikdashPhotos/ under the process's
    # working directory, NOT under the exe. Without this the PNGs land wherever the shell happened
    # to be and the run reports "no PNG produced" while three perfectly good frames sit elsewhere.
    $proc = Start-Process -FilePath $exe -ArgumentList $args -PassThru -WorkingDirectory $shotRoot
    $entry = [ordered]@{ view = $v.name; bugItGo = $v.go; pid = $proc.Id }
    try {
        Start-Sleep -Seconds $SettleSeconds
        $proc.Refresh()
        if ($proc.HasExited) { throw "exited early, code $($proc.ExitCode)" }
        $entry.peakWorkingSetMB = [int]($proc.PeakWorkingSet64 / 1MB)
        $hwnd = $proc.MainWindowHandle
        $entry.hwnd = [string]$hwnd
        if ($hwnd -eq [IntPtr]::Zero) { throw 'no main window handle' }
        [void][Win]::SetForegroundWindow($hwnd)
        Send-Key $hwnd 0x71          # F2 - photo mode (hides HUD)
        Start-Sleep -Seconds 5
        Send-Key $hwnd 0x78          # F9 - HighResShot 2x -> PNG
        Start-Sleep -Seconds $ShotSeconds
    } catch {
        $entry.error = $_.Exception.Message
        $report.errors += "$($v.name): $($_.Exception.Message)"
    } finally {
        if (-not $proc.HasExited) { $proc.CloseMainWindow() | Out-Null; Start-Sleep -Seconds 4 }
        if (-not $proc.HasExited) { $proc | Stop-Process -Force }
    }
    $shot = Get-ChildItem -LiteralPath $photos -Filter *.png -EA SilentlyContinue |
            Sort-Object LastWriteTime | Select-Object -Last 1
    if ($shot) {
        $dest = Join-Path $outDir ("$Label-veg-$($v.name).png")
        Move-Item -LiteralPath $shot.FullName -Destination $dest -Force
        $entry.file = $dest; $entry.bytes = (Get-Item -LiteralPath $dest).Length
    } else {
        $entry.file = $null; $report.errors += "$($v.name): no PNG produced"
    }
    $report.frames += $entry
    ($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $receipt -Encoding utf8
}

$got = @($report.frames | Where-Object { $_.file }).Count
$report.status = if ($got -eq $views.Count) { 'frames_captured_visual_review_pending' } else { 'incomplete' }
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $receipt -Encoding utf8
Write-Output ("captured {0}/{1} -> {2}" -f $got, $views.Count, $receipt)
