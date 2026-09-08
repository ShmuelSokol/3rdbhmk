// MikdashLocalization.cpp -- string data, the glossary, the Hebrew face and RTL layout.
//
// The mirroring arithmetic is NOT here. It is in MikdashRtl inside SaveMigrationMath.h,
// which compiles without Unreal and is exercised by Tests/SaveMigrationMathTest.cpp. This
// file is the engine layer: read the data, register the table, set the culture, build the
// composite font, and forward the layout sums.

#include "MikdashLocalization.h"

#include "Components/Widget.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/FontFace.h"
#include "Fonts/CompositeFont.h"
#include "HAL/IConsoleManager.h"
#include "Internationalization/Internationalization.h"
#include "Internationalization/StringTableRegistry.h"
#include "Layout/FlowDirection.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Styling/CoreStyle.h"

#include "MikdashSettings.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashLoc, Log, All);

namespace
{
    /**
     * Read a UTF-8 file without trusting the platform's text heuristics.
     *
     * FFileHelper::LoadFileToString decides the encoding from a byte-order mark and
     * guesses when there is none. The author will edit strings.json in whatever editor he
     * likes, and a Hebrew string that silently arrives as Latin-1 mojibake is worse than a
     * refused load, so the bytes are read raw and converted as UTF-8 explicitly.
     */
    bool LoadUtf8File(const FString& Path, FString& OutText)
    {
        TArray<uint8> Bytes;
        if (!FFileHelper::LoadFileToArray(Bytes, *Path))
        {
            return false;
        }
        int32 Offset = 0;
        if (Bytes.Num() >= 3 && Bytes[0] == 0xEF && Bytes[1] == 0xBB && Bytes[2] == 0xBF)
        {
            Offset = 3;   // UTF-8 BOM
        }
        Bytes.Add(0);
        OutText = FString(UTF8_TO_TCHAR(reinterpret_cast<const ANSICHAR*>(Bytes.GetData() + Offset)));
        return true;
    }

    EMikdashStringStatus ParseStatus(const FString& In)
    {
        if (In.Equals(TEXT("confident"), ESearchCase::IgnoreCase))    { return EMikdashStringStatus::Confident; }
        if (In.Equals(TEXT("needs_review"), ESearchCase::IgnoreCase)) { return EMikdashStringStatus::NeedsReview; }
        if (In.Equals(TEXT("needs-review"), ESearchCase::IgnoreCase)) { return EMikdashStringStatus::NeedsReview; }
        return EMikdashStringStatus::Missing;
    }
}

// ---------------------------------------------------------------------------
// lifetime
// ---------------------------------------------------------------------------

void UMikdashLocalization::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    if (StringDataSearchPaths.Num() == 0)
    {
        // SourceAssets first, on purpose. In a development tree that is the file the
        // author edits; a stale copy under Content must never win over the correction he
        // just made. In a packaged build the SourceAssets folder is simply not there and
        // the cooked copy is used.
        StringDataSearchPaths = {
            TEXT("SourceAssets/localization-review/strings.json"),
            TEXT("Content/Localization/Mikdash/strings.json"),
        };
    }
    if (FontSearchPaths.Num() == 0)
    {
        FontSearchPaths = {
            TEXT("Content/MikdashV3/Fonts"),
            TEXT("SourceAssets/localization-review/fonts"),
        };
    }

    LoadStringData();
    BuildFonts();

    // Pick the language up from the settings subsystem, which owns it and has already
    // read the settings file by the time a game-instance subsystem initialises.
    if (const UGameInstance* Instance = GetGameInstance())
    {
        if (const UMikdashSettingsSubsystem* Settings = Instance->GetSubsystem<UMikdashSettingsSubsystem>())
        {
            Language = Settings->Get().Language == MikdashSettings::ELanguage::Hebrew
                ? EMikdashLanguage::Hebrew : EMikdashLanguage::English;
        }
    }

    ApplyCultureToEngine();
    RegisterStringTable();

    UE_LOG(LogMikdashLoc, Log,
           TEXT("Mikdash localization: %d strings (%d confident, %d flagged), %d glossary terms, language %s, Hebrew face %s"),
           Status.StringCount, Status.StringsConfident, Status.StringsFlagged, Status.GlossaryCount,
           Language == EMikdashLanguage::Hebrew ? TEXT("he") : TEXT("en"),
           Status.bFontFound ? *Status.FontFile : TEXT("NOT FOUND"));
}

