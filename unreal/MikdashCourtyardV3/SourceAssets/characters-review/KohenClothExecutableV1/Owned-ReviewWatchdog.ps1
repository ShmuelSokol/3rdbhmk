# Dot-sourcing defines functions only. No process, Add-Type or native launch at load time.
function Write-ReviewAtomicJson([string]$Path, $Value) {
    if (Test-Path -LiteralPath $Path) { throw "Receipt already exists: $Path" }
    $temporary = $Path + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
    $json = $Value | ConvertTo-Json -Depth 14
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($json)
    $stream = [IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
    try { [IO.File]::Move($temporary, $Path) }
    finally { if (Test-Path -LiteralPath $temporary) { [IO.File]::Delete($temporary) } }
}

function Assert-ReviewSlotClear([string]$Marker) {
    if (Test-Path -LiteralPath $Marker) { throw "Native slot blocked: $Marker. Coordinator must verify all recorded owned processes have exited before explicit manual clearance; no automatic removal." }
}

function New-ReviewOwnershipSentinel([string]$Marker, [string]$Token, [string]$ReceiptFolder) {
    Assert-ReviewSlotClear $Marker
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $Marker) -Force
    Write-ReviewAtomicJson $Marker ([ordered]@{
        status='unresolved_ownership'; blockedUtc=[DateTime]::UtcNow.ToString('o'); owner='KohenClothExecutableV1'; ownershipToken=$Token
        receiptFolder=$ReceiptFolder; wrapperProcessId=$PID
        clearance='Retain unless this owner confirms cleanup; otherwise coordinator must verify root and all descendants exited before manual clearance.'
    })
    $saved = Get-Content -LiteralPath $Marker -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    if ($saved.ownershipToken -cne $Token) { throw 'Ownership sentinel verification failed; launch refused.' }
}

function Complete-ReviewOwnership([string]$Marker, [string]$Token, [bool]$CleanupConfirmed) {
    if (-not $CleanupConfirmed) { return $false }
    $saved = Get-Content -LiteralPath $Marker -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    if ($saved.owner -cne 'KohenClothExecutableV1' -or $saved.ownershipToken -cne $Token) {
        throw 'Foreign ownership sentinel; retained untouched.'
    }
    [IO.File]::Delete($Marker)
    return $true
}

function Get-ReviewGuardReason([long]$PrivateBytes, [long]$FreeCommitBytes, [double]$ElapsedSeconds, [int]$DeadlineSeconds) {
    if ($PrivateBytes -lt 0 -or $FreeCommitBytes -lt 0) { return 'measurement_failed' }
    if ($PrivateBytes -ge 4GB) { return 'private_cap' }
    if ($FreeCommitBytes -lt 2GB) { return 'commit_reserve' }
    if ($ElapsedSeconds -ge $DeadlineSeconds) { return 'deadline' }
    return ''
}

