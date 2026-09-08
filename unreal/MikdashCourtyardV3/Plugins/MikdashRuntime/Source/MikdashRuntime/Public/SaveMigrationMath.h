// SaveMigrationMath.h -- engine-independent save container, migration and RTL layout maths.
//
// This header deliberately includes NOTHING from Unreal. It is compiled both by the
// MikdashRuntime module (through MikdashSaveGame.cpp and MikdashLocalization.cpp) and by
// Tests/SaveMigrationMathTest.cpp, which is built with cl.exe alone. Keeping the byte
// format, the version migrations and the mirroring arithmetic here means the worst bug
// class in this feature -- a save file that corrupts or crashes on load -- can be tested
// exhaustively without an editor.
//
// Two things live here that a reader might not expect:
//
//   1. The RTL layout arithmetic (namespace MikdashRtl). It is here rather than in
//      MikdashLocalization.h because the standalone test compiles exactly one header and
//      MikdashLocalization.h is a UCLASS header that cannot be compiled without Unreal.
//      MikdashLocalization.h includes this file and calls into it; nothing is duplicated.
//
//   2. std::string / std::vector. SettingsMath.h next door is allocation-free, but a save
//      record genuinely holds variable-length lists of tour-stop and codex identifiers.
//      They are confined to this header and to the save path; no other Mikdash header
//      grows a standard-library dependency because of this one.
//
// ---------------------------------------------------------------------------------------
// CONTAINER FORMAT (little-endian throughout, so a save is portable between platforms)
//
//   offset  size  field
//        0     4  magic            'M' 'K' 'D' 'S'
//        4     4  formatVersion    container layout; 1 today
//        8     4  recordVersion    payload schema; see the version history below
//       12     4  payloadBytes     length of the payload that follows the header
//       16     4  payloadCrc32     CRC-32 (IEEE, reflected, poly 0xEDB88320) of the payload
//       20     N  payload
//
// A file is accepted only if every one of these holds: at least 20 bytes present; magic
// matches; formatVersion is known; recordVersion is inside [OldestSupportedVersion,
// CurrentRecordVersion]; payloadBytes is inside [0, MaxPayloadBytes]; the buffer is
// exactly 20 + payloadBytes long; the CRC of those bytes matches; and the payload reader
// consumes the payload exactly, with every length and count inside its declared bound.
// Anything else returns an ESaveDecodeError and leaves the caller's record untouched. The
// reader never allocates on an unvalidated length, never reads past the buffer, and never
// throws, so a hostile or truncated file costs a rejected load and nothing more.
// ---------------------------------------------------------------------------------------

#pragma once

