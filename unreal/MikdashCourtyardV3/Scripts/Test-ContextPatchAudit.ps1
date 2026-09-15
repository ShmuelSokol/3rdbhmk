<# Bounded read-only Entry dependency audit; never opens or saves a project map. #>
param([ValidateRange(60,300)][int]$TimeoutSeconds=180)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$review=Join-Path $project 'SourceAssets/context-review/ContextCoursingV2'
$exe='C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$busy=@(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(UnrealEditor|UnrealEditor-Cmd|ShaderCompileWorker|MikdashCourtyardV3|UnrealPak)\.exe$' -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'AutomationTool|UnrealBuildTool')
})
if($busy.Count){throw 'Native slot occupied; nothing launched'}
$free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
if($free -lt 9GB){throw 'Less than 9 GiB free commit; nothing launched'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$receipt=Join-Path $review "dependency-launch-$stamp.json"
$log=Join-Path $review "dependency-launch-$stamp.log"
if((Test-Path -LiteralPath $receipt) -or (Test-Path -LiteralPath $log)){throw 'Receipt/log path collision'}
$prior=@(Get-ChildItem -LiteralPath $review -Filter 'dependency-audit-*.json' | Select-Object -ExpandProperty FullName)
$script=Join-Path $project 'Scripts/audit_context_patch_dependencies.py'
$launchArgs=@(('"'+(Join-Path $project 'MikdashCourtyardV3.uproject')+'"'),'/Engine/Maps/Entry',
    '-ContextPatchDependencyAudit','-nullrhi','-unattended','-nosplash','-nosound',
    '-NoAsyncLoadingThread','-AsyncCompilationMaxConcurrency=1',
    ('-ExecCmds="py '+$script.Replace('\','/')+'"'),('-abslog="'+$log+'"'))
$r=[ordered]@{status='starting';startedUtc=(Get-Date).ToUniversalTime().ToString('o');arguments=$launchArgs;
    initialFreeCommitBytes=$free;minimumFreeCommitBytes=$free;peakPrivateBytes=[long]0;
    scriptSha256=(Get-FileHash -LiteralPath $script).Hash.ToLowerInvariant();scope='Read-only material dependency audit in Engine Entry; no map load/save or cook.'}
function Save-Receipt {$r | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $receipt -Encoding utf8}
Save-Receipt
$proc=$null
try {
    $proc=Start-Process -FilePath $exe -ArgumentList $launchArgs -WorkingDirectory $project -WindowStyle Hidden -PassThru
    $r.pid=$proc.Id;$r.status='running';Save-Receipt
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    while((Get-Date) -lt $deadline){
        Start-Sleep -Seconds 2;$proc.Refresh();if($proc.HasExited){break}
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        $r.peakPrivateBytes=[Math]::Max([long]$r.peakPrivateBytes,[long]$proc.PrivateMemorySize64)
        $r.minimumFreeCommitBytes=[Math]::Min([long]$r.minimumFreeCommitBytes,$free)
        if($proc.PrivateMemorySize64 -gt 6.5GB -or $free -lt 2GB){throw 'Owned audit reached memory reserve'}
    }
    if(!$proc.HasExited){throw 'Owned audit timed out'}
    $proc.WaitForExit();$r.exitCode=$proc.ExitCode
    $fresh=@(Get-ChildItem -LiteralPath $review -Filter 'dependency-audit-*.json' | Where-Object {$prior -notcontains $_.FullName})
    if($fresh.Count -ne 1){throw 'Expected exactly one fresh native audit receipt'}
    $native=Get-Content -LiteralPath $fresh[0].FullName -Raw | ConvertFrom-Json
    $r.nativeReceipt=$fresh[0].Name;$r.native=$native
    if($native.scriptSha256 -ne $r.scriptSha256 -or $native.stamp -notmatch ('-'+$proc.Id+'$')){
        throw 'Native audit identity differs from launched script/PID'
    }
    if($native.status -ne 'audited_with_explicit_unknowns' -or !$native.ownedContext -or $native.errors.Count -or
        !$native.mapsUnchanged -or !$native.sourceAssetsUnchanged -or @($native.dirtyAfter).Count){throw 'Native dependency audit failed'}
    if($proc.ExitCode -ne 0){throw "Audit editor exited $($proc.ExitCode); receipt preserved"}
    $r.status='dependency-audit-passed-with-explicit-unknowns'
} catch {$r.status='failed';$r.error=$_.Exception.Message}
finally {
    if($proc){$proc.Refresh();if(!$proc.HasExited){
        $owned=Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
        if($owned -and $owned.Path -eq $exe){$owned | Stop-Process -Force;$r.stoppedOwnedEditor=$true}
    }}
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o');Save-Receipt
}
[ordered]@{status=$r.status;receipt=$receipt}|ConvertTo-Json
if($r.status -eq 'failed'){exit 1}
