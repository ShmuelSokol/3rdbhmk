#pragma once
#include <algorithm>
#include <cmath>

// Engine-independent white-dove presentation math shared by AMikdashDovePawn and the
// standalone tests. Units: centimeters, seconds, degrees. No Unreal types. This shapes
// wing motion, the following camera and near-obstacle steering; it is not a flight model.
namespace MikdashDove
{
struct Vec3
{
    double X = 0, Y = 0, Z = 0;
};
inline Vec3 operator+(const Vec3& A, const Vec3& B) { return {A.X + B.X, A.Y + B.Y, A.Z + B.Z}; }
inline Vec3 operator-(const Vec3& A, const Vec3& B) { return {A.X - B.X, A.Y - B.Y, A.Z - B.Z}; }
inline Vec3 operator*(const Vec3& A, double S) { return {A.X * S, A.Y * S, A.Z * S}; }
inline double Dot(const Vec3& A, const Vec3& B) { return A.X * B.X + A.Y * B.Y + A.Z * B.Z; }
inline Vec3 Cross(const Vec3& A, const Vec3& B)
{
    return {A.Y * B.Z - A.Z * B.Y, A.Z * B.X - A.X * B.Z, A.X * B.Y - A.Y * B.X};
}
inline double Length(const Vec3& A) { return std::sqrt(Dot(A, A)); }
inline bool Finite(const Vec3& A) { return std::isfinite(A.X) && std::isfinite(A.Y) && std::isfinite(A.Z); }
inline Vec3 Normalized(const Vec3& A)
{
    const double L = Length(A);
    return L > 1e-9 ? A * (1.0 / L) : Vec3{};
}
inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }
inline double DegToRad(double D) { return D * 3.14159265358979323846 / 180.0; }
inline double WrapDegrees(double D)
{
    D = std::fmod(D + 180.0, 360.0);
    if (D < 0) D += 360.0;
    return D - 180.0;
}
// Exponential smoothing weight for a first-order lag of LagSeconds. Dt is clamped to a
// quarter second so a hitch never becomes a camera jump larger than one lag interval.
inline double LagAlpha(double Dt, double LagSeconds)
{
    if (!std::isfinite(Dt) || Dt <= 0) return 0.0;
    if (LagSeconds <= 0) return 1.0;
    return 1.0 - std::exp(-Clamp(Dt, 0.0, 0.25) / LagSeconds);
}

constexpr double FlapAmplitudeDegrees = 35.0;
constexpr double CruiseFlapHz = 4.0;
constexpr double ClimbFlapHz = 6.0;
constexpr double GlideDihedralDegrees = 8.0;
constexpr double ClimbSpeedCmPerSecond = 100.0;      // vertical speed above which the beat quickens
constexpr double GlideSinkCmPerSecond = -150.0;      // vertical speed below which wings level out
constexpr double AmplitudeBlendSeconds = 0.25;
constexpr double CameraLagSeconds = 0.15;
constexpr double LookAheadCm = 200.0;
constexpr double LookAheadFullSpeed = 600.0;
constexpr double MaxBankDegrees = 10.0;
constexpr double BankDegreesPerYawRate = 0.1;        // 100 deg/s of turn gives the full bank
constexpr double CameraArmCm = 230.0;
constexpr double CameraHeightCm = 45.0;
constexpr double ObstacleSweepRadiusCm = 60.0;
constexpr double ObstacleSweepLengthCm = 300.0;
constexpr double ObstacleMinSpeedScale = 0.25;
constexpr double MinFloorClearanceCm = 120.0;
constexpr double MinCeilingClearanceCm = 60.0;

