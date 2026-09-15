<# Guarded native state and rendered-frame probe in an isolated playable archive.
   Uses the game's explicit diagnostic, never UI input. No cook or source map save.
#>
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedChildSha256,
    [switch]$DisableClosure,
    [switch]$Constrained,
    [ValidatePattern('\A-?[0-9]+(?:\.[0-9]+)?(?: -?[0-9]+(?:\.[0-9]+)?){5}\z')]
    [string]$CameraBugItGo='-20732 19230 -814 6 175 0',
    [ValidateRange(120,360)][int]$TimeoutSeconds=240
)
$ErrorActionPreference='Stop'
$minimumStart=if($Constrained){8.75GB}else{9GB}
$maximumPrivate=if($Constrained){7GB}else{8GB}
$reserve=if($Constrained){1.5GB}else{1.25GB}
$width=if($Constrained){960}else{1280}
$height=if($Constrained){540}else{720}
$project=Split-Path $PSScriptRoot -Parent
$root=Join-Path $Archive 'Windows'
$exe=Join-Path $root 'MikdashCourtyardV3/Binaries/Win64/MikdashCourtyardV3.exe'
if (!(Test-Path -LiteralPath $exe)) { throw "Missing game child: $exe" }
$hash=(Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant()
if($hash -ne $ExpectedChildSha256.ToLowerInvariant()){throw 'Unexpected game child hash'}
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3 -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied; nothing launched'}
$os=Get-CimInstance Win32_OperatingSystem
$headroom=[long]$os.FreeVirtualMemory*1KB
if($headroom -lt $minimumStart){throw "Less than $($minimumStart/1GB) GiB free commit; nothing launched"}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$review=Join-Path $project 'SourceAssets/context-review/KotelCutClosureV1'
$diag=Join-Path $root 'MikdashCourtyardV3/Saved/Diagnostics'
$receipt=Join-Path $review "runtime-$stamp.json"
$log=Join-Path $review "runtime-$stamp.log"
New-Item -ItemType Directory -Path $review -Force | Out-Null
$prior=@(Get-ChildItem -LiteralPath $diag -Filter 'KotelClosureRuntimeV1-*.json' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
function Map-Hashes {
    $result=[ordered]@{}
    Get-ChildItem -LiteralPath (Join-Path $project 'Content') -Filter '*.umap' -Recurse -File | Sort-Object FullName | ForEach-Object {
        $result[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }
    return $result
}
$r=[ordered]@{
    status='starting';startedUtc=(Get-Date).ToUniversalTime().ToString('o')
    archive=$Archive;childSha256=$hash;closureDisabled=[bool]$DisableClosure;requestedCamera=$CameraBugItGo
    scope='Tests the specified archive contents and runtime without cooking. High/77% capture at the recorded viewport; native state checks and visual acceptance separate. Caller must identify any mounted asset patches.'
    constrained=[bool]$Constrained;viewport=@($width,$height);initialRequiredFreeCommitBytes=$minimumStart
    mapHashesBefore=(Map-Hashes);initialFreeCommitBytes=$headroom
    peakPrivateBytes=[long]0;minimumFreeCommitBytes=$headroom
    reserveBytes=[long]$reserve;maximumPrivateBytes=[long]$maximumPrivate
}
function Save-Receipt {$r | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $receipt -Encoding utf8}
$launchArgs=@('-unattended','-nosound','-nosplash','-windowed',('-ResX='+$width),('-ResY='+$height),
    '-MikdashKotelClosureDiagnostic','-MikdashKotelClosureProbe',('-abslog="'+$log+'"'),
    ('-ExecCmds="sg.ViewDistanceQuality 2,sg.ShadowQuality 2,sg.GlobalIlluminationQuality 2,sg.ReflectionQuality 2,sg.PostProcessQuality 2,sg.TextureQuality 2,sg.EffectsQuality 2,sg.FoliageQuality 2,sg.ShadingQuality 2,r.ScreenPercentage 77,r.SetRes '+$width+'x'+$height+'w,Ghost,BugItGo '+$CameraBugItGo+'"'),
    ('-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashPhotoMode]:LeashRadiusCm=900000,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=KotelProbe_'+$stamp+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=KotelProbe_'+$stamp+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False'))
if($DisableClosure){$launchArgs+='-MikdashDisableKotelClosure'}
if($Constrained){$launchArgs+='-NoAsyncLoadingThread'}
$r.arguments=$launchArgs
Save-Receipt
$proc=$null
try {
    $proc=Start-Process -FilePath $exe -ArgumentList $launchArgs -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $r.pid=$proc.Id;$r.status='running';Save-Receipt
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    while((Get-Date) -lt $deadline){
        Start-Sleep -Seconds 2
        $proc.Refresh()
        if($proc.HasExited){break}
        $private=[long]$proc.PrivateMemorySize64
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $r.peakPrivateBytes=[Math]::Max([long]$r.peakPrivateBytes,$private)
        $r.minimumFreeCommitBytes=[Math]::Min([long]$r.minimumFreeCommitBytes,$free)
        # At the enforced 1280x720 viewport, native startup measured 7.33 GiB
        # private with 1.78 GiB still free. The old 2 GiB guard aborted that
        # healthy startup (no OOM). Keep a 1.25 GiB system reserve and a tighter
        # 8 GiB child ceiling; this does not change the full-cook/Entry guards.
        if($private -gt $r.maximumPrivateBytes -or $free -lt $r.reserveBytes){throw 'Owned game reached memory reserve; aborting this probe'}
    }
    if(!$proc.HasExited){throw 'Native Kotel probe timed out'}
    $proc.WaitForExit();$r.exitCode=$proc.ExitCode
    if($proc.ExitCode -ne 0){throw "Native probe exited $($proc.ExitCode)"}
    $fresh=@(Get-ChildItem -LiteralPath $diag -Filter 'KotelClosureRuntimeV1-*.json' -ErrorAction SilentlyContinue | Where-Object {$prior -notcontains $_.FullName})
    if($fresh.Count -ne 1){throw "Expected one fresh native receipt; got $($fresh.Count)"}
    $native=Get-Content -LiteralPath $fresh[0].FullName -Raw | ConvertFrom-Json
    Copy-Item -LiteralPath $fresh[0].FullName -Destination (Join-Path $review $fresh[0].Name)
    $r.nativeReceipt=$fresh[0].Name;$r.native=$native
    $r.photos=@()
    foreach($state in $native.states){
        $photoPath=$state.photoPath
        if(!$photoPath -or !(Test-Path -LiteralPath $photoPath)){continue}
        $destination=Join-Path $review ("runtime-$stamp-phase"+$r.photos.Count+'.png')
        Copy-Item -LiteralPath $photoPath -Destination $destination
        $r.photos+=@{file=(Split-Path $destination -Leaf);sha256=(Get-FileHash -LiteralPath $destination).Hash.ToLowerInvariant();source=$photoPath}
    }
    if(!$native.passed -or $native.states.Count -ne 4){throw 'Native guards, state readback or four-phase probe failed'}
    if($null -eq $native.disabled -or [bool]$native.disabled -ne [bool]$DisableClosure){throw 'Native control mode differs from requested closure mode'}
    if(($native.states.state -join ',') -ne 'Modern,Yechezkel,Overlay,Modern-again'){throw 'Native phase order differs from required round trip'}
    if(!$native.finalReadback.passed -or @($native.states | Where-Object {!$_.passed}).Count){throw 'Individual native phase or final readback failed'}
    if($r.photos.Count -ne 4){throw 'A native phase photo is missing'}
    $r.status='native-state-passed-visual-review-pending'
} catch {$r.status='failed';$r.error=$_.Exception.Message}
finally {
    if($proc){
        $proc.Refresh()
        if(!$proc.HasExited){
            $live=Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
            if($live -and $live.Path -eq $exe){$live | Stop-Process -Force;$r.stoppedOwnedChild=$true}
        }
    }
    $r.mapHashesAfter=Map-Hashes
    $r.mapsUnchanged=(($r.mapHashesBefore|ConvertTo-Json -Compress) -eq ($r.mapHashesAfter|ConvertTo-Json -Compress))
    if(!$r.mapsUnchanged){$r.status='failed';$r.error='Source map set or bytes changed'}
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o');Save-Receipt
}
[pscustomobject]@{status=$r.status;receipt=$receipt;log=$log;error=$r.error}|ConvertTo-Json
if($r.status -eq 'failed'){exit 1}
