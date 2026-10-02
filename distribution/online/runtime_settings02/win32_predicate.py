"""Real Win32 filesystem probe, transcribed from frozen settings01 DiskPath.

This is NOT compiled UE C++, not a fake Unreal API, and not the complete
SettingsOwned callback. Source hash locks the audited implementation it models.
All kernel handles and file information below are actual Windows calls.
"""
import ctypes as C
from ctypes import wintypes as W
import importlib.util
from pathlib import Path
import hashlib
import json
import os

FROZEN = Path(__file__).resolve().parent.parent / 'runtime_settings01'
MANIFEST_SHA = '0bf99f7c893e91be22442a615426b11ad5625b01f71a200d6cc458a8cd42fbd7'

def verify_frozen():
    data=(FROZEN/'manifest.json').read_bytes()
    if hashlib.sha256(data).hexdigest()!=MANIFEST_SHA:
        raise RuntimeError('settings01 manifest changed')
    pins=json.loads(data)
    for name,sha in pins.items():
        if hashlib.sha256((FROZEN/name).read_bytes()).hexdigest()!=sha:
            raise RuntimeError('settings01 changed: '+name)
    return pins

verify_frozen()
spec=importlib.util.spec_from_file_location('frozen_launcher',FROZEN/'launcher_contract.py')
lex=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lex)
if os.name!='nt': raise RuntimeError('Windows required; no simulation fallback')
k=C.WinDLL('kernel32',use_last_error=True)
s=C.WinDLL('shell32',use_last_error=True)

class FileTime(C.Structure):
    _fields_=[('low',W.DWORD),('high',W.DWORD)]
class Info(C.Structure):
    _fields_=[('attrs',W.DWORD),('creation',FileTime),('access',FileTime),
              ('write',FileTime),('volume',W.DWORD),('size_high',W.DWORD),
              ('size_low',W.DWORD),('links',W.DWORD),('id_high',W.DWORD),('id_low',W.DWORD)]

k.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,W.LPVOID,W.DWORD,W.DWORD,W.HANDLE]
k.CreateFileW.restype=W.HANDLE
k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle.restype=W.BOOL
k.GetFileInformationByHandle.argtypes=[W.HANDLE,C.POINTER(Info)]
k.GetFileInformationByHandle.restype=W.BOOL
k.GetFinalPathNameByHandleW.argtypes=[W.HANDLE,W.LPWSTR,W.DWORD,W.DWORD]
k.GetFinalPathNameByHandleW.restype=W.DWORD
k.GetDriveTypeW.argtypes=[W.LPCWSTR];k.GetDriveTypeW.restype=W.UINT
k.CreateHardLinkW.argtypes=[W.LPCWSTR,W.LPCWSTR,W.LPVOID];k.CreateHardLinkW.restype=W.BOOL
k.DeviceIoControl.argtypes=[W.HANDLE,W.DWORD,W.LPVOID,W.DWORD,W.LPVOID,W.DWORD,C.POINTER(W.DWORD),W.LPVOID]
k.DeviceIoControl.restype=W.BOOL
k.MoveFileW.argtypes=[W.LPCWSTR,W.LPCWSTR];k.MoveFileW.restype=W.BOOL
k.RemoveDirectoryW.argtypes=[W.LPCWSTR];k.RemoveDirectoryW.restype=W.BOOL
s.CommandLineToArgvW.argtypes=[W.LPCWSTR,C.POINTER(C.c_int)]
s.CommandLineToArgvW.restype=C.POINTER(W.LPWSTR)
k.LocalFree.argtypes=[W.HLOCAL];k.LocalFree.restype=W.HLOCAL
INVALID=C.c_void_p(-1).value
READ_ATTRIBUTES=0x80
BACKUP=0x02000000
NOFOLLOW=0x00200000

def open_attributes(path, share_delete=True, desired_access=READ_ATTRIBUTES):
    h=k.CreateFileW(str(path),desired_access,3|(4 if share_delete else 0),None,3,BACKUP|NOFOLLOW,None)
    if h==INVALID: raise C.WinError(C.get_last_error())
    return h

def inspect_handle(h):
    info=Info(); got=k.GetFileInformationByHandle(h,C.byref(info))
    buf=C.create_unicode_buffer(1024)
    n=k.GetFinalPathNameByHandleW(h,buf,1024,0)
    final=buf.value if 0<n<1024 else ''
    if final.startswith('\\\\?\\'): final=final[4:]
    return {'got':bool(got),'n':n,'final':final.replace('\\','/'),
            'attrs':info.attrs,'links':info.links,
            'identity':[info.volume,(info.id_high<<32)|info.id_low]}

def disk_path(path, directory, after_close=None):
    """Same Win32 flags/branch decisions as DiskPath; optional deterministic race hook.

    Hook is test-only and runs after a real handle is closed, no fake OS result.
    Source permits missing final file only, requires all parents pre-created.
    """
    try: p=lex.canonical(str(path))
    except ValueError:return {'ok':False,'reason':'syntax'}
    if k.GetDriveTypeW(p[:3])!=3:return {'ok':False,'reason':'not_fixed_drive'}
    parts=p[3:].split('/');current=p[:3]; trace=[]
    for i in range(-1,len(parts)):
        if i>=0:current=current.rstrip('/')+'/'+parts[i]
        last=i==len(parts)-1
        try:h=open_attributes(current)
        except OSError as e:
            okay=last and not directory and e.winerror==2
            return {'ok':okay,'reason':'missing_leaf' if okay else 'open_failed',
                    'winerror':e.winerror,'trace':trace}
        try:r=inspect_handle(h)
        finally:k.CloseHandle(h)
        trace.append({'path':current,**r})
        if after_close:after_close(current,last)
        if not r['got'] or not 0<r['n']<1024 or r['final'].casefold()!=current.casefold() or r['attrs']&0x400:
            return {'ok':False,'reason':'alias_or_reparse','trace':trace}
        is_dir=bool(r['attrs']&0x10)
        if is_dir!=(not last or directory):return {'ok':False,'reason':'wrong_type','trace':trace}
        if not is_dir and r['links']!=1:return {'ok':False,'reason':'hardlink','trace':trace}
    return {'ok':True,'reason':'observed_path','identity':r['identity'],'trace':trace}

def owned_root(path, expected_identity):
    r=disk_path(path,True)
    return {'ok':r['ok'] and r.get('identity')==expected_identity,'path_result':r,
            'expected_identity':expected_identity}

def windows_argv(line):
    count=C.c_int();ptr=s.CommandLineToArgvW(line,C.byref(count))
    if not ptr:raise C.WinError(C.get_last_error())
    try:return [ptr[i] for i in range(count.value)]
    finally:k.LocalFree(C.cast(ptr,W.HLOCAL))

def exact_argument_admission(line, contract):
    """New test-side strict closure validator; not installed into frozen launcher.

    No user-controlled base options. This tests Windows tokenization, not UE FParse.
    A real launcher must validate its WHOLE approved argument list similarly.
    """
    expected='SettingsPathProbe.exe '+contract['exact_suffix']
    return line==expected and windows_argv(line)==['SettingsPathProbe.exe']+contract['tokens']
