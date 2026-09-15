<# Temporarily tests the prepared family patch, then restores the verified CityWall patch.
   Only the named isolated archive is eligible. No source-map, base-container or user-save edits.
#>
param([switch]$PlanOnly)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$project=Split-Path $PSScriptRoot -Parent
$archive='C:\Mikdash\Builds\Checkpoint-contextpatch01-20260915'
$pakDir=Join-Path $archive 'Windows\MikdashCourtyardV3\Content\Paks'
$child=Join-Path $archive 'Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
$expectedChild='3aee6ac4d129e6327a7077d59d83557a50c10ecb731aa94744e1eb612d02f087'
$candidateDir='C:\Mikdash\Working-5.8\ContextPatchStudies\AllCoursingFamilies-20260915T180845462Z-51ac6460\ContainerRecipeV1-20260915T181041867043Z-a4dde6b3'
$review=Join-Path $project 'SourceAssets/context-review/ContextCoursingV2'
$stairReview=Join-Path $project 'SourceAssets/context-review/KotelCutClosureV1'
$baseline=Get-Content -LiteralPath (Join-Path $review 'current-playable-patch.json') -Raw|ConvertFrom-Json
$candidate=Get-Content -LiteralPath (Join-Path $candidateDir 'native-build.json') -Raw|ConvertFrom-Json
$recipePath=Join-Path $candidateDir 'recipe.json'
$recipe=Get-Content -LiteralPath $recipePath -Raw|ConvertFrom-Json
$names=@('ContextCoursingV2_1_P.pak','ContextCoursingV2_1_P.ucas','ContextCoursingV2_1_P.utoc')
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Assert-Slot {
    $busy=@(Get-CimInstance Win32_Process|Where-Object {
        $_.Name -match '^(UnrealEditor|UnrealEditor-Cmd|UnrealPak|ShaderCompileWorker|MikdashCourtyardV3)\.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'AutomationTool|UnrealBuildTool')
    })
    if($busy.Count){throw 'Native slot occupied'}
}
function Base-Hashes {
    $files=@(Get-ChildItem -LiteralPath $pakDir -File|Where-Object {$names -notcontains $_.Name}|Sort-Object Name)
    if($files.Count -ne 6){throw 'Unexpected base/other patch file census'}
    $result=[ordered]@{};foreach($file in $files){$result[$file.Name]=Hash $file.FullName};return $result
}
Assert-Slot
if((Hash $child) -ne $expectedChild){throw 'Unexpected runtime child'}
if($baseline.status -ne 'verified-citywall-only-patch-restored' -or $baseline.full13FamilyPatchMounted){throw 'Baseline receipt is not the verified CityWall-only state'}
if((($baseline.patchOutputs.file|Sort-Object)-join ',') -ne ($names-join ',')){throw 'Unexpected baseline bundle census'}
if((($candidate.outputs.file|Sort-Object)-join ',') -ne ($names-join ',')){throw 'Unexpected candidate bundle census'}
if($candidate.ioExitCode -ne 0 -or $candidate.pakExitCode -ne 0 -or (Hash $recipePath) -ne $candidate.recipeSha256){throw 'Candidate build/recipe identity failed'}
if($recipe.allowedPackages.Count -ne 13){throw 'Expected the audited 13-package candidate'}
foreach($entry in $baseline.patchOutputs){if((Hash (Join-Path $pakDir $entry.file)) -ne $entry.sha256){throw 'Installed baseline differs from verified patch'}}
foreach($entry in $candidate.outputs){if((Hash (Join-Path $candidateDir ('Containers/'+$entry.file))) -ne $entry.sha256){throw 'Candidate bundle changed'}}
$free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
if($free -lt 6.5GB){throw 'Insufficient headroom for constrained NullRHI probe; no files changed'}
if($PlanOnly){[ordered]@{archive=$archive;candidateRecipeSha256=(Hash $recipePath);candidatePackageCount=13;baselineFiles=$names;nativeLaunched=$false;filesChanged=$false}|ConvertTo-Json;return}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$transaction=Join-Path 'C:\Mikdash\Working-5.8\ContextPatchStudies' ('HeadlessTransaction-'+$stamp)
if(Test-Path -LiteralPath $transaction){throw 'Transaction directory collision'}
New-Item -ItemType Directory -Path $transaction|Out-Null
$receipt=Join-Path $review ('family-headless-'+$stamp+'.json')
if(Test-Path -LiteralPath $receipt){throw 'Receipt collision'}
$before=Base-Hashes
$prior=@(Get-ChildItem -LiteralPath $stairReview -Filter 'stair-*.json'|Select-Object -ExpandProperty FullName)
$r=[ordered]@{status='preparing';startedUtc=(Get-Date).ToUniversalTime().ToString('o');archive=$archive;
    childSha256=$expectedChild;candidateRecipeSha256=(Hash $recipePath);candidateOutputs=$candidate.outputs;
    baselineOutputs=$baseline.patchOutputs;baseHashesBefore=$before;transaction=$transaction;
    installed=$false;restored=$false;nativeStatus=$null;error=$null;
    scope='NullRHI candidate-container mount and real character stair replay only. No pixels or complete material-binding/shader acceptance.'}
