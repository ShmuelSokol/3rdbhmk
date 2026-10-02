#include "ContextMaterialFixture.h"
#include "Containers/Ticker.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/DefaultPawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstance.h"
#include "Materials/MaterialRenderProxy.h"
#include "MaterialShared.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "RenderingThread.h"
#include "SceneInterface.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/UObjectGlobals.h"
#include "UnrealClient.h"

namespace ContextMaterialFixture
{
namespace
{
const TCHAR* Packages[] = {
    TEXT("/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building"),
    TEXT("/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall"),
    TEXT("/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/M_CityFacadeV1"),
    TEXT("/Game/MikdashV3/JerusalemContext/CityDetailV1/Materials/MI_CityDetail_Canvas"),
    TEXT("/Game/MikdashV3/JerusalemContext/CityDetailV1/Materials/MI_CityDetail_CityStone"),
    TEXT("/Game/MikdashV3/JerusalemContext/CityDetailV1/Materials/MI_CityDetail_DarkPlant"),
    TEXT("/Game/MikdashV3/JerusalemContext/CityDetailV1/Materials/MI_CityDetail_Laundry"),
    TEXT("/Game/MikdashV3/JerusalemContext/CityDetailV1/Materials/MI_CityDetail_Meleke"),
    TEXT("/Game/MikdashV3/JerusalemContext/CityDetailV1/Materials/MI_CityDetail_Metal"),
    TEXT("/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/MI_CityFacade_CityStone"),
    TEXT("/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Materials/MI_OldCityPlaster"),
    TEXT("/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/ExteriorFixesV1/MI_M_Context_Building_ExteriorV1"),
    TEXT("/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/ExteriorFixesV1/MI_M_Context_CityWall_ExteriorV1")
};

struct FFixture
{
    FString Output;
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<UStaticMeshComponent> StaticCoupon;
    TWeakObjectPtr<UHierarchicalInstancedStaticMeshComponent> HismCoupon;
    TWeakObjectPtr<ACameraActor> Camera;
    TWeakObjectPtr<ADefaultPawn> HiddenPawn;
    bool bPawnWasHidden = false;
    TArray<TWeakObjectPtr<AActor>> Actors;
    TSharedRef<FJsonObject> Receipt = MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Rows;
    TSharedPtr<FJsonObject> Row;
    FDelegateHandle MapHandle;
    FDelegateHandle ScreenshotHandle;
    FTSTicker::FDelegateHandle TickHandle;
    double Started = FPlatformTime::Seconds();
    double PhaseStarted = 0;
    int32 Index = 0;
    int32 Phase = 0;
    bool bScreenshotProcessed = false;
    bool bFinished = false;
    bool bWritable = false;
    bool bChecksPassed = true;
};
TUniquePtr<FFixture> State;

TSharedRef<FJsonObject> TransformJson(const FTransform& Transform)
{
    TSharedRef<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("location"), Transform.GetLocation().ToString());
    Result->SetStringField(TEXT("rotation"), Transform.Rotator().ToString());
    Result->SetStringField(TEXT("scale"), Transform.GetScale3D().ToString());
    return Result;
}

void Finish(bool bPassed, const FString& Status)
{
    if (!State || State->bFinished) return;
    State->bFinished = true;
    if (State->Row && State->Index < UE_ARRAY_COUNT(Packages) && State->Rows.Num() == State->Index)
    {
        State->Row->SetBoolField(TEXT("screenshotProcessed"), false);
        State->Rows.Add(MakeShared<FJsonValueObject>(State->Row));
    }
    State->Receipt->SetBoolField(TEXT("passed"), bPassed);
    State->Receipt->SetBoolField(TEXT("completed"), State->Index == UE_ARRAY_COUNT(Packages));
    State->Receipt->SetStringField(TEXT("status"), Status);
    State->Receipt->SetStringField(TEXT("scope"), TEXT("isolated cooked material fixture; full-map and visual acceptance not asserted"));
    State->Receipt->SetArrayField(TEXT("materials"), State->Rows);
    State->Receipt->SetNumberField(TEXT("elapsedSeconds"), FPlatformTime::Seconds() - State->Started);
    FString Json;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Json);
    FJsonSerializer::Serialize(State->Receipt, Writer);
    const bool bSaved = State->bWritable && FFileHelper::SaveStringToFile(Json, *(State->Output / TEXT("native-fixture.json")));
    UE_LOG(LogTemp, Display, TEXT("ContextMaterialFixture finished passed=%d receiptSaved=%d status=%s"), bPassed, bSaved, *Status);
    FPlatformMisc::RequestExit(false);
}

