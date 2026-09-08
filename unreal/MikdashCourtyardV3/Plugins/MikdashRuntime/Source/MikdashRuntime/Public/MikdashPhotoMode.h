// MikdashPhotoMode.h -- photo mode for the Mikdash walkthrough.
//
// The walkthrough is meant to be SHARED, and what people share is a picture. Before this
// existed the only way to get one was the operating system's own screen grab: the HUD in
// shot, the walking camera's fixed field of view, no depth of field, and the resolution of
// whatever window happened to be open.
//
// What this adds:
//
//   * The world freezes and the camera detaches. It flies freely, but on a leash: a
//     radius around where the visitor was standing and the level's own bounds, both
//     applied through MikdashCamera::ClampToSphere / ClampToBox, so nobody ends up
//     photographing the void outside the map.
//
//   * Field of view, roll, focus distance and aperture for real depth of field, exposure
//     compensation, and a set of colour grades. Everything is applied as a post process
//     blend on the photo camera itself, so nothing about the level's own post process
//     volumes is touched and exiting restores the visitor's view exactly.
//
//   * Composition aids: HUD toggle, rule-of-thirds and horizon guides, a few frame
//     borders, and a watermark.
//
//   * A high-resolution capture at 2x or 4x that writes a PNG next to the game.
//
// HOW THE CAPTURE WORKS, AND WHETHER IT WORKS PACKAGED
//
// It uses FViewport::TakeHighResScreenShot() together with GetHighResScreenshotConfig()
// (Engine/Public/HighResScreenshot.h and Engine/Public/UnrealClient.h). Both are plain
// ENGINE_API entry points with no WITH_EDITOR and no !UE_BUILD_SHIPPING guard around
// them in 5.8, which is why they were chosen: the obvious alternative, sending the
// "HighResShot" console command, goes through an exec handler and is not something to
// rely on in a Shipping build. Setting FilenameOverride to an absolute path makes the
// engine skip its numbered-suffix logic and write exactly that file, as a PNG.
//
// The high-resolution path re-renders the scene through the game viewport client, so
// anything drawn on the HUD canvas -- the borders and the watermark here -- lands in the
// PNG, while Slate widgets do not. The settings read-out is therefore suppressed for the
// capture frames and restored afterwards, which is what you want anyway.
//
// The overlay is drawn through AHUD's post-rendered actor hook rather than by replacing
// the HUD class, so no other system's HUD is disturbed. If the player controller has no
// HUD at all, one is requested and the previous class is restored on exit.
//
// No Content. No Blueprint, material, font or texture asset is required; the overlay is
// canvas drawing and the grades are numeric post process settings.

#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "GameFramework/Actor.h"
#include "Engine/Scene.h"
#include "Subsystems/GameInstanceSubsystem.h"

#include "MikdashPhotoMode.generated.h"

class ACameraActor;
class AHUD;
class APlayerController;
class UCameraComponent;
class UCanvas;
class UInputComponent;
class UMikdashPhotoMode;
class UWorld;

/** Colour grades offered in photo mode. Numeric post process settings, no assets. */
UENUM(BlueprintType)
enum class EMikdashPhotoGrade : uint8
{
    AsShot          UMETA(DisplayName = "As shot"),
    WarmGold        UMETA(DisplayName = "Warm gold"),
    CoolStone       UMETA(DisplayName = "Cool stone"),
    Sepia           UMETA(DisplayName = "Sepia"),
    Monochrome      UMETA(DisplayName = "Monochrome"),
    HighContrast    UMETA(DisplayName = "High contrast"),
    SoftDawn        UMETA(DisplayName = "Soft dawn"),
};

/** Frame borders. Letterbox ratios are drawn as bars, not as a change of aspect. */
UENUM(BlueprintType)
enum class EMikdashPhotoBorder : uint8
{
    None            UMETA(DisplayName = "None"),
    Hairline        UMETA(DisplayName = "Hairline"),
    Cinemascope     UMETA(DisplayName = "Letterbox 2.39:1"),
    Widescreen      UMETA(DisplayName = "Letterbox 1.85:1"),
    Square          UMETA(DisplayName = "Square 1:1"),
    Portrait        UMETA(DisplayName = "Portrait 4:5"),
};

/** Everything a photograph is made of, so a shot can be described in one value. */
USTRUCT(BlueprintType)
struct FMikdashPhotoSettings
{
    GENERATED_BODY()

    /** Horizontal field of view in degrees. 12 is a long lens, 120 a very wide one. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") float FieldOfViewDegrees = 70.0f;

    /** Camera roll in degrees. Damped toward the dialled value, never snapped. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") float RollDegrees = 0.0f;

    /** Focus distance in centimetres. Zero means "focus on whatever is under the centre". */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") float FocusDistanceCm = 0.0f;

