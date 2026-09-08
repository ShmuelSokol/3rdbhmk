// MikdashSaveGame.h -- save, resume and autosave for the walkthrough.
//
// Before this existed a visitor who quit half way through the courts lost everything:
// where they were standing, what the sun was doing, which tour stops they had reached,
// which codex entries they had opened and how their photo mode was set. This subsystem
// persists all of it, in numbered slots, with a continue-from-last entry.
//
// WHAT IS AND IS NOT IN THIS FILE
//
//   The byte format, the CRC, the version migrations and every bounds check live in
//   Public/SaveMigrationMath.h, which includes nothing from Unreal and is exercised by
//   Tests/SaveMigrationMathTest.cpp under cl.exe alone. Save corruption is the worst
//   bug class in this feature, so the part that can corrupt is the part that is testable
//   without an editor. Nothing in this file re-decides any of it.
//
//   This file is the engine half: capturing the live world into a record, applying a
//   record back to the live world, talking to the platform save system, and the small
//   amount of book-keeping (play time, autosave timing) that needs a tick.
//
// WHY NOT USaveGame
//
//   UGameplayStatics::SaveGameToSlot wraps the payload in an FSaveGameHeader and runs it
//   through UObject serialisation. That is fine until a file is truncated or a build
//   changes a UPROPERTY: the failure mode is a null return with no reason, or worse, a
//   partially deserialised object. This subsystem writes its own container through
//   ISaveGameSystem instead, so the bytes on disk are exactly the MKDS container that the
//   standalone test round-trips, corrupts, truncates and migrates. ISaveGameSystem is
//   still the platform layer, so save paths, user indices and console save UI behave the
//   way the engine expects. Verified against
//   Engine/Source/Runtime/Engine/Public/SaveGameSystem.h in UE 5.8.
//
// OWNERSHIP BOUNDARIES
//
//   The front end (UMikdashFrontEnd), the guided tour and the codex are separate agents'
//   work. This subsystem never reaches into them. It offers:
//
//     * the slot list and its labels, for a load/continue screen,
//     * NotifyTourStopReached / SetTourActive, for the tour,
//     * UnlockCodexEntry / IsCodexEntryUnlocked, for the codex,
//     * OnStateRestored, which those systems bind to re-read their state after a load.
//
//   Options are the settings subsystem's, not this one's. A slot SNAPSHOTS them, using
//   reflection over FMikdashSettingsRecord so a new slider is captured without anyone
//   editing this file, and hands the snapshot back through GetSnapshotOptions(). It does
//   not push them into the live settings on load: a visitor who has since turned the
//   graphics down should not have an old slot silently turn them back up. That decision
//   belongs to the settings screen, which is free to apply the returned record if it
//   wants that behaviour.

#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Subsystems/GameInstanceSubsystem.h"

#include "SaveMigrationMath.h"
// Included rather than forward-declared: GetSnapshotOptions returns FMikdashSettingsRecord
// by value from a UFUNCTION, and UHT needs the complete type to generate the thunk.
#include "MikdashSettings.h"

#include "MikdashSaveGame.generated.h"

class AMikdashTimeOfDay;
class APlayerController;
class UMikdashSettingsSubsystem;
class UWorld;

/** Why an autosave fired. Recorded in the slot label and in the log. */
UENUM(BlueprintType)
enum class EMikdashSaveReason : uint8
{
    Manual      UMETA(DisplayName = "Manual"),
    TourStop    UMETA(DisplayName = "Tour stop"),
    Quit        UMETA(DisplayName = "Quit"),
    Periodic    UMETA(DisplayName = "Periodic"),
};

/**
 * Why a load did not happen. Mirrors MikdashSave::ESaveDecodeError one for one, plus the
 * two failures that happen before the decoder is ever reached.
 */
UENUM(BlueprintType)
enum class EMikdashSaveError : uint8
{
    None                UMETA(DisplayName = "None"),
    SlotEmpty           UMETA(DisplayName = "No save in that slot"),
    ReadFailed          UMETA(DisplayName = "The file could not be read"),
    BufferTooSmall      UMETA(DisplayName = "File is shorter than a save header"),
    BadMagic            UMETA(DisplayName = "Not a Mikdash save file"),
    UnsupportedFormat   UMETA(DisplayName = "Unsupported save container version"),
    VersionTooOld       UMETA(DisplayName = "Older than this build can migrate"),
    VersionTooNew       UMETA(DisplayName = "Written by a newer build"),
    PayloadTooLarge     UMETA(DisplayName = "Declared payload is implausibly large"),
    LengthMismatch      UMETA(DisplayName = "File is truncated or has extra bytes"),
    ChecksumMismatch    UMETA(DisplayName = "Payload failed its checksum"),
    PayloadUnderrun     UMETA(DisplayName = "Payload ended early"),
    PayloadTrailing     UMETA(DisplayName = "Payload has unread trailing bytes"),
    FieldOutOfRange     UMETA(DisplayName = "Contains an out-of-range length"),
};

