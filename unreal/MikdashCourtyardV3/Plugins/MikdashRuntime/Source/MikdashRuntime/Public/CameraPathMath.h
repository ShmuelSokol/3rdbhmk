#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <vector>

// Engine-independent camera path math shared by the cinematic intro, the photo-mode
// free camera and the standalone test. Units: centimeters, seconds, degrees. No Unreal
// types, so Tests/CameraPathMathTest.cpp compiles with cl.exe alone.
//
// Rotation convention is Unreal's exactly (see MakeBasis): X forward, Y right, Z up,
// Yaw about +Z, Pitch positive looks up, Roll about the forward axis. The basis rows
// reproduce FRotationMatrix, so a rotation computed here can be handed to the engine
// or written as a Sequencer key without a sign fix-up.
//
// This is framing and pacing math only. It knows nothing about level geometry beyond
// the axis-aligned boxes a caller hands it, so a path that passes PolylineClearsBoxes
// is clear of THOSE boxes and nothing else.
namespace MikdashCamera
{
constexpr double Pi = 3.14159265358979323846;

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
inline double Distance(const Vec3& A, const Vec3& B) { return Length(B - A); }
inline bool Finite(const Vec3& A) { return std::isfinite(A.X) && std::isfinite(A.Y) && std::isfinite(A.Z); }
inline Vec3 Normalized(const Vec3& A)
{
    const double L = Length(A);
    return L > 1e-12 ? A * (1.0 / L) : Vec3{};
}
inline Vec3 Lerp(const Vec3& A, const Vec3& B, double T) { return A + (B - A) * T; }
inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }
inline double Saturate(double V) { return Clamp(V, 0.0, 1.0); }
inline double DegToRad(double D) { return D * Pi / 180.0; }
inline double RadToDeg(double R) { return R * 180.0 / Pi; }

// Signed angle in (-180, 180].
inline double WrapDegrees(double D)
{
    if (!std::isfinite(D)) return 0.0;
    D = std::fmod(D + 180.0, 360.0);
    if (D < 0) D += 360.0;
    return D - 180.0;
}
inline double ShortestDeltaDegrees(double From, double To) { return WrapDegrees(To - From); }

// Adds whole turns to Angle so it is the representation nearest Previous. Sequencer keys
// must be unwrapped this way, or a 179 to -179 pair spins the camera the long way round.
inline double UnwrapDegrees(double Previous, double Angle)
{
    if (!std::isfinite(Previous) || !std::isfinite(Angle)) return Angle;
    return Previous + ShortestDeltaDegrees(Previous, Angle);
}

// -------------------------------------------------------------------------------------
// Easing. Every curve here is defined on [0, 1], pinned to Ease(0) == 0 and Ease(1) == 1,
// and monotonically non-decreasing, so it can drive time along an arc-length path without
// ever reversing the camera. Inputs outside [0, 1] are saturated; NaN maps to 0.
// -------------------------------------------------------------------------------------
inline double SafeT(double T) { return std::isfinite(T) ? Saturate(T) : 0.0; }

inline double EaseLinear(double T) { return SafeT(T); }

// 3t^2 - 2t^3. C1: zero velocity at both ends.
inline double SmoothStep(double T)
{
    const double S = SafeT(T);
    return S * S * (3.0 - 2.0 * S);
}

// 6t^5 - 15t^4 + 10t^3. C2: zero velocity AND acceleration at both ends; the gentlest start.
inline double SmootherStep(double T)
{
    const double S = SafeT(T);
    return S * S * S * (S * (S * 6.0 - 15.0) + 10.0);
}

inline double EaseInOutSine(double T) { return 0.5 * (1.0 - std::cos(Pi * SafeT(T))); }

inline double EaseInCubic(double T)
{
    const double S = SafeT(T);
    return S * S * S;
}

inline double EaseOutCubic(double T)
{
    const double S = 1.0 - SafeT(T);
    return 1.0 - S * S * S;
}

inline double EaseInOutCubic(double T)
{
    const double S = SafeT(T);
    if (S < 0.5) return 4.0 * S * S * S;
    const double U = -2.0 * S + 2.0;
    return 1.0 - U * U * U / 2.0;
}