template<typename T> T* Spawn(UWorld* World, const FVector& Location, const FRotator& Rotation)
{
    FActorSpawnParameters Parameters;
    Parameters.ObjectFlags |= RF_Transient;
    T* Result = World->SpawnActor<T>(Location, Rotation, Parameters);
    if (Result) State->Actors.Add(Result);
    return Result;
}

void OnMap(UWorld* World)
{
    if (!State || State->bFinished) return;
    if (!World || !World->IsGameWorld() || World->GetPackage()->GetName() != TEXT("/Engine/Maps/Entry") ||
        !World->GetAuthGameMode() || World->GetAuthGameMode()->GetClass() != AGameModeBase::StaticClass() ||
        World->GetLevels().Num() != 1 || World->GetStreamingLevels().Num() != 0 || State->World.IsValid())
    {
        Finish(false, TEXT("refused-world-or-game-mode"));
        return;
    }
    State->Receipt->SetStringField(TEXT("worldPackage"), World->GetPackage()->GetName());
    State->Receipt->SetStringField(TEXT("gameModeClass"), World->GetAuthGameMode()->GetClass()->GetPathName());
    TArray<TSharedPtr<FJsonValue>> OriginalActors;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* ExistingActor = *It;
        OriginalActors.Add(MakeShared<FJsonValueString>(ExistingActor->GetPathName() + TEXT(" : ") + ExistingActor->GetClass()->GetPathName()));
        TInlineComponentArray<UStaticMeshComponent*> Meshes(ExistingActor);
        const bool bDefaultPlayerPawn = ExistingActor->GetClass() == ADefaultPawn::StaticClass() &&
            ExistingActor->HasAnyFlags(RF_Transient) && World->GetFirstPlayerController() &&
            World->GetFirstPlayerController()->GetPawn() == ExistingActor;
        if ((!Meshes.IsEmpty() && !bDefaultPlayerPawn) || ExistingActor->GetClass()->GetPathName().StartsWith(TEXT("/Script/MikdashRuntime.")))
        {
            Finish(false, TEXT("refused-existing-scene-actor"));
            return;
        }
    }
    State->Receipt->SetArrayField(TEXT("originalActors"), OriginalActors);
    State->World = World;
    State->PhaseStarted = FPlatformTime::Seconds();
}

