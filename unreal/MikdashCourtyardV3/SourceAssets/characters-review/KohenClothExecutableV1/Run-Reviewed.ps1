param([switch]$CoordinatorReviewed)
$ErrorActionPreference = 'Stop'
if (-not $CoordinatorReviewed) { throw 'Native execution requires coordinator review/slot. Nothing launched.' }
. (Join-Path $PSScriptRoot 'Owned-ReviewWatchdog.ps1')
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'ReviewProject/KohenClothReview.uproject')).Path
$script = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'run_in_editor.py')).Path
$engine = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
Invoke-OwnedReviewJob -Kind native -ReviewRoot $PSScriptRoot -Executable $engine `
    -ArgumentVector @($project,'-run=pythonscript',"-script=$script",'-unattended','-nullrhi','-nosplash','-NoSound','-stdout','-FullStdOutLogOutput') `
    -WorkingDirectory (Split-Path $project) -DeadlineSeconds 600
