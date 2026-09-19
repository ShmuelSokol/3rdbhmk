param([switch]$Apply)
$ErrorActionPreference = 'Stop'

$root = (Split-Path -Parent $PSScriptRoot).Replace('\','/')
$busy = @(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3,AutomationTool -ErrorAction SilentlyContinue)
$busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
if(([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 20GB){throw 'Source map operation needs 20 GiB free commit'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$folder="$root/SourceAssets/water-review/CourtOutletV2"
$log="$folder/map-run-$stamp.log"
$receipt="$folder/map-run-$stamp.json"
if(Test-Path -LiteralPath $receipt){throw 'Fresh audit receipt required'}
$before=@(Get-ChildItem -LiteralPath $folder -Filter 'map-*.json' -File | Where-Object {$_.Name -notlike 'map-run-*'} | Select-Object -ExpandProperty FullName)
$record=[ordered]@{status='starting';scope='Backed-up Candidate48 two-binding update or fresh verification';apply=[bool]$Apply;startedUtc=$stamp;log=$log;minimumStartCommitBytes=20GB;maximumPrivateBytes=16GB;reserveCommitBytes=4GB;peakPrivateBytes=0}
function Save-Receipt {$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receipt -Encoding utf8}
Save-Receipt
$exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$arguments=@(('"'+$root+'/MikdashCourtyardV3.uproject"'),'-run=pythonscript',('-script="'+$root+'/Scripts/integrate_court_outlet_v2.py"'),'-nullrhi','-EnablePlugins=GeometryScripting','-DisablePlugins=MetaHumanCharacter,MetaHumanSDK','-unattended','-nosplash','-nosound','-notraceserver','-NoMetaHumanAccountPortalLoginFallback','-NoAsyncLoadingThread','-asyncstaticmeshcompilationmaxconcurrency=1',('-abslog="'+$log+'"'))
if($Apply){$arguments += '-CourtOutletMapApply'}

$child=$null
try {
    $child=Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $record.pid=$child.Id;$record.status='running';Save-Receipt
    $deadline=(Get-Date).AddSeconds(600)
    do {
        Start-Sleep -Seconds 2
        $child.Refresh()
        if($child.HasExited){break}
        $record.peakPrivateBytes=[math]::Max([long]$record.peakPrivateBytes,[long]$child.PrivateMemorySize64)
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        if($child.PrivateMemorySize64 -gt 16GB -or $free -lt 4GB){throw 'Owned source map operation hit memory reserve'}
        if((Get-Date) -gt $deadline){throw 'Owned source map operation timed out'}
    } while($true)
    $child.WaitForExit();$record.exitCode=$child.ExitCode
    if($child.ExitCode -ne 0){throw "Audit exited $($child.ExitCode)"}
    $outputs=@(Get-ChildItem -LiteralPath $folder -Filter 'map-*.json' -File | Where-Object {$_.Name -notlike 'map-run-*'} | Where-Object {$_.FullName -notin $before})
    if($outputs.Count -ne 1){throw 'Expected one fresh mesh audit output'}
    $result=Get-Content -LiteralPath $outputs[0].FullName -Raw | ConvertFrom-Json
    $expectedStatus=if($Apply){'applied-needs-fresh-verification'}else{'verified-fresh-map'}
    if($result.status -ne $expectedStatus){throw 'Outlet operation did not complete'}
    $record.output=$outputs[0].FullName;$record.outputSha256=(Get-FileHash -LiteralPath $record.output).Hash.ToLower()
    $record.status=$result.status
} catch {
    $record.status='failed';$record.error=$_.Exception.Message
} finally {
    try {
        if($child){$child.Refresh();if(-not $child.HasExited){$child | Stop-Process -Force;$record.stoppedOwnedChild=$true}}
    } catch {
        $record.status='failed';$record.cleanupError=$_.Exception.Message
    }
    Save-Receipt
}
Write-Output "$($record.status): $receipt"
if($record.status -eq 'failed'){exit 1}
