#pragma once
#include <cmath>

namespace MikdashCinematicTiming
{
// Native/orbit choreography clock, deliberately not wall time. A newly registered
// core ticker can report editor startup time on its first callback. Discard that
// callback entirely. Later stalls advance at most 100 ms per callback (no catch-up),
// preserving camera continuity; playback can take longer in wall time under load.
// External LevelSequence playback owns its world clock and must not use this gate.
struct StepGate
{
    bool AwaitingFirst = true;
    void Reset() { AwaitingFirst = true; }
    float Accept(float DeltaSeconds)
    {
        if (AwaitingFirst)
        {
            AwaitingFirst = false;
            return 0.0f;
        }
        if (!std::isfinite(DeltaSeconds) || DeltaSeconds <= 0.0f)
            return 0.0f;
        return DeltaSeconds > 0.1f ? 0.1f : DeltaSeconds;
    }
};
}
