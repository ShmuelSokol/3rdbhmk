#define _CRT_SECURE_NO_WARNINGS

// Standalone test for SunPositionMath.h. No Unreal, no engine headers.
//
//   cl /std:c++17 /EHsc /W4 /WX /I..\Source\MikdashRuntime\Public SunPositionMathTest.cpp
//   SunPositionMathTest.exe <optional path to tests.json>
//
// Every check goes through Check(), which is live in debug AND release builds; the printed
// lines are the numeric evidence, and with an argument the same numbers are written as
// JSON for SourceAssets/sky-review/tests.json.
//
// REFERENCE DATA PROVENANCE
// -------------------------
// Sun rise/set/transit/civil-twilight times come from the US Naval Observatory
// Astronomical Applications API v4.0.1:
//   https://aa.usno.navy.mil/api/rstt/oneday?date=<D>&coords=31.7767,35.2345&tz=<2|3>
// queried 2026-09-08. USNO publishes whole minutes for a SEA-LEVEL observer with the
// standard -0.8333 degree horizon (34' refraction + 16' semidiameter), which is exactly the
// convention SunPositionMath.h implements. Jerusalem's real 750 m elevation would move true
// rise about 4 minutes earlier and set 4 minutes later; that offset is deliberately NOT in
// the library, so comparing against a service that applies it (sunrisesunset.io reports
// 05:37/17:55 for 2026-03-21 where USNO reports 05:42/17:51) would show a spurious 5 minute
// "error". The elevation term is a scene decision, not an astronomy bug.
//
// Moon phase instants come from the same USNO responses ("closestphase").
// The Israeli daylight-saving transition dates were cross-checked against the IANA tz
// database (pytz 2019.3, Asia/Jerusalem): 2026-03-27..2026-10-25, 2027-03-26..2027-10-31.
//
// USNO rounds published times to the nearest minute, so up to 0.5 minute of every quoted
// error is reference quantisation. Both the raw signed error and the "excess" (the part
// rounding cannot explain) are reported.

#include "SunPositionMath.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

using namespace MikdashSun;

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

static long long CheckCount = 0;
static void CheckImpl(bool Condition, const char* Text, int Line)
{
    ++CheckCount;
    if (!Condition)
    {
        std::fprintf(stderr, "FAIL line %d: %s\n", Line, Text);
        std::exit(1);
    }
}
#define Check(X) CheckImpl(!!(X), #X, __LINE__)

static std::vector<std::pair<std::string, std::string>> Facts;

static void Fact(const std::string& Key, double Value)
{
    char Buffer[64];
    std::snprintf(Buffer, sizeof(Buffer), "%.6f", Value);
    Facts.emplace_back(Key, Buffer);
}
static void FactInt(const std::string& Key, long long Value) { Facts.emplace_back(Key, std::to_string(Value)); }
static void FactText(const std::string& Key, const std::string& Value) { Facts.emplace_back(Key, "\"" + Value + "\""); }

static bool Near(double A, double B, double Tolerance) { return std::fabs(A - B) <= Tolerance; }

// ---------------------------------------------------------------------------
// Reference table
// ---------------------------------------------------------------------------

struct FReferenceDay
{
    int Year, Month, Day;
    double TimeZone;      // the offset USNO was queried with
    int RiseH, RiseM;     // published sunrise
    int SetH, SetM;       // published sunset
    int NoonH, NoonM;     // published upper transit
    int DawnH, DawnM;     // published begin civil twilight
    int DuskH, DuskM;     // published end civil twilight
};

// USNO api/rstt/oneday, coords 31.7767,35.2345.
static const FReferenceDay References[] = {
    {2025, 12, 21, 2.0, 6, 35, 16, 39, 11, 37, 6, 8, 17, 6},
    {2026, 1, 1, 2.0, 6, 39, 16, 46, 11, 43, 6, 12, 17, 13},
    {2026, 3, 21, 2.0, 5, 42, 17, 51, 11, 46, 5, 18, 18, 15},
    {2026, 4, 15, 3.0, 6, 11, 19, 8, 12, 39, 5, 46, 19, 33},
    {2026, 6, 21, 3.0, 5, 34, 19, 48, 12, 41, 5, 6, 20, 16},
    {2026, 8, 15, 3.0, 6, 4, 19, 23, 12, 44, 5, 38, 19, 49},
    {2026, 9, 23, 3.0, 6, 28, 18, 35, 12, 31, 6, 3, 18, 59},
    {2026, 10, 15, 3.0, 6, 42, 18, 7, 12, 25, 6, 18, 18, 32},
    {2026, 12, 21, 2.0, 6, 35, 16, 39, 11, 37, 6, 8, 17, 6},
    {2027, 6, 21, 3.0, 5, 34, 19, 48, 12, 41, 5, 6, 20, 16},
};
static const int ReferenceCount = int(sizeof(References) / sizeof(References[0]));

/** Signed error in minutes of Computed (hours) against a published HH:MM. Published times
 * are truncated to the minute, so anything in [0,1) minutes is inside the same minute. */
static double ErrorMinutes(double ComputedHours, int PublishedH, int PublishedM)
{
    return ComputedHours * 60.0 - (PublishedH * 60.0 + PublishedM);
}

