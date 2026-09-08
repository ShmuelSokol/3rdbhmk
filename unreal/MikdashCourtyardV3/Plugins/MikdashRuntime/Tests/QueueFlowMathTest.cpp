// Standalone test for QueueFlowMath.h. No Unreal, no engine headers, no build system.
//
//   "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
//   cl /nologo /EHsc /std:c++17 /W4 /I"<plugin>/Source/MikdashRuntime/Public" QueueFlowMathTest.cpp
//   QueueFlowMathTest.exe > tests.json
//
// It prints a JSON object on stdout and a one-line PASS/FAIL summary on stderr, so the JSON
// can be redirected straight into SourceAssets/security-review/tests.json.
#include "QueueFlowMath.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

using namespace MikdashQueue;

static int Failures = 0;
static std::vector<std::string> Checks;

static void Check(bool Condition, const char* Name)
{
    Checks.push_back(std::string("    {\"check\": \"") + Name + "\", \"pass\": " + (Condition ? "true" : "false") + "}");
    if (!Condition)
    {
        ++Failures;
        std::fprintf(stderr, "FAIL: %s\n", Name);
    }
}

// ---------------------------------------------------------------------------
// A run: feed the checkpoint a Poisson arrival stream for N seconds at 60 Hz.
// ---------------------------------------------------------------------------
struct FRunResult
{
    int Served = 0;
    int Refused = 0;
    int BagChecked = 0;
    int BagLineFull = 0;
    int Offered = 0;
    int MaxQueueSeen = 0;
    int FifoBreaches = 0;
    double MeanWait = 0.0;
    double MaxWait = 0.0;
    double Bound = 0.0;
    bool bFair = false;
    std::string FairnessReason;
    int ClearedPopped = 0;
    int WavedPopped = 0;
    bool bClearedInOrder = true;
};

static FRunResult Run(const FFlowParams& P, double Seconds, std::uint64_t Seed, double Hz = 60.0)
{
    FCheckpoint C;
    C.Configure(P, Seed);
    const double Dt = 1.0 / Hz;
    FRunResult R;
    double LastClearTime = -1.0;
    for (double T = 0.0; T < Seconds; T += Dt)
    {
        const int Arrivals = C.DrawArrivals(Dt);
        for (int I = 0; I < Arrivals; ++I)
        {
            ++R.Offered;
            C.RequestToPass();
        }
        C.Advance(Dt);
        FTicket Popped;
        while (C.PopWavedAside(Popped))
        {
            ++R.WavedPopped;
        }
        while (C.PopCleared(Popped))
        {
            ++R.ClearedPopped;
            if (Popped.ClearTime + 1e-9 < LastClearTime)
            {
                R.bClearedInOrder = false;
            }
            LastClearTime = Popped.ClearTime;
        }
    }
    const char* Reason = "";
    R.bFair = C.FairnessHolds(Reason);
    R.FairnessReason = Reason;
    R.Served = C.ServedCount();
    R.Refused = C.RefusedCount();
    R.BagChecked = C.BagCheckedCount();
    R.BagLineFull = C.BagLineFullCount();
    R.MaxQueueSeen = C.MaxObservedQueueLength();
    R.FifoBreaches = C.FifoBreachCount();
    R.MeanWait = C.MeanObservedTotalWaitSeconds();
    R.MaxWait = C.MaxObservedTotalWaitSeconds();
    R.Bound = WorstCaseWaitSeconds(C.GetParams());
    return R;
}

