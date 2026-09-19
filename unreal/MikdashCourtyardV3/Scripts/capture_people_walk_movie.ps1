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
    [switch]$UnfilteredMotionDiagnostic
)
$ErrorActionPreference='Stop'
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
if($ScheduledShots -and $captureFrames -gt 120){throw 'Scheduled screenshot diagnostic limited to120frames'}
New-Item -ItemType Directory -Path $outDir | Out-Null
$log=Join-Path $outDir 'runtime.log'
$receipt=Join-Path $outDir 'movie-receipt.json'
$ini='-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FableMovieProbe_'+$Label+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FableMovieProbe_'+$Label+'_Settings,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False'
$launchArgs="-windowed -ResX=$ResX -ResY=$ResY -nosplash -nosteam -notraceserver -notrace -dumpmovie -benchmark -fps=$FixedFps $ExtraArgs $ini -csvCaptureFrames=$captureFrames -ExitAfterCsvProfiling -csvNoProcessingThread -abslog=`"$log`" -ExecCmds=`"sg.ViewDistanceQuality 2,sg.ShadowQuality 2,sg.GlobalIlluminationQuality 2,sg.ReflectionQuality 2,sg.PostProcessQuality 2,sg.TextureQuality 2,sg.EffectsQuality 2,sg.FoliageQuality 2,sg.ShadingQuality 2,r.ScreenPercentage 77,Ghost,BugItGo $Go,csv.ForceExit 0`""
$inspectionFrame=$captureFrames-1
if($UnfilteredMotionDiagnostic){
    # Capture-only isolation of temporal reconstruction and blur; never a release preset.
    $launchArgs=$launchArgs.Replace('r.ScreenPercentage 77,','r.ScreenPercentage 100,r.AntiAliasingMethod 0,ShowFlag.AntiAliasing 0,r.MotionBlurQuality 0,')
}
$launchArgs += " -csvExecCmds=`"${inspectionFrame}:getall MikdashCrowdField SeededAgents,${inspectionFrame}:getall MikdashCrowdField RefusedSeeds`""
if($ScheduledShots){
    New-Item -ItemType Directory -Path $shots -Force | Out-Null
    $priorIndices=@($prior | ForEach-Object {if([IO.Path]::GetFileNameWithoutExtension($_) -match '^MovieFrame(\d+)$'){[long]$Matches[1]}})
    $nextIndex=if($priorIndices.Count){[long]($priorIndices | Measure-Object -Maximum).Maximum+1}else{0}
    $commands=@()
    for($frame=1;$frame -lt $captureFrames;$frame++){
        $target=(Join-Path $shots ('MovieFrame{0:d6}.png' -f ($nextIndex+$frame-1))).Replace('\','/')
        $commands+="${frame}:Shot filename=$target -nosuffix"
    }
    $commands+="${inspectionFrame}:getall MikdashCrowdField SeededAgents"
    $commands+="${inspectionFrame}:getall MikdashCrowdField RefusedSeeds"
    $commands+="${inspectionFrame}:getall HierarchicalInstancedStaticMeshComponent NumBuiltInstances"
    $commands+="${inspectionFrame}:getall HierarchicalInstancedStaticMeshComponent InstanceCountToRender"
    $launchArgs=$launchArgs.Replace('-dumpmovie ','') -replace ' -csvExecCmds="[^"]*"',''
    $launchArgs+=' -csvExecCmds="'+($commands -join ',')+'"'
    if($launchArgs.Length -gt 30000){throw 'Scheduled screenshot command exceeds safe Windows length'}
}
if($RealTimeDiagnostic){$launchArgs=$launchArgs.Replace("-benchmark -fps=$FixedFps ",'')}
$report=[ordered]@{status='starting';label=$Label;view=$View;archive=$Archive;bugItGo=$Go;method='Fixed-step consecutive MovieFrame screenshots; NOT a performance measurement';commandLine=$launchArgs;resolution="$ResX x $ResY";fixedFps=$FixedFps;settleFrames=$settleFrames;recordFrames=$recordFrames;captureFrames=$captureFrames;keepEvery=$KeepEvery;extraArgs=$ExtraArgs;childSha256=(Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant();startedUtc=[DateTime]::UtcNow.ToString('o');peakPrivateBytes=0;minimumFreeCommitBytes=[long]::MaxValue;maximumPrivateBytes=8GB;reserveCommitBytes=1.25GB;errors=@()}
function Save-Receipt {$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receipt -Encoding utf8}
$report.scheduledShots=[bool]$ScheduledShots
$report.realTimeDiagnostic=[bool]$RealTimeDiagnostic
$report.unfilteredMotionDiagnostic=[bool]$UnfilteredMotionDiagnostic
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