/** The part of an error that USNO's rounding to the nearest minute cannot explain. */
static double ExcessMinutes(double ErrMinutes)
{
    const double Excess = std::fabs(ErrMinutes) - 0.5;
    return Excess > 0.0 ? Excess : 0.0;
}

static std::string HoursToClock(double Hours)
{
    double H = Wrap24(Hours);
    int Hour = int(H);
    double Rem = (H - Hour) * 60.0;
    int Minute = int(Rem);
    int Second = int((Rem - Minute) * 60.0 + 0.5);
    if (Second >= 60) { Second -= 60; ++Minute; }
    if (Minute >= 60) { Minute -= 60; ++Hour; }
    char Buffer[32];
    std::snprintf(Buffer, sizeof(Buffer), "%02d:%02d:%02d", Hour % 24, Minute, Second);
    return Buffer;
}

// ---------------------------------------------------------------------------
// 1. Calendar and Israeli clock
// ---------------------------------------------------------------------------

static void TestCalendar()
{
    // 2026-09-08 is a Tuesday; 2026-01-01 a Thursday.
    Check(DayOfWeekSundayZero(2026, 9, 8) == 2);
    Check(DayOfWeekSundayZero(2026, 1, 1) == 4);
    Check(DayOfWeekSundayZero(2000, 1, 1) == 6); // Saturday
    Check(DayOfWeekSundayZero(1900, 1, 1) == 1); // Monday

    Check(IsLeapYear(2024) && !IsLeapYear(2026) && !IsLeapYear(1900) && IsLeapYear(2000));
    Check(DaysInMonth(2024, 2) == 29 && DaysInMonth(2026, 2) == 28);
    Check(DayOfYear(2026, 1, 1) == 1);
    Check(DayOfYear(2026, 12, 31) == 365);
    Check(DayOfYear(2024, 12, 31) == 366);

    // Last Sunday of March 2026 is the 29th; of October 2026 the 25th.
    Check(LastWeekdayOfMonth(2026, 3, 0) == 29);
    Check(LastWeekdayOfMonth(2026, 10, 0) == 25);
    Check(LastWeekdayOfMonth(2027, 3, 0) == 28);
    Check(LastWeekdayOfMonth(2027, 10, 0) == 31);

    // Julian Day anchors (Meeus): 2000-01-01 12:00 UT = 2451545.0.
    Check(Near(JulianDayFromUtc(2000, 1, 1, 12.0), 2451545.0, 1e-9));
    Check(Near(JulianDayFromUtc(1987, 1, 27, 0.0), 2446822.5, 1e-9));
    Check(Near(JulianDayFromUtc(1957, 10, 4, 0.81 * 24.0), 2436116.31, 1e-9));
    Fact("julianDay_2000_01_01T12Z", JulianDayFromUtc(2000, 1, 1, 12.0));
}

static void TestIsraeliClock()
{
    // 2026: IDT from Friday 27 March 02:00 to Sunday 25 October 02:00 (IANA tz database).
    Check(IsraelUtcOffsetHours(2026, 3, 26, 12.0) == 2.0);
    Check(IsraelUtcOffsetHours(2026, 3, 27, 1.5) == 2.0);
    Check(IsraelUtcOffsetHours(2026, 3, 27, 2.5) == 3.0);
    Check(IsraelUtcOffsetHours(2026, 3, 28, 12.0) == 3.0);
    Check(IsraelUtcOffsetHours(2026, 10, 24, 12.0) == 3.0);
    Check(IsraelUtcOffsetHours(2026, 10, 25, 1.5) == 3.0);
    Check(IsraelUtcOffsetHours(2026, 10, 25, 2.5) == 2.0);
    Check(IsraelUtcOffsetHours(2026, 10, 26, 12.0) == 2.0);
    // 2027: 26 March to 31 October.
    Check(IsraelUtcOffsetHours(2027, 3, 25, 12.0) == 2.0);
    Check(IsraelUtcOffsetHours(2027, 3, 26, 12.0) == 3.0);
    Check(IsraelUtcOffsetHours(2027, 10, 30, 12.0) == 3.0);
    Check(IsraelUtcOffsetHours(2027, 10, 31, 12.0) == 2.0);
    // Deep winter and deep summer.
    Check(IsraelUtcOffsetHours(2026, 1, 15, 12.0) == 2.0);
    Check(IsraelUtcOffsetHours(2026, 7, 15, 12.0) == 3.0);
    Check(IsraelUtcOffsetHours(2026, 12, 25, 12.0) == 2.0);
    FactInt("israelDstStartDay2026", LastWeekdayOfMonth(2026, 3, 0) - 2);
    FactInt("israelDstEndDay2026", LastWeekdayOfMonth(2026, 10, 0));
}

// ---------------------------------------------------------------------------
// 2. Equation of time and declination
// ---------------------------------------------------------------------------

