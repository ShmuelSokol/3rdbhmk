#include "MikdashPhotoMode.h"

#include "CameraPathMath.h"

#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "CanvasItem.h"
#include "CanvasTypes.h"
#include "Components/InputComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformFileManager.h"
#include "HighResScreenshot.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/DateTime.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashPhoto, Log, All);

namespace
{
// The engine-independent camera math is shared with the cinematic intro and the standalone
// test, so the leash a visitor feels here is provably the same clamp the tests cover.
FVector ToVec(const MikdashCamera::Vec3& V) { return FVector(V.X, V.Y, V.Z); }
MikdashCamera::Vec3 ToMath(const FVector& V) { return MikdashCamera::Vec3{V.X, V.Y, V.Z}; }

/** Held-key helper that works while the world is paused. */
bool KeyDown(const APlayerController* PC, const FKey& Key)
{
    return PC && PC->PlayerInput && PC->IsInputKeyDown(Key);
}
} // namespace

// =====================================================================================
// AMikdashPhotoCamera
// =====================================================================================

AMikdashPhotoCamera::AMikdashPhotoCamera()
{
    PrimaryActorTick.bCanEverTick = true;
    // The whole point of photo mode is that the world is stopped, so this actor has to be
    // one of the very few things that still ticks.
    PrimaryActorTick.bTickEvenWhenPaused = true;
    SetActorTickEnabled(true);

    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("PhotoCamera"));
    SetRootComponent(Camera);
    Camera->bConstrainAspectRatio = false;
    Camera->PostProcessBlendWeight = 1.0f;
}

void AMikdashPhotoCamera::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (PhotoOwner)
    {
        PhotoOwner->ApplyToCamera(DeltaSeconds);
    }
}

