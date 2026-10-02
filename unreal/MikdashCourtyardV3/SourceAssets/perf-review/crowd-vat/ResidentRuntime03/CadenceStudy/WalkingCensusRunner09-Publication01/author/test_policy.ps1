$ErrorActionPreference='Stop'
. "$PSScriptRoot/support.ps1"
$script:checks=0
function Check($Value,[string]$Message){$script:checks++;if(-not $Value){throw $Message}}
Check ((Get-IdleGuard (9GB-1) 0 0 180 -Acquire) -eq 'start_commit_below_9GiB') 'entry refusal'
Check ((Get-IdleGuard 9GB 0 0 180 -Acquire) -eq '') 'entry exact'
Check ((Get-IdleGuard 9GB 4GB 0 180) -eq 'owned_job_4GiB_cap') 'owned cap'
Check ((Get-IdleGuard (2GB-1) 0 0 180) -eq 'commit_2GiB_reserve') 'reserve'
Check ((Get-IdleGuard 9GB 0 174 180) -eq 'total_deadline_cleanup_reserved') 'deadline'
function Test-Polls($Samples,[long]$Free=9GB,[string]$Error=''){
 $script:seq=$Samples;$script:index=0;$script:fixtureFree=$Free;$clock=@{Elapsed=@{TotalSeconds=0.0}}
 $r=[ordered]@{peakOwnedJobBytes=0L;status='failed'};$caught=''
 try{Wait-IdleNaturalExit { $s=$script:seq[[Math]::Min($script:index,$script:seq.Count-1)];$script:index++;return $s } {$script:fixtureFree} {param($ms) $clock.Elapsed.TotalSeconds+=$ms/1000.0} $clock 180 $r}catch{$caught=$_.Exception.Message}
 if($Error){Check ($caught -like "*$Error*") "expected $Error";Check (-not $r.naturalDrainConfirmed) 'failure not success'}
 else{Check ($caught -eq '' -and $r.naturalDrainConfirmed) "natural drain: $caught";Check ($r.terminalPoll.activeProcesses -eq 0 -and $r.terminalPoll.rootExited) 'terminal evidence'}
 return $r
}
function Sample([bool]$Exit,[int]$Active,[int]$Code=0,[long]$Private=0){return @{RootExited=$Exit;ActiveProcesses=$Active;ExitCode=$Code;PrivateBytes=$Private;PeakJobBytes=$Private}}
$r=Test-Polls @((Sample $false 1),(Sample $true 1),(Sample $true 0))
Check ($r.pollCount -eq 3 -and $r.drainSamples.Count -eq 2) 'root then descendants drained'
$null=Test-Polls @((Sample $true 1 1)) -Error 'Nonzero'
$null=Test-Polls @((Sample $false 1 0 4GB)) -Error '4GiB'
$null=Test-Polls @((Sample $false 1)) -Free (2GB-1) -Error '2GiB'
$null=Test-Polls @((Sample $true 1)) -Error 'deadline'
$scratch=Join-Path ([IO.Path]::GetTempPath()) ('walking09-policy-'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $scratch
try{
 $marker=Join-Path $scratch 'slot.json'
 Write-IdleAtomic $marker @{owner='WalkingCensusRunner09';ownershipToken='ours'}
 Check (-not (Complete-IdleOwnership $marker 'ours' $false)) 'unconfirmed retained'
 Check (Test-Path -LiteralPath $marker) 'marker present'
 $caught=$false;try{Complete-IdleOwnership $marker 'foreign' $true}catch{$caught=$true}
 Check $caught 'foreign token refused'
 Check (Complete-IdleOwnership $marker 'ours' $true) 'confirmed exact owner'
 Check (-not (Test-Path -LiteralPath $marker)) 'confirmed marker closed'
}finally{
 # Exact files owned by this fixture only. Never recursive deletion.
 if(Test-Path -LiteralPath $marker){Remove-Item -LiteralPath $marker}
 Remove-Item -LiteralPath $scratch
}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1'){
 $tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
 Check ($errors.Count -eq 0) ("PowerShell syntax: "+$file.Name)
}
@{checks=$script:checks;failures=0;processesLaunched=0;UEExecuted=$false}|ConvertTo-Json -Compress