void UMikdashLocalization::Deinitialize()
{
    FStringTableRegistry::Get().UnregisterStringTable(FName(*StringTableId));
    RegularFont.Reset();
    BoldFont.Reset();
    Super::Deinitialize();
}

UMikdashLocalization* UMikdashLocalization::Get(const UObject* WorldContext)
{
    if (!WorldContext)
    {
        return nullptr;
    }
    const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
    UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
    return Instance ? Instance->GetSubsystem<UMikdashLocalization>() : nullptr;
}

// ---------------------------------------------------------------------------
// data
// ---------------------------------------------------------------------------

bool UMikdashLocalization::LoadStringData()
{
    Entries.Reset();
    KeyOrder.Reset();
    Terms.Reset();
    TermOrder.Reset();
    Status = FMikdashLocalizationStatus();

    FString Text;
    FString Chosen;
    for (const FString& Relative : StringDataSearchPaths)
    {
        const FString Candidate = FPaths::Combine(FPaths::ProjectDir(), Relative);
        if (LoadUtf8File(Candidate, Text))
        {
            Chosen = Candidate;
            break;
        }
    }
    if (Chosen.IsEmpty())
    {
        Status.Problem = TEXT("No strings.json found on any search path; the build will show raw keys.");
        UE_LOG(LogMikdashLoc, Error, TEXT("%s"), *Status.Problem);
        return false;
    }
    Status.SourcePath = Chosen;

    TSharedPtr<FJsonObject> Root;
    const TSharedRef<TJsonReader<TCHAR>> Reader = TJsonReaderFactory<TCHAR>::Create(Text);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        // A syntax error in the author's own edit. Said plainly, with the path, because he
        // is the one who will have introduced it and he needs to know which file to fix.
        Status.Problem = FString::Printf(TEXT("%s is not valid JSON; nothing was loaded and the build will show English keys."), *Chosen);
        UE_LOG(LogMikdashLoc, Error, TEXT("%s"), *Status.Problem);
        return false;
    }

    const TArray<TSharedPtr<FJsonValue>>* EntryArray = nullptr;
    if (Root->TryGetArrayField(TEXT("entries"), EntryArray) && EntryArray)
    {
        for (const TSharedPtr<FJsonValue>& Value : *EntryArray)
        {
            const TSharedPtr<FJsonObject>* Object = nullptr;
            if (!Value.IsValid() || !Value->TryGetObject(Object) || !Object || !Object->IsValid())
            {
                continue;
            }
            FString Key;
            if (!(*Object)->TryGetStringField(TEXT("key"), Key) || Key.IsEmpty())
            {
                continue;
            }

            FEntry Entry;
            (*Object)->TryGetStringField(TEXT("en"), Entry.English);
            (*Object)->TryGetStringField(TEXT("he"), Entry.Hebrew);
            FString StatusText;
            (*Object)->TryGetStringField(TEXT("status"), StatusText);
            Entry.Status = ParseStatus(StatusText);
            if (Entry.Hebrew.IsEmpty())
            {
                Entry.Status = EMikdashStringStatus::Missing;
            }

            const FName KeyName(*Key);
            if (!Entries.Contains(KeyName))
            {
                KeyOrder.Add(KeyName);
            }
            Entries.Add(KeyName, Entry);
        }
    }

    const TArray<TSharedPtr<FJsonValue>>* GlossaryArray = nullptr;
    if (Root->TryGetArrayField(TEXT("glossary"), GlossaryArray) && GlossaryArray)
    {
        for (const TSharedPtr<FJsonValue>& Value : *GlossaryArray)
        {
            const TSharedPtr<FJsonObject>* Object = nullptr;
            if (!Value.IsValid() || !Value->TryGetObject(Object) || !Object || !Object->IsValid())
            {
                continue;
            }
            FString Id;
            if (!(*Object)->TryGetStringField(TEXT("id"), Id) || Id.IsEmpty())
            {
                continue;
            }

            FMikdashTerm Term;
            Term.Id = FName(*Id);
            (*Object)->TryGetStringField(TEXT("hebrew"), Term.Hebrew);
            (*Object)->TryGetStringField(TEXT("translit"), Term.Transliteration);
            (*Object)->TryGetStringField(TEXT("glossEn"), Term.GlossEn);
            (*Object)->TryGetStringField(TEXT("glossHe"), Term.GlossHe);
            (*Object)->TryGetStringField(TEXT("note"), Term.Note);
            FString StatusText;
            (*Object)->TryGetStringField(TEXT("status"), StatusText);
            Term.Status = ParseStatus(StatusText);
            Term.bValid = !Term.Hebrew.IsEmpty();

            if (!Terms.Contains(Term.Id))
            {
                TermOrder.Add(Term.Id);
            }
            Terms.Add(Term.Id, Term);
        }
    }

    // Counted here rather than trusted from the file's own "counts" block: the file is
    // hand-edited, so the block can be stale while the entries are correct, and the number
    // reported to the author has to be the one that is actually loaded.
    Status.StringCount = Entries.Num();
    for (const TPair<FName, FEntry>& Pair : Entries)
    {
        if (Pair.Value.Status == EMikdashStringStatus::Confident) { ++Status.StringsConfident; }
        else { ++Status.StringsFlagged; }
    }
    Status.GlossaryCount = Terms.Num();
    for (const TPair<FName, FMikdashTerm>& Pair : Terms)
    {
        if (Pair.Value.Status == EMikdashStringStatus::Confident) { ++Status.GlossaryConfident; }
        else { ++Status.GlossaryFlagged; }
    }
    Status.bLoaded = Status.StringCount > 0;
    if (!Status.bLoaded)
    {
        Status.Problem = FString::Printf(TEXT("%s parsed but held no entries."), *Chosen);
    }
    return Status.bLoaded;
}

