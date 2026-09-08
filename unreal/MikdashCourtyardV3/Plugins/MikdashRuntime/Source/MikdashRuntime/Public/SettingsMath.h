// SettingsMath.h -- engine-independent maths for the Mikdash walkthrough front end.
//
// This header deliberately includes NOTHING from Unreal. It is compiled both by the
// MikdashRuntime module and by Tests/SettingsMathTest.cpp, which is built with cl.exe
// alone. Keep it free of UE types, UE macros, allocation and I/O so the test stays a
// pure numeric check.
//
// Everything a human can change in the front end lives in FSettings. The rules for
// what a legal value is, how a graphics preset expands into the nine individual
// scalability groups, how an old saved file is brought forward, and the sensitivity /
// field-of-view / volume curves all live here, so they can be checked without an editor.

#pragma once

#include <cmath>

namespace MikdashSettings
{

// ---------------------------------------------------------------------------
// Version history of the saved settings record.
//   1  first shipped set: no accessibility block, mouse sensitivity stored on a
//      0..10 linear scale, FieldOfView stored as a VERTICAL angle, SubtitleScale
//      stored as an index (0 small, 1 medium, 2 large), no upscaling fields.
//   2  accessibility block added, sensitivity normalised to 0..1, FieldOfView
//      became a HORIZONTAL angle at 16:9, upscaling method added.
//   3  SubtitleScale became a multiplier, upscaling quality + screen percentage.
// ---------------------------------------------------------------------------
inline constexpr int CurrentVersion = 3;
inline constexpr int OldestSupportedVersion = 1;

enum class EPreset : int { Low = 0, Medium = 1, High = 2, Epic = 3, Cinematic = 4, Custom = 5 };

// Values match UE EWindowMode::Type so the runtime side can cast directly.
enum class EWindowMode : int { Fullscreen = 0, WindowedFullscreen = 1, Windowed = 2 };

enum class EUpscaleMethod : int { Off = 0, TemporalAA = 1, TemporalSuperResolution = 2, Spatial = 3 };
enum class EUpscaleQuality : int { Native = 0, Quality = 1, Balanced = 2, Performance = 3, UltraPerformance = 4 };
enum class ELanguage : int { English = 0, Hebrew = 1 };
enum class EHoldMode : int { Hold = 0, Toggle = 1 };
enum class EColourVision : int { Off = 0, Deuteranope = 1, Protanope = 2, Tritanope = 3 };

inline constexpr int PresetCount = 6;
inline constexpr int LanguageCount = 2;

// UE scalability groups accept 0..4 (Low, Medium, High, Epic, Cinematic).
inline constexpr int MinQuality = 0;
inline constexpr int MaxQuality = 4;

inline constexpr int MinResolutionX = 640;
inline constexpr int MinResolutionY = 480;
inline constexpr int MaxResolutionX = 16384;
inline constexpr int MaxResolutionY = 16384;

// 0 means uncapped. Anything positive is clamped into this band.
inline constexpr float MinFrameRateCap = 24.0f;
inline constexpr float MaxFrameRateCap = 1000.0f;

// Horizontal field of view at 16:9.
inline constexpr float MinFov = 60.0f;
inline constexpr float MaxFov = 120.0f;
inline constexpr float DefaultFov = 90.0f;
inline constexpr float ReferenceAspect = 16.0f / 9.0f;

inline constexpr float MinTextScale = 0.75f;
inline constexpr float MaxTextScale = 2.0f;
inline constexpr float MinSubtitleScale = 0.75f;
inline constexpr float MaxSubtitleScale = 2.0f;

inline constexpr float MinSnapTurn = 15.0f;
inline constexpr float MaxSnapTurn = 90.0f;
inline constexpr float SnapTurnStep = 15.0f;

inline constexpr float MinScreenPercentage = 33.0f;
inline constexpr float MaxScreenPercentage = 200.0f;

// The quietest audible step before the curve is treated as silence, in decibels.
inline constexpr float VolumeFloorDb = -60.0f;

inline constexpr float Pi = 3.14159265358979323846f;

// ---------------------------------------------------------------------------
// Small helpers (no <algorithm>, so the header stays cheap inside UE).
// ---------------------------------------------------------------------------

inline float ClampF(float Value, float Low, float High)
{
    // NaN-safe: a NaN compares false against everything, so send it to Low.
    if (!(Value == Value)) { return Low; }
    if (Value < Low) { return Low; }
    if (Value > High) { return High; }
    return Value;
}

inline int ClampI(int Value, int Low, int High)
{
    if (Value < Low) { return Low; }
    if (Value > High) { return High; }
    return Value;
}

inline bool NearlyEqual(float A, float B, float Tolerance = 1.0e-4f)
{
    const float Difference = A - B;
    return (Difference < 0.0f ? -Difference : Difference) <= Tolerance;
}

inline float SnapToStep(float Value, float Step, float Low, float High)
{
    if (Step <= 0.0f) { return ClampF(Value, Low, High); }
    const float Steps = std::floor((ClampF(Value, Low, High) - Low) / Step + 0.5f);
    return ClampF(Low + Steps * Step, Low, High);
}

// ---------------------------------------------------------------------------
// Scalability
// ---------------------------------------------------------------------------

/** The nine individual scalability groups the front end exposes, in UI order. */
struct FScalability
{
    int ViewDistance = 3;
    int Shadows = 3;
    int GlobalIllumination = 3;
    int Reflections = 3;
    int PostProcess = 3;
    int Textures = 3;
    int Effects = 3;
    int Foliage = 3;
    int Shading = 3;

