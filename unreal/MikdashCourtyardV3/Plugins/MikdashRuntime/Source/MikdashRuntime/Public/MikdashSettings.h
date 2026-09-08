// MikdashSettings.h -- persisted settings for the Mikdash walkthrough front end.
//
// Three things live here:
//   FMikdashSettingsRecord   the serialisable mirror of MikdashSettings::FSettings
//   UMikdashSettingsSave     the USaveGame that carries one record to disk
//   UMikdashSettingsSubsystem the game-instance subsystem that owns the live values,
//                            applies them to the engine, and saves them
//
// All the rules about what a value may be, how a preset expands, and how an older
// saved record is brought forward live in the engine-independent SettingsMath.h and
// are covered by Tests/SettingsMathTest.cpp. Nothing in this file re-decides them.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "Subsystems/GameInstanceSubsystem.h"

#include "SettingsMath.h"

#include "MikdashSettings.generated.h"

class APlayerController;
class USoundClass;

/**
 * The saved shape of the settings. Deliberately plain: ints, floats and bools only,
 * so that adding a field never changes the serialised layout of the existing ones and
 * a record written by an older build still deserialises. Meaning is assigned by
 * SettingsMath.h; Version drives the migration there.
 */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashSettingsRecord
{
    GENERATED_BODY()

    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings") int32 Version = MikdashSettings::CurrentVersion;

    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 Preset = 2;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 ViewDistance = 2;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 Shadows = 2;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 GlobalIllumination = 2;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 Reflections = 2;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 PostProcess = 2;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 Textures = 3;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 Effects = 2;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 Foliage = 1;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Graphics") int32 Shading = 2;

    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Display") int32 ResolutionX = 1920;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Display") int32 ResolutionY = 1080;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Display") int32 WindowMode = 1;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Display") float FrameRateCap = 0.0f;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Display") int32 UpscaleMethod = 2;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Display") int32 UpscaleQuality = 1;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Display") float ScreenPercentage = 77.0f;

    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Camera") float FieldOfView = 90.0f;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Camera") float MouseSensitivity = 0.5f;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Camera") bool bInvertY = false;

    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Audio") float MasterVolume = 0.8f;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Audio") float MusicVolume = 0.7f;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Audio") float EffectsVolume = 0.8f;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Audio") float VoiceVolume = 0.9f;

    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Text") bool bSubtitles = true;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Text") float SubtitleScale = 1.0f;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Text") int32 Language = 0;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Text") float TextScale = 1.0f;

    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Accessibility") bool bCameraShake = true;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Accessibility") bool bHeadBob = true;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Accessibility") bool bVignetteOnMovement = false;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Accessibility") bool bSnapTurn = false;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Accessibility") float SnapTurnDegrees = 45.0f;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Accessibility") int32 ColourVision = 0;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Accessibility") int32 SprintMode = 0;
    UPROPERTY(SaveGame, BlueprintReadWrite, Category = "Mikdash|Settings|Accessibility") int32 CrouchMode = 0;

    /** Copy into the engine-independent struct without validating. */
    MikdashSettings::FSettings ToMath() const;

    /** Copy back out of the engine-independent struct. */
    void FromMath(const MikdashSettings::FSettings& In);
};

/** One record on disk. Slot name and index come from the subsystem. */
UCLASS(MinimalAPI)
class UMikdashSettingsSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) FMikdashSettingsRecord Record;

    /** Free text so a human reading the .sav can tell which build wrote it. */
    UPROPERTY(SaveGame) FString WrittenBy;
};

/**
 * A colour-blind-safe palette for the front-end UI.
 *
 * The front end only ever uses colour to say four things: this is the page, this is
 * selected, this is a warning, this is unavailable. Each variant keeps those four
 * separable for the named deficiency AND keeps them separable by lightness, so the
 * distinction survives a greyscale capture as well.
 */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashPalette
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|UI") FLinearColor Background = FLinearColor(0.020f, 0.021f, 0.026f, 0.94f);
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|UI") FLinearColor Panel = FLinearColor(0.055f, 0.056f, 0.065f, 0.96f);
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|UI") FLinearColor Text = FLinearColor(0.92f, 0.90f, 0.85f, 1.0f);
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|UI") FLinearColor TextDim = FLinearColor(0.62f, 0.61f, 0.58f, 1.0f);
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|UI") FLinearColor Accent = FLinearColor(0.85f, 0.68f, 0.30f, 1.0f);
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|UI") FLinearColor Selected = FLinearColor(0.95f, 0.82f, 0.45f, 1.0f);
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|UI") FLinearColor Warning = FLinearColor(0.90f, 0.42f, 0.28f, 1.0f);
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|UI") FLinearColor Disabled = FLinearColor(0.36f, 0.36f, 0.38f, 1.0f);

    static FMikdashPalette Make(MikdashSettings::EColourVision Mode);
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FMikdashSettingsChanged);

/**
 * Owns the live settings for the session.
 *
 * Read through Get(). Change through Edit()/Commit() or one of the Set helpers; every
 * one of those clamps through SettingsMath, applies to the engine and writes the save
 * file, then broadcasts OnSettingsChanged so open UI refreshes.
 *
 * Other systems (the walkthrough controller, a guided tour, a subtitle overlay) are
 * expected to READ the accessibility and input values from here rather than keep their
 * own copies. This subsystem never reaches into another system to enforce them.
 */
