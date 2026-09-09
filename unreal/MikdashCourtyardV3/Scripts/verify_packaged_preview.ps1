<#
Bounded packaged startup verification, not interactive/visual acceptance.
Explicit child executable only. No map override: checks the real packaged default.
No UI input. -ShowWindow explicitly requests a visible window and optional screenshot.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExePath,
    [Parameter(Mandatory=$true)][string]$OutputDir,
    [ValidateRange(20,300)][int]$WaitSeconds=120,
    [ValidateRange(1,30)][int]$SettleSeconds=8,
    [switch]$ShowWindow
)
$ErrorActionPreference='Stop'
$expectedMap='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
$exe=(Resolve-Path -LiteralPath $ExePath).Path
if ($exe -notmatch '[\\/]MikdashCourtyardV3[\\/]Binaries[\\/]Win64[\\/]MikdashCourtyardV3\.exe$') { throw 'Explicit packaged child executable required, not bootstrap' }
$out=[IO.Path]::GetFullPath($OutputDir)
if (Test-Path -LiteralPath $out) { throw 'Output directory must not exist' }
$busy=@(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(MikdashCourtyardV3|UnrealEditor|UnrealEditor-Cmd|AutomationTool|UnrealBuildTool)$' })
if ($busy.Count) { throw 'Existing game/editor/build process present; preserving it' }
New-Item -ItemType Directory -Path $out | Out-Null
$log=Join-Path $out 'runtime.log'
$receiptPath=Join-Path $out 'receipt.json'
$prefix='AstraProbe_Package_'+[guid]::NewGuid().ToString('N')
$project=Split-Path -Parent $PSScriptRoot
$packageProject=Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $exe))
$saveRoots=@((Join-Path $project 'Saved\SaveGames'),(Join-Path $packageProject 'Saved\SaveGames'),(Join-Path $env:LOCALAPPDATA 'MikdashCourtyardV3\Saved\SaveGames')) | Select-Object -Unique
function SaveHashes {
    $result=@{}
    foreach($root in $saveRoots) {
        if(Test-Path -LiteralPath $root) {
            foreach($file in Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.sav') {
                if(-not $file.Name.StartsWith($prefix,[StringComparison]::Ordinal)) { $result[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLower() }
            }
        }
    }
    return $result
}
$before=SaveHashes
$report=[ordered]@{status='started';childExe=$exe;childSha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLower();expectedDefaultMap=$expectedMap;savePrefix=$prefix;originalSaveHashesBefore=$before;errors=@();scope='Bounded startup/default-map/log smoke only. Controls, Kotel walking, rendered photo quality and audio are not verified.';screenshotAcceptance='Not reviewed';startedUtc=(Get-Date).ToUniversalTime().ToString('o')}
function WriteReceipt { $report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $receiptPath -Encoding UTF8 }
$proc=$null
try {
    # Quoted complete ini arguments preserve slash-qualified config class names.
    $arguments="-windowed -ResX=1280 -ResY=720 -log -abslog=`"$log`" `"-ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=$prefix,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=$prefix`""
    $report.arguments=$arguments
    $style=if($ShowWindow){'Normal'}else{'Hidden'}
    $proc=Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory (Split-Path -Parent $exe) -WindowStyle $style -PassThru
    $report.pid=$proc.Id;WriteReceipt
    $clock=[Diagnostics.Stopwatch]::StartNew();$ready=$false
    while($clock.Elapsed.TotalSeconds -lt $WaitSeconds) {
        Start-Sleep -Milliseconds 500;$proc.Refresh()
        if($proc.HasExited){throw 'Child exited before startup acceptance'}
        $text=if(Test-Path -LiteralPath $log){Get-Content -LiteralPath $log -Raw}else{''}
        if($text -match 'LogInit: Display: Game Engine Initialized' -and $text -match 'MIKDASH_MENU_OPEN') { $ready=$true;break }
    }
    if(-not $ready){throw 'Startup markers missing before deadline'}
    $report.readySeconds=$clock.Elapsed.TotalSeconds
    Start-Sleep -Seconds $SettleSeconds
    $proc.Refresh();if($proc.HasExited){throw 'Child exited during settling'}
    if($ShowWindow) {
        # Proven screen-region method; does not prove unobscured game pixels.
        Add-Type -AssemblyName System.Drawing
        Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public static class AstraPreviewWindow {
 [StructLayout(LayoutKind.Sequential)] public struct RECT {public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out RECT r);
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
'@
        [void][AstraPreviewWindow]::SetProcessDPIAware()
        $handle=$proc.MainWindowHandle
        $rect=New-Object AstraPreviewWindow+RECT
        if($handle -eq [IntPtr]::Zero -or -not [AstraPreviewWindow]::GetWindowRect($handle,[ref]$rect)){throw 'No visible window rectangle available'}
        $width=$rect.Right-$rect.Left;$height=$rect.Bottom-$rect.Top
        if($width -lt 100 -or $height -lt 100){throw 'Window rectangle too small'}
        $bitmap=New-Object System.Drawing.Bitmap $width,$height
        $graphics=[Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.CopyFromScreen($rect.Left,$rect.Top,0,0,(New-Object Drawing.Size $width,$height))
            $image=Join-Path $out 'startup.png';$bitmap.Save($image,[Drawing.Imaging.ImageFormat]::Png)
            $report.screenshot=$image;$report.screenshotSha256=(Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLower()
            $report.screenshotAcceptance='Screen-region capture may be obscured or console; inspect manually. Not visual acceptance.'
        } finally {$graphics.Dispose();$bitmap.Dispose()}
    }
    $report.status='startup_observed_pending_log_and_preservation_checks'
} catch {
    $report.status='failed';$report.errors+= $_.Exception.Message
} finally {
    if($null -ne $proc) {
        try {
            $proc.Refresh()
            if(-not $proc.HasExited) {
                [void]$proc.CloseMainWindow()
                if(-not $proc.WaitForExit(15000)) {
                    Stop-Process -Id $proc.Id -Force
                    [void]$proc.WaitForExit(10000)
                    $report.errors+='Own child required forced termination'
                }
            }
            $proc.Refresh();$report.exitCode=$proc.ExitCode
            if($proc.ExitCode -ne 0){$report.errors+='Nonzero child exit code'}
        } catch {$report.errors+='Teardown: '+$_.Exception.Message}
    }
    try {
        $after=SaveHashes;$report.originalSaveHashesAfter=$after
        $changes=@((@($before.Keys)+@($after.Keys)) | Select-Object -Unique | Where-Object {$before[$_] -ne $after[$_]})
        $report.originalSavesUnchanged=($changes.Count -eq 0);$report.saveDifferences=$changes
        if($changes.Count){$report.errors+='Original saves changed'}
        $text=if(Test-Path -LiteralPath $log){Get-Content -LiteralPath $log -Raw}else{''}
        $loadLines=@($text -split '\r?\n' | Where-Object {$_ -match 'LogLoad: LoadMap:'})
        $report.defaultMapLoadLines=$loadLines
        $mapPattern='LogLoad: LoadMap:\s*'+[regex]::Escape($expectedMap)+'(?:\?|\s|$)'
        $report.correctDefaultMap=($loadLines.Count -gt 0 -and $loadLines[0] -match $mapPattern)
        if(-not $report.correctDefaultMap){$report.errors+='First loaded map is not the exact Selected48 default'}
        $bad=@($text -split '\r?\n' | Where-Object {$_ -match 'Fatal error|Assertion failed|Unhandled Exception|LogWindows: Error|LogMaterial: (Error|Fatal)|LogShaderCompilers: (Error|Fatal)|LogMaterial: Warning: Material failed to compile|missing the usage flag Nanite|Default Material will be used|default material will be used'})
        $report.rejectedLogLines=$bad
        if($bad.Count){$report.errors+='Fatal/shader/default-material warning detected'}
        if($text -match 'MIKDASH_MENU_RESUME'){$report.errors+='Unexpected resume without test input'}
        if(Test-Path -LiteralPath $log){$report.logSha256=(Get-FileHash -LiteralPath $log -Algorithm SHA256).Hash.ToLower()}
        if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLower() -ne $report.childSha256){$report.errors+='Child executable changed'}
    } catch {$report.errors+='Final verification: '+$_.Exception.Message}
    $report.status=if($report.errors.Count -eq 0 -and $report.status -eq 'startup_observed_pending_log_and_preservation_checks'){'passed_startup_smoke_only'}else{'failed'}
    $report.finishedUtc=(Get-Date).ToUniversalTime().ToString('o');WriteReceipt
}
Write-Output $receiptPath
if($report.status -ne 'passed_startup_smoke_only'){exit 1}
