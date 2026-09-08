#include "MikdashPlayerController.h"
// MikdashFrontEnd.cpp -- implementation of the walkthrough's front end.
//
// Written by the coordinator after the authoring agent was cut off mid-task by a
// session limit, leaving MikdashFrontEnd.h and MikdashMenuWidget.{h,cpp} complete but
// this translation unit missing. Every function declared in the header is defined here
// and the behaviour follows the header's own documented contract; where the header left
// a choice open the reasoning is in a comment at the point of the decision.

#include "MikdashFrontEnd.h"

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectGlobals.h"

#define LOCTEXT_NAMESPACE "MikdashFrontEnd"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashFrontEnd, Log, All);

namespace
{
    /** Z-orders. The loading screen sits above everything, including a menu behind it. */
    constexpr int32 ZOrderMenu    = 100;
    constexpr int32 ZOrderLoading = 200;

    /** Match an actor by editor label where labels exist, and by tag or name everywhere. */
    bool ActorMatchesLabel(const AActor* Actor, const FString& Label)
    {
        if (!Actor || Label.IsEmpty())
        {
            return false;
        }
#if WITH_EDITOR
        // Labels are editor-only data. In a packaged build the branch below is the one
        // that runs, which is why a tag is also honoured: a cooked build has no labels.
        if (Actor->GetActorLabel().Equals(Label, ESearchCase::IgnoreCase))
        {
            return true;
        }
#endif
        if (Actor->ActorHasTag(FName(*Label)))
        {
            return true;
        }
        return Actor->GetName().Equals(Label, ESearchCase::IgnoreCase);
    }
}

// ---------------------------------------------------------------------------
// lifetime
// ---------------------------------------------------------------------------

void UMikdashFrontEnd::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    if (!bEnabled)
    {
        UE_LOG(LogMikdashFrontEnd, Log, TEXT("Front end disabled by config; booting straight into the level."));
        return;
    }

    MapLoadedHandle = FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this, &UMikdashFrontEnd::OnMapLoaded);

    // A subsystem can be created after the first map is already up (late plugin load,
    // or PIE), in which case the delegate above will never fire for the current world.
    // The boot ticker covers that case and stops as soon as it has done its work.
    BootTickHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &UMikdashFrontEnd::TickBoot), 0.0f);
}

void UMikdashFrontEnd::Deinitialize()
{
    if (MapLoadedHandle.IsValid())
    {
        FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(MapLoadedHandle);
        MapLoadedHandle.Reset();
    }

    for (FTSTicker::FDelegateHandle* Handle : { &BootTickHandle, &CameraTickHandle, &LoadingTickHandle })
    {
        if (Handle->IsValid())
        {
            FTSTicker::GetCoreTicker().RemoveTicker(*Handle);
            Handle->Reset();
        }
    }

    ReleasePauseKey();
    StopMenuCamera();
    TearDownScreens();

    GuidedTour.Unbind();

    Super::Deinitialize();
}

UMikdashFrontEnd* UMikdashFrontEnd::Get(const UObject* WorldContext)
{
    if (!WorldContext)
    {
        return nullptr;
    }
    const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
    UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
    return GameInstance ? GameInstance->GetSubsystem<UMikdashFrontEnd>() : nullptr;
}

APlayerController* UMikdashFrontEnd::GetOwningController() const
{
    if (APlayerController* Bound = BoundController.Get())
    {
        return Bound;
    }
    const UWorld* World = GetWorld();
    return World ? UGameplayStatics::GetPlayerController(const_cast<UWorld*>(World), 0) : nullptr;
}

// ---------------------------------------------------------------------------
// boot
// ---------------------------------------------------------------------------

void UMikdashFrontEnd::OnMapLoaded(UWorld* LoadedWorld)
{
    if (!bEnabled || !LoadedWorld)
    {
        return;
    }

    RestoreMenuCameraTick();
    // Anything the previous world owned is gone with it.
    MainMenu = nullptr;
    PauseMenu = nullptr;
    SettingsScreen = nullptr;
    CreditsScreen = nullptr;
    LoadingScreen = nullptr;
    MenuCamera = nullptr;
    PreviousViewTarget = nullptr;
    bMenuCameraIsBorrowed = false;
    BoundController = nullptr;
    PauseInput = nullptr;
    Screen = EMikdashScreen::None;
    bPausedByFrontEnd = false;

    if (!BootTickHandle.IsValid())
    {
        BootTickHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateUObject(this, &UMikdashFrontEnd::TickBoot), 0.0f);
    }
}