#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace MikdashSave
{

// ---------------------------------------------------------------------------
// Version history of the saved record payload.
//
//   1  the first walkthrough build. Player position was stored in AMOS in the
//      source coordinate convention of the measured architecture (X east, Y up,
//      Z south) and only a yaw was kept. Time of day was an index into a table of
//      six named presets. Tour stops were indices into the eight-stop route that
//      build shipped with. There was no play-time counter, no codex, no photo
//      mode and no options block.
//   2  position became centimetres in Unreal axes and gained pitch and roll; time
//      of day became a float in hours; a 32-bit play-time counter and the codex
//      list were added.
//   3  tour stops became string identifiers instead of indices, a current-stop
//      identifier was added, and the photo-mode block was added.
//   4  the current format: slot label, absolute save time, build number, a paused
//      flag for the time of day, the opaque options block, and the play-time
//      counter widened to 64 bits.
// ---------------------------------------------------------------------------
inline constexpr int32_t CurrentRecordVersion = 4;
inline constexpr int32_t OldestSupportedVersion = 1;
inline constexpr int32_t CurrentFormatVersion = 1;

inline constexpr int32_t HeaderBytes = 20;
inline constexpr uint8_t Magic0 = 'M';
inline constexpr uint8_t Magic1 = 'K';
inline constexpr uint8_t Magic2 = 'D';
inline constexpr uint8_t Magic3 = 'S';

// Hard ceilings. Their only job is to make a corrupt length field cheap: the reader
// refuses before it reserves anything, so a garbage count cannot turn into a huge
// allocation or a long loop.
inline constexpr uint32_t MaxPayloadBytes = 4u * 1024u * 1024u;
inline constexpr uint32_t MaxStringBytes = 4096u;
inline constexpr uint32_t MaxArrayCount = 8192u;
inline constexpr uint32_t MaxOptionCount = 512u;

// The measured architecture is authored in amos and imported at 0.5 m per amah; the
// manifest's expectedSourceToUnrealCm is [x*50, z*50, y*50]. A v1 save therefore has to
// be multiplied by 50 and have its axes swapped to reach Unreal centimetres.
inline constexpr double MetresPerAmah = 0.5;
inline constexpr double CentimetresPerAmah = MetresPerAmah * 100.0;  // 50

inline constexpr int32_t LegacyTimeOfDayPresetCount = 6;
inline constexpr int32_t LegacyTourStopCount = 8;

// ---------------------------------------------------------------------------
// Errors. Ok is the only value that means the record was filled in.
// ---------------------------------------------------------------------------
enum class ESaveDecodeError : int
{
    Ok = 0,
    BufferTooSmall,      // fewer than HeaderBytes bytes
    BadMagic,            // not a Mikdash save at all
    UnsupportedFormat,   // container layout this build does not know
    VersionTooOld,       // below OldestSupportedVersion; no migration path exists
    VersionTooNew,       // written by a later build; refused rather than guessed at
    PayloadTooLarge,     // declared payload above MaxPayloadBytes
    LengthMismatch,      // buffer is not exactly HeaderBytes + payloadBytes (truncated or padded)
    ChecksumMismatch,    // the payload bytes are not the bytes that were written
    PayloadUnderrun,     // a field ran off the end of the payload
    PayloadTrailingBytes,// the payload was longer than the schema for its version
    FieldOutOfRange      // a count or length exceeded its declared ceiling
};

inline const char* DescribeError(ESaveDecodeError Error)
{
    switch (Error)
    {
    case ESaveDecodeError::Ok:                   return "ok";
    case ESaveDecodeError::BufferTooSmall:       return "file is shorter than a save header";
    case ESaveDecodeError::BadMagic:             return "not a Mikdash save file";
    case ESaveDecodeError::UnsupportedFormat:    return "unsupported save container version";
    case ESaveDecodeError::VersionTooOld:        return "save is older than this build can migrate";
    case ESaveDecodeError::VersionTooNew:        return "save was written by a newer build";
    case ESaveDecodeError::PayloadTooLarge:      return "declared payload is implausibly large";
    case ESaveDecodeError::LengthMismatch:       return "file is truncated or has extra bytes";
    case ESaveDecodeError::ChecksumMismatch:     return "save payload failed its checksum";
    case ESaveDecodeError::PayloadUnderrun:      return "save payload ended early";
    case ESaveDecodeError::PayloadTrailingBytes: return "save payload has unread trailing bytes";
    case ESaveDecodeError::FieldOutOfRange:      return "save contains an out-of-range length";
    }
    return "unknown save error";
}

// ---------------------------------------------------------------------------
// Record
// ---------------------------------------------------------------------------
struct FTransformRecord
{
    double X = 0.0;
    double Y = 0.0;
    double Z = 0.0;
    double Pitch = 0.0;
    double Yaw = 0.0;
    double Roll = 0.0;
};

struct FPhotoRecord
{
    float FieldOfViewDegrees = 90.0f;
    float ExposureCompensation = 0.0f;
    float FocusDistanceCm = 1000.0f;
    float Aperture = 4.0f;
    float RollDegrees = 0.0f;
    uint32_t ResolutionMultiplier = 1;
    bool bHideInterface = true;
    std::string LookId;
};

enum class EOptionType : int { Bool = 0, Int = 1, Float = 2, String = 3 };

// The settings screen belongs to another agent. Rather than copy their struct into the
// save format -- which would break every time they add a slider -- the save carries an
// opaque typed key/value list. They write whatever keys they like; this code stores and
// returns them without interpreting a single one.
struct FOptionValue
{
    std::string Key;
    EOptionType Type = EOptionType::Bool;
    bool BoolValue = false;
    int32_t IntValue = 0;
    float FloatValue = 0.0f;
    std::string StringValue;
};

struct FSaveRecord
{
    int32_t RecordVersion = CurrentRecordVersion;

    std::string SlotLabel;
    std::string MapName;
    uint64_t SaveTimeUnixSeconds = 0;
    uint64_t PlayTimeSeconds = 0;
    uint32_t BuildNumber = 0;

    FTransformRecord PlayerTransform;

    float TimeOfDayHours = 12.0f;
    bool bTimeOfDayPaused = false;

    std::vector<std::string> CompletedTourStops;
    std::string CurrentTourStop;
    bool bTourActive = false;

    std::vector<std::string> UnlockedCodexEntries;

    FPhotoRecord Photo;
    std::vector<FOptionValue> Options;
};

// What a migration had to invent or throw away. The front end shows nothing from this;
// it exists so a failed migration is visible in a log and in the tests instead of being
// silently absorbed.
struct FMigrationReport
{
    int32_t FromVersion = CurrentRecordVersion;
    int32_t ToVersion = CurrentRecordVersion;
    int32_t StepsApplied = 0;
    int32_t TourStopsDropped = 0;      // legacy indices with no identifier in the table
    int32_t FieldsDefaulted = 0;       // fields the old format simply did not have
    bool bTimeOfDayPresetOutOfRange = false;
    bool bCoordinatesConverted = false;
};

// ---------------------------------------------------------------------------
// CRC-32, IEEE reflected. Written as a bit loop so there is no table to get wrong and
// no static initialisation order to worry about.
// ---------------------------------------------------------------------------
inline uint32_t Crc32(const uint8_t* Data, size_t Length)
{
    uint32_t Crc = 0xFFFFFFFFu;
    for (size_t Index = 0; Index < Length; ++Index)
    {
        Crc ^= static_cast<uint32_t>(Data[Index]);
        for (int Bit = 0; Bit < 8; ++Bit)
        {
            const uint32_t Mask = static_cast<uint32_t>(-static_cast<int32_t>(Crc & 1u));
            Crc = (Crc >> 1) ^ (0xEDB88320u & Mask);
        }
    }
    return ~Crc;
}

inline uint32_t Crc32(const std::vector<uint8_t>& Bytes)
{
    return Crc32(Bytes.empty() ? nullptr : Bytes.data(), Bytes.size());
}

// ---------------------------------------------------------------------------
// Little-endian writer. Grows a byte vector; cannot fail.
// ---------------------------------------------------------------------------
class FByteWriter
{
public:
    explicit FByteWriter(std::vector<uint8_t>& InOut) : Out(InOut) {}

    void U8(uint8_t Value) { Out.push_back(Value); }
    void Bool(bool Value) { Out.push_back(Value ? uint8_t(1) : uint8_t(0)); }

    void U32(uint32_t Value)
    {
        Out.push_back(static_cast<uint8_t>(Value & 0xFFu));
        Out.push_back(static_cast<uint8_t>((Value >> 8) & 0xFFu));
        Out.push_back(static_cast<uint8_t>((Value >> 16) & 0xFFu));
        Out.push_back(static_cast<uint8_t>((Value >> 24) & 0xFFu));
    }

    void I32(int32_t Value)
    {
        uint32_t Bits;
        std::memcpy(&Bits, &Value, 4);
        U32(Bits);
    }

    void U64(uint64_t Value)
    {
        U32(static_cast<uint32_t>(Value & 0xFFFFFFFFu));
        U32(static_cast<uint32_t>((Value >> 32) & 0xFFFFFFFFu));
    }

    void F32(float Value)
    {
        uint32_t Bits;
        std::memcpy(&Bits, &Value, 4);
        U32(Bits);
    }

    void F64(double Value)
    {
        uint64_t Bits;
        std::memcpy(&Bits, &Value, 8);
        U64(Bits);
    }

    void Str(const std::string& Value)
    {
        const uint32_t Length = static_cast<uint32_t>(Value.size() > MaxStringBytes ? MaxStringBytes : Value.size());
        U32(Length);
        Out.insert(Out.end(), Value.begin(), Value.begin() + static_cast<std::ptrdiff_t>(Length));
    }

private:
    std::vector<uint8_t>& Out;
};

// ---------------------------------------------------------------------------
// Little-endian reader. Every read is bounds-checked. Once the error latch is set the
// reader keeps returning zeros, so a caller that forgets to check between fields still
// cannot be steered off the end of the buffer.
// ---------------------------------------------------------------------------
class FByteReader
{
public:
    FByteReader(const uint8_t* InData, size_t InLength) : Data(InData), Length(InLength) {}

    bool IsOk() const { return Error == ESaveDecodeError::Ok; }
    ESaveDecodeError GetError() const { return Error; }
    size_t Remaining() const { return Cursor <= Length ? Length - Cursor : 0; }
    bool AtEnd() const { return Cursor == Length; }

    void Fail(ESaveDecodeError InError)
    {
        if (Error == ESaveDecodeError::Ok) { Error = InError; }
    }

    uint8_t U8()
    {
        if (!Require(1)) { return 0; }
        return Data[Cursor++];
    }

    bool Bool()
    {
        // Anything non-zero reads as true; a byte of 0x7F in a damaged file is a true,
        // not a rejection. Booleans are the one field where a wrong value is harmless.
        return U8() != 0;
    }

    uint32_t U32()
    {
        if (!Require(4)) { return 0; }
        const uint32_t Value =
            static_cast<uint32_t>(Data[Cursor]) |
            (static_cast<uint32_t>(Data[Cursor + 1]) << 8) |
            (static_cast<uint32_t>(Data[Cursor + 2]) << 16) |
            (static_cast<uint32_t>(Data[Cursor + 3]) << 24);
        Cursor += 4;
        return Value;
    }

    int32_t I32()
    {
        const uint32_t Bits = U32();
        int32_t Value;
        std::memcpy(&Value, &Bits, 4);
        return Value;
    }

    uint64_t U64()
    {
        const uint64_t Low = U32();
        const uint64_t High = U32();
        return Low | (High << 32);
    }

    float F32()
    {
        const uint32_t Bits = U32();
        float Value;
        std::memcpy(&Value, &Bits, 4);
        return Value;
    }

    double F64()
    {
        const uint64_t Bits = U64();
        double Value;
        std::memcpy(&Value, &Bits, 8);
        return Value;
    }

    std::string Str()
    {
        const uint32_t StringLength = U32();
        if (!IsOk()) { return std::string(); }
        if (StringLength > MaxStringBytes)
        {
            Fail(ESaveDecodeError::FieldOutOfRange);
            return std::string();
        }
        if (!Require(StringLength)) { return std::string(); }
        std::string Value(reinterpret_cast<const char*>(Data + Cursor), StringLength);
        Cursor += StringLength;
        return Value;
    }

    // Reads a count and refuses it before the caller reserves anything for it. The second
    // bound is the real protection: a count can never exceed the bytes left, because even
    // the smallest element costs four bytes.
    uint32_t Count(uint32_t Ceiling)
    {
        const uint32_t Value = U32();
        if (!IsOk()) { return 0; }
        if (Value > Ceiling || static_cast<uint64_t>(Value) * 4ull > static_cast<uint64_t>(Remaining()))
        {
            Fail(ESaveDecodeError::FieldOutOfRange);
            return 0;
        }
        return Value;
    }

private:
    bool Require(size_t Bytes)
    {
        if (!IsOk()) { return false; }
        if (Cursor + Bytes > Length || Cursor + Bytes < Cursor)
        {
            Fail(ESaveDecodeError::PayloadUnderrun);
            return false;
        }
        return true;
    }

    const uint8_t* Data = nullptr;
    size_t Length = 0;
    size_t Cursor = 0;
    ESaveDecodeError Error = ESaveDecodeError::Ok;
};

// ---------------------------------------------------------------------------
// Migration arithmetic. Each piece is a pure function so it can be checked on its own.
// ---------------------------------------------------------------------------

// Degrees onto (-180, 180]. NaN becomes 0 rather than propagating into a transform.
inline double NormalizeDegrees(double Degrees)
{
    if (!(Degrees == Degrees)) { return 0.0; }
    if (Degrees > 1.0e9 || Degrees < -1.0e9) { return 0.0; }
    double Value = std::fmod(Degrees, 360.0);
    if (Value <= -180.0) { Value += 360.0; }
    else if (Value > 180.0) { Value -= 360.0; }
    // fmod of exactly -180 lands on -180; fold it to +180 so the range is half-open one way.
    if (Value == -180.0) { Value = 180.0; }
    return Value;
}

// v1 stored the position in amos in the source convention: X east, Y up, Z south. The
// import matrix used by every asset in the project is [x*50, z*50, y*50], so Unreal X is
// the source X, Unreal Y is the source Z and Unreal Z is the source Y (the up axis).
inline FTransformRecord SourceAmosToUnrealCm(double SourceX, double SourceY, double SourceZ)
{
    FTransformRecord Result;
    Result.X = SourceX * CentimetresPerAmah;
    Result.Y = SourceZ * CentimetresPerAmah;
    Result.Z = SourceY * CentimetresPerAmah;
    return Result;
}

// The source yaw is measured about the source up axis (Y) from +X towards -Z. Unreal
// measures yaw from +X towards +Y, and Unreal +Y is source +Z, so the sense reverses.
inline double SourceYawToUnrealYaw(double SourceYawDegrees)
{
    return NormalizeDegrees(-SourceYawDegrees);
}

// The six presets v1 shipped with, in the order they appeared in that build's enum.
inline float LegacyTimeOfDayPresetToHours(int32_t PresetIndex, bool& bOutOfRange)
{
    static const float Hours[LegacyTimeOfDayPresetCount] = {
        5.0f,   // Dawn      -- alos hashachar
        8.0f,   // Morning
        12.0f,  // Midday
        15.0f,  // Afternoon
        18.0f,  // Dusk      -- bein ha'arbayim
        22.0f   // Night
    };
    if (PresetIndex < 0 || PresetIndex >= LegacyTimeOfDayPresetCount)
    {
        bOutOfRange = true;
        return 12.0f;
    }
    bOutOfRange = false;
    return Hours[PresetIndex];
}

// The eight-stop route v1 and v2 shipped with, in save order. A v1 save holds indices
// into this table; anything outside it is a stop that build never had and is dropped.
inline const char* LegacyTourStopId(int32_t StopIndex)
{
    static const char* Ids[LegacyTourStopCount] = {
        "stop.approach",
        "stop.har",
        "stop.ezras_nashim",
        "stop.azarah",
        "stop.mizbeach",
        "stop.ulam",
        "stop.heikhal",
        "stop.kodesh_hakodashim"
    };
    if (StopIndex < 0 || StopIndex >= LegacyTourStopCount) { return nullptr; }
    return Ids[StopIndex];
}

inline float ClampTimeOfDayHours(float Hours)
{
    if (!(Hours == Hours)) { return 12.0f; }
    if (Hours < 0.0f) { return 0.0f; }
    if (Hours >= 24.0f) { return std::fmod(Hours, 24.0f); }
    return Hours;
}

// ---------------------------------------------------------------------------
// Payload readers, one per version. Each fills the record in that version's own terms;
// MigrateToCurrent then brings the record forward.
// ---------------------------------------------------------------------------
namespace Detail
{

inline void ReadPhotoBlock(FByteReader& Reader, FPhotoRecord& Photo)
{
    Photo.FieldOfViewDegrees = Reader.F32();
    Photo.ExposureCompensation = Reader.F32();
    Photo.FocusDistanceCm = Reader.F32();
    Photo.Aperture = Reader.F32();
    Photo.RollDegrees = Reader.F32();
    Photo.ResolutionMultiplier = Reader.U32();
    Photo.bHideInterface = Reader.Bool();
    Photo.LookId = Reader.Str();
}

inline void WritePhotoBlock(FByteWriter& Writer, const FPhotoRecord& Photo)
{
    Writer.F32(Photo.FieldOfViewDegrees);
    Writer.F32(Photo.ExposureCompensation);
    Writer.F32(Photo.FocusDistanceCm);
    Writer.F32(Photo.Aperture);
    Writer.F32(Photo.RollDegrees);
    Writer.U32(Photo.ResolutionMultiplier);
    Writer.Bool(Photo.bHideInterface);
    Writer.Str(Photo.LookId);
}

inline void ReadStringList(FByteReader& Reader, std::vector<std::string>& Out)
{
    const uint32_t Number = Reader.Count(MaxArrayCount);
    if (!Reader.IsOk()) { return; }
    Out.clear();
    Out.reserve(Number);
    for (uint32_t Index = 0; Index < Number && Reader.IsOk(); ++Index)
    {
        Out.push_back(Reader.Str());
    }
}

inline void WriteStringList(FByteWriter& Writer, const std::vector<std::string>& In)
{
    const uint32_t Number = static_cast<uint32_t>(In.size() > MaxArrayCount ? MaxArrayCount : In.size());
    Writer.U32(Number);
    for (uint32_t Index = 0; Index < Number; ++Index) { Writer.Str(In[Index]); }
}

// v1: amos, source axes, yaw only, preset time of day, integer stop indices.
inline void ReadV1(FByteReader& Reader, FSaveRecord& Record, std::vector<int32_t>& OutLegacyStops, int32_t& OutTimeOfDayPreset)
{
    Record.MapName = Reader.Str();
    const double SourceX = static_cast<double>(Reader.F32());
    const double SourceY = static_cast<double>(Reader.F32());
    const double SourceZ = static_cast<double>(Reader.F32());
    const double SourceYaw = static_cast<double>(Reader.F32());
    // Kept raw; MigrateToCurrent does the conversion so the conversion itself is testable.
    Record.PlayerTransform.X = SourceX;
    Record.PlayerTransform.Y = SourceY;
    Record.PlayerTransform.Z = SourceZ;
    Record.PlayerTransform.Yaw = SourceYaw;
    OutTimeOfDayPreset = static_cast<int32_t>(Reader.U8());
    const uint32_t Number = Reader.Count(MaxArrayCount);
    OutLegacyStops.clear();
    if (Reader.IsOk())
    {
        OutLegacyStops.reserve(Number);
        for (uint32_t Index = 0; Index < Number && Reader.IsOk(); ++Index)
        {
            OutLegacyStops.push_back(Reader.I32());
        }
    }
    Record.bTourActive = Reader.Bool();
}

// v2: Unreal centimetres, full rotator, float hours, 32-bit play time, codex, still
// integer stop indices.
inline void ReadV2(FByteReader& Reader, FSaveRecord& Record, std::vector<int32_t>& OutLegacyStops)
{
    Record.MapName = Reader.Str();
    Record.PlayerTransform.X = Reader.F64();
    Record.PlayerTransform.Y = Reader.F64();
    Record.PlayerTransform.Z = Reader.F64();
    Record.PlayerTransform.Pitch = Reader.F64();
    Record.PlayerTransform.Yaw = Reader.F64();
    Record.PlayerTransform.Roll = Reader.F64();
    Record.TimeOfDayHours = Reader.F32();
    Record.PlayTimeSeconds = static_cast<uint64_t>(Reader.U32());
    const uint32_t Number = Reader.Count(MaxArrayCount);
    OutLegacyStops.clear();
    if (Reader.IsOk())
    {
        OutLegacyStops.reserve(Number);
        for (uint32_t Index = 0; Index < Number && Reader.IsOk(); ++Index)
        {
            OutLegacyStops.push_back(Reader.I32());
        }
    }
    Record.bTourActive = Reader.Bool();
    ReadStringList(Reader, Record.UnlockedCodexEntries);
}

// v3: stop identifiers become strings, a current stop appears, photo mode appears.
inline void ReadV3(FByteReader& Reader, FSaveRecord& Record)
{
    Record.MapName = Reader.Str();
    Record.PlayerTransform.X = Reader.F64();
    Record.PlayerTransform.Y = Reader.F64();
    Record.PlayerTransform.Z = Reader.F64();
    Record.PlayerTransform.Pitch = Reader.F64();
    Record.PlayerTransform.Yaw = Reader.F64();
    Record.PlayerTransform.Roll = Reader.F64();
    Record.TimeOfDayHours = Reader.F32();
    Record.PlayTimeSeconds = static_cast<uint64_t>(Reader.U32());
    ReadStringList(Reader, Record.CompletedTourStops);
    Record.CurrentTourStop = Reader.Str();
    Record.bTourActive = Reader.Bool();
    ReadStringList(Reader, Record.UnlockedCodexEntries);
    ReadPhotoBlock(Reader, Record.Photo);
}

// v4: the current schema.
inline void ReadV4(FByteReader& Reader, FSaveRecord& Record)
{
    Record.SlotLabel = Reader.Str();
    Record.MapName = Reader.Str();
    Record.SaveTimeUnixSeconds = Reader.U64();
    Record.PlayTimeSeconds = Reader.U64();
    Record.BuildNumber = Reader.U32();
    Record.PlayerTransform.X = Reader.F64();
    Record.PlayerTransform.Y = Reader.F64();
    Record.PlayerTransform.Z = Reader.F64();
    Record.PlayerTransform.Pitch = Reader.F64();
    Record.PlayerTransform.Yaw = Reader.F64();
    Record.PlayerTransform.Roll = Reader.F64();
    Record.TimeOfDayHours = Reader.F32();
    Record.bTimeOfDayPaused = Reader.Bool();
    ReadStringList(Reader, Record.CompletedTourStops);
    Record.CurrentTourStop = Reader.Str();
    Record.bTourActive = Reader.Bool();
    ReadStringList(Reader, Record.UnlockedCodexEntries);
    ReadPhotoBlock(Reader, Record.Photo);

    const uint32_t OptionCount = Reader.Count(MaxOptionCount);
    if (!Reader.IsOk()) { return; }
    Record.Options.clear();
    Record.Options.reserve(OptionCount);
    for (uint32_t Index = 0; Index < OptionCount && Reader.IsOk(); ++Index)
    {
        FOptionValue Option;
        Option.Key = Reader.Str();
        const uint8_t RawType = Reader.U8();
        if (RawType > static_cast<uint8_t>(EOptionType::String))
        {
            Reader.Fail(ESaveDecodeError::FieldOutOfRange);
            return;
        }
        Option.Type = static_cast<EOptionType>(RawType);
        switch (Option.Type)
        {
        case EOptionType::Bool:   Option.BoolValue = Reader.Bool(); break;
        case EOptionType::Int:    Option.IntValue = Reader.I32(); break;
        case EOptionType::Float:  Option.FloatValue = Reader.F32(); break;
        case EOptionType::String: Option.StringValue = Reader.Str(); break;
        }
        Record.Options.push_back(std::move(Option));
    }
}

inline void WriteV4Payload(FByteWriter& Writer, const FSaveRecord& Record)
{
    Writer.Str(Record.SlotLabel);
    Writer.Str(Record.MapName);
    Writer.U64(Record.SaveTimeUnixSeconds);
    Writer.U64(Record.PlayTimeSeconds);
    Writer.U32(Record.BuildNumber);
    Writer.F64(Record.PlayerTransform.X);
    Writer.F64(Record.PlayerTransform.Y);
    Writer.F64(Record.PlayerTransform.Z);
    Writer.F64(Record.PlayerTransform.Pitch);
    Writer.F64(Record.PlayerTransform.Yaw);
    Writer.F64(Record.PlayerTransform.Roll);
    Writer.F32(Record.TimeOfDayHours);
    Writer.Bool(Record.bTimeOfDayPaused);
    WriteStringList(Writer, Record.CompletedTourStops);
    Writer.Str(Record.CurrentTourStop);
    Writer.Bool(Record.bTourActive);
    WriteStringList(Writer, Record.UnlockedCodexEntries);
    WritePhotoBlock(Writer, Record.Photo);

    const uint32_t OptionCount =
        static_cast<uint32_t>(Record.Options.size() > MaxOptionCount ? MaxOptionCount : Record.Options.size());
    Writer.U32(OptionCount);
    for (uint32_t Index = 0; Index < OptionCount; ++Index)
    {
        const FOptionValue& Option = Record.Options[Index];
        Writer.Str(Option.Key);
        Writer.U8(static_cast<uint8_t>(Option.Type));
        switch (Option.Type)
        {
        case EOptionType::Bool:   Writer.Bool(Option.BoolValue); break;
        case EOptionType::Int:    Writer.I32(Option.IntValue); break;
        case EOptionType::Float:  Writer.F32(Option.FloatValue); break;
        case EOptionType::String: Writer.Str(Option.StringValue); break;
        }
    }
}

}  // namespace Detail

// ---------------------------------------------------------------------------
// Migration. Applied step by step so each hop is exercised by every older save, and so
// adding version 5 means adding exactly one step.
// ---------------------------------------------------------------------------
inline void MigrateV1ToV2(FSaveRecord& Record, const std::vector<int32_t>& LegacyStops,
                          int32_t TimeOfDayPreset, FMigrationReport& Report)
{
    const FTransformRecord Converted =
        SourceAmosToUnrealCm(Record.PlayerTransform.X, Record.PlayerTransform.Y, Record.PlayerTransform.Z);
    const double UnrealYaw = SourceYawToUnrealYaw(Record.PlayerTransform.Yaw);
    Record.PlayerTransform.X = Converted.X;
    Record.PlayerTransform.Y = Converted.Y;
    Record.PlayerTransform.Z = Converted.Z;
    Record.PlayerTransform.Pitch = 0.0;
    Record.PlayerTransform.Yaw = UnrealYaw;
    Record.PlayerTransform.Roll = 0.0;
    Report.bCoordinatesConverted = true;

    bool bOutOfRange = false;
    Record.TimeOfDayHours = LegacyTimeOfDayPresetToHours(TimeOfDayPreset, bOutOfRange);
    Report.bTimeOfDayPresetOutOfRange = bOutOfRange;

    // v1 had no play-time counter and no codex.
    Record.PlayTimeSeconds = 0;
    Record.UnlockedCodexEntries.clear();
    Report.FieldsDefaulted += 2;

    (void)LegacyStops;  // still indices at v2; converted by the v2 -> v3 step.
    Report.StepsApplied += 1;
}

inline void MigrateV2ToV3(FSaveRecord& Record, const std::vector<int32_t>& LegacyStops, FMigrationReport& Report)
{
    Record.CompletedTourStops.clear();
    Record.CompletedTourStops.reserve(LegacyStops.size());
    for (const int32_t StopIndex : LegacyStops)
    {
        if (const char* Id = LegacyTourStopId(StopIndex))
        {
            Record.CompletedTourStops.push_back(Id);
        }
        else
        {
            Report.TourStopsDropped += 1;
        }
    }
    // The last completed stop is the best available answer for where the tour was.
    Record.CurrentTourStop = Record.CompletedTourStops.empty() ? std::string() : Record.CompletedTourStops.back();
    Record.Photo = FPhotoRecord();
    Report.FieldsDefaulted += 1;
    Report.StepsApplied += 1;
}

inline void MigrateV3ToV4(FSaveRecord& Record, FMigrationReport& Report)
{
    Record.SlotLabel.clear();          // the front end labels the slot from its index
    Record.SaveTimeUnixSeconds = 0;    // unknown; the slot card shows "unknown"
    Record.BuildNumber = 0;
    Record.bTimeOfDayPaused = false;
    Record.Options.clear();            // settings fall back to the live config on load
    Report.FieldsDefaulted += 5;
    Report.StepsApplied += 1;
}

// ---------------------------------------------------------------------------
// Decode: header validation, payload read, migration to the current version.
// The record is only written on success; on any error the caller's record is untouched.
// ---------------------------------------------------------------------------
inline ESaveDecodeError Decode(const uint8_t* Bytes, size_t Length, FSaveRecord& OutRecord, FMigrationReport& OutReport)
{
    if (Bytes == nullptr || Length < static_cast<size_t>(HeaderBytes))
    {
        return ESaveDecodeError::BufferTooSmall;
    }
    if (Bytes[0] != Magic0 || Bytes[1] != Magic1 || Bytes[2] != Magic2 || Bytes[3] != Magic3)
    {
        return ESaveDecodeError::BadMagic;
    }

    FByteReader HeaderReader(Bytes, static_cast<size_t>(HeaderBytes));
    HeaderReader.U32();  // magic, already checked
    const int32_t FormatVersion = HeaderReader.I32();
    const int32_t RecordVersion = HeaderReader.I32();
    const uint32_t PayloadBytes = HeaderReader.U32();
    const uint32_t PayloadCrc = HeaderReader.U32();
    if (!HeaderReader.IsOk()) { return HeaderReader.GetError(); }

    if (FormatVersion != CurrentFormatVersion) { return ESaveDecodeError::UnsupportedFormat; }
    if (RecordVersion < OldestSupportedVersion) { return ESaveDecodeError::VersionTooOld; }
    if (RecordVersion > CurrentRecordVersion) { return ESaveDecodeError::VersionTooNew; }
    if (PayloadBytes > MaxPayloadBytes) { return ESaveDecodeError::PayloadTooLarge; }
    if (Length != static_cast<size_t>(HeaderBytes) + static_cast<size_t>(PayloadBytes))
    {
        return ESaveDecodeError::LengthMismatch;
    }
    if (Crc32(Bytes + HeaderBytes, PayloadBytes) != PayloadCrc)
    {
        return ESaveDecodeError::ChecksumMismatch;
    }

    FSaveRecord Record;
    Record.RecordVersion = RecordVersion;
    FMigrationReport Report;
    Report.FromVersion = RecordVersion;
    Report.ToVersion = CurrentRecordVersion;

    FByteReader Reader(Bytes + HeaderBytes, PayloadBytes);
    std::vector<int32_t> LegacyStops;
    int32_t TimeOfDayPreset = 2;  // midday, if v1 and the byte is unreadable

    switch (RecordVersion)
    {
    case 1: Detail::ReadV1(Reader, Record, LegacyStops, TimeOfDayPreset); break;
    case 2: Detail::ReadV2(Reader, Record, LegacyStops); break;
    case 3: Detail::ReadV3(Reader, Record); break;
    case 4: Detail::ReadV4(Reader, Record); break;
    default: return ESaveDecodeError::UnsupportedFormat;
    }

    if (!Reader.IsOk()) { return Reader.GetError(); }
    if (!Reader.AtEnd()) { return ESaveDecodeError::PayloadTrailingBytes; }

    if (RecordVersion <= 1) { MigrateV1ToV2(Record, LegacyStops, TimeOfDayPreset, Report); }
    if (RecordVersion <= 2) { MigrateV2ToV3(Record, LegacyStops, Report); }
    if (RecordVersion <= 3) { MigrateV3ToV4(Record, Report); }

    Record.RecordVersion = CurrentRecordVersion;
    Record.TimeOfDayHours = ClampTimeOfDayHours(Record.TimeOfDayHours);
    Record.PlayerTransform.Pitch = NormalizeDegrees(Record.PlayerTransform.Pitch);
    Record.PlayerTransform.Yaw = NormalizeDegrees(Record.PlayerTransform.Yaw);
    Record.PlayerTransform.Roll = NormalizeDegrees(Record.PlayerTransform.Roll);

    OutRecord = std::move(Record);
    OutReport = Report;
    return ESaveDecodeError::Ok;
}

inline ESaveDecodeError Decode(const std::vector<uint8_t>& Bytes, FSaveRecord& OutRecord, FMigrationReport& OutReport)
{
    return Decode(Bytes.empty() ? nullptr : Bytes.data(), Bytes.size(), OutRecord, OutReport);
}

// Encodes at CurrentRecordVersion. Deterministic: the same record always produces the
// same bytes, which is what makes the round-trip test meaningful.
inline std::vector<uint8_t> Encode(const FSaveRecord& Record)
{
    std::vector<uint8_t> Payload;
    Payload.reserve(512);
    FByteWriter PayloadWriter(Payload);
    Detail::WriteV4Payload(PayloadWriter, Record);

    std::vector<uint8_t> Out;
    Out.reserve(Payload.size() + HeaderBytes);
    FByteWriter HeaderWriter(Out);
    HeaderWriter.U8(Magic0);
    HeaderWriter.U8(Magic1);
    HeaderWriter.U8(Magic2);
    HeaderWriter.U8(Magic3);
    HeaderWriter.I32(CurrentFormatVersion);
    HeaderWriter.I32(CurrentRecordVersion);
    HeaderWriter.U32(static_cast<uint32_t>(Payload.size()));
    HeaderWriter.U32(Crc32(Payload));
    Out.insert(Out.end(), Payload.begin(), Payload.end());
    return Out;
}

// Cheap header peek for the slot list: tells the front end which version a file claims
// without decoding it. Returns 0 when the header is not a valid Mikdash header.
inline int32_t PeekRecordVersion(const uint8_t* Bytes, size_t Length)
{
    if (Bytes == nullptr || Length < static_cast<size_t>(HeaderBytes)) { return 0; }
    if (Bytes[0] != Magic0 || Bytes[1] != Magic1 || Bytes[2] != Magic2 || Bytes[3] != Magic3) { return 0; }
    FByteReader Reader(Bytes, static_cast<size_t>(HeaderBytes));
    Reader.U32();
    const int32_t FormatVersion = Reader.I32();
    const int32_t RecordVersion = Reader.I32();
    if (!Reader.IsOk() || FormatVersion != CurrentFormatVersion) { return 0; }
    return RecordVersion;
}

}  // namespace MikdashSave


