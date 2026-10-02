// Harmless non-UE executable. No socket, registry, UE or config API.
#include "WinLease.h"
#include <cstdio>
#include <fstream>
#include <iterator>
using namespace MikdashOnline::Settings05;
#define REQUIRE(x) do{if(!(x))return __LINE__;}while(0)
int main(int argc,char** argv){
    uint64_t x=0;
    REQUIRE(Hex("0020000000000001",16,x)&&x==9007199254740993ULL);
    REQUIRE(Hex("ffffffffffffffff",16,x)&&x==UINT64_MAX);
    REQUIRE(!Hex("10000000000000000",17,x));
    REQUIRE(!Hex("FFFFFFFFFFFFFFFF",16,x));
    REQUIRE(!Hex("+000000000000001",16,x));
    REQUIRE(!RootSyntax("C:/a/../b"));REQUIRE(!RootSyntax("C:/NUL"));
    if(argc==2){
        std::ifstream in(argv[1],std::ios::binary);std::vector<uint8_t> b((std::istreambuf_iterator<char>(in)),{});
        Descriptor d;std::vector<uint8_t> v;
        REQUIRE(Envelope(b.data(),b.size(),v,d));
        REQUIRE(d.file==UINT64_MAX&&d.created==9007199254740993ULL);
        REQUIRE(std::string(v.begin(),v.end())=="{}");
        auto bad=b;bad.push_back(0);REQUIRE(!Envelope(bad.data(),bad.size(),v,d));
        bad=b;bad[3]='3';REQUIRE(!Envelope(bad.data(),bad.size(),v,d));
        bad=b;bad.back()='G';REQUIRE(!Envelope(bad.data(),bad.size(),v,d));
        for(size_t n=0;n<b.size();++n)REQUIRE(!Envelope(b.data(),n,v,d));
        std::puts("codec_pass");return 0;
    }
    // Actual owned stdin, one frame then EOF. Parent owns a <=2s startup bound
    // and a 30s exact-job watchdog; this fixture does not emulate the UE reader.
    HANDLE input=GetStdHandle(STD_INPUT_HANDLE);uint8_t bytes[4097]{};DWORD n=0,total=0;
    while(total<sizeof(bytes)&&ReadFile(input,bytes+total,sizeof(bytes)-total,&n,nullptr)&&n)total+=n;
    REQUIRE(total>4&&total<=4096);
    size_t length=(size_t(bytes[0])<<24)|(size_t(bytes[1])<<16)|(size_t(bytes[2])<<8)|bytes[3];
    REQUIRE(length==total-4);
    Descriptor d;std::vector<uint8_t> v;REQUIRE(Envelope(bytes+4,length,v,d));
    WinLease lease;REQUIRE(lease.Bind(d,Qpc()+10));REQUIRE(lease.Live());
    REQUIRE(!lease.Bind(d,Qpc()+10)); // no generation rebinding/renewal
    WinLease expired;REQUIRE(!expired.Bind(d,Qpc()-1));
    WinLease wrongPid;auto bad=d;bad.pid^=1;REQUIRE(!wrongPid.Bind(bad,Qpc()+1));
    WinLease wrongTime;bad=d;bad.created^=1;REQUIRE(!wrongTime.Bind(bad,Qpc()+1));
    // Independent handle to the same real event, not a fabricated kernel result.
    HANDLE duplicate=nullptr;
    REQUIRE(DuplicateHandle(GetCurrentProcess(),reinterpret_cast<HANDLE>(uintptr_t(d.event)),
        GetCurrentProcess(),&duplicate,0,FALSE,DUPLICATE_SAME_ACCESS));
    auto shortData=d;shortData.event=uint64_t(reinterpret_cast<uintptr_t>(duplicate));
    WinLease shortLease;REQUIRE(shortLease.Bind(shortData,Qpc()+0.02));
    Sleep(30);REQUIRE(!shortLease.Live());REQUIRE(!shortLease.Bind(shortData,Qpc()+10));REQUIRE(shortLease.Close());
    const auto path=d.root+"/User/native-ready";
    {std::ofstream ready(path);ready<<"native_winlease_bound";REQUIRE(ready.good());}
    // Native validation sees the real parent event without sockets or a second pipe.
    const double end=Qpc()+5;
    while(lease.Live()&&Qpc()<end)Sleep(2);
    REQUIRE(Qpc()<end);REQUIRE(!lease.Live());REQUIRE(lease.Close());
    return 0;
}