// Trapezoidal speed profile: velocity smoothsteps up over the first InFraction of the
// shot, holds, then smoothsteps down over the last OutFraction. This is the one a long
// travelling shot wants, because unlike EaseInOutCubic the middle really is constant
// speed instead of one velocity peak. Monotonic (velocity is never negative) and C1
// (velocity is continuous). InFraction + OutFraction is normalised down to 1.
inline double EaseTrapezoid(double T, double InFraction, double OutFraction)
{
    const double S = SafeT(T);
    double In = std::isfinite(InFraction) ? Clamp(InFraction, 0.0, 1.0) : 0.0;
    double Out = std::isfinite(OutFraction) ? Clamp(OutFraction, 0.0, 1.0) : 0.0;
    const double Sum = In + Out;
    if (Sum > 1.0) { In /= Sum; Out /= Sum; }
    // Area under the velocity profile: each ramp contributes half its width.
    const double Area = 1.0 - 0.5 * In - 0.5 * Out;
    if (Area <= 1e-12) return S;
    // Integral of SmoothStep(y) dy from 0 to a is a^3 - a^4 / 2.
    const double InArea = In * 0.5;
    double Travelled;
    if (In > 0 && S < In)
    {
        const double A = Saturate(S / In);
        Travelled = In * (A * A * A - A * A * A * A * 0.5);
    }
    else if (S <= 1.0 - Out)
    {
        Travelled = InArea + (S - In);
    }
    else
    {
        const double R = Out > 0 ? Saturate((1.0 - S) / Out) : 0.0;
        Travelled = Area - Out * (R * R * R - R * R * R * R * 0.5);
    }
    return Saturate(Travelled / Area);
}

// -------------------------------------------------------------------------------------
// Cubic Hermite and Catmull-Rom primitives.
// -------------------------------------------------------------------------------------
inline Vec3 CubicHermite(const Vec3& P0, const Vec3& M0, const Vec3& P1, const Vec3& M1, double S)
{
    const double S2 = S * S, S3 = S2 * S;
    const double H00 = 2 * S3 - 3 * S2 + 1;
    const double H10 = S3 - 2 * S2 + S;
    const double H01 = -2 * S3 + 3 * S2;
    const double H11 = S3 - S2;
    return P0 * H00 + M0 * H10 + P1 * H01 + M1 * H11;
}

inline Vec3 CubicHermiteTangent(const Vec3& P0, const Vec3& M0, const Vec3& P1, const Vec3& M1, double S)
{
    const double S2 = S * S;
    const double D00 = 6 * S2 - 6 * S;
    const double D10 = 3 * S2 - 4 * S + 1;
    const double D01 = -6 * S2 + 6 * S;
    const double D11 = 3 * S2 - 2 * S;
    return P0 * D00 + M0 * D10 + P1 * D01 + M1 * D11;
}

// Uniform Catmull-Rom on the middle span P1..P2. Kept for callers that already have four
// evenly spaced points; SplinePath uses the non-uniform form below, which does not
// overshoot when control points are unevenly spaced.
inline Vec3 CatmullRomUniform(const Vec3& P0, const Vec3& P1, const Vec3& P2, const Vec3& P3, double S)
{
    return CubicHermite(P1, (P2 - P0) * 0.5, P2, (P3 - P1) * 0.5, S);
}

// -------------------------------------------------------------------------------------
// Orientation, in Unreal's rotator convention.
// -------------------------------------------------------------------------------------
struct Orientation
{
    double Pitch = 0, Yaw = 0, Roll = 0;
};

struct Basis
{
    Vec3 Forward, Right, Up;
};

// Rows of Unreal's FRotationMatrix, so Forward/Right/Up match the engine sign for sign.
inline Basis MakeBasis(const Orientation& R)
{
    const double CP = std::cos(DegToRad(R.Pitch)), SP = std::sin(DegToRad(R.Pitch));
    const double CY = std::cos(DegToRad(R.Yaw)), SY = std::sin(DegToRad(R.Yaw));
    const double CR = std::cos(DegToRad(R.Roll)), SR = std::sin(DegToRad(R.Roll));
    Basis B;
    B.Forward = {CP * CY, CP * SY, SP};
    B.Right = {SR * SP * CY - CR * SY, SR * SP * SY + CR * CY, -SR * CP};
    B.Up = {-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY, CR * CP};
    return B;
}

// Pitch/Yaw that aim From at To. Roll is not implied by a look-at and comes back 0; use
// RollTowards to carry the previous frame's roll forward. A degenerate (zero length)
// direction returns the identity rather than a NaN rotator.
inline Orientation LookAt(const Vec3& From, const Vec3& To)
{
    const Vec3 D = To - From;
    if (!Finite(D)) return {};
    const double Flat = std::sqrt(D.X * D.X + D.Y * D.Y);
    if (Flat < 1e-9 && std::abs(D.Z) < 1e-9) return {};
    Orientation R;
    R.Yaw = RadToDeg(std::atan2(D.Y, D.X));
    R.Pitch = RadToDeg(std::atan2(D.Z, Flat));
    R.Roll = 0.0;
    return R;
}

// Fraction of the way from Current to Target after Dt seconds, given a half life.
// Dt is clamped to a quarter second so a hitch cannot snap the camera.
inline double DampAlpha(double Dt, double HalfLifeSeconds)
{
    if (!std::isfinite(Dt) || Dt <= 0) return 0.0;
    if (!std::isfinite(HalfLifeSeconds) || HalfLifeSeconds <= 0) return 1.0;
    return 1.0 - std::exp(-0.6931471805599453 * Clamp(Dt, 0.0, 0.25) / HalfLifeSeconds);
}

