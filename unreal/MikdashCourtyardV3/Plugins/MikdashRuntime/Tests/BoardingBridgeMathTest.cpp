#define _CRT_SECURE_NO_WARNINGS

// Standalone test for BoardingBridgeMath.h, the arithmetic behind
// AMikdashTransitBoardingBridge. No Unreal, no engine headers.
//
//   cl /std:c++17 /EHsc /W4 /WX /I<...>/Public BoardingBridgeMathTest.cpp
//   BoardingBridgeMathTest.exe <optional path to a JSON receipt>
//
// It also includes TransitMath.h, because the photographer COUNT the bridge honours comes
// from AMikdashTransit::SuggestPhotographerCount, which is MikdashTransit::PhotographerCount.
// The 22 percent claim is measured against that function, not a copy of it.
//
// Every check goes through Check(), live in debug AND release builds.

#include "BoardingBridgeMath.h"
#include "TransitMath.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using namespace MikdashBoardingBridge;

static long long CheckCount = 0;
static void CheckImpl(bool Condition, const char* Text, int Line)
{
    ++CheckCount;
    if (!Condition)
    {
        std::fprintf(stderr, "FAIL line %d: %s\n", Line, Text);
        std::exit(1);
    }
}
#define Check(X) CheckImpl(!!(X), #X, __LINE__)

static bool Near(double A, double B, double Tolerance = 1e-9) { return std::abs(A - B) <= Tolerance; }

static std::vector<std::pair<std::string, std::string>> Facts;
static void Fact(const std::string& Key, double Value)
{
    char Buffer[64];
    std::snprintf(Buffer, sizeof(Buffer), "%.6f", Value);
    Facts.emplace_back(Key, Buffer);
}
static void FactInt(const std::string& Key, long long Value) { Facts.emplace_back(Key, std::to_string(Value)); }

static const double NaNValue = std::numeric_limits<double>::quiet_NaN();
static const uint32_t BaseSeed = 20260908u;

// Deterministic pseudo-random stream for the simulations, independent of the header's hash.
struct Rng
{
    uint64_t State;
    explicit Rng(uint64_t Seed) : State(Seed * 6364136223846793005ULL + 1442695040888963407ULL) {}
    double Unit()
    {
        State = State * 6364136223846793005ULL + 1442695040888963407ULL;
        return static_cast<double>(State >> 11) * (1.0 / 9007199254740992.0);
    }
    double Range(double Lo, double Hi) { return Lo + (Hi - Lo) * Unit(); }
    int Int(int Lo, int Hi) { return Lo + static_cast<int>(Unit() * (Hi - Lo + 1)); }
};

// ---------------------------------------------------------------------------

static void WindowChecks()
{
    for (double D = 0.0; D <= 60.0; D += 0.25)
    {
        const Window W = DwellWindow(D);
        if (D < MinUsableDwellSeconds)
        {
            Check(!W.bUsable);
            continue;
        }
        Check(W.bUsable);
        Check(W.AlightEnd > 0.0 && W.AlightEnd <= W.BoardStart);
        Check(W.BoardStart < W.Deadline);
        Check(W.Deadline <= D - 1.0 + 1e-12);
        Check(Near(W.Dwell, D));
    }
    Check(!DwellWindow(NaNValue).bUsable);
    Check(!DwellWindow(std::numeric_limits<double>::infinity()).bUsable);
    Check(!DwellWindow(-5.0).bUsable);
    Check(!DwellWindow(30.0, -1.0).bUsable);
    Check(!DwellWindow(30.0, NaNValue).bUsable);
    // A margin that eats the boarding phase makes the window unusable rather than negative.
    Check(!DwellWindow(10.0, 6.0).bUsable);
    const Window W = DwellWindow(30.0, 1.0);
    Check(Near(W.AlightEnd, 13.5) && Near(W.BoardStart, 13.5) && Near(W.Deadline, 29.0));
    std::printf("window: alighting ends at %.1f of a 30 s dwell, boarding deadline %.1f s, dwells under %.0f s refused\n",
                W.AlightEnd, W.Deadline, MinUsableDwellSeconds);
}

