#include "ServiceScheduleMath.h"
#include <cstdlib>
#include <iostream>
#include <limits>
using namespace MikdashService;

static int Passed = 0;
static void Check(bool Good, const char* Why)
{
    if (!Good) { std::cerr << "FAILED: " << Why << '\n'; std::exit(1); }
    ++Passed;
}

int main()
{
    const double NaN = std::numeric_limits<double>::quiet_NaN();
    const double Inf = std::numeric_limits<double>::infinity();
    Anchors A;
    LampSchedule Lamps;
    DwellTimes Dwell;
    const double Speed = 90.0;

    // ---- geometry constants match the measured floors --------------------
    Check(KodeshLineX == -5600.0 && HeikhalEastX == -3600.0, "Heikhal envelope constants");
    Check(FloorZ == 925.0 && StoneTopZ == 975.0, "floor and stone top heights");

    // ---- zone classification --------------------------------------------
    Check(ZoneOf({-4650, 0, FloorZ}) == Zone::Heikhal, "golden altar is in the Heikhal");
    Check(ZoneOf({-5330, 315.176, FloorZ}) == Zone::Heikhal, "menorah is in the Heikhal");
    Check(ZoneOf({-3450, 0, FloorZ}) == Zone::Doorway, "doorway centre");
    Check(ZoneOf({-3450, 300, FloorZ}) == Zone::Outside, "doorway is narrower than the hall");
    Check(ZoneOf({-3200, 0, FloorZ}) == Zone::Ulam, "Ulam approach");
    Check(ZoneOf({-6100, 0, FloorZ}) == Zone::Kodesh, "inner room classified separately");
    Check(ZoneOf({-5650, 0, FloorZ}) == Zone::ParochesGap, "paroches gap is its own zone");
    Check(ZoneOf({-5650, 300, FloorZ}) == Zone::Outside, "the gap is only 175 cm either side");
    Check(ZoneOf({NaN, 0, FloorZ}) == Zone::Outside, "non-finite point is never inside");
    Check(ZoneOf({-8000, 0, FloorZ}) == Zone::Outside, "beyond the House");

    // ---- the scenario gate ----------------------------------------------
    Check(ZonePermitted(Scenario::OrdinaryDay, Zone::Heikhal), "ordinary day permits the Heikhal");
    Check(!ZonePermitted(Scenario::OrdinaryDay, Zone::Kodesh), "ordinary day never permits the inner room");
    Check(!ZonePermitted(Scenario::OrdinaryDay, Zone::ParochesGap), "ordinary day never permits the gap");
    Check(ZonePermitted(Scenario::YomKippur, Zone::Kodesh), "the Yom Kippur scenario permits it");
    Check(ZonePermitted(Scenario::YomKippur, Zone::Heikhal), "Yom Kippur keeps the daily zones too");
    Check(!KindPermitted(Scenario::OrdinaryDay, StationKind::InnerEntry), "inner station gated by scenario");
    Check(KindPermitted(Scenario::YomKippur, StationKind::InnerEntry), "inner station allowed when on");
    Check(KindPermitted(Scenario::OrdinaryDay, StationKind::Lamp), "lamp station always allowed");

    // ---- the hard boundary at the paroches line --------------------------
    Refusal Why = Refusal::None;
    Check(!SegmentPermitted(Scenario::OrdinaryDay, {-5400, 0, FloorZ}, {-5900, 0, FloorZ}, Why)
        && Why == Refusal::CrossesKodeshLine, "a leg through the paroches is refused");
    Check(!SegmentPermitted(Scenario::OrdinaryDay, {-5400, 0, FloorZ}, {KodeshLineX, 0, FloorZ}, Why)
        && Why == Refusal::CrossesKodeshLine, "reaching the line exactly is refused, not just crossing");
    Check(SegmentPermitted(Scenario::OrdinaryDay, {-5400, 0, FloorZ}, {-5590, 0, FloorZ}, Why),
        "just east of the line is still the Heikhal");
    Check(SegmentPermitted(Scenario::YomKippur, {-5400, 0, FloorZ}, {-6100, 0, FloorZ}, Why),
        "the Yom Kippur scenario permits the same leg");
    Check(!SegmentPermitted(Scenario::YomKippur, {-5400, 300, FloorZ}, {-6100, 300, FloorZ}, Why)
        && Why == Refusal::OutsideReviewedEnvelope, "even on Yom Kippur it must pass through the gap");
    Check(SegmentPermitted(Scenario::OrdinaryDay, {-3200, 0, FloorZ}, {-3200, 480, FloorZ}, Why),
        "the Ulam really is 500 cm to either side");
    Check(!SegmentPermitted(Scenario::OrdinaryDay, {-3200, 0, FloorZ}, {-3200, 620, FloorZ}, Why)
        && Why == Refusal::OutsideReviewedEnvelope, "a leg that leaves the reviewed floor is refused");
    Check(!SegmentPermitted(Scenario::OrdinaryDay, {-4000, 400, FloorZ}, {-3200, 400, FloorZ}, Why)
        && Why == Refusal::OutsideReviewedEnvelope,
        "a corner cut through the doorway wall is refused even though both ends are inside");
    Check(!SegmentPermitted(Scenario::OrdinaryDay, {NaN, 0, FloorZ}, {-3200, 0, FloorZ}, Why)
        && Why == Refusal::BadGeometry, "non-finite leg fails closed");
    Check(!SegmentPermitted(Scenario::OrdinaryDay, {-4000, 0, FloorZ}, {Inf, 0, FloorZ}, Why)
        && Why == Refusal::BadGeometry, "infinite leg fails closed");

    // ---- the measured menorah anchors ------------------------------------
    Check(std::fabs(A.LampAt(3).Y - A.MenorahCentreY) < 1e-9, "the centre lamp sits on the menorah axis");
    Check(A.LampAt(0).Y < A.LampAt(6).Y, "lamp 0 is north of lamp 6");
    Check(std::fabs(A.LampAt(6).Y - A.LampAt(0).Y - 2.0 * A.BranchHalfSpanY) < 1e-9, "lamps evenly span the branches");
    Check(A.StoneStand.X > A.MenorahX, "the three-step stone is east of the menorah");
    Check(ZoneOf(A.StoneStand) == Zone::Heikhal && ZoneOf(A.GoldenAltar) == Zone::Heikhal,
        "the stone and the golden altar are both inside the Heikhal");
    for (std::size_t K = 0; K < LampCount; ++K)
    {
        Check(A.StandForLamp(K).Y >= A.StoneMinY && A.StandForLamp(K).Y <= A.StoneMaxY,
            "the stand point stays on the stone footprint");
        Check(std::fabs(A.StandForLamp(K).Z - StoneTopZ) < 1e-9, "lamps are tended from the stone top");
        Check(A.LampAt(K).X == A.MenorahX, "lamps sit on the menorah axis in X");
    }

    // ---- the ordinary-day sequence ---------------------------------------
    Plan P;
    Check(BuildMenorahSequence(Scenario::OrdinaryDay, A, Lamps, Dwell, P, Why), "ordinary sequence builds");
    Check(P.Count > 0 && P.Count <= MaxStations, "sequence fits the fixed store");
    Check(LampsTended(P) == LampCount, "all seven lamps are tended");
    std::size_t Bad = 0;
    Check(ValidatePlan(Scenario::OrdinaryDay, P, Speed, DefaultMinLoopSeconds, DefaultMaxLoopSeconds, Bad)
        == Refusal::None, "the ordinary-day plan validates end to end");
    for (std::size_t I = 0; I < P.Count; ++I)
    {
        Check(P.Items[I].Stand.X > KodeshLineX, "no ordinary-day station reaches the paroches line");
        Check(P.Items[I].Kind != StationKind::InnerEntry && P.Items[I].Kind != StationKind::InnerExit,
            "no inner station on an ordinary day");
        Check(P.Items[I].Action != nullptr && P.Items[I].Action[0] != '\0', "every station has plain-language text");
    }
    // five, then out, then two: the order of Temidin uMusafin 3:17.
    std::size_t FirstRun = 0, SecondRun = 0, Withdrawals = 0;
    bool AfterWithdraw = false;
    for (std::size_t I = 0; I < P.Count; ++I)
    {
        if (P.Items[I].Kind == StationKind::WithdrawOutside) { AfterWithdraw = true; ++Withdrawals; }
        else if (P.Items[I].Kind == StationKind::Lamp) { (AfterWithdraw ? SecondRun : FirstRun) += 1; }
    }
    Check(FirstRun == 5 && SecondRun == 2 && Withdrawals == 1, "five lamps, a withdrawal, then two lamps");
    // the golden altar comes after the two remaining lamps (Abaye's order).
    std::size_t LastLamp = 0, AltarAt = 0;
    for (std::size_t I = 0; I < P.Count; ++I)
    {
        if (P.Items[I].Kind == StationKind::Lamp) LastLamp = I;
        if (P.Items[I].Kind == StationKind::GoldenAltar) AltarAt = I;
    }
    Check(AltarAt > LastLamp, "the incense station follows the last lamp");

    const double Loop = PlanLoopSeconds(P, Speed);
    Check(Loop >= 180.0 && Loop <= 360.0, "the loop lands in the commissioned three to six minutes");
    Check(std::fabs(Loop - (PlanWalkSeconds(P, Speed) + PlanDwellSeconds(P))) < 1e-9, "loop = walking + dwelling");
    Check(PlanWalkSeconds(P, 0.0) == 0.0 && PlanWalkSeconds(P, NaN) == 0.0, "bad speed yields no walking time");

    // ---- the Yom Kippur scenario -----------------------------------------
    Plan YK;
    Check(BuildMenorahSequence(Scenario::YomKippur, A, Lamps, Dwell, YK, Why), "Yom Kippur sequence builds");
    Check(YK.Count == P.Count + 2, "it adds exactly an entry and an exit, nothing else");
    Check(LampsTended(YK) == LampCount, "the daily lamp service is still performed that day");
    Check(ValidatePlan(Scenario::YomKippur, YK, Speed, 180.0, 420.0, Bad) == Refusal::None,
        "the Yom Kippur plan validates under its own window");
    Check(ValidatePlan(Scenario::OrdinaryDay, YK, Speed, 180.0, 420.0, Bad) == Refusal::ScenarioForbidsStation,
        "the same plan is refused the moment the scenario flag is off");
    bool SawInner = false;
    for (std::size_t I = 0; I < YK.Count; ++I)
        if (YK.Items[I].Stand.X <= KodeshLineX) SawInner = true;
    Check(SawInner, "the Yom Kippur plan really does pass the line");

    // ---- validation refuses bad plans ------------------------------------
    Plan Tamper = P;
    Tamper.Items[4].Stand.X = -5900.0;
    Check(ValidatePlan(Scenario::OrdinaryDay, Tamper, Speed, 180.0, 360.0, Bad) == Refusal::CrossesKodeshLine
        && Bad == 4, "a station moved past the line is caught and named");
    Tamper = P; Tamper.Items[2].Stand.Z = 1400.0;
    Check(ValidatePlan(Scenario::OrdinaryDay, Tamper, Speed, 180.0, 360.0, Bad) == Refusal::BadFloorHeight,
        "a floating station is refused");
    Tamper = P; Tamper.Items[2].Stand.Y = 900.0;
    Check(ValidatePlan(Scenario::OrdinaryDay, Tamper, Speed, 180.0, 360.0, Bad) == Refusal::OutsideReviewedEnvelope,
        "a station outside the hall is refused");
    Tamper = P; Tamper.Items[3].DwellSeconds = NaN;
    Check(ValidatePlan(Scenario::OrdinaryDay, Tamper, Speed, 180.0, 360.0, Bad) == Refusal::BadGeometry,
        "a non-finite dwell is refused");
    Tamper = P; Tamper.Items[3].LampIndex = 99;
    Check(ValidatePlan(Scenario::OrdinaryDay, Tamper, Speed, 180.0, 360.0, Bad) == Refusal::BadLampGrouping,
        "an impossible lamp index is refused");
    Tamper = P; Tamper.Count = 1;
    Check(ValidatePlan(Scenario::OrdinaryDay, Tamper, Speed, 180.0, 360.0, Bad) == Refusal::EmptySequence,
        "a one-station plan is not a sequence");
    Check(ValidatePlan(Scenario::OrdinaryDay, P, Speed, 180.0, 200.0, Bad) == Refusal::DurationOutOfWindow,
        "a loop outside the requested window is refused");
    Check(ValidatePlan(Scenario::OrdinaryDay, P, -5.0, 180.0, 360.0, Bad) == Refusal::BadGeometry,
        "a negative walk speed is refused");
    Tamper = P; Tamper.Items[Tamper.Count - 1].Stand = A.GoldenAltar;
    Check(ValidatePlan(Scenario::OrdinaryDay, Tamper, Speed, 180.0, 360.0, Bad) == Refusal::SequenceNotClosed,
        "a sequence that does not end where it began is refused, so the interval restart cannot teleport");
    Check(std::fabs(P.Items[0].Stand.X - P.Items[P.Count - 1].Stand.X) < 1e-9
        && std::fabs(P.Items[0].Stand.Y - P.Items[P.Count - 1].Stand.Y) < 1e-9,
        "the authored sequence really is closed");

    LampSchedule BadLamps; BadLamps.FirstGroup = 4; BadLamps.SecondGroup = 2;
    Plan Never;
    Check(!BuildMenorahSequence(Scenario::OrdinaryDay, A, BadLamps, Dwell, Never, Why)
        && Why == Refusal::BadLampGrouping && Never.Count == 0,
        "the two groups must account for all seven lamps");
    DwellTimes BadDwell; BadDwell.AltarSeconds = -1.0;
    Check(!BuildMenorahSequence(Scenario::OrdinaryDay, A, Lamps, BadDwell, Never, Why),
        "a negative dwell is refused before anything is built");

    // ---- the runner -------------------------------------------------------
    Sequencer Run;
    Check(!Run.IsReady() && Run.Why() == Refusal::NotConfigured, "unconfigured runner fails closed");
    Check(Run.CurrentLamp() == 0, "an unconfigured runner tends no lamp");
    Check(!Run.Tick(1.0, false), "an unconfigured runner does not advance");
    Check(!Run.Configure(Scenario::OrdinaryDay, P, Speed, -1.0), "a negative interval is refused");
    Check(!Run.Configure(Scenario::OrdinaryDay, YK, Speed, 60.0), "the runner applies the scenario gate too");
    Check(Run.Configure(Scenario::OrdinaryDay, P, Speed, 60.0), "the ordinary-day runner configures");
    Check(Run.Where().State == Phase::Dwelling && Run.Where().Index == 0, "it starts standing at station 0");
    Check(std::fabs(Run.LoopSeconds() - Loop) < 1e-9, "the runner reports the same loop length");

    Check(!Run.Tick(NaN, false) && !Run.Tick(-1.0, false), "a bad clock step changes nothing");
    const std::size_t IndexBefore = Run.Where().Index;
    Check(Run.Tick(30.0, false, true) && Run.Where().Index == IndexBefore, "a paused tick advances nothing");

    // a blocked leg holds; it never teleports and it is counted.
    Run.Tick(Dwell.ApproachSeconds + 0.5, false);          // finish dwelling, start walking
    Check(Run.Where().State == Phase::Walking, "it began walking after the first dwell");
    const Point3 HeldAt = Run.CurrentStand();
    Check(Run.Tick(20.0, true), "a blocked tick is accepted");
    Check(Run.Where().State == Phase::Held && Run.Where().BlockedNow, "a blocked leg holds");
    Check(Run.Where().BlockedLegs == 1 && Run.Where().HeldSeconds >= 20.0, "the hold is recorded");
    Check(Run.CurrentStand().X == HeldAt.X && Run.CurrentStand().Y == HeldAt.Y,
        "a held body does not move a centimetre");
    Check(Run.Tick(60.0, true) && Run.Where().BlockedLegs == 1, "one leg blocked for longer is still one leg");
    Check(Run.Tick(1.0, false) && Run.Where().State != Phase::Held, "it resumes when the leg clears");

    // every position the runner ever reports must satisfy the boundary.
    Sequencer Walk;
    Check(Walk.Configure(Scenario::OrdinaryDay, P, Speed, 45.0), "second runner configures");
    int LampSeen[LampCount] = {};
    bool SawWaiting = false;
    for (int Step = 0; Step < 20000; ++Step)
    {
        Walk.Tick(0.05, false);
        const Point3 At = Walk.CurrentStand();
        Check(At.X > KodeshLineX, "the body never reaches the paroches line on an ordinary day");
        Check(ZoneOf(At) != Zone::Outside, "the body never leaves the reviewed envelope");
        Check(ZonePermitted(Scenario::OrdinaryDay, ZoneOf(At)), "the body never enters a gated zone");
        const int Lamp = Walk.CurrentLamp();
        if (Lamp > 0) LampSeen[Lamp - 1] = 1;
        if (Walk.Where().State == Phase::Waiting) SawWaiting = true;
        Check(Walk.CurrentAction() != nullptr && Walk.CurrentAction()[0] != '\0', "there is always something to say");
    }
    int Distinct = 0;
    for (int V : LampSeen) Distinct += V;
    Check(Distinct == static_cast<int>(LampCount), "all seven lamps were reported over the run");
    Check(SawWaiting, "the interval between sequences is observed");
    Check(Walk.Where().CompletedLoops >= 2, "the sequence repeats on its interval");
    Check(Walk.Where().BlockedLegs == 0 && Walk.Where().HeldSeconds == 0.0, "an unobstructed run holds nowhere");

    // a zero interval restarts immediately rather than waiting forever.
    Sequencer Immediate;
    Check(Immediate.Configure(Scenario::OrdinaryDay, P, Speed, 0.0), "zero interval configures");
    for (int Step = 0; Step < 16000; ++Step) Immediate.Tick(0.05, false);
    Check(Immediate.Where().CompletedLoops >= 2, "a zero interval still loops");
    Check(Immediate.Where().State != Phase::Waiting, "a zero interval never parks in Waiting");

    // one enormous step must not skip stations or overrun the boundary.
    Sequencer Coarse;
    Check(Coarse.Configure(Scenario::OrdinaryDay, P, Speed, 30.0), "coarse runner configures");
    Check(Coarse.Tick(5000.0, false), "one very large step is accepted");
    Check(Coarse.CurrentStand().X > KodeshLineX, "a large step cannot escape the boundary");
    Check(Coarse.Where().CompletedLoops >= 1, "a large step completes whole sequences");

    // the Yom Kippur runner really does pass the line, and only then.
    Sequencer Inner;
    Check(Inner.Configure(Scenario::YomKippur, YK, Speed, 30.0, 180.0, 420.0), "Yom Kippur runner configures");
    bool WentInside = false;
    for (int Step = 0; Step < 20000; ++Step)
    {
        Inner.Tick(0.05, false);
        const Point3 At = Inner.CurrentStand();
        Check(ZoneOf(At) != Zone::Outside, "the Yom Kippur body stays in the reviewed envelope");
        if (At.X <= KodeshLineX) WentInside = true;
    }
    Check(WentInside, "the Yom Kippur scenario, and only it, passes the paroches");

    std::cout << "Service schedule: " << Passed
              << " checks passed (zones, scenario gate, paroches boundary, measured menorah anchors, "
                 "five-then-two lamp order, three-to-six-minute loop, blocked-leg hold, interval repeat)\n";
    return 0;
}