static void TestEquationOfTimeAndDeclination()
{
    // The equation of time runs from about -14.2 min (mid February) to +16.4 min (early
    // November), crossing zero four times a year. Sample the whole of 2026.
    double MinEq = 1e9, MaxEq = -1e9;
    int MinDay = 0, MaxDay = 0;
    for (int N = 1; N <= 365; ++N)
    {
        int Month = 1, Day = N;
        while (Day > DaysInMonth(2026, Month)) { Day -= DaysInMonth(2026, Month); ++Month; }
        const double JD = JulianDayFromUtc(2026, Month, Day, 12.0);
        const double Eq = EquationOfTimeMinutes(JD);
        if (Eq < MinEq) { MinEq = Eq; MinDay = N; }
        if (Eq > MaxEq) { MaxEq = Eq; MaxDay = N; }
    }
    Check(Near(MinEq, -14.2, 0.4));
    Check(Near(MaxEq, 16.4, 0.4));
    Check(MinDay >= 35 && MinDay <= 50);   // 4-19 February
    Check(MaxDay >= 300 && MaxDay <= 312); // 27 October - 8 November
    Fact("equationOfTimeMinMinutes2026", MinEq);
    Fact("equationOfTimeMaxMinutes2026", MaxEq);
    FactInt("equationOfTimeMinDayOfYear2026", MinDay);
    FactInt("equationOfTimeMaxDayOfYear2026", MaxDay);

    // Declination: zero at the equinoxes, +-obliquity at the solstices.
    const double DecMarch = SolarDeclinationDeg(JulianDayFromUtc(2026, 3, 20, 14.46)); // 2026 vernal equinox
    const double DecJune = SolarDeclinationDeg(JulianDayFromUtc(2026, 6, 21, 8.24));
    const double DecDecember = SolarDeclinationDeg(JulianDayFromUtc(2026, 12, 21, 20.5));
    Check(Near(DecMarch, 0.0, 0.02));
    Check(Near(DecJune, 23.44, 0.02));
    Check(Near(DecDecember, -23.44, 0.02));
    Fact("declinationVernalEquinox2026Deg", DecMarch);
    Fact("declinationJuneSolstice2026Deg", DecJune);
    Fact("declinationDecemberSolstice2026Deg", DecDecember);

    // Obliquity in 2000 was 23.4393 degrees.
    Check(Near(MeanObliquityOfEclipticDeg(0.0), 23.4392911, 1e-6));
}

// ---------------------------------------------------------------------------
// 3. Sunrise / sunset / twilight against USNO
// ---------------------------------------------------------------------------

struct FAccuracySummary
{
    double WorstRise = 0.0, WorstSet = 0.0, WorstNoon = 0.0, WorstTwilight = 0.0;
    double WorstAny = 0.0;
    std::string WorstAnyLabel;
};

