// SettingsMathTest.cpp -- standalone test for Public/SettingsMath.h.
//
// No Unreal, no test framework. Build and run with the VS2022 BuildTools toolchain:
//
//   call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
//   cl /nologo /EHsc /std:c++17 /W4 /I"<plugin>\Source\MikdashRuntime\Public" ^
//      "<plugin>\Source\MikdashRuntime\Tests\SettingsMathTest.cpp" /Fe:SettingsMathTest.exe
//   SettingsMathTest.exe > SourceAssets\frontend-review\tests.json
//
// Exit code 0 when every case passes, 1 otherwise. The JSON on stdout is the
// receipt; a one-line human summary goes to stderr so a redirected stdout stays
// machine-readable.

#include "SettingsMath.h"

#include <cstdio>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

using namespace MikdashSettings;

namespace
{

struct FCase
{
    std::string Group;
    std::string Name;
    bool bPassed = false;
    std::string Detail;
};

std::vector<FCase> Cases;
std::string CurrentGroup = "ungrouped";

void Group(const char* Name) { CurrentGroup = Name; }

void Check(const char* Name, bool bCondition, const std::string& Detail = std::string())
{
    Cases.push_back(FCase{ CurrentGroup, Name, bCondition, Detail });
}

std::string F(float Value)
{
    char Buffer[64];
    std::snprintf(Buffer, sizeof(Buffer), "%.6g", static_cast<double>(Value));
    return Buffer;
}

std::string I(int Value)
{
    char Buffer[32];
    std::snprintf(Buffer, sizeof(Buffer), "%d", Value);
    return Buffer;
}

void CheckNear(const char* Name, float Actual, float Expected, float Tolerance)
{
    const bool bOk = NearlyEqual(Actual, Expected, Tolerance);
    Check(Name, bOk, bOk ? std::string() : ("actual " + F(Actual) + " expected " + F(Expected) + " tol " + F(Tolerance)));
}

std::string Escape(const std::string& In)
{
    std::string Out;
    for (const char C : In)
    {
        if (C == '"' || C == '\\') { Out += '\\'; Out += C; }
        else if (C == '\n') { Out += "\\n"; }
        else { Out += C; }
    }
    return Out;
}

// -------------------------------------------------------------------------
// Preset expansion
// -------------------------------------------------------------------------
void TestPresets()
{
    Group("presets");

    for (int Level = 0; Level <= 4; ++Level)
    {
        const EPreset Preset = static_cast<EPreset>(Level);
        const FScalability Groups = PresetToScalability(Preset);

        bool bInRange = true;
        for (int Index = 0; Index < FScalability::Count(); ++Index)
        {
            bInRange = bInRange && Groups.Get(Index) >= MinQuality && Groups.Get(Index) <= MaxQuality;
        }
        Check("preset groups stay inside 0..4", bInRange, PresetName(Preset));

        Check("preset round-trips through InferPreset", InferPreset(Groups) == Preset, PresetName(Preset));
    }

    // Every preset must expand to a distinct layout, or InferPreset is ambiguous.
    bool bAllDistinct = true;
    for (int A = 0; A <= 4; ++A)
    {
        for (int B = A + 1; B <= 4; ++B)
        {
            if (PresetToScalability(static_cast<EPreset>(A)) == PresetToScalability(static_cast<EPreset>(B)))
            {
                bAllDistinct = false;
            }
        }
    }
    Check("the five presets expand to five distinct layouts", bAllDistinct);

    // Documented departures from a flat level.
    Check("textures sit above the preset below Epic", PresetToScalability(EPreset::Medium).Textures == 2,
          "medium textures " + I(PresetToScalability(EPreset::Medium).Textures));
    Check("foliage sits below the preset above Low", PresetToScalability(EPreset::Epic).Foliage == 2,
          "epic foliage " + I(PresetToScalability(EPreset::Epic).Foliage));
    Check("Low does not push foliage negative", PresetToScalability(EPreset::Low).Foliage == 0);
    Check("Cinematic does not push textures past 4", PresetToScalability(EPreset::Cinematic).Textures == 4);

    // A hand-edited group set is Custom, not a lie about a preset.
    FScalability Mixed = PresetToScalability(EPreset::High);
    Mixed.Shadows = 0;
    Check("a hand-edited layout reads as Custom", InferPreset(Mixed) == EPreset::Custom);

    // Monotonic: raising the preset never lowers a group.
    bool bMonotonic = true;
    for (int Level = 0; Level < 4; ++Level)
    {
        const FScalability Lower = PresetToScalability(static_cast<EPreset>(Level));
        const FScalability Higher = PresetToScalability(static_cast<EPreset>(Level + 1));
        for (int Index = 0; Index < FScalability::Count(); ++Index)
        {
            if (Higher.Get(Index) < Lower.Get(Index)) { bMonotonic = false; }
        }
    }
    Check("raising the preset never lowers a group", bMonotonic);
}

// -------------------------------------------------------------------------
// Clamping and validation
// -------------------------------------------------------------------------
void TestClamp()
{
    Group("clamp");

    FSettings Defaults = MakeDefaults();
    Check("the defaults need no correction", Clamp(Defaults) == 0);
    Check("the defaults validate", Validate(MakeDefaults()));

    // Every scalar field out of range at once.
    FSettings Bad = MakeDefaults();
    Bad.Version = 99;
    Bad.ResolutionX = 1;
    Bad.ResolutionY = 999999;
    Bad.WindowMode = static_cast<EWindowMode>(7);
    Bad.FrameRateCap = 4.0f;
    Bad.FieldOfView = 300.0f;
    Bad.MouseSensitivity = -3.0f;
    Bad.MasterVolume = 5.0f;
    Bad.MusicVolume = -1.0f;
    Bad.EffectsVolume = 2.0f;
    Bad.VoiceVolume = -0.5f;
    Bad.SubtitleScale = 9.0f;
    Bad.TextScale = 0.0f;
    Bad.SnapTurnDegrees = 1000.0f;
    Bad.Language = static_cast<ELanguage>(42);
    Bad.ColourVision = static_cast<EColourVision>(-4);
    Bad.SprintMode = static_cast<EHoldMode>(9);
    Bad.CrouchMode = static_cast<EHoldMode>(9);
    Bad.Groups.Shadows = 17;
    Bad.Groups.Foliage = -6;
    Bad.ScreenPercentage = 5000.0f;
    Bad.UpscaleMethod = static_cast<EUpscaleMethod>(88);
    Bad.UpscaleQuality = static_cast<EUpscaleQuality>(-2);

    const int Corrections = Clamp(Bad);
    Check("a fully corrupt record reports many corrections", Corrections >= 20, "corrections " + I(Corrections));
    Check("a clamped record then validates", Validate(Bad));
    Check("clamp is idempotent", Clamp(Bad) == 0);

    Check("resolution floor held", Bad.ResolutionX == MinResolutionX, "x " + I(Bad.ResolutionX));
    Check("resolution ceiling held", Bad.ResolutionY == MaxResolutionY, "y " + I(Bad.ResolutionY));
    Check("fov ceiling held", NearlyEqual(Bad.FieldOfView, MaxFov), "fov " + F(Bad.FieldOfView));
    Check("frame cap floor held", NearlyEqual(Bad.FrameRateCap, MinFrameRateCap), "cap " + F(Bad.FrameRateCap));
    Check("snap turn snapped into the band", NearlyEqual(Bad.SnapTurnDegrees, MaxSnapTurn), "snap " + F(Bad.SnapTurnDegrees));

    // 0 is a legal frame cap and means uncapped: it must not be pulled up to 24.
    FSettings Uncapped = MakeDefaults();
    Uncapped.FrameRateCap = 0.0f;
    Clamp(Uncapped);
    Check("an uncapped frame rate stays uncapped", Uncapped.FrameRateCap == 0.0f, "cap " + F(Uncapped.FrameRateCap));

    // NaN must not survive into the engine.
    FSettings NotANumber = MakeDefaults();
    const float NaN = std::numeric_limits<float>::quiet_NaN();
    NotANumber.FieldOfView = NaN;
    NotANumber.MasterVolume = NaN;
    Clamp(NotANumber);
    Check("a NaN field of view is repaired", NotANumber.FieldOfView == NotANumber.FieldOfView, F(NotANumber.FieldOfView));
    Check("a NaN volume is repaired", NotANumber.MasterVolume == NotANumber.MasterVolume, F(NotANumber.MasterVolume));

    // Cross-field: a record claiming Epic while its groups are Low is corrected.
    FSettings Lying = MakeDefaults();
    Lying.Groups = PresetToScalability(EPreset::Low);
    Lying.Preset = EPreset::Cinematic;
    Clamp(Lying);
    Check("a mismatched preset label is corrected to the real one", Lying.Preset == EPreset::Low, PresetName(Lying.Preset));

    // Screen percentage is derived on every tier except Native.
    FSettings Derived = MakeDefaults();
    SetUpscaling(Derived, EUpscaleMethod::TemporalSuperResolution, EUpscaleQuality::Performance);
    Derived.ScreenPercentage = 123.0f;
    Clamp(Derived);
    CheckNear("performance tier forces its screen percentage", Derived.ScreenPercentage, 59.0f, 1.0e-3f);

    FSettings HandDialled = MakeDefaults();
    SetUpscaling(HandDialled, EUpscaleMethod::TemporalSuperResolution, EUpscaleQuality::Native);
    HandDialled.ScreenPercentage = 133.0f;
    Clamp(HandDialled);
    CheckNear("the native tier keeps a hand-dialled render scale", HandDialled.ScreenPercentage, 133.0f, 1.0e-3f);

    // SetGroup keeps the label honest.
    FSettings Edited = MakeDefaults();
    SetGroup(Edited, 1, 0);
    Check("editing one group flips the label to Custom", Edited.Preset == EPreset::Custom);
    SetGroup(Edited, 1, PresetToScalability(EPreset::High).Shadows);
    Check("restoring the group restores the label", Edited.Preset == EPreset::High, PresetName(Edited.Preset));
    SetGroup(Edited, 99, 4);
    Check("an out-of-range group index is ignored", Validate(Edited));
}

// -------------------------------------------------------------------------
// Migration
// -------------------------------------------------------------------------
void TestMigration()
{
    Group("migration");

    // A v1 record as it was actually written: 0..10 sensitivity, vertical FOV,
    // subtitle size as an index, no accessibility block.
    FSettings V1 = MakeDefaults();
    V1.Version = 1;
    V1.MouseSensitivity = 7.5f;          // 0..10 dial
    V1.FieldOfView = 60.0f;              // vertical degrees
    V1.SubtitleScale = 2.0f;             // index: large
    V1.bCameraShake = false;             // pre-migration junk in a field v1 never had
    V1.TextScale = 0.0f;
    V1.SnapTurnDegrees = 0.0f;

    FSettings Migrated = V1;
    const bool bChanged = Migrate(Migrated);
    Check("a v1 record reports as changed", bChanged);
    Check("a v1 record lands on the current version", Migrated.Version == CurrentVersion, "version " + I(Migrated.Version));
    Check("a migrated v1 record validates", Validate(Migrated));
    CheckNear("v1 sensitivity 7.5/10 becomes 0.75", Migrated.MouseSensitivity, 0.75f, 1.0e-5f);
    CheckNear("v1 vertical 60 becomes horizontal 90.08 at 16:9",
              Migrated.FieldOfView, HorizontalFovFromVertical(60.0f, ReferenceAspect), 1.0e-3f);
    CheckNear("v1 subtitle index 2 becomes the large multiplier", Migrated.SubtitleScale, 1.4f, 1.0e-5f);
    Check("v1 accessibility fields are taken from the defaults, not the file",
          Migrated.bCameraShake == MakeDefaults().bCameraShake);
    CheckNear("v1 text scale is taken from the defaults", Migrated.TextScale, MakeDefaults().TextScale, 1.0e-5f);

    // A v2 record: sensitivity already normalised, FOV already horizontal, but the
    // subtitle field is still an index and there is no upscaling quality.
    FSettings V2 = MakeDefaults();
    V2.Version = 2;
    V2.MouseSensitivity = 0.3f;
    V2.FieldOfView = 100.0f;
    V2.SubtitleScale = 0.0f;             // index: small
    FSettings MigratedV2 = V2;
    Check("a v2 record reports as changed", Migrate(MigratedV2));
    Check("a migrated v2 record validates", Validate(MigratedV2));
    CheckNear("v2 sensitivity is left alone", MigratedV2.MouseSensitivity, 0.3f, 1.0e-5f);
    CheckNear("v2 field of view is left alone", MigratedV2.FieldOfView, 100.0f, 1.0e-4f);
    CheckNear("v2 subtitle index 0 becomes the small multiplier", MigratedV2.SubtitleScale, 0.85f, 1.0e-5f);
    Check("v2 gains the native upscaling tier", MigratedV2.UpscaleQuality == EUpscaleQuality::Native);

    // Current version: migration is a no-op apart from clamping.
    FSettings Current = MakeDefaults();
    Check("a current clean record reports no change", !Migrate(Current));
    Check("a current record survives migration unchanged", Validate(Current));

    FSettings CurrentDirty = MakeDefaults();
    CurrentDirty.FieldOfView = 999.0f;
    Check("a current dirty record reports a change", Migrate(CurrentDirty));
    Check("a current dirty record is repaired", Validate(CurrentDirty));

    // A record from a future build, or from before the oldest supported version,
    // is thrown away rather than reinterpreted.
    FSettings FromTheFuture = MakeDefaults();
    FromTheFuture.Version = CurrentVersion + 5;
    FromTheFuture.FieldOfView = 61.0f;
    Check("a future record reports as changed", Migrate(FromTheFuture));
    Check("a future record is replaced by the defaults",
          NearlyEqual(FromTheFuture.FieldOfView, MakeDefaults().FieldOfView) && FromTheFuture.Version == CurrentVersion);

    FSettings TooOld = MakeDefaults();
    TooOld.Version = 0;
    Migrate(TooOld);
    Check("a pre-v1 record is replaced by the defaults", TooOld.Version == CurrentVersion && Validate(TooOld));

    // Migration is a fixed point: running it twice changes nothing the second time.
    FSettings Once = V1;
    Migrate(Once);
    FSettings Twice = Once;
    Check("migration is a fixed point", !Migrate(Twice));
}

// -------------------------------------------------------------------------
// Curves
// -------------------------------------------------------------------------
void TestCurves()
{
    Group("curves");

    CheckNear("the middle of the sensitivity slider is 1.0", SensitivityMultiplier(0.5f), 1.0f, 1.0e-5f);
    CheckNear("the bottom of the sensitivity slider is a quarter", SensitivityMultiplier(0.0f), 0.25f, 1.0e-5f);
    CheckNear("the top of the sensitivity slider is four times", SensitivityMultiplier(1.0f), 4.0f, 1.0e-5f);

    bool bMonotonic = true;
    float Previous = -1.0f;
    for (int Step = 0; Step <= 100; ++Step)
    {
        const float Value = SensitivityMultiplier(static_cast<float>(Step) / 100.0f);
        if (Value <= Previous) { bMonotonic = false; }
        Previous = Value;
    }
    Check("the sensitivity curve is strictly increasing", bMonotonic);

    bool bRoundTrips = true;
    for (int Step = 0; Step <= 20; ++Step)
    {
        const float T = static_cast<float>(Step) / 20.0f;
        if (!NearlyEqual(SensitivityFromMultiplier(SensitivityMultiplier(T)), T, 1.0e-4f)) { bRoundTrips = false; }
    }
    Check("sensitivity round-trips through its inverse", bRoundTrips);

    // Field of view. A 90 degree horizontal at 16:9 is 58.72 degrees vertical.
    CheckNear("90 horizontal at 16:9 is 58.72 vertical", VerticalFovFromHorizontal(90.0f, ReferenceAspect), 58.7156f, 1.0e-2f);
    CheckNear("the fov conversion round-trips",
              HorizontalFovFromVertical(VerticalFovFromHorizontal(103.0f, 2.35f), 2.35f), 103.0f, 1.0e-3f);
    CheckNear("Hor+ at 16:9 is the identity", HorPlusFovForAspect(95.0f, ReferenceAspect), 95.0f, 1.0e-3f);
    Check("Hor+ widens on an ultrawide display", HorPlusFovForAspect(90.0f, 21.0f / 9.0f) > 90.0f,
          F(HorPlusFovForAspect(90.0f, 21.0f / 9.0f)));
    Check("Hor+ narrows on a 4:3 display", HorPlusFovForAspect(90.0f, 4.0f / 3.0f) < 90.0f,
          F(HorPlusFovForAspect(90.0f, 4.0f / 3.0f)));

    bool bVerticalHeld = true;
    for (float Aspect = 1.0f; Aspect <= 3.0f; Aspect += 0.25f)
    {
        const float Horizontal = HorPlusFovForAspect(90.0f, Aspect);
        if (!NearlyEqual(VerticalFovFromHorizontal(Horizontal, Aspect),
                         VerticalFovFromHorizontal(90.0f, ReferenceAspect), 1.0e-2f))
        {
            bVerticalHeld = false;
        }
    }
    Check("Hor+ holds the vertical angle across aspect ratios", bVerticalHeld);

    // Volume.
    CheckNear("volume 0 is silence", VolumeToGain(0.0f), 0.0f, 1.0e-9f);
    CheckNear("volume 1 is unity gain", VolumeToGain(1.0f), 1.0f, 1.0e-5f);
    CheckNear("volume 0.5 is -30 dB", VolumeToGain(0.5f), 0.0316228f, 1.0e-5f);
    bool bVolumeRoundTrips = true;
    for (int Step = 1; Step <= 20; ++Step)
    {
        const float T = static_cast<float>(Step) / 20.0f;
        if (!NearlyEqual(GainToVolume(VolumeToGain(T)), T, 1.0e-4f)) { bVolumeRoundTrips = false; }
    }
    Check("volume round-trips through its inverse", bVolumeRoundTrips);

    // Upscaling.
    CheckNear("upscaling off is 100 per cent", UpscaleScreenPercentage(EUpscaleMethod::Off, EUpscaleQuality::Performance), 100.0f, 1.0e-5f);
    CheckNear("TSR quality is 77 per cent", UpscaleScreenPercentage(EUpscaleMethod::TemporalSuperResolution, EUpscaleQuality::Quality), 77.0f, 1.0e-5f);
    CheckNear("TSR ultra performance is 50 per cent", UpscaleScreenPercentage(EUpscaleMethod::TemporalSuperResolution, EUpscaleQuality::UltraPerformance), 50.0f, 1.0e-5f);
    bool bTiersDescend = true;
    float PreviousPercentage = 1000.0f;
    for (int Tier = 0; Tier <= 4; ++Tier)
    {
        const float Percentage = UpscaleScreenPercentage(EUpscaleMethod::TemporalSuperResolution, static_cast<EUpscaleQuality>(Tier));
        if (Percentage > PreviousPercentage) { bTiersDescend = false; }
        PreviousPercentage = Percentage;
    }
    Check("upscaling tiers never rise as they get faster", bTiersDescend);

    // Text sizing.
    CheckNear("an unscaled font keeps its base size", ScaledFontSize(24.0f, 1.0f, 1.0f), 24.0f, 1.0e-5f);
    CheckNear("subtitle and text scale multiply", ScaledFontSize(20.0f, 1.4f, 1.5f), 42.0f, 1.0e-4f);
    CheckNear("an absurd text scale is clamped", ScaledFontSize(20.0f, 1.0f, 99.0f), 20.0f * MaxTextScale, 1.0e-4f);

    // Snap turn.
    CheckNear("snap turn snaps to the nearest 15 degrees", SnapTurnStepDegrees(52.0f), 45.0f, 1.0e-4f);
    CheckNear("snap turn snaps upward past the midpoint", SnapTurnStepDegrees(53.0f), 60.0f, 1.0e-4f);
    CheckNear("snap turn holds its floor", SnapTurnStepDegrees(0.0f), MinSnapTurn, 1.0e-4f);
    CheckNear("snap turn holds its ceiling", SnapTurnStepDegrees(500.0f), MaxSnapTurn, 1.0e-4f);
}

} // namespace

