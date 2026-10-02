# Offline fixtures only. No engine, cook, build, or real Start/Stop-Process calls.
# Run with pwsh -NoProfile -File Tests/test_checkpoint_wrappers.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
$count = 0
function Assert($Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
    $script:count++
}
function Assert-Throws([scriptblock]$Action, [string]$Message) {
    $thrown = $false
    try { & $Action | Out-Null } catch { $thrown = $true }
    Assert $thrown $Message
}
$asts = @{}
foreach ($name in @('Checkpoint-Build.ps1', 'Smoke-Build.ps1')) {
    $tokens = $null; $errors = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $root $name), [ref]$tokens, [ref]$errors)
    Assert ($errors.Count -eq 0) "$name parser errors: $errors"
    $asts[$name] = $ast
    # Load function declarations only; production top-level code is NEVER evaluated.
    foreach ($fn in $ast.FindAll({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
        if ($fn.Name -ne 'Save-Receipt') { . ([scriptblock]::Create($fn.Extent.Text)) }
    }
}
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('checkpoint-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture | Out-Null
# Keep fixtures for diagnosis; no recursive deletion in this test.
Write-Output "Fixtures: $fixture"
$projectFixture = Join-Path $fixture 'project'
foreach ($dir in @('Content/Distribution', 'Config', 'Plugins/P/Source', 'Plugins/P/Intermediate', 'Plugins/P/Binaries', 'Binaries')) {
    New-Item -ItemType Directory -Path (Join-Path $projectFixture $dir) -Force | Out-Null
}
'{}' | Set-Content (Join-Path $projectFixture 'MikdashCourtyardV3.uproject')
foreach ($file in @('Content/map.umap', 'Content/Distribution/runtime.json', 'Config/DefaultEngine.ini', 'Plugins/P/Source/code.cpp', 'Plugins/P/P.uplugin', 'Plugins/P/Intermediate/generated.cpp', 'Plugins/P/Binaries/plugin.dll', 'Binaries/game.exe')) {
    'before' | Set-Content (Join-Path $projectFixture $file)
}
function Manifest { @(Get-DependencyManifest $projectFixture $false) | ConvertTo-Json -Depth 6 -Compress }
$initial = Manifest
Assert ($initial -notmatch 'generated.cpp|plugin.dll|game.exe') 'Generated outputs must not invalidate a build manifest'
Assert ((@(Get-DependencyManifest $projectFixture $true) | ConvertTo-Json -Depth 6) -match 'plugin.dll') 'Existing binary mode must include plugin binaries'
foreach ($file in @('Content/map.umap', 'Content/Distribution/runtime.json', 'Config/DefaultEngine.ini', 'Plugins/P/Source/code.cpp', 'Plugins/P/P.uplugin')) {
    'after' | Set-Content (Join-Path $projectFixture $file)
    Assert ((Manifest) -ne $initial) "Missed changed dependency: $file"
    'before' | Set-Content (Join-Path $projectFixture $file)
    Assert ((Manifest) -eq $initial) "Manifest is not deterministic: $file"
}
$added = Join-Path $projectFixture 'Content/added.uasset'
'new' | Set-Content $added
Assert ((Manifest) -ne $initial) 'Missed added dependency'
Remove-Item -LiteralPath $added
$removed = Join-Path $projectFixture 'Content/map.umap'
Remove-Item -LiteralPath $removed
Assert ((Manifest) -ne $initial) 'Missed deleted dependency'
'before' | Set-Content $removed
'{"AdditionalPluginDirectories":["../external"]}' | Set-Content (Join-Path $projectFixture 'MikdashCourtyardV3.uproject')
Assert-Throws { Get-DependencyManifest $projectFixture $false } 'External dependency roots must fail closed'
'{}' | Set-Content (Join-Path $projectFixture 'MikdashCourtyardV3.uproject')
$packaging = Join-Path $projectFixture 'Config/DefaultGame.ini'
'+DirectoriesToAlwaysStageAsNonUFS=(Path="Distribution")' | Set-Content $packaging
Assert-PackagingInputs $projectFixture
foreach ($path in @('../outside', 'C:/external', '/external', '$(ProjectDir)/outside', '%EXTERNAL%')) {
    ('+DirectoriesToAlwaysStageAsUFS=(Path="' + $path + '")') | Set-Content $packaging
    Assert-Throws { Get-DependencyManifest $projectFixture $false } "External staged data accepted: $path"
}
Assert (Test-CheckpointSuccess 'checkpoint_playable' $false) 'Legacy success compatibility'
Assert (Test-CheckpointSuccess 'checkpoint_startup_verified' $false) 'New startup success'
Assert (-not (Test-CheckpointSuccess 'cook_archive_passed_smoke_skipped' $false)) 'Skip must be explicit'
Assert ((Get-DiskRequirement 4GB 10) -eq 18GB) 'Disk estimate must include archive, stage and explicit reserve'
Assert-Throws { Get-DiskRequirement 0 10 } 'Missing disk baseline must fail'
Assert-Throws { Get-DiskRequirement 4GB 0 } 'Missing reserve must fail'
Assert-Throws { Assert-DiskHeadroom (18GB - 1) 4GB 10 } 'Insufficient disk must refuse before cook'
Assert ((Assert-DiskHeadroom 18GB 4GB 10) -eq 18GB) 'Exact headroom boundary must pass'
Assert-Throws { Assert-FreshDestination $projectFixture } 'Existing archive must be refused'
Assert-FreshDestination (Join-Path $fixture 'fresh-archive')

# Evaluate the actual cook predicate with one failed guard at a time.
$cookAssignment = $asts['Checkpoint-Build.ps1'].Find({ param($n)
    $n -is [Management.Automation.Language.AssignmentStatementAst] -and
    $n.Left.Extent.Text -eq '$cookOk' -and $n.Right.Extent.Text -match 'dependenciesUnchanged'
}, $true)
foreach ($bad in @('none', 'exitCode', 'childExists', 'candidateSha256After', 'mainSha256After', 'dependenciesUnchanged')) {
    $before = 'candidate'; $mainBefore = 'main'
    $r = @{ exitCode = 0; childExists = $true; candidateSha256After = $before; mainSha256After = $mainBefore; dependenciesUnchanged = $true }
    if ($bad -eq 'exitCode') { $r[$bad] = 1 }
    elseif ($bad -in @('childExists', 'dependenciesUnchanged')) { $r[$bad] = $false }
    elseif ($bad -ne 'none') { $r[$bad] = 'changed' }
    . ([scriptblock]::Create($cookAssignment.Extent.Text))
    Assert ($cookOk -eq ($bad -eq 'none')) "Cook predicate missed $bad"
}

# Execute the real build smoke/finalization tail in a fixture, with a stub smoke
# script. This verifies real script exit semantics (including exit from & script).
$buildText = $asts['Checkpoint-Build.ps1'].Extent.Text
$tail = $buildText.Substring($buildText.IndexOf('if ($cookOk -and -not $SkipSmoke)'))
$successFunction = $asts['Checkpoint-Build.ps1'].Find({ param($n)
    $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Test-CheckpointSuccess'
}, $false).Extent.Text
foreach ($mode in @('startup_verified', 'playable', 'started_but_no_window', 'never_started', 'window_opened_then_exited', 'memory_refused', 'memory_guard_failed', 'cleanup_failed', 'missing', 'malformed', 'throw', 'badexit', 'skip')) {
    $case = Join-Path $fixture $mode
    New-Item -ItemType Directory -Path (Join-Path $case 'SourceAssets/build-review') -Force | Out-Null
    $prefix = @'
param($Mode)
$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot; $job = $PSScriptRoot; $archive = $PSScriptRoot
$Label = 'test'; $stamp = 'fixture'; $cookOk = $true; $SkipSmoke = ($Mode -eq 'skip')
$r = [ordered]@{ status = 'cook_archive_passed_smoke_pending' }
function Save-Receipt { $r | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $job 'checkpoint-receipt.json') }
'@
    ($prefix + "`n" + $successFunction + "`n" + $tail) | Set-Content (Join-Path $case 'build-tail.ps1')
    @'
param($Archive, $ReceiptPath)
switch ($Mode) {
    'missing' { exit 1 }
    'malformed' { '{' | Set-Content $ReceiptPath; exit 1 }
    'throw' { throw 'fixture smoke error' }
    'badexit' { '{"status":"playable"}' | Set-Content $ReceiptPath; exit 9 }
    default { @{ status = $Mode } | ConvertTo-Json | Set-Content $ReceiptPath }
}
if ($Mode -notin @('startup_verified', 'playable')) { exit 1 }
exit 0
'@ | Set-Content (Join-Path $case 'Smoke-Build.ps1')
    & (Join-Path $case 'build-tail.ps1') $mode | Out-Null
    $code = $LASTEXITCODE
    Assert (($code -eq 0) -eq ($mode -in @('startup_verified', 'playable', 'skip'))) "Build tail returned $code for $mode"
    Assert (Test-Path (Join-Path $case 'checkpoint-receipt.json')) "Missing terminal receipt for $mode"
    $result = Get-Content (Join-Path $case 'checkpoint-receipt.json') -Raw | ConvertFrom-Json
    if ($mode -in @('startup_verified', 'playable')) { Assert ($result.status -eq 'checkpoint_startup_verified') 'Do not claim playable quality' }
    if ($mode -eq 'skip') { Assert ($result.status -eq 'cook_archive_passed_smoke_skipped') 'Skip smoke must not claim startup or playable acceptance' }
}

# Smoke uses only mock objects. Block all real process and CIM access.
function Get-Process {
    if ($global:CheckpointTestsmokeMode -eq 'busy') { [pscustomobject]@{ Id = 999 } }
}
function Get-CimInstance {
    param($ClassName, $Filter)
    if ($ClassName -eq 'Win32_Process') { return }
    if ($ClassName -ne 'Win32_OperatingSystem') { throw "Unexpected CIM request: $ClassName" }
    $global:CheckpointTestmemoryReads++
    if ($global:CheckpointTestsmokeMode -eq 'unknown_memory') { return [pscustomobject]@{} }
    $freeBytes = 9GB
    if ($global:CheckpointTestsmokeMode -eq 'refuse') { $freeBytes = 9GB - 1KB }
    if ($global:CheckpointTestmemoryReads -gt 1) {
        if ($global:CheckpointTestsmokeMode -eq 'reserve') { $freeBytes = 2GB - 1KB }
        if ($global:CheckpointTestsmokeMode -eq 'boundary') { $freeBytes = 2GB }
        if ($global:CheckpointTestsmokeMode -eq 'stability_reserve' -and
            $global:CheckpointTestclock -ge ([datetime]'2026-01-01').AddSeconds(3)) { $freeBytes = 2GB - 1KB }
    }
    [pscustomobject]@{ FreeVirtualMemory = $freeBytes / 1KB }
}
function Start-Process {
    param($FilePath, $WorkingDirectory, $ArgumentList, $WindowStyle, [switch]$PassThru)
    $global:CheckpointTestlaunches++
    $global:CheckpointTestarguments = $ArgumentList
    Assert ($WindowStyle -eq 'Hidden') 'Smoke must launch hidden'
    $global:CheckpointTestmockProcess
}
function Stop-Process {
    param($InputObject, [switch]$Force, $ErrorAction)
    Assert ([object]::ReferenceEquals($InputObject, $global:CheckpointTestmockProcess)) 'Cleanup targeted an unowned process'
    $global:CheckpointTeststopped++
    if ($global:CheckpointTestsmokeMode -eq 'cleanup') { throw 'fixture stop failure' }
    $InputObject.HasExited = $true
}
function Get-Date { $global:CheckpointTestclock }
function Start-Sleep {
    param($Seconds)
    Assert ($Seconds -eq 1) 'Memory guard must poll every second, including stability'
    $global:CheckpointTestclock = $global:CheckpointTestclock.AddSeconds($Seconds)
    if ($global:CheckpointTestsmokeMode -eq 'early') { $global:CheckpointTestmockProcess.HasExited = $true }
    if ($global:CheckpointTestsmokeMode -eq 'stability_private' -and
        $global:CheckpointTestclock -ge ([datetime]'2026-01-01').AddSeconds(3)) {
        $global:CheckpointTestmockProcess.PrivateMemorySize64 = 8GB + 1
    }
}
$smokeArchive = Join-Path $fixture 'smoke'
$exe = Join-Path $smokeArchive 'Windows/MikdashCourtyardV3/Binaries/Win64/MikdashCourtyardV3.exe'
New-Item -ItemType Directory -Path (Split-Path $exe) -Force | Out-Null
'not an executable' | Set-Content $exe
$prefixes = @()
foreach ($smokeMode in @('playable', 'timeout', 'early', 'monitor', 'cleanup', 'busy', 'refuse', 'unknown_memory', 'private', 'reserve', 'stability_private', 'stability_reserve', 'boundary')) {
    $global:CheckpointTestsmokeMode = $smokeMode; $global:CheckpointTeststopped = 0; $global:CheckpointTestclock = [datetime]'2026-01-01'
    $global:CheckpointTestlaunches = 0; $global:CheckpointTestmemoryReads = 0; $global:CheckpointTestarguments = @()
    $global:CheckpointTestmockProcess = [pscustomobject]@{
        Id = 123; StartTime = $global:CheckpointTestclock; Path = $exe; HasExited = $false
        WorkingSet64 = 100MB; MainWindowHandle = $(if ($smokeMode -eq 'timeout') { 0 } else { 1 }); Refreshes = 0
        PrivateMemorySize64 = $(if ($smokeMode -eq 'private') { 8GB + 1 } elseif ($smokeMode -eq 'boundary') { 8GB } else { 100MB })
    }
    $global:CheckpointTestmockProcess | Add-Member ScriptMethod Refresh {
        $this.Refreshes++
        if ($global:CheckpointTestsmokeMode -eq 'monitor' -and $this.Refreshes -eq 1) { throw 'fixture monitor exception' }
    }
    $global:CheckpointTestmockProcess | Add-Member ScriptMethod WaitForExit { param($Timeout) $this.HasExited }
    Assert (Test-SmokeProcessIdentity $global:CheckpointTestmockProcess 123 $global:CheckpointTestclock $exe) 'Owned identity rejected'
    Assert (-not (Test-SmokeProcessIdentity $global:CheckpointTestmockProcess 124 $global:CheckpointTestclock $exe)) 'Foreign PID accepted'
    Assert (-not (Test-SmokeProcessIdentity $global:CheckpointTestmockProcess 123 $global:CheckpointTestclock.AddSeconds(-1) $exe)) 'Recycled PID accepted'
    Assert (-not (Test-SmokeProcessIdentity $global:CheckpointTestmockProcess 123 $global:CheckpointTestclock ($exe + '.other'))) 'Foreign executable accepted'
    $receipt = Join-Path $fixture "smoke-$smokeMode.json"
    & (Join-Path $root 'Smoke-Build.ps1') -Archive $smokeArchive -TimeoutSeconds 2 -ReceiptPath $receipt | Out-Null
    $code = $LASTEXITCODE
    $result = Get-Content $receipt -Raw | ConvertFrom-Json
    $expected = @{
        playable = 'startup_verified'; timeout = 'started_but_no_window'; early = 'window_opened_then_exited'
        monitor = 'error'; cleanup = 'cleanup_failed'; busy = 'error'; refuse = 'memory_refused'; unknown_memory = 'error'
        private = 'memory_guard_failed'; reserve = 'memory_guard_failed'; stability_private = 'memory_guard_failed'
        stability_reserve = 'memory_guard_failed'; boundary = 'startup_verified'
    }[$smokeMode]
    Assert ($result.status -eq $expected) "Smoke $smokeMode returned $($result.status): $($result.error)"
    Assert (($code -eq 0) -eq ($smokeMode -in @('playable', 'boundary'))) "Smoke $smokeMode exit mismatch"
    $refused = $smokeMode -in @('busy', 'refuse', 'unknown_memory')
    Assert ($global:CheckpointTestlaunches -eq $(if ($refused) { 0 } else { 1 })) "Smoke $smokeMode launched despite refusal"
    Assert ($global:CheckpointTeststopped -eq $(if ($refused -or $smokeMode -eq 'early') { 0 } else { 1 })) "Smoke $smokeMode cleanup not bounded to one owned handle"
    Assert ($result.minimumStartCommitBytes -eq 9GB -and $result.maximumPrivateBytes -eq 8GB -and $result.reserveCommitBytes -eq 2GB) 'Memory thresholds changed'
    Assert ($result.testSavePrefix -match '^CheckpointSmoke_[a-f0-9]{32}$' -and $result.testSavePrefix -notin $prefixes) 'Save prefix must be fresh and recorded on every attempt'
    $prefixes += $result.testSavePrefix
    if (-not $refused) {
        $argsText = $global:CheckpointTestarguments -join ' '
        $prefix = $result.testSavePrefix
        Assert ($global:CheckpointTestarguments -contains "-TestSavePrefix=$prefix") 'Missing TestSavePrefix'
        Assert ($argsText.Contains("[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=$prefix,")) 'Missing isolated game-save override'
        Assert ($argsText.Contains("[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=${prefix}_Settings,")) 'Missing isolated settings override'
        Assert ($argsText.Contains('[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False')) 'Do not apply user graphics settings'
        Assert (($result.arguments -join ' ') -eq $argsText) 'Receipt must record exact launch arguments'
    }
    if ($smokeMode -in @('playable', 'boundary')) {
        Assert ($global:CheckpointTestmemoryReads -eq 12) 'Need prelaunch, initial, and ten stability memory samples'
    }
    if ($smokeMode -in @('private', 'stability_private')) { Assert ($result.peakPrivateBytes -gt 8GB) 'Private cap violation must be recorded' }
    if ($smokeMode -in @('reserve', 'stability_reserve')) { Assert ($result.minimumObservedCommitBytes -lt 2GB) 'Reserve violation must be recorded' }
}
Write-Output "PASS: $count assertions; no production launches. Fixtures retained at $fixture"