void AMikdashPhotoCamera::PostRenderFor(APlayerController* PC, UCanvas* Canvas, FVector CameraPosition, FVector CameraDir)
{
    Super::PostRenderFor(PC, Canvas, CameraPosition, CameraDir);
    if (!PhotoOwner || !Canvas || !PhotoOwner->IsActive())
    {
        return;
    }

    const FMikdashPhotoSettings S = PhotoOwner->GetSettings();
    const float W = static_cast<float>(Canvas->SizeX);
    const float H = static_cast<float>(Canvas->SizeY);
    if (W <= 1.0f || H <= 1.0f)
    {
        return;
    }

    const FLinearColor GuideColour(1.0f, 1.0f, 1.0f, 0.35f);
    const FLinearColor BarColour(0.0f, 0.0f, 0.0f, 1.0f);

    // ---- frame border ---------------------------------------------------------------
    // Drawn first so the guides sit on top of the bars rather than under them.
    auto DrawBars = [&](float TargetAspect)
    {
        const float Aspect = W / H;
        if (TargetAspect > Aspect)
        {
            // Wider than the screen: bars top and bottom.
            const float Keep = W / TargetAspect;
            const float Bar = FMath::Max(0.0f, (H - Keep) * 0.5f);
            if (Bar > 0.5f)
            {
                FCanvasTileItem Top(FVector2D(0.0f, 0.0f), FVector2D(W, Bar), BarColour);
                Top.BlendMode = SE_BLEND_Opaque;
                Canvas->DrawItem(Top);
                FCanvasTileItem Bottom(FVector2D(0.0f, H - Bar), FVector2D(W, Bar), BarColour);
                Bottom.BlendMode = SE_BLEND_Opaque;
                Canvas->DrawItem(Bottom);
            }
        }
        else
        {
            // Taller than the screen: bars left and right.
            const float Keep = H * TargetAspect;
            const float Bar = FMath::Max(0.0f, (W - Keep) * 0.5f);
            if (Bar > 0.5f)
            {
                FCanvasTileItem Left(FVector2D(0.0f, 0.0f), FVector2D(Bar, H), BarColour);
                Left.BlendMode = SE_BLEND_Opaque;
                Canvas->DrawItem(Left);
                FCanvasTileItem Right(FVector2D(W - Bar, 0.0f), FVector2D(Bar, H), BarColour);
                Right.BlendMode = SE_BLEND_Opaque;
                Canvas->DrawItem(Right);
            }
        }
    };

    switch (S.Border)
    {
    case EMikdashPhotoBorder::Hairline:
    {
        const float Inset = FMath::Max(2.0f, FMath::Min(W, H) * 0.02f);
        Canvas->K2_DrawBox(FVector2D(Inset, Inset), FVector2D(W - 2.0f * Inset, H - 2.0f * Inset),
                           FMath::Max(1.0f, H / 540.0f), FLinearColor(1.0f, 1.0f, 1.0f, 0.85f));
        break;
    }
    case EMikdashPhotoBorder::Cinemascope: DrawBars(2.39f); break;
    case EMikdashPhotoBorder::Widescreen:  DrawBars(1.85f); break;
    case EMikdashPhotoBorder::Square:      DrawBars(1.0f);  break;
    case EMikdashPhotoBorder::Portrait:    DrawBars(0.8f);  break;
    case EMikdashPhotoBorder::None:
    default: break;
    }

    // ---- rule of thirds -------------------------------------------------------------
    if (S.bShowThirds)
    {
        const float Thickness = FMath::Max(1.0f, H / 900.0f);
        for (int32 I = 1; I <= 2; ++I)
        {
            const float X = W * (static_cast<float>(I) / 3.0f);
            const float Y = H * (static_cast<float>(I) / 3.0f);
            Canvas->K2_DrawLine(FVector2D(X, 0.0f), FVector2D(X, H), Thickness, GuideColour);
            Canvas->K2_DrawLine(FVector2D(0.0f, Y), FVector2D(W, Y), Thickness, GuideColour);
        }
    }

    // ---- horizon guide --------------------------------------------------------------
    // A level line through the centre plus the camera's own roll, so a tilted horizon is
    // deliberate rather than accidental. Green when level, amber when not.
    if (S.bShowHorizon)
    {
        const float Roll = PhotoOwner->GetSettings().RollDegrees;
        const float Radians = FMath::DegreesToRadians(Roll);
        const float Half = FMath::Sqrt(W * W + H * H) * 0.5f;
        const FVector2D Centre(W * 0.5f, H * 0.5f);
        const FVector2D Along(FMath::Cos(Radians), FMath::Sin(Radians));
        const bool bLevel = FMath::Abs(Roll) < 0.25f;
        const FLinearColor HorizonColour = bLevel ? FLinearColor(0.35f, 1.0f, 0.45f, 0.6f)
                                                  : FLinearColor(1.0f, 0.72f, 0.25f, 0.6f);
        Canvas->K2_DrawLine(Centre - Along * Half, Centre + Along * Half, FMath::Max(1.0f, H / 720.0f), HorizonColour);
        // A short true-level tick so the tilt is readable against something.
        Canvas->K2_DrawLine(FVector2D(Centre.X - W * 0.08f, Centre.Y), FVector2D(Centre.X + W * 0.08f, Centre.Y),
                            FMath::Max(1.0f, H / 1080.0f), FLinearColor(1.0f, 1.0f, 1.0f, 0.25f));
    }

    UFont* Font = GEngine ? GEngine->GetMediumFont() : nullptr;

    // ---- watermark ------------------------------------------------------------------
    // Deliberately drawn on the HUD canvas, not in Slate, so it survives into the
    // high-resolution PNG. See the header for why that distinction matters.
    if (S.bWatermark && Font)
    {
        const FString Text = PhotoOwner->GetWatermarkText();
        if (!Text.IsEmpty())
        {
            const float Margin = FMath::Max(8.0f, H * 0.035f);
            Canvas->K2_DrawText(Font, Text, FVector2D(Margin, H - Margin - 18.0f), FVector2D(1.0f, 1.0f),
                                FLinearColor(1.0f, 1.0f, 1.0f, 0.55f), 0.0f, FLinearColor(0.0f, 0.0f, 0.0f, 0.5f),
                                FVector2D(1.0f, 1.0f), false, false, false, FLinearColor::Black);
        }
    }

    // ---- settings read-out ----------------------------------------------------------
    // Suppressed while a capture is in flight, so it never lands in the photograph even
    // though it is drawn on the same canvas the capture reads.
    if (S.bShowHud && !bSuppressReadout && Font)
    {
        const float Margin = FMath::Max(8.0f, H * 0.035f);
        float Y = Margin;
        const FLinearColor Ink(1.0f, 1.0f, 1.0f, 0.85f);
        const FLinearColor Shadow(0.0f, 0.0f, 0.0f, 0.6f);
        auto Line = [&](const FString& Text)
        {
            Canvas->K2_DrawText(Font, Text, FVector2D(Margin, Y), FVector2D(1.0f, 1.0f), Ink, 0.0f, Shadow,
                                FVector2D(1.0f, 1.0f), false, false, false, FLinearColor::Black);
            Y += 20.0f;
        };
        Line(TEXT("PHOTO MODE"));
        Line(FString::Printf(TEXT("Field of view  %.0f deg      (mouse wheel)"), S.FieldOfViewDegrees));
        Line(FString::Printf(TEXT("Roll           %+.1f deg     (Z / X)"), S.RollDegrees));
        Line(FString::Printf(TEXT("Focus          %s   (bracket keys, F to focus centre)"),
                             S.FocusDistanceCm > 1.0f ? *FString::Printf(TEXT("%.0f cm"), S.FocusDistanceCm) : TEXT("auto")));
        Line(FString::Printf(TEXT("Aperture       f/%.1f        (comma / period)"), S.Aperture));
        Line(FString::Printf(TEXT("Exposure       %+.2f EV      (hyphen / equals)"), S.ExposureBias));
        Line(FString::Printf(TEXT("Grade          %s   (G)"), *PhotoOwner->GetGradeName()));
        Line(FString::Printf(TEXT("Border         %s   (B)"), *PhotoOwner->GetBorderName()));
        Line(FString::Printf(TEXT("Guides         thirds %s (T), horizon %s (Y), watermark %s (N)"),
                             S.bShowThirds ? TEXT("on") : TEXT("off"),
                             S.bShowHorizon ? TEXT("on") : TEXT("off"),
                             S.bWatermark ? TEXT("on") : TEXT("off")));
        Line(FString::Printf(TEXT("Leash          %.0f%% of %.0f m used"),
                             PhotoOwner->GetLeashUsedFraction() * 100.0f, PhotoOwner->GetLeashRadiusCm() / 100.0f));
        Line(TEXT("F9 photograph 2x   F10 photograph 4x   R reset   H hide this   F2 leave"));
        if (!PhotoOwner->GetLastPhotoPath().IsEmpty())
        {
            Line(FString::Printf(TEXT("Saved %d: %s"), PhotoOwner->GetPhotoCount(), *PhotoOwner->GetLastPhotoPath()));
        }
    }
}

// =====================================================================================
// UMikdashPhotoMode
// =====================================================================================

