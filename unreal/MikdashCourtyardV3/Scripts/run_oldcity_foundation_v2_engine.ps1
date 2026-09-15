<#
    OldCityFoundationV2: every engine step, one at a time, each waiting for the native slot.

    Launch DETACHED (the harness watchdog kills long tracked waits):
      Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
        '-File','C:\Mikdash\Working-5.8\MikdashCourtyardV3\Scripts\run_oldcity_foundation_v2_engine.ps1',
        '-Steps','preflight48,apply48,verify48,apply50,verify50'
    Undo both maps:   ... -File run_oldcity_foundation_v2_engine.ps1 -Revert
    Progress: SourceAssets\context-review\OldCityFoundationV2\engine\runner-progress.json (poll it).

    Steps: preflight48 preflight50 apply48 apply50 verify48 verify50 revert48 revert50
           cook            Checkpoint-Build.ps1 -Label <Label>, started with Start-Process and waited on
           capture:<archiveDir>|<label>|<only,views>   Scripts\capture_city_facade.ps1
           captureafter:<label>|<only,views>          same, on the newest Checkpoint-<Label>-* archive
           done            writes C:\Mikdash\Working-5.8\SLOT-oldcity-done.txt

    The slot is ours only when BOTH SLOT-cp26-review-done.txt and SLOT-residents-done.txt exist, no
    UnrealEditor / UnrealEditor-Cmd / MikdashCourtyardV3 runs, no dotnet runs AutomationTool or
    UnrealBuildTool, and commit headroom (Commit Limit - Committed Bytes) is at least -NeedCommitGB.
#>
param([string]$Steps = 'preflight48', [switch]$Revert, [int]$WaitMinutes = 720, [double]$NeedCommitGB = 12.0,
      [string]$Label = 'oldcity01', [int]$EditorTimeoutMinutes = 180,
      # Cook with the already verified binaries and NO UAT build step. Use when this work is
      # content-only and someone else's C++ is mid-edit in the shared tree (15 Sep: an in-flight
      # KotelClosureRuntime.cpp failed to compile and took the whole cook down with UAT exit 6).
      # The resulting archive contains the previously verified runtime, not any pending C++.
      [switch]$CookUseExistingBinaries)
