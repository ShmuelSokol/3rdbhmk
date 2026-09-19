<# Capture fixed-step animation evidence, not performance. Never deletes prior frames.
   SettleSeconds and RecordSeconds are simulated time at FixedFps; wall time is only a watchdog.
   Every new MovieFrame must form a contiguous numeric sequence. Native exit and the CSV
   frame controller must complete normally before a filmstrip can pass acquisition. #>
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$Label,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9._-]{1,40}$')][string]$View,
    [Parameter(Mandatory=$true)][ValidatePattern('\A-?[0-9]+(?:\.[0-9]+)?(?: -?[0-9]+(?:\.[0-9]+)?){5}\z')][string]$Go,
    [ValidateRange(1,30)][int]$SettleSeconds=10,
    [ValidateRange(1,10)][int]$RecordSeconds=3,
    [ValidateRange(640,1920)][int]$ResX=1280,
    [ValidateRange(360,1080)][int]$ResY=720,
    [ValidateRange(1,120)][int]$KeepEvery=1,
    [ValidateRange(1,120)][int]$FixedFps=30,
    [ValidatePattern('^(?:-CrowdCount=(?:0|[1-9][0-9]{0,4}))?$')][string]$ExtraArgs='',
    [switch]$ScheduledShots,
    [switch]$RealTimeDiagnostic,
    [switch]$UnfilteredMotionDiagnostic,
    [switch]$DisableMotionBlurDiagnostic,
    [switch]$DisableTemporalAADiagnostic,
    [switch]$InspectMotionState,
    [switch]$AuditMotionTransitions,
    [switch]$UseMotionHistoryCandidate,
    # When set, Go XYZ is the character capsule center; the existing native probe
    # restores collision and walks toward this XY with ordinary movement input.
    [ValidatePattern('\A(?:-?[0-9]+(?:\.[0-9]+)? -?[0-9]+(?:\.[0-9]+)?)?\z')][string]$WalkTo='',
    [ValidateSet('None','Velocity','Reprojection')][string]$MotionVisualization='None',
    [ValidatePattern('\A(?:(?:0(?:\.[0-9]{1,6})?|1(?:\.0{1,6})?) (?:0(?:\.[0-9]{1,6})?|1(?:\.0{1,6})?))?\z')][string]$InspectPixel='',
    [ValidatePattern('\A(?:/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+:PersistentLevel\.[A-Za-z][A-Za-z0-9_]{0,80})?\z')][string]$InspectActorPath=''
)
$ErrorActionPreference='Stop'
if($WalkTo -and ($RealTimeDiagnostic -or $SettleSeconds -lt 3)){throw 'Walking movie requires fixed-step capture and at least three settle seconds'}
$Archive=[IO.Path]::GetFullPath($Archive)
if($ExtraArgs -match '=(\d+)$' -and [int]$Matches[1] -gt 60000){throw 'CrowdCount must not exceed60000'}
$exe=Join-Path $Archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if(-not(Test-Path -LiteralPath $exe)){throw 'Packaged executable missing'}
$stageRoot=Split-Path (Split-Path (Split-Path $exe -Parent) -Parent) -Parent
$shots=Join-Path $stageRoot 'Saved\Screenshots\Windows'
$project=Split-Path $PSScriptRoot -Parent
$outDir=Join-Path $project "SourceAssets\visual-review\movie-$Label-$View"
if(Test-Path -LiteralPath $outDir){throw 'Fresh label/view required; existing evidence preserved'}
foreach($name in @('UnrealEditor','UnrealEditor-Cmd','AutomationTool','UnrealBuildTool','MikdashCourtyardV3')){
    if(Get-Process -Name $name -ErrorAction SilentlyContinue){throw "Native slot occupied by $name"}
}
if(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'}).Count){throw 'Native build slot occupied'}
if(([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 9GB){throw 'Requires9GiB free commit'}
$settleFrames=$SettleSeconds*$FixedFps
$recordFrames=$RecordSeconds*$FixedFps
$captureFrames=$settleFrames+$recordFrames+2
$volumeRoots=@([IO.Path]::GetPathRoot([IO.Path]::GetFullPath($outDir)),[IO.Path]::GetPathRoot($shots)) | Select-Object -Unique
$captureDrives=@($volumeRoots | ForEach-Object {[IO.DriveInfo]::new($_)})
foreach($captureDrive in $captureDrives){
    if($captureDrive.AvailableFreeSpace -lt (2GB+([long]$captureFrames*$ResX*$ResY*8))){throw 'Insufficient disk headroom for source frames and retained copies'}
}
$prior=@(Get-ChildItem -LiteralPath $shots -Filter 'MovieFrame*.png' -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
if($ScheduledShots -and $captureFrames -gt 240){throw 'Scheduled screenshot diagnostic limited to240frames'}
New-Item -ItemType Directory -Path $outDir | Out-Null
$log=Join-Path $outDir 'runtime.log'
$receipt=Join-Path $outDir 'movie-receipt.json'
$ini='-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FableMovieProbe_'+$Label+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FableMovieProbe_'+$Label+'_Settings,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False'
$launchArgs="-windowed -ResX=$ResX -ResY=$ResY -nosplash -nosteam -notraceserver -notrace -dumpmovie -benchmark -fps=$FixedFps $ExtraArgs $ini -csvCaptureFrames=$captureFrames -ExitAfterCsvProfiling -csvNoProcessingThread -abslog=`"$log`" -ExecCmds=`"sg.ViewDistanceQuality 2,sg.ShadowQuality 2,sg.GlobalIlluminationQuality 2,sg.ReflectionQuality 2,sg.PostProcessQuality 2,sg.TextureQuality 2,sg.EffectsQuality 2,sg.FoliageQuality 2,sg.ShadingQuality 2,r.ScreenPercentage 77,Ghost,BugItGo $Go,csv.ForceExit 0`""
$inspectionFrame=$captureFrames-1
if($AuditMotionTransitions){$launchArgs+=' -MikdashCrowdMotionAudit'}
if($UseMotionHistoryCandidate){$launchArgs+=' -MikdashCrowdMotionHistory'}
if($WalkTo){
    $origin=$Go.Split(' ');$target=$WalkTo.Replace(' ',':')
    $start=($origin[0..2]+@($origin[4],$origin[3])) -join ':'
    $launchArgs+=" -MikdashWalkProbe=label=MovieWalk;start=$start;wp=$target;delay=1;timeout=45"
}
$motionViewCommands=@()
if($MotionVisualization -eq 'Velocity'){
    # Global renderer shader: no uncooked BufferVisualization material or
    # shipping debug-view override. HSV encodes velocity direction/magnitude.
    $launchArgs=$launchArgs.Replace('Ghost,BugItGo','ShowFlag.VisualizeMotionBlur 1,r.MotionBlur.Visualize 1,r.MotionBlur.VisualizeDebugInformation 0,Ghost,BugItGo')
    $motionViewCommands=@('ShowFlag.VisualizeMotionBlur','r.MotionBlur.Visualize','r.MotionBlur.VisualizeDebugInformation')
}
elseif($MotionVisualization -eq 'Reprojection'){
    $launchArgs=$launchArgs.Replace('Ghost,BugItGo','ShowFlag.VisualizeReprojection 1,Ghost,BugItGo')
    $motionViewCommands=@('ShowFlag.VisualizeReprojection')
}
if($UnfilteredMotionDiagnostic){
    # Capture-only isolation of temporal reconstruction and blur; never a release preset.
    $launchArgs=$launchArgs.Replace('r.ScreenPercentage 77,','r.ScreenPercentage 100,r.AntiAliasingMethod 0,ShowFlag.AntiAliasing 0,r.MotionBlurQuality 0,')
}
elseif($DisableTemporalAADiagnostic){
    $launchArgs=$launchArgs.Replace('r.ScreenPercentage 77,','r.ScreenPercentage 77,r.AntiAliasingMethod 0,ShowFlag.AntiAliasing 0,')
}
if($DisableMotionBlurDiagnostic -and -not $UnfilteredMotionDiagnostic){
    $launchArgs=$launchArgs.Replace('r.ScreenPercentage 77,','r.ScreenPercentage 77,r.MotionBlurQuality 0,')
}
$inspectionCommands=@("${inspectionFrame}:getall MikdashCrowdField SeededAgents","${inspectionFrame}:getall MikdashCrowdField RefusedSeeds")
foreach($command in $motionViewCommands){$inspectionCommands+="${inspectionFrame}:$command"}
if($InspectMotionState){
    foreach($command in @('LIST ISM','r.Velocity.EnableVertexDeformation','r.VelocityOutputPass','r.AntiAliasingMethod')){
        $inspectionCommands+="${inspectionFrame}:$command"
    }
}
if($InspectPixel){$inspectionCommands+="${inspectionFrame}:InspectScenePixel $InspectPixel"}
if($InspectActorPath){
    foreach($property in @('StaticMesh','OverrideMaterials','RelativeLocation','RelativeRotation','RelativeScale3D')){
        $inspectionCommands+="${inspectionFrame}:getall StaticMeshComponent $property OUTER=$InspectActorPath"
    }
}
$launchArgs+=' -csvExecCmds="'+($inspectionCommands -join ',')+'"'
if($ScheduledShots){
    New-Item -ItemType Directory -Path $shots -Force | Out-Null
    $priorIndices=@($prior | ForEach-Object {if([IO.Path]::GetFileNameWithoutExtension($_) -match '^MovieFrame(\d+)$'){[long]$Matches[1]}})
    $nextIndex=if($priorIndices.Count){[long]($priorIndices | Measure-Object -Maximum).Maximum+1}else{0}
    $commands=@()
    for($frame=1;$frame -lt $captureFrames;$frame++){
        # UE resolves a basename in GameScreenshotSaveDirectory (ScreenShotDir in
        # GameEngine). Avoid repeating the long archive path on every frame.
        $target='MovieFrame{0:d6}.png' -f ($nextIndex+$frame-1)
        $commands+="${frame}:Shot filename=$target -nosuffix"
    }
    $commands+=$inspectionCommands
    $commands+="${inspectionFrame}:getall HierarchicalInstancedStaticMeshComponent NumBuiltInstances"
    $commands+="${inspectionFrame}:getall HierarchicalInstancedStaticMeshComponent InstanceCountToRender"
    $launchArgs=$launchArgs.Replace('-dumpmovie ','') -replace ' -csvExecCmds="[^"]*"',''
    $launchArgs+=' -csvExecCmds="'+($commands -join ',')+'"'
}
if($RealTimeDiagnostic){$launchArgs=$launchArgs.Replace("-benchmark -fps=$FixedFps ",'')}
# UE FCommandLine has a 16384-character buffer, smaller than Windows' limit.
if(($launchArgs.Length+$exe.Length+4) -gt 15000){throw 'Capture command exceeds conservative Unreal command-line limit'}
$report=[ordered]@{status='starting';label=$Label;view=$View;archive=$Archive;bugItGo=$Go;method='Fixed-step consecutive MovieFrame screenshots; NOT a performance measurement';commandLine=$launchArgs;resolution="$ResX x $ResY";fixedFps=$FixedFps;settleFrames=$settleFrames;recordFrames=$recordFrames;captureFrames=$captureFrames;keepEvery=$KeepEvery;extraArgs=$ExtraArgs;childSha256=(Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant();startedUtc=[DateTime]::UtcNow.ToString('o');peakPrivateBytes=0;minimumFreeCommitBytes=[long]::MaxValue;maximumPrivateBytes=8GB;reserveCommitBytes=1.25GB;errors=@()}
function Save-Receipt {$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receipt -Encoding utf8}
$report.scheduledShots=[bool]$ScheduledShots
$report.realTimeDiagnostic=[bool]$RealTimeDiagnostic
$report.unfilteredMotionDiagnostic=[bool]$UnfilteredMotionDiagnostic
$report.disableMotionBlurDiagnostic=[bool]$DisableMotionBlurDiagnostic
$report.disableTemporalAADiagnostic=[bool]$DisableTemporalAADiagnostic
$report.inspectPixel=$InspectPixel
$report.inspectActorPath=$InspectActorPath
$report.inspectMotionState=[bool]$InspectMotionState
$report.auditMotionTransitions=[bool]$AuditMotionTransitions
$report.motionHistoryCandidate=[bool]$UseMotionHistoryCandidate
$report.walkTo=$WalkTo
$report.motionVisualization=$MotionVisualization
$report.motionVisualizationReadbacks=@()
if($ScheduledShots){$report.method='Fixed-step scheduled ordinary screenshots; NOT a performance measurement'}
if($RealTimeDiagnostic){$report.method='Real-time visibility diagnostic; requested frame counts only, NO fixed simulated-time claim'}
Save-Receipt
$proc=$null
try{
    $proc=Start-Process -FilePath $exe -ArgumentList $launchArgs -WorkingDirectory $stageRoot -WindowStyle Hidden -PassThru
    $report.pid=$proc.Id;$report.status='running';Save-Receipt
    $deadline=(Get-Date).AddSeconds(120+$captureFrames*5)
    while((Get-Date) -lt $deadline){
        Start-Sleep -Seconds 2;$proc.Refresh();if($proc.HasExited){break}
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $report.peakPrivateBytes=[Math]::Max([long]$report.peakPrivateBytes,$proc.PrivateMemorySize64)
        $report.minimumFreeCommitBytes=[Math]::Min([long]$report.minimumFreeCommitBytes,$free)
        if($proc.PrivateMemorySize64 -gt 8GB -or $free -lt 1.25GB){throw 'Owned movie capture hit memory guard'}
        foreach($captureDrive in $captureDrives){if($captureDrive.AvailableFreeSpace -lt 1GB){throw 'Owned movie capture hit disk reserve'}}
    }
    if(-not $proc.HasExited){throw 'Movie frame completion watchdog expired'}
    if($proc.ExitCode -ne 0){throw 'Nonzero game exit'}
    if(@(Select-String -LiteralPath $log -SimpleMatch 'CSV finalize time :').Count -ne 1){throw 'Missing unique CSV frame-controller finalization'}
    $report.csvFinalized=$true
    if($InspectPixel -and @(Select-String -LiteralPath $log -SimpleMatch 'ScenePixelV1 complete candidates=').Count -ne 1){throw 'Expected one completed scene pixel inspection'}
    if($InspectActorPath -and -not @(Select-String -LiteralPath $log -SimpleMatch ($InspectActorPath+'.') | Where-Object {$_.Line.Contains('.StaticMesh = ')}).Count){throw 'Expected inspected actor mesh readback'}
    if($InspectMotionState){
        if(@(Select-String -LiteralPath $log -SimpleMatch 'Name, Num Instances, Has Previous Transform, Num Custom Floats').Count -ne 1){throw 'Expected one native ISM motion-state listing'}
        foreach($variable in @('r.Velocity.EnableVertexDeformation','r.VelocityOutputPass','r.AntiAliasingMethod')){
            if(-not @(Select-String -LiteralPath $log -Pattern ([regex]::Escape($variable)+'\s*=\s*"?-?\d+')).Count){throw "Missing motion-state readback: $variable"}
        }
    }
    if($AuditMotionTransitions -and @(Select-String -LiteralPath $log -SimpleMatch 'CrowdMotionAuditV1 complete samples=4096 ').Count -ne 1){throw 'Expected one complete bounded motion-transition audit'}
    if($UseMotionHistoryCandidate){
        if(@(Select-String -LiteralPath $log -SimpleMatch 'CrowdMotionHistoryV3 enabled customFloats=26 poses=6').Count -ne 1){throw 'Expected one complete history candidate activation'}
        if(@(Select-String -LiteralPath $log -SimpleMatch 'CrowdMotionHistoryV3 refused').Count){throw 'History candidate activation refused'}
    }
    if($WalkTo){
        $starts=@(Select-String -LiteralPath $log -Pattern 'MIKDASH_WALKPROBE start label=MovieWalk t=([0-9.]+) ')
        if($starts.Count -ne 1){throw 'Expected one native walking start'}
        $startTime=[double]::Parse($starts[0].Matches[0].Groups[1].Value,[cultureinfo]::InvariantCulture)
        if(@(Select-String -LiteralPath $log -SimpleMatch 'MIKDASH_WALKPROBE stuck label=MovieWalk ')){throw 'Walking movie encountered a stall'}
        $samples=@(Select-String -LiteralPath $log -Pattern 'MIKDASH_WALKPROBE sample label=MovieWalk t=([0-9.]+) pos=(-?[0-9.]+),(-?[0-9.]+),(-?[0-9.]+) feetZ=(-?[0-9.]+) speed2D=([0-9.]+) velZ=(-?[0-9.]+) mode=(\d+) grounded=(\d+) ')
        $moving=@()
        foreach($sample in $samples){
            $g=$sample.Matches[0].Groups
            $values=@(1..7 | ForEach-Object {[double]::Parse($g[$_].Value,[cultureinfo]::InvariantCulture)})
            $time=$startTime+$values[0]
            # Keep away from frame-window boundaries; prove actual grounded movement
            # during retained footage rather than accepting a launch command alone.
            if($time -gt ($SettleSeconds+2.0/$FixedFps) -and $time -lt ($SettleSeconds+$RecordSeconds-2.0/$FixedFps) -and $values[5] -gt 10 -and $g[9].Value -eq '1'){
                $moving+=@{gameSeconds=$time;x=$values[1];y=$values[2];z=$values[3];speed=$values[5]}
            }
        }
        if($moving.Count -lt 2){throw 'Insufficient grounded walking samples in retained footage'}
        $distance=[math]::Sqrt([math]::Pow($moving[-1].x-$moving[0].x,2)+[math]::Pow($moving[-1].y-$moving[0].y,2))
        $report.walkingEvidence=@{scope='Movement during footage, not full route acceptance';samples=$moving;displacementCm=$distance}
        if($distance -lt 100){throw 'Retained walking footage spans less than100cm'}
    }
    foreach($variable in $motionViewCommands){
        $expected=if($variable -eq 'r.MotionBlur.VisualizeDebugInformation'){0}else{1}
        $readbacks=@(Select-String -LiteralPath $log -Pattern ('(?<![A-Za-z0-9_.])'+[regex]::Escape($variable)+'\s*=\s*(?:"([^"]*)"|(\S+))(?:\s|$)'))
        if(-not $readbacks.Count){throw "Missing motion visualization readback: $variable"}
        $lastReadback=$readbacks[-1]
        $valueMatch=$lastReadback.Matches[0]
        $rawValue=if($valueMatch.Groups[1].Success){$valueMatch.Groups[1].Value}else{$valueMatch.Groups[2].Value}
        $actual=0
        if($rawValue -ceq 'true'){$actual=1}
        elseif($rawValue -ceq 'false'){$actual=0}
        elseif(-not [int]::TryParse($rawValue,[ref]$actual)){throw "Invalid final motion visualization readback: $variable = $rawValue"}
        $report.motionVisualizationReadbacks+=@{variable=$variable;expected=$expected;actual=$actual;raw=$rawValue;line=$lastReadback.LineNumber;count=$readbacks.Count}
        if($actual -ne $expected){throw "Last motion visualization readback differs: $variable = $actual; expected $expected"}
    }
    $counts=@(Select-String -LiteralPath $log -Pattern '\.SeededAgents = (\d+)\s*$')
    if($counts.Count -ne 1){throw 'Expected one late crowd population readback'}
    $report.seededAgents=[int]$counts[0].Matches[0].Groups[1].Value
    if($ExtraArgs -match '=(\d+)$' -and $report.seededAgents -ne [int]$Matches[1]){throw 'Late population differs from request'}
}catch{$report.errors+=$_.Exception.Message}
finally{
    if($proc){
        try{$proc.Refresh();if(-not $proc.HasExited){[void]$proc.CloseMainWindow();[void]$proc.WaitForExit(15000)}}catch{$report.errors+='Graceful close failed: '+$_.Exception.Message}
        try{$proc.Refresh();if(-not $proc.HasExited){$proc | Stop-Process -Force;$report.errors+='Owned game required termination'}else{$report.exitCode=$proc.ExitCode}}catch{$report.errors+='Owned cleanup failed: '+$_.Exception.Message}
    }
    Save-Receipt
}
try{
    $fresh=@(Get-ChildItem -LiteralPath $shots -Filter 'MovieFrame*.png' -File -ErrorAction SilentlyContinue | Where-Object {$prior -notcontains $_.FullName} | ForEach-Object {
        if($_.BaseName -notmatch '^MovieFrame(\d+)$'){throw 'Unexpected movie frame naming'}
        [pscustomobject]@{index=[long]$Matches[1];file=$_}
    } | Sort-Object index)
    $report.framesDumped=$fresh.Count
    if($fresh.Count -lt ($settleFrames+$recordFrames)){throw 'Insufficient rendered frames for requested simulated window'}
    for($i=1;$i -lt $fresh.Count;$i++){if($fresh[$i].index -ne ($fresh[$i-1].index+1)){throw 'Movie frame sequence has a gap'}}
    $report.firstSourceIndex=$fresh[0].index
    $kept=@()
    for($i=$settleFrames;$i -lt ($settleFrames+$recordFrames);$i+=$KeepEvery){
        $source=$fresh[$i];$dest=Join-Path $outDir ('frame-{0:d6}.png' -f $i)
        Copy-Item -LiteralPath $source.file.FullName -Destination $dest
        $kept+=[ordered]@{file=$dest;source=$source.file.Name;sourceIndex=$source.index;sequenceIndex=$i;simulatedSecondsFromFirstDump=if($RealTimeDiagnostic){$null}else{$i/[double]$FixedFps};sha256=(Get-FileHash -LiteralPath $dest).Hash.ToLowerInvariant()}
    }
    $report.frames=$kept;$report.framesKept=$kept.Count
    $report.rawLogSha256=(Get-FileHash -LiteralPath $log).Hash.ToLowerInvariant()
}catch{$report.errors+=$_.Exception.Message}
finally{
    $report.status=if($report.errors.Count -eq 0 -and $report.csvFinalized -and $report.framesKept -gt 0){'movie_captured_visual_review_pending'}else{'failed_capture'}
    $report.finishedUtc=[DateTime]::UtcNow.ToString('o');Save-Receipt
}
Write-Output "$($report.status): $outDir"
if($report.status -eq 'failed_capture'){exit 1}