static void TestPublishedTimes(FAccuracySummary& Summary)
{
    for (int I = 0; I < ReferenceCount; ++I)
    {
        const FReferenceDay& R = References[I];
        const FDayEvents E = ComputeDayEvents(JerusalemLatitudeDeg, JerusalemLongitudeDeg, R.Year, R.Month, R.Day, R.TimeZone);

        char Prefix[64];
        std::snprintf(Prefix, sizeof(Prefix), "%04d-%02d-%02d", R.Year, R.Month, R.Day);
        const std::string P(Prefix);

        // The clock the library picks for that date must match the offset USNO was queried
        // with, otherwise the comparison is meaningless.
        Check(IsraelUtcOffsetHours(R.Year, R.Month, R.Day, 12.0) == R.TimeZone);

        const double RiseErr = ErrorMinutes(E.SunriseHours, R.RiseH, R.RiseM);
        const double SetErr = ErrorMinutes(E.SunsetHours, R.SetH, R.SetM);
        const double NoonErr = ErrorMinutes(E.SolarNoonHours, R.NoonH, R.NoonM);
        const double DawnErr = ErrorMinutes(E.CivilDawnHours, R.DawnH, R.DawnM);
        const double DuskErr = ErrorMinutes(E.CivilDuskHours, R.DuskH, R.DuskM);

        std::printf("  %s  rise %s (%+6.2f min)  set %s (%+6.2f min)  noon %s (%+6.2f min)  "
                    "civil %s (%+6.2f) / %s (%+6.2f)\n",
                    P.c_str(), HoursToClock(E.SunriseHours).c_str(), RiseErr, HoursToClock(E.SunsetHours).c_str(), SetErr,
                    HoursToClock(E.SolarNoonHours).c_str(), NoonErr, HoursToClock(E.CivilDawnHours).c_str(), DawnErr,
                    HoursToClock(E.CivilDuskHours).c_str(), DuskErr);

        Fact(P + ".sunriseHours", E.SunriseHours);
        Fact(P + ".sunsetHours", E.SunsetHours);
        Fact(P + ".solarNoonHours", E.SolarNoonHours);
        Fact(P + ".civilDawnHours", E.CivilDawnHours);
        Fact(P + ".civilDuskHours", E.CivilDuskHours);
        Fact(P + ".sunriseErrorMinutes", RiseErr);
        Fact(P + ".sunsetErrorMinutes", SetErr);
        Fact(P + ".solarNoonErrorMinutes", NoonErr);
        Fact(P + ".civilDawnErrorMinutes", DawnErr);
        Fact(P + ".civilDuskErrorMinutes", DuskErr);
        Fact(P + ".sunriseExcessMinutes", ExcessMinutes(RiseErr));
        Fact(P + ".sunsetExcessMinutes", ExcessMinutes(SetErr));
        FactText(P + ".sunriseClock", HoursToClock(E.SunriseHours));
        FactText(P + ".sunsetClock", HoursToClock(E.SunsetHours));

        // Hard gate: the task's two-minute bar, applied to the raw signed error against the
        // start of the published minute.
        Check(std::fabs(RiseErr) < 2.0);
        Check(std::fabs(SetErr) < 2.0);
        Check(std::fabs(NoonErr) < 2.0);
        Check(std::fabs(DawnErr) < 2.0);
        Check(std::fabs(DuskErr) < 2.0);

        // Sanity that cannot be satisfied by a coincidence: the events must be ordered, and
        // nearly symmetric about solar noon. NOT exactly symmetric: the declination moves by
        // up to 0.4 degrees between sunrise and sunset, which shifts the two half-days by up
        // to about a minute near the equinoxes. That asymmetry is real; it is recorded here
        // rather than absorbed into a loose tolerance elsewhere.
        Check(E.CivilDawnHours < E.SunriseHours);
        Check(E.SunriseHours < E.SolarNoonHours);
        Check(E.SolarNoonHours < E.SunsetHours);
        Check(E.SunsetHours < E.CivilDuskHours);
        const double AsymmetryMinutes =
            ((E.SolarNoonHours - E.SunriseHours) - (E.SunsetHours - E.SolarNoonHours)) * 60.0;
        Fact(P + ".halfDayAsymmetryMinutes", AsymmetryMinutes);
        Check(std::fabs(AsymmetryMinutes) < 1.5);
        Check(E.bSunriseValid && E.bSunsetValid && E.bCivilDawnValid && E.bCivilDuskValid);

        // The refracted altitude at the computed rise/set is the -0.833 target.
        const FSolarAngles AtRise =
            SolarPosition(JerusalemLatitudeDeg, JerusalemLongitudeDeg, R.Year, R.Month, R.Day, E.SunriseHours, R.TimeZone);
        Check(Near(AtRise.AltitudeDeg, SunriseAltitudeDeg, 0.01));

        const double Worst = std::fabs(RiseErr) > std::fabs(SetErr) ? std::fabs(RiseErr) : std::fabs(SetErr);
        if (std::fabs(RiseErr) > Summary.WorstRise) Summary.WorstRise = std::fabs(RiseErr);
        if (std::fabs(SetErr) > Summary.WorstSet) Summary.WorstSet = std::fabs(SetErr);
        if (std::fabs(NoonErr) > Summary.WorstNoon) Summary.WorstNoon = std::fabs(NoonErr);
        if (std::fabs(DawnErr) > Summary.WorstTwilight) Summary.WorstTwilight = std::fabs(DawnErr);
        if (std::fabs(DuskErr) > Summary.WorstTwilight) Summary.WorstTwilight = std::fabs(DuskErr);
        if (Worst > Summary.WorstAny)
        {
            Summary.WorstAny = Worst;
            Summary.WorstAnyLabel = P;
        }
    }

    Fact("worstSunriseErrorMinutes", Summary.WorstRise);
    Fact("worstSunsetErrorMinutes", Summary.WorstSet);
    Fact("worstSolarNoonErrorMinutes", Summary.WorstNoon);
    Fact("worstCivilTwilightErrorMinutes", Summary.WorstTwilight);
    Fact("worstRiseSetErrorMinutes", Summary.WorstAny);
    Fact("worstRiseSetExcessMinutes", ExcessMinutes(Summary.WorstAny));
    FactText("worstRiseSetErrorDate", Summary.WorstAnyLabel);
    FactInt("referenceDayCount", ReferenceCount);
}

// ---------------------------------------------------------------------------
// 4. Altitude and azimuth
// ---------------------------------------------------------------------------

