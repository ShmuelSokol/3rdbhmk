<# Four-state native collision/readback probe. No rendered acceptance. #>
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedChildSha256,
    [switch]$DisableClosure,
    [switch]$PlanOnly,
    [ValidateRange(60,180)][int]$TimeoutSeconds=120
)
$ErrorActionPreference='Stop'
$limits=@{initial=[long](6.5GB);maximum=[long](2.5GB);reserve=[long](3.5GB)}
if($PlanOnly){[ordered]@{nativeLaunched=$false;nullRHI=$true;initialGiB=6.5;maximumPrivateGiB=2.5;reserveGiB=3.5;states=@('Modern','Yechezkel','Overlay','Modern-again')}|ConvertTo-Json;return}
$project=Split-Path $PSScriptRoot -Parent
$root=Join-Path $Archive 'Windows'
$exe=Join-Path $root 'MikdashCourtyardV3/Binaries/Win64/MikdashCourtyardV3.exe'
$hash=(Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant()
if($hash -ne $ExpectedChildSha256.ToLowerInvariant()){throw 'Unexpected game child hash'}
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3,UnrealPak -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'"|Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied; nothing launched'}
$free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
if($free -lt $limits.initial){throw 'Less than 6.5 GiB free commit; nothing launched'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$review=Join-Path $project 'SourceAssets/context-review/KotelCutClosureV1'
$diag=Join-Path $root 'MikdashCourtyardV3/Saved/Diagnostics'
$receipt=Join-Path $review "headless-states-$stamp.json"
$log=Join-Path $review "headless-states-$stamp.log"
if((Test-Path -LiteralPath $receipt) -or (Test-Path -LiteralPath $log)){throw 'Refusing to reuse diagnostic paths'}
$prior=@(Get-ChildItem -LiteralPath $diag -Filter 'KotelClosureRuntimeV1-*.json' -ErrorAction SilentlyContinue|Select-Object -ExpandProperty FullName)
function Map-Hashes {
    $out=[ordered]@{}
    Get-ChildItem -LiteralPath (Join-Path $project 'Content') -Filter '*.umap' -Recurse -File|Sort-Object FullName|ForEach-Object {$out[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant()}
    return $out
}
$r=[ordered]@{status='starting';startedUtc=(Get-Date).ToUniversalTime().ToString('o');archive=$Archive;childSha256=$hash;closureDisabled=[bool]$DisableClosure;scope='NullRHI four-state native identity, mesh, visibility and collision readbacks. No pixels or traversal-wide acceptance.';mapHashesBefore=(Map-Hashes);initialFreeCommitBytes=$free;initialRequiredFreeCommitBytes=$limits.initial;maximumPrivateBytes=$limits.maximum;reserveBytes=$limits.reserve;peakPrivateBytes=[long]0;minimumFreeCommitBytes=$free;normalExitClaimed=$false}
function Save-Receipt {$r|ConvertTo-Json -Depth 28|Set-Content -LiteralPath $receipt -Encoding utf8}
$launchArgs=@('-nullrhi','-unattended','-nosound','-nosplash','-MikdashKotelClosureDiagnostic','-MikdashKotelClosureProbe','-MikdashKotelClosureHeadless',('-abslog="'+$log+'"'),('-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=KotelHeadless_'+$stamp+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=KotelHeadless_'+$stamp))
if($DisableClosure){$launchArgs+='-MikdashDisableKotelClosure'}
$r.arguments=$launchArgs;Save-Receipt
$proc=$null
try {
    $proc=Start-Process -FilePath $exe -ArgumentList $launchArgs -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $r.pid=$proc.Id;$r.status='running';Save-Receipt
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    while((Get-Date) -lt $deadline){
        Start-Sleep -Seconds 2;$proc.Refresh()
        if($proc.HasExited){break}
        $private=[long]$proc.PrivateMemorySize64
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $r.peakPrivateBytes=[Math]::Max([long]$r.peakPrivateBytes,$private)
        $r.minimumFreeCommitBytes=[Math]::Min([long]$r.minimumFreeCommitBytes,$free)
        if($private -gt $limits.maximum -or $free -lt $limits.reserve){throw 'Owned headless probe reached memory bound'}
    }
    if(!$proc.HasExited){throw 'Headless probe timed out'}
    $proc.WaitForExit();$r.exitCode=$proc.ExitCode
    if($proc.ExitCode -ne 0){throw "Native probe exited $($proc.ExitCode)"}
    $fresh=@(Get-ChildItem -LiteralPath $diag -Filter 'KotelClosureRuntimeV1-*.json' -ErrorAction SilentlyContinue|Where-Object {$prior -notcontains $_.FullName})
    if($fresh.Count -ne 1){throw 'Expected one fresh native receipt'}
    $native=Get-Content -LiteralPath $fresh[0].FullName -Raw|ConvertFrom-Json
    Copy-Item -LiteralPath $fresh[0].FullName -Destination (Join-Path $review $fresh[0].Name)
    $r.nativeReceipt=$fresh[0].Name;$r.nativeReceiptSha256=(Get-FileHash -LiteralPath $fresh[0].FullName).Hash.ToLowerInvariant();$r.native=$native
    if(!$native.headless -or !$native.passed -or @($native.states).Count -ne 4 -or @($native.photoPaths).Count -ne 0){throw 'Expected successful headless four-state receipt without photos'}
    if($null -eq $native.disabled -or [bool]$native.disabled -ne [bool]$DisableClosure){throw 'Native control mode mismatch'}
    if(($native.states.state -join ',') -ne 'Modern,Yechezkel,Overlay,Modern-again'){throw 'Wrong native state order'}
    if(!$native.finalReadback.passed -or @($native.states|Where-Object {!$_.passed -or !$_.sourceStateVisibilityAndActorCollisionPassed}).Count){throw 'Individual native phase/final readback failed'}
    $text=Get-Content -LiteralPath $log -Raw
    if($text -match 'Fatal error:|Ran out of memory|Assertion failed:'){throw 'Fatal native error in log'}
    $r.normalExitClaimed=$true;$r.status='passed-native-headless-states'
} catch {$r.status='failed';$r.error=$_.Exception.Message}
finally {
    if($proc){$proc.Refresh();if(!$proc.HasExited){$live=Get-Process -Id $proc.Id -ErrorAction SilentlyContinue;if($live -and $live.Path -eq $exe){$live|Stop-Process -Force;$r.stoppedOwnedChild=$true}}}
    $r.mapHashesAfter=Map-Hashes
    $r.mapsUnchanged=(($r.mapHashesBefore|ConvertTo-Json -Compress) -eq ($r.mapHashesAfter|ConvertTo-Json -Compress))
    if(!$r.mapsUnchanged){$r.status='failed';$r.error='Source map set or bytes changed'}
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o');Save-Receipt
}
[ordered]@{status=$r.status;receipt=$receipt;error=$r.error}|ConvertTo-Json
if($r.status -ne 'passed-native-headless-states'){exit 1}