bool UMikdashLocalization::ReloadStrings()
{
    const bool bLoaded = LoadStringData();
    RegisterStringTable();
    OnLanguageChanged.Broadcast(Language);
    return bLoaded;
}

const UMikdashLocalization::FEntry* UMikdashLocalization::FindEntry(FName Key) const
{
    return Entries.Find(Key);
}

FString UMikdashLocalization::Resolve(const FEntry& Entry) const
{
    if (Language == EMikdashLanguage::Hebrew && !Entry.Hebrew.IsEmpty())
    {
        // Flagged Hebrew is NOT shown. Those lines are waiting on the author, and a line
        // he has not approved reaching a visitor is exactly what the flag exists to stop.
        // bShowFlaggedHebrew turns them on for his own review pass.
        if (Entry.Status == EMikdashStringStatus::Confident || bShowFlaggedHebrew)
        {
            return Entry.Hebrew;
        }
    }
    return Entry.English;
}

void UMikdashLocalization::RegisterStringTable()
{
    const FName TableId(*StringTableId);

    // Unregister first: Internal_NewLocTable on a live id leaves the old entries in place
    // for keys the new data no longer has, which would resurrect a string the author has
    // deleted. A clean rebuild is the only way a reload means what it says.
    FStringTableRegistry::Get().UnregisterStringTable(TableId);
    FStringTableRegistry::Get().Internal_NewLocTable(TableId, FTextKey(*StringTableNamespace));

    for (const FName& Key : KeyOrder)
    {
        if (const FEntry* Entry = Entries.Find(Key))
        {
            FStringTableRegistry::Get().Internal_SetLocTableEntry(TableId, FTextKey(*Key.ToString()), Resolve(*Entry));
        }
    }
}

// ---------------------------------------------------------------------------
// strings
// ---------------------------------------------------------------------------

FText UMikdashLocalization::Text(FName Key) const
{
    if (const FEntry* Entry = FindEntry(Key))
    {
        return FText::FromString(Resolve(*Entry));
    }
    // Loud rather than blank. A missing key that renders as nothing is invisible in a
    // screenshot and survives to a build; one that renders as <menu.newThing> does not.
    return FText::FromString(FString::Printf(TEXT("<%s>"), *Key.ToString()));
}