static void TestAltitudeAzimuth()
{
    // Equinox: the sun rises almost due east and sets almost due west anywhere on Earth,
    // and culminates at (90 - latitude).
    const FDayEvents Equinox = ComputeDayEvents(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 3, 20, 2.0);
    Check(Near(Equinox.SunriseAzimuthDeg, 90.0, 1.2));
    Check(Near(Equinox.SunsetAzimuthDeg, 270.0, 1.2));
    Check(Near(Equinox.NoonAltitudeDeg, 90.0 - JerusalemLatitudeDeg, 0.6));
    Fact("equinox2026SunriseAzimuthDeg", Equinox.SunriseAzimuthDeg);
    Fact("equinox2026SunsetAzimuthDeg", Equinox.SunsetAzimuthDeg);
    Fact("equinox2026NoonAltitudeDeg", Equinox.NoonAltitudeDeg);

    // Solstices: noon altitude is 90 - lat +- obliquity. Jerusalem sees 81.7 and 34.8.
    const FDayEvents June = ComputeDayEvents(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 6, 21, 3.0);
    const FDayEvents December = ComputeDayEvents(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 12, 21, 2.0);
    Check(Near(June.NoonAltitudeDeg, 90.0 - JerusalemLatitudeDeg + 23.44, 0.1));
    Check(Near(December.NoonAltitudeDeg, 90.0 - JerusalemLatitudeDeg - 23.44, 0.1));
    Fact("juneSolstice2026NoonAltitudeDeg", June.NoonAltitudeDeg);
    Fact("decemberSolstice2026NoonAltitudeDeg", December.NoonAltitudeDeg);
    Fact("juneSolstice2026SunriseAzimuthDeg", June.SunriseAzimuthDeg);
    Fact("decemberSolstice2026SunriseAzimuthDeg", December.SunriseAzimuthDeg);
    // Rising point swings roughly 28 degrees either side of east over the year at 31.8 N.
    Check(June.SunriseAzimuthDeg < 65.0 && June.SunriseAzimuthDeg > 58.0);
    Check(December.SunriseAzimuthDeg > 115.0 && December.SunriseAzimuthDeg < 122.0);

    // Day length: longest in June, shortest in December. The two solstice days add to MORE
    // than 24 h, not exactly 24 h: the -0.833 degree horizon lengthens every day by roughly
    // 9 minutes at each end, so the expected sum is about 24.3 h. A sum of exactly 24 would
    // mean refraction and semidiameter had been dropped.
    const double SolsticeSum = June.DayLengthHours + December.DayLengthHours;
    Fact("solsticeDayLengthSumHours", SolsticeSum);
    Check(SolsticeSum > 24.15 && SolsticeSum < 24.45);
    Check(June.DayLengthHours > 14.0 && June.DayLengthHours < 14.4);
    Check(December.DayLengthHours > 10.0 && December.DayLengthHours < 10.2);
    Fact("juneSolstice2026DayLengthHours", June.DayLengthHours);
    Fact("decemberSolstice2026DayLengthHours", December.DayLengthHours);

    // At solar noon the azimuth is due south at this latitude for every date of the year
    // (declination never exceeds the latitude), and the hour angle is zero.
    for (int Month = 1; Month <= 12; ++Month)
    {
        const double Tz = IsraelUtcOffsetHours(2026, Month, 15, 12.0);
        const double Noon = SolarNoonHours(JerusalemLongitudeDeg, 2026, Month, 15, Tz);
        const FSolarAngles A = SolarPosition(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, Month, 15, Noon, Tz);
        Check(Near(A.HourAngleDeg, 0.0, 0.01));
        Check(Near(A.AzimuthDeg, 180.0, 0.05));
    }

    // Saemundsson refraction takes a TRUE altitude, so at h = 0 it is 28.96 arcminutes
    // (0.4827 deg). The 34 arcminute figure belongs to Bennett's inverse formula, whose
    // argument is the apparent altitude; mixing the two is the classic refraction bug.
    Check(Near(AtmosphericRefractionDeg(0.0), 28.96 / 60.0, 0.005));
    Check(AtmosphericRefractionDeg(45.0) < 0.02);
    Check(AtmosphericRefractionDeg(90.0) < 0.005);
    Fact("refractionAtHorizonDeg", AtmosphericRefractionDeg(0.0));

    // Continuity: over one calendar day the altitude curve must have exactly two turning
    // points, a maximum at solar noon and a minimum at solar midnight, with no jitter from
    // an unwrapped hour angle. Sampled every 5 minutes.
    {
        const double Tz = 3.0;
        int Turns = 0;
        double PeakHours = 0.0, PeakAltitude = -1e9;
        double Previous = SolarPosition(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 6, 21, 0.0, Tz).AltitudeDeg;
        double PreviousSlope = 0.0;
        for (int Step = 1; Step <= 24 * 12; ++Step)
        {
            const double Hours = Step / 12.0;
            const double Altitude =
                SolarPosition(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 6, 21, Hours, Tz).AltitudeDeg;
            const double Slope = Altitude - Previous;
            Check(std::fabs(Slope) < 4.0); // no discontinuity: 5 minutes moves the sun < 4 deg
            if (Step > 1 && Slope * PreviousSlope < 0.0) ++Turns;
            if (Altitude > PeakAltitude)
            {
                PeakAltitude = Altitude;
                PeakHours = Hours;
            }
            Previous = Altitude;
            PreviousSlope = Slope;
        }
        Check(Turns == 2);
        const FDayEvents E = ComputeDayEvents(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 6, 21, Tz);
        Check(std::fabs(PeakHours - E.SolarNoonHours) < 1.0 / 12.0);
        Fact("altitudeCurveTurningPoints", double(Turns));
        Fact("altitudePeakHoursJune21", PeakHours);
    }
}

// ---------------------------------------------------------------------------
// 5. Moon
// ---------------------------------------------------------------------------

struct FPhaseReference
{
    int Year, Month, Day;
    double LocalHours;
    double TimeZone;
    const char* Phase; // "new", "full", "first", "last"
};

