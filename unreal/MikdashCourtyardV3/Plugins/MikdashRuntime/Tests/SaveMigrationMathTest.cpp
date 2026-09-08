// SaveMigrationMathTest.cpp -- standalone test for Public/SaveMigrationMath.h.
//
// No Unreal, no test framework. Build and run with the VS2022 BuildTools toolchain:
//
//   call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
//   cl /nologo /EHsc /std:c++17 /W4 /I"<plugin>\Source\MikdashRuntime\Public" ^
//      "<plugin>\Tests\SaveMigrationMathTest.cpp" /Fe:SaveMigrationMathTest.exe
//   SaveMigrationMathTest.exe
//
// Exit code 0 when every case passes, 1 otherwise. The JSON on stdout is the receipt; a
// one-line human summary goes to stderr so a redirected stdout stays machine-readable.
//
// WHAT THIS TEST IS FOR
//
// Save corruption is the worst bug class in this feature. A visitor who loses an hour of
// walking to a half-written file has no way back, and the failure usually shows up on
// someone else's machine, months later, in a build nobody can rebuild. So the reader is
// attacked here rather than trusted:
//
//   * every single-bit flip in a valid save must be rejected,
//   * every truncation of a valid save must be rejected,
//   * a payload declaring an implausible length or count must be rejected BEFORE the
//     reader allocates or loops on that number,
//   * and on every rejection the caller's record must be left exactly as it was, because
//     a partially applied load is worse than a refused one.
//
// The migration half is checked field by field against what each old version actually
// carried, so "migrates without loss" means the fields v1 held are all still there and
// the fields it did not hold are at documented defaults -- not that the call returned Ok.

#include "SaveMigrationMath.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

using namespace MikdashSave;

namespace
{

// ---------------------------------------------------------------------------
// harness
// ---------------------------------------------------------------------------

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
    FCase Case;
    Case.Group = CurrentGroup;
    Case.Name = Name;
    Case.bPassed = bCondition;
    Case.Detail = Detail;
    Cases.push_back(Case);
}

std::string Num(double Value)
{
    char Buffer[64];
    std::snprintf(Buffer, sizeof(Buffer), "%.10g", Value);
    return std::string(Buffer);
}

std::string Num(long long Value)
{
    char Buffer[32];
    std::snprintf(Buffer, sizeof(Buffer), "%lld", Value);
    return std::string(Buffer);
}

// int32_t is `int` on MSVC, which is ambiguous between the double and long long
// overloads above; this resolves it without a cast at every call site.
std::string Num(int Value) { return Num(static_cast<long long>(Value)); }

void CheckEqual(const char* Name, double Actual, double Expected, double Tolerance = 0.0)
{
    const double Difference = std::fabs(Actual - Expected);
    Check(Name, Difference <= Tolerance, "got " + Num(Actual) + " expected " + Num(Expected));
}

void CheckEqualInt(const char* Name, long long Actual, long long Expected)
{
    Check(Name, Actual == Expected, "got " + Num(Actual) + " expected " + Num(Expected));
}

void CheckEqualStr(const char* Name, const std::string& Actual, const std::string& Expected)
{
    Check(Name, Actual == Expected, "got \"" + Actual + "\" expected \"" + Expected + "\"");
}

void CheckError(const char* Name, ESaveDecodeError Actual, ESaveDecodeError Expected)
{
    Check(Name, Actual == Expected,
          std::string("got ") + DescribeError(Actual) + ", expected " + DescribeError(Expected));
}

// ---------------------------------------------------------------------------
// helpers for building files by hand
// ---------------------------------------------------------------------------

/** Wrap a payload in a valid container header at the given record version. */
std::vector<uint8_t> MakeContainer(int32_t RecordVersion, const std::vector<uint8_t>& Payload,
                                   int32_t FormatVersion = CurrentFormatVersion)
{
    std::vector<uint8_t> Out;
    FByteWriter Writer(Out);
    Writer.U8(Magic0);
    Writer.U8(Magic1);
    Writer.U8(Magic2);
    Writer.U8(Magic3);
    Writer.I32(FormatVersion);
    Writer.I32(RecordVersion);
    Writer.U32(static_cast<uint32_t>(Payload.size()));
    Writer.U32(Crc32(Payload));
    Out.insert(Out.end(), Payload.begin(), Payload.end());
    return Out;
}

/** The v1 payload exactly as that build wrote it: amos, source axes, yaw only. */
std::vector<uint8_t> MakeV1Payload(const std::string& MapName,
                                   float SourceX, float SourceY, float SourceZ, float SourceYaw,
                                   uint8_t TimePreset, const std::vector<int32_t>& StopIndices,
                                   bool bTourActive)
{
    std::vector<uint8_t> Payload;
    FByteWriter Writer(Payload);
    Writer.Str(MapName);
    Writer.F32(SourceX);
    Writer.F32(SourceY);
    Writer.F32(SourceZ);
    Writer.F32(SourceYaw);
    Writer.U8(TimePreset);
    Writer.U32(static_cast<uint32_t>(StopIndices.size()));
    for (const int32_t Index : StopIndices) { Writer.I32(Index); }
    Writer.Bool(bTourActive);
    return Payload;
}

std::vector<uint8_t> MakeV2Payload(const std::string& MapName, const FTransformRecord& Transform,
                                   float Hours, uint32_t PlayTime, const std::vector<int32_t>& StopIndices,
                                   bool bTourActive, const std::vector<std::string>& Codex)
{
    std::vector<uint8_t> Payload;
    FByteWriter Writer(Payload);
    Writer.Str(MapName);
    Writer.F64(Transform.X);
    Writer.F64(Transform.Y);
    Writer.F64(Transform.Z);
    Writer.F64(Transform.Pitch);
    Writer.F64(Transform.Yaw);
    Writer.F64(Transform.Roll);
    Writer.F32(Hours);
    Writer.U32(PlayTime);
    Writer.U32(static_cast<uint32_t>(StopIndices.size()));
    for (const int32_t Index : StopIndices) { Writer.I32(Index); }
    Writer.Bool(bTourActive);
    Writer.U32(static_cast<uint32_t>(Codex.size()));
    for (const std::string& Entry : Codex) { Writer.Str(Entry); }
    return Payload;
}

std::vector<uint8_t> MakeV3Payload(const std::string& MapName, const FTransformRecord& Transform,
                                   float Hours, uint32_t PlayTime, const std::vector<std::string>& Stops,
                                   const std::string& CurrentStop, bool bTourActive,
                                   const std::vector<std::string>& Codex, const FPhotoRecord& Photo)
{
    std::vector<uint8_t> Payload;
    FByteWriter Writer(Payload);
    Writer.Str(MapName);
    Writer.F64(Transform.X);
    Writer.F64(Transform.Y);
    Writer.F64(Transform.Z);
    Writer.F64(Transform.Pitch);
    Writer.F64(Transform.Yaw);
    Writer.F64(Transform.Roll);
    Writer.F32(Hours);
    Writer.U32(PlayTime);
    Writer.U32(static_cast<uint32_t>(Stops.size()));
    for (const std::string& Stop : Stops) { Writer.Str(Stop); }
    Writer.Str(CurrentStop);
    Writer.Bool(bTourActive);
    Writer.U32(static_cast<uint32_t>(Codex.size()));
    for (const std::string& Entry : Codex) { Writer.Str(Entry); }
    Detail::WritePhotoBlock(Writer, Photo);
    return Payload;
}

