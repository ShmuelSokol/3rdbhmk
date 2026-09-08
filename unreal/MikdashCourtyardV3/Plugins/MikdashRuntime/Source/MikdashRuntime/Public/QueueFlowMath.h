#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

// Engine-independent queueing math shared by AMikdashGateSecurity and the standalone tests.
// Units: seconds, people, people-per-minute. No Unreal types, no allocation, no globals,
// no static state -- every FCheckpoint carries its own deterministic stream.
//
// WHAT THIS IS: the arithmetic behind a modern security checkpoint at a gate approach --
// arrivals joining the shortest of several walk-through detector lanes, a randomised service
// time at the detector, an occasional wave-aside to a bag-scanner table, a hard queue cap so
// that a lane that is already full turns people away instead of growing without bound, and a
// fairness invariant that says nobody waits forever.
//
// WHAT THIS IS NOT: it is not a crowd simulation, a pathfinder, a collision model, or a
// security system. It produces waiting times and slot indices. Bodies, footsteps and
// animation belong to the crowd and resident systems, which call in through the actor's
// public API; nothing here moves anything.
//
// PROVENANCE: the checkpoint itself is MODERN STAGING (see SourceAssets/security-review/
// sources.md). Metal detectors, bag scanners and the queue discipline they impose are
// modelled on the entrance procedure at the Har HaBayit and Kotel plaza approaches TODAY.
// They are not derived from any classical source and no source is cited for them.
// The one halachic element in the scene is the SIGNAGE about footwear, which this file
// does not model at all -- it is geometry and texture, not queueing.
namespace MikdashQueue
{
// ---------------------------------------------------------------------------
// Fixed capacities. Chosen so an FCheckpoint is a plain value type that can live
// inside a UObject without ever allocating on tick.
// ---------------------------------------------------------------------------
constexpr int MaxLanes = 6;         // walk-through detector lanes at one gate approach
constexpr int MaxBagTables = 4;     // bag-scanner tables shared by those lanes
constexpr int MaxQueue = 64;        // hard cap on people waiting in one lane

constexpr double MinServiceSeconds = 0.20;
constexpr double MaxServiceSeconds = 120.0;

inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }
inline bool Finite(double V) { return std::isfinite(V); }

// ---------------------------------------------------------------------------
// Deterministic stream. SplitMix64: same seed -> same run, on every platform and
// every compiler, which is what makes the standalone test meaningful.
// ---------------------------------------------------------------------------
struct FRandomStream
{
    std::uint64_t State = 0x9E3779B97F4A7C15ull;

    void Seed(std::uint64_t InSeed) { State = InSeed ? InSeed : 0x9E3779B97F4A7C15ull; }

    std::uint64_t NextBits()
    {
        State += 0x9E3779B97F4A7C15ull;
        std::uint64_t Z = State;
        Z = (Z ^ (Z >> 30)) * 0xBF58476D1CE4E5B9ull;
        Z = (Z ^ (Z >> 27)) * 0x94D049BB133111EBull;
        return Z ^ (Z >> 31);
    }

    /** Uniform in [0, 1). */
    double Next01() { return double(NextBits() >> 11) * (1.0 / 9007199254740992.0); }

    /** Uniform in [-1, 1]. */
    double NextSigned() { return Next01() * 2.0 - 1.0; }
};

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------
struct FFlowParams
{
    /** People arriving at this gate approach, per minute, across all lanes. */
    double ArrivalsPerMinute = 40.0;
    /** Mean time one person spends at the detector: step in, pause, walk through. */
    double MeanServiceSeconds = 5.0;
    /** Symmetric jitter around the mean; the draw is clamped to stay positive. */
    double ServiceJitterSeconds = 2.0;
    /** Probability that a person is waved aside to a bag table after the detector. */
    double BagCheckProbability = 0.18;
    /** Mean time at the bag table once waved aside. */
    double BagCheckSeconds = 14.0;
    double BagCheckJitterSeconds = 5.0;
    int DetectorLanes = 2;
    int BagTables = 1;
    /** Hard cap per lane. A lane at capacity refuses; this is what bounds the wait. */
    int QueueCapacityPerLane = 20;
    /** Hard cap on the line waiting for a bag table. Somebody waved aside when this line is
     * already full is simply let through instead -- the checkpoint would rather pass a person
     * unchecked than hold them indefinitely, and that choice is what bounds the second half
     * of the wait. Modern staging, like the bag table itself. */
    int BagQueueCapacity = 8;
    /** Design ceiling. FairnessHolds() reports a breach; it never silently clamps.
     * It must be at least WorstCaseWaitSeconds() or it cannot be honoured; see
     * CeilingIsAchievable(), which the actor reports rather than patching over. */
    double FairnessCapSeconds = 360.0;