FText UMikdashLocalization::TextFormat(FName Key, const TArray<FText>& Arguments) const
{
    FFormatOrderedArguments Ordered;
    Ordered.Reserve(Arguments.Num());
    for (const FText& Argument : Arguments)
    {
        Ordered.Add(FFormatArgumentValue(Argument));
    }
    return FText::Format(FTextFormat(Text(Key)), Ordered);
}

FText UMikdashLocalization::TextStatic(const UObject* WorldContext, FName Key)
{
    if (const UMikdashLocalization* Loc = Get(WorldContext))
    {
        return Loc->Text(Key);
    }
    return FText::FromString(FString::Printf(TEXT("<%s>"), *Key.ToString()));
}

bool UMikdashLocalization::HasKey(FName Key) const
{
    return Entries.Contains(Key);
}

EMikdashStringStatus UMikdashLocalization::GetKeyStatus(FName Key) const
{
    const FEntry* Entry = FindEntry(Key);
    return Entry ? Entry->Status : EMikdashStringStatus::Missing;
}

FString UMikdashLocalization::GetSourceString(FName Key) const
{
    const FEntry* Entry = FindEntry(Key);
    return Entry ? Entry->English : FString();
}

TArray<FName> UMikdashLocalization::GetAllKeys() const
{
    TArray<FName> Keys = KeyOrder;
    Keys.Sort([](const FName& A, const FName& B) { return A.ToString() < B.ToString(); });
    return Keys;
}

// ---------------------------------------------------------------------------
// glossary
// ---------------------------------------------------------------------------

FMikdashTerm UMikdashLocalization::GetTerm(FName TermId) const
{
    if (const FMikdashTerm* Found = Terms.Find(TermId))
    {
        return *Found;
    }
    return FMikdashTerm();
}

TArray<FMikdashTerm> UMikdashLocalization::GetAllTerms() const
{
    TArray<FMikdashTerm> Out;
    Out.Reserve(TermOrder.Num());
    for (const FName& Id : TermOrder)
    {
        if (const FMikdashTerm* Found = Terms.Find(Id))
        {
            Out.Add(*Found);
        }
    }
    return Out;
}

FText UMikdashLocalization::Term(FName TermId) const
{
    const FMikdashTerm Found = GetTerm(TermId);
    if (!Found.bValid)
    {
        return FText::FromString(FString::Printf(TEXT("<term:%s>"), *TermId.ToString()));
    }
    if (Language == EMikdashLanguage::Hebrew)
    {
        return FText::FromString(Found.Hebrew);
    }
    // The English build shows the transliteration from the author's book, never an English
    // translation. "Heikhal", not "Sanctuary". That is the whole reason this glossary
    // exists rather than a set of ordinary translated strings.
    return FText::FromString(Found.Transliteration.IsEmpty() ? Found.Hebrew : Found.Transliteration);
}

FText UMikdashLocalization::TermWithGlossAlways(FName TermId) const
{
    const FMikdashTerm Found = GetTerm(TermId);
    if (!Found.bValid)
    {
        return Term(TermId);
    }

    const FText Bare = Term(TermId);
    const FString Gloss = Language == EMikdashLanguage::Hebrew ? Found.GlossHe : Found.GlossEn;

    // An empty gloss is the author reserving the wording (korban, tamid). Rendering
    // "korban ()" would advertise the gap; the bare term simply reads correctly.
    if (Gloss.IsEmpty())
    {
        return Bare;
    }
    // In Hebrew the gloss is usually the same word with its definite article, and
    // "היכל (ההיכל)" is noise. Only a gloss that says something different is shown.
    if (Language == EMikdashLanguage::Hebrew && Gloss == Found.Hebrew)
    {
        return Bare;
    }
    return FText::FromString(FString::Printf(TEXT("%s (%s)"), *Bare.ToString(), *Gloss));
}

FText UMikdashLocalization::TermWithGloss(FName TermId)
{
    if (IntroducedTerms.Contains(TermId))
    {
        return Term(TermId);
    }
    IntroducedTerms.Add(TermId);
    return TermWithGlossAlways(TermId);
}

