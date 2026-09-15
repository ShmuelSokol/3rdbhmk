<#
    ResidentV4: every engine step, one at a time, each waiting for the native slot.
    Launch DETACHED:
      Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
        '-File','C:\Mikdash\Working-5.8\MikdashCourtyardV3\Scripts\run_resident_v4_engine.ps1','-Steps','import,apply48,revert48,apply50'
    Progress: SourceAssets\characters-review\ResidentV4\engine-runner-progress.json (poll it).
    Steps: import, apply48, revert48, apply50, editorbuild, cook, movie:<view>
    The slot is free only when no UnrealEditor / UnrealEditor-Cmd / MikdashCourtyardV3 runs AND no dotnet.exe
    runs AutomationTool or UnrealBuildTool (UE 5.8 runs both as dotnet; Get-Process by name never sees them).
#>
param([string]$Steps = 'import', [int]$WaitMinutes = 360, [double]$NeedGB = 4.0, [string]$Label = 'cp23')
$ErrorActionPreference = 'Stop'
$project = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
$uproject = Join-Path $project 'MikdashCourtyardV3.uproject'
$editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$script = Join-Path $project 'Scripts\release_resident_v4.py'
$logs = 'C:\Users\shmue\AppData\Local\Temp\claude\C--Mikdash\5fc175f9-915c-4dbd-a939-b7c7ecc4da9b\scratchpad'
$progress = Join-Path $project 'SourceAssets\characters-review\ResidentV4\engine-runner-progress.json'
$receipts = Join-Path $project 'SourceAssets\characters-review\ResidentV4\engine'
New-Item -ItemType Directory -Force -Path $receipts | Out-Null
$todo = $Steps.Split(',') | ForEach-Object { $_.Trim() }
$state = [ordered]@{ started = (Get-Date).ToUniversalTime().ToString('o'); steps = [ordered]@{}; status = 'running'; todo = $todo }
if (Test-Path -LiteralPath $progress) {
    try { $old = Get-Content -LiteralPath $progress -Raw | ConvertFrom-Json; if ($old.archive) { $state.archive = $old.archive } } catch {}
}
function Save { ($state | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $progress -Encoding utf8 }
function Free-GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1) }
function Busy {
    $b = @(Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3, AutomationTool, UnrealBuildTool -ErrorAction SilentlyContinue |
           Select-Object -ExpandProperty ProcessName)
    $b += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' } |
            ForEach-Object { if ($_.CommandLine -match 'AutomationTool') { 'dotnet(UAT)' } else { 'dotnet(UBT)' } })
    return @($b | Select-Object -Unique)
}
function Wait-Slot([string]$step) {
    $deadline = (Get-Date).AddMinutes($WaitMinutes)
    while ($true) {
        $busy = Busy
        if ($busy.Count -eq 0 -and (Free-GB) -ge $NeedGB) {
            Start-Sleep -Seconds 20            # another agent may be between two chained steps
            $busy = Busy
            if ($busy.Count -eq 0) { return }
        }
        $state.steps[$step] = @{ status = 'waiting_for_slot'; busy = ($busy -join ','); freeGB = (Free-GB); utc = (Get-Date).ToUniversalTime().ToString('o') }
        Save
        if ((Get-Date) -gt $deadline) { throw "slot never freed for $step" }
        Start-Sleep -Seconds 30
    }
}
function Newest([string]$pattern, [datetime]$after) {
    Get-ChildItem -LiteralPath $receipts -Filter $pattern -EA SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $after } | Sort-Object LastWriteTime | Select-Object -Last 1
}
function Run-Editor([string]$step, [string]$mode, [string]$pattern, [string]$okPrefix) {
    Wait-Slot $step
    $t0 = Get-Date
    $log = Join-Path $logs ("resident-v4-$step-" + $t0.ToString('HHmmss') + ".log")
    $argline = "`"$uproject`" -ExecutePythonScript=$($script.Replace('\','/')) $mode -unattended -nullrhi -NoSplash -abslog=`"$log`""
    $state.steps[$step] = @{ status = 'running'; startedUtc = $t0.ToUniversalTime().ToString('o'); log = $log; args = $argline }
    Save
    $p = Start-Process -FilePath $editor -ArgumentList $argline -PassThru -WindowStyle Hidden
    $p.WaitForExit()
    $r = Newest $pattern $t0
    $status = if ($r) { (Get-Content -LiteralPath $r.FullName -Raw | ConvertFrom-Json).status } else { 'no_receipt' }
    $state.steps[$step] = @{ status = $status; receipt = if ($r) { $r.FullName } else { $null }; exitCode = $p.ExitCode; log = $log }
    Save
    if (-not ($status -like "$okPrefix*")) { throw "$step ended with $status" }
}
function Latest-Archive { (Get-ChildItem 'C:\Mikdash\Builds' -Directory -Filter "Checkpoint-$Label-*" | Sort-Object LastWriteTime | Select-Object -Last 1) }
try {
    foreach ($s in $todo) {
        if ($s -eq 'import') { Run-Editor $s '-RV4Import' 'resident-v4-import-all-*.json' 'imported_saved' }
        elseif ($s -eq 'importrevert') { Run-Editor $s '-RV4ImportRevert' 'resident-v4-import-revert-all-*.json' 'import_reverted' }
        elseif ($s -eq 'apply48') { Run-Editor $s '-RV4Apply -RV4Target=Candidate48' 'resident-v4-apply-Candidate48-*.json' 'apply_' }
        elseif ($s -eq 'revert48') { Run-Editor $s '-RV4RevertAndReapply -RV4Target=Candidate48' 'resident-v4-apply-Candidate48-*.json' 'apply_' }
        elseif ($s -eq 'apply50') { Run-Editor $s '-RV4Apply -RV4Target=Main50' 'resident-v4-apply-Main50-*.json' 'apply_' }
        elseif ($s -eq 'editorbuild') {
            Wait-Slot $s
            $bat = Join-Path $logs 'rv4-editor-build.bat'
            $blog = Join-Path $logs ('rv4-editor-build-' + (Get-Date).ToString('HHmmss') + '.log')
            @('@echo off', ('call "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" MikdashCourtyardV3Editor Win64 Development -Project="' + $uproject + '" -WaitMutex -NoHotReload'), 'exit /b %ERRORLEVEL%') |
                Set-Content -LiteralPath $bat -Encoding ascii
            $state.steps[$s] = @{ status = 'running'; log = $blog }
            Save
            & $env:COMSPEC /d /c $bat *> $blog
            $code = $LASTEXITCODE
            $state.steps[$s] = @{ status = if ($code -eq 0) { 'built' } else { 'failed' }; exitCode = $code; log = $blog }
            Save
            if ($code -ne 0) { throw "editor build failed ($code)" }
        }
        elseif ($s -eq 'cook') {
            Wait-Slot $s
            $state.steps[$s] = @{ status = 'running'; startedUtc = (Get-Date).ToUniversalTime().ToString('o') }
            Save
            $out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $project 'Checkpoint-Build.ps1') -Label $Label 2>&1 | Out-String
            $arch = Latest-Archive
            $state.steps[$s] = @{ status = if ($arch) { 'archived' } else { 'no_archive' }; archive = if ($arch) { $arch.FullName } else { $null }; tail = ($out -split "`n" | Select-Object -Last 20) -join "`n" }
            Save
            if (-not $arch) { throw 'cook produced no archive' }
            $state.archive = $arch.FullName
        }
        elseif ($s -like 'movie:*') {
            # movie:<view>|<BugItGo>|<recordSeconds>
            $parts = $s.Substring(6).Split('|')
            Wait-Slot $s
            $arch = if ($state.archive) { $state.archive } else { (Latest-Archive).FullName }
            $state.steps[$s] = @{ status = 'running'; archive = $arch }
            Save
            $out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $project 'Scripts\capture_people_walk_movie.ps1') `
                -Archive $arch -Label $Label -View $parts[0] -Go $parts[1] -SettleSeconds 0 -RecordSeconds ([int]$parts[2]) -FixedFps 10 -ResX 1920 -ResY 1080 2>&1 | Out-String
            $state.steps[$s] = @{ status = 'done'; out = $out.Trim() }
            Save
        }
        else { throw "unknown step $s" }
    }
    $state.status = 'done'
} catch {
    $state.status = 'failed'
    $state.error = $_.Exception.Message
} finally {
    $state.finished = (Get-Date).ToUniversalTime().ToString('o')
    Save
}