/** A record with something interesting in every field, for the round-trip cases. */
FSaveRecord MakeRichRecord()
{
    FSaveRecord Record;
    Record.RecordVersion = CurrentRecordVersion;
    // Hebrew and an em dash: the save path is UTF-8 bytes end to end, and a label the
    // visitor typed in Hebrew must survive it byte for byte.
    Record.SlotLabel = "\xD7\x94\xD7\x99\xD7\x9B\xD7\x9C \xE2\x80\x94 Heikhal";
    Record.MapName = "/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough";
    Record.SaveTimeUnixSeconds = 1788000000ull;
    Record.PlayTimeSeconds = 9876543210ull;   // wider than 32 bits on purpose
    Record.BuildNumber = 4294967295u;

    Record.PlayerTransform.X = -6200.5;
    Record.PlayerTransform.Y = 1234.25;
    Record.PlayerTransform.Z = 925.0;
    Record.PlayerTransform.Pitch = -12.5;
    Record.PlayerTransform.Yaw = 179.75;
    Record.PlayerTransform.Roll = 0.125;

    Record.TimeOfDayHours = 5.5f;
    Record.bTimeOfDayPaused = true;

    Record.CompletedTourStops = { "stop.approach", "stop.azarah", "stop.heikhal" };
    Record.CurrentTourStop = "stop.heikhal";
    Record.bTourActive = true;

    Record.UnlockedCodexEntries = { "codex.menorah", "codex.shulchan", "codex.paroches" };

    Record.Photo.FieldOfViewDegrees = 24.0f;
    Record.Photo.ExposureCompensation = -1.75f;
    Record.Photo.FocusDistanceCm = 42000.0f;
    Record.Photo.Aperture = 1.4f;
    Record.Photo.RollDegrees = -3.5f;
    Record.Photo.ResolutionMultiplier = 4;
    Record.Photo.bHideInterface = false;
    Record.Photo.LookId = "look.evening";

    FOptionValue BoolOption;
    BoolOption.Key = "settings.bInvertY";
    BoolOption.Type = EOptionType::Bool;
    BoolOption.BoolValue = true;
    Record.Options.push_back(BoolOption);

    FOptionValue IntOption;
    IntOption.Key = "settings.ResolutionX";
    IntOption.Type = EOptionType::Int;
    IntOption.IntValue = -2147483647 - 1;   // INT32_MIN, written without the macro
    Record.Options.push_back(IntOption);

    FOptionValue FloatOption;
    FloatOption.Key = "settings.ScreenPercentage";
    FloatOption.Type = EOptionType::Float;
    FloatOption.FloatValue = 77.125f;
    Record.Options.push_back(FloatOption);

    FOptionValue StringOption;
    StringOption.Key = "settings.LastMap";
    StringOption.Type = EOptionType::String;
    StringOption.StringValue = "\xD7\xA2\xD7\x96\xD7\xA8\xD7\x94";   // "azarah" in Hebrew
    Record.Options.push_back(StringOption);

    return Record;
}

bool PhotoEqual(const FPhotoRecord& A, const FPhotoRecord& B)
{
    return A.FieldOfViewDegrees == B.FieldOfViewDegrees
        && A.ExposureCompensation == B.ExposureCompensation
        && A.FocusDistanceCm == B.FocusDistanceCm
        && A.Aperture == B.Aperture
        && A.RollDegrees == B.RollDegrees
        && A.ResolutionMultiplier == B.ResolutionMultiplier
        && A.bHideInterface == B.bHideInterface
        && A.LookId == B.LookId;
}

bool OptionEqual(const FOptionValue& A, const FOptionValue& B)
{
    if (A.Key != B.Key || A.Type != B.Type) { return false; }
    switch (A.Type)
    {
    case EOptionType::Bool:   return A.BoolValue == B.BoolValue;
    case EOptionType::Int:    return A.IntValue == B.IntValue;
    case EOptionType::Float:  return A.FloatValue == B.FloatValue;
    case EOptionType::String: return A.StringValue == B.StringValue;
    }
    return false;
}

/** Everything the v4 schema carries, compared exactly. No tolerance: this is a byte format. */
bool RecordEqual(const FSaveRecord& A, const FSaveRecord& B, std::string& OutFirstDifference)
{
    auto Differ = [&OutFirstDifference](const char* Field) { OutFirstDifference = Field; return false; };

    if (A.SlotLabel != B.SlotLabel)                       { return Differ("SlotLabel"); }
    if (A.MapName != B.MapName)                           { return Differ("MapName"); }
    if (A.SaveTimeUnixSeconds != B.SaveTimeUnixSeconds)   { return Differ("SaveTimeUnixSeconds"); }
    if (A.PlayTimeSeconds != B.PlayTimeSeconds)           { return Differ("PlayTimeSeconds"); }
    if (A.BuildNumber != B.BuildNumber)                   { return Differ("BuildNumber"); }
    if (A.PlayerTransform.X != B.PlayerTransform.X)       { return Differ("PlayerTransform.X"); }
    if (A.PlayerTransform.Y != B.PlayerTransform.Y)       { return Differ("PlayerTransform.Y"); }
    if (A.PlayerTransform.Z != B.PlayerTransform.Z)       { return Differ("PlayerTransform.Z"); }
    if (A.PlayerTransform.Pitch != B.PlayerTransform.Pitch) { return Differ("PlayerTransform.Pitch"); }
    if (A.PlayerTransform.Yaw != B.PlayerTransform.Yaw)   { return Differ("PlayerTransform.Yaw"); }
    if (A.PlayerTransform.Roll != B.PlayerTransform.Roll) { return Differ("PlayerTransform.Roll"); }
    if (A.TimeOfDayHours != B.TimeOfDayHours)             { return Differ("TimeOfDayHours"); }
    if (A.bTimeOfDayPaused != B.bTimeOfDayPaused)         { return Differ("bTimeOfDayPaused"); }
    if (A.CompletedTourStops != B.CompletedTourStops)     { return Differ("CompletedTourStops"); }
    if (A.CurrentTourStop != B.CurrentTourStop)           { return Differ("CurrentTourStop"); }
    if (A.bTourActive != B.bTourActive)                   { return Differ("bTourActive"); }
    if (A.UnlockedCodexEntries != B.UnlockedCodexEntries) { return Differ("UnlockedCodexEntries"); }
    if (!PhotoEqual(A.Photo, B.Photo))                    { return Differ("Photo"); }
    if (A.Options.size() != B.Options.size())             { return Differ("Options.size"); }
    for (size_t Index = 0; Index < A.Options.size(); ++Index)
    {
        if (!OptionEqual(A.Options[Index], B.Options[Index])) { return Differ("Options[i]"); }
    }
    return true;
}

/** A record filled with values no decode could ever produce, to prove nothing was written. */
FSaveRecord MakeSentinel()
{
    FSaveRecord Sentinel;
    Sentinel.SlotLabel = "SENTINEL-LABEL";
    Sentinel.MapName = "SENTINEL-MAP";
    Sentinel.SaveTimeUnixSeconds = 0xDEADBEEFull;
    Sentinel.PlayTimeSeconds = 0xFEEDFACEull;
    Sentinel.BuildNumber = 0x5A5A5A5Au;
    Sentinel.PlayerTransform.X = -999999.5;
    Sentinel.TimeOfDayHours = 3.25f;
    Sentinel.CompletedTourStops = { "sentinel.stop" };
    Sentinel.UnlockedCodexEntries = { "sentinel.codex" };
    Sentinel.CurrentTourStop = "sentinel.current";
    return Sentinel;
}

bool IsSentinelIntact(const FSaveRecord& Record)
{
    const FSaveRecord Expected = MakeSentinel();
    std::string Ignored;
    return RecordEqual(Record, Expected, Ignored);
}

// ---------------------------------------------------------------------------
// 1. round trip
// ---------------------------------------------------------------------------