bool UMikdashFrontEnd::TickBoot(float /*DeltaTime*/)
{
    UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld())
    {
        return true; // keep waiting
    }
    if (!UGameplayStatics::GetPlayerController(World, 0))
    {
        return true; // the controller is not up yet
    }

    BootTickHandle.Reset();

    if (bShowMainMenuOnBoot && !bWalkthroughStarted)
    {
        ShowMainMenu();
    }
    else
    {
        // No title screen wanted, but the pause key still has to work.
        EnsurePauseKeyBound(UGameplayStatics::GetPlayerController(World, 0));
    }
    return false; // done
}

// ---------------------------------------------------------------------------
// screens
// ---------------------------------------------------------------------------

template <typename WidgetType>
WidgetType* UMikdashFrontEnd::MakeScreen(TObjectPtr<WidgetType>& Slot, int32 ZOrder)
{
    if (Slot)
    {
        Slot->Rebuild(); // Re-evaluate dove/mute labels and refusal status on each opening.
        if (!Slot->IsInViewport())
        {
            Slot->AddToViewport(ZOrder);
        }
        return Slot;
    }

    UGameInstance* GameInstance = GetGameInstance();
    if (!GameInstance)
    {
        return nullptr;
    }

    WidgetType* Widget = CreateWidget<WidgetType>(GameInstance, WidgetType::StaticClass());
    if (!Widget)
    {
        UE_LOG(LogMikdashFrontEnd, Warning, TEXT("Could not create front-end widget %s."), *WidgetType::StaticClass()->GetName());
        return nullptr;
    }

    // The widget navigates by calling back into this subsystem, so this must be set
    // before it is constructed: NativeConstruct builds the body and reads FrontEnd.
    Widget->FrontEnd = this;
    Widget->Rebuild();
    Widget->AddToViewport(ZOrder);
    Slot = Widget;
    return Widget;
}

void UMikdashFrontEnd::TearDownScreens()
{
    auto Drop = [](UUserWidget* Widget)
    {
        if (Widget && Widget->IsInViewport())
        {
            Widget->RemoveFromParent();
        }
    };
    Drop(MainMenu);
    Drop(PauseMenu);
    Drop(SettingsScreen);
    Drop(CreditsScreen);
    Drop(LoadingScreen);

    MainMenu = nullptr;
    PauseMenu = nullptr;
    SettingsScreen = nullptr;
    CreditsScreen = nullptr;
    LoadingScreen = nullptr;
}

void UMikdashFrontEnd::SetScreen(EMikdashScreen NewScreen)
{
    if (Screen == NewScreen)
    {
        return;
    }

    // Drop the screens that are not the new one. The loading screen is deliberately
    // left alone here: it is layered above whatever else is up and is retired only by
    // HideLoadingScreen, so a menu can be built behind it while it is still covering.
    auto DropIfNot = [NewScreen](UUserWidget* Widget, EMikdashScreen Owns)
    {
        if (Widget && Owns != NewScreen && Widget->IsInViewport())
        {
            Widget->RemoveFromParent();
        }
    };
    DropIfNot(MainMenu, EMikdashScreen::MainMenu);
    DropIfNot(PauseMenu, EMikdashScreen::PauseMenu);
    DropIfNot(SettingsScreen, EMikdashScreen::Settings);
    DropIfNot(CreditsScreen, EMikdashScreen::Credits);

    Screen = NewScreen;
    const bool bIsVisible = Screen != EMikdashScreen::None;

    ApplyMenuInputMode(bIsVisible);

    OnScreenChanged.Broadcast(Screen);
}