    /** f-stop. Small numbers blur the background hard; 22 is effectively everything sharp. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") float Aperture = 4.0f;

    /** Exposure compensation in stops, added to the scene's own auto exposure. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") float ExposureBias = 0.0f;

    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") EMikdashPhotoGrade Grade = EMikdashPhotoGrade::AsShot;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") EMikdashPhotoBorder Border = EMikdashPhotoBorder::None;

    /** The settings read-out. Never appears in a capture whether this is on or off. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") bool bShowHud = true;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") bool bShowThirds = false;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") bool bShowHorizon = false;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Photo") bool bWatermark = true;
};

/**
 * The free-flying camera. Ticks while the world is paused, applies the leash, and draws
 * the overlay through the HUD's post-rendered actor hook so that the borders and the
 * watermark reach the high-resolution capture.
 */
UCLASS(NotBlueprintable, NotPlaceable)
class MIKDASHRUNTIME_API AMikdashPhotoCamera : public AActor
{
    GENERATED_BODY()
public:
    AMikdashPhotoCamera();

    virtual void Tick(float DeltaSeconds) override;
    virtual void PostRenderFor(APlayerController* PC, UCanvas* Canvas, FVector CameraPosition, FVector CameraDir) override;

    UPROPERTY(VisibleAnywhere, Category = "Mikdash|Photo") TObjectPtr<UCameraComponent> Camera;

    /**
     * Set by the subsystem when the camera is spawned. Not called "Owner": AActor already
     * has a member of that name and UHT will not accept a second one.
     */
    UPROPERTY(Transient) TObjectPtr<UMikdashPhotoMode> PhotoOwner;

    /** Mouse look accumulated between camera ticks. */
    float LookYawInput = 0.0f;
    float LookPitchInput = 0.0f;

    /** Suppresses the read-out for the frames a capture is in flight. */
    bool bSuppressReadout = false;
};

/**
 * Photo mode itself. A game instance subsystem, like the front end, so it survives a
 * pause and is reachable from anywhere without a Blueprint reference.
 */
UCLASS(Config = Game, MinimalAPI)
class UMikdashPhotoMode : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    MIKDASHRUNTIME_API virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    MIKDASHRUNTIME_API virtual void Deinitialize() override;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo", meta = (WorldContext = "WorldContext"))
    static MIKDASHRUNTIME_API UMikdashPhotoMode* Get(const UObject* WorldContext);

    // -- entering and leaving ----------------------------------------------

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API bool Enter();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void Exit();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void Toggle();
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") bool IsActive() const { return bActive; }

    /** Why the last Enter() refused, empty when it did not. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") FString GetLastRefusalReason() const { return LastRefusal; }

    // -- the picture -------------------------------------------------------

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void SetFieldOfView(float Degrees);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void AdjustFieldOfView(float DeltaDegrees);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void SetRoll(float Degrees);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void AdjustRoll(float DeltaDegrees);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void SetFocusDistance(float Centimetres);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void AdjustFocusDistance(float DeltaCentimetres);
    /** Focus on whatever the centre of frame is looking at. Returns the distance used. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API float FocusOnCentre();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void SetAperture(float FStop);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void AdjustAperture(float Stops);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void SetExposureBias(float Stops);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void AdjustExposureBias(float DeltaStops);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void SetGrade(EMikdashPhotoGrade Grade);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void CycleGrade(int32 Direction);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void SetBorder(EMikdashPhotoBorder Border);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void CycleBorder(int32 Direction);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void ToggleHud();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void ToggleThirds();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void ToggleHorizon();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void ToggleWatermark();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void ResetSettings();

    // By value, not by reference: a UFUNCTION cannot return a reference to a struct.
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") FMikdashPhotoSettings GetSettings() const { return Settings; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") MIKDASHRUNTIME_API FString GetGradeName() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") MIKDASHRUNTIME_API FString GetBorderName() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") MIKDASHRUNTIME_API FString GetWatermarkText() const;

    // Void-returning wrappers, because a key binding wants a void() and the useful forms
    // above return a value or take an argument.
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void CycleGradeForward();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void CycleBorderForward();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API void FocusOnCentreVoid();

    // -- capture -----------------------------------------------------------

    /**
     * Take a high-resolution photograph at Multiplier times the current viewport size and
     * write it as a PNG. Returns the absolute path it will be written to, or an empty
     * string if the request was refused (no viewport, or a size the GPU cannot allocate).
     *
     * The file appears one to a few frames later: the engine services the request on the
     * next viewport draw.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Photo") MIKDASHRUNTIME_API FString TakePhoto(int32 Multiplier);

    /** Directory the next photograph will be written to, created if it does not exist. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") MIKDASHRUNTIME_API FString ResolvePhotoDirectory() const;

    /** Absolute path, without extension, for a photograph taken now at this multiplier. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") MIKDASHRUNTIME_API FString BuildPhotoBaseName(int32 Multiplier) const;

    /** The last path handed to the engine, for a receipt or an on-screen confirmation. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") FString GetLastPhotoPath() const { return LastPhotoPath; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") int32 GetPhotoCount() const { return PhotosTaken; }

    // -- the leash ---------------------------------------------------------

    /** Clamp a proposed camera position into the leash sphere and the level bounds. */
    MIKDASHRUNTIME_API FVector ClampToLeash(const FVector& Proposed) const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") FVector GetLeashAnchor() const { return LeashAnchor; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") float GetLeashRadiusCm() const { return LeashRadiusCm; }
    /** How far out of the leash sphere the camera currently is, 0 when free. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Photo") MIKDASHRUNTIME_API float GetLeashUsedFraction() const;

    /** Applies the whole settings block to the camera. Called every tick while active. */
    MIKDASHRUNTIME_API void ApplyToCamera(float DeltaSeconds);

    AMikdashPhotoCamera* GetPhotoCamera() const { return PhotoCamera; }

