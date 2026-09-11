<#
    Capture the two HERODIAN ASHLAR acceptance frames from a PACKAGED build, with no editor.

    Derived line-for-line from Scripts\capture_frame_defects.ps1 (same launch flags, same photo
    directory reasoning, same map-loaded poll, same PostMessage key delivery). It exists as a separate
    file only so the ashlar pass and the vegetation pass can run without editing each other's script.

    The two cameras are the ones that produced the BEFORE frames, verbatim from
    SourceAssets\visual-review\cp05b-frames-20260910.json:

      01  spawn, no teleport, facing the Heichal. Shows the Azarah PAVING and the wall in ONE frame -
          this is the in-frame colour and grain control. cp05b-01-azarah-facing-heichal-spawn.png
      02  1752,1200,580 pitch 5 yaw 0, 4 m from the inner eastern gate wall jamb at eye height. The
          only walking-height photograph of the Herodian wall.
          cp05b-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png

    HONEST DIFFERENCE FROM THE BEFORE FRAME: cp05b-02 was reached without BugItGo, and the cp05b
    receipt records that BugItGo leaves a thin black sliver of the player mesh near the camera.
    PostMessage cannot drive photo-mode WASD (it needs real Slate focus), so BugItGo is the only way to
    place the camera from a script. Frame 01 needs no teleport at all and is therefore exactly
    comparable; frame 02 may carry that sliver at an edge. It does not touch the wall surface, which is
    what is being judged, and the receipt says so.

      .\capture_frame_ashlar.ps1 -Archive C:\Mikdash\Builds\Checkpoint-cp11-<stamp> -Label cp11
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    # Optional map package to open instead of GameDefaultMap, e.g. the anti-repeat frame-trial copy
    # cooked alongside Candidate48. Empty = the configured default map, exactly as before.
    [ValidatePattern('^(|/Game/[A-Za-z0-9_/]+)$')][string]$Map = '',
    [int]$MapWaitSeconds = 300,
    [int]$AfterMapSeconds = 25,
    [int]$ShotWaitSeconds = 120,
    [int]$WindowWaitSeconds = 240,
    [int]$Attempts = 2
)
$ErrorActionPreference = 'Stop'

$exe = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged exe not found: $exe" }
# LaunchDir is the process WORKING DIRECTORY, one level ABOVE the exe folder. This is where the ten
# cp05b frames actually landed; getting it wrong is why the cp07 attempt captured nothing.
$launchDir = Join-Path $Archive 'Windows'
$photos = Join-Path $launchDir 'MikdashPhotos'
$gameLog = Join-Path $Archive 'Windows\MikdashCourtyardV3\Saved\Logs\MikdashCourtyardV3.log'
$outDir = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\visual-review'

$views = @(
    @{ name = '01-azarah-facing-heichal-spawn'; go = $null
       answers = 'colour and grain against the approved paving in the SAME frame and the same light' },
    @{ name = '02-herodian-ashlar-inner-east-gate-jamb-walkingheight'; go = '1752 1200 580 5 0 0'
       answers = 'the boss, the micro-grain and the tile repeat at walking height, 4 m from the face' }
)

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinFA {
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern IntPtr SetForegroundWindow(IntPtr h);
}
'@

function Send-Key([IntPtr]$hwnd, [int]$vk) {
    [void][WinFA]::PostMessage($hwnd, 0x0100, [IntPtr]$vk, [IntPtr]0)
    Start-Sleep -Milliseconds 140
    [void][WinFA]::PostMessage($hwnd, 0x0101, [IntPtr]$vk, [IntPtr]0)
}

$iniArgs = '-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:LeashRadiusCm=900000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:FlySpeedCmPerSecond=3000,' +
           '[/Script/MikdashRuntime.MikdashPhotoMode]:SprintMultiplier=12.0,' +
           '[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=Ashlar_' + $Label + ',' +
           '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=Ashlar_' + $Label + '_Settings'