void TestRoundTrip()
{
    Group("round trip");

    const FSaveRecord Original = MakeRichRecord();
    const std::vector<uint8_t> Bytes = Encode(Original);

    Check("encode produced a header plus a payload", Bytes.size() > static_cast<size_t>(HeaderBytes),
          Num(static_cast<long long>(Bytes.size())) + " bytes");
    Check("magic is MKDS",
          Bytes.size() >= 4 && Bytes[0] == 'M' && Bytes[1] == 'K' && Bytes[2] == 'D' && Bytes[3] == 'S');
    CheckEqualInt("header advertises the current record version",
                  PeekRecordVersion(Bytes.data(), Bytes.size()), CurrentRecordVersion);

    FSaveRecord Decoded;
    FMigrationReport Report;
    CheckError("a freshly written save decodes", Decode(Bytes, Decoded, Report), ESaveDecodeError::Ok);

    std::string Difference;
    Check("every field survives the round trip exactly", RecordEqual(Original, Decoded, Difference),
          Difference.empty() ? "" : "first difference: " + Difference);

    CheckEqualInt("a current-version save needs no migration steps", Report.StepsApplied, 0);
    CheckEqualInt("the decoded record reports the current version", Decoded.RecordVersion, CurrentRecordVersion);

    // Determinism matters because the receipt and the in-place verify in the save path
    // both assume the same record always produces the same bytes.
    const std::vector<uint8_t> Again = Encode(Original);
    Check("encoding is deterministic", Again == Bytes);

    const std::vector<uint8_t> Reencoded = Encode(Decoded);
    Check("re-encoding a decoded record reproduces the same bytes", Reencoded == Bytes);

    // An empty record is the state a brand-new slot is written from.
    const FSaveRecord Empty;
    const std::vector<uint8_t> EmptyBytes = Encode(Empty);
    FSaveRecord EmptyDecoded;
    FMigrationReport EmptyReport;
    CheckError("an empty record round-trips", Decode(EmptyBytes, EmptyDecoded, EmptyReport), ESaveDecodeError::Ok);
    std::string EmptyDifference;
    Check("an empty record survives unchanged", RecordEqual(Empty, EmptyDecoded, EmptyDifference),
          EmptyDifference.empty() ? "" : "first difference: " + EmptyDifference);

    // Non-finite floats. The photo block is written by another agent's UI; a NaN reaching
    // the file must not become a decode failure that costs the visitor the whole slot.
    FSaveRecord Weird = MakeRichRecord();
    Weird.Photo.ExposureCompensation = std::nanf("");
    Weird.Photo.FocusDistanceCm = 3.4e38f;
    Weird.PlayerTransform.Z = 1.0e300;
    const std::vector<uint8_t> WeirdBytes = Encode(Weird);
    FSaveRecord WeirdDecoded;
    FMigrationReport WeirdReport;
    CheckError("a record holding NaN and huge floats still round-trips",
               Decode(WeirdBytes, WeirdDecoded, WeirdReport), ESaveDecodeError::Ok);
    Check("NaN survives as NaN rather than becoming a decode failure",
          WeirdDecoded.Photo.ExposureCompensation != WeirdDecoded.Photo.ExposureCompensation);
    CheckEqual("a huge coordinate survives exactly", WeirdDecoded.PlayerTransform.Z, 1.0e300, 0.0);

    // The one field the decoder deliberately rewrites: an out-of-range yaw is normalised.
    FSaveRecord Spun = MakeRichRecord();
    Spun.PlayerTransform.Yaw = 725.0;   // two turns and five degrees
    FSaveRecord SpunDecoded;
    FMigrationReport SpunReport;
    Decode(Encode(Spun), SpunDecoded, SpunReport);
    CheckEqual("an out-of-range yaw is normalised on load", SpunDecoded.PlayerTransform.Yaw, 5.0, 1.0e-9);

    // Long strings and full lists, at the ceilings the format declares.
    FSaveRecord Big;
    Big.SlotLabel = std::string(static_cast<size_t>(MaxStringBytes) + 100, 'x');
    for (uint32_t Index = 0; Index < 64; ++Index)
    {
        Big.CompletedTourStops.push_back("stop." + std::to_string(Index));
        Big.UnlockedCodexEntries.push_back("codex." + std::to_string(Index));
    }
    for (uint32_t Index = 0; Index < MaxOptionCount; ++Index)
    {
        FOptionValue Option;
        Option.Key = "settings.key" + std::to_string(Index);
        Option.Type = EOptionType::Int;
        Option.IntValue = static_cast<int32_t>(Index);
        Big.Options.push_back(Option);
    }
    FSaveRecord BigDecoded;
    FMigrationReport BigReport;
    CheckError("a record at the format's ceilings round-trips",
               Decode(Encode(Big), BigDecoded, BigReport), ESaveDecodeError::Ok);
    CheckEqualInt("an over-long label is truncated to the declared ceiling, not rejected",
                  static_cast<long long>(BigDecoded.SlotLabel.size()), static_cast<long long>(MaxStringBytes));
    CheckEqualInt("all option entries survive at the ceiling",
                  static_cast<long long>(BigDecoded.Options.size()), static_cast<long long>(MaxOptionCount));
    CheckEqualInt("all tour stops survive", static_cast<long long>(BigDecoded.CompletedTourStops.size()), 64);
    CheckEqualInt("all codex entries survive", static_cast<long long>(BigDecoded.UnlockedCodexEntries.size()), 64);

    // Empty strings inside a list are a real case: a stop identifier that was never set.
    FSaveRecord Blanks;
    Blanks.CompletedTourStops = { "", "stop.azarah", "" };
    Blanks.CurrentTourStop = "";
    FSaveRecord BlanksDecoded;
    FMigrationReport BlanksReport;
    CheckError("empty strings inside a list round-trip",
               Decode(Encode(Blanks), BlanksDecoded, BlanksReport), ESaveDecodeError::Ok);
    Check("empty strings are preserved, not dropped", BlanksDecoded.CompletedTourStops == Blanks.CompletedTourStops);
}

// ---------------------------------------------------------------------------
// 2. migration
// ---------------------------------------------------------------------------

void TestV1Migration()
{
    Group("v1 migration");

    // A plausible v1 save: standing in the Heikhal, facing the Kodesh HaKodashim, at the
    // Afternoon preset, six of the eight stops done, tour still running.
    const std::vector<int32_t> Stops = { 0, 1, 2, 3, 4, 5 };
    const std::vector<uint8_t> Payload =
        MakeV1Payload("/Game/MikdashV3/Maps/Courtyard", -124.0f, 18.5f, 24.0f, 90.0f, 3, Stops, true);
    const std::vector<uint8_t> File = MakeContainer(1, Payload);

    CheckEqualInt("a v1 file advertises version 1", PeekRecordVersion(File.data(), File.size()), 1);

    FSaveRecord Record;
    FMigrationReport Report;
    CheckError("a v1 save loads", Decode(File, Record, Report), ESaveDecodeError::Ok);

    CheckEqualInt("the report names the version it came from", Report.FromVersion, 1);
    CheckEqualInt("the report names the version it reached", Report.ToVersion, CurrentRecordVersion);
    CheckEqualInt("three migration steps ran", Report.StepsApplied, 3);
    CheckEqualInt("the record now claims the current version", Record.RecordVersion, CurrentRecordVersion);

    // Nothing v1 actually carried may be lost.
    CheckEqualStr("the map name survives", Record.MapName, "/Game/MikdashV3/Maps/Courtyard");
    Check("the tour-active flag survives", Record.bTourActive);

    // Position: amos in source axes (X east, Y up, Z south) to Unreal centimetres, which is
    // [x*50, z*50, y*50]. Getting this backwards would put the visitor inside a wall, and
    // it would look plausible enough on a slot card to ship.
    CheckEqual("v1 X converts to centimetres", Record.PlayerTransform.X, -124.0 * 50.0, 1.0e-6);
    CheckEqual("v1 source Z becomes Unreal Y", Record.PlayerTransform.Y, 24.0 * 50.0, 1.0e-6);
    CheckEqual("v1 source Y (up) becomes Unreal Z", Record.PlayerTransform.Z, 18.5 * 50.0, 1.0e-6);
    CheckEqual("v1 yaw reverses sense", Record.PlayerTransform.Yaw, -90.0, 1.0e-9);
    CheckEqual("v1 had no pitch, so pitch is zero", Record.PlayerTransform.Pitch, 0.0, 0.0);
    CheckEqual("v1 had no roll, so roll is zero", Record.PlayerTransform.Roll, 0.0, 0.0);
    Check("the report records that coordinates were converted", Report.bCoordinatesConverted);

    // Time of day: preset 3 is Afternoon, 15:00 in the table that build shipped with.
    CheckEqual("the time-of-day preset expands to its hour", Record.TimeOfDayHours, 15.0, 1.0e-6);
    Check("the preset was in range", !Report.bTimeOfDayPresetOutOfRange);

    // Tour stops: indices become the identifiers that build's route used, in save order.
    const std::vector<std::string> Expected = {
        "stop.approach", "stop.har", "stop.ezras_nashim", "stop.azarah", "stop.mizbeach", "stop.ulam"
    };
    Check("stop indices become stop identifiers, in order", Record.CompletedTourStops == Expected);
    CheckEqualInt("no stop was dropped", Report.TourStopsDropped, 0);
    CheckEqualStr("the current stop becomes the last one completed", Record.CurrentTourStop, "stop.ulam");

    // Fields v1 simply did not have, at their documented defaults.
    CheckEqualInt("play time defaults to zero", static_cast<long long>(Record.PlayTimeSeconds), 0);
    CheckEqualInt("the codex starts empty", static_cast<long long>(Record.UnlockedCodexEntries.size()), 0);
    CheckEqualInt("no options were invented", static_cast<long long>(Record.Options.size()), 0);
    CheckEqualStr("the slot label is empty for the front end to fill", Record.SlotLabel, "");
    CheckEqualInt("the save time is unknown", static_cast<long long>(Record.SaveTimeUnixSeconds), 0);
    Check("photo mode is at its defaults", PhotoEqual(Record.Photo, FPhotoRecord()));
    Check("time of day is not paused", !Record.bTimeOfDayPaused);
    Check("the report counts the fields it had to default", Report.FieldsDefaulted >= 7,
          "counted " + Num(static_cast<long long>(Report.FieldsDefaulted)));

    // A migrated record must be writable again without loss: this is what makes an old
    // save become a current one the first time the visitor saves after loading it.
    const std::vector<uint8_t> Rewritten = Encode(Record);
    FSaveRecord Reloaded;
    FMigrationReport RewriteReport;
    CheckError("a migrated record can be written back out", Decode(Rewritten, Reloaded, RewriteReport),
               ESaveDecodeError::Ok);
    CheckEqualInt("the rewritten file is at the current version", RewriteReport.StepsApplied, 0);
    std::string Difference;
    Check("nothing is lost between the migration and the rewrite", RecordEqual(Record, Reloaded, Difference),
          Difference.empty() ? "" : "first difference: " + Difference);

    // Out-of-range legacy data.
    const std::vector<int32_t> BadStops = { 0, 99, 3, -1, 7 };
    FSaveRecord BadRecord;
    FMigrationReport BadReport;
    CheckError("a v1 save with impossible stop indices still loads",
               Decode(MakeContainer(1, MakeV1Payload("m", 0.f, 0.f, 0.f, 0.f, 200, BadStops, false)),
                      BadRecord, BadReport),
               ESaveDecodeError::Ok);
    CheckEqualInt("stops outside that build's route are dropped", BadReport.TourStopsDropped, 2);
    CheckEqualInt("the stops that do exist are kept",
                  static_cast<long long>(BadRecord.CompletedTourStops.size()), 3);
    Check("an out-of-range time preset is flagged", BadReport.bTimeOfDayPresetOutOfRange);
    CheckEqual("an out-of-range time preset falls back to midday", BadRecord.TimeOfDayHours, 12.0, 1.0e-6);

    // An empty v1 save: no stops, no map name. The degenerate case a first-launch build wrote.
    FSaveRecord EmptyRecord;
    FMigrationReport EmptyReport;
    CheckError("an empty v1 save loads",
               Decode(MakeContainer(1, MakeV1Payload("", 0.f, 0.f, 0.f, 0.f, 0, {}, false)),
                      EmptyRecord, EmptyReport),
               ESaveDecodeError::Ok);
    CheckEqualStr("an empty v1 save leaves no current stop", EmptyRecord.CurrentTourStop, "");
    CheckEqual("preset 0 is dawn", EmptyRecord.TimeOfDayHours, 5.0, 1.0e-6);
}