function Get-ReviewSourceHashes([string]$ReviewRoot) {
    $active = [IO.Path]::GetFullPath((Join-Path $ReviewRoot '../../..'))
    $files = @(
        Get-ChildItem -LiteralPath (Join-Path $active 'Content') -Recurse -File | Where-Object { $_.Extension -in '.uasset','.umap' }
        Get-ChildItem -LiteralPath (Join-Path $active 'SourceAssets/characters-review') -Recurse -File -Filter '*.glb'
        Get-ChildItem -LiteralPath (Join-Path $ReviewRoot 'ReviewProject/Source') -Recurse -File
        Get-ChildItem -LiteralPath (Join-Path $ReviewRoot 'ReviewProject/Plugins') -Recurse -File |
            Where-Object { $_.FullName -notmatch '[\\/](Binaries|Intermediate)[\\/]' }
        Get-Item -LiteralPath (Join-Path $ReviewRoot 'ReviewProject/KohenClothReview.uproject')
        Get-Item -LiteralPath (Join-Path $ReviewRoot '../KohenClothFeasibilityV1/prepared-input.json')
        Get-Item -LiteralPath (Join-Path $active 'Scripts/release_kohen_gadol_v1.py')
        Get-ChildItem -LiteralPath $ReviewRoot -File | Where-Object { $_.Extension -in '.py','.ps1','.cs' }
    )
    $hashes = [ordered]@{}
    foreach ($file in ($files | Sort-Object FullName -Unique)) {
        $hashes[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
    return $hashes
}

function Invoke-OwnedReviewJob {
    param([ValidateSet('native','build')][string]$Kind, [string]$ReviewRoot, [string]$Executable,
          [string[]]$ArgumentVector, [string]$WorkingDirectory, [int]$DeadlineSeconds)
    $ErrorActionPreference = 'Stop'
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [guid]::NewGuid().ToString('N')
    $folder = Join-Path $ReviewRoot ('WrapperRuns/' + $Kind + '-' + $stamp)
    $null = New-Item -ItemType Directory -Path $folder
    $record = [ordered]@{
        revision='owned-job-v3'; kind=$Kind; status='preflight'; startedUtc=[DateTime]::UtcNow.ToString('o')
        minimumStartCommitBytes=9GB; maximumPrivateBytes=4GB; reserveCommitBytes=2GB
        deadlineSeconds=$DeadlineSeconds; cleanupDeadlineMilliseconds=5000; pollMilliseconds=500
        hidden=$true; createdSuspended=$true; ownership='Windows Job Object; retained root handle; descendants cannot break away'
        processStarted=$false; peakPrivateBytes=0L; minimumFreeCommitBytes=[long]::MaxValue
        cleanupConfirmed=$null; sourcePreserved=$null; outcome='notrun'
        scope='Wrapper execution only; never cloth/visual/clearance acceptance'
    }
    $owned = $null; $before = $null; $sentinelAcquired=$false
    $ownershipToken=[guid]::NewGuid().ToString('N')
    $blockedSlot = [IO.Path]::GetFullPath((Join-Path $ReviewRoot '../../context-review/HaramThresholdSidesV1/native-slot-blocked.json'))
    $record.blockedSlotPath=$blockedSlot
    try {
        Assert-ReviewSlotClear $blockedSlot
        $busy = @(Get-Process -Name 'UnrealEditor','UnrealEditor-Cmd','UnrealBuildTool','AutomationTool' -ErrorAction SilentlyContinue)
        $busy += @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -OperationTimeoutSec 3 |
            Where-Object { $_.CommandLine -match 'UnrealBuildTool|AutomationTool' })
        if ($busy.Count) { $record.status='slot_refused'; throw 'Native/build slot occupied; no process touched.' }
        $memory = Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 3
        if ($null -eq $memory.FreeVirtualMemory) { throw 'Cannot establish free commit' }
        $record.startFreeCommitBytes = [long]$memory.FreeVirtualMemory * 1KB
        if ($record.startFreeCommitBytes -lt 9GB) { $record.status='start_memory_refused'; throw 'Unchanged start guard requires9GiB free commit.' }
        $before = Get-ReviewSourceHashes $ReviewRoot
        Write-ReviewAtomicJson (Join-Path $folder 'source-before.json') $before
        $exe = (Resolve-Path -LiteralPath $Executable).ProviderPath
        # Only a reviewed wrapper execution compiles/loads this managed helper.
        if ('KohenReviewGuard.OwnedChildJob' -as [type]) { throw 'Watchdog type already loaded; use a fresh PowerShell host to prevent stale helper reuse.' }
        Add-Type -Path (Join-Path $ReviewRoot 'OwnedChildJob.cs')
        $free = [long][KohenReviewGuard.OwnedChildJob]::AvailableCommit()
        if ($free -lt 9GB) { $record.status='start_memory_refused'; throw 'Free commit fell below9GiB before launch.' }
        $record.executable=$exe; $record.arguments=$ArgumentVector
        Write-ReviewAtomicJson (Join-Path $folder 'launch-intent.json') $record
        $clock = [Diagnostics.Stopwatch]::StartNew()
        Assert-ReviewSlotClear $blockedSlot
        New-ReviewOwnershipSentinel $blockedSlot $ownershipToken $folder
        $sentinelAcquired=$true; $record.ownershipToken=$ownershipToken
        $owned = [KohenReviewGuard.OwnedChildJob]::new($exe, $ArgumentVector, $WorkingDirectory, (Join-Path $folder 'child-output.log'), [ulong]4GB)
        $record.processStarted=$true; $record.processId=$owned.ProcessId; $record.processCreationFileTime=$owned.CreationFileTime
        $record.status='running'
        while ($true) {
            $sample = $owned.Poll()
            $free = [long][KohenReviewGuard.OwnedChildJob]::AvailableCommit()
            $private = [long][math]::Max($sample.PrivateBytes,$sample.PeakJobBytes)
            $record.peakPrivateBytes=[math]::Max($record.peakPrivateBytes,$private)
            $record.minimumFreeCommitBytes=[math]::Min($record.minimumFreeCommitBytes,$free)
            $record.elapsedSeconds=$clock.Elapsed.TotalSeconds
            $reason = Get-ReviewGuardReason $private $free $clock.Elapsed.TotalSeconds $DeadlineSeconds
            if ($reason) { $record.status=$reason; throw "Owned $Kind guard: $reason" }
            if ($sample.RootExited) {
                $record.exitCode=$sample.ExitCode
                $record.activeDescendantsAtRootExit=$sample.ActiveProcesses
                if ($sample.ExitCode -ne 0) { $record.status='child_failed'; throw "Owned $Kind child exit=$($sample.ExitCode)" }
                if ($sample.ActiveProcesses -ne 0) { $record.status='descendants_after_root_exit'; throw 'Root exited while owned workers remained; bounded cleanup required.' }
                $record.status='child_exited_zero'; $record.outcome='execution_completed'; break
            }
            Start-Sleep -Milliseconds 500
        }
    } catch {
        if ($record.status -in 'preflight','running') { $record.status='wrapper_error' }
        $record.error=$_.Exception.Message
        $cause=$_.Exception
        while ($cause.InnerException) { $cause=$cause.InnerException }
        if ($cause.Data.Contains('OwnedProcessId')) {
            $record.processStarted=$true; $record.processId=$cause.Data['OwnedProcessId']
            $record.processCreationFileTime=$cause.Data['OwnedCreationFileTime']
            $record.cleanupConfirmed=$cause.Data['OwnedCleanupConfirmed']
            if (-not $record.cleanupConfirmed) { $record.status='cleanup_failed' }
        }
    } finally {
        # Clean the owned job FIRST, before source hashing/receipt work.
        if ($owned) {
            $cleanupClock=[Diagnostics.Stopwatch]::StartNew()
            try {
                $record.cleanupConfirmed=$owned.StopWithinFiveSeconds()
                $record.cleanupError=$owned.CleanupError
                if (-not $record.cleanupConfirmed) { $record.status='cleanup_failed'; $record.outcome='failed' }
            } catch { $record.cleanupConfirmed=$false; $record.cleanupError=$_.Exception.Message; $record.status='cleanup_failed'; $record.outcome='failed' }
            finally {
                try { $owned.Dispose() } catch { $record.cleanupConfirmed=$false; $record.cleanupError=$_.Exception.Message }
                $record.cleanupElapsedMilliseconds=$cleanupClock.ElapsedMilliseconds
            }
        }
        # The prelaunch sentinel already blocks future runs even if every later write fails.
        # Constructor failures without positive cleanup evidence deliberately retain it.
        if ($sentinelAcquired) {
            try {
                $record.sentinelRemoved=Complete-ReviewOwnership $blockedSlot $ownershipToken ($record.cleanupConfirmed -eq $true)
                $record.slotBlocked=-not $record.sentinelRemoved
                if ($record.slotBlocked) { $record.status='cleanup_failed'; $record.outcome='failed' }
            } catch { $record.sentinelClearError=$_.Exception.Message; $record.slotBlocked=$true; $record.status='cleanup_failed'; $record.outcome='failed' }
        }
        if ($before) {
            try {
                $changed = @(); $after = [ordered]@{}
                foreach ($path in $before.Keys) {
                    $hash = if (Test-Path -LiteralPath $path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash } else { 'MISSING' }
                    $after[$path]=$hash
                    if ($hash -ne $before[$path]) { $changed += $path }
                }
                $record.sourcePreserved=($changed.Count -eq 0); $record.sourceFilesChecked=$before.Count; $record.changedSources=$changed
                Write-ReviewAtomicJson (Join-Path $folder 'source-after.json') $after
                if ($changed.Count) { $record.status='source_changed'; $record.outcome='failed' }
            } catch { $record.sourcePreserved=$false; $record.preservationError=$_.Exception.Message; $record.status='preservation_failed'; $record.outcome='failed' }
        }
        if ($record.minimumFreeCommitBytes -eq [long]::MaxValue) { $record.minimumFreeCommitBytes=$null }
        $record.finishedUtc=[DateTime]::UtcNow.ToString('o')
        Write-ReviewAtomicJson (Join-Path $folder 'wrapper.json') $record
    }
    Write-Output "Wrapper receipt: $(Join-Path $folder 'wrapper.json')"
    if ($record.status -ne 'child_exited_zero' -or -not $record.cleanupConfirmed -or -not $record.sourcePreserved) {
        throw "Owned $Kind did not complete safely: $($record.status). Evidence retained in $folder"
    }
}