// Damped roll: always takes the short way round, never overshoots, and is a no-op for a
// non-finite Dt. Used by the cinematic banking and by photo mode alike, so a visitor
// spinning the roll dial gets the same smoothing the flythrough does.
inline double RollTowards(double CurrentRoll, double TargetRoll, double Dt, double HalfLifeSeconds)
{
    if (!std::isfinite(CurrentRoll)) return WrapDegrees(TargetRoll);
    if (!std::isfinite(TargetRoll)) return CurrentRoll;
    return WrapDegrees(CurrentRoll + ShortestDeltaDegrees(CurrentRoll, TargetRoll) * DampAlpha(Dt, HalfLifeSeconds));
}

// Damps a whole rotator the same way, unwrapping each axis so a 179 to -179 step is one
// degree of motion and not 358.
inline Orientation OrientationTowards(const Orientation& Current, const Orientation& Target, double Dt, double HalfLifeSeconds)
{
    const double A = DampAlpha(Dt, HalfLifeSeconds);
    Orientation Out;
    Out.Pitch = Clamp(Current.Pitch + ShortestDeltaDegrees(Current.Pitch, Target.Pitch) * A, -89.9, 89.9);
    Out.Yaw = WrapDegrees(Current.Yaw + ShortestDeltaDegrees(Current.Yaw, Target.Yaw) * A);
    Out.Roll = WrapDegrees(Current.Roll + ShortestDeltaDegrees(Current.Roll, Target.Roll) * A);
    return Out;
}

// Bank into a turn: proportional to yaw rate, saturating at MaxBankDegrees. Sign is
// negative for a left turn so the horizon tips into the corner the way a wing would.
// Feed the result through RollTowards; raw yaw rate is far too jittery to key directly.
inline double BankFromTurnRate(double YawRateDegPerSecond, double MaxBankDegrees, double RateForFullBank)
{
    if (!std::isfinite(YawRateDegPerSecond) || !std::isfinite(RateForFullBank) || RateForFullBank <= 0) return 0.0;
    return -Clamp(YawRateDegPerSecond / RateForFullBank, -1.0, 1.0) * std::abs(MaxBankDegrees);
}

// -------------------------------------------------------------------------------------
// Arc-length parameterised Catmull-Rom path.
//
// Build() lays a non-uniform (centripetal by default, Alpha 0.5) Catmull-Rom through the
// control points. Centripetal parameterisation is what stops a cusp or a loop forming
// where two control points sit close together, which a uniform spline does happily and
// which reads on screen as the camera flicking backwards.
//
// The curve is C1 across every interior control point by construction: the two segments
// meeting at P(i) both use the tangent (P(i+1) - P(i-1)) / (u(i+1) - u(i-1)) there, so
// DerivativeAtParam is continuous. The end tangents come from phantom points reflected
// through the endpoints, which reduces exactly to the endpoint chord direction, so there
// is no NaN and no wild flick at either end.
//
// A distance table (Gauss-Legendre quadrature per sub-interval, then Newton inversion)
// turns distance along the curve into curve parameter, so PointAtDistance moves at a
// genuinely even speed. Without it, a Catmull-Rom evaluated at even parameter steps
// races through long segments and crawls through short ones.
// -------------------------------------------------------------------------------------
class SplinePath
{
public:
    // Points must number at least 2 and be consecutively distinct. Returns false and
    // leaves the object empty otherwise; it never half-builds.
    bool Build(const std::vector<Vec3>& InPoints, double Alpha = 0.5, int SamplesPerSegment = 64)
    {
        Reset();
        if (InPoints.size() < 2 || SamplesPerSegment < 4) return false;
        for (std::size_t I = 0; I < InPoints.size(); ++I)
        {
            if (!Finite(InPoints[I])) return false;
        }
        for (std::size_t I = 1; I < InPoints.size(); ++I)
        {
            if (Distance(InPoints[I - 1], InPoints[I]) < MinSpacingCm) return false;
        }
        Points = InPoints;
        Knots.resize(Points.size());
        Knots[0] = 0.0;
        const double A = Clamp(std::isfinite(Alpha) ? Alpha : 0.5, 0.0, 1.0);
        for (std::size_t I = 1; I < Points.size(); ++I)
        {
            Knots[I] = Knots[I - 1] + std::pow(Distance(Points[I - 1], Points[I]), A);
        }
        BuildDistanceTable(SamplesPerSegment);
        return TotalLengthCm > 0.0;
    }

    void Reset()
    {
        Points.clear();
        Knots.clear();
        SampleParam.clear();
        SampleDistance.clear();
        TotalLengthCm = 0.0;
    }

