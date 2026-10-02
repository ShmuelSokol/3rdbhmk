#pragma once
#include "../runtime_readiness01/ReadyOutput.h"
namespace MikdashOnline::Receiver04 { class Bootstrap; }
namespace MikdashOnline::Adoption01 {
// Only the already-validated private MKR1 reader can mint this capability.
// No caller predicate, public constructor, writable config, or key export.
class FParsedAdmission final {
    Receiver03::Bootstrap Snapshot;
    const std::string ProcessGeneration;
    const double StartupUntil;
    const TSharedRef<const Settings01::IOwnedSessionLease> Lease;
    FParsedAdmission(const Receiver03::Bootstrap& B,const std::string& Generation,
        TSharedRef<const Settings01::IOwnedSessionLease> InLease,double StartupDeadline)
        :ProcessGeneration(Generation),StartupUntil(FMath::Min(StartupDeadline,B.Deadline)),Lease(InLease) {
        Snapshot.Identity=B.Identity;Snapshot.Deadline=B.Deadline;Snapshot.Port=B.Port;
        FMemory::Memcpy(Snapshot.Key,B.Key,sizeof(Snapshot.Key));
    }
    friend bool Readiness01::Admit(const TArray<uint8>&,double,Receiver03::Bootstrap&,double);
public:
    FParsedAdmission(const FParsedAdmission&)=delete;
    FParsedAdmission& operator=(const FParsedAdmission&)=delete;
    const Owner& Identity()const{return Snapshot.Identity;}
    const std::string& Generation()const{return ProcessGeneration;}
    double Deadline()const{return Snapshot.Deadline;}
    double StartupDeadline()const{return StartupUntil;}
    bool Live()const {return LiveLease()&&Receiver03::QpcSeconds()<StartupUntil;}
    bool LiveLease()const {
        check(IsInGameThread());
        const auto Current=Settings05::FindLease(Snapshot.Identity);
        const double N=Receiver03::QpcSeconds();
        return Current.IsValid()&&Current.Get()==&Lease.Get()&&Lease->IsLiveForCurrentProcess()&&
            std::isfinite(N)&&N>=0&&N<Snapshot.Deadline&&N<Snapshot.Identity.expires_at;
    }
    // Only exact receiver adoption may construct Authority with the retained key.
private:
    friend class MikdashOnline::Receiver04::Bootstrap;
    const Receiver03::Bootstrap& Config()const{return Snapshot;}
};
}
