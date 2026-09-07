#pragma once
#include <array>
#include <cmath>
#include <cstdint>

// Named ritual events, not modern clock times. No particle renderer or ritual
// permission table is supplied here. Prerequisites are reviewed scenario facts.
namespace MikdashIncense
{
enum class Scenario { OrdinaryDay, YomKippur };
enum class Service { Morning, Afternoon, YomKippurInner };
enum class RitualPhase { MorningBloodCompleted, MorningIncenseCue,
    YomKippurBullSlaughterCompleted, YomKippurInnerCue,
    AfternoonLimbsCompleted, AfternoonIncenseCue };
enum class Location { Unknown, GoldenAltarInHeikhal, ReviewedInnerSanctuaryAnchor };
enum class Officiant { Unknown, AssignedKohen, KohenGadol };
enum class Withdrawal { Unknown, DailyHeikhalAndUlamAltarArea, YomKippurInnerService };
enum class Outcome { Recorded, Started, AlreadyStarted, Paused, Denied, NeedsReview };
enum class SmokePhase { None, Emitting, Residual, Finished };

struct Preconditions
{
    bool ScenarioReviewed = false;
    bool LocationReviewed = false;
    bool OfficiantPreparedAndAssigned = false;
    bool GarmentsReviewedForService = false;
    bool WithdrawalComplete = false;
    Location At = Location::Unknown;
    Officiant Actor = Officiant::Unknown;
    Withdrawal WithdrawalPolicy = Withdrawal::Unknown;
};

struct SmokeTiming
{
    // Explicit artistic parameters, not sourced ritual durations. Zero means
    // no visible smoke duration, without disabling the recorded service event.
    double EmissionSeconds = 0.0;
    double ResidualSeconds = 0.0;
};

struct ServiceState
{
    bool Started = false;
    bool OfficiantExited = false;
    SmokePhase Visual = SmokePhase::None;
    double EmissionRemaining = 0.0;
    double ResidualRemaining = 0.0;
};

struct Snapshot
{
    std::uint32_t Version = 1;
    std::uint64_t CycleId = 0;
    Scenario Day = Scenario::OrdinaryDay;
    SmokeTiming Timing;
    bool MorningBloodCompleted = false;
    bool YomKippurBullSlaughterCompleted = false;
    bool AfternoonLimbsCompleted = false;
    std::array<ServiceState, 3> Services{};
};

struct Result
{
    Outcome Value;
    Service Which;
    std::uint64_t CycleId;
    const char* Explanation;
    const char* SourceId;
};

class Schedule
{
public:
    explicit Schedule(Scenario Day = Scenario::OrdinaryDay,
        std::uint64_t CycleId = 0, SmokeTiming Timing = SmokeTiming{})
    {
        Data.Day = Day;
        Data.CycleId = CycleId;
        if (ValidTiming(Timing)) Data.Timing = Timing;
    }

    // Returns Started once per (CycleId, Service). Renderer should consume that
    // event or reconstruct from Save(), never start on every visible frame.
    Result Advance(RitualPhase Phase, const Preconditions& Ready, bool Paused = false)
    {
        Service Which = Service::Morning;
        switch (Phase)
        {
        case RitualPhase::MorningBloodCompleted:
        case RitualPhase::MorningIncenseCue: break;
        case RitualPhase::YomKippurBullSlaughterCompleted:
        case RitualPhase::YomKippurInnerCue: Which = Service::YomKippurInner; break;
        case RitualPhase::AfternoonLimbsCompleted:
        case RitualPhase::AfternoonIncenseCue: Which = Service::Afternoon; break;
        default: return Make(Outcome::NeedsReview, Which, "Unmodeled ritual phase.");
        }
        if (Paused) return Make(Outcome::Paused, Which, "Simulation paused; no phase changed.");
        if (!ValidScenario(Data.Day) || !Ready.ScenarioReviewed)
            return Make(Outcome::NeedsReview, Which, "A reviewed scenario is required.");
        if (Which == Service::YomKippurInner && Data.Day != Scenario::YomKippur)
            return Make(Outcome::Denied, Which, "The special inner service is not an ordinary-day event.");
        if (Phase == RitualPhase::MorningBloodCompleted)
        {
            Data.MorningBloodCompleted = true;
            return Make(Outcome::Recorded, Which, "Morning predecessor recorded.");
        }
        if (Phase == RitualPhase::YomKippurBullSlaughterCompleted)
        {
            Data.YomKippurBullSlaughterCompleted = true;
            return Make(Outcome::Recorded, Which, "Yom Kippur predecessor recorded.");
        }
        if (Phase == RitualPhase::AfternoonLimbsCompleted)
        {
            Data.AfternoonLimbsCompleted = true;
            return Make(Outcome::Recorded, Which, "Afternoon predecessor recorded.");
        }
        ServiceState& Run = Data.Services[Index(Which)];
        if (Run.Started) return Make(Outcome::AlreadyStarted, Which, "This service was already emitted in this cycle.");
        if ((Which == Service::Morning && !Data.MorningBloodCompleted)
            || (Which == Service::Afternoon && !Data.AfternoonLimbsCompleted)
            || (Which == Service::YomKippurInner && !Data.YomKippurBullSlaughterCompleted))
            return Make(Outcome::Denied, Which, "The named predecessor has not occurred.");
        if (!Ready.LocationReviewed || Ready.At == Location::Unknown || Ready.Actor == Officiant::Unknown
            || Ready.WithdrawalPolicy == Withdrawal::Unknown)
            return Make(Outcome::NeedsReview, Which, "Location, officiant or withdrawal policy needs review.");
        const bool Inner = Which == Service::YomKippurInner;
        if (Ready.At != (Inner ? Location::ReviewedInnerSanctuaryAnchor : Location::GoldenAltarInHeikhal)
            || Ready.WithdrawalPolicy != (Inner ? Withdrawal::YomKippurInnerService : Withdrawal::DailyHeikhalAndUlamAltarArea))
            return Make(Outcome::Denied, Which, "Location or withdrawal policy belongs to a different service.");
        if ((Ready.Actor != Officiant::AssignedKohen && Ready.Actor != Officiant::KohenGadol)
            || ((Inner || Data.Day == Scenario::YomKippur) && Ready.Actor != Officiant::KohenGadol)
            || !Ready.OfficiantPreparedAndAssigned || !Ready.GarmentsReviewedForService || !Ready.WithdrawalComplete)
            return Make(Outcome::Denied, Which, "Officiant, garments or withdrawal prerequisites remain incomplete.");
        Run.Started = true;
        Run.EmissionRemaining = Data.Timing.EmissionSeconds;
        Run.ResidualRemaining = Data.Timing.ResidualSeconds;
        RefreshVisual(Run);
        return Make(Outcome::Started, Which, "Service event started; smoke duration is an artistic parameter.");
    }

