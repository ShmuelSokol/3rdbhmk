#include "MikdashMenuWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/BorderSlot.h"
#include "Components/Button.h"
#include "Components/CheckBox.h"
#include "Components/ComboBoxString.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/Slider.h"
#include "Components/Spacer.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WidgetSwitcher.h"
#include "Engine/Texture2D.h"
#include "Kismet/KismetSystemLibrary.h"
#include "MikdashFrontEnd.h"
#include "Misc/Paths.h"
#include "Styling/CoreStyle.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashMenu, Log, All);

namespace MS = MikdashSettings;

// ---------------------------------------------------------------------------
// Localisation
//
// This project ships no .locres and this module is not allowed to add Content, so
// the two languages live in a pair of literals per string. It is not a substitute
// for a real localisation pipeline -- it does not scale past two languages and it
// cannot be handed to a translator -- but it makes the Hebrew option real today
// rather than an entry that switches nothing.
// ---------------------------------------------------------------------------
namespace
{
    bool GHebrew = false;

    FText L(const TCHAR* English, const TCHAR* Hebrew)
    {
        return FText::FromString(GHebrew && Hebrew && *Hebrew ? Hebrew : English);
    }

    FText Num(float Value, int32 Decimals = 0)
    {
        return FText::FromString(FString::SanitizeFloat(Value, Decimals));
    }

    TArray<FText> QualityNames()
    {
        return { L(TEXT("Low"), TEXT("נמוך")),
                 L(TEXT("Medium"), TEXT("בינוני")),
                 L(TEXT("High"), TEXT("גבוה")),
                 L(TEXT("Epic"), TEXT("אפיק")),
                 L(TEXT("Cinematic"), TEXT("קולנועי")) };
    }
}

// ---------------------------------------------------------------------------
// UMikdashUiAction
// ---------------------------------------------------------------------------

void UMikdashUiAction::HandleClicked() { if (Clicked) { Clicked(); } }
void UMikdashUiAction::HandleFloat(float Value) { if (FloatChanged) { FloatChanged(Value); } }
void UMikdashUiAction::HandleBool(bool bValue) { if (BoolChanged) { BoolChanged(bValue); } }
void UMikdashUiAction::HandleSelection(FString Item, ESelectInfo::Type Info) { if (SelectionChanged) { SelectionChanged(Item, Info); } }

// ---------------------------------------------------------------------------
// UMikdashMenuWidget
// ---------------------------------------------------------------------------

UMikdashSettingsSubsystem* UMikdashMenuWidget::Settings() const
{
    return UMikdashSettingsSubsystem::Get(this);
}

FMikdashPalette UMikdashMenuWidget::Palette() const
{
    const UMikdashSettingsSubsystem* S = Settings();
    return S ? S->GetPalette() : FMikdashPalette();
}

FSlateFontInfo UMikdashMenuWidget::Font(float BaseSize, bool bBold) const
{
    const UMikdashSettingsSubsystem* S = Settings();
    const float Scale = S ? S->GetTextScale() : 1.0f;
    const float Size = MS::ScaledFontSize(BaseSize, 1.0f, Scale);

    // Hebrew needs a font with Hebrew glyphs. The engine default has none, so when the
    // configured .ttf is present Slate is pointed straight at the file on disk; no font
    // asset, no import, no Content change.
    if (S && S->IsRightToLeft())
    {
        const FString& Path = bBold ? S->HebrewFontFileBold : S->HebrewFontFile;
        if (!Path.IsEmpty() && FPaths::FileExists(Path))
        {
            return FSlateFontInfo(Path, Size);
        }
    }
    return FCoreStyle::GetDefaultFontStyle(bBold ? "Bold" : "Regular", static_cast<int32>(Size));
}

UMikdashUiAction* UMikdashMenuWidget::MakeAction()
{
    UMikdashUiAction* Action = NewObject<UMikdashUiAction>(this);
    Actions.Add(Action);
    return Action;
}

void UMikdashMenuWidget::NativeConstruct()
{
    Super::NativeConstruct();

    // Initialize() normally built the tree already; this covers a path where it did not.
    if (WidgetTree && !WidgetTree->RootWidget)
    {
        BuildChrome();
    }

    RefreshValues();

    // Give the first entry focus so arrow keys and a gamepad work without a mouse.
    if (FirstEntry)
    {
        FirstEntry->SetKeyboardFocus();
    }
}

FReply UMikdashMenuWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& KeyEvent)
{
    const FKey Key = KeyEvent.GetKey();
    if (Key == EKeys::Escape || Key == EKeys::Gamepad_FaceButton_Right || Key == EKeys::Virtual_Back)
    {
        HandleBack();
        return FReply::Handled();
    }
    return Super::NativeOnKeyDown(Geometry, KeyEvent);
}

