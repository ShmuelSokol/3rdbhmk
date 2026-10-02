param(
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [switch]$CoordinatorReviewed,
    [switch]$NativeSlotConfirmed,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedManifest,
    [ValidateRange(30,900)][int]$DeadlineSeconds=300
)
$ErrorActionPreference='Stop'
$timer=[Diagnostics.Stopwatch]::StartNew()
# Parsing/review does not authorize execution. No Add-Type before explicit gates.
if (-not $CoordinatorReviewed -or -not $NativeSlotConfirmed) { throw 'Coordinator review and exclusive native slot required; nothing launched.' }
if ([IntPtr]::Size -ne 8) { throw 'Fresh 64-bit PowerShell required.' }
$root=[IO.Path]::GetFullPath($PSScriptRoot)
$manifestPath=Join-Path $root 'allowlist.json'
if ((Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedManifest) { throw 'Manifest hash mismatch.' }
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
function Assert-PinnedSources {
    foreach ($entry in $manifest.entries) {
        if ($entry.path -notmatch '^[A-Za-z0-9_./-]+$' -or $entry.path.Split('/') -contains '..') { throw 'Unsafe source name.' }
        $path=[IO.Path]::GetFullPath((Join-Path $root $entry.path))
        if (-not $path.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Source escaped root.' }
        $item=Get-Item -LiteralPath $path
        for ($part=$item; $null -ne $part; $part=$part.Parent) {
            if ($part.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse paths refused.' }
            if ($part -is [IO.FileInfo]) { $part=$part.Directory; if ($part.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse directory refused.' } }
        }
        if ($item.Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.sha256) { throw 'Pinned source mismatch.' }
    }
}
Assert-PinnedSources
. (Join-Path $root 'DeadlinePolicy.ps1')
$allowed=@{};foreach ($entry in $manifest.entries) {$allowed[$entry.path]=$true};$allowed['allowlist.json']=$true
foreach ($item in Get-ChildItem -LiteralPath $root -Recurse -File) {
    $relative=$item.FullName.Substring($root.Length+1).Replace('\','/')
    if (-not $allowed.ContainsKey($relative)) { throw 'Fresh exact source stage required; unlisted file exists.' }
}
$context=Get-Content -LiteralPath (Join-Path $root 'source-context.json') -Raw | ConvertFrom-Json
# EngineRoot is the installation directory containing Engine, not Engine itself.
$EngineRoot=[IO.Path]::GetFullPath($EngineRoot)
foreach ($key in @('dotnet','ubt','engineSource')) { $context.$key=Join-Path $EngineRoot $context.$key }
foreach ($entry in $context.engineFiles) { $entry.path=Join-Path $EngineRoot $entry.path }
foreach ($entry in $context.engineFiles) {
    if ((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.sha256) { throw 'Installed engine/tool pin mismatch.' }
}
$project=Join-Path $root 'P/Receiver04Compile.uproject'
foreach ($name in @('P/Intermediate','P/Binaries','P/Saved','run','native.pending')) {
    if (Test-Path -LiteralPath (Join-Path $root $name)) { throw 'Fresh stage required; prior output or unresolved ownership exists.' }
}
$helper=Join-Path $root 'OwnedChildJob.cs'
if ((Get-FileHash -LiteralPath $helper).Hash.ToLowerInvariant() -cne '0ef998314f3e68976c851e055d9aafe0e56e935334f1556a44e5e683a05fcec4') { throw 'Cloth helper pin mismatch.' }
if ('KohenReviewGuard.OwnedChildJob' -as [type]) { throw 'Use a fresh PowerShell process; helper type already loaded.' }
Add-Type -Path $helper
# Exact existing admission/reserve/private guards; no low-memory exception.
if ([KohenReviewGuard.OwnedChildJob]::AvailableCommit() -lt 9GB) { throw '9 GiB free-commit guard unmet; nothing launched.' }
$drive=[IO.DriveInfo]::new([IO.Path]::GetPathRoot($root))
if ($drive.AvailableFreeSpace -lt 6GB) { throw '6 GiB staging-disk floor unmet.' }
$run=Join-Path $root 'run'
$null=New-Item -ItemType Directory -Path $run
$marker=Join-Path $root 'native.pending'
$held=[IO.File]::Open($marker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
$markerBytes=[Text.Encoding]::UTF8.GetBytes('Receiver04UECompile02 unresolved ownership; coordinator clearance required')
$held.Write($markerBytes,0,$markerBytes.Length);$held.Flush($true)
$job=$null; $clean=$false; $status='not_started'; $exitCode=$null; $peak=0; $sourceStable=$false
$log=Join-Path $run 'native-local.log'
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
try {
    # Recheck immediately before process acquisition, after all managed preparation.
    if ([KohenReviewGuard.OwnedChildJob]::AvailableCommit() -lt 9GB) { throw 'Admission guard changed.' }
    if ((Get-CompileDeadlineDecision $timer.Elapsed.TotalSeconds $DeadlineSeconds -BeforeLaunch).Stop) { throw 'Insufficient total deadline remains for acquisition and cleanup.' }
    $arguments=@($context.ubt,'Receiver04CompileEditor','Win64','Development',"-Project=$project",
        '-NoLink','-DisableUnity','-MaxParallelActions=1',
        '-NoUBA','-NoXGE','-NoFASTBuild','-NoSNDBS','-NoHotReloadFromIDE',"-Log=$(Join-Path $run 'ubt-local.log')")
    $status='running'
    if ((Get-CompileDeadlineDecision $timer.Elapsed.TotalSeconds $DeadlineSeconds -BeforeLaunch).Stop) { throw 'Launch deadline consumed.' }
    $job=[KohenReviewGuard.OwnedChildJob]::new($context.dotnet,[string[]]$arguments,$context.engineSource,$log,[uint64]4GB)
    for ($i=0; $i -lt 3601; $i++) {
        if ((Get-CompileDeadlineDecision $timer.Elapsed.TotalSeconds $DeadlineSeconds).Stop) { $status='deadline_cleanup_reserve';break }
        $sample=$job.Poll();$peak=[Math]::Max($peak,$sample.PeakJobBytes)
        if ((Get-CompileDeadlineDecision $timer.Elapsed.TotalSeconds $DeadlineSeconds).Stop) { $status='deadline_cleanup_reserve';break }
        if ([KohenReviewGuard.OwnedChildJob]::AvailableCommit() -lt 2GB) { $status='commit_reserve';break }
        if ($sample.PrivateBytes -ge 4GB) { $status='private_cap';break }
        if ($drive.AvailableFreeSpace -lt 2GB) { $status='disk_reserve';break }
        if ((Get-Item -LiteralPath $log).Length -gt 64MB) { $status='log_limit';break }
        if ((Get-CompileDeadlineDecision $timer.Elapsed.TotalSeconds $DeadlineSeconds).Stop) { $status='deadline_cleanup_reserve';break }
        if ($sample.RootExited) {
            $exitCode=$sample.ExitCode
            $status=if ($exitCode -eq 0 -and $sample.ActiveProcesses -eq 0) {'ubt_zero_object_review_required'} else {'ubt_failed_or_children_pending'}
            break
        }
        $decision=Get-CompileDeadlineDecision $timer.Elapsed.TotalSeconds $DeadlineSeconds
        if ($decision.Stop) { $status='deadline_cleanup_reserve';break }
        if ($decision.SleepMilliseconds -gt 0) { Start-Sleep -Milliseconds $decision.SleepMilliseconds }
    }
    if ($status -eq 'running') { $status='iteration_limit' }
} catch { $status='operation_failed' } # no environment, command line or arbitrary exception dump
finally {
    if ($null -ne $job) {
        try { $clean=$job.StopWithinFiveSeconds() } catch { $clean=$false }
        try { $job.Dispose() } catch { $clean=$false }
    }
    $cleanupFinishedSeconds=$timer.Elapsed.TotalSeconds
    $held.Dispose()
    if ($clean) { [IO.File]::Delete($marker) } # exact locally owned marker, never a foreign slot
    try {
        Assert-PinnedSources
        foreach ($item in Get-ChildItem -LiteralPath (Join-Path $root 'P') -Recurse -File) {
            $relative=$item.FullName.Substring($root.Length+1).Replace('\','/')
            if ($relative -match '/(Source|Config)/' -and -not $allowed.ContainsKey($relative)) { throw 'Unlisted build input appeared.' }
        }
        $sourceStable=$true
    } catch { $sourceStable=$false }
    $withinDeadline=($timer.Elapsed.TotalSeconds -lt $DeadlineSeconds)
    if (-not $withinDeadline) { $status='total_deadline_overrun' }
    $receipt=[ordered]@{status=$status;exitCode=$exitCode;cleanupConfirmed=$clean;sourceStable=$sourceStable;
        totalBudgetSeconds=$DeadlineSeconds;cleanupReserveSeconds=6;cleanupFinishedSeconds=$cleanupFinishedSeconds;withinTotalDeadline=$withinDeadline;
        seconds=$timer.Elapsed.TotalSeconds;peakJobBytes=$peak;manifestSha256=$ExpectedManifest;
        scope='UBT compile-only; separate generated/object inspection required; no runtime acceptance'}
    $data=[Text.UTF8Encoding]::new($false).GetBytes(($receipt|ConvertTo-Json))
    $stream=[IO.File]::Open((Join-Path $run 'receipt.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$stream.Write($data,0,$data.Length)} finally {$stream.Dispose()}
}
if ($timer.Elapsed.TotalSeconds -ge $DeadlineSeconds) {
    [IO.File]::WriteAllText((Join-Path $run 'deadline-overrun.txt'),'Receipt I/O exceeded total deadline; reject attempt.')
    throw 'Total wall deadline overrun; compile attempt not accepted.'
}
if (-not $clean -or -not $sourceStable -or $status -ne 'ubt_zero_object_review_required') { throw 'Compile attempt not accepted; inspect local receipt. Retained marker forbids retry when cleanup is unconfirmed.' }
Write-Output 'UBT returned zero with owned cleanup; generated-code/object inspection is still required.'
