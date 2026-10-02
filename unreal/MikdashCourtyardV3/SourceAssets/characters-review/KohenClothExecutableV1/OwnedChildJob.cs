// Wrapper support only. Loaded by PowerShell AFTER approval/preflight, never by the UE plugin.
// Kernel job ownership prevents PID-reuse/tree-enumeration cleanup races.
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace KohenReviewGuard {
public sealed class Sample {
    public ulong PrivateBytes, PeakJobBytes;
    public uint ActiveProcesses;
    public bool RootExited;
    public uint ExitCode;
}
public sealed class OwnedChildJob : IDisposable {
    IntPtr job, root, thread, output, input;
    public uint ProcessId { get; private set; }
    public long CreationFileTime { get; private set; }
    public bool CleanupConfirmed { get; private set; }
    public string CleanupError { get; private set; }
    const uint SUSPENDED=4, NO_WINDOW=0x08000000, STILL_ACTIVE=259;
    const uint KILL_ON_CLOSE=0x2000, PROCESS_MEMORY=0x100, JOB_MEMORY=0x200;
    [StructLayout(LayoutKind.Sequential)] struct Security { public int Length; public IntPtr Descriptor; public int Inherit; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct Startup {
        public int cb; public string Reserved, Desktop, Title;
        public uint X,Y,XSize,YSize,XChars,YChars,Fill,Flags;
        public short Show, Reserved2; public IntPtr Bytes, StdIn, StdOut, StdErr;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo { public IntPtr Process, Thread; public uint Pid,Tid; }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimit {
        public long ProcessTime, JobTime; public uint Flags;
        public UIntPtr MinWorkingSet, MaxWorkingSet; public uint ActiveLimit;
        public UIntPtr Affinity; public uint Priority, Scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct Io { public ulong ROp,WOp,OOp,RBytes,WBytes,OBytes; }
    [StructLayout(LayoutKind.Sequential)] struct Limits {
        public BasicLimit Basic; public Io Io;
        public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
    }
    [StructLayout(LayoutKind.Sequential)] struct Accounting {
        public long User,Kernel,PeriodUser,PeriodKernel;
        public uint Faults,Total,Active,Terminated;
    }
    [StructLayout(LayoutKind.Sequential)] struct Counters {
        public uint Size,Faults; public UIntPtr PeakWorking,Working,PeakPaged,Paged,PeakNonPaged,NonPaged,Pagefile,PeakPagefile,Private;
    }
    [StructLayout(LayoutKind.Sequential)] struct Memory {
        public uint Length,Load; public ulong TotalPhysical,AvailablePhysical,TotalPageFile,AvailablePageFile,TotalVirtual,AvailableVirtual,Extended;
    }
    [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr attributes,string name);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int info,ref Limits value,uint length);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int info,IntPtr buffer,uint length,IntPtr returned);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool IsProcessInJob(IntPtr process,IntPtr job,out bool result);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateJobObject(IntPtr job,uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint milliseconds);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetProcessTimes(IntPtr process,out long creation,out long exit,out long kernel,out long user);
    [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
    [DllImport("psapi.dll",SetLastError=true)] static extern bool GetProcessMemoryInfo(IntPtr process,ref Counters counters,uint size);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GlobalMemoryStatusEx(ref Memory status);
    [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] static extern IntPtr CreateFile(string path,uint access,uint share,ref Security security,uint creation,uint flags,IntPtr template);
    [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] static extern bool CreateProcess(string app,StringBuilder command,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr environment,string cwd,ref Startup startup,out ProcessInfo info);
    static void Require(bool good) { if(!good) throw new Win32Exception(Marshal.GetLastWin32Error()); }
    static void Close(ref IntPtr h) { if(h!=IntPtr.Zero && h!=new IntPtr(-1)) CloseHandle(h); h=IntPtr.Zero; }
    public static ulong AvailableCommit() {
        Memory m=new Memory(); m.Length=(uint)Marshal.SizeOf(typeof(Memory)); Require(GlobalMemoryStatusEx(ref m)); return m.AvailablePageFile;
    }
    // Standard Windows argv quoting; do not invoke cmd.exe or interpolate shell text.
    public static string Quote(string value) {
        if(value.IndexOf('\0')>=0) throw new ArgumentException("NUL in argument");
        StringBuilder b=new StringBuilder("\""); int slashes=0;
        foreach(char c in value) {
            if(c=='\\') { slashes++; continue; }
            if(c=='\"') { b.Append('\\',slashes*2+1); b.Append(c); }
            else { b.Append('\\',slashes); b.Append(c); }
            slashes=0;
        }
        b.Append('\\',slashes*2); b.Append('"'); return b.ToString();
    }
    T Query<T>(int type) where T:struct {
        int size=Marshal.SizeOf(typeof(T)); IntPtr p=Marshal.AllocHGlobal(size);
        try { Require(QueryInformationJobObject(job,type,p,(uint)size,IntPtr.Zero)); return (T)Marshal.PtrToStructure(p,typeof(T)); }
        finally { Marshal.FreeHGlobal(p); }
    }
    public OwnedChildJob(string exe,string[] args,string cwd,string log,ulong cap) {
        if(IntPtr.Size!=8) throw new InvalidOperationException("64-bit host required");
        try {
            job=CreateJobObject(IntPtr.Zero,null); Require(job!=IntPtr.Zero);
            Limits limits=new Limits(); limits.Basic.Flags=KILL_ON_CLOSE|PROCESS_MEMORY|JOB_MEMORY;
            limits.ProcessMemory=new UIntPtr(cap); limits.JobMemory=new UIntPtr(cap);
            Require(SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf(typeof(Limits))));
            Security sa=new Security {Length=Marshal.SizeOf(typeof(Security)),Inherit=1};
            output=CreateFile(log,0x40000000,1,ref sa,1,0x80,IntPtr.Zero); Require(output!=new IntPtr(-1)); // CREATE_NEW
            input=CreateFile("NUL",0x80000000,3,ref sa,3,0x80,IntPtr.Zero); Require(input!=new IntPtr(-1));
            Startup si=new Startup(); si.cb=Marshal.SizeOf(typeof(Startup)); si.Flags=0x101; si.Show=0;
            si.StdIn=input; si.StdOut=output; si.StdErr=output;
            StringBuilder command=new StringBuilder(Quote(exe)); foreach(string a in args) command.Append(" ").Append(Quote(a));
            ProcessInfo pi;
            Require(CreateProcess(exe,command,IntPtr.Zero,IntPtr.Zero,true,SUSPENDED|NO_WINDOW,IntPtr.Zero,cwd,ref si,out pi));
            root=pi.Process; thread=pi.Thread; ProcessId=pi.Pid;
            long created,exit,kernel,user; Require(GetProcessTimes(root,out created,out exit,out kernel,out user)); CreationFileTime=created;
            // No child code executes before kernel ownership is established. No breakaway flags.
            Require(AssignProcessToJobObject(job,root));
            Require(ResumeThread(thread)!=0xffffffff); Close(ref thread); Close(ref output); Close(ref input);
        } catch(Exception error) {
            // Retained handle, including assign-to-job failure: never PID/name-based termination.
            if(root!=IntPtr.Zero) {
                error.Data["OwnedProcessId"]=ProcessId;
                error.Data["OwnedCreationFileTime"]=CreationFileTime;
                TerminateProcess(root,0xdead);
                error.Data["OwnedCleanupConfirmed"]=(WaitForSingleObject(root,5000)==0);
            }
            Dispose(); throw;
        }
    }
    public Sample Poll() {
        if(job==IntPtr.Zero) throw new ObjectDisposedException("OwnedChildJob");
        Sample s=new Sample();
        uint wait=WaitForSingleObject(root,0);
        if(wait==0xffffffff) throw new Win32Exception(Marshal.GetLastWin32Error()); // WAIT_FAILED
        if(wait==0) { // WAIT_OBJECT_0: the exit code is now final; 259 is also a valid exit code.
            uint code; Require(GetExitCodeProcess(root,out code));
            s.RootExited=true; s.ExitCode=code;
        } else if(wait!=258) { // WAIT_TIMEOUT: never read the provisional exit code.
            throw new InvalidOperationException("Unexpected process wait result: "+wait);
        }
        s.ActiveProcesses=Query<Accounting>(1).Active; s.PeakJobBytes=Query<Limits>(9).PeakJobMemory.ToUInt64();
        // Job membership, not parent PID ancestry, establishes every queried handle's ownership.
        const int bytes=65536; IntPtr p=Marshal.AllocHGlobal(bytes);
        try {
            Require(QueryInformationJobObject(job,3,p,bytes,IntPtr.Zero));
            int count=Marshal.ReadInt32(p,4); if(count<0 || count>(bytes-8)/8) throw new InvalidOperationException("Job PID list invalid");
            for(int i=0;i<count;i++) {
                uint pid=checked((uint)Marshal.ReadInt64(p,8+i*8)); IntPtr proc=OpenProcess(0x00100410,false,pid);
                if(proc==IntPtr.Zero) {
                    if(Marshal.GetLastWin32Error()==87) continue; // member exited since snapshot
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }
                try {
                    bool member; Require(IsProcessInJob(proc,job,out member)); if(!member) continue; // PID reuse, never adopt
                    Counters m=new Counters(); m.Size=(uint)Marshal.SizeOf(typeof(Counters));
                    if(!GetProcessMemoryInfo(proc,ref m,m.Size)) {
                        if(WaitForSingleObject(proc,0)==0) continue;
                        throw new Win32Exception(Marshal.GetLastWin32Error());
                    }
                    s.PrivateBytes+=m.Private.ToUInt64();
                } finally { CloseHandle(proc); }
            }
        } finally { Marshal.FreeHGlobal(p); }
        return s;
    }
    public bool StopWithinFiveSeconds() {
        Stopwatch timer=Stopwatch.StartNew(); CleanupConfirmed=false; CleanupError=null;
        var members=new List<IntPtr>();
        try {
            // Capture owned handles BEFORE termination; job accounting can reach zero
            // before process handles signal. Never trust a PID without membership validation.
            const int bytes=65536; IntPtr list=Marshal.AllocHGlobal(bytes);
            try {
                Require(QueryInformationJobObject(job,3,list,bytes,IntPtr.Zero));
                int count=Marshal.ReadInt32(list,4);
                if(count<0 || count>(bytes-8)/8) throw new InvalidOperationException("Cleanup job PID list invalid");
                for(int i=0;i<count;i++) {
                    if(timer.ElapsedMilliseconds>=5000) throw new TimeoutException("Cleanup handle capture reached5s deadline");
                    uint pid=checked((uint)Marshal.ReadInt64(list,8+i*8));
                    if(pid==ProcessId) continue; // original retained root handle below
                    IntPtr member=OpenProcess(0x00100400,false,pid); // SYNCHRONIZE | QUERY_INFORMATION
                    if(member==IntPtr.Zero) {
                        int error=Marshal.GetLastWin32Error();
                        if(error==87) continue; // process already gone
                        throw new Win32Exception(error);
                    }
                    try {
                        bool ours; Require(IsProcessInJob(member,job,out ours));
                        if(ours) { members.Add(member); member=IntPtr.Zero; }
                    } finally { Close(ref member); }
                }
            } finally { Marshal.FreeHGlobal(list); }
        } catch(Exception e) { CleanupError="Cannot confirm all captured ownership: "+e.Message; }
        try {
            // Still terminate the retained job if capture failed; never claim confirmation.
            Require(TerminateJobObject(job,0xdead));
            if(CleanupError!=null) return false;
            while(timer.ElapsedMilliseconds<5000) {
                bool signaled=IsSignaled(root);
                foreach(IntPtr member in members) { if(!IsSignaled(member)) signaled=false; }
                uint active=Query<Accounting>(1).Active;
                if(signaled && active==0 && timer.ElapsedMilliseconds<5000) { CleanupConfirmed=true; return true; }
                Thread.Sleep((int)Math.Min(50,Math.Max(1,5000-timer.ElapsedMilliseconds)));
            }
            CleanupError="Owned root/member handle unsignaled or job active at5s cleanup deadline";
        } catch(Exception e) { CleanupError=e.Message; }
        finally { foreach(IntPtr member in members) CloseHandle(member); }
        return false;
    }
    static bool IsSignaled(IntPtr process) {
        uint wait=WaitForSingleObject(process,0);
        if(wait==0xffffffff) throw new Win32Exception(Marshal.GetLastWin32Error()); // WAIT_FAILED
        if(wait==0) return true;
        if(wait==258) return false; // WAIT_TIMEOUT
        throw new InvalidOperationException("Unexpected cleanup wait result: "+wait);
    }
    public void Dispose() {
        // KILL_ON_JOB_CLOSE is fail-safe if the PowerShell host exits unexpectedly.
        // Normal cleanup calls StopWithinFiveSeconds first and records confirmation.
        Close(ref job); Close(ref thread); Close(ref root); Close(ref output); Close(ref input);
    }
}
}
