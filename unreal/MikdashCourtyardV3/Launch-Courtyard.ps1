[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectFile = Join-Path $PSScriptRoot 'MikdashCourtyardV3.uproject'
$mapFile = Join-Path $PSScriptRoot 'Content\MikdashV3\IntegratedReviewV2\Maps\Walkthrough.umap'
$engineRoot = 'C:\Program Files\Epic Games\UE_5.8'
$editorFile = Join-Path $engineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
foreach ($requiredFile in @($projectFile, $mapFile, $editorFile)) {
    if (!(Test-Path -LiteralPath $requiredFile -PathType Leaf)) { throw "Required file missing: $requiredFile" }
}
$engineVersion = Get-Content -LiteralPath (Join-Path $engineRoot 'Engine\Build\Build.version') -Raw | ConvertFrom-Json
if ($engineVersion.MajorVersion -ne 5 -or $engineVersion.MinorVersion -ne 8) { throw 'This working copy requires Unreal 5.8.' }
$projectDescriptor = Get-Content -LiteralPath $projectFile -Raw | ConvertFrom-Json
if ($projectDescriptor.EngineAssociation -ne '5.8') { throw 'Unexpected project engine association; inspect before opening.' }
if ($CheckOnly) {
    Write-Output "Verified existing combined Walkthrough map and Unreal $($engineVersion.MajorVersion).$($engineVersion.MinorVersion).$($engineVersion.PatchVersion). No application launched."
    return
}
$matchingEditor = Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($projectFile) }
if ($matchingEditor) { Write-Output 'This project already has an editor process. Use its existing window.'; return }
Start-Process -FilePath $editorFile -ArgumentList @(('"' + $projectFile + '"'), '-d3d12') -WindowStyle Normal