void TestV2AndV3Migration()
{
    Group("v2 and v3 migration");

    FTransformRecord Transform;
    Transform.X = -6200.0;
    Transform.Y = 100.0;
    Transform.Z = 925.0;
    Transform.Pitch = -8.0;
    Transform.Yaw = 181.0;      // deliberately outside (-180, 180]
    Transform.Roll = 0.0;

    const std::vector<int32_t> Stops = { 6, 7 };
    const std::vector<std::string> Codex = { "codex.aron", "codex.keruvim" };

    FSaveRecord Record;
    FMigrationReport Report;
    CheckError("a v2 save loads",
               Decode(MakeContainer(2, MakeV2Payload("map2", Transform, 18.25f, 3600u, Stops, true, Codex)),
                      Record, Report),
               ESaveDecodeError::Ok);
    CheckEqualInt("two migration steps ran from v2", Report.StepsApplied, 2);
    CheckEqual("v2 coordinates are already centimetres and are not converted again",
               Record.PlayerTransform.X, -6200.0, 0.0);
    Check("v2 did not need a coordinate conversion", !Report.bCoordinatesConverted);
    CheckEqual("v2 yaw is normalised into range", Record.PlayerTransform.Yaw, -179.0, 1.0e-9);
    CheckEqual("v2 hours survive", Record.TimeOfDayHours, 18.25, 1.0e-6);
    CheckEqualInt("v2 play time survives", static_cast<long long>(Record.PlayTimeSeconds), 3600);
    Check("v2 codex entries survive", Record.UnlockedCodexEntries == Codex);
    const std::vector<std::string> ExpectedStops = { "stop.heikhal", "stop.kodesh_hakodashim" };
    Check("v2 stop indices become identifiers", Record.CompletedTourStops == ExpectedStops);
    CheckEqualStr("v2 current stop is the last completed", Record.CurrentTourStop, "stop.kodesh_hakodashim");
    Check("v2 photo mode is defaulted", PhotoEqual(Record.Photo, FPhotoRecord()));

    FPhotoRecord Photo;
    Photo.FieldOfViewDegrees = 35.0f;
    Photo.Aperture = 2.8f;
    Photo.ResolutionMultiplier = 2;
    Photo.bHideInterface = false;
    Photo.LookId = "look.dawn";

    const std::vector<std::string> V3Stops = { "stop.azarah", "stop.mizbeach" };
    FSaveRecord V3Record;
    FMigrationReport V3Report;
    CheckError("a v3 save loads",
               Decode(MakeContainer(3, MakeV3Payload("map3", Transform, 6.5f, 120u, V3Stops,
                                                     "stop.mizbeach", false, Codex, Photo)),
                      V3Record, V3Report),
               ESaveDecodeError::Ok);
    CheckEqualInt("one migration step ran from v3", V3Report.StepsApplied, 1);
    Check("v3 stop identifiers survive unchanged", V3Record.CompletedTourStops == V3Stops);
    CheckEqualStr("v3 current stop survives", V3Record.CurrentTourStop, "stop.mizbeach");
    Check("v3 photo mode survives", PhotoEqual(V3Record.Photo, Photo));
    CheckEqualInt("v3 gained no options", static_cast<long long>(V3Record.Options.size()), 0);
    Check("v3 gained a not-paused time of day", !V3Record.bTimeOfDayPaused);
    CheckEqualInt("v3 gained an unknown save time", static_cast<long long>(V3Record.SaveTimeUnixSeconds), 0);

    // Every supported version must reach the current one. Adding version 5 without adding
    // its migration step makes this fail rather than silently skipping the step.
    bool bAllVersionsLoad = true;
    for (int32_t Version = OldestSupportedVersion; Version <= CurrentRecordVersion; ++Version)
    {
        std::vector<uint8_t> File;
        switch (Version)
        {
        case 1: File = MakeContainer(1, MakeV1Payload("m", 1.f, 2.f, 3.f, 0.f, 1, { 0 }, false)); break;
        case 2: File = MakeContainer(2, MakeV2Payload("m", Transform, 12.f, 0u, { 0 }, false, {})); break;
        case 3: File = MakeContainer(3, MakeV3Payload("m", Transform, 12.f, 0u, { "s" }, "s", false, {}, Photo)); break;
        default: File = Encode(MakeRichRecord()); break;
        }
        FSaveRecord Loaded;
        FMigrationReport LoadedReport;
        if (Decode(File, Loaded, LoadedReport) != ESaveDecodeError::Ok ||
            Loaded.RecordVersion != CurrentRecordVersion ||
            LoadedReport.StepsApplied != CurrentRecordVersion - Version)
        {
            bAllVersionsLoad = false;
        }
    }
    Check("every supported version reaches the current one in the right number of steps", bAllVersionsLoad);
}

// ---------------------------------------------------------------------------
// 3. rejection of corrupt and truncated files
// ---------------------------------------------------------------------------