static void SizingChecks()
{
    Check(DoorThroughput(0.0, 2, 0.8) == 0);
    Check(DoorThroughput(NaNValue, 2, 0.8) == 0);
    Check(DoorThroughput(8.0, 0, 0.8) == 0);
    Check(DoorThroughput(8.0, 2, 0.0) == 0);
    Check(DoorThroughput(8.0, 1, 0.8) == 10);
    Check(DoorThroughput(8.0, 2, 0.8) == 20);

    Rng R(11);
    long long Sized = 0, Refused = 0, MaxAdmitted = 0;
    for (int Trial = 0; Trial < 20000; ++Trial)
    {
        const double D = R.Range(2.0, 45.0);
        const Window W = DwellWindow(D);
        const int Requested = R.Int(0, 80);
        const int Doors = R.Int(1, 4);
        const double PerPerson = R.Range(0.5, 1.5);
        const int MaxPer = R.Int(1, 60);
        const int Pool = R.Int(0, 300);
        const int MinGroup = R.Int(1, 3);
        const bool bAlighting = R.Unit() < 0.5;
        const int N = GroupSizeForDwell(Requested, W, bAlighting, Doors, PerPerson, MaxPer, Pool, MinGroup);
        Check(N >= 0);
        Check(N <= Requested && N <= MaxPer && N <= Pool);
        Check(N == 0 || N >= MinGroup);
        if (!W.bUsable || Requested <= 0 || Pool <= 0) Check(N == 0);
        if (N > 0)
        {
            // The last admitted person's door slot lies strictly inside the phase.
            const double Phase = bAlighting ? W.AlightEnd : (W.Deadline - W.BoardStart);
            const int LastSlot = (N - 1) / Doors;
            Check(LastSlot * PerPerson < Phase);
            ++Sized;
            MaxAdmitted = std::max<long long>(MaxAdmitted, N);
        }
        else ++Refused;
    }
    // The default configuration: a 20-40 s rail dwell with a request of 22-70.
    const Window Rail = DwellWindow(20.0);
    Check(GroupSizeForDwell(70, Rail, false, 2, 0.8, 40, 240) == 24);
    Check(GroupSizeForDwell(70, Rail, true, 2, 0.8, 40, 240) == 22);
    const Window Bus = DwellWindow(14.0);
    Check(GroupSizeForDwell(26, Bus, false, 1, 0.8, 40, 240) == 8);
    Check(GroupSizeForDwell(26, Bus, true, 1, 0.8, 40, 240) == 7);
    // Thin pool: a request of 20 with 3 figures left gives 3, with a minimum of 4 gives none.
    Check(GroupSizeForDwell(20, Rail, false, 2, 0.8, 40, 3, 1) == 3);
    Check(GroupSizeForDwell(20, Rail, false, 2, 0.8, 40, 3, 4) == 0);
    FactInt("sizing.trials", 20000);
    FactInt("sizing.groupsSized", Sized);
    FactInt("sizing.maxAdmitted", MaxAdmitted);
    std::printf("sizing: %lld of 20000 random requests sized, %lld refused, largest admitted group %lld, every door slot inside its phase\n",
                Sized, Refused, MaxAdmitted);
}

