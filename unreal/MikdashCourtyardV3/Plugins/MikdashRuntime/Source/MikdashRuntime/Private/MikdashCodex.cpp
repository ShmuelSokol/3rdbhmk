#include "MikdashCodex.h"

#include "TourMath.h"

#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Dom/JsonValue.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashCodex, Log, All);

#define LOCTEXT_NAMESPACE "MikdashCodex"

namespace
{
/** A JSON string field, or empty. Missing and empty are the same thing to the reader,
 * and both mean "nobody wrote it" - never "no text needed". */
FText TextField(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field)
{
    FString Value;
    if (Object.IsValid() && Object->TryGetStringField(Field, Value) && !Value.IsEmpty())
    {
        return FText::FromString(Value);
    }
    return FText::GetEmpty();
}

/** {"en": "...", "he": "..."} - the shape every human-readable field uses. */
void LocalisedField(const TSharedPtr<FJsonObject>& Parent, const TCHAR* Field, FText& OutEnglish, FText& OutHebrew)
{
    OutEnglish = FText::GetEmpty();
    OutHebrew = FText::GetEmpty();
    if (!Parent.IsValid()) return;
    const TSharedPtr<FJsonObject>* Child = nullptr;
    if (Parent->TryGetObjectField(Field, Child) && Child != nullptr)
    {
        OutEnglish = TextField(*Child, TEXT("en"));
        OutHebrew = TextField(*Child, TEXT("he"));
    }
    else
    {
        // Tolerate a plain string where the shape is a pair; the English is what we get.
        OutEnglish = TextField(Parent, Field);
    }
}

void NameArrayField(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, TArray<FName>& Out)
{
    Out.Reset();
    const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
    if (!Object->TryGetArrayField(Field, Array) || Array == nullptr) return;
    for (const TSharedPtr<FJsonValue>& Value : *Array)
    {
        FString Text;
        if (Value.IsValid() && Value->TryGetString(Text) && !Text.IsEmpty())
        {
            Out.Add(FName(*Text));
        }
    }
}

void TextArrayField(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, TArray<FText>& Out)
{
    Out.Reset();
    const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
    if (!Object->TryGetArrayField(Field, Array) || Array == nullptr) return;
    for (const TSharedPtr<FJsonValue>& Value : *Array)
    {
        FString Text;
        if (Value.IsValid() && Value->TryGetString(Text) && !Text.IsEmpty())
        {
            Out.Add(FText::FromString(Text));
        }
    }
}
} // namespace

AMikdashCodex::AMikdashCodex()
{
    PrimaryActorTick.bCanEverTick = false;
    SetCanBeDamaged(false);
}

void AMikdashCodex::BeginPlay()
{
    Super::BeginPlay();
    if (!ReloadEntries())
    {
        // Loud, and then carry on. A missing codex must not stop the walkthrough; the
        // panel says why it is empty.
        UE_LOG(LogMikdashCodex, Error, TEXT("Codex not loaded: %s"), *LoadError);
    }
    if (bStartFullyUnlocked)
    {
        UnlockAll();
    }
}

AMikdashCodex* AMikdashCodex::Get(const UObject* WorldContext)
{
    const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
    if (World == nullptr) return nullptr;
    for (TActorIterator<AMikdashCodex> It(const_cast<UWorld*>(World)); It; ++It)
    {
        if (IsValid(*It)) return *It;
    }
    return nullptr;
}

FString AMikdashCodex::GetContentPath() const
{
    return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / ContentRelativePath);
}

