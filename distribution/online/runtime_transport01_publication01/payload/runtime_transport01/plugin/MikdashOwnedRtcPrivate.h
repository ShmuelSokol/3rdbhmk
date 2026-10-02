#pragma once
#include "MikdashOwnedRtc.h"
#include "epic_rtc/core/platform.h"
#include "epic_rtc/plugins/signalling/websocket_factory.h"
#include "epic_rtc/plugins/signalling/websocket.h"
#include "epic_rtc_helper/memory/ref_count_impl_helper.h"
class IWebSocket;
namespace UE::PixelStreaming2 {
class FEpicRtcStreamer;
class FMikdashOwnedConference;
class FMikdashOwnedSocket final : public EpicRtcWebsocketInterface {
    TWeakPtr<FMikdashOwnedConference> Scope;
    TSharedPtr<IWebSocket> Socket;
    TRefCountPtr<EpicRtcWebsocketObserverInterface> Observer;
    FDelegateHandle OpenHandle,ErrorHandle,CloseHandle,MessageHandle,BinaryHandle;
    bool Used=false,Closed=false;
    void CloseOwned();
public:
    explicit FMikdashOwnedSocket(TWeakPtr<FMikdashOwnedConference> In):Scope(In){}
    virtual ~FMikdashOwnedSocket() override;
    virtual EpicRtcBool Connect(EpicRtcStringView Url,EpicRtcWebsocketObserverInterface* InObserver) override;
    virtual void Disconnect(EpicRtcStringView Reason) override;
    virtual void Send(EpicRtcStringView Message) override;
    void Revoke(){CloseOwned();}
    EPICRTC_REFCOUNT_INTERFACE_IN_PLACE
};
class FMikdashOwnedFactory final : public EpicRtcWebsocketFactoryInterface {
    TWeakPtr<FMikdashOwnedConference> Scope;
    TRefCountPtr<FMikdashOwnedSocket> Socket;
    bool Issued=false;
public:
    explicit FMikdashOwnedFactory(TWeakPtr<FMikdashOwnedConference> In):Scope(In){}
    virtual EpicRtcErrorCode CreateWebsocket(EpicRtcWebsocketInterface** Out) override;
    void Revoke(){if(Socket)Socket->Revoke();}
    EPICRTC_REFCOUNT_INTERFACE_IN_PLACE
};
class FMikdashOwnedConference final : public TSharedFromThis<FMikdashOwnedConference> {
    friend class FMikdashOwnedSocket;
    const FMikdashRtcIdentity Identity;
    const FString Url;
    FString Ticket;
    const double AttachEnd;
    const TSharedRef<const IMikdashRtcLease> Lease;
    double Last=-1;
    bool Taken=false,Closing=false,Ticking=false,Connected=false,Installed=false;
    TWeakPtr<FEpicRtcStreamer> Streamer;
    TRefCountPtr<EpicRtcPlatformInterface> Platform;
    TRefCountPtr<EpicRtcConferenceInterface> Conference;
    TRefCountPtr<FMikdashOwnedFactory> Factory;
    FString Name;
    FDelegateHandle Frame,Exit;
    bool Take(const FString& InUrl,TMap<FString,FString>& Headers);
    void Tick();
public:
    FMikdashOwnedConference(const FMikdashRtcIdentity& In,const FString& InUrl,FString InTicket,double Until,
        const TSharedPtr<FEpicRtcStreamer>& S,TSharedRef<const IMikdashRtcLease> InLease)
        :Identity(In),Url(InUrl),Ticket(MoveTemp(InTicket)),AttachEnd(Until),Lease(InLease),Streamer(S){}
    ~FMikdashOwnedConference();
    bool Initialize();
    bool Live();
    void Seal(){Installed=true;}
    void Revoke();
    const TRefCountPtr<EpicRtcConferenceInterface>& GetConference()const{return Conference;}
};
}