UCLASS(Config = Game, MinimalAPI)
class UMikdashSettingsSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    MIKDASHRUNTIME_API virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    MIKDASHRUNTIME_API virtual void Deinitialize() override;

    /** Convenience lookup; null when there is no game instance (commandlet, cook). */
    static MIKDASHRUNTIME_API UMikdashSettingsSubsystem* Get(const UObject* WorldContext);

    // -- reading -----------------------------------------------------------

    const MikdashSettings::FSettings& Get() const { return Current; }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API FMikdashSettingsRecord GetRecord() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API FMikdashPalette GetPalette() const;

    /** Look multiplier from the exponential sensitivity curve. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API float GetLookMultiplier() const;
    /** -1 when invert Y is on, +1 otherwise. Multiply pitch input by this. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API float GetPitchSign() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool IsHeadBobEnabled() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool IsCameraShakeEnabled() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool IsMovementVignetteEnabled() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool IsSnapTurnEnabled() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API float GetSnapTurnDegrees() const;
    /** True when sprint is a toggle rather than a hold. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool IsSprintToggle() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool IsCrouchToggle() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool AreSubtitlesEnabled() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API float GetTextScale() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API float GetSubtitleScale() const;
    /** Linear gain 0..1 for the named bus, master already folded in. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API float GetMusicGain() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API float GetEffectsGain() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API float GetVoiceGain() const;
    /** True when the UI should be laid out right to left. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool IsRightToLeft() const;

    // -- writing -----------------------------------------------------------

    /**
     * Mutable access for a batch of edits. The caller changes fields on the returned
     * struct and then calls Commit(). Nothing is clamped, applied or saved until then,
     * so dragging a slider does not hammer the disk.
     */
    MikdashSettings::FSettings& Edit() { return Current; }

    /** Clamp, apply to the engine, save, broadcast. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Settings") MIKDASHRUNTIME_API void Commit();

    /** Apply to the engine and broadcast, but do NOT touch the disk. For live preview. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Settings") MIKDASHRUNTIME_API void Preview();

    MIKDASHRUNTIME_API void Set(const MikdashSettings::FSettings& In);

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Settings") MIKDASHRUNTIME_API void ResetToDefaults();

    /** Read the save file; migrate it if it is older; fall back to defaults. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool Load();

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Settings") MIKDASHRUNTIME_API bool Save();

    /** Push everything at the engine. Safe to call with no world or no controller. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Settings") MIKDASHRUNTIME_API void ApplyAll();

    /** Camera FOV for the given controller, honouring Hor+ on the real viewport aspect. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Settings") MIKDASHRUNTIME_API void ApplyCameraTo(APlayerController* Controller);

    /** Fired after any commit, preview or reset. */
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Settings") FMikdashSettingsChanged OnSettingsChanged;

    /** True when the last Load() found no file and the defaults were used. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") bool WasLoadedFromDisk() const { return bLoadedFromDisk; }

    /** True when the last Load() had to migrate an older record. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") bool WasMigrated() const { return bMigratedOnLoad; }

    /** Version of the record that was found on disk, or 0 when there was none. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Settings") int32 GetLoadedVersion() const { return LoadedVersion; }

    // -- configuration (DefaultGame.ini, [/Script/MikdashRuntime.MikdashSettingsSubsystem]) --

    /** Save slot. Changing this orphans, rather than destroys, an existing file. */
    UPROPERTY(Config) FString SaveSlot = TEXT("MikdashSettings");
    UPROPERTY(Config) int32 SaveUserIndex = 0;

    /**
     * Optional SoundClass assets for the three sub-buses. Without them the music,
     * effects and voice sliders are stored and readable but move nothing: there is no
     * audio bus asset in this project for them to drive, and this module is not
     * allowed to create Content. Master volume always works: it goes through
     * FApp::SetVolumeMultiplier, which needs no asset.
     */
    UPROPERTY(Config) FSoftObjectPath MusicSoundClass;
    UPROPERTY(Config) FSoftObjectPath EffectsSoundClass;
    UPROPERTY(Config) FSoftObjectPath VoiceSoundClass;

    /** Culture codes used for the two languages. */
    UPROPERTY(Config) FString EnglishCulture = TEXT("en");
    UPROPERTY(Config) FString HebrewCulture = TEXT("he");

    /**
     * A font file that covers Hebrew. Slate can take a raw .ttf path, so the front end
     * can render Hebrew with no imported Content asset. Empty means "use the engine
     * default", which on a stock UE install has no Hebrew glyphs and will show boxes.
     */
    UPROPERTY(Config) FString HebrewFontFile = TEXT("C:/Windows/Fonts/gisha.ttf");
    UPROPERTY(Config) FString HebrewFontFileBold = TEXT("C:/Windows/Fonts/gishabd.ttf");

    /** Set false to stop the subsystem touching UGameUserSettings at all. */
    UPROPERTY(Config) bool bApplyGraphicsToEngine = true;

private:
    MikdashSettings::FSettings Current;

    bool bLoadedFromDisk = false;
    bool bMigratedOnLoad = false;
    int32 LoadedVersion = 0;

    void ApplyGraphics();
    void ApplyAudio();
    void ApplyLanguage();
    void ApplyCameraEverywhere();
};
