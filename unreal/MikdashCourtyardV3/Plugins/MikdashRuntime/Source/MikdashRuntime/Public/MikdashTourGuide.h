// MikdashTourGuide.h -- the guided tour of the Third Beis HaMikdash.
//
// THE PROBLEM THIS SOLVES
// Before this existed a visitor was dropped into a large, accurate, silent building with
// nothing telling him what it was. That is the difference between an architectural model
// and something a person can be shown. This actor walks him the path a pilgrim actually
// took - in from the east, through the gates, up to the altar, into the House, west to
// the paroches - and at each stop tells him what happens there, what it measures, and
// where that measurement comes from.
//
// DESIGN CONSTRAINTS, and why each one is here
//
//  * NO CONTENT REQUIRED. Every stop, every word and every coordinate is read from
//    SourceAssets/tour-review/tour-stops.json at run time. Nothing in this module needs
//    a Blueprint, a widget asset, a map or a texture. If the marker meshes that
//    Scripts/release_tour.py places are absent, the tour still runs and falls back to an
//    on-screen bearing and distance.
//
//  * NO SECOND UI CONVENTION. The project already has an E-to-talk dialog panel for the
//    residents (AMikdashPlayerController): a hit-test-invisible Slate overlay added to
//    the viewport, which never pauses the game, never captures the mouse and never
//    touches the input mode. This follows that exactly rather than inventing a rival.
//
//  * IT DOES NOT OWN THE BINDINGS. Its keys go on its OWN input component, pushed onto
//    the controller's stack the way UMikdashFrontEnd pushes its pause key, at a priority
//    below the front end's. Movement, look, the talk key, the dove and the pause menu
//    keep working untouched. Every key is config, so a collision is a settings edit.
//
//  * SKIPPABLE, PAUSABLE, RESUMABLE. Nothing auto-advances: a visitor can stand at the
//    altar for ten minutes and the tour waits. He can skip a stop he does not care
//    about, wander off entirely, and rejoin - and if he wanders into the Heikhal by
//    himself the tour offers him the Heikhal's stop rather than marching him back.
//
//  * TWO MODES. "Walk me there" flies the view along the stop's own approach path and
//    sets him down on the stop. "Follow the marker" shows him where to go and lets him
//    walk. Either can be switched to mid-leg without losing the stop.
//
// WHAT IS NOT ASSERTED HERE
// Nothing halachic. The arithmetic is in TourMath.h and knows only where the stops are;
// the claims are in the JSON, each with its citation and one of three confidence labels,
// and the codex (AMikdashCodex) is what shows them. Where the sources disagree the text
// says so and names the disagreement, and where the project invented something it says
// that too.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "InputCoreTypes.h"

#include "TourMath.h"

#include "MikdashTourGuide.generated.h"

class ACameraActor;
class AMikdashCodex;
class APlayerController;
class SWidget;
class UInputComponent;

UENUM(BlueprintType)
enum class EMikdashTourMode : uint8
{
    /** The view is moved for the visitor along the stop's approach path. */
    WalkMeThere      UMETA(DisplayName = "Walk me there"),
    /** A marker is shown and the visitor walks there himself. */
    FollowTheMarker  UMETA(DisplayName = "Follow the marker"),
};

UENUM(BlueprintType)
enum class EMikdashTourPanel : uint8
{
    /** Nothing on screen but the small progress line. */
    Hidden,
    /** The current stop: name, what happens here, measurements, sources. */
    Stop,
    /** The codex browser. */
    Codex,
};

/** Kept separate from the codex's own enum so this header does not have to include it. */
UENUM(BlueprintType)
enum class EMikdashConfidenceLabel : uint8
{
    Certain,
    Disputed,
    Authored,
};

/** One stop as loaded from the JSON. The geometry lives in MikdashTour::Route; this is
 * the text that hangs off it. */
USTRUCT(BlueprintType)
struct FMikdashTourStopText
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FName Key;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FText Name;
    /** Empty when nobody has written it; the panel then shows the English alone. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FText NameHebrew;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FText Subtitle;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FText WhatHappensHere;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FText Explanation;
    /** Pre-formatted "32 amot = 1600 cm - Yechezkel 40:47" lines. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") TArray<FText> Measurements;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") TArray<FText> Sources;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") TArray<FName> CodexEntries;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") EMikdashConfidenceLabel Confidence = EMikdashConfidenceLabel::Certain;
    /** Unfilled in the shipped data: one narration line per stop, when it is recorded. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FString NarrationAudioAsset;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FVector Stand = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Tour") FVector Look = FVector::ZeroVector;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FMikdashTourStopReached, FName, StopKey);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FMikdashTourFinished);

/**
 * Drives the route, the stop detection, the prompts and the progress.
 *
 * Place ONE in the level - Scripts/release_tour.py does - and it registers itself with
 * UMikdashFrontEnd so the "Guided tour" entry in the main menu lights up. If none is
 * placed the entry stays visible and greyed with a reason, which is the front end's own
 * behaviour and is better than a missing menu item.
 */
