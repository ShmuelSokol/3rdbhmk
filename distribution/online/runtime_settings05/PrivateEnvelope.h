#pragma once
// No UE dependency. Exact v2 framing/uint decoding shared by UE and native tests.
#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
namespace MikdashOnline::Settings05 {
struct Descriptor {
    std::string root,generation;
    uint64_t file=0,created=0,event=0;
    uint32_t volume=0,pid=0;
    unsigned slots=0;
};
inline bool Hex(const char* p,size_t n,uint64_t& out) {
    if(!p||n==0||n>16)return false;
    uint64_t v=0;
    for(size_t i=0;i<n;++i){char c=p[i];unsigned d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:16;
        if(d==16)return false;v=(v<<4)|d;}
    out=v;return true;
}
inline bool RootSyntax(const std::string& s) {
    if(s.size()<4||s.size()>240||!((s[0]>='A'&&s[0]<='Z')||(s[0]>='a'&&s[0]<='z'))||s[1]!=':'||s[2]!='/')return false;
    size_t start=3;
    for(size_t i=3;i<=s.size();++i){
        if(i==s.size()||s[i]=='/'){
            auto p=s.substr(start,i-start);if(p.empty()||p.size()>100||p=="."||p==".."||p.back()=='.')return false;
            auto base=p.substr(0,p.find('.'));for(auto& c:base)if(c>='a'&&c<='z')c-=32;
            if(base=="CON"||base=="PRN"||base=="AUX"||base=="NUL"||
                (base.size()==4&&(base.substr(0,3)=="COM"||base.substr(0,3)=="LPT")&&base[3]>='0'&&base[3]<='9'))return false;
            start=i+1;
        }else {char c=s[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.'))return false;}
    }return true;
}
inline bool Envelope(const uint8_t* p,size_t n,std::vector<uint8_t>& v1,Descriptor& result) {
    if(!p||n<8||n>4092||std::string(reinterpret_cast<const char*>(p),4)!="MKS2")return false;
    size_t m=(size_t(p[4])<<24)|(size_t(p[5])<<16)|(size_t(p[6])<<8)|p[7];
    if(m<2||m>4092||m+10>n)return false;
    size_t len=(size_t(p[8+m])<<8)|p[9+m];
    if(len<4||len>240||n!=10+m+len+98)return false;
    Descriptor d;d.root.assign(reinterpret_cast<const char*>(p+10+m),len);
    if(!RootSyntax(d.root))return false;
    const char* t=reinterpret_cast<const char*>(p+10+m+len);uint64_t a=0,b=0,c=0,g=0,h=0;
    if(!Hex(t,8,a)||!Hex(t+8,16,d.file)||!Hex(t+24,8,b)||!Hex(t+32,16,d.created)||
       !Hex(t+48,16,d.event)||!Hex(t+64,2,c)||!Hex(t+66,16,g)||!Hex(t+82,16,h))return false;
    if(!b||!d.created||!d.event||c<1||c>64||!(g||h))return false;
    d.volume=uint32_t(a);d.pid=uint32_t(b);d.slots=unsigned(c);d.generation.assign(t+66,32);
    v1.assign(p+8,p+8+m);result=d;return true;
}
}
