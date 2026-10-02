#include "Wire.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Windows/WindowsHWrapper.h"
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")

namespace MikdashOnline::Receiver03 {
double QpcSeconds(){
    LARGE_INTEGER T,F;
    if(!::QueryPerformanceCounter(&T)||!::QueryPerformanceFrequency(&F)||F.QuadPart<=0)return -1;
    return double(T.QuadPart)/double(F.QuadPart);
}
bool Hmac(const uint8 (&Key)[32],const ANSICHAR* Domain,int32 DomainBytes,
          const uint8* Body,int32 BodyBytes,uint8 (&Out)[32]){
    if(BodyBytes<1||BodyBytes>MaxBody||DomainBytes<1||DomainBytes>64)return false;
    BCRYPT_ALG_HANDLE Algorithm=nullptr;BCRYPT_HASH_HANDLE Hash=nullptr;
    uint8 Object[1024]={};ULONG Needed=0,Result=0;
    bool Ok=::BCryptOpenAlgorithmProvider(&Algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,BCRYPT_ALG_HANDLE_HMAC_FLAG)>=0;
    if(Ok)Ok=::BCryptGetProperty(Algorithm,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&Needed),sizeof(Needed),&Result,0)>=0 && Needed<=sizeof(Object);
    if(Ok)Ok=::BCryptCreateHash(Algorithm,&Hash,Object,Needed,const_cast<PUCHAR>(Key),sizeof(Key),0)>=0;
    if(Ok)Ok=::BCryptHashData(Hash,reinterpret_cast<PUCHAR>(const_cast<ANSICHAR*>(Domain)),DomainBytes,0)>=0;
    if(Ok)Ok=::BCryptHashData(Hash,const_cast<PUCHAR>(Body),BodyBytes,0)>=0;
    if(Ok)Ok=::BCryptFinishHash(Hash,Out,sizeof(Out),0)>=0;
    if(Hash)::BCryptDestroyHash(Hash);
    if(Algorithm)::BCryptCloseAlgorithmProvider(Algorithm,0);
    ::SecureZeroMemory(Object,sizeof(Object));
    return Ok;
}
static bool Json(const uint8* Data,int32 Count,TSharedPtr<FJsonObject>& Out){
    if(Count<2||Count>MaxBody)return false;
    FString Text;Text.Reserve(Count);
    for(int32 I=0;I<Count;++I){if(Data[I]<32||Data[I]>126)return false;Text.AppendChar(TCHAR(Data[I]));}
    // The UE object deserializer otherwise overwrites duplicate keys. Token scan
    // rejects duplicates, arrays, excessive depth, extra roots and nonfinite numbers.
    auto Reader=TJsonReaderFactory<>::Create(Text);
    TArray<TSet<FString>> Fields;EJsonNotation Token;int32 Roots=0,Tokens=0;
    while(Reader->ReadNext(Token)){
        if(++Tokens>128||Token==EJsonNotation::Error||Token==EJsonNotation::ArrayStart||Token==EJsonNotation::ArrayEnd)return false;
        if(Token!=EJsonNotation::ObjectEnd){
            if(Fields.Num()){
                const FString Name=Reader->GetIdentifier();
                if(Name.IsEmpty()||Name.Len()>32||Fields.Last().Contains(Name))return false;
                Fields.Last().Add(Name);
            }else if(Token!=EJsonNotation::ObjectStart)return false;
        }
        if(Token==EJsonNotation::ObjectStart){
            if(Fields.Num()==0&&++Roots!=1)return false;
            if(Fields.Num()>=3)return false;
            Fields.AddDefaulted();
        }else if(Token==EJsonNotation::ObjectEnd){if(Fields.Num()==0)return false;Fields.Pop();}
        else if(Token==EJsonNotation::Number&&!FMath::IsFinite(Reader->GetValueAsNumber()))return false;
        else if(Token==EJsonNotation::String&&Reader->GetValueAsString().Len()>128)return false;
    }
    if(Roots!=1||Fields.Num()!=0||!Reader->GetErrorMessage().IsEmpty())return false;
    return FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Out)&&Out.IsValid();
}
static bool Shape(const FJsonObject& O,std::initializer_list<const TCHAR*> Names){
    if(O.Values.Num()!=int32(Names.size()))return false;
    for(const TCHAR* N:Names)if(!O.HasField(N))return false;
    return true;
}
static bool Text(const FJsonObject& O,const TCHAR* Name,std::string& Out,bool Empty=false){
    FString V;if(!O.HasTypedField<EJson::String>(Name)||!O.TryGetStringField(Name,V)||V.Len()>128||(!Empty&&V.IsEmpty()))return false;
    Out.clear();
    for(TCHAR C:V){if(!((C>='a'&&C<='z')||(C>='A'&&C<='Z')||(C>='0'&&C<='9')||C=='_'||C=='-'))return false;Out.push_back(char(C));}
    return true;
}
static bool Number(const FJsonObject& O,const TCHAR* N,double& V,double Min,double Max){
    return O.HasTypedField<EJson::Number>(N)&&O.TryGetNumberField(N,V)&&FMath::IsFinite(V)&&V>=Min&&V<=Max;
}
static bool ReadOwner(const FJsonObject& O,Owner& V){
    return Shape(O,{TEXT("session_id"),TEXT("process_key"),TEXT("stream_id"),TEXT("save_prefix"),TEXT("settings_slot"),TEXT("expires_at")})&&
        Text(O,TEXT("session_id"),V.session_id)&&Text(O,TEXT("process_key"),V.process_key)&&
        Text(O,TEXT("stream_id"),V.stream_id)&&Text(O,TEXT("save_prefix"),V.save_prefix)&&
        Text(O,TEXT("settings_slot"),V.settings_slot)&&Number(O,TEXT("expires_at"),V.expires_at,0,1099511627776.0);
}
bool ParseBootstrap(const TArray<uint8>& Body,Bootstrap& Out){
    TSharedPtr<FJsonObject> O;const TSharedPtr<FJsonObject>* OwnerObject=nullptr;double Version=0,Port=0;
    if(!Json(Body.GetData(),Body.Num(),O)||!Shape(*O,{TEXT("version"),TEXT("clock_domain"),TEXT("owner"),TEXT("qpc_deadline"),TEXT("port"),TEXT("key_hex")})||
        !Number(*O,TEXT("version"),Version,1,1)||!Number(*O,TEXT("port"),Port,1024,65535)||Port!=FMath::FloorToDouble(Port)||
        !Number(*O,TEXT("qpc_deadline"),Out.Deadline,0,1099511627776.0)||
        !O->TryGetObjectField(TEXT("owner"),OwnerObject)||!ReadOwner(**OwnerObject,Out.Identity))return false;
    FString Domain;if(!O->TryGetStringField(TEXT("clock_domain"),Domain)||Domain!=TEXT("windows-qpc-v1"))return false;
    FString Hex;if(!O->TryGetStringField(TEXT("key_hex"),Hex)||Hex.Len()!=64)return false;
    for(int32 I=0;I<32;++I){
        auto Digit=[](TCHAR C)->int32{return C>='0'&&C<='9'?C-'0':C>='a'&&C<='f'?C-'a'+10:-1;};
        int32 A=Digit(Hex[I*2]),B=Digit(Hex[I*2+1]);if(A<0||B<0)return false;Out.Key[I]=uint8(A*16+B);
    }
    Out.Port=int32(Port);return true;
}
bool DecodeRequest(const TArray<uint8>& Frame,const uint8 (&Key)[32],Packet& Out){
    if(Frame.Num()<38||Frame.Num()>MaxBody+36)return false;
    const uint32 N=(uint32(Frame[0])<<24)|(uint32(Frame[1])<<16)|(uint32(Frame[2])<<8)|Frame[3];
    if(N<2||N>MaxBody||Frame.Num()!=int32(N)+36)return false;
    uint8 Mac[32];static const ANSICHAR Domain[]="mikdash-request-v1";
    if(!Hmac(Key,Domain,sizeof(Domain),Frame.GetData()+4,N,Mac))return false;
    uint8 Difference=0;for(int32 I=0;I<32;++I)Difference|=Mac[I]^Frame[4+N+I];
    FMemory::Memzero(Mac,sizeof(Mac));if(Difference)return false;
    TSharedPtr<FJsonObject> O;const TSharedPtr<FJsonObject>* OwnerObject=nullptr;
    if(!Json(Frame.GetData()+4,N,O)||!Shape(*O,{TEXT("version"),TEXT("owner"),TEXT("sequence"),TEXT("operation"),TEXT("connection_id"),TEXT("event")}))return false;
    double V=0,S=0;
    if(!Number(*O,TEXT("version"),V,1,1)||!Number(*O,TEXT("sequence"),S,1,9007199254740991.0)||S!=FMath::FloorToDouble(S)||
       !O->TryGetObjectField(TEXT("owner"),OwnerObject)||!ReadOwner(**OwnerObject,Out.owner)||
       !Text(*O,TEXT("operation"),Out.operation)||!Text(*O,TEXT("connection_id"),Out.connection_id,true))return false;
    Out.version=1;Out.sequence=uint64_t(S);Out.action.clear();Out.x=Out.y=0;
    if(Out.operation=="input"){
        const TSharedPtr<FJsonObject>* E=nullptr;
        if(!O->TryGetObjectField(TEXT("event"),E)||!Shape(**E,{TEXT("action"),TEXT("x"),TEXT("y")})||
            !Text(**E,TEXT("action"),Out.action)||!Number(**E,TEXT("x"),Out.x,-1,1)||!Number(**E,TEXT("y"),Out.y,-1,1))return false;
        const bool Axis=Out.action=="move"||Out.action=="look";
        if(!Axis&&(!(Out.action=="interact"||Out.action=="pause"||Out.action=="mute")||Out.x!=0||Out.y!=0))return false;
        return !Out.connection_id.empty();
    }
    if(O->Values[TEXT("event")]->Type!=EJson::Null)return false;
    if(Out.operation=="open")return Out.connection_id.empty();
    if(Out.operation=="bind")return !Out.connection_id.empty();
    return Out.operation=="release"||Out.operation=="close";
}
bool EncodeAck(const Ack& A,const uint8 (&Key)[32],TArray<uint8>& Out){
    // All text comes from the strictly parsed request, not native error messages.
    const Owner& O=A.owner;
    const FString Body=FString::Printf(TEXT("{\"version\":1,\"owner\":{\"session_id\":\"%s\",\"process_key\":\"%s\",\"stream_id\":\"%s\",\"save_prefix\":\"%s\",\"settings_slot\":\"%s\",\"expires_at\":%.17g},\"sequence\":%llu,\"operation\":\"%s\",\"connection_id\":\"%s\",\"status\":\"%s\"}"),
        UTF8_TO_TCHAR(O.session_id.c_str()),UTF8_TO_TCHAR(O.process_key.c_str()),UTF8_TO_TCHAR(O.stream_id.c_str()),
        UTF8_TO_TCHAR(O.save_prefix.c_str()),UTF8_TO_TCHAR(O.settings_slot.c_str()),O.expires_at,
        static_cast<unsigned long long>(A.sequence),UTF8_TO_TCHAR(A.operation.c_str()),UTF8_TO_TCHAR(A.connection_id.c_str()),UTF8_TO_TCHAR(A.status.c_str()));
    FTCHARToUTF8 Bytes(*Body);int32 N=Bytes.Length();if(N<2||N>MaxBody)return false;
    uint8 Mac[32];static const ANSICHAR Domain[]="mikdash-response-v1";
    if(!Hmac(Key,Domain,sizeof(Domain),reinterpret_cast<const uint8*>(Bytes.Get()),N,Mac))return false;
    Out.Reset();Out.Add(uint8(N>>24));Out.Add(uint8(N>>16));Out.Add(uint8(N>>8));Out.Add(uint8(N));
    Out.Append(reinterpret_cast<const uint8*>(Bytes.Get()),N);Out.Append(Mac,32);return true;
}
}
