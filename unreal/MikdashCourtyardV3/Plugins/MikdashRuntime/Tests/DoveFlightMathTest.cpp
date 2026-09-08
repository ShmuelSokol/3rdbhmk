#include "DoveFlightMath.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>

using namespace MikdashDove;

static bool Near(double A, double B, double Tolerance = 1e-6) { return std::abs(A - B) <= Tolerance; }

static void WingBeatChecks()
{
    // Cruise: 4 Hz, amplitude 35, peak within a beat; phase advances exactly one cycle per 0.25 s.
    WingBeat Cruise;
    double Peak = 0, Trough = 0;
    for (int I = 0; I < 240; ++I) { const double A = Cruise.Advance(1.0 / 240, 0, 500); Peak = std::max(Peak, A); Trough = std::min(Trough, A); }
    assert(Peak > 34.0 && Peak <= 35.0001 && Trough < -34.0);
    assert(Near(Cruise.Phase(), 0.0, 1e-6) || Near(Cruise.Phase(), 2 * 3.14159265358979323846, 1e-6));
    assert(!Cruise.Gliding() && !Cruise.Climbing());
    // Climb: 6 Hz -> 1.5 cycles in 0.25 s; phase continuity means no jump at the switch.
    WingBeat Climb;
    double Previous = Climb.Angle();
    for (int I = 0; I < 60; ++I)
    {
        const double A = Climb.Advance(1.0 / 240, I < 30 ? 0 : 400, 500);
        assert(std::abs(A - Previous) < 6.0); // continuous even where cruise switches to climb
        Previous = A;
    }
    assert(Climb.Climbing());
    // Glide: descending fast levels the wings toward the dihedral within about a second.
    WingBeat Glide;
    for (int I = 0; I < 120; ++I) Glide.Advance(1.0 / 60, -400, 900);
    assert(Glide.Gliding() && Glide.Amplitude() < 0.5);
    for (int I = 0; I < 60; ++I) { const double A = Glide.Advance(1.0 / 60, -400, 900); assert(A > 7.0 && A < 8.5); }
    // Flapping resumes when the dive ends.
    for (int I = 0; I < 120; ++I) Glide.Advance(1.0 / 60, 0, 900);
    assert(!Glide.Gliding() && Glide.Amplitude() > 34.0);
    // Bad input leaves state untouched.
    const double Before = Glide.Angle();
    assert(Near(Glide.Advance(std::numeric_limits<double>::quiet_NaN(), 0, 0), Before));
    assert(Near(Glide.Advance(-1, 0, 0), Before));
    assert(Near(Glide.Advance(0.01, std::numeric_limits<double>::infinity(), 0), Before));
}

static void CameraChecks()
{
    CameraState State;
    CameraInput In;
    In.PawnPosition = {1000, 0, 500}; In.Velocity = {0, 0, 0}; In.ControlYawDegrees = 0; In.ControlPitchDegrees = 0; In.Dt = 1.0 / 60;
    CameraOutput Out = AdvanceCamera(State, In);
    // First frame snaps: 230 behind, 45 above, focus on the pawn when still.
    assert(Near(Out.Position.X, 770) && Near(Out.Position.Y, 0) && Near(Out.Position.Z, 545));
    assert(Near(Out.Focus.X, 1000) && Near(Out.RollDegrees, 0));
    // Full-speed forward flight: focus leads by 200 cm; the camera lags toward the new target.
    In.Velocity = {1800, 0, 0};
    Out = AdvanceCamera(State, In);
    assert(Near(Out.Focus.X, 1200));
    const double ExpectedAlpha = 1.0 - std::exp(-(1.0 / 60) / 0.15);
    assert(Near(Out.Position.X, 770 + (970 - 770) * ExpectedAlpha, 1e-6));
    // After one second of the same target the camera has closed nearly all of the gap.
    for (int I = 0; I < 60; ++I) Out = AdvanceCamera(State, In);
    assert(std::abs(Out.Position.X - 970) < 0.5);
    // Slow flight scales the look-ahead: 300 cm/s gives half.
    In.Velocity = {300, 0, 0};
    Out = AdvanceCamera(State, In);
    assert(Near(Out.Focus.X, 1100));
    // Bank: 50 deg/s turn -> 5 degrees; 400 deg/s clamps at 10; sign follows the turn.
    assert(Near(BankRoll(50), 5) && Near(BankRoll(400), 10) && Near(BankRoll(-400), -10) && Near(BankRoll(std::numeric_limits<double>::quiet_NaN()), 0));
    In.YawRateDegreesPerSecond = 400;
    for (int I = 0; I < 120; ++I) Out = AdvanceCamera(State, In);
    assert(Out.RollDegrees > 9.9 && Out.RollDegrees <= 10.0);
    // Pitch: looking down puts the camera above and behind.
    CameraState Down;
    CameraInput Look = In; Look.Velocity = {0, 0, 0}; Look.ControlPitchDegrees = -60; Look.YawRateDegreesPerSecond = 0;
    Out = AdvanceCamera(Down, Look);
    assert(Out.Position.Z > 500 + 230 * std::sin(DegToRad(60)) + 44 && Out.Position.X < 1000);
    // Long hitch never overshoots: alpha capped at a quarter second of lag.
    assert(LagAlpha(10.0, 0.15) < 1.0 && Near(LagAlpha(10.0, 0.15), 1.0 - std::exp(-0.25 / 0.15)));
    assert(Near(LagAlpha(0, 0.15), 0) && Near(LagAlpha(std::numeric_limits<double>::quiet_NaN(), 0.15), 0) && Near(LagAlpha(0.1, 0), 1));
}

