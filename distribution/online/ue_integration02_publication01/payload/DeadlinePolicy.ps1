# Pure timing policy only. Dot-sourcing starts no clock, process or native API.
function Get-CompileDeadlineDecision {
    param([double]$ElapsedSeconds,[int]$BudgetSeconds,[switch]$BeforeLaunch)
    if ([double]::IsNaN($ElapsedSeconds) -or [double]::IsInfinity($ElapsedSeconds) -or
        $ElapsedSeconds -lt 0 -or $BudgetSeconds -lt 30 -or $BudgetSeconds -gt 900) {
        throw 'Invalid compile clock/budget.'
    }
    # The unchanged helper may spend5s cleaning. Reserve1s more for polling and
    # transition overhead; admission leaves10s. No fresh budget after execution.
    $reserve=if ($BeforeLaunch) {10.0} else {6.0}
    $remaining=$BudgetSeconds-$reserve-$ElapsedSeconds
    [pscustomobject]@{
        Stop=($remaining -le 0)
        SleepMilliseconds=[int][Math]::Floor([Math]::Min(250.0,[Math]::Max(0.0,$remaining*1000.0)))
    }
}