    // Geometry is usable as soon as the control points and knots are in place. The
    // distance table is built AFTER that, and building it evaluates the derivative, so
    // the evaluators must not gate on TotalLengthCm: an earlier revision did, which made
    // BuildDistanceTable integrate a curve that reported itself invalid, measure a total
    // length of zero, and hand Build() a false. Every downstream check then failed.
    bool HasGeometry() const { return Points.size() >= 2 && Knots.size() == Points.size(); }
    bool IsValid() const { return HasGeometry() && TotalLengthCm > 0.0; }
    std::size_t NumPoints() const { return Points.size(); }
    std::size_t NumSegments() const { return Points.empty() ? 0 : Points.size() - 1; }
    double TotalLength() const { return TotalLengthCm; }
    double MinParam() const { return Knots.empty() ? 0.0 : Knots.front(); }
    double MaxParam() const { return Knots.empty() ? 0.0 : Knots.back(); }
    // Curve parameter at control point Index; the interior ones are the C1 junctions.
    double KnotAt(std::size_t Index) const { return Index < Knots.size() ? Knots[Index] : 0.0; }
    Vec3 ControlPoint(std::size_t Index) const { return Index < Points.size() ? Points[Index] : Vec3{}; }

    Vec3 PointAtParam(double U) const
    {
        if (!HasGeometry()) return {};
        std::size_t Segment = 0;
        double S = 0;
        Locate(U, Segment, S);
        Vec3 P0, M0, P1, M1;
        HermiteForm(Segment, P0, M0, P1, M1);
        return CubicHermite(P0, M0, P1, M1, S);
    }

    // dP/dU, in cm per unit of curve parameter. Continuous across interior knots (C1).
    Vec3 DerivativeAtParam(double U) const
    {
        if (!HasGeometry()) return {};
        std::size_t Segment = 0;
        double S = 0;
        Locate(U, Segment, S);
        Vec3 P0, M0, P1, M1;
        HermiteForm(Segment, P0, M0, P1, M1);
        const double H = Knots[Segment + 1] - Knots[Segment];
        return CubicHermiteTangent(P0, M0, P1, M1, S) * (1.0 / H);
    }

    Vec3 TangentAtParam(double U) const { return Normalized(DerivativeAtParam(U)); }

    // Curve parameter at DistanceCm along the curve. Table lookup, then up to three
    // Newton steps against an exact quadrature of the remaining stretch, so the residual
    // sits far below the sampling error of the table alone.
    double ParamAtDistance(double DistanceCm) const
    {
        if (!IsValid()) return 0.0;
        if (!std::isfinite(DistanceCm)) return MinParam();
        const double Target = Clamp(DistanceCm, 0.0, TotalLengthCm);
        std::size_t Lo = 0, Hi = SampleDistance.size() - 1;
        while (Hi - Lo > 1)
        {
            const std::size_t Mid = (Lo + Hi) / 2;
            if (SampleDistance[Mid] <= Target) Lo = Mid; else Hi = Mid;
        }
        const double Da = SampleDistance[Lo], Db = SampleDistance[Hi];
        const double Ua = SampleParam[Lo], Ub = SampleParam[Hi];
        double U = (Db - Da) > 1e-12 ? Ua + (Ub - Ua) * ((Target - Da) / (Db - Da)) : Ua;
        for (int Iteration = 0; Iteration < 3; ++Iteration)
        {
            const double Travelled = Da + ArcLengthBetween(Ua, U);
            const double Speed = Length(DerivativeAtParam(U));
            if (Speed < 1e-9) break;
            const double Step = (Target - Travelled) / Speed;
            U = Clamp(U + Step, MinParam(), MaxParam());
            if (std::abs(Step) < 1e-10) break;
        }
        return U;
    }

    Vec3 PointAtDistance(double DistanceCm) const { return PointAtParam(ParamAtDistance(DistanceCm)); }
    Vec3 TangentAtDistance(double DistanceCm) const { return TangentAtParam(ParamAtDistance(DistanceCm)); }

    // The call a shot actually makes: Alpha in [0, 1] through the shot, already eased,
    // mapped to an even-speed position on the curve.
    Vec3 PointAtEasedAlpha(double Alpha) const { return PointAtDistance(SafeT(Alpha) * TotalLengthCm); }

    // Polyline of Count + 1 evenly spaced points, for a clearance check or a receipt.
    std::vector<Vec3> SampleEvenly(int Count) const
    {
        std::vector<Vec3> Out;
        if (!IsValid() || Count < 1) return Out;
        Out.reserve(static_cast<std::size_t>(Count) + 1);
        for (int I = 0; I <= Count; ++I)
        {
            Out.push_back(PointAtDistance(TotalLengthCm * (static_cast<double>(I) / Count)));
        }
        return Out;
    }

private:
    static constexpr double MinSpacingCm = 1e-4;