static void ObstacleChecks()
{
    // No hit: input unchanged, full speed.
    SteerResult R = SteerAroundObstacle({1, 0, 0}, false, {0, 0, 0}, 0);
    assert(Near(R.Direction.X, 1) && Near(R.SpeedScale, 1) && !R.bSliding);
    // Oblique approach to a wall facing -X: slide along +Y, slow proportionally to distance.
    R = SteerAroundObstacle({0.8, 0.6, 0}, true, {-1, 0, 0}, 150);
    assert(Near(R.Direction.X, 0) && Near(R.Direction.Y, 0.6) && Near(R.SpeedScale, 0.5) && R.bSliding);
    // Head-on: deflect along the wall instead of stopping, at the minimum speed scale when touching.
    R = SteerAroundObstacle({1, 0, 0}, true, {-1, 0, 0}, 0);
    assert(Near(R.Direction.X, 0) && std::abs(R.Direction.Y) > 0.49 && Near(R.SpeedScale, 0.25) && R.bSliding);
    // Moving away from the surface is untouched apart from the slowdown.
    R = SteerAroundObstacle({-1, 0, 0}, true, {-1, 0, 0}, 100);
    assert(Near(R.Direction.X, -1) && !R.bSliding && R.SpeedScale > 0.33 && R.SpeedScale < 0.34);
    // Floor ahead while diving: vertical component removed, horizontal kept.
    R = SteerAroundObstacle({0.7, 0, -0.7}, true, {0, 0, 1}, 60);
    assert(Near(R.Direction.Z, 0) && Near(R.Direction.X, 0.7) && R.bSliding);
    // Degenerate normal or input: pass-through.
    R = SteerAroundObstacle({1, 0, 0}, true, {0, 0, 0}, 10);
    assert(Near(R.Direction.X, 1) && Near(R.SpeedScale, 1));
    R = SteerAroundObstacle({0, 0, 0}, true, {-1, 0, 0}, 10);
    assert(Near(R.SpeedScale, 1) && !R.bSliding);
    // Distance beyond the sweep never speeds the bird above one.
    R = SteerAroundObstacle({1, 0, 0}, true, {0, 1, 0}, 900);
    assert(Near(R.SpeedScale, 1));
    // Altitude: 120 cm floor rule, 60 cm ceiling rule, centered when both bind.
    ClearanceInput C; C.bFloorHit = true; C.FloorDistanceCm = 50;
    assert(Near(AltitudeCorrection(C), 70));
    C.FloorDistanceCm = 200; assert(Near(AltitudeCorrection(C), 0));
    ClearanceInput Roof; Roof.bCeilingHit = true; Roof.CeilingDistanceCm = 20;
    assert(Near(AltitudeCorrection(Roof), -40));
    ClearanceInput Both; Both.bFloorHit = Both.bCeilingHit = true; Both.FloorDistanceCm = 40; Both.CeilingDistanceCm = 20;
    assert(Near(AltitudeCorrection(Both), -10)); // gap 60, center 30 above floor: move down 10
    ClearanceInput None; assert(Near(AltitudeCorrection(None), 0));
    ClearanceInput Penetrating; Penetrating.bFloorHit = true; Penetrating.FloorDistanceCm = -5;
    assert(Near(AltitudeCorrection(Penetrating), 120));
    assert(Near(ClampVerticalVelocity(-300, 70), 0) && Near(ClampVerticalVelocity(300, 70), 300));
    assert(Near(ClampVerticalVelocity(300, -40), 0) && Near(ClampVerticalVelocity(-300, 0), -300));
    assert(Near(ClampVerticalVelocity(std::numeric_limits<double>::quiet_NaN(), 0), 0));
    // Body pitch: half the climb angle, clamped, zero when slow.
    assert(Near(BodyPitchDegrees({500, 0, 500}), 22.5) && Near(BodyPitchDegrees({0, 0, 900}), 25) && Near(BodyPitchDegrees({10, 0, 10}), 0));
}

int main()
{
    WingBeatChecks();
    CameraChecks();
    ObstacleChecks();
    std::cout << "Dove flight math: wing beat (4/6 Hz, 35 deg, glide), lagged camera, look-ahead, bank, obstacle slide and altitude clamp checks passed\n";
}
