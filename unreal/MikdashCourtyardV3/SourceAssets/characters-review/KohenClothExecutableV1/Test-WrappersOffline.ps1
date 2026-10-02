# Offline only: AST parsing and pure policy/receipt functions; no Add-Type or child.
$ErrorActionPreference='Stop'
$count=0
function Assert-Offline($Condition,[string]$Message) {
    if(-not $Condition){throw $Message}
    $script:count++
}
$helper=Join-Path $PSScriptRoot 'Owned-ReviewWatchdog.ps1'
foreach($file in (Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1')) {
    $tokens=$null; $errors=$null
    $null=[System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    Assert-Offline ($errors.Count -eq 0) ($file.Name + ': ' + ($errors -join ';'))
}
. $helper
Assert-Offline ((Get-ReviewGuardReason 0 9GB 0 600) -eq '') 'Normal sample rejected'
Assert-Offline ((Get-ReviewGuardReason (4GB-1) 2GB 599.99 600) -eq '') 'Boundary-safe sample rejected'
Assert-Offline ((Get-ReviewGuardReason 4GB 9GB 0 600) -eq 'private_cap') 'Private cap not enforced'
Assert-Offline ((Get-ReviewGuardReason 0 (2GB-1) 0 600) -eq 'commit_reserve') 'Commit reserve not enforced'
Assert-Offline ((Get-ReviewGuardReason 0 9GB 600 600) -eq 'deadline') 'Native deadline not enforced'
Assert-Offline ((Get-ReviewGuardReason 0 9GB 900 900) -eq 'deadline') 'Build deadline not enforced'
Assert-Offline ((Get-ReviewGuardReason -1 9GB 0 600) -eq 'measurement_failed') 'Invalid measurement accepted'
$text=Get-Content -LiteralPath $helper -Raw
Assert-Offline ($text.Contains('startFreeCommitBytes -lt 9GB') -and $text.Contains('$free -lt 9GB')) 'Start9GiB checks changed'
Assert-Offline ($text.IndexOf('$owned.StopWithinFiveSeconds()') -lt $text.IndexOf('$after = [ordered]@{}')) 'Hashing precedes cleanup'
Assert-Offline ($text -notmatch 'Stop-Process|taskkill') 'Broad process cleanup present'
$cs=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'OwnedChildJob.cs') -Raw
Assert-Offline ($cs.IndexOf('Require(AssignProcessToJobObject') -lt $cs.IndexOf('Require(ResumeThread')) 'Child executes before ownership'
Assert-Offline ($cs.Contains('SUSPENDED|NO_WINDOW') -and $cs.Contains('KILL_ON_CLOSE|PROCESS_MEMORY|JOB_MEMORY')) 'Hidden launch/limits absent'
Assert-Offline ($cs.Contains('IsProcessInJob(proc,job,out member)')) 'PID reuse ownership check absent'
Assert-Offline ($cs.Contains('timer.ElapsedMilliseconds<5000') -and $cs.Contains('TerminateJobObject(job')) 'Bounded job cleanup absent'
$cleanup=$cs.Substring($cs.IndexOf('public bool StopWithinFiveSeconds()'),$cs.IndexOf('public void Dispose()')-$cs.IndexOf('public bool StopWithinFiveSeconds()'))
Assert-Offline ($cleanup.Contains('bool signaled=IsSignaled(root)') -and $cleanup.Contains('if(signaled && active==0 && timer.ElapsedMilliseconds<5000)')) 'Cleanup must require root signal AND empty job within original budget'
Assert-Offline ($cleanup.IndexOf('Require(IsProcessInJob(member,job,out ours))') -lt $cleanup.IndexOf('Require(TerminateJobObject(job') -and $cleanup.Contains('if(!IsSignaled(member)) signaled=false')) 'Captured descendants not confirmed through owned handles'
Assert-Offline ($cleanup.Contains('if(wait==0xffffffff) throw new Win32Exception(Marshal.GetLastWin32Error())') -and $cleanup.Contains('if(CleanupError!=null) return false')) 'Wait/capture errors must fail confirmation'
Assert-Offline ($cleanup.Contains('finally { foreach(IntPtr member in members) CloseHandle(member); }') -and ([regex]::Matches($cleanup,'Stopwatch.StartNew')).Count -eq 1) 'Retained handles must close and cleanup must share one deadline'
$poll=$cs.Substring($cs.IndexOf('public Sample Poll()'),$cs.IndexOf('public bool StopWithinFiveSeconds()')-$cs.IndexOf('public Sample Poll()'))
Assert-Offline ($poll.IndexOf('uint wait=WaitForSingleObject(root,0)') -lt $poll.IndexOf('GetExitCodeProcess(root,out code)')) 'Exit code read before wait'
Assert-Offline ($poll -match 'if\(wait==0xffffffff\) throw new Win32Exception\(Marshal.GetLastWin32Error\(\)\)') 'WAIT_FAILED not surfaced'
Assert-Offline ($poll -match '(?s)if\(wait==0\) \{[^}]*GetExitCodeProcess\(root,out code\)[^}]*s.RootExited=true;' -and $poll.Contains('else if(wait!=258)')) 'Exit code not restricted to signaled handle'
Assert-Offline ($text.Contains('../../context-review/HaramThresholdSidesV1/native-slot-blocked.json') -and ([regex]::Matches($text,'Assert-ReviewSlotClear \$blockedSlot')).Count -eq 2) 'Shared marker preflight/recheck missing'
Assert-Offline ($text.IndexOf('New-ReviewOwnershipSentinel $blockedSlot') -lt $text.IndexOf('$owned = [KohenReviewGuard.OwnedChildJob]::new')) 'Sentinel must persist before process creation'
Assert-Offline ($text.Contains('$stream.Flush($true)') -and $text.Contains('Complete-ReviewOwnership $blockedSlot $ownershipToken ($record.cleanupConfirmed -eq $true)')) 'Durable flush/positive cleanup gate missing'
$build=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Build-Reviewed.ps1') -Raw
Assert-Offline ($build.Contains('-MaxParallelActions=1') -and $build.Contains('-DeadlineSeconds 900')) 'Build bounds absent'
$run=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Run-Reviewed.ps1') -Raw
Assert-Offline ($run.Contains('-DeadlineSeconds 600')) 'Native bound absent'
$dir=Join-Path $PSScriptRoot ('WrapperOfflineTests/' + [guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $dir
$marker=Join-Path $dir 'native-slot-blocked.json'
Assert-ReviewSlotClear $marker
$token=[guid]::NewGuid().ToString('N')
New-ReviewOwnershipSentinel $marker $token $dir
$blocked=$false
try { Assert-ReviewSlotClear $marker } catch { $blocked=$true }
Assert-Offline $blocked 'Unconfirmed cleanup did not refuse next launch'
$markerHash=(Get-FileHash -LiteralPath $marker).Hash
$foreignRefused=$false
try { New-ReviewOwnershipSentinel $marker 'foreign-token' $dir } catch { $foreignRefused=$true }
Assert-Offline $foreignRefused 'Foreign acquisition must refuse'
Assert-Offline ((Get-FileHash -LiteralPath $marker).Hash -eq $markerHash) 'Existing shared block overwritten'
Assert-Offline ((Get-Content -LiteralPath $marker -Raw|ConvertFrom-Json).ownershipToken -ceq $token) 'Ownership token missing'
Assert-Offline (-not (Complete-ReviewOwnership $marker $token $false)) 'Unconfirmed cleanup removed sentinel'
Assert-Offline ((Get-FileHash -LiteralPath $marker).Hash -eq $markerHash) 'Unconfirmed cleanup changed sentinel'
$foreignRefused=$false
try { Complete-ReviewOwnership $marker 'foreign-token' $true } catch { $foreignRefused=$true }
Assert-Offline ($foreignRefused -and (Get-FileHash -LiteralPath $marker).Hash -eq $markerHash) 'Foreign cleanup changed sentinel'
# Real filesystem persistence failure; the launch stand-in must never be reached.
$badParent=Join-Path $dir 'not-a-directory'
[IO.File]::WriteAllText($badParent,'fault fixture')
$launchReached=$false; $persistFailed=$false
try { New-ReviewOwnershipSentinel (Join-Path $badParent 'blocked.json') $token $dir; $launchReached=$true } catch { $persistFailed=$true }
Assert-Offline ($persistFailed -and -not $launchReached) 'Persistence failure permitted launch'
# Later receipt write fails too: pre-existing sentinel still denies subsequent launch.
$lateWriteFailed=$false
try { Write-ReviewAtomicJson (Join-Path $badParent 'receipt.json') @{status='cleanup_failed'} } catch { $lateWriteFailed=$true }
$blocked=$false
try { Assert-ReviewSlotClear $marker } catch { $blocked=$true }
Assert-Offline ($lateWriteFailed -and $blocked -and (Get-FileHash -LiteralPath $marker).Hash -eq $markerHash) 'Late receipt failure reopened slot'
# Constructor absent/unknown cleanup evidence is never affirmative cleanup.
Assert-Offline (-not (Complete-ReviewOwnership $marker $token ($null -eq $true))) 'Unknown constructor cleanup removed sentinel'
Assert-Offline (Complete-ReviewOwnership $marker $token $true) 'Confirmed owned cleanup did not release'
Assert-Offline (-not (Test-Path -LiteralPath $marker)) 'Owned sentinel remains after confirmed cleanup'
$malformed=Join-Path $dir 'malformed-sentinel.txt'
[IO.File]::WriteAllText($malformed,'unparseable foreign sentinel')
$foreignRefused=$false
try { New-ReviewOwnershipSentinel $malformed $token $dir } catch { $foreignRefused=$true }
Assert-Offline ($foreignRefused -and [IO.File]::ReadAllText($malformed) -eq 'unparseable foreign sentinel') 'Malformed foreign sentinel not preserved'
$receipt=Join-Path $dir 'atomic-fixture.json'
Write-ReviewAtomicJson $receipt @{fixture=$true; value=17}
Assert-Offline ((Get-Content -LiteralPath $receipt -Raw|ConvertFrom-Json).value -eq 17) 'Atomic payload invalid'
$refused=$false
try { Write-ReviewAtomicJson $receipt @{value=18} } catch { $refused=$true }
Assert-Offline $refused 'Existing receipt overwritten'
Assert-Offline ((Get-Content -LiteralPath $receipt -Raw|ConvertFrom-Json).value -eq 17) 'Preserved receipt changed'
Assert-Offline (@(Get-ChildItem -LiteralPath $dir -Filter '*.tmp').Count -eq 0) 'Published fixture left temp file'
$frozen=[ordered]@{}
Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'ReviewProject') -Recurse -File |
    Where-Object { $_.FullName -notmatch '[\\/](Binaries|Intermediate|Saved)[\\/]' } |
    ForEach-Object { $frozen[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
$wrapperHashes=[ordered]@{}
foreach($name in @('Run-Reviewed.ps1','Build-Reviewed.ps1','Owned-ReviewWatchdog.ps1','OwnedChildJob.cs','Test-WrappersOffline.ps1','REVIEW.txt','WRAPPER-REVISION.txt')) {
    $wrapperHashes[$name]=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $name) -Algorithm SHA256).Hash
}
Write-ReviewAtomicJson (Join-Path $dir 'result.json') @{passed=$true; assertions=$count; processLaunches=0; wrapperRuns=0; nativeRuns=0; managedHelperCompiled=$false; frozenProjectHashes=$frozen; wrapperHashes=$wrapperHashes; limit='Static/native-source checks and pure PowerShell policy functions, not OS Job Object execution proof'}
Write-Output "$count offline wrapper assertions passed; no wrapper/native/helper execution. $dir"