void TestRejection()
{
    Group("corrupt and truncated saves");

    const std::vector<uint8_t> Good = Encode(MakeRichRecord());

    FSaveRecord Record;
    FMigrationReport Report;

    // The trivial rejections.
    CheckError("a null buffer is rejected", Decode(nullptr, 0, Record, Report), ESaveDecodeError::BufferTooSmall);
    CheckError("a null buffer with a claimed length is rejected",
               Decode(nullptr, 4096, Record, Report), ESaveDecodeError::BufferTooSmall);
    CheckError("an empty file is rejected", Decode(std::vector<uint8_t>(), Record, Report),
               ESaveDecodeError::BufferTooSmall);
    CheckError("a file one byte short of a header is rejected",
               Decode(Good.data(), static_cast<size_t>(HeaderBytes) - 1, Record, Report),
               ESaveDecodeError::BufferTooSmall);

    {
        std::vector<uint8_t> NotMikdash(64, 0);
        NotMikdash[0] = 'P'; NotMikdash[1] = 'K';   // a zip, which is what a wrong file usually is
        CheckError("a file that is not a Mikdash save is rejected",
                   Decode(NotMikdash, Record, Report), ESaveDecodeError::BadMagic);
    }
    {
        std::vector<uint8_t> AllZero(4096, 0);
        CheckError("a file of zeroes is rejected", Decode(AllZero, Record, Report), ESaveDecodeError::BadMagic);
    }

    // Container and record versions.
    CheckError("an unknown container format is rejected",
               Decode(MakeContainer(CurrentRecordVersion, std::vector<uint8_t>(), 2), Record, Report),
               ESaveDecodeError::UnsupportedFormat);
    CheckError("a record version below the oldest supported is rejected",
               Decode(MakeContainer(OldestSupportedVersion - 1, std::vector<uint8_t>()), Record, Report),
               ESaveDecodeError::VersionTooOld);
    CheckError("a record version from a newer build is rejected rather than guessed at",
               Decode(MakeContainer(CurrentRecordVersion + 1, std::vector<uint8_t>()), Record, Report),
               ESaveDecodeError::VersionTooNew);
    CheckError("a negative record version is rejected",
               Decode(MakeContainer(-1, std::vector<uint8_t>()), Record, Report),
               ESaveDecodeError::VersionTooOld);

    // Length fields. These are the ones that turn into an allocation if they are trusted.
    {
        std::vector<uint8_t> Huge = Good;
        const uint32_t Claim = MaxPayloadBytes + 1u;
        std::memcpy(Huge.data() + 12, &Claim, 4);
        CheckError("an implausibly large declared payload is refused before anything is read",
                   Decode(Huge, Record, Report), ESaveDecodeError::PayloadTooLarge);
    }
    {
        std::vector<uint8_t> Huge = Good;
        const uint32_t Claim = 0xFFFFFFFFu;
        std::memcpy(Huge.data() + 12, &Claim, 4);
        CheckError("a payload length of 0xFFFFFFFF is refused",
                   Decode(Huge, Record, Report), ESaveDecodeError::PayloadTooLarge);
    }
    {
        std::vector<uint8_t> Padded = Good;
        Padded.push_back(0);
        CheckError("a file with a byte appended is rejected",
                   Decode(Padded, Record, Report), ESaveDecodeError::LengthMismatch);
    }

    // TRUNCATION AT EVERY LENGTH. A save interrupted by a power cut or a full disk is a
    // prefix of a good file; not one prefix of any length may decode as Ok.
    {
        int32_t FirstAccepted = -1;
        int32_t Crashes = 0;
        for (size_t Length = 0; Length < Good.size(); ++Length)
        {
            FSaveRecord Truncated = MakeSentinel();
            FMigrationReport TruncatedReport;
            const ESaveDecodeError Error = Decode(Good.data(), Length, Truncated, TruncatedReport);
            if (Error == ESaveDecodeError::Ok && FirstAccepted < 0)
            {
                FirstAccepted = static_cast<int32_t>(Length);
            }
            if (!IsSentinelIntact(Truncated))
            {
                ++Crashes;
            }
        }
        Check("no truncation of a valid save is accepted", FirstAccepted < 0,
              FirstAccepted < 0 ? "checked " + Num(static_cast<long long>(Good.size())) + " prefixes"
                                : "accepted a prefix of " + Num(FirstAccepted) + " bytes");
        Check("a rejected truncation leaves the caller's record untouched", Crashes == 0,
              Crashes == 0 ? "" : Num(Crashes) + " truncations wrote into the record");
    }

    // SINGLE-BIT FLIPS. Disk rot, a bad cable and a half-flushed write all look like this.
    // CRC-32 detects every single-bit error in the payload; the header checks catch the
    // rest. Not one flip may decode as Ok.
    {
        int32_t Accepted = 0;
        int32_t Touched = 0;
        std::string FirstFailure;
        for (size_t ByteIndex = 0; ByteIndex < Good.size(); ++ByteIndex)
        {
            for (int Bit = 0; Bit < 8; ++Bit)
            {
                std::vector<uint8_t> Flipped = Good;
                Flipped[ByteIndex] ^= static_cast<uint8_t>(1u << Bit);

                FSaveRecord Out = MakeSentinel();
                FMigrationReport OutReport;
                if (Decode(Flipped, Out, OutReport) == ESaveDecodeError::Ok)
                {
                    ++Accepted;
                    if (FirstFailure.empty())
                    {
                        FirstFailure = "byte " + Num(static_cast<long long>(ByteIndex)) + " bit " + Num(static_cast<long long>(Bit));
                    }
                }
                else if (!IsSentinelIntact(Out))
                {
                    ++Touched;
                }
            }
        }
        Check("no single-bit corruption of a valid save is accepted", Accepted == 0,
              Accepted == 0 ? "checked " + Num(static_cast<long long>(Good.size() * 8)) + " flips"
                            : Num(Accepted) + " accepted, first at " + FirstFailure);
        Check("a rejected corruption leaves the caller's record untouched", Touched == 0,
              Touched == 0 ? "" : Num(Touched) + " flips wrote into the record");
    }

    // A checksum that simply does not match, with everything else intact.
    {
        std::vector<uint8_t> BadCrc = Good;
        BadCrc[16] = static_cast<uint8_t>(BadCrc[16] ^ 0xFF);
        CheckError("a payload that fails its checksum is rejected",
                   Decode(BadCrc, Record, Report), ESaveDecodeError::ChecksumMismatch);
    }

    // Hostile payloads: the container is perfectly well formed, and the attack is inside.
    {
        std::vector<uint8_t> Payload;
        FByteWriter Writer(Payload);
        Writer.Str("map");
        Writer.U32(0xFFFFFFFFu);          // a string length of four gigabytes
        const std::vector<uint8_t> File = MakeContainer(3, Payload);
        FSaveRecord Out = MakeSentinel();
        FMigrationReport OutReport;
        const ESaveDecodeError Error = Decode(File, Out, OutReport);
        Check("a four-gigabyte string length is refused without allocating",
              Error == ESaveDecodeError::FieldOutOfRange || Error == ESaveDecodeError::PayloadUnderrun,
              std::string("got ") + DescribeError(Error));
        Check("the record is untouched after a hostile string length", IsSentinelIntact(Out));
    }
    {
        // A v4 payload whose tour-stop count is above the declared ceiling. The reader must
        // refuse on the count itself, before it reserves anything or enters the loop.
        std::vector<uint8_t> Payload;
        FByteWriter Writer(Payload);
        Writer.Str("label");
        Writer.Str("map");
        Writer.U64(0);
        Writer.U64(0);
        Writer.U32(0);
        for (int Index = 0; Index < 6; ++Index) { Writer.F64(0.0); }
        Writer.F32(12.0f);
        Writer.Bool(false);
        Writer.U32(MaxArrayCount + 1u);   // the hostile count
        const std::vector<uint8_t> File = MakeContainer(4, Payload);
        FSaveRecord Out = MakeSentinel();
        FMigrationReport OutReport;
        CheckError("an array count above the ceiling is refused",
                   Decode(File, Out, OutReport), ESaveDecodeError::FieldOutOfRange);
        Check("the record is untouched after a hostile array count", IsSentinelIntact(Out));
    }
    {
        // An option type byte outside the enum. Casting it blindly would be undefined
        // behaviour and would then be switched on.
        FSaveRecord Base;
        Base.Options.clear();
        std::vector<uint8_t> Payload;
        FByteWriter Writer(Payload);
        Detail::WriteV4Payload(Writer, Base);
        // The final field of the payload is the option count, written as 0. Replace it with
        // one option whose type byte is 200.
        Payload.resize(Payload.size() - 4);
        FByteWriter Extra(Payload);
        Extra.U32(1);
        Extra.Str("settings.bogus");
        Extra.U8(200);
        const std::vector<uint8_t> File = MakeContainer(4, Payload);
        FSaveRecord Out = MakeSentinel();
        FMigrationReport OutReport;
        CheckError("an unknown option type is refused", Decode(File, Out, OutReport),
                   ESaveDecodeError::FieldOutOfRange);
        Check("the record is untouched after an unknown option type", IsSentinelIntact(Out));
    }
    {
        // Trailing bytes: the container length and checksum are correct, but the schema
        // consumes less than the payload holds. That is a payload from a build with a
        // different schema, and guessing at it is how a field lands in the wrong place.
        std::vector<uint8_t> Payload;
        FByteWriter Writer(Payload);
        Detail::WriteV4Payload(Writer, FSaveRecord());
        Payload.push_back(0x7F);
        const std::vector<uint8_t> File = MakeContainer(4, Payload);
        FSaveRecord Out = MakeSentinel();
        FMigrationReport OutReport;
        CheckError("a payload with unread trailing bytes is refused",
                   Decode(File, Out, OutReport), ESaveDecodeError::PayloadTrailingBytes);
        Check("the record is untouched after trailing bytes", IsSentinelIntact(Out));
    }
    {
        // Underrun: the payload ends inside a field. The container is consistent, so only
        // the reader's own bounds checks can catch this.
        std::vector<uint8_t> Payload;
        FByteWriter Writer(Payload);
        Detail::WriteV4Payload(Writer, FSaveRecord());
        Payload.resize(Payload.size() - 3);
        const std::vector<uint8_t> File = MakeContainer(4, Payload);
        FSaveRecord Out = MakeSentinel();
        FMigrationReport OutReport;
        CheckError("a payload that ends inside a field is refused",
                   Decode(File, Out, OutReport), ESaveDecodeError::PayloadUnderrun);
        Check("the record is untouched after an underrun", IsSentinelIntact(Out));
    }
    {
        // A v1 file whose payload is empty. Every field underruns immediately.
        const std::vector<uint8_t> File = MakeContainer(1, std::vector<uint8_t>());
        FSaveRecord Out = MakeSentinel();
        FMigrationReport OutReport;
        CheckError("a v1 file with no payload is refused",
                   Decode(File, Out, OutReport), ESaveDecodeError::PayloadUnderrun);
        Check("the record is untouched after an empty v1 payload", IsSentinelIntact(Out));
    }

    // PeekRecordVersion must be as defensive as Decode: the slot list calls it on files it
    // has not validated yet.
    CheckEqualInt("peeking a null buffer returns zero", PeekRecordVersion(nullptr, 0), 0);
    CheckEqualInt("peeking a short buffer returns zero",
                  PeekRecordVersion(Good.data(), static_cast<size_t>(HeaderBytes) - 1), 0);
    {
        std::vector<uint8_t> NotMikdash(64, 0);
        CheckEqualInt("peeking a foreign file returns zero", PeekRecordVersion(NotMikdash.data(), NotMikdash.size()), 0);
    }
    {
        std::vector<uint8_t> BadFormat = MakeContainer(3, std::vector<uint8_t>(), 99);
        CheckEqualInt("peeking an unknown container format returns zero",
                      PeekRecordVersion(BadFormat.data(), BadFormat.size()), 0);
    }

    // Every error code must have wording. An unexplained refusal on a load screen is only
    // marginally better than a crash.
    {
        bool bAllDescribed = true;
        for (int Index = 0; Index <= static_cast<int>(ESaveDecodeError::FieldOutOfRange); ++Index)
        {
            const char* Text = DescribeError(static_cast<ESaveDecodeError>(Index));
            if (Text == nullptr || Text[0] == '\0') { bAllDescribed = false; }
        }
        Check("every error code has human wording", bAllDescribed);
    }
}

