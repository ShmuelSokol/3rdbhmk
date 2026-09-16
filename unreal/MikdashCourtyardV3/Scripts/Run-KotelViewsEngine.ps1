<#
    Serial engine sequence for the KotelViewsV1 repairs. One engine at a time, detached,
    receipts after every step. It refuses to start until the Old City agent's slot file exists
    and the native slot is actually free, and it stops at the first failed step.

    Steps (Candidate48 FIRST - it is the cook map - then Main50):
      1 remove the illustrative MountAccessV2 stair actors      (release_remove_mount_access.py)
      2 fresh-process verify of step 1
      3 build the cut street duplicates and swap them in        (release_kotel_plaza_way_cut.py)
      4 fresh-process verify of step 3

    Each step is a hidden editor started on /Engine/Maps/Entry with -ExecutePythonScript, as
    AGENTS.md requires for actor mutation in this project (not -run=pythonscript), -nullrhi and
    a unique absolute log. Nothing here cooks, builds C++ or captures frames; those are separate.

    .\Run-KotelViewsEngine.ps1 -WaitMinutes 240
    .\Run-KotelViewsEngine.ps1 -PlanOnly
#>
param(
    [int]$WaitMinutes = 240,
    [switch]$PlanOnly,
    [switch]$SkipSlotFile,
    [double]$NeedCommitGiB = 12.0,
    # Resume: 1-based index of the first step to run. A step already applied is not repeated,
    # and a verify step then finds its apply receipt on disk instead of in this run's log.
    [int]$StartAtStep = 1
)
$ErrorActionPreference = 'Stop'
$project = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
$editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$slotFile = 'C:\Mikdash\Working-5.8\SLOT-oldcity-done.txt'
$review = Join-Path $project 'SourceAssets\context-review\KotelViewsV1'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$progress = Join-Path $review "engine-run-$stamp.json"
New-Item -ItemType Directory -Force -Path $review | Out-Null

$steps = @(
    @{ name = 'mount-access-remove-candidate48'; script = 'release_remove_mount_access.py';
       args = @('-Candidate48', '-MountAccessRemoveApply'); receipt = 'mount-access-remove-apply-Candidate48-*.json';
       expect = 'applied_saved_reopened' }
    @{ name = 'mount-access-verify-candidate48'; script = 'release_remove_mount_access.py';
       args = @('-Candidate48'); verifyOf = 'mount-access-remove-candidate48'; verifyFlag = '-MountAccessRemoveVerify=';
       receipt = 'mount-access-remove-verify-Candidate48-*.json'; expect = 'verified_fresh_process' }
    @{ name = 'mount-access-remove-main50'; script = 'release_remove_mount_access.py';
       args = @('-Main50', '-MountAccessRemoveApply'); receipt = 'mount-access-remove-apply-Main50-*.json';
       expect = 'applied_saved_reopened' }
    @{ name = 'mount-access-verify-main50'; script = 'release_remove_mount_access.py';
       args = @('-Main50'); verifyOf = 'mount-access-remove-main50'; verifyFlag = '-MountAccessRemoveVerify=';
       receipt = 'mount-access-remove-verify-Main50-*.json'; expect = 'verified_fresh_process' }
    @{ name = 'plaza-way-cut-candidate48'; script = 'release_kotel_plaza_way_cut.py';
       args = @('-Candidate48', '-PlazaWayCutApply'); receipt = 'plaza-way-cut-apply-Candidate48-*.json';
       expect = 'applied_saved_reopened' }
    @{ name = 'plaza-way-cut-verify-candidate48'; script = 'release_kotel_plaza_way_cut.py';
       args = @('-Candidate48'); verifyOf = 'plaza-way-cut-candidate48'; verifyFlag = '-PlazaWayCutVerify=';
       receipt = 'plaza-way-cut-verify-Candidate48-*.json'; expect = 'verified_fresh_process' }
    @{ name = 'plaza-way-cut-main50'; script = 'release_kotel_plaza_way_cut.py';
       args = @('-Main50', '-PlazaWayCutApply'); receipt = 'plaza-way-cut-apply-Main50-*.json';
       expect = 'applied_saved_reopened' }
    @{ name = 'plaza-way-cut-verify-main50'; script = 'release_kotel_plaza_way_cut.py';
       args = @('-Main50'); verifyOf = 'plaza-way-cut-main50'; verifyFlag = '-PlazaWayCutVerify=';
       receipt = 'plaza-way-cut-verify-Main50-*.json'; expect = 'verified_fresh_process' }
)

function Commit-Free-GiB {
    $m = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    [math]::Round(($m.CommitLimit - $m.CommittedBytes) / 1GB, 2)
}
function Busy {
    $busy = @(Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3 -ErrorAction SilentlyContinue |
              Select-Object -ExpandProperty ProcessName)
    $busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -ErrorAction SilentlyContinue |
               Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' } | ForEach-Object { 'dotnet-UAT/UBT' })
    return $busy
}