protected:
    // -- config ------------------------------------------------------------

    /** Turn the whole feature off from DefaultGame.ini without touching code. */
    UPROPERTY(Config) bool bEnabled = true;

    /** Take the F2 key. Set false to bind photo mode from somewhere else entirely. */
    UPROPERTY(Config) bool bOwnToggleKey = true;
    UPROPERTY(Config) int32 InputPriority = 1200;

    /** Metres per second the free camera flies at, before the sprint and creep modifiers. */
    UPROPERTY(Config) float FlySpeedCmPerSecond = 900.0f;
    UPROPERTY(Config) float SprintMultiplier = 4.0f;
    UPROPERTY(Config) float CreepMultiplier = 0.15f;
    UPROPERTY(Config) float LookSensitivity = 2.2f;

    /** How far from where the visitor was standing the camera may fly. */
    UPROPERTY(Config) float LeashRadiusCm = 6000.0f;

    /**
     * Hard outer bounds, in centimetres. Defaults to the built enclosure plus a generous
     * skirt: the architecture manifest gives the whole Mikdash as
     * [-8100, -9450, 0] .. [9200, 9450, 6130], and the Jerusalem context around it is
     * much larger, so the default lets a photographer climb well clear of the roof while
     * still refusing to leave the built world.
     */
    UPROPERTY(Config) FVector BoundsMin = FVector(-60000.0, -60000.0, -3000.0);
    UPROPERTY(Config) FVector BoundsMax = FVector(60000.0, 60000.0, 40000.0);

    UPROPERTY(Config) float MinFieldOfViewDegrees = 12.0f;
    UPROPERTY(Config) float MaxFieldOfViewDegrees = 120.0f;
    UPROPERTY(Config) float MinAperture = 1.2f;
    UPROPERTY(Config) float MaxAperture = 22.0f;
    UPROPERTY(Config) float MaxFocusDistanceCm = 200000.0f;
    UPROPERTY(Config) float MinExposureBias = -5.0f;
    UPROPERTY(Config) float MaxExposureBias = 5.0f;
    UPROPERTY(Config) float RollHalfLifeSeconds = 0.12f;
    UPROPERTY(Config) float MaxRollDegrees = 45.0f;

    /** Where photographs go. Empty means "next to the game", see ResolvePhotoDirectory. */
    UPROPERTY(Config) FString PhotoDirectoryOverride;
    UPROPERTY(Config) FString PhotoFilePrefix = TEXT("Mikdash");
    UPROPERTY(Config) FString WatermarkText = TEXT("Mikdash walkthrough");

    /** Frames the read-out stays hidden after a capture is requested. */
    UPROPERTY(Config) int32 CaptureQuietFrames = 4;

private:
    friend class AMikdashPhotoCamera;

    APlayerController* GetOwningController() const;
    void BindKeys(APlayerController* Controller);
    void UnbindKeys(APlayerController* Controller);
    void HandleToggleKey();
    void HandleShot2x();
    void HandleShot4x();
    void RegisterOverlay(APlayerController* Controller);
    void UnregisterOverlay(APlayerController* Controller);
    void BuildPostProcess(struct FPostProcessSettings& Out) const;

    /**
     * Retried until a player controller exists. The subsystem is created before the first
     * controller is, so binding once in Initialize would leave the toggle key dead for the
     * whole run in every case that matters.
     */
    bool TryBindToggleKey(float DeltaSeconds);

    // Axis handlers. Mouse look is accumulated here and consumed once per camera tick, so
    // the rate does not depend on how many input events arrived in a frame.
    void HandleLookX(float Value);
    void HandleLookY(float Value);
    void HandleWheel(float Value);

    UPROPERTY(Transient) TObjectPtr<AMikdashPhotoCamera> PhotoCamera;
    UPROPERTY(Transient) TObjectPtr<UInputComponent> PhotoInput;
    UPROPERTY(Transient) TObjectPtr<UInputComponent> ToggleInput;
    UPROPERTY(Transient) TWeakObjectPtr<AActor> PreviousViewTarget;
    UPROPERTY(Transient) TWeakObjectPtr<AHUD> OverlayHud;

    FTSTicker::FDelegateHandle BindTickHandle;

    FMikdashPhotoSettings Settings;
    FString LastPhotoPath;
    FString LastRefusal;
    FVector LeashAnchor = FVector::ZeroVector;
    float CurrentRollDegrees = 0.0f;
    int32 PhotosTaken = 0;
    int32 QuietFramesLeft = 0;
    bool bActive = false;
    bool bWasPaused = false;
    bool bHudOverlaysWereOn = false;
    bool bRestoreFullTickWhenPaused = false;
};