// ---------------------------------------------------------------------------
// 4. numeric helpers
// ---------------------------------------------------------------------------

void TestNumericHelpers()
{
    Group("numeric helpers");

    // The IEEE CRC-32 check value. If this is wrong then every save this build writes is
    // unreadable by every other build, which is a format break disguised as a passing test.
    {
        const char* Check9 = "123456789";
        const uint32_t Value = Crc32(reinterpret_cast<const uint8_t*>(Check9), 9);
        Check("CRC-32 matches the IEEE check value", Value == 0xCBF43926u,
              "got 0x" + std::string(1, "0123456789ABCDEF"[(Value >> 28) & 0xF]) + "...");
    }
    CheckEqualInt("CRC-32 of nothing is zero", static_cast<long long>(Crc32(nullptr, 0)), 0);

    CheckEqual("NaN degrees become zero", NormalizeDegrees(std::nan("")), 0.0, 0.0);
    CheckEqual("an absurd angle becomes zero", NormalizeDegrees(1.0e12), 0.0, 0.0);
    CheckEqual("540 degrees normalises to 180", NormalizeDegrees(540.0), 180.0, 1.0e-9);
    CheckEqual("-540 degrees normalises to 180", NormalizeDegrees(-540.0), 180.0, 1.0e-9);
    CheckEqual("-180 folds to 180", NormalizeDegrees(-180.0), 180.0, 0.0);
    CheckEqual("180 stays 180", NormalizeDegrees(180.0), 180.0, 0.0);
    CheckEqual("359 becomes -1", NormalizeDegrees(359.0), -1.0, 1.0e-9);
    CheckEqual("zero stays zero", NormalizeDegrees(0.0), 0.0, 0.0);
    CheckEqual("normalising twice changes nothing", NormalizeDegrees(NormalizeDegrees(721.5)),
               NormalizeDegrees(721.5), 0.0);

    CheckEqual("NaN hours become midday", ClampTimeOfDayHours(std::nanf("")), 12.0, 0.0);
    CheckEqual("negative hours clamp to midnight", ClampTimeOfDayHours(-3.0f), 0.0, 0.0);
    CheckEqual("24 hours wraps to zero", ClampTimeOfDayHours(24.0f), 0.0, 1.0e-6);
    CheckEqual("25 hours wraps to one", ClampTimeOfDayHours(25.0f), 1.0, 1.0e-6);
    CheckEqual("a valid hour is untouched", ClampTimeOfDayHours(23.5f), 23.5, 1.0e-6);

    {
        const FTransformRecord Converted = SourceAmosToUnrealCm(2.0, 3.0, 5.0);
        CheckEqual("source X scales by 50", Converted.X, 100.0, 0.0);
        CheckEqual("source Z becomes Unreal Y", Converted.Y, 250.0, 0.0);
        CheckEqual("source Y becomes Unreal Z", Converted.Z, 150.0, 0.0);
        CheckEqual("one amah is fifty centimetres", CentimetresPerAmah, 50.0, 0.0);
    }
    CheckEqual("source yaw reverses", SourceYawToUnrealYaw(45.0), -45.0, 1.0e-9);
    CheckEqual("source yaw reversal normalises", SourceYawToUnrealYaw(-190.0), -170.0, 1.0e-9);

    {
        bool bOutOfRange = true;
        CheckEqual("preset 2 is midday", LegacyTimeOfDayPresetToHours(2, bOutOfRange), 12.0, 0.0);
        Check("preset 2 is in range", !bOutOfRange);
        LegacyTimeOfDayPresetToHours(-1, bOutOfRange);
        Check("a negative preset is out of range", bOutOfRange);
        LegacyTimeOfDayPresetToHours(LegacyTimeOfDayPresetCount, bOutOfRange);
        Check("a preset one past the table is out of range", bOutOfRange);
    }

    Check("legacy stop 0 is the approach",
          LegacyTourStopId(0) != nullptr && std::strcmp(LegacyTourStopId(0), "stop.approach") == 0);
    Check("legacy stop 7 is the Kodesh HaKodashim",
          LegacyTourStopId(7) != nullptr && std::strcmp(LegacyTourStopId(7), "stop.kodesh_hakodashim") == 0);
    Check("a legacy stop index off the end has no identifier", LegacyTourStopId(LegacyTourStopCount) == nullptr);
    Check("a negative legacy stop index has no identifier", LegacyTourStopId(-1) == nullptr);
}

// ---------------------------------------------------------------------------
// 5. right-to-left layout
// ---------------------------------------------------------------------------