// USNO "closestphase" instants from the same queries, in Jerusalem wall-clock time.
static const FPhaseReference PhaseReferences[] = {
    {2025, 12, 20, 3.0 + 43.0 / 60.0, 2.0, "new"},
    {2026, 1, 3, 12.0 + 3.0 / 60.0, 2.0, "full"},
    {2026, 3, 19, 3.0 + 23.0 / 60.0, 2.0, "new"},
    {2026, 4, 17, 14.0 + 52.0 / 60.0, 3.0, "new"},
    {2026, 6, 22, 0.0 + 55.0 / 60.0, 3.0, "first"},
    {2026, 8, 12, 20.0 + 37.0 / 60.0, 3.0, "new"},
    {2026, 9, 26, 19.0 + 49.0 / 60.0, 3.0, "full"},
    {2026, 10, 18, 19.0 + 12.0 / 60.0, 3.0, "first"},
    {2026, 12, 24, 3.0 + 28.0 / 60.0, 2.0, "full"},
};
static const int PhaseReferenceCount = int(sizeof(PhaseReferences) / sizeof(PhaseReferences[0]));

static void TestMoon()
{
    double WorstIllumError = 0.0;
    double WorstPhaseAngleError = 0.0;

    for (int I = 0; I < PhaseReferenceCount; ++I)
    {
        const FPhaseReference& R = PhaseReferences[I];
        const FMoonState M = MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, R.Year, R.Month, R.Day, R.LocalHours,
                                       R.TimeZone);
        char Prefix[64];
        std::snprintf(Prefix, sizeof(Prefix), "moon.%04d-%02d-%02d.%s", R.Year, R.Month, R.Day, R.Phase);
        const std::string P(Prefix);

        Fact(P + ".illuminatedFraction", M.IlluminatedFraction);
        Fact(P + ".ageDays", M.AgeDays);
        Fact(P + ".elongationDeg", M.ElongationDeg);
        Fact(P + ".phaseAngleDeg", M.PhaseAngleDeg);

        const std::string Kind(R.Phase);
        double ExpectedIllum = 0.0, ExpectedElongation = 0.0;
        if (Kind == "new") { ExpectedIllum = 0.0; ExpectedElongation = 0.0; }
        else if (Kind == "full") { ExpectedIllum = 1.0; ExpectedElongation = 180.0; }
        else if (Kind == "first") { ExpectedIllum = 0.5; ExpectedElongation = 90.0; }
        else { ExpectedIllum = 0.5; ExpectedElongation = 270.0; }

        const double IllumError = std::fabs(M.IlluminatedFraction - ExpectedIllum);
        const double ElongationError = std::fabs(Wrap180(M.ElongationDeg - ExpectedElongation));
        if (IllumError > WorstIllumError) WorstIllumError = IllumError;
        if (ElongationError > WorstPhaseAngleError) WorstPhaseAngleError = ElongationError;

        std::printf("  moon %04d-%02d-%02d %-5s  illum %6.4f (want %4.2f)  elongation %7.3f deg (want %5.1f)  "
                    "age %6.3f d\n",
                    R.Year, R.Month, R.Day, R.Phase, M.IlluminatedFraction, ExpectedIllum, M.ElongationDeg,
                    ExpectedElongation, M.AgeDays);

        // The truncated series must land within a degree of the true syzygy geometry.
        Check(ElongationError < 1.0);
        Check(IllumError < 0.01);
    }
    Fact("moonWorstIlluminationError", WorstIllumError);
    Fact("moonWorstElongationErrorDeg", WorstPhaseAngleError);

    // Waxing/waning must flip at full moon: 2026-09-26 19:49 local.
    Check(MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 9, 25, 20.0, 3.0).bWaxing);
    Check(!MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 9, 27, 20.0, 3.0).bWaxing);

    // Age must sweep a full synodic month and wrap. Sample a whole lunation.
    double PreviousAge = MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 3, 19, 4.0, 2.0).AgeDays;
    int Wraps = 0;
    for (int DayIndex = 1; DayIndex <= 30; ++DayIndex)
    {
        int Month = 3, Day = 19 + DayIndex;
        while (Day > DaysInMonth(2026, Month)) { Day -= DaysInMonth(2026, Month); ++Month; }
        const double Tz = IsraelUtcOffsetHours(2026, Month, Day, 4.0);
        const double Age = MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, Month, Day, 4.0, Tz).AgeDays;
        if (Age < PreviousAge) ++Wraps;
        PreviousAge = Age;
        Check(Age >= 0.0 && Age <= SynodicMonthDays + 1e-9);
    }
    Check(Wraps == 1);
    FactInt("moonLunationWraps", Wraps);

    // Moon altitude must behave: a full moon is roughly opposite the sun, so at local
    // midnight near full moon it is high, and near new moon it is below the horizon.
    const FMoonState FullMidnight = MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 9, 27, 0.0, 3.0);
    const FMoonState NewMidnight = MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 8, 12, 0.0, 3.0);
    Check(FullMidnight.AltitudeDeg > 20.0);
    Check(NewMidnight.AltitudeDeg < 0.0);
    Fact("moonFullMidnightAltitudeDeg", FullMidnight.AltitudeDeg);
    Fact("moonNewMidnightAltitudeDeg", NewMidnight.AltitudeDeg);

    // USNO gave moonrise 06:49 and moonset 20:42 on 2026-03-21 (tz +2). Rather than
    // reimplementing a rise/set solver for the moon, check the altitude sign either side of
    // those instants: a crossing that is more than a few minutes off would show here.
    const double RiseHours = 6.0 + 49.0 / 60.0;
    Check(MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 3, 21, RiseHours - 0.25, 2.0).RefractedAltitudeDeg < 0.0);
    Check(MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 3, 21, RiseHours + 0.25, 2.0).RefractedAltitudeDeg > 0.0);
    const double SetHours = 20.0 + 42.0 / 60.0;
    Check(MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 3, 21, SetHours - 0.25, 2.0).RefractedAltitudeDeg > 0.0);
    Check(MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 3, 21, SetHours + 0.25, 2.0).RefractedAltitudeDeg < 0.0);

    // USNO fracillum for 2026-03-21 was 7 percent; for 2026-12-21, 90 percent.
    const double Illum0321 = MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 3, 21, 12.0, 2.0).IlluminatedFraction;
    const double Illum1221 = MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, 12, 21, 12.0, 2.0).IlluminatedFraction;
    Fact("moon.2026-03-21T12.illuminatedFraction", Illum0321);
    Fact("moon.2026-12-21T12.illuminatedFraction", Illum1221);
    Check(Near(Illum0321, 0.07, 0.03));
    Check(Near(Illum1221, 0.90, 0.03));
}