void UMikdashMenuWidget::Rebuild()
{
    if (!BodyColumn) { return; }
    ValueLabels.Reset();
    Actions.Reset();
    FirstEntry = nullptr;
    BodyColumn->ClearChildren();

    if (HeadingText) { HeadingText->SetText(GetHeading()); HeadingText->SetFont(Font(38.0f, true)); }
    if (FooterText)
    {
        const FText Hint = GetFooterHint();
        FooterText->SetText(Hint);
        FooterText->SetFont(Font(15.0f));
        FooterText->SetVisibility(Hint.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    }

    BuildBody(BodyColumn);
    RefreshValues();
}

void UMikdashMenuWidget::BuildChrome()
{
    if (!WidgetTree) { return; }

    const UMikdashSettingsSubsystem* S = Settings();
    GHebrew = S && S->IsRightToLeft();
    const FMikdashPalette P = Palette();

    RootOverlay = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("Root"));
    WidgetTree->RootWidget = RootOverlay;

    // Background layer. Opaque for full-screen pages, a wash for the title screen so
    // the camera move over the court stays visible behind it.
    BackgroundLayer = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Background"));
    FLinearColor Ground = P.Background;
    if (!WantsOpaqueBackground()) { Ground.A = 0.45f; }
    BackgroundLayer->SetBrushColor(Ground);
    BackgroundLayer->SetPadding(FMargin(0.0f));
    if (UOverlaySlot* PanelSlot = RootOverlay->AddChildToOverlay(BackgroundLayer))
    {
        PanelSlot->SetHorizontalAlignment(HAlign_Fill);
        PanelSlot->SetVerticalAlignment(VAlign_Fill);
    }

    // Centred panel.
    USizeBox* Sizer = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("Sizer"));
    Sizer->SetWidthOverride(GetPanelWidth());
    if (UOverlaySlot* PanelSlot = RootOverlay->AddChildToOverlay(Sizer))
    {
        PanelSlot->SetHorizontalAlignment(HAlign_Center);
        PanelSlot->SetVerticalAlignment(VAlign_Center);
        PanelSlot->SetPadding(FMargin(24.0f, 32.0f));
    }

    PanelBorder = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Panel"));
    PanelBorder->SetBrushColor(P.Panel);
    PanelBorder->SetPadding(FMargin(34.0f, 28.0f));
    Sizer->SetContent(PanelBorder);

    UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Column"));
    PanelBorder->SetContent(Column);

    HeadingText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("Heading"));
    HeadingText->SetText(GetHeading());
    HeadingText->SetFont(Font(38.0f, true));
    HeadingText->SetColorAndOpacity(FSlateColor(P.Accent));
    HeadingText->SetAutoWrapText(true);
    HeadingText->SetJustification(GHebrew ? ETextJustify::Right : ETextJustify::Left);
    if (UVerticalBoxSlot* PanelSlot = Column->AddChildToVerticalBox(HeadingText))
    {
        PanelSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 14.0f));
        PanelSlot->SetHorizontalAlignment(HAlign_Fill);
    }

    BodyColumn = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Body"));
    if (UVerticalBoxSlot* PanelSlot = Column->AddChildToVerticalBox(BodyColumn))
    {
        PanelSlot->SetHorizontalAlignment(HAlign_Fill);
    }

    FooterText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("Footer"));
    FooterText->SetText(GetFooterHint());
    FooterText->SetFont(Font(15.0f));
    FooterText->SetColorAndOpacity(FSlateColor(P.TextDim));
    FooterText->SetAutoWrapText(true);
    FooterText->SetVisibility(GetFooterHint().IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    if (UVerticalBoxSlot* PanelSlot = Column->AddChildToVerticalBox(FooterText))
    {
        PanelSlot->SetPadding(FMargin(0.0f, 18.0f, 0.0f, 0.0f));
    }

    BuildBody(BodyColumn);
}

UTextBlock* UMikdashMenuWidget::AddText(UPanelWidget* Parent, const FText& Value, float Size,
                                        const FLinearColor& Colour, bool bBold, ETextJustify::Type Justify)
{
    if (!Parent || !WidgetTree) { return nullptr; }
    UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
    Text->SetText(Value);
    Text->SetFont(Font(Size, bBold));
    Text->SetColorAndOpacity(FSlateColor(Colour));
    Text->SetAutoWrapText(true);
    Text->SetJustification(GHebrew && Justify == ETextJustify::Left ? ETextJustify::Right : Justify);
    Parent->AddChild(Text);
    return Text;
}

UButton* UMikdashMenuWidget::AddMenuEntry(UPanelWidget* Parent, const FText& Label, TFunction<void()> OnClicked)
{
    if (!Parent || !WidgetTree) { return nullptr; }
    const FMikdashPalette P = Palette();

    UButton* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass());
    Button->SetBackgroundColor(FLinearColor(0.12f, 0.12f, 0.14f, 0.92f));

    UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
    Text->SetText(Label);
    Text->SetFont(Font(24.0f));
    Text->SetColorAndOpacity(FSlateColor(P.Text));
    Text->SetJustification(ETextJustify::Center);
    Button->SetContent(Text);

    UMikdashUiAction* Action = MakeAction();
    Action->Clicked = MoveTemp(OnClicked);
    Button->OnClicked.AddDynamic(Action, &UMikdashUiAction::HandleClicked);

    if (UVerticalBoxSlot* PanelSlot = Cast<UVerticalBoxSlot>(Parent->AddChild(Button)))
    {
        PanelSlot->SetPadding(FMargin(0.0f, 5.0f));
        PanelSlot->SetHorizontalAlignment(HAlign_Fill);
    }

    if (!FirstEntry) { FirstEntry = Button; }
    return Button;
}

UHorizontalBox* UMikdashMenuWidget::AddRow(UPanelWidget* Parent, const FText& Label)
{
    if (!Parent || !WidgetTree) { return nullptr; }
    const FMikdashPalette P = Palette();

    UHorizontalBox* Row = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());

    UTextBlock* LabelText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
    LabelText->SetText(Label);
    LabelText->SetFont(Font(18.0f));
    LabelText->SetColorAndOpacity(FSlateColor(P.Text));
    LabelText->SetAutoWrapText(true);
    LabelText->SetJustification(GHebrew ? ETextJustify::Right : ETextJustify::Left);
    if (UHorizontalBoxSlot* PanelSlot = Row->AddChildToHorizontalBox(LabelText))
    {
        PanelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        PanelSlot->SetVerticalAlignment(VAlign_Center);
        PanelSlot->SetPadding(FMargin(0.0f, 0.0f, 14.0f, 0.0f));
    }

    if (UVerticalBoxSlot* PanelSlot = Cast<UVerticalBoxSlot>(Parent->AddChild(Row)))
    {
        PanelSlot->SetPadding(FMargin(0.0f, 6.0f));
        PanelSlot->SetHorizontalAlignment(HAlign_Fill);
    }
    return Row;
}

USlider* UMikdashMenuWidget::AddSliderRow(UPanelWidget* Parent, const FText& Label,
                                          float Value, float Min, float Max, float Step,
                                          TFunction<void(float)> OnChanged, TFunction<FText()> ValueText)
{
    UHorizontalBox* Row = AddRow(Parent, Label);
    if (!Row) { return nullptr; }
    const FMikdashPalette P = Palette();

    USlider* Slider = WidgetTree->ConstructWidget<USlider>(USlider::StaticClass());
    Slider->SetMinValue(Min);
    Slider->SetMaxValue(Max);
    Slider->SetStepSize(Step > 0.0f ? Step : (Max - Min) / 20.0f);
    Slider->SetValue(FMath::Clamp(Value, Min, Max));
    Slider->SetSliderBarColor(FLinearColor(0.22f, 0.22f, 0.25f, 1.0f));
    Slider->SetSliderHandleColor(P.Accent);

    UMikdashUiAction* Action = MakeAction();
    Action->FloatChanged = MoveTemp(OnChanged);
    Slider->OnValueChanged.AddDynamic(Action, &UMikdashUiAction::HandleFloat);

    if (UHorizontalBoxSlot* PanelSlot = Row->AddChildToHorizontalBox(Slider))
    {
        PanelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        PanelSlot->SetVerticalAlignment(VAlign_Center);
    }

    UTextBlock* Readout = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
    Readout->SetFont(Font(17.0f));
    Readout->SetColorAndOpacity(FSlateColor(P.TextDim));
    Readout->SetJustification(ETextJustify::Right);
    Readout->SetMinDesiredWidth(112.0f);
    if (UHorizontalBoxSlot* PanelSlot = Row->AddChildToHorizontalBox(Readout))
    {
        PanelSlot->SetVerticalAlignment(VAlign_Center);
        PanelSlot->SetPadding(FMargin(12.0f, 0.0f, 0.0f, 0.0f));
    }
    if (ValueText)
    {
        ValueLabels.Emplace(Readout, MoveTemp(ValueText));
    }
    return Slider;
}

