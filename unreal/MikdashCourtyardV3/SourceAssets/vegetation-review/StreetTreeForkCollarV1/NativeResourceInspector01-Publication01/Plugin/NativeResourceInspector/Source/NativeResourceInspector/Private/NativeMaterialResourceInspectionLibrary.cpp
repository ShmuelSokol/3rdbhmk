#include "NativeMaterialResourceInspectionLibrary.h"
#include "ResourceInspectionDecision.h"
#include "Materials/Material.h"
#include "MaterialShared.h"
#include "SceneTypes.h"
#include "RHIShaderPlatform.h"
#include "HAL/PlatformTime.h"
#include "UObject/StrongObjectPtr.h"

namespace
{
FNativeMaterialResourceInspection FinishReport(FNativeMaterialResourceInspection R)
{
    ResourceInspectionDecision::Facts F;
    F.GameThread = R.bOnGameThread;
    F.Admitted = R.bSupervisorAdmitted;
    F.MaterialValid = R.bMaterialValid;
    F.TargetValid = R.bTargetValid;
    F.ResourceBefore = R.bResourceBeforePresent;
    F.ResourceAfter = R.bResourceAfterPresent;
    F.IdentityStable = R.bResourceIdentityStable;
    F.PlatformMatches = R.bPlatformMatches;
    F.QualityMatches = R.bQualityMatches;
    F.HasErrors = !R.FinalCompileErrors.IsEmpty();
    F.Finished = R.bCompilationFinished;
    F.MapPresent = R.bShaderMapPresent;
    F.MapValid = R.bShaderMapValid;
    F.MapComplete = R.bShaderMapComplete;
    R.Status = UTF8_TO_TCHAR(ResourceInspectionDecision::Decide(F));
    R.bReady = R.Status == TEXT("READY_REQUESTED_GAME_THREAD_RESOURCE_ONLY");
    return R;
}
}

FNativeMaterialResourceInspection UNativeMaterialResourceInspectionLibrary::InspectExistingMaterial(
    UMaterial* Material, ENativeInspectionPlatform TargetPlatform,
    ENativeInspectionQuality TargetQuality, bool bAllowSharedQualityResource,
    bool bSupervisorAdmitted)
{
    FNativeMaterialResourceInspection R;
    R.bOnGameThread = IsInGameThread();
    R.bSupervisorAdmitted = bSupervisorAdmitted;
    R.bAllowSharedQuality = bAllowSharedQualityResource;
    if (!R.bOnGameThread || !R.bSupervisorAdmitted) return FinishReport(R);
    R.bMaterialValid = IsValid(Material);
    if (!R.bMaterialValid) return FinishReport(R);
    TStrongObjectPtr<UMaterial> Retained(Material);
    EShaderPlatform Platform = SP_NumPlatforms;
    switch (TargetPlatform)
    {
        case ENativeInspectionPlatform::PCD3DSM5: Platform = SP_PCD3D_SM5; break;
        case ENativeInspectionPlatform::PCD3DSM6: Platform = SP_PCD3D_SM6; break;
        default: return FinishReport(R);
    }
    EMaterialQualityLevel::Type Quality = EMaterialQualityLevel::Num;
    switch (TargetQuality)
    {
        case ENativeInspectionQuality::Low: Quality = EMaterialQualityLevel::Low; break;
        case ENativeInspectionQuality::Medium: Quality = EMaterialQualityLevel::Medium; break;
        case ENativeInspectionQuality::High: Quality = EMaterialQualityLevel::High; break;
        case ENativeInspectionQuality::Epic: Quality = EMaterialQualityLevel::Epic; break;
        default: return FinishReport(R);
    }
    R.bTargetValid = true;
    R.RequestedPlatform = static_cast<int32>(Platform);
    R.RequestedQuality = static_cast<int32>(Quality);
    R.ActiveRHIPlatform = static_cast<int32>(GMaxRHIShaderPlatform);
    R.MaterialPath = Retained->GetPathName();
    const FGuid StateBefore = Retained->StateId;
    R.StateIdBefore = StateBefore.ToString();
    FMaterialResource* Before = Retained->GetMaterialResource(Platform, Quality);
    R.bResourceBeforePresent = Before != nullptr;
    if (!Before) return FinishReport(R);
    R.bWaitCalled = true;
    const double Started = FPlatformTime::Seconds();
    // Drain existing cache/compile work only. Never submit/recompile/save/load.
    // Editor-only module: the installed public FMaterial API is WITH_EDITOR.
    Before->FinishCompilation();
    R.WaitSeconds = FPlatformTime::Seconds() - Started;
    FMaterialResource* After = Retained->GetMaterialResource(Platform, Quality);
    R.StateIdAfter = Retained->StateId.ToString();
    R.bResourceAfterPresent = After != nullptr;
    R.bResourceIdentityStable = After == Before && Retained->StateId == StateBefore;
    if (!After || !R.bResourceIdentityStable) return FinishReport(R);
    R.ObservedPlatform = static_cast<int32>(After->GetShaderPlatform());
    R.ObservedQuality = static_cast<int32>(After->GetQualityLevel());
    R.bUsedSharedQuality = After->GetQualityLevel() == EMaterialQualityLevel::Num;
    R.bPlatformMatches = R.ObservedPlatform == R.RequestedPlatform;
    R.bQualityMatches = ResourceInspectionDecision::QualityMatches(
        R.RequestedQuality, R.ObservedQuality, static_cast<int32>(EMaterialQualityLevel::Num), bAllowSharedQualityResource);
    R.bCompilationFinished = After->IsCompilationFinished();
    R.FinalCompileErrors = After->GetCompileErrors();
    R.bShaderMapPresent = After->GetGameThreadShaderMap() != nullptr;
    R.bShaderMapValid = After->HasValidGameThreadShaderMap();
    R.bShaderMapComplete = After->IsGameThreadShaderMapComplete();
    // Also reject any identity change during completion/readback callbacks.
    R.bResourceIdentityStable = Retained->GetMaterialResource(Platform, Quality) == After && Retained->StateId == StateBefore;
    return FinishReport(R);
}
