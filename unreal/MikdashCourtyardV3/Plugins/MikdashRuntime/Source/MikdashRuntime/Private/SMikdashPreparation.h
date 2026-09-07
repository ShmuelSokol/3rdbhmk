#pragma once
#include "PreparationJourney.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"

class SMikdashPreparation : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SMikdashPreparation) {}
        SLATE_ARGUMENT(MikdashPreparation::Journey*, Journey)
        SLATE_EVENT(FSimpleDelegate, OnBack)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args)
    {
        Model = Args._Journey;
        Back = Args._OnBack;
        // Only the chooser view is local. The controller retains the story and
        // its outstanding facts when this widget is closed and reopened.
        bChoosingStory = Model->GetStage() == MikdashPreparation::Stage::Inactive;
        ButtonText = FCoreStyle::Get().GetWidgetStyle<FTextBlockStyle>("NormalText");
        ButtonText.SetFont(FCoreStyle::GetDefaultFontStyle("Regular", 18));
        TSharedRef<SVerticalBox> Content = SNew(SVerticalBox);
        TSharedRef<SVerticalBox> Chooser = SNew(SVerticalBox)
            .Visibility_Lambda([this]() { return bChoosingStory ? EVisibility::Visible : EVisibility::Collapsed; });
        Content->AddSlot().AutoHeight()[Chooser];
        Chooser->AddSlot().AutoHeight().Padding(0, 6)[Text("Before you arrive", 28)];
        Chooser->AddSlot().AutoHeight().Padding(0, 6)[Text("Practice with a fictional visitor. These short lessons introduce distinctions; they do not determine your personal status or grant entry to a sacred area.")];
        const MikdashPreparation::Scenario Scenarios[] = {
            MikdashPreparation::Scenario::PreparedPilgrim, MikdashPreparation::Scenario::CorpseProcessPending,
            MikdashPreparation::Scenario::AwaitingDayCompletion, MikdashPreparation::Scenario::OfferingPending,
            MikdashPreparation::Scenario::UnknownHistory};
        for (const auto Scenario : Scenarios)
        {
            Chooser->AddSlot().AutoHeight().Padding(0, 3)
            [SNew(SButton).TextStyle(&ButtonText).ContentPadding(10)
                .Text(FText::FromString(UTF8_TO_TCHAR(MikdashPreparation::GetScenarioCard(Scenario).Title)))
                .OnClicked_Lambda([this, Scenario]() { Model->Start(Scenario); bChoosingStory = false; bHint = false; ResetScroll(); return FReply::Handled().SetUserFocus(AsShared()); })];
        }
        Chooser->AddSlot().AutoHeight().Padding(0, 6)
        [SNew(SButton).TextStyle(&ButtonText).ContentPadding(8).Text(FText::FromString(TEXT("Return to current story")))
            .Visibility_Lambda([this]() { return Model->GetStage() != MikdashPreparation::Stage::Inactive ? EVisibility::Visible : EVisibility::Collapsed; })
            .OnClicked_Lambda([this]() { bChoosingStory = false; ResetScroll(); return FReply::Handled().SetUserFocus(AsShared()); })];
        TSharedRef<SVerticalBox> Lesson = SNew(SVerticalBox)
            .Visibility_Lambda([this]() { return bChoosingStory ? EVisibility::Collapsed : EVisibility::Visible; });
        Content->AddSlot().AutoHeight()[Lesson];
        Lesson->AddSlot().AutoHeight().Padding(0, 6)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 26)).AutoWrapText(true)
            .Text_Lambda([this]() { return FText::FromString(UTF8_TO_TCHAR(Model->GetCard().Title)); })];
        Lesson->AddSlot().AutoHeight().Padding(0, 5)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true)
            .Text_Lambda([this]() { return FText::FromString(UTF8_TO_TCHAR(Model->GetCard().FictionalHistory)); })];
        Lesson->AddSlot().AutoHeight().Padding(0, 5)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true)
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::Recall ? EVisibility::Visible : EVisibility::Collapsed; })
            .Text_Lambda([this]() { return FText::FromString(UTF8_TO_TCHAR(Model->GetCard().Question)); })];
        // Put correction beside the question, before the choices, so answering
        // never hides the explanation below a long chooser or footer.
        Lesson->AddSlot().AutoHeight().Padding(0, 6)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true)
            .Text_Lambda([this]() { return FText::FromString(UTF8_TO_TCHAR((Model->GetStage() == MikdashPreparation::Stage::Reflection ? Model->GetPreparationSummary() : (bHint ? Model->GetCard().Hint : Model->GetFeedback())))); })];
        for (const auto Answer : {MikdashPreparation::Answer::AllClear, MikdashPreparation::Answer::CheckRemainingRequirements, MikdashPreparation::Answer::SeekReview})
        {
            Lesson->AddSlot().AutoHeight().Padding(0, 3)
            [SNew(SButton).TextStyle(&ButtonText).ContentPadding(8)
                .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::Recall ? EVisibility::Visible : EVisibility::Collapsed; })
                .Text(FText::FromString(UTF8_TO_TCHAR(MikdashPreparation::AnswerLabel(Answer))))
                .OnClicked_Lambda([this, Answer]() { bHint = false; Model->SubmitAnswer(Answer); ResetScroll(); return FReply::Handled().SetUserFocus(AsShared()); })];
        }
        Lesson->AddSlot().AutoHeight().Padding(0, 4)
        [SNew(SButton).TextStyle(&ButtonText).ContentPadding(8).Text(FText::FromString(TEXT("Show a hint")))
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::Recall ? EVisibility::Visible : EVisibility::Collapsed; })
            .OnClicked_Lambda([this]() { bHint = true; ResetScroll(); return FReply::Handled().SetUserFocus(AsShared()); })];
        Lesson->AddSlot().AutoHeight().Padding(0, 6)
        [SNew(SBorder).Padding(18).BorderBackgroundColor(FLinearColor(0.04f, 0.04f, 0.05f, 1.f))
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::ModestPreparation ? EVisibility::Visible : EVisibility::Collapsed; })
            [Text("Private preparation happens offscreen. No undressing or immersion is depicted. Completing this scene records the lesson only; outstanding requirements remain outstanding.")]];
        Lesson->AddSlot().AutoHeight().Padding(0, 5)
        [SNew(SButton).TextStyle(&ButtonText).ContentPadding(10).Text(FText::FromString(TEXT("Continue after the private preparation")))
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::ModestPreparation ? EVisibility::Visible : EVisibility::Collapsed; })
            .OnClicked_Lambda([this]() { bHint = false; Model->CompleteModestPreparation(); ResetScroll(); return FReply::Handled().SetUserFocus(AsShared()); })];
        Lesson->AddSlot().AutoHeight().Padding(0, 6)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)).AutoWrapText(true)
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::Inactive ? EVisibility::Collapsed : EVisibility::Visible; })
            .Text_Lambda([this]() { return FText::FromString(UTF8_TO_TCHAR(Model->GetCard().Source)); })];
        ChildSlot[SNew(SBorder).Padding(24).HAlign(HAlign_Center).VAlign(VAlign_Center)
            .BorderBackgroundColor(FLinearColor(0.025f, 0.035f, 0.05f, 1.f))
            [SNew(SBox).WidthOverride(900).MaxDesiredHeight(640)
                [SNew(SVerticalBox)
                    + SVerticalBox::Slot().FillHeight(1.f)
                    [SAssignNew(Scroll, SScrollBox) + SScrollBox::Slot()[Content]]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 6)
                    [SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1.f).Padding(0, 0, 6, 0)
                        [SNew(SButton).TextStyle(&ButtonText).ContentPadding(8).Text(FText::FromString(TEXT("Choose another story")))
                            .Visibility_Lambda([this]() { return bChoosingStory ? EVisibility::Collapsed : EVisibility::Visible; })
                            .OnClicked_Lambda([this]() { bChoosingStory = true; bHint = false; ResetScroll(); return FReply::Handled().SetUserFocus(AsShared()); })]
                        + SHorizontalBox::Slot().FillWidth(1.f)
                        [SNew(SButton).TextStyle(&ButtonText).ContentPadding(8).Text(FText::FromString(TEXT("Back to walkthrough menu")))
                            .OnClicked_Lambda([this]() { Back.ExecuteIfBound(); return FReply::Handled(); })]]]]];
    }
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override
    {
        // Escape and P both return to the walkthrough menu. Handling P here keeps
        // it from falling through to the controller's paused P binding, which
        // would resume play and capture the mouse straight from the lesson.
        if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::P)
        {
            if (!Event.IsRepeat()) Back.ExecuteIfBound();
            return FReply::Handled();
        }
        return SCompoundWidget::OnKeyDown(Geometry, Event);
    }
private:
    void ResetScroll() { if (Scroll.IsValid()) Scroll->ScrollToStart(); }
    TSharedRef<STextBlock> Text(const char* Value, int Size = 18)
    {
        return SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", Size))
            .AutoWrapText(true).Text(FText::FromString(UTF8_TO_TCHAR(Value)));
    }
    MikdashPreparation::Journey* Model = nullptr;
    FSimpleDelegate Back;
    FTextBlockStyle ButtonText;
    TSharedPtr<SScrollBox> Scroll;
    bool bChoosingStory = true;
    bool bHint = false;
};