void UMikdashPhotoMode::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    ResetSettings();
    // The toggle key is bound lazily: at subsystem creation there is no player controller
    // yet, so binding once here would leave F2 dead for the whole run. The ticker retries
    // until a controller exists and then removes itself.
    if (bEnabled && bOwnToggleKey)
    {
        BindTickHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateUObject(this, &UMikdashPhotoMode::TryBindToggleKey), 0.5f);
    }
}

bool UMikdashPhotoMode::TryBindToggleKey(float DeltaSeconds)
{
    (void)DeltaSeconds;
    if (ToggleInput)
    {
        BindTickHandle.Reset();
        return false;
    }
    if (APlayerController* Controller = GetOwningController())
    {
        BindKeys(Controller);
        if (ToggleInput)
        {
            UE_LOG(LogMikdashPhoto, Log, TEXT("Photo mode bound to F2."));
            BindTickHandle.Reset();
            return false;
        }
    }
    return true;
}

void UMikdashPhotoMode::Deinitialize()
{
    if (bActive)
    {
        Exit();
    }
    if (BindTickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(BindTickHandle);
        BindTickHandle.Reset();
    }
    if (APlayerController* Controller = GetOwningController())
    {
        UnbindKeys(Controller);
    }
    Super::Deinitialize();
}

UMikdashPhotoMode* UMikdashPhotoMode::Get(const UObject* WorldContext)
{
    if (const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr)
    {
        if (UGameInstance* Instance = World->GetGameInstance())
        {
            return Instance->GetSubsystem<UMikdashPhotoMode>();
        }
    }
    return nullptr;
}

APlayerController* UMikdashPhotoMode::GetOwningController() const
{
    const UGameInstance* Instance = GetGameInstance();
    return Instance ? Instance->GetFirstLocalPlayerController() : nullptr;
}

FString UMikdashPhotoMode::GetWatermarkText() const
{
    return WatermarkText;
}

// -------------------------------------------------------------------------------------
// input
// -------------------------------------------------------------------------------------

void UMikdashPhotoMode::BindKeys(APlayerController* Controller)
{
    if (!Controller || !bEnabled || !bOwnToggleKey || ToggleInput)
    {
        return;
    }
    // Not registered as a component: it has no owning actor. This is the same pattern the
    // front end uses for its pause key -- construct, bind, push, and pop on the way out.
    ToggleInput = NewObject<UInputComponent>(this, UInputComponent::StaticClass(), TEXT("MikdashPhotoToggleInput"));
    ToggleInput->Priority = InputPriority;
    // Photo mode has to be reachable while the world is paused, because the world is
    // paused for the whole time photo mode is up.
    FInputKeyBinding& Binding = ToggleInput->BindKey(EKeys::F2, IE_Pressed, this, &UMikdashPhotoMode::HandleToggleKey);
    Binding.bConsumeInput = true;
    Binding.bExecuteWhenPaused = true;
    Controller->PushInputComponent(ToggleInput);
}

void UMikdashPhotoMode::UnbindKeys(APlayerController* Controller)
{
    if (Controller && ToggleInput)
    {
        Controller->PopInputComponent(ToggleInput);
    }
    ToggleInput = nullptr;
}

void UMikdashPhotoMode::HandleToggleKey()
{
    Toggle();
}

void UMikdashPhotoMode::HandleShot2x()
{
    TakePhoto(2);
}

void UMikdashPhotoMode::HandleShot4x()
{
    TakePhoto(4);
}

// -------------------------------------------------------------------------------------
// entering and leaving
// -------------------------------------------------------------------------------------