// ===========================================================================
// RTL layout arithmetic.
//
// Mirroring an interface is not the same as reversing a string. Slate reverses the text
// run itself through ICU; what it does NOT do for hand-authored geometry is decide where
// a progress bar starts filling from, which side a panel's padding is on, or where a
// slider handle sits at 30%. Those are the sums below, and they are the ones that go
// wrong silently -- a bar that fills from the wrong end still looks like a bar.
//
// Every mirror here is an involution: applying it twice returns the original. That is the
// property the tests lean on, because a nested widget tree mirrors at each level and a
// non-involutive mirror drifts.
// ===========================================================================
namespace MikdashRtl
{

enum class EFlow : int { LeftToRight = 0, RightToLeft = 1 };

// Matches EFlowDirectionPreference in SlateCore/Public/Layout/FlowDirection.h so the
// runtime can cast between them; verified against UE 5.8.
enum class EFlowPreference : int { Inherit = 0, Culture = 1, LeftToRight = 2, RightToLeft = 3 };

// Matches ETextJustify::Type in SlateCore/Public/Styling/SlateTypes.h.
enum class EJustify : int { Left = 0, Center = 1, Right = 2 };

inline EFlow Opposite(EFlow Flow)
{
    return Flow == EFlow::LeftToRight ? EFlow::RightToLeft : EFlow::LeftToRight;
}

inline bool IsRightToLeft(EFlow Flow) { return Flow == EFlow::RightToLeft; }

// Culture code to layout direction. Handles the "he-IL" / "he_IL" / "iw" spellings that
// turn up in saved settings and on command lines. Kept explicit rather than asking ICU,
// so the answer is identical in the standalone test and in the packaged build.
inline EFlow LayoutDirectionForCulture(const char* CultureCode)
{
    if (CultureCode == nullptr) { return EFlow::LeftToRight; }

    char Language[8] = { 0 };
    int Index = 0;
    for (; Index < 7 && CultureCode[Index] != '\0'; ++Index)
    {
        const char C = CultureCode[Index];
        if (C == '-' || C == '_') { break; }
        Language[Index] = (C >= 'A' && C <= 'Z') ? static_cast<char>(C - 'A' + 'a') : C;
    }
    Language[Index] = '\0';

    // he: Hebrew. iw: the deprecated ISO code for Hebrew, still emitted by some tools.
    // yi: Yiddish, Hebrew script. ar/fa/ur/ps/sd/dv/ckb: the other right-to-left scripts
    // a build might be handed. Only he is shipped here; the rest are listed so a stray
    // culture code cannot silently produce a left-to-right Hebrew-script layout.
    static const char* RtlLanguages[] = { "he", "iw", "yi", "ji", "ar", "fa", "ur", "ps", "sd", "dv", "ckb" };
    for (const char* Candidate : RtlLanguages)
    {
        if (std::strcmp(Language, Candidate) == 0) { return EFlow::RightToLeft; }
    }
    return EFlow::LeftToRight;
}

// Mirrors SWidget::ComputeFlowDirection in UE 5.8: Inherit keeps the parent's flow,
// Culture restarts from the culture's own direction, and the two explicit values force it.
inline EFlow ResolveFlow(EFlow ParentFlow, EFlowPreference Preference, EFlow CultureFlow)
{
    switch (Preference)
    {
    case EFlowPreference::Inherit:     return ParentFlow;
    case EFlowPreference::Culture:     return CultureFlow;
    case EFlowPreference::LeftToRight: return EFlow::LeftToRight;
    case EFlowPreference::RightToLeft: return EFlow::RightToLeft;
    }
    return ParentFlow;
}

// A child box laid out at Left with width ChildWidth inside a parent of ParentWidth,
// reflected about the parent's vertical centre line. The involution ParentWidth - (Left +
// ChildWidth) is exact in floating point when the operands are exact, and it is what keeps
// a mirrored-twice layout identical to the original.
inline double MirrorLeft(double Left, double ChildWidth, double ParentWidth)
{
    return ParentWidth - (Left + ChildWidth);
}

// Normalised alignment (0 = leading edge, 1 = trailing edge).
inline double MirrorAlignment(double Alignment) { return 1.0 - Alignment; }

// Padding is authored left/top/right/bottom; mirroring swaps the horizontal pair only.
struct FMargin
{
    double Left = 0.0;
    double Top = 0.0;
    double Right = 0.0;
    double Bottom = 0.0;

