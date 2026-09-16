<#
    FaceV5: capture the Kohen Gadol at 1 m, 2 m and 3.5 m, plus one walking frame.

      powershell -NoProfile -ExecutionPolicy Bypass -File Scripts\capture_facev5_kohen.ps1 `
          -Archive <checkpoint archive> [-RecordSeconds 240]

    Where the cameras come from (derived, not guessed): the two KG cameras proven on Candidate48 in
    the cp18 receipts are the FRONT view '-5530 150 1090 -8 36 0' and the TEND view
    '-5255 60 1045 -6 108 0'. Intersecting those two view rays puts him at about x -5331, y 294,
    with both cameras ~2.46 m out - the two solutions agree to the centimetre. The 1 m / 2 m / 3.5 m
    positions below step along the FRONT view vector (cos36, sin36) from that point.

    He walks in and then tends the menorah, and start_on_begin_play is true on this map, so nothing
    has to be triggered - the capture just has to run long enough for him to arrive.
#>
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [int]$RecordSeconds = 240,
    [int]$SettleSeconds = 30,
    [int]$FixedFps = 10,
    [int]$ResX = 1920,
    [int]$ResY = 1080,
    [string]$Label = 'people01'
)
$ErrorActionPreference = 'Stop'
$project = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
$cap = Join-Path $project 'Scripts\capture_people_walk_movie.ps1'

# view name -> BugItGo. z 1105 is head height for a level look at the face; the walk view is the
# proven full-length camera from the cp18 receipts.
$views = [ordered]@{
    'kg-face-1m'   = '-5412 236 1105 0 36 0'
    'kg-face-2m'   = '-5493 177 1105 0 36 0'
    'kg-face-3m5'  = '-5614 89 1105 -4 36 0'
    'kg-walk-full' = '-5000 -60 1050 -12 84 0'
}

foreach ($name in $views.Keys) {
    foreach ($n in @('UnrealEditor', 'UnrealEditor-Cmd', 'AutomationTool', 'MikdashCourtyardV3')) {
        $p = Get-Process -Name $n -ErrorAction SilentlyContinue
        if ($p) { throw "refusing to capture: $n is running (pid $($p.Id -join ','))" }
    }
    Write-Output ("=== {0}  {1}  {2} ===" -f $name, $views[$name], (Get-Date -Format HH:mm:ss))
    & powershell -NoProfile -ExecutionPolicy Bypass -File $cap `
        -Archive $Archive -Label $Label -View $name -Go $views[$name] `
        -SettleSeconds $SettleSeconds -RecordSeconds $RecordSeconds `
        -FixedFps $FixedFps -ResX $ResX -ResY $ResY 2>&1 | Select-Object -Last 6
    Start-Sleep -Seconds 5
}
Write-Output ("=== ALL CAPTURES DONE {0} ===" -f (Get-Date -Format HH:mm:ss))