/** Photo-mode state carried in a slot. Plain values; the photo agent owns their meaning. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashPhotoState
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Save|Photo") float FieldOfViewDegrees = 90.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Save|Photo") float ExposureCompensation = 0.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Save|Photo") float FocusDistanceCm = 1000.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Save|Photo") float Aperture = 4.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Save|Photo") float RollDegrees = 0.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Save|Photo") int32 ResolutionMultiplier = 1;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Save|Photo") bool bHideInterface = true;
    /** Identifier of the colour-grade preset. Free text; the photo agent defines the set. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Save|Photo") FName LookId;
};

/**
 * One save slot as the front end sees it.
 *
 * Filled by reading only the header and the first fields of a slot, so listing eight
 * slots does not deserialise eight full records. bValid is false for an empty slot AND
 * for a corrupt one; Error says which, and Error is what a load screen should show
 * rather than silently hiding the row -- a visitor whose save went bad deserves to be
 * told, not to find the slot missing.
 */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashSaveSlotInfo
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") int32 SlotIndex = 0;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") FString SlotName;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") bool bExists = false;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") bool bValid = false;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") EMikdashSaveError Error = EMikdashSaveError::SlotEmpty;
    /** Human wording for Error, already localised through the string table. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") FText ErrorText;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") FText Label;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") FDateTime SaveTimeUtc;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") float PlayTimeSeconds = 0.0f;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") FString MapName;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") int32 RecordVersion = 0;
    /** True when the record on disk is older than this build and had to be brought forward. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") bool bWouldMigrate = false;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") int32 CompletedStopCount = 0;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") int32 CodexEntryCount = 0;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Save") float TimeOfDayHours = 12.0f;
};

/** Fired after a save attempt, successful or not. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FMikdashSaveCompleted, int32, SlotIndex, bool, bSuccess);
/** Fired after a load attempt. On failure, Error says why and nothing was changed. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FMikdashLoadCompleted, int32, SlotIndex, bool, bSuccess, EMikdashSaveError, Error);
/**
 * Fired once, after a successful load, when the record has been applied to the world.
 * This is the hook the tour and the codex bind: re-read GetCompletedTourStops(),
 * GetCurrentTourStop() and GetUnlockedCodexEntries() here and rebuild your own state.
 */
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FMikdashStateRestored);
/** Fired when an entry is unlocked for the first time. Not fired during a load. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FMikdashSaveCodexUnlocked, FName, EntryId);

/**
 * The save system.
 *
 * Live progress -- completed stops, codex entries, photo settings, play time -- lives
 * here for the whole session and is written into whichever slot is saved. Reading it is
 * free; writing it is a memory operation, not a disk one, until a save is asked for.
 *
 * Threading: everything here is game thread. Saves go through ISaveGameSystem's blocking
 * SaveGame by default because the payload is a few kilobytes and an autosave that races a
 * level transition is a much worse problem than a two-millisecond hitch. Set
 * bAsyncSaves=true in config to use SaveGameAsync instead.
 */
