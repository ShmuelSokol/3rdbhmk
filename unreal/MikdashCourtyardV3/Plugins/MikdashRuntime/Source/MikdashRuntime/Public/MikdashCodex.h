// MikdashCodex.h -- the browsable reference behind the walkthrough.
//
// A visitor who has just been shown the menorah wants to know two things: what the
// sources actually say, and how much of what he is looking at anybody actually knows.
// This actor answers both. Every entry carries its citation and one of three labels:
//
//   certain   the sources agree, or one is decisive and nothing cited disputes it
//   disputed  they disagree, and the entry names who holds what
//   authored  nobody said this; the project chose it because a model has to put
//             something somewhere
//
// That third label is the reason this class exists at all. A reconstruction that cannot
// tell you which of its walls is measured and which is invented is a picture, not a
// reconstruction. So the label is a required field: an entry whose JSON carries an
// unrecognised label is REFUSED at load, never quietly promoted to "certain".
//
// WHERE THE CONTENT LIVES
// SourceAssets/tour-review/codex-entries.json. Not in this file, and not in any string
// literal in this module. The text can be corrected, argued with and translated without
// a recompile, which for a project whose whole value is the accuracy of its text is the
// only sane arrangement.
//
// WHAT THIS CLASS DOES NOT DO
// It does not decide halacha, it does not rank sources, and it does not hide an entry
// because it is inconvenient. It reads a file, serves rows, and remembers which rows the
// visitor has unlocked by going to the place they describe.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "MikdashCodex.generated.h"

/** The three labels. Mirrors MikdashTour::Confidence in TourMath.h; the JSON strings
 * are "certain", "disputed" and "authored" and nothing else parses. */
UENUM(BlueprintType)
enum class EMikdashConfidence : uint8
{
    Certain  UMETA(DisplayName = "Certain - the sources agree"),
    Disputed UMETA(DisplayName = "Disputed - the entry names who holds what"),
    Authored UMETA(DisplayName = "Authored - the project's own choice"),
};

/** One "X amot, from Y" line inside an entry. */
USTRUCT(BlueprintType)
struct FMikdashCodexMeasurement
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText Label;
    /** Already formatted for reading - "32 amot = 1600 cm". Never recomputed here: the
     * number a visitor is shown is the number a human wrote in the JSON. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText Value;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText Source;
};

/** One named position in a disagreement. Both sides get a name; "some say otherwise" is
 * not good enough for this project. */
USTRUCT(BlueprintType)
struct FMikdashCodexPosition
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText Who;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText Holds;
};

USTRUCT(BlueprintType)
struct FMikdashCodexEntry
{
    GENERATED_BODY()

    /** Stable identifier. Never shown, never translated. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FName Id;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FName Category;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText Name;
    /** The Hebrew name, when the JSON carries one. Empty means nobody has written it -
     * never "no translation needed". The panel falls back to the English. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText NameHebrew;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText Summary;
    /** Empty by design in the shipped data: see the hebrewPolicy note in the JSON. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FText SummaryHebrew;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") EMikdashConfidence Confidence = EMikdashConfidence::Authored;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") TArray<FMikdashCodexMeasurement> Measurements;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") TArray<FMikdashCodexPosition> Positions;
    /** Citations, as written in the research this project read. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") TArray<FText> Sources;
    /** Paths of the build receipts that record what was actually made, and to what size. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") TArray<FText> Receipts;

    /** Tour stop keys that unlock this entry when the visitor reaches them. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") TArray<FName> UnlockedBy;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") TArray<FName> Related;

    /** Unfilled in the shipped data. One line of narration per entry, when it is recorded. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Codex") FString NarrationAudioAsset;
};

/** Fired when an entry the visitor had not seen becomes available. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FMikdashCodexUnlocked, FName, EntryId);

/**
 * Serves the codex and remembers what the visitor unlocked.
 *
 * Place one in the level (Scripts/release_tour.py does), or let AMikdashTourGuide spawn
 * one. If two exist the first found wins and the second logs a warning rather than
 * fighting it.
 */
UCLASS(Config = Game, Blueprintable)
class MIKDASHRUNTIME_API AMikdashCodex : public AActor
{
    GENERATED_BODY()
public:
    AMikdashCodex();

