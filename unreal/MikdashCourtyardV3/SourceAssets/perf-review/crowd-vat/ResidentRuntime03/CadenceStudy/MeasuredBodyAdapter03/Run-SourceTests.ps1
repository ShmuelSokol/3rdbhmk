param([Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]{1,32}$')][string]$RunId)
$ErrorActionPreference='Stop'
$timer=[Diagnostics.Stopwatch]::StartNew()
$out=Join-Path 'C:/Mikdash/Verification' ('MeasuredBodyAdapter03-'+$RunId)
if(Test-Path -LiteralPath $out){throw 'Fresh source-test directory required'}
$marker='C:/Mikdash/Working-5.8/MikdashCourtyardV3/SourceAssets/context-review/HaramThresholdSidesV1/native-slot-blocked.json'
if(Test-Path -LiteralPath $marker){throw 'Shared execution slot unresolved'}
$busy=@(Get-Process UnrealEditor,UnrealEditor-Cmd,ShaderCompileWorker,cl,link -ErrorAction SilentlyContinue)
if($busy.Count){throw 'Serial execution slot occupied; no foreign cleanup'}
$memory=Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 3
if($null -eq $memory.FreeVirtualMemory){throw 'Unknown source-fixture free commit'}
$free=[long]$memory.FreeVirtualMemory*1KB
if($free -lt 2GB){throw 'Existing 2GiB reserve unavailable for source fixture'}
# Standalone MSVC fixture only. No UE/UBT command, editor start or editor guard change.
$helper=Join-Path (Split-Path $PSScriptRoot -Parent) 'Study13IdlePositionExport02/OwnedChildJob.cs'
if((Get-FileHash -LiteralPath $helper).Hash.ToLowerInvariant() -cne '0ef998314f3e68976c851e055d9aafe0e56e935334f1556a44e5e683a05fcec4'){throw 'Owned Job helper differs'}
$null=New-Item -ItemType Directory -Path $out
$null=New-Item -ItemType Directory -Path "$out/baseline"
$pins=[ordered]@{}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File){
    if($file.Extension -notin '.h','.cpp'){continue}
    $relative=[IO.Path]::GetRelativePath($PSScriptRoot,$file.FullName)
    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $out $relative)
    $pins[$relative]=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()
}
$commands=@'
@echo on
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /O2 MeasuredControllerTest.cpp /Fe:MeasuredControllerTest.exe /Fo:MeasuredControllerTest.obj
if errorlevel 1 exit /b 1
MeasuredControllerTest.exe
exit /b %errorlevel%
'@
[IO.File]::WriteAllText("$out/compile.cmd",($commands.Replace("`r`n","`n").Replace("`n","`r`n")+"`r`n"))
$shim=@'
$ErrorActionPreference='Stop'
$s=[Diagnostics.ProcessStartInfo]::new('C:\Windows\System32\cmd.exe','/d /c compile.cmd')
$s.WorkingDirectory=$PSScriptRoot;$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.WindowStyle='Hidden'
$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true
$p=[Diagnostics.Process]::Start($s)
$stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
if(-not $p.WaitForExit(45000)){throw 'Compiler shim deadline; parent owned Job performs cleanup'}
[IO.File]::WriteAllText("$PSScriptRoot/compiler-local.log",$stdout.Result+$stderr.Result)
Write-Output ($stdout.Result+$stderr.Result)
exit $p.ExitCode
'@
[IO.File]::WriteAllText("$out/compile-shim.ps1",$shim)
Add-Type -Path $helper
$record=[ordered]@{status='failed';scope='standalone MSVC C++ source fixture; no UE/UBT';sourcePins=$pins;cleanupConfirmed=$false;slotBlocked=$false;peakJobBytes=0L;drain=@()}
$token=[guid]::NewGuid().ToString('N');$owned=$null;$acquired=$false
try {
    if($timer.Elapsed.TotalSeconds -ge 50){throw 'Source-test setup deadline'}
    $bytes=[Text.Encoding]::UTF8.GetBytes((@{owner='MeasuredBodyAdapter03';token=$token;run=$out;status='ownership_unresolved'}|ConvertTo-Json))
    $stream=[IO.File]::Open($marker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    $acquired=$true
    if([KohenReviewGuard.OwnedChildJob]::AvailableCommit() -lt 2GB){$record.cleanupConfirmed=$true;throw '2GiB reserve unavailable'}
    $hostExe='C:/Users/shmue/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    $owned=[KohenReviewGuard.OwnedChildJob]::new($hostExe,[string[]]@('-NoProfile','-NonInteractive','-File',"$out/compile-shim.ps1"),$out,"$out/local-only.log",[ulong]4GB)
    while($true){
        if($timer.Elapsed.TotalSeconds -ge 54){throw '60s total deadline, cleanup reserved'}
        $s=$owned.Poll();$free=[long][KohenReviewGuard.OwnedChildJob]::AvailableCommit()
        $record.peakJobBytes=[Math]::Max($record.peakJobBytes,[long][Math]::Max($s.PrivateBytes,$s.PeakJobBytes))
        if($s.RootExited){$record.drain+=@{elapsed=$timer.Elapsed.TotalSeconds;exitCode=$s.ExitCode;active=$s.ActiveProcesses}}
        if($free -lt 2GB -or $record.peakJobBytes -ge 4GB){throw 'Owned source fixture memory guard'}
        if($timer.Elapsed.TotalSeconds -ge 54){throw 'Work deadline reached'}
        if($s.RootExited){if($s.ExitCode -ne 0){throw "Compiler/fixture exit $($s.ExitCode)"};if($s.ActiveProcesses -eq 0){$record.status='source_fixture_exit_zero';break}}
        Start-Sleep -Milliseconds ([int][Math]::Max(1,[Math]::Min(100,[Math]::Floor((54-$timer.Elapsed.TotalSeconds)*1000))))
    }
} catch {$record.error=$_.Exception.Message} finally {
    if($owned){
        try{$record.cleanupConfirmed=$owned.StopWithinFiveSeconds();$record.cleanupError=$owned.CleanupError}
        catch{$record.cleanupConfirmed=$false;$record.cleanupError=$_.Exception.Message}
        finally{try{$owned.Dispose()}catch{$record.cleanupConfirmed=$false;$record.cleanupError=$_.Exception.Message}}
    }
    if($acquired){
        try{
            $saved=Get-Content -LiteralPath $marker -Raw|ConvertFrom-Json
            if($record.cleanupConfirmed -and $saved.owner -ceq 'MeasuredBodyAdapter03' -and $saved.token -ceq $token){[IO.File]::Delete($marker)}else{$record.slotBlocked=$true}
        }catch{$record.slotBlocked=$true;$record.markerError=$_.Exception.Message}
    }
    foreach($name in $pins.Keys){if((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $name)).Hash.ToLowerInvariant() -cne $pins[$name]){$record.status='source_changed'}}
    if(-not $record.cleanupConfirmed -or $record.slotBlocked){$record.status='cleanup_unconfirmed'}
    $record.elapsedSeconds=$timer.Elapsed.TotalSeconds
    if($record.elapsedSeconds -ge 60){$record.status='deadline_exceeded'}
    [IO.File]::WriteAllText("$out/receipt.json",($record|ConvertTo-Json -Depth 12))
}
Get-Content -LiteralPath "$out/local-only.log"
Write-Output "Receipt: $out/receipt.json"
if($record.status -ne 'source_fixture_exit_zero'){throw "Source tests rejected: $($record.status)"}