UCheckBox* UMikdashMenuWidget::AddCheckRow(UPanelWidget* Parent, const FText& Label, bool bValue,
                                           TFunction<void(bool)> OnChanged)
{
    UHorizontalBox* Row = AddRow(Parent, Label);
    if (!Row) { return nullptr; }

    UCheckBox* Check = WidgetTree->ConstructWidget<UCheckBox>(UCheckBox::StaticClass());
    Check->SetIsChecked(bValue);

    UMikdashUiAction* Action = MakeAction();
    Action->BoolChanged = MoveTemp(OnChanged);
    Check->OnCheckStateChanged.AddDynamic(Action, &UMikdashUiAction::HandleBool);

    if (UHorizontalBoxSlot* PanelSlot = Row->AddChildToHorizontalBox(Check))
    {
        PanelSlot->SetVerticalAlignment(VAlign_Center);
        PanelSlot->SetHorizontalAlignment(HAlign_Right);
        PanelSlot->SetPadding(FMargin(0.0f, 0.0f, 100.0f, 0.0f));
    }
    return Check;
}

UComboBoxString* UMikdashMenuWidget::AddChoiceRow(UPanelWidget* Parent, const FText& Label,
                                                  const TArray<FText>& Options, int32 Selected,
                                                  TFunction<void(int32)> OnChanged)
{
    UHorizontalBox* Row = AddRow(Parent, Label);
    if (!Row) { return nullptr; }

    UComboBoxString* Combo = WidgetTree->ConstructWidget<UComboBoxString>(UComboBoxString::StaticClass());
    for (const FText& Option : Options)
    {
        Combo->AddOption(Option.ToString());
    }
    if (Options.IsValidIndex(Selected))
    {
        Combo->SetSelectedIndex(Selected);
    }

    // Capture the option strings so the handler can turn the selected string back into
    // an index; UComboBoxString reports the string, not the index it came from.
    TArray<FString> OptionStrings;
    OptionStrings.Reserve(Options.Num());
    for (const FText& Option : Options) { OptionStrings.Add(Option.ToString()); }

    UMikdashUiAction* Action = MakeAction();
    TFunction<void(int32)> Forward = MoveTemp(OnChanged);
    Action->SelectionChanged = [OptionStrings, Forward](FString Item, ESelectInfo::Type Info)
    {
        // Direct is the programmatic path used when the page is rebuilt; acting on it
        // would fire a settings change for a value nobody touched.
        if (Info == ESelectInfo::Direct) { return; }
        const int32 Index = OptionStrings.IndexOfByKey(Item);
        if (Index != INDEX_NONE && Forward) { Forward(Index); }
    };
    Combo->OnSelectionChanged.AddDynamic(Action, &UMikdashUiAction::HandleSelection);

    if (UHorizontalBoxSlot* PanelSlot = Row->AddChildToHorizontalBox(Combo))
    {
        PanelSlot->SetVerticalAlignment(VAlign_Center);
        PanelSlot->SetPadding(FMargin(0.0f, 0.0f, 12.0f, 0.0f));
    }
    if (USizeBox* Unused = nullptr) { (void)Unused; }
    return Combo;
}

void UMikdashMenuWidget::AddSpacer(UPanelWidget* Parent, float Height)
{
    if (!Parent || !WidgetTree) { return; }
    USpacer* Spacer = WidgetTree->ConstructWidget<USpacer>(USpacer::StaticClass());
    Spacer->SetSize(FVector2D(1.0f, Height));
    Parent->AddChild(Spacer);
}

void UMikdashMenuWidget::AddSectionHeading(UPanelWidget* Parent, const FText& Value)
{
    AddSpacer(Parent, 14.0f);
    AddText(Parent, Value, 20.0f, Palette().Accent, true);
    AddSpacer(Parent, 4.0f);
}

void UMikdashMenuWidget::RefreshValues()
{
    for (const TPair<TWeakObjectPtr<UTextBlock>, TFunction<FText()>>& Entry : ValueLabels)
    {
        if (UTextBlock* Text = Entry.Key.Get())
        {
            if (Entry.Value) { Text->SetText(Entry.Value()); }
        }
    }
}

// ---------------------------------------------------------------------------
// UMikdashMainMenuWidget
// ---------------------------------------------------------------------------

FText UMikdashMainMenuWidget::GetHeading() const
{
    return FrontEnd ? FrontEnd->GetTitle() : L(TEXT("The Third Beis HaMikdash"), TEXT("בית המקדש השלישי"));
}

FText UMikdashMainMenuWidget::GetFooterHint() const
{
    return L(TEXT("Arrow keys or the mouse to choose. Enter to confirm."),
             TEXT("חצים או עכבר לבחירה. Enter לאישור."));
}

void UMikdashMainMenuWidget::BuildBody(UVerticalBox* Body)
{
    if (!Body) { return; }
    const FMikdashPalette P = Palette();

    const FText Subtitle = FrontEnd ? FrontEnd->GetSubtitle()
        : L(TEXT("A measured walkthrough"), TEXT("סיור מדוד"));
    AddText(Body, Subtitle, 19.0f, P.TextDim);
    AddSpacer(Body, 18.0f);

    AddMenuEntry(Body, L(TEXT("Begin the walkthrough"), TEXT("התחל בסיור")),
        [this]() { if (FrontEnd) { FrontEnd->BeginWalkthrough(); } });

    // The guided tour belongs to another system. The entry always exists so its absence
    // is visible; it is disabled and annotated when nothing has claimed it.
    const bool bTourAvailable = FrontEnd && FrontEnd->IsGuidedTourAvailable();
    const FText TourLabel = FrontEnd ? FrontEnd->GetGuidedTourLabel()
        : L(TEXT("Guided tour"), TEXT("סיור מודרך"));
    UButton* TourButton = AddMenuEntry(Body, TourLabel,
        [this]() { if (FrontEnd) { FrontEnd->RequestGuidedTour(); } });
    if (TourButton && !bTourAvailable)
    {
        TourButton->SetIsEnabled(false);
        TourButton->SetBackgroundColor(FLinearColor(0.09f, 0.09f, 0.10f, 0.85f));
        UTextBlock* Reason = AddText(Body, FrontEnd ? FrontEnd->GetGuidedTourUnavailableReason()
            : L(TEXT("No guided tour is loaded in this build."), TEXT("אין סיור מודרך בגרסה זו.")),
            14.0f, P.Disabled);
        if (Reason) { Reason->SetVisibility(ESlateVisibility::HitTestInvisible); }
    }

    AddMenuEntry(Body, L(TEXT("Settings"), TEXT("הגדרות")),
        [this]() { if (FrontEnd) { FrontEnd->ShowSettings(); } });
    AddMenuEntry(Body, L(TEXT("Credits"), TEXT("קרדיטים")),
        [this]() { if (FrontEnd) { FrontEnd->ShowCredits(); } });
    AddMenuEntry(Body, L(TEXT("Quit"), TEXT("יציאה")),
        [this]() { if (FrontEnd) { FrontEnd->QuitToDesktop(); } });
}