void UMikdashFrontEnd::ShowMainMenu()
{
    if (!bEnabled)
    {
        return;
    }
    MakeScreen(MainMenu, ZOrderMenu);
    SetScreen(EMikdashScreen::MainMenu);
    ReturnScreen = EMikdashScreen::MainMenu;

    StartMenuCamera();
    EnsurePauseKeyBound(GetOwningController());
}

void UMikdashFrontEnd::BeginWalkthrough()
{
    // Hold the loading screen briefly so the hand-over from the title camera to the
    // visitor's own view is covered rather than snapping.
    if (BeginWalkthroughLoadingSeconds > 0.0f)
    {
        bPendingBeginAfterLoading = true;
        ShowLoadingScreen(BeginWalkthroughLoadingSeconds);
        return;
    }

    bPendingBeginAfterLoading = false;
    StopMenuCamera();
    SetScreen(EMikdashScreen::None);

    if (!bWalkthroughStarted)
    {
        bWalkthroughStarted = true;
        OnWalkthroughStarted.Broadcast();
    }
    EnsurePauseKeyBound(GetOwningController());
}

void UMikdashFrontEnd::RequestGuidedTour()
{
    if (!IsGuidedTourAvailable())
    {
        UE_LOG(LogMikdashFrontEnd, Log, TEXT("Guided tour requested with nothing bound; ignoring."));
        return;
    }

    // Leave the front end first so the tour owns the screen from its first frame.
    StopMenuCamera();
    SetScreen(EMikdashScreen::None);
    if (!bWalkthroughStarted)
    {
        bWalkthroughStarted = true;
        OnWalkthroughStarted.Broadcast();
    }
    EnsurePauseKeyBound(GetOwningController());

    GuidedTour.ExecuteIfBound();
    OnGuidedTourRequested.Broadcast();
}

void UMikdashFrontEnd::ShowPreparationLesson()
{
    if (!bEnabled) return;
    if (AMikdashPlayerController* Controller = Cast<AMikdashPlayerController>(GetOwningController()))
    {
        SetScreen(EMikdashScreen::Preparation);
        Controller->ShowPreparationLesson();
    }
}

void UMikdashFrontEnd::ShowSettings()
{
    ReturnScreen = (Screen == EMikdashScreen::PauseMenu) ? EMikdashScreen::PauseMenu : EMikdashScreen::MainMenu;
    MakeScreen(SettingsScreen, ZOrderMenu);
    SetScreen(EMikdashScreen::Settings);
}

void UMikdashFrontEnd::ShowCredits()
{
    ReturnScreen = (Screen == EMikdashScreen::PauseMenu) ? EMikdashScreen::PauseMenu : EMikdashScreen::MainMenu;
    MakeScreen(CreditsScreen, ZOrderMenu);
    SetScreen(EMikdashScreen::Credits);
}

void UMikdashFrontEnd::ShowPauseMenu()
{
    if (!bEnabled || Screen == EMikdashScreen::MainMenu)
    {
        return; // the title screen is not something to pause over
    }

    MakeScreen(PauseMenu, ZOrderMenu);
    SetScreen(EMikdashScreen::PauseMenu);
    ReturnScreen = EMikdashScreen::PauseMenu;

    if (bPauseWorld && !bPausedByFrontEnd)
    {
        if (UWorld* World = GetWorld())
        {
            bPausedByFrontEnd = UGameplayStatics::SetGamePaused(World, true);
        }
    }
}

void UMikdashFrontEnd::ResumeWalkthrough()
{
    // This API also explicitly starts a walk from the title screen, including probes.
    bPendingBeginAfterLoading = false;
    if (LoadingTickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(LoadingTickHandle);
        LoadingTickHandle.Reset();
    }
    if (LoadingScreen) LoadingScreen->RemoveFromParent();
    StopMenuCamera();
    if (!bWalkthroughStarted)
    {
        bWalkthroughStarted = true;
        OnWalkthroughStarted.Broadcast();
    }

    if (bPausedByFrontEnd)
    {
        if (UWorld* World = GetWorld())
        {
            UGameplayStatics::SetGamePaused(World, false);
        }
        bPausedByFrontEnd = false;
    }
    SetScreen(EMikdashScreen::None);
}

