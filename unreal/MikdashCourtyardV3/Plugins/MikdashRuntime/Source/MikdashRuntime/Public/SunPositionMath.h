#pragma once
#include <cmath>

// Engine-independent solar and lunar position maths for the Mikdash time-of-day system.
// No Unreal types, no engine headers: AMikdashTimeOfDay and the standalone test in
// Plugins/MikdashRuntime/Tests/SunPositionMathTest.cpp both compile against this file.
//
// Algorithm: NOAA Solar Calculator (the Astronomical Almanac's low-precision solar
// coordinates, as published by NOAA ESRL/GML), with the event solvers iterated so the
// declination and equation of time are evaluated AT the event rather than at local noon.
// Reference altitude for sunrise/sunset is -0.833 degrees (34' mean refraction plus the
// 16' semidiameter of the disc), the same convention the US Naval Observatory uses, so
// computed times are directly comparable with USNO published rise/set times at sea level.
//
// Deliberately NOT modelled: observer elevation (Jerusalem sits at ~750 m, which makes the
// real horizon dip and moves true rise/set about 4-5 minutes earlier/later than the
// sea-level figure), refraction anomalies, and the topography of the Mount of Olives to
// the east. Those are stated in the test evidence rather than silently absorbed.
//
// Units: degrees for all angles, hours (0..24) for all civil times, days for moon age.
// Azimuth is compass azimuth: 0 = north, 90 = east, measured clockwise. Altitude is the
// geometric angle above the true horizon unless a function says "Refracted".
namespace MikdashSun
{
constexpr double Pi = 3.14159265358979323846;
constexpr double Deg2Rad = Pi / 180.0;
constexpr double Rad2Deg = 180.0 / Pi;

// The Temple Mount. Latitude north, longitude EAST positive.
constexpr double JerusalemLatitudeDeg = 31.7767;
constexpr double JerusalemLongitudeDeg = 35.2345;

// Standard event altitudes.
constexpr double SunriseAltitudeDeg = -0.833;   // upper limb on the horizon, mean refraction
constexpr double CivilTwilightAltitudeDeg = -6.0;
constexpr double NauticalTwilightAltitudeDeg = -12.0;
constexpr double AstronomicalTwilightAltitudeDeg = -18.0;

constexpr double SynodicMonthDays = 29.530588853;

inline double Rad(double Degrees) { return Degrees * Deg2Rad; }
inline double Deg(double Radians) { return Radians * Rad2Deg; }

/** Wrap to [0, 360). */
inline double Wrap360(double Degrees)
{
    double W = std::fmod(Degrees, 360.0);
    if (W < 0.0) W += 360.0;
    return W;
}

/** Wrap to [-180, 180). */
inline double Wrap180(double Degrees) { return Wrap360(Degrees + 180.0) - 180.0; }

/** Wrap to [0, 24). */
inline double Wrap24(double Hours)
{
    double W = std::fmod(Hours, 24.0);
    if (W < 0.0) W += 24.0;
    return W;
}

inline double Clamp(double V, double Lo, double Hi) { return V < Lo ? Lo : (V > Hi ? Hi : V); }

// ---------------------------------------------------------------------------
// Calendar
// ---------------------------------------------------------------------------

/** Proleptic Gregorian day number, 0 = Monday. Sakamoto's algorithm. */
inline int DayOfWeekMondayZero(int Year, int Month, int Day)
{
    static const int Table[12] = {0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4};
    int Y = Year;
    if (Month < 3) Y -= 1;
    const int W = (Y + Y / 4 - Y / 100 + Y / 400 + Table[Month - 1] + Day) % 7; // 0 = Sunday
    return (W + 6) % 7;                                                        // 0 = Monday
}

/** 0 = Sunday .. 6 = Saturday. */
inline int DayOfWeekSundayZero(int Year, int Month, int Day)
{
    return (DayOfWeekMondayZero(Year, Month, Day) + 1) % 7;
}

inline bool IsLeapYear(int Year)
{
    return (Year % 4 == 0 && Year % 100 != 0) || (Year % 400 == 0);
}

inline int DaysInMonth(int Year, int Month)
{
    static const int Days[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (Month == 2 && IsLeapYear(Year)) return 29;
    return Days[Month - 1];
}

/** Day of the year, 1 = 1 January. */
inline int DayOfYear(int Year, int Month, int Day)
{
    int N = Day;
    for (int M = 1; M < Month; ++M) N += DaysInMonth(Year, M);
    return N;
}

/** Day-of-month of the last given weekday (0 = Sunday) in a month. */
inline int LastWeekdayOfMonth(int Year, int Month, int WeekdaySundayZero)
{
    const int Last = DaysInMonth(Year, Month);
    const int LastDow = DayOfWeekSundayZero(Year, Month, Last);
    int Back = (LastDow - WeekdaySundayZero + 7) % 7;
    return Last - Back;
}

/** Julian Day for a Gregorian calendar date and a UTC time of day. Meeus 7.1. */
inline double JulianDayFromUtc(int Year, int Month, int Day, double UtcHours)
{
    int Y = Year;
    int M = Month;
    if (M <= 2)
    {
        Y -= 1;
        M += 12;
    }
    const int A = Y / 100;
    const int B = 2 - A + A / 4;
    const double JD = std::floor(365.25 * (Y + 4716)) + std::floor(30.6001 * (M + 1)) + Day + B - 1524.5;
    return JD + UtcHours / 24.0;
}

inline double JulianCentury(double JulianDay) { return (JulianDay - 2451545.0) / 36525.0; }

// ---------------------------------------------------------------------------
// Israel civil time
// ---------------------------------------------------------------------------

/** Israel Daylight Time, per the 2013 amendment to the Time Determination Law that is
 * still in force: IDT begins at 02:00 local on the FRIDAY BEFORE the last Sunday of March
 * and ends at 02:00 local on the last Sunday of October. Verified against the IANA tz
 * database for 2026 (27 Mar -> 25 Oct) and 2027 (26 Mar -> 31 Oct). Local hours are
 * interpreted as the wall clock reading, so the ambiguous hour at the October fall-back
 * resolves to standard time, which is what a scrubbing time-of-day slider wants. */
inline bool IsIsraelDaylightSaving(int Year, int Month, int Day, double LocalHours)
{
    if (Month < 3 || Month > 10) return false;
    if (Month > 3 && Month < 10) return true;

    if (Month == 3)
    {
        const int LastSunday = LastWeekdayOfMonth(Year, 3, 0);
        const int StartDay = LastSunday - 2; // the Friday before
        if (Day > StartDay) return true;
        if (Day < StartDay) return false;
        return LocalHours >= 2.0;
    }

    const int EndDay = LastWeekdayOfMonth(Year, 10, 0);
    if (Day < EndDay) return true;
    if (Day > EndDay) return false;
    return LocalHours < 2.0;
}

/** UTC offset in hours for Jerusalem wall-clock time: +2 (IST) or +3 (IDT). */
inline double IsraelUtcOffsetHours(int Year, int Month, int Day, double LocalHours)
{
    return IsIsraelDaylightSaving(Year, Month, Day, LocalHours) ? 3.0 : 2.0;
}

// ---------------------------------------------------------------------------
// Solar coordinates (NOAA / Astronomical Almanac low precision)
// ---------------------------------------------------------------------------

/** Geometric mean longitude of the sun, degrees, wrapped. */
inline double GeometricMeanLongitudeSunDeg(double T)
{
    return Wrap360(280.46646 + T * (36000.76983 + T * 0.0003032));
}

/** Geometric mean anomaly of the sun, degrees (not wrapped: used inside trig only). */
inline double GeometricMeanAnomalySunDeg(double T)
{
    return 357.52911 + T * (35999.05029 - 0.0001537 * T);
}

/** Eccentricity of Earth's orbit. */
inline double EarthOrbitEccentricity(double T)
{
    return 0.016708634 - T * (0.000042037 + 0.0000001267 * T);
}

/** Sun's equation of the centre, degrees. */
inline double SunEquationOfCentreDeg(double T)
{
    const double M = Rad(GeometricMeanAnomalySunDeg(T));
    return std::sin(M) * (1.914602 - T * (0.004817 + 0.000014 * T)) + std::sin(2.0 * M) * (0.019993 - 0.000101 * T) +
           std::sin(3.0 * M) * 0.000289;
}

inline double SunTrueLongitudeDeg(double T) { return GeometricMeanLongitudeSunDeg(T) + SunEquationOfCentreDeg(T); }

/** Apparent longitude of the sun, degrees (nutation and aberration applied). */
inline double SunApparentLongitudeDeg(double T)
{
    return SunTrueLongitudeDeg(T) - 0.00569 - 0.00478 * std::sin(Rad(125.04 - 1934.136 * T));
}

/** Mean obliquity of the ecliptic, degrees. */
inline double MeanObliquityOfEclipticDeg(double T)
{
    return 23.0 + (26.0 + ((21.448 - T * (46.815 + T * (0.00059 - T * 0.001813)))) / 60.0) / 60.0;
}

/** Obliquity corrected for nutation, degrees. */
inline double ObliquityCorrectedDeg(double T)
{
    return MeanObliquityOfEclipticDeg(T) + 0.00256 * std::cos(Rad(125.04 - 1934.136 * T));
}

/** Solar declination, degrees, for a Julian Day. */
inline double SolarDeclinationDeg(double JulianDay)
{
    const double T = JulianCentury(JulianDay);
    const double Lambda = Rad(SunApparentLongitudeDeg(T));
    const double Eps = Rad(ObliquityCorrectedDeg(T));
    return Deg(std::asin(std::sin(Eps) * std::sin(Lambda)));
}

/** Solar right ascension, degrees [0,360), for a Julian Day. */
inline double SolarRightAscensionDeg(double JulianDay)
{
    const double T = JulianCentury(JulianDay);
    const double Lambda = Rad(SunApparentLongitudeDeg(T));
    const double Eps = Rad(ObliquityCorrectedDeg(T));
    return Wrap360(Deg(std::atan2(std::cos(Eps) * std::sin(Lambda), std::cos(Lambda))));
}

/** Equation of time in MINUTES (apparent solar time minus mean solar time). */
inline double EquationOfTimeMinutes(double JulianDay)
{
    const double T = JulianCentury(JulianDay);
    const double Eps = Rad(ObliquityCorrectedDeg(T));
    const double L0 = Rad(GeometricMeanLongitudeSunDeg(T));
    const double M = Rad(GeometricMeanAnomalySunDeg(T));
    const double E = EarthOrbitEccentricity(T);
    const double Y = std::tan(Eps / 2.0) * std::tan(Eps / 2.0);

    const double EqTime = Y * std::sin(2.0 * L0) - 2.0 * E * std::sin(M) + 4.0 * E * Y * std::sin(M) * std::cos(2.0 * L0) -
                          0.5 * Y * Y * std::sin(4.0 * L0) - 1.25 * E * E * std::sin(2.0 * M);
    return 4.0 * Deg(EqTime);
}

/** Saemundsson's refraction (Meeus 16.3), in degrees, to be ADDED to a geometric altitude
 * to get the apparent one. Its argument is the true altitude, so at h = 0 it returns 28.96
 * arcminutes (0.483 deg), not the 34 arcminutes that Bennett's inverse formula returns for
 * an APPARENT altitude of 0. The two are consistent; they answer different questions.
 * Presentation only: sunrise and sunset use the fixed -0.833 deg horizon instead, and the
 * formula is not trustworthy below about -1 deg. */
inline double AtmosphericRefractionDeg(double GeometricAltitudeDeg)
{
    if (GeometricAltitudeDeg < -1.0) return 0.0;
    const double H = GeometricAltitudeDeg;
    return (1.02 / std::tan(Rad(H + 10.3 / (H + 5.11)))) / 60.0;
}

struct FSolarAngles
{
    double AltitudeDeg = 0.0;          // geometric altitude above the true horizon
    double RefractedAltitudeDeg = 0.0; // altitude an observer sees
    double AzimuthDeg = 0.0;           // compass azimuth, 0 = N, 90 = E
    double DeclinationDeg = 0.0;
    double EquationOfTimeMinutes = 0.0;
    double HourAngleDeg = 0.0; // 0 at solar noon, positive in the afternoon
    double JulianDay = 0.0;
};

/** Hour angle (0..180 degrees) at which the sun's altitude equals TargetAltitudeDeg.
 * bValid is false when the sun never reaches that altitude on the given day (polar cases;
 * never true at Jerusalem's latitude, but the caller must still be able to tell). */
inline double HourAngleForAltitudeDeg(double LatitudeDeg, double DeclinationDeg, double TargetAltitudeDeg, bool& bValid)
{
    const double Lat = Rad(LatitudeDeg);
    const double Dec = Rad(DeclinationDeg);
    const double CosH = (std::sin(Rad(TargetAltitudeDeg)) - std::sin(Lat) * std::sin(Dec)) / (std::cos(Lat) * std::cos(Dec));
    bValid = (CosH >= -1.0 && CosH <= 1.0);
    return Deg(std::acos(Clamp(CosH, -1.0, 1.0)));
}

/** Sun altitude/azimuth for a wall-clock civil time at a location.
 * TimeZoneOffsetHours is the offset of that wall clock from UTC (Jerusalem: +2 or +3). */
inline FSolarAngles SolarPosition(double LatitudeDeg, double LongitudeDeg, int Year, int Month, int Day, double LocalHours,
                                  double TimeZoneOffsetHours)
{
    FSolarAngles Out;
    Out.JulianDay = JulianDayFromUtc(Year, Month, Day, LocalHours - TimeZoneOffsetHours);

    const double EqTime = EquationOfTimeMinutes(Out.JulianDay);
    const double Dec = SolarDeclinationDeg(Out.JulianDay);
    Out.EquationOfTimeMinutes = EqTime;
    Out.DeclinationDeg = Dec;

    // True solar time in minutes past local midnight, then hour angle.
    const double TrueSolarMinutes = LocalHours * 60.0 + EqTime + 4.0 * LongitudeDeg - 60.0 * TimeZoneOffsetHours;
    double HourAngle = TrueSolarMinutes / 4.0 - 180.0;
    HourAngle = Wrap180(HourAngle);
    Out.HourAngleDeg = HourAngle;

    const double Lat = Rad(LatitudeDeg);
    const double D = Rad(Dec);
    const double H = Rad(HourAngle);

    const double SinAlt = std::sin(Lat) * std::sin(D) + std::cos(Lat) * std::cos(D) * std::cos(H);
    Out.AltitudeDeg = Deg(std::asin(Clamp(SinAlt, -1.0, 1.0)));
    Out.RefractedAltitudeDeg = Out.AltitudeDeg + AtmosphericRefractionDeg(Out.AltitudeDeg);

    // Azimuth measured from south, then rotated to a compass bearing.
    const double AzFromSouth = Deg(std::atan2(std::sin(H), std::cos(H) * std::sin(Lat) - std::tan(D) * std::cos(Lat)));
    Out.AzimuthDeg = Wrap360(AzFromSouth + 180.0);
    return Out;
}

/** Local solar noon in wall-clock hours, iterated so the equation of time is evaluated at
 * noon itself rather than at midnight. */
inline double SolarNoonHours(double LongitudeDeg, int Year, int Month, int Day, double TimeZoneOffsetHours)
{
    double Noon = 12.0;
    for (int Iteration = 0; Iteration < 4; ++Iteration)
    {
        const double JD = JulianDayFromUtc(Year, Month, Day, Noon - TimeZoneOffsetHours);
        const double EqTime = EquationOfTimeMinutes(JD);
        Noon = (720.0 - 4.0 * LongitudeDeg - EqTime) / 60.0 + TimeZoneOffsetHours;
    }
    return Noon;
}

/** One solar event (rising or setting) at a target altitude, in wall-clock hours.
 * bRising selects the morning branch. bValid is false when the event does not occur.
 * Iterated three times: the first pass uses the declination at local noon, later passes
 * use the declination at the event, which is what removes the ~30 s error that a
 * single-pass NOAA spreadsheet carries. */
inline double SolarEventHours(double LatitudeDeg, double LongitudeDeg, int Year, int Month, int Day, double TargetAltitudeDeg,
                              bool bRising, double TimeZoneOffsetHours, bool& bValid)
{
    const double Noon = SolarNoonHours(LongitudeDeg, Year, Month, Day, TimeZoneOffsetHours);
    double Event = bRising ? Noon - 6.0 : Noon + 6.0;
    bValid = true;

    for (int Iteration = 0; Iteration < 4; ++Iteration)
    {
        const double JD = JulianDayFromUtc(Year, Month, Day, Event - TimeZoneOffsetHours);
        const double Dec = SolarDeclinationDeg(JD);
        const double EqTime = EquationOfTimeMinutes(JD);
        bool bReachable = true;
        const double HourAngle = HourAngleForAltitudeDeg(LatitudeDeg, Dec, TargetAltitudeDeg, bReachable);
        if (!bReachable)
        {
            bValid = false;
            return bRising ? 0.0 : 24.0;
        }
        const double NoonNow = (720.0 - 4.0 * LongitudeDeg - EqTime) / 60.0 + TimeZoneOffsetHours;
        Event = bRising ? NoonNow - HourAngle / 15.0 : NoonNow + HourAngle / 15.0;
    }
    return Event;
}

struct FDayEvents
{
    double SolarNoonHours = 12.0;
    double SunriseHours = 6.0;
    double SunsetHours = 18.0;
    double CivilDawnHours = 5.5;
    double CivilDuskHours = 18.5;
    double DayLengthHours = 12.0;
    double SunriseAzimuthDeg = 90.0;
    double SunsetAzimuthDeg = 270.0;
    double NoonAltitudeDeg = 45.0;
    bool bSunriseValid = true;
    bool bSunsetValid = true;
    bool bCivilDawnValid = true;
    bool bCivilDuskValid = true;
};

/** Sunrise, sunset, civil twilight and solar noon for one calendar day, all in wall-clock
 * hours for TimeZoneOffsetHours. */
inline FDayEvents ComputeDayEvents(double LatitudeDeg, double LongitudeDeg, int Year, int Month, int Day,
                                   double TimeZoneOffsetHours)
{
    FDayEvents Out;
    Out.SolarNoonHours = SolarNoonHours(LongitudeDeg, Year, Month, Day, TimeZoneOffsetHours);
    Out.SunriseHours = SolarEventHours(LatitudeDeg, LongitudeDeg, Year, Month, Day, SunriseAltitudeDeg, true,
                                       TimeZoneOffsetHours, Out.bSunriseValid);
    Out.SunsetHours = SolarEventHours(LatitudeDeg, LongitudeDeg, Year, Month, Day, SunriseAltitudeDeg, false,
                                      TimeZoneOffsetHours, Out.bSunsetValid);
    Out.CivilDawnHours = SolarEventHours(LatitudeDeg, LongitudeDeg, Year, Month, Day, CivilTwilightAltitudeDeg, true,
                                         TimeZoneOffsetHours, Out.bCivilDawnValid);
    Out.CivilDuskHours = SolarEventHours(LatitudeDeg, LongitudeDeg, Year, Month, Day, CivilTwilightAltitudeDeg, false,
                                         TimeZoneOffsetHours, Out.bCivilDuskValid);
    Out.DayLengthHours = Out.SunsetHours - Out.SunriseHours;

    Out.SunriseAzimuthDeg =
        SolarPosition(LatitudeDeg, LongitudeDeg, Year, Month, Day, Out.SunriseHours, TimeZoneOffsetHours).AzimuthDeg;
    Out.SunsetAzimuthDeg =
        SolarPosition(LatitudeDeg, LongitudeDeg, Year, Month, Day, Out.SunsetHours, TimeZoneOffsetHours).AzimuthDeg;
    Out.NoonAltitudeDeg =
        SolarPosition(LatitudeDeg, LongitudeDeg, Year, Month, Day, Out.SolarNoonHours, TimeZoneOffsetHours).AltitudeDeg;
    return Out;
}

/** Jerusalem convenience wrappers: latitude, longitude and the Israeli clock are implied. */
inline FDayEvents JerusalemDayEvents(int Year, int Month, int Day)
{
    return ComputeDayEvents(JerusalemLatitudeDeg, JerusalemLongitudeDeg, Year, Month, Day,
                            IsraelUtcOffsetHours(Year, Month, Day, 12.0));
}

inline FSolarAngles JerusalemSolarPosition(int Year, int Month, int Day, double LocalHours)
{
    return SolarPosition(JerusalemLatitudeDeg, JerusalemLongitudeDeg, Year, Month, Day, LocalHours,
                         IsraelUtcOffsetHours(Year, Month, Day, LocalHours));
}

// ---------------------------------------------------------------------------
// Moon
// ---------------------------------------------------------------------------

/** Greenwich mean sidereal time in degrees. Meeus 12.4. */
inline double GreenwichMeanSiderealTimeDeg(double JulianDay)
{
    const double D = JulianDay - 2451545.0;
    const double T = D / 36525.0;
    return Wrap360(280.46061837 + 360.98564736629 * D + 0.000387933 * T * T - T * T * T / 38710000.0);
}

struct FMoonState
{
    double AgeDays = 0.0;              // days since the last new moon
    double PhaseFraction = 0.0;        // 0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter
    double IlluminatedFraction = 0.0;  // 0..1 of the disc lit
    double PhaseAngleDeg = 180.0;      // sun-moon-earth angle; 180 = new, 0 = full
    double ElongationDeg = 0.0;        // moon minus sun apparent longitude, 0..360
    bool bWaxing = true;
    double EclipticLongitudeDeg = 0.0;
    double EclipticLatitudeDeg = 0.0;
    double DistanceKm = 385000.0;
    double AltitudeDeg = 0.0;          // topocentric, parallax applied
    double RefractedAltitudeDeg = 0.0;
    double AzimuthDeg = 0.0;
    /** Position angle of the bright limb, degrees east of north; the terminator is
     * perpendicular to it. Drives which way a crescent points. */
    double BrightLimbAngleDeg = 0.0;
};

/** Moon position and phase. Truncated Meeus (Astronomical Algorithms ch. 47 and 48):
 * the principal periodic terms only. Longitude is good to roughly 0.1-0.2 degrees and the
 * illuminated fraction to about half a percent, which is far finer than a rendered disc
 * needs; it is not an ephemeris for occultation work. */
inline FMoonState MoonState(double LatitudeDeg, double LongitudeDeg, int Year, int Month, int Day, double LocalHours,
                            double TimeZoneOffsetHours)
{
    FMoonState Out;
    const double JD = JulianDayFromUtc(Year, Month, Day, LocalHours - TimeZoneOffsetHours);
    const double T = JulianCentury(JD);

    // Mean elements.
    const double Lp = Wrap360(218.3164477 + 481267.88123421 * T - 0.0015786 * T * T + T * T * T / 538841.0 -
                              T * T * T * T / 65194000.0);
    const double D = Wrap360(297.8501921 + 445267.1114034 * T - 0.0018819 * T * T + T * T * T / 545868.0 -
                             T * T * T * T / 113065000.0);
    const double M = Wrap360(357.5291092 + 35999.0502909 * T - 0.0001536 * T * T + T * T * T / 24490000.0);
    const double Mp = Wrap360(134.9633964 + 477198.8675055 * T + 0.0087414 * T * T + T * T * T / 69699.0 -
                              T * T * T * T / 14712000.0);
    const double F = Wrap360(93.2720950 + 483202.0175233 * T - 0.0036539 * T * T - T * T * T / 3526000.0 +
                             T * T * T * T / 863310000.0);

    const double dR = Rad(D), mR = Rad(M), mpR = Rad(Mp), fR = Rad(F);

    const double LonCorrection = 6.288774 * std::sin(mpR) + 1.274027 * std::sin(2 * dR - mpR) + 0.658314 * std::sin(2 * dR) +
                                 0.213618 * std::sin(2 * mpR) - 0.185116 * std::sin(mR) - 0.114332 * std::sin(2 * fR) +
                                 0.058793 * std::sin(2 * dR - 2 * mpR) + 0.057066 * std::sin(2 * dR - mR - mpR) +
                                 0.053322 * std::sin(2 * dR + mpR) + 0.045758 * std::sin(2 * dR - mR) +
                                 0.041024 * std::sin(mpR - mR) - 0.034720 * std::sin(dR) - 0.030465 * std::sin(mR + mpR) +
                                 0.015327 * std::sin(2 * dR - 2 * fR) - 0.012528 * std::sin(mpR + 2 * fR) +
                                 0.010980 * std::sin(mpR - 2 * fR) + 0.010675 * std::sin(4 * dR - mpR) +
                                 0.010034 * std::sin(3 * mpR) + 0.008548 * std::sin(4 * dR - 2 * mpR);

    const double LatTerms = 5.128122 * std::sin(fR) + 0.280602 * std::sin(mpR + fR) + 0.277693 * std::sin(mpR - fR) +
                            0.173237 * std::sin(2 * dR - fR) + 0.055413 * std::sin(2 * dR - mpR + fR) +
                            0.046271 * std::sin(2 * dR - mpR - fR) + 0.032573 * std::sin(2 * dR + fR) +
                            0.017198 * std::sin(2 * mpR + fR) + 0.009266 * std::sin(2 * dR + mpR - fR) +
                            0.008822 * std::sin(2 * mpR - fR) + 0.008216 * std::sin(2 * dR - mR - fR);

    const double DistanceCorrectionKm = -20905.355 * std::cos(mpR) - 3699.111 * std::cos(2 * dR - mpR) -
                                        2955.968 * std::cos(2 * dR) - 569.925 * std::cos(2 * mpR) +
                                        246.158 * std::cos(2 * dR - 2 * mpR) - 152.138 * std::cos(2 * dR - mR - mpR) -
                                        170.733 * std::cos(2 * dR + mpR) - 204.586 * std::cos(2 * dR - mR);

    Out.EclipticLongitudeDeg = Wrap360(Lp + LonCorrection);
    Out.EclipticLatitudeDeg = LatTerms;
    Out.DistanceKm = 385000.56 + DistanceCorrectionKm;

    // Phase. Meeus 48.4 gives the phase angle directly from the mean elements.
    const double PhaseAngle = Wrap360(180.0 - D - 6.289 * std::sin(mpR) + 2.100 * std::sin(mR) -
                                      1.274 * std::sin(2 * dR - mpR) - 0.658 * std::sin(2 * dR) -
                                      0.214 * std::sin(2 * mpR) - 0.110 * std::sin(dR));
    Out.PhaseAngleDeg = PhaseAngle > 180.0 ? 360.0 - PhaseAngle : PhaseAngle;
    Out.IlluminatedFraction = (1.0 + std::cos(Rad(Out.PhaseAngleDeg))) * 0.5;

    const double SunLongitude = SunApparentLongitudeDeg(T);
    Out.ElongationDeg = Wrap360(Out.EclipticLongitudeDeg - SunLongitude);
    Out.bWaxing = Out.ElongationDeg < 180.0;
    Out.PhaseFraction = Out.ElongationDeg / 360.0;
    Out.AgeDays = Out.PhaseFraction * SynodicMonthDays;

    // Equatorial coordinates.
    const double Eps = Rad(ObliquityCorrectedDeg(T));
    const double Lam = Rad(Out.EclipticLongitudeDeg);
    const double Bet = Rad(Out.EclipticLatitudeDeg);
    const double RightAscension = std::atan2(std::sin(Lam) * std::cos(Eps) - std::tan(Bet) * std::sin(Eps), std::cos(Lam));
    const double Declination = std::asin(std::sin(Bet) * std::cos(Eps) + std::cos(Bet) * std::sin(Eps) * std::sin(Lam));

    const double LocalSidereal = GreenwichMeanSiderealTimeDeg(JD) + LongitudeDeg;
    const double HourAngle = Rad(Wrap180(LocalSidereal - Deg(RightAscension)));

    const double Lat = Rad(LatitudeDeg);
    const double SinAlt =
        std::sin(Lat) * std::sin(Declination) + std::cos(Lat) * std::cos(Declination) * std::cos(HourAngle);
    double Altitude = Deg(std::asin(Clamp(SinAlt, -1.0, 1.0)));

    // Geocentric to topocentric: the moon is close enough that horizontal parallax
    // (about 0.95 degrees) pushes a rising moon visibly lower.
    const double HorizontalParallax = Deg(std::asin(6378.14 / Out.DistanceKm));
    Altitude -= HorizontalParallax * std::cos(Rad(Altitude));
    Out.AltitudeDeg = Altitude;
    Out.RefractedAltitudeDeg = Altitude + AtmosphericRefractionDeg(Altitude);

    const double AzFromSouth = Deg(std::atan2(std::sin(HourAngle),
                                              std::cos(HourAngle) * std::sin(Lat) - std::tan(Declination) * std::cos(Lat)));
    Out.AzimuthDeg = Wrap360(AzFromSouth + 180.0);

    // Bright-limb position angle: the sun's equatorial direction seen from the moon.
    const double SunRA = Rad(SolarRightAscensionDeg(JD));
    const double SunDec = Rad(SolarDeclinationDeg(JD));
    const double DeltaRA = SunRA - RightAscension;
    Out.BrightLimbAngleDeg = Wrap360(Deg(std::atan2(
        std::cos(SunDec) * std::sin(DeltaRA),
        std::sin(SunDec) * std::cos(Declination) - std::cos(SunDec) * std::sin(Declination) * std::cos(DeltaRA))));
    return Out;
}

inline FMoonState JerusalemMoonState(int Year, int Month, int Day, double LocalHours)
{
    return MoonState(JerusalemLatitudeDeg, JerusalemLongitudeDeg, Year, Month, Day, LocalHours,
                     IsraelUtcOffsetHours(Year, Month, Day, LocalHours));
}

// ---------------------------------------------------------------------------
// Presentation helpers shared by the actor and the tests
// ---------------------------------------------------------------------------

/** Named times of day. The values are the order the presets blend in across a day. */
enum class ETimePreset
{
    Dawn = 0,     // civil dawn: sun about -6 deg, before the disc appears
    Sunrise,      // disc on the horizon
    Morning,      // sun about 30 deg
    Midday,       // solar noon
    Afternoon,    // sun about 27 deg descending
    Sunset,       // disc on the horizon, descending
    Dusk,         // civil dusk
    Night,        // sun below -12 deg
    Count
};

/** Wall-clock hour for a preset on a given day, derived from that day's real events. */
inline double PresetHours(const FDayEvents& Events, ETimePreset Preset)
{
    switch (Preset)
    {
    case ETimePreset::Dawn: return Events.CivilDawnHours;
    case ETimePreset::Sunrise: return Events.SunriseHours;
    case ETimePreset::Morning: return Events.SunriseHours + (Events.SolarNoonHours - Events.SunriseHours) * 0.5;
    case ETimePreset::Midday: return Events.SolarNoonHours;
    case ETimePreset::Afternoon: return Events.SolarNoonHours + (Events.SunsetHours - Events.SolarNoonHours) * 0.6;
    case ETimePreset::Sunset: return Events.SunsetHours;
    case ETimePreset::Dusk: return Events.CivilDuskHours;
    case ETimePreset::Night: return Wrap24(Events.SolarNoonHours + 12.0);
    default: return Events.SolarNoonHours;
    }
}

/** Unreal light rotation for a compass azimuth and an altitude, in the project's world
 * frame (+X east, +Y south, +Z up; established by the capture receipts and recorded in
 * Scripts/release_lighting_polish.spec.json).
 *
 * The light TRAVEL direction is d = (-sin(az)cos(alt), +cos(az)cos(alt), -sin(alt)), and a
 * directional light shines along its forward vector, so Pitch = -alt and
 * Yaw = atan2(d.Y, d.X). Returned as pitch/yaw/roll degrees. */
inline void LightRotationForSky(double AzimuthDeg, double AltitudeDeg, double& OutPitch, double& OutYaw, double& OutRoll)
{
    const double Az = Rad(AzimuthDeg);
    const double Alt = Rad(AltitudeDeg);
    const double DX = -std::sin(Az) * std::cos(Alt);
    const double DY = std::cos(Az) * std::cos(Alt);
    OutPitch = -AltitudeDeg;
    OutYaw = Deg(std::atan2(DY, DX));
    OutRoll = 0.0;
    (void)Alt;
}

/** 0..1 normalized day fraction from a wall-clock hour. */
inline double NormalizedTimeFromHours(double Hours) { return Wrap24(Hours) / 24.0; }
inline double HoursFromNormalizedTime(double Normalized) { return Wrap24(Normalized * 24.0); }

} // namespace MikdashSun