UCLASS(Config = Game, Blueprintable)
class MIKDASHRUNTIME_API AMikdashTourGuide : public AActor
{
    GENERATED_BODY()
public:
    AMikdashTourGuide();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour", meta = (WorldContext = "WorldContext"))
    static AMikdashTourGuide* Get(const UObject* WorldContext);

    // -- content -----------------------------------------------------------

    /**
     * Read tour-stops.json and build the route. Called from BeginPlay; safe to call
     * again to pick up an edit.
     *
     * Refuses, and leaves any previously loaded route untouched, on: a missing or
     * malformed file, a stop with no key, a duplicate key, a non-finite coordinate,
     * radii that are not separated enough to give the arrival hysteresis something to
     * work with, or two consecutive stops so close that arriving at one already arrives
     * at the next. The reason is in GetLoadError().
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") bool ReloadRoute();
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool IsRouteLoaded() const { return bRouteLoaded; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetLoadError() const { return LoadError; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetContentPath() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") int32 GetStopCount() const { return StopText.Num(); }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool GetStopAt(int32 Index, FMikdashTourStopText& OutStop) const;

    // -- running the tour --------------------------------------------------

    /** Start from the beginning, or resume where the visitor left off if he has been
     * here before this session. This is what the menu entry calls. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void BeginOrResumeTour();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void BeginTourFromStart();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void PauseTour();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void ResumeTour();
    /** Leave the tour. Progress is kept, so BeginOrResumeTour() comes back to this stop. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void LeaveTour();

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void NextStop();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void PreviousStop();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") bool GoToStopByKey(FName StopKey);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") bool GoToStopIndex(int32 Index);

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void SetTourMode(EMikdashTourMode Mode);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void ToggleTourMode();
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") EMikdashTourMode GetTourMode() const;

    /** Send the visitor back to the nearest point of the route he strayed from. In
     * "follow the marker" it just re-aims the marker; in "walk me there" it flies him. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void RejoinRoute();

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void TogglePanel();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") void ToggleCodexPanel();
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") EMikdashTourPanel GetPanel() const { return Panel; }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool IsTourRunning() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool IsTourPaused() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool IsAtStop() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool IsOffRoute() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") int32 GetCurrentStopIndex() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FName GetCurrentStopKey() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") int32 GetVisitedCount() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") float GetProgressFraction() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FVector GetMarkerWorldLocation() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") float GetDistanceToStopCm() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") float GetBearingToStopDegrees() const;

    /** Save and restore across a session, as one short string. Refuses a string that
     * does not fit the loaded route rather than clamping it: a clamped resume drops the
     * visitor somewhere he has never been and reads as a bug in the building. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") FString SaveBookmark() const;
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Tour") bool RestoreBookmark(const FString& Bookmark);

    // -- what the panel reads (FString, matching the resident dialog convention) ------

    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetHeading() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetSubheading() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetBody() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetMeasurementsBlock() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetSourcesBlock() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetFooter() const;
    /** The one-line status always on screen while the tour runs. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetStatusLine() const;
    /** The arrival / off-route / "you are near X" prompt, or empty. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetPromptText() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool IsPromptVisible() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool IsStopPanelVisible() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") bool IsCodexPanelVisible() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetCodexHeading() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetCodexBody() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Tour") FString GetCodexFooter() const;

    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Tour") FMikdashTourStopReached OnStopReached;
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Tour") FMikdashTourFinished OnTourFinished;

    // -- configuration ([/Script/MikdashRuntime.MikdashTourGuide] in DefaultGame.ini) --

    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour")
    FString ContentRelativePath = TEXT("SourceAssets/tour-review/tour-stops.json");

    /** Register with UMikdashFrontEnd so the menu entry lights up. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") bool bRegisterWithFrontEnd = true;

    /** Spawn an AMikdashCodex if the level has none, so placing this actor alone is
     * enough for both halves to work. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") bool bSpawnCodexIfMissing = true;

    /** Take the tour keys. False leaves every key alone and the tour is driven from
     * Blueprint or from the menu. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") bool bBindKeys = true;
    /** Below UMikdashFrontEnd's pause key (1000) on purpose: the pause screen wins. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") int32 TourInputPriority = 900;

    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") FKey TogglePanelKey = EKeys::T;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") FKey NextStopKey = EKeys::N;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") FKey PreviousStopKey = EKeys::B;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") FKey ToggleModeKey = EKeys::G;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") FKey CodexKey = EKeys::C;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") FKey RejoinKey = EKeys::R;

    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") EMikdashTourMode DefaultMode = EMikdashTourMode::FollowTheMarker;

    /** Camera pacing for "walk me there". Comfort choices, not measurements. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") float CameraSpeedCmPerSec = 450.0f;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") float CameraMinSeconds = 1.5f;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") float CameraMaxSeconds = 14.0f;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") float CameraBlendSeconds = 0.9f;
    /** How far above the stop's floor point the flying view sits. Roughly eye height;
     * the project's capture convention is 168 cm. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") float CameraEyeHeightCm = 168.0f;

    /** Corridor widths. The pair must keep MikdashTour::MinCorridorGapCm between them or
     * SetCorridor refuses and the defaults stand. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") float OffRouteCm = 1400.0f;
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") float RejoinCm = 900.0f;

    /** How close the visitor has to get to a stop he was not sent to before the tour
     * offers to take him there instead. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") float WanderOfferRadiusCm = 500.0f;

    /** Actor tag the marker meshes carry; each also carries its stop key as a tag.
     * Placed by Scripts/release_tour.py. Absent markers are not an error. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Tour") FName MarkerTag = TEXT("MikdashTourMarker");

private:
    void BindKeys(APlayerController* Controller);
    void ReleaseKeys();
    UFUNCTION() void HandleTogglePanelKey();
    UFUNCTION() void HandleNextKey();
    UFUNCTION() void HandlePreviousKey();
    UFUNCTION() void HandleModeKey();
    UFUNCTION() void HandleCodexKey();
    UFUNCTION() void HandleRejoinKey();

    void HandleMenuRequest();

    APlayerController* GetController() const;
    /** Where the visitor is, for arrival purposes: the flying camera while it flies,
     * otherwise the pawn's feet. */
    FVector GetVisitorLocation() const;

