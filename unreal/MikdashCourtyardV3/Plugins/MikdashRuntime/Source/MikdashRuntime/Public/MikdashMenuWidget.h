// MikdashMenuWidget.h -- every front-end screen, authored entirely in C++.
//
// There is no UMG designer step anywhere in this pipeline, so each screen is a
// UUserWidget subclass that builds its own tree with WidgetTree->ConstructWidget in
// NativeConstruct. Nothing here needs a .uasset, a Blueprint, or a font import: text
// uses FCoreStyle's default font, or a .ttf read straight off disk for Hebrew.
//
// Screens:
//   UMikdashMainMenuWidget      title, background camera move, five entries
//   UMikdashPauseMenuWidget     resume, settings, main menu, quit
//   UMikdashSettingsWidget      six pages covering graphics through accessibility
//   UMikdashCreditsWidget       scrolling credits, built from real data
//   UMikdashLoadingScreenWidget still image and a rotating line of text
//
// The screens do not know how to navigate. They call back into UMikdashFrontEnd,
// which owns the stack, the input mode and the pause state.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "Types/SlateEnums.h"

#include "MikdashSettings.h"

#include "MikdashMenuWidget.generated.h"

class UBorder;
class UButton;
class UCheckBox;
class UComboBoxString;
class UHorizontalBox;
class UImage;
class UMikdashFrontEnd;
class UOverlay;
class UPanelWidget;
class UScrollBox;
class USlider;
class UTextBlock;
class UVerticalBox;
class UWidgetSwitcher;

/**
 * One heading and its lines in the credits.
 *
 * The front end fills these from what is actually on disk under
 * SourceAssets/third-party plus the fixed acknowledgements, so a credit can never
 * drift away from the licence file that justifies it.
 */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashCreditsSection
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Credits") FText Heading;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Credits") TArray<FText> Lines;
};

/**
 * A UObject that turns a lambda into something UMG's dynamic delegates can bind.
 *
 * UMG events are DYNAMIC delegates, so they need a UFUNCTION on a UObject. Without
 * this every button on every page would need its own named handler, which is how a
 * C++-authored menu turns into six hundred lines of boilerplate. Instances are held
 * in the owning widget's Actions array so the garbage collector leaves them alone.
 */
UCLASS(MinimalAPI)
class UMikdashUiAction : public UObject
{
    GENERATED_BODY()
public:
    TFunction<void()> Clicked;
    TFunction<void(float)> FloatChanged;
    TFunction<void(bool)> BoolChanged;
    TFunction<void(FString, ESelectInfo::Type)> SelectionChanged;

    UFUNCTION() void HandleClicked();
    UFUNCTION() void HandleFloat(float Value);
    UFUNCTION() void HandleBool(bool bValue);
    UFUNCTION() void HandleSelection(FString Item, ESelectInfo::Type Info);
};

/**
 * Shared chrome and construction helpers for every front-end screen.
 *
 * Layout is always the same: a full-screen background layer, a centred panel, a
 * heading, a body the subclass fills, and a footer hint line. Fonts and colours come
 * from the settings subsystem, so the text-size scale and the colour-blind palette
 * apply to every screen without each screen knowing about them.
 */
UCLASS(MinimalAPI, Abstract)
class UMikdashMenuWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    MIKDASHRUNTIME_API virtual void NativeConstruct() override;
    MIKDASHRUNTIME_API virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& KeyEvent) override;

    /** Set before AddToViewport. The screen calls back into this for navigation. */
    UPROPERTY(Transient) TObjectPtr<UMikdashFrontEnd> FrontEnd;

    /** Rebuild the body in place. Used when the language or text scale changes. */
    MIKDASHRUNTIME_API void Rebuild();