UCLASS(Config = Game, MinimalAPI)
class UMikdashSaveSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    MIKDASHRUNTIME_API virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    MIKDASHRUNTIME_API virtual void Deinitialize() override;

    /** Null in a commandlet or cook, where there is no game instance. Always check. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save", meta = (WorldContext = "WorldContext"))
    static MIKDASHRUNTIME_API UMikdashSaveSystem* Get(const UObject* WorldContext);

    // -- slots -------------------------------------------------------------

    UFUNCTION(BlueprintPure, Category = "Mikdash|Save") int32 GetSlotCount() const { return SlotCount; }

    /** Platform slot name for a visitor-facing slot index. Index is clamped. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save") MIKDASHRUNTIME_API FString MakeSlotName(int32 SlotIndex) const;

    /** Index of the dedicated autosave slot. It is one past the manual slots. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save") int32 GetAutosaveSlotIndex() const { return SlotCount; }

    /**
     * Every slot, manual then autosave, headers only.
     *
     * bRefresh=false returns the cached list from the last scan, which is what a menu
     * redrawing every frame should pass. A save, a load or a delete invalidates the cache
     * on its own, so a screen never has to know when to force a rescan.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save")
    MIKDASHRUNTIME_API TArray<FMikdashSaveSlotInfo> GetSlotInfos(bool bRefresh = true);

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save")
    MIKDASHRUNTIME_API FMikdashSaveSlotInfo GetSlotInfo(int32 SlotIndex, bool bRefresh = true);

    /** True when at least one slot holds a record this build can load. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save") MIKDASHRUNTIME_API bool HasAnyLoadableSave();

    /**
     * The slot a Continue entry should use: the most recently written VALID slot,
     * autosave included. SlotIndex is -1 when there is none, which is how a front end
     * decides to grey the entry out.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save") MIKDASHRUNTIME_API FMikdashSaveSlotInfo GetContinueSlot();

    /** The first slot with nothing in it, or -1 when every manual slot is used. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save") MIKDASHRUNTIME_API int32 FindFirstEmptySlot();

    // -- saving and loading ------------------------------------------------

    /** Capture the world into a record and write it. Label may be empty for a default. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save")
    MIKDASHRUNTIME_API bool SaveToSlot(int32 SlotIndex, const FString& Label);

    /**
     * Write the autosave slot.
     *
     * Silently does nothing, returning false, when bAutosaveEnabled is false or when the
     * last autosave was less than MinimumAutosaveIntervalSeconds ago and Reason is not
     * Quit. Quit always writes: losing the last minute because the throttle was still
     * warm is exactly the failure this feature exists to stop.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save")
    MIKDASHRUNTIME_API bool Autosave(EMikdashSaveReason Reason);

    /**
     * Read a slot, migrate it if needed, and apply it to the world.
     *
     * On any failure the live state is left exactly as it was -- the record is decoded in
     * full before a single field is applied -- and OnLoadCompleted carries the reason.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save")
    MIKDASHRUNTIME_API bool LoadFromSlot(int32 SlotIndex);

    /** Load GetContinueSlot(). False when there is nothing to continue. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save") MIKDASHRUNTIME_API bool ContinueFromLast();

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save") MIKDASHRUNTIME_API bool DeleteSlot(int32 SlotIndex);

    /** Clear the live session state without touching disk. Used by "new walkthrough". */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save") MIKDASHRUNTIME_API void ResetSessionState();

    /** Localised wording for an error code, from the Mikdash string table. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save")
    static MIKDASHRUNTIME_API FText DescribeError(EMikdashSaveError Error);

    // -- the guided tour's interface ---------------------------------------

    /**
     * Mark a stop reached. Records it as completed, makes it current, and triggers a
     * TourStop autosave. Calling it twice for the same stop is harmless.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save|Tour")
    MIKDASHRUNTIME_API void NotifyTourStopReached(FName StopId);

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save|Tour") MIKDASHRUNTIME_API void SetTourActive(bool bActive);
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save|Tour") bool IsTourActive() const { return bTourActive; }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Save|Tour") MIKDASHRUNTIME_API bool IsTourStopComplete(FName StopId) const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save|Tour") MIKDASHRUNTIME_API TArray<FName> GetCompletedTourStops() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save|Tour") FName GetCurrentTourStop() const { return CurrentTourStop; }
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save|Tour") MIKDASHRUNTIME_API void SetCurrentTourStop(FName StopId);

    // -- the codex's interface ---------------------------------------------

    /** Returns true when this was the first time. Fires OnCodexEntryUnlocked in that case. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save|Codex")
    MIKDASHRUNTIME_API bool UnlockCodexEntry(FName EntryId);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Save|Codex") MIKDASHRUNTIME_API bool IsCodexEntryUnlocked(FName EntryId) const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save|Codex") MIKDASHRUNTIME_API TArray<FName> GetUnlockedCodexEntries() const;

    // -- photo mode --------------------------------------------------------

    UFUNCTION(BlueprintPure, Category = "Mikdash|Save|Photo") MIKDASHRUNTIME_API FMikdashPhotoState GetPhotoState() const;
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save|Photo") MIKDASHRUNTIME_API void SetPhotoState(const FMikdashPhotoState& In);

    // -- play time ---------------------------------------------------------

    /** Seconds of walkthrough, accumulated across every session that touched this slot. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save") MIKDASHRUNTIME_API float GetPlayTimeSeconds() const;

    /** hh:mm:ss, or mm:ss under an hour. Culture-independent digits by design. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Save") MIKDASHRUNTIME_API FText GetPlayTimeText() const;

    /** Stop and start the play-time clock. The front end pauses it while a menu is up. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save") MIKDASHRUNTIME_API void SetPlayTimeCounting(bool bCounting);

    // -- options snapshot --------------------------------------------------

    /**
     * The settings this slot was written with, as a record the settings screen can apply.
     * bOutHadSnapshot is false when the slot predates the options block or was written
     * with no settings subsystem present.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Save|Options")
    MIKDASHRUNTIME_API FMikdashSettingsRecord GetSnapshotOptions(bool& bOutHadSnapshot) const;

    // -- delegates ---------------------------------------------------------

    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Save") FMikdashSaveCompleted OnSaveCompleted;
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Save") FMikdashLoadCompleted OnLoadCompleted;
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Save") FMikdashStateRestored OnStateRestored;
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Save") FMikdashSaveCodexUnlocked OnCodexEntryUnlocked;

    // -- configuration ([/Script/MikdashRuntime.MikdashSaveSystem] in DefaultGame.ini) --

    /** Number of visitor-facing manual slots. The autosave slot is extra. */
    UPROPERTY(Config) int32 SlotCount = 8;

    /** Prefix of the platform slot name. Manual slots are <prefix>_00.., autosave <prefix>_Auto. */
    UPROPERTY(Config) FString SlotNamePrefix = TEXT("MikdashSave");

    UPROPERTY(Config) int32 UserIndex = 0;

    UPROPERTY(Config) bool bAutosaveEnabled = true;

    /** Autosave at every tour stop. Off leaves only the periodic and quit autosaves. */
    UPROPERTY(Config) bool bAutosaveAtTourStops = true;

    /** Autosave when the application is shutting down. */
    UPROPERTY(Config) bool bAutosaveOnQuit = true;

    /** 0 disables the timed autosave. Tour-stop and quit autosaves are unaffected. */
    UPROPERTY(Config) float PeriodicAutosaveSeconds = 300.0f;

    /** Throttle. A tour stop reached inside this window of the last autosave is skipped. */
    UPROPERTY(Config) float MinimumAutosaveIntervalSeconds = 20.0f;

    /** Use ISaveGameSystem::SaveGameAsync. Off by default; see the class comment. */
    UPROPERTY(Config) bool bAsyncSaves = false;

    /** Restore the visitor's position and orientation on load. */
    UPROPERTY(Config) bool bRestorePlayerTransform = true;

    /** Restore the time of day on load, when an AMikdashTimeOfDay is in the level. */
    UPROPERTY(Config) bool bRestoreTimeOfDay = true;

    /** Build number written into every record. Bump it in config per shipped build. */
    UPROPERTY(Config) int32 BuildNumber = 1;

