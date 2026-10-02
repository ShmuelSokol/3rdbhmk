# Explicit OS integration test: hidden harmless PowerShell children only, never UE/UBT.
# Use a fresh 64-bit PowerShell 7 host. Outputs/logs stay in a unique TEMP fixture.
param(
    [Parameter(Mandatory)][string]$ExpectedHelperHash,
    [string]$HelperPath=(Join-Path $PSScriptRoot 'OwnedChildJob.cs')
)
$ErrorActionPreference='Stop'
if (-not $IsWindows -or -not [Environment]::Is64BitProcess) { throw '64-bit Windows PowerShell 7 required' }
$exe=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
if ([IO.Path]::GetFileName($exe) -ine 'pwsh.exe') { throw 'Test children must use pwsh.exe' }
if ((Get-FileHash -LiteralPath $HelperPath).Hash -ne $ExpectedHelperHash) { throw 'Helper hash differs from reviewed revision' }
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('KohenOwnedJobReview-'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $fixture
$copy=Join-Path $fixture 'OwnedChildJob.cs'
Copy-Item -LiteralPath $HelperPath -Destination $copy
if ((Get-FileHash -LiteralPath $copy).Hash -ne $ExpectedHelperHash) { throw 'Copied helper hash differs' }
$jobs=[Collections.Generic.List[object]]::new()
$held=[Collections.Generic.List[object]]::new()
$result=[ordered]@{
    schema='owned-job-os-integration-v1'; passed=$false; helperHash=$ExpectedHelperHash
    testScriptHash=(Get-FileHash -LiteralPath $PSCommandPath).Hash
    startedUtc=[DateTime]::UtcNow.ToString('o'); fixture=$fixture; cases=@(); cleanup=@()
    scope='Actual Windows Job test using hidden sleeping PowerShell children; no UE/UBT or native wrapper execution'
    limit='No memory-pressure, host-crash, arbitrary descendant-churn or OS API-fault injection proof'
}
function Encode-TestCommand([string]$Code) { [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Code)) }
function Assert-TestReserve {
    # Harmless fixture reserve only. Does not invoke or alter the native 9/4/2 guards.
    if ([KohenReviewGuard.OwnedChildJob]::AvailableCommit() -lt 2GB) { throw 'Fixture free commit below2GiB' }
}
function New-TestJob([string]$Name,[string[]]$Arguments) {
    Assert-TestReserve
    $job=[KohenReviewGuard.OwnedChildJob]::new($exe,$Arguments,$fixture,(Join-Path $fixture ($Name+'.log')),[ulong]4GB)
    $jobs.Add([pscustomobject]@{name=$Name;job=$job})
    return $job
}
function Hold-TestMembers($Job) {
    # Read-only use of the exact hash-pinned helper's Job API. Retain process handles,
    # validate kernel membership, and never use PID-based termination.
    $type=[KohenReviewGuard.OwnedChildJob]
    $handle=$type.GetField('job',[Reflection.BindingFlags]'NonPublic,Instance').GetValue($Job)
    $query=$type.GetMethod('QueryInformationJobObject',[Reflection.BindingFlags]'NonPublic,Static')
    $membership=$type.GetMethod('IsProcessInJob',[Reflection.BindingFlags]'NonPublic,Static')
    $buffer=[Runtime.InteropServices.Marshal]::AllocHGlobal(65536)
    try {
        if (-not $query.Invoke($null,@($handle,[int]3,$buffer,[uint32]65536,[IntPtr]::Zero))) { throw 'Job member query failed' }
        $count=[Runtime.InteropServices.Marshal]::ReadInt32($buffer,4)
        if ($count -lt 0 -or $count -gt 8191) { throw 'Invalid Job member count' }
        for ($i=0;$i -lt $count;$i++) {
            $memberId=[int][Runtime.InteropServices.Marshal]::ReadInt64($buffer,8+8*$i)
            $process=[Diagnostics.Process]::GetProcessById($memberId)
            try {
                $arguments=[object[]]@($process.Handle,$handle,$false)
                if (-not $membership.Invoke($null,$arguments) -or -not $arguments[2]) { throw 'Member ownership changed' }
                $entry=[pscustomobject]@{pid=$memberId;name=$process.ProcessName;creationUtc=$process.StartTime.ToUniversalTime().ToString('o');process=$process}
                $held.Add($entry)
                $entry
            } catch { $process.Dispose(); throw }
        }
    } finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($buffer) }
}
try {
    Add-Type -Path $copy
    $result.managedHelperCompiled=$true
    $control=New-TestJob 'control' @('-NoProfile','-NonInteractive','-EncodedCommand',(Encode-TestCommand 'Start-Sleep -Seconds 60'))
    $normal=New-TestJob 'exit-zero' @('-NoProfile','-NonInteractive','-EncodedCommand',(Encode-TestCommand 'exit 0'))
    $clock=[Diagnostics.Stopwatch]::StartNew()
    do {
        Assert-TestReserve; $sample=$normal.Poll()
        if ($sample.RootExited -and $sample.ActiveProcesses -eq 0) { break }
        Start-Sleep -Milliseconds 50
    } while ($clock.Elapsed.TotalSeconds -lt 15)
    $normalPassed=$sample.RootExited -and $sample.ExitCode -eq 0 -and $sample.ActiveProcesses -eq 0
    $result.cases+=@{name='normal_exit';passed=$normalPassed;rootPid=$normal.ProcessId;rootExited=$sample.RootExited;exitCode=$sample.ExitCode;active=$sample.ActiveProcesses}
    if (-not $normalPassed) { throw 'Normal completion failed' }
    $rootScript=Join-Path $fixture 'tree-root.ps1'
    $rootText=@'
param([string]$Exe,[string]$Fixture)
$ErrorActionPreference='Stop'
$ready=Join-Path $Fixture 'descendant-ready.txt'
$code='[IO.File]::WriteAllText(' + "'" + $ready.Replace("'","''") + "'" + ', "ready"); Start-Sleep -Seconds 60'
$start=[Diagnostics.ProcessStartInfo]::new($Exe)
$start.UseShellExecute=$false; $start.CreateNoWindow=$true; $start.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
foreach($arg in @('-NoProfile','-NonInteractive','-EncodedCommand',[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($code)))) { $start.ArgumentList.Add($arg) }
$child=[Diagnostics.Process]::Start($start)
$null=$child.Handle
[IO.File]::WriteAllText((Join-Path $Fixture 'tree-ready.json'),(@{rootPid=$PID;childPid=$child.Id}|ConvertTo-Json))
Start-Sleep -Seconds 60
'@
    [IO.File]::WriteAllText($rootScript,$rootText)
    $tree=New-TestJob 'owned-tree' @('-NoProfile','-NonInteractive','-File',$rootScript,'-Exe',$exe,'-Fixture',$fixture)
    $clock.Restart()
    do {
        Assert-TestReserve; $sample=$tree.Poll()
        $ready=(Test-Path -LiteralPath (Join-Path $fixture 'descendant-ready.txt')) -and (Test-Path -LiteralPath (Join-Path $fixture 'tree-ready.json'))
        if ($ready -and $sample.ActiveProcesses -ge 2) { break }
        if ($sample.RootExited) { throw 'Tree root exited before readiness' }
        Start-Sleep -Milliseconds 50
    } while ($clock.Elapsed.TotalSeconds -lt 15)
    if (-not $ready -or $sample.ActiveProcesses -lt 2) { throw 'Tree readiness not established' }
    $identity=Get-Content -LiteralPath (Join-Path $fixture 'tree-ready.json') -Raw|ConvertFrom-Json
    $members=@(Hold-TestMembers $tree)
    $controls=@(Hold-TestMembers $control)
    if ($identity.rootPid -ne $tree.ProcessId -or $identity.childPid -notin $members.pid -or $control.ProcessId -in $members.pid) { throw 'Kernel Job ownership differs from expected test identities' }
    $clock.Restart()
    do { Assert-TestReserve; if ($tree.Poll().RootExited) { throw 'Tree exited before fixture deadline' }; Start-Sleep -Milliseconds 50 } while ($clock.Elapsed.TotalSeconds -lt 1)
    $clock.Restart()
    $confirmed=$tree.StopWithinFiveSeconds()
    $elapsed=$clock.ElapsedMilliseconds
    $after=$tree.Poll(); $survivor=$control.Poll()
    $signals=@(foreach ($member in $members) { @{pid=$member.pid;name=$member.name;creationUtc=$member.creationUtc;signaled=$member.process.WaitForExit(0)} })
    $survives=-not $survivor.RootExited -and $survivor.ActiveProcesses -ge 1
    $treePassed=$confirmed -and $after.RootExited -and $after.ActiveProcesses -eq 0 -and $survives -and @($signals|Where-Object {-not $_.signaled}).Count -eq 0
    $result.cases+=@{name='deadline_tree_cleanup';passed=$treePassed;rootPid=$tree.ProcessId;descendantPid=$identity.childPid;cleanupConfirmed=$confirmed;cleanupMilliseconds=$elapsed;rootSignaled=$after.RootExited;activeAfter=$after.ActiveProcesses;memberSignals=$signals;controlPid=$control.ProcessId;controlSurvived=$survives;controlActive=$survivor.ActiveProcesses}
    if (-not $treePassed) { throw 'Root/member exit confirmation or control survival failed' }
    $result.passed=$true
} catch { $result.error=$_.Exception.ToString(); $result.passed=$false }
finally {
    foreach ($entry in $jobs) {
        $confirmed=$false; $errorText=$null; $clock=[Diagnostics.Stopwatch]::StartNew()
        try { $confirmed=$entry.job.StopWithinFiveSeconds(); $errorText=$entry.job.CleanupError }
        catch { $errorText=$_.Exception.Message }
        finally { $entry.job.Dispose() }
        $result.cleanup+=@{name=$entry.name;pid=$entry.job.ProcessId;confirmed=$confirmed;milliseconds=$clock.ElapsedMilliseconds;error=$errorText}
        if (-not $confirmed) { $result.passed=$false }
    }
    $result.finalHeldProcessSignals=@(foreach ($entry in $held) { @{pid=$entry.pid;name=$entry.name;creationUtc=$entry.creationUtc;signaled=$entry.process.WaitForExit(0)} })
    if (@($result.finalHeldProcessSignals|Where-Object {-not $_.signaled}).Count) { $result.passed=$false }
    foreach ($entry in $held) { $entry.process.Dispose() }
    $result.finishedUtc=[DateTime]::UtcNow.ToString('o')
    $result|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $fixture 'result.json') -Encoding utf8NoBOM
}
$result|ConvertTo-Json -Depth 12
if (-not $result.passed) { exit 1 }