    /** Clamp every field into a range the simulation can actually run. Returns a copy;
     * the caller keeps the authored values so a receipt can show what was corrected. */
    FFlowParams Sanitized() const
    {
        FFlowParams P = *this;
        P.ArrivalsPerMinute = Finite(P.ArrivalsPerMinute) ? Clamp(P.ArrivalsPerMinute, 0.0, 600.0) : 0.0;
        P.MeanServiceSeconds = Finite(P.MeanServiceSeconds) ? Clamp(P.MeanServiceSeconds, MinServiceSeconds, MaxServiceSeconds) : 5.0;
        P.ServiceJitterSeconds = Finite(P.ServiceJitterSeconds) ? Clamp(P.ServiceJitterSeconds, 0.0, P.MeanServiceSeconds - MinServiceSeconds * 0.5) : 0.0;
        P.BagCheckProbability = Finite(P.BagCheckProbability) ? Clamp(P.BagCheckProbability, 0.0, 1.0) : 0.0;
        P.BagCheckSeconds = Finite(P.BagCheckSeconds) ? Clamp(P.BagCheckSeconds, MinServiceSeconds, MaxServiceSeconds) : 14.0;
        P.BagCheckJitterSeconds = Finite(P.BagCheckJitterSeconds) ? Clamp(P.BagCheckJitterSeconds, 0.0, P.BagCheckSeconds - MinServiceSeconds * 0.5) : 0.0;
        P.DetectorLanes = std::max(1, std::min(MaxLanes, P.DetectorLanes));
        P.BagTables = std::max(0, std::min(MaxBagTables, P.BagTables));
        P.QueueCapacityPerLane = std::max(1, std::min(MaxQueue, P.QueueCapacityPerLane));
        P.BagQueueCapacity = std::max(1, std::min(MaxQueue, P.BagQueueCapacity));
        P.FairnessCapSeconds = Finite(P.FairnessCapSeconds) ? Clamp(P.FairnessCapSeconds, 1.0, 3600.0) : 360.0;
        if (P.BagTables == 0)
        {
            P.BagCheckProbability = 0.0;   // nowhere to wave anyone aside to
        }
        return P;
    }

    bool IsSane() const
    {
        const FFlowParams S = Sanitized();
        return S.ArrivalsPerMinute == ArrivalsPerMinute && S.MeanServiceSeconds == MeanServiceSeconds
            && S.ServiceJitterSeconds == ServiceJitterSeconds && S.BagCheckProbability == BagCheckProbability
            && S.BagCheckSeconds == BagCheckSeconds && S.BagCheckJitterSeconds == BagCheckJitterSeconds
            && S.DetectorLanes == DetectorLanes && S.BagTables == BagTables
            && S.QueueCapacityPerLane == QueueCapacityPerLane && S.BagQueueCapacity == BagQueueCapacity
            && S.FairnessCapSeconds == FairnessCapSeconds;
    }
};

// ---------------------------------------------------------------------------
// One person's place in the checkpoint
// ---------------------------------------------------------------------------
enum class EStage : std::uint8_t
{
    None = 0,
    WaitingAtDetector,   // standing in the lane, shuffling forward
    AtDetector,          // stepped in, paused, walking through the arch
    WaitingAtBagTable,   // waved aside, standing at the table
    AtBagTable,          // bag on the conveyor, under the hood
    Cleared,             // through; the caller may release the body
    Refused              // the lane was full when they asked; sent to another approach
};