/** Sine wing beat with phase continuity across frequency changes and a glide state. */
class WingBeat
{
public:
    // Returns the LEFT wing roll in degrees (positive raises the wing tip). The right wing
    // mirrors it. VerticalSpeed and Speed are the pawn velocity's Z and total magnitude.
    double Advance(double Dt, double VerticalSpeed, double Speed)
    {
        if (!std::isfinite(Dt) || Dt <= 0 || !std::isfinite(VerticalSpeed) || !std::isfinite(Speed)) return Angle();
        Dt = Clamp(Dt, 0.0, 0.25);
        bGliding = VerticalSpeed < GlideSinkCmPerSecond && Speed > 200.0;
        bClimbing = VerticalSpeed > ClimbSpeedCmPerSecond;
        const double Frequency = bClimbing ? ClimbFlapHz : CruiseFlapHz;
        const double TargetAmplitude = bGliding ? 0.0 : FlapAmplitudeDegrees;
        CurrentAmplitude += (TargetAmplitude - CurrentAmplitude) * LagAlpha(Dt, AmplitudeBlendSeconds);
        PhaseRadians = std::fmod(PhaseRadians + 2.0 * 3.14159265358979323846 * Frequency * Dt, 2.0 * 3.14159265358979323846);
        return Angle();
    }
    double Angle() const
    {
        const double Glide = GlideDihedralDegrees * (1.0 - CurrentAmplitude / FlapAmplitudeDegrees);
        return std::sin(PhaseRadians) * CurrentAmplitude + Glide;
    }
    double Phase() const { return PhaseRadians; }
    double Amplitude() const { return CurrentAmplitude; }
    bool Gliding() const { return bGliding; }
    bool Climbing() const { return bClimbing; }
private:
    double PhaseRadians = 0.0;
    double CurrentAmplitude = FlapAmplitudeDegrees;
    bool bGliding = false, bClimbing = false;
};

// Focus point ahead of the bird along its velocity, fading in with speed.
inline Vec3 LookAheadFocus(const Vec3& PawnPosition, const Vec3& Velocity)
{
    const double Speed = Length(Velocity);
    if (!Finite(Velocity) || Speed < 1.0) return PawnPosition;
    return PawnPosition + Normalized(Velocity) * (LookAheadCm * Clamp(Speed / LookAheadFullSpeed, 0.0, 1.0));
}
inline Vec3 ForwardFromYawPitch(double YawDegrees, double PitchDegrees)
{
    const double Y = DegToRad(YawDegrees), P = DegToRad(PitchDegrees);
    return {std::cos(P) * std::cos(Y), std::cos(P) * std::sin(Y), std::sin(P)};
}
// Where the camera wants to be: behind the focus along the control rotation, raised.
inline Vec3 DesiredCameraPosition(const Vec3& Focus, double YawDegrees, double PitchDegrees,
    double ArmCm = CameraArmCm, double HeightCm = CameraHeightCm)
{
    return Focus - ForwardFromYawPitch(YawDegrees, PitchDegrees) * ArmCm + Vec3{0, 0, HeightCm};
}
inline double BankRoll(double YawRateDegreesPerSecond)
{
    if (!std::isfinite(YawRateDegreesPerSecond)) return 0.0;
    return Clamp(YawRateDegreesPerSecond * BankDegreesPerYawRate, -MaxBankDegrees, MaxBankDegrees);
}

struct CameraState
{
    Vec3 Position;
    double RollDegrees = 0.0;
    bool bInitialized = false;
};
struct CameraInput
{
    Vec3 PawnPosition, Velocity;
    double ControlYawDegrees = 0.0, ControlPitchDegrees = 0.0;
    double YawRateDegreesPerSecond = 0.0;
    double Dt = 0.0;
};
struct CameraOutput
{
    Vec3 Position, Focus;
    double RollDegrees = 0.0;
};
// Lagged follow: position interpolates toward the desired spot with a 0.15 s lag, the
// camera looks at the look-ahead focus, and roll banks with the turn rate. Not a collision
// test; the adapter shortens the arm against geometry before applying the result.
inline CameraOutput AdvanceCamera(CameraState& State, const CameraInput& In)
{
    CameraOutput Out;
    Out.Focus = LookAheadFocus(In.PawnPosition, In.Velocity);
    const Vec3 Desired = DesiredCameraPosition(Out.Focus, In.ControlYawDegrees, In.ControlPitchDegrees);
    if (!State.bInitialized || !Finite(State.Position))
    {
        State.Position = Desired; State.RollDegrees = 0.0; State.bInitialized = true;
    }
    else
    {
        const double Alpha = LagAlpha(In.Dt, CameraLagSeconds);
        State.Position = State.Position + (Desired - State.Position) * Alpha;
        State.RollDegrees += (BankRoll(In.YawRateDegreesPerSecond) - State.RollDegrees) * Alpha;
    }
    Out.Position = State.Position; Out.RollDegrees = State.RollDegrees;
    return Out;
}