bool AMikdashCodex::ReloadEntries()
{
    const FString Path = GetContentPath();
    LoadError.Reset();

    FString Raw;
    if (!FFileHelper::LoadFileToString(Raw, *Path))
    {
        LoadError = FString::Printf(TEXT("could not read %s"), *Path);
        return false;
    }

    TSharedPtr<FJsonObject> Root;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Raw);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        LoadError = FString::Printf(TEXT("%s is not valid JSON"), *Path);
        return false;
    }

    // Build into locals. Nothing touches the live set until every row has passed, so a
    // half-broken edit leaves the running codex exactly as it was.
    TArray<FMikdashCodexEntry> NewEntries;
    TMap<FName, int32> NewIndex;
    TArray<FName> NewCategories;
    TMap<FName, FText> NewCategoryNames;
    TMap<FName, FText> NewDefinitions;

    NewCategories.Add(FName(TEXT("all")));
    NewCategoryNames.Add(FName(TEXT("all")), LOCTEXT("AllCategories", "Everything"));

    const TArray<TSharedPtr<FJsonValue>>* CategoryArray = nullptr;
    if (Root->TryGetArrayField(TEXT("categories"), CategoryArray) && CategoryArray != nullptr)
    {
        for (const TSharedPtr<FJsonValue>& Value : *CategoryArray)
        {
            const TSharedPtr<FJsonObject> Object = Value.IsValid() ? Value->AsObject() : nullptr;
            if (!Object.IsValid()) continue;
            FString Id;
            if (!Object->TryGetStringField(TEXT("id"), Id) || Id.IsEmpty()) continue;
            FText English, Hebrew;
            LocalisedField(Object, TEXT("name"), English, Hebrew);
            const FName CategoryId(*Id);
            NewCategories.AddUnique(CategoryId);
            NewCategoryNames.Add(CategoryId, English.IsEmpty() ? FText::FromString(Id) : English);
        }
    }

    const TSharedPtr<FJsonObject>* Labels = nullptr;
    if (Root->TryGetObjectField(TEXT("confidenceLabels"), Labels) && Labels != nullptr)
    {
        for (const TCHAR* Key : { TEXT("certain"), TEXT("disputed"), TEXT("authored") })
        {
            NewDefinitions.Add(FName(Key), TextField(*Labels, Key));
        }
    }

    const TArray<TSharedPtr<FJsonValue>>* EntryArray = nullptr;
    if (!Root->TryGetArrayField(TEXT("entries"), EntryArray) || EntryArray == nullptr)
    {
        LoadError = TEXT("no \"entries\" array");
        return false;
    }

    for (int32 Row = 0; Row < EntryArray->Num(); ++Row)
    {
        const TSharedPtr<FJsonObject> Object = (*EntryArray)[Row].IsValid() ? (*EntryArray)[Row]->AsObject() : nullptr;
        if (!Object.IsValid())
        {
            LoadError = FString::Printf(TEXT("entry %d is not an object"), Row);
            return false;
        }

        FMikdashCodexEntry Entry;

        FString Id;
        if (!Object->TryGetStringField(TEXT("id"), Id) || Id.IsEmpty())
        {
            LoadError = FString::Printf(TEXT("entry %d has no id"), Row);
            return false;
        }
        Entry.Id = FName(*Id);
        if (NewIndex.Contains(Entry.Id))
        {
            LoadError = FString::Printf(TEXT("duplicate entry id \"%s\""), *Id);
            return false;
        }

        FString Category;
        Object->TryGetStringField(TEXT("category"), Category);
        Entry.Category = Category.IsEmpty() ? FName(TEXT("method")) : FName(*Category);

        // The label is the point of the whole class, so an unknown one is fatal rather
        // than silently defaulted. A typo must never read as "certain".
        FString ConfidenceText;
        if (!Object->TryGetStringField(TEXT("confidence"), ConfidenceText))
        {
            LoadError = FString::Printf(TEXT("entry \"%s\" has no confidence label"), *Id);
            return false;
        }
        MikdashTour::Confidence Parsed = MikdashTour::Confidence::Authored;
        if (!MikdashTour::ParseConfidence(TCHAR_TO_ANSI(*ConfidenceText), Parsed))
        {
            LoadError = FString::Printf(TEXT("entry \"%s\" has an unrecognised confidence label \"%s\"; expected certain, disputed or authored"),
                                        *Id, *ConfidenceText);
            return false;
        }
        Entry.Confidence = Parsed == MikdashTour::Confidence::Certain ? EMikdashConfidence::Certain
                         : Parsed == MikdashTour::Confidence::Disputed ? EMikdashConfidence::Disputed
                         : EMikdashConfidence::Authored;

        LocalisedField(Object, TEXT("name"), Entry.Name, Entry.NameHebrew);
        LocalisedField(Object, TEXT("summary"), Entry.Summary, Entry.SummaryHebrew);
        if (Entry.Name.IsEmpty())
        {
            Entry.Name = FText::FromString(Id);
        }

        const TArray<TSharedPtr<FJsonValue>>* MeasurementArray = nullptr;
        if (Object->TryGetArrayField(TEXT("measurements"), MeasurementArray) && MeasurementArray != nullptr)
        {
            for (const TSharedPtr<FJsonValue>& Value : *MeasurementArray)
            {
                const TSharedPtr<FJsonObject> Measurement = Value.IsValid() ? Value->AsObject() : nullptr;
                if (!Measurement.IsValid()) continue;
                FMikdashCodexMeasurement Row2;
                Row2.Label = TextField(Measurement, TEXT("label"));
                Row2.Value = TextField(Measurement, TEXT("value"));
                Row2.Source = TextField(Measurement, TEXT("source"));
                Entry.Measurements.Add(Row2);
            }
        }

        const TSharedPtr<FJsonObject>* Dispute = nullptr;
        if (Object->TryGetObjectField(TEXT("dispute"), Dispute) && Dispute != nullptr)
        {
            const TArray<TSharedPtr<FJsonValue>>* PositionArray = nullptr;
            if ((*Dispute)->TryGetArrayField(TEXT("positions"), PositionArray) && PositionArray != nullptr)
            {
                for (const TSharedPtr<FJsonValue>& Value : *PositionArray)
                {
                    const TSharedPtr<FJsonObject> Position = Value.IsValid() ? Value->AsObject() : nullptr;
                    if (!Position.IsValid()) continue;
                    FMikdashCodexPosition Row2;
                    Row2.Who = TextField(Position, TEXT("who"));
                    Row2.Holds = TextField(Position, TEXT("holds"));
                    Entry.Positions.Add(Row2);
                }
            }
        }

        TextArrayField(Object, TEXT("sources"), Entry.Sources);
        TextArrayField(Object, TEXT("receipts"), Entry.Receipts);
        NameArrayField(Object, TEXT("unlockedBy"), Entry.UnlockedBy);
        NameArrayField(Object, TEXT("related"), Entry.Related);

        const TSharedPtr<FJsonObject>* Narration = nullptr;
        if (Object->TryGetObjectField(TEXT("narrationAudio"), Narration) && Narration != nullptr)
        {
            (*Narration)->TryGetStringField(TEXT("asset"), Entry.NarrationAudioAsset);
        }

        // A disputed entry that does not name the disagreement is the failure mode this
        // whole file exists to prevent. Warn loudly; do not refuse the load, because a
        // half-written entry is still better read than hidden.
        if (Entry.Confidence == EMikdashConfidence::Disputed && Entry.Positions.Num() < 2)
        {
            UE_LOG(LogMikdashCodex, Warning,
                   TEXT("Codex entry \"%s\" is labelled disputed but names %d position(s). Name who holds what."),
                   *Id, Entry.Positions.Num());
        }
        if (Entry.Confidence != EMikdashConfidence::Authored && Entry.Sources.Num() == 0)
        {
            UE_LOG(LogMikdashCodex, Warning,
                   TEXT("Codex entry \"%s\" claims %s but cites nothing."),
                   *Id, *ConfidenceText);
        }

        NewIndex.Add(Entry.Id, NewEntries.Num());
        if (!NewCategories.Contains(Entry.Category))
        {
            NewCategories.Add(Entry.Category);
            NewCategoryNames.Add(Entry.Category, FText::FromName(Entry.Category));
        }
        NewEntries.Add(MoveTemp(Entry));
    }

    Entries = MoveTemp(NewEntries);
    IndexById = MoveTemp(NewIndex);
    Categories = MoveTemp(NewCategories);
    CategoryNames = MoveTemp(NewCategoryNames);
    ConfidenceDefinitions = MoveTemp(NewDefinitions);
    bLoaded = true;

    UE_LOG(LogMikdashCodex, Log, TEXT("Codex loaded: %d entries (%d certain, %d disputed, %d authored) from %s"),
           Entries.Num(),
           CountByConfidence(EMikdashConfidence::Certain),
           CountByConfidence(EMikdashConfidence::Disputed),
           CountByConfidence(EMikdashConfidence::Authored),
           *Path);
    return true;
}

