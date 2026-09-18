param([switch]$RenderTarget, [switch]$CalibrateColors, [switch]$RepairColors, [switch]$VerifyColors)
$ErrorActionPreference = 'Stop'
if (@($RenderTarget,$CalibrateColors,$RepairColors,$VerifyColors | Where-Object {$_}).Count -gt 1) {throw 'Choose one study mode'}
$root = (Split-Path -Parent $PSScriptRoot).Replace('\', '/')
$busy = @(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3 -ErrorAction SilentlyContinue)
$busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if ($busy.Count) { throw 'Native slot occupied' }
$free = [long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory * 1KB
if ($free -lt 6GB) { throw 'Isolated GPU study needs 6 GiB free commit' }
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$log = "$root/SourceAssets/characters-review/KohenSkinV2/gpu-head-$stamp.log"
$record = [ordered]@{status='starting';startedUtc=$stamp;scope='isolated GPU head study in Engine Entry, transient actors, no saves';minimumStartCommitBytes=6GB;maximumPrivateBytes=4GB;reserveCommitBytes=2GB;peakPrivateBytes=0;log=$log}
$receipt = "$root/SourceAssets/characters-review/KohenSkinV2/gpu-head-run-$stamp.json"
$record.disabledAuthoringPlugins='MetaHumanCharacter,MetaHumanSDK'
function Save-Receipt { $record | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8 }
Save-Receipt
$exe = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$arguments = @(('"'+$root+'/MikdashCourtyardV3.uproject"'),'/Engine/Maps/Entry',('-ExecCmds="py '+$root+'/Scripts/capture_kohen_skin_study.py"'),'-DisablePlugins=MetaHumanCharacter,MetaHumanSDK','-RenderOffscreen','-unattended','-nosplash','-nosound','-notraceserver','-NoMetaHumanAccountPortalLoginFallback','-NoAsyncLoadingThread','-ResX=960','-ResY=720','-asyncstaticmeshcompilationmaxconcurrency=1','-asyncskinnedassetcompilationmaxconcurrency=1','-asynctexturecompilationmaxconcurrency=1',('-abslog="'+$log+'"'))
if ($RenderTarget -or $CalibrateColors -or $RepairColors -or $VerifyColors) {
    $exe = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $arguments = @($arguments | Where-Object {$_ -ne '/Engine/Maps/Entry' -and $_ -notlike '-ExecCmds=*'})
    $scriptName = if ($CalibrateColors) {'calibrate_kohen_vertex_colors.py'} elseif ($RepairColors -or $VerifyColors) {'repair_kohen_linear_colors.py'} else {'capture_kohen_skin_commandlet.py'}
    $arguments += @('-run=pythonscript',('-script="'+$root+'/Scripts/'+$scriptName+'"'),'-AllowCommandletRendering')
    $record.scope='isolated GPU render-target commandlet, transient actors, no saves'
    $record.script=$scriptName
    if ($RepairColors -or $VerifyColors) {
        $arguments = @($arguments | Where-Object {$_ -ne '-AllowCommandletRendering' -and $_ -ne '-RenderOffscreen'})
        $arguments += '-nullrhi'
        $arguments += $(if ($RepairColors) {'-KohenLinearApply'} else {'-KohenLinearVerify'})
        $record.scope = if ($RepairColors) {'backed-up material color repair; no mesh/map binding changes'} else {'fresh-process material color verification; no saves'}
    }
    Save-Receipt
}
$child = $null
try {
    $child = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $record.pid=$child.Id; $record.status='running'; Save-Receipt
    $deadline = (Get-Date).AddSeconds(300)
    do {
        Start-Sleep -Seconds 2
        $child.Refresh()
        if ($child.HasExited) { break }
        $record.peakPrivateBytes=[math]::Max([long]$record.peakPrivateBytes,[long]$child.PrivateMemorySize64)
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        if ($child.PrivateMemorySize64 -gt 4GB -or $free -lt 2GB) {throw 'Owned GPU study hit memory reserve'}
        if ((Get-Date) -gt $deadline) {throw 'Owned GPU study timed out'}
    } while ($true)
    $child.WaitForExit(); $record.exitCode=$child.ExitCode
    if ($child.ExitCode -ne 0) {throw "Commandlet exited $($child.ExitCode)"}
    $record.status='editor-exited-zero-inspect-capture-receipt'
} catch {
    $record.status='failed';$record.error=$_.Exception.Message
} finally {
    if ($child) {
        $child.Refresh()
        if (-not $child.HasExited) { $child | Stop-Process -Force; $record.stoppedOwnedChild=$true }
    }
    Save-Receipt
}
if ($record.status -eq 'failed') { exit 1 }
