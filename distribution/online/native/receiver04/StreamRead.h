#pragma once
#include "CoreMinimal.h"

namespace MikdashOnline::Receiver04 {
enum class StreamRead { Data, Wait, Closed };
// UE5.8 FSocketBSD streaming semantics, NOT raw Winsock recv semantics:
// true + zero bytes = would-block; false = EOF/error. EOF does not refresh the
// subsystem error, so querying GetLastErrorCode here can misclassify a stale value.
template<class Socket> StreamRead ReadStream(Socket& Peer,uint8* Buffer,int32 Want,int32& Read){
    Read=0;
    if(!Peer.Recv(Buffer,Want,Read))return StreamRead::Closed;
    if(Read==0)return StreamRead::Wait;
    return Read>0&&Read<=Want?StreamRead::Data:StreamRead::Closed;
}
}
