"""Hash-guarded project-local plugin insertions; never write installed UE.

Only author-owned recipe/additions/pins may be published. Result contains private
engine implementation and belongs solely in an isolated licensed build checkout.
"""
from pathlib import Path
import argparse,hashlib,json,re
ROOT=Path(__file__).resolve().parent
PREFIX='Source/PixelStreaming2RTC/'
FILES=['Private/EpicRtcStreamer.h','Private/EpicRtcStreamer.cpp',
       'Private/PixelStreaming2RTCModule.h','Private/PixelStreaming2RTCModule.cpp',
       'Internal/EpicRtcConferenceUtils.h','Internal/EpicRtcWebsocket.h',
       'PixelStreaming2RTC.Build.cs']
def sha(b):return hashlib.sha256(b).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise ValueError('Plugin source anchor mismatch')
    return s.replace(a,b,1)
def build(plugin):
    pins=json.loads((ROOT/'plugin-pins.json').read_text());out={}
    for n,h in pins.items():
        b=(plugin/n).read_bytes()
        if sha(b)!=h:raise ValueError('Installed plugin version mismatch')
        out[n]=b
    def edit(n,f):out[PREFIX+n]=f(out[PREFIX+n].decode('utf-8-sig').replace('\r\n','\n')).encode()
    def sh(s):
        s=once(s,'#include "EpicRtcAudioCapturer.h"','#include "EpicRtcAudioCapturer.h"\n#include "MikdashOwnedRtcPrivate.h"')
        s=once(s,'\t\tFEpicRtcStreamer(const FString& StreamerId, TRefCountPtr<EpicRtcConferenceInterface> Conference);', '''        bool MikdashCanAdopt() { return !OwnedConference.IsValid()&&!EpicRtcSession.IsValid()&&!IsStreaming()&&!IsConnected(); }
        bool MikdashAdopt(TSharedRef<FMikdashOwnedConference> Scope) {
            if(!MikdashCanAdopt()||!Scope->GetConference())return false;
            OwnedConference=Scope;EpicRtcConference=Scope->GetConference();return true;
        }
        bool MikdashMatchesScope(const FMikdashOwnedConference* Scope)const {
            return Scope&&OwnedConference.IsValid()&&OwnedConference.Get()==Scope&&EpicRtcConference==OwnedConference->GetConference();
        }
        bool MikdashIsOwned()const{return OwnedConference.IsValid();}
        void MikdashRevoke(){if(OwnedConference.IsValid())OwnedConference->Revoke();}
        FEpicRtcStreamer(const FString& StreamerId, TRefCountPtr<EpicRtcConferenceInterface> Conference);''')
        s=once(s,'\t\t// Begin EpicRtc Classes','        TSharedPtr<FMikdashOwnedConference> OwnedConference;\n\t\t// Begin EpicRtc Classes')
        a='\t\tFRTCStreamerFactory(TRefCountPtr<EpicRtcConferenceInterface> Conference);'
        s=once(s,a,'''        TSharedPtr<FEpicRtcStreamer> FindCreated(const TSharedPtr<IPixelStreaming2Streamer>& S) {
            if(OwnedClosing||!S.IsValid())return {};
            for(const auto& Weak:Created) {
                const auto Exact=Weak.Pin();
                if(Exact.IsValid()&&Exact.Get()==S.Get())return Exact;
            }
            return {};
        }
        void RevokeOwned(){
            if(OwnedClosing)return;
            OwnedClosing=true; // block owned adoption before callback-capable teardown
            // Snapshot owned objects before callback-capable StopStreaming.
            TArray<TSharedPtr<FEpicRtcStreamer>> Owned;
            for(const auto& Weak:Created)
                if(const auto S=Weak.Pin();S.IsValid()&&S->MikdashIsOwned())Owned.Add(S);
            for(const auto& S:Owned)S->MikdashRevoke();
        }
'''+a)
        a='\t\tTRefCountPtr<EpicRtcConferenceInterface> EpicRtcConference;\n\t};\n} // namespace UE::PixelStreaming2'
        s=once(s,a,'        bool OwnedClosing=false;\n        TArray<TWeakPtr<FEpicRtcStreamer>> Created; // passive exact-instance origin proof, never admission policy\n'+a)
        return s
    edit('Private/EpicRtcStreamer.h',sh)
    def sc(s):
        s=once(s,'\t\tTickableTasks = FPixelStreaming2RTCModule::GetModule()->GetSharedTickableTasks();', '''        if(OwnedConference.IsValid()) {
            if(!OwnedConference->Live()){StreamState=EStreamState::Disconnected;return;}
            TickableTasks.Reset(); // private conference owns its bounded game-thread service
        } else TickableTasks = FPixelStreaming2RTCModule::GetModule()->GetSharedTickableTasks();''')
        s=once(s,'\t\tOnPreConnection().Broadcast(this);','\t\tOnPreConnection().Broadcast(this);\n        if(OwnedConference.IsValid()&&!OwnedConference->Live()){StopStreaming();return;}')
        s=once(s,'\t\tTSharedPtr<IPixelStreaming2Streamer> NewStreamer = MakeShared<FEpicRtcStreamer>(StreamerId, EpicRtcConference);', '''        Created.RemoveAll([](const TWeakPtr<FEpicRtcStreamer>& Weak){return !Weak.IsValid();});
        TSharedPtr<FEpicRtcStreamer> NewStreamer = MakeShared<FEpicRtcStreamer>(StreamerId, EpicRtcConference);
        Created.Add(NewStreamer);''')
        return s
    edit('Private/EpicRtcStreamer.cpp',sc)
    def mh(s):
        a='\t\tTRefCountPtr<EpicRtcConferenceInterface>& GetEpicRtcConference() { return EpicRtcConference; }'
        return once(s,a,a+'''
        TRefCountPtr<EpicRtcPlatformInterface> MikdashPlatform(){return EpicRtcPlatform;}
        TSharedPtr<FEpicRtcStreamer> MikdashFindCreated(const TSharedPtr<IPixelStreaming2Streamer>& S) {
            return StreamerFactory?StreamerFactory->FindCreated(S):TSharedPtr<FEpicRtcStreamer>();
        }
        bool MikdashCreateConference(const FString& Name,EpicRtcWebsocketFactoryInterface* Factory,
            TRefCountPtr<EpicRtcConferenceInterface>& Out);''')
    edit('Private/PixelStreaming2RTCModule.h',mh)
    def mc(s):
        start=s.index('\t\tEpicRtcConfig ConferenceConfig = {')
        end=s.index('\n\t\t// clang-format on',start)
        config=s[start:end]
        config=once(config,'WebsocketFactory.GetReference()','Factory')
        config,count=re.subn(r'\._logging = \{.*?\n\t\t\t\},\n\t\t\t\._stats', '._logging = {},\n\t\t\t._stats',config,flags=re.S)
        if count!=1:raise ValueError('Logging source anchor mismatch')
        method='''
    bool FPixelStreaming2RTCModule::MikdashCreateConference(const FString& Name,
        EpicRtcWebsocketFactoryInterface* Factory,TRefCountPtr<EpicRtcConferenceInterface>& Out) {
        if(!IsInGameThread()||!bModuleReady||!EpicRtcPlatform||!Factory||Out)return false;
        FUtf8String EpicRtcFieldTrials(GetFieldTrials());
'''+config+'''
        const FUtf8String Id(Name);
        TRefCountPtr<EpicRtcConferenceInterface> Existing;
        if(EpicRtcPlatform->GetConference(ToEpicRtcStringView(Id),Existing.GetInitReference())==EpicRtcErrorCode::Ok||Existing)return false;
        const auto Result=EpicRtcPlatform->CreateConference(ToEpicRtcStringView(Id),ConferenceConfig,Out.GetInitReference());
        if(Result!=EpicRtcErrorCode::Ok){Out=nullptr;return false;} // never release a foreign named conference
        return Out.IsValid();
    }
'''
        s=once(s,'\t\tTickableTasks.Reset();\n\t\tStreamerFactory.Reset();',
            '\t\tif(StreamerFactory)StreamerFactory->RevokeOwned();\n\t\tTickableTasks.Reset();\n\t\tStreamerFactory.Reset();')
        return once(s,'\nIMPLEMENT_MODULE(',method+'\nIMPLEMENT_MODULE(').replace(
            '\n    bool FPixelStreaming2RTCModule::MikdashCreateConference','\nnamespace UE::PixelStreaming2 {\n    bool FPixelStreaming2RTCModule::MikdashCreateConference',1).replace(
            '\nIMPLEMENT_MODULE(','\n}\nIMPLEMENT_MODULE(',1)
    edit('Private/PixelStreaming2RTCModule.cpp',mc)
    out[PREFIX+'Public/MikdashOwnedRtc.h']=(ROOT/'plugin/MikdashOwnedRtc.h').read_bytes()
    for n in ['MikdashOwnedRtcPrivate.h','MikdashOwnedRtc.cpp']:out[PREFIX+'Private/'+n]=(ROOT/'plugin'/n).read_bytes()
    return out
