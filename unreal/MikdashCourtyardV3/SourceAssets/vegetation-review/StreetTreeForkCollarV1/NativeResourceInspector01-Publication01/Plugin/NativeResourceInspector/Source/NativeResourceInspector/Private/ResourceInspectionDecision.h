#pragma once

// Portable author-written decision only. No UE types, reflection or resource mocks.
namespace ResourceInspectionDecision
{
struct Facts
{
    bool GameThread = false;
    bool Admitted = false;
    bool MaterialValid = false;
    bool TargetValid = false;
    bool ResourceBefore = false;
    bool ResourceAfter = false;
    bool IdentityStable = false;
    bool PlatformMatches = false;
    bool QualityMatches = false;
    bool HasErrors = false;
    bool Finished = false;
    bool MapPresent = false;
    bool MapValid = false;
    bool MapComplete = false;
};

inline const char* Decide(const Facts& F)
{
    if (!F.GameThread) return "REFUSED_NOT_GAME_THREAD";
    if (!F.Admitted) return "REFUSED_NOT_SUPERVISOR_ADMITTED";
    if (!F.MaterialValid) return "REFUSED_MATERIAL_INVALID";
    if (!F.TargetValid) return "REFUSED_TARGET_UNSUPPORTED";
    if (!F.ResourceBefore) return "PENDING_RESOURCE_ABSENT_BEFORE_WAIT";
    if (!F.ResourceAfter) return "PENDING_RESOURCE_ABSENT_AFTER_WAIT";
    if (!F.IdentityStable) return "REFUSED_IDENTITY_CHANGED";
    if (!F.PlatformMatches) return "REFUSED_PLATFORM_MISMATCH";
    if (!F.QualityMatches) return "REFUSED_QUALITY_MISMATCH";
    if (F.HasErrors) return "REFUSED_FINAL_COMPILE_ERRORS";
    if (!F.Finished) return "PENDING_COMPILATION_UNFINISHED";
    if (!F.MapPresent) return "PENDING_SHADER_MAP_ABSENT";
    if (!F.MapValid) return "PENDING_SHADER_MAP_NOT_FINALIZED";
    if (!F.MapComplete) return "PENDING_SHADER_MAP_INCOMPLETE";
    return "READY_REQUESTED_GAME_THREAD_RESOURCE_ONLY";
}

inline bool QualityMatches(int Requested, int Observed, int SharedQualitySentinel, bool AllowShared)
{
    return Requested == Observed || (AllowShared && Observed == SharedQualitySentinel);
}
}
