<# Walks a mapped Haram gate flight in a fresh packaged process.
   The existing walker diagnostic has no exit command. This wrapper stops only its
   owned child AFTER copying its completed logs; that is not reported as normal exit.
#>
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedChildSha256,
    [Parameter(Mandatory=$true)][long]$GateId,
    [switch]$Constrained,
    [switch]$SourcePreview,
    [switch]$PlanOnly,
    [ValidateRange(60,180)][int]$TimeoutSeconds=90
)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
# NullRHI physics replay only: the prior 172339339Z run peaked at 0.970 GiB.
# The opt-in lowers the private cap by 6 GiB and raises the system reserve by
# 1.5 GiB. It leaves a 0.5 GiB initial cushion; no GPU/full-cook guard changes.
$limits=[ordered]@{name='default';initialBytes=[long](9GB);maximumBytes=[long](8.5GB);reserveBytes=[long](2GB)}
if($Constrained){$limits=[ordered]@{name='constrained-nullrhi-physics';initialBytes=[long](6.5GB);maximumBytes=[long](2.5GB);reserveBytes=[long](3.5GB)}}
if($SourcePreview){$limits=[ordered]@{name='source-editor-nullrhi';initialBytes=[long](20GB);maximumBytes=[long](16GB);reserveBytes=[long](4GB)}}
if($PlanOnly){
    [ordered]@{nativeLaunched=$false;nullRHI=$true;archive=$Archive;expectedChildSha256=$ExpectedChildSha256;memoryProfile=$limits.name;initialFreeCommitGiB=($limits.initialBytes/1GB);maximumPrivateGiB=($limits.maximumBytes/1GB);reserveGiB=($limits.reserveBytes/1GB);timeoutSeconds=$TimeoutSeconds;normalExitClaimed=$false}|ConvertTo-Json
    return
}
$root=Join-Path $Archive 'Windows'
$exe=Join-Path $root 'MikdashCourtyardV3/Binaries/Win64/MikdashCourtyardV3.exe'
if($SourcePreview){$root=$project;$exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'}
$exe=(Resolve-Path -LiteralPath $exe).Path
$hash=(Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant()
if($hash -ne $ExpectedChildSha256.ToLowerInvariant()){throw 'Unexpected child executable'}
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3 -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'"|Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
$free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
if($free -lt $limits.initialBytes){throw ('Less than {0} GiB free commit ({1})' -f ($limits.initialBytes/1GB),$limits.name)}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$review=Join-Path $project 'SourceAssets/enclosure-review/HaramPrecinctV1'
New-Item -ItemType Directory -Path $review -Force | Out-Null
$output=Join-Path $review "stair-$stamp.json"
$log=Join-Path $review "stair-$stamp.log"
function Map-Hashes {
    $result=[ordered]@{}
    Get-ChildItem -LiteralPath (Join-Path $project 'Content') -Filter '*.umap' -Recurse -File | Sort-Object FullName | ForEach-Object {
        $result[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }
    return $result
}
$r=[ordered]@{status='starting';archive=$Archive;childSha256=$hash;gateId=$GateId;startedUtc=(Get-Date).ToUniversalTime().ToString('o');scope='Native NullRHI character movement replay; no rendered acceptance or normal-exit claim';memoryProfile=$limits.name;initialRequiredFreeCommitBytes=$limits.initialBytes;initialFreeCommitBytes=$free;maximumPrivateBytes=$limits.maximumBytes;reserveBytes=$limits.reserveBytes;normalExitClaimed=$false;peakPrivateBytes=[long]0;minimumFreeCommitBytes=$free;mapHashesBefore=(Map-Hashes)}
function Save-Receipt {$r|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $output -Encoding utf8}
function Read-InitialClosure([string]$LogText) {
    $marker='KotelClosureRuntimeV1 initial readback '
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
$plan=Get-Content (Join-Path $review 'plan.json') -Raw | ConvertFrom-Json
$gate=@($plan.gates | Where-Object {$_.osmId -eq $GateId})
if($gate.Count -ne 1){throw 'Gate ID must identify one planned entry'}
$gate=$gate[0]
$label='HaramAccess'+$GateId
function Gate-Point([double]$distance) {
    return @(([double]$gate.positionCm[0]+[double]$gate.inward[0]*$distance),([double]$gate.positionCm[1]+[double]$gate.inward[1]*$distance))
}
function Number([double]$value) {return $value.ToString('F3',[Globalization.CultureInfo]::InvariantCulture)}
# Start outside the mapped boundary, cross the apron and full flight, then settle on paving.
$start=Gate-Point -100
$yaw=[Math]::Atan2([double]$gate.inward[1],[double]$gate.inward[0])*180/[Math]::PI
$points=@(([double]$gate.runCm/2),([double]$gate.runCm-90),([double]$gate.runCm+150)) | ForEach-Object {
    $point=Gate-Point $_
    (Number $point[0])+':'+(Number $point[1])
}
$spec='label='+$label+';state=YECHEZKEL;start='+(Number $start[0])+':'+(Number $start[1])+':'+(Number ([double]$gate.thresholdZCm+160))+':'+(Number $yaw)+':-8;wp='+($points -join '/')+';delay=10;timeout=40'
$r.gate=$gate
$launchArgs=@('-nullrhi','-unattended','-nosound','-nosplash','-MikdashKotelClosureDiagnostic',('-abslog="'+$log+'"'),('-MikdashWalkProbe="'+$spec+'"'),('-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=KotelStair_'+$stamp+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=KotelStair_'+$stamp))
if($SourcePreview){
    $launchArgs=@(('"'+(Join-Path $project 'MikdashCourtyardV3.uproject')+'"'),'/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough','-game','-asyncstaticmeshcompilationmaxconcurrency=1')+$launchArgs
    $r.scope='Editor game runtime physics replay with current source map; NOT packaged acceptance or a normal-exit claim.'
    $r.runtimePluginSha256=(Get-FileHash -LiteralPath (Join-Path $project 'Plugins/MikdashRuntime/Binaries/Win64/UnrealEditor-MikdashRuntime.dll')).Hash.ToLowerInvariant()
}
$r.sourcePreview=[bool]$SourcePreview
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
        if($text -match ('MIKDASH_WALKPROBE done label='+$label+' ')){break}
        if($proc.HasExited){throw 'Game exited before completed walk receipt'}
        $private=[long]$proc.PrivateMemorySize64
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $r.peakPrivateBytes=[Math]::Max([long]$r.peakPrivateBytes,$private)
        $r.minimumFreeCommitBytes=[Math]::Min([long]$r.minimumFreeCommitBytes,$free)
        if($private -gt $limits.maximumBytes -or $free -lt $limits.reserveBytes){throw ('Owned NullRHI walk probe reached memory bound ({0} GiB private / {1} GiB reserve; {2})' -f ($limits.maximumBytes/1GB),($limits.reserveBytes/1GB),$limits.name)}
    }
    $done=@($text -split '\r?\n'|Where-Object {$_ -match ('MIKDASH_WALKPROBE done label='+$label+' ')})
    $reached=@([regex]::Matches($text,('MIKDASH_WALKPROBE reached label='+$label+' wp=(\d+) '))|ForEach-Object {$_.Groups[1].Value})
    $r.completedLines=$done;$r.reachedWaypoints=$reached
    $r.probeLines=@($text -split '\r?\n'|Where-Object {$_ -match 'MIKDASH_WALKPROBE|KotelClosureRuntimeV1'})
    $r.initialClosureReadback=Read-InitialClosure $text
    if(!$r.initialClosureReadback.haramPrecinct.enabled){throw 'Archive does not have the Haram precinct enabled'}
    if(!$r.initialClosureReadback.passed -or $null -eq $r.initialClosureReadback.disabled -or [bool]$r.initialClosureReadback.disabled){throw 'Closure guard refused or control mode mismatched; stair run cannot certify requested configuration'}
    if($done.Count -ne 1 -or ($reached -join ',') -ne '0,1,2'){throw 'Missing real waypoint reach events or final completion'}
    if($done[0] -notmatch 'stuckEvents=0 grounded=1' -or $done[0] -notmatch 'mesh=SM_Haram_Deck_'){throw 'Stair climb stuck, ungrounded, or ended on wrong floor'}
    $feet=[regex]::Match($done[0],'finalFeetZ=([-\d.]+)')
    if(!$feet.Success -or [Math]::Abs([double]::Parse($feet.Groups[1].Value,[Globalization.CultureInfo]::InvariantCulture)-0.5) -gt 3){throw 'Stair endpoint height differs from verified upper deck'}
    if($text -match 'Fatal error:|Ran out of memory|Assertion failed:'){throw 'Fatal native error in log'}
    $r.status='passed-native-haram-gate-route'
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