struct FTicket
{
    int Id = -1;
    int Lane = -1;
    /** Simulation time the person joined the queue. */
    double JoinTime = 0.0;
    /** Time the DETECTOR service began; negative until it does. */
    double DetectorStartTime = -1.0;
    /** Time the person finally cleared the whole checkpoint; negative until they do. */
    double ClearTime = -1.0;
    /** Decided at join time so the actor can pre-aim the body at the bag table. */
    bool bBagCheck = false;
    EStage Stage = EStage::None;

    bool IsValid() const { return Id >= 0; }
    double WaitSoFar(double Now) const { return std::max(0.0, Now - JoinTime); }
    double TotalWait() const { return ClearTime >= 0.0 ? ClearTime - JoinTime : -1.0; }
};

/** What RequestToPass hands back. */
struct FPassGrant
{
    bool bAccepted = false;
    int TicketId = -1;
    int Lane = -1;
    /** Index in the lane, 0 = at the arch. The actor turns this into a standing position. */
    int SlotIndex = -1;
    /** Predicted seconds from now until this person is clear of the whole checkpoint.
     * A prediction, not a promise: the actual figure is FTicket::TotalWait() afterwards. */
    double EstimatedWaitSeconds = 0.0;
    bool bBagCheck = false;
};

// ---------------------------------------------------------------------------
// Analytic cross-checks. These do NOT drive the simulation; the test compares the
// simulated queue against them so a wrong sign or a wrong unit shows up immediately.
// ---------------------------------------------------------------------------

/** Offered load in erlangs: arrivals per second times mean service time. */
inline double OfferedLoad(const FFlowParams& P)
{
    return (P.ArrivalsPerMinute / 60.0) * P.MeanServiceSeconds;
}

/** Server utilisation of an c-server checkpoint. >= 1 means the queue cap will bite. */
inline double Utilisation(const FFlowParams& P)
{
    const double C = double(std::max(1, P.DetectorLanes));
    return OfferedLoad(P) / C;
}

/** Erlang-C: probability that an arrival to an M/M/c queue has to wait at all.
 * Standard textbook formula, used only as a sanity rail in the tests. */
inline double ErlangC(const FFlowParams& P)
{
    const int C = std::max(1, P.DetectorLanes);
    const double A = OfferedLoad(P);
    const double Rho = A / double(C);
    if (Rho >= 1.0)
    {
        return 1.0;
    }
    double Term = 1.0, Sum = 1.0;
    for (int K = 1; K < C; ++K)
    {
        Term *= A / double(K);
        Sum += Term;
    }
    const double Last = Term * A / double(C);     // A^c / c!
    const double Numerator = Last / (1.0 - Rho);
    return Numerator / (Sum + Numerator);
}

/** Mean waiting time before service in an M/M/c queue, seconds. Sanity rail only. */
inline double MeanWaitMMc(const FFlowParams& P)
{
    const int C = std::max(1, P.DetectorLanes);
    const double Rho = Utilisation(P);
    if (Rho >= 1.0)
    {
        return std::numeric_limits<double>::infinity();
    }
    return ErlangC(P) * P.MeanServiceSeconds / (double(C) * (1.0 - Rho));
}

/** The bound that makes "nobody waits forever" a theorem rather than a hope.
 *
 * DETECTOR. A lane holds at most QueueCapacityPerLane people waiting and refuses anyone
 * else, so an accepted person finds at most QueueCapacityPerLane - 1 people ahead of them
 * in the line plus at most one already at the arch; their own pass follows. Every one of
 * those services is drawn clamped to at most MeanService + Jitter, and a lane never idles
 * while anyone is waiting, so the detector half is at most
 *     (QueueCapacityPerLane + 1) x (MeanService + Jitter).
 *
 * BAG TABLE. A person waved aside joins a line capped at BagQueueCapacity -- past that they
 * are let through rather than held -- so at most BagQueueCapacity - 1 are ahead of them,
 * spread over BagTables tables, plus the round already in progress and their own:
 *     (ceil(BagQueueCapacity / BagTables) + 2) x (BagCheck + BagJitter).
 *
 * Nothing else can delay anybody: every arrival that would lengthen either line is refused
 * or passed through. The sum is therefore a true upper bound on the total wait. The
 * standalone test drives a ten-times-overloaded checkpoint against it for an hour. */