void TestRtl()
{
    using namespace MikdashRtl;

    Group("RTL: enum agreement with Slate");

    // The runtime casts between these and Slate's own enums. If the engine ever renumbers
    // them the cast becomes silent nonsense, so the numbers are asserted here rather than
    // assumed. Values checked against UE 5.8:
    //   SlateCore/Public/Layout/FlowDirection.h  EFlowDirection, EFlowDirectionPreference
    //   SlateCore/Public/Types/SlateEnums.h      ETextJustify::Type
    CheckEqualInt("EFlow::LeftToRight is 0", static_cast<int>(EFlow::LeftToRight), 0);
    CheckEqualInt("EFlow::RightToLeft is 1", static_cast<int>(EFlow::RightToLeft), 1);
    CheckEqualInt("EFlowPreference::Inherit is 0", static_cast<int>(EFlowPreference::Inherit), 0);
    CheckEqualInt("EFlowPreference::Culture is 1", static_cast<int>(EFlowPreference::Culture), 1);
    CheckEqualInt("EFlowPreference::LeftToRight is 2", static_cast<int>(EFlowPreference::LeftToRight), 2);
    CheckEqualInt("EFlowPreference::RightToLeft is 3", static_cast<int>(EFlowPreference::RightToLeft), 3);
    CheckEqualInt("EJustify::Left is 0", static_cast<int>(EJustify::Left), 0);
    CheckEqualInt("EJustify::Center is 1", static_cast<int>(EJustify::Center), 1);
    CheckEqualInt("EJustify::Right is 2", static_cast<int>(EJustify::Right), 2);

    Group("RTL: culture to direction");

    Check("he is right to left", LayoutDirectionForCulture("he") == EFlow::RightToLeft);
    Check("he-IL is right to left", LayoutDirectionForCulture("he-IL") == EFlow::RightToLeft);
    Check("he_IL is right to left", LayoutDirectionForCulture("he_IL") == EFlow::RightToLeft);
    Check("HE-il is right to left", LayoutDirectionForCulture("HE-il") == EFlow::RightToLeft);
    Check("the deprecated iw code is right to left", LayoutDirectionForCulture("iw") == EFlow::RightToLeft);
    Check("iw-IL is right to left", LayoutDirectionForCulture("iw-IL") == EFlow::RightToLeft);
    Check("yi (Yiddish, Hebrew script) is right to left", LayoutDirectionForCulture("yi") == EFlow::RightToLeft);
    Check("ar is right to left", LayoutDirectionForCulture("ar") == EFlow::RightToLeft);
    Check("en is left to right", LayoutDirectionForCulture("en") == EFlow::LeftToRight);
    Check("en-US is left to right", LayoutDirectionForCulture("en-US") == EFlow::LeftToRight);
    Check("an empty culture code is left to right", LayoutDirectionForCulture("") == EFlow::LeftToRight);
    Check("a null culture code is left to right", LayoutDirectionForCulture(nullptr) == EFlow::LeftToRight);
    // "hen" must not match "he" on a prefix: a language subtag is compared whole.
    Check("hen does not match he on a prefix", LayoutDirectionForCulture("hen") == EFlow::LeftToRight);
    Check("a very long subtag does not overflow the buffer",
          LayoutDirectionForCulture("abcdefghijklmnopqrstuvwxyz") == EFlow::LeftToRight);

    Group("RTL: flow resolution");

    Check("Inherit keeps the parent's flow",
          ResolveFlow(EFlow::RightToLeft, EFlowPreference::Inherit, EFlow::LeftToRight) == EFlow::RightToLeft);
    Check("Culture restarts from the culture",
          ResolveFlow(EFlow::LeftToRight, EFlowPreference::Culture, EFlow::RightToLeft) == EFlow::RightToLeft);
    Check("an explicit LeftToRight wins over the culture",
          ResolveFlow(EFlow::RightToLeft, EFlowPreference::LeftToRight, EFlow::RightToLeft) == EFlow::LeftToRight);
    Check("an explicit RightToLeft wins over the culture",
          ResolveFlow(EFlow::LeftToRight, EFlowPreference::RightToLeft, EFlow::LeftToRight) == EFlow::RightToLeft);
    Check("Opposite flips both ways",
          Opposite(EFlow::LeftToRight) == EFlow::RightToLeft && Opposite(EFlow::RightToLeft) == EFlow::LeftToRight);
    Check("Opposite is an involution", Opposite(Opposite(EFlow::RightToLeft)) == EFlow::RightToLeft);

    Group("RTL: mirroring is an involution");

    // A nested widget tree mirrors at every level. A mirror that is not an involution
    // drifts by a fraction of a pixel per level, which is invisible in a screenshot and
    // then visible as a misaligned column three panels deep.
    {
        bool bAllInvolutions = true;
        const double Widths[] = { 0.0, 1.0, 7.5, 760.0, 1920.0, 1e6 };
        for (const double Parent : Widths)
        {
            for (const double Child : Widths)
            {
                for (double Left = -100.0; Left <= 900.0; Left += 37.25)
                {
                    const double Once = MirrorLeft(Left, Child, Parent);
                    const double Twice = MirrorLeft(Once, Child, Parent);
                    if (Twice != Left) { bAllInvolutions = false; }
                }
            }
        }
        Check("mirroring a left edge twice returns the original exactly", bAllInvolutions);
    }
    CheckEqual("a child fills the parent: mirrored left is zero", MirrorLeft(0.0, 760.0, 760.0), 0.0, 0.0);
    CheckEqual("a child at the left edge lands at the right edge",
               MirrorLeft(0.0, 100.0, 760.0), 660.0, 0.0);
    CheckEqual("a centred child stays centred", MirrorLeft(330.0, 100.0, 760.0), 330.0, 0.0);

    {
        bool bAllInvolutions = true;
        for (double Alignment = -0.5; Alignment <= 1.5; Alignment += 0.125)
        {
            if (MirrorAlignment(MirrorAlignment(Alignment)) != Alignment) { bAllInvolutions = false; }
        }
        Check("mirroring an alignment twice returns the original", bAllInvolutions);
    }
    CheckEqual("leading alignment becomes trailing", MirrorAlignment(0.0), 1.0, 0.0);
    CheckEqual("centre alignment is unchanged", MirrorAlignment(0.5), 0.5, 0.0);

    {
        FMargin Authored;
        Authored.Left = 24.0;
        Authored.Top = 8.0;
        Authored.Right = 4.0;
        Authored.Bottom = 12.0;
        const FMargin Once = MirrorMargin(Authored);
        Check("mirroring a margin swaps left and right", Once.Left == 4.0 && Once.Right == 24.0);
        Check("mirroring a margin leaves top and bottom alone", Once.Top == 8.0 && Once.Bottom == 12.0);
        Check("mirroring a margin twice returns the original", MirrorMargin(Once) == Authored);
    }

    Check("mirroring justification twice returns the original",
          MirrorJustify(MirrorJustify(EJustify::Left)) == EJustify::Left
          && MirrorJustify(MirrorJustify(EJustify::Right)) == EJustify::Right
          && MirrorJustify(MirrorJustify(EJustify::Center)) == EJustify::Center);
    Check("left justification mirrors to right", MirrorJustify(EJustify::Left) == EJustify::Right);
    Check("centre justification does not mirror", MirrorJustify(EJustify::Center) == EJustify::Center);
    Check("natural justification is left in LTR", NaturalJustify(EFlow::LeftToRight) == EJustify::Left);
    Check("natural justification is right in RTL", NaturalJustify(EFlow::RightToLeft) == EJustify::Right);

    {
        bool bAllInvolutions = true;
        for (int32_t Count = 1; Count <= 12; ++Count)
        {
            for (int32_t Index = 0; Index < Count; ++Index)
            {
                if (MirrorChildIndex(MirrorChildIndex(Index, Count), Count) != Index) { bAllInvolutions = false; }
            }
        }
        Check("mirroring a child index twice returns the original", bAllInvolutions);
    }
    CheckEqualInt("the first child of five becomes the last", MirrorChildIndex(0, 5), 4);
    CheckEqualInt("the middle child of five stays put", MirrorChildIndex(2, 5), 2);
    CheckEqualInt("an index past the end is clamped", MirrorChildIndex(99, 5), 4);
    CheckEqualInt("a negative index is clamped", MirrorChildIndex(-3, 5), 0);
    CheckEqualInt("an empty row gives index zero", MirrorChildIndex(0, 0), 0);

    Group("RTL: bars, sliders and scrolling");

    // A bar that fills from the wrong end still looks like a bar, so it is exactly the
    // kind of mistake that reaches a build. The width is direction-independent; only the
    // offset changes.
    {
        const double Track = 400.0;
        bool bWidthsMatch = true;
        bool bOffsetsMirror = true;
        for (double Fraction = 0.0; Fraction <= 1.0; Fraction += 0.05)
        {
            const FFillSpan Ltr = ProgressFill(Fraction, Track, EFlow::LeftToRight);
            const FFillSpan Rtl = ProgressFill(Fraction, Track, EFlow::RightToLeft);
            if (Ltr.Width != Rtl.Width) { bWidthsMatch = false; }
            if (Ltr.Offset != 0.0) { bOffsetsMirror = false; }
            if (std::fabs(Rtl.Offset - (Track - Rtl.Width)) > 1.0e-9) { bOffsetsMirror = false; }
        }
        Check("a bar's filled width does not depend on direction", bWidthsMatch);
        Check("a bar fills from the left in LTR and the right in RTL", bOffsetsMirror);
    }
    {
        const FFillSpan Empty = ProgressFill(0.0, 400.0, EFlow::RightToLeft);
        CheckEqual("an empty RTL bar sits at the right-hand end", Empty.Offset, 400.0, 0.0);
        CheckEqual("an empty bar has no width", Empty.Width, 0.0, 0.0);
        const FFillSpan Full = ProgressFill(1.0, 400.0, EFlow::RightToLeft);
        CheckEqual("a full RTL bar starts at zero", Full.Offset, 0.0, 0.0);
        CheckEqual("a full bar is the whole track", Full.Width, 400.0, 0.0);
        const FFillSpan Over = ProgressFill(4.0, 400.0, EFlow::LeftToRight);
        CheckEqual("a fraction above one is clamped", Over.Width, 400.0, 0.0);
        const FFillSpan Under = ProgressFill(-4.0, 400.0, EFlow::LeftToRight);
        CheckEqual("a fraction below zero is clamped", Under.Width, 0.0, 0.0);
        const FFillSpan NotANumber = ProgressFill(std::nan(""), 400.0, EFlow::LeftToRight);
        CheckEqual("a NaN fraction becomes empty rather than a NaN width", NotANumber.Width, 0.0, 0.0);
    }

    {
        const double Track = 300.0;
        const double Handle = 20.0;
        CheckEqual("an LTR handle at zero sits half a handle in from the left",
                   SliderHandleCentre(0.0, Track, Handle, EFlow::LeftToRight), 10.0, 1.0e-9);
        CheckEqual("an RTL handle at zero sits half a handle in from the right",
                   SliderHandleCentre(0.0, Track, Handle, EFlow::RightToLeft), 290.0, 1.0e-9);
        CheckEqual("an LTR handle at one sits half a handle in from the right",
                   SliderHandleCentre(1.0, Track, Handle, EFlow::LeftToRight), 290.0, 1.0e-9);
        CheckEqual("an RTL handle at one sits half a handle in from the left",
                   SliderHandleCentre(1.0, Track, Handle, EFlow::RightToLeft), 10.0, 1.0e-9);

        bool bMirrorsAboutTheCentre = true;
        for (double Fraction = 0.0; Fraction <= 1.0; Fraction += 0.05)
        {
            const double Ltr = SliderHandleCentre(Fraction, Track, Handle, EFlow::LeftToRight);
            const double Rtl = SliderHandleCentre(Fraction, Track, Handle, EFlow::RightToLeft);
            if (std::fabs((Ltr + Rtl) - Track) > 1.0e-9) { bMirrorsAboutTheCentre = false; }
        }
        Check("an RTL handle is the exact reflection of the LTR one", bMirrorsAboutTheCentre);
        CheckEqual("a handle at 30% is where the arithmetic says",
                   SliderHandleCentre(0.3, Track, Handle, EFlow::LeftToRight), 10.0 + 280.0 * 0.3, 1.0e-9);
    }

    {
        CheckEqual("an LTR scroll offset passes through",
                   ScrollOffsetToLeft(120.0, 1000.0, 400.0, EFlow::LeftToRight), 120.0, 1.0e-9);
        CheckEqual("an RTL scroll offset is measured from the other end",
                   ScrollOffsetToLeft(120.0, 1000.0, 400.0, EFlow::RightToLeft), 480.0, 1.0e-9);
        CheckEqual("scrolling past the end is clamped",
                   ScrollOffsetToLeft(9999.0, 1000.0, 400.0, EFlow::LeftToRight), 600.0, 1.0e-9);
        CheckEqual("a negative scroll offset is clamped",
                   ScrollOffsetToLeft(-50.0, 1000.0, 400.0, EFlow::LeftToRight), 0.0, 1.0e-9);
        CheckEqual("content that fits does not scroll in LTR",
                   ScrollOffsetToLeft(50.0, 200.0, 400.0, EFlow::LeftToRight), 0.0, 1.0e-9);
        CheckEqual("content that fits does not scroll in RTL",
                   ScrollOffsetToLeft(50.0, 200.0, 400.0, EFlow::RightToLeft), -200.0, 1.0e-9);
    }

    Group("RTL: direction cues");

    Check("directional icons flip in RTL", ShouldMirrorDirectionalIcon(EFlow::RightToLeft));
    Check("directional icons do not flip in LTR", !ShouldMirrorDirectionalIcon(EFlow::LeftToRight));
    CheckEqual("the directional sign is +1 in LTR", DirectionalSign(EFlow::LeftToRight), 1.0, 0.0);
    CheckEqual("the directional sign is -1 in RTL", DirectionalSign(EFlow::RightToLeft), -1.0, 0.0);
    Check("IsRightToLeft agrees with the enum",
          IsRightToLeft(EFlow::RightToLeft) && !IsRightToLeft(EFlow::LeftToRight));

    Group("RTL: a whole panel mirrors and mirrors back");

    // The end-to-end property: take a panel with children, padding, a bar and a slider,
    // mirror every part of it, mirror again, and get the original back bit for bit. This
    // is what makes it safe for every screen to call the mirror helpers unconditionally.
    {
        struct FChild
        {
            double Left;
            double Width;
            FMargin Padding;
            double Alignment;
        };
        const double ParentWidth = 760.0;
        FChild Children[4] = {
            { 0.0,   200.0, { 12.0, 4.0, 0.0, 4.0 },  0.0 },
            { 210.0, 120.0, { 8.0, 0.0, 8.0, 0.0 },   0.5 },
            { 340.0, 300.0, { 0.0, 2.0, 24.0, 2.0 },  1.0 },
            { 650.0, 110.0, { 6.0, 6.0, 6.0, 6.0 },   0.25 },
        };

        bool bRoundTrips = true;
        for (const FChild& Child : Children)
        {
            const double MirroredLeft = MirrorLeft(Child.Left, Child.Width, ParentWidth);
            const FMargin MirroredPadding = MirrorMargin(Child.Padding);
            const double MirroredAlignment = MirrorAlignment(Child.Alignment);

            if (MirrorLeft(MirroredLeft, Child.Width, ParentWidth) != Child.Left) { bRoundTrips = false; }
            if (!(MirrorMargin(MirroredPadding) == Child.Padding)) { bRoundTrips = false; }
            if (MirrorAlignment(MirroredAlignment) != Child.Alignment) { bRoundTrips = false; }

            // A mirrored child must still be inside the parent whenever the original was.
            const bool bWasInside = Child.Left >= 0.0 && Child.Left + Child.Width <= ParentWidth;
            const bool bIsInside = MirroredLeft >= 0.0 && MirroredLeft + Child.Width <= ParentWidth;
            if (bWasInside != bIsInside) { bRoundTrips = false; }
        }
        Check("a whole panel mirrors and mirrors back exactly", bRoundTrips);

        // Children must not overlap after mirroring if they did not overlap before. This
        // catches an off-by-one in the reflection that leaves two buttons on top of
        // each other only in the Hebrew build.
        bool bNoOverlap = true;
        for (int A = 0; A < 4; ++A)
        {
            for (int B = A + 1; B < 4; ++B)
            {
                const double LeftA = MirrorLeft(Children[A].Left, Children[A].Width, ParentWidth);
                const double LeftB = MirrorLeft(Children[B].Left, Children[B].Width, ParentWidth);
                const bool bOverlapBefore =
                    Children[A].Left < Children[B].Left + Children[B].Width &&
                    Children[B].Left < Children[A].Left + Children[A].Width;
                const bool bOverlapAfter =
                    LeftA < LeftB + Children[B].Width && LeftB < LeftA + Children[A].Width;
                if (bOverlapBefore != bOverlapAfter) { bNoOverlap = false; }
            }
        }
        Check("mirroring preserves which children overlap", bNoOverlap);

        // And the visual order must reverse: the child authored first is furthest right.
        bool bOrderReverses = true;
        for (int Index = 0; Index + 1 < 4; ++Index)
        {
            const double LeftEarlier = MirrorLeft(Children[Index].Left, Children[Index].Width, ParentWidth);
            const double LeftLater = MirrorLeft(Children[Index + 1].Left, Children[Index + 1].Width, ParentWidth);
            if (!(LeftEarlier > LeftLater)) { bOrderReverses = false; }
        }
        Check("the first authored child ends up furthest right", bOrderReverses);
    }
}