    // Control point with the ends extended by reflection, so segment 0 and the last
    // segment have four points like every other segment.
    Vec3 PointExtended(std::ptrdiff_t Index) const
    {
        const std::ptrdiff_t Last = static_cast<std::ptrdiff_t>(Points.size()) - 1;
        if (Index < 0) return Points[0] * 2.0 - Points[1];
        if (Index > Last) return Points[static_cast<std::size_t>(Last)] * 2.0 - Points[static_cast<std::size_t>(Last - 1)];
        return Points[static_cast<std::size_t>(Index)];
    }

    double KnotExtended(std::ptrdiff_t Index) const
    {
        const std::ptrdiff_t Last = static_cast<std::ptrdiff_t>(Knots.size()) - 1;
        if (Index < 0) return Knots[0] - (Knots[1] - Knots[0]);
        if (Index > Last) return Knots[static_cast<std::size_t>(Last)] + (Knots[static_cast<std::size_t>(Last)] - Knots[static_cast<std::size_t>(Last - 1)]);
        return Knots[static_cast<std::size_t>(Index)];
    }

    void Locate(double U, std::size_t& OutSegment, double& OutS) const
    {
        const double Clamped = std::isfinite(U) ? Clamp(U, MinParam(), MaxParam()) : MinParam();
        std::size_t Segment = 0;
        while (Segment + 2 < Knots.size() && Clamped >= Knots[Segment + 1]) ++Segment;
        const double H = Knots[Segment + 1] - Knots[Segment];
        OutSegment = Segment;
        OutS = H > 1e-12 ? Clamp((Clamped - Knots[Segment]) / H, 0.0, 1.0) : 0.0;
    }

    // Non-uniform Catmull-Rom expressed as a Hermite segment. Tangents are scaled by the
    // segment's knot width so dP/dU at S == 0 is exactly M0 / H and at S == 1 is exactly
    // M1 / H; the shared tangent at an interior knot is what makes the curve C1.
    void HermiteForm(std::size_t Segment, Vec3& P0, Vec3& M0, Vec3& P1, Vec3& M1) const
    {
        const std::ptrdiff_t I = static_cast<std::ptrdiff_t>(Segment);
        const Vec3 Prev = PointExtended(I - 1), Here = PointExtended(I);
        const Vec3 Next = PointExtended(I + 1), After = PointExtended(I + 2);
        const double UPrev = KnotExtended(I - 1), UHere = KnotExtended(I);
        const double UNext = KnotExtended(I + 1), UAfter = KnotExtended(I + 2);
        const double H = UNext - UHere;
        P0 = Here;
        P1 = Next;
        M0 = (Next - Prev) * (H / std::max(UNext - UPrev, 1e-12));
        M1 = (After - Here) * (H / std::max(UAfter - UHere, 1e-12));
    }

    // Four-point Gauss-Legendre of |dP/dU| over [Ua, Ub]. The integrand is a square root
    // so this is approximate, but two orders of magnitude better than the chord length a
    // naive table would use.
    double ArcLengthBetween(double Ua, double Ub) const
    {
        static const double Node[4] = {-0.8611363115940526, -0.3399810435848563, 0.3399810435848563, 0.8611363115940526};
        static const double Weight[4] = {0.3478548451374538, 0.6521451548625461, 0.6521451548625461, 0.3478548451374538};
        const double Half = (Ub - Ua) * 0.5, Mid = (Ua + Ub) * 0.5;
        double Sum = 0.0;
        for (int I = 0; I < 4; ++I)
        {
            Sum += Weight[I] * Length(DerivativeAtParam(Mid + Half * Node[I]));
        }
        return Sum * Half;
    }

    void BuildDistanceTable(int SamplesPerSegment)
    {
        SampleParam.clear();
        SampleDistance.clear();
        SampleParam.push_back(Knots[0]);
        SampleDistance.push_back(0.0);
        double Accumulated = 0.0;
        for (std::size_t Segment = 0; Segment < NumSegments(); ++Segment)
        {
            const double Ua = Knots[Segment], Ub = Knots[Segment + 1];
            for (int I = 1; I <= SamplesPerSegment; ++I)
            {
                const double A = Ua + (Ub - Ua) * (static_cast<double>(I - 1) / SamplesPerSegment);
                const double B = Ua + (Ub - Ua) * (static_cast<double>(I) / SamplesPerSegment);
                Accumulated += ArcLengthBetween(A, B);
                SampleParam.push_back(B);
                SampleDistance.push_back(Accumulated);
            }
        }
        TotalLengthCm = Accumulated;
    }

    std::vector<Vec3> Points;
    std::vector<double> Knots;
    std::vector<double> SampleParam;
    std::vector<double> SampleDistance;
    double TotalLengthCm = 0.0;
};

// -------------------------------------------------------------------------------------
// Containment clamps. Photo mode uses these as the leash that stops a visitor flying the
// free camera out of the level and photographing the void.
// -------------------------------------------------------------------------------------
struct Box
{
    Vec3 Min, Max;
};