void UMikdashFrontEnd::TogglePauseMenu()
{
    switch (Screen)
    {
    case EMikdashScreen::None:
        ShowPauseMenu();
        break;
    case EMikdashScreen::PauseMenu:
        ResumeWalkthrough();
        break;
    case EMikdashScreen::Settings:
    case EMikdashScreen::Credits:
        GoBack();
        break;
    default:
        // Main menu and loading screen swallow the key on purpose.
        break;
    }
}

void UMikdashFrontEnd::GoBack()
{
    switch (ReturnScreen)
    {
    case EMikdashScreen::PauseMenu:
        ShowPauseMenu();
        break;
    default:
        ShowMainMenu();
        break;
    }
}

void UMikdashFrontEnd::ReturnToMainMenu()
{
    if (bPausedByFrontEnd)
    {
        if (UWorld* World = GetWorld())
        {
            UGameplayStatics::SetGamePaused(World, false);
        }
        bPausedByFrontEnd = false;
    }

    bWalkthroughStarted = false;

    // Default is to redraw the title over the level that is already loaded, which keeps
    // every placed actor and the lighting exactly as they are. Travelling is opt-in
    // because this project's map is large and reloading it is slow.
    if (!MainMenuMap.IsEmpty())
    {
        if (UWorld* World = GetWorld())
        {
            TearDownScreens();
            Screen = EMikdashScreen::None;
            UGameplayStatics::OpenLevel(World, FName(*MainMenuMap));
            return;
        }
    }

    ShowMainMenu();
}

void UMikdashFrontEnd::QuitToDesktop()
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }
    if (bPausedByFrontEnd)
    {
        UGameplayStatics::SetGamePaused(World, false);
        bPausedByFrontEnd = false;
    }
    UKismetSystemLibrary::QuitGame(World, GetOwningController(), EQuitPreference::Quit, false);
}

// ---------------------------------------------------------------------------
// loading screen
// ---------------------------------------------------------------------------

void UMikdashFrontEnd::ShowLoadingScreen(float MinimumSeconds)
{
    UMikdashLoadingScreenWidget* Widget = MakeScreen(LoadingScreen, ZOrderLoading);
    if (!Widget)
    {
        // Without a widget there is nothing to hold, so do not strand the caller
        // behind a loading screen that does not exist.
        if (bPendingBeginAfterLoading)
        {
            bPendingBeginAfterLoading = false;
            BeginWalkthroughLoadingSeconds = 0.0f;
            BeginWalkthrough();
        }
        return;
    }

    Widget->Lines = BuildLoadingLines();
    Widget->SecondsPerLine = LoadingLineSeconds;
    Widget->StillImage = Cast<UTexture2D>(LoadingStillImage.TryLoad());

    LoadingHideAfterSeconds = FPlatformTime::Seconds() + FMath::Max(0.0f, MinimumSeconds);
    SetScreen(EMikdashScreen::Loading);

    if (!LoadingTickHandle.IsValid())
    {
        LoadingTickHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateUObject(this, &UMikdashFrontEnd::TickLoading), 0.0f);
    }
}

bool UMikdashFrontEnd::TickLoading(float /*DeltaTime*/)
{
    if (Screen != EMikdashScreen::Loading)
    {
        LoadingTickHandle.Reset();
        return false;
    }
    if (FPlatformTime::Seconds() < LoadingHideAfterSeconds)
    {
        return true;
    }

    LoadingTickHandle.Reset();
    HideLoadingScreen();
    return false;
}

void UMikdashFrontEnd::HideLoadingScreen()
{
    if (LoadingScreen && LoadingScreen->IsInViewport())
    {
        LoadingScreen->RemoveFromParent();
    }

    if (bPendingBeginAfterLoading)
    {
        bPendingBeginAfterLoading = false;

        // Enter the walkthrough directly rather than re-entering BeginWalkthrough,
        // which would show the loading screen again.
        StopMenuCamera();
        SetScreen(EMikdashScreen::None);
        if (!bWalkthroughStarted)
        {
            bWalkthroughStarted = true;
            OnWalkthroughStarted.Broadcast();
        }
        EnsurePauseKeyBound(GetOwningController());
        return;
    }

    if (Screen == EMikdashScreen::Loading)
    {
        SetScreen(EMikdashScreen::None);
    }
}