// ---------------------------------------------------------------------------
// UMikdashPauseMenuWidget
// ---------------------------------------------------------------------------

FText UMikdashPauseMenuWidget::GetHeading() const
{
    return L(TEXT("Paused"), TEXT("השהיה"));
}

FText UMikdashPauseMenuWidget::GetFooterHint() const
{
    return L(TEXT("Escape returns to the walkthrough."),
             TEXT("Escape מחזיר לסיור."));
}

void UMikdashPauseMenuWidget::HandleBack()
{
    if (FrontEnd) { FrontEnd->ResumeWalkthrough(); }
}

void UMikdashPauseMenuWidget::BuildBody(UVerticalBox* Body)
{
    if (!Body) { return; }
    AddMenuEntry(Body, L(TEXT("Resume"), TEXT("המשך")),
        [this]() { if (FrontEnd) { FrontEnd->ResumeWalkthrough(); } });
    AddMenuEntry(Body, L(TEXT("Settings"), TEXT("הגדרות")),
        [this]() { if (FrontEnd) { FrontEnd->ShowSettings(); } });
    AddMenuEntry(Body, L(TEXT("Return to main menu"), TEXT("חזרה לתפריט הראשי")),
        [this]() { if (FrontEnd) { FrontEnd->ReturnToMainMenu(); } });
    AddMenuEntry(Body, L(TEXT("Quit"), TEXT("יציאה")),
        [this]() { if (FrontEnd) { FrontEnd->QuitToDesktop(); } });
}

// ---------------------------------------------------------------------------
// UMikdashSettingsWidget
// ---------------------------------------------------------------------------

FText UMikdashSettingsWidget::GetHeading() const
{
    return L(TEXT("Settings"), TEXT("הגדרות"));
}

FText UMikdashSettingsWidget::GetFooterHint() const
{
    return L(TEXT("Every change is saved as you make it and survives a restart."),
             TEXT("כל שינוי נשמר מיד ונשמר גם לאחר יציאה."));
}

void UMikdashSettingsWidget::HandleBack()
{
    if (FrontEnd) { FrontEnd->GoBack(); }
}

void UMikdashSettingsWidget::CommitAndRefresh()
{
    if (UMikdashSettingsSubsystem* S = Settings())
    {
        S->Commit();
    }
    RefreshValues();
}

void UMikdashSettingsWidget::BuildBody(UVerticalBox* Body)
{
    if (!Body || !WidgetTree) { return; }
    UMikdashSettingsSubsystem* S = Settings();
    if (!S)
    {
        AddText(Body, L(TEXT("Settings are unavailable: the settings subsystem did not start."),
                        TEXT("ההגדרות אינן זמינות.")),
                18.0f, Palette().Warning);
        return;
    }

    const FMikdashPalette P = Palette();

    // Tab strip.
    UHorizontalBox* Tabs = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
    Body->AddChildToVerticalBox(Tabs);

    Pages = WidgetTree->ConstructWidget<UWidgetSwitcher>(UWidgetSwitcher::StaticClass());
    UScrollBox* Scroller = WidgetTree->ConstructWidget<UScrollBox>(UScrollBox::StaticClass());
    Scroller->AddChild(Pages);
    USizeBox* ScrollSizer = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
    ScrollSizer->SetHeightOverride(520.0f);
    ScrollSizer->SetContent(Scroller);
    if (UVerticalBoxSlot* PanelSlot = Body->AddChildToVerticalBox(ScrollSizer))
    {
        PanelSlot->SetPadding(FMargin(0.0f, 12.0f));
        PanelSlot->SetHorizontalAlignment(HAlign_Fill);
    }

    const TArray<FText> PageNames = {
        L(TEXT("Graphics"), TEXT("גרפיקה")),
        L(TEXT("Display"), TEXT("תצוגה")),
        L(TEXT("Audio"), TEXT("שמע")),
        L(TEXT("Text and language"), TEXT("טקסט ושפה")),
        L(TEXT("Accessibility"), TEXT("נגישות")),
        L(TEXT("Controls"), TEXT("שליטה")),
    };

    PageTabs.Reset();
    for (int32 Index = 0; Index < PageNames.Num(); ++Index)
    {
        UButton* Tab = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass());
        Tab->SetBackgroundColor(Index == ActivePage ? FLinearColor(0.22f, 0.19f, 0.11f, 0.95f)
                                                    : FLinearColor(0.10f, 0.10f, 0.12f, 0.9f));
        UTextBlock* TabText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
        TabText->SetText(PageNames[Index]);
        TabText->SetFont(Font(16.0f, Index == ActivePage));
        TabText->SetColorAndOpacity(FSlateColor(Index == ActivePage ? P.Selected : P.TextDim));
        TabText->SetJustification(ETextJustify::Center);
        Tab->SetContent(TabText);

        UMikdashUiAction* Action = MakeAction();
        Action->Clicked = [this, Index]()
        {
            ActivePage = Index;
            Rebuild();
        };
        Tab->OnClicked.AddDynamic(Action, &UMikdashUiAction::HandleClicked);

        if (UHorizontalBoxSlot* PanelSlot = Tabs->AddChildToHorizontalBox(Tab))
        {
            PanelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
            PanelSlot->SetPadding(FMargin(2.0f, 0.0f));
        }
        PageTabs.Add(Tab);
        if (Index == 0 && !FirstEntry) { FirstEntry = Tab; }
    }

    auto MakePage = [this]() -> UVerticalBox*
    {
        UVerticalBox* Page = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
        Pages->AddChild(Page);
        return Page;
    };

    BuildGraphicsPage(MakePage());
    BuildDisplayPage(MakePage());
    BuildAudioPage(MakePage());
    BuildTextPage(MakePage());
    BuildAccessibilityPage(MakePage());
    BuildControlsPage(MakePage());

    Pages->SetActiveWidgetIndex(FMath::Clamp(ActivePage, 0, Pages->GetNumWidgets() - 1));

    // Footer buttons.
    UHorizontalBox* Buttons = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
    Body->AddChildToVerticalBox(Buttons);

    auto AddFooterButton = [this, Buttons, P](const FText& Label, TFunction<void()> OnClicked)
    {
        UButton* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass());
        Button->SetBackgroundColor(FLinearColor(0.12f, 0.12f, 0.14f, 0.92f));
        UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
        Text->SetText(Label);
        Text->SetFont(Font(18.0f));
        Text->SetColorAndOpacity(FSlateColor(P.Text));
        Text->SetJustification(ETextJustify::Center);
        Button->SetContent(Text);
        UMikdashUiAction* Action = MakeAction();
        Action->Clicked = MoveTemp(OnClicked);
        Button->OnClicked.AddDynamic(Action, &UMikdashUiAction::HandleClicked);
        if (UHorizontalBoxSlot* PanelSlot = Buttons->AddChildToHorizontalBox(Button))
        {
            PanelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
            PanelSlot->SetPadding(FMargin(3.0f, 0.0f));
        }
    };

    AddFooterButton(L(TEXT("Reset to defaults"), TEXT("איפוס לברירת המחדל")),
        [this]()
        {
            if (UMikdashSettingsSubsystem* Sub = Settings()) { Sub->ResetToDefaults(); }
            Rebuild();
        });
    AddFooterButton(L(TEXT("Back"), TEXT("חזרה")),
        [this]() { if (FrontEnd) { FrontEnd->GoBack(); } });
}