inline bool BoxContains(const Box& B, const Vec3& P)
{
    return P.X >= B.Min.X && P.X <= B.Max.X && P.Y >= B.Min.Y && P.Y <= B.Max.Y && P.Z >= B.Min.Z && P.Z <= B.Max.Z;
}

// Clamps into the box shrunk by MarginCm on every side. A margin wider than half the box
// collapses to the box centre on that axis rather than inverting the bounds.
inline Vec3 ClampToBox(const Vec3& P, const Box& B, double MarginCm = 0.0)
{
    const double M = std::isfinite(MarginCm) ? std::max(0.0, MarginCm) : 0.0;
    const double Mid[3] = {(B.Min.X + B.Max.X) * 0.5, (B.Min.Y + B.Max.Y) * 0.5, (B.Min.Z + B.Max.Z) * 0.5};
    const Vec3 Source = Finite(P) ? P : Vec3{Mid[0], Mid[1], Mid[2]};
    const double Lo[3] = {B.Min.X + M, B.Min.Y + M, B.Min.Z + M};
    const double Hi[3] = {B.Max.X - M, B.Max.Y - M, B.Max.Z - M};
    double V[3] = {Source.X, Source.Y, Source.Z};
    for (int I = 0; I < 3; ++I)
    {
        V[I] = Lo[I] > Hi[I] ? Mid[I] : Clamp(V[I], Lo[I], Hi[I]);
    }
    return {V[0], V[1], V[2]};
}

// Leash to a sphere around the anchor (the player's body, in photo mode).
inline Vec3 ClampToSphere(const Vec3& P, const Vec3& Center, double RadiusCm)
{
    if (!Finite(P)) return Center;
    const Vec3 D = P - Center;
    const double L = Length(D);
    const double R = std::isfinite(RadiusCm) ? std::max(0.0, RadiusCm) : 0.0;
    return (L <= R || L < 1e-9) ? P : Center + D * (R / L);
}

// Slab test. Used to prove a proposed cinematic segment does not pass through a wall, a
// gate jamb or the sanctuary block, given those blocks as axis-aligned boxes.
inline bool SegmentIntersectsBox(const Vec3& A, const Vec3& B, const Box& Bx, double InflateCm = 0.0)
{
    if (!Finite(A) || !Finite(B)) return false;
    const double G = std::isfinite(InflateCm) ? std::max(0.0, InflateCm) : 0.0;
    const double Lo[3] = {Bx.Min.X - G, Bx.Min.Y - G, Bx.Min.Z - G};
    const double Hi[3] = {Bx.Max.X + G, Bx.Max.Y + G, Bx.Max.Z + G};
    const double Start[3] = {A.X, A.Y, A.Z};
    const double Delta[3] = {B.X - A.X, B.Y - A.Y, B.Z - A.Z};
    double Enter = 0.0, Exit = 1.0;
    for (int I = 0; I < 3; ++I)
    {
        if (std::abs(Delta[I]) < 1e-12)
        {
            if (Start[I] < Lo[I] || Start[I] > Hi[I]) return false;
            continue;
        }
        double T1 = (Lo[I] - Start[I]) / Delta[I];
        double T2 = (Hi[I] - Start[I]) / Delta[I];
        if (T1 > T2) { const double Swap = T1; T1 = T2; T2 = Swap; }
        Enter = std::max(Enter, T1);
        Exit = std::min(Exit, T2);
        if (Enter > Exit) return false;
    }
    return true;
}

// True when the whole polyline clears every box by InflateCm. The first offending
// segment and box are reported so a release script can name them in a receipt.
inline bool PolylineClearsBoxes(const std::vector<Vec3>& Polyline, const std::vector<Box>& Boxes, double InflateCm,
                                std::size_t* OutSegment = nullptr, std::size_t* OutBox = nullptr)
{
    for (std::size_t S = 0; S + 1 < Polyline.size(); ++S)
    {
        for (std::size_t B = 0; B < Boxes.size(); ++B)
        {
            if (SegmentIntersectsBox(Polyline[S], Polyline[S + 1], Boxes[B], InflateCm))
            {
                if (OutSegment) *OutSegment = S;
                if (OutBox) *OutBox = B;
                return false;
            }
        }
    }
    return true;
}

// -------------------------------------------------------------------------------------
// Frustum-safe clamp.
//
// Given where the camera is, where it points and what it is meant to be looking at, this
// pushes the camera back until the subject is beyond the near plane by a real margin, and
// re-aims it until the subject sits inside a safe inset of the frustum. It keeps the
// menorah in frame through the last beat of the intro, and keeps photo mode from letting
// a visitor jam the lens into the subject.
// -------------------------------------------------------------------------------------
struct FrustumSpec
{
    double HorizontalFovDegrees = 75.0;
    double AspectRatio = 16.0 / 9.0;
    double NearClipCm = 10.0;
    // Fraction of the half angle the subject must stay within. 1.0 is the frustum edge;
    // 0.8 keeps the subject clear of the corners where distortion is worst.
    double SafeInset = 0.8;
};

