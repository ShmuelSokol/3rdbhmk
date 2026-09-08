// Standalone test for the conversation state machine (ResidentDialogState.h) and for the
// route side it has to cooperate with (ResidentRouteLoop.h): which leg a looping plan is on,
// how a body turns to face a look target or the walker, and how a blocked body recovers.
// Compiled with cl /std:c++17 /W4 /WX and run without Unreal. Asserts stay enabled.
#include "ResidentDialogState.h"
#include "ResidentRouteLoop.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>

namespace
{
MikdashDialog::Aim At(double DistanceCm, double FacingDot)
{
    MikdashDialog::Aim Candidate;
    Candidate.DistanceCm = DistanceCm;
    Candidate.FacingDot = FacingDot;
    Candidate.Valid = true;
    return Candidate;
}

void RangeAndSelectionChecks()
{
    assert(MikdashDialog::InTalkRange(At(0.0, 1.0)));
    assert(MikdashDialog::InTalkRange(At(250.0, 0.5)));
    assert(!MikdashDialog::InTalkRange(At(250.1, 1.0)));
    assert(!MikdashDialog::InTalkRange(At(100.0, 0.49)));
    assert(!MikdashDialog::InTalkRange(At(100.0, -1.0)));   // resident is behind the walker
    assert(!MikdashDialog::InTalkRange(MikdashDialog::Aim()));  // no candidate at all

    MikdashDialog::Aim Broken = At(100.0, 1.0);
    Broken.DistanceCm = std::nan("");
    assert(!MikdashDialog::InTalkRange(Broken));
    Broken = At(100.0, 1.0);
    Broken.FacingDot = std::nan("");
    assert(!MikdashDialog::InTalkRange(Broken));

    // Hysteresis: a talk survives out to the release range and a wider angle, but a new one
    // cannot be started there.
    assert(MikdashDialog::StillHeld(At(300.0, 0.1)));
    assert(!MikdashDialog::InTalkRange(At(300.0, 0.1)));
    assert(!MikdashDialog::StillHeld(At(321.0, 1.0)));
    assert(!MikdashDialog::StillHeld(At(100.0, -0.01)));

    std::vector<MikdashDialog::Aim> Crowd;
    assert(MikdashDialog::BestCandidate(Crowd) == -1);
    Crowd.push_back(At(600.0, 1.0));            // too far
    Crowd.push_back(At(200.0, 0.2));            // not in front
    assert(MikdashDialog::BestCandidate(Crowd) == -1);
    Crowd.push_back(At(240.0, 0.9));            // index 2, qualifies
    assert(MikdashDialog::BestCandidate(Crowd) == 2);
    Crowd.push_back(At(120.0, 0.6));            // index 3, nearer
    assert(MikdashDialog::BestCandidate(Crowd) == 3);
    Crowd.push_back(At(120.0, 0.95));           // index 4, same distance, better facing
    assert(MikdashDialog::BestCandidate(Crowd) == 4);
    Crowd.push_back(At(120.0, 0.7));            // no better than index 4
    assert(MikdashDialog::BestCandidate(Crowd) == 4);
    std::printf("Range and selection: 250 cm / 60 degree gate, hysteresis and nearest-in-front pick checked\n");
}

void ConversationChecks()
{
    MikdashDialog::Conversation Talk;
    const std::size_t Lines = 4;

    // Nothing in range: no prompt, and the talk key does nothing.
    Talk.Observe(MikdashDialog::Aim());
    assert(Talk.GetPhase() == MikdashDialog::Phase::Idle);
    assert(!Talk.ShouldShowPrompt() && !Talk.IsTalking() && !Talk.ShouldResidentHold());
    assert(!Talk.PressTalk(Lines));
    assert(!Talk.PressCancel());

    // In range and in front: the prompt appears but nothing is open yet.
    Talk.Observe(At(180.0, 0.9));
    assert(Talk.GetPhase() == MikdashDialog::Phase::Prompt);
    assert(Talk.ShouldShowPrompt() && !Talk.IsTalking() && !Talk.ShouldResidentHold());

    // First press opens on the first authored line; the resident is asked to hold.
    assert(Talk.PressTalk(Lines));
    assert(Talk.IsTalking() && Talk.ShouldResidentHold() && !Talk.ShouldShowPrompt());
    assert(Talk.LineIndex() == 0 && Talk.AdvanceCount() == 0);

    // Further presses step the lines and wrap.
    for (std::size_t Step = 1; Step < Lines; ++Step)
    {
        Talk.Observe(At(180.0, 0.9));
        assert(Talk.PressTalk(Lines));
        assert(Talk.LineIndex() == Step);
    }
    Talk.Observe(At(180.0, 0.9));
    assert(Talk.PressTalk(Lines));
    assert(Talk.LineIndex() == 0 && Talk.AdvanceCount() == static_cast<int>(Lines));

    // A single authored line is legal and simply stays put.
    MikdashDialog::Conversation Single;
    Single.Observe(At(50.0, 1.0));
    assert(Single.PressTalk(1) && Single.LineIndex() == 0);
    assert(Single.PressTalk(1) && Single.LineIndex() == 0);
    assert(!Single.PressTalk(0));

    // Cancel closes the panel and leaves the prompt when still in range.
    assert(Talk.PressCancel());
    assert(!Talk.IsTalking() && !Talk.ShouldResidentHold());
    assert(Talk.GetPhase() == MikdashDialog::Phase::Prompt);
    assert(Talk.LastCloseReason() == "closed");
    assert(!Talk.PressCancel());   // a second cancel is not consumed, so Escape reaches the menu

    // Stepping just outside the talk range keeps an open panel open (hysteresis) ...
    assert(Talk.PressTalk(Lines));
    Talk.Observe(At(300.0, 0.2));
    assert(Talk.IsTalking());
    // ... but walking away, or turning right around, ends it and releases the resident.
    Talk.Observe(At(400.0, 0.9));
    assert(!Talk.IsTalking() && !Talk.ShouldResidentHold());
    assert(Talk.GetPhase() == MikdashDialog::Phase::Idle);
    assert(Talk.LastCloseReason() == "walked away");
    assert(Talk.LineIndex() == 0);

    Talk.Observe(At(100.0, 0.9));
    assert(Talk.PressTalk(Lines) && Talk.IsTalking());
    Talk.Observe(At(100.0, -0.5));
    assert(!Talk.IsTalking());

    // The resident going away (destroyed, unbound) closes the panel too.
    Talk.Observe(At(100.0, 0.9));
    assert(Talk.PressTalk(Lines) && Talk.IsTalking());
    Talk.Observe(MikdashDialog::Aim());
    assert(!Talk.IsTalking() && Talk.GetPhase() == MikdashDialog::Phase::Idle);

    Talk.Observe(At(100.0, 0.9));
    assert(Talk.PressTalk(Lines));
    Talk.Reset();
    assert(Talk.GetPhase() == MikdashDialog::Phase::Idle && Talk.LineIndex() == 0 && !Talk.ShouldResidentHold());
    std::printf("Conversation: prompt, open, step, wrap, cancel, hysteresis, walk-away and reset checked\n");
}

void RouteCooperationChecks()
{
    // A looping plan of N waypoints walks leg j%N -> (j+1)%N, so laps simply repeat.
    const std::size_t N = 5;
    for (std::size_t Goal = 0; Goal < N * 3; ++Goal)
    {
        const MikdashRoute::Leg Leg = MikdashRoute::LegForGoal(Goal, N);
        assert(Leg.From == Goal % N);
        assert(Leg.To == (Goal + 1) % N);
        assert(Leg.From != Leg.To);
    }
    assert(MikdashRoute::LegForGoal(0, 0).From == 0 && MikdashRoute::LegForGoal(0, 0).To == 0);

    // Two loops in the two authored zones, both valid under the shipped rules.
    std::vector<MikdashRoute::Point2> Court;
    Court.push_back(MikdashRoute::Point2{3525, 1050});
    Court.push_back(MikdashRoute::Point2{4975, 1050});
    Court.push_back(MikdashRoute::Point2{4975, 2750});
    Court.push_back(MikdashRoute::Point2{3525, 2750});
    const std::vector<double> Pauses(4, 4.0);
    const std::vector<std::string> Labels(4, std::string("Walk the court leg"));
    std::string Why;
    assert(MikdashRoute::ValidateLoop(Court, Pauses, Labels, &Why));
    assert(std::abs(MikdashRoute::LoopLengthCm(Court) - 6300.0) < 1e-6);

    // The corridor test the population uses for each authored leg.
    assert(MikdashRoute::SegmentWithinCorridor(Court[0], Court[1], Court));
    assert(MikdashRoute::SegmentWithinCorridor(MikdashRoute::Point2{4000, 1150},
        MikdashRoute::Point2{4500, 1150}, Court));            // 100 cm inside the corridor
    assert(!MikdashRoute::SegmentWithinCorridor(MikdashRoute::Point2{4000, 1400},
        MikdashRoute::Point2{4500, 1400}, Court));            // 350 cm off the loop

    // Turning to face the walker while talking: 120 deg/s reaches 90 degrees in 0.75 s and
    // does not overshoot, and the shortest way around is taken through the wrap.
    double Yaw = 0.0;
    for (int Step = 0; Step < 44; ++Step) Yaw = MikdashRoute::TurnToward(Yaw, 90.0, 1.0 / 60.0);
    assert(Yaw > 86.0 && Yaw < 89.0);                            // still short of the target
    for (int Step = 0; Step < 4; ++Step) Yaw = MikdashRoute::TurnToward(Yaw, 90.0, 1.0 / 60.0);
    assert(Yaw == 90.0);                                          // snapped, never overshot
    Yaw = 170.0;
    Yaw = MikdashRoute::TurnToward(Yaw, -170.0, 1.0 / 60.0);
    assert(Yaw > 170.0 || Yaw < -170.0);           // wrapped forward, not 340 degrees back
    assert(std::abs(MikdashRoute::WrapDegrees(Yaw - 170.0)) <= 2.001);
    assert(MikdashRoute::TurnToward(10.0, 20.0, 0.0) == 10.0);
    assert(MikdashRoute::TurnToward(10.0, std::nan(""), 0.1) == 10.0);
    const double Toward = MikdashRoute::YawTowardDegrees(MikdashRoute::Point2{0, 0}, MikdashRoute::Point2{0, 100});
    assert(std::abs(Toward - 90.0) < 1e-9);

    // A body held still against a target for two seconds asks for one reviewed sidestep,
    // alternating sides; moving again clears the timer.
    MikdashRoute::BlockRecovery Recovery;
    for (int Step = 0; Step < 119; ++Step) assert(!Recovery.Advance(1.0 / 60.0, 0.0, true));
    bool Fired = false;
    for (int Step = 0; Step < 3 && !Fired; ++Step) Fired = Recovery.Advance(1.0 / 60.0, 0.0, true);
    assert(Fired);
    assert(Recovery.AttemptCount() == 1);
    const MikdashRoute::Point2 First = Recovery.SidestepTarget(MikdashRoute::Point2{0, 0}, MikdashRoute::Point2{100, 0});
    const MikdashRoute::Point2 Second = Recovery.SidestepTarget(MikdashRoute::Point2{0, 0}, MikdashRoute::Point2{100, 0});
    assert(std::abs(First.Y + Second.Y) < 1e-9 && std::abs(First.Y) > 99.0);
    for (int Step = 0; Step < 240; ++Step) assert(!Recovery.Advance(1.0 / 60.0, 5.0, true));
    assert(!Recovery.Advance(1.0 / 60.0, 0.0, false));   // no active target, no recovery
    assert(Recovery.StillTime() == 0.0);
    std::printf("Route cooperation: leg cycling, zone loops, corridor, facing turn and block recovery checked\n");
}
} // namespace

int main()
{
    RangeAndSelectionChecks();
    ConversationChecks();
    RouteCooperationChecks();
    std::printf("PASS: resident dialog state machine and its route cooperation\n");
    return 0;
}