// ---------------------------------------------------------------------------
// guided tour
// ---------------------------------------------------------------------------

void UMikdashFrontEnd::RegisterGuidedTour(const FMikdashGuidedTourRequest& Delegate, const FText& Label)
{
    if (GuidedTour.IsBound())
    {
        // Logged rather than silently replaced: two tours competing for one entry is a
        // wiring mistake somebody needs to see.
        UE_LOG(LogMikdashFrontEnd, Warning, TEXT("A guided tour was already registered; replacing it."));
    }
    GuidedTour = Delegate;
    if (!Label.IsEmpty())
    {
        GuidedTourLabel = Label;
    }
    if (MainMenu)
    {
        MainMenu->Rebuild();
    }
}

void UMikdashFrontEnd::UnregisterGuidedTour()
{
    GuidedTour.Unbind();
    if (MainMenu)
    {
        MainMenu->Rebuild();
    }
}

void UMikdashFrontEnd::SetGuidedTourLabel(const FText& Label)
{
    GuidedTourLabel = Label;
    if (MainMenu)
    {
        MainMenu->Rebuild();
    }
}

bool UMikdashFrontEnd::IsGuidedTourAvailable() const
{
    return GuidedTour.IsBound() || OnGuidedTourRequested.IsBound();
}

FText UMikdashFrontEnd::GetGuidedTourLabel() const
{
    return GuidedTourLabel.IsEmpty() ? LOCTEXT("GuidedTour", "Guided tour") : GuidedTourLabel;
}

FText UMikdashFrontEnd::GetGuidedTourUnavailableReason() const
{
    return LOCTEXT("GuidedTourUnavailable", "The guided tour is not in this build yet.");
}

// ---------------------------------------------------------------------------
// input and view
// ---------------------------------------------------------------------------

void UMikdashFrontEnd::EnsurePauseKeyBound(APlayerController* Controller)
{
    if (!bOwnPauseKey || !Controller || Cast<AMikdashPlayerController>(Controller))
    {
        return;
    }
    if (BoundController.Get() == Controller && PauseInput)
    {
        return;
    }

    ReleasePauseKey();

    PauseInput = NewObject<UInputComponent>(this, UInputComponent::StaticClass(), TEXT("MikdashFrontEndPauseInput"));
    PauseInput->Priority = PauseInputPriority;
    // Consumed so a pause handler another system has on the same key does not also fire.
    PauseInput->BindKey(EKeys::Escape, IE_Pressed, this, &UMikdashFrontEnd::HandlePauseKey).bConsumeInput = true;

    Controller->PushInputComponent(PauseInput);
    BoundController = Controller;
}

void UMikdashFrontEnd::ReleasePauseKey()
{
    if (APlayerController* Controller = BoundController.Get())
    {
        if (PauseInput)
        {
            Controller->PopInputComponent(PauseInput);
        }
    }
    PauseInput = nullptr;
    BoundController = nullptr;
}

void UMikdashFrontEnd::HandlePauseKey()
{
    TogglePauseMenu();
}

void UMikdashFrontEnd::ApplyMenuInputMode(bool bMenuUp)
{
    APlayerController* Controller = GetOwningController();
    if (!Controller)
    {
        return;
    }

    if (AMikdashPlayerController* WalkController = Cast<AMikdashPlayerController>(Controller))
        WalkController->SynchronizeFrontEndMenu(bMenuUp);

    if (bMenuUp)
    {
        FInputModeGameAndUI Mode;
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        Controller->SetInputMode(Mode);
        Controller->bShowMouseCursor = true;
    }
    else
    {
        Controller->SetInputMode(FInputModeGameOnly());
        Controller->bShowMouseCursor = false;
    }
}

