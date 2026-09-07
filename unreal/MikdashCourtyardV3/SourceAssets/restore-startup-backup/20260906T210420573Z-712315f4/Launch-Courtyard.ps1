$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$engineRoot = 'C:\Program Files\Epic Games\UE_5.7'
$editor = Join-Path $engineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
if (!(Test-Path $editor)) { throw 'Unreal 5.7 editor was not found at the verified installation location.' }
$template = Get-ChildItem (Join-Path $engineRoot 'Templates') -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'FirstPerson.*BP|TP_FirstPersonBP' -and (Test-Path (Join-Path $_.FullName 'Content')) } | Select-Object -First 1
if ($template) {
    Copy-Item (Join-Path $template.FullName 'Content\*') (Join-Path $projectRoot 'Content') -Recurse -Force
    $inputFile = Join-Path $template.FullName 'Config\DefaultInput.ini'
    if (Test-Path $inputFile) { Copy-Item $inputFile (Join-Path $projectRoot 'Config\DefaultInput.ini') }
    $contentRoot = Join-Path $projectRoot 'Content'
    $characters = @(Get-ChildItem $contentRoot -Recurse -File -Filter 'BP_FirstPersonCharacter.uasset')
    $modes = @(Get-ChildItem $contentRoot -Recurse -File -Filter 'BP_FirstPersonGameMode.uasset')
    if ($characters.Count -eq 1 -and $modes.Count -eq 1) {
        function AssetPath($file) { '/Game/' + $file.FullName.Substring($contentRoot.Length + 1).Replace('\','/').Replace('.uasset','') }
        @{character=(AssetPath $characters[0]);gameMode=(AssetPath $modes[0]);template=$template.FullName} | ConvertTo-Json | Set-Content (Join-Path $projectRoot 'SourceAssets\gameplay-config.json') -Encoding utf8
    }
    @{template=$template.FullName;characters=@($characters.FullName);gameModes=@($modes.FullName)} | ConvertTo-Json | Set-Content (Join-Path $projectRoot 'SourceAssets\template-discovery.json') -Encoding utf8
} else {
    @{status='FirstPerson template folder not found';availableTemplates=@(Get-ChildItem (Join-Path $engineRoot 'Templates') -Name -ErrorAction SilentlyContinue)} | ConvertTo-Json | Set-Content (Join-Path $projectRoot 'SourceAssets\template-discovery.json') -Encoding utf8
}
Start-Process $editor -ArgumentList @(('"' + (Join-Path $projectRoot 'MikdashCourtyardV3.uproject') + '"'), '-d3d12')
