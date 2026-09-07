#include "IncenseServiceSchedule.h"
#include <cstdlib>
#include <iostream>
#include <limits>
using namespace MikdashIncense;
void Check(bool Good, const char* Why) { if (!Good) { std::cerr << Why << '\n'; std::exit(1); } }
Preconditions Daily()
{
    Preconditions P;
    P.ScenarioReviewed = P.LocationReviewed = P.OfficiantPreparedAndAssigned = true;
    P.GarmentsReviewedForService = P.WithdrawalComplete = true;
    P.At = Location::GoldenAltarInHeikhal;
    P.Actor = Officiant::AssignedKohen;
    P.WithdrawalPolicy = Withdrawal::DailyHeikhalAndUlamAltarArea;
    return P;
}
int main()
{
    Preconditions P = Daily();
    Schedule S(Scenario::OrdinaryDay, 17, {10, 5});
    Check(S.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::Denied, "missing predecessor");
    Check(S.Advance(RitualPhase::MorningBloodCompleted, P, true).Value == Outcome::Paused, "paused ritual event");
    Check(!S.Save().MorningBloodCompleted, "pause cannot advance predecessor");
    Check(S.Advance(RitualPhase::MorningBloodCompleted, P).Value == Outcome::Recorded, "record predecessor");
    P.LocationReviewed = false;
    Check(S.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::NeedsReview, "unreviewed location");
    P = Daily(); P.WithdrawalComplete = false;
    Check(S.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::Denied, "withdrawal is required");
    P = Daily(); P.GarmentsReviewedForService = false;
    Check(S.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::Denied, "garment prerequisite");
    P = Daily();
    Check(S.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::Started, "morning starts once");
    Check(S.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::AlreadyStarted, "repeat tick no reemission");
    Check(!S.TickSmoke(4, true) && S.State(Service::Morning)->EmissionRemaining == 10, "pause freezes visual");
    Check(S.TickSmoke(12) && S.State(Service::Morning)->Visual == SmokePhase::Residual
        && S.State(Service::Morning)->ResidualRemaining == 3, "large tick crosses emission boundary");
    Check(!S.State(Service::Morning)->OfficiantExited, "visual phase cannot invent officiant exit");
    Schedule Reloaded;
    Check(Reloaded.Restore(S.Save()), "valid snapshot restores");
    Check(Reloaded.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::AlreadyStarted, "reload no duplicate");
    Check(Reloaded.MarkOfficiantExited(Service::Morning), "explicit exit");
    Check(Reloaded.State(Service::Morning)->ResidualRemaining == 3, "exit does not erase residual");
    Check(Reloaded.TickSmoke(100) && Reloaded.State(Service::Morning)->Visual == SmokePhase::Finished, "tail terminates");
    Check(Reloaded.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::AlreadyStarted, "finished is not restartable");
    Check(Reloaded.Advance(RitualPhase::AfternoonLimbsCompleted, P).Value == Outcome::Recorded, "PM predecessor");
    Check(Reloaded.Advance(RitualPhase::AfternoonIncenseCue, P).Value == Outcome::Started, "PM separate from AM");
    Check(Reloaded.Advance(RitualPhase::YomKippurInnerCue, P).Value == Outcome::Denied, "ordinary day no inner event");

    Schedule YK(Scenario::YomKippur, 18, {1, 2});
    YK.Advance(RitualPhase::MorningBloodCompleted, P);
    Check(YK.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::Denied, "YK daily officiant is high priest");
    P.Actor = Officiant::KohenGadol;
    Check(YK.Advance(RitualPhase::MorningIncenseCue, P).Value == Outcome::Started, "YK retains daily morning event");
    YK.Advance(RitualPhase::YomKippurBullSlaughterCompleted, P);
    Check(YK.Advance(RitualPhase::YomKippurInnerCue, P).Value == Outcome::Denied, "inner service cannot use golden altar");
    P.At = Location::ReviewedInnerSanctuaryAnchor;
    Check(YK.Advance(RitualPhase::YomKippurInnerCue, P).Value == Outcome::Denied, "inner withdrawal policy differs");
    P.WithdrawalPolicy = Withdrawal::YomKippurInnerService;
    Check(YK.Advance(RitualPhase::YomKippurInnerCue, P).Value == Outcome::Started, "separate YK inner event");
    P = Daily(); P.Actor = Officiant::KohenGadol;
    YK.Advance(RitualPhase::AfternoonLimbsCompleted, P);
    Check(YK.Advance(RitualPhase::AfternoonIncenseCue, P).Value == Outcome::Started, "YK retains afternoon event");
    Check(YK.Save().Services[0].Started && YK.Save().Services[1].Started && YK.Save().Services[2].Started, "three distinct identities");

    Snapshot Bad = S.Save(); Bad.Services[0].Started = false;
    Check(!Reloaded.Restore(Bad) && Reloaded.Save().CycleId == 17, "invalid restore cannot replace valid state");
    Bad = S.Save(); Bad.Version = 2;
    Check(!Reloaded.Restore(Bad), "unknown version rejected");
    Bad = S.Save(); Bad.Services[0].ResidualRemaining = std::numeric_limits<double>::infinity();
    Check(!Reloaded.Restore(Bad), "nonfinite snapshot rejected");
    Bad = S.Save(); Bad.MorningBloodCompleted = false;
    Check(!Reloaded.Restore(Bad), "snapshot requires predecessor");
    Check(!Reloaded.TickSmoke(std::numeric_limits<double>::quiet_NaN()), "nonfinite clock rejected");
    Check(!Reloaded.TickSmoke(-1), "backwards visual clock rejected");
    Check(Reloaded.State(static_cast<Service>(99)) == nullptr, "invalid service safe");
    Check(Reloaded.Advance(static_cast<RitualPhase>(99), P).Value == Outcome::NeedsReview, "unknown phase fails closed");
    std::cout << "Incense schedule: ritual phases, prerequisites, pause, distinct services, smoke lifetime and reload checks passed\n";
}
