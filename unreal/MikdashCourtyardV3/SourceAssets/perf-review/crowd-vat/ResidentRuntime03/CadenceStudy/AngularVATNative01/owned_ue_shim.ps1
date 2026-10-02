# Only invoked INSIDE the OS-proven Job Object. No standalone native authorization.
param([Parameter(Mandatory)][string]$LaunchFile,[Parameter(Mandatory)][int]$DeadlineSeconds)
$ErrorActionPreference='Stop'
$launch=Get-Content -LiteralPath $LaunchFile -Raw|ConvertFrom-Json
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName=$launch.executable
$info.Arguments=$launch.exactArgumentLine
$info.UseShellExecute=$false
$info.CreateNoWindow=$true
$info.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
$info.WorkingDirectory=Join-Path $PSScriptRoot 'P'
$child=[Diagnostics.Process]::new();$child.StartInfo=$info
$clock=[Diagnostics.Stopwatch]::StartNew()
try{
    if(-not $child.Start()){throw 'UE child launch failed'}
    while(-not $child.WaitForExit(200)){
        if($clock.Elapsed.TotalSeconds -ge $DeadlineSeconds){throw 'Shim deadline; supervisor must clean owned job'}
    }
    exit $child.ExitCode
}finally{$child.Dispose()}
