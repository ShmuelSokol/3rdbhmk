<# Owned Entry-only GPU study. No full map cook/save and no desktop input. #>
param([ValidateRange(90,360)][int]$TimeoutSeconds=240)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$review=Join-Path $project 'SourceAssets/context-review/KotelCutClosureV1'
$exe=[IO.Path]::GetFullPath('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,MikdashCourtyardV3 -ErrorAction SilentlyContinue)
$busy+=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'AutomationTool|UnrealBuildTool'})
if($busy.Count){throw 'Native slot occupied'}
$memory=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
if(($memory.CommitLimit-$memory.CommittedBytes) -lt 9GB){throw 'GPU Entry study requires 9GiB commit headroom'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$receipt=Join-Path $review "launch-$stamp.json"
$log=Join-Path $review "launch-$stamp.log"
$prior=@(Get-ChildItem $review -Filter 'native-study-*.json' | Select-Object -ExpandProperty FullName)
$r=[ordered]@{status='starting';startedUtc=(Get-Date).ToUniversalTime().ToString('o');scope='Unsaved Engine Entry seam A/B/A study, not production integration';peakPrivateBytes=0;peakWorkingSetBytes=0;minimumCommitFreeBytes=($memory.CommitLimit-$memory.CommittedBytes)}
function Save-Receipt {$r | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receipt -Encoding utf8}
Save-Receipt
$script=Join-Path $review 'native_study.py'
$launchArgs=@(('"'+(Join-Path $project 'MikdashCourtyardV3.uproject')+'"'),'/Engine/Maps/Entry','-KotelClosureStudy','-EnablePlugins=GeometryScripting','-unattended','-nosplash','-nosound','-NoAsyncLoadingThread','-AsyncCompilationMaxConcurrency=1',('-ExecCmds="py '+$script.Replace('\','/')+'"'),('-abslog="'+$log+'"'))
$proc=$null
try {
    $proc=Start-Process -FilePath $exe -ArgumentList $launchArgs -WorkingDirectory $project -WindowStyle Hidden -PassThru
    $r.pid=$proc.Id;$r.arguments=$launchArgs;$r.status='running';Save-Receipt
    $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
    while((Get-Date) -lt $deadline){
        Start-Sleep -Seconds 2; $proc.Refresh(); if($proc.HasExited){break}
        $r.peakPrivateBytes=[math]::Max([long]$r.peakPrivateBytes,[long]$proc.PrivateMemorySize64)
        $r.peakWorkingSetBytes=[math]::Max([long]$r.peakWorkingSetBytes,[long]$proc.WorkingSet64)
        $memory=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
        $free=$memory.CommitLimit-$memory.CommittedBytes
        $r.minimumCommitFreeBytes=[math]::Min([long]$r.minimumCommitFreeBytes,[long]$free)
        # GPU editor startup measured 4.67GiB private before study setup. The former
        # 4GiB ceiling stopped startup with >5GiB still free; retain a 2GiB reserve.
        if($proc.PrivateMemorySize64 -gt 6.5GB -or $free -lt 2GB){throw 'Study watchdog memory reserve reached'}
    }
    if(!$proc.HasExited){throw 'Study watchdog timeout'}
    $proc.WaitForExit();$r.exitCode=$proc.ExitCode
    if($proc.ExitCode -ne 0){throw "Editor exited $($proc.ExitCode)"}
    $fresh=@(Get-ChildItem $review -Filter 'native-study-*.json' | Where-Object {$prior -notcontains $_.FullName})
    if($fresh.Count -ne 1){throw 'Expected one fresh study receipt'}
    $native=Get-Content $fresh[0].FullName -Raw | ConvertFrom-Json
    $r.nativeReceipt=$fresh[0].FullName;$r.nativeStatus=$native.status
    $r.captureCount=@($native.captures).Count;$r.nativeErrors=$native.errors
    if($native.status -ne 'captured_visual_review_pending' -or @($native.dirtyProductionAfter).Count -or $native.errors.Count -or !$native.allProductionAssetsUnchanged -or $r.captureCount -ne 3){throw 'Native study incomplete; inspect preserved receipt'}
    $r.status='captured-ABA-pixel-review-pending'
} catch {$r.status='failed';$r.error=$_.Exception.Message}
finally {
    if($proc){$proc.Refresh();if(!$proc.HasExited){
        if((Get-Process -Id $proc.Id).Path -ne $exe){throw 'Owned process path differs; refusing stop'}
        $proc | Stop-Process -Force;$r.forcedStop=$true
    }}
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o');Save-Receipt
}
Write-Output "$($r.status): $receipt"
if($r.status -eq 'failed'){exit 1}
