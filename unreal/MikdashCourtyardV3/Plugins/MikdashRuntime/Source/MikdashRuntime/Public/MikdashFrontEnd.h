// MikdashFrontEnd.h -- the front end of the Mikdash walkthrough.
//
// Before this existed the build dropped the visitor straight into the court with no
// title, no options and no way out but Alt-F4. This subsystem owns everything that
// wraps the walkthrough: the title screen and its slow camera move over the Mikdash,
// the pause screen, the settings pages, the credits, and the loading screen.
//
// Design constraints this file is built around:
//
//  * No Content. Every widget is built in C++ (see MikdashMenuWidget.h) and no map,
//    Blueprint, texture or font asset is required for the front end to run. Optional
//    assets can be named in DefaultGame.ini and are used when present.
//
//  * No separate menu map. The title screen is drawn over the walkthrough level with
//    the player frozen and the view handed to a menu camera, so nothing about the
//    project's startup map, streaming or packaging has to change for it to work.
//
//  * It does not own the gameplay bindings. The only key it takes is the pause key,
//    and it takes that through its own pushed input component, so movement, look, the
//    talk key and everything else another system has bound keep working untouched.
//    Set bOwnPauseKey=false in config to leave even that alone.
//
//  * The guided tour is somebody else's. This exposes an entry and a delegate; if no
//    one has bound it the entry is present but disabled with a reason, rather than
//    hidden or crashing.

#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Subsystems/GameInstanceSubsystem.h"

#include "MikdashMenuWidget.h"

#include "MikdashFrontEnd.generated.h"

class ACameraActor;
class APlayerController;
class UInputComponent;
class UWorld;

/** Which screen is on top. */
UENUM(BlueprintType)
enum class EMikdashScreen : uint8
{
    None        UMETA(DisplayName = "None"),
    MainMenu    UMETA(DisplayName = "Main menu"),
    Settings    UMETA(DisplayName = "Settings"),
    Credits     UMETA(DisplayName = "Credits"),
    PauseMenu   UMETA(DisplayName = "Pause menu"),
    Preparation UMETA(DisplayName = "Preparation lesson"),
    Loading     UMETA(DisplayName = "Loading"),
};

/** Native binding point for the guided tour. Single-cast: one tour owns the entry. */
DECLARE_DELEGATE(FMikdashGuidedTourRequest);

