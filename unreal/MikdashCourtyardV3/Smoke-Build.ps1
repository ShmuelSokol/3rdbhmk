<#
    Bounded startup smoke of the packaged CHILD executable. Launch it directly so
    ownership never depends on a process name or finding a bootstrap descendant.
    Bootstrap / double-click behavior is not covered by this smoke.
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [ValidateRange(1, 3600)][int]$TimeoutSeconds = 300,
    [string]$ReceiptPath
)
$ErrorActionPreference = 'Stop'

function Test-SmokeProcessIdentity($Process, [int]$OwnedId, [datetime]$OwnedStart, [string]$OwnedPath) {
    # Never adopt another process, even one with the same name/path or recycled PID.
    try {
        return ($Process -and -not $Process.HasExited -and $Process.Id -eq $OwnedId -and
            $Process.StartTime.ToUniversalTime() -eq $OwnedStart.ToUniversalTime() -and
            [IO.Path]::GetFullPath($Process.Path) -eq [IO.Path]::GetFullPath($OwnedPath))
    } catch { return $false }
}

function Get-SmokeCommitBytes {
    # Same Win32_OperatingSystem metric as run_resident_runtime_movie.ps1.
    $memory = Get-CimInstance Win32_OperatingSystem
    if ($null -eq $memory.FreeVirtualMemory -or [long]$memory.FreeVirtualMemory -lt 0) {
        throw 'Cannot establish free commit; refusing unguarded smoke.'
    }
    [long]$memory.FreeVirtualMemory * 1KB
}

function Assert-SmokeMemory($Process, $Record) {
    $privateBytes = $Process.PrivateMemorySize64
    if ($null -eq $privateBytes -or [long]$privateBytes -lt 0) { throw 'Cannot establish owned child private memory.' }
    $freeBytes = Get-SmokeCommitBytes
    $Record.peakPrivateBytes = [math]::Max([long]$Record.peakPrivateBytes, [long]$privateBytes)
    $Record.minimumObservedCommitBytes = [math]::Min([long]$Record.minimumObservedCommitBytes, $freeBytes)
    if ($privateBytes -gt $Record.maximumPrivateBytes -or $freeBytes -lt $Record.reserveCommitBytes) {
        $Record.status = 'memory_guard_failed'
        throw "Owned smoke memory guard: private $privateBytes bytes (cap $($Record.maximumPrivateBytes)); free commit $freeBytes bytes (reserve $($Record.reserveCommitBytes))."
    }
}

