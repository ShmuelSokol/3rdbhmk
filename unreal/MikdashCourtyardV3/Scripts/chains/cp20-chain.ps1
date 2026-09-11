<#
  cp20 chain (precinct retaining faces: one-quarry tone V4, close fade 1.0). Launched DETACHED.
  Steps: retone (-PMRetone=V4 -PMFarStrength=1.0 -PMCloseFadeFar=1.0) -> fresh-process verify -> cp20 cook (2 attempts)
  -> capture P1,P2,P3,02,07. Stops on the first failure.
  Slot rule (stricter than cp19b): no engine/game/UAT/UBT process AND no other agent's capture/cook/chain script running,
  continuously for 60 s - so another agent's back-to-back capture views or chained steps are never interleaved.
  Progress: C:\Mikdash\Working-5.8\cp20-chain.log   Status: C:\Mikdash\Working-5.8\cp20-chain.status
#>
param([switch]$SkipRetone, [string]$RetoneReceipt = '', [switch]$SkipCook)
$ErrorActionPreference = 'Stop'
$root = 'C:\Mikdash\Working-5.8'
$proj = "$root\MikdashCourtyardV3"
$uproject = "$proj\MikdashCourtyardV3.uproject"
$ue = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$log = "$root\cp20-chain.log"
$statusFile = "$root\cp20-chain.status"
$macroReceipts = "$proj\SourceAssets\enclosure-review\PrecinctMacroV1"
$script = 'C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_precinct_macro.py'

function Log([string]$m) { $line = (Get-Date).ToUniversalTime().ToString('s') + 'Z  ' + $m; Add-Content -LiteralPath $log -Value $line -Encoding utf8 }
function Status([string]$s) { Set-Content -LiteralPath $statusFile -Value $s -Encoding utf8; Log "STATUS $s" }
function Busy-Reason {
    $p = Get-Process UnrealEditor, UnrealEditor-Cmd, AutomationTool, MikdashCourtyardV3, UnrealBuildTool, ShaderCompileWorker -EA SilentlyContinue
    if ($p) { return 'process ' + (($p | Select-Object -ExpandProperty ProcessName -Unique) -join ',') }
    $me = $PID
    $s = Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe' OR Name='cmd.exe'" -EA SilentlyContinue |
         Where-Object { $_.ProcessId -ne $me -and $_.CommandLine -and
                        $_.CommandLine -match 'capture_frame|Checkpoint-Build|FrameTrial|RunUAT|Build\.bat|-chain\.ps1' -and
                        $_.CommandLine -notmatch 'cp20-chain\.ps1' }
    if ($s) { return 'script ' + (($s | ForEach-Object { ($_.CommandLine -replace '\s+', ' ').Substring(0, [math]::Min(90, $_.CommandLine.Length)) }) -join ' | ') }
    $free = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)
    if ($free -lt 4.0) { return "ram $free GB" }
    return $null
}
function Wait-Slot([int]$minutes = 240) {
    $deadline = (Get-Date).AddMinutes($minutes)
    $freeSince = $null; $lastWhy = ''
    while ($true) {
        $why = Busy-Reason
        if ($why) {
            $freeSince = $null
            if ($why -ne $lastWhy) { Log "slot busy: $why"; $lastWhy = $why }
        } else {
            if (-not $freeSince) { $freeSince = Get-Date }
            if (((Get-Date) - $freeSince).TotalSeconds -ge 60) { Log 'slot free for 60 s'; return }
        }
        if ((Get-Date) -gt $deadline) { throw "slot never freed in $minutes min (last: $lastWhy)" }
        Start-Sleep -Seconds 10
    }
}
function Newest([string]$dir, [string]$filter, [datetime]$after) {
    Get-ChildItem -LiteralPath $dir -Filter $filter -EA SilentlyContinue | Where-Object { $_.LastWriteTime -ge $after } |
        Sort-Object LastWriteTime | Select-Object -Last 1
}
function Run-Engine([string]$name, [string]$engineArgs, [int]$timeoutMin = 45) {
    Wait-Slot
    $abs = "$root\cp20-$name.log"
    $full = "`"$uproject`" $engineArgs -unattended -nullrhi -NoSplash -abslog=`"$abs`""
    Log "RUN $name :: $full"
    $p = Start-Process -FilePath $ue -ArgumentList $full -PassThru -WindowStyle Hidden
    if (-not $p.WaitForExit($timeoutMin * 60 * 1000)) { $p | Stop-Process -Force; throw "$name timed out after $timeoutMin min" }
    Log "EXIT $name code=$($p.ExitCode)"
    return $p.ExitCode
}
function Receipt-Status($file) { if (-not $file) { return $null }; (Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json).status }