static void ConvergeChecks()
{
    Rng R(23);
    long long Groups = 0, People = 0, Fitted = 0, NotFitted = 0;
    double LatestArrivalMargin = 1e9;
    for (int Trial = 0; Trial < 6000; ++Trial)
    {
        const double D = R.Range(4.0, 45.0);
        const Window W = DwellWindow(D);
        if (!W.bUsable) continue;
        const int Doors = R.Int(1, 3);
        const double PerPerson = R.Range(0.6, 1.2);
        const int N = GroupSizeForDwell(R.Int(1, 70), W, false, Doors, PerPerson, 40, 240);
        if (N == 0) continue;
        ++Groups;
        const uint32_t Seed = GroupSeed(BaseSeed, Trial % 16, Trial, false);
        double LastArrival = 0.0;
        for (int Member = 0; Member < N; ++Member)
        {
            ++People;
            const double Distance = R.Range(60.0, 3200.0);
            const double Speed = WalkSpeedFor(Seed, Member, 90.0, 130.0);
            Check(Speed >= 90.0 && Speed <= 130.0);
            const ConvergePlan Plan = ConvergeSchedule(Member, Distance, Speed, W, Doors, PerPerson);
            if (!Plan.bFits)
            {
                ++NotFitted;
                // The only legal reasons not to fit: too far to arrive in time, or beyond the walk bound.
                Check(Distance > MaxWalkCm || Distance / Speed > W.Deadline);
                continue;
            }
            ++Fitted;
            // THE claim: nobody arrives after the deadline, nobody arrives before boarding opens,
            // nobody departs before the doors opened, and the walk takes exactly distance/speed.
            Check(Plan.ArriveAt <= W.Deadline);
            Check(Plan.ArriveAt >= W.BoardStart - 1e-9);
            Check(Plan.DepartAt >= 0.0);
            Check(Near(Plan.ArriveAt - Plan.DepartAt, Distance / Speed, 1e-9));
            LastArrival = std::max(LastArrival, Plan.ArriveAt);
        }
        LatestArrivalMargin = std::min(LatestArrivalMargin, W.Deadline - LastArrival);
        Check(LastArrival <= W.Deadline);
    }
    Check(Groups > 1000 && Fitted > 0 && NotFitted > 0);
    Check(LatestArrivalMargin >= 0.0);

    // Theorem the bridge relies on: every member of a SIZED group whose walk is no longer
    // than the alighting phase fits, so a gather point within BoardStart * speed of the door
    // is always animated.
    long long Guaranteed = 0;
    for (int Trial = 0; Trial < 4000; ++Trial)
    {
        const Window W = DwellWindow(R.Range(4.0, 45.0));
        if (!W.bUsable) continue;
        const int Doors = R.Int(1, 3);
        const double PerPerson = R.Range(0.6, 1.2);
        const int N = GroupSizeForDwell(R.Int(1, 70), W, false, Doors, PerPerson, 40, 240);
        for (int Member = 0; Member < N; ++Member)
        {
            const double Speed = R.Range(90.0, 130.0);
            const double Distance = std::min(MaxWalkCm, R.Range(0.0, W.BoardStart * Speed));
            Check(ConvergeSchedule(Member, Distance, Speed, W, Doors, PerPerson).bFits);
            ++Guaranteed;
        }
    }
    Check(Guaranteed > 10000);

    // Rejections.
    const Window W = DwellWindow(30.0);
    Check(!ConvergeSchedule(0, NaNValue, 100.0, W, 2, 0.8).bFits);
    Check(!ConvergeSchedule(0, 500.0, 0.0, W, 2, 0.8).bFits);
    Check(!ConvergeSchedule(0, 500.0, -1.0, W, 2, 0.8).bFits);
    Check(!ConvergeSchedule(0, MaxWalkCm + 1.0, 100.0, W, 2, 0.8).bFits);
    Check(!ConvergeSchedule(-1, 500.0, 100.0, W, 2, 0.8).bFits);
    Check(!ConvergeSchedule(0, 500.0, 100.0, DwellWindow(2.0), 2, 0.8).bFits);
    Check(!ConvergeSchedule(0, 500.0, 100.0, W, 2, 0.0).bFits);
    // Someone 2900 cm away at 100 cm/s needs 29 s: exactly the deadline of a 30 s dwell fits, 2901 does not.
    Check(ConvergeSchedule(0, 2900.0, 100.0, W, 2, 0.8).bFits);
    Check(!ConvergeSchedule(0, 2901.0, 100.0, W, 2, 0.8).bFits);

    // Alighters step off inside the alighting phase for every sized group.
    long long Alighters = 0;
    for (int Trial = 0; Trial < 4000; ++Trial)
    {
        const Window Wa = DwellWindow(R.Range(4.0, 45.0));
        if (!Wa.bUsable) continue;
        const int Doors = R.Int(1, 3);
        const double PerPerson = R.Range(0.6, 1.2);
        const int N = GroupSizeForDwell(R.Int(1, 70), Wa, true, Doors, PerPerson, 40, 240);
        for (int Member = 0; Member < N; ++Member)
        {
            const double StepOut = AlightStepOutSeconds(Member, Doors, PerPerson);
            Check(StepOut >= 0.4 && StepOut < Wa.AlightEnd + 0.4);
            ++Alighters;
        }
    }
    Check(Alighters > 10000);
    FactInt("converge.groups", Groups);
    FactInt("converge.peopleFitted", Fitted);
    FactInt("converge.peopleNotFitted", NotFitted);
    Fact("converge.smallestDeadlineMarginSeconds", LatestArrivalMargin);
    FactInt("converge.guaranteedFits", Guaranteed);
    FactInt("alighting.stepOutsChecked", Alighters);
    std::printf("converge: %lld groups, %lld boarders scheduled, %lld too far to make the door, smallest margin before doors close %.3f s; %lld guaranteed fits; %lld alighters inside their phase\n",
                Groups, Fitted, NotFitted, LatestArrivalMargin, Guaranteed, Alighters);
}

