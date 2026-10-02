#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "../SessionBridge.h"

namespace MikdashOnline::Receiver03 {
constexpr int32 MaxBody=4096;
struct Bootstrap {
    Owner Identity;
    double Deadline=0;
    int32 Port=0;
    uint8 Key[32]={};
    Bootstrap()=default;
    Bootstrap(const Bootstrap&)=delete;
    Bootstrap& operator=(const Bootstrap&)=delete;
    ~Bootstrap(){FMemory::Memzero(Key,sizeof(Key));}
};
// All parsers bounded before conversion. No arbitrary JSON/crypto error text logged.
bool ParseBootstrap(const TArray<uint8>& Body,Bootstrap& Out);
bool DecodeRequest(const TArray<uint8>& Frame,const uint8 (&Key)[32],Packet& Out);
bool EncodeAck(const Ack& Value,const uint8 (&Key)[32],TArray<uint8>& Out);
bool Hmac(const uint8 (&Key)[32],const ANSICHAR* Domain,int32 DomainBytes,
          const uint8* Body,int32 BodyBytes,uint8 (&Out)[32]);
double QpcSeconds();
}