void UMikdashLocalization::MarkTermIntroduced(FName TermId)
{
    IntroducedTerms.Add(TermId);
}

bool UMikdashLocalization::WasTermIntroduced(FName TermId) const
{
    return IntroducedTerms.Contains(TermId);
}

void UMikdashLocalization::ResetIntroducedTerms()
{
    IntroducedTerms.Reset();
}

// ---------------------------------------------------------------------------
// language
// ---------------------------------------------------------------------------

FString UMikdashLocalization::GetCultureCode() const
{
    return Language == EMikdashLanguage::Hebrew ? TEXT("he-IL") : TEXT("en");
}

void UMikdashLocalization::ApplyCultureToEngine()
{
    const FString Culture = GetCultureCode();

    // SetCurrentLanguageAndLocale rather than SetCurrentCulture: the language drives
    // localization lookup and the locale drives number and date formatting, and the two
    // are set together here because a Hebrew UI with English date formatting reads wrong.
    // Verified against Core/Public/Internationalization/Internationalization.h in UE 5.8.
    FInternationalization::Get().SetCurrentLanguageAndLocale(Culture);

    // Without this the window root stays left to right and only widgets that explicitly
    // ask for Culture flip, which produces the worst possible result: a mirrored panel
    // inside an unmirrored frame. Verified against SlateCore/Private/Layout/FlowDirection.cpp.
    if (IConsoleVariable* Variable = IConsoleManager::Get().FindConsoleVariable(TEXT("Slate.ShouldFollowCultureByDefault")))
    {
        Variable->Set(1, ECVF_SetByGameSetting);
    }
    if (IConsoleVariable* Variable = IConsoleManager::Get().FindConsoleVariable(TEXT("Slate.EnableLayoutLocalization")))
    {
        Variable->Set(1, ECVF_SetByGameSetting);
    }
}

void UMikdashLocalization::SetLanguage(EMikdashLanguage NewLanguage)
{
    if (NewLanguage == Language)
    {
        return;
    }
    Language = NewLanguage;
    ApplyCultureToEngine();
    RegisterStringTable();

    // A term glossed in English is not glossed in Hebrew, so the "already introduced" set
    // is meaningless across a language change and is cleared rather than carried over.
    ResetIntroducedTerms();

    OnLanguageChanged.Broadcast(Language);
}

// ---------------------------------------------------------------------------
// right-to-left layout
// ---------------------------------------------------------------------------

MikdashRtl::EFlow UMikdashLocalization::Flow() const
{
    // Derived from the culture code through the same function the standalone test drives,
    // not from FLayoutLocalization, so the answer is identical in the test and in the
    // build and cannot depend on whether Slate has ticked this frame.
    const FString Culture = GetCultureCode();
    // Get() is const UTF8CHAR* (char8_t here), and LayoutDirectionForCulture takes a plain
    // const char*. Culture codes are ASCII, so the reinterpret_cast is exact.
    const FTCHARToUTF8 Converted(*Culture);
    return MikdashRtl::LayoutDirectionForCulture(reinterpret_cast<const char*>(Converted.Get()));
}

bool UMikdashLocalization::IsRightToLeft() const
{
    return MikdashRtl::IsRightToLeft(Flow());
}

EFlowDirection UMikdashLocalization::GetFlowDirection() const
{
    return IsRightToLeft() ? EFlowDirection::RightToLeft : EFlowDirection::LeftToRight;
}

void UMikdashLocalization::ApplyLayoutDirection(UWidget* Widget) const
{
    if (Widget)
    {
        Widget->SetFlowDirectionPreference(EFlowDirectionPreference::Culture);
    }
}

FMargin UMikdashLocalization::Mirror(const FMargin& AuthoredLeftToRight) const
{
    if (!IsRightToLeft())
    {
        return AuthoredLeftToRight;
    }
    MikdashRtl::FMargin In;
    In.Left = AuthoredLeftToRight.Left;
    In.Top = AuthoredLeftToRight.Top;
    In.Right = AuthoredLeftToRight.Right;
    In.Bottom = AuthoredLeftToRight.Bottom;
    const MikdashRtl::FMargin Out = MikdashRtl::MirrorMargin(In);
    return FMargin(static_cast<float>(Out.Left), static_cast<float>(Out.Top),
                   static_cast<float>(Out.Right), static_cast<float>(Out.Bottom));
}