inline double WorstCaseWaitSeconds(const FFlowParams& In)
{
    const FFlowParams P = In.Sanitized();
    const double SlowestDetector = P.MeanServiceSeconds + P.ServiceJitterSeconds;
    double Worst = double(P.QueueCapacityPerLane + 1) * SlowestDetector;
    if (P.BagTables > 0 && P.BagCheckProbability > 0.0)
    {
        const double SlowestBag = P.BagCheckSeconds + P.BagCheckJitterSeconds;
        const double Rounds = std::ceil(double(P.BagQueueCapacity) / double(P.BagTables)) + 2.0;
        Worst += Rounds * SlowestBag;
    }
    return Worst;
}

/** Is the authored fairness ceiling actually reachable with these parameters?
 *
 * WorstCaseWaitSeconds is a property of the capacity and the service times; FairnessCapSeconds
 * is a wish. If the wish is smaller than the bound, a busy checkpoint WILL breach the ceiling
 * and FairnessHolds() will say so. That is a configuration error, and it is detectable before
 * anyone is made to stand in the queue, so it is reported rather than silently patched. */
inline bool CeilingIsAchievable(const FFlowParams& P)
{
    return WorstCaseWaitSeconds(P) <= P.Sanitized().FairnessCapSeconds + 1e-9;
}

/** The largest per-lane capacity whose worst case still fits inside the authored ceiling,
 * or 0 when even a queue of one cannot. The bag line is shrunk alongside it, because on a
 * busy approach the bag half of the bound is usually the larger of the two. Use it to set
 * QueueCapacityPerLane and BagQueueCapacity together. */
inline int CapacityForCeiling(const FFlowParams& In)
{
    const FFlowParams P = In.Sanitized();
    for (int C = P.QueueCapacityPerLane; C >= 1; --C)
    {
        FFlowParams Q = P;
        Q.QueueCapacityPerLane = C;
        Q.BagQueueCapacity = std::min(P.BagQueueCapacity, C);
        if (WorstCaseWaitSeconds(Q) <= P.FairnessCapSeconds + 1e-9)
        {
            return C;
        }
    }
    return 0;
}

// ---------------------------------------------------------------------------
// The checkpoint
// ---------------------------------------------------------------------------
class FCheckpoint
{
public:
    void Configure(const FFlowParams& InParams, std::uint64_t InSeed)
    {
        Authored = InParams;
        Params = InParams.Sanitized();
        Rng.Seed(InSeed);
        Now = 0.0;
        NextTicketId = 0;
        Served = 0;
        Refused = 0;
        BagChecked = 0;
        BagLineFull = 0;
        SumTotalWait = 0.0;
        MaxTotalWait = 0.0;
        MaxObservedQueue = 0;
        FifoBreaches = 0;
        ResetClearedRing();
        for (int L = 0; L < MaxLanes; ++L)
        {
            Lanes[L] = FLane();
        }
        for (int B = 0; B < MaxBagTables; ++B)
        {
            BagTables[B] = FServer();
        }
        BagQueueHead = 0;
        BagQueueCount = 0;
    }

    const FFlowParams& GetParams() const { return Params; }
    const FFlowParams& GetAuthoredParams() const { return Authored; }
    double GetNow() const { return Now; }

    // -- queue interrogation ------------------------------------------------

    int GetLaneCount() const { return Params.DetectorLanes; }

    /** People standing in a lane, NOT counting the one currently at the arch. */
    int QueueLength(int Lane) const
    {
        return (Lane >= 0 && Lane < Params.DetectorLanes) ? Lanes[Lane].Count : 0;
    }

    /** Everyone anywhere in the checkpoint who has not yet cleared. */
    int TotalQueueLength() const
    {
        int Total = BagQueueCount;
        for (int L = 0; L < Params.DetectorLanes; ++L)
        {
            Total += Lanes[L].Count + (Lanes[L].Server.bBusy ? 1 : 0);
        }
        for (int B = 0; B < Params.BagTables; ++B)
        {
            Total += BagTables[B].bBusy ? 1 : 0;
        }
        return Total;
    }