void UMikdashSettingsWidget::BuildGraphicsPage(UVerticalBox* Page)
{
    UMikdashSettingsSubsystem* S = Settings();
    if (!Page || !S) { return; }

    AddSectionHeading(Page, L(TEXT("Preset"), TEXT("ערכה מוכנה")));

    TArray<FText> Presets = QualityNames();
    Presets.Add(L(TEXT("Custom"), TEXT("מותאם אישית")));
    AddChoiceRow(Page, L(TEXT("Graphics preset"), TEXT("ערכת גרפיקה")),
                 Presets, static_cast<int32>(S->Get().Preset),
                 [this](int32 Index)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     // Choosing Custom explicitly is meaningless: Custom is what the record
                     // becomes when a group is edited by hand, not something to select.
                     if (Index >= static_cast<int32>(MS::EPreset::Custom)) { return; }
                     MS::ApplyPreset(Sub->Edit(), static_cast<MS::EPreset>(Index));
                     Sub->Commit();
                     Rebuild();
                 });

    AddSectionHeading(Page, L(TEXT("Individual quality"), TEXT("איכות לפי קבוצה")));

    static const TCHAR* const GroupLabelsHe[9] = {
        TEXT("מרחק ראייה"), TEXT("צללים"),
        TEXT("תאורה גלובלית"), TEXT("השתקפויות"),
        TEXT("עיבוד תמונה"), TEXT("מרקמים"),
        TEXT("אפקטים"), TEXT("צמחייה"), TEXT("הצללה") };

    for (int32 Index = 0; Index < MS::FScalability::Count(); ++Index)
    {
        AddChoiceRow(Page, L(ANSI_TO_TCHAR(MS::GroupName(Index)), GroupLabelsHe[Index]),
                     QualityNames(), S->Get().Groups.Get(Index),
                     [this, Index](int32 Quality)
                     {
                         UMikdashSettingsSubsystem* Sub = Settings();
                         if (!Sub) { return; }
                         MS::SetGroup(Sub->Edit(), Index, Quality);
                         Sub->Commit();
                         RefreshValues();
                     });
    }
}