float UMikdashLocalization::MirrorAlignment(float Authored) const
{
    return IsRightToLeft() ? static_cast<float>(MikdashRtl::MirrorAlignment(Authored)) : Authored;
}

float UMikdashLocalization::MirrorLeft(float Left, float ChildWidth, float ParentWidth) const
{
    return IsRightToLeft()
        ? static_cast<float>(MikdashRtl::MirrorLeft(Left, ChildWidth, ParentWidth))
        : Left;
}

void UMikdashLocalization::ProgressFill(float Fraction, float TrackWidth, float& OutLeft, float& OutWidth) const
{
    const MikdashRtl::FFillSpan Span = MikdashRtl::ProgressFill(Fraction, TrackWidth, Flow());
    OutLeft = static_cast<float>(Span.Offset);
    OutWidth = static_cast<float>(Span.Width);
}

float UMikdashLocalization::SliderHandleCentre(float Fraction, float TrackWidth, float HandleWidth) const
{
    return static_cast<float>(MikdashRtl::SliderHandleCentre(Fraction, TrackWidth, HandleWidth, Flow()));
}

int32 UMikdashLocalization::MirrorChildIndex(int32 Index, int32 Count) const
{
    return IsRightToLeft() ? MikdashRtl::MirrorChildIndex(Index, Count) : Index;
}

float UMikdashLocalization::DirectionalSign() const
{
    return static_cast<float>(MikdashRtl::DirectionalSign(Flow()));
}

bool UMikdashLocalization::ShouldMirrorDirectionalIcon() const
{
    return MikdashRtl::ShouldMirrorDirectionalIcon(Flow());
}

EMikdashJustify UMikdashLocalization::NaturalJustify() const
{
    return static_cast<EMikdashJustify>(MikdashRtl::NaturalJustify(Flow()));
}

EMikdashJustify UMikdashLocalization::MirrorJustify(EMikdashJustify Authored) const
{
    if (!IsRightToLeft())
    {
        return Authored;
    }
    return static_cast<EMikdashJustify>(
        MikdashRtl::MirrorJustify(static_cast<MikdashRtl::EJustify>(static_cast<int32>(Authored))));
}

// ---------------------------------------------------------------------------
// fonts
// ---------------------------------------------------------------------------

FString UMikdashLocalization::ResolveFontPath(const FString& FileName) const
{
    if (FileName.IsEmpty())
    {
        return FString();
    }
    for (const FString& Folder : FontSearchPaths)
    {
        const FString Candidate = FPaths::Combine(FPaths::ProjectDir(), Folder, FileName);
        if (FPaths::FileExists(Candidate))
        {
            return FPaths::ConvertRelativePathToFull(Candidate);
        }
    }
    return FString();
}