    int WaitingForBagTable() const { return BagQueueCount; }

    /** The lane a newcomer would be sent to: fewest waiting, ties to the lower index. */
    int ShortestLane() const
    {
        int Best = 0;
        for (int L = 1; L < Params.DetectorLanes; ++L)
        {
            if (Lanes[L].Count < Lanes[Best].Count)
            {
                Best = L;
            }
        }
        return Best;
    }

    /** Seconds a person joining `Lane` right now should expect to spend in total.
     * Deterministic and side-effect free, so a caller may ask before committing. */
    double EstimatedWaitSeconds(int Lane, bool bAssumeBagCheck) const
    {
        if (Lane < 0 || Lane >= Params.DetectorLanes)
        {
            return -1.0;
        }
        const FLane& L = Lanes[Lane];
        double Wait = double(L.Count) * Params.MeanServiceSeconds;
        Wait += L.Server.bBusy ? std::max(0.0, L.Server.FreeAtTime - Now) : 0.0;
        Wait += Params.MeanServiceSeconds;                       // their own pass through the arch
        if (bAssumeBagCheck && Params.BagTables > 0)
        {
            const double Ahead = double(BagQueueCount) / double(Params.BagTables);
            Wait += Ahead * Params.BagCheckSeconds + Params.BagCheckSeconds;
        }
        return Wait;
    }

    // -- the public request --------------------------------------------------

    /** A visitor asks to pass. Returns a grant; on refusal EstimatedWaitSeconds is < 0.
     * Refusal happens only when the shortest lane is at its hard capacity -- that refusal
     * is exactly what keeps the wait bounded. */
    FPassGrant RequestToPass()
    {
        FPassGrant G;
        const int Lane = ShortestLane();
        FLane& L = Lanes[Lane];
        if (L.Count >= Params.QueueCapacityPerLane)
        {
            ++Refused;
            G.bAccepted = false;
            G.Lane = Lane;
            G.EstimatedWaitSeconds = -1.0;
            return G;
        }
        FTicket T;
        T.Id = NextTicketId++;
        T.Lane = Lane;
        T.JoinTime = Now;
        T.bBagCheck = Params.BagTables > 0 && Rng.Next01() < Params.BagCheckProbability;
        T.Stage = EStage::WaitingAtDetector;

        G.bAccepted = true;
        G.TicketId = T.Id;
        G.Lane = Lane;
        G.SlotIndex = L.Count;
        G.bBagCheck = T.bBagCheck;
        G.EstimatedWaitSeconds = EstimatedWaitSeconds(Lane, T.bBagCheck);

        L.Slots[(L.Head + L.Count) % MaxQueue] = T;
        ++L.Count;
        MaxObservedQueue = std::max(MaxObservedQueue, L.Count);
        return G;
    }

    /** Position of a live ticket, or an invalid ticket if it has already cleared or was
     * never issued. Callers use SlotIndex to place a body in the line. */
    bool FindTicket(int TicketId, FTicket& Out, int& OutSlotIndex) const
    {
        for (int L = 0; L < Params.DetectorLanes; ++L)
        {
            const FLane& Lane = Lanes[L];
            if (Lane.Server.bBusy && Lane.Server.Occupant.Id == TicketId)
            {
                Out = Lane.Server.Occupant;
                OutSlotIndex = -1;                 // at the arch, not in the line
                return true;
            }
            for (int I = 0; I < Lane.Count; ++I)
            {
                const FTicket& T = Lane.Slots[(Lane.Head + I) % MaxQueue];
                if (T.Id == TicketId)
                {
                    Out = T;
                    OutSlotIndex = I;
                    return true;
                }
            }
        }
        for (int I = 0; I < BagQueueCount; ++I)
        {
            const FTicket& T = BagQueue[(BagQueueHead + I) % MaxQueue];
            if (T.Id == TicketId)
            {
                Out = T;
                OutSlotIndex = I;
                return true;
            }
        }
        for (int B = 0; B < Params.BagTables; ++B)
        {
            if (BagTables[B].bBusy && BagTables[B].Occupant.Id == TicketId)
            {
                Out = BagTables[B].Occupant;
                OutSlotIndex = -1;
                return true;
            }
        }
        return false;
    }

