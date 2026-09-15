<# Replays the already-proven cp22e Kotel stair route in a fresh packaged process.
   The existing walker diagnostic has no exit command. This wrapper stops only its
   owned child AFTER copying its completed logs; that is not reported as normal exit.
#>
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedChildSha256,
    [switch]$DisableClosure,
    [switch]$Constrained,
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
if($PlanOnly){
    [ordered]@{nativeLaunched=$false;nullRHI=$true;archive=$Archive;expectedChildSha256=$ExpectedChildSha256;memoryProfile=$limits.name;initialFreeCommitGiB=($limits.initialBytes/1GB);maximumPrivateGiB=($limits.maximumBytes/1GB);reserveGiB=($limits.reserveBytes/1GB);timeoutSeconds=$TimeoutSeconds;normalExitClaimed=$false}|ConvertTo-Json
    return
}
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
$r=[ordered]@{status='starting';archive=$Archive;childSha256=$hash;closureDisabled=[bool]$DisableClosure;startedUtc=(Get-Date).ToUniversalTime().ToString('o');scope='Native NullRHI character movement replay; no rendered acceptance or normal-exit claim';memoryProfile=$limits.name;initialRequiredFreeCommitBytes=$limits.initialBytes;initialFreeCommitBytes=$free;maximumPrivateBytes=$limits.maximumBytes;reserveBytes=$limits.reserveBytes;normalExitClaimed=$false;peakPrivateBytes=[long]0;minimumFreeCommitBytes=$free;mapHashesBefore=(Map-Hashes)}
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
$label='KotelClosureStair'
$spec='label='+$label+';state=MODERN;start=-17432.4:16006.8:-1110:175.49:-8;wp=-19027.4:16132.7/-20323.4:16235.0/-21000.0:16287.0;delay=10;timeout=40'
$launchArgs=@('-nullrhi','-unattended','-nosound','-nosplash','-MikdashKotelClosureDiagnostic',('-abslog="'+$log+'"'),('-MikdashWalkProbe="'+$spec+'"'),('-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=KotelStair_'+$stamp+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=KotelStair_'+$stamp))
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
        if($text -match 'MIKDASH_WALKPROBE done label=KotelClosureStair '){break}
        if($proc.HasExited){throw 'Game exited before completed walk receipt'}
        $private=[long]$proc.PrivateMemorySize64
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $r.peakPrivateBytes=[Math]::Max([long]$r.peakPrivateBytes,$private)
        $r.minimumFreeCommitBytes=[Math]::Min([long]$r.minimumFreeCommitBytes,$free)
        if($private -gt $limits.maximumBytes -or $free -lt $limits.reserveBytes){throw ('Owned NullRHI walk probe reached memory bound ({0} GiB private / {1} GiB reserve; {2})' -f ($limits.maximumBytes/1GB),($limits.reserveBytes/1GB),$limits.name)}
    }
    $done=@($text -split '\r?\n'|Where-Object {$_ -match 'MIKDASH_WALKPROBE done label=KotelClosureStair '})
    $reached=@([regex]::Matches($text,'MIKDASH_WALKPROBE reached label=KotelClosureStair wp=(\d+) ')|ForEach-Object {$_.Groups[1].Value})
    $r.completedLines=$done;$r.reachedWaypoints=$reached
    $r.probeLines=@($text -split '\r?\n'|Where-Object {$_ -match 'MIKDASH_WALKPROBE|KotelClosureRuntimeV1'})
    $r.initialClosureReadback=Read-InitialClosure $text
    if(!$r.initialClosureReadback.passed -or $null -eq $r.initialClosureReadback.disabled -or [bool]$r.initialClosureReadback.disabled -ne [bool]$DisableClosure){throw 'Closure guard refused or control mode mismatched; stair run cannot certify requested configuration'}
    if($done.Count -ne 1 -or ($reached -join ',') -ne '0,1,2'){throw 'Missing real waypoint reach events or final completion'}
    if($done[0] -notmatch 'stuckEvents=0 grounded=1' -or $done[0] -notmatch 'mesh=SM_PlazaV1_DeckTile'){throw 'Stair climb stuck, ungrounded, or ended on wrong floor'}
    $feet=[regex]::Match($done[0],'finalFeetZ=([-\d.]+)')
    if(!$feet.Success -or [Math]::Abs([double]::Parse($feet.Groups[1].Value,[Globalization.CultureInfo]::InvariantCulture)-(-982.4)) -gt 3){throw 'Stair endpoint height differs from verified upper deck'}
    if($text -match 'Fatal error:|Ran out of memory|Assertion failed:'){throw 'Fatal native error in log'}
    $r.status='passed-native-stair-route'
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