    int& At(int Index)
    {
        switch (Index)
        {
        case 0: return ViewDistance;
        case 1: return Shadows;
        case 2: return GlobalIllumination;
        case 3: return Reflections;
        case 4: return PostProcess;
        case 5: return Textures;
        case 6: return Effects;
        case 7: return Foliage;
        default: return Shading;
        }
    }
    int Get(int Index) const { return const_cast<FScalability*>(this)->At(Index); }
    static constexpr int Count() { return 9; }

    bool operator==(const FScalability& Other) const
    {
        for (int Index = 0; Index < Count(); ++Index)
        {
            if (Get(Index) != Other.Get(Index)) { return false; }
        }
        return true;
    }
    bool operator!=(const FScalability& Other) const { return !(*this == Other); }
};

inline const char* GroupName(int Index)
{
    static const char* const Names[9] = {
        "View distance", "Shadows", "Global illumination", "Reflections",
        "Post process", "Textures", "Effects", "Foliage", "Shading" };
    return Names[ClampI(Index, 0, 8)];
}

inline const char* PresetName(EPreset Preset)
{
    switch (Preset)
    {
    case EPreset::Low: return "Low";
    case EPreset::Medium: return "Medium";
    case EPreset::High: return "High";
    case EPreset::Epic: return "Epic";
    case EPreset::Cinematic: return "Cinematic";
    default: return "Custom";
    }
}

/**
 * Expand a preset into the nine groups.
 *
 * Low..Cinematic are the flat UE quality levels 0..4, with two deliberate
 * departures for this particular walkthrough:
 *   - Textures stay one level above the preset below Epic. The measured stone and
 *     the Kotel photographic surface are the whole point of the piece, and texture
 *     quality costs memory rather than frame time on the target card.
 *   - Foliage stays one level BELOW the preset above Low. There is very little
 *     foliage in the court and it is the most expensive thing per pixel here.
 * Custom is not expandable; it returns the Epic layout so a caller that ignores
 * the return value still gets something legal.
 */
inline FScalability PresetToScalability(EPreset Preset)
{
    FScalability Result;
    const int Level = (Preset == EPreset::Custom) ? 3 : ClampI(static_cast<int>(Preset), MinQuality, MaxQuality);
    for (int Index = 0; Index < FScalability::Count(); ++Index)
    {
        Result.At(Index) = Level;
    }
    if (Level < 3)
    {
        Result.Textures = ClampI(Level + 1, MinQuality, MaxQuality);
    }
    if (Level > 0)
    {
        Result.Foliage = ClampI(Level - 1, MinQuality, MaxQuality);
    }
    return Result;
}

/** The preset whose expansion equals these groups, or Custom when none does. */
inline EPreset InferPreset(const FScalability& Groups)
{
    for (int Candidate = 0; Candidate <= 4; ++Candidate)
    {
        if (PresetToScalability(static_cast<EPreset>(Candidate)) == Groups)
        {
            return static_cast<EPreset>(Candidate);
        }
    }
    return EPreset::Custom;
}

// ---------------------------------------------------------------------------
// Curves
// ---------------------------------------------------------------------------

/**
 * Mouse sensitivity. The slider is a plain 0..1; the multiplier applied to look
 * input is exponential so the middle of the slider is 1.0 and each half of the
 * travel is a factor of four. A linear slider spends most of its useful range in
 * the bottom fifth, which is the usual complaint about first-person options.
 */
inline float SensitivityMultiplier(float Normalised)
{
    const float T = ClampF(Normalised, 0.0f, 1.0f);
    return std::pow(2.0f, (T - 0.5f) * 4.0f);
}

/** Inverse of SensitivityMultiplier, for putting a stored multiplier back on a slider. */
inline float SensitivityFromMultiplier(float Multiplier)
{
    const float Safe = ClampF(Multiplier, 0.25f, 4.0f);
    return ClampF(std::log2(Safe) / 4.0f + 0.5f, 0.0f, 1.0f);
}

/** Vertical FOV for a horizontal FOV at a given aspect ratio. Degrees in, degrees out. */
inline float VerticalFovFromHorizontal(float HorizontalDegrees, float Aspect)
{
    const float SafeAspect = ClampF(Aspect, 0.2f, 8.0f);
    const float Half = ClampF(HorizontalDegrees, 1.0f, 179.0f) * 0.5f * Pi / 180.0f;
    return 2.0f * std::atan(std::tan(Half) / SafeAspect) * 180.0f / Pi;
}

/** Horizontal FOV for a vertical FOV at a given aspect ratio. */
inline float HorizontalFovFromVertical(float VerticalDegrees, float Aspect)
{
    const float SafeAspect = ClampF(Aspect, 0.2f, 8.0f);
    const float Half = ClampF(VerticalDegrees, 1.0f, 179.0f) * 0.5f * Pi / 180.0f;
    return 2.0f * std::atan(std::tan(Half) * SafeAspect) * 180.0f / Pi;
}

/**
 * Hor+ : the visitor sets a horizontal FOV at 16:9 and a wider monitor shows more
 * to the sides while the vertical angle is held. UE cameras take a horizontal FOV,
 * so this converts the authored value into the horizontal angle to feed the camera
 * on the actual display aspect.
 */
inline float HorPlusFovForAspect(float AuthoredHorizontalAt16x9, float TargetAspect)
{
    const float Vertical = VerticalFovFromHorizontal(AuthoredHorizontalAt16x9, ReferenceAspect);
    return HorizontalFovFromVertical(Vertical, TargetAspect);
}

/** Perceptual volume: a 0..1 slider onto a linear amplitude over a 60 dB range. */
inline float VolumeToGain(float Normalised)
{
    const float T = ClampF(Normalised, 0.0f, 1.0f);
    if (T <= 0.0f) { return 0.0f; }
    return std::pow(10.0f, (VolumeFloorDb * (1.0f - T)) / 20.0f);
}

/** Inverse of VolumeToGain. */
inline float GainToVolume(float Gain)
{
    const float G = ClampF(Gain, 0.0f, 1.0f);
    if (G <= 0.0f) { return 0.0f; }
    return ClampF(1.0f - (20.0f * std::log10(G)) / VolumeFloorDb, 0.0f, 1.0f);
}

/** Screen percentage for an upscaling method and quality tier. */
inline float UpscaleScreenPercentage(EUpscaleMethod Method, EUpscaleQuality Quality)
{
    if (Method == EUpscaleMethod::Off) { return 100.0f; }
    switch (Quality)
    {
    case EUpscaleQuality::Quality: return 77.0f;
    case EUpscaleQuality::Balanced: return 67.0f;
    case EUpscaleQuality::Performance: return 59.0f;
    case EUpscaleQuality::UltraPerformance: return 50.0f;
    case EUpscaleQuality::Native:
    default: return 100.0f;
    }
}

/** Final on-screen font size for a base size, a per-element scale and the global text scale. */
inline float ScaledFontSize(float BaseSize, float Scale, float TextScale)
{
    return ClampF(BaseSize, 1.0f, 400.0f)
        * ClampF(Scale, MinSubtitleScale, MaxSubtitleScale)
        * ClampF(TextScale, MinTextScale, MaxTextScale);
}

/** v1 and v2 stored subtitle size as an index; v3 stores a multiplier. */
inline float LegacySubtitleIndexToScale(int Index)
{
    switch (ClampI(Index, 0, 2))
    {
    case 0: return 0.85f;
    case 2: return 1.4f;
    default: return 1.0f;
    }
}

inline float SnapTurnStepDegrees(float Requested)
{
    return SnapToStep(Requested, SnapTurnStep, MinSnapTurn, MaxSnapTurn);
}

// ---------------------------------------------------------------------------
// The settings record
// ---------------------------------------------------------------------------

struct FSettings
{
    int Version = CurrentVersion;