    virtual void BeginPlay() override;

    /** The codex in this world, or null. Never spawns; AMikdashTourGuide does that. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex", meta = (WorldContext = "WorldContext"))
    static AMikdashCodex* Get(const UObject* WorldContext);

    // -- loading -----------------------------------------------------------

    /**
     * Read the JSON. Called from BeginPlay; safe to call again to pick up an edit.
     *
     * Returns false and fills GetLoadError() on any of: file missing, malformed JSON, an
     * entry with no id, a duplicate id, or an unrecognised confidence label. Nothing is
     * half-loaded: on failure the previous entry set is left in place untouched.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Codex")
    bool ReloadEntries();

    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") bool IsLoaded() const { return bLoaded; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") FString GetLoadError() const { return LoadError; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") FString GetContentPath() const;

    // -- reading -----------------------------------------------------------

    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") int32 Num() const { return Entries.Num(); }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") TArray<FMikdashCodexEntry> GetEntries() const { return Entries; }

    /** Index of an entry by id, or INDEX_NONE. Never a silent 0. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") int32 IndexOf(FName EntryId) const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") bool GetEntry(FName EntryId, FMikdashCodexEntry& OutEntry) const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") bool GetEntryAt(int32 Index, FMikdashCodexEntry& OutEntry) const;

    /** Category ids in the order the JSON lists them, plus a leading "all". */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") TArray<FName> GetCategories() const { return Categories; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") FText GetCategoryName(FName CategoryId) const;

    /** Entry indices in a category, in file order. NAME_None or "all" gives everything. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") TArray<int32> IndicesInCategory(FName CategoryId) const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") static FText ConfidenceDisplayName(EMikdashConfidence Value);
    /** The one-line definition of a label, read from the JSON so it can be corrected there. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") FText ConfidenceDefinition(EMikdashConfidence Value) const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") int32 CountByConfidence(EMikdashConfidence Value) const;

    // -- unlocking ---------------------------------------------------------

    /**
     * Mark everything a stop teaches as unlocked. Returns how many entries this call
     * newly opened. Unlocking is permanent for the session and never reverses: a visitor
     * who wandered away from a stop has still been there.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Codex") int32 UnlockForStop(FName StopKey);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Codex") bool UnlockEntry(FName EntryId);
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Codex") void UnlockAll();
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Codex") void ResetUnlocked();

    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") bool IsUnlocked(FName EntryId) const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") int32 UnlockedCount() const { return Unlocked.Num(); }

    /**
     * Entries no stop unlocks. Some of the most important ones are here on purpose -
     * "How to read this codex" is not attached to a place - so the browser must show
     * locked entries as titles rather than hiding them. Hiding an entry that says the
     * model invented something would be the one unforgivable bug in this class.
     */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Codex") TArray<FName> EntriesWithNoUnlock() const;

    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Codex") FMikdashCodexUnlocked OnEntryUnlocked;

    // -- configuration -----------------------------------------------------

    /** Relative to the project directory. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Codex")
    FString ContentRelativePath = TEXT("SourceAssets/tour-review/codex-entries.json");

    /** Start with everything readable. False is the default: the codex fills as the
     * visitor goes, which is the only reason to walk the tour twice. */
    UPROPERTY(Config, EditAnywhere, Category = "Mikdash|Codex")
    bool bStartFullyUnlocked = false;

private:
    UPROPERTY(Transient) TArray<FMikdashCodexEntry> Entries;
    UPROPERTY(Transient) TArray<FName> Categories;
    UPROPERTY(Transient) TMap<FName, FText> CategoryNames;
    UPROPERTY(Transient) TMap<FName, FText> ConfidenceDefinitions;

    TMap<FName, int32> IndexById;
    TSet<FName> Unlocked;

    bool bLoaded = false;
    FString LoadError;
};