void UMikdashSettingsWidget::BuildDisplayPage(UVerticalBox* Page)
{
    UMikdashSettingsSubsystem* S = Settings();
    if (!Page || !S) { return; }

    AddSectionHeading(Page, L(TEXT("Window"), TEXT("חלון")));

    TArray<FIntPoint> Resolutions;
    UKismetSystemLibrary::GetSupportedFullscreenResolutions(Resolutions);
    if (Resolutions.Num() == 0)
    {
        Resolutions = { FIntPoint(1280, 720), FIntPoint(1600, 900), FIntPoint(1920, 1080),
                        FIntPoint(2560, 1440), FIntPoint(3840, 2160) };
    }
    TArray<FText> ResolutionNames;
    int32 SelectedResolution = 0;
    for (int32 Index = 0; Index < Resolutions.Num(); ++Index)
    {
        ResolutionNames.Add(FText::FromString(FString::Printf(TEXT("%d x %d"), Resolutions[Index].X, Resolutions[Index].Y)));
        if (Resolutions[Index].X == S->Get().ResolutionX && Resolutions[Index].Y == S->Get().ResolutionY)
        {
            SelectedResolution = Index;
        }
    }
    AddChoiceRow(Page, L(TEXT("Resolution"), TEXT("רזולוציה")),
                 ResolutionNames, SelectedResolution,
                 [this, Resolutions](int32 Index)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub || !Resolutions.IsValidIndex(Index)) { return; }
                     Sub->Edit().ResolutionX = Resolutions[Index].X;
                     Sub->Edit().ResolutionY = Resolutions[Index].Y;
                     Sub->Commit();
                 });

    AddChoiceRow(Page, L(TEXT("Window mode"), TEXT("מצב חלון")),
                 { L(TEXT("Fullscreen"), TEXT("מסך מלא")),
                   L(TEXT("Borderless window"), TEXT("חלון ללא מסגרת")),
                   L(TEXT("Windowed"), TEXT("חלוני")) },
                 static_cast<int32>(S->Get().WindowMode),
                 [this](int32 Index)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().WindowMode = static_cast<MS::EWindowMode>(Index);
                     Sub->Commit();
                 });

    static const float Caps[] = { 0.0f, 30.0f, 60.0f, 72.0f, 90.0f, 120.0f, 144.0f, 165.0f, 240.0f };
    TArray<FText> CapNames;
    int32 SelectedCap = 0;
    for (int32 Index = 0; Index < UE_ARRAY_COUNT(Caps); ++Index)
    {
        CapNames.Add(Caps[Index] <= 0.0f ? L(TEXT("Uncapped"), TEXT("ללא הגבלה"))
                                         : FText::FromString(FString::Printf(TEXT("%d fps"), FMath::RoundToInt(Caps[Index]))));
        if (FMath::IsNearlyEqual(Caps[Index], S->Get().FrameRateCap, 0.5f)) { SelectedCap = Index; }
    }
    AddChoiceRow(Page, L(TEXT("Frame rate cap"), TEXT("הגבלת קצב פריימים")),
                 CapNames, SelectedCap,
                 [this](int32 Index)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub || Index < 0 || Index >= UE_ARRAY_COUNT(Caps)) { return; }
                     Sub->Edit().FrameRateCap = Caps[Index];
                     Sub->Commit();
                 });

    AddSectionHeading(Page, L(TEXT("Upscaling"), TEXT("הגדלת רזולוציה")));

    AddChoiceRow(Page, L(TEXT("Method"), TEXT("שיטה")),
                 { L(TEXT("Off"), TEXT("כבוי")),
                   L(TEXT("Temporal anti-aliasing (TAAU)"), TEXT("TAAU")),
                   L(TEXT("Temporal super resolution (TSR)"), TEXT("TSR")),
                   L(TEXT("Spatial"), TEXT("מרחבי")) },
                 static_cast<int32>(S->Get().UpscaleMethod),
                 [this](int32 Index)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     MS::SetUpscaling(Sub->Edit(), static_cast<MS::EUpscaleMethod>(Index), Sub->Get().UpscaleQuality);
                     Sub->Commit();
                     RefreshValues();
                 });

    AddChoiceRow(Page, L(TEXT("Quality"), TEXT("איכות")),
                 { L(TEXT("Native"), TEXT("מלא")),
                   L(TEXT("Quality"), TEXT("איכות")),
                   L(TEXT("Balanced"), TEXT("מאוזן")),
                   L(TEXT("Performance"), TEXT("ביצועים")),
                   L(TEXT("Ultra performance"), TEXT("ביצועים מרביים")) },
                 static_cast<int32>(S->Get().UpscaleQuality),
                 [this](int32 Index)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     MS::SetUpscaling(Sub->Edit(), Sub->Get().UpscaleMethod, static_cast<MS::EUpscaleQuality>(Index));
                     Sub->Commit();
                     RefreshValues();
                 });

    AddSliderRow(Page, L(TEXT("Render scale"), TEXT("קנה מידה של רנדור")),
                 S->Get().ScreenPercentage, MS::MinScreenPercentage, MS::MaxScreenPercentage, 1.0f,
                 [this](float Value)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().ScreenPercentage = Value;
                     Sub->Preview();
                     RefreshValues();
                 },
                 [this]() -> FText
                 {
                     const UMikdashSettingsSubsystem* Sub = Settings();
                     return Sub ? FText::FromString(FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Sub->Get().ScreenPercentage)))
                                : FText::GetEmpty();
                 });
    AddText(Page, L(TEXT("The render scale is fixed by the upscaling tier unless that tier is Native."),
                    TEXT("קנה המידה נקבע לפי רמת ההגדלה, אלא אם היא מלאה.")),
            13.0f, Palette().TextDim);

    AddSectionHeading(Page, L(TEXT("Camera"), TEXT("מצלמה")));
    AddSliderRow(Page, L(TEXT("Field of view"), TEXT("שדה ראייה")),
                 S->Get().FieldOfView, MS::MinFov, MS::MaxFov, 1.0f,
                 [this](float Value)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().FieldOfView = Value;
                     Sub->Preview();
                     RefreshValues();
                 },
                 [this]() -> FText
                 {
                     const UMikdashSettingsSubsystem* Sub = Settings();
                     return Sub ? FText::FromString(FString::Printf(TEXT("%d°"), FMath::RoundToInt(Sub->Get().FieldOfView)))
                                : FText::GetEmpty();
                 });
}

void UMikdashSettingsWidget::BuildAudioPage(UVerticalBox* Page)
{
    UMikdashSettingsSubsystem* S = Settings();
    if (!Page || !S) { return; }

    auto Percent = [](float Value) { return FText::FromString(FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Value * 100.0f))); };

    struct FVolumeRow { FText Label; float MS::FSettings::* Field; };
    const FVolumeRow Rows[] = {
        { L(TEXT("Master"), TEXT("ראשי")),   &MS::FSettings::MasterVolume },
        { L(TEXT("Music"), TEXT("מוסיקה")), &MS::FSettings::MusicVolume },
        { L(TEXT("Effects"), TEXT("אפקטים")), &MS::FSettings::EffectsVolume },
        { L(TEXT("Voice"), TEXT("קול")),      &MS::FSettings::VoiceVolume },
    };

    AddSectionHeading(Page, L(TEXT("Volume"), TEXT("עוצמה")));
    for (const FVolumeRow& Row : Rows)
    {
        float MS::FSettings::* const Field = Row.Field;
        AddSliderRow(Page, Row.Label, S->Get().*Field, 0.0f, 1.0f, 0.05f,
                     [this, Field](float Value)
                     {
                         UMikdashSettingsSubsystem* Sub = Settings();
                         if (!Sub) { return; }
                         Sub->Edit().*Field = Value;
                         Sub->Preview();
                         RefreshValues();
                     },
                     [this, Field, Percent]() -> FText
                     {
                         const UMikdashSettingsSubsystem* Sub = Settings();
                         return Sub ? Percent(Sub->Get().*Field) : FText::GetEmpty();
                     });
    }

    AddText(Page, L(TEXT("Master volume applies immediately. Music, effects and voice are stored and readable by the rest of the build, but this project has no sound-class assets for them yet, so those three sliders do not change what you hear until those assets exist."),
                    TEXT("העוצמה הראשית פועלת מיד. שלושת האחרים נשמרים אך אינם פועלים עדיין.")),
            13.0f, Palette().TextDim);
}