private:
    /** Fill Record from the live world. Fields with no source keep their current value. */
    void CaptureRecord(MikdashSave::FSaveRecord& Record, const FString& Label) const;

    /** Push a decoded record into the live world. Only called after a clean decode. */
    void ApplyRecord(const MikdashSave::FSaveRecord& Record);

    /** Copy the session lists into a record, without touching the world. */
    void CaptureSessionState(MikdashSave::FSaveRecord& Record) const;
    void AdoptSessionState(const MikdashSave::FSaveRecord& Record);

    void CaptureOptions(MikdashSave::FSaveRecord& Record) const;

    bool WriteSlot(int32 SlotIndex, const MikdashSave::FSaveRecord& Record);
    bool ReadSlot(int32 SlotIndex, TArray<uint8>& OutBytes) const;

    FMikdashSaveSlotInfo ScanSlot(int32 SlotIndex) const;

    APlayerController* GetLocalController() const;
    AMikdashTimeOfDay* FindTimeOfDay() const;
    UMikdashSettingsSubsystem* GetSettings() const;

    bool TickSave(float DeltaTime);
    void HandlePreExit();

    static EMikdashSaveError ToSaveError(MikdashSave::ESaveDecodeError Error);

    /** Live session state. Written into whichever slot is saved next. */
    TSet<FName> CompletedTourStops;
    TArray<FName> CompletedTourStopOrder;   // save order is the order they were reached
    TSet<FName> UnlockedCodex;
    TArray<FName> UnlockedCodexOrder;
    FName CurrentTourStop;
    bool bTourActive = false;
    FMikdashPhotoState Photo;

    /**
     * The options block of the record last loaded, kept for GetSnapshotOptions.
     *
     * std::vector rather than TArray because it is assigned straight from
     * MikdashSave::FSaveRecord::Options, and converting a container on every load only to
     * convert it back on every read would be work in service of a house style.
     */
    std::vector<MikdashSave::FOptionValue> SnapshotOptions;
    bool bHasSnapshotOptions = false;

    double AccumulatedPlayTimeSeconds = 0.0;
    bool bPlayTimeCounting = true;

    double LastAutosaveRealSeconds = -1.0e9;
    double NextPeriodicAutosaveRealSeconds = 0.0;
    bool bQuitAutosaveDone = false;

    TArray<FMikdashSaveSlotInfo> CachedSlots;
    bool bSlotCacheValid = false;

    FTSTicker::FDelegateHandle TickHandle;
    FDelegateHandle PreExitHandle;
};