/** Blueprint-facing equivalent. Binding either one enables the menu entry. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FMikdashGuidedTourRequestDynamic);

/** Fired when the visitor leaves the title screen and the walkthrough starts. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FMikdashWalkthroughStarted);

/** Fired whenever the top screen changes, including to None. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FMikdashScreenChanged, EMikdashScreen, Screen);

UCLASS(Config = Game, MinimalAPI)
class UMikdashFrontEnd : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    MIKDASHRUNTIME_API virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    MIKDASHRUNTIME_API virtual void Deinitialize() override;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end", meta = (WorldContext = "WorldContext"))
    static MIKDASHRUNTIME_API UMikdashFrontEnd* Get(const UObject* WorldContext);

    // -- navigation --------------------------------------------------------

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void ShowMainMenu();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void BeginWalkthrough();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void RequestGuidedTour();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void ShowSettings();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void ShowCredits();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void ShowPauseMenu();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void ResumeWalkthrough();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void TogglePauseMenu();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void ReturnToMainMenu();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void QuitToDesktop();

    /** Go back one screen: settings and credits return to whatever opened them. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void GoBack();

    /** Show the loading screen for at least this many seconds. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void ShowLoadingScreen(float MinimumSeconds);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void HideLoadingScreen();

    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end") EMikdashScreen GetScreen() const { return Screen; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end") bool IsFrontEndVisible() const { return Screen != EMikdashScreen::None; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end") bool HasWalkthroughStarted() const { return bWalkthroughStarted; }

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void ShowPreparationLesson();

    // -- guided tour -------------------------------------------------------

    /**
     * Claim the Guided tour entry.
     *
     * Label may be empty to keep the default wording. Whoever registers owns the entry
     * until they unregister; a second registration replaces the first and is logged, so
     * two tours fighting over the slot is visible rather than silent.
     */
    MIKDASHRUNTIME_API void RegisterGuidedTour(const FMikdashGuidedTourRequest& Delegate, const FText& Label = FText::GetEmpty());
    MIKDASHRUNTIME_API void UnregisterGuidedTour();

    /** Blueprint / other-module equivalent. Any binding on this also enables the entry. */
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Front end") FMikdashGuidedTourRequestDynamic OnGuidedTourRequested;

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API void SetGuidedTourLabel(const FText& Label);

    /** False when nothing is bound; the menu entry is then shown greyed with a reason. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end") MIKDASHRUNTIME_API bool IsGuidedTourAvailable() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end") MIKDASHRUNTIME_API FText GetGuidedTourLabel() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end") MIKDASHRUNTIME_API FText GetGuidedTourUnavailableReason() const;

    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Front end") FMikdashWalkthroughStarted OnWalkthroughStarted;
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Front end") FMikdashScreenChanged OnScreenChanged;

    // -- content used by the screens ---------------------------------------

    /**
     * The credits, assembled at call time.
     *
     * The fixed acknowledgements (the Temple Institute photographs, the author's own
     * book, OpenStreetMap) are constants here. The third-party model list is read from
     * SourceAssets/third-party/third-party-manifest.json and the per-asset
     * provenance.json files, so an asset that is added or removed on disk changes the
     * credits without anybody editing this file. If that folder cannot be read the
     * section says so rather than inventing entries.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API TArray<FMikdashCreditsSection> BuildCredits() const;

    /** The rotating lines shown on the loading screen. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Front end") MIKDASHRUNTIME_API TArray<FText> BuildLoadingLines() const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end") MIKDASHRUNTIME_API FText GetTitle() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Front end") MIKDASHRUNTIME_API FText GetSubtitle() const;

    /** The controller the front end is driving, or null. */
    MIKDASHRUNTIME_API APlayerController* GetOwningController() const;

    // -- configuration ([/Script/MikdashRuntime.MikdashFrontEnd] in DefaultGame.ini) --

    /** Master switch. False leaves the build booting straight into the level as before. */
    UPROPERTY(Config) bool bEnabled = true;

    /** Show the title screen when a map finishes loading. */
    UPROPERTY(Config) bool bShowMainMenuOnBoot = true;

    /**
     * Take the pause key. The only key the front end binds. It is consumed, so a pause
     * handler another system already has on the same key does not also fire; set this
     * false to leave the key entirely alone and drive the pause screen by calling
     * TogglePauseMenu() from wherever that other handler lives.
     */
    UPROPERTY(Config) bool bOwnPauseKey = true;

    /** Priority of the pushed input component. Higher wins. */
    UPROPERTY(Config) int32 PauseInputPriority = 1000;

    /** Pause the world while the pause screen is up. */
    UPROPERTY(Config) bool bPauseWorld = true;

    /**
     * Actor label of a camera in the level to use for the title-screen background.
     * When no actor with this label exists the front end spawns its own transient
     * camera and orbits it around MenuCameraFocus instead; when there is no game world
     * at all the title screen simply draws on an opaque ground.
     */
    UPROPERTY(Config) FString MenuCameraActorLabel = TEXT("MenuCamera");

    /** Centre of the fallback orbit, in world centimetres. */
    UPROPERTY(Config) FVector MenuCameraFocus = FVector(0.0, 0.0, 1600.0);
    UPROPERTY(Config) float MenuCameraRadiusCm = 14000.0f;
    UPROPERTY(Config) float MenuCameraHeightCm = 5200.0f;
    /** Degrees per second. A full turn at 1.2 is five minutes, slow enough to read over. */
    UPROPERTY(Config) float MenuCameraDegreesPerSecond = 1.2f;
    UPROPERTY(Config) float MenuCameraStartYaw = 215.0f;
    UPROPERTY(Config) float MenuCameraBlendSeconds = 1.5f;
    UPROPERTY(Config) float MenuCameraFov = 55.0f;

    /**
     * Map to travel to for "Return to main menu". Empty (the default) means do not
     * travel: the title screen is redrawn over the level that is already loaded. That
     * keeps the walkthrough's placed actors and lighting exactly as they were, at the
     * cost of not resetting the visitor's position.
     */
    UPROPERTY(Config) FString MainMenuMap;

    /** Optional still shown behind the loading text. Empty falls back to a dark ground. */
    UPROPERTY(Config) FSoftObjectPath LoadingStillImage;

    UPROPERTY(Config) float LoadingLineSeconds = 4.5f;

    /** Minimum time the loading screen is held when starting the walkthrough. */
    UPROPERTY(Config) float BeginWalkthroughLoadingSeconds = 2.5f;

    /** Folder scanned for third-party attributions, relative to the project directory. */
    UPROPERTY(Config) FString ThirdPartyFolder = TEXT("SourceAssets/third-party");

    UPROPERTY(Config) FString TitleOverride;
    UPROPERTY(Config) FString SubtitleOverride;

    /** Extra loading lines appended to the built-in set. */
    UPROPERTY(Config) TArray<FString> ExtraLoadingLines;

