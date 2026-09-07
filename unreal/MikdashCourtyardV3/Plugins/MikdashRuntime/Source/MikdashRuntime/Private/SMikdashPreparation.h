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
        ButtonText = FCoreStyle::Get().GetWidgetStyle<FTextBlockStyle>("NormalText");
        ButtonText.SetFont(FCoreStyle::GetDefaultFontStyle("Regular", 18));
        TSharedRef<SVerticalBox> Content = SNew(SVerticalBox);
        Content->AddSlot().AutoHeight().Padding(0, 8)[Text("Before you arrive", 28)];
        Content->AddSlot().AutoHeight().Padding(0, 8)[Text("Practice with a fictional visitor. These short lessons introduce distinctions; they do not determine your personal status or grant entry to a sacred area.")];
        const MikdashPreparation::Scenario Scenarios[] = {
            MikdashPreparation::Scenario::PreparedPilgrim, MikdashPreparation::Scenario::CorpseProcessPending,
            MikdashPreparation::Scenario::AwaitingDayCompletion, MikdashPreparation::Scenario::OfferingPending,
            MikdashPreparation::Scenario::UnknownHistory};
        for (const auto Scenario : Scenarios)
        {
            Content->AddSlot().AutoHeight().Padding(0, 3)
            [SNew(SButton).TextStyle(&ButtonText).ContentPadding(10)
                .Text(FText::FromString(UTF8_TO_TCHAR(MikdashPreparation::GetScenarioCard(Scenario).Title)))
                .OnClicked_Lambda([this, Scenario]() { Model->Start(Scenario); bHint = false; return FReply::Handled(); })];
        }
        Content->AddSlot().AutoHeight().Padding(0, 14)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true)
            .Text_Lambda([this]() { return FText::FromString(Model->GetStage() == MikdashPreparation::Stage::Inactive
                ? TEXT("Choose a story above to begin.") : FString::Printf(TEXT("%s\n\n%s"),
                    UTF8_TO_TCHAR(Model->GetCard().FictionalHistory), UTF8_TO_TCHAR(Model->GetCard().Question))); })];
        for (const auto Answer : {MikdashPreparation::Answer::AllClear, MikdashPreparation::Answer::CheckRemainingRequirements, MikdashPreparation::Answer::SeekReview})
        {
            Content->AddSlot().AutoHeight().Padding(0, 3)
            [SNew(SButton).TextStyle(&ButtonText).ContentPadding(10)
                .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::Recall ? EVisibility::Visible : EVisibility::Collapsed; })
                .Text(FText::FromString(UTF8_TO_TCHAR(MikdashPreparation::AnswerLabel(Answer))))
                .OnClicked_Lambda([this, Answer]() { bHint = false; Model->SubmitAnswer(Answer); return FReply::Handled(); })];
        }
        Content->AddSlot().AutoHeight().Padding(0, 5)
        [SNew(SButton).TextStyle(&ButtonText).ContentPadding(10).Text(FText::FromString(TEXT("Show a hint")))
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::Recall ? EVisibility::Visible : EVisibility::Collapsed; })
            .OnClicked_Lambda([this]() { bHint = true; return FReply::Handled(); })];
        Content->AddSlot().AutoHeight().Padding(0, 8)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true)
            .Text_Lambda([this]() { return FText::FromString(UTF8_TO_TCHAR((Model->GetStage() == MikdashPreparation::Stage::Reflection ? Model->GetPreparationSummary() : (bHint ? Model->GetCard().Hint : Model->GetFeedback())))); })];
        Content->AddSlot().AutoHeight().Padding(0, 10)
        [SNew(SBorder).Padding(18).BorderBackgroundColor(FLinearColor(0.04f, 0.04f, 0.05f, 1.f))
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::ModestPreparation ? EVisibility::Visible : EVisibility::Collapsed; })
            [Text("Private preparation happens offscreen. No undressing or immersion is depicted. Completing this scene records the lesson only; outstanding requirements remain outstanding.")]];
        Content->AddSlot().AutoHeight().Padding(0, 5)
        [SNew(SButton).TextStyle(&ButtonText).ContentPadding(10).Text(FText::FromString(TEXT("Continue after the private preparation")))
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::ModestPreparation ? EVisibility::Visible : EVisibility::Collapsed; })
            .OnClicked_Lambda([this]() { bHint = false; Model->CompleteModestPreparation(); return FReply::Handled(); })];
        Content->AddSlot().AutoHeight().Padding(0, 10)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)).AutoWrapText(true)
            .Visibility_Lambda([this]() { return Model->GetStage() == MikdashPreparation::Stage::Inactive ? EVisibility::Collapsed : EVisibility::Visible; })
            .Text_Lambda([this]() { return FText::FromString(UTF8_TO_TCHAR(Model->GetCard().Source)); })];
        Content->AddSlot().AutoHeight().Padding(0, 8)
        [SNew(SButton).TextStyle(&ButtonText).ContentPadding(12).Text(FText::FromString(TEXT("Back to walkthrough menu")))
            .OnClicked_Lambda([this]() { Back.ExecuteIfBound(); return FReply::Handled(); })];
        ChildSlot[SNew(SBorder).Padding(24).HAlign(HAlign_Center).VAlign(VAlign_Center)
            .BorderBackgroundColor(FLinearColor(0.025f, 0.035f, 0.05f, 1.f))
            [SNew(SBox).WidthOverride(900).MaxDesiredHeight(640)
                [SNew(SScrollBox) + SScrollBox::Slot()[Content]]]];
    }
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override
    {
        if (Event.GetKey() == EKeys::Escape) { if (!Event.IsRepeat()) Back.ExecuteIfBound(); return FReply::Handled(); }
        return SCompoundWidget::OnKeyDown(Geometry, Event);
    }
private:
    TSharedRef<STextBlock> Text(const char* Value, int Size = 18)
    {
        return SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", Size))
            .AutoWrapText(true).Text(FText::FromString(UTF8_TO_TCHAR(Value)));
    }
    MikdashPreparation::Journey* Model = nullptr;
    FSimpleDelegate Back;
    FTextBlockStyle ButtonText;
    bool bHint = false;
};