void UMikdashSettingsWidget::BuildTextPage(UVerticalBox* Page)
{
    UMikdashSettingsSubsystem* S = Settings();
    if (!Page || !S) { return; }

    AddSectionHeading(Page, L(TEXT("Subtitles"), TEXT("כתוביות")));
    AddCheckRow(Page, L(TEXT("Show subtitles"), TEXT("הצג כתוביות")), S->Get().bSubtitles,
                [this](bool bValue)
                {
                    UMikdashSettingsSubsystem* Sub = Settings();
                    if (!Sub) { return; }
                    Sub->Edit().bSubtitles = bValue;
                    Sub->Commit();
                });

    AddSliderRow(Page, L(TEXT("Subtitle size"), TEXT("גודל כתוביות")),
                 S->Get().SubtitleScale, MS::MinSubtitleScale, MS::MaxSubtitleScale, 0.05f,
                 [this](float Value)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().SubtitleScale = Value;
                     Sub->Commit();
                     RefreshValues();
                 },
                 [this]() -> FText
                 {
                     const UMikdashSettingsSubsystem* Sub = Settings();
                     return Sub ? FText::FromString(FString::Printf(TEXT("%.2fx"), Sub->Get().SubtitleScale)) : FText::GetEmpty();
                 });

    AddSectionHeading(Page, L(TEXT("Text size"), TEXT("גודל טקסט")));
    AddSliderRow(Page, L(TEXT("Interface text scale"), TEXT("קנה מידה של טקסט")),
                 S->Get().TextScale, MS::MinTextScale, MS::MaxTextScale, 0.05f,
                 [this](float Value)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().TextScale = Value;
                     Sub->Commit();
                     // The whole page has to be rebuilt: every font size on it changed.
                     Rebuild();
                 },
                 [this]() -> FText
                 {
                     const UMikdashSettingsSubsystem* Sub = Settings();
                     return Sub ? FText::FromString(FString::Printf(TEXT("%.2fx"), Sub->Get().TextScale)) : FText::GetEmpty();
                 });

    AddSectionHeading(Page, L(TEXT("Language"), TEXT("שפה")));
    AddChoiceRow(Page, L(TEXT("Language"), TEXT("שפה")),
                 { FText::FromString(TEXT("English")), FText::FromString(TEXT("עברית")) },
                 static_cast<int32>(S->Get().Language),
                 [this](int32 Index)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().Language = static_cast<MS::ELanguage>(Index);
                     Sub->Commit();
                     GHebrew = Sub->IsRightToLeft();
                     Rebuild();
                 });

    const UMikdashSettingsSubsystem* Sub = Settings();
    const bool bHebrewFontPresent = Sub && !Sub->HebrewFontFile.IsEmpty() && FPaths::FileExists(Sub->HebrewFontFile);
    if (!bHebrewFontPresent)
    {
        AddText(Page, L(TEXT("Hebrew needs a font with Hebrew glyphs. None was found at the configured path, so Hebrew text will show as boxes until HebrewFontFile in DefaultGame.ini points at one."),
                        TEXT("עברית דורשת גופן עם אותיות עבריות.")),
                13.0f, Palette().Warning);
    }
}

void UMikdashSettingsWidget::BuildAccessibilityPage(UVerticalBox* Page)
{
    UMikdashSettingsSubsystem* S = Settings();
    if (!Page || !S) { return; }

    AddSectionHeading(Page, L(TEXT("Motion comfort"), TEXT("נוחות תנועה")));

    AddCheckRow(Page, L(TEXT("Camera shake"), TEXT("רעידת מצלמה")), S->Get().bCameraShake,
                [this](bool bValue) { UMikdashSettingsSubsystem* Sub = Settings(); if (Sub) { Sub->Edit().bCameraShake = bValue; Sub->Commit(); } });
    AddCheckRow(Page, L(TEXT("Head bob while walking"), TEXT("תנועת ראש בהליכה")), S->Get().bHeadBob,
                [this](bool bValue) { UMikdashSettingsSubsystem* Sub = Settings(); if (Sub) { Sub->Edit().bHeadBob = bValue; Sub->Commit(); } });
    AddCheckRow(Page, L(TEXT("Vignette while moving"), TEXT("האפלה בשוליים בתנועה")), S->Get().bVignetteOnMovement,
                [this](bool bValue) { UMikdashSettingsSubsystem* Sub = Settings(); if (Sub) { Sub->Edit().bVignetteOnMovement = bValue; Sub->Commit(); } });
    AddCheckRow(Page, L(TEXT("Snap turning"), TEXT("סיבוב בקפיצות")), S->Get().bSnapTurn,
                [this](bool bValue) { UMikdashSettingsSubsystem* Sub = Settings(); if (Sub) { Sub->Edit().bSnapTurn = bValue; Sub->Commit(); } });

    AddSliderRow(Page, L(TEXT("Snap turn angle"), TEXT("זווית סיבוב")),
                 S->Get().SnapTurnDegrees, MS::MinSnapTurn, MS::MaxSnapTurn, MS::SnapTurnStep,
                 [this](float Value)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().SnapTurnDegrees = MS::SnapTurnStepDegrees(Value);
                     Sub->Commit();
                     RefreshValues();
                 },
                 [this]() -> FText
                 {
                     const UMikdashSettingsSubsystem* Sub = Settings();
                     return Sub ? FText::FromString(FString::Printf(TEXT("%d°"), FMath::RoundToInt(Sub->Get().SnapTurnDegrees))) : FText::GetEmpty();
                 });

    AddSectionHeading(Page, L(TEXT("Colour"), TEXT("צבע")));
    AddChoiceRow(Page, L(TEXT("Colour-blind safe mode"), TEXT("מצב בטוח לעיוורון צבעים")),
                 { L(TEXT("Off"), TEXT("כבוי")),
                   L(TEXT("Deuteranopia (green)"), TEXT("דוטרנופיה")),
                   L(TEXT("Protanopia (red)"), TEXT("פרוטנופיה")),
                   L(TEXT("Tritanopia (blue)"), TEXT("טריטנופיה")) },
                 static_cast<int32>(S->Get().ColourVision),
                 [this](int32 Index)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().ColourVision = static_cast<MS::EColourVision>(Index);
                     Sub->Commit();
                     Rebuild();
                 });
    AddText(Page, L(TEXT("This repaints the front end so nothing depends on telling red from green. It does not recolour the court itself, which is measured stone and gold and carries no colour-coded meaning."),
                    TEXT("האפשרות צובעת מחדש את הממשק בלבד.")),
            13.0f, Palette().TextDim);

    AddSectionHeading(Page, L(TEXT("Readability"), TEXT("קריאות")));
    AddText(Page, L(TEXT("Text size and field of view are on the Text and Display pages."),
                    TEXT("גודל הטקסט ושדה הראייה נמצאים בלשוניות אחרות.")),
            13.0f, Palette().TextDim);
}

