#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "NativeMaterialResourceInspectionLibrary.generated.h"

class UMaterial;

UENUM(BlueprintType)
enum class ENativeInspectionPlatform : uint8
{
    PCD3DSM5,
    PCD3DSM6
};

UENUM(BlueprintType)
enum class ENativeInspectionQuality : uint8
{
    Low,
    Medium,
    High,
    Epic
};

USTRUCT(BlueprintType)
struct NATIVERESOURCEINSPECTOR_API FNativeMaterialResourceInspection
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category="Inspection") FString Status;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") FString MaterialPath;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") FString StateIdBefore;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") FString StateIdAfter;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") int32 RequestedPlatform = -1;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") int32 RequestedQuality = -1;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") int32 ObservedPlatform = -1;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") int32 ObservedQuality = -1;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") int32 ActiveRHIPlatform = -1;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bAllowSharedQuality = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bUsedSharedQuality = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bOnGameThread = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bSupervisorAdmitted = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bMaterialValid = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bTargetValid = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bWaitCalled = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") double WaitSeconds = 0;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bResourceBeforePresent = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bResourceAfterPresent = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bResourceIdentityStable = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bPlatformMatches = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bQualityMatches = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bCompilationFinished = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bShaderMapPresent = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bShaderMapValid = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bShaderMapComplete = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") TArray<FString> FinalCompileErrors;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bReady = false;
    // Deliberately never asserted by this game-thread inspector.
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bRenderThreadInspected = false;
    UPROPERTY(BlueprintReadOnly, Category="Inspection") bool bSaved = false;
};

UCLASS()
class NATIVERESOURCEINSPECTOR_API UNativeMaterialResourceInspectionLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    // bSupervisorAdmitted is a misuse fuse, NOT a supervisor or native permission.
    // FinishCompilation can block; a real external admitted deadline is mandatory.
    UFUNCTION(BlueprintCallable, Category="Isolated Review|Material Resource")
    static FNativeMaterialResourceInspection InspectExistingMaterial(
        UMaterial* Material,
        ENativeInspectionPlatform TargetPlatform,
        ENativeInspectionQuality TargetQuality,
        bool bAllowSharedQualityResource,
        bool bSupervisorAdmitted);
};