int32 AMikdashCodex::IndexOf(FName EntryId) const
{
    const int32* Found = IndexById.Find(EntryId);
    return Found ? *Found : INDEX_NONE;
}

bool AMikdashCodex::GetEntry(FName EntryId, FMikdashCodexEntry& OutEntry) const
{
    return GetEntryAt(IndexOf(EntryId), OutEntry);
}

bool AMikdashCodex::GetEntryAt(int32 Index, FMikdashCodexEntry& OutEntry) const
{
    if (!Entries.IsValidIndex(Index)) return false;
    OutEntry = Entries[Index];
    return true;
}

FText AMikdashCodex::GetCategoryName(FName CategoryId) const
{
    const FText* Found = CategoryNames.Find(CategoryId);
    return Found ? *Found : FText::FromName(CategoryId);
}

TArray<int32> AMikdashCodex::IndicesInCategory(FName CategoryId) const
{
    TArray<int32> Out;
    const bool bAll = CategoryId.IsNone() || CategoryId == FName(TEXT("all"));
    for (int32 Index = 0; Index < Entries.Num(); ++Index)
    {
        if (bAll || Entries[Index].Category == CategoryId) Out.Add(Index);
    }
    return Out;
}

FText AMikdashCodex::ConfidenceDisplayName(EMikdashConfidence Value)
{
    switch (Value)
    {
    case EMikdashConfidence::Certain:  return LOCTEXT("ConfidenceCertain", "Certain");
    case EMikdashConfidence::Disputed: return LOCTEXT("ConfidenceDisputed", "Disputed");
    case EMikdashConfidence::Authored: return LOCTEXT("ConfidenceAuthored", "Authored");
    }
    return LOCTEXT("ConfidenceUnknown", "Authored");
}