$ErrorActionPreference = 'Stop'
$project = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
$uproject = Join-Path $project 'MikdashCourtyardV3.uproject'
$editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$script = Join-Path $project 'Scripts\release_oldcity_foundations_v2.py'
$receipts = Join-Path $project 'SourceAssets\context-review\OldCityFoundationV2\engine'
$logs = 'C:\Mikdash\Working-5.8\OldCityFoundationV2-logs'
$progress = Join-Path $receipts 'runner-progress.json'
$slotFiles = @('C:\Mikdash\Working-5.8\SLOT-cp26-review-done.txt', 'C:\Mikdash\Working-5.8\SLOT-residents-done.txt')
New-Item -ItemType Directory -Force -Path $receipts, $logs | Out-Null
if ($Revert) { $Steps = 'revert48,revert50' }
$todo = @($Steps.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$state = [ordered]@{ started = (Get-Date).ToUniversalTime().ToString('o'); pid = $PID; todo = $todo; steps = [ordered]@{}; status = 'running' }

function Save {
    $json = $state | ConvertTo-Json -Depth 8
    for ($i = 0; $i -lt 10; $i++) { try { [IO.File]::WriteAllText($progress, $json); return } catch { Start-Sleep -Milliseconds 300 } }
}
function Commit-Free-GB {
    $m = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    [math]::Round(($m.CommitLimit - $m.CommittedBytes) / 1GB, 2)
}
function Busy {
    $b = @(Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName)
    $b += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' } |
            ForEach-Object { if ($_.CommandLine -match 'AutomationTool') { 'dotnet(UAT)' } else { 'dotnet(UBT)' } })
    return @($b | Select-Object -Unique)
}
function Wait-Slot([string]$step) {
    $deadline = (Get-Date).AddMinutes($WaitMinutes)
    while ($true) {
        $missing = @($slotFiles | Where-Object { -not (Test-Path -LiteralPath $_) })
        $busy = Busy
        $free = Commit-Free-GB
        if (-not $missing.Count -and -not $busy.Count -and $free -ge $NeedCommitGB) {
            Start-Sleep -Seconds (Get-Random -Minimum 15 -Maximum 40)   # another agent may be between chained steps
            if (-not (Busy).Count -and (Commit-Free-GB) -ge $NeedCommitGB) { return $free }
        }
        $state.steps[$step] = [ordered]@{ status = 'waiting_for_slot'; missingSlotFiles = $missing; busy = ($busy -join ','); commitFreeGB = $free; utc = (Get-Date).ToUniversalTime().ToString('o') }
        Save
        if ((Get-Date) -gt $deadline) { throw "slot never freed for $step" }
        Start-Sleep -Seconds 30
    }
}
function Newest([string]$pattern, [datetime]$after) {
    Get-ChildItem -LiteralPath $receipts -Filter $pattern -EA SilentlyContinue | Where-Object { $_.LastWriteTime -ge $after } |
        Sort-Object LastWriteTime | Select-Object -Last 1
}
function Run-Editor([string]$step, [string]$mode, [string]$target, [string[]]$okPrefixes) {
    $free = Wait-Slot $step
    $t0 = Get-Date
    $log = Join-Path $logs ("ocf2-$step-" + $t0.ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '.log')
    $argline = "`"$uproject`" /Engine/Maps/Entry -ExecutePythonScript=$($script.Replace('\','/')) -OCF2$mode -OCF2Target=$target " +
               "-unattended -nullrhi -NoSplash -NoSound -abslog=`"$log`""
    $state.steps[$step] = [ordered]@{ status = 'running'; startedUtc = $t0.ToUniversalTime().ToString('o'); commitFreeGBAtLaunch = $free; log = $log; args = $argline }
    Save
    $p = Start-Process -FilePath $editor -ArgumentList $argline -PassThru -WindowStyle Hidden
    $peak = 0L
    while (-not $p.HasExited) {
        Start-Sleep -Seconds 10
        try { $p.Refresh(); $peak = [math]::Max([long]$peak, [long]$p.PeakPagedMemorySize64) } catch {}
        if ((Get-Date) -gt $t0.AddMinutes($EditorTimeoutMinutes)) { throw "$step exceeded $EditorTimeoutMinutes minutes (editor PID $($p.Id) left running for inspection)" }
    }
    $r = Newest ("native-" + $mode.ToLower() + "-$target-*.json") $t0
    $status = if ($r) { (Get-Content -LiteralPath $r.FullName -Raw | ConvertFrom-Json).status } else { 'no_receipt' }
    $state.steps[$step] = [ordered]@{ status = $status; receipt = $(if ($r) { $r.FullName } else { $null }); exitCode = $p.ExitCode;
                                      peakPrivateGB = [math]::Round($peak / 1GB, 2); log = $log; finishedUtc = (Get-Date).ToUniversalTime().ToString('o') }
    Save
    if (-not @($okPrefixes | Where-Object { $status -like "$_*" }).Count) { throw "$step ended with $status" }
}
function Latest-Archive { Get-ChildItem 'C:\Mikdash\Builds' -Directory -Filter "Checkpoint-$Label-*" -EA SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1 }
function Run-Capture([string]$step, [string]$archive, [string]$capLabel, [string]$only) {
    $only = $only.Replace('+', ',')    # views are '+'-separated inside a step because steps are ','-separated
    Wait-Slot $step | Out-Null
    $state.steps[$step] = [ordered]@{ status = 'running'; archive = $archive; label = $capLabel; only = $only }
    Save
    $capLog = Join-Path $logs "capture-$capLabel.txt"
    $p = Start-Process powershell -PassThru -WindowStyle Hidden -RedirectStandardOutput $capLog -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $project 'Scripts\capture_city_facade.ps1'),
        '-Archive', $archive, '-Label', $capLabel, '-Only', $only, '-IncludeFoundationViews')
    $p.WaitForExit()
    $receipt = Join-Path $project "SourceAssets\visual-review\city-facade\city-facade-frames-$capLabel.json"
    $st = if (Test-Path -LiteralPath $receipt) { (Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json).status } else { 'no_receipt' }
    $state.steps[$step] = [ordered]@{ status = $st; receipt = $receipt; exitCode = $p.ExitCode; archive = $archive; log = $capLog }
    Save
}