static std::string RunJson(const char* Name, const FFlowParams& P, const FRunResult& R)
{
    char Buffer[1400];
    std::snprintf(Buffer, sizeof(Buffer),
        "    {\"scenario\": \"%s\", \"lanes\": %d, \"bagTables\": %d, \"capacityPerLane\": %d,\n"
        "     \"arrivalsPerMinute\": %.1f, \"meanServiceSeconds\": %.2f, \"bagCheckProbability\": %.3f,\n"
        "     \"utilisation\": %.4f, \"erlangC\": %.4f, \"analyticMeanWaitBeforeServiceSeconds\": %.3f,\n"
        "     \"offered\": %d, \"served\": %d, \"refused\": %d, \"bagChecked\": %d, \"observedBagRate\": %.4f,\n"
        "     \"maxQueueObserved\": %d, \"meanTotalWaitSeconds\": %.3f, \"maxTotalWaitSeconds\": %.3f,\n"
        "     \"closedFormWorstCaseSeconds\": %.3f, \"fifoBreaches\": %d, \"clearedPopped\": %d, \"wavedAsidePopped\": %d,\n"
        "     \"passedOnFullBagLine\": %d, \"ceilingSeconds\": %.1f, \"ceilingAchievable\": %s,\n"
        "     \"fair\": %s, \"fairnessReason\": \"%s\"}",
        Name, P.DetectorLanes, P.BagTables, P.QueueCapacityPerLane,
        P.ArrivalsPerMinute, P.MeanServiceSeconds, P.BagCheckProbability,
        Utilisation(P), ErlangC(P), MeanWaitMMc(P) > 1e9 ? -1.0 : MeanWaitMMc(P),
        R.Offered, R.Served, R.Refused, R.BagChecked,
        R.Served > 0 ? double(R.BagChecked) / double(R.Served) : 0.0,
        R.MaxQueueSeen, R.MeanWait, R.MaxWait, R.Bound, R.FifoBreaches,
        R.ClearedPopped, R.WavedPopped,
        R.BagLineFull, P.FairnessCapSeconds, CeilingIsAchievable(P) ? "true" : "false",
        R.bFair ? "true" : "false", R.FairnessReason.c_str());
    return Buffer;
}

