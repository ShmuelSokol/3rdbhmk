namespace {
class FActualRtcLease final : public UE::PixelStreaming2::IMikdashRtcLease {
    const TSharedRef<const Adoption01::FParsedAdmission> Admission;
    const TWeakPtr<Authority> Service;
public:
    FActualRtcLease(TSharedRef<const Adoption01::FParsedAdmission> A,TSharedPtr<Authority> S):Admission(A),Service(S){}
    bool Live()const override {
        const auto S=Service.Pin();
        return S.IsValid()&&!S->IsClosed()&&S->BoundOwner()==Admission->Identity()&&Admission->LiveLease();
    }
};
}
bool Bootstrap::AttachOwnedMedia(const Packet& P) {
    if(MediaStarted||!ConsumersBound||Stopping||Busy||!IsOwnedRouteLive()||
       !Admission.IsValid()||!Admission->LiveLease()||P.process_generation!=Admission->Generation()||
       !(P.owner==Admission->Identity())||!Route.Input(Receiver03::QpcSeconds(),P.process_generation,P.connection_id))return false;
    const auto Owned=MediaOwner.Pin();const auto Retained=Service;
    if(!Owned.IsValid()||!Retained.IsValid()||Retained->IsClosed()||P.action.size()!=64||
       P.y<=Receiver03::QpcSeconds()||P.y>Admission->Deadline())return false;
    UE::PixelStreaming2::FMikdashRtcIdentity I;
    I.Session=UTF8_TO_TCHAR(P.owner.session_id.c_str());I.Process=UTF8_TO_TCHAR(P.owner.process_key.c_str());
    I.Stream=UTF8_TO_TCHAR(P.owner.stream_id.c_str());I.Save=UTF8_TO_TCHAR(P.owner.save_prefix.c_str());
    I.Settings=UTF8_TO_TCHAR(P.owner.settings_slot.c_str());I.ProcessGeneration=UTF8_TO_TCHAR(P.process_generation.c_str());
    I.Connection=UTF8_TO_TCHAR(P.connection_id.c_str());I.QpcEnd=Admission->Deadline();I.OwnerEnd=P.owner.expires_at;
    const TSharedRef<const UE::PixelStreaming2::IMikdashRtcLease> Lease=MakeShared<FActualRtcLease>(Admission.ToSharedRef(),Retained);
    MediaStarted=true; // retain any partial acquisition BEFORE plugin callbacks
    const bool Attached=UE::PixelStreaming2::MikdashAttachOwnedRtc(Streamer,I,uint16(P.x),UTF8_TO_TCHAR(P.action.c_str()),P.y,Lease);
    const bool Current=!Stopping&&Admission.IsValid()&&Admission->LiveLease()&&Service==Retained&&!Retained->IsClosed()&&
        Route.Input(Receiver03::QpcSeconds(),P.process_generation,P.connection_id)&&Gate.IsValid()&&Streamer.IsValid()&&
        Streamer->GetInputHandler().Pin()==Gate;
    if(!Attached||!Current){UE::PixelStreaming2::MikdashRevokeOwnedRtc(Streamer);return false;}
    return Owned->StartAuthenticatedMedia(P.owner,int32(P.x))&&!Stopping&&Admission->LiveLease()&&
        Service==Retained&&!Retained->IsClosed()&&Route.Input(Receiver03::QpcSeconds(),P.process_generation,P.connection_id);
}