try {
    Status 'started'
    $retone = $null
    if (-not $SkipRetone) {
        $s = Get-Date
        [void](Run-Engine 'macro-retoneV4' "-run=pythonscript -script=`"$script`" -PMRetone=V4 -PMFarStrength=1.0 -PMCloseFadeFar=1.0")
        $retone = Newest $macroReceipts 'precinct-macro-retone-V4-*.json' $s
        $st = Receipt-Status $retone
        Log "retone receipt $($retone.FullName) status=$st"
        if ($st -ne 'retoned_visual_acceptance_pending') { Status 'FAILED_retone'; throw "retone status $st" }
    } elseif ($RetoneReceipt) { $retone = Get-Item -LiteralPath $RetoneReceipt }
    if ($retone) {
        $s = Get-Date
        [void](Run-Engine 'macro-verifyV4' "-run=pythonscript -script=`"$script`" -PMVerify=`"$($retone.FullName)`"")
        $vr = Newest $macroReceipts 'precinct-macro-verify-*.json' $s
        $st = Receipt-Status $vr
        Log "verify receipt $($vr.FullName) status=$st"
        if ($st -ne 'verified') { Status 'FAILED_verify'; throw "verify status $st" }
        Status 'retoned_verified'
    }
    if (-not $SkipCook) {
        $archive = $null
        for ($attempt = 1; $attempt -le 2 -and -not $archive; $attempt++) {
            Wait-Slot
            $s = Get-Date
            Log "RUN cook attempt $attempt"
            Status "cooking_attempt_$attempt"
            $p = Start-Process -FilePath 'powershell.exe' -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$proj\Checkpoint-Build.ps1`" -Label cp20 -WaitMinutes 120" -PassThru -WindowStyle Hidden
            if (-not $p.WaitForExit(150 * 60 * 1000)) { $p | Stop-Process -Force; Log 'cook timed out' }
            $job = Get-ChildItem -LiteralPath $root -Directory -Filter 'Checkpoint-cp20-*' | Where-Object { $_.CreationTime -ge $s } | Sort-Object CreationTime | Select-Object -Last 1
            $rc = if ($job) { Join-Path $job.FullName 'checkpoint-receipt.json' } else { $null }
            $st = if ($rc -and (Test-Path $rc)) { (Get-Content $rc -Raw | ConvertFrom-Json) } else { $null }
            Log "cook attempt $attempt job=$($job.FullName) status=$($st.status)"
            if ($st -and $st.status -eq 'checkpoint_playable') { $archive = $st.archive }
            elseif ($job) {
                $uat = Join-Path $job.FullName 'uat.log'
                if (Test-Path $uat) {
                    $hits = Select-String -LiteralPath $uat -Pattern 'ShaderCompileWorker|access violation|M_CrowdVAT|PrecinctMacro|ErrorLog\.txt' -EA SilentlyContinue | Select-Object -First 8
                    foreach ($h in $hits) { Log ('  uat: ' + $h.Line.Trim()) }
                }
            }
        }
        if (-not $archive) { Status 'FAILED_cook'; throw 'cook did not reach checkpoint_playable in two attempts' }
        Log "ARCHIVE $archive"
        Set-Content -LiteralPath "$root\cp20-chain.archive" -Value $archive -Encoding utf8
        Wait-Slot
        Log 'RUN capture'
        Status 'capturing'
        $p = Start-Process -FilePath 'powershell.exe' -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$proj\Scripts\capture_frame_precinct_macro.ps1`" -Archive `"$archive`" -Label cp20 -Views P1,P2,P3,02,07" -PassThru -WindowStyle Hidden
        if (-not $p.WaitForExit(90 * 60 * 1000)) { $p | Stop-Process -Force; Log 'capture timed out' }
        Log "EXIT capture code=$($p.ExitCode)"
        Status 'captured'
    }
    Status 'done'
} catch {
    Log ('ERROR ' + $_.Exception.Message)
    if (-not ((Get-Content -LiteralPath $statusFile -EA SilentlyContinue) -like 'FAILED*')) { Status ('FAILED ' + $_.Exception.Message) }
}