bool BuildScene(UWorld* World)
{
    UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
    APlayerController* Controller = World->GetFirstPlayerController();
    if (!Cube || !Controller || !World->Scene) return false;
    APawn* Pawn = Controller->GetPawn();
    if (Pawn)
    {
        if (Pawn->GetClass() != ADefaultPawn::StaticClass() || !Pawn->HasAnyFlags(RF_Transient)) return false;
        State->HiddenPawn = CastChecked<ADefaultPawn>(Pawn);
        State->bPawnWasHidden = Pawn->IsHidden();
        Pawn->SetActorHiddenInGame(true);
        State->Receipt->SetStringField(TEXT("hiddenDefaultPawn"), Pawn->GetPathName());
        State->Receipt->SetBoolField(TEXT("defaultPawnPreviouslyHidden"), State->bPawnWasHidden);
        State->Receipt->SetBoolField(TEXT("defaultPawnHiddenReadback"), Pawn->IsHidden());
    }
    for (int32 CouponIndex = 0; CouponIndex < 2; ++CouponIndex)
    {
        AActor* CouponActor = Spawn<AActor>(World, FVector::ZeroVector, FRotator::ZeroRotator);
        if (!CouponActor) return false;
        UStaticMeshComponent* Component = CouponIndex == 0
            ? NewObject<UStaticMeshComponent>(CouponActor, TEXT("ContextFixtureStatic"), RF_Transient)
            : NewObject<UHierarchicalInstancedStaticMeshComponent>(CouponActor, TEXT("ContextFixtureHISM"), RF_Transient);
        CouponActor->AddInstanceComponent(Component);
        CouponActor->SetRootComponent(Component);
        Component->SetMobility(EComponentMobility::Movable);
        Component->SetStaticMesh(Cube);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCanEverAffectNavigation(false);
        Component->SetGenerateOverlapEvents(false);
        Component->RegisterComponent();
        const FTransform CouponTransform(FRotator::ZeroRotator,
            CouponIndex == 0 ? FVector(-270, 270, 200) : FVector(270, -270, 200), FVector(4));
        if (CouponIndex == 0)
        {
            Component->SetWorldTransform(CouponTransform);
            State->StaticCoupon = Component;
        }
        else
        {
            UHierarchicalInstancedStaticMeshComponent* Hism = CastChecked<UHierarchicalInstancedStaticMeshComponent>(Component);
            Hism->AddInstance(CouponTransform, true);
            State->HismCoupon = Hism;
        }
    }
    ADirectionalLight* Light = Spawn<ADirectionalLight>(World, FVector(0, 0, 1000), FRotator(-40, 225, 0));
    ACameraActor* Camera = Spawn<ACameraActor>(World, FVector(1150, 1150, 760), FRotator(-19, 225, 0));
    if (!Light || !Camera) return false;
    Light->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Light->GetLightComponent()->SetIntensity(5.0f);
    UCameraComponent* CameraComponent = Camera->GetCameraComponent();
    CameraComponent->SetFieldOfView(70.0f);
    CameraComponent->SetAspectRatio(1280.0f / 720.0f);
    CameraComponent->SetConstraintAspectRatio(true);
    CameraComponent->PostProcessBlendWeight = 1.0f;
    FPostProcessSettings& Settings = CameraComponent->PostProcessSettings;
    Settings.bOverride_AutoExposureMinBrightness = true; Settings.AutoExposureMinBrightness = 1;
    Settings.bOverride_AutoExposureMaxBrightness = true; Settings.AutoExposureMaxBrightness = 1;
    Settings.bOverride_AutoExposureBias = true; Settings.AutoExposureBias = 0;
    Settings.bOverride_BloomIntensity = true; Settings.BloomIntensity = 0;
    Settings.bOverride_VignetteIntensity = true; Settings.VignetteIntensity = 0;
    Controller->SetViewTarget(Camera);
    State->Camera = Camera;
    State->Receipt->SetStringField(TEXT("cubeMesh"), Cube->GetPathName());
    State->Receipt->SetObjectField(TEXT("lightTransform"), TransformJson(Light->GetActorTransform()));
    State->Receipt->SetNumberField(TEXT("lightIntensity"), Light->GetLightComponent()->Intensity);
    return true;
}

