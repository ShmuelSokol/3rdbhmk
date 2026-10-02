param([Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]{1,32}$')][string]$RunId,
      [ValidateSet('Compile')][string]$Mode='Compile',
      [switch]$CoordinatorNativeRun,[ValidateRange(60,600)][int]$DeadlineSeconds=300)
$ErrorActionPreference='Stop'
if(-not $CoordinatorNativeRun){throw 'CoordinatorNativeRun required; preparation never launches'}
if(-not [Environment]::Is64BitProcess){throw '64-bit PowerShell required'}
$base=$PSScriptRoot
. "$base/support.ps1"
$root=[IO.Path]::GetFullPath((Join-Path $base '../../../../../..'))
$proof=Get-Content -LiteralPath "$base/inputs.json" -Raw|ConvertFrom-Json
$pin=Get-Content -LiteralPath "$base/harness-hashes.json" -Raw|ConvertFrom-Json
foreach($p in $pin.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $base $p.Name)).Hash.ToLowerInvariant() -ne $p.Value){throw "Harness source changed: $($p.Name)"}}
if((Get-FileHash -LiteralPath "$base/OwnedChildJob.cs").Hash.ToLowerInvariant() -ne $proof.helperSha256){throw 'OS-proven helper revision mismatch'}
$out=Join-Path $base "runs/$RunId/$($Mode.ToLowerInvariant())"
if($Mode -eq 'Render'){
    $prior=Get-Content -LiteralPath "$base/runs/$RunId/compile/wrapper.json" -Raw|ConvertFrom-Json
    $nativePrior=Get-Content -LiteralPath "$base/runs/$RunId/compile/native.json" -Raw|ConvertFrom-Json
    if($prior.status -ne 'child_exited_zero' -or -not $prior.cleanupConfirmed -or -not $prior.sourcePreserved -or $nativePrior.status -ne 'compile_readback_passed'){throw 'Successful Compile receipt required'}
    if($nativePrior.harnessHashesSha256 -ne (Get-FileHash -LiteralPath "$base/harness-hashes.json").Hash.ToLowerInvariant()){throw 'Compile receipt source revision differs'}
}
if(Test-Path -LiteralPath $out){throw 'Fresh run required; never replace receipts'}
$marker=Join-Path $root 'SourceAssets/context-review/HaramThresholdSidesV1/native-slot-blocked.json'
if(Test-Path -LiteralPath $marker){throw 'Native ownership unresolved; do not clear marker automatically'}
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,ShaderCompileWorker,UnrealBuildTool,AutomationTool -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -OperationTimeoutSec 3|Where-Object {$_.CommandLine -match 'UnrealBuildTool|AutomationTool'})
if($busy.Count){throw 'Serial slot occupied; no foreign process touched'}
$lock=[IO.File]::Open((Join-Path $base 'native.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$null=New-Item -ItemType Directory -Path $out
$record=[ordered]@{status='starting';minimumStartCommitBytes=6GB;maximumOwnedJobBytes=4GB;reserveCommitBytes=2GB;deadlineSeconds=$DeadlineSeconds;cleanupDeadlineMilliseconds=5000;peakPrivateBytes=0L;cleanupConfirmed=$false;sourcePreserved=$false;slotBlocked=$false;nativeLaunch=$false}
$owned=$null;$acquired=$false;$token=[guid]::NewGuid().ToString('N');$clock=[Diagnostics.Stopwatch]::StartNew()
$before=[ordered]@{}
try{
    foreach($p in $pin.PSObject.Properties){
        $path=Join-Path $base $p.Name
        $h=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
        if($h -ne $p.Value){throw 'Harness changed during preflight'}
        $before[$path]=$h
    }
    foreach($entry in $proof.files.PSObject.Properties){
        foreach($prefix in @($root,"$base/P")){
            $path=Join-Path $prefix $entry.Value.relative
            $h=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
            if($h -ne $entry.Value.sha256){throw "Staged/protected dependency differs: $path"}
            $before[$path]=$h
        }
    }
    $frozen=Join-Path $base '../AngularVATStudy01/candidate_builder.py'
    $before[$frozen]=(Get-FileHash -LiteralPath $frozen).Hash.ToLowerInvariant()
    if($before[$frozen] -ne $proof.frozenBuilderSha256){throw 'Frozen generator source changed'}
    if('KohenReviewGuard.OwnedChildJob' -as [type]){throw 'Fresh PowerShell host required'}
    Add-Type -Path "$base/OwnedChildJob.cs"
    $free=[long][KohenReviewGuard.OwnedChildJob]::AvailableCommit()
    $record.startFreeCommitBytes=$free
    if($free -lt 6GB){throw '6GiB free commit required; no launch'}
    $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $argv=[string[]]@("$base/P/AngularVATReview.uproject",'-run=pythonscript',"-script=$base/native.py","-AngularRun=$RunId","-AngularMode=$Mode",
        '-nop4','-SCCProvider=None','-AllowCommandletRendering','-RenderOffscreen','-DisablePlugins=MetaHumanCharacter,MetaHumanSDK',
        '-unattended','-nosplash','-nosound','-notraceserver','-NoAsyncLoadingThread','-NoMetaHumanAccountPortalLoginFallback',
        '-asyncstaticmeshcompilationmaxconcurrency=1','-asyncskinnedassetcompilationmaxconcurrency=1','-asynctexturecompilationmaxconcurrency=1',
        '-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=999',
        '-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreadsDuringGame=999',
        '-ini:Engine:[DevOptions.Shaders]:bForceUseSCWMemoryPressureLimits=False',
        '-ini:Engine:[/Script/Engine.RendererSettings]:r.DynamicGlobalIlluminationMethod=0',
        '-ini:Engine:[/Script/Engine.RendererSettings]:r.ReflectionMethod=0',
        '-ini:Engine:[/Script/Engine.RendererSettings]:r.Shadow.Virtual.Enable=0',"-abslog=$out/native.log")
    if($Mode -eq 'Render'){
        # Separate tiny content-only project; never the production full-editor path.
        # Needed only for registered transient actors/components. 4GiB cap unchanged.
        $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
        $argv=[string[]]@($argv|Where-Object {$_ -ne '-run=pythonscript' -and -not $_.StartsWith('-script=') -and $_ -ne '-AllowCommandletRendering'})
        $argv += "-ExecutePythonScript=$base/native.py"
    }
    $record.executable=$exe;$record.arguments=$argv
    # UE PythonScriptCommandlet manually parses -script= and cannot consume the
    # helper's whole-token quoting. A hidden owned pwsh shim preserves the exact
    # engine argument line; UE and all workers remain descendants in the same job.
    $record.exactArgumentLine=($argv|ForEach-Object {
        if($_.Contains('"')){throw 'Unexpected literal quote in launch input'}
        if($_ -match '^(-script=|-abslog=|-ExecutePythonScript=)(.*)$'){$Matches[1]+'"'+$Matches[2]+'"'}
        elseif($_.StartsWith('-')){$_}else{'"'+$_+'"'}
    }) -join ' '
    Atomic-Receipt "$out/launch.json" $record
    if(Test-Path -LiteralPath $marker){throw 'Slot ownership changed; launch refused'}
    Atomic-Receipt $marker @{owner='AngularVATNative01';ownershipToken=$token;wrapperPid=$PID;receiptFolder=$out;status='unresolved_ownership'}
    $acquired=$true
    if([KohenReviewGuard.OwnedChildJob]::AvailableCommit() -lt 6GB){$record.cleanupConfirmed=$true;throw 'Commit fell below6GiB before launch'}
    if($clock.Elapsed.TotalSeconds -ge ($DeadlineSeconds-10)){$record.cleanupConfirmed=$true;throw 'Deadline consumed before launch'}
    $hostExe=(Get-Command pwsh -ErrorAction Stop).Source
    $shimArgs=[string[]]@('-NoProfile','-NonInteractive','-File',"$base/owned_ue_shim.ps1",'-LaunchFile',"$out/launch.json",'-DeadlineSeconds',([string]($DeadlineSeconds-5)))
    Assert-AngularDeadline $clock.Elapsed.TotalSeconds $DeadlineSeconds
    $owned=[KohenReviewGuard.OwnedChildJob]::new($hostExe,$shimArgs,"$base/P","$out/child-local.log",[ulong]4GB)
    $record.nativeLaunch=$true;$record.pid=$owned.ProcessId;$record.creationFileTime=$owned.CreationFileTime
    while($true){
        $sample=$owned.Poll();$free=[long][KohenReviewGuard.OwnedChildJob]::AvailableCommit()
        $private=[long][Math]::Max($sample.PrivateBytes,$sample.PeakJobBytes)
        $record.peakPrivateBytes=[Math]::Max($record.peakPrivateBytes,$private)
        if($private -ge 4GB){throw 'Owned job private cap'}
        if($free -lt 2GB){throw '2GiB reserve guard'}
        if($clock.Elapsed.TotalSeconds -ge ($DeadlineSeconds-6)){throw 'Total deadline: reserve cleanup5s plus poll margin'}
        if($sample.RootExited){
            $record.exitCode=$sample.ExitCode
            if($sample.ExitCode -ne 0 -or $sample.ActiveProcesses -ne 0){throw 'Child failed or descendants still live'}
            $record.status='child_exited_zero';break
        }
        Start-Sleep -Milliseconds 500
    }
}catch{
    $record.status='failed';$record.error=$_.Exception.Message
    $cause=$_.Exception;while($cause.InnerException){$cause=$cause.InnerException}
    if($cause.Data.Contains('OwnedProcessId')){
        $record.nativeLaunch=$true
        $record.pid=$cause.Data['OwnedProcessId'];$record.creationFileTime=$cause.Data['OwnedCreationFileTime']
        $record.cleanupConfirmed=($cause.Data['OwnedCleanupConfirmed'] -eq $true)
    }
}finally{
    try{
    if($owned){
        try{$record.cleanupConfirmed=$owned.StopWithinFiveSeconds();$record.cleanupError=$owned.CleanupError}
        catch{$record.cleanupConfirmed=$false;$record.cleanupError=$_.Exception.Message}
        finally{try{$owned.Dispose()}catch{$record.cleanupConfirmed=$false;$record.cleanupError=$_.Exception.Message}}
    }
    $record.ownedElapsedSeconds=$clock.Elapsed.TotalSeconds
    if($acquired){
        $clear=Complete-AngularOwnership $marker $token ($record.cleanupConfirmed -eq $true)
        $record.slotBlocked=$clear.slotBlocked;$record.markerError=$clear.error
    }
    try{
        $preservation=Get-AngularPreservation $before
        $record.sourcePreserved=$preservation.preserved;$record.changed=$preservation.changed;$record.preservationError=$preservation.error
        if($record.status -eq 'child_exited_zero'){
            $native=Get-Content -LiteralPath "$out/native.json" -Raw|ConvertFrom-Json
            $wanted=if($Mode -eq 'Compile'){'compile_readback_passed'}else{'controlled_pose_samples_not_temporal_acceptance'}
            if($native.status -ne $wanted){throw 'Native receipt proof failed'}
            if(@($native.compilers).Count -eq 0){throw 'Positive shader resource receipt missing'}
            foreach($compiler in $native.compilers){
                if(-not $compiler.positiveResourceShaderEvidence -or @($compiler.compilerErrors).Count -or @($compiler.compilerErrorsAfterStatistics).Count){throw 'Positive shader proof or clean diagnostics missing'}
                foreach($field in @('num_vertex_shader_instructions','num_pixel_shader_instructions','num_vertex_texture_samples','num_pixel_texture_samples','num_samplers')){
                    if([int]$compiler.statistics.$field -le 0){throw "Nonpositive shader statistic: $field"}
                }
            }
            $bad=Select-String -LiteralPath "$out/native.log" -Pattern 'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|LogMaterial: Error|Fatal error:'
            if($bad){throw 'Compiler/fallback diagnostic in local log'}
        }
    }catch{$record.status='evidence_failed';$record.error=$_.Exception.Message}
    if(-not $record.sourcePreserved -or ($record.nativeLaunch -and -not $record.cleanupConfirmed) -or $record.slotBlocked){$record.status='preservation_or_cleanup_failed'}
    Atomic-Receipt "$out/wrapper.json" $record
    }finally{$lock.Dispose()}
}
if($record.status -ne 'child_exited_zero'){throw "Run failed safely; inspect $out/wrapper.json; slotBlocked=$($record.slotBlocked)"}
Write-Output "Guarded run complete: $out/wrapper.json"
