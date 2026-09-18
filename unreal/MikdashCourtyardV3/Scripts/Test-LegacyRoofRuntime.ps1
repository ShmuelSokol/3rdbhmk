<# Bounded diagnostic against an isolated packaged archive, without editor/map mutation.
   -NullRHI checks component state only. Rendered A1 state captures remain a separate gate.
#>
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedChildSha256,
    [switch]$NullRHI,
    [ValidateRange(30,300)][int]$TimeoutSeconds=180
)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$root=Join-Path $Archive 'Windows'
$exe=Join-Path $root 'MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe'
if (!(Test-Path -LiteralPath $exe)) { throw "Missing child executable: $exe" }
$exe=(Resolve-Path -LiteralPath $exe).Path
$hash=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $ExpectedChildSha256.ToLowerInvariant()) { throw 'Child executable hash differs from expected build' }
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3 -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' })
if ($busy.Count) { throw 'Native slot is occupied; diagnostic did not launch' }
$free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
if($free -lt 9GB){throw 'Roof runtime probe requires9GiB free commit; nothing launched'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$review=Join-Path $project 'SourceAssets\context-review\LegacyRoofRuntimeV1'
New-Item -ItemType Directory -Force -Path $review | Out-Null
$log=Join-Path $review "packaged-$stamp.log"
$output=Join-Path $review "packaged-$stamp.json"
$diagnostics=Join-Path $root 'MikdashCourtyardV3\Saved\Diagnostics'
$old=@(Get-ChildItem -LiteralPath $diagnostics -Filter 'LegacyRoofRuntimeV1-*.json' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
function Map-Hashes {
    $hashes=[ordered]@{}
    Get-ChildItem -LiteralPath (Join-Path $project 'Content') -Filter '*.umap' -File -Recurse |
        Sort-Object FullName | ForEach-Object { $hashes[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName).Hash }
    return $hashes
}
$before=Map-Hashes
$r=[ordered]@{status='running';archive=$Archive;childSha256=$hash;nullRHI=[bool]$NullRHI;startedUtc=(Get-Date).ToUniversalTime().ToString('o');mapHashesBefore=$before;scope='Specified archive and pinned child executable; native component state only, rendered acceptance is separate.';initialRequiredFreeCommitBytes=9GB;maximumPrivateBytes=8GB;reserveBytes=1.25GB;peakPrivateBytes=0;minimumFreeCommitBytes=$free}
$argsForGame=@('-unattended','-nosound','-nosplash','-windowed','-ResX=1280','-ResY=720','-MikdashLegacyRoofDiagnostic','-MikdashLegacyRoofDiagnosticExit',('-abslog="'+$log+'"'),('-ini:Game:[/Script/MikdashRuntime.MikdashFrontEnd]:bShowMainMenuOnBoot=False,[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=RoofProbe_'+$stamp+',[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=RoofProbe_'+$stamp))
if ($NullRHI) { $argsForGame+='-nullrhi' }
$r.arguments=$argsForGame
$r | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $output -Encoding utf8
$process=$null
try {
    $process=Start-Process -FilePath $exe -ArgumentList $argsForGame -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $r.processId=$process.Id
    $r | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $output -Encoding utf8
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $process.Refresh()
        if ($process.HasExited) { break }
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $r.minimumFreeCommitBytes=[Math]::Min([long]$r.minimumFreeCommitBytes,$free)
        $r.peakPrivateBytes=[Math]::Max([long]$r.peakPrivateBytes,[long]$process.PrivateMemorySize64)
        if($process.PrivateMemorySize64 -gt 8GB -or $free -lt 1.25GB){throw 'Owned roof probe reached memory reserve'}
        Start-Sleep -Seconds 1
    }
    $process.Refresh()
    $r.exited=$process.HasExited
    if ($r.exited) { $process.WaitForExit(); $r.exitCode=$process.ExitCode }
    $fresh=@(Get-ChildItem -LiteralPath $diagnostics -Filter 'LegacyRoofRuntimeV1-*.json' -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notin $old })
    if ($fresh.Count -ne 1) { throw "Expected one fresh native receipt, got $($fresh.Count)" }
    $native=Get-Content -LiteralPath $fresh[0].FullName -Raw | ConvertFrom-Json
    Copy-Item -LiteralPath $fresh[0].FullName -Destination (Join-Path $review ("native-"+$fresh[0].Name))
    $r.nativeReceipt=$fresh[0].FullName
    $r.native=$native
    if (!$r.exited -or $r.exitCode -ne 0 -or !$native.passed -or $native.states.Count -ne 10) {
        throw 'Native state probe or normal exit failed; see diagnostic/log'
    }
    $r.status='passed-native-state-probe'
} catch {
    $r.status='failed'
    $r.error=$_.Exception.Message
} finally {
    if ($process) {
        try {
            $process.Refresh()
            if (!$process.HasExited) {
                $process | Stop-Process -Force
                $r.terminatedOwnedChild=$true
            }
        } catch { $r.status='failed'; $r.cleanupError=$_.Exception.Message }
    }
    try {
        $r.mapHashesAfter=Map-Hashes
        $r.mapsUnchanged=(($before | ConvertTo-Json -Compress) -eq ($r.mapHashesAfter | ConvertTo-Json -Compress))
        if (!$r.mapsUnchanged) { $r.status='failed'; $r.error='Project map set or bytes changed during diagnostic' }
    } catch { $r.status='failed'; $r.mapHashError=$_.Exception.Message }
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o')
    $r | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $output -Encoding utf8
}
[pscustomobject]@{status=$r.status;receipt=$output;log=$log;error=$r.error} | ConvertTo-Json
if ($r.status -ne 'passed-native-state-probe') { exit 1 }