bool UMikdashPhotoMode::Enter()
{
    LastRefusal.Reset();
    if (!bEnabled)
    {
        LastRefusal = TEXT("Photo mode is disabled in configuration.");
        return false;
    }
    if (bActive)
    {
        return true;
    }

    UWorld* World = GetWorld();
    APlayerController* Controller = GetOwningController();
    if (!World || !Controller)
    {
        LastRefusal = TEXT("No world or player controller.");
        return false;
    }
    BindKeys(Controller);

    FVector ViewLocation = FVector::ZeroVector;
    FRotator ViewRotation = FRotator::ZeroRotator;
    Controller->GetPlayerViewPoint(ViewLocation, ViewRotation);

    // Where the visitor was standing is the anchor of the leash: they can fly around
    // freely but cannot take the camera out of the level and photograph the void.
    LeashAnchor = Controller->GetPawn() ? Controller->GetPawn()->GetActorLocation() : ViewLocation;

    FActorSpawnParameters Params;
    Params.Owner = Controller;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    PhotoCamera = World->SpawnActor<AMikdashPhotoCamera>(AMikdashPhotoCamera::StaticClass(), ViewLocation, ViewRotation, Params);
    if (!PhotoCamera)
    {
        LastRefusal = TEXT("Could not spawn the photo camera.");
        return false;
    }
    PhotoCamera->PhotoOwner = this;

    Settings.RollDegrees = 0.0f;
    CurrentRollDegrees = 0.0f;
    Settings.FieldOfViewDegrees = Controller->PlayerCameraManager ? Controller->PlayerCameraManager->GetFOVAngle() : 70.0f;
    Settings.FieldOfViewDegrees = FMath::Clamp(Settings.FieldOfViewDegrees, MinFieldOfViewDegrees, MaxFieldOfViewDegrees);

    PreviousViewTarget = Controller->GetViewTarget();
    Controller->SetViewTargetWithBlend(PhotoCamera, 0.25f);

    // Freeze the world. The camera actor ticks even when paused, and the controller is
    // told to keep ticking so its PlayerInput still updates and the keys below respond.
    bWasPaused = UGameplayStatics::IsGamePaused(World);
    if (!bWasPaused)
    {
        UGameplayStatics::SetGamePaused(World, true);
    }
    bRestoreFullTickWhenPaused = Controller->PrimaryActorTick.bTickEvenWhenPaused;
    Controller->PrimaryActorTick.bTickEvenWhenPaused = true;

    // Photo mode's own input, pushed on top so movement keys mean camera movement here
    // without disturbing anything the walkthrough has bound.
    PhotoInput = NewObject<UInputComponent>(this, UInputComponent::StaticClass(), TEXT("MikdashPhotoInput"));
    PhotoInput->Priority = InputPriority + 1;
    auto Bind = [this](const FKey& Key, void (UMikdashPhotoMode::*Fn)())
    {
        FInputKeyBinding& B = PhotoInput->BindKey(Key, IE_Pressed, this, Fn);
        B.bConsumeInput = true;
        B.bExecuteWhenPaused = true;
    };
    Bind(EKeys::F9, &UMikdashPhotoMode::HandleShot2x);
    Bind(EKeys::F10, &UMikdashPhotoMode::HandleShot4x);
    Bind(EKeys::G, &UMikdashPhotoMode::CycleGradeForward);
    Bind(EKeys::B, &UMikdashPhotoMode::CycleBorderForward);
    Bind(EKeys::H, &UMikdashPhotoMode::ToggleHud);
    Bind(EKeys::T, &UMikdashPhotoMode::ToggleThirds);
    Bind(EKeys::Y, &UMikdashPhotoMode::ToggleHorizon);
    Bind(EKeys::N, &UMikdashPhotoMode::ToggleWatermark);
    Bind(EKeys::R, &UMikdashPhotoMode::ResetSettings);
    Bind(EKeys::F, &UMikdashPhotoMode::FocusOnCentreVoid);
    {
        FInputAxisKeyBinding& Wheel = PhotoInput->BindAxisKey(EKeys::MouseWheelAxis, this, &UMikdashPhotoMode::HandleWheel);
        Wheel.bConsumeInput = true;
        Wheel.bExecuteWhenPaused = true;
        FInputAxisKeyBinding& MX = PhotoInput->BindAxisKey(EKeys::MouseX, this, &UMikdashPhotoMode::HandleLookX);
        MX.bConsumeInput = true;
        MX.bExecuteWhenPaused = true;
        FInputAxisKeyBinding& MY = PhotoInput->BindAxisKey(EKeys::MouseY, this, &UMikdashPhotoMode::HandleLookY);
        MY.bConsumeInput = true;
        MY.bExecuteWhenPaused = true;
    }
    Controller->PushInputComponent(PhotoInput);

    RegisterOverlay(Controller);

    bActive = true;
    QuietFramesLeft = 0;
    UE_LOG(LogMikdashPhoto, Log, TEXT("Photo mode entered at %s, leash %.0f cm."), *ViewLocation.ToString(), LeashRadiusCm);
    return true;
}

void UMikdashPhotoMode::Exit()
{
    if (!bActive)
    {
        return;
    }
    bActive = false;

    UWorld* World = GetWorld();
    APlayerController* Controller = GetOwningController();

    if (Controller)
    {
        UnregisterOverlay(Controller);
        if (PhotoInput)
        {
            Controller->PopInputComponent(PhotoInput);
        }
        if (AActor* Previous = PreviousViewTarget.Get())
        {
            Controller->SetViewTargetWithBlend(Previous, 0.25f);
        }
        else if (APawn* Pawn = Controller->GetPawn())
        {
            Controller->SetViewTargetWithBlend(Pawn, 0.25f);
        }
        Controller->PrimaryActorTick.bTickEvenWhenPaused = bRestoreFullTickWhenPaused;
    }
    PhotoInput = nullptr;
    PreviousViewTarget = nullptr;

    if (World && !bWasPaused)
    {
        UGameplayStatics::SetGamePaused(World, false);
    }
    if (PhotoCamera)
    {
        PhotoCamera->PhotoOwner = nullptr;
        PhotoCamera->Destroy();
        PhotoCamera = nullptr;
    }
    UE_LOG(LogMikdashPhoto, Log, TEXT("Photo mode left after %d photograph(s)."), PhotosTaken);
}

void UMikdashPhotoMode::Toggle()
{
    if (bActive)
    {
        Exit();
    }
    else
    {
        Enter();
    }
}

void UMikdashPhotoMode::RegisterOverlay(APlayerController* Controller)
{
    if (!Controller || !PhotoCamera)
    {
        return;
    }
    AHUD* Hud = Controller->GetHUD();
    if (!Hud)
    {
        // Nothing has claimed the HUD, so ask for the plain engine one. Nothing is being
        // taken away from anybody in this branch.
        Controller->ClientSetHUD(AHUD::StaticClass());
        Hud = Controller->GetHUD();
    }
    if (!Hud)
    {
        UE_LOG(LogMikdashPhoto, Warning,
               TEXT("No HUD available; guides, borders and the watermark will not be drawn."));
        return;
    }
    OverlayHud = Hud;
    bHudOverlaysWereOn = Hud->bShowOverlays != 0;
    Hud->bShowOverlays = true;
    Hud->AddPostRenderedActor(PhotoCamera);
}

