# Single policy implementation; source preparation only until coordinator review.
param(
 [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]{1,32}$')][string]$RunId,
 [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string]$ExpectedManifest
)
& "$PSScriptRoot/Run-Reviewed.ps1" -Mode Build -RunId $RunId -ExpectedManifest $ExpectedManifest