$report = [ordered]@{
    status = 'starting'; label = $Label; archive = $Archive; exe = $exe
    launchDir = $launchDir; photoDir = $photos
    map = $(if ($Map) { $Map } else { 'GameDefaultMap' })
    recipe = 'SourceAssets/visual-review/cp05b-frames-20260910.json, the same two cameras as the before-frames'
    compares = @{
        '01' = 'SourceAssets/visual-review/cp05b-01-azarah-facing-heichal-spawn.png'
        '02' = 'SourceAssets/visual-review/cp05b-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png'
    }
    startedUtc = (Get-Date).ToUniversalTime().ToString('o'); frames = @(); errors = @()
}
$receipt = Join-Path $outDir ("frame-ashlar-$Label.json")
function Save-Receipt { ($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $receipt -Encoding utf8 }

if (Test-Path -LiteralPath $photos) { Remove-Item -LiteralPath $photos -Recurse -Force }

foreach ($v in $views) {
  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    $arguments = "$Map -windowed -ResX=1600 -ResY=900 -nosplash -nosteam -notraceserver -notrace -noverifygc $iniArgs"
    if ($v.go) { $arguments += " -ExecCmds=`"Ghost,BugItGo $($v.go)`"" }
    if (Test-Path -LiteralPath $gameLog) { Remove-Item -LiteralPath $gameLog -Force -EA SilentlyContinue }
    $before = @()
    if (Test-Path -LiteralPath $photos) {
        $before = @(Get-ChildItem -LiteralPath $photos -Filter *.png -EA SilentlyContinue |
                    Select-Object -ExpandProperty FullName)
    }
    $proc = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru -WorkingDirectory $launchDir
    $entry = [ordered]@{ view = $v.name; answers = $v.answers; bugItGo = $v.go; pid = $proc.Id }
    try {
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

        # POLL for the window. A freshly cooked build's FIRST launch spends minutes on
        # "Encountered a new graphics PSO ... Missed", and MainWindowHandle is 0 (or $null, which
        # PowerShell will not even cast to IntPtr) until the window actually exists. Reading it once,
        # as the cp11c attempt did, throws before the game has finished starting.
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
        $entry.hwnd = [string]$hwnd
        if ($hwnd -eq [IntPtr]::Zero) { throw "no main window handle after $WindowWaitSeconds s" }
        [void][WinFA]::SetForegroundWindow($hwnd)
        Send-Key $hwnd 0x71          # F2 - photo mode (hides the HUD)
        Start-Sleep -Seconds 6
        Send-Key $hwnd 0x78          # F9 - HighResShot 2x -> 3840x2160 PNG

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
    if (-not $entry.file -and $attempt -lt $Attempts) {
        Write-Output ("retrying {0} (attempt {1} failed: {2})" -f $v.name, $attempt, $entry.error)
        Start-Sleep -Seconds 15
        continue
    }
    break
  }
}

# The cooked build silently substitutes the default material when a usage flag is missing on a PARENT
# UMaterial, and only the packaged log ever says so. Pull the LogMaterial lines for this pass's assets.
if (Test-Path -LiteralPath $gameLog) {
    $log = Get-Content -LiteralPath $gameLog -Raw -EA SilentlyContinue
    $report.materialWarnings = @(
        [regex]::Matches($log, '(?m)^.*LogMaterial:\s*(Warning|Error).*$') |
        ForEach-Object { $_.Value.Trim() } | Select-Object -Unique
    )
    $report.ashlarFallback = @($report.materialWarnings | Where-Object { $_ -match 'HerodianV[45]|LimestoneAshlar|LimestoneTrim|PBR_Tiled|AntiRepeat' })
}

$got = @($report.frames | Where-Object { $_.file }).Count
$report.status = if ($got -eq $views.Count) { 'frames_captured_visual_review_pending' } else { 'incomplete' }
$report.capturedCount = $got
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
Save-Receipt
Write-Output ("captured {0}/{1} -> {2}" -f $got, $views.Count, $receipt)
