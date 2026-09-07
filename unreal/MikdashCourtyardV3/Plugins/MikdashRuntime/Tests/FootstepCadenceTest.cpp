#include "FootstepCadence.h"
#include <cassert>
#include <iostream>
#include <limits>

int Walk(float Speed, int Fps)
{
    FMikdashFootstepCadence C;
    int Count = 0;
    for (int I = 0; I < 10 * Fps; ++I)
        Count += C.Advance(Speed / Fps, Speed, 1.f / Fps, true, false);
    return Count;
}

int main()
{
    FMikdashFootstepCadence C;
    for (int I = 0; I < 600; ++I)
    {
        assert(!C.Advance(0, 0, 1.f/60, true, false)); // standing
        assert(!C.Advance(0, 600, 1.f/60, true, false)); // blocked input
        assert(!C.Advance(10, 600, 1.f/60, true, true)); // paused
        assert(!C.Advance(10, 600, 1.f/60, false, false)); // airborne
    }
    assert(!C.Advance(2000, 600, 1.f/60, true, false)); // relocation
    assert(!C.Advance(10, 600, 1.f, true, false)); // long frame: no burst
    assert(!C.Advance(std::numeric_limits<float>::quiet_NaN(), 100, .1f, true, false));
    assert(!C.Advance(60, 100, .25f, true, false));
    C.Reset();
    assert(!C.Advance(10, 100, .1f, true, false)); // possession/reset drops remainder
    for (float Speed : {100.f, 240.f, 600.f})
    {
        const int A = Walk(Speed, 30), B = Walk(Speed, 60), D = Walk(Speed, 120);
        assert(std::abs(A-B) <= 1 && std::abs(B-D) <= 1);
        assert(A >= 14 && A <= 38);
        std::cout << "speed=" << Speed << " steps/10s=" << A << ',' << B << ',' << D << '\n';
    }
    std::cout << "PASS: standing, wall, pause, air, relocation, reset and frame-rate cadence\n";
}