// ---------------------------------------------------------------------------
// 6. Presentation helpers used by AMikdashTimeOfDay
// ---------------------------------------------------------------------------

static void TestPresentationHelpers()
{
    // World frame: +X east, +Y south, +Z up. A sun due east at the horizon must travel
    // west, i.e. -X; a sun overhead must travel straight down.
    double Pitch = 0, Yaw = 0, Roll = 0;
    LightRotationForSky(90.0, 0.0, Pitch, Yaw, Roll);
    Check(Near(Pitch, 0.0, 1e-9));
    Check(Near(std::fabs(Wrap180(Yaw - 180.0)), 0.0, 1e-9)); // travel along -X
    LightRotationForSky(90.0, 90.0, Pitch, Yaw, Roll);
    Check(Near(Pitch, -90.0, 1e-9));
    LightRotationForSky(180.0, 30.0, Pitch, Yaw, Roll); // due south, 30 up: travels north (-Y)
    Check(Near(Pitch, -30.0, 1e-9));
    Check(Near(std::fabs(Wrap180(Yaw - (-90.0))), 0.0, 1e-6));

    // Verify against the direction the previous lighting pass recorded for its morning sun
    // (azimuth 110, elevation 30 -> rotator pitch -30, yaw -160).
    LightRotationForSky(110.0, 30.0, Pitch, Yaw, Roll);
    Check(Near(Pitch, -30.0, 1e-9));
    Check(Near(Wrap180(Yaw + 160.0), 0.0, 1e-6));
    Fact("morningPresetYawDeg", Yaw);

    // Preset hours must be ordered through the day and derived from the real events.
    const FDayEvents E = JerusalemDayEvents(2026, 6, 21);
    Check(PresetHours(E, ETimePreset::Dawn) < PresetHours(E, ETimePreset::Sunrise));
    Check(PresetHours(E, ETimePreset::Sunrise) < PresetHours(E, ETimePreset::Morning));
    Check(PresetHours(E, ETimePreset::Morning) < PresetHours(E, ETimePreset::Midday));
    Check(PresetHours(E, ETimePreset::Midday) < PresetHours(E, ETimePreset::Afternoon));
    Check(PresetHours(E, ETimePreset::Afternoon) < PresetHours(E, ETimePreset::Sunset));
    Check(PresetHours(E, ETimePreset::Sunset) < PresetHours(E, ETimePreset::Dusk));
    Fact("preset.2026-06-21.dawnHours", PresetHours(E, ETimePreset::Dawn));
    Fact("preset.2026-06-21.sunriseHours", PresetHours(E, ETimePreset::Sunrise));
    Fact("preset.2026-06-21.morningHours", PresetHours(E, ETimePreset::Morning));
    Fact("preset.2026-06-21.middayHours", PresetHours(E, ETimePreset::Midday));
    Fact("preset.2026-06-21.afternoonHours", PresetHours(E, ETimePreset::Afternoon));
    Fact("preset.2026-06-21.sunsetHours", PresetHours(E, ETimePreset::Sunset));
    Fact("preset.2026-06-21.duskHours", PresetHours(E, ETimePreset::Dusk));
    Fact("preset.2026-06-21.nightHours", PresetHours(E, ETimePreset::Night));

    // The morning preset must actually be a mid-morning sun, not an arbitrary angle.
    const FSolarAngles Morning = JerusalemSolarPosition(2026, 6, 21, PresetHours(E, ETimePreset::Morning));
    Check(Morning.AltitudeDeg > 30.0 && Morning.AltitudeDeg < 60.0);
    Fact("preset.2026-06-21.morningAltitudeDeg", Morning.AltitudeDeg);

    // Normalized time round trip.
    for (int Step = 0; Step < 24 * 4; ++Step)
    {
        const double Hours = Step / 4.0;
        Check(Near(HoursFromNormalizedTime(NormalizedTimeFromHours(Hours)), Hours, 1e-9));
    }
    Check(Near(Wrap24(-1.0), 23.0, 1e-12));
    Check(Near(Wrap24(25.5), 1.5, 1e-12));
    Check(Near(Wrap360(-10.0), 350.0, 1e-12));
    Check(Near(Wrap180(190.0), -170.0, 1e-12));
}