ACameraActor* UMikdashFrontEnd::FindLabelledMenuCamera(UWorld* World) const
{
    if (!World || MenuCameraActorLabel.IsEmpty())
    {
        return nullptr;
    }
    for (TActorIterator<ACameraActor> It(World); It; ++It)
    {
        if (ActorMatchesLabel(*It, MenuCameraActorLabel))
        {
            return *It;
        }
    }
    return nullptr;
}

void UMikdashFrontEnd::StartMenuCamera()
{
    UWorld* World = GetWorld();
    APlayerController* Controller = GetOwningController();
    if (!World || !Controller)
    {
        return; // no game world: the title screen draws on its own ground
    }
    if (MenuCamera)
    {
        return;
    }

    if (!PreviousViewTarget.IsValid())
    {
        PreviousViewTarget = Controller->GetViewTarget();
    }

    if (ACameraActor* Existing = FindLabelledMenuCamera(World))
    {
        MenuCamera = Existing;
        bMenuCameraIsBorrowed = true;
    }
    else
    {
        FActorSpawnParameters Params;
        Params.ObjectFlags |= RF_Transient; // never saved into the level
        MenuCameraYaw = MenuCameraStartYaw;
        const FVector Location(
            MenuCameraFocus.X + MenuCameraRadiusCm * FMath::Cos(FMath::DegreesToRadians(MenuCameraYaw)),
            MenuCameraFocus.Y + MenuCameraRadiusCm * FMath::Sin(FMath::DegreesToRadians(MenuCameraYaw)),
            MenuCameraFocus.Z + MenuCameraHeightCm);
        const FRotator Rotation = FRotationMatrix::MakeFromX(MenuCameraFocus - Location).Rotator();

        MenuCamera = World->SpawnActor<ACameraActor>(Location, Rotation, Params);
        bMenuCameraIsBorrowed = false;

        if (MenuCamera)
        {
            if (UCameraComponent* Camera = MenuCamera->GetCameraComponent())
            {
                Camera->SetFieldOfView(MenuCameraFov);
            }
            // Only a camera we spawned orbits. A camera placed in the level is where
            // an artist put it, so it is left exactly as authored.
            if (!CameraTickHandle.IsValid())
            {
                CameraTickHandle = FTSTicker::GetCoreTicker().AddTicker(
                    FTickerDelegate::CreateUObject(this, &UMikdashFrontEnd::TickMenuCamera), 0.0f);
            }
        }
    }

    if (MenuCamera)
    {
        MenuTickController = Controller;
        bPreviousFullTickWhenPaused = Controller->bShouldPerformFullTickWhenPaused;
        Controller->bShouldPerformFullTickWhenPaused = true;
        Controller->SetViewTargetWithBlend(MenuCamera, MenuCameraBlendSeconds);
    }
}

bool UMikdashFrontEnd::TickMenuCamera(float DeltaTime)
{
    if (!MenuCamera || bMenuCameraIsBorrowed || Screen == EMikdashScreen::None)
    {
        CameraTickHandle.Reset();
        return false;
    }

    MenuCameraYaw = FMath::Fmod(MenuCameraYaw + MenuCameraDegreesPerSecond * DeltaTime, 360.0f);
    const FVector Location(
        MenuCameraFocus.X + MenuCameraRadiusCm * FMath::Cos(FMath::DegreesToRadians(MenuCameraYaw)),
        MenuCameraFocus.Y + MenuCameraRadiusCm * FMath::Sin(FMath::DegreesToRadians(MenuCameraYaw)),
        MenuCameraFocus.Z + MenuCameraHeightCm);

    MenuCamera->SetActorLocation(Location);
    MenuCamera->SetActorRotation(FRotationMatrix::MakeFromX(MenuCameraFocus - Location).Rotator());
    return true;
}

void UMikdashFrontEnd::RestoreMenuCameraTick()
{
    if (APlayerController* Controller = MenuTickController.Get())
        Controller->bShouldPerformFullTickWhenPaused = bPreviousFullTickWhenPaused;
    MenuTickController.Reset();
}

