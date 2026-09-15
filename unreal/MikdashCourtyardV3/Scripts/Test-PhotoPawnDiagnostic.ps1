<# Runs an opt-in native photo diagnostic in an isolated archive. No UI input or map save. #>
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedChildSha256,
    [ValidatePattern('^[A-Za-z0-9_]*$')][string]$Component = '',
    [ValidateRange(60,240)][int]$TimeoutSeconds=120
)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$root=Join-Path $Archive 'Windows'
$exe=Join-Path $root 'MikdashCourtyardV3/Binaries/Win64/MikdashCourtyardV3.exe'
if ((Get-FileHash -LiteralPath $exe).Hash -ne $ExpectedChildSha256) { throw 'Unexpected game child hash' }
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3 -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$review=Join-Path $project 'SourceAssets/context-review/CameraObstructionV1'
$diag=Join-Path $root 'MikdashCourtyardV3/Saved/Diagnostics'
$receipt=Join-Path $review "probe-$stamp.json"
$log=Join-Path $review "probe-$stamp.log"
$prior=@(Get-ChildItem -LiteralPath $diag -Filter 'PhotoPawn-*.json' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
function Map-Hashes {
    $result=[ordered]@{}
    Get-ChildItem -LiteralPath (Join-Path $project 'Content') -Filter '*.umap' -Recurse -File | Sort-Object FullName | ForEach-Object {
        $result[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName).Hash
    }
    return $result
}
$r=[ordered]@{status='starting';startedUtc=(Get-Date).ToUniversalTime().ToString('o');archive=$Archive;childSha256=$ExpectedChildSha256;component=$Component;mapHashesBefore=(Map-Hashes);scope='Opt-in pawn skeletal visibility diagnostic; not a production fix or full recook.'}
function Save-Receipt { $r | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $receipt -Encoding utf8 }
Save-Receipt
$launchArgs=@('-unattended','-nosound','-nosplash','-windowed','-ResX=1600','-ResY=900','-MikdashPhotoPawnDiagnostic','-MikdashPhotoPawnProbe',('-abslog="'+$log+'"'),'-ExecCmds="Ghost,BugItGo -33500 0 6500 -25 180 0"',('-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashPhotoMode]:LeashRadiusCm=900000,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=PhotoProbe_'+$stamp+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=PhotoProbe_'+$stamp))
if($Component){$launchArgs+=('-MikdashPhotoPawnComponent='+$Component)}
$proc=$null
try {
    $proc=Start-Process -FilePath $exe -ArgumentList $launchArgs -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $r.pid=$proc.Id; $r.arguments=$launchArgs; $r.status='running'; Save-Receipt
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    while((Get-Date) -lt $deadline){Start-Sleep -Seconds 2; $proc.Refresh(); if($proc.HasExited){break}}
    if(!$proc.HasExited){throw 'Native probe timed out'}
    $proc.WaitForExit(); $r.exitCode=$proc.ExitCode
    if($proc.ExitCode -ne 0){throw "Native probe exited $($proc.ExitCode)"}
    $fresh=@(Get-ChildItem -LiteralPath $diag -Filter 'PhotoPawn-*.json' | Where-Object {$prior -notcontains $_.FullName} | Sort-Object Name)
    if(!$fresh.Count){throw 'No fresh native diagnostic receipts'}
    $r.native=@()
    foreach($f in $fresh){
        $value=Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
        Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $review $f.Name)
        $r.native+=@{file=$f.Name;data=$value}
        if($value.probePhotoPath -and (Test-Path -LiteralPath $value.probePhotoPath)){
            $photo=Join-Path $review "probe-$stamp.png"
            Copy-Item -LiteralPath $value.probePhotoPath -Destination $photo -Force
            $r.photo=$photo; $r.photoSha256=(Get-FileHash -LiteralPath $photo).Hash.ToLowerInvariant()
        }
    }
    $r.status='native-exited-receipts-collected-review-pending'
} catch { $r.status='failed'; $r.error=$_.Exception.Message }
finally {
    if($proc){$proc.Refresh(); if(!$proc.HasExited){
        if((Get-Process -Id $proc.Id).Path -ne $exe){throw 'Owned process path changed; refusing stop'}
        $proc | Stop-Process -Force; $r.forcedStop=$true
    }}
    $r.mapHashesAfter=Map-Hashes
    $r.mapsUnchanged=(($r.mapHashesBefore|ConvertTo-Json -Compress) -eq ($r.mapHashesAfter|ConvertTo-Json -Compress))
    if(!$r.mapsUnchanged){$r.status='failed';$r.error='Source map hash changed'}
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o'); Save-Receipt
}
Write-Output "$($r.status): $receipt"
if($r.status -eq 'failed'){exit 1}