FText AMikdashCodex::ConfidenceDefinition(EMikdashConfidence Value) const
{
    static const FName Keys[] = { FName(TEXT("certain")), FName(TEXT("disputed")), FName(TEXT("authored")) };
    const int32 Index = static_cast<int32>(Value);
    if (Index >= 0 && Index < static_cast<int32>(UE_ARRAY_COUNT(Keys)))
    {
        if (const FText* Found = ConfidenceDefinitions.Find(Keys[Index]))
        {
            if (!Found->IsEmpty()) return *Found;
        }
    }
    // Fallbacks, used only when the JSON did not carry the definitions.
    switch (Value)
    {
    case EMikdashConfidence::Certain:  return LOCTEXT("DefCertain", "The sources agree, or one is decisive and nothing cited disputes it.");
    case EMikdashConfidence::Disputed: return LOCTEXT("DefDisputed", "The sources disagree. The entry names who holds what.");
    default:                           return LOCTEXT("DefAuthored", "Nobody said this. The project chose it because a model has to put something somewhere.");
    }
}

int32 AMikdashCodex::CountByConfidence(EMikdashConfidence Value) const
{
    int32 Total = 0;
    for (const FMikdashCodexEntry& Entry : Entries)
    {
        if (Entry.Confidence == Value) ++Total;
    }
    return Total;
}

int32 AMikdashCodex::UnlockForStop(FName StopKey)
{
    int32 Opened = 0;
    for (const FMikdashCodexEntry& Entry : Entries)
    {
        if (Entry.UnlockedBy.Contains(StopKey) && UnlockEntry(Entry.Id)) ++Opened;
    }
    return Opened;
}

bool AMikdashCodex::UnlockEntry(FName EntryId)
{
    if (IndexOf(EntryId) == INDEX_NONE) return false;
    bool bAlready = false;
    Unlocked.Add(EntryId, &bAlready);
    if (!bAlready) OnEntryUnlocked.Broadcast(EntryId);
    return !bAlready;
}

void AMikdashCodex::UnlockAll()
{
    for (const FMikdashCodexEntry& Entry : Entries) UnlockEntry(Entry.Id);
}

void AMikdashCodex::ResetUnlocked()
{
    Unlocked.Reset();
}

bool AMikdashCodex::IsUnlocked(FName EntryId) const
{
    return Unlocked.Contains(EntryId);
}

TArray<FName> AMikdashCodex::EntriesWithNoUnlock() const
{
    TArray<FName> Out;
    for (const FMikdashCodexEntry& Entry : Entries)
    {
        if (Entry.UnlockedBy.Num() == 0) Out.Add(Entry.Id);
    }
    return Out;
}

#undef LOCTEXT_NAMESPACE