static void CapChecks()
{
    Check(!AdmitGroup(0, 0));
    Check(!AdmitGroup(-1, 6));
    Check(AdmitGroup(0, 6) && AdmitGroup(5, 6) && !AdmitGroup(6, 6) && !AdmitGroup(7, 6));

    // Sixteen stops served at once, every arrival asking to start two groups (alighting and
    // boarding), each group living for its own random span. The ledger must never exceed the cap.
    Rng R(31);
    const int Cap = 6;
    struct Live { double EndsAt; };
    std::vector<Live> Active;
    long long Admitted = 0, Refused = 0, MaxActive = 0, Events = 0;
    double Now = 0.0;
    for (int Event = 0; Event < 200000; ++Event)
    {
        Now += R.Range(0.05, 3.0);
        // Retire finished groups.
        for (size_t I = 0; I < Active.size();)
        {
            if (Active[I].EndsAt <= Now) { Active[I] = Active.back(); Active.pop_back(); }
            else ++I;
        }
        for (int Direction = 0; Direction < 2; ++Direction)
        {
            ++Events;
            if (AdmitGroup(static_cast<int>(Active.size()), Cap))
            {
                Active.push_back({Now + R.Range(4.0, 50.0)});
                ++Admitted;
            }
            else ++Refused;
            Check(static_cast<int>(Active.size()) <= Cap);
            MaxActive = std::max<long long>(MaxActive, static_cast<long long>(Active.size()));
        }
    }
    Check(MaxActive == Cap);   // the cap binds and is reached, never exceeded
    Check(Refused > 0 && Admitted > 0);
    FactInt("cap.events", Events);
    FactInt("cap.admitted", Admitted);
    FactInt("cap.refused", Refused);
    FactInt("cap.maxConcurrent", MaxActive);
    std::printf("cap: %lld group requests, %lld admitted, %lld refused at the cap, peak concurrency %lld of %d\n",
                Events, Admitted, Refused, MaxActive, Cap);
}