protected:
    /** Subclasses fill the body column. Called from NativeConstruct and Rebuild. */
    virtual void BuildBody(UVerticalBox* Body) {}

    /** Heading shown at the top of the panel. */
    virtual FText GetHeading() const { return FText::GetEmpty(); }

    /** Small line under the buttons. Empty hides it. */
    virtual FText GetFooterHint() const { return FText::GetEmpty(); }

    /** Escape / gamepad B. Default does nothing so a main menu does not close itself. */
    virtual void HandleBack() {}

    /** How wide the centred panel is, in slate units before DPI scaling. */
    virtual float GetPanelWidth() const { return 760.0f; }

    /** When true the background layer is opaque, hiding the level behind it. */
    virtual bool WantsOpaqueBackground() const { return false; }

    // -- construction helpers ---------------------------------------------

    MIKDASHRUNTIME_API UMikdashSettingsSubsystem* Settings() const;
    MIKDASHRUNTIME_API FMikdashPalette Palette() const;

    /** Default font at a base size, scaled by the accessibility text scale, Hebrew-aware. */
    MIKDASHRUNTIME_API FSlateFontInfo Font(float BaseSize, bool bBold = false) const;

    MIKDASHRUNTIME_API UTextBlock* AddText(UPanelWidget* Parent, const FText& Value, float Size,
                                           const FLinearColor& Colour, bool bBold = false,
                                           ETextJustify::Type Justify = ETextJustify::Left);

    /** A full-width menu entry. Returns the button so the caller can disable it. */
    MIKDASHRUNTIME_API UButton* AddMenuEntry(UPanelWidget* Parent, const FText& Label, TFunction<void()> OnClicked);

    /** A label / control / value row, returns the horizontal box for the control slot. */
    MIKDASHRUNTIME_API UHorizontalBox* AddRow(UPanelWidget* Parent, const FText& Label);

    MIKDASHRUNTIME_API USlider* AddSliderRow(UPanelWidget* Parent, const FText& Label,
                                             float Value, float Min, float Max, float Step,
                                             TFunction<void(float)> OnChanged,
                                             TFunction<FText()> ValueText);

    MIKDASHRUNTIME_API UCheckBox* AddCheckRow(UPanelWidget* Parent, const FText& Label, bool bValue,
                                              TFunction<void(bool)> OnChanged);

    MIKDASHRUNTIME_API UComboBoxString* AddChoiceRow(UPanelWidget* Parent, const FText& Label,
                                                     const TArray<FText>& Options, int32 Selected,
                                                     TFunction<void(int32)> OnChanged);

    MIKDASHRUNTIME_API void AddSpacer(UPanelWidget* Parent, float Height);
    MIKDASHRUNTIME_API void AddSectionHeading(UPanelWidget* Parent, const FText& Value);

    /** Re-run every registered value label. Called after any settings change. */
    MIKDASHRUNTIME_API void RefreshValues();

    /** Keep a lambda alive for a dynamic delegate. */
    MIKDASHRUNTIME_API UMikdashUiAction* MakeAction();

    UPROPERTY(Transient) TObjectPtr<UOverlay> RootOverlay;
    UPROPERTY(Transient) TObjectPtr<UBorder> BackgroundLayer;
    UPROPERTY(Transient) TObjectPtr<UBorder> PanelBorder;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> BodyColumn;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> HeadingText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FooterText;
    UPROPERTY(Transient) TObjectPtr<UButton> FirstEntry;

    UPROPERTY(Transient) TArray<TObjectPtr<UMikdashUiAction>> Actions;

    /** Value labels that must be recomputed when a setting changes. */
    TArray<TPair<TWeakObjectPtr<UTextBlock>, TFunction<FText()>>> ValueLabels;

private:
    void BuildChrome();
};

/** Title screen. Five entries; the guided tour is disabled when nothing is bound. */
UCLASS(MinimalAPI)
class UMikdashMainMenuWidget : public UMikdashMenuWidget
{
    GENERATED_BODY()
protected:
    MIKDASHRUNTIME_API virtual void BuildBody(UVerticalBox* Body) override;
    MIKDASHRUNTIME_API virtual FText GetHeading() const override;
    MIKDASHRUNTIME_API virtual FText GetFooterHint() const override;
    virtual float GetPanelWidth() const override { return 620.0f; }
};

