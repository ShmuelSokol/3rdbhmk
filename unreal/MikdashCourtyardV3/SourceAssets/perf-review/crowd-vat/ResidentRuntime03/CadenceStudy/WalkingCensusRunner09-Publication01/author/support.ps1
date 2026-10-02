# Definitions only. Pure policy calls do not compile or launch anything.
function Write-IdleAtomic([string]$Path,$Value) {
    if(Test-Path -LiteralPath $Path){throw 'Fresh receipt/sentinel required'}
    $temp=$Path+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 16))
    $stream=[IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    [IO.File]::Move($temp,$Path)
}
function Get-IdleGuard([long]$Free,[long]$Private,[double]$Elapsed,[int]$Deadline,[switch]$Acquire) {
    if($Free -lt 0 -or $Private -lt 0){return 'measurement_failed'}
    if($Acquire -and $Free -lt 9GB){return 'start_commit_below_9GiB'}
    if($Private -ge 4GB){return 'owned_job_4GiB_cap'}
    if($Free -lt 2GB){return 'commit_2GiB_reserve'}
    $margin=if($Acquire){10}else{6}
    if($Elapsed -ge ($Deadline-$margin)){return 'total_deadline_cleanup_reserved'}
    return ''
}
function Get-IdleSleepMilliseconds([double]$Elapsed,[int]$Deadline) {
    return [int][Math]::Max(0,[Math]::Min(500,[Math]::Floor(($Deadline-6-$Elapsed)*1000)))
}
function Complete-IdleOwnership([string]$Marker,[string]$Token,[bool]$Confirmed) {
    if($Confirmed){
        $saved=Get-Content -LiteralPath $Marker -Raw -ErrorAction Stop|ConvertFrom-Json -ErrorAction Stop
        if($saved.owner -cne 'WalkingCensusRunner09' -or $saved.ownershipToken -cne $Token){throw 'Foreign/corrupt marker retained'}
        [IO.File]::Delete($Marker)
        return $true
    }
    if(-not (Test-Path -LiteralPath $Marker)){
        Write-IdleAtomic $Marker @{owner='WalkingCensusRunner09';ownershipToken=$Token;status='cleanup_unconfirmed';manualCoordinatorClearanceRequired=$true}
    }
    return $false
}
function Assert-IdleHashes($Hashes) {
    foreach($key in $Hashes.Keys){
        if(-not (Test-Path -LiteralPath $key) -or (Get-FileHash -LiteralPath $key -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Hashes[$key]){throw "Pinned input changed: $key"}
    }
}

# The production polling loop is injectable for deterministic, process-free tests.
# Root handle signal and Job accounting are separate observations; do not require
# them to become terminal in the same Poll. Only natural Job0 can succeed here.
function Wait-IdleNaturalExit([scriptblock]$Poll,[scriptblock]$Free,[scriptblock]$Sleep,$Clock,[int]$Deadline,$Record) {
    $Record.pollCount=0
    $Record.drainSamples=[Collections.Generic.List[object]]::new()
    $Record.terminalPoll=$null
    $Record.naturalDrainConfirmed=$false
    while($true){
        $guard=Get-IdleGuard ([long](& $Free)) 0 $Clock.Elapsed.TotalSeconds $Deadline
        if($guard){throw $guard}
        $sample=& $Poll
        $freeCommit=[long](& $Free)
        $private=[long][Math]::Max($sample.PrivateBytes,$sample.PeakJobBytes)
        $Record.pollCount++
        $Record.peakOwnedJobBytes=[Math]::Max($Record.peakOwnedJobBytes,$private)
        $evidence=[ordered]@{pollIndex=$Record.pollCount;elapsedSeconds=$Clock.Elapsed.TotalSeconds;
            rootExited=[bool]$sample.RootExited;exitCode=$null;activeProcesses=[long]$sample.ActiveProcesses;
            privateBytes=[long]$sample.PrivateBytes;peakJobBytes=[long]$sample.PeakJobBytes;freeCommitBytes=$freeCommit}
        if($sample.RootExited){
            $evidence.exitCode=[long]$sample.ExitCode
            $Record.exitCode=[long]$sample.ExitCode
            $Record.drainSamples.Add($evidence)
        }
        # Store evidence before rejecting a guarded sample, including timeout/cap.
        $Record.terminalPoll=$evidence
        $guard=Get-IdleGuard $freeCommit $private $Clock.Elapsed.TotalSeconds $Deadline
        if($guard){throw $guard}
        if($sample.RootExited){
            if($sample.ExitCode -ne 0){throw 'Nonzero owned root exit'}
            if($sample.ActiveProcesses -eq 0){
                $Record.naturalDrainConfirmed=$true
                $Record.status='child_exited_zero'
                return
            }
        }
        $sleepMilliseconds=Get-IdleSleepMilliseconds $Clock.Elapsed.TotalSeconds $Deadline
        if($sleepMilliseconds -le 0){throw 'Total work deadline reached'}
        & $Sleep $sleepMilliseconds
    }
}