bool BindMaterial()
{
    State->Row.Reset();
    const FString Package = Packages[State->Index];
    const FString ObjectPath = Package + TEXT(".") + FPaths::GetBaseFilename(Package);
    UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, *ObjectPath);
    if (!Material || Material->GetPathName() != ObjectPath) return false;
    State->StaticCoupon->SetMaterial(0, Material);
    State->HismCoupon->SetMaterial(0, Material);
    State->Row = MakeShared<FJsonObject>();
    State->Row->SetBoolField(TEXT("passed"), false);
    State->Row->SetNumberField(TEXT("index"), State->Index);
    State->Row->SetStringField(TEXT("requestedPackage"), Package);
    State->Row->SetStringField(TEXT("loadedMaterial"), Material->GetPathName());
    State->Row->SetStringField(TEXT("materialClass"), Material->GetClass()->GetPathName());
    TArray<TSharedPtr<FJsonValue>> Parents;
    UMaterialInterface* Current = Material;
    for (int32 Depth = 0; Current && Depth < 16; ++Depth)
    {
        Parents.Add(MakeShared<FJsonValueString>(Current->GetPathName()));
        UMaterialInstance* Instance = Cast<UMaterialInstance>(Current);
        Current = Instance ? Instance->Parent.Get() : nullptr;
    }
    State->Row->SetArrayField(TEXT("parentChain"), Parents);
    State->Row->SetStringField(TEXT("photoPath"), State->Output / FString::Printf(TEXT("material-%02d.png"), State->Index));
    State->PhaseStarted = FPlatformTime::Seconds();
    return true;
}

