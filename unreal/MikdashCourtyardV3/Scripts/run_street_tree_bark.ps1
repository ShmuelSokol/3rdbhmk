param([ValidateSet('Audit','Apply','Verify')][string]$Mode='Audit')
$ErrorActionPreference='Stop'
$root=(Split-Path -Parent $PSScriptRoot).Replace('\','/')
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3 -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
if(([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 6GB){throw 'Bark material job requires 6 GiB free commit'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$out="$root/SourceAssets/vegetation-review/StreetTreesV1"
$log="$out/bark-job-$stamp.log"
$receipt="$out/bark-job-$stamp.json"
$record=[ordered]@{status='starting';mode=$Mode;minimumStartCommitBytes=6GB;maximumPrivateBytes=4GB;reserveCommitBytes=2GB;peakPrivateBytes=0;log=$log}
function Save-Receipt {$record|ConvertTo-Json|Set-Content -LiteralPath $receipt -Encoding utf8}
Save-Receipt
$exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$arguments=@(('"'+$root+'/MikdashCourtyardV3.uproject"'),'-run=pythonscript',('-script="'+$root+'/Scripts/repair_street_tree_bark.py"'),('-Bark'+$Mode),'-AllowCommandletRendering','-RenderOffscreen','-DisablePlugins=MetaHumanCharacter,MetaHumanSDK','-unattended','-nosplash','-nosound','-notraceserver','-NoAsyncLoadingThread','-asyncstaticmeshcompilationmaxconcurrency=1','-asyncskinnedassetcompilationmaxconcurrency=1','-asynctexturecompilationmaxconcurrency=1',('-abslog="'+$log+'"'))
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
        if ($child.PrivateMemorySize64 -gt 4GB -or $free -lt 2GB) {throw 'Owned bark material job hit memory reserve'}
        if ((Get-Date) -gt $deadline) {throw 'Owned bark material job timed out'}
    } while ($true)
    $child.WaitForExit(); $record.exitCode=$child.ExitCode
    if ($child.ExitCode -ne 0) {throw "Commandlet exited $($child.ExitCode)"}
    $record.status='native-exited-zero-inspect-readback-receipt'
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