    // Graphics
    EPreset Preset = EPreset::High;
    FScalability Groups = PresetToScalability(EPreset::High);
    int ResolutionX = 1920;
    int ResolutionY = 1080;
    EWindowMode WindowMode = EWindowMode::WindowedFullscreen;
    float FrameRateCap = 0.0f;                       // 0 == uncapped
    EUpscaleMethod UpscaleMethod = EUpscaleMethod::TemporalSuperResolution;
    EUpscaleQuality UpscaleQuality = EUpscaleQuality::Quality;
    float ScreenPercentage = 77.0f;

    // Camera and input
    float FieldOfView = DefaultFov;                  // horizontal, at 16:9
    float MouseSensitivity = 0.5f;                   // 0..1, see SensitivityMultiplier
    bool bInvertY = false;

    // Audio
    float MasterVolume = 0.8f;
    float MusicVolume = 0.7f;
    float EffectsVolume = 0.8f;
    float VoiceVolume = 0.9f;

    // Text
    bool bSubtitles = true;
    float SubtitleScale = 1.0f;
    ELanguage Language = ELanguage::English;
    float TextScale = 1.0f;

    // Accessibility / motion sickness
    bool bCameraShake = true;
    bool bHeadBob = true;
    bool bVignetteOnMovement = false;
    bool bSnapTurn = false;
    float SnapTurnDegrees = 45.0f;
    EColourVision ColourVision = EColourVision::Off;
    EHoldMode SprintMode = EHoldMode::Hold;
    EHoldMode CrouchMode = EHoldMode::Hold;
};

inline FSettings MakeDefaults() { return FSettings(); }

// ---------------------------------------------------------------------------
// Clamping and validation
// ---------------------------------------------------------------------------

namespace Detail
{
    inline int FixI(int& Field, int Low, int High)
    {
        const int Fixed = ClampI(Field, Low, High);
        if (Fixed != Field) { Field = Fixed; return 1; }
        return 0;
    }
    inline int FixF(float& Field, float Low, float High)
    {
        const bool bNaN = !(Field == Field);
        const float Fixed = ClampF(Field, Low, High);
        if (bNaN || Fixed != Field) { Field = Fixed; return 1; }
        return 0;
    }
    template <typename EnumType>
    inline int FixEnum(EnumType& Field, int Low, int High)
    {
        const int Value = static_cast<int>(Field);
        if (Value < Low || Value > High)
        {
            Field = static_cast<EnumType>(ClampI(Value, Low, High));
            return 1;
        }
        return 0;
    }
}

/**
 * Force every field into a legal range. Returns the number of fields that had to be
 * corrected, so a caller (and the test) can tell a clean record from a repaired one.
 * Clamp never fails and never rejects a record.
 */
inline int Clamp(FSettings& S)
{
    int Corrections = 0;

    Corrections += Detail::FixI(S.Version, OldestSupportedVersion, CurrentVersion);
    Corrections += Detail::FixEnum(S.Preset, 0, PresetCount - 1);
    for (int Index = 0; Index < FScalability::Count(); ++Index)
    {
        Corrections += Detail::FixI(S.Groups.At(Index), MinQuality, MaxQuality);
    }

    Corrections += Detail::FixI(S.ResolutionX, MinResolutionX, MaxResolutionX);
    Corrections += Detail::FixI(S.ResolutionY, MinResolutionY, MaxResolutionY);
    Corrections += Detail::FixEnum(S.WindowMode, 0, 2);

    // 0 stays 0 (uncapped); any other value is pulled into the supported band.
    if (S.FrameRateCap != 0.0f)
    {
        Corrections += Detail::FixF(S.FrameRateCap, MinFrameRateCap, MaxFrameRateCap);
    }

    Corrections += Detail::FixEnum(S.UpscaleMethod, 0, 3);
    Corrections += Detail::FixEnum(S.UpscaleQuality, 0, 4);
    Corrections += Detail::FixF(S.ScreenPercentage, MinScreenPercentage, MaxScreenPercentage);

    Corrections += Detail::FixF(S.FieldOfView, MinFov, MaxFov);
    Corrections += Detail::FixF(S.MouseSensitivity, 0.0f, 1.0f);

    Corrections += Detail::FixF(S.MasterVolume, 0.0f, 1.0f);
    Corrections += Detail::FixF(S.MusicVolume, 0.0f, 1.0f);
    Corrections += Detail::FixF(S.EffectsVolume, 0.0f, 1.0f);
    Corrections += Detail::FixF(S.VoiceVolume, 0.0f, 1.0f);

    Corrections += Detail::FixF(S.SubtitleScale, MinSubtitleScale, MaxSubtitleScale);
    Corrections += Detail::FixEnum(S.Language, 0, LanguageCount - 1);
    Corrections += Detail::FixF(S.TextScale, MinTextScale, MaxTextScale);

    const float SnappedTurn = SnapTurnStepDegrees(S.SnapTurnDegrees);
    if (!NearlyEqual(SnappedTurn, S.SnapTurnDegrees, 1.0e-3f)) { ++Corrections; }
    S.SnapTurnDegrees = SnappedTurn;

    Corrections += Detail::FixEnum(S.ColourVision, 0, 3);
    Corrections += Detail::FixEnum(S.SprintMode, 0, 1);
    Corrections += Detail::FixEnum(S.CrouchMode, 0, 1);

    // Cross-field consistency. These count as corrections too: a record whose preset
    // says High but whose groups are all Low would otherwise show a lie in the UI.
    const EPreset Implied = InferPreset(S.Groups);
    if (S.Preset != Implied) { S.Preset = Implied; ++Corrections; }

    // The screen percentage is derived, EXCEPT on the Native tier, where the visitor
    // is allowed to dial an arbitrary render scale by hand.
    if (S.UpscaleMethod == EUpscaleMethod::Off || S.UpscaleQuality != EUpscaleQuality::Native)
    {
        const float ImpliedPercentage = UpscaleScreenPercentage(S.UpscaleMethod, S.UpscaleQuality);
        if (!NearlyEqual(S.ScreenPercentage, ImpliedPercentage, 1.0e-3f))
        {
            S.ScreenPercentage = ImpliedPercentage;
            ++Corrections;
        }
    }

    return Corrections;
}

/** True when the record needs no correction at all. */
inline bool Validate(const FSettings& S)
{
    FSettings Copy = S;
    return Clamp(Copy) == 0;
}

/** Set the nine groups from a preset and keep Preset in step. Custom is a no-op. */
inline void ApplyPreset(FSettings& S, EPreset Preset)
{
    if (Preset == EPreset::Custom) { S.Preset = InferPreset(S.Groups); return; }
    S.Groups = PresetToScalability(Preset);
    S.Preset = Preset;
}

/** Change one group by index and re-derive whether the record is still a preset. */
inline void SetGroup(FSettings& S, int GroupIndex, int Quality)
{
    if (GroupIndex < 0 || GroupIndex >= FScalability::Count()) { return; }
    S.Groups.At(GroupIndex) = ClampI(Quality, MinQuality, MaxQuality);
    S.Preset = InferPreset(S.Groups);
}

/** Change the upscaling tier and re-derive the screen percentage. */
inline void SetUpscaling(FSettings& S, EUpscaleMethod Method, EUpscaleQuality Quality)
{
    S.UpscaleMethod = Method;
    S.UpscaleQuality = Quality;
    S.ScreenPercentage = UpscaleScreenPercentage(Method, Quality);
}

// ---------------------------------------------------------------------------
// Migration
// ---------------------------------------------------------------------------

/**
 * Bring an older saved record forward to CurrentVersion in place.
 *
 * Returns true when anything was changed. A record from the future, or one below
 * OldestSupportedVersion, is replaced wholesale by the defaults -- silently
 * reinterpreting unknown bytes is how a settings file bricks a boot. Migration
 * always finishes with a Clamp, so the result is legal by construction.
 */
inline bool Migrate(FSettings& S)
{
    if (S.Version == CurrentVersion)
    {
        return Clamp(S) != 0;
    }

    if (S.Version < OldestSupportedVersion || S.Version > CurrentVersion)
    {
        S = MakeDefaults();
        return true;
    }

    if (S.Version == 1)
    {
        // Sensitivity was a 0..10 linear dial.
        S.MouseSensitivity = ClampF(S.MouseSensitivity / 10.0f, 0.0f, 1.0f);
        // FOV was stored vertically; the UI is horizontal at 16:9 from v2 on.
        S.FieldOfView = HorizontalFovFromVertical(S.FieldOfView, ReferenceAspect);
        // The accessibility block did not exist; take the defaults rather than
        // whatever happened to sit in the uninitialised struct.
        const FSettings Fresh = MakeDefaults();
        S.bCameraShake = Fresh.bCameraShake;
        S.bHeadBob = Fresh.bHeadBob;
        S.bVignetteOnMovement = Fresh.bVignetteOnMovement;
        S.bSnapTurn = Fresh.bSnapTurn;
        S.SnapTurnDegrees = Fresh.SnapTurnDegrees;
        S.ColourVision = Fresh.ColourVision;
        S.SprintMode = Fresh.SprintMode;
        S.CrouchMode = Fresh.CrouchMode;
        S.TextScale = Fresh.TextScale;
        S.UpscaleMethod = Fresh.UpscaleMethod;
        S.Version = 2;
    }

    if (S.Version == 2)
    {
        // SubtitleScale held an index 0/1/2 in v1 and v2.
        S.SubtitleScale = LegacySubtitleIndexToScale(static_cast<int>(S.SubtitleScale + 0.5f));
        SetUpscaling(S, S.UpscaleMethod, EUpscaleQuality::Native);
        S.Version = 3;
    }

    S.Version = CurrentVersion;
    Clamp(S);
    return true;
}

} // namespace MikdashSettings
