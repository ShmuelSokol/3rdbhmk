param(
 [Parameter(Mandatory)][ValidateSet('Build','Census')][string]$Mode,
 [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]{1,32}$')][string]$RunId,
 [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedManifest,
 [ValidatePattern('^[a-z0-9-]{1,32}$')][string]$BuildRun,
 [ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedBuildSeal
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=[IO.Path]::GetFullPath($PSScriptRoot)
if($root -notmatch '^C:\\Mikdash\\Verification\\WalkingCensusRunner09-review-[a-z0-9-]{1,32}$'){throw 'Exact reviewed external stage required'}
if((Get-FileHash -LiteralPath "$root/manifest.json").Hash.ToLowerInvariant() -cne $ExpectedManifest){throw 'Reviewed manifest mismatch'}
$manifest=Get-Content -LiteralPath "$root/manifest.json" -Raw|ConvertFrom-Json
foreach($p in $manifest.files.PSObject.Properties){
 if((Get-FileHash -LiteralPath (Join-Path $root $p.Name)).Hash.ToLowerInvariant() -cne $p.Value){throw 'Source closure mismatch'}
}
$inputs=Get-Content -LiteralPath "$root/inputs.json" -Raw|ConvertFrom-Json
$python=$inputs.python
. "$root/support.ps1"
function Invoke-Offline([string[]]$Arguments){
 & $python -B "$root/runner.py" @Arguments
 if($LASTEXITCODE -ne 0){throw 'Offline closure/result validation failed'}
}
Invoke-Offline @('verify')
$marker=$inputs.slotMarker
if(Test-Path -LiteralPath $marker){throw 'Unresolved shared slot; no launch'}
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3,ShaderCompileWorker,UnrealBuildTool,AutomationTool,MSBuild,dotnet,cl,link -ErrorAction SilentlyContinue)
if($busy.Count){throw 'Serial slot busy; no foreign cleanup'}
$os=Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 3
if($null -eq $os.FreeVirtualMemory -or [long]$os.FreeVirtualMemory*1KB -lt 9GB){throw '9GiB entry guard; no launch'}
$prep=@('prepare','--mode',$Mode,'--name',$RunId)
if($Mode -eq 'Census'){
 if(-not $BuildRun -or -not $ExpectedBuildSeal){throw 'Pinned successful build run and independently reviewed seal hash required'}
 if((Get-FileHash -LiteralPath "$root/runs/$BuildRun/build-seal.json").Hash.ToLowerInvariant() -cne $ExpectedBuildSeal){throw 'Reviewed compiled seal mismatch'}
 $prep+=@('--build',$BuildRun)
}
Invoke-Offline $prep
$out=Join-Path "$root/runs" $RunId
$request=Get-Content -LiteralPath "$out/request.json" -Raw|ConvertFrom-Json
$project="$out/ProbeProject/CookedWorldProbe.uproject"
$savePrefix=$request.descriptor.savePrefix
if($Mode -eq 'Build'){
 $exe='C:/Windows/System32/cmd.exe'
 $command='@echo off'+"`r`n"+'call "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" CookedWorldProbeEditor Win64 Development -Project="'+$project+'" -WaitMutex -NoHotReload -NoXGE -NoUBA -NoFASTBuild -MaxParallelActions=1 -NoEngineChanges -Log="'+$out+'/compiler-local.log"'+"`r`n"+'exit /b %errorlevel%'+"`r`n"
 [IO.File]::WriteAllText("$out/compile.cmd",$command)
 $launchArgs=[string[]]@('/d','/c',"$out/compile.cmd")
}else{
 $exe=$inputs.engineExe
 $ini="-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=$savePrefix,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=${savePrefix}_Settings,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False"
 $launchArgs=[string[]]@($project,$inputs.map,'-game','-WalkingCensus09','-unattended','-NullRHI','-nosound','-nosplash','-NoLiveCoding','-NoHotReload','-NoSourceControl','-ddc=NoShared',"-UserDir=$out/User/","-abslog=$out/native-local.log",$ini)
}
Write-IdleAtomic "$out/launch.json" @{exe=$exe;arguments=$launchArgs;workingDirectory=$out;savePrefix=$savePrefix;mode=$Mode}
# Redirect through a hidden owned shim; helper's suspended Job creation encloses
# this shim and every descendant before execution. No unowned Start-Process.
$shim=@'
$ErrorActionPreference='Stop'
$spec=Get-Content -LiteralPath "$PSScriptRoot/launch.json" -Raw|ConvertFrom-Json
$env:UE_LocalDataCachePath="$PSScriptRoot/DDC"
[Environment]::SetEnvironmentVariable('UE-LocalDataCachePath',"$PSScriptRoot/DDC",'Process')
[Environment]::SetEnvironmentVariable('UE-SharedDataCachePath','None','Process')
$s=[Diagnostics.ProcessStartInfo]::new()
$s.FileName=$spec.exe;$s.WorkingDirectory=$spec.workingDirectory
$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.WindowStyle='Hidden'
foreach($a in $spec.arguments){$s.ArgumentList.Add([string]$a)}
$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true
$p=[Diagnostics.Process]::Start($s)
$stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
if(-not $p.WaitForExit(165000)){throw 'Shim deadline; enclosing Job must clean up'}
# Native log files carry full logs. Bound echoed output to avoid duplicate receipts.
$a=$stdout.Result;$b=$stderr.Result
Write-Output ($a.Substring(0,[Math]::Min(16384,$a.Length)))
Write-Output ($b.Substring(0,[Math]::Min(16384,$b.Length)))
exit $p.ExitCode
'@
[IO.File]::WriteAllText("$out/launch-shim.ps1",$shim)
if((Get-FileHash -LiteralPath "$root/OwnedChildJob.cs").Hash.ToLowerInvariant() -cne '0ef998314f3e68976c851e055d9aafe0e56e935334f1556a44e5e683a05fcec4'){throw 'Owned helper pin'}
Add-Type -Path "$root/OwnedChildJob.cs"
$record=[ordered]@{mode=$Mode;manifest=$ExpectedManifest;status='failed';cleanupConfirmed=$false;slotBlocked=$false;sourcePreserved=$false;peakOwnedJobBytes=0L;savePrefix=$savePrefix;externalProject=$project;worldReady=$false}
$timer=[Diagnostics.Stopwatch]::StartNew()
$token=[guid]::NewGuid().ToString('N');$owned=$null;$acquired=$false;$constructorEntered=$false
try{
 Write-IdleAtomic $marker @{owner='WalkingCensusRunner09';ownershipToken=$token;run=$out;status='ownership_unresolved'}
 $acquired=$true
 $guard=Get-IdleGuard ([KohenReviewGuard.OwnedChildJob]::AvailableCommit()) 0 $timer.Elapsed.TotalSeconds 180 -Acquire
 if($guard){throw $guard}
 $busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3,ShaderCompileWorker,UnrealBuildTool,AutomationTool,MSBuild,dotnet,cl,link -ErrorAction SilentlyContinue)
 if($busy.Count){throw 'Serial slot became busy'}
 $hostExe='C:/Users/shmue/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
 $constructorEntered=$true
 $owned=[KohenReviewGuard.OwnedChildJob]::new($hostExe,[string[]]@('-NoProfile','-NonInteractive','-File',"$out/launch-shim.ps1"),$out,"$out/owned-local.log",[ulong]4GB)
 $record.ownedPid=$owned.ProcessId;$record.ownedCreationFileTime=$owned.CreationFileTime
 Wait-IdleNaturalExit {$owned.Poll()} {[KohenReviewGuard.OwnedChildJob]::AvailableCommit()} {param($ms) Start-Sleep -Milliseconds $ms} $timer 180 $record
}catch{$record.error=$_.Exception.Message}
finally{
 if($owned){
  try{$record.cleanupConfirmed=$owned.StopWithinFiveSeconds();$record.cleanupError=$owned.CleanupError}
  catch{$record.cleanupConfirmed=$false;$record.cleanupError=$_.Exception.Message}
  finally{try{$owned.Dispose()}catch{$record.cleanupConfirmed=$false;$record.cleanupError=$_.Exception.Message}}
 }elseif(-not $constructorEntered){$record.cleanupConfirmed=$true}
 # Constructor uncertainty is NOT cleared from root-only exception metadata.
 if($acquired){try{$record.slotBlocked=-not (Complete-IdleOwnership $marker $token $record.cleanupConfirmed)}catch{$record.slotBlocked=$true;$record.markerError=$_.Exception.Message}}
 $record.executionElapsedSeconds=$timer.Elapsed.TotalSeconds
 if(-not $record.cleanupConfirmed -or $record.slotBlocked){$record.status='cleanup_unconfirmed'}
 elseif($record.executionElapsedSeconds -ge 180){$record.status='deadline_exceeded'}
 try{Invoke-Offline @('preserve','--name',$RunId);$record.sourcePreserved=$true}catch{$record.status='source_changed';$record.preservationError=$_.Exception.Message}
 if($record.status -eq 'child_exited_zero' -and $record.sourcePreserved){
  if($Mode -eq 'Build'){$record.status='build_exit_zero'}
  else{try{Invoke-Offline @('validate','--name',$RunId);$record.status='census_diagnostic_validated'}catch{$record.status='result_rejected';$record.validationError=$_.Exception.Message}}
 }
 Write-IdleAtomic "$out/receipt.json" $record
}
Write-Output "Receipt: $out/receipt.json"
if($record.status -notin @('build_exit_zero','census_diagnostic_validated')){throw "Reviewed run refused/failed: $($record.status)"}
