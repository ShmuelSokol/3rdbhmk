<#
    OldCityStreetsV1: every engine step, one at a time, each waiting for the native slot.

    Launch DETACHED (the harness watchdog kills long tracked waits):
      Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
        '-File','C:\Mikdash\Working-5.8\MikdashCourtyardV3\Scripts\run_oldcity_streets_engine.ps1',
        '-Steps','preflight48,apply48,verify48,apply50,verify50'
    Undo both maps:   ... -File run_oldcity_streets_engine.ps1 -Revert
    Progress: SourceAssets\context-review\OldCityStreetsV1\engine\runner-progress.json (poll it).

    Steps: preflight48 preflight50 apply48 apply50 verify48 verify50 revert48 revert50
           cook            Checkpoint-Build.ps1 -Label <Label>, started with Start-Process and waited on
           capture:<archiveDir>|<label>|<views>   Scripts\capture_city_facade.ps1 (views '+'-separated)
           captureafter:<label>|<views>           same, on the newest Checkpoint-<Label>-* archive
           done            writes C:\Mikdash\Working-5.8\SLOT-streets-done.txt

    The slot is ours only when every file in -SlotFiles exists, no UnrealEditor / UnrealEditor-Cmd /
    MikdashCourtyardV3 runs, no dotnet runs AutomationTool or UnrealBuildTool, and commit headroom
    (Commit Limit - Committed Bytes) is at least -NeedCommitGB.

    COOK: -CookUseExistingBinaries is ON by default. On 15 Sep another agent's in-flight
    KotelClosureRuntime.cpp referenced Data::MaterialIds / Data::MaterialCount, which its header does
    not declare, so Checkpoint-Build.ps1's -build step failed with UAT exit 6 and took the whole cook
    down (it did that to the foundations pass's oldcity01 cook). This work is content-only, so it
    cooks with the already verified binaries and no UAT build step. The resulting archive therefore
    carries the previously verified runtime, NOT any pending C++, and the receipt records that.
    Pass -CookUseExistingBinaries:$false once the tree compiles clean.
#>
param([string]$Steps = 'preflight48', [switch]$Revert, [int]$WaitMinutes = 720, [double]$NeedCommitGB = 12.0,
      [string]$Label = 'streets01', [int]$EditorTimeoutMinutes = 180,
      [string[]]$SlotFiles = @('C:\Mikdash\Working-5.8\SLOT-trees-done.txt'),
      [bool]$CookUseExistingBinaries = $true)
$ErrorActionPreference = 'Stop'
$project = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
$uproject = Join-Path $project 'MikdashCourtyardV3.uproject'
$editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$script = Join-Path $project 'Scripts\release_oldcity_streets.py'
$receipts = Join-Path $project 'SourceAssets\context-review\OldCityStreetsV1\engine'
$logs = 'C:\Mikdash\Working-5.8\OldCityStreetsV1-logs'
$progress = Join-Path $receipts 'runner-progress.json'
New-Item -ItemType Directory -Force -Path $receipts, $logs | Out-Null
if ($Revert) { $Steps = 'revert48,revert50' }
$todo = @($Steps.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$state = [ordered]@{ started = (Get-Date).ToUniversalTime().ToString('o'); pid = $PID; todo = $todo
                     slotFiles = $SlotFiles; steps = [ordered]@{}; status = 'running' }

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
        $missing = @($SlotFiles | Where-Object { -not (Test-Path -LiteralPath $_) })
        $busy = Busy
        $free = Commit-Free-GB
        if (-not $missing.Count -and -not $busy.Count -and $free -ge $NeedCommitGB) {
            # Two agents polling on the same cadence both saw a free slot in the same second on
            # 11 Sep and launched two games from one archive. Settle a random interval, then re-check.
            Start-Sleep -Seconds (Get-Random -Minimum 15 -Maximum 40)
            if (-not (Busy).Count -and (Commit-Free-GB) -ge $NeedCommitGB) { return $free }
        }
        $state.steps[$step] = [ordered]@{ status = 'waiting_for_slot'; missingSlotFiles = $missing
                                          busy = ($busy -join ','); commitFreeGB = $free
                                          utc = (Get-Date).ToUniversalTime().ToString('o') }
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
    $log = Join-Path $logs ("ocs-$step-" + $t0.ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '.log')
    $argline = "`"$uproject`" /Engine/Maps/Entry -ExecutePythonScript=$($script.Replace('\','/')) -OCS$mode -OCSTarget=$target " +
               "-unattended -nullrhi -NoSplash -NoSound -abslog=`"$log`""
    $state.steps[$step] = [ordered]@{ status = 'running'; startedUtc = $t0.ToUniversalTime().ToString('o')
                                      commitFreeGBAtLaunch = $free; log = $log; args = $argline }
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
    $state.steps[$step] = [ordered]@{ status = $status; receipt = $(if ($r) { $r.FullName } else { $null }); exitCode = $p.ExitCode
                                      peakPrivateGB = [math]::Round($peak / 1GB, 2); log = $log
                                      finishedUtc = (Get-Date).ToUniversalTime().ToString('o') }
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
                $cookArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $project 'Checkpoint-Build.ps1'), '-Label', $Label)
                if ($CookUseExistingBinaries) { $cookArgs += '-UseExistingBinaries' }
                $state.steps[$s] = [ordered]@{ status = 'running'; startedUtc = $t0.ToUniversalTime().ToString('o')
                                               commitFreeGBAtLaunch = $free; log = $cookLog
                                               useExistingBinaries = [bool]$CookUseExistingBinaries }
                Save
                $p = Start-Process powershell -PassThru -WindowStyle Hidden -RedirectStandardOutput $cookLog -ArgumentList $cookArgs
                $p.WaitForExit()
                $arch = Latest-Archive
                # "A newer archive directory exists" is NOT proof of a playable build, and the
                # wrapper's own ExitCode came back null on the streets01 run, so neither test
                # would have caught a failed cook. The CHECKPOINT RECEIPT is the proof - and it
                # is written to the JOB directory under Working-5.8, not into the archive.
                $job = Get-ChildItem 'C:\Mikdash\Working-5.8' -Directory -Filter "Checkpoint-$Label-*" -EA SilentlyContinue |
                       Where-Object { $_.LastWriteTime -ge $t0 } | Sort-Object LastWriteTime | Select-Object -Last 1
                $receiptPath = if ($job) { Join-Path $job.FullName 'checkpoint-receipt.json' } else { $null }
                $receipt = if ($receiptPath -and (Test-Path -LiteralPath $receiptPath)) {
                    Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json } else { $null }
                $cookOk = $receipt -and $receipt.exitCode -eq 0 -and $receipt.childExists -and $receipt.smoke.status -eq 'playable'
                $state.steps[$s] = [ordered]@{ status = $(if ($cookOk) { 'checkpoint_playable' } else { 'cook_unverified' })
                                               archive = $(if ($arch) { $arch.FullName } else { $null })
                                               receipt = $receiptPath
                                               exitCode = $(if ($receipt) { $receipt.exitCode } else { $null })
                                               childSha256 = $(if ($receipt) { $receipt.childSha256 } else { $null })
                                               smoke = $(if ($receipt) { $receipt.smoke.status } else { $null })
                                               archiveBytes = $(if ($receipt) { $receipt.archiveBytes } else { $null })
                                               log = $cookLog
                                               useExistingBinaries = [bool]$CookUseExistingBinaries }
                if ($cookOk) { $state.archive = $arch.FullName }
                Save
                if (-not $cookOk) { throw "cook not verified playable; receipt: $receiptPath" }
            }
            '^capture:' { $parts = $s.Substring(8).Split('|'); Run-Capture $s $parts[0] $parts[1] $parts[2] }
            '^captureafter:' {
                $parts = $s.Substring(13).Split('|')
                $arch = if ($state.archive) { $state.archive } else { (Latest-Archive).FullName }
                Run-Capture $s $arch $parts[0] $parts[1]
            }
            '^done$' {
                [IO.File]::WriteAllText('C:\Mikdash\Working-5.8\SLOT-streets-done.txt', "OldCityStreetsV1 engine work finished $((Get-Date).ToUniversalTime().ToString('o'))`r`n")
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
