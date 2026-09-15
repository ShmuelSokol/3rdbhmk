# Operational helper: expand only the existing C: page file, without restarting.
# Uses normal Windows elevation; never changes UAC, services, or boot configuration.
# Automatic page-file management is retained. Capacity after a later boot is Windows-managed.
[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$targetMB = 65536
$receiptDir = 'C:\Mikdash\Working-5.8\MemoryRecovery'
$nativeSource = @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class MikdashPagefile {
    [StructLayout(LayoutKind.Sequential)] struct LUID { public uint Low; public int High; }
    [StructLayout(LayoutKind.Sequential)] struct TOKEN_PRIVILEGES { public uint Count; public LUID Luid; public uint Attributes; }
    [StructLayout(LayoutKind.Sequential)] struct UNICODE_STRING { public ushort Length; public ushort MaximumLength; public IntPtr Buffer; }
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool CloseHandle(IntPtr handle);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool LookupPrivilegeValue(string system, string name, out LUID luid);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool AdjustTokenPrivileges(IntPtr token, bool disableAll, ref TOKEN_PRIVILEGES next, uint length, out TOKEN_PRIVILEGES previous, out uint returned);
    [DllImport("ntdll.dll")] static extern int NtCreatePagingFile(ref UNICODE_STRING name, ref long minimum, ref long maximum, uint priority);
    public static int Expand64GB() {
        IntPtr token;
        if (!OpenProcessToken(GetCurrentProcess(), 0x28, out token)) throw new Win32Exception();
        TOKEN_PRIVILEGES previous = new TOKEN_PRIVILEGES();
        bool adjusted = false;
        IntPtr buffer = IntPtr.Zero;
        try {
            LUID luid;
            if (!LookupPrivilegeValue(null, "SeCreatePagefilePrivilege", out luid)) throw new Win32Exception();
            TOKEN_PRIVILEGES next = new TOKEN_PRIVILEGES { Count=1, Luid=luid, Attributes=2 };
            uint returned;
            bool ok = AdjustTokenPrivileges(token, false, ref next, (uint)Marshal.SizeOf(typeof(TOKEN_PRIVILEGES)), out previous, out returned);
            int error = Marshal.GetLastWin32Error();
            if (!ok || error != 0) throw new Win32Exception(error);
            adjusted = true;
            string path = @"\??\C:\pagefile.sys";
            buffer = Marshal.StringToHGlobalUni(path);
            UNICODE_STRING name = new UNICODE_STRING { Length=(ushort)(path.Length*2), MaximumLength=(ushort)((path.Length+1)*2), Buffer=buffer };
            long minimum = 64L*1024*1024*1024, maximum = minimum;
            return NtCreatePagingFile(ref name, ref minimum, ref maximum, 0);
        } finally {
            if (buffer != IntPtr.Zero) Marshal.FreeHGlobal(buffer);
            if (adjusted) { TOKEN_PRIVILEGES ignored; uint returned; AdjustTokenPrivileges(token, false, ref previous, (uint)Marshal.SizeOf(typeof(TOKEN_PRIVILEGES)), out ignored, out returned); }
            CloseHandle(token);
        }
    }
}
'@
Add-Type -TypeDefinition $nativeSource
if ($CheckOnly) { 'Native interop compiled; no settings changed.'; exit 0 }

function Read-Memory {
    $page = @(Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage)
    $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    [ordered]@{ pagefiles=$page; committedBytes=[long]$memory.CommittedBytes; commitLimit=[long]$memory.CommitLimit; automaticManagedPagefile=(Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile }
}
New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
$receiptPath = Join-Path $receiptDir ('pagefile-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ') + '.json')
$receipt = [ordered]@{ targetMB=$targetMB; restartRequested=$false; persistentSettingsChanged=$false; status='started'; before=$null; after=$null }
try {
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Requires ordinary Windows administrator elevation.' }
    $receipt.before = Read-Memory
    $current = @($receipt.before.pagefiles | Where-Object Name -EQ 'C:\pagefile.sys')
    if ($current.Count -ne 1) { throw 'Expected one existing C:\pagefile.sys. No page file created.' }
    if ($current[0].AllocatedBaseSize -ge $targetMB) { throw 'Existing page file is already at least 64 GB; refusing to shrink or change it.' }
    $growth = ($targetMB - [long]$current[0].AllocatedBaseSize) * 1MB
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
    if ($disk.FreeSpace -lt ($growth + 30GB)) { throw 'Insufficient free space to retain a 30 GB reserve.' }
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    $status = [MikdashPagefile]::Expand64GB()
    $receipt.nativeStatus = $status
    if ($status -lt 0) { throw ('Windows rejected live expansion, NTSTATUS {0:X8}.' -f $status) }
    Start-Sleep -Seconds 3
    $receipt.after = Read-Memory
    $afterPage = @($receipt.after.pagefiles | Where-Object Name -EQ 'C:\pagefile.sys')
    if ($afterPage.Count -ne 1 -or $afterPage[0].AllocatedBaseSize -lt $targetMB -or $receipt.after.commitLimit -lt ($receipt.before.commitLimit + $growth - 64MB)) {
        throw 'Live capacity increase not verified by both page-file size and commit limit.'
    }
    $receipt.status = 'live_expansion_verified'
} catch {
    $receipt.status = 'failed'
    $receipt.error = $_.Exception.Message
} finally {
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
}
if ($receipt.status -ne 'live_expansion_verified') { Write-Error $receipt.error; exit 1 }
Write-Output $receiptPath
