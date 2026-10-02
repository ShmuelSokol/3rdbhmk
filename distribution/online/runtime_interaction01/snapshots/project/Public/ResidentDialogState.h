#pragma once
#include <cmath>
#include <cstddef>
#include <string>
#include <vector>

// Engine-independent state machine for the walker's short conversations with a resident.
// Shared by AMikdashPlayerController and the standalone tests.
//
// This is an authored line reader with a proximity and facing gate. It selects nothing,
// generates nothing and decides nothing about halacha: it advances an index through lines
// a human wrote, and tells the caller when a resident should hold still and turn.
namespace MikdashDialog
{
// Within 250 cm and roughly facing the resident. Facing uses the dot product of the
// camera's forward vector with the horizontal direction to the resident: 0.5 is a 60 degree
// half-angle, wide enough to be forgiving without letting a resident behind the walker win.
const double TalkRangeCm = 250.0;
const double ReleaseRangeCm = 320.0;      // hysteresis, so a small step does not drop a talk
const double FacingDotMinimum = 0.5;
const double ReleaseFacingDot = 0.0;      // while talking, only turning fully away ends it

/** One candidate resident as the controller measured it this frame. */
struct Aim
{
    double DistanceCm = 0.0;
    double FacingDot = -1.0;
    bool Valid = false;
};

inline bool InTalkRange(const Aim& Candidate)
{
    return Candidate.Valid && std::isfinite(Candidate.DistanceCm) && std::isfinite(Candidate.FacingDot)
        && Candidate.DistanceCm >= 0.0 && Candidate.DistanceCm <= TalkRangeCm && Candidate.FacingDot >= FacingDotMinimum;
}
inline bool StillHeld(const Aim& Candidate)
{
    return Candidate.Valid && std::isfinite(Candidate.DistanceCm) && std::isfinite(Candidate.FacingDot)
        && Candidate.DistanceCm >= 0.0 && Candidate.DistanceCm <= ReleaseRangeCm && Candidate.FacingDot >= ReleaseFacingDot;
}

/** Nearest resident that is in range and in front; -1 when none qualifies. Ties on distance
 * are broken by the better facing so a resident squarely ahead beats one at the edge. */
inline int BestCandidate(const std::vector<Aim>& Candidates)
{
    int Best = -1;
    for (std::size_t I = 0; I < Candidates.size(); ++I)
    {
        if (!InTalkRange(Candidates[I])) continue;
        if (Best < 0) { Best = static_cast<int>(I); continue; }
        const Aim& Current = Candidates[static_cast<std::size_t>(Best)];
        const Aim& Rival = Candidates[I];
        if (Rival.DistanceCm < Current.DistanceCm - 1e-9
            || (std::abs(Rival.DistanceCm - Current.DistanceCm) <= 1e-9 && Rival.FacingDot > Current.FacingDot))
            Best = static_cast<int>(I);
    }
    return Best;
}

enum class Phase { Idle, Prompt, Talking };

/** The panel never pauses the game. It opens on a talk press while a resident is in range
 * and in front, steps one authored line per further press, wraps at the end, and closes on
 * cancel, on the resident becoming unavailable, or on the walker leaving the wider hold
 * range. While talking the resident is asked to hold still and face the walker. */
class Conversation
{
public:
    /** Call once per frame with the chosen resident's aim (Valid=false when there is none). */
    void Observe(const Aim& Chosen)
    {
        Current = Chosen;
        if (State == Phase::Talking)
        {
            if (!StillHeld(Current)) Close("walked away");
            return;
        }
        State = InTalkRange(Current) ? Phase::Prompt : Phase::Idle;
    }

    /** The talk key. Returns true when the press was consumed by the conversation. */
    bool PressTalk(std::size_t LineCount)
    {
        if (LineCount == 0) return false;
        if (State == Phase::Talking)
        {
            Line = (Line + 1) % LineCount;
            ++Advances;
            return true;
        }
        if (!InTalkRange(Current)) return false;
        State = Phase::Talking; Line = 0; Advances = 0; Reason.clear();
        return true;
    }

    /** Cancel key. Returns true when a panel was actually open and is now closed. */
    bool PressCancel()
    {
        if (State != Phase::Talking) return false;
        Close("closed");
        return true;
    }

    void Reset()
    {
        State = Phase::Idle; Line = 0; Advances = 0; Current = Aim(); Reason.clear();
    }

    Phase GetPhase() const { return State; }
    bool IsTalking() const { return State == Phase::Talking; }
    bool ShouldShowPrompt() const { return State == Phase::Prompt; }
    // The resident stops and turns to the walker only while a panel is actually open.
    bool ShouldResidentHold() const { return State == Phase::Talking; }
    std::size_t LineIndex() const { return Line; }
    int AdvanceCount() const { return Advances; }
    const std::string& LastCloseReason() const { return Reason; }
    const Aim& Observed() const { return Current; }

private:
    void Close(const char* Why)
    {
        State = InTalkRange(Current) ? Phase::Prompt : Phase::Idle;
        Line = 0; Advances = 0; Reason = Why;
    }
    Phase State = Phase::Idle;
    std::size_t Line = 0;
    int Advances = 0;
    Aim Current;
    std::string Reason;
};
} // namespace MikdashDialog