void UMikdashLocalization::BuildFonts()
{
    ResolvedHebrewFontPath = ResolveFontPath(HebrewFontFile);
    ResolvedHebrewBoldFontPath = ResolveFontPath(HebrewBoldFontFile);
    if (ResolvedHebrewBoldFontPath.IsEmpty())
    {
        ResolvedHebrewBoldFontPath = ResolvedHebrewFontPath;
    }

    // A cooked font-face asset wins over a loose file when the release script has made
    // one, because that is the copy a packaged build actually has.
    UObject* FaceAsset = HebrewFontFaceAsset.IsValid() ? HebrewFontFaceAsset.TryLoad() : nullptr;
    UObject* BoldFaceAsset = HebrewBoldFontFaceAsset.IsValid() ? HebrewBoldFontFaceAsset.TryLoad() : nullptr;
    if (FaceAsset && !FaceAsset->IsA<UFontFace>()) { FaceAsset = nullptr; }
    if (BoldFaceAsset && !BoldFaceAsset->IsA<UFontFace>()) { BoldFaceAsset = nullptr; }
    if (FaceAsset && !BoldFaceAsset) { BoldFaceAsset = FaceAsset; }

    bUsingFontFaceAssets = FaceAsset != nullptr;
    Status.bFontFromAsset = bUsingFontFaceAssets;
    Status.FontFile = bUsingFontFaceAssets ? HebrewFontFaceAsset.ToString() : HebrewFontFile;
    Status.bFontFound = bUsingFontFaceAssets || !ResolvedHebrewFontPath.IsEmpty();

    if (!Status.bFontFound)
    {
        const FString Problem = FString::Printf(
            TEXT("No Hebrew face: neither the font-face asset '%s' nor the file '%s' under any of %d search paths. Hebrew text will draw as boxes."),
            *HebrewFontFaceAsset.ToString(), *HebrewFontFile, FontSearchPaths.Num());
        Status.Problem = Status.Problem.IsEmpty() ? Problem : Status.Problem + TEXT(" ") + Problem;
        UE_LOG(LogMikdashLoc, Error, TEXT("%s"), *Problem);
        return;
    }

    const FString LatinPath = FPaths::Combine(FPaths::EngineContentDir(), LatinFontFile);
    const FString LatinBoldPath = FPaths::Combine(FPaths::EngineContentDir(), LatinBoldFontFile);

    // The Hebrew ranges. U+0590..U+05FF is the Hebrew block: letters, nikud, cantillation
    // and punctuation. U+FB1D..U+FB4F is Hebrew presentation forms, which is where the
    // precomposed shin-with-dot and the ligatures live; text that has been through an
    // Israeli word processor often carries them and they would otherwise fall back to a
    // face that does not have them.
    auto AddHebrewSubFont = [this](FStandaloneCompositeFont& Composite, UObject* Asset, const FString& Path)
    {
        FCompositeSubFont SubFont;
        FTypefaceEntry Entry(TEXT("Regular"));
        if (Asset)
        {
            Entry.Font = FFontData(Asset);
        }
        else
        {
            Entry.Font = FFontData(Path, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
        }
        SubFont.Typeface.Fonts.Add(MoveTemp(Entry));
        SubFont.CharacterRanges.Add(FInt32Range::Inclusive(0x0590, 0x05FF));
        SubFont.CharacterRanges.Add(FInt32Range::Inclusive(0xFB1D, 0xFB4F));
        SubFont.ScalingFactor = HebrewFontScale;
        Composite.SubTypefaces.Add(MoveTemp(SubFont));
    };

    // Default typeface stays the Latin face the rest of the interface already uses, so a
    // mixed line -- "1 amah = 0.5 m" -- keeps one Latin face rather than picking up the
    // Hebrew font's own Latin, which is a different design and reads as a mistake.
    RegularFont = MakeShared<FStandaloneCompositeFont>(
        TEXT("Regular"), LatinPath, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
    AddHebrewSubFont(*RegularFont, FaceAsset, ResolvedHebrewFontPath);

    BoldFont = MakeShared<FStandaloneCompositeFont>(
        TEXT("Bold"), LatinBoldPath, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
    AddHebrewSubFont(*BoldFont, BoldFaceAsset, ResolvedHebrewBoldFontPath);
}

FSlateFontInfo UMikdashLocalization::GetFont(float Size) const
{
    const float Clamped = FMath::Clamp(Size, 4.0f, 256.0f);
    if (RegularFont.IsValid())
    {
        return FSlateFontInfo(RegularFont, Clamped);
    }
    // Never an invalid FSlateFontInfo: a null font in Slate is a crash, and a missing
    // Hebrew face should cost boxes, not a shipped build that will not draw a menu.
    return FCoreStyle::GetDefaultFontStyle("Regular", Clamped);
}

FSlateFontInfo UMikdashLocalization::GetBoldFont(float Size) const
{
    const float Clamped = FMath::Clamp(Size, 4.0f, 256.0f);
    if (BoldFont.IsValid())
    {
        return FSlateFontInfo(BoldFont, Clamped);
    }
    return FCoreStyle::GetDefaultFontStyle("Bold", Clamped);
}

FString UMikdashLocalization::GetHebrewFontPath() const
{
    return ResolvedHebrewFontPath;
}