function Save-Receipt {$r|ConvertTo-Json -Depth 16|Set-Content -LiteralPath $receipt -Encoding utf8}
Save-Receipt
$mayHaveChanged=$false
try {
    foreach($entry in $baseline.patchOutputs){
        $backup=Join-Path $transaction $entry.file
        Copy-Item -LiteralPath (Join-Path $pakDir $entry.file) -Destination $backup
        if((Hash $backup) -ne $entry.sha256){throw 'Baseline backup hash failed'}
    }
    Assert-Slot
    foreach($entry in $candidate.outputs){
        $mayHaveChanged=$true
        Copy-Item -LiteralPath (Join-Path $candidateDir ('Containers/'+$entry.file)) -Destination (Join-Path $pakDir $entry.file) -Force
        if((Hash (Join-Path $pakDir $entry.file)) -ne $entry.sha256){throw 'Candidate installation hash failed'}
    }
    $r.installed=$true;$r.status='testing';Save-Receipt
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Test-KotelStairRuntime.ps1') -Archive $archive -ExpectedChildSha256 $expectedChild -Constrained
    $r.probeExitCode=$LASTEXITCODE
    $fresh=@(Get-ChildItem -LiteralPath $stairReview -Filter 'stair-*.json'|Where-Object {$prior -notcontains $_.FullName})
    if($fresh.Count -ne 1){throw 'Expected one fresh stair receipt'}
    $native=Get-Content -LiteralPath $fresh[0].FullName -Raw|ConvertFrom-Json
    $r.nativeReceipt=$fresh[0].Name;$r.nativeReceiptSha256=Hash $fresh[0].FullName;$r.native=$native;$r.nativeStatus=$native.status
    if($r.probeExitCode -ne 0 -or $native.status -ne 'passed-native-stair-route' -or !$native.mapsUnchanged){throw 'Native stair replay did not pass'}
    $logPath=[IO.Path]::ChangeExtension($fresh[0].FullName,'.log')
    $log=Get-Content -LiteralPath $logPath -Raw
    $r.mountEvidence=@($log -split '\r?\n'|Where-Object {$_ -match 'Mounted container.*ContextCoursingV2_1_P\.utoc' -or $_ -match 'Mounted Pak file.*ContextCoursingV2_1_P\.pak'})
    if(!@($r.mountEvidence|Where-Object {$_ -match 'Order=203'}).Count -or $r.mountEvidence.Count -lt 2){throw 'Missing paired patch mount/priority proof'}
    $r.status='passed-native-mount-and-stair-restoration-pending'
} catch {$r.status='failed';$r.error=$_.Exception.Message}
finally {
    try {
        if($mayHaveChanged){
            Assert-Slot
            foreach($entry in $baseline.patchOutputs){
                $backup=Join-Path $transaction $entry.file
                if((Hash $backup) -ne $entry.sha256){throw 'Cannot restore: baseline backup changed'}
            }
            foreach($entry in $baseline.patchOutputs){
                Copy-Item -LiteralPath (Join-Path $transaction $entry.file) -Destination (Join-Path $pakDir $entry.file) -Force
                if((Hash (Join-Path $pakDir $entry.file)) -ne $entry.sha256){throw 'Baseline restoration readback failed'}
            }
        }
        $r.restored=$true;$r.baseHashesAfter=Base-Hashes
        $r.baseContainersUnchanged=(($before|ConvertTo-Json -Compress) -eq ($r.baseHashesAfter|ConvertTo-Json -Compress))
        if(!$r.baseContainersUnchanged -or (Hash $child) -ne $expectedChild){throw 'Base containers or child changed'}
        if($r.status -eq 'passed-native-mount-and-stair-restoration-pending'){$r.status='passed-native-mount-and-stair-restored'}
    } catch {$r.status='restoration-or-integrity-failed';$r.error=(@($r.error,$_.Exception.Message)|Where-Object {$_})-join '; '}
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o');Save-Receipt
}
[ordered]@{status=$r.status;receipt=$receipt;error=$r.error}|ConvertTo-Json
if($r.status -ne 'passed-native-mount-and-stair-restored'){exit 1}
