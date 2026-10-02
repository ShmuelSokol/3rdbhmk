param([switch]$CoordinatorReviewed)
$ErrorActionPreference = 'Stop'
if (-not $CoordinatorReviewed) { throw 'Isolated UBT build requires coordinator review/slot. Nothing launched.' }
. (Join-Path $PSScriptRoot 'Owned-ReviewWatchdog.ps1')
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'ReviewProject/KohenClothReview.uproject')).Path
$engine = 'C:/Program Files/Epic Games/UE_5.8/Engine'
$dotnet = Join-Path $engine 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'
$ubt = (Resolve-Path -LiteralPath (Join-Path $engine 'Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll')).Path
# Same installed UBT used by Build.bat, without a batch bootstrap/rebuild of UBT.
# One UBT invocation, one local compiler action. Job owns compiler descendants.
Invoke-OwnedReviewJob -Kind build -ReviewRoot $PSScriptRoot -Executable $dotnet `
    -ArgumentVector @($ubt,'KohenClothReviewEditor','Win64','Development',"-Project=$project",'-WaitMutex','-NoHotReloadFromIDE','-MaxParallelActions=1','-NoUBA','-NoXGE') `
    -WorkingDirectory (Join-Path $engine 'Source') -DeadlineSeconds 900