static void PhotographerChecks()
{
    // The count the bridge honours is the transit layer's own draw.
    long long People = 0, Photographers = 0, Draws = 0;
    int MinSeen = 1 << 30, MaxSeen = -1;
    bool Flags[128];
    for (int Stop = 0; Stop < 16; ++Stop)
    {
        for (int Run = 0; Run < 800; ++Run)
        {
            const int Count = 5 + ((Stop * 7 + Run * 13) % 66);   // 5..70
            const int K = MikdashTransit::PhotographerCount(BaseSeed, Stop, Run, Count, 0.22);
            Check(K >= 0 && K <= Count);
            Check(K >= static_cast<int>(std::floor(Count * 0.22)) && K <= static_cast<int>(std::ceil(Count * 0.22)));
            Check(K == MikdashTransit::PhotographerCount(BaseSeed, Stop, Run, Count, 0.22));   // deterministic
            People += Count; Photographers += K; ++Draws;
            MinSeen = std::min(MinSeen, K); MaxSeen = std::max(MaxSeen, K);

            const uint32_t Seed = GroupSeed(BaseSeed, Stop, Run, true);
            const int Marked = SelectPhotographers(Seed, Count, K, Flags);
            Check(Marked == K);
            int Counted = 0;
            for (int I = 0; I < Count; ++I) Counted += Flags[I] ? 1 : 0;
            Check(Counted == K);
            // Determinism of the selection.
            bool Again[128];
            Check(SelectPhotographers(Seed, Count, K, Again) == K);
            for (int I = 0; I < Count; ++I) Check(Again[I] == Flags[I]);
            for (int I = 0; I < Count; ++I)
            {
                const double Hold = PhotographerHoldSeconds(Seed, I);
                Check(Hold >= 4.0 && Hold <= 9.0);
            }
        }
    }
    const double Share = static_cast<double>(Photographers) / static_cast<double>(People);
    Check(Share > 0.21 && Share < 0.23);
    Check(MinSeen >= 1 && MaxSeen <= 16);

    // Different runs pick different people at least sometimes (not a constant selection).
    bool A[64], B[64];
    SelectPhotographers(GroupSeed(BaseSeed, 3, 10, true), 20, 4, A);
    SelectPhotographers(GroupSeed(BaseSeed, 3, 11, true), 20, 4, B);
    bool Differ = false;
    for (int I = 0; I < 20; ++I) Differ = Differ || (A[I] != B[I]);
    Check(Differ);
    // Edge cases.
    Check(SelectPhotographers(1u, 0, 3, A) == 0);
    Check(SelectPhotographers(1u, 5, 0, A) == 0);
    Check(SelectPhotographers(1u, 5, 9, A) == 5);
    Check(SelectPhotographers(1u, 5, 2, nullptr) == 0);
    // Share of zero and one behave.
    Check(MikdashTransit::PhotographerCount(BaseSeed, 1, 1, 30, 0.0) == 0);
    Check(MikdashTransit::PhotographerCount(BaseSeed, 1, 1, 30, 1.0) == 30);
    FactInt("photographers.draws", Draws);
    FactInt("photographers.people", People);
    FactInt("photographers.marked", Photographers);
    Fact("photographers.share", Share);
    std::printf("photographers: %lld draws over %lld people, %lld photographers = %.4f of the group (target 0.22), per-group %d..%d, selection exact and deterministic, holds 4..9 s\n",
                Draws, People, Photographers, Share, MinSeen, MaxSeen);
}