/** Escape screen during the walkthrough. */
UCLASS(MinimalAPI)
class UMikdashPauseMenuWidget : public UMikdashMenuWidget
{
    GENERATED_BODY()
protected:
    MIKDASHRUNTIME_API virtual void BuildBody(UVerticalBox* Body) override;
    MIKDASHRUNTIME_API virtual FText GetHeading() const override;
    MIKDASHRUNTIME_API virtual FText GetFooterHint() const override;
    MIKDASHRUNTIME_API virtual void HandleBack() override;
    virtual float GetPanelWidth() const override { return 560.0f; }
};

/** Six pages of settings over a widget switcher. */
UCLASS(MinimalAPI)
class UMikdashSettingsWidget : public UMikdashMenuWidget
{
    GENERATED_BODY()
public:
    /** Which page to open on. Survives a rebuild after a language change. */
    UPROPERTY(Transient) int32 ActivePage = 0;

protected:
    MIKDASHRUNTIME_API virtual void BuildBody(UVerticalBox* Body) override;
    MIKDASHRUNTIME_API virtual FText GetHeading() const override;
    MIKDASHRUNTIME_API virtual FText GetFooterHint() const override;
    MIKDASHRUNTIME_API virtual void HandleBack() override;
    virtual float GetPanelWidth() const override { return 1020.0f; }
    virtual bool WantsOpaqueBackground() const override { return true; }

private:
    void BuildGraphicsPage(UVerticalBox* Page);
    void BuildDisplayPage(UVerticalBox* Page);
    void BuildAudioPage(UVerticalBox* Page);
    void BuildTextPage(UVerticalBox* Page);
    void BuildAccessibilityPage(UVerticalBox* Page);
    void BuildControlsPage(UVerticalBox* Page);

    /** Commit the current edit, then refresh every value label on this page. */
    void CommitAndRefresh();

    UPROPERTY(Transient) TObjectPtr<UWidgetSwitcher> Pages;
    UPROPERTY(Transient) TArray<TObjectPtr<UButton>> PageTabs;
};

/** Scrolling credits. Content comes from UMikdashFrontEnd::BuildCredits(). */
UCLASS(MinimalAPI)
class UMikdashCreditsWidget : public UMikdashMenuWidget
{
    GENERATED_BODY()
protected:
    MIKDASHRUNTIME_API virtual void BuildBody(UVerticalBox* Body) override;
    MIKDASHRUNTIME_API virtual FText GetHeading() const override;
    MIKDASHRUNTIME_API virtual FText GetFooterHint() const override;
    MIKDASHRUNTIME_API virtual void HandleBack() override;
    virtual float GetPanelWidth() const override { return 1020.0f; }
    virtual bool WantsOpaqueBackground() const override { return true; }
};

/**
 * Still image plus a line of text that changes every few seconds.
 *
 * This ticks (a native UUserWidget subclass always does, unlike a Blueprint one that
 * has to opt in), so the line advances even while the game thread is busy streaming.
 */
UCLASS(MinimalAPI)
class UMikdashLoadingScreenWidget : public UMikdashMenuWidget
{
    GENERATED_BODY()
public:
    MIKDASHRUNTIME_API virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;

    /** Lines rotated through, in order. Set by the front end before display. */
    UPROPERTY(Transient) TArray<FText> Lines;

    /** Seconds each line is held. */
    UPROPERTY(Transient) float SecondsPerLine = 4.5f;

    /** Optional still image. Null falls back to a plain dark ground. */
    UPROPERTY(Transient) TObjectPtr<UTexture2D> StillImage;

protected:
    MIKDASHRUNTIME_API virtual void BuildBody(UVerticalBox* Body) override;
    MIKDASHRUNTIME_API virtual FText GetHeading() const override;
    virtual float GetPanelWidth() const override { return 900.0f; }
    virtual bool WantsOpaqueBackground() const override { return true; }

private:
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RotatingLine;
    UPROPERTY(Transient) TObjectPtr<UImage> StillImageWidget;
    float Elapsed = 0.0f;
    int32 LineIndex = 0;
};