void UMikdashSettingsWidget::BuildControlsPage(UVerticalBox* Page)
{
    UMikdashSettingsSubsystem* S = Settings();
    if (!Page || !S) { return; }

    AddSectionHeading(Page, L(TEXT("Looking"), TEXT("מבט")));
    AddSliderRow(Page, L(TEXT("Mouse sensitivity"), TEXT("רגישות עכבר")),
                 S->Get().MouseSensitivity, 0.0f, 1.0f, 0.01f,
                 [this](float Value)
                 {
                     UMikdashSettingsSubsystem* Sub = Settings();
                     if (!Sub) { return; }
                     Sub->Edit().MouseSensitivity = Value;
                     Sub->Preview();
                     RefreshValues();
                 },
                 [this]() -> FText
                 {
                     const UMikdashSettingsSubsystem* Sub = Settings();
                     return Sub ? FText::FromString(FString::Printf(TEXT("%.2fx"), Sub->GetLookMultiplier())) : FText::GetEmpty();
                 });

    AddCheckRow(Page, L(TEXT("Invert vertical look"), TEXT("הפוך מבט אנכי")), S->Get().bInvertY,
                [this](bool bValue) { UMikdashSettingsSubsystem* Sub = Settings(); if (Sub) { Sub->Edit().bInvertY = bValue; Sub->Commit(); } });

    AddSectionHeading(Page, L(TEXT("Hold or toggle"), TEXT("לחיצה או מתג")));
    const TArray<FText> HoldModes = { L(TEXT("Hold"), TEXT("לחיצה ממושכת")),
                                      L(TEXT("Toggle"), TEXT("מתג")) };
    AddChoiceRow(Page, L(TEXT("Sprint"), TEXT("ריצה")), HoldModes, static_cast<int32>(S->Get().SprintMode),
                 [this](int32 Index) { UMikdashSettingsSubsystem* Sub = Settings(); if (Sub) { Sub->Edit().SprintMode = static_cast<MS::EHoldMode>(Index); Sub->Commit(); } });
    AddChoiceRow(Page, L(TEXT("Crouch"), TEXT("התכופפות")), HoldModes, static_cast<int32>(S->Get().CrouchMode),
                 [this](int32 Index) { UMikdashSettingsSubsystem* Sub = Settings(); if (Sub) { Sub->Edit().CrouchMode = static_cast<MS::EHoldMode>(Index); Sub->Commit(); } });

    AddText(Page, L(TEXT("Sensitivity and invert are applied here and are also readable by the walkthrough controller. Hold-versus-toggle is stored and readable; the movement code has to ask for it, and this front end does not reach into it."),
                    TEXT("הערכים נשמרים וניתנים לקריאה על ידי קוד התנועה.")),
            13.0f, Palette().TextDim);
}

// ---------------------------------------------------------------------------
// UMikdashCreditsWidget
// ---------------------------------------------------------------------------

FText UMikdashCreditsWidget::GetHeading() const
{
    return L(TEXT("Credits and sources"), TEXT("קרדיטים ומקורות"));
}

FText UMikdashCreditsWidget::GetFooterHint() const
{
    return L(TEXT("Escape returns."), TEXT("Escape מחזיר."));
}

void UMikdashCreditsWidget::HandleBack()
{
    if (FrontEnd) { FrontEnd->GoBack(); }
}

void UMikdashCreditsWidget::BuildBody(UVerticalBox* Body)
{
    if (!Body || !WidgetTree) { return; }
    const FMikdashPalette P = Palette();

    UScrollBox* Scroller = WidgetTree->ConstructWidget<UScrollBox>(UScrollBox::StaticClass());
    USizeBox* Sizer = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
    Sizer->SetHeightOverride(560.0f);
    Sizer->SetContent(Scroller);
    if (UVerticalBoxSlot* PanelSlot = Body->AddChildToVerticalBox(Sizer))
    {
        PanelSlot->SetHorizontalAlignment(HAlign_Fill);
    }

    UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
    Scroller->AddChild(Column);

    const TArray<FMikdashCreditsSection> Sections = FrontEnd ? FrontEnd->BuildCredits() : TArray<FMikdashCreditsSection>();
    if (Sections.Num() == 0)
    {
        AddText(Column, L(TEXT("The credits could not be assembled: the front end is not available."),
                          TEXT("לא ניתן להרכיב את הקרדיטים.")),
                17.0f, P.Warning);
    }
    for (const FMikdashCreditsSection& Section : Sections)
    {
        AddSpacer(Column, 12.0f);
        AddText(Column, Section.Heading, 22.0f, P.Accent, true);
        AddSpacer(Column, 4.0f);
        for (const FText& Line : Section.Lines)
        {
            UTextBlock* Text = AddText(Column, Line, 15.0f, P.Text);
            if (Text) { Text->SetAutoWrapText(true); }
            AddSpacer(Column, 3.0f);
        }
    }

    AddSpacer(Body, 12.0f);
    AddMenuEntry(Body, L(TEXT("Back"), TEXT("חזרה")),
        [this]() { if (FrontEnd) { FrontEnd->GoBack(); } });
}

// ---------------------------------------------------------------------------
// UMikdashLoadingScreenWidget
// ---------------------------------------------------------------------------

FText UMikdashLoadingScreenWidget::GetHeading() const
{
    return L(TEXT("Entering the court"), TEXT("נכנסים לעזרה"));
}

void UMikdashLoadingScreenWidget::BuildBody(UVerticalBox* Body)
{
    if (!Body || !WidgetTree) { return; }
    const FMikdashPalette P = Palette();

    // Still image, when one was configured and loaded. There is no fabricated
    // placeholder art: without an image the panel simply sits on the dark ground.
    if (StillImage)
    {
        StillImageWidget = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass());
        StillImageWidget->SetBrushFromTexture(StillImage, false);
        StillImageWidget->SetDesiredSizeOverride(FVector2D(820.0f, 340.0f));
        if (UVerticalBoxSlot* PanelSlot = Body->AddChildToVerticalBox(StillImageWidget))
        {
            PanelSlot->SetHorizontalAlignment(HAlign_Center);
            PanelSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 20.0f));
        }
    }

    RotatingLine = AddText(Body, Lines.Num() > 0 ? Lines[0] : FText::GetEmpty(), 20.0f, P.Text, false, ETextJustify::Center);
    if (RotatingLine)
    {
        RotatingLine->SetAutoWrapText(true);
        RotatingLine->SetMinDesiredWidth(760.0f);
    }

    AddSpacer(Body, 16.0f);
    AddText(Body, L(TEXT("Loading..."), TEXT("טוען...")), 15.0f, P.TextDim, false, ETextJustify::Center);
}

void UMikdashLoadingScreenWidget::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);

    if (Lines.Num() <= 1 || !RotatingLine) { return; }

    Elapsed += DeltaTime;
    if (Elapsed >= FMath::Max(1.0f, SecondsPerLine))
    {
        Elapsed = 0.0f;
        LineIndex = (LineIndex + 1) % Lines.Num();
        RotatingLine->SetText(Lines[LineIndex]);
    }
}
