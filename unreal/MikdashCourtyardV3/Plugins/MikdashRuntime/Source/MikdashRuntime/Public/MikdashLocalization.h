// MikdashLocalization.h -- Hebrew as a first-class language, not a string swap.
//
// Four separate problems live behind the word "Hebrew", and this file addresses them as
// four separate things because doing only the first is what makes a build look translated
// and read wrong.
//
//   1. THE STRINGS are data, not code. Every line of the interface comes from
//      SourceAssets/localization-review/strings.json, read at run time. The author is a
//      native speaker; he can correct any Hebrew line in that file and see it on the next
//      launch with no recompile, no cook and no editor. An entry whose Hebrew is empty or
//      still flagged for review falls back to the English string on screen, because an
//      English line is better than a wrong Hebrew one.
//
//   2. THE LAYOUT mirrors, not just the text. Slate reverses the glyph run through ICU on
//      its own. What it does not do is decide which end a progress bar fills from, which
//      side a panel's padding sits on, or where a slider handle is at 30%. Those sums are
//      in MikdashRtl (SaveMigrationMath.h) and are covered by the standalone test; this
//      file is the thin engine layer over them plus the one engine switch that matters,
//      Slate.ShouldFollowCultureByDefault, which makes the window root itself flip.
//
//   3. THE FONT has to contain the Hebrew block AND position nikud correctly. Slate's
//      default face (Roboto) has no Hebrew at all, so without this the Hebrew build draws
//      boxes. The font is wired as a composite: the default typeface keeps the Latin face
//      the rest of the UI already uses, and a sub-typeface covers U+0590..U+05FF and the
//      Hebrew presentation forms. Which face, and the evidence for choosing it, is in
//      SourceAssets/localization-review/font-audit.json, alongside a rendered specimen
//      PNG a human can actually look at.
//
//   4. THE SUBJECT'S OWN TERMS stay Hebrew in both builds. Heikhal, Kodesh HaKodashim,
//      mizbe'ach, menorah, shulchan, paroches, kohen, amah are not translated into English
//      in the English build; they are given once with a gloss and then used bare. That is
//      a glossary in data (the "glossary" array of strings.json), so the same term reads
//      the same way in a menu, a tour caption and a codex page without anyone remembering
//      to be consistent. Term(): the bare term. TermWithGloss(): the term plus its gloss,
//      which returns the bare form on every call after the first.
//
// Every API here was checked against UE 5.8 under
// C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime:
//   EFlowDirection / EFlowDirectionPreference / FLayoutLocalization  SlateCore/Public/Layout/FlowDirection.h
//   UWidget::SetFlowDirectionPreference                              UMG/Public/Components/Widget.h
//   FStandaloneCompositeFont / FCompositeSubFont / FTypeface         SlateCore/Public/Fonts/CompositeFont.h
//   FSlateFontInfo(TSharedPtr<const FCompositeFont>, float, ...)     SlateCore/Public/Fonts/SlateFontInfo.h
//   FStringTableRegistry::Internal_NewLocTable / _SetLocTableEntry   Core/Public/Internationalization/StringTableRegistry.h
//   FInternationalization::SetCurrentLanguageAndLocale               Core/Public/Internationalization/Internationalization.h
//
// The front end and menus are built entirely in C++ with no UMG designer step, and nothing
// here REQUIRES a .uasset: the strings come from a .json and the font from a .ttf read
// straight off disk, so the feature works in a development tree before any import has been
// run. Scripts/release_localization.py additionally imports the .ttf as a UFontFace asset,
// which this prefers when it exists, because a loose file under Content is not cooked into
// a package unless the project lists its folder -- and that is a project setting, not this
// module's to change.

#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
#include "Layout/Margin.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "UObject/SoftObjectPath.h"

#include "SaveMigrationMath.h"

#include "MikdashLocalization.generated.h"

enum class EFlowDirection : uint8;
struct FCompositeFont;
struct FStandaloneCompositeFont;
class UWidget;

