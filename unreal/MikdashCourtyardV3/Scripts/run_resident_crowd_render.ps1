param([ValidateSet('01','02','03','04','05','06','07','08','09','10','11','13')][string]$Study='03',[ValidateRange(100,10000)][int]$DistanceCm=253,[ValidateSet('Man_Standard','Man_Heavy','Man_Elder','Woman_Young','Woman_Elder','Youth')][string]$Variant='Man_Standard',[ValidateSet('Front','Right','Rear','Left')][string]$View='Front',[switch]$Sweep,[switch]$ShadowParity,[switch]$NoNormalDetail,[switch]$NormalCorrection,[ValidateSet('Walk','Idle','Transition')][string]$Mode='Walk')
$ErrorActionPreference = 'Stop'
if($Mode -ne 'Walk' -and ($Study -notin @('11','13') -or $Variant -notin @('Man_Elder','Woman_Young') -or $Sweep -or $NoNormalDetail -or $NormalCorrection)){throw 'Idle/Transition review requires Study11/13 Elder/Woman without other diagnostics'}
if($NormalCorrection -and ($Study -ne '10' -or $Sweep -or $Variant -notin @('Man_Elder','Woman_Young'))){throw 'NormalCorrection is a Study10 four-phase diagnostic only'}
$root = (Split-Path -Parent $PSScriptRoot).Replace('\','/')
$busy = @(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3,AutomationTool -ErrorAction SilentlyContinue)
$busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
if(([long](Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory*1KB) -lt 6GB){throw 'Isolated audit needs 6 GiB free commit'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$folder="$root/SourceAssets/perf-review/crowd-vat/ResidentStudy$Study"
if($Variant -ne 'Man_Standard'){$folder+='/Cast/'+$Variant}
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$log="$folder/resident-crowd-render-run-$stamp.log"
$receipt="$folder/resident-crowd-render-run-$stamp.json"
if(Test-Path -LiteralPath $receipt){throw 'Fresh audit receipt required'}
$before=@(Get-ChildItem -LiteralPath $folder -Filter 'render-*.json' -File | Where-Object {$_.Name -match '^render-\d{8}T\d{12}Z\.json$'} | Select-Object -ExpandProperty FullName)
$record=[ordered]@{status='starting';scope='Isolated native GPU static pose A/B; no saves';startedUtc=$stamp;log=$log;minimumStartCommitBytes=6GB;maximumPrivateBytes=4GB;reserveCommitBytes=2GB;peakPrivateBytes=0}
function Save-Receipt {$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receipt -Encoding utf8}
Save-Receipt
$exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$arguments=@(('"'+$root+'/MikdashCourtyardV3.uproject"'),'-run=pythonscript',('-script="'+$root+'/Scripts/capture_resident_crowd.py"'),'-AllowCommandletRendering','-RenderOffscreen','-EnablePlugins=AnimToTexture,GeometryScripting','-DisablePlugins=MetaHumanCharacter,MetaHumanSDK','-unattended','-nosplash','-nosound','-notraceserver','-NoMetaHumanAccountPortalLoginFallback','-NoAsyncLoadingThread','-asyncstaticmeshcompilationmaxconcurrency=1',('-abslog="'+$log+'"'))

$arguments += ('-ResidentCrowdStudy='+$Study)
$arguments += ('-ResidentCrowdVariant='+$Variant)
$arguments += ('-ResidentCrowdView='+$View)
$arguments += ('-ResidentCrowdMode='+$Mode)
if($Sweep){$arguments += '-ResidentCrowdSweep'}
if($ShadowParity){$arguments += '-ResidentCrowdShadowParity'}
if($NoNormalDetail){$arguments += '-ResidentCrowdNoNormalDetail'}
if($NormalCorrection){$arguments += '-ResidentCrowdNormalCorrection'}
if($PSBoundParameters.ContainsKey('DistanceCm')){$arguments += ('-ResidentCrowdDistanceCm='+$DistanceCm)}
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
    $outputs=@(Get-ChildItem -LiteralPath $folder -Filter 'render-*.json' -File | Where-Object {$_.Name -match '^render-\d{8}T\d{12}Z\.json$'} | Where-Object {$_.FullName -notin $before})
    if($outputs.Count -ne 1){throw 'Expected one fresh near candidate receipt'}
    $result=Get-Content -LiteralPath $outputs[0].FullName -Raw | ConvertFrom-Json
    $expectedStatus='captured-review-pending'
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