struct SteerResult
{
    Vec3 Direction;
    double SpeedScale = 1.0;
    bool bSliding = false;
};
// Shapes a movement input against a forward sphere-sweep hit: the closer the surface,
// the lower the speed scale (never below a quarter), and the input component into the
// surface is removed so the bird slides along it. A head-on approach deflects along the
// wall to the right instead of pinning the bird against it.
inline SteerResult SteerAroundObstacle(const Vec3& Input, bool bHit, const Vec3& HitNormal, double HitDistanceCm)
{
    SteerResult Result; Result.Direction = Input;
    const double Magnitude = Length(Input);
    if (!bHit || !Finite(Input) || Magnitude < 1e-6 || !Finite(HitNormal) || Length(HitNormal) < 0.5) return Result;
    const Vec3 Normal = Normalized(HitNormal);
    const double Distance = std::isfinite(HitDistanceCm) ? Clamp(HitDistanceCm, 0.0, ObstacleSweepLengthCm) : 0.0;
    Result.SpeedScale = Clamp(Distance / ObstacleSweepLengthCm, ObstacleMinSpeedScale, 1.0);
    const double Into = Dot(Input, Normal);
    if (Into >= 0) return Result; // already moving away from the surface
    Vec3 Slide = Input - Normal * Into;
    if (Length(Slide) < 0.05 * Magnitude)
    {
        Vec3 Along = Cross(Normal, Vec3{0, 0, 1});
        if (Length(Along) < 1e-6) Along = Cross(Normal, Vec3{1, 0, 0}); // floor or ceiling ahead
        Slide = Normalized(Along) * (Magnitude * 0.5);
    }
    Result.Direction = Slide; Result.bSliding = true;
    return Result;
}

struct ClearanceInput
{
    bool bFloorHit = false;
    double FloorDistanceCm = 0.0;
    bool bCeilingHit = false;
    double CeilingDistanceCm = 0.0;
};
// Vertical correction (cm, positive up) that keeps at least 120 cm above a traced floor and
// 60 cm below a traced ceiling. Both together move the bird toward the middle of the gap.
inline double AltitudeCorrection(const ClearanceInput& In)
{
    double Up = 0.0, Down = 0.0;
    if (In.bFloorHit && std::isfinite(In.FloorDistanceCm) && In.FloorDistanceCm < MinFloorClearanceCm)
        Up = MinFloorClearanceCm - std::max(0.0, In.FloorDistanceCm);
    if (In.bCeilingHit && std::isfinite(In.CeilingDistanceCm) && In.CeilingDistanceCm < MinCeilingClearanceCm)
        Down = MinCeilingClearanceCm - std::max(0.0, In.CeilingDistanceCm);
    if (Up > 0 && Down > 0)
    {
        const double Gap = std::max(0.0, In.FloorDistanceCm) + std::max(0.0, In.CeilingDistanceCm);
        return Gap * 0.5 - std::max(0.0, In.FloorDistanceCm); // center of the gap
    }
    return Up - Down;
}
// Vertical velocity after a correction: never keep sinking into a floor or rising into a ceiling.
inline double ClampVerticalVelocity(double VelocityZ, double Correction)
{
    if (!std::isfinite(VelocityZ)) return 0.0;
    if (Correction > 0 && VelocityZ < 0) return 0.0;
    if (Correction < 0 && VelocityZ > 0) return 0.0;
    return VelocityZ;
}
// Body pitch that reads as climbing or diving without tumbling.
inline double BodyPitchDegrees(const Vec3& Velocity)
{
    const double Speed = Length(Velocity);
    if (!Finite(Velocity) || Speed < 50.0) return 0.0;
    return Clamp(std::asin(Clamp(Velocity.Z / Speed, -1.0, 1.0)) * 180.0 / 3.14159265358979323846 * 0.5, -25.0, 25.0);
}
} // namespace MikdashDove