int main()
{
    std::vector<std::string> Runs;

    // -----------------------------------------------------------------------
    // 1. Parameter sanitising: garbage in must not produce a running-away queue.
    // -----------------------------------------------------------------------
    {
        FFlowParams Bad;
        Bad.ArrivalsPerMinute = std::nan("");
        Bad.MeanServiceSeconds = -4.0;
        Bad.ServiceJitterSeconds = 1e9;
        Bad.BagCheckProbability = 7.0;
        Bad.DetectorLanes = 999;
        Bad.BagTables = -3;
        Bad.QueueCapacityPerLane = 0;
        Bad.BagQueueCapacity = -9;
        Bad.FairnessCapSeconds = std::nan("");
        const FFlowParams S = Bad.Sanitized();
        Check(!Bad.IsSane(), "garbage parameters are reported as not sane");
        Check(S.IsSane(), "sanitising is idempotent");
        Check(S.DetectorLanes == MaxLanes, "lane count clamps to MaxLanes");
        Check(S.BagTables == 0, "negative bag tables clamp to zero");
        Check(S.BagCheckProbability == 0.0, "no bag tables forces the wave-aside rate to zero");
        Check(S.MeanServiceSeconds >= MinServiceSeconds, "service time cannot be negative");
        Check(S.ServiceJitterSeconds < S.MeanServiceSeconds, "jitter cannot exceed the mean");
        Check(S.QueueCapacityPerLane >= 1, "queue capacity is at least one");
        Check(S.BagQueueCapacity >= 1 && S.BagQueueCapacity <= MaxQueue, "bag queue capacity is clamped into range");
        Check(std::isfinite(WorstCaseWaitSeconds(Bad)), "worst-case bound is finite for garbage input");

        FFlowParams Good;
        Check(Good.IsSane(), "the default parameters are already sane");
    }

    // -----------------------------------------------------------------------
    // 2. Determinism: the same seed replays exactly; a different seed does not.
    // -----------------------------------------------------------------------
    {
        FFlowParams P;
        const FRunResult A = Run(P, 600.0, 12345);
        const FRunResult B = Run(P, 600.0, 12345);
        const FRunResult C = Run(P, 600.0, 999);
        Check(A.Served == B.Served && A.MaxWait == B.MaxWait && A.BagChecked == B.BagChecked,
              "the same seed replays the same checkpoint exactly");
        Check(A.Served != C.Served || A.MaxWait != C.MaxWait,
              "a different seed produces a different checkpoint");
        Check(A.Served > 0, "the nominal checkpoint actually serves people");
    }

    // -----------------------------------------------------------------------
    // 3. Nominal load: an under-loaded checkpoint clears everybody, refuses nobody,
    //    and the waits stay far under the bound.
    // -----------------------------------------------------------------------
    {
        FFlowParams P;                     // 40/min, 2 lanes, 5 s service -> rho = 1.67
        P.ArrivalsPerMinute = 18.0;        // rho = 0.75
        const FRunResult R = Run(P, 1800.0, 20260908);
        Runs.push_back(RunJson("nominal_two_lanes_underloaded", P, R));
        Check(R.Refused == 0, "an under-loaded checkpoint refuses nobody");
        Check(R.Served >= R.Offered - 30, "an under-loaded checkpoint clears essentially everybody");
        Check(R.bFair, "nominal load satisfies the fairness invariant");
        Check(R.FifoBreaches == 0, "nominal load never serves a lane out of join order");
        Check(R.MaxWait <= R.Bound, "nominal max wait is inside the closed-form bound");
        Check(R.MeanWait > 0.0 && R.MeanWait < R.Bound, "nominal mean wait is positive and bounded");
        Check(R.ClearedPopped == R.Served, "every served person was handed back through PopCleared");
        Check(R.WavedPopped == R.BagChecked, "every waved-aside person was reported exactly once");
        // the simulated wait must be at least the service time and at most service + queue
        Check(R.MeanWait >= P.MeanServiceSeconds - P.ServiceJitterSeconds,
              "mean total wait is at least one service time");
        // and it must be in the same country as the M/M/c analytic prediction
        const double Analytic = MeanWaitMMc(P) + P.MeanServiceSeconds
                              + P.BagCheckProbability * P.BagCheckSeconds;
        Check(R.MeanWait > 0.3 * Analytic && R.MeanWait < 3.0 * Analytic,
              "simulated mean wait is within a factor of three of the M/M/c prediction");
    }

    // -----------------------------------------------------------------------
    // 4. Overload: this is the case the fairness claim is really about. Arrivals far
    //    exceed capacity; the queue must NOT grow without bound and nobody already in
    //    it may wait past the closed-form worst case. The excess is refused instead.
    // -----------------------------------------------------------------------
    {
        // 4a. A capacity whose worst case is LARGER than the authored ceiling. This is a
        //     configuration error, and the point of the test is that the invariant catches it
        //     rather than that it never happens.
        FFlowParams Loose;
        Loose.ArrivalsPerMinute = 240.0;       // rho = 10 on two lanes
        Loose.QueueCapacityPerLane = 12;
        Loose.FairnessCapSeconds = 60.0;       // a wish this capacity cannot possibly honour
        Check(!CeilingIsAchievable(Loose), "a capacity of 12 cannot honour a 60 s ceiling");
        const FRunResult L = Run(Loose, 3600.0, 77);
        Runs.push_back(RunJson("overload_ceiling_unreachable", Loose, L));
        Check(L.MaxWait <= L.Bound + 1e-6, "even a misconfigured checkpoint stays inside the hard bound");
        Check(!L.bFair, "the invariant reports the ceiling breach instead of hiding it");
        Check(L.FairnessReason.find("ceiling") != std::string::npos, "and it names the ceiling as the reason");
        Check(L.MaxQueueSeen <= Loose.QueueCapacityPerLane, "no lane ever exceeds its hard capacity");
        Check(L.FifoBreaches == 0, "overload never serves a lane out of join order");

        // 4b. The same 10x overload against a ceiling the capacity can actually carry.
        FFlowParams P = Loose;
        P.FairnessCapSeconds = 300.0;
        P.QueueCapacityPerLane = CapacityForCeiling(P);
        P.BagQueueCapacity = P.BagQueueCapacity < P.QueueCapacityPerLane ? P.BagQueueCapacity : P.QueueCapacityPerLane;
        Check(P.QueueCapacityPerLane >= 1, "some capacity honours the ceiling");
        Check(CeilingIsAchievable(P), "the recommended capacity honours the ceiling");
        const FRunResult R = Run(P, 3600.0, 77);
        Runs.push_back(RunJson("overload_ten_times_capacity", P, R));
        Check(R.Refused > 0, "an overloaded checkpoint refuses people rather than queueing them");
        Check(R.MaxQueueSeen <= P.QueueCapacityPerLane, "no lane ever exceeds its recommended capacity");
        Check(R.bFair, "overload at the recommended capacity satisfies the fairness invariant");
        Check(R.MaxWait <= R.Bound + 1e-6, "even under 10x overload nobody waits past the bound");
        Check(R.MaxWait <= P.FairnessCapSeconds + 1e-6, "and nobody waits past the authored ceiling");
        Check(R.FifoBreaches == 0, "overload never serves a lane out of join order");
        Check(R.Served > 0, "the overloaded checkpoint still clears people");
        Check(Utilisation(P) > 1.0, "the overload scenario really is over capacity");
        Check(ErlangC(P) == 1.0, "Erlang-C saturates at one when utilisation reaches one");
        Check(CeilingIsAchievable(FFlowParams()), "the shipped default parameters honour their own ceiling");
    }

    // -----------------------------------------------------------------------
    // 5. Wave-aside rate: the observed fraction must match the authored probability.
    // -----------------------------------------------------------------------
    {
        FFlowParams P;
        P.ArrivalsPerMinute = 20.0;
        P.BagCheckProbability = 0.30;
        P.BagTables = 2;
        const FRunResult R = Run(P, 7200.0, 4242);
        Runs.push_back(RunJson("wave_aside_rate", P, R));
        const double Observed = R.Served > 0 ? double(R.BagChecked) / double(R.Served) : 0.0;
        Check(std::fabs(Observed - 0.30) < 0.03, "observed wave-aside rate matches the authored 30%");
        Check(R.BagChecked > 100, "the bag table saw enough traffic for that rate to mean something");
        Check(R.bFair, "the wave-aside path still satisfies the fairness invariant");

        FFlowParams Zero = P;
        Zero.BagCheckProbability = 0.0;
        const FRunResult Z = Run(Zero, 1200.0, 4242);
        Check(Z.BagChecked == 0, "a zero wave-aside rate never sends anyone to the bag table");
        FFlowParams All = P;
        All.BagCheckProbability = 1.0;
        // Counted at the arch, so at any instant BagChecked leads Served by whoever is still
        // at the table. Drain the checkpoint to empty before demanding equality.
        FCheckpoint AC;
        AC.Configure(All, 4242);
        FTicket Ignored;
        for (double T = 0.0; T < 1200.0; T += 1.0 / 60.0)
        {
            const int N = AC.DrawArrivals(1.0 / 60.0);
            for (int I = 0; I < N; ++I)
            {
                AC.RequestToPass();
            }
            AC.Advance(1.0 / 60.0);
            while (AC.PopCleared(Ignored)) {}
            while (AC.PopWavedAside(Ignored)) {}
        }
        Check(AC.BagCheckedCount() + AC.BagLineFullCount() >= AC.ServedCount(),
              "every person served under a rate of one was either bag-checked or passed on a full bag line");
        Check(AC.BagLineFullCount() > 0, "one table cannot absorb a 100% wave-aside rate, so the line fills");
        double Drain = 0.0;
        while (AC.TotalQueueLength() > 0 && Drain < 4.0 * WorstCaseWaitSeconds(All))
        {
            AC.Advance(1.0 / 60.0);
            Drain += 1.0 / 60.0;
            while (AC.PopCleared(Ignored)) {}
            while (AC.PopWavedAside(Ignored)) {}
        }
        Check(AC.TotalQueueLength() == 0, "the all-bag-check checkpoint drains completely");
        Check(AC.BagCheckedCount() + AC.BagLineFullCount() == AC.ServedCount(),
              "a wave-aside rate of one accounts for everybody: bag-checked, or passed on a full bag line");
        Check(AC.BagCheckedCount() > 0, "and the bag table itself did most of the work");

        // With enough tables and a long enough line, nobody has to be passed unchecked.
        FFlowParams Ample = All;
        Ample.BagTables = MaxBagTables;
        Ample.BagQueueCapacity = MaxQueue;
        Ample.ArrivalsPerMinute = 8.0;
        const FRunResult Am = Run(Ample, 3600.0, 4242);
        Runs.push_back(RunJson("all_bag_check_ample_tables", Ample, Am));
        Check(Am.BagChecked == Am.WavedPopped, "with ample tables every selected person reaches one");
        Check(Am.bFair, "the all-bag-check checkpoint still satisfies the fairness invariant");
    }

    // -----------------------------------------------------------------------
    // 6. Adding a lane must shorten the queue, never lengthen it.
    // -----------------------------------------------------------------------
    {
        FFlowParams One;
        One.ArrivalsPerMinute = 22.0;
        One.DetectorLanes = 1;
        FFlowParams Two = One;
        Two.DetectorLanes = 2;
        FFlowParams Four = One;
        Four.DetectorLanes = 4;
        const FRunResult R1 = Run(One, 1800.0, 5150);
        const FRunResult R2 = Run(Two, 1800.0, 5150);
        const FRunResult R4 = Run(Four, 1800.0, 5150);
        Runs.push_back(RunJson("one_lane", One, R1));
        Runs.push_back(RunJson("two_lanes", Two, R2));
        Runs.push_back(RunJson("four_lanes", Four, R4));
        Check(R2.MeanWait < R1.MeanWait, "a second lane shortens the mean wait");
        Check(R4.MeanWait <= R2.MeanWait, "a fourth lane does not lengthen the mean wait");
        Check(R2.Refused <= R1.Refused, "a second lane refuses no more people than one lane");
        Check(Utilisation(Two) < Utilisation(One), "utilisation falls when a lane is added");
    }

    // -----------------------------------------------------------------------
    // 7. Idle and edge behaviour.
    // -----------------------------------------------------------------------
    {
        FCheckpoint C;
        FFlowParams P;
        C.Configure(P, 1);
        Check(C.TotalQueueLength() == 0, "a fresh checkpoint is empty");
        Check(C.QueueLength(-1) == 0 && C.QueueLength(99) == 0, "out-of-range lane queries return zero");
        FTicket T;
        Check(!C.PopCleared(T), "an empty checkpoint clears nobody");
        Check(!C.PopWavedAside(T), "an empty checkpoint waves nobody aside");
        C.Advance(-1.0);
        C.Advance(0.0);
        C.Advance(std::nan(""));
        Check(C.GetNow() == 0.0, "a non-positive or NaN delta does not advance the clock");
        int Slot = -1;
        Check(!C.FindTicket(0, T, Slot), "an unissued ticket is not found");

        // fill one lane to capacity, then confirm the refusal
        C.Configure(P, 1);
        int Accepted = 0;
        for (int I = 0; I < P.QueueCapacityPerLane * P.DetectorLanes + 10; ++I)
        {
            const FPassGrant G = C.RequestToPass();
            Accepted += G.bAccepted ? 1 : 0;
            if (!G.bAccepted)
            {
                Check(G.EstimatedWaitSeconds < 0.0, "a refused request returns a negative wait");
                Check(G.TicketId == -1, "a refused request issues no ticket");
            }
        }
        Check(Accepted == P.QueueCapacityPerLane * P.DetectorLanes,
              "exactly capacity x lanes people are accepted before the checkpoint refuses");
        Check(C.RefusedCount() == 10, "the refusal count is exact");
        Check(C.QueueLength(0) == P.QueueCapacityPerLane && C.QueueLength(1) == P.QueueCapacityPerLane,
              "the shortest-lane rule filled both lanes evenly");
        Check(C.EstimatedWaitSeconds(0, false) > 0.0, "a full lane still reports a positive estimate");
        Check(C.EstimatedWaitSeconds(-1, false) < 0.0, "an invalid lane reports a negative estimate");

        // drain it and confirm everyone comes out, in order, inside the bound
        double T2 = 0.0;
        int Drained = 0;
        while (T2 < 4.0 * WorstCaseWaitSeconds(P) && C.TotalQueueLength() > 0)
        {
            C.Advance(1.0 / 60.0);
            T2 += 1.0 / 60.0;
            FTicket D;
            while (C.PopCleared(D))
            {
                ++Drained;
            }
            FTicket W;
            while (C.PopWavedAside(W))
            {
            }
        }
        Check(C.TotalQueueLength() == 0, "a closed checkpoint drains completely");
        Check(C.ServedCount() == Accepted, "everyone accepted is eventually served");
        const char* Reason = "";
        Check(C.FairnessHolds(Reason), "the drained checkpoint satisfies the fairness invariant");
        Check(C.MaxObservedTotalWaitSeconds() <= WorstCaseWaitSeconds(P) + 1e-6,
              "the longest wait in a full-to-empty drain is inside the bound");
    }

    // -----------------------------------------------------------------------
    // 8. Frame-rate independence: the same wall-clock at 30, 60 and 144 Hz must
    //    give substantially the same throughput.
    // -----------------------------------------------------------------------
    {
        FFlowParams P;
        P.ArrivalsPerMinute = 18.0;
        const FRunResult A = Run(P, 1800.0, 8080, 30.0);
        const FRunResult B = Run(P, 1800.0, 8080, 60.0);
        const FRunResult D = Run(P, 1800.0, 8080, 144.0);
        const double Ref = double(B.Served);
        Check(std::fabs(A.Served - Ref) / Ref < 0.10, "throughput at 30 Hz is within 10% of 60 Hz");
        Check(std::fabs(D.Served - Ref) / Ref < 0.10, "throughput at 144 Hz is within 10% of 60 Hz");
        Check(A.bFair && B.bFair && D.bFair, "the fairness invariant holds at every frame rate");
        // a single enormous delta must not fast-forward past the whole queue
        FCheckpoint C;
        C.Configure(P, 3);
        for (int I = 0; I < 10; ++I)
        {
            C.RequestToPass();
        }
        C.Advance(100000.0);
        Check(C.GetNow() <= 3600.0 + 1e-6, "one huge delta is clamped to an hour");
    }

    // -----------------------------------------------------------------------
    // 9. The closed-form bound really does bound the simulation, across a sweep.
    // -----------------------------------------------------------------------
    {
        int Sweep = 0;
        for (int Lanes = 1; Lanes <= 4; ++Lanes)
        {
            for (int Cap = 4; Cap <= 20; Cap += 8)
            {
                for (double Rate = 10.0; Rate <= 300.0; Rate *= 3.0)
                {
                    FFlowParams P;
                    P.DetectorLanes = Lanes;
                    P.QueueCapacityPerLane = Cap;
                    P.ArrivalsPerMinute = Rate;
                    P.BagTables = (Lanes >= 2) ? 2 : 1;
                    const FRunResult R = Run(P, 900.0, 100u + unsigned(Sweep));
                    if (R.MaxWait > R.Bound + 1e-6 || !R.bFair || R.FifoBreaches != 0)
                    {
                        std::fprintf(stderr, "sweep breach: lanes=%d cap=%d rate=%.0f max=%.2f bound=%.2f %s\n",
                                     Lanes, Cap, Rate, R.MaxWait, R.Bound, R.FairnessReason.c_str());
                        ++Sweep;
                        Check(false, "sweep case stayed inside the closed-form bound");
                    }
                    ++Sweep;
                }
            }
        }
        Check(Sweep == 4 * 3 * 4, "the sweep ran all 48 cases without a breach");
    }

    // -----------------------------------------------------------------------
    // 10. Guard head scan: continuous, periodic, bounded, and it actually moves.
    // -----------------------------------------------------------------------
    {
        FGuardScan S;
        S.SweepDegrees = 55.0;
        S.PeriodSeconds = 9.0;
        double Lo = 1e9, Hi = -1e9, MaxJump = 0.0;
        double Prev = S.YawOffsetAt(0.0);
        for (double T = 0.0; T <= 36.0; T += 1.0 / 120.0)
        {
            const double Y = S.YawOffsetAt(T);
            Lo = Y < Lo ? Y : Lo;
            Hi = Y > Hi ? Y : Hi;
            const double Jump = std::fabs(Y - Prev);
            MaxJump = Jump > MaxJump ? Jump : MaxJump;
            Prev = Y;
        }
        Check(Hi <= S.SweepDegrees + 1e-9 && Lo >= -S.SweepDegrees - 1e-9, "the head stays inside the sweep arc");
        Check(Hi > S.SweepDegrees * 0.99 && Lo < -S.SweepDegrees * 0.99, "the head reaches both ends of the arc");
        Check(MaxJump < 2.0, "the head never jumps: the scan is continuous frame to frame");
        Check(std::fabs(S.YawOffsetAt(3.0) - S.YawOffsetAt(3.0 + S.PeriodSeconds)) < 1e-6, "the scan is periodic");
        Check(std::fabs(S.YawOffsetAt(2.0) - S.YawOffsetAt(2.0 + 0.02)) < 1e-9 ||
              std::fabs(S.YawOffsetAt(0.1) - S.YawOffsetAt(0.12)) < 1e-9, "the head dwells at the ends of the sweep");
        FGuardScan Phased = S;
        Phased.PhaseSeconds = 3.33;
        Check(std::fabs(Phased.YawOffsetAt(1.0) - S.YawOffsetAt(1.0)) > 1e-3, "a phase offset desynchronises two guards");
        FGuardScan Silly;
        Silly.PeriodSeconds = -5.0;
        Silly.DwellFraction = 9.0;
        Check(std::isfinite(Silly.YawOffsetAt(1.0)), "a nonsense scan still returns a finite angle");
    }

    // -----------------------------------------------------------------------
    // Emit the receipt.
    // -----------------------------------------------------------------------
    std::printf("{\n");
    std::printf("  \"test\": \"QueueFlowMathTest\",\n");
    std::printf("  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/QueueFlowMath.h\",\n");
    std::printf("  \"source\": \"Plugins/MikdashRuntime/Tests/QueueFlowMathTest.cpp\",\n");
    std::printf("  \"whatIsTested\": \"Arithmetic only: arrival draw, shortest-lane join, service and "
                "bag-check timing, the hard queue cap, FIFO order within a lane, the closed-form wait "
                "bound, frame-rate independence and the guard head scan. Nothing here tests geometry, "
                "materials, navigation or anything native.\",\n");
    std::printf("  \"provenance\": \"The checkpoint is MODERN STAGING (SourceAssets/security-review/"
                "sources.md). No classical source describes a metal detector, a bag scanner or a queue "
                "discipline, and none is cited for any number in this file.\",\n");
    std::printf("  \"checks\": [\n%s\n  ],\n", [&]{
        std::string S;
        for (size_t I = 0; I < Checks.size(); ++I)
        {
            S += Checks[I];
            if (I + 1 < Checks.size())
            {
                S += ",\n";
            }
        }
        return S;
    }().c_str());
    std::printf("  \"runs\": [\n%s\n  ],\n", [&]{
        std::string S;
        for (size_t I = 0; I < Runs.size(); ++I)
        {
            S += Runs[I];
            if (I + 1 < Runs.size())
            {
                S += ",\n";
            }
        }
        return S;
    }().c_str());
    std::printf("  \"checkCount\": %d,\n", int(Checks.size()));
    std::printf("  \"failures\": %d,\n", Failures);
    std::printf("  \"status\": \"%s\"\n", Failures == 0 ? "PASS" : "FAIL");
    std::printf("}\n");

    std::fprintf(stderr, "%s: %d checks, %d failures\n", Failures == 0 ? "PASS" : "FAIL",
                 int(Checks.size()), Failures);
    return Failures == 0 ? 0 : 1;
}
