# No Add-Type, helper execution, UE, UBT, or child processes. Files only in fresh test directory.
$ErrorActionPreference='Stop'
. "$PSScriptRoot/support.ps1"
$dir=Join-Path $PSScriptRoot ('fault-tests/'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $dir
$cases=[Collections.Generic.List[string]]::new()
function Check([bool]$Ok,[string]$Name){if(-not $Ok){throw "Offline test failed: $Name"};$cases.Add($Name)}
foreach($name in @('run_native.ps1','support.ps1','owned_ue_shim.ps1','test_offline.ps1')){
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)
    Check ($errors.Count -eq 0) "parse $name"
}
$marker=Join-Path $dir 'good.json'
Atomic-Receipt $marker @{owner='AngularVATNative01';ownershipToken='mine'}
$r=Complete-AngularOwnership $marker 'mine' $false
Check ($r.slotBlocked -and (Test-Path $marker)) 'failed cleanup retains marker'
$r=Complete-AngularOwnership $marker 'mine' $true
Check (-not $r.slotBlocked -and -not(Test-Path $marker)) 'confirmed owned cleanup clears marker'
$r=Complete-AngularOwnership $marker 'mine' $true
Check ($r.slotBlocked -and (Test-Path $marker)) 'missing marker restores fail-closed sentinel'
$corrupt=Join-Path $dir 'corrupt.json';[IO.File]::WriteAllText($corrupt,'not json')
$r=Complete-AngularOwnership $corrupt 'mine' $true
Check ($r.slotBlocked -and [IO.File]::ReadAllText($corrupt) -eq 'not json') 'corrupt marker contained and retained'
$foreign=Join-Path $dir 'foreign.json';Atomic-Receipt $foreign @{owner='other';ownershipToken='other'}
$r=Complete-AngularOwnership $foreign 'mine' $true
Check ($r.slotBlocked -and (Test-Path $foreign)) 'foreign marker retained'
$absent=Join-Path $dir 'absent.json';$r=Complete-AngularOwnership $absent 'mine' $false
Check ($r.slotBlocked -and (Test-Path $absent)) 'failed cleanup plus missing marker restored'
$failed=$false;try{Atomic-Receipt $foreign @{overwrite=$true}}catch{$failed=$true}
Check $failed 'atomic receipt refuses overwrite'
$failed=$false;try{Assert-AngularDeadline 295 300}catch{$failed=$true}
Check $failed 'elapsed prelaunch deadline refuses launch'
Assert-AngularDeadline 294 300;Check $true 'prelaunch cleanup reserve retained'
$before=@{};$before[$foreign]=(Get-FileHash $foreign).Hash.ToLowerInvariant()
Check (Get-AngularPreservation $before).preserved 'protected hashes match'
$before[(Join-Path $dir 'missing.asset')]='abc'
Check (-not (Get-AngularPreservation $before).preserved) 'missing protected asset fails preservation without throwing'
$bad=@{};$bad[$dir]='abc'
Check (-not (Get-AngularPreservation $bad).preserved) 'hash IO failure contained for terminal receipt'
$source=Get-Content "$PSScriptRoot/support.ps1" -Raw
Check ($source.Contains('Flush($true)')) 'durable flush source contract'
$wrapper=Get-Content "$PSScriptRoot/run_native.ps1" -Raw
Check ($wrapper -match 'Assert-AngularDeadline \$clock.Elapsed.TotalSeconds \$DeadlineSeconds\s+\$owned=') 'deadline immediately before OwnedChildJob construction'
Check ($wrapper.Contains('}finally{$lock.Dispose()}')) 'terminal receipt fault retains outer lock disposal'
Check (-not ($wrapper -match 'WaitForExit\(\)')) 'no unbounded WaitForExit'
$record=@{passed=$true;cases=$cases;nativeLaunches=0;helperOSProof='Reused exact cloth OS-tested helper; not rerun';scope='Filesystem fault injection plus syntax/source contracts, not crash/power-loss or OS fault injection'}
Atomic-Receipt (Join-Path $dir 'result.json') $record
$record|ConvertTo-Json -Depth 5
