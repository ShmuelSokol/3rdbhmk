<#
    Kohen Gadol V1: every engine step, one at a time, each waiting for the native slot.
    Launch DETACHED:
      Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
        '-File','C:\Mikdash\Working-5.8\MikdashCourtyardV3\Scripts\run_kohen_gadol_v1_engine.ps1','-Steps','all'
    Progress: SourceAssets\characters-review\KohenGadolV1\engine-runner-progress.json (poll it).
    Steps: import, apply48, revert48, apply50, cook, movie-tend, movie-walk   (or 'all', or a comma list)
    Every step refuses to start while UnrealEditor / UnrealEditor-Cmd / AutomationTool / UnrealBuildTool /
    MikdashCourtyardV3 is running, and stops the chain on the first failed receipt.
#>
param([string]$Steps = 'all', [int]$WaitMinutes = 240, [double]$NeedGB = 4.0)
$ErrorActionPreference = 'Stop'
$project = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
$uproject = Join-Path $project 'MikdashCourtyardV3.uproject'
$editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$script = Join-Path $project 'Scripts\release_kohen_gadol_v1.py'
$logs = 'C:\Users\shmue\AppData\Local\Temp\claude\C--Mikdash\5fc175f9-915c-4dbd-a939-b7c7ecc4da9b\scratchpad'
$progress = Join-Path $project 'SourceAssets\characters-review\KohenGadolV1\engine-runner-progress.json'
$receipts = Join-Path $project 'SourceAssets\service-review'
$all = @('import', 'apply48', 'revert48', 'apply50', 'cook', 'movie-tend', 'movie-walk')
$todo = if ($Steps -eq 'all') { $all } else { $Steps.Split(',') | ForEach-Object { $_.Trim() } }
$state = [ordered]@{ started = (Get-Date).ToUniversalTime().ToString('o'); steps = [ordered]@{}; status = 'running' }
function Save { ($state | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $progress -Encoding utf8 }
function Free-GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1) }
function Wait-Slot([string]$step) {
    $deadline = (Get-Date).AddMinutes($WaitMinutes)
    while ($true) {
        $busy = Get-Process UnrealEditor, UnrealEditor-Cmd, MikdashCourtyardV3, AutomationTool, UnrealBuildTool -ErrorAction SilentlyContinue
        if (-not $busy -and (Free-GB) -ge $NeedGB) { return }
        $state.steps[$step] = @{ status = 'waiting_for_slot'; busy = (@($busy | Select-Object -ExpandProperty ProcessName -Unique) -join ','); freeGB = (Free-GB) }
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
    $log = Join-Path $logs ("kohen-gadol-$step.log")
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
try {
    foreach ($s in $todo) {
        switch ($s) {
            'import'   { Run-Editor $s '-KohenGadolImport' 'kohen-gadol-import-SK_KohenGadol_V1-*.json' 'imported_saved' }
            'reimport' { Run-Editor $s '-KohenGadolReimport' 'kohen-gadol-reimport-SK_KohenGadol_V1-*.json' 'reimported_saved' }
            'apply48'  { Run-Editor $s '-KohenGadolApply -KohenTarget=Candidate48' 'kohen-gadol-apply-Candidate48-*.json' 'apply_' }
            'revert48' { Run-Editor $s '-KohenGadolRevertAndReapply -KohenTarget=Candidate48' 'kohen-gadol-apply-Candidate48-*.json' 'apply_' }
            'apply50'  { Run-Editor $s '-KohenGadolApply -KohenTarget=Main50' 'kohen-gadol-apply-Main50-*.json' 'apply_' }
            'cook' {
                Wait-Slot $s
                $state.steps[$s] = @{ status = 'running'; startedUtc = (Get-Date).ToUniversalTime().ToString('o') }
                Save
                $out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $project 'Checkpoint-Build.ps1') -Label cp18 2>&1 | Out-String
                $arch = Get-ChildItem 'C:\Mikdash\Builds' -Directory -Filter 'Checkpoint-cp18-*' | Sort-Object LastWriteTime | Select-Object -Last 1
                $state.steps[$s] = @{ status = if ($arch) { 'archived' } else { 'no_archive' }; archive = if ($arch) { $arch.FullName } else { $null }; tail = ($out -split "`n" | Select-Object -Last 15) -join "`n" }
                Save
                if (-not $arch) { throw 'cook produced no archive' }
                $state.archive = $arch.FullName
            }
            'movie-tend' {
                Wait-Slot $s
                $arch = if ($state.archive) { $state.archive } else { (Get-ChildItem 'C:\Mikdash\Builds' -Directory -Filter 'Checkpoint-cp18-*' | Sort-Object LastWriteTime | Select-Object -Last 1).FullName }
                $state.steps[$s] = @{ status = 'running'; archive = $arch }
                Save
                $out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $project 'Scripts\capture_people_walk_movie.ps1') `
                    -Archive $arch -Label cp18 -View kohen-tend-close -Go '-5255 60 1045 -6 108 0' -SettleSeconds 0 -RecordSeconds 900 -FixedFps 10 -ResX 1920 -ResY 1080 2>&1 | Out-String
                $state.steps[$s] = @{ status = 'done'; out = $out.Trim() }
                Save
            }
            'movie-walk' {
                Wait-Slot $s
                $arch = if ($state.archive) { $state.archive } else { (Get-ChildItem 'C:\Mikdash\Builds' -Directory -Filter 'Checkpoint-cp18-*' | Sort-Object LastWriteTime | Select-Object -Last 1).FullName }
                $state.steps[$s] = @{ status = 'running'; archive = $arch }
                Save
                $out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $project 'Scripts\capture_people_walk_movie.ps1') `
                    -Archive $arch -Label cp18 -View kohen-walk-close -Go '-5060 30 1005 -6 84 0' -SettleSeconds 0 -RecordSeconds 420 -FixedFps 10 -ResX 1920 -ResY 1080 2>&1 | Out-String
                $state.steps[$s] = @{ status = 'done'; out = $out.Trim() }
                Save
            }
            'movie-front' {
                # West of the menorah looking east-north-east: he walks in and tends FACING WEST, so this is
                # the only view that shows the choshen, the tzitz and the bells from the front.
                Wait-Slot $s
                $arch = if ($state.archive) { $state.archive } else { (Get-ChildItem 'C:\Mikdash\Builds' -Directory -Filter 'Checkpoint-cp18-*' | Sort-Object LastWriteTime | Select-Object -Last 1).FullName }
                $state.steps[$s] = @{ status = 'running'; archive = $arch }
                Save
                $out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $project 'Scripts\capture_people_walk_movie.ps1') `
                    -Archive $arch -Label cp18 -View kohen-front -Go '-5530 150 1090 -8 36 0' -SettleSeconds 0 -RecordSeconds 600 -FixedFps 10 -ResX 1920 -ResY 1080 2>&1 | Out-String
                $state.steps[$s] = @{ status = 'done'; out = $out.Trim() }
                Save
            }
            'movie-walk2' {
                # Full-length side view ~3.1 m from his path: head to floor in frame, so the hem is visible
                # through push-off (the first walk camera sat ~2 m off the path and cut him at the shin).
                Wait-Slot $s
                $arch = if ($state.archive) { $state.archive } else { (Get-ChildItem 'C:\Mikdash\Builds' -Directory -Filter 'Checkpoint-cp18-*' | Sort-Object LastWriteTime | Select-Object -Last 1).FullName }
                $state.steps[$s] = @{ status = 'running'; archive = $arch }
                Save
                $out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $project 'Scripts\capture_people_walk_movie.ps1') `
                    -Archive $arch -Label cp18 -View kohen-walk-full -Go '-5000 -60 1050 -12 84 0' -SettleSeconds 0 -RecordSeconds 420 -FixedFps 10 -ResX 1920 -ResY 1080 2>&1 | Out-String
                $state.steps[$s] = @{ status = 'done'; out = $out.Trim() }
                Save
            }
            default { throw "unknown step $s" }
        }
    }
    $state.status = 'done'
} catch {
    $state.status = 'failed'
    $state.error = $_.Exception.Message
} finally {
    $state.finished = (Get-Date).ToUniversalTime().ToString('o')
    Save
}