$report = [ordered]@{
    status = 'starting'; startedUtc = (Get-Date).ToUniversalTime().ToString('o'); stamp = $stamp
    slotFile = $slotFile; steps = @(); errors = @()
    scope = 'Map-side repairs only: removes the MountAccessV2 placement and swaps the cut street duplicates. No cook, no C++ build, no frame capture.'
}
function Save { ($report | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $progress -Encoding utf8 }
Save

if ($PlanOnly) {
    $report.status = 'plan_only'
    $report.plannedSteps = @($steps | ForEach-Object { $_.name })
    Save
    Write-Output ($report | ConvertTo-Json -Depth 6)
    return
}

$deadline = (Get-Date).AddMinutes($WaitMinutes)
while ($true) {
    $haveSlot = $SkipSlotFile -or (Test-Path -LiteralPath $slotFile)
    $busy = @(Busy)
    $free = Commit-Free-GiB
    if ($haveSlot -and -not $busy.Count -and $free -ge $NeedCommitGiB) { break }
    if ((Get-Date) -gt $deadline) {
        $report.status = 'deferred'
        $report.errors += "waited $WaitMinutes min: slotFile=$haveSlot busy=$($busy -join ',') commitFreeGiB=$free"
        Save
        Write-Output "DEFERRED: slotFile=$haveSlot busy=$($busy -join ',') commitFreeGiB=$free"
        exit 2
    }
    Start-Sleep -Seconds 20
}
$report.initialCommitFreeGiB = Commit-Free-GiB
$report.status = 'running'
Save

for ($stepIndex = 0; $stepIndex -lt $steps.Count; $stepIndex++) {
    $step = $steps[$stepIndex]
    if (($stepIndex + 1) -lt $StartAtStep) { continue }
    $entry = [ordered]@{ name = $step.name; stepNumber = $stepIndex + 1; startedUtc = (Get-Date).ToUniversalTime().ToString('o') }
    try {
        # Other agents share this machine: wait for the slot rather than abandoning the sequence.
        $slotDeadline = (Get-Date).AddMinutes(90)
        while (@(Busy).Count) {
            if ((Get-Date) -gt $slotDeadline) { throw 'Native slot held by another process for 90 minutes' }
            Start-Sleep -Seconds 20
        }
        $stepArgs = @($step.args)
        if ($step.verifyOf) {
            $prior = $report.steps | Where-Object { $_.name -eq $step.verifyOf } | Select-Object -Last 1
            $receiptPath = if ($prior -and $prior.receiptPath) { $prior.receiptPath } else {
                $pattern = ($steps | Where-Object { $_.name -eq $step.verifyOf }).receipt
                $candidates = @(Get-ChildItem -LiteralPath $review -Filter $pattern -ErrorAction SilentlyContinue |
                                Sort-Object LastWriteTime)
                $good = @($candidates | Where-Object {
                    ((Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json).status) -eq 'applied_saved_reopened' })
                if ($good.Count) { $good[-1].FullName } else { $null }
            }
            if (-not $receiptPath) { throw "No applied receipt found for $($step.verifyOf)" }
            $entry.verifiesReceipt = $receiptPath
            $stepArgs += ($step.verifyFlag + '"' + $receiptPath + '"')
        }
        $log = Join-Path $review ("engine-$($step.name)-$stamp.log")
        $before = @(Get-ChildItem -LiteralPath $review -Filter $step.receipt -ErrorAction SilentlyContinue |
                    Select-Object -ExpandProperty FullName)
        $launch = @("`"$project\MikdashCourtyardV3.uproject`"", '/Engine/Maps/Entry',
                    "-ExecutePythonScript=`"$project/Scripts/$($step.script)`"",
                    '-unattended', '-nosplash', '-nullrhi', '-EnablePlugins=GeometryScripting',
                    "-abslog=`"$log`"") + $stepArgs
        $entry.arguments = $launch -join ' '
        $proc = Start-Process -FilePath $editor -ArgumentList $launch -PassThru -WindowStyle Hidden
        $entry.pid = $proc.Id
        $report.steps += $entry; Save
        $stepDeadline = (Get-Date).AddMinutes(45)
        while (-not $proc.HasExited -and (Get-Date) -lt $stepDeadline) { Start-Sleep -Seconds 10; $proc.Refresh() }
        if (-not $proc.HasExited) { $proc | Stop-Process -Force; throw 'Step timed out after 45 minutes' }
        $entry.exitCode = $proc.ExitCode
        $fresh = @(Get-ChildItem -LiteralPath $review -Filter $step.receipt -ErrorAction SilentlyContinue |
                   Where-Object { $before -notcontains $_.FullName } | Sort-Object LastWriteTime)
        if ($fresh.Count -lt 1) { throw 'No fresh receipt was written' }
        $receipt = Get-Content -LiteralPath $fresh[-1].FullName -Raw | ConvertFrom-Json
        $entry.receiptPath = $fresh[-1].FullName
        $entry.receiptStatus = $receipt.status
        if ($receipt.status -ne $step.expect) { throw "Receipt status '$($receipt.status)', expected '$($step.expect)'" }
        $entry.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
        Save
    } catch {
        $entry.error = $_.Exception.Message
        $report.errors += "$($step.name): $($_.Exception.Message)"
        $report.status = 'failed'
        Save
        Write-Output "FAILED at $($step.name): $($_.Exception.Message)"
        exit 1
    }
}
$report.status = 'all_steps_passed_visual_acceptance_pending'
$report.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
Save
Write-Output ("OK: {0} steps, progress {1}" -f $steps.Count, $progress)