    bool TickSmoke(double Seconds, bool Paused = false)
    {
        if (Paused || !std::isfinite(Seconds) || Seconds < 0.0) return false;
        for (ServiceState& Run : Data.Services)
        {
            if (!Run.Started) continue;
            double Remaining = Seconds;
            const double UsedEmission = Remaining < Run.EmissionRemaining ? Remaining : Run.EmissionRemaining;
            Run.EmissionRemaining -= UsedEmission;
            Remaining -= UsedEmission;
            const double UsedResidual = Remaining < Run.ResidualRemaining ? Remaining : Run.ResidualRemaining;
            Run.ResidualRemaining -= UsedResidual;
            RefreshVisual(Run);
        }
        return true;
    }

    bool MarkOfficiantExited(Service Which, bool Paused = false)
    {
        if (Paused || !ValidService(Which)) return false;
        ServiceState& Run = Data.Services[Index(Which)];
        if (!Run.Started || Run.OfficiantExited) return false;
        Run.OfficiantExited = true; // Does not stop smoke or grant entry.
        return true;
    }

    const ServiceState* State(Service Which) const
    {
        return ValidService(Which) ? &Data.Services[Index(Which)] : nullptr;
    }
    Snapshot Save() const { return Data; }
    bool Restore(const Snapshot& Saved)
    {
        if (Saved.Version != 1 || !ValidScenario(Saved.Day) || !ValidTiming(Saved.Timing)) return false;
        for (unsigned I = 0; I < 3; ++I)
        {
            const ServiceState& Run = Saved.Services[I];
            if (!std::isfinite(Run.EmissionRemaining) || !std::isfinite(Run.ResidualRemaining)
                || Run.EmissionRemaining < 0 || Run.ResidualRemaining < 0
                || Run.EmissionRemaining > Saved.Timing.EmissionSeconds || Run.ResidualRemaining > Saved.Timing.ResidualSeconds)
                return false;
            if (!Run.Started && (Run.OfficiantExited || Run.Visual != SmokePhase::None
                || Run.EmissionRemaining != 0 || Run.ResidualRemaining != 0)) return false;
            if (Run.Started)
            {
                if ((I == 0 && !Saved.MorningBloodCompleted) || (I == 1 && !Saved.AfternoonLimbsCompleted)
                    || (I == 2 && (Saved.Day != Scenario::YomKippur || !Saved.YomKippurBullSlaughterCompleted))) return false;
                ServiceState Expected = Run;
                RefreshVisual(Expected);
                if (Expected.Visual != Run.Visual) return false;
                if (Run.EmissionRemaining > 0 && Run.ResidualRemaining != Saved.Timing.ResidualSeconds) return false;
            }
        }
        if (Saved.Day == Scenario::OrdinaryDay && Saved.YomKippurBullSlaughterCompleted) return false;
        Data = Saved;
        return true;
    }

private:
    Snapshot Data;
    static bool ValidScenario(Scenario Day) { return Day == Scenario::OrdinaryDay || Day == Scenario::YomKippur; }
    static bool ValidService(Service Which)
    { return Which == Service::Morning || Which == Service::Afternoon || Which == Service::YomKippurInner; }
    static unsigned Index(Service Which) { return static_cast<unsigned>(Which); }
    static bool ValidTiming(SmokeTiming Timing)
    { return std::isfinite(Timing.EmissionSeconds) && std::isfinite(Timing.ResidualSeconds)
        && Timing.EmissionSeconds >= 0 && Timing.ResidualSeconds >= 0; }
    static void RefreshVisual(ServiceState& Run)
    { Run.Visual = Run.EmissionRemaining > 0 ? SmokePhase::Emitting
        : (Run.ResidualRemaining > 0 ? SmokePhase::Residual : SmokePhase::Finished); }
    Result Make(Outcome Value, Service Which, const char* Explanation) const
    { return {Value, Which, Data.CycleId, Explanation, Which == Service::YomKippurInner
        ? "KET-YK-SEQUENCE; KET-YK-WITHDRAWAL; KET-SMOKE-FORM"
        : "KET-DAILY-SEQUENCE; KET-DAILY-LOCATION; KET-OVERSEER; KET-SMOKE-DAILY"}; }
};
}