void UMikdashPhotoMode::UnregisterOverlay(APlayerController* Controller)
{
    (void)Controller;
    if (AHUD* Hud = OverlayHud.Get())
    {
        if (PhotoCamera)
        {
            Hud->RemovePostRenderedActor(PhotoCamera);
        }
        Hud->bShowOverlays = bHudOverlaysWereOn;
    }
    OverlayHud = nullptr;
}

// -------------------------------------------------------------------------------------
// the leash and the per-frame update
// -------------------------------------------------------------------------------------

FVector UMikdashPhotoMode::ClampToLeash(const FVector& Proposed) const
{
    // Sphere first, then the hard box: the sphere is the leash the visitor feels, the box
    // is the guarantee that no configuration of the sphere can put the camera outside the
    // built world.
    const MikdashCamera::Vec3 Leashed =
        MikdashCamera::ClampToSphere(ToMath(Proposed), ToMath(LeashAnchor), LeashRadiusCm);
    const MikdashCamera::Box LevelBox{ToMath(BoundsMin), ToMath(BoundsMax)};
    return ToVec(MikdashCamera::ClampToBox(Leashed, LevelBox, 0.0));
}

float UMikdashPhotoMode::GetLeashUsedFraction() const
{
    if (!PhotoCamera || LeashRadiusCm <= 1.0f)
    {
        return 0.0f;
    }
    const float Distance = static_cast<float>(FVector::Dist(PhotoCamera->GetActorLocation(), LeashAnchor));
    return FMath::Clamp(Distance / LeashRadiusCm, 0.0f, 1.0f);
}

void UMikdashPhotoMode::ApplyToCamera(float DeltaSeconds)
{
    if (!bActive || !PhotoCamera || !PhotoCamera->Camera)
    {
        return;
    }
    APlayerController* Controller = GetOwningController();
    const float Dt = FMath::Clamp(DeltaSeconds, 0.0f, 0.25f);

    // ---- held keys ------------------------------------------------------------------
    FVector Move = FVector::ZeroVector;
    float RollRate = 0.0f;
    float FocusRate = 0.0f;
    float ApertureRate = 0.0f;
    float ExposureRate = 0.0f;
    float Speed = FlySpeedCmPerSecond;
    if (Controller)
    {
        if (KeyDown(Controller, EKeys::W)) Move.X += 1.0f;
        if (KeyDown(Controller, EKeys::S)) Move.X -= 1.0f;
        if (KeyDown(Controller, EKeys::D)) Move.Y += 1.0f;
        if (KeyDown(Controller, EKeys::A)) Move.Y -= 1.0f;
        if (KeyDown(Controller, EKeys::SpaceBar)) Move.Z += 1.0f;
        if (KeyDown(Controller, EKeys::LeftControl) || KeyDown(Controller, EKeys::RightControl)) Move.Z -= 1.0f;
        if (KeyDown(Controller, EKeys::LeftShift) || KeyDown(Controller, EKeys::RightShift)) Speed *= SprintMultiplier;
        if (KeyDown(Controller, EKeys::LeftAlt)) Speed *= CreepMultiplier;
        if (KeyDown(Controller, EKeys::Z)) RollRate -= 1.0f;
        if (KeyDown(Controller, EKeys::X)) RollRate += 1.0f;
        if (KeyDown(Controller, EKeys::LeftBracket)) FocusRate -= 1.0f;
        if (KeyDown(Controller, EKeys::RightBracket)) FocusRate += 1.0f;
        if (KeyDown(Controller, EKeys::Comma)) ApertureRate -= 1.0f;
        if (KeyDown(Controller, EKeys::Period)) ApertureRate += 1.0f;
        if (KeyDown(Controller, EKeys::Hyphen)) ExposureRate -= 1.0f;
        if (KeyDown(Controller, EKeys::Equals)) ExposureRate += 1.0f;
    }

    // ---- look and move --------------------------------------------------------------
    FRotator Rotation = PhotoCamera->GetActorRotation();
    Rotation.Yaw += PhotoCamera->LookYawInput * LookSensitivity;
    Rotation.Pitch = FMath::Clamp(Rotation.Pitch - PhotoCamera->LookPitchInput * LookSensitivity, -89.0f, 89.0f);
    PhotoCamera->LookYawInput = 0.0f;
    PhotoCamera->LookPitchInput = 0.0f;

    if (!Move.IsNearlyZero())
    {
        Move.Normalize();
        const FRotator YawPitch(Rotation.Pitch, Rotation.Yaw, 0.0f);
        const FVector World = FRotationMatrix(YawPitch).TransformVector(FVector(Move.X, Move.Y, 0.0f)) +
                              FVector(0.0, 0.0, Move.Z);
        const FVector Proposed = PhotoCamera->GetActorLocation() + World * (Speed * Dt);
        PhotoCamera->SetActorLocation(ClampToLeash(Proposed), false, nullptr, ETeleportType::TeleportPhysics);
    }

    // ---- dialled values -------------------------------------------------------------
    if (!FMath::IsNearlyZero(RollRate))
    {
        AdjustRoll(RollRate * 45.0f * Dt);
    }
    if (!FMath::IsNearlyZero(FocusRate))
    {
        // Proportional, so the same hold covers a useful range near and far.
        const float Base = FMath::Max(Settings.FocusDistanceCm, 100.0f);
        AdjustFocusDistance(FocusRate * Base * 1.2f * Dt);
    }
    if (!FMath::IsNearlyZero(ApertureRate))
    {
        AdjustAperture(ApertureRate * 6.0f * Dt);
    }
    if (!FMath::IsNearlyZero(ExposureRate))
    {
        AdjustExposureBias(ExposureRate * 2.0f * Dt);
    }

    // Roll is damped rather than snapped, using the same half-life damping the cinematic
    // camera uses, so a hand on the key does not produce a step per frame.
    CurrentRollDegrees = static_cast<float>(MikdashCamera::RollTowards(
        CurrentRollDegrees, Settings.RollDegrees, Dt, RollHalfLifeSeconds));
    Rotation.Roll = CurrentRollDegrees;
    PhotoCamera->SetActorRotation(Rotation);

    // ---- camera and post process ----------------------------------------------------
    PhotoCamera->Camera->SetFieldOfView(Settings.FieldOfViewDegrees);
    FPostProcessSettings Post;
    BuildPostProcess(Post);
    PhotoCamera->Camera->PostProcessSettings = Post;
    PhotoCamera->Camera->PostProcessBlendWeight = 1.0f;

    // ---- capture quiet frames -------------------------------------------------------
    if (QuietFramesLeft > 0)
    {
        --QuietFramesLeft;
        PhotoCamera->bSuppressReadout = true;
    }
    else
    {
        PhotoCamera->bSuppressReadout = false;
    }
}