// ---------------------------------------------------------------------------
// 7. Dawn over the Mount: the money shot has to be reachable
// ---------------------------------------------------------------------------

static void TestDawnOverTheMount()
{
    // Sunrise azimuth across the year at Jerusalem must stay inside the eastern quadrant
    // and never invert, and the day must always have a dawn.
    double MinAz = 1e9, MaxAz = -1e9;
    for (int Month = 1; Month <= 12; ++Month)
    {
        for (int Day = 1; Day <= DaysInMonth(2026, Month); ++Day)
        {
            const double Tz = IsraelUtcOffsetHours(2026, Month, Day, 12.0);
            const FDayEvents E = ComputeDayEvents(JerusalemLatitudeDeg, JerusalemLongitudeDeg, 2026, Month, Day, Tz);
            Check(E.bSunriseValid && E.bSunsetValid && E.bCivilDawnValid && E.bCivilDuskValid);
            Check(E.SunriseHours > 4.0 && E.SunriseHours < 8.0);
            Check(E.SunsetHours > 16.0 && E.SunsetHours < 21.0);
            Check(E.CivilDawnHours < E.SunriseHours && E.SunriseHours - E.CivilDawnHours < 0.6);
            if (E.SunriseAzimuthDeg < MinAz) MinAz = E.SunriseAzimuthDeg;
            if (E.SunriseAzimuthDeg > MaxAz) MaxAz = E.SunriseAzimuthDeg;
        }
    }
    Check(MinAz > 55.0 && MaxAz < 125.0);
    Fact("sunriseAzimuthMinDeg2026", MinAz);
    Fact("sunriseAzimuthMaxDeg2026", MaxAz);

    // Civil twilight length at Jerusalem is about 22-27 minutes.
    const FDayEvents Summer = JerusalemDayEvents(2026, 6, 21);
    const FDayEvents Winter = JerusalemDayEvents(2026, 12, 21);
    const double SummerTwilight = (Summer.SunriseHours - Summer.CivilDawnHours) * 60.0;
    const double WinterTwilight = (Winter.SunriseHours - Winter.CivilDawnHours) * 60.0;
    Check(SummerTwilight > 22.0 && SummerTwilight < 32.0);
    Check(WinterTwilight > 22.0 && WinterTwilight < 32.0);
    Fact("civilTwilightMinutesJune", SummerTwilight);
    Fact("civilTwilightMinutesDecember", WinterTwilight);
}

// ---------------------------------------------------------------------------

int main(int ArgCount, char** Args)
{
    std::printf("SunPositionMath standalone test (Jerusalem %.4f N, %.4f E)\n", JerusalemLatitudeDeg,
                JerusalemLongitudeDeg);
    std::printf("Reference: US Naval Observatory api/rstt/oneday, sea level, -0.833 deg horizon.\n\n");

    TestCalendar();
    TestIsraeliClock();
    TestEquationOfTimeAndDeclination();

    std::printf("Sun events vs USNO published minutes:\n");
    FAccuracySummary Summary;
    TestPublishedTimes(Summary);
    std::printf("\n");

    TestAltitudeAzimuth();

    std::printf("Moon phase vs USNO phase instants:\n");
    TestMoon();
    std::printf("\n");

    TestPresentationHelpers();
    TestDawnOverTheMount();

    std::printf("worst sunrise error %.2f min, worst sunset error %.2f min, worst solar noon error %.2f min,\n"
                "worst civil twilight error %.2f min over %d reference days (worst day %s)\n",
                Summary.WorstRise, Summary.WorstSet, Summary.WorstNoon, Summary.WorstTwilight, ReferenceCount,
                Summary.WorstAnyLabel.c_str());
    std::printf("%lld checks passed\n", CheckCount);

    FactInt("checksPassed", CheckCount);
    FactText("status", "pass");
    FactText("referenceSource", "US Naval Observatory api/rstt/oneday v4.0.1, queried 2026-09-08");
    FactText("referenceConvention", "sea level, -0.8333 deg horizon; Jerusalem's 750 m elevation is deliberately not modelled");

    if (ArgCount > 1)
    {
        FILE* File = std::fopen(Args[1], "wb");
        if (!File)
        {
            std::fprintf(stderr, "cannot write %s\n", Args[1]);
            return 2;
        }
        std::fprintf(File, "{\n");
        for (size_t I = 0; I < Facts.size(); ++I)
        {
            std::fprintf(File, "  \"%s\": %s%s\n", Facts[I].first.c_str(), Facts[I].second.c_str(),
                         I + 1 < Facts.size() ? "," : "");
        }
        std::fprintf(File, "}\n");
        std::fclose(File);
        std::printf("wrote %s\n", Args[1]);
    }
    return 0;
}