/** The shipped languages. Matches MikdashSettings::ELanguage so the two never drift. */
UENUM(BlueprintType)
enum class EMikdashLanguage : uint8
{
    English UMETA(DisplayName = "English"),
    Hebrew  UMETA(DisplayName = "Hebrew"),
};

/**
 * Horizontal justification, mirrored by the RTL helpers below.
 *
 * Deliberately this module's own enum rather than ETextJustify::Type. ETextJustify lives
 * in Slate/Public/Framework/Text/TextLayout.h, and Slate is a PRIVATE dependency of both
 * this module and UMG, so naming it in a public header would force Slate on anything that
 * includes this file. The values are the same integers as ETextJustify::Type -- Left 0,
 * Center 1, Right 2, verified against UE 5.8 -- so a caller casts straight across:
 *
 *     TextBlock->SetJustification(static_cast<ETextJustify::Type>(Loc->NaturalJustify()));
 *
 * Tests/SaveMigrationMathTest.cpp asserts those three numbers, so if the engine ever
 * renumbers them the gate fails rather than the cast quietly producing nonsense.
 */
UENUM(BlueprintType)
enum class EMikdashJustify : uint8
{
    Left   UMETA(DisplayName = "Left"),
    Center UMETA(DisplayName = "Center"),
    Right  UMETA(DisplayName = "Right"),
};

/** How sure the author is of a line. Only Confident Hebrew is shown. */
UENUM(BlueprintType)
enum class EMikdashStringStatus : uint8
{
    Missing     UMETA(DisplayName = "No Hebrew yet"),
    NeedsReview UMETA(DisplayName = "Flagged for the author"),
    Confident   UMETA(DisplayName = "Confident"),
};

/**
 * One term of the subject's own vocabulary.
 *
 * Hebrew is the term itself, in Hebrew script, and it is what appears on screen in BOTH
 * builds. Transliteration is the Latin spelling used in the English build's running text
 * -- it follows the author's book, so "Heikhal" and "Kodesh HaKodashim", not a library
 * romanisation. GlossEn is the short English explanation attached on first use only.
 *
 * A term with an empty gloss is deliberate, not missing: korban and tamid are flagged in
 * the data because "sacrifice" and "offering" are not interchangeable and the choice is
 * the author's. Those render bare, with no parenthesis, until he fills them in.
 */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashTerm
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Glossary") FName Id;
    /** The term in Hebrew script. Shown in both builds. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Glossary") FString Hebrew;
    /** Latin spelling for the English build, per the author's book. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Glossary") FString Transliteration;
    /** Short English explanation. Empty where the author has reserved the wording. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Glossary") FString GlossEn;
    /** Short Hebrew explanation, usually the term with its definite article. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Glossary") FString GlossHe;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Glossary") EMikdashStringStatus Status = EMikdashStringStatus::Confident;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Glossary") FString Note;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Glossary") bool bValid = false;
};

/** What the last load of the string data found. Shown by the developer readout. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashLocalizationStatus
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") bool bLoaded = false;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") FString SourcePath;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") FString Problem;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") int32 StringCount = 0;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") int32 StringsConfident = 0;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") int32 StringsFlagged = 0;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") int32 GlossaryCount = 0;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") int32 GlossaryConfident = 0;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") int32 GlossaryFlagged = 0;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") FString FontFile;
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") bool bFontFound = false;
    /** True when a cooked UFontFace asset was used rather than a loose .ttf on disk. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Localization") bool bFontFromAsset = false;
};

/** Fired after the language changes and the string table has been rebuilt. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FMikdashLanguageChanged, EMikdashLanguage, Language);

/**
 * The localization subsystem.
 *
 * Read every visible string through Text(). Read every subject term through Term() or
 * TermWithGloss(). Lay out every panel through the mirroring helpers rather than by
 * hand-writing an FMargin, and a Hebrew build mirrors without any screen knowing it did.
 */