void UMikdashPhotoMode::HandleLookX(float Value)
{
    if (PhotoCamera)
    {
        PhotoCamera->LookYawInput += Value;
    }
}

void UMikdashPhotoMode::HandleLookY(float Value)
{
    if (PhotoCamera)
    {
        PhotoCamera->LookPitchInput += Value;
    }
}

void UMikdashPhotoMode::HandleWheel(float Value)
{
    if (!FMath::IsNearlyZero(Value))
    {
        // Multiplicative, so a click near a long lens is a small change in degrees and a
        // click near a wide one is a large change, which is how a zoom ring feels.
        SetFieldOfView(Settings.FieldOfViewDegrees * FMath::Pow(0.92f, Value));
    }
}

// -------------------------------------------------------------------------------------
// the picture
// -------------------------------------------------------------------------------------

void UMikdashPhotoMode::SetFieldOfView(float Degrees)
{
    Settings.FieldOfViewDegrees = FMath::Clamp(Degrees, MinFieldOfViewDegrees, MaxFieldOfViewDegrees);
}

void UMikdashPhotoMode::AdjustFieldOfView(float DeltaDegrees)
{
    SetFieldOfView(Settings.FieldOfViewDegrees + DeltaDegrees);
}

void UMikdashPhotoMode::SetRoll(float Degrees)
{
    Settings.RollDegrees = FMath::Clamp(Degrees, -MaxRollDegrees, MaxRollDegrees);
}

void UMikdashPhotoMode::AdjustRoll(float DeltaDegrees)
{
    SetRoll(Settings.RollDegrees + DeltaDegrees);
}

void UMikdashPhotoMode::SetFocusDistance(float Centimetres)
{
    Settings.FocusDistanceCm = FMath::Clamp(Centimetres, 0.0f, MaxFocusDistanceCm);
}

void UMikdashPhotoMode::AdjustFocusDistance(float DeltaCentimetres)
{
    SetFocusDistance(Settings.FocusDistanceCm + DeltaCentimetres);
}

float UMikdashPhotoMode::FocusOnCentre()
{
    if (!PhotoCamera)
    {
        return Settings.FocusDistanceCm;
    }
    UWorld* World = GetWorld();
    if (!World)
    {
        return Settings.FocusDistanceCm;
    }
    const FVector Start = PhotoCamera->GetActorLocation();
    const FVector End = Start + PhotoCamera->GetActorForwardVector() * MaxFocusDistanceCm;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MikdashPhotoFocus), true);
    Query.AddIgnoredActor(PhotoCamera);
    if (World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Query))
    {
        SetFocusDistance(static_cast<float>(Hit.Distance));
    }
    return Settings.FocusDistanceCm;
}

void UMikdashPhotoMode::FocusOnCentreVoid()
{
    FocusOnCentre();
}

void UMikdashPhotoMode::SetAperture(float FStop)
{
    Settings.Aperture = FMath::Clamp(FStop, MinAperture, MaxAperture);
}

void UMikdashPhotoMode::AdjustAperture(float Stops)
{
    SetAperture(Settings.Aperture + Stops);
}

void UMikdashPhotoMode::SetExposureBias(float Stops)
{
    Settings.ExposureBias = FMath::Clamp(Stops, MinExposureBias, MaxExposureBias);
}

void UMikdashPhotoMode::AdjustExposureBias(float DeltaStops)
{
    SetExposureBias(Settings.ExposureBias + DeltaStops);
}

void UMikdashPhotoMode::SetGrade(EMikdashPhotoGrade Grade)
{
    Settings.Grade = Grade;
}

void UMikdashPhotoMode::CycleGrade(int32 Direction)
{
    const int32 Count = static_cast<int32>(EMikdashPhotoGrade::SoftDawn) + 1;
    int32 Index = static_cast<int32>(Settings.Grade) + (Direction >= 0 ? 1 : -1);
    Index = ((Index % Count) + Count) % Count;
    Settings.Grade = static_cast<EMikdashPhotoGrade>(Index);
}

void UMikdashPhotoMode::CycleGradeForward()
{
    CycleGrade(1);
}

void UMikdashPhotoMode::SetBorder(EMikdashPhotoBorder Border)
{
    Settings.Border = Border;
}