static void ApronChecks()
{
    Apron A;
    Check(!MakeApron({0, 0}, {0, 0}, A));
    Check(!MakeApron({0, 0}, {30, 0}, A));
    Check(!MakeApron({NaNValue, 0}, {300, 0}, A));
    Check(MakeApron({0, 0}, {300, 0}, A));
    Check(Near(A.Out.X, 1.0) && Near(A.Out.Y, 0.0) && Near(A.Side.X, 0.0) && Near(A.Side.Y, 1.0));
    Check(Near(KerbDepth(A, {150, 500}), 150.0));
    Check(Near(KerbDepth(A, {-40, 0}), -40.0));
    Check(OutsideVehicle(A, {60, 0}, 60.0) && !OutsideVehicle(A, {59.9, 0}, 60.0) && !OutsideVehicle(A, {NaNValue, 0}, 60.0));

    // A rotated door: every gather and dispersal point stays outside the vehicle.
    Rng R(41);
    long long Points = 0;
    double MinGatherDepth = 1e9, MinDispersalDepth = 1e9, MaxGatherDepth = 0.0, MaxDispersalRadius = 0.0;
    for (int Trial = 0; Trial < 400; ++Trial)
    {
        const double Yaw = R.Range(-Pi, Pi);
        const Vec2 Door{R.Range(-200000.0, 200000.0), R.Range(-100000.0, 100000.0)};
        const Vec2 Furniture = Door + Vec2{std::cos(Yaw), std::sin(Yaw)} * R.Range(200.0, 700.0);
        Check(MakeApron(Door, Furniture, A));
        const uint32_t Seed = GroupSeed(BaseSeed, Trial % 16, Trial, Trial % 2 == 0);
        for (int Member = 0; Member < 40; ++Member)
        {
            const Vec2 G = GatherPoint(A, Seed, Member, 110.0, 520.0, 450.0);
            const Vec2 P = DispersalPoint(A, Seed, Member, 600.0, 1400.0);
            const double Gd = KerbDepth(A, G), Pd = KerbDepth(A, P);
            Check(OutsideVehicle(A, G, 60.0));
            Check(OutsideVehicle(A, P, 200.0));
            Check(Length(P - Door) <= 1400.0 + 1e-6 && Length(P - Door) >= 600.0 - 1e-6);
            Check(std::abs(Dot(G - Door, A.Side)) <= 450.0 + 25.0 + 1e-6);
            MinGatherDepth = std::min(MinGatherDepth, Gd);
            MaxGatherDepth = std::max(MaxGatherDepth, Gd);
            MinDispersalDepth = std::min(MinDispersalDepth, Pd);
            MaxDispersalRadius = std::max(MaxDispersalRadius, Length(P - Door));
            ++Points;
            // Determinism.
            const Vec2 G2 = GatherPoint(A, Seed, Member, 110.0, 520.0, 450.0);
            const Vec2 P2 = DispersalPoint(A, Seed, Member, 600.0, 1400.0);
            Check(Near(G.X, G2.X) && Near(G.Y, G2.Y) && Near(P.X, P2.X) && Near(P.Y, P2.Y));
        }
    }
    Check(MaxGatherDepth <= 520.0 + 25.0 + 1e-6);

    // Yaw and walking.
    Check(Near(YawToward({0, 0}, {10, 0}), 0.0));
    Check(Near(YawToward({0, 0}, {0, 10}), 90.0));
    Check(Near(YawToward({0, 0}, {-10, 0}), 180.0));
    Check(Near(YawToward({5, 5}, {5, 5}), 0.0));
    const Vec2 Mid = WalkPosition({0, 0}, {1000, 0}, 100.0, 5.0);
    Check(Near(Mid.X, 500.0) && Near(Mid.Y, 0.0));
    const Vec2 End = WalkPosition({0, 0}, {1000, 0}, 100.0, 50.0);
    Check(Near(End.X, 1000.0));
    const Vec2 Start = WalkPosition({0, 0}, {1000, 0}, 100.0, -1.0);
    Check(Near(Start.X, 0.0));
    const Vec2 Same = WalkPosition({7, 7}, {7, 7}, 100.0, 1.0);
    Check(Near(Same.X, 7.0) && Near(Same.Y, 7.0));
    Check(SegmentSampleCount(0.0) == 1 && SegmentSampleCount(100.0) == 4 && SegmentSampleCount(101.0) == 5 && SegmentSampleCount(NaNValue) == 1);
    for (int I = 0; I < 200; ++I)
    {
        Check(FigureScaleFor(BaseSeed, I) >= 0.92 && FigureScaleFor(BaseSeed, I) <= 1.08);
        Check(GarmentIndexFor(BaseSeed, I, 5) >= 0 && GarmentIndexFor(BaseSeed, I, 5) <= 4);
        Check(GarmentIndexFor(BaseSeed, I, 1) == 0);
    }
    FactInt("apron.pointsChecked", Points);
    Fact("apron.minGatherDepthCm", MinGatherDepth);
    Fact("apron.minDispersalDepthCm", MinDispersalDepth);
    std::printf("apron: %lld points on 400 rotated aprons, gather depth %.1f..%.1f cm, dispersal depth >= %.1f cm, radius <= %.1f cm, none inside the vehicle\n",
                Points, MinGatherDepth, MaxGatherDepth, MinDispersalDepth, MaxDispersalRadius);
}

