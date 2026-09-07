#pragma once
#include <cstddef>
#include <string>

// Engine-independent, side-effect-free selector. Call only with CurrentFloor evidence.
namespace MikdashSurfaceAudio
{
enum class Bank { Silent, RecordedStone, RecordedSoft };
struct Registration
{
    const wchar_t* PackagePath; // Exact verified imported mesh package, no object suffix.
    Bank Samples;
};

inline std::wstring CanonicalPackage(const wchar_t* Path)
{
    if (!Path) return {};
    std::wstring Value(Path);
    if (Value.compare(0, 6, L"/Game/") != 0 || Value.find(L"..") != std::wstring::npos
        || Value.find_first_of(L"\\ :\t\r\n'") != std::wstring::npos) return {};
    const auto Dot = Value.find(L'.');
    if (Dot != std::wstring::npos)
    {
        const auto Slash = Value.rfind(L'/', Dot);
        if (Slash == std::wstring::npos || Value.substr(Dot + 1) != Value.substr(Slash + 1, Dot - Slash - 1)) return {};
        Value.resize(Dot);
    }
    if (Value.empty() || Value.back() == L'/' || Value.find(L"//") != std::wstring::npos) return {};
    return Value;
}

inline bool InFamily(const std::wstring& Path, const wchar_t* Family)
{
    const std::wstring Prefix(Family);
    return Path.size() > Prefix.size() && Path.compare(0, Prefix.size(), Prefix) == 0;
}

inline Bank Route(const wchar_t* FloorMeshPath, bool Grounded, bool BlockingWalkableFloor,
                  const Registration* VerifiedFloors = nullptr, std::size_t Count = 0)
{
    if (!Grounded || !BlockingWalkableFloor) return Bank::Silent;
    const std::wstring Path = CanonicalPackage(FloorMeshPath);
    if (Path.empty() || (!VerifiedFloors && Count != 0)) return Bank::Silent;
    bool Found = false;
    Bank Explicit = Bank::Silent;
    for (std::size_t Index = 0; Index < Count; ++Index)
    {
        const Registration& Item = VerifiedFloors[Index];
        if (Path != CanonicalPackage(Item.PackagePath)) continue;
        if (Item.Samples != Bank::Silent && Item.Samples != Bank::RecordedStone && Item.Samples != Bank::RecordedSoft)
            return Bank::Silent;
        if (Found && Explicit != Item.Samples) return Bank::Silent; // Conflicting evidence fails closed.
        Found = true;
        Explicit = Item.Samples;
    }
    if (Found) return Explicit; // Also permits an explicit silent exclusion.
    // Native receipt identifies this exact top surface, not the skirt or entire family.
    if (Path == L"/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface") return Bank::RecordedStone;
    // Preserve source-family behavior from the existing controller. This is an
    // illustrative material assignment, not a geological or historical assertion.
    if (InFamily(Path, L"/Game/MikdashV3/JerusalemContext/Terrain/")) return Bank::RecordedSoft;
    if (InFamily(Path, L"/Game/MikdashV3/Architecture/")
        || InFamily(Path, L"/Game/MikdashV3/JerusalemContext/Streets/")
        || InFamily(Path, L"/Game/MikdashV3/JerusalemContext/Buildings/")) return Bank::RecordedStone;
    return Bank::Silent;
}
}