void UMikdashPhotoMode::CycleBorder(int32 Direction)
{
    const int32 Count = static_cast<int32>(EMikdashPhotoBorder::Portrait) + 1;
    int32 Index = static_cast<int32>(Settings.Border) + (Direction >= 0 ? 1 : -1);
    Index = ((Index % Count) + Count) % Count;
    Settings.Border = static_cast<EMikdashPhotoBorder>(Index);
}

void UMikdashPhotoMode::CycleBorderForward()
{
    CycleBorder(1);
}

void UMikdashPhotoMode::ToggleHud() { Settings.bShowHud = !Settings.bShowHud; }
void UMikdashPhotoMode::ToggleThirds() { Settings.bShowThirds = !Settings.bShowThirds; }
void UMikdashPhotoMode::ToggleHorizon() { Settings.bShowHorizon = !Settings.bShowHorizon; }
void UMikdashPhotoMode::ToggleWatermark() { Settings.bWatermark = !Settings.bWatermark; }

void UMikdashPhotoMode::ResetSettings()
{
    Settings = FMikdashPhotoSettings();
    Settings.FieldOfViewDegrees = FMath::Clamp(Settings.FieldOfViewDegrees, MinFieldOfViewDegrees, MaxFieldOfViewDegrees);
    Settings.Aperture = FMath::Clamp(Settings.Aperture, MinAperture, MaxAperture);
}

FString UMikdashPhotoMode::GetGradeName() const
{
    switch (Settings.Grade)
    {
    case EMikdashPhotoGrade::WarmGold:     return TEXT("warm gold");
    case EMikdashPhotoGrade::CoolStone:    return TEXT("cool stone");
    case EMikdashPhotoGrade::Sepia:        return TEXT("sepia");
    case EMikdashPhotoGrade::Monochrome:   return TEXT("monochrome");
    case EMikdashPhotoGrade::HighContrast: return TEXT("high contrast");
    case EMikdashPhotoGrade::SoftDawn:     return TEXT("soft dawn");
    case EMikdashPhotoGrade::AsShot:
    default:                               return TEXT("as shot");
    }
}

FString UMikdashPhotoMode::GetBorderName() const
{
    switch (Settings.Border)
    {
    case EMikdashPhotoBorder::Hairline:    return TEXT("hairline");
    case EMikdashPhotoBorder::Cinemascope: return TEXT("2.39:1");
    case EMikdashPhotoBorder::Widescreen:  return TEXT("1.85:1");
    case EMikdashPhotoBorder::Square:      return TEXT("1:1");
    case EMikdashPhotoBorder::Portrait:    return TEXT("4:5");
    case EMikdashPhotoBorder::None:
    default:                               return TEXT("none");
    }
}

void UMikdashPhotoMode::BuildPostProcess(FPostProcessSettings& Out) const
{
    // Depth of field. The focal distance is in centimetres like everything else here; a
    // zero means the photographer has not set one, so DOF is left alone entirely rather
    // than focused on the near plane.
    if (Settings.FocusDistanceCm > 1.0f)
    {
        Out.bOverride_DepthOfFieldFocalDistance = true;
        Out.DepthOfFieldFocalDistance = Settings.FocusDistanceCm;
        Out.bOverride_DepthOfFieldFstop = true;
        Out.DepthOfFieldFstop = Settings.Aperture;
        Out.bOverride_DepthOfFieldSensorWidth = true;
        Out.DepthOfFieldSensorWidth = 36.0f; // full frame, so the f-numbers mean what they say
    }

    Out.bOverride_AutoExposureBias = true;
    Out.AutoExposureBias = Settings.ExposureBias;

    // Colour grades: numeric only, so no material or LUT asset is needed and the whole
    // feature works in a cooked build with no extra content.
    auto Set = [&Out](const FVector4& Saturation, const FVector4& Contrast, const FVector4& Gamma,
                      const FVector4& Gain, float WhiteTemperature)
    {
        Out.bOverride_ColorSaturation = true; Out.ColorSaturation = Saturation;
        Out.bOverride_ColorContrast = true;   Out.ColorContrast = Contrast;
        Out.bOverride_ColorGamma = true;      Out.ColorGamma = Gamma;
        Out.bOverride_ColorGain = true;       Out.ColorGain = Gain;
        Out.bOverride_WhiteTemp = true;       Out.WhiteTemp = WhiteTemperature;
    };
    const FVector4 One(1.0, 1.0, 1.0, 1.0);
    switch (Settings.Grade)
    {
    case EMikdashPhotoGrade::WarmGold:
        Set(FVector4(1.06, 1.02, 0.94, 1.05), FVector4(1.05, 1.04, 1.02, 1.04),
            One, FVector4(1.06, 1.01, 0.90, 1.0), 7600.0f);
        break;
    case EMikdashPhotoGrade::CoolStone:
        Set(FVector4(0.94, 0.97, 1.05, 0.96), FVector4(1.04, 1.04, 1.06, 1.05),
            One, FVector4(0.96, 0.99, 1.07, 1.0), 5200.0f);
        break;
    case EMikdashPhotoGrade::Sepia:
        Set(FVector4(1.0, 1.0, 1.0, 0.22), FVector4(1.06, 1.05, 1.02, 1.05),
            FVector4(1.0, 0.99, 1.02, 1.0), FVector4(1.12, 1.0, 0.80, 1.0), 8000.0f);
        break;
    case EMikdashPhotoGrade::Monochrome:
        Set(FVector4(1.0, 1.0, 1.0, 0.0), FVector4(1.10, 1.10, 1.10, 1.10), One, One, 6500.0f);
        break;
    case EMikdashPhotoGrade::HighContrast:
        Set(FVector4(1.0, 1.0, 1.0, 1.08), FVector4(1.22, 1.22, 1.22, 1.22),
            FVector4(1.0, 1.0, 1.0, 0.96), One, 6500.0f);
        break;
    case EMikdashPhotoGrade::SoftDawn:
        Set(FVector4(1.0, 0.99, 1.02, 0.88), FVector4(0.92, 0.92, 0.94, 0.92),
            FVector4(1.0, 1.0, 1.0, 1.06), FVector4(1.04, 1.0, 1.02, 1.0), 7000.0f);
        Out.bOverride_FilmToe = true;
        Out.FilmToe = 0.5f;
        break;
    case EMikdashPhotoGrade::AsShot:
    default:
        break;
    }
}