UCLASS(Config = Game, MinimalAPI)
class UMikdashLocalization : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    MIKDASHRUNTIME_API virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    MIKDASHRUNTIME_API virtual void Deinitialize() override;

    /** Null in a commandlet or cook. Callers must handle that; see TextStatic(). */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization", meta = (WorldContext = "WorldContext"))
    static MIKDASHRUNTIME_API UMikdashLocalization* Get(const UObject* WorldContext);

    // -- strings -----------------------------------------------------------

    /**
     * The visible text for a key.
     *
     * Hebrew is returned only when the entry's Hebrew is non-empty AND its status is
     * confident. Anything else falls back to the English source string. An unknown key
     * returns the key itself wrapped in angle brackets so a missing string is loud in a
     * screenshot instead of being an invisible blank.
     */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization")
    MIKDASHRUNTIME_API FText Text(FName Key) const;

    /** Text(Key) with {0}, {1}... substituted. Ordered arguments only, by design: a
     *  translator reordering the arguments is exactly what ordered placeholders allow. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Localization")
    MIKDASHRUNTIME_API FText TextFormat(FName Key, const TArray<FText>& Arguments) const;

    /** Same as Text(), usable where there is no world context. Falls back to the key. */
    static MIKDASHRUNTIME_API FText TextStatic(const UObject* WorldContext, FName Key);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization") MIKDASHRUNTIME_API bool HasKey(FName Key) const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization") MIKDASHRUNTIME_API EMikdashStringStatus GetKeyStatus(FName Key) const;

    /** English source string for a key, whatever the current language. For logs and receipts. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization") MIKDASHRUNTIME_API FString GetSourceString(FName Key) const;

    /** Every key, sorted. For the release script's readback and the developer readout. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Localization") MIKDASHRUNTIME_API TArray<FName> GetAllKeys() const;

    /** Re-read the data file without restarting. Bound to a console command in development. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Localization") MIKDASHRUNTIME_API bool ReloadStrings();

    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization") FMikdashLocalizationStatus GetStatus() const { return Status; }

    // -- the glossary ------------------------------------------------------

    UFUNCTION(BlueprintPure, Category = "Mikdash|Glossary") MIKDASHRUNTIME_API FMikdashTerm GetTerm(FName TermId) const;
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Glossary") MIKDASHRUNTIME_API TArray<FMikdashTerm> GetAllTerms() const;

    /**
     * The term as it should appear in running text.
     *
     * Hebrew build: the Hebrew word. English build: the transliteration from the author's
     * book. Never an English translation -- that is the whole point of the glossary.
     */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Glossary")
    MIKDASHRUNTIME_API FText Term(FName TermId) const;

    /**
     * The term with its gloss, once.
     *
     * The first call in a session for a given term returns "Heikhal (the Sanctuary)"; every
     * call after it returns "Heikhal". A term whose gloss the author has reserved returns
     * the bare term from the very first call, with no empty parenthesis.
     *
     * Call MarkTermIntroduced() when a term is shown by something that formats it itself,
     * and ResetIntroducedTerms() when the visitor starts a fresh walkthrough.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Glossary")
    MIKDASHRUNTIME_API FText TermWithGloss(FName TermId);

    /** The term with its gloss unconditionally. For a codex page heading. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Glossary")
    MIKDASHRUNTIME_API FText TermWithGlossAlways(FName TermId) const;

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Glossary") MIKDASHRUNTIME_API void MarkTermIntroduced(FName TermId);
    UFUNCTION(BlueprintPure, Category = "Mikdash|Glossary") MIKDASHRUNTIME_API bool WasTermIntroduced(FName TermId) const;
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Glossary") MIKDASHRUNTIME_API void ResetIntroducedTerms();

    // -- language ----------------------------------------------------------

    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization") EMikdashLanguage GetLanguage() const { return Language; }

    /**
     * Change language.
     *
     * Sets the engine culture (so ICU's own bidi and number formatting follow), flips the
     * Slate layout direction, rebuilds the string table and broadcasts. Screens rebuild
     * themselves from OnLanguageChanged; nothing here touches a widget.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Localization")
    MIKDASHRUNTIME_API void SetLanguage(EMikdashLanguage NewLanguage);

    /** ISO code actually pushed at the engine: "en" or "he-IL". */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization") MIKDASHRUNTIME_API FString GetCultureCode() const;

    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Localization") FMikdashLanguageChanged OnLanguageChanged;

    // -- right-to-left layout ----------------------------------------------

    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL") MIKDASHRUNTIME_API bool IsRightToLeft() const;

    /** The layout direction as Slate's own enum. Not a UFUNCTION: EFlowDirection is not a UENUM. */
    MIKDASHRUNTIME_API EFlowDirection GetFlowDirection() const;

    /**
     * Set a widget's flow preference to follow the culture.
     *
     * Every panel the front end builds should go through this rather than being left on
     * Inherit, because Inherit only propagates once something above it has decided. One
     * call at the root of each screen is enough; children inherit from there.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API void ApplyLayoutDirection(UWidget* Widget) const;

    /**
     * Padding authored left-to-right, swapped when the build is Hebrew.
     *
     * Authoring rule for the whole UI: write every margin as if the language were English
     * and pass it through here. Never write a mirrored margin by hand -- the arithmetic is
     * an involution and hand-mirroring one panel twice is how a layout drifts.
     */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API FMargin Mirror(const FMargin& AuthoredLeftToRight) const;

    /** Alignment 0..1 along the horizontal axis, mirrored when Hebrew. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API float MirrorAlignment(float Authored) const;

    /** Left edge of a child inside a parent, mirrored when Hebrew. Slate units. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API float MirrorLeft(float Left, float ChildWidth, float ParentWidth) const;

    /** Left edge and width of the filled part of a progress bar at Fraction of Track. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API void ProgressFill(float Fraction, float TrackWidth, float& OutLeft, float& OutWidth) const;

    /** Centre of a slider handle at Fraction, in the track's own space. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API float SliderHandleCentre(float Fraction, float TrackWidth, float HandleWidth) const;

    /** Index of the child that occupies visual position Index in a row of Count. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API int32 MirrorChildIndex(int32 Index, int32 Count) const;

    /** +1 left to right, -1 right to left. Multiply an X offset or a nudge by this. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API float DirectionalSign() const;

    /** True when a back arrow, a next chevron or a progress icon must be flipped. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API bool ShouldMirrorDirectionalIcon() const;

    /** Reading-edge justification: Left in English, Right in Hebrew. Cast to ETextJustify::Type. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API EMikdashJustify NaturalJustify() const;

    /** An explicitly authored justification, mirrored when Hebrew. Center is unchanged. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|RTL")
    MIKDASHRUNTIME_API EMikdashJustify MirrorJustify(EMikdashJustify Authored) const;

    // -- fonts -------------------------------------------------------------

    /**
     * A font that can draw both scripts at the requested size.
     *
     * The composite is built once: the default typeface is the Latin face the rest of the
     * UI already uses, and a sub-typeface covers U+0590..U+05FF plus the Hebrew
     * presentation forms U+FB1D..U+FB4F. Latin text in a Hebrew sentence therefore keeps
     * the same face it has in the English build, which is what makes a mixed line like
     * "1 amah = 0.5 m" look deliberate rather than patched.
     *
     * If the Hebrew .ttf cannot be found on disk this returns the engine's default font
     * and records the failure in GetStatus().Problem. It never returns an invalid
     * FSlateFontInfo, because a null font in Slate is a crash, not a missing glyph.
     */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization")
    MIKDASHRUNTIME_API FSlateFontInfo GetFont(float Size) const;

    /** Bold variant of the same composite. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization")
    MIKDASHRUNTIME_API FSlateFontInfo GetBoldFont(float Size) const;

    /** Absolute path of the Hebrew face actually in use, or empty when none was found. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Localization") MIKDASHRUNTIME_API FString GetHebrewFontPath() const;

    // -- configuration ([/Script/MikdashRuntime.MikdashLocalization] in DefaultGame.ini) --

    /** Table id other modules pass to FText::FromStringTable. */
    UPROPERTY(Config) FString StringTableId = TEXT("MikdashStrings");
    UPROPERTY(Config) FString StringTableNamespace = TEXT("Mikdash");

    /**
     * Where the string data is looked for, in order, relative to the project directory.
     * The authoring copy under SourceAssets is searched FIRST on purpose: in a development
     * tree that is the file the author edits, and a stale cooked copy must not win over
     * the correction he just made.
     */
    UPROPERTY(Config) TArray<FString> StringDataSearchPaths;

    /**
     * Imported UFontFace assets, preferred when they exist.
     *
     * A .ttf sitting loose under Content is NOT packaged unless the project lists its
     * folder under Packaging -> Additional Non-Asset Directories, which is a project
     * setting this module has no business editing. A UFontFace asset is a normal cooked
     * asset and needs no such entry, so Scripts/release_localization.py imports one and
     * this is where it is looked for. When the asset is missing the loose .ttf below is
     * used instead, which is what makes the feature work in a development tree before
     * the release script has ever been run.
     */
    UPROPERTY(Config) FSoftObjectPath HebrewFontFaceAsset;
    UPROPERTY(Config) FSoftObjectPath HebrewBoldFontFaceAsset;

    /** Hebrew face file name, looked for in FontSearchPaths. The fallback for the above. */
    UPROPERTY(Config) FString HebrewFontFile = TEXT("NotoSansHebrew-Regular.ttf");
    UPROPERTY(Config) FString HebrewBoldFontFile = TEXT("NotoSansHebrew-Bold.ttf");
    UPROPERTY(Config) TArray<FString> FontSearchPaths;

    /** Latin face for the default typeface. Relative to the engine content directory. */
    UPROPERTY(Config) FString LatinFontFile = TEXT("Slate/Fonts/Roboto-Regular.ttf");
    UPROPERTY(Config) FString LatinBoldFontFile = TEXT("Slate/Fonts/Roboto-Bold.ttf");

    /** Sub-font scale, so the Hebrew face's x-height matches the Latin one. */
    UPROPERTY(Config) float HebrewFontScale = 1.0f;

    /** Show flagged Hebrew rather than falling back to English. Development aid only. */
    UPROPERTY(Config) bool bShowFlaggedHebrew = false;

private:
    struct FEntry
    {
        FString English;
        FString Hebrew;
        EMikdashStringStatus Status = EMikdashStringStatus::Missing;
    };

    bool LoadStringData();
    void RegisterStringTable();
    void ApplyCultureToEngine();
    void BuildFonts();
    FString ResolveFontPath(const FString& FileName) const;
    const FEntry* FindEntry(FName Key) const;
    FString Resolve(const FEntry& Entry) const;

    MikdashRtl::EFlow Flow() const;

    TMap<FName, FEntry> Entries;
    TArray<FName> KeyOrder;
    TMap<FName, FMikdashTerm> Terms;
    TArray<FName> TermOrder;
    TSet<FName> IntroducedTerms;

    EMikdashLanguage Language = EMikdashLanguage::English;
    FMikdashLocalizationStatus Status;

    FString ResolvedHebrewFontPath;
    FString ResolvedHebrewBoldFontPath;
    /** Kept alive by the composite fonts' own FGCObject; recorded here for the status. */
    bool bUsingFontFaceAssets = false;

    TSharedPtr<FStandaloneCompositeFont> RegularFont;
    TSharedPtr<FStandaloneCompositeFont> BoldFont;
};