bool Readback()
{
    UWorld* World = State->World.Get();
    UMaterialInterface* Material = State->StaticCoupon->GetMaterial(0);
    if (!World || !World->Scene || !Material || !State->Camera.IsValid() || !World->GetFirstPlayerController()) return false;
    const bool bBound = State->HismCoupon->GetMaterial(0) == Material && Material->GetPathName() == State->Row->GetStringField(TEXT("loadedMaterial"));
    const FIntPoint Size = GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport ? GEngine->GameViewport->Viewport->GetSizeXY() : FIntPoint::ZeroValue;
    State->Row->SetNumberField(TEXT("viewportWidth"), Size.X);
    State->Row->SetNumberField(TEXT("viewportHeight"), Size.Y);
    State->Row->SetBoolField(TEXT("exactBinding"), bBound);
    State->Row->SetStringField(TEXT("staticMaterial"), Material->GetPathName());
    State->Row->SetStringField(TEXT("hismMaterial"), GetPathNameSafe(State->HismCoupon->GetMaterial(0)));
    State->Row->SetNumberField(TEXT("hismInstanceCount"), State->HismCoupon->GetInstanceCount());
    State->Row->SetObjectField(TEXT("staticTransform"), TransformJson(State->StaticCoupon->GetComponentTransform()));
    FTransform InstanceTransform;
    const bool bInstanceRead = State->HismCoupon->GetInstanceTransform(0, InstanceTransform, true);
    State->Row->SetObjectField(TEXT("hismInstanceTransform"), TransformJson(InstanceTransform));
    State->Row->SetObjectField(TEXT("camera"), TransformJson(State->Camera->GetActorTransform()));
    State->Row->SetNumberField(TEXT("cameraFov"), State->Camera->GetCameraComponent()->FieldOfView);
    FVector ActualCameraLocation;
    FRotator ActualCameraRotation;
    World->GetFirstPlayerController()->GetPlayerViewPoint(ActualCameraLocation, ActualCameraRotation);
    State->Row->SetObjectField(TEXT("actualPlayerView"), TransformJson(FTransform(ActualCameraRotation, ActualCameraLocation)));
    const bool bCameraMatches = ActualCameraLocation.Equals(FVector(1150, 1150, 760), 0.1) &&
        ActualCameraRotation.Equals(FRotator(-19, 225, 0), 0.01) &&
        State->Camera->GetActorLocation().Equals(ActualCameraLocation, 0.1) &&
        State->Camera->GetActorRotation().Equals(ActualCameraRotation, 0.01) &&
        FMath::IsNearlyEqual(State->Camera->GetCameraComponent()->FieldOfView, 70.0f, 0.001f);
    State->Row->SetBoolField(TEXT("actualCameraMatchesFixed"), bCameraMatches);
    const FPostProcessSettings& Exposure = State->Camera->GetCameraComponent()->PostProcessSettings;
    State->Row->SetNumberField(TEXT("exposureMinBrightness"), Exposure.AutoExposureMinBrightness);
    State->Row->SetNumberField(TEXT("exposureMaxBrightness"), Exposure.AutoExposureMaxBrightness);
    State->Row->SetNumberField(TEXT("exposureBias"), Exposure.AutoExposureBias);
    State->Row->SetStringField(TEXT("viewTarget"), GetPathNameSafe(World->GetFirstPlayerController()->GetViewTarget()));
    const EShaderPlatform Platform = World->Scene->GetShaderPlatform();
    FMaterialResource* Resource = Material->GetMaterialResource(Platform);
    const bool bGameComplete = Resource && Resource->GetGameThreadShaderMap() && Resource->IsGameThreadShaderMapComplete();
    State->Row->SetNumberField(TEXT("shaderPlatform"), static_cast<int32>(Platform));
    State->Row->SetBoolField(TEXT("gameThreadResourcePresent"), Resource != nullptr);
    State->Row->SetBoolField(TEXT("gameThreadShaderMapComplete"), bGameComplete);
    State->Row->SetBoolField(TEXT("instancedStaticMeshUsage"), Resource && Resource->IsUsedWithInstancedStaticMeshes());
    struct FRenderReadback { bool bPresent = false; bool bComplete = false; bool bFallback = true; FString AssetName; } Render;
    FMaterialRenderProxy* Proxy = Material->GetRenderProxy();
    const ERHIFeatureLevel::Type Feature = World->GetFeatureLevel();
    if (Proxy)
    {
        ENQUEUE_RENDER_COMMAND(ContextFixtureReadback)([Proxy, Feature, &Render](FRHICommandListImmediate&)
        {
            const FMaterial* Actual = Proxy->GetMaterialNoFallback(Feature);
            Render.bPresent = Actual != nullptr;
            Render.bComplete = Actual && Actual->GetRenderingThreadShaderMap() && Actual->IsRenderingThreadShaderMapComplete();
            const FMaterialRenderProxy* SelectedProxy = Proxy;
            const FMaterial& Selected = Proxy->GetMaterialWithFallback(Feature, SelectedProxy);
            Render.bFallback = SelectedProxy != Proxy;
            Render.AssetName = Selected.GetAssetName();
        });
        FlushRenderingCommands();
    }
    State->Row->SetBoolField(TEXT("renderThreadMaterialPresent"), Render.bPresent);
    State->Row->SetBoolField(TEXT("renderThreadShaderMapComplete"), Render.bComplete);
    State->Row->SetBoolField(TEXT("renderThreadFallbackUsed"), Render.bFallback);
    State->Row->SetStringField(TEXT("renderThreadSelectedAsset"), Render.AssetName);
    const bool bPassed = bBound && bCameraMatches && bInstanceRead && State->HismCoupon->GetInstanceCount() == 1 &&
        Size == FIntPoint(1280, 720) && World->GetFirstPlayerController()->GetViewTarget() == State->Camera.Get() &&
        bGameComplete && Render.bPresent && Render.bComplete && !Render.bFallback && Resource->IsUsedWithInstancedStaticMeshes();
    State->Row->SetBoolField(TEXT("passed"), bPassed);
    return bPassed;
}