// -------------------------------------------------------------------------------------
// capture
// -------------------------------------------------------------------------------------

FString UMikdashPhotoMode::ResolvePhotoDirectory() const
{
    FString Directory = PhotoDirectoryOverride;
    if (Directory.IsEmpty())
    {
        // "Next to the game": the directory the executable was launched from in a packaged
        // build, which is where a person looks for their pictures. If that is not writable
        // (an install under Program Files, say), fall back to the project's Saved folder,
        // which always is.
        Directory = FPaths::ConvertRelativePathToFull(FPaths::LaunchDir()) / TEXT("MikdashPhotos");
    }
    Directory = FPaths::ConvertRelativePathToFull(Directory);

    IPlatformFile& File = FPlatformFileManager::Get().GetPlatformFile();
    if (!File.DirectoryExists(*Directory))
    {
        File.CreateDirectoryTree(*Directory);
    }
    if (!File.DirectoryExists(*Directory))
    {
        Directory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("MikdashPhotos"));
        File.CreateDirectoryTree(*Directory);
    }
    return Directory;
}

FString UMikdashPhotoMode::BuildPhotoBaseName(int32 Multiplier) const
{
    const FDateTime Now = FDateTime::Now();
    FString MapName = TEXT("Mikdash");
    if (const UWorld* World = GetWorld())
    {
        MapName = World->GetMapName();
        MapName.RemoveFromStart(World->StreamingLevelsPrefix);
    }
    const FString Name = FString::Printf(TEXT("%s_%s_%s_%dx"),
                                         *PhotoFilePrefix,
                                         *MapName,
                                         *Now.ToString(TEXT("%Y%m%d-%H%M%S")),
                                         FMath::Max(1, Multiplier));
    return ResolvePhotoDirectory() / Name;
}

FString UMikdashPhotoMode::TakePhoto(int32 Multiplier)
{
    const int32 Scale = FMath::Clamp(Multiplier, 1, 4);

    FViewport* Viewport = (GEngine && GEngine->GameViewport) ? GEngine->GameViewport->Viewport : nullptr;
    if (!Viewport)
    {
        LastRefusal = TEXT("No game viewport to capture.");
        UE_LOG(LogMikdashPhoto, Warning, TEXT("%s"), *LastRefusal);
        return FString();
    }

    const FIntPoint Size = Viewport->GetSizeXY();
    if (Size.X <= 0 || Size.Y <= 0)
    {
        LastRefusal = TEXT("Viewport has no size.");
        return FString();
    }

    const FString Base = BuildPhotoBaseName(Scale);

    // FHighResScreenshotConfig plus FViewport::TakeHighResScreenShot is the route chosen
    // deliberately: both are plain ENGINE_API in 5.8 with no editor-only or non-shipping
    // guard, so this works in a packaged Shipping build. Setting FilenameOverride makes
    // FScreenshotRequest skip its numbered-suffix logic, so the file lands exactly here
    // with a .png extension appended.
    FHighResScreenshotConfig& Config = GetHighResScreenshotConfig();
    Config.SetHDRCapture(false);
    Config.SetForce128BitRendering(false);
    Config.SetMaskEnabled(false);
    Config.bDateTimeBasedNaming = false;
    Config.bDumpBufferVisualizationTargets = false;
    Config.ResolutionMultiplier = static_cast<float>(Scale);
    Config.SetFilename(Base);
    if (!Config.SetResolution(static_cast<uint32>(Size.X * Scale), static_cast<uint32>(Size.Y * Scale), 1.0f))
    {
        LastRefusal = FString::Printf(TEXT("%dx (%d by %d) is larger than this GPU's maximum texture."),
                                      Scale, Size.X * Scale, Size.Y * Scale);
        UE_LOG(LogMikdashPhoto, Warning, TEXT("%s"), *LastRefusal);
        return FString();
    }

    if (!Viewport->TakeHighResScreenShot())
    {
        LastRefusal = FString::Printf(TEXT("The engine refused a %dx capture at this size."), Scale);
        UE_LOG(LogMikdashPhoto, Warning, TEXT("%s"), *LastRefusal);
        return FString();
    }

    // The read-out must not be in the photograph. The capture is serviced on a later
    // viewport draw, so it is hidden for a few frames rather than for exactly one.
    QuietFramesLeft = FMath::Max(1, CaptureQuietFrames);
    if (PhotoCamera)
    {
        PhotoCamera->bSuppressReadout = true;
    }

    ++PhotosTaken;
    LastPhotoPath = Base + TEXT(".png");
    LastRefusal.Reset();
    UE_LOG(LogMikdashPhoto, Log, TEXT("Photograph %d requested at %dx (%d by %d): %s"),
           PhotosTaken, Scale, Size.X * Scale, Size.Y * Scale, *LastPhotoPath);
    return LastPhotoPath;
}
