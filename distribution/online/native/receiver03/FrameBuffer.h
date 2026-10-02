#pragma once
#include "Wire.h"
namespace MikdashOnline::Receiver03 {
// Used by the actual receiver and by listener-free native automation tests.
class FrameBuffer {
    TArray<uint8> Data;int32 Expected=4;double Deadline=0;bool Bad=false;
public:
    void Begin(double Now){Reset();Deadline=Now+0.5;Bad=!FMath::IsFinite(Now)||Now<0;}
    void Reset(){if(Data.Num())FMemory::Memzero(Data.GetData(),Data.Num());Data.Reset();Expected=4;Deadline=0;Bad=false;}
    bool Expired(double Now) const{return Bad||!FMath::IsFinite(Now)||Now<0||Now>=Deadline;}
    int32 Want(double Now) const{return Expired(Now)?0:FMath::Min(1024,Expected-Data.Num());}
    bool Append(const uint8* Bytes,int32 Count,double Now){
        if(!Bytes||Count<=0||Count>Want(Now)){Bad=true;return false;}
        Data.Append(Bytes,Count);
        if(Data.Num()==4&&Expected==4){
            const uint32 N=(uint32(Data[0])<<24)|(uint32(Data[1])<<16)|(uint32(Data[2])<<8)|Data[3];
            if(N<2||N>MaxBody){Bad=true;return false;}Expected=int32(N)+36;
        }
        return true;
    }
    bool Complete() const{return !Bad&&Expected>4&&Data.Num()==Expected;}
    const TArray<uint8>& Frame() const{return Data;}
};
}
