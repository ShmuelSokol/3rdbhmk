param([ValidateSet('01','02','03','04','05','06','07','08','09','10','11')][string]$Study='03',[switch]$Build,[ValidateSet('Man_Standard','Man_Heavy','Man_Elder','Woman_Young','Woman_Elder','Youth')][string]$Variant='Man_Standard',[switch]$NormalsAudit,[switch]$Posed)
$ErrorActionPreference = 'Stop'
if($Study -eq '11' -and ($NormalsAudit -or $Posed -or $Variant -notin @('Man_Elder','Woman_Young'))){throw 'Study11 supports direct-normal Elder/Woman build or fresh readback only'}
if($Posed -and -not $NormalsAudit){throw 'Posed requires NormalsAudit'}
if($NormalsAudit -and ($Build -or $Study -notin @('09','10') -or $Variant -notin @('Man_Elder','Woman_Young'))){throw 'NormalsAudit requires existing Study09/10 Elder or Woman_Young and no Build'}
$root = (Split-Path -Parent $PSScriptRoot).Replace('\','/')
$busy = @(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3,AutomationTool -ErrorAction SilentlyContinue)
$busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
if(([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 6GB){throw 'Isolated audit needs 6 GiB free commit'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$folder="$root/SourceAssets/perf-review/crowd-vat/ResidentStudy$Study"
if($Variant -ne 'Man_Standard'){$folder+='/Cast/'+$Variant}
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$log="$folder/resident-crowd-run-$stamp.log"
$receipt="$folder/resident-crowd-run-$stamp.json"
if(Test-Path -LiteralPath $receipt){throw 'Fresh audit receipt required'}
$outputPattern=if($Posed){'posed-normals-*.json'}elseif($NormalsAudit){'normals-*.json'}else{'native-*.json'}
$before=@(Get-ChildItem -LiteralPath $folder -Filter $outputPattern -File | Where-Object {$_.Name -notlike 'resident-crowd-run-*'} | Select-Object -ExpandProperty FullName)
$record=[ordered]@{status='starting';scope='ResidentV4 two-detail crowd pilot or readback; no maps';build=[bool]$Build;startedUtc=$stamp;log=$log;minimumStartCommitBytes=6GB;maximumPrivateBytes=4GB;reserveCommitBytes=2GB;peakPrivateBytes=0}
function Save-Receipt {$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receipt -Encoding utf8}
Save-Receipt
$exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$arguments=@(('"'+$root+'/MikdashCourtyardV3.uproject"'),'-run=pythonscript',('-script="'+$root+'/Scripts/build_resident_crowd.py"'),'-nullrhi','-EnablePlugins=AnimToTexture,GeometryScripting','-DisablePlugins=MetaHumanCharacter,MetaHumanSDK','-unattended','-nosplash','-nosound','-notraceserver','-NoMetaHumanAccountPortalLoginFallback','-NoAsyncLoadingThread','-asyncstaticmeshcompilationmaxconcurrency=1',('-abslog="'+$log+'"'))
if($Study -eq '11'){$arguments[2]='-script="'+$root+'/Scripts/build_resident_direct_normals.py"';$record.scope='Complete direct skeletal normal candidate build or fresh readback'}
if($NormalsAudit){$arguments[2]='-script="'+$root+'/Scripts/audit_resident_vat_normals.py"';$record.scope='Read-only resident source/static normal audit and texture export';$record.normalsAudit=$true}
if($Posed){$arguments[2]='-script="'+$root+'/Scripts/audit_resident_vat_pose.py"';$record.scope='Read-only resident evaluated skeletal normal export';$record.posed=$true}
if($Build){$arguments += '-ResidentCrowdBuild'}
$arguments += ('-ResidentCrowdStudy='+$Study)
$arguments += ('-ResidentCrowdVariant='+$Variant)
$child=$null
try {
    $child=Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $record.pid=$child.Id;$record.status='running';Save-Receipt
    $deadline=(Get-Date).AddSeconds(900)
    do {
        Start-Sleep -Seconds 2
        $child.Refresh()
        if($child.HasExited){break}
        $record.peakPrivateBytes=[math]::Max([long]$record.peakPrivateBytes,[long]$child.PrivateMemorySize64)
        $free=[long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB
        if($child.PrivateMemorySize64 -gt 4GB -or $free -lt 2GB){throw 'Owned isolated audit hit memory reserve'}
        if((Get-Date) -gt $deadline){throw 'Owned isolated audit timed out'}
    } while($true)
    $child.WaitForExit();$record.exitCode=$child.ExitCode
    if($child.ExitCode -ne 0){throw "Audit exited $($child.ExitCode)"}
    $outputs=@(Get-ChildItem -LiteralPath $folder -Filter $outputPattern -File | Where-Object {$_.Name -notlike 'resident-crowd-run-*'} | Where-Object {$_.FullName -notin $before})
    if($outputs.Count -ne 1){throw 'Expected one fresh near candidate receipt'}
    $result=Get-Content -LiteralPath $outputs[0].FullName -Raw | ConvertFrom-Json
    $expectedStatus=if($Posed){'exported-posed-normals'}elseif($NormalsAudit){'audited-reference-normals'}elseif($Build){'built-needs-fresh-readback-and-render'}else{'verified-fresh-candidate-not-rendered'}
    if($result.status -ne $expectedStatus){throw 'Near candidate operation did not complete'}
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