    // -- the clock ------------------------------------------------------------

    /** Advance the checkpoint. Substeps internally so a long frame cannot let a server
     * finish twice in one go without the next person starting at the right moment. */
    void Advance(double DeltaSeconds)
    {
        if (!Finite(DeltaSeconds) || DeltaSeconds <= 0.0)
        {
            return;
        }
        const double MaxStep = MinServiceSeconds * 0.5;
        double Remaining = std::min(DeltaSeconds, 3600.0);
        while (Remaining > 0.0)
        {
            const double Step = std::min(Remaining, MaxStep);
            Now += Step;
            Remaining -= Step;
            Step_Bag();
            Step_Detectors();
        }
    }

    /** Pop the next person who has finished the whole checkpoint, oldest first.
     * The caller releases the body when this returns true. */
    bool PopCleared(FTicket& Out)
    {
        if (ClearedCount == 0)
        {
            return false;
        }
        Out = Cleared[ClearedHead];
        ClearedHead = (ClearedHead + 1) % MaxCleared;
        --ClearedCount;
        return true;
    }

    /** Pop the next person who has just been waved aside from the arch to a bag table,
     * oldest first. The caller redirects the body; the ticket is still live. */
    bool PopWavedAside(FTicket& Out)
    {
        if (WavedCount == 0)
        {
            return false;
        }
        Out = Waved[WavedHead];
        WavedHead = (WavedHead + 1) % MaxCleared;
        --WavedCount;
        return true;
    }

    // -- statistics and the fairness invariant --------------------------------

    int ServedCount() const { return Served; }
    int RefusedCount() const { return Refused; }
    /** People who actually reached a bag table. */
    int BagCheckedCount() const { return BagChecked; }
    /** People selected for a bag check who were passed through instead because the bag line
     * was at its cap. A non-zero figure means BagQueueCapacity or BagTables is too small. */
    int BagLineFullCount() const { return BagLineFull; }
    int MaxObservedQueueLength() const { return MaxObservedQueue; }
    double MaxObservedTotalWaitSeconds() const { return MaxTotalWait; }
    double MeanObservedTotalWaitSeconds() const { return Served > 0 ? SumTotalWait / double(Served) : 0.0; }
    /** Number of times somebody in a lane was served ahead of somebody who joined that
     * lane earlier. A correct FIFO ring can never do this; it stays 0 or the model is wrong. */
    int FifoBreachCount() const { return FifoBreaches; }
    double ObservedBagCheckRate() const { return Served > 0 ? double(BagChecked) / double(Served) : 0.0; }

    /** The fairness check the brief asks for: nobody waits forever.
     *  1. every completed wait is <= the closed-form worst case for these parameters;
     *  2. every completed wait is <= the authored design ceiling;
     *  3. no lane ever served out of join order;
     *  4. nobody is still standing in a lane whose wait already exceeds the worst case.
     * Returns false and fills OutReason on the first failure. */
    bool FairnessHolds(const char*& OutReason) const
    {
        const double Bound = WorstCaseWaitSeconds(Params);
        if (MaxTotalWait > Bound + 1e-6)
        {
            OutReason = "a completed wait exceeded the closed-form worst case";
            return false;
        }
        if (MaxTotalWait > Params.FairnessCapSeconds + 1e-6)
        {
            OutReason = "a completed wait exceeded the authored fairness ceiling";
            return false;
        }
        if (FifoBreaches != 0)
        {
            OutReason = "a lane served out of join order";
            return false;
        }
        for (int L = 0; L < Params.DetectorLanes; ++L)
        {
            const FLane& Lane = Lanes[L];
            for (int I = 0; I < Lane.Count; ++I)
            {
                if (Lane.Slots[(Lane.Head + I) % MaxQueue].WaitSoFar(Now) > Bound + 1e-6)
                {
                    OutReason = "someone is still waiting past the closed-form worst case";
                    return false;
                }
            }
        }
        for (int I = 0; I < BagQueueCount; ++I)
        {
            if (BagQueue[(BagQueueHead + I) % MaxQueue].WaitSoFar(Now) > Bound + 1e-6)
            {
                OutReason = "someone at the bag table has waited past the closed-form worst case";
                return false;
            }
        }
        OutReason = "";
        return true;
    }

