[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectFile = Join-Path $PSScriptRoot 'MikdashCourtyardV3.uproject'
function Get-SelectedIniValues([string]$Path, [string]$Section, [string]$Key) {
    $currentSection = ''
    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $line = $rawLine.Trim()
        if (!$line -or $line.StartsWith(';') -or $line.StartsWith('#')) { continue }
        if ($line.StartsWith('[') -and $line.EndsWith(']')) { $currentSection = $line.Substring(1, $line.Length - 2); continue }
        if ($currentSection -ceq $Section -and $line.Contains('=')) {
            $parts = $line.Split('=', 2)
            $entryName = $parts[0].Trim()
            if ($entryName.TrimStart([char[]]'+-.!') -ceq $Key) {
                if ($entryName -cne $Key -and $entryName -cne ('+' + $Key)) { throw "Unsupported config operator for $Key" }
                $parts[1].Trim()
            }
        }
    }
}
$engineIni = Join-Path $PSScriptRoot 'Config\DefaultEngine.ini'
$gameIni = Join-Path $PSScriptRoot 'Config\DefaultGame.ini'
$defaultMaps = @(Get-SelectedIniValues $engineIni '/Script/EngineSettings.GameMapsSettings' 'GameDefaultMap')
$startupMaps = @(Get-SelectedIniValues $engineIni '/Script/EngineSettings.GameMapsSettings' 'EditorStartupMap')
$cookMaps = @(Get-SelectedIniValues $gameIni '/Script/UnrealEd.ProjectPackagingSettings' 'MapsToCook')
if ($defaultMaps.Count -ne 1 -or $startupMaps.Count -ne 1 -or $cookMaps.Count -ne 1) { throw 'Require exactly one game default, editor startup and cook map.' }
$cookMatch = [regex]::Match($cookMaps[0], '^\(FilePath="([^"]+)"\)$')
if (!$cookMatch.Success -or $defaultMaps[0] -cne $startupMaps[0] -or $defaultMaps[0] -cne $cookMatch.Groups[1].Value) { throw 'Game default, editor startup and cook map disagree.' }
$selectedMap = $defaultMaps[0]
$allowedMaps = @('/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough', '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough')
if ($allowedMaps -cnotcontains $selectedMap) { throw 'Configured map is outside the explicit Main50/Selected48 allowlist.' }
$mapFile = Join-Path $PSScriptRoot ('Content\' + $selectedMap.Substring(6) + '.umap')
$engineRoot = 'C:\Program Files\Epic Games\UE_5.8'
$editorFile = Join-Path $engineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
foreach ($requiredFile in @($projectFile, $mapFile, $editorFile)) {
    if (!(Test-Path -LiteralPath $requiredFile -PathType Leaf)) { throw "Required file missing: $requiredFile" }
}
$mapBytes = (Get-Item -LiteralPath $mapFile).Length
if ($mapBytes -le 2000000 -or $mapBytes -ge 400000000) { throw 'Configured map size is implausible.' }
$engineVersion = Get-Content -LiteralPath (Join-Path $engineRoot 'Engine\Build\Build.version') -Raw | ConvertFrom-Json
if ($engineVersion.MajorVersion -ne 5 -or $engineVersion.MinorVersion -ne 8) { throw 'This working copy requires Unreal 5.8.' }
$projectDescriptor = Get-Content -LiteralPath $projectFile -Raw | ConvertFrom-Json
if ($projectDescriptor.EngineAssociation -ne '5.8') { throw 'Unexpected project engine association; inspect before opening.' }
if ($CheckOnly) {
    Write-Output "Verified selected map $selectedMap; game/editor/cook settings agree. Unreal $($engineVersion.MajorVersion).$($engineVersion.MinorVersion).$($engineVersion.PatchVersion). No application launched."
    return
}
$editorProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'")
$matchingEditor = $editorProcesses | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -and $_.CommandLine.Contains($projectFile) }
if ($matchingEditor) { Write-Output 'This project already has an editor process. Use its existing window.'; return }
if ($editorProcesses.Count) { throw 'An Unreal editor or commandlet is already running. Its process has been preserved; finish that job before opening another editor.' }
Start-Process -FilePath $editorFile -ArgumentList @(('"' + $projectFile + '"'), $selectedMap, '-d3d12') -WindowStyle Normal