try {
    foreach ($s in $todo) {
        switch -Regex ($s) {
            '^preflight48$' { Run-Editor $s 'Preflight' 'Candidate48' @('preflight_ok') }
            '^preflight50$' { Run-Editor $s 'Preflight' 'Main50' @('preflight_ok') }
            '^apply48$'     { Run-Editor $s 'Apply' 'Candidate48' @('applied_') }
            '^apply50$'     { Run-Editor $s 'Apply' 'Main50' @('applied_') }
            '^verify48$'    { Run-Editor $s 'Verify' 'Candidate48' @('verified_') }
            '^verify50$'    { Run-Editor $s 'Verify' 'Main50' @('verified_') }
            '^revert48$'    { Run-Editor $s 'Revert' 'Candidate48' @('reverted_', 'nothing_to_revert') }
            '^revert50$'    { Run-Editor $s 'Revert' 'Main50' @('reverted_', 'nothing_to_revert') }
            '^cook$' {
                $free = Wait-Slot $s
                $t0 = Get-Date
                $cookLog = Join-Path $logs "cook-$Label.txt"
                $state.steps[$s] = [ordered]@{ status = 'running'; startedUtc = $t0.ToUniversalTime().ToString('o'); commitFreeGBAtLaunch = $free; log = $cookLog }
                Save
                $cookArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $project 'Checkpoint-Build.ps1'), '-Label', $Label)
                if ($CookUseExistingBinaries) { $cookArgs += '-UseExistingBinaries' }
                $state.steps[$s].useExistingBinaries = [bool]$CookUseExistingBinaries
                Save
                $p = Start-Process powershell -PassThru -WindowStyle Hidden -RedirectStandardOutput $cookLog -ArgumentList $cookArgs
                $p.WaitForExit()
                $arch = Latest-Archive
                $ok = $arch -and $arch.LastWriteTime -ge $t0
                $state.steps[$s] = [ordered]@{ status = $(if ($ok) { 'archived' } else { 'no_archive' }); archive = $(if ($arch) { $arch.FullName } else { $null }); exitCode = $p.ExitCode; log = $cookLog }
                if ($ok) { $state.archive = $arch.FullName }
                Save
                if (-not $ok) { throw 'cook produced no new archive' }
            }
            '^capture:' {
                $parts = $s.Substring(8).Split('|')
                Run-Capture $s $parts[0] $parts[1] $parts[2]
            }
            '^captureafter:' {
                $parts = $s.Substring(13).Split('|')
                $arch = if ($state.archive) { $state.archive } else { (Latest-Archive).FullName }
                Run-Capture $s $arch $parts[0] $parts[1]
            }
            '^done$' {
                [IO.File]::WriteAllText('C:\Mikdash\Working-5.8\SLOT-oldcity-done.txt', "OldCityFoundationV2 engine work finished $((Get-Date).ToUniversalTime().ToString('o'))`r`n")
                $state.steps[$s] = [ordered]@{ status = 'slot_released' }
                Save
            }
            default { throw "unknown step $s" }
        }
    }
    $state.status = 'done'
} catch {
    $state.status = 'failed'
    $state.error = $_.Exception.Message
} finally {
    $state.finished = (Get-Date).ToUniversalTime().ToString('o')
    Save
}