    bool FairnessHolds() const
    {
        const char* Reason = "";
        return FairnessHolds(Reason);
    }

    /** Arrivals in a slice of time, Poisson-thinned from ArrivalsPerMinute. Callers that
     * have their own crowd source ignore this entirely and just call RequestToPass. */
    int DrawArrivals(double DeltaSeconds)
    {
        if (!Finite(DeltaSeconds) || DeltaSeconds <= 0.0)
        {
            return 0;
        }
        const double Lambda = (Params.ArrivalsPerMinute / 60.0) * std::min(DeltaSeconds, 60.0);
        // Knuth's method; Lambda is small here, so the loop is short.
        const double Limit = std::exp(-Lambda);
        double Product = 1.0;
        int K = 0;
        while (K < 64)
        {
            Product *= Rng.Next01();
            if (Product <= Limit)
            {
                break;
            }
            ++K;
        }
        return K;
    }

private:
    struct FServer
    {
        bool bBusy = false;
        double FreeAtTime = 0.0;
        FTicket Occupant;
    };

    struct FLane
    {
        int Head = 0;
        int Count = 0;
        FTicket Slots[MaxQueue];
        FServer Server;
        int LastStartedId = -1;
    };

    static constexpr int MaxCleared = 128;

    void ResetClearedRing()
    {
        ClearedHead = 0;
        ClearedCount = 0;
        WavedHead = 0;
        WavedCount = 0;
    }

    double DrawService()
    {
        const double D = Params.MeanServiceSeconds + Params.ServiceJitterSeconds * Rng.NextSigned();
        return Clamp(D, MinServiceSeconds, Params.MeanServiceSeconds + Params.ServiceJitterSeconds);
    }

    double DrawBagService()
    {
        const double D = Params.BagCheckSeconds + Params.BagCheckJitterSeconds * Rng.NextSigned();
        return Clamp(D, MinServiceSeconds, Params.BagCheckSeconds + Params.BagCheckJitterSeconds);
    }

    void PushCleared(FTicket T)
    {
        T.Stage = EStage::Cleared;
        T.ClearTime = Now;
        ++Served;
        const double Total = T.TotalWait();
        SumTotalWait += Total;
        MaxTotalWait = std::max(MaxTotalWait, Total);
        if (ClearedCount < MaxCleared)
        {
            Cleared[(ClearedHead + ClearedCount) % MaxCleared] = T;
            ++ClearedCount;
        }
        // If the caller never drains PopCleared the oldest entries are dropped, but the
        // statistics above have already counted them, so nothing is lost from the receipt.
    }

    void Step_Detectors()
    {
        for (int L = 0; L < Params.DetectorLanes; ++L)
        {
            FLane& Lane = Lanes[L];
            if (Lane.Server.bBusy && Now >= Lane.Server.FreeAtTime)
            {
                FTicket T = Lane.Server.Occupant;
                Lane.Server.bBusy = false;
                if (T.bBagCheck && Params.BagTables > 0)
                {
                    if (BagQueueCount < Params.BagQueueCapacity)
                    {
                        ++BagChecked;
                        T.Stage = EStage::WaitingAtBagTable;
                        BagQueue[(BagQueueHead + BagQueueCount) % MaxQueue] = T;
                        ++BagQueueCount;
                        if (WavedCount < MaxCleared)
                        {
                            Waved[(WavedHead + WavedCount) % MaxCleared] = T;
                            ++WavedCount;
                        }
                    }
                    else
                    {
                        // The bag line is already at its cap. The checkpoint would rather pass
                        // a person unchecked than hold them indefinitely; that is what keeps
                        // the second half of the wait bounded, and it is counted separately so
                        // a receipt can say how often it happened.
                        ++BagLineFull;
                        PushCleared(T);
                    }
                }
                else
                {
                    PushCleared(T);
                }
            }
            if (!Lane.Server.bBusy && Lane.Count > 0)
            {
                FTicket T = Lane.Slots[Lane.Head];
                Lane.Head = (Lane.Head + 1) % MaxQueue;
                --Lane.Count;
                if (T.Id < Lane.LastStartedId)
                {
                    ++FifoBreaches;
                }
                Lane.LastStartedId = T.Id;
                T.Stage = EStage::AtDetector;
                T.DetectorStartTime = Now;
                Lane.Server.Occupant = T;
                Lane.Server.bBusy = true;
                Lane.Server.FreeAtTime = Now + DrawService();
            }
        }
    }

