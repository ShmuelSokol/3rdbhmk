param([ValidateRange(30,1800)][int]$FirstFrame=300,[ValidateRange(1,30)][int]$FrameStep=3,[ValidateSet('02','03')][string]$Study='02',[switch]$ExerciseDistanceStops)
$ErrorActionPreference='Stop'
$root=(Split-Path -Parent $PSScriptRoot).Replace('\','/')
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3,AutomationTool -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
if(([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 9GB){throw 'Requires9GiB free commit'}
$stamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$folder="$root/SourceAssets/perf-review/crowd-vat/ResidentRuntime$Study/game-$stamp"
if(Test-Path -LiteralPath $folder){throw 'Fresh game evidence folder required'}
New-Item -ItemType Directory -Path $folder | Out-Null
$mapFile="$root/Content/MikdashV3/Review/ResidentRuntime$Study/RuntimeReview.umap"
$mapHash=(Get-FileHash -LiteralPath $mapFile).Hash.ToLower()
$log="$folder/runtime.log";$receipt="$folder/run.json"
$exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$frames=@(0..49 | ForEach-Object {$FirstFrame+$FrameStep*$_})
$readbackFrame=$frames[-1]+2
$captureFrames=$readbackFrame+3
$commands=@($frames | ForEach-Object {"${_}:Shot filename=$folder/frame-$_.png -nosuffix"})
foreach($property in @('SeededAgents','RefusedSeeds','GroundTraceMisses','ActivePoseCount','FrozenLastSweep','CulledLastSweep')){$commands+="${readbackFrame}:getall MikdashCrowdField $property"}
$commands+="${readbackFrame}:LIST ISM"
if($ExerciseDistanceStops){
    if($Study -ne '03' -or $readbackFrame -lt 900){throw 'Distance-stop review requires Study03 and at least900frames'}
    $commands+=@('151:set MikdashCrowdField FreezeDistanceCm 1','181:getall MikdashCrowdField FrozenLastSweep',
        '241:set MikdashCrowdField FreezeDistanceCm 30000','751:set MikdashCrowdField FreezeDistanceCm 1',
        '751:set MikdashCrowdField CullDistanceCm 2','781:getall MikdashCrowdField CulledLastSweep',
        '841:set MikdashCrowdField CullDistanceCm 30000','841:set MikdashCrowdField FreezeDistanceCm 30000')
}
$ini='-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=ResidentRuntimeReview,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=ResidentRuntimeReview_Settings,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False'
$arguments=@(('"'+$root+'/MikdashCourtyardV3.uproject"'),"/Game/MikdashV3/Review/ResidentRuntime$Study/RuntimeReview",'-game','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-unattended','-nosplash','-nosound','-notraceserver','-notrace','-NoAsyncLoadingThread','-asyncstaticmeshcompilationmaxconcurrency=1','-DisablePlugins=MetaHumanCharacter,MetaHumanSDK','-NoMetaHumanAccountPortalLoginFallback','-benchmark','-fps=30',("-csvCaptureFrames=$captureFrames"),'-ExitAfterCsvProfiling','-csvNoProcessingThread','-MikdashCrowdMotionAudit','-MikdashCrowdReviewAudit',$ini,('-abslog="'+$log+'"'),'-ExecCmds="r.ScreenPercentage 100,r.AntiAliasingMethod 0,r.MotionBlurQuality 0,csv.ForceExit 0"',('-csvExecCmds="'+($commands -join ',')+'"'))
if(($arguments -join ' ').Length -gt 14500){throw 'Unreal command-line length exceeded'}
$record=[ordered]@{status='starting';scope='Fixed-step uncooked game-world movement review, not packaged release or performance';map=$mapFile;mapSha256=$mapHash;startedUtc=$stamp;log=$log;resolution=@(1280,720);fixedFps=30;captureFrames=$captureFrames;warmupFrames=$FirstFrame;frameStep=$FrameStep;requestedScreenshots=$frames;minimumStartCommitBytes=9GB;maximumPrivateBytes=8GB;reserveCommitBytes=1.25GB;peakPrivateBytes=0;commandLine=($arguments -join ' ')}
$record.exerciseDistanceStops=[bool]$ExerciseDistanceStops
function Save-Receipt {$record | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $receipt -Encoding utf8}
Save-Receipt;$child=$null
try{
    $record.runtimeDllSha256=(Get-FileHash -LiteralPath "$root/Plugins/MikdashRuntime/Binaries/Win64/UnrealEditor-MikdashRuntime.dll").Hash.ToLower()
    $child=Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $record.pid=$child.Id;$record.status='running';Save-Receipt;$deadline=(Get-Date).AddSeconds(600)
    do{
        Start-Sleep -Seconds 2;$child.Refresh();if($child.HasExited){break}
        $record.peakPrivateBytes=[math]::Max([long]$record.peakPrivateBytes,[long]$child.PrivateMemorySize64)
        if($child.PrivateMemorySize64 -gt 8GB -or ([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 1.25GB){throw 'Owned review game hit memory reserve'}
        if((Get-Date) -gt $deadline){throw 'Owned review game timed out'}
    }while($true)
    $child.WaitForExit();$record.exitCode=$child.ExitCode;if($child.ExitCode -ne 0){throw 'Review game exited nonzero'}
    if(@(Select-String -LiteralPath $log -SimpleMatch 'CSV finalize time :').Count -ne 1){throw 'CSV frame controller did not finalize uniquely'}
    $record.readbacks=@{}
    foreach($property in @('SeededAgents','RefusedSeeds','GroundTraceMisses','ActivePoseCount','FrozenLastSweep','CulledLastSweep')){
        $matchesFound=@(Select-String -LiteralPath $log -Pattern ('\.'+$property+' = (\d+)\s*$'))
        $expected=1
        if($ExerciseDistanceStops -and $property -in @('FrozenLastSweep','CulledLastSweep')){$expected=2}
        if($matchesFound.Count -ne $expected){throw "Missing expected $property readbacks"}
        $record.readbacks[$property]=[int]$matchesFound[-1].Matches[0].Groups[1].Value
        if($expected -eq 2){
            $duringStop=[int]$matchesFound[0].Matches[0].Groups[1].Value
            $record["during$property"]=$duringStop
            if($duringStop -ne 48 -or $record.readbacks[$property] -ne 0){throw "$property did not enter48 and return0"}
        }
    }
    if($record.readbacks.SeededAgents -ne 48 -or $record.readbacks.RefusedSeeds -ne 0 -or $record.readbacks.GroundTraceMisses -ne 0 -or $record.readbacks.ActivePoseCount -ne 2){throw 'Live population/ground/pose readback mismatch'}
    $record.images=@($frames | ForEach-Object {$p="$folder/frame-$_.png";if(-not(Test-Path -LiteralPath $p)){throw "Missing screenshot $_"};@{frame=$_;file=$p;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLower()}})
    $record.status='captured-live-review-pending'
}catch{$record.status='failed';$record.error=$_.Exception.Message}
finally{
    try{
        if($child){$child.Refresh();if(-not $child.HasExited){$child | Stop-Process -Force;$record.stoppedOwnedChild=$true}}
    }catch{$record.cleanupError=$_.Exception.Message;$record.status='failed-cleanup'}
    try{
        $record.mapUnchanged=(Get-FileHash -LiteralPath $mapFile).Hash.ToLower() -eq $mapHash
        if(-not $record.mapUnchanged){$record.status='failed-map-changed'}
    }catch{$record.mapHashError=$_.Exception.Message;$record.status='failed-map-check'}
    Save-Receipt
}
Write-Output "$($record.status): $receipt"
if($record.status -ne 'captured-live-review-pending'){exit 1}
