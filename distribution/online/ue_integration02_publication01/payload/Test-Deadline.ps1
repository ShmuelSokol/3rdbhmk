$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'DeadlinePolicy.ps1')
$checks=0
function Check([bool]$Condition) {
    if (-not $Condition) { throw 'Offline deadline assertion failed.' }
    $script:checks++
}
foreach ($budget in @(30,300,900)) {
    Check (-not (Get-CompileDeadlineDecision ($budget-10-.001) $budget -BeforeLaunch).Stop)
    Check ((Get-CompileDeadlineDecision ($budget-10) $budget -BeforeLaunch).Stop)
    Check ((Get-CompileDeadlineDecision ($budget-6) $budget).Stop)
    Check ((Get-CompileDeadlineDecision ($budget+1) $budget).Stop)
    $justBefore=Get-CompileDeadlineDecision ($budget-6-.1) $budget
    Check (-not $justBefore.Stop -and $justBefore.SleepMilliseconds -le 100)
    # Actual production policy under a deterministic clock: arbitrary poll phase,
    # up to .5s spent in polling/guards, full5s helper cleanup + .25s final work.
    # These are explicitly modelled latencies, not a claim about stalled OS APIs.
    foreach ($phase in @(0.0,.001,.099,.249)) {
        $wall=3.0+$phase # include preparation in the single wall budget
        $steps=0
        while ($steps -lt 10000) {
            $steps++
            if ((Get-CompileDeadlineDecision $wall $budget).Stop) { break }
            $wall+=.5
            if ((Get-CompileDeadlineDecision $wall $budget).Stop) { break }
            $d=Get-CompileDeadlineDecision $wall $budget
            $wall+=$d.SleepMilliseconds/1000.0
        }
        Check ($steps -lt 10000)
        $wall+=5.0+.25
        Check ($wall -lt $budget)
    }
    # A callback that stalls beyond the reserve cannot become accepted success.
    Check ((Get-CompileDeadlineDecision ($budget-.1) $budget).Stop)
}
$wrapper=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Build-Reviewed.ps1') -Raw
Check ($wrapper.Contains('cleanupReserveSeconds=6'))
Check ($wrapper.Contains("'total_deadline_overrun'"))
Check ($wrapper.Contains('AvailableCommit() -lt 9GB'))
Check ($wrapper.Contains('AvailableCommit() -lt 2GB'))
Check ($wrapper.Contains('[uint64]4GB'))
Check ($wrapper.IndexOf('$timer=[Diagnostics.Stopwatch]::StartNew()') -lt $wrapper.IndexOf('Assert-PinnedSources'))
Check (-not $wrapper.Contains('Start-Sleep -Milliseconds 250'))
[ordered]@{status='passed';checks=$checks;mode='pure-clock-policy-and-source';launches=0;nativeCalls=0}|ConvertTo-Json -Compress