def stage(plugin,dest):
    plugin=plugin.resolve();dest=dest.resolve()
    if dest.exists() or plugin==dest or plugin in dest.parents:raise ValueError('Fresh separate output required')
    for q in (plugin,*plugin.parents,dest,*dest.parents):
        if q.exists() and (q.is_symlink() or getattr(q.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse refused')
    out=build(plugin);dest.mkdir(parents=True)
    for n,b in out.items():
        p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    # This is a private patch overlay, not a full plugin or a publication payload.
    return dict(files=len(out),engineImplementationPrivate=True,ueCompiled=False)

def local_clone(plugin):
    """Private source-only plugin closure; never a publication payload.

    The installed EpicRtc binary remains installed and hash-pinned, not copied.
    Source recipes are only valid for this exact licensed engine installation.
    """
    pins=json.loads((ROOT/'plugin-source-pins.json').read_text());out={}
    for n,h in pins.items():
        p=plugin/n
        for q in (p,*p.parents):
            if q.is_symlink() or getattr(q.lstat(),'st_file_attributes',0)&0x400:raise ValueError('Reparse refused')
        b=p.read_bytes()
        if sha(b)!=h:raise ValueError('Local plugin dependency changed')
        if not n.endswith('.lib'):out[n]=b
    out.update(build(plugin))
    name='Source/ThirdParty/EpicRtc/EpicRtc.Build.cs'
    s=out[name].decode('utf-8-sig').replace('\r\n','\n')
    s=once(s,'Path.Combine(ModuleDirectory, "Lib", PlatformName, PlatformArchitecture, ConfigPath, LibraryName)',
        'Path.Combine(EngineDirectory, "Plugins", "Media", "PixelStreaming2", "Source", "ThirdParty", "EpicRtc", "Lib", PlatformName, PlatformArchitecture, ConfigPath, LibraryName)')
    out[name]=s.encode()
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plugin',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(stage(a.plugin,a.output)))
