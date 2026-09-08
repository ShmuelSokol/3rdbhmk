#pragma once
#include "MikdashSceneUnitsMath.h"
#include "SaveMigrationMath.h"
#include <iomanip>
#include <locale>
#include <sstream>

// Scene metadata uses the existing CRC-protected extension list. The historical
// binary format and source-amot decoder remain unchanged, including old50cm saves.
namespace MikdashSaveScene
{
inline constexpr const char* MetadataKey = "mikdash.scene.coordinates";
enum class Decision
{
    RestorePosition, RestoreLegacyPosition, DifferentLayout, InvalidSavedIdentity,
    InvalidCurrentIdentity, NoWalkingPosition
};
struct Identity
{
    MikdashSceneUnits::Frame Frame;
    std::string MapPackage;
    bool HasWalkingPosition = false;
};
inline bool ValidMap(const std::string& Map)
{
    return !Map.empty() && Map.size() <= 1024 && Map[0] == '/'
        && Map.find_first_of("|\r\n\t") == std::string::npos;
}
inline bool SameFrame(const MikdashSceneUnits::Frame& A, const MikdashSceneUnits::Frame& B)
{
    return MikdashSceneUnits::Valid(A) && MikdashSceneUnits::Valid(B)
        && A.SchemaVersion == B.SchemaVersion && A.CoordinateRevision == B.CoordinateRevision
        && A.FixedOrigin.X == B.FixedOrigin.X && A.FixedOrigin.Y == B.FixedOrigin.Y
        && A.FixedOrigin.Z == B.FixedOrigin.Z;
}
inline std::string Encode(const Identity& Value)
{
    if (!MikdashSceneUnits::Valid(Value.Frame) || !ValidMap(Value.MapPackage)) return "invalid";
    std::ostringstream Out;
    Out.imbue(std::locale::classic());
    Out << "1|" << (Value.Frame.CoordinateRevision == MikdashSceneUnits::Revision::Legacy50V1 ? "Legacy50.v1" : "Selected48.v1")
        << '|' << std::setprecision(17) << Value.Frame.FixedOrigin.X << '|'
        << Value.Frame.FixedOrigin.Y << '|' << Value.Frame.FixedOrigin.Z << '|'
        << Value.MapPackage << '|' << (Value.HasWalkingPosition ? '1' : '0');
    return Out.str();
}
inline bool Number(const std::string& Text, double& Out)
{
    if (Text.empty()) return false;
    std::istringstream Input(Text);
    Input.imbue(std::locale::classic());
    double Candidate = 0;
    Input >> std::noskipws >> Candidate;
    if (!Input || !Input.eof() || !std::isfinite(Candidate)) return false;
    Out = Candidate; return true;
}
inline bool Decode(const std::string& Text, Identity& Out)
{
    std::array<std::string,7> Fields;
    std::size_t Start = 0;
    for (std::size_t I = 0; I < Fields.size(); ++I)
    {
        const std::size_t End = Text.find('|', Start);
        if ((I+1 < Fields.size() && End == std::string::npos)
            || (I+1 == Fields.size() && End != std::string::npos)) return false;
        Fields[I] = Text.substr(Start, End == std::string::npos ? End : End-Start);
        Start = End == std::string::npos ? Text.size() : End+1;
    }
    Identity Candidate;
    if (Fields[0] != "1") return false;
    if (Fields[1] == "Legacy50.v1") Candidate.Frame.CoordinateRevision = MikdashSceneUnits::Revision::Legacy50V1;
    else if (Fields[1] == "Selected48.v1") Candidate.Frame.CoordinateRevision = MikdashSceneUnits::Revision::Selected48V1;
    else return false;
    if (!Number(Fields[2],Candidate.Frame.FixedOrigin.X)
        || !Number(Fields[3],Candidate.Frame.FixedOrigin.Y)
        || !Number(Fields[4],Candidate.Frame.FixedOrigin.Z) || !ValidMap(Fields[5])) return false;
    Candidate.MapPackage = Fields[5];
    if (Fields[6] != "0" && Fields[6] != "1") return false;
    Candidate.HasWalkingPosition = Fields[6] == "1";
    Out = Candidate; return true;
}
// Caller captures fresh settings first. No non-metadata option is removed or
// truncated; on lack of capacity the record stays unchanged and no slot is written.
inline bool Store(MikdashSave::FSaveRecord& Record, const Identity* ValidIdentity)
{
    std::vector<MikdashSave::FOptionValue> Options;
    for (const auto& Value : Record.Options)
        if (Value.Key != MetadataKey) Options.push_back(Value);
    if (Options.size() >= MikdashSave::MaxOptionCount) return false;
    MikdashSave::FOptionValue Metadata;
    Metadata.Key = MetadataKey;
    Metadata.Type = MikdashSave::EOptionType::String;
    Metadata.StringValue = ValidIdentity ? Encode(*ValidIdentity) : "invalid";
    Options.push_back(Metadata);
    Record.Options = std::move(Options); return true;
}
inline std::string ShortMapName(const std::string& Map)
{
    const auto Slash = Map.find_last_of('/');
    std::string Name = Slash == std::string::npos ? Map : Map.substr(Slash+1);
    const std::string Prefix = "UEDPIE_";
    if (Name.compare(0,Prefix.size(),Prefix) == 0)
    {
        const auto End = Name.find('_',Prefix.size());
        bool Digits = End != std::string::npos && End > Prefix.size();
        if (Digits) for (std::size_t I=Prefix.size(); I<End; ++I)
            if (Name[I] < '0' || Name[I] > '9') Digits=false;
        if (Digits) Name = Name.substr(End+1);
    }
    return Name;
}
inline Decision Evaluate(const MikdashSave::FSaveRecord& Record,
                         const MikdashSceneUnits::Frame* Current, const std::string& CurrentMap)
{
    if (!Current || !MikdashSceneUnits::Valid(*Current) || !ValidMap(CurrentMap))
        return Decision::InvalidCurrentIdentity;
    const MikdashSave::FOptionValue* Found = nullptr;
    for (const auto& Value : Record.Options)
    {
        if (Value.Key != MetadataKey) continue;
        if (Found) return Decision::InvalidSavedIdentity;
        Found = &Value;
    }
    if (!Found)
    {
        // Older saves had no origin/revision identity. Preserve their historical
        // behavior only in the origin-zero legacy scene, never assume candidate48.
        const MikdashSceneUnits::Frame Legacy;
        const bool CompatibleMap = Record.MapName.empty() || ShortMapName(Record.MapName) == ShortMapName(CurrentMap);
        return SameFrame(*Current,Legacy) && CompatibleMap ? Decision::RestoreLegacyPosition : Decision::DifferentLayout;
    }
    Identity Saved;
    if (Found->Type != MikdashSave::EOptionType::String || !Decode(Found->StringValue,Saved))
        return Decision::InvalidSavedIdentity;
    if (!Saved.HasWalkingPosition) return Decision::NoWalkingPosition;
    return SameFrame(Saved.Frame,*Current) && Saved.MapPackage == CurrentMap
        ? Decision::RestorePosition : Decision::DifferentLayout;
}
}
