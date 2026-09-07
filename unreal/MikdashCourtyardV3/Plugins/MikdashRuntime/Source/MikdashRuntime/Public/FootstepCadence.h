#pragma once
#include <algorithm>
#include <cmath>

// Engine-independent distance accumulator, shared by runtime and native tests.
class FMikdashFootstepCadence
{
public:
    void Reset() { DistanceSinceStep = 0.f; }
    bool Advance(float Distance, float Speed, float DeltaTime, bool Grounded, bool Paused)
    {
        if (!std::isfinite(Distance) || !std::isfinite(Speed) || !std::isfinite(DeltaTime)
            || Distance < 0.f || Speed < 10.f || DeltaTime <= 0.f || DeltaTime > .25f
            || !Grounded || Paused || Distance > Speed * DeltaTime * 2.f + 50.f)
        {
            Reset();
            return false;
        }
        const float Fraction = std::max(0.f, std::min(1.f, (Speed - 100.f) / 500.f));
        const float Stride = 65.f + Fraction * 95.f;
        DistanceSinceStep += Distance;
        if (DistanceSinceStep < Stride) return false;
        DistanceSinceStep = std::fmod(DistanceSinceStep, Stride);
        return true;
    }
private:
    float DistanceSinceStep = 0.f;
};