// ---------------------------------------------------------------------------
// receipt
// ---------------------------------------------------------------------------

std::string Escape(const std::string& In)
{
    std::string Out;
    Out.reserve(In.size() + 8);
    for (const char Character : In)
    {
        switch (Character)
        {
        case '"':  Out += "\\\""; break;
        case '\\': Out += "\\\\"; break;
        case '\n': Out += "\\n"; break;
        case '\r': Out += "\\r"; break;
        case '\t': Out += "\\t"; break;
        default:
            if (static_cast<unsigned char>(Character) < 0x20)
            {
                char Buffer[8];
                std::snprintf(Buffer, sizeof(Buffer), "\\u%04X", static_cast<unsigned char>(Character));
                Out += Buffer;
            }
            else
            {
                Out += Character;
            }
            break;
        }
    }
    return Out;
}

}  // namespace

int main()
{
    TestRoundTrip();
    TestV1Migration();
    TestV2AndV3Migration();
    TestRejection();
    TestNumericHelpers();
    TestRtl();

    const int Total = static_cast<int>(Cases.size());
    int Passed = 0;
    for (const FCase& Case : Cases)
    {
        if (Case.bPassed) { ++Passed; }
    }
    const bool bAllPassed = Passed == Total;

    std::printf("{\n");
    std::printf("  \"test\": \"SaveMigrationMathTest\",\n");
    std::printf("  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/SaveMigrationMath.h\",\n");
    std::printf("  \"status\": \"%s\",\n", bAllPassed ? "passed" : "cases_did_not_pass");
    std::printf("  \"recordVersion\": %d,\n", CurrentRecordVersion);
    std::printf("  \"oldestSupportedVersion\": %d,\n", OldestSupportedVersion);
    std::printf("  \"total\": %d,\n", Total);
    std::printf("  \"passed\": %d,\n", Passed);
    std::printf("  \"limitations\": [\n");
    std::printf("    \"Pure numeric and byte-level check of the save container, its migrations and the RTL layout arithmetic. It establishes nothing about the engine classes, the platform save system, the widgets, the font on screen, or the Hebrew wording.\",\n");
    std::printf("    \"The corruption sweep covers every single-bit flip and every truncation of one representative save. Multi-bit corruption is covered only in so far as CRC-32 and the header checks cover it.\"\n");
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

    std::fprintf(stderr, "SaveMigrationMathTest: %d/%d passed (%s)\n", Passed, Total, bAllPassed ? "PASS" : "FAIL");
    for (const FCase& Case : Cases)
    {
        if (!Case.bPassed)
        {
            std::fprintf(stderr, "  FAIL [%s] %s -- %s\n", Case.Group.c_str(), Case.Name.c_str(), Case.Detail.c_str());
        }
    }
    return bAllPassed ? 0 : 1;
}