bool Tick(float)
{
    if (!State || State->bFinished) return false;
    const double Now = FPlatformTime::Seconds();
    if (Now - State->Started > 150) { Finish(false, TEXT("total-timeout")); return false; }
    UWorld* World = State->World.Get();
    if (!World) return true;
    if (World->GetPackage()->GetName() != TEXT("/Engine/Maps/Entry")) { Finish(false, TEXT("world-changed")); return false; }
    if (State->Phase == 0)
    {
        if (Now - State->PhaseStarted < 5 || !World->GetFirstPlayerController()) return true;
        if (!BuildScene(World) || !BindMaterial()) { Finish(false, TEXT("fixture-setup-failed")); return false; }
        State->Phase = 1;
    }
    else if (State->Phase == 1 && Now - State->PhaseStarted >= 3)
    {
        State->bChecksPassed &= Readback();
        State->bScreenshotProcessed = false;
        FScreenshotRequest::RequestScreenshot(State->Row->GetStringField(TEXT("photoPath")), false, false);
        State->PhaseStarted = Now;
        State->Phase = 2;
    }
    else if (State->Phase == 2)
    {
        const FString Path = State->Row->GetStringField(TEXT("photoPath"));
        const int64 Bytes = IFileManager::Get().FileSize(*Path);
        if (State->bScreenshotProcessed && Bytes > 8)
        {
            State->Row->SetBoolField(TEXT("screenshotProcessed"), true);
            State->Row->SetNumberField(TEXT("photoBytes"), static_cast<double>(Bytes));
            State->Rows.Add(MakeShared<FJsonValueObject>(State->Row));
            UE_LOG(LogTemp, Display, TEXT("ContextMaterialFixture material=%d passed=%d photo=%s"), State->Index, State->Row->GetBoolField(TEXT("passed")), *Path);
            ++State->Index;
            if (State->Index == UE_ARRAY_COUNT(Packages)) { Finish(State->bChecksPassed, TEXT("completed")); return false; }
            if (!BindMaterial()) { Finish(false, TEXT("material-load-failed")); return false; }
            State->Phase = 1;
        }
        else if (Now - State->PhaseStarted > 20) { Finish(false, TEXT("screenshot-timeout")); return false; }
    }
    return true;
}
} // namespace

void Startup()
{
    if (!FParse::Param(FCommandLine::Get(), TEXT("MikdashContextMaterialFixture"))) return;
    State = MakeUnique<FFixture>();
    if (!FParse::Value(FCommandLine::Get(), TEXT("MikdashContextFixtureOutput="), State->Output) ||
        State->Output.IsEmpty() || FPaths::IsRelative(State->Output))
    { Finish(false, TEXT("absolute-output-required")); return; }
    FPaths::NormalizeDirectoryName(State->Output);
    TArray<FString> ExistingFiles;
    IFileManager::Get().FindFilesRecursive(ExistingFiles, *State->Output, TEXT("*"), true, false);
    if (!ExistingFiles.IsEmpty()) { Finish(false, TEXT("refused-nonempty-output")); return; }
    State->bWritable = IFileManager::Get().MakeDirectory(*State->Output, true);
    if (!State->bWritable) { Finish(false, TEXT("output-create-failed")); return; }
    State->Receipt->SetStringField(TEXT("auditSha256"), TEXT("091504419cf3faaa97213b259c5d2cf208550e3ee552066a5d3e06fa331c6467"));
    State->Receipt->SetNumberField(TEXT("requestedMaterialCount"), UE_ARRAY_COUNT(Packages));
    if (!FString(FCommandLine::Get()).Contains(TEXT("/Engine/Maps/Entry?game=/Script/Engine.GameModeBase")))
    { Finish(false, TEXT("explicit-entry-url-required")); return; }
    State->MapHandle = FCoreUObjectDelegates::PostLoadMapWithWorld.AddStatic(&OnMap);
    State->ScreenshotHandle = FScreenshotRequest::OnScreenshotRequestProcessed().AddLambda([]() { if (State) State->bScreenshotProcessed = true; });
    State->TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateStatic(&Tick));
}

void Shutdown()
{
    if (!State) return;
    FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(State->MapHandle);
    FScreenshotRequest::OnScreenshotRequestProcessed().Remove(State->ScreenshotHandle);
    FTSTicker::GetCoreTicker().RemoveTicker(State->TickHandle);
    if (State->HiddenPawn.IsValid()) State->HiddenPawn->SetActorHiddenInGame(State->bPawnWasHidden);
    for (const TWeakObjectPtr<AActor>& Actor : State->Actors) if (Actor.IsValid()) Actor->Destroy();
    State.Reset();
}
} // namespace ContextMaterialFixture