$prefix = 'CheckpointSmoke_' + [guid]::NewGuid().ToString('N')
$res = [ordered]@{
    archive = $Archive
    startedUtc = (Get-Date).ToUniversalTime().ToString('o')
    timeoutSeconds = $TimeoutSeconds
    status = 'error'
    testSavePrefix = $prefix
    settingsSaveSlot = $prefix + '_Settings'
    windowStyle = 'Hidden'
    minimumStartCommitBytes = 9GB
    maximumPrivateBytes = 8GB
    # Stricter than the resident movie's 1.25 GiB reserve, per checkpoint policy.
    reserveCommitBytes = 2GB
    peakPrivateBytes = 0
    minimumObservedCommitBytes = [long]::MaxValue
    memoryPollSeconds = 1
    scope = 'Bounded direct-child startup only. NOT bootstrap, route, audio or interaction acceptance.'
}
$p = $null; $ownedStart = $null; $peakMB = 0
$windowOpened = $false; $everRan = $false; $secondsToWindow = $null
try {
    $child = Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
    $launcher = (Resolve-Path -LiteralPath $child -ErrorAction Stop).ProviderPath
    $res.launcher = $launcher
    # Preserve the serial native slot rule, including UAT/UBT hosted by dotnet.
    $busy = @(Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3, AutomationTool, UnrealBuildTool -ErrorAction SilentlyContinue)
    $busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" |
        Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' })
    if ($busy.Count) { throw 'Native slot is occupied; refusing smoke.' }

    $res.freeCommitBytesBeforeLaunch = Get-SmokeCommitBytes
    $res.minimumObservedCommitBytes = $res.freeCommitBytesBeforeLaunch
    if ($res.freeCommitBytesBeforeLaunch -lt $res.minimumStartCommitBytes) {
        $res.status = 'memory_refused'
        throw 'Requires 9 GiB free commit before smoke; no process launched.'
    }
    # Use both established Game INI overrides even if an older packaged binary
    # does not implement TestSavePrefix. Never use the user's save/settings slots.
    $ini = "-ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=$prefix,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=${prefix}_Settings,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False"
    $launchArguments = @('-windowed', '-ResX=1280', '-ResY=720', '-nosplash', "-TestSavePrefix=$prefix", $ini)
    $res.arguments = $launchArguments
    $p = Start-Process -FilePath $launcher -WorkingDirectory (Split-Path $launcher) `
        -ArgumentList $launchArguments -WindowStyle Hidden -PassThru
    # Retain the actual Process object for monitoring and cleanup, never a name lookup.
    $ownedStart = $p.StartTime
    $res.processId = $p.Id
    $res.processStartedUtc = $ownedStart.ToUniversalTime().ToString('o')
    $t0 = Get-Date
    $deadline = $t0.AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $p.Refresh()
        if (-not (Test-SmokeProcessIdentity $p $res.processId $ownedStart $launcher)) { break }
        $everRan = $true
        Assert-SmokeMemory $p $res
        $peakMB = [math]::Max($peakMB, [int]($p.WorkingSet64 / 1MB))
        if ($p.MainWindowHandle -ne 0) {
            $windowOpened = $true
            $secondsToWindow = [int]((Get-Date) - $t0).TotalSeconds
            break
        }
        Start-Sleep -Seconds 1
    }
    if ($windowOpened) {
        $stabilityDeadline = (Get-Date).AddSeconds(10)
        do {
            Start-Sleep -Seconds 1
            $p.Refresh()
            $res.stillAliveAfterWindow = Test-SmokeProcessIdentity $p $res.processId $ownedStart $launcher
            if (-not $res.stillAliveAfterWindow) { break }
            Assert-SmokeMemory $p $res
            $peakMB = [math]::Max($peakMB, [int]($p.WorkingSet64 / 1MB))
        } while ((Get-Date) -lt $stabilityDeadline)
    }
    $res.status = if ($windowOpened -and $res.stillAliveAfterWindow) { 'startup_verified' }
                  elseif ($windowOpened) { 'window_opened_then_exited' }
                  elseif ($everRan) { 'started_but_no_window' }
                  else { 'never_started' }
} catch {
    if ($res.status -notin @('memory_refused', 'memory_guard_failed')) { $res.status = 'error' }
    $res.error = $_.Exception.Message
} finally {
    # On EVERY outcome stop only our retained, identity-checked child handle.
    # No name-based kill and no taskkill /T (which can race with PID reuse).
    $res.cleanupSucceeded = $true
    if ($p) {
        try {
            $p.Refresh()
            if (-not $p.HasExited) {
                if (-not $ownedStart -or -not (Test-SmokeProcessIdentity $p $p.Id $ownedStart $launcher)) {
                    throw 'Cannot establish launched-process identity for cleanup; refusing to target another process.'
                }
                Stop-Process -InputObject $p -Force -ErrorAction Stop
                if (-not $p.WaitForExit(10000)) { throw 'Owned smoke process did not exit after cleanup.' }
            }
        } catch {
            $res.cleanupSucceeded = $false
            $res.cleanupError = $_.Exception.Message
            $res.status = 'cleanup_failed'
        }
    }
    $res.processEverStarted = $everRan
    $res.windowOpened = $windowOpened
    $res.secondsToWindow = $secondsToWindow
    $res.peakWorkingSetMB = $peakMB
    if ($res.minimumObservedCommitBytes -eq [long]::MaxValue) { $res.minimumObservedCommitBytes = $null }
    $res.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
    if ($ReceiptPath) { $res | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReceiptPath -Encoding utf8 }
}
Write-Output ($res | ConvertTo-Json -Depth 6)
if ($res.status -ne 'startup_verified') { exit 1 }
exit 0