    bool operator==(const FMargin& Other) const
    {
        return Left == Other.Left && Top == Other.Top && Right == Other.Right && Bottom == Other.Bottom;
    }
};

inline FMargin MirrorMargin(const FMargin& In)
{
    FMargin Out;
    Out.Left = In.Right;
    Out.Top = In.Top;
    Out.Right = In.Left;
    Out.Bottom = In.Bottom;
    return Out;
}

inline EJustify MirrorJustify(EJustify In)
{
    if (In == EJustify::Left) { return EJustify::Right; }
    if (In == EJustify::Right) { return EJustify::Left; }
    return EJustify::Center;
}

// Text justification that follows the flow: a paragraph's natural justification is its
// leading edge, which is the right in an RTL layout.
inline EJustify NaturalJustify(EFlow Flow)
{
    return Flow == EFlow::RightToLeft ? EJustify::Right : EJustify::Left;
}

inline double ClampUnit(double Value)
{
    if (!(Value == Value)) { return 0.0; }  // NaN
    if (Value < 0.0) { return 0.0; }
    if (Value > 1.0) { return 1.0; }
    return Value;
}

// A filled bar. The filled span always has the same width; only which end it grows from
// changes. This is the sum that a "just reverse the text" approach gets wrong.
struct FFillSpan
{
    double Offset = 0.0;
    double Width = 0.0;