void UMikdashFrontEnd::StopMenuCamera()
{
    RestoreMenuCameraTick();
    if (CameraTickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(CameraTickHandle);
        CameraTickHandle.Reset();
    }

    if (APlayerController* Controller = GetOwningController())
    {
        if (AActor* Previous = PreviousViewTarget.Get())
        {
            Controller->SetViewTargetWithBlend(Previous, MenuCameraBlendSeconds);
        }
        else
        {
            // The visitor's own pawn is the right thing to fall back to.
            if (APawn* Pawn = Controller->GetPawn())
            {
                Controller->SetViewTargetWithBlend(Pawn, MenuCameraBlendSeconds);
            }
        }
    }
    PreviousViewTarget = nullptr;

    if (MenuCamera && !bMenuCameraIsBorrowed)
    {
        MenuCamera->Destroy();
    }
    MenuCamera = nullptr;
    bMenuCameraIsBorrowed = false;
}

// ---------------------------------------------------------------------------
// content
// ---------------------------------------------------------------------------

FText UMikdashFrontEnd::GetTitle() const
{
    return TitleOverride.IsEmpty()
        ? LOCTEXT("Title", "The Third Beis HaMikdash")
        : FText::FromString(TitleOverride);
}

FText UMikdashFrontEnd::GetSubtitle() const
{
    return SubtitleOverride.IsEmpty()
        ? LOCTEXT("Subtitle", "A measured reconstruction from the sources, in modern Jerusalem")
        : FText::FromString(SubtitleOverride);
}

TArray<FText> UMikdashFrontEnd::BuildLoadingLines() const
{
    TArray<FText> Lines;
    Lines.Add(LOCTEXT("Loading1", "The measurements come from Yechezkel, read through the commentaries."));
    Lines.Add(LOCTEXT("Loading2", "Where the sources disagree, the codex says so rather than choosing quietly."));
    Lines.Add(LOCTEXT("Loading3", "The menorah was matched against a photograph of the Temple Institute's own."));
    Lines.Add(LOCTEXT("Loading4", "The Kotel here is built of individual ashlar blocks, course by course."));
    Lines.Add(LOCTEXT("Loading5", "A kohen may not enter the Heikhal except in the midst of service."));
    Lines.Add(LOCTEXT("Loading6", "The Kodesh HaKodashim is entered once a year, and by one man."));
    Lines.Add(LOCTEXT("Loading7", "Shoes are removed on the Mount. That rule is older than the building."));

    for (const FString& Extra : ExtraLoadingLines)
    {
        if (!Extra.IsEmpty())
        {
            Lines.Add(FText::FromString(Extra));
        }
    }
    return Lines;
}

TArray<FMikdashCreditsSection> UMikdashFrontEnd::BuildCredits() const
{
    TArray<FMikdashCreditsSection> Sections;

    {
        FMikdashCreditsSection& Sources = Sections.AddDefaulted_GetRef();
        Sources.Heading = LOCTEXT("CreditsSources", "Sources");
        Sources.Lines.Add(LOCTEXT("CreditsBook", "Lishchno Tidreshu, the author's own work, is the primary measured source."));
        Sources.Lines.Add(LOCTEXT("CreditsTanach", "Yechezkel 40 to 48, with Mishnah Middot and Rambam's Hilchot Beit HaBechirah."));
    }

    {
        FMikdashCreditsSection& Art = Sections.AddDefaulted_GetRef();
        Art.Heading = LOCTEXT("CreditsArt", "Reference and artwork");
        Art.Lines.Add(LOCTEXT("CreditsTI", "Photographs of the vessels are used by the personal permission of the owners of Machon HaMikdash, the Temple Institute."));
        Art.Lines.Add(LOCTEXT("CreditsOSM", "The modern city is built from OpenStreetMap data, (c) OpenStreetMap contributors, ODbL."));
    }

    Sections.Append(ReadThirdPartyCredits());

    {
        FMikdashCreditsSection& Built = Sections.AddDefaulted_GetRef();
        Built.Heading = LOCTEXT("CreditsBuilt", "Built with");
        Built.Lines.Add(LOCTEXT("CreditsUE", "Unreal Engine 5.8."));
    }

    return Sections;
}

