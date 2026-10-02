#pragma once
#include "../native/SessionBridge.h"
#include <utility>

namespace MikdashOnline::RuntimeCandidate01 {
// Production lifecycle shared by the concrete UE port and focused native tests.
// Port operations are synchronous; all calls serialized on the game thread.
template<class Port> class StoppedLease final {
public:
    using Streamer=typename Port::Streamer;
    using Producer=typename Port::Producer;
    enum class State { Empty, Acquiring, Ready, Closing, Closed, Quarantined };
private:
    Port& P;
    Owner Expected;
    double Deadline=0,Last=-1;
    Streamer S;
    Producer V;
    State Phase=State::Empty;
    bool Busy=false,Cancel=false;
    struct Guard { bool& B; explicit Guard(bool& In):B(In){B=true;} ~Guard(){B=false;} };
    static bool Id(const std::string& Value){
        if(Value.empty()||Value.size()>128)return false;
        for(unsigned char C:Value)if(!((C>='a'&&C<='z')||(C>='A'&&C<='Z')||
            (C>='0'&&C<='9')||C=='_'||C=='-'))return false;
        return true;
    }
    bool Fresh(){
        const double N=P.Now();
        if(!std::isfinite(N)||N<0||N<Last||N>1099511627776.0)return false;
        Last=N;return N<Deadline;
    }
    bool Stable(){
        return !Cancel&&P.ScopeValid()&&P.Valid(S)&&P.Find(Expected.stream_id)==S&&
            P.Id(S)==Expected.stream_id&&P.Type(S)=="DefaultRtc"&&
            !P.Streaming(S)&&!P.Connected(S)&&P.UrlEmpty(S)&&Fresh()&&!Cancel;
    }
    bool Fail(){Cancel=true;Phase=State::Closing;return false;}
public:
    explicit StoppedLease(Port& In):P(In){}
    StoppedLease(const StoppedLease&)=delete;
    StoppedLease& operator=(const StoppedLease&)=delete;
    State GetState()const{return Phase;}
    bool Matches(const Owner& Value){return P.Valid(BorrowStopped(Value));}

    bool Prepare(const Owner& Value,double NativeDeadline){
        if(Busy||Phase!=State::Empty)return false;
        Guard Lock(Busy);
        if(!Id(Value.session_id)||!Id(Value.process_key)||!Id(Value.stream_id)||
           !Id(Value.save_prefix)||!Id(Value.settings_slot)||!std::isfinite(Value.expires_at)||
           Value.expires_at<0||Value.expires_at>1099511627776.0||!std::isfinite(NativeDeadline))return false;
        Expected=Value;Deadline=NativeDeadline;Phase=State::Acquiring;
        if(!P.ScopeValid()||!Fresh()||Deadline-Last>86400||
           P.DefaultId()==Expected.stream_id||P.Registered(Expected.stream_id))return Fail();
        // No callback between final presence check and Create in the concrete
        // port. Exclusive game-thread registry mutation is a host prerequisite.
        if(Cancel||!Fresh())return Fail();
        S=P.Create(Expected.stream_id);
        if(!P.Valid(S))return Fail();
        V=P.GetProducer(S); // capture the factory identity before later callbacks
        // Own the returned pointer before any further call. No adoption of an
        // existing ID is allowed; do not use this with concurrent registry writers.
        if(Cancel||P.Find(Expected.stream_id)!=S||P.Id(S)!=Expected.stream_id||
           P.Type(S)!="DefaultRtc"||P.Streaming(S)||P.Connected(S))return Fail();
        P.ClearUrl(S); // discard any URL inherited by the engine from config
        if(!Stable())return Fail();
        // Installed DefaultRtc factory created the real backbuffer producer.
        // Pin that exact producer rather than creating a second capture callback.
        if(!P.Valid(V)||P.GetProducer(S)!=V||!Stable())return Fail();
        Phase=State::Ready;return true;
    }

    Streamer BorrowStopped(const Owner& Value){
        if(Busy||Phase!=State::Ready||!(Expected==Value))return {};
        Guard Lock(Busy);
        if(!Stable()||P.GetProducer(S)!=V||!Fresh()||Cancel){Fail();return {};}
        return S; // trusted receiver bootstrap only; NOT a grant to start media
    }

    bool Close(){
        Cancel=true;
        if(Busy)return false; // synchronous Stop/Delete callbacks cannot recurse
        if(Phase==State::Closed)return true;
        if(Phase==State::Quarantined)return false;
        Guard Lock(Busy);Phase=State::Closing;
        if(!P.Valid(S)){Phase=State::Closed;return true;}
        if(!P.CleanupScopeValid()){Phase=State::Quarantined;return false;}
        // This candidate never starts media. If external code did, public boolean
        // status is not sufficient proof that async signaling teardown completed.
        if(P.Streaming(S)||P.Connected(S)){
            Phase=State::Quarantined;P.Stop(S);return false;
        }
        auto Attached=P.GetProducer(S);
        if(P.Valid(Attached)&&(!P.Valid(V)||Attached!=V)){Phase=State::Quarantined;return false;}
        // Never adopt a newly attached producer during failed-start cleanup.
        P.SetProducer(S,{});
        if(P.Valid(P.GetProducer(S))){Phase=State::Quarantined;return false;}
        P.Remove(S); // concrete port uses DeleteStreamer(pointer), never ID
        if(P.Find(Expected.stream_id)==S){Phase=State::Quarantined;return false;}
        V={};S={};Phase=State::Closed;return true;
    }
};
}