    void Step_Bag()
    {
        for (int B = 0; B < Params.BagTables; ++B)
        {
            FServer& S = BagTables[B];
            if (S.bBusy && Now >= S.FreeAtTime)
            {
                S.bBusy = false;
                PushCleared(S.Occupant);
            }
            if (!S.bBusy && BagQueueCount > 0)
            {
                FTicket T = BagQueue[BagQueueHead];
                BagQueueHead = (BagQueueHead + 1) % MaxQueue;
                --BagQueueCount;
                T.Stage = EStage::AtBagTable;
                S.Occupant = T;
                S.bBusy = true;
                S.FreeAtTime = Now + DrawBagService();
            }
        }
    }

    FFlowParams Authored;
    FFlowParams Params;
    FRandomStream Rng;
    double Now = 0.0;
    int NextTicketId = 0;

    FLane Lanes[MaxLanes];
    FServer BagTables[MaxBagTables];
    FTicket BagQueue[MaxQueue];
    int BagQueueHead = 0;
    int BagQueueCount = 0;

    FTicket Cleared[MaxCleared];
    int ClearedHead = 0;
    int ClearedCount = 0;

    FTicket Waved[MaxCleared];
    int WavedHead = 0;
    int WavedCount = 0;

    int Served = 0;
    int Refused = 0;
    int BagChecked = 0;
    int BagLineFull = 0;
    double SumTotalWait = 0.0;
    double MaxTotalWait = 0.0;
    int MaxObservedQueue = 0;
    int FifoBreaches = 0;
};

// ---------------------------------------------------------------------------
// Guard posts. A guard stands still and scans; this is the whole of their behaviour.
// ---------------------------------------------------------------------------
struct FGuardScan
{
    /** Half-angle of the sweep, degrees either side of the post's facing. */
    double SweepDegrees = 55.0;
    /** Seconds for one full there-and-back sweep. */
    double PeriodSeconds = 9.0;
    /** Fraction of the period spent holding still at each end of the sweep. */
    double DwellFraction = 0.35;
    /** Phase offset so two guards on the same post do not move in lockstep. */
    double PhaseSeconds = 0.0;

    /** Yaw offset from the post facing, degrees, at time T. Continuous, C0, and
     * periodic: a hold at each end joined by a smoothstep, never a linear sawtooth. */
    double YawOffsetAt(double T) const
    {
        const double Period = std::max(0.5, PeriodSeconds);
        const double Dwell = Clamp(DwellFraction, 0.0, 0.49);
        double U = std::fmod((T + PhaseSeconds) / Period, 1.0);
        if (U < 0.0)
        {
            U += 1.0;
        }
        // half the period turns one way, half turns back
        const bool bReturn = U >= 0.5;
        double V = bReturn ? (U - 0.5) * 2.0 : U * 2.0;   // 0..1 within this half
        double S;
        if (V < Dwell)
        {
            S = 0.0;
        }
        else if (V > 1.0 - Dwell)
        {
            S = 1.0;
        }
        else
        {
            const double W = (V - Dwell) / std::max(1e-6, 1.0 - 2.0 * Dwell);
            S = W * W * (3.0 - 2.0 * W);                 // smoothstep
        }
        const double Signed = bReturn ? (1.0 - S) : S;   // 0 -> 1 -> 0 over the period
        return (Signed * 2.0 - 1.0) * SweepDegrees;
    }
};

} // namespace MikdashQueue
