#pragma once
// Actual Win32 implementation, shared unchanged with harmless non-UE tests.
#ifndef _WINDOWS_
#include <windows.h>
#endif
#include <cmath>
#include "PrivateEnvelope.h"
namespace MikdashOnline::Settings05 {
inline double Qpc(){LARGE_INTEGER t,f;if(!QueryPerformanceCounter(&t)||!QueryPerformanceFrequency(&f)||f.QuadPart<=0)return -1;return double(t.QuadPart)/f.QuadPart;}
inline bool ProcessIdentity(uint32_t pid,uint64_t created){
    FILETIME c,e,k,u;
    return pid==GetCurrentProcessId()&&GetProcessTimes(GetCurrentProcess(),&c,&e,&k,&u)&&
        ((uint64_t(c.dwHighDateTime)<<32)|c.dwLowDateTime)==created;
}
class WinLease final {
    Descriptor d;HANDLE event=nullptr,root=nullptr;bool used=false,revoked=false;
    double deadline=0,last=-1;
    bool RootMatches() const {
        BY_HANDLE_FILE_INFORMATION i{};wchar_t path[1024]{};
        const DWORD n=GetFinalPathNameByHandleW(root,path,1024,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
        std::wstring expected=L"\\\\?\\"+std::wstring(d.root.begin(),d.root.end());
        for(auto& c:expected)if(c==L'/')c=L'\\';
        return n>0&&n<1024&&_wcsicmp(path,expected.c_str())==0&&GetFileInformationByHandle(root,&i)&&
            (i.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)&&!(i.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)&&
            i.dwVolumeSerialNumber==d.volume&&((uint64_t(i.nFileIndexHigh)<<32)|i.nFileIndexLow)==d.file;
    }
public:
    WinLease()=default;WinLease(const WinLease&)=delete;WinLease& operator=(const WinLease&)=delete;
    ~WinLease(){Close();}
    bool Bind(const Descriptor& value,double end){
        if(used)return false;used=true;d=value;
        const double now=Qpc();
        if(!RootSyntax(d.root)||!std::isfinite(end)||now<0||end<=now||end-now>86400||
           !ProcessIdentity(d.pid,d.created)||d.event>UINTPTR_MAX)return false;
        // Transfer ownership ONLY after complete trusted envelope+v1 admission.
        event=reinterpret_cast<HANDLE>(uintptr_t(d.event));deadline=end;
        DWORD flags=0;
        if(!GetHandleInformation(event,&flags)||(flags&HANDLE_FLAG_INHERIT)||WaitForSingleObject(event,0)!=WAIT_TIMEOUT){revoked=true;return false;}
        std::wstring path(d.root.begin(),d.root.end());
        root=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,
                         FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
        if(root==INVALID_HANDLE_VALUE){root=nullptr;revoked=true;return false;}
        return Live();
    }
    bool Live(){
        const double now=Qpc();
        if(revoked||!used||!root||!event||!std::isfinite(now)||now<0||now<last||now>=deadline||
           !ProcessIdentity(d.pid,d.created)||WaitForSingleObject(event,0)!=WAIT_TIMEOUT||!RootMatches()){
            revoked=true;return false;}
        last=now;return true;
    }
    void Revoke(){revoked=true;}
    bool Close(){
        Revoke();bool ok=true;
        if(root){if(CloseHandle(root))root=nullptr;else ok=false;}
        if(event){if(CloseHandle(event))event=nullptr;else ok=false;}
        return ok;
    }
};
}
