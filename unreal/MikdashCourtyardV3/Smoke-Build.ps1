<#
    Bounded startup smoke for a packaged build: does the thing the user double-clicks open?

    Split out of Checkpoint-Build.ps1 so a build that already exists can be re-tested without
    paying for another cook.

    The subtlety this exists to handle: the exe in the archive root is a LAUNCHER STUB that
    spawns the real game under MikdashCourtyardV3\Binaries\Win64 and then exits. Watching the
    handle returned by Start-Process therefore reports failure a second or two in, while the
    game is still loading. Watch for a process by NAME with a real window handle instead, and
    treat "it ran for a while, reached a plausible working set, then exited" as its own
    outcome rather than as success.

        .\Smoke-Build.ps1 -Archive C:\Mikdash\Builds\Checkpoint-cp01-<stamp>
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [int]$TimeoutSeconds = 300,
    [string]$ReceiptPath
)
$ErrorActionPreference = 'Stop'

$root  = Join-Path $Archive 'Windows'
$child = Join-Path $root 'MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
$stub  = Join-Path $root 'MikdashCourtyardV3.exe'
$launcher = if (Test-Path -LiteralPath $stub) { $stub } elseif (Test-Path -LiteralPath $child) { $child }
            else { throw "No launchable exe under $root" }

if (Get-Process MikdashCourtyardV3 -ErrorAction SilentlyContinue) {
    throw 'A build is already running; close it before smoking another'
}

$res = [ordered]@{
    archive = $Archive; launcher = $launcher
    startedUtc = (Get-Date).ToUniversalTime().ToString('o')
    timeoutSeconds = $TimeoutSeconds
}
$p = Start-Process -FilePath $launcher -ArgumentList '-windowed', '-ResX=1280', '-ResY=720', '-nosplash' -PassThru

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$peakMB = 0; $windowOpened = $false; $everRan = $false; $secondsToWindow = $null
$t0 = Get-Date
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    $procs = @(Get-Process MikdashCourtyardV3 -ErrorAction SilentlyContinue)
    if ($procs.Count) {
        $everRan = $true
        $peakMB = [math]::Max($peakMB, [int](($procs | Measure-Object WorkingSet64 -Maximum).Maximum / 1MB))
        if ($procs | Where-Object { $_.MainWindowHandle -ne 0 }) {
            $windowOpened = $true
            $secondsToWindow = [int]((Get-Date) - $t0).TotalSeconds
            break
        }
    } elseif ($everRan) {
        break        # it started and is now gone - a crash or a clean early exit, not success
    }
}

# Let a window that just appeared actually finish its first frames before judging it.
if ($windowOpened) {
    Start-Sleep -Seconds 10
    $procs = @(Get-Process MikdashCourtyardV3 -ErrorAction SilentlyContinue)
    $res.stillAliveAfterWindow = [bool]$procs.Count
    if ($procs.Count) { $peakMB = [math]::Max($peakMB, [int](($procs | Measure-Object WorkingSet64 -Maximum).Maximum / 1MB)) }
}

foreach ($proc in @(Get-Process MikdashCourtyardV3 -ErrorAction SilentlyContinue) + @($p)) {
    if ($proc -and (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}

$res.processEverStarted = $everRan
$res.windowOpened       = $windowOpened
$res.secondsToWindow    = $secondsToWindow
$res.peakWorkingSetMB   = $peakMB
$res.finishedUtc        = (Get-Date).ToUniversalTime().ToString('o')
$res.status =
    if ($windowOpened -and $res.stillAliveAfterWindow) { 'playable' }
    elseif ($windowOpened)                             { 'window_opened_then_exited' }
    elseif ($everRan)                                  { 'started_but_no_window' }
    else                                               { 'never_started' }
$res.scope = 'Bounded startup only. NOT route, audio or interaction acceptance.'

if ($ReceiptPath) { $res | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReceiptPath -Encoding utf8 }
Write-Output ($res | ConvertTo-Json -Depth 6)
if ($res.status -ne 'playable') { exit 1 }