int main()
{
    TestPresets();
    TestClamp();
    TestMigration();
    TestCurves();

    int Passed = 0;
    for (const FCase& Case : Cases) { Passed += Case.bPassed ? 1 : 0; }
    const int Total = static_cast<int>(Cases.size());
    const bool bAllPassed = Passed == Total;

    std::printf("{\n");
    std::printf("  \"suite\": \"MikdashSettings::SettingsMath\",\n");
    std::printf("  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/SettingsMath.h\",\n");
    std::printf("  \"test\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Tests/SettingsMathTest.cpp\",\n");
    std::printf("  \"engineIndependent\": true,\n");
    std::printf("  \"settingsVersion\": %d,\n", CurrentVersion);
    std::printf("  \"oldestSupportedVersion\": %d,\n", OldestSupportedVersion);
    std::printf("  \"total\": %d,\n", Total);
    std::printf("  \"passed\": %d,\n", Passed);
    std::printf("  \"failed\": %d,\n", Total - Passed);
    std::printf("  \"status\": \"%s\",\n", bAllPassed ? "passed" : "failed");
    std::printf("  \"limitations\": [\n");
    std::printf("    \"Pure numeric check of the settings maths only. It establishes nothing about the widgets, the engine wiring, the saved file on disk, or how any of it looks on screen.\"\n");
    std::printf("  ],\n");
    std::printf("  \"cases\": [\n");
    for (int Index = 0; Index < Total; ++Index)
    {
        const FCase& Case = Cases[static_cast<size_t>(Index)];
        std::printf("    {\"group\": \"%s\", \"name\": \"%s\", \"passed\": %s, \"detail\": \"%s\"}%s\n",
                    Escape(Case.Group).c_str(), Escape(Case.Name).c_str(),
                    Case.bPassed ? "true" : "false", Escape(Case.Detail).c_str(),
                    Index + 1 < Total ? "," : "");
    }
    std::printf("  ]\n");
    std::printf("}\n");

    std::fprintf(stderr, "SettingsMathTest: %d/%d passed (%s)\n", Passed, Total, bAllPassed ? "PASS" : "FAIL");
    for (const FCase& Case : Cases)
    {
        if (!Case.bPassed)
        {
            std::fprintf(stderr, "  FAIL [%s] %s -- %s\n", Case.Group.c_str(), Case.Name.c_str(), Case.Detail.c_str());
        }
    }
    return bAllPassed ? 0 : 1;
}