inline double VerticalFovDegrees(const FrustumSpec& Spec)
{
    const double Aspect = (std::isfinite(Spec.AspectRatio) && Spec.AspectRatio > 1e-6) ? Spec.AspectRatio : 1.0;
    const double HalfH = DegToRad(Clamp(Spec.HorizontalFovDegrees, 1.0, 170.0)) * 0.5;
    return RadToDeg(2.0 * std::atan(std::tan(HalfH) / Aspect));
}

struct FrustumClampResult
{
    Vec3 Position;
    Orientation Rotation;
    bool bPositionClamped = false;
    bool bRotationClamped = false;
    double SubjectDistanceCm = 0.0;
    // Angle between the camera forward and the subject, in degrees.
    double SubjectOffAxisDegrees = 0.0;
};

// Position and rotation adjusted so Subject is at least MinSubjectDistanceCm away (and
// always beyond the near plane) and inside the safe inset.
//
// With zero roll the safe region is the frustum rectangle inset by SafeInset, and the
// yaw/pitch correction is exact, so one pass lands the subject on the inset edge. With
// any roll the rectangle turns with the camera, so the conservative inscribed cone of
// half angle min(halfH, halfV) is used instead: a subject inside that cone is inside the
// frustum at every roll angle, which is exactly the guarantee photo mode needs when the
// visitor is free to tilt the horizon.
inline FrustumClampResult FrustumSafeClamp(const Vec3& Position, const Orientation& Rotation, const Vec3& Subject,
                                           const FrustumSpec& Spec, double MinSubjectDistanceCm)
{
    FrustumClampResult Out;
    Out.Position = Finite(Position) ? Position : Vec3{};
    Out.Rotation = Rotation;
    if (!Finite(Subject)) return Out;

    const double Near = (std::isfinite(Spec.NearClipCm) && Spec.NearClipCm > 0) ? Spec.NearClipCm : 10.0;
    const double MinDistance = std::max(std::isfinite(MinSubjectDistanceCm) ? MinSubjectDistanceCm : 0.0, Near * 1.5);

    Basis B = MakeBasis(Out.Rotation);
    Vec3 D = Subject - Out.Position;
    double Dist = Length(D);
    if (Dist < MinDistance)
    {
        // Back off along the view direction; if the camera sits exactly on the subject,
        // back off along the forward axis instead of producing a NaN.
        const Vec3 Away = Dist > 1e-6 ? Normalized(D) * -1.0 : Normalized(B.Forward) * -1.0;
        Out.Position = Subject + Away * MinDistance;
        Out.bPositionClamped = true;
        D = Subject - Out.Position;
        Dist = Length(D);
    }
    Out.SubjectDistanceCm = Dist;
    if (Dist < 1e-9) return Out;

    const double Inset = Clamp(std::isfinite(Spec.SafeInset) ? Spec.SafeInset : 0.8, 0.05, 1.0);
    const double HalfH = DegToRad(Clamp(Spec.HorizontalFovDegrees, 1.0, 170.0)) * 0.5 * Inset;
    const double HalfV = DegToRad(VerticalFovDegrees(Spec)) * 0.5 * Inset;

    // Decompose in the un-rolled basis: yaw and pitch corrections are exact there.
    const Orientation Flat{Out.Rotation.Pitch, Out.Rotation.Yaw, 0.0};
    B = MakeBasis(Flat);
    const double Cz = Dot(D, B.Forward);
    Out.SubjectOffAxisDegrees = RadToDeg(std::acos(Clamp(Cz / Dist, -1.0, 1.0)));

    if (Cz <= 0.0)
    {
        // Behind the camera: no incremental correction is meaningful, so just look at it.
        const Orientation Aim = LookAt(Out.Position, Subject);
        Out.Rotation.Pitch = Clamp(Aim.Pitch, -89.9, 89.9);
        Out.Rotation.Yaw = WrapDegrees(Aim.Yaw);
        Out.bRotationClamped = true;
        return Out;
    }

    if (std::abs(WrapDegrees(Out.Rotation.Roll)) > 1e-6)
    {
        // The frustum rectangle turns with the lens, so the only region that is inside
        // the frustum at EVERY roll angle is the cone inscribed in it, half angle
        // min(halfH, halfV). Rotate the forward axis along the great circle toward the
        // subject by exactly (Off - Cone): the smallest rotation that lands the subject
        // on the cone edge, and exact rather than approximate.
        //
        // A previous revision blended pitch and yaw toward the look-at rotation by the
        // fraction (1 - Cone/Off). Interpolating two Euler angles by a fraction does not
        // reduce the angle between the forward axis and the subject by that fraction, so
        // the subject was left outside the cone the doc comment promised, and the
        // guarantee photo mode leans on when the visitor tilts the horizon did not hold.
        const double Cone = std::min(HalfH, HalfV);
        const double Off = std::acos(Clamp(Cz / Dist, -1.0, 1.0));
        const double SinOff = std::sin(Off);
        if (Off > Cone && SinOff > 1e-12)
        {
            const Vec3 Unit = D * (1.0 / Dist);
            // Slerp: (sin(Cone) * Forward + sin(Off - Cone) * Unit) / sin(Off).
            const Vec3 Slerped = B.Forward * (std::sin(Cone) / SinOff) + Unit * (std::sin(Off - Cone) / SinOff);
            const Vec3 Aimed = Normalized(Slerped);
            if (Finite(Aimed) && Length(Aimed) > 0.5)
            {
                Out.Rotation.Pitch = Clamp(RadToDeg(std::asin(Clamp(Aimed.Z, -1.0, 1.0))), -89.9, 89.9);
                Out.Rotation.Yaw = WrapDegrees(RadToDeg(std::atan2(Aimed.Y, Aimed.X)));
                Out.bRotationClamped = true;
            }
        }
        return Out;
    }

    // Zero roll: the safe region is the frustum rectangle inset by SafeInset.
    //
    // The pitch correction is exact in one step, because the vertical angle is exactly
    // the elevation of the subject in the yawed plane minus the pitch. The horizontal one
    // is NOT: a yaw turn is about world Z, so it changes the forward component as well as
    // the sideways one, and a single pass leaves the subject about a tenth of a degree
    // outside its own safe inset whenever the pitch is non-zero. Alternating the two
    // exact-per-axis corrections converges on the corner in a handful of passes; the loop
    // exits the moment the residual stops moving, so the common untouched case costs one
    // basis evaluation.
    double NewPitch = Out.Rotation.Pitch;
    double NewYaw = Out.Rotation.Yaw;
    bool bNeeded = false;
    for (int Pass = 0; Pass < 24; ++Pass)
    {
        const Basis Step = MakeBasis(Orientation{NewPitch, NewYaw, 0.0});
        const double Sx = Dot(D, Step.Right), Sy = Dot(D, Step.Up), Sz = Dot(D, Step.Forward);
        if (Sz <= 0.0) break;
        const double AngleH = std::atan2(Sx, Sz);
        const double AngleV = std::atan2(Sy, Sz);
        const double DeltaH = AngleH - Clamp(AngleH, -HalfH, HalfH);
        const double DeltaV = AngleV - Clamp(AngleV, -HalfV, HalfV);
        if (Pass == 0)
        {
            // The reported "was it clamped" answer is about the pose the caller handed
            // in, so it is decided on the first pass and at the same 1e-9 rad tolerance
            // SubjectInSafeFrustum reads back.
            if (std::abs(DeltaH) <= 1e-9 && std::abs(DeltaV) <= 1e-9) break;
            bNeeded = true;
        }
        else if (std::abs(DeltaH) <= 1e-15 && std::abs(DeltaV) <= 1e-15)
        {
            break;
        }
        NewYaw = WrapDegrees(NewYaw + RadToDeg(DeltaH));
        NewPitch = Clamp(NewPitch + RadToDeg(DeltaV), -89.9, 89.9);
    }
    if (bNeeded)
    {
        Out.Rotation.Yaw = NewYaw;
        Out.Rotation.Pitch = NewPitch;
        Out.bRotationClamped = true;
    }
    return Out;
}

// True when Subject falls inside the safe inset of the frustum at Position/Rotation.
inline bool SubjectInSafeFrustum(const Vec3& Position, const Orientation& Rotation, const Vec3& Subject, const FrustumSpec& Spec)
{
    const FrustumClampResult R = FrustumSafeClamp(Position, Rotation, Subject, Spec, 0.0);
    return !R.bPositionClamped && !R.bRotationClamped;
}

// Horizontal FOV that frames a sphere of RadiusCm at DistanceCm inside the safe inset.
// Returns the 170 degree ceiling when the camera is inside the sphere, so a caller
// clamps rather than dividing by a negative.
inline double FovToFrame(double RadiusCm, double DistanceCm, double SafeInset = 0.8)
{
    if (!std::isfinite(RadiusCm) || !std::isfinite(DistanceCm) || RadiusCm <= 0 || DistanceCm <= RadiusCm) return 170.0;
    const double Inset = Clamp(std::isfinite(SafeInset) ? SafeInset : 0.8, 0.05, 1.0);
    return Clamp(2.0 * RadToDeg(std::asin(Clamp(RadiusCm / DistanceCm, 0.0, 1.0))) / Inset, 1.0, 170.0);
}
} // namespace MikdashCamera