    void ApplyTuning();
    void StartCameraFlight();
    void StopCameraFlight(bool bSetPawnDown);
    void UpdateCameraFlight();
    void UpdateMarkers();
    void RefreshMarkerCache();
    void OnArrived(int32 StopIndex);

    MikdashTour::Point3 ToTourPoint(const FVector& V) const { return MikdashTour::Point3{V.X, V.Y, V.Z}; }
    FVector FromTourPoint(const MikdashTour::Point3& P) const { return FVector(P.X, P.Y, P.Z); }

    MikdashTour::Route Route;
    MikdashTour::Guide Guide;
    /** Backing store for the const char* keys MikdashTour::Stop holds. */
    TArray<TArray<ANSICHAR>> KeyStorage;

    UPROPERTY(Transient) TArray<FMikdashTourStopText> StopText;
    UPROPERTY(Transient) TObjectPtr<AMikdashCodex> Codex;
    UPROPERTY(Transient) TObjectPtr<UInputComponent> TourInput;
    UPROPERTY(Transient) TObjectPtr<ACameraActor> FlightCamera;
    UPROPERTY(Transient) TWeakObjectPtr<APlayerController> BoundController;
    UPROPERTY(Transient) TWeakObjectPtr<AActor> PreviousViewTarget;

    /** Marker actors by stop key. Weak, and deliberately not a UPROPERTY: they belong to
     * the level, this is only a lookup, and nothing here should keep one alive. */
    TMap<FName, TWeakObjectPtr<AActor>> Markers;

    TSharedPtr<SWidget> OverlayWidget;

    EMikdashTourPanel Panel = EMikdashTourPanel::Hidden;
    /** Which panel to return to when the codex closes. */
    EMikdashTourPanel PanelBeforeCodex = EMikdashTourPanel::Stop;

    /** Codex browser cursor. */
    int32 CodexCursor = 0;
    int32 CodexCategory = 0;

    /** The stop the visitor has wandered near but was not sent to, or INDEX_NONE. */
    int32 WanderOffer = INDEX_NONE;

    bool bRouteLoaded = false;
    bool bFlying = false;
    bool bEverStarted = false;
    FString LoadError;
    FString TransientNote;
    double TransientNoteUntil = 0.0;
};
