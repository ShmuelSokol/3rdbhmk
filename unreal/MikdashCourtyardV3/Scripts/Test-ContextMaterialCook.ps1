<# Isolated single-material experiment. Never stages/deploys assets or requests a map.
   Run -SelfTest for offline checks; -PlanOnly prints the recipe without launching.
#>
param(
    [ValidateSet('M_Context_CityWall','M_Context_Building','M_CityFacadeV1')]
    [string]$Material='M_Context_CityWall',
    [ValidateRange(1,600)][int]$TimeoutSeconds=600,
    [switch]$AllCoursingFamilies,
    [string]$DependencyAuditReceipt,
    [switch]$Constrained,
    [switch]$PlanOnly,
    [switch]$SelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$project=Split-Path $PSScriptRoot -Parent
$engine='C:/Program Files/Epic Games/UE_5.8/Engine'
$exe=Join-Path $engine 'Binaries/Win64/UnrealEditor-Cmd.exe'
$studyRoot='C:/Mikdash/Working-5.8/ContextPatchStudies'
function Get-CookLimits([bool]$UseConstrained) {
    if($UseConstrained){return [ordered]@{name='constrained-single-material';initialBytes=[long](8.5GB);maximumBytes=[long](5.5GB);reserveBytes=[long](2.5GB)}}
    return [ordered]@{name='default';initialBytes=[long](9GB);maximumBytes=[long](6.5GB);reserveBytes=[long](2GB)}
}
$limits=Get-CookLimits ([bool]$Constrained)
$masters=[ordered]@{
    M_Context_CityWall='/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall'
    M_Context_Building='/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building'
    M_CityFacadeV1='/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/M_CityFacadeV1'
}
# Create suspended, assign to a kill-on-close job, then resume: no descendant can
# escape in the Start-Process/AssignProcessToJobObject race. No breakaway allowed.
if(-not ('ContextCookJobV1' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.ComponentModel;
using System.Runtime.InteropServices;
public sealed class ContextCookJobV1 : IDisposable {
    IntPtr job, process;
    public int Pid { get; private set; }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimit { public long PerProcess, PerJob; public uint Flags; public UIntPtr MinWorking, MaxWorking; public uint Active; public UIntPtr Affinity; public uint Priority, Scheduling; }
    [StructLayout(LayoutKind.Sequential)] struct IOCounters { public ulong A,B,C,D,E,F; }
    [StructLayout(LayoutKind.Sequential)] struct ExtendedLimit { public BasicLimit Basic; public IOCounters IO; public UIntPtr ProcessMemory, JobMemory, PeakProcess, PeakJob; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct Startup { public uint cb; public string Reserved, Desktop, Title; public uint X,Y,XSize,YSize,XChars,YChars,Fill,Flags; public ushort Show, Reserved2; public IntPtr ReservedPtr, In, Out, Err; }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo { public IntPtr Process, Thread; public uint Pid, Tid; }
    [StructLayout(LayoutKind.Sequential)] struct Performance { public uint Size; public UIntPtr Total, Limit, Peak, PhysicalTotal, PhysicalAvailable, SystemCache, KernelTotal, KernelPaged, KernelNonpaged, PageSize; public uint Handles, Processes, Threads; }
    [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr attrs, string name);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr h, int kind, ref ExtendedLimit info, uint len);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr h, IntPtr p);
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)] static extern bool CreateProcess(string app, StringBuilder command, IntPtr pa, IntPtr ta, bool inherit, uint flags, IntPtr env, string cwd, ref Startup si, out ProcessInfo pi);
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint ResumeThread(IntPtr h);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool TerminateProcess(IntPtr h, uint code);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr h, int kind, IntPtr info, uint len, out uint used);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr p, out uint code);
    [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr h, uint ms);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
    [DllImport("psapi.dll", SetLastError=true)] static extern bool GetPerformanceInfo(ref Performance p, uint size);
    static Exception Error(string action) { return new Win32Exception(Marshal.GetLastWin32Error(), action); }
    public static string Quote(string s) {
        var b=new StringBuilder("\""); int slash=0;
        foreach(char c in s) { if(c=='\\') { slash++; continue; } if(c=='\"') { b.Append('\\',slash*2+1); b.Append(c); } else { b.Append('\\',slash); b.Append(c); } slash=0; }
        b.Append('\\',slash*2); return b.Append('"').ToString();
    }
    public static ulong FreeCommit() { var p=new Performance(); p.Size=(uint)Marshal.SizeOf(p); if(!GetPerformanceInfo(ref p,p.Size)) throw Error("GetPerformanceInfo"); return (p.Limit.ToUInt64()-p.Total.ToUInt64())*p.PageSize.ToUInt64(); }
    public ContextCookJobV1(string exe, string[] args, string cwd) {
        job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero) throw Error("CreateJobObject");
        ProcessInfo pi=new ProcessInfo();
        try {
            var limits=new ExtendedLimit(); limits.Basic.Flags=0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if(!SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf(limits))) throw Error("SetInformationJobObject");
            var cmd=new StringBuilder(Quote(exe)); foreach(string a in args) cmd.Append(' ').Append(Quote(a));
            var si=new Startup(); si.cb=(uint)Marshal.SizeOf(si); si.Flags=1; si.Show=0;
            if(!CreateProcess(exe,cmd,IntPtr.Zero,IntPtr.Zero,false,0x08000004,IntPtr.Zero,cwd,ref si,out pi)) throw Error("CreateProcess suspended hidden");
            process=pi.Process; Pid=(int)pi.Pid;
            if(!AssignProcessToJobObject(job,process)) throw Error("AssignProcessToJobObject");
            if(ResumeThread(pi.Thread)==0xffffffff) throw Error("ResumeThread");
        } catch { if(pi.Process!=IntPtr.Zero) TerminateProcess(pi.Process,1); Dispose(); throw; }
        finally { if(pi.Thread!=IntPtr.Zero) CloseHandle(pi.Thread); }
    }
    public bool HasExited { get { return WaitForSingleObject(process,0)==0; } }
    public uint ExitCode { get { uint c; if(!GetExitCodeProcess(process,out c)) throw Error("GetExitCodeProcess"); return c; } }
    public int[] Members() {
        int capacity=4096, size=8+IntPtr.Size*capacity; IntPtr b=Marshal.AllocHGlobal(size);
        try { uint used; if(!QueryInformationJobObject(job,3,b,(uint)size,out used)) throw Error("QueryInformationJobObject"); int n=Marshal.ReadInt32(b,4); if(n>capacity) throw new Exception("Job process census overflow"); var ids=new int[n]; for(int i=0;i<n;i++) ids[i]=(int)Marshal.ReadIntPtr(b,8+i*IntPtr.Size); return ids; }
        finally { Marshal.FreeHGlobal(b); }
    }
    public void Dispose() { if(job!=IntPtr.Zero) { CloseHandle(job); job=IntPtr.Zero; } if(process!=IntPtr.Zero) { CloseHandle(process); process=IntPtr.Zero; } GC.SuppressFinalize(this); }
    ~ContextCookJobV1() { Dispose(); }
}
'@
}
function Get-LogEvidence([string]$Text,[string[]]$MapPackages) {
    $rows=@($Text -split '\r?\n')
    $cookRows=@($rows | Where-Object {$_ -match 'LogCook:.*(?:Cooking /|Enqueing cook request|Request for |Loading package |DemoteToRequest:)'})
    $mapRows=@($rows | Where-Object {$_ -match '(?:LogCook|LogLoad|LogSavePackage|LogStreaming):.*(?:\.umap\b|LoadMap:)'})
    foreach($name in $MapPackages) {
        $pattern=[regex]::Escape($name)+'(?=[,\s''".]|$)'
        $mapRows+=@($cookRows | Where-Object {$_ -match $pattern})
    }
    $packages=@([regex]::Matches($Text,'LogCook:.*?Cooking (/[^,\s]+)') | ForEach-Object {$_.Groups[1].Value} | Sort-Object -Unique)
    return [ordered]@{
        successSummary=($Text -match 'LogInit: Display: Success - 0 error\(s\), \d+ warning\(s\)')
        fatalOrError=($Text -match '(?m)(?:Fatal error:|^.*Log[^:]*: Error:|Failure - \d+ error\(s\))')
        mapEvidence=@($mapRows | Sort-Object -Unique)
        cookingPackages=$packages
        requestAndCookRows=$cookRows
        workerCounts=@([regex]::Matches($Text,'Using (\d+) local workers for shader compilation') | ForEach-Object {[int]$_.Groups[1].Value})
    }
}
if($SelfTest) {
    $defaultLimits=Get-CookLimits $false
    $tightLimits=Get-CookLimits $true
    if($defaultLimits.initialBytes -ne 9GB -or $defaultLimits.maximumBytes -ne 6.5GB -or $defaultLimits.reserveBytes -ne 2GB){throw 'Default profile changed'}
    if($tightLimits.initialBytes -ne 8.5GB -or $tightLimits.maximumBytes -ne 5.5GB -or $tightLimits.reserveBytes -ne 2.5GB){throw 'Constrained profile mismatch'}
    if(($tightLimits.initialBytes-$tightLimits.maximumBytes-$tightLimits.reserveBytes) -ne 0.5GB -or $tightLimits.reserveBytes -le $defaultLimits.reserveBytes){throw 'Constrained cushion/reserve mismatch'}
    if([ContextCookJobV1]::Quote('C:\folder with space\') -ne '"C:\folder with space\\"'){throw 'Trailing slash quotation failed'}
    if([ContextCookJobV1]::Quote('a"b') -ne '"a\"b"'){throw 'Embedded quote failed'}
    $fixture="LogCook: Display: Cooking /Game/Material, Instigator: { CommandLine }`nLogInit: Display: Success - 0 error(s), 2 warning(s)"
    $e=Get-LogEvidence $fixture @('/Game/Map')
    if(!$e.successSummary -or $e.fatalOrError -or $e.mapEvidence.Count -or $e.cookingPackages.Count -ne 1){throw 'Success census failed'}
    $e=Get-LogEvidence ($fixture+"`nLogCook: Display: Cooking /Game/Map, Instigator: { Dependency }") @('/Game/Map')
    if($e.mapEvidence.Count -ne 1){throw 'Long package map detection failed'}
    $e=Get-LogEvidence "LogCook: Verbose: Enqueing cook request, Filename='C:/Content/Map.umap', Platform='Windows'" @()
    if($e.mapEvidence.Count -ne 1){throw 'Filename map request detection failed'}
    $e=Get-LogEvidence 'LogLoad: LoadMap: /Engine/Maps/Entry' @()
    if($e.mapEvidence.Count -ne 1){throw 'Unexpected map load detection failed'}
    $e=Get-LogEvidence 'LogShaderCompilers: Error: Shader compile failed' @()
    if(!$e.fatalOrError){throw 'Shader error detection failed'}
    'PASS: C# helper compiled; 10 offline profile/quote/log assertions; no process launched.'; return
}
function Read-PinnedDependencyAudit {
    if(!$DependencyAuditReceipt){throw '-AllCoursingFamilies requires -DependencyAuditReceipt'}
    $auditJson=& python (Join-Path $PSScriptRoot 'prepare_context_iostore_patch.py') --validate-audit $DependencyAuditReceipt
    if($LASTEXITCODE -ne 0){throw 'Pinned dependency audit validation failed'}
    return ($auditJson | ConvertFrom-Json)
}
$dependencyAudit=$null
$requestedPackages=@($masters[$Material])
$studyLabel=$Material
if($AllCoursingFamilies){
    if(!$Constrained){throw '-AllCoursingFamilies requires the explicit -Constrained memory profile'}
    if($PSBoundParameters.ContainsKey('Material')){throw '-Material and -AllCoursingFamilies are mutually exclusive'}
    $dependencyAudit=Read-PinnedDependencyAudit
    $requestedPackages=@($dependencyAudit.packages)
    if($requestedPackages.Count -ne 13){throw 'Expected exactly 13 audited family packages'}
    $studyLabel='AllCoursingFamilies'
} elseif($DependencyAuditReceipt){throw '-DependencyAuditReceipt requires -AllCoursingFamilies'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$study=Join-Path $studyRoot "$studyLabel-$stamp"
$log=Join-Path $study 'cook.log'
$launchArgs=@((Join-Path $project 'MikdashCourtyardV3.uproject'),'-run=Cook','-TargetPlatform=Windows',
    ('-Package='+($requestedPackages -join '+')),'-CookSinglePackage','-CookSkipRequests','-SkipZenStore',
    ('-OutputDir='+(Join-Path $study 'Cooked/[Platform]')),
    '-ini:Game:[/Script/UnrealEd.ProjectPackagingSettings]:bShareMaterialShaderCode=False',
    '-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=999,[DevOptions.Shaders]:NumUnusedShaderCompilingThreadsDuringGame=999,[DevOptions.Shaders]:bForceUseSCWMemoryPressureLimits=False',
    '-cookprocesscount=1','-NoAsyncLoadingThread','-unattended','-nosplash',
    '-cookshowpackagenames','-cookshowinstigators','-LogCmds=LogCook Verbose,LogSavePackage Verbose',('-abslog='+$log))
if($PlanOnly) { [ordered]@{executable=$exe;arguments=$launchArgs;study=$study;requestedPackages=$requestedPackages;allCoursingFamilies=[bool]$AllCoursingFamilies;dependencyAudit=$dependencyAudit;timeoutSeconds=$TimeoutSeconds;memoryProfile=$limits.name;initialFreeCommitGiB=($limits.initialBytes/1GB);reserveGiB=($limits.reserveBytes/1GB);maxOwnedPrivateGiB=($limits.maximumBytes/1GB);nativeLaunched=$false}|ConvertTo-Json -Depth 5; return }
function Assert-NativeSlot {
    $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(?:Unreal.*|ShaderCompileWorker|AutomationTool|UnrealBuildTool|RunUAT|dotnet|MikdashCourtyardV3).*\.exe$' -or ($_.Name -match '^(cmd|powershell|pwsh)\.exe$' -and $_.CommandLine -match '(?:RunUAT\.bat|UnrealBuildTool|AutomationTool\.dll)')})
    if($busy.Count){throw ('Native slot occupied: '+(($busy | ForEach-Object {"$($_.Name):$($_.ProcessId)"}) -join ', '))}
}
function Content-Snapshot {
    $content=Join-Path $project 'Content'
    $files=@(Get-ChildItem -LiteralPath $content -Recurse -File | Sort-Object FullName)
    $metadata=@($files | ForEach-Object {[ordered]@{path=$_.FullName.Substring($content.Length+1).Replace('\','/');bytes=$_.Length;lastWriteUtcTicks=$_.LastWriteTimeUtc.Ticks}})
    $maps=[ordered]@{}; foreach($f in @($files | Where-Object Extension -eq '.umap')){$maps[$f.FullName]=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
    $masterHashes=[ordered]@{}; foreach($name in $masters.Keys){$file=Join-Path $content ($masters[$name].Substring(6)+'.uasset');$masterHashes[$name]=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()}
    $requestedHashes=[ordered]@{}; foreach($packageName in $requestedPackages){$file=Join-Path $content ($packageName.Substring(6)+'.uasset');$requestedHashes[$packageName]=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()}
    return [ordered]@{metadata=$metadata;mapHashes=$maps;masterHashes=$masterHashes;requestedHashes=$requestedHashes}
}
New-Item -ItemType Directory -Path $study | Out-Null
$receipt=Join-Path $study 'receipt.json'
$r=[ordered]@{status='preflight';startedUtc=(Get-Date).ToUniversalTime().ToString('o');study=$study;executable=$exe;arguments=$launchArgs;material=$studyLabel;package=($requestedPackages -join '+');requestedPackages=$requestedPackages;allCoursingFamilies=[bool]$AllCoursingFamilies;dependencyAudit=$dependencyAudit;timeoutSeconds=$TimeoutSeconds;nativeLaunched=$false;memoryProfile=$limits.name;maxOwnedPrivateBytes=$limits.maximumBytes;reserveBytes=$limits.reserveBytes;initialRequiredFreeCommitBytes=$limits.initialBytes;peakOwnedPrivateBytes=[long]0;minimumFreeCommitBytes=[long]::MaxValue;observedProcesses=@();error=$null}
function Save-Receipt {$r | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $receipt -Encoding utf8}
$job=$null; $before=$null; $observed=@{}; $mapPackages=@()
try {
    Save-Receipt
    Assert-NativeSlot
    if(!(Test-Path -LiteralPath $exe)){throw 'Editor commandlet missing'}
    # UE overrides the unused-thread setting on <=4 cores; fail rather than imply a one-worker bound there.
    $cores=[int](Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
    if($cores -le 4){throw 'One-worker configuration requires more than four logical cores in this UE version'}
    $before=Content-Snapshot
    $before | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $study 'source-before.json') -Encoding utf8
    if($before.mapHashes.Count -ne 20){throw "Expected 20 protected maps; found $($before.mapHashes.Count)"}
    $mapPackages=@($before.mapHashes.Keys | ForEach-Object {'/Game/'+$_.Substring((Join-Path $project 'Content').Length+1).Replace('\','/').Replace('.umap','')})
    $r.requestedSourceHashesBefore=$before.requestedHashes; $r.sourceMastersBefore=$before.masterHashes; $r.mapCount=$before.mapHashes.Count; $r.contentFileCount=$before.metadata.Count
    $r.executableSha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    $r.engineVersion=Get-Content -LiteralPath (Join-Path $engine 'Build/Build.version') -Raw | ConvertFrom-Json
    Assert-NativeSlot
    if($AllCoursingFamilies){$r.dependencyAudit=Read-PinnedDependencyAudit}
    $r.initialFreeCommitBytes=[long][ContextCookJobV1]::FreeCommit()
    if($r.initialFreeCommitBytes -lt $limits.initialBytes){throw ('Less than {0} GiB free system commit ({1}); nothing launched' -f ($limits.initialBytes/1GB),$limits.name)}
    Save-Receipt
    $job=[ContextCookJobV1]::new($exe,[string[]]$launchArgs,$project)
    $r.nativeLaunched=$true; $r.pid=$job.Pid; $r.status='running'; Save-Receipt
    $timer=[Diagnostics.Stopwatch]::StartNew()
    while($true) {
        $sum=[long]0
        foreach($memberId in $job.Members()) {
            $p=Get-Process -Id $memberId -ErrorAction SilentlyContinue
            if($p){$sum+=$p.PrivateMemorySize64; $observed["$memberId"]=[ordered]@{pid=$memberId;name=$p.ProcessName;startUtc=$p.StartTime.ToUniversalTime().ToString('o')}}
        }
        $free=[long][ContextCookJobV1]::FreeCommit()
        $r.peakOwnedPrivateBytes=[Math]::Max([long]$r.peakOwnedPrivateBytes,$sum)
        $r.minimumFreeCommitBytes=[Math]::Min([long]$r.minimumFreeCommitBytes,$free)
        if($sum -gt $limits.maximumBytes -or $free -lt $limits.reserveBytes){throw ('Cooker/job reached memory bound ({0} GiB total private / {1} GiB system reserve; {2})' -f ($limits.maximumBytes/1GB),($limits.reserveBytes/1GB),$limits.name)}
        if(Test-Path -LiteralPath $log){
            $liveEvidence=Get-LogEvidence (Get-Content -LiteralPath $log -Raw) $mapPackages
            if($liveEvidence.mapEvidence.Count){throw 'Unexpected map request/load detected; stopping owned job'}
        }
        if($job.HasExited){$r.exitCode=$job.ExitCode; break}
        if($timer.Elapsed.TotalSeconds -ge $TimeoutSeconds){throw 'Cook timeout reached'}
        Start-Sleep -Milliseconds 1000
    }
    if($r.exitCode -ne 0){throw "Cook exited $($r.exitCode)"}
    $r.status='cook-exited-validation-pending'
} catch {$r.status='failed'; $r.error=$_.Exception.Message}
finally {
    if($job){
        try {$r.jobMembersBeforeCleanup=@($job.Members())}
        catch {$r.status='failed';$r.error='Job census failed during cleanup: '+$_.Exception.Message}
        finally {$job.Dispose();$job=$null}
    }
    $r.observedProcesses=@($observed.Values | Sort-Object pid)
    try {
        $after=Content-Snapshot
        $after | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $study 'source-after.json') -Encoding utf8
        if($before){
            $r.requestedSourceHashesUnchanged=(($before.requestedHashes|ConvertTo-Json -Compress) -eq ($after.requestedHashes|ConvertTo-Json -Compress))
            $r.requestedSourceHashesAfter=$after.requestedHashes
            $r.mapsUnchanged=(($before.mapHashes|ConvertTo-Json -Compress) -eq ($after.mapHashes|ConvertTo-Json -Compress))
            $r.sourceMastersUnchanged=(($before.masterHashes|ConvertTo-Json -Compress) -eq ($after.masterHashes|ConvertTo-Json -Compress))
            $r.contentMetadataUnchanged=(($before.metadata|ConvertTo-Json -Compress -Depth 4) -eq ($after.metadata|ConvertTo-Json -Compress -Depth 4))
            if(!$r.requestedSourceHashesUnchanged -or !$r.mapsUnchanged -or !$r.sourceMastersUnchanged -or !$r.contentMetadataUnchanged){throw 'Production Content metadata, map bytes or master bytes changed'}
        }
        $r.outputs=@(Get-ChildItem -LiteralPath $study -Recurse -File | Where-Object {$_.FullName -like "$study\Cooked\*"} | Sort-Object FullName | ForEach-Object {[ordered]@{path=$_.FullName.Substring($study.Length+1);bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}})
        $r.cookedMapOutputs=@($r.outputs | Where-Object {$_.path -match '\.umap$'})
        $r.cookedPackageOutputs=@($r.outputs | Where-Object {$_.path -match '\.uasset$'})
        if(Test-Path -LiteralPath $log){$r.logEvidence=Get-LogEvidence (Get-Content -LiteralPath $log -Raw) $mapPackages}
        if($r.status -eq 'cook-exited-validation-pending') {
            if(!$r.logEvidence.successSummary -or $r.logEvidence.fatalOrError){throw 'Missing zero-error cook success summary or logged cook error'}
            if($r.logEvidence.mapEvidence.Count -or $r.cookedMapOutputs.Count){throw 'Map request/load/output found'}
            foreach($packageName in $requestedPackages){
                if($r.logEvidence.cookingPackages -notcontains $packageName){throw ('Requested package absent from log census: '+$packageName)}
                foreach($segment in @('.uasset','.uexp')){
                    if(!@($r.outputs | Where-Object {$_.path.Replace('\','/').EndsWith('/'+$packageName.Substring(6)+$segment)}).Count){throw ('Requested cooked package segment missing: '+$packageName+$segment)}
                }
            }
            if(!$r.logEvidence.workerCounts.Count -or @($r.logEvidence.workerCounts | Where-Object {$_ -ne 1}).Count){throw 'One local shader worker was not confirmed by engine log'}
            $r.status='cook-passed-package-review-pending'
        }
    } catch {$r.status='failed'; $r.error=(@($r.error,$_.Exception.Message) | Where-Object {$_}) -join '; '}
    $r.scope='Isolated filesystem cook only. Receipt records cooker/load map evidence, map outputs, all 20 map hashes, three source-master hashes and all Content metadata. Passed means zero observed map requests/outputs; dependency census still requires review. No packaged shader/visual acceptance.'
    $r.finishedUtc=(Get-Date).ToUniversalTime().ToString('o'); Save-Receipt
}
[ordered]@{status=$r.status;receipt=$receipt;log=$log;error=$r.error}|ConvertTo-Json
if($r.status -eq 'failed'){exit 1}
