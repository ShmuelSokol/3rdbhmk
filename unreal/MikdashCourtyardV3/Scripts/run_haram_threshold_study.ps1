param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]{1,48}$')][string]$RunId,
    [ValidateSet('Preflight','Build','Verify')][string]$Mode='Preflight',
    [switch]$SaveCandidate,
    [switch]$CoordinatorNativeRun,
    [ValidateRange(30,600)][int]$TimeoutSeconds=300
)
$ErrorActionPreference='Stop'
if (-not $CoordinatorNativeRun) { throw 'CoordinatorNativeRun is required; preparation does not authorize a native launch' }
if ($Mode -ne 'Build' -and $SaveCandidate) { throw 'Only Build can save isolated assets' }
$root=(Split-Path -Parent $PSScriptRoot).Replace('\','/')
$study="$root/SourceAssets/context-review/HaramThresholdSidesV1"
$blockedSlot="$study/native-slot-blocked.json"
if(Test-Path -LiteralPath $blockedSlot) { throw 'Native slot remains blocked; coordinator must confirm recorded owned process has exited before removing marker' }
$output="$study/$RunId/$($Mode.ToLowerInvariant())"
$assetDirectory="$root/Content/MikdashV3/MaterialReview/HaramThresholdSidesV1/$RunId"
$candidateFile="$assetDirectory/SM_ThresholdSides.uasset"
if (Test-Path -LiteralPath $output) { throw 'Fresh mode output required; preserve previous evidence' }
if ($Mode -ne 'Verify' -and (Test-Path -LiteralPath $assetDirectory)) { throw 'Fresh candidate namespace required' }
if ($Mode -eq 'Verify' -and -not (Test-Path -LiteralPath $candidateFile)) { throw 'Saved isolated candidate required' }
if ($Mode -ne 'Preflight') {
    # Offline gate before native startup, repeated inside Python before any mutation.
    & 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe' -B "$root/Scripts/haram_threshold_study_common.py" --check-preflight $RunId
    if ($LASTEXITCODE -ne 0) { throw 'Fresh matching successful preflight required; native not launched' }
}
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3,ShaderCompileWorker -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if ($busy.Count) { throw 'Native slot occupied; coordinate, do not stop another worker' }
if (([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 6GB) { throw 'Isolated study requires 6 GiB free commit' }
$manifest=Get-Content -LiteralPath "$study/source-audit.json" -Raw | ConvertFrom-Json
function Get-ProtectedHashes($paths) {
    $hashes=[ordered]@{}
    foreach($path in $paths) { $hashes[$path]=(Get-FileHash -LiteralPath "$root/$path" -Algorithm SHA256).Hash.ToLowerInvariant() }
    return $hashes
}
$before=Get-ProtectedHashes $manifest.protectedPaths
foreach($property in $manifest.pinnedAssets.psobject.Properties) {
    $relative='Content/'+$property.Name.Substring(6)+'.uasset'
    if($before[$relative] -ne $property.Value) { throw "Accepted input changed: $relative" }
}
# An exclusive shared study lock also protects against two wrappers racing the busy check.
# A project-wide coordinator must still serialize this with other native harnesses.
$lock=$null
$child=$null
$record=$null
try {
    $lock=[System.IO.File]::Open("$study/native.lock",[System.IO.FileMode]::OpenOrCreate,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
    if(Test-Path -LiteralPath $blockedSlot) { throw 'Native slot blocked; coordinator review required' }
    New-Item -ItemType Directory -Path $output | Out-Null
    $log="$output/native.log"
    $record=[ordered]@{status='starting';mode=$Mode;runId=$RunId;saveCandidate=[bool]$SaveCandidate;
        minimumStartCommitBytes=6GB;maximumPrivateBytes=4GB;reserveCommitBytes=2GB;
        peakPrivateBytes=0;minimumFreeCommitBytes=[long]::MaxValue;protectedBefore=$before;log=$log}
    function Save-Receipt { $record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$output/wrapper.json" -Encoding utf8 }
    Save-Receipt
    # Full editor threshold-sides01 exceeded the unchanged cap before script execution.
    # Commandlet uses only five source-audited CDO getters, with positive preflight proof.
    $exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $argumentLine=('"{0}/MikdashCourtyardV3.uproject" /Engine/Maps/Entry -run=pythonscript -script="{0}/Scripts/study_haram_threshold_sides.py" -ThresholdCoordinator -ThresholdRun={1} -nop4 -SCCProvider=None -EnablePlugins=GeometryScripting -AllowCommandletRendering -RenderOffscreen -DisablePlugins=MetaHumanCharacter,MetaHumanSDK -unattended -nosplash -nosound -notraceserver -NoMetaHumanAccountPortalLoginFallback -NoAsyncLoadingThread -asyncstaticmeshcompilationmaxconcurrency=1 -asyncskinnedassetcompilationmaxconcurrency=1 -asynctexturecompilationmaxconcurrency=1 -ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=999 -ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreadsDuringGame=999 -ini:Engine:[DevOptions.Shaders]:bForceUseSCWMemoryPressureLimits=False -abslog="{2}"' -f $root,$RunId,$log)
    # Isolated direct-sun mapping review only; preserve Nanite/texture quality/resolution.
    $argumentLine+=' -ini:Engine:[/Script/Engine.RendererSettings]:r.DynamicGlobalIlluminationMethod=0 -ini:Engine:[/Script/Engine.RendererSettings]:r.ReflectionMethod=0 -ini:Engine:[/Script/Engine.RendererSettings]:r.Shadow.Virtual.Enable=0'
    if($Mode -eq 'Preflight') { $argumentLine+=' -ThresholdPreflight' }
    if($Mode -eq 'Verify') { $argumentLine+=' -ThresholdVerify' }
    if($SaveCandidate) { $argumentLine+=' -ThresholdSave' }
    $record.executable=$exe
    $record.argumentLine=$argumentLine
    $child=Start-Process -FilePath $exe -ArgumentList $argumentLine -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $record.pid=$child.Id
    $record.status='running'
    Save-Receipt
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $child.Refresh()
        if($child.HasExited) { break }
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $record.minimumFreeCommitBytes=[math]::Min($record.minimumFreeCommitBytes,$free)
        $record.peakPrivateBytes=[math]::Max($record.peakPrivateBytes,[long]$child.PrivateMemorySize64)
        if($child.PrivateMemorySize64 -gt 4GB -or $free -lt 2GB) { throw 'Owned study hit memory reserve' }
        if((Get-Date) -gt $deadline) { throw 'Owned study timed out' }
    } while($true)
    if(-not $child.WaitForExit(5000)) { throw 'Owned process exit did not settle within 5 seconds' }
    $record.exitCode=$child.ExitCode
    if($child.ExitCode -ne 0) { throw "Native exited $($child.ExitCode)" }
    $native=Get-Content -LiteralPath "$output/native.json" -Raw | ConvertFrom-Json
    if($Mode -eq 'Preflight') {
        if($native.status -ne 'preflight-passed' -or @($native.captures).Count -ne 0 -or
           $native.queries.collisionEnabled -ne $true -or $native.queries.castShadow -ne $true -or
           $native.queries.collisionNumeric -ne 1 -or $native.queries.shadowNumeric -ne 1) { throw 'Incomplete positive read-only preflight' }
    } elseif($native.status -ne 'captured-review-pending' -or @($native.captures).Count -ne 9) { throw 'Incomplete native proof/capture receipt' }
    $completion=@(Select-String -LiteralPath $log -SimpleMatch "HARAM_THRESHOLD_STUDY_COMPLETE $($Mode.ToLowerInvariant()) $RunId")
    if($completion.Count -ne 1) { throw 'Expected exactly one completion marker' }
    $bad=@(Select-String -LiteralPath $log -Pattern 'Failed to compile Material|Invalid shader map|Sampler type is|LogShaderCompilers: Error|Fatal error:|LogPython: Error|LogPythonScriptCommandlet: Error|LogUtils: (Error|Warning)|LogStaticMeshEditorSubsystem: (Error|Warning)')
    if($bad.Count) { throw 'Native/shader error in study log' }
    $record.nativeReceiptSha256=(Get-FileHash -LiteralPath "$output/native.json").Hash.ToLowerInvariant()
    $record.logSha256=(Get-FileHash -LiteralPath $log).Hash.ToLowerInvariant()
    $record.status=if($Mode -eq 'Preflight'){'preflight-passed'}else{'native-proof-passed-visual-review-pending'}
} catch {
    if($null -eq $record) { throw }
    $record.status='failed'
    $record.error=$_.Exception.Message
} finally {
    if($null -ne $record) {
        $record.nativeSlotFree=$false
        try {
            if($child) {
                $child.Refresh()
                if(-not $child.HasExited) {
                    # Only this wrapper's owned process; never global process-name cleanup.
                    $child | Stop-Process -Force
                    if(-not $child.WaitForExit(5000)) { throw 'Owned process remains alive after bounded cleanup wait' }
                    $record.stoppedOwnedChild=$true
                }
            }
            $record.nativeSlotFree=$true
        } catch {
            $record.status='failed'
            $record.cleanupError=$_.Exception.Message
            # Persistent interlock survives wrapper exit; never advertise a free slot.
            try { $record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $blockedSlot -Encoding utf8 }
            catch { $record.slotMarkerError=$_.Exception.Message }
        }
        try {
            $after=Get-ProtectedHashes $manifest.protectedPaths
            $record.protectedAfter=$after
            foreach($key in $before.Keys) { if($before[$key] -ne $after[$key]) { throw "Protected file changed: $key" } }
            if(Test-Path -LiteralPath "$output/native-protected.json") {
                $extra=Get-Content -LiteralPath "$output/native-protected.json" -Raw | ConvertFrom-Json
                foreach($p in $extra.psobject.Properties) {
                    if((Get-FileHash -LiteralPath "$root/$($p.Name)").Hash -ne $p.Value) { throw "Protected dependency changed: $($p.Name)" }
                }
            }
            $saved=@(Get-ChildItem -LiteralPath $assetDirectory -Recurse -File -ErrorAction SilentlyContinue)
            foreach($file in $saved) { if($file.FullName.Replace('\','/') -ne $candidateFile) { throw "Unexpected study file: $($file.FullName)" } }
            if(-not $SaveCandidate -and $Mode -ne 'Verify' -and $saved.Count) { throw 'Save occurred without SaveCandidate' }
        } catch {
            $record.status='failed'
            $record.preservationOrCleanupError=$_.Exception.Message
        }
        Save-Receipt
    }
    if($lock) { $lock.Dispose() }
}
if($record.status -eq 'failed') { exit 1 }
exit 0