    bool operator==(const FFillSpan& Other) const { return Offset == Other.Offset && Width == Other.Width; }
};

inline FFillSpan ProgressFill(double Fraction, double TrackWidth, EFlow Flow)
{
    const double Clamped = ClampUnit(Fraction);
    FFillSpan Span;
    Span.Width = TrackWidth * Clamped;
    Span.Offset = (Flow == EFlow::RightToLeft) ? (TrackWidth - Span.Width) : 0.0;
    return Span;
}

// Centre of a slider handle on its track. At 0 the handle sits at the leading edge, which
// is the right-hand end in an RTL layout.
inline double SliderHandleCentre(double Fraction, double TrackWidth, double HandleWidth, EFlow Flow)
{
    const double Clamped = ClampUnit(Fraction);
    const double Travel = TrackWidth - HandleWidth;
    const double Along = HandleWidth * 0.5 + Travel * Clamped;
    return (Flow == EFlow::RightToLeft) ? (TrackWidth - Along) : Along;
}

// Horizontal scroll offset, measured from the leading edge in both directions, converted
// to the left-anchored offset the renderer wants.
inline double ScrollOffsetToLeft(double LeadingOffset, double ContentWidth, double ViewportWidth, EFlow Flow)
{
    const double MaxOffset = ContentWidth - ViewportWidth;
    const double Clamped = MaxOffset <= 0.0 ? 0.0 : (LeadingOffset < 0.0 ? 0.0 : (LeadingOffset > MaxOffset ? MaxOffset : LeadingOffset));
    return (Flow == EFlow::RightToLeft) ? (MaxOffset - Clamped) : Clamped;
}

// Index of a child in a row after mirroring: the first authored child sits at the leading
// edge, which is the right-hand end in RTL, so the paint order reverses.
inline int32_t MirrorChildIndex(int32_t Index, int32_t Count)
{
    if (Count <= 0) { return 0; }
    if (Index < 0) { return 0; }
    if (Index >= Count) { return Count - 1; }
    return Count - 1 - Index;
}

// Icons that encode a direction (a back chevron, a "next" arrow, a progress caret) have to
// flip; icons that encode a thing (a camera, a menorah, a compass rose showing real world
// north) must not. The caller declares which kind it has; this only answers the direction
// question, and it answers "no" for LTR so a shared style asset stays correct in both.
inline bool ShouldMirrorDirectionalIcon(EFlow Flow) { return Flow == EFlow::RightToLeft; }

// Horizontal component of a nudge or a swipe, in layout space. A "move towards the next
// item" gesture is +1 in LTR and -1 in RTL.
inline double DirectionalSign(EFlow Flow) { return Flow == EFlow::RightToLeft ? -1.0 : 1.0; }

}  // namespace MikdashRtl
