#include "../Source/MikdashRuntime/Public/CinematicTimingMath.h"
#include <cstdio>
#include <initializer_list>
#include <limits>

int main()
{
    using MikdashCinematicTiming::StepGate;
    int checks = 0;
    int failures = 0;
    auto check = [&](bool value) { ++checks; if (!value) ++failures; };
    StepGate gate;
    check(gate.Accept(23.0f) == 0.0f);
    check(std::abs(gate.Accept(1.0f / 60.0f) - 1.0f / 60.0f) < 1e-7f);
    check(gate.Accept(12.0f) == 0.1f);
    check(gate.Accept(-1.0f) == 0.0f);
    check(gate.Accept(0.0f) == 0.0f);
    check(gate.Accept(std::numeric_limits<float>::infinity()) == 0.0f);
    check(gate.Accept(-std::numeric_limits<float>::infinity()) == 0.0f);
    check(gate.Accept(std::numeric_limits<float>::quiet_NaN()) == 0.0f);
    // Invalid/stalled input neither poisons future steps nor causes catch-up.
    check(gate.Accept(0.05f) == 0.05f);
    for (int fps : {30, 60})
    {
        gate.Reset();
        check(gate.Accept(23.0f) == 0.0f);
        double elapsed = 0.0;
        for (int i = 0; i < fps * 68; ++i)
            elapsed += gate.Accept(1.0f / static_cast<float>(fps));
        check(std::abs(elapsed - 68.0) < 0.0001);
    }
    gate.Reset();
    check(gate.Accept(0.016f) == 0.0f);
    check(gate.Accept(0.016f) == 0.016f);
    gate.Reset();
    check(gate.Accept(std::numeric_limits<float>::quiet_NaN()) == 0.0f);
    check(gate.Accept(0.1f) == 0.1f);
    std::printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