private:
    void SetScreen(EMikdashScreen NewScreen);
    void TearDownScreens();

    template <typename WidgetType>
    WidgetType* MakeScreen(TObjectPtr<WidgetType>& Slot, int32 ZOrder);

    void OnMapLoaded(UWorld* LoadedWorld);
    bool TickBoot(float DeltaTime);
    bool TickMenuCamera(float DeltaTime);
    bool TickLoading(float DeltaTime);

    void EnsurePauseKeyBound(APlayerController* Controller);
    void ReleasePauseKey();
    UFUNCTION() void HandlePauseKey();

    void ApplyMenuInputMode(bool bMenuUp);
    void StartMenuCamera();
    void StopMenuCamera();
    void RestoreMenuCameraTick();
    TWeakObjectPtr<APlayerController> MenuTickController;
    bool bPreviousFullTickWhenPaused = false;
    ACameraActor* FindLabelledMenuCamera(UWorld* World) const;

    TArray<FMikdashCreditsSection> ReadThirdPartyCredits() const;

    UPROPERTY(Transient) TObjectPtr<UMikdashMainMenuWidget> MainMenu;
    UPROPERTY(Transient) TObjectPtr<UMikdashPauseMenuWidget> PauseMenu;
    UPROPERTY(Transient) TObjectPtr<UMikdashSettingsWidget> SettingsScreen;
    UPROPERTY(Transient) TObjectPtr<UMikdashCreditsWidget> CreditsScreen;
    UPROPERTY(Transient) TObjectPtr<UMikdashLoadingScreenWidget> LoadingScreen;

    UPROPERTY(Transient) TObjectPtr<UInputComponent> PauseInput;
    UPROPERTY(Transient) TWeakObjectPtr<APlayerController> BoundController;

    UPROPERTY(Transient) TObjectPtr<ACameraActor> MenuCamera;
    UPROPERTY(Transient) TWeakObjectPtr<AActor> PreviousViewTarget;
    /** True when MenuCamera is a level actor we borrowed rather than one we spawned. */
    bool bMenuCameraIsBorrowed = false;
    float MenuCameraYaw = 0.0f;

    EMikdashScreen Screen = EMikdashScreen::None;
    /** Where GoBack() returns to from settings and credits. */
    EMikdashScreen ReturnScreen = EMikdashScreen::MainMenu;

    bool bWalkthroughStarted = false;
    bool bPausedByFrontEnd = false;
    bool bPendingBeginAfterLoading = false;
    double LoadingHideAfterSeconds = 0.0;

    FMikdashGuidedTourRequest GuidedTour;
    FText GuidedTourLabel;

    FDelegateHandle MapLoadedHandle;
    FTSTicker::FDelegateHandle BootTickHandle;
    FTSTicker::FDelegateHandle CameraTickHandle;
    FTSTicker::FDelegateHandle LoadingTickHandle;
};