TArray<FMikdashCreditsSection> UMikdashFrontEnd::ReadThirdPartyCredits() const
{
    TArray<FMikdashCreditsSection> Sections;

    const FString Folder = FPaths::Combine(FPaths::ProjectDir(), ThirdPartyFolder);
    if (!IFileManager::Get().DirectoryExists(*Folder))
    {
        // Say so rather than inventing entries: an empty attribution list that looks
        // deliberate is worse than one that admits it could not be read.
        FMikdashCreditsSection& Missing = Sections.AddDefaulted_GetRef();
        Missing.Heading = LOCTEXT("CreditsThirdParty", "Third-party assets");
        Missing.Lines.Add(FText::Format(
            LOCTEXT("CreditsThirdPartyMissing", "The attribution folder could not be read ({0}), so this list may be incomplete."),
            FText::FromString(ThirdPartyFolder)));
        return Sections;
    }

    TArray<FString> Files;
    IFileManager::Get().FindFilesRecursive(Files, *Folder, TEXT("*.json"), true, false);
    Files.Sort();

    FMikdashCreditsSection Section;
    Section.Heading = LOCTEXT("CreditsThirdParty", "Third-party assets");

    // De-duplicated on the string, not on FText: FText has no operator== and comparing
    // display text is the wrong test anyway. The same asset is often described in both
    // the manifest and its own provenance file.
    TSet<FString> Seen;

    for (const FString& File : Files)
    {
        FString Raw;
        if (!FFileHelper::LoadFileToString(Raw, *File))
        {
            continue;
        }

        TSharedPtr<FJsonObject> Root;
        const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Raw);
        if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
        {
            continue;
        }

        // Two shapes are accepted: a manifest with an "assets" array, and a single
        // per-asset provenance object. Both are already present in this project.
        auto LineFor = [](const TSharedPtr<FJsonObject>& Entry) -> FString
        {
            if (!Entry.IsValid())
            {
                return FString();
            }
            FString Name, Author, Licence;
            // Field names differ between the manifests already on disk: the top-level
            // third-party-manifest.json uses slug/licenseName, the per-asset
            // provenance.json files use title/author, and the audio manifests use
            // name/license. Missing one of these silently drops an attribution, and at
            // least one CC BY credit was found unshipped that way.
            for (const TCHAR* Key : { TEXT("name"), TEXT("title"), TEXT("asset"), TEXT("slug") })
            {
                if (Name.IsEmpty()) { Entry->TryGetStringField(Key, Name); }
            }
            for (const TCHAR* Key : { TEXT("author"), TEXT("creator"), TEXT("attribution") })
            {
                if (Author.IsEmpty()) { Entry->TryGetStringField(Key, Author); }
            }
            for (const TCHAR* Key : { TEXT("license"), TEXT("licence"), TEXT("licenseName"), TEXT("licenceName") })
            {
                if (Licence.IsEmpty()) { Entry->TryGetStringField(Key, Licence); }
            }

            if (Name.IsEmpty())
            {
                return FString();
            }
            FString Line = Name;
            if (!Author.IsEmpty()) { Line += FString::Printf(TEXT(" by %s"), *Author); }
            if (!Licence.IsEmpty()) { Line += FString::Printf(TEXT(" (%s)"), *Licence); }
            return Line;
        };

        const TArray<TSharedPtr<FJsonValue>>* Assets = nullptr;
        if (Root->TryGetArrayField(TEXT("assets"), Assets) && Assets)
        {
            for (const TSharedPtr<FJsonValue>& Value : *Assets)
            {
                const FString Line = LineFor(Value.IsValid() ? Value->AsObject() : nullptr);
                if (!Line.IsEmpty() && !Seen.Contains(Line))
                {
                    Seen.Add(Line);
                    Section.Lines.Add(FText::FromString(Line));
                }
            }
        }
        else
        {
            const FString Line = LineFor(Root);
            if (!Line.IsEmpty() && !Seen.Contains(Line))
            {
                Seen.Add(Line);
                Section.Lines.Add(FText::FromString(Line));
            }
        }
    }

    if (Section.Lines.Num() > 0)
    {
        Sections.Add(MoveTemp(Section));
    }
    return Sections;
}

#undef LOCTEXT_NAMESPACE
