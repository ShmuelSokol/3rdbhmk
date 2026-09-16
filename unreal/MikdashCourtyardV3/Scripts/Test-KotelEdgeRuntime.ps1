<# Observes the planned outward Kotel excavation-edge crossing in a fresh packaged process.
   The existing walker diagnostic has no exit command. This wrapper stops only its
   owned child AFTER copying its completed logs; that is not reported as normal exit.
#>
param(
    [string]$Archive,
    [ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedChildSha256,
    [switch]$DisableClosure,
    [ValidateSet('VisualOnly','PawnBlocking')][string]$ExpectedCollisionMode='PawnBlocking',
    [switch]$Constrained,
    [switch]$PlanOnly,
    [switch]$SelfTest,
    [ValidateRange(60,180)][int]$TimeoutSeconds=90
)
$ErrorActionPreference='Stop'
function Number-Field([string]$Line,[string]$Name) {
    $match=[regex]::Match($Line,'(?:^|\s)'+[regex]::Escape($Name)+'=(-?\d+(?:\.\d+)?)')
    if(!$match.Success){throw "Missing numeric $Name in native event"}
    return [double]::Parse($match.Groups[1].Value,[Globalization.CultureInfo]::InvariantCulture)
}
function Floor-Identity([string]$Line) {
    $match=[regex]::Match($Line,'comp=(\S+) owner=(\S+) mesh=(\S+) tags=(\S+)')
    if(!$match.Success){throw 'Missing native hit component/owner/mesh identity'}
    return [ordered]@{component=$match.Groups[1].Value;actor=$match.Groups[2].Value;mesh=$match.Groups[3].Value;tags=$match.Groups[4].Value}
}
function Source-TerrainZ([double]$X,[double]$Y) {
    # Exact source triangle279: zero Y gradient. Never extrapolate its plane.
    if($X -gt -21624.515625 -or $Y -gt 19972.431640625 -or ($X+$Y) -lt -4152.083984375){return $null}
    return -622.593235044541 - 0.4399999755859375*($X+22487.94)
}
function Read-EdgeObservation([string]$LogText,[string]$ClosureComponentName='', [string]$ClosureActorName='', [double]$FaceX=-22487.94) {
    # -22487.94 is the CUT boundary, where the V1 curtain stood and where the source-terrain
    # plane above still starts. KotelRetainingWallV2 stands on the deck, up to MAX_DEVIATION_CM
    # inside that line, so the blocking face is passed in from the generated geometry
    # (retaining-wall-v2.json probeLane.footingFrontXcm) rather than assumed to be the boundary.
    $lines=@($LogText -split '\r?\n' | Where-Object {$_ -match 'MIKDASH_WALKPROBE \w+ label=KotelEdgeOut '})
    $starts=@($lines | Where-Object {$_ -match 'MIKDASH_WALKPROBE start '})
    $done=@($lines | Where-Object {$_ -match 'MIKDASH_WALKPROBE done '})
    if($starts.Count -ne 1 -or $done.Count -ne 1){throw 'Need exactly one native start and done event'}
    if($starts[0] -notmatch 'capsule=34\.0/96\.0 ' -or $starts[0] -notmatch 'state=MODERN '){throw 'Native capsule/state differs from reviewed plan'}
    $samples=@();$landings=@();$sweeps=@();$reaches=@()
    foreach($line in $lines){
        if($line -match 'MIKDASH_WALKPROBE sample '){
            $xyz=[regex]::Match($line,' pos=(-?[\d.]+),(-?[\d.]+),(-?[\d.]+) ')
            if(!$xyz.Success){throw 'Missing actual sample position'}
            $v=@(1..3 | ForEach-Object {[double]::Parse($xyz.Groups[$_].Value,[Globalization.CultureInfo]::InvariantCulture)})
            $samples+=@{t=(Number-Field $line 't');x=$v[0];y=$v[1];z=$v[2];feetZ=(Number-Field $line 'feetZ');grounded=(Number-Field $line 'grounded');mode=(Number-Field $line 'mode');velocityZ=(Number-Field $line 'velZ');floor=(Floor-Identity $line);sourceTerrainZ=(Source-TerrainZ $v[0] $v[1]);raw=$line}
        } elseif($line -match 'MIKDASH_WALKPROBE landed '){
            $landings+=@{t=(Number-Field $line 't');dropCm=(Number-Field $line 'dropCm');feetZ=(Number-Field $line 'feetZ');floor=(Floor-Identity $line);raw=$line}
        } elseif($line -match 'MIKDASH_WALKPROBE stuck '){
            $impact=[regex]::Match($line,' at=X=(-?[\d.]+) Y=(-?[\d.]+) Z=(-?[\d.]+) normal=X=(-?[\d.]+) Y=(-?[\d.]+) Z=(-?[\d.]+) ')
            if(!$impact.Success){throw 'Missing actual capsule-sweep impact/normal'}
            $v=@(1..6 | ForEach-Object {[double]::Parse($impact.Groups[$_].Value,[Globalization.CultureInfo]::InvariantCulture)})
            $sweeps+=@{t=(Number-Field $line 't');blocking=(Number-Field $line 'blocking');impactX=$v[0];impactY=$v[1];impactZ=$v[2];normalX=$v[3];normalY=$v[4];normalZ=$v[5];hit=(Floor-Identity $line);raw=$line}
        } elseif($line -match 'MIKDASH_WALKPROBE reached '){$reaches+=@{waypoint=(Number-Field $line 'wp');t=(Number-Field $line 't');raw=$line}}
    }
    if(!$samples.Count){throw 'Missing actual trajectory samples'}
    $firstGround=@($samples | Where-Object {$_.grounded -eq 1 -and $_.t -le 1.0} | Select-Object -First 1)
    $firstLanding=@($landings | Where-Object {$_.t -le 1.0} | Select-Object -First 1)
    # Only the exact deck mesh is currently proven here. An unidentified proxy
    # or the higher PrecinctCut floor is a confound, not a relaxed precondition.
    $initialOK=$firstGround.Count -eq 1 -and $firstLanding.Count -eq 1
    if($initialOK){
        $initialOK=[Math]::Abs($firstGround[0].feetZ+984.594) -le 5 -and [Math]::Abs($firstLanding[0].feetZ+984.594) -le 5 -and
            $firstGround[0].floor.mesh -eq 'SM_PlazaV1_DeckTile' -and $firstLanding[0].floor.mesh -eq 'SM_PlazaV1_DeckTile' -and
            [Math]::Abs($firstGround[0].x+22187.94) -le 10 -and [Math]::Abs($firstGround[0].y-19383.62484) -le 10
    }
    $after=@($samples | Where-Object {$_.t -gt 1.0})
    $highSide=@($after | Where-Object {$null -ne $_.sourceTerrainZ -and $_.x -le (-22487.94-44) -and [Math]::Abs($_.y-19383.62484) -le 75})
    $penetration=@($highSide | Where-Object {$_.feetZ -lt $_.sourceTerrainZ-10})
    $falling=@($highSide | Where-Object {$_.grounded -eq 0 -and $_.mode -eq 3 -and $_.velocityZ -lt -1})
    $last=$samples[-1]
    $finalPosition=[regex]::Match($done[0],' finalPos=X=(-?[\d.]+) Y=(-?[\d.]+) Z=(-?[\d.]+) ')
    if(!$finalPosition.Success){throw 'Missing actual final native position'}
    $fv=@(1..3 | ForEach-Object {[double]::Parse($finalPosition.Groups[$_].Value,[Globalization.CultureInfo]::InvariantCulture)})
    $final=@{t=(Number-Field $done[0] 't');x=$fv[0];y=$fv[1];z=$fv[2];feetZ=(Number-Field $done[0] 'finalFeetZ');grounded=(Number-Field $done[0] 'grounded');floor=(Floor-Identity $done[0]);sourceTerrainZ=(Source-TerrainZ $fv[0] $fv[1])}
    if($final.t -lt $last.t){throw 'Native done event predates last trajectory sample'}
    $landedAfterLastSample=@($landings | Where-Object {$_.t -gt $last.t -and $_.t -le $final.t})
    # Done supplies actual final grounded state and position; samples can precede
    # it by 0.5s. A later landing invalidates stale falling-mode/velocity evidence.
    $unfinishedFall=$final.grounded -eq 0 -and $last.mode -eq 3 -and $last.grounded -eq 0 -and $last.velocityZ -lt -1 -and $landedAfterLastSample.Count -eq 0
    $edgeBlocks=@($sweeps | Where-Object {$_.blocking -eq 1 -and [Math]::Abs($_.impactX-$FaceX) -le 44 -and [Math]::Abs($_.impactY-19383.62484) -le 75 -and $_.normalX -gt 0.5 -and $_.hit.component -ne 'none' -and $_.hit.actor -ne 'none' -and ($_.hit.mesh -ne '-' -or ($ClosureComponentName -and $ClosureActorName -and $_.hit.component -eq $ClosureComponentName -and $_.hit.actor -eq $ClosureActorName -and $_.hit.tags -match '(?:^|\+)KotelClosureRuntimeV1(?:\+|$)'))})
    # The pawn must never get past the blocking face, which now stands on the deck.
    $neverCrossed=$final.x -ge $FaceX -and @($after | Where-Object {$_.x -lt $FaceX}).Count -eq 0
    $groundedOnDeck=$final.grounded -eq 1 -and [Math]::Abs($final.feetZ+984.594) -le 5 -and $after.Count -gt 0 -and @($after | Where-Object {$_.grounded -ne 1 -or [Math]::Abs($_.feetZ+984.594) -gt 5}).Count -eq 0
    $actualReach=@($reaches | Where-Object {$_.waypoint -eq 0}).Count -eq 1
    $finalOnHighFloor=$null -ne $final.sourceTerrainZ -and $final.grounded -eq 1 -and [Math]::Abs($final.feetZ-$final.sourceTerrainZ) -le 5 -and $final.floor.mesh -ne '-' -and $final.floor.actor -ne 'none'
    $nearTarget=[Math]::Abs($final.x+22787.94) -le 75 -and [Math]::Abs($final.y-19383.62484) -le 75
    $sustainedHigh=@($highSide | Where-Object {$_.grounded -eq 1 -and [Math]::Abs($_.feetZ-$_.sourceTerrainZ) -le 5}).Count -ge 2
    $category='inconclusive-trajectory'
    if(!$initialOK){$category='inconclusive-initial-floor'}
    elseif($null -eq $final.sourceTerrainZ -or @($after | Where-Object {$null -eq $_.sourceTerrainZ}).Count){$category='inconclusive-source-domain'}
    elseif($falling.Count -and ($unfinishedFall -or @($landings | Where-Object {$_.t -gt $falling[0].t -and $_.feetZ -lt -989.594}).Count)){$category='falls-off-or-through'}
    elseif($penetration.Count){$category='enters-beneath-high-terrain'}
    elseif($edgeBlocks.Count -ge 2 -and $neverCrossed -and $groundedOnDeck){$category='blocked-retaining-edge'}
    elseif($actualReach -and $nearTarget -and $finalOnHighFloor -and $sustainedHigh){$category='unexpected-climb'}
    elseif($sweeps.Count){$category='inconclusive-or-other-obstruction'}
    return [ordered]@{category=$category;blockingFaceXcm=$FaceX;initialFloorValidated=[bool]$initialOK;traversalAccepted=$false;perimeterSafetyAccepted=$false;firstGrounded=$firstGround;initialLanding=$firstLanding;start=$starts[0];done=$done[0];actualWaypointReach=$actualReach;actualFinalSample=$last;nativeFinalState=$final;landingsAfterLastSample=$landedAfterLastSample;unfinishedFall=$unfinishedFall;penetrationSampleCount=$penetration.Count;blockingEdgeSweepCount=$edgeBlocks.Count;minimumObservedFeetZ=[Math]::Min([double]($samples.feetZ|Measure-Object -Minimum).Minimum,$final.feetZ);samples=$samples;landings=$landings;capsuleSweeps=$sweeps;reachedEvents=$reaches;rawEvents=$lines;limitations='Sampled trajectory and stuck-triggered 150cm capsule sweeps. Done reached counter can advance after four stuck events and is never used as reach proof. Initial guard is before steering; no rendered or perimeter-wide acceptance.'}
}
if($SelfTest){
    $head="MIKDASH_WALKPROBE start label=KotelEdgeOut capsule=34.0/96.0 state=MODERN enclosure[test]`nMIKDASH_WALKPROBE landed label=KotelEdgeOut t=0.1 dropCm=7.8 feetZ=-982.4 comp=Deck owner=DeckActor mesh=SM_PlazaV1_DeckTile tags=-`nMIKDASH_WALKPROBE sample label=KotelEdgeOut t=0.5 pos=-22187.9,19383.6,-886.4 feetZ=-982.4 velZ=0 mode=1 grounded=1 comp=Deck owner=DeckActor mesh=SM_PlazaV1_DeckTile tags=-`n"
    $stationary="MIKDASH_WALKPROBE sample label=KotelEdgeOut t=2.0 pos=-22453.9,19383.6,-886.4 feetZ=-982.4 velZ=0 mode=1 grounded=1 comp=Deck owner=DeckActor mesh=SM_PlazaV1_DeckTile tags=-`n"
    $sweep="MIKDASH_WALKPROBE stuck label=KotelEdgeOut t=3.0 blocking=1 at=X=-22487.940 Y=19383.625 Z=-886.400 normal=X=1.000 Y=0.000 Z=0.000 comp=Terrain owner=TerrainActor mesh=V3Terrain tags=-`n"
    $done='MIKDASH_WALKPROBE done label=KotelEdgeOut t=3.5 reached=1/1 finalPos=X=-22453.900 Y=19383.600 Z=-886.400 finalFeetZ=-982.4 grounded=1 comp=Deck owner=DeckActor mesh=SM_PlazaV1_DeckTile tags=-'
    $blocked=Read-EdgeObservation ($head+$stationary+$sweep+$sweep+$done)
    if($blocked.category -ne 'blocked-retaining-edge' -or $blocked.actualWaypointReach -or $blocked.traversalAccepted){throw 'Blocked/done-counter test failed'}
    $below="MIKDASH_WALKPROBE sample label=KotelEdgeOut t=2.0 pos=-22550,19383.6,-886.4 feetZ=-982.4 velZ=0 mode=1 grounded=1 comp=Lower owner=LowerActor mesh=LowerFloor tags=-`n"
    if((Read-EdgeObservation ($head+$below+$done)).category -ne 'enters-beneath-high-terrain'){throw 'Penetration test failed'}
    $fall=$below.Replace('velZ=0 mode=1 grounded=1','velZ=-200 mode=3 grounded=0')
    $fallDone=$done.Replace('grounded=1','grounded=0').Replace('X=-22453.900','X=-22550.000')
    if((Read-EdgeObservation ($head+$fall+$fallDone)).category -ne 'falls-off-or-through'){throw 'Unfinished fall test failed'}
    $lateLanding="MIKDASH_WALKPROBE landed label=KotelEdgeOut t=2.2 dropCm=5 feetZ=-982.4 comp=Lower owner=LowerActor mesh=LowerFloor tags=-`n"
    $reconciled=Read-EdgeObservation ($head+$fall+$lateLanding+$done.Replace('X=-22453.900','X=-22550.000'))
    if($reconciled.unfinishedFall -or $reconciled.category -eq 'falls-off-or-through' -or $reconciled.nativeFinalState.grounded -ne 1 -or $reconciled.landingsAfterLastSample.Count -ne 1){throw 'Late landing must override stale final falling sample'}
    $groundedDoneOnly=Read-EdgeObservation ($head+$fall+$done.Replace('X=-22453.900','X=-22550.000'))
    if($groundedDoneOnly.unfinishedFall){throw 'Actual grounded done must override stale sample even if landing event missing'}
    if((Read-EdgeObservation ($head.Replace('SM_PlazaV1_DeckTile','PrecinctCut')+$below+$done)).initialFloorValidated){throw 'Wrong initial-floor test failed'}
    if([Math]::Abs((Source-TerrainZ -22787.94 19308.62484)-(Source-TerrainZ -22787.94 19458.62484)) -gt 0.000001){throw 'Source plane must have zero Y gradient across validated lane'}
    if($null -ne (Source-TerrainZ -25000 19383.62484) -or (Read-EdgeObservation ($head+$below.Replace('pos=-22550,','pos=-25000,')+$done)).category -ne 'inconclusive-source-domain'){throw 'Source plane extrapolation must be refused'}
    $dynamicSweep=$sweep.Replace('comp=Terrain owner=TerrainActor mesh=V3Terrain tags=-','comp=DynamicMeshComponent_1 owner=MikdashEnclosure_0 mesh=- tags=KotelClosureRuntimeV1+')
    $dynamicBlock=Read-EdgeObservation ($head+$stationary+$dynamicSweep+$dynamicSweep+$done) 'DynamicMeshComponent_1' 'MikdashEnclosure_0'
    if($dynamicBlock.category -ne 'blocked-retaining-edge' -or $dynamicBlock.blockingEdgeSweepCount -ne 2){throw 'Known dynamic closure blocker must be identified without a StaticMesh name'}
    $unknownDynamic=Read-EdgeObservation ($head+$stationary+$dynamicSweep+$dynamicSweep+$done) 'DifferentComponent' 'MikdashEnclosure_0'
    if($unknownDynamic.category -eq 'blocked-retaining-edge' -or $unknownDynamic.blockingEdgeSweepCount -ne 0){throw 'Tagged but unmatched dynamic component must not count as known closure'}
    # The V2 wall blocks on the deck, inside the cut boundary: the face position must come from
    # the caller, and an impact on it must NOT be accepted against the old boundary constant.
    $sweepV2=$sweep.Replace('X=-22487.940','X=-22439.850')
    $stationaryV2=$stationary.Replace('pos=-22453.9,','pos=-22420.0,')
    $doneV2=$done.Replace('X=-22453.900','X=-22420.000')
    $v2=Read-EdgeObservation ($head+$stationaryV2+$sweepV2+$sweepV2+$doneV2) '' '' -22439.85
    if($v2.category -ne 'blocked-retaining-edge' -or $v2.blockingFaceXcm -ne -22439.85){throw 'V2 face block test failed'}
    if((Read-EdgeObservation ($head+$stationaryV2+$sweepV2+$sweepV2+$doneV2)).blockingEdgeSweepCount -ne 0){
        throw 'A V2-face impact must not be accepted against the old cut-boundary constant'}
    'PASS: 12 offline edge outcome tests; no native launched.';return
}
$project=Split-Path $PSScriptRoot -Parent
$edgeSpec='label=KotelEdgeOut;state=MODERN;start=-22187.94:19383.62484:-878.594:180:0;wp=-22787.94:19383.62484;delay=10;timeout=12'
# NullRHI physics replay only: the prior 172339339Z run peaked at 0.970 GiB.
# The opt-in lowers the private cap by 6 GiB and raises the system reserve by
# 1.5 GiB. It leaves a 0.5 GiB initial cushion; no GPU/full-cook guard changes.
$limits=[ordered]@{name='default';initialBytes=[long](9GB);maximumBytes=[long](8.5GB);reserveBytes=[long](2GB)}
if($Constrained){$limits=[ordered]@{name='constrained-nullrhi-physics';initialBytes=[long](6.5GB);maximumBytes=[long](2.5GB);reserveBytes=[long](3.5GB)}}
if($PlanOnly){
    [ordered]@{nativeLaunched=$false;nullRHI=$true;expectedCollisionMode=$ExpectedCollisionMode;probeSpec=$edgeSpec;archive=$Archive;expectedChildSha256=$ExpectedChildSha256;memoryProfile=$limits.name;initialFreeCommitGiB=($limits.initialBytes/1GB);maximumPrivateGiB=($limits.maximumBytes/1GB);reserveGiB=($limits.reserveBytes/1GB);timeoutSeconds=$TimeoutSeconds;normalExitClaimed=$false}|ConvertTo-Json
    return
}
if(!$Archive -or !$ExpectedChildSha256){throw 'Archive and ExpectedChildSha256 are required for a native edge observation'}
$root=Join-Path $Archive 'Windows'
$exe=Join-Path $root 'MikdashCourtyardV3/Binaries/Win64/MikdashCourtyardV3.exe'
$hash=(Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant()
if($hash -ne $ExpectedChildSha256.ToLowerInvariant()){throw 'Unexpected child executable'}
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3 -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'"|Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
$free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
if($free -lt $limits.initialBytes){throw ('Less than {0} GiB free commit ({1})' -f ($limits.initialBytes/1GB),$limits.name)}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$review=Join-Path $project 'SourceAssets/context-review/KotelCutClosureV1'
$edgePlan=Join-Path $review 'edge-walk-plan.md'
if(!(Test-Path -LiteralPath $edgePlan)){throw 'Missing reviewed edge-walk plan'}
New-Item -ItemType Directory -Path $review -Force | Out-Null
$output=Join-Path $review "edge-$stamp.json"
$log=Join-Path $review "edge-$stamp.log"
function Map-Hashes {
    $result=[ordered]@{}
    Get-ChildItem -LiteralPath (Join-Path $project 'Content') -Filter '*.umap' -Recurse -File | Sort-Object FullName | ForEach-Object {
        $result[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }
    return $result
}
$r=[ordered]@{status='starting';expectedCollisionMode=$ExpectedCollisionMode;edgePlanSha256=(Get-FileHash -LiteralPath $edgePlan).Hash.ToLowerInvariant();archive=$Archive;childSha256=$hash;closureDisabled=[bool]$DisableClosure;startedUtc=(Get-Date).ToUniversalTime().ToString('o');scope='Observed NullRHI edge physics only; no traversal/safety/rendered acceptance or normal-exit claim';memoryProfile=$limits.name;initialRequiredFreeCommitBytes=$limits.initialBytes;initialFreeCommitBytes=$free;maximumPrivateBytes=$limits.maximumBytes;reserveBytes=$limits.reserveBytes;normalExitClaimed=$false;peakPrivateBytes=[long]0;minimumFreeCommitBytes=$free;mapHashesBefore=(Map-Hashes)}
function Save-Receipt {$r|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $output -Encoding utf8}
function Read-InitialClosure([string]$LogText,[string]$marker='KotelClosureRuntimeV1 initial readback ') {
    $start=$LogText.IndexOf($marker,[StringComparison]::Ordinal)
    if($start -lt 0 -or $LogText.IndexOf($marker,$start+$marker.Length,[StringComparison]::Ordinal) -ge 0){throw 'Expected one initial native closure guard readback'}
    $start=$LogText.IndexOf('{',$start+$marker.Length)
    if($start -lt 0){throw 'Initial readback JSON is missing'}
    # Unreal's default JSON writer is pretty-printed. Find the matching object
    # boundary while respecting quoted braces and escaped quotes; do not use a
    # greedy regex that can consume a later diagnostic object.
    $depth=0;$quoted=$false;$escaped=$false
    for($i=$start;$i -lt $LogText.Length;$i++){
        $ch=$LogText[$i]
        if($quoted){
            if($escaped){$escaped=$false}
            elseif($ch -eq '\'){$escaped=$true}
            elseif($ch -eq '"'){$quoted=$false}
            continue
        }
        if($ch -eq '"'){$quoted=$true}
        elseif($ch -eq '{'){$depth++}
        elseif($ch -eq '}'){
            $depth--
            if($depth -eq 0){return ($LogText.Substring($start,$i-$start+1)|ConvertFrom-Json)}
        }
    }
    throw 'Initial readback JSON is incomplete'
}
$label='KotelEdgeOut'
$spec=$edgeSpec
$launchArgs=@('-nullrhi','-unattended','-nosound','-nosplash','-MikdashKotelClosureDiagnostic',('-abslog="'+$log+'"'),('-MikdashWalkProbe="'+$spec+'"'),('-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=KotelEdge_'+$stamp+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=KotelEdge_'+$stamp))
if($DisableClosure){$launchArgs+='-MikdashDisableKotelClosure'}
$r.arguments=$launchArgs;Save-Receipt
$proc=$null
try {
    $proc=Start-Process -FilePath $exe -ArgumentList $launchArgs -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $r.pid=$proc.Id;$r.status='running';Save-Receipt
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    $text=''
    while((Get-Date) -lt $deadline){
        Start-Sleep -Seconds 2;$proc.Refresh()
        if(Test-Path -LiteralPath $log){$text=Get-Content -LiteralPath $log -Raw}
        if($text -match 'MIKDASH_WALKPROBE done label=KotelEdgeOut '){break}
        if($proc.HasExited){throw 'Game exited before completed walk receipt'}
        $private=[long]$proc.PrivateMemorySize64
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $r.peakPrivateBytes=[Math]::Max([long]$r.peakPrivateBytes,$private)
        $r.minimumFreeCommitBytes=[Math]::Min([long]$r.minimumFreeCommitBytes,$free)
        if($private -gt $limits.maximumBytes -or $free -lt $limits.reserveBytes){throw ('Owned NullRHI walk probe reached memory bound ({0} GiB private / {1} GiB reserve; {2})' -f ($limits.maximumBytes/1GB),($limits.reserveBytes/1GB),$limits.name)}
    }
    $done=@($text -split '\r?\n'|Where-Object {$_ -match 'MIKDASH_WALKPROBE done label=KotelEdgeOut '})
    $reached=@([regex]::Matches($text,'MIKDASH_WALKPROBE reached label=KotelEdgeOut wp=(\d+) ')|ForEach-Object {$_.Groups[1].Value})
    $r.completedLines=$done;$r.reachedWaypoints=$reached
    $r.probeLines=@($text -split '\r?\n'|Where-Object {$_ -match 'MIKDASH_WALKPROBE|KotelClosureRuntimeV1'})
    $r.initialClosureReadback=Read-InitialClosure $text
    if(!$r.initialClosureReadback.passed -or $null -eq $r.initialClosureReadback.disabled -or [bool]$r.initialClosureReadback.disabled -ne [bool]$DisableClosure){throw 'Closure guard refused or control mode mismatched; edge observation cannot identify requested configuration'}
    if($done.Count -ne 1){throw 'Missing unique native diagnostic completion'}
    if($text -match 'KotelClosureRuntimeV1 guard:'){throw 'Native closure repair refused a guard; observation cannot certify this mode'}
    $closureComponent='';$closureActor=''
    if($ExpectedCollisionMode -eq 'VisualOnly'){
        if($r.initialClosureReadback.PSObject.Properties['collisionPolicy'] -and $r.initialClosureReadback.collisionPolicy -eq 'pawn-only-query-v1'){throw 'Pawn-blocking binary does not match explicit visual-only expectation'}
        if(!$DisableClosure -and ($r.initialClosureReadback.closure.collisionMode -ne 0 -or $r.initialClosureReadback.closure.configuredCollisionMode -ne 0)){throw 'Visual-only closure unexpectedly has collision'}
    } else {
        if(!$r.initialClosureReadback.PSObject.Properties['collisionPolicy'] -or $r.initialClosureReadback.collisionPolicy -ne 'pawn-only-query-v1'){throw 'Missing requested pawn-blocking native collision policy'}
        if(!$DisableClosure){
            $r.collisionStateReadback=Read-InitialClosure $text 'KotelClosureRuntimeV1 collision state readback '
            $active=$r.collisionStateReadback
            $body=$active.closure
            if(!$active.passed -or $active.status -ne 'active-visible' -or !$active.terrain.actualVisible -or !$active.terrain.actorCollisionEnabled -or !$active.deck.actualVisible -or !$active.deck.actorCollisionEnabled){throw 'Actual Modern closure/source state was not ready'}
            if($body.class -ne '/Script/GeometryFramework.DynamicMeshComponent' -or !$body.actualVisible -or $body.collisionMode -ne 1 -or $body.configuredCollisionMode -ne 1 -or !$body.physicsDataReady -or !$body.physicsMeshesCreated -or $body.physicsMeshCreationFailed -or $body.chaosTriangleMeshCount -lt 1 -or !$body.doubleSidedPhysics -or !$body.pawnOnlyResponses -or $body.pawnResponse -ne 2 -or !$body.physicsStateCreated -or !$body.bodyInstanceValid){throw 'Actual pawn-blocking Chaos body/readback failed'}
            $closureComponent=$body.componentName;$closureActor=$body.actorName
            if(!$closureComponent -or !$closureActor){throw 'Missing exact dynamic blocker identity'}
        }
    }
    # The blocking face position comes from the generated wall, never from an assumption.
    $wallPath=Join-Path $project 'SourceAssets/context-review/KotelViewsV1/retaining-wall-v2.json'
    if(!(Test-Path -LiteralPath $wallPath)){throw 'Missing retaining-wall-v2.json; cannot locate the blocking face'}
    $lane=(Get-Content -LiteralPath $wallPath -Raw | ConvertFrom-Json).probeLane
    if([Math]::Abs([double]$lane.yCm - 19383.62484) -gt 0.001){throw 'Generated probe lane Y differs from the reviewed edge-walk lane'}
    $r.wallFaceXcm=[double]$lane.footingFrontXcm
    $r.wallFaceSource='retaining-wall-v2.json probeLane.footingFrontXcm'
    $r.observation=Read-EdgeObservation $text $closureComponent $closureActor ([double]$lane.footingFrontXcm)
    if($text -match 'Fatal error:|Ran out of memory|Assertion failed:'){throw 'Fatal native error in log'}
    $r.status=if($r.observation.initialFloorValidated){'observed-native-edge-outcome'}else{'inconclusive-initial-floor'}
} catch {$r.status='failed';$r.error=$_.Exception.Message}
finally {
    if($proc){$proc.Refresh();if(!$proc.HasExited){
        $live=Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
        if($live -and $live.Path -eq $exe){$live|Stop-Process -Force;$r.stoppedOwnedChild=$true}
    }}
    $r.mapHashesAfter=Map-Hashes
    $r.mapsUnchanged=(($r.mapHashesBefore|ConvertTo-Json -Compress) -eq ($r.mapHashesAfter|ConvertTo-Json -Compress))
    if(!$r.mapsUnchanged){$r.status='failed';$r.error='Source map set or bytes changed'}
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o');Save-Receipt
}
[pscustomobject]@{status=$r.status;receipt=$output;log=$log;error=$r.error}|ConvertTo-Json
if($r.status -eq 'failed'){exit 1}
if($r.status -eq 'inconclusive-initial-floor'){exit 2}
