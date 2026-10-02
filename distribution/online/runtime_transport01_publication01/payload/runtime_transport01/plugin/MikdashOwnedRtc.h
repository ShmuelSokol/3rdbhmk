#pragma once
#include "CoreMinimal.h"
#include "IPixelStreaming2Streamer.h"

namespace UE::PixelStreaming2 {
class IMikdashRtcLease {
public:
    virtual ~IMikdashRtcLease()=default;
    virtual bool Live()const=0;
};
// Values originate in the already authenticated receiver capability. This is not
// a network decoder or a caller-supplied positive lease predicate.
struct FMikdashRtcIdentity {
    FString Session,Process,Stream,Save,Settings,ProcessGeneration,Connection;
    double QpcEnd=0,OwnerEnd=0;
};
// Available only in the hash-patched project-local RTC module. It adopts a
// factory-proven, stopped, session-less streamer into a NEW private conference.
// URL has no credential; the one-use ticket goes only in an upgrade header.
PIXELSTREAMING2RTC_API bool MikdashAttachOwnedRtc(
    const TSharedPtr<IPixelStreaming2Streamer>& Streamer,const FMikdashRtcIdentity& Identity,
    uint16 Port,FString Ticket,double AttachmentEnd,TSharedRef<const IMikdashRtcLease> Lease);
PIXELSTREAMING2RTC_API void MikdashRevokeOwnedRtc(const TSharedPtr<IPixelStreaming2Streamer>& Streamer);
}