static void DeterminismChecks()
{
    // Same (stop, run, direction): same seed. Any change: a different seed.
    long long Collisions = 0, Pairs = 0;
    for (int Stop = 0; Stop < 16; ++Stop)
    {
        for (int Run = 0; Run < 300; ++Run)
        {
            const uint32_t S = GroupSeed(BaseSeed, Stop, Run, true);
            Check(S == GroupSeed(BaseSeed, Stop, Run, true));
            Check(S != GroupSeed(BaseSeed, Stop, Run, false));
            ++Pairs;
            if (S == GroupSeed(BaseSeed, Stop, Run + 1, true)) ++Collisions;
            if (S == GroupSeed(BaseSeed, (Stop + 1) % 16, Run, true)) ++Collisions;
        }
    }
    Check(Collisions == 0);
    // Negative indices are clamped, not undefined.
    Check(GroupSeed(BaseSeed, -1, -1, true) == GroupSeed(BaseSeed, 0, 0, true));
    // A different base seed yields a different plan; the same base seed yields the same.
    Apron A;
    Check(MakeApron({0, 0}, {0, 400}, A));
    const uint32_t S1 = GroupSeed(BaseSeed, 4, 9, false), S2 = GroupSeed(BaseSeed + 1, 4, 9, false);
    bool AnyDifferent = false;
    for (int Member = 0; Member < 20; ++Member)
    {
        const Vec2 P1 = GatherPoint(A, S1, Member, 110.0, 520.0, 450.0);
        const Vec2 P2 = GatherPoint(A, S2, Member, 110.0, 520.0, 450.0);
        AnyDifferent = AnyDifferent || !Near(P1.X, P2.X) || !Near(P1.Y, P2.Y);
        Check(Near(WalkSpeedFor(S1, Member, 90.0, 130.0), WalkSpeedFor(S1, Member, 90.0, 130.0)));
    }
    Check(AnyDifferent);
    FactInt("determinism.seedPairs", Pairs);
    std::printf("determinism: %lld (stop, run) seeds stable, zero collisions with neighbours, direction and base seed both change the plan\n", Pairs);
}

// ---------------------------------------------------------------------------

static void WriteJson(const char* Path)
{
    std::FILE* File = std::fopen(Path, "wb");
    if (!File)
    {
        std::fprintf(stderr, "could not open %s\n", Path);
        std::exit(2);
    }
    std::fprintf(File, "{\n  \"test\": \"BoardingBridgeMathTest\",\n  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/BoardingBridgeMath.h\",\n");
    std::fprintf(File, "  \"allPassed\": true,\n  \"checksEvaluated\": %lld,\n  \"measurements\": {\n", CheckCount);
    for (size_t I = 0; I < Facts.size(); ++I)
    {
        std::fprintf(File, "    \"%s\": %s%s\n", Facts[I].first.c_str(), Facts[I].second.c_str(), I + 1 < Facts.size() ? "," : "");
    }
    std::fprintf(File, "  }\n}\n");
    std::fclose(File);
}

int main(int argc, char** argv)
{
    WindowChecks();
    SizingChecks();
    ConvergeChecks();
    CapChecks();
    PhotographerChecks();
    ApronChecks();
    DeterminismChecks();
    if (argc > 1) WriteJson(argv[1]);
    std::cout << "PASS " << CheckCount << " checks: dwell window, group sizing, converge timing, concurrency cap, photographers, apron geometry and determinism" << std::endl;
    return 0;
}
