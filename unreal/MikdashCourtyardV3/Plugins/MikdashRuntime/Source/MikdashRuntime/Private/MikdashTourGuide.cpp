// MikdashTourGuide.cpp -- see MikdashTourGuide.h for the design and its reasons.
//
// The UI here is deliberately the SAME shape as the resident dialog panel in
// MikdashPlayerController.cpp: one SCompoundWidget added once to the viewport,
// EVisibility::HitTestInvisible throughout, driven entirely by FString getters on the
// owning actor read through Text_Lambda. It never pauses the world, never captures the
// mouse and never changes the input mode, so talking to a resident, flying the dove and
// the pause menu all keep working while the tour is up.

#include "MikdashTourGuide.h"

#include "MikdashCodex.h"
#include "MikdashFrontEnd.h"

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashTour, Log, All);

#define LOCTEXT_NAMESPACE "MikdashTour"

namespace
{
/** Above the resident overlay (10) and below the pause menu (100). */
constexpr int32 ZOrderTour = 20;

FText TextField(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field)
{
    FString Value;
    if (Object.IsValid() && Object->TryGetStringField(Field, Value) && !Value.IsEmpty())
    {
        return FText::FromString(Value);
    }
    return FText::GetEmpty();
}

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
        OutEnglish = TextField(Parent, Field);
    }
}

/** [x, y, z] -> FVector. Returns false for a malformed or non-finite triple rather than
 * letting a NaN reach the route, where it would poison every distance. */
bool VectorField(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, FVector& Out)
{
    const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
    if (!Object.IsValid() || !Object->TryGetArrayField(Field, Array) || Array == nullptr) return false;
    if (Array->Num() != 3) return false;
    double Values[3] = {0, 0, 0};
    for (int32 Index = 0; Index < 3; ++Index)
    {
        if (!(*Array)[Index].IsValid() || !(*Array)[Index]->TryGetNumber(Values[Index])) return false;
        if (!FMath::IsFinite(Values[Index])) return false;
    }
    Out = FVector(Values[0], Values[1], Values[2]);
    return true;
}

double NumberField(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, double Fallback)
{
    double Value = 0.0;
    if (Object.IsValid() && Object->TryGetNumberField(Field, Value) && FMath::IsFinite(Value)) return Value;
    return Fallback;
}

FString Join(const TArray<FText>& Lines, const TCHAR* Bullet)
{
    FString Out;
    for (const FText& Line : Lines)
    {
        if (Line.IsEmpty()) continue;
        Out += Bullet;
        Out += Line.ToString();
        Out += TEXT("\n");
    }
    return Out.TrimEnd();
}

/** "Name" plus the Hebrew name when the JSON carries one. An empty Hebrew field
 * means nobody has written it, never that no translation is wanted. */
FString WithHebrew(const FText& English, const FText& Hebrew)
{
    if (Hebrew.IsEmpty()) return English.ToString();
    return English.ToString() + TEXT("   ") + Hebrew.ToString();
}
} // namespace

// ---------------------------------------------------------------------------
// The overlay. Same convention as the resident dialog panel.
// ---------------------------------------------------------------------------

namespace
{
class SMikdashTourOverlay : public SCompoundWidget
{
public:
    using Getter = FString (AMikdashTourGuide::*)() const;
    enum class Mode { Status, Prompt, Stop, Codex };

    SLATE_BEGIN_ARGS(SMikdashTourOverlay) {}
        SLATE_ARGUMENT(TWeakObjectPtr<AMikdashTourGuide>, Guide)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args)
    {
        Guide = Args._Guide;
        SetVisibility(EVisibility::HitTestInvisible);
        const FLinearColor Panel(0.025f, 0.035f, 0.05f, 0.90f);
        const FLinearColor Hint(0.025f, 0.035f, 0.05f, 0.55f);
        const FLinearColor Bright(0.90f, 0.92f, 0.96f, 1.f);
        const FLinearColor Dim(0.66f, 0.70f, 0.78f, 1.f);
        const FLinearColor Quiet(0.56f, 0.60f, 0.68f, 1.f);

        ChildSlot
        [
            SNew(SOverlay)
            // Progress line, top right, whenever the tour is running.
            + SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Top).Padding(28, 24)
            [
                SNew(SBorder).BorderBackgroundColor(Hint).Padding(FMargin(14, 8))
                .Visibility_Lambda([this]() { return Visible(Mode::Status); })
                [SNew(STextBlock).ColorAndOpacity(Dim)
                    .Font(FCoreStyle::GetDefaultFontStyle("Regular", 15))
                    .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetStatusLine); })]
            ]
            // Arrival / off-route / "you are near" prompt, above the talk prompt.
            + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0, 0, 0, 140)
            [
                SNew(SBorder).BorderBackgroundColor(Hint).Padding(FMargin(14, 7))
                .Visibility_Lambda([this]() { return Visible(Mode::Prompt); })
                [SNew(STextBlock).ColorAndOpacity(Bright)
                    .Font(FCoreStyle::GetDefaultFontStyle("Regular", 16))
                    .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetPromptText); })]
            ]
            // The stop panel.
            + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0, 0, 0, 56)
            [
                SNew(SBox).WidthOverride(880)
                .Visibility_Lambda([this]() { return Visible(Mode::Stop); })
                [
                    SNew(SBorder).BorderBackgroundColor(Panel).Padding(FMargin(24, 18))
                    [
                        SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 21)).AutoWrapText(true)
                            .ColorAndOpacity(Bright)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetHeading); })]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Italic", 15)).AutoWrapText(true)
                            .ColorAndOpacity(Dim)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetSubheading); })]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17)).AutoWrapText(true)
                            .ColorAndOpacity(Bright)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetBody); })]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)).AutoWrapText(true)
                            .ColorAndOpacity(Dim)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetMeasurementsBlock); })]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 13)).AutoWrapText(true)
                            .ColorAndOpacity(Quiet)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetSourcesBlock); })]
                        + SVerticalBox::Slot().AutoHeight()
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 13))
                            .ColorAndOpacity(Quiet).AutoWrapText(true)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetFooter); })]
                    ]
                ]
            ]
            // The codex panel, in the same place, instead of the stop panel.
            + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
            [
                SNew(SBox).WidthOverride(920)
                .Visibility_Lambda([this]() { return Visible(Mode::Codex); })
                [
                    SNew(SBorder).BorderBackgroundColor(Panel).Padding(FMargin(26, 20))
                    [
                        SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 20)).AutoWrapText(true)
                            .ColorAndOpacity(Bright)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetCodexHeading); })]
                        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 15)).AutoWrapText(true)
                            .ColorAndOpacity(Bright)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetCodexBody); })]
                        + SVerticalBox::Slot().AutoHeight()
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 13)).AutoWrapText(true)
                            .ColorAndOpacity(Quiet)
                            .Text_Lambda([this]() { return Text(&AMikdashTourGuide::GetCodexFooter); })]
                    ]
                ]
            ]
        ];
    }

private:
    FText Text(Getter Read) const
    {
        const AMikdashTourGuide* Owner = Guide.Get();
        return Owner ? FText::FromString((Owner->*Read)()) : FText::GetEmpty();
    }
    EVisibility Visible(Mode Which) const
    {
        const AMikdashTourGuide* Owner = Guide.Get();
        if (Owner == nullptr) return EVisibility::Collapsed;
        bool bShow = false;
        switch (Which)
        {
        case Mode::Status: bShow = Owner->IsTourRunning() && !Owner->IsCodexPanelVisible(); break;
        case Mode::Prompt: bShow = Owner->IsPromptVisible(); break;
        case Mode::Stop:   bShow = Owner->IsStopPanelVisible(); break;
        case Mode::Codex:  bShow = Owner->IsCodexPanelVisible(); break;
        }
        return bShow ? EVisibility::HitTestInvisible : EVisibility::Collapsed;
    }
    TWeakObjectPtr<AMikdashTourGuide> Guide;
};
} // namespace

// ---------------------------------------------------------------------------
// Lifetime
// ---------------------------------------------------------------------------

AMikdashTourGuide::AMikdashTourGuide()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;
    SetCanBeDamaged(false);
}

void AMikdashTourGuide::BeginPlay()
{
    Super::BeginPlay();

    if (!ReloadRoute())
    {
        UE_LOG(LogMikdashTour, Error, TEXT("Tour route not loaded: %s"), *LoadError);
    }

    Codex = AMikdashCodex::Get(this);
    if (Codex == nullptr && bSpawnCodexIfMissing)
    {
        FActorSpawnParameters Params;
        Params.ObjectFlags |= RF_Transient;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Codex = GetWorld() ? GetWorld()->SpawnActor<AMikdashCodex>(AMikdashCodex::StaticClass(), FTransform::Identity, Params) : nullptr;
    }

    RefreshMarkerCache();
    UpdateMarkers();

    if (APlayerController* Controller = GetController())
    {
        if (bBindKeys) BindKeys(Controller);
        if (UWorld* World = GetWorld())
        {
            if (World->GetGameViewport() != nullptr)
            {
                OverlayWidget = SNew(SMikdashTourOverlay).Guide(this);
                World->GetGameViewport()->AddViewportWidgetContent(OverlayWidget.ToSharedRef(), ZOrderTour);
            }
        }
    }

    if (bRegisterWithFrontEnd)
    {
        if (UMikdashFrontEnd* FrontEnd = UMikdashFrontEnd::Get(this))
        {
            FMikdashGuidedTourRequest Request;
            Request.BindUObject(this, &AMikdashTourGuide::HandleMenuRequest);
            // The label says what the entry does, and says it in the language of the
            // thing being toured rather than of the software.
            FrontEnd->RegisterGuidedTour(Request, LOCTEXT("TourLabel", "Guided tour: the pilgrim's way"));
        }
    }
}

void AMikdashTourGuide::EndPlay(const EEndPlayReason::Type Reason)
{
    if (bRegisterWithFrontEnd)
    {
        if (UMikdashFrontEnd* FrontEnd = UMikdashFrontEnd::Get(this))
        {
            FrontEnd->UnregisterGuidedTour();
        }
    }
    StopCameraFlight(false);
    ReleaseKeys();
    if (UWorld* World = GetWorld())
    {
        if (World->GetGameViewport() != nullptr && OverlayWidget.IsValid())
        {
            World->GetGameViewport()->RemoveViewportWidgetContent(OverlayWidget.ToSharedRef());
        }
    }
    OverlayWidget.Reset();
    Super::EndPlay(Reason);
}

APlayerController* AMikdashTourGuide::GetController() const
{
    return GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
}

AMikdashTourGuide* AMikdashTourGuide::Get(const UObject* WorldContext)
{
    const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
    if (World == nullptr) return nullptr;
    for (TActorIterator<AMikdashTourGuide> It(const_cast<UWorld*>(World)); It; ++It)
    {
        if (IsValid(*It)) return *It;
    }
    return nullptr;
}

// ---------------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------------

FString AMikdashTourGuide::GetContentPath() const
{
    return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / ContentRelativePath);
}

bool AMikdashTourGuide::ReloadRoute()
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
    const TArray<TSharedPtr<FJsonValue>>* StopArray = nullptr;
    if (!Root->TryGetArrayField(TEXT("stops"), StopArray) || StopArray == nullptr || StopArray->Num() == 0)
    {
        LoadError = TEXT("no \"stops\" array, or it is empty");
        return false;
    }

    const TSharedPtr<FJsonObject>* Defaults = nullptr;
    Root->TryGetObjectField(TEXT("defaults"), Defaults);
    const double DefaultArrive = Defaults ? NumberField(*Defaults, TEXT("arriveRadiusCm"), MikdashTour::DefaultArriveRadiusCm)
                                          : MikdashTour::DefaultArriveRadiusCm;
    const double DefaultLeave = Defaults ? NumberField(*Defaults, TEXT("leaveRadiusCm"), MikdashTour::DefaultLeaveRadiusCm)
                                         : MikdashTour::DefaultLeaveRadiusCm;

    // Build into locals; the live route is not touched until the whole file passes.
    MikdashTour::Route NewRoute;
    TArray<TArray<ANSICHAR>> NewKeys;
    TArray<FMikdashTourStopText> NewText;
    NewKeys.Reserve(StopArray->Num());
    // Reserved up front: the keys are pointed at by MikdashTour::Stop, so the array must
    // not reallocate while stops hold pointers into it.
    NewKeys.SetNum(StopArray->Num());

    for (int32 Row = 0; Row < StopArray->Num(); ++Row)
    {
        const TSharedPtr<FJsonObject> Object = (*StopArray)[Row].IsValid() ? (*StopArray)[Row]->AsObject() : nullptr;
        if (!Object.IsValid())
        {
            LoadError = FString::Printf(TEXT("stop %d is not an object"), Row);
            return false;
        }
        FString Key;
        if (!Object->TryGetStringField(TEXT("key"), Key) || Key.IsEmpty())
        {
            LoadError = FString::Printf(TEXT("stop %d has no key"), Row);
            return false;
        }

        FMikdashTourStopText Text;
        Text.Key = FName(*Key);
        LocalisedField(Object, TEXT("name"), Text.Name, Text.NameHebrew);
        FText UnusedHebrew;
        LocalisedField(Object, TEXT("subtitle"), Text.Subtitle, UnusedHebrew);
        LocalisedField(Object, TEXT("whatHappensHere"), Text.WhatHappensHere, UnusedHebrew);
        LocalisedField(Object, TEXT("explanation"), Text.Explanation, UnusedHebrew);
        if (Text.Name.IsEmpty()) Text.Name = FText::FromString(Key);

        FString ConfidenceText;
        Object->TryGetStringField(TEXT("confidence"), ConfidenceText);
        MikdashTour::Confidence Parsed = MikdashTour::Confidence::Authored;
        if (!MikdashTour::ParseConfidence(TCHAR_TO_ANSI(*ConfidenceText), Parsed))
        {
            LoadError = FString::Printf(TEXT("stop \"%s\" has an unrecognised confidence label \"%s\""), *Key, *ConfidenceText);
            return false;
        }
        Text.Confidence = Parsed == MikdashTour::Confidence::Certain ? EMikdashConfidenceLabel::Certain
                        : Parsed == MikdashTour::Confidence::Disputed ? EMikdashConfidenceLabel::Disputed
                        : EMikdashConfidenceLabel::Authored;

        const TArray<TSharedPtr<FJsonValue>>* MeasurementArray = nullptr;
        if (Object->TryGetArrayField(TEXT("measurements"), MeasurementArray) && MeasurementArray != nullptr)
        {
            for (const TSharedPtr<FJsonValue>& Value : *MeasurementArray)
            {
                const TSharedPtr<FJsonObject> Measurement = Value.IsValid() ? Value->AsObject() : nullptr;
                if (!Measurement.IsValid()) continue;
                FText Label, LabelHebrew;
                LocalisedField(Measurement, TEXT("label"), Label, LabelHebrew);
                FString Amount;
                double Amot = 0.0, Cm = 0.0, Tefachim = 0.0;
                int32 Count = 0;
                if (Measurement->TryGetNumberField(TEXT("count"), Count)) Amount += FString::Printf(TEXT("%d"), Count);
                if (Measurement->TryGetNumberField(TEXT("amot"), Amot))
                {
                    if (!Amount.IsEmpty()) Amount += TEXT(", ");
                    Amount += FString::Printf(TEXT("%g amot"), Amot);
                }
                if (Measurement->TryGetNumberField(TEXT("tefachim"), Tefachim))
                {
                    if (!Amount.IsEmpty()) Amount += TEXT(", ");
                    Amount += FString::Printf(TEXT("%g tefachim"), Tefachim);
                }
                if (Measurement->TryGetNumberField(TEXT("cm"), Cm) && Cm > 0.0)
                {
                    Amount += Amount.IsEmpty() ? FString::Printf(TEXT("%g cm"), Cm)
                                               : FString::Printf(TEXT(" = %g cm"), Cm);
                }
                FString Source;
                Measurement->TryGetStringField(TEXT("source"), Source);
                FString Line = Label.IsEmpty() ? Amount : (Label.ToString() + TEXT(": ") + Amount);
                if (!Source.IsEmpty()) Line += TEXT("   [") + Source + TEXT("]");
                Text.Measurements.Add(FText::FromString(Line));
            }
        }

        const TArray<TSharedPtr<FJsonValue>>* SourceArray = nullptr;
        if (Object->TryGetArrayField(TEXT("sources"), SourceArray) && SourceArray != nullptr)
        {
            for (const TSharedPtr<FJsonValue>& Value : *SourceArray)
            {
                FString Line;
                if (Value.IsValid() && Value->TryGetString(Line) && !Line.IsEmpty()) Text.Sources.Add(FText::FromString(Line));
            }
        }
        const TArray<TSharedPtr<FJsonValue>>* CodexArray = nullptr;
        if (Object->TryGetArrayField(TEXT("codexEntries"), CodexArray) && CodexArray != nullptr)
        {
            for (const TSharedPtr<FJsonValue>& Value : *CodexArray)
            {
                FString Line;
                if (Value.IsValid() && Value->TryGetString(Line) && !Line.IsEmpty()) Text.CodexEntries.Add(FName(*Line));
            }
        }
        const TSharedPtr<FJsonObject>* Narration = nullptr;
        if (Object->TryGetObjectField(TEXT("narrationAudio"), Narration) && Narration != nullptr)
        {
            (*Narration)->TryGetStringField(TEXT("asset"), Text.NarrationAudioAsset);
        }

        MikdashTour::Stop Geometry;
        FVector Stand, Look;
        if (!VectorField(Object, TEXT("stand"), Stand) || !VectorField(Object, TEXT("look"), Look))
        {
            LoadError = FString::Printf(TEXT("stop \"%s\" has a missing or non-finite stand/look"), *Key);
            return false;
        }
        Text.Stand = Stand;
        Text.Look = Look;

        // The key has to outlive this function: MikdashTour::Stop keeps a const char* to
        // it, so it is copied into storage the route owns for as long as the route does.
        // Narrowed one character at a time rather than through a conversion macro: the
        // keys are ASCII by construction (the JSON's own key field), and this keeps the
        // buffer's element type exactly the char the header expects.
        NewKeys[Row].Reserve(Key.Len() + 1);
        for (int32 Char = 0; Char < Key.Len(); ++Char)
        {
            NewKeys[Row].Add(static_cast<ANSICHAR>(Key[Char]));
        }
        NewKeys[Row].Add('\0');
        Geometry.Key = NewKeys[Row].GetData();
        Geometry.Stand = ToTourPoint(Stand);
        Geometry.Look = ToTourPoint(Look);
        Geometry.ArriveRadiusCm = NumberField(Object, TEXT("arriveRadiusCm"), DefaultArrive);
        Geometry.LeaveRadiusCm = NumberField(Object, TEXT("leaveRadiusCm"), DefaultLeave);
        Geometry.CameraSeconds = NumberField(Object, TEXT("cameraSeconds"), 0.0);

        const TArray<TSharedPtr<FJsonValue>>* ApproachArray = nullptr;
        if (Object->TryGetArrayField(TEXT("approach"), ApproachArray) && ApproachArray != nullptr)
        {
            if (static_cast<uint32>(ApproachArray->Num()) > MikdashTour::MaxWaypoints)
            {
                LoadError = FString::Printf(TEXT("stop \"%s\" has %d approach waypoints; the limit is %d"),
                                            *Key, ApproachArray->Num(), static_cast<int32>(MikdashTour::MaxWaypoints));
                return false;
            }
            for (const TSharedPtr<FJsonValue>& Value : *ApproachArray)
            {
                const TArray<TSharedPtr<FJsonValue>>* Triple = nullptr;
                if (!Value.IsValid() || !Value->TryGetArray(Triple) || Triple == nullptr || Triple->Num() != 3)
                {
                    LoadError = FString::Printf(TEXT("stop \"%s\" has a malformed approach waypoint"), *Key);
                    return false;
                }
                double Values[3] = {0, 0, 0};
                for (int32 Index = 0; Index < 3; ++Index)
                {
                    if (!(*Triple)[Index]->TryGetNumber(Values[Index]) || !FMath::IsFinite(Values[Index]))
                    {
                        LoadError = FString::Printf(TEXT("stop \"%s\" has a non-finite approach waypoint"), *Key);
                        return false;
                    }
                }
                Geometry.Waypoints[Geometry.WaypointCount++] = MikdashTour::Point3{Values[0], Values[1], Values[2]};
            }
        }

        if (!NewRoute.Add(Geometry))
        {
            LoadError = FString::Printf(TEXT("more than %d stops"), static_cast<int32>(MikdashTour::MaxStops));
            return false;
        }
        NewText.Add(MoveTemp(Text));
    }

    std::size_t BadStop = 0;
    const MikdashTour::Refusal Why = NewRoute.Validate(&BadStop);
    if (Why != MikdashTour::Refusal::None)
    {
        const FString BadKey = NewText.IsValidIndex(static_cast<int32>(BadStop)) ? NewText[static_cast<int32>(BadStop)].Key.ToString() : TEXT("?");
        LoadError = FString::Printf(TEXT("route refused at stop %d (\"%s\"): %s"),
                                    static_cast<int32>(BadStop), *BadKey, ANSI_TO_TCHAR(MikdashTour::RefusalText(Why)));
        return false;
    }

    KeyStorage = MoveTemp(NewKeys);
    // Rebuild the route against the storage this object now owns, because moving the
    // arrays moved the buffers the stops were pointing at.
    Route.Clear();
    for (int32 Row = 0; Row < NewText.Num(); ++Row)
    {
        MikdashTour::Stop Geometry = NewRoute.At(static_cast<std::size_t>(Row));
        Geometry.Key = KeyStorage[Row].GetData();
        Route.Add(Geometry);
    }
    StopText = MoveTemp(NewText);
    Guide.SetRoute(&Route);
    ApplyTuning();
    bRouteLoaded = true;
    bEverStarted = false;

    UE_LOG(LogMikdashTour, Log, TEXT("Tour route loaded: %d stops, %.0f m of walking, from %s"),
           StopText.Num(), Route.TotalLengthCm() / 100.0, *Path);
    return true;
}

void AMikdashTourGuide::ApplyTuning()
{
    MikdashTour::CameraTuning Tuning;
    Tuning.SpeedCmPerSec = CameraSpeedCmPerSec;
    Tuning.MinSeconds = CameraMinSeconds;
    Tuning.MaxSeconds = CameraMaxSeconds;
    Guide.SetCameraTuning(Tuning);
    // Refuses a pair that cannot hold, and keeps the working defaults if so.
    Guide.SetCorridor(OffRouteCm, RejoinCm);
}

bool AMikdashTourGuide::GetStopAt(int32 Index, FMikdashTourStopText& OutStop) const
{
    if (!StopText.IsValidIndex(Index)) return false;
    OutStop = StopText[Index];
    return true;
}

// ---------------------------------------------------------------------------
// Running the tour
// ---------------------------------------------------------------------------

void AMikdashTourGuide::HandleMenuRequest()
{
    BeginOrResumeTour();
}

void AMikdashTourGuide::BeginOrResumeTour()
{
    if (!bRouteLoaded)
    {
        TransientNote = FString::Printf(TEXT("The tour could not load: %s"), *LoadError);
        TransientNoteUntil = FPlatformTime::Seconds() + 8.0;
        Panel = EMikdashTourPanel::Stop;
        return;
    }
    if (Guide.IsPaused())
    {
        ResumeTour();
        return;
    }
    if (Guide.IsRunning())
    {
        Panel = EMikdashTourPanel::Stop;
        return;
    }
    if (bEverStarted && Guide.VisitedCount() > 0)
    {
        // Come back to the stop he left from, not to the beginning.
        const MikdashTour::Bookmark Saved = Guide.Save();
        Guide.Restore(Saved);
        GoToStopIndex(static_cast<int32>(Saved.TargetIndex));
        Panel = EMikdashTourPanel::Stop;
        return;
    }
    BeginTourFromStart();
}

void AMikdashTourGuide::BeginTourFromStart()
{
    if (!bRouteLoaded) return;
    const MikdashTour::Mode Mode = DefaultMode == EMikdashTourMode::WalkMeThere
        ? MikdashTour::Mode::WalkMeThere : MikdashTour::Mode::FollowTheMarker;
    if (!Guide.Begin(Mode, ToTourPoint(GetVisitorLocation())))
    {
        TransientNote = TEXT("The route refused to start.");
        TransientNoteUntil = FPlatformTime::Seconds() + 6.0;
        return;
    }
    bEverStarted = true;
    Panel = EMikdashTourPanel::Stop;
    WanderOffer = INDEX_NONE;
    if (Guide.IsCameraMoving()) StartCameraFlight();
    UpdateMarkers();
}

void AMikdashTourGuide::PauseTour()
{
    Guide.Pause();
    StopCameraFlight(false);
}

void AMikdashTourGuide::ResumeTour()
{
    Guide.Resume();
    Panel = EMikdashTourPanel::Stop;
    if (Guide.IsCameraMoving()) StartCameraFlight();
}

void AMikdashTourGuide::LeaveTour()
{
    StopCameraFlight(false);
    Guide.EndTour();
    Panel = EMikdashTourPanel::Hidden;
    UpdateMarkers();
}

void AMikdashTourGuide::NextStop()
{
    if (!Guide.IsRunning()) return;
    const bool bMoved = Guide.Next(ToTourPoint(GetVisitorLocation()));
    if (!bMoved)
    {
        TransientNote = LOCTEXT("LastStopNotSeen", "This is the last stop; go to it before finishing.").ToString();
        TransientNoteUntil = FPlatformTime::Seconds() + 5.0;
        return;
    }
    if (Guide.GetPhase() == MikdashTour::Phase::Finished)
    {
        StopCameraFlight(false);
        Panel = EMikdashTourPanel::Stop;
        UpdateMarkers();
        OnTourFinished.Broadcast();
        return;
    }
    WanderOffer = INDEX_NONE;
    if (Guide.IsCameraMoving()) StartCameraFlight();
    UpdateMarkers();
}

void AMikdashTourGuide::PreviousStop()
{
    if (!Guide.IsRunning()) return;
    if (!Guide.Previous(ToTourPoint(GetVisitorLocation()))) return;
    WanderOffer = INDEX_NONE;
    if (Guide.IsCameraMoving()) StartCameraFlight();
    UpdateMarkers();
}

bool AMikdashTourGuide::GoToStopByKey(FName StopKey)
{
    for (int32 Index = 0; Index < StopText.Num(); ++Index)
    {
        if (StopText[Index].Key == StopKey) return GoToStopIndex(Index);
    }
    return false;
}

bool AMikdashTourGuide::GoToStopIndex(int32 Index)
{
    if (!StopText.IsValidIndex(Index)) return false;
    if (!Guide.GoToStop(static_cast<std::size_t>(Index), ToTourPoint(GetVisitorLocation()))) return false;
    WanderOffer = INDEX_NONE;
    Panel = EMikdashTourPanel::Stop;
    if (Guide.IsCameraMoving()) StartCameraFlight(); else StopCameraFlight(false);
    UpdateMarkers();
    return true;
}

void AMikdashTourGuide::SetTourMode(EMikdashTourMode Mode)
{
    const MikdashTour::Mode Wanted = Mode == EMikdashTourMode::WalkMeThere
        ? MikdashTour::Mode::WalkMeThere : MikdashTour::Mode::FollowTheMarker;
    Guide.SetMode(Wanted, ToTourPoint(GetVisitorLocation()));
    if (Guide.IsCameraMoving()) StartCameraFlight(); else StopCameraFlight(false);
    UpdateMarkers();
}

void AMikdashTourGuide::ToggleTourMode()
{
    SetTourMode(GetTourMode() == EMikdashTourMode::WalkMeThere
                ? EMikdashTourMode::FollowTheMarker : EMikdashTourMode::WalkMeThere);
}

EMikdashTourMode AMikdashTourGuide::GetTourMode() const
{
    return Guide.GetMode() == MikdashTour::Mode::WalkMeThere
        ? EMikdashTourMode::WalkMeThere : EMikdashTourMode::FollowTheMarker;
}

void AMikdashTourGuide::RejoinRoute()
{
    if (!Guide.IsRunning()) return;
    // If he has wandered up to a different stop, take him THERE rather than marching him
    // back to a place he has walked past. That is what "rejoin" means to a person.
    if (WanderOffer != INDEX_NONE)
    {
        GoToStopIndex(WanderOffer);
        return;
    }
    if (GetTourMode() == EMikdashTourMode::WalkMeThere)
    {
        StartCameraFlight();
        return;
    }
    TransientNote = LOCTEXT("HeadForMarker", "Head for the marker to rejoin the route.").ToString();
    TransientNoteUntil = FPlatformTime::Seconds() + 5.0;
}

void AMikdashTourGuide::TogglePanel()
{
    if (!Guide.IsRunning() && Guide.GetPhase() != MikdashTour::Phase::Finished)
    {
        BeginOrResumeTour();
        return;
    }
    Panel = Panel == EMikdashTourPanel::Hidden ? EMikdashTourPanel::Stop : EMikdashTourPanel::Hidden;
}

void AMikdashTourGuide::ToggleCodexPanel()
{
    if (Panel == EMikdashTourPanel::Codex)
    {
        Panel = PanelBeforeCodex;
        return;
    }
    PanelBeforeCodex = Panel;
    Panel = EMikdashTourPanel::Codex;
    // Open on something relevant: the first entry this stop teaches.
    if (Codex != nullptr)
    {
        const int32 Current = GetCurrentStopIndex();
        if (StopText.IsValidIndex(Current) && StopText[Current].CodexEntries.Num() > 0)
        {
            const int32 Found = Codex->IndexOf(StopText[Current].CodexEntries[0]);
            if (Found != INDEX_NONE) CodexCursor = Found;
        }
    }
}

bool AMikdashTourGuide::IsTourRunning() const { return Guide.IsRunning(); }
bool AMikdashTourGuide::IsTourPaused() const { return Guide.IsPaused(); }
bool AMikdashTourGuide::IsAtStop() const { return Guide.IsAtStop(); }
bool AMikdashTourGuide::IsOffRoute() const { return Guide.IsOffRoute(); }
int32 AMikdashTourGuide::GetCurrentStopIndex() const { return static_cast<int32>(Guide.TargetIndex()); }
int32 AMikdashTourGuide::GetVisitedCount() const { return static_cast<int32>(Guide.VisitedCount()); }

FName AMikdashTourGuide::GetCurrentStopKey() const
{
    const int32 Index = GetCurrentStopIndex();
    return StopText.IsValidIndex(Index) ? StopText[Index].Key : NAME_None;
}

float AMikdashTourGuide::GetProgressFraction() const
{
    return static_cast<float>(Guide.GetProgress().FractionByDistance);
}

FVector AMikdashTourGuide::GetMarkerWorldLocation() const
{
    return FromTourPoint(Guide.MarkerPosition());
}

float AMikdashTourGuide::GetDistanceToStopCm() const
{
    return static_cast<float>(Guide.DistanceToTargetCm());
}

float AMikdashTourGuide::GetBearingToStopDegrees() const
{
    return static_cast<float>(Guide.BearingToTargetDegrees());
}

// ---------------------------------------------------------------------------
// The frame
// ---------------------------------------------------------------------------

FVector AMikdashTourGuide::GetVisitorLocation() const
{
    if (bFlying && FlightCamera != nullptr)
    {
        FVector Where = FlightCamera->GetActorLocation();
        Where.Z -= CameraEyeHeightCm;      // report the floor point, not the eye
        return Where;
    }
    if (const APlayerController* Controller = GetController())
    {
        if (const APawn* Pawn = Controller->GetPawn())
        {
            FVector Where = Pawn->GetActorLocation();
            // Feet, so a stop measured on the floor and a capsule centred 96 cm up agree.
            Where.Z -= Pawn->GetSimpleCollisionHalfHeight();
            return Where;
        }
        FVector Location;
        FRotator Rotation;
        Controller->GetPlayerViewPoint(Location, Rotation);
        return Location;
    }
    return GetActorLocation();
}

void AMikdashTourGuide::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bRouteLoaded) return;

    const int32 Before = GetCurrentStopIndex();
    const bool bArrived = Guide.Observe(ToTourPoint(GetVisitorLocation()), DeltaSeconds);
    if (bArrived) OnArrived(Before);

    if (bFlying)
    {
        UpdateCameraFlight();
        if (!Guide.IsCameraMoving()) StopCameraFlight(true);
    }

    // Has he wandered up to a different stop? Offer it rather than nagging him back.
    WanderOffer = INDEX_NONE;
    if (Guide.IsRunning() && !Guide.IsAtStop())
    {
        const int32 Near = Route.NearestStopWithin(ToTourPoint(GetVisitorLocation()), WanderOfferRadiusCm);
        if (Near != INDEX_NONE && Near != GetCurrentStopIndex()) WanderOffer = Near;
    }

    UpdateMarkers();
}

void AMikdashTourGuide::OnArrived(int32 StopIndex)
{
    if (!StopText.IsValidIndex(StopIndex)) return;
    const FMikdashTourStopText& Stop = StopText[StopIndex];
    Panel = Panel == EMikdashTourPanel::Codex ? Panel : EMikdashTourPanel::Stop;
    if (Codex != nullptr)
    {
        const int32 Opened = Codex->UnlockForStop(Stop.Key);
        if (Opened > 0)
        {
            TransientNote = FString::Printf(TEXT("%d codex %s unlocked."), Opened, Opened == 1 ? TEXT("entry") : TEXT("entries"));
            TransientNoteUntil = FPlatformTime::Seconds() + 6.0;
        }
    }
    OnStopReached.Broadcast(Stop.Key);
}

// ---------------------------------------------------------------------------
// Camera flight
// ---------------------------------------------------------------------------

void AMikdashTourGuide::StartCameraFlight()
{
    APlayerController* Controller = GetController();
    UWorld* World = GetWorld();
    if (Controller == nullptr || World == nullptr) return;

    if (FlightCamera == nullptr)
    {
        FActorSpawnParameters Params;
        Params.ObjectFlags |= RF_Transient;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        FlightCamera = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform::Identity, Params);
        if (FlightCamera == nullptr) return;
    }
    if (!bFlying)
    {
        PreviousViewTarget = Controller->GetViewTarget();
        bFlying = true;
    }
    UpdateCameraFlight();
    Controller->SetViewTargetWithBlend(FlightCamera, CameraBlendSeconds);
}

void AMikdashTourGuide::UpdateCameraFlight()
{
    if (FlightCamera == nullptr) return;
    FVector Where = FromTourPoint(Guide.CameraPosition());
    Where.Z += CameraEyeHeightCm;
    const int32 Index = GetCurrentStopIndex();
    const FVector LookAt = StopText.IsValidIndex(Index) ? StopText[Index].Look : Where + FVector(100, 0, 0);
    FlightCamera->SetActorLocation(Where);
    FlightCamera->SetActorRotation((LookAt - Where).Rotation());
}

void AMikdashTourGuide::StopCameraFlight(bool bSetPawnDown)
{
    if (!bFlying) return;
    bFlying = false;
    APlayerController* Controller = GetController();
    if (Controller != nullptr)
    {
        // Set the body down where the flight ended, so the visitor is standing where he
        // was just shown rather than back where he took off from.
        const int32 Index = GetCurrentStopIndex();
        if (bSetPawnDown && StopText.IsValidIndex(Index))
        {
            if (APawn* Pawn = Controller->GetPawn())
            {
                FVector Target = StopText[Index].Stand;
                Target.Z += Pawn->GetSimpleCollisionHalfHeight();
                Pawn->SetActorLocation(Target, false, nullptr, ETeleportType::TeleportPhysics);
                const FVector LookAt = StopText[Index].Look;
                Controller->SetControlRotation((LookAt - (Target + FVector(0, 0, CameraEyeHeightCm))).Rotation());
            }
        }
        AActor* Back = PreviousViewTarget.IsValid() ? PreviousViewTarget.Get() : Cast<AActor>(Controller->GetPawn());
        if (Back != nullptr) Controller->SetViewTargetWithBlend(Back, CameraBlendSeconds);
    }
    PreviousViewTarget = nullptr;
}

// ---------------------------------------------------------------------------
// Markers
// ---------------------------------------------------------------------------

void AMikdashTourGuide::RefreshMarkerCache()
{
    Markers.Reset();
    UWorld* World = GetWorld();
    if (World == nullptr) return;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!IsValid(Actor) || !Actor->ActorHasTag(MarkerTag)) continue;
        // The second tag is the stop key. A marker with only the group tag is ignored
        // rather than guessed at.
        for (const FName& Tag : Actor->Tags)
        {
            if (Tag == MarkerTag) continue;
            Markers.Add(Tag, Actor);
            break;
        }
    }
    if (Markers.Num() > 0)
    {
        UE_LOG(LogMikdashTour, Log, TEXT("Tour markers found in the level: %d"), Markers.Num());
    }
}

void AMikdashTourGuide::UpdateMarkers()
{
    if (Markers.Num() == 0) return;
    const FName Current = Guide.IsRunning() ? GetCurrentStopKey() : NAME_None;
    for (const TPair<FName, TWeakObjectPtr<AActor>>& Pair : Markers)
    {
        if (AActor* Actor = Pair.Value.Get())
        {
            Actor->SetActorHiddenInGame(Pair.Key != Current);
        }
    }
}

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------

void AMikdashTourGuide::BindKeys(APlayerController* Controller)
{
    if (Controller == nullptr) return;
    ReleaseKeys();
    TourInput = NewObject<UInputComponent>(this, UInputComponent::StaticClass(), TEXT("MikdashTourInput"));
    TourInput->Priority = TourInputPriority;
    // Consumed, so a key the tour owns does not also reach a handler below it. Every key
    // is config precisely so a collision with another system is a settings edit.
    TourInput->BindKey(TogglePanelKey, IE_Pressed, this, &AMikdashTourGuide::HandleTogglePanelKey).bConsumeInput = true;
    TourInput->BindKey(NextStopKey, IE_Pressed, this, &AMikdashTourGuide::HandleNextKey).bConsumeInput = true;
    TourInput->BindKey(PreviousStopKey, IE_Pressed, this, &AMikdashTourGuide::HandlePreviousKey).bConsumeInput = true;
    TourInput->BindKey(ToggleModeKey, IE_Pressed, this, &AMikdashTourGuide::HandleModeKey).bConsumeInput = true;
    TourInput->BindKey(CodexKey, IE_Pressed, this, &AMikdashTourGuide::HandleCodexKey).bConsumeInput = true;
    TourInput->BindKey(RejoinKey, IE_Pressed, this, &AMikdashTourGuide::HandleRejoinKey).bConsumeInput = true;
    Controller->PushInputComponent(TourInput);
    BoundController = Controller;
}

void AMikdashTourGuide::ReleaseKeys()
{
    if (APlayerController* Controller = BoundController.Get())
    {
        if (TourInput != nullptr) Controller->PopInputComponent(TourInput);
    }
    TourInput = nullptr;
    BoundController = nullptr;
}

void AMikdashTourGuide::HandleTogglePanelKey() { TogglePanel(); }

void AMikdashTourGuide::HandleNextKey()
{
    if (Panel == EMikdashTourPanel::Codex)
    {
        if (Codex != nullptr && Codex->Num() > 0) CodexCursor = (CodexCursor + 1) % Codex->Num();
        return;
    }
    NextStop();
}

void AMikdashTourGuide::HandlePreviousKey()
{
    if (Panel == EMikdashTourPanel::Codex)
    {
        if (Codex != nullptr && Codex->Num() > 0) CodexCursor = (CodexCursor + Codex->Num() - 1) % Codex->Num();
        return;
    }
    PreviousStop();
}

void AMikdashTourGuide::HandleModeKey()
{
    if (Panel == EMikdashTourPanel::Codex)
    {
        if (Codex != nullptr && Codex->GetCategories().Num() > 0)
        {
            CodexCategory = (CodexCategory + 1) % Codex->GetCategories().Num();
            const TArray<int32> InCategory = Codex->IndicesInCategory(Codex->GetCategories()[CodexCategory]);
            if (InCategory.Num() > 0) CodexCursor = InCategory[0];
        }
        return;
    }
    ToggleTourMode();
}

void AMikdashTourGuide::HandleCodexKey() { ToggleCodexPanel(); }
void AMikdashTourGuide::HandleRejoinKey() { RejoinRoute(); }

// ---------------------------------------------------------------------------
// What the panel reads
// ---------------------------------------------------------------------------

bool AMikdashTourGuide::IsStopPanelVisible() const
{
    return Panel == EMikdashTourPanel::Stop
        && (Guide.IsRunning() || Guide.GetPhase() == MikdashTour::Phase::Finished || !bRouteLoaded);
}

bool AMikdashTourGuide::IsCodexPanelVisible() const { return Panel == EMikdashTourPanel::Codex; }

bool AMikdashTourGuide::IsPromptVisible() const
{
    return !GetPromptText().IsEmpty();
}

FString AMikdashTourGuide::GetHeading() const
{
    if (!bRouteLoaded) return TEXT("The guided tour is not available");
    if (Guide.GetPhase() == MikdashTour::Phase::Finished) return TEXT("The end of the way");
    const int32 Index = GetCurrentStopIndex();
    if (!StopText.IsValidIndex(Index)) return FString();
    return FString::Printf(TEXT("%d. %s"), Index + 1, *WithHebrew(StopText[Index].Name, StopText[Index].NameHebrew));
}

FString AMikdashTourGuide::GetSubheading() const
{
    if (!bRouteLoaded) return LoadError;
    if (Guide.GetPhase() == MikdashTour::Phase::Finished)
    {
        return FString::Printf(TEXT("%d of %d stops visited."), GetVisitedCount(), StopText.Num());
    }
    const int32 Index = GetCurrentStopIndex();
    if (!StopText.IsValidIndex(Index)) return FString();
    return StopText[Index].Subtitle.ToString();
}

FString AMikdashTourGuide::GetBody() const
{
    if (!bRouteLoaded)
    {
        return TEXT("The tour text could not be read from ") + GetContentPath()
             + TEXT(". Nothing about the building is affected; only this panel is.");
    }
    if (Guide.GetPhase() == MikdashTour::Phase::Finished)
    {
        return TEXT("That is the whole path, from the foot of the Mount to the curtain. "
                    "Everything you were shown is in the codex with its source and an honest label for "
                    "how firm that source is. Walk anywhere you like now.");
    }
    const int32 Index = GetCurrentStopIndex();
    if (!StopText.IsValidIndex(Index)) return FString();
    FString Out = StopText[Index].WhatHappensHere.ToString();
    const FString Explanation = StopText[Index].Explanation.ToString();
    if (!Explanation.IsEmpty())
    {
        if (!Out.IsEmpty()) Out += TEXT("\n\n");
        Out += Explanation;
    }
    return Out;
}

FString AMikdashTourGuide::GetMeasurementsBlock() const
{
    const int32 Index = GetCurrentStopIndex();
    if (!StopText.IsValidIndex(Index) || StopText[Index].Measurements.Num() == 0) return FString();
    return Join(StopText[Index].Measurements, TEXT("  "));
}

FString AMikdashTourGuide::GetSourcesBlock() const
{
    const int32 Index = GetCurrentStopIndex();
    if (!StopText.IsValidIndex(Index) || StopText[Index].Sources.Num() == 0) return FString();
    FString Out = TEXT("Sources: ");
    for (int32 I = 0; I < StopText[Index].Sources.Num(); ++I)
    {
        if (I > 0) Out += TEXT("; ");
        Out += StopText[Index].Sources[I].ToString();
    }
    return Out;
}

FString AMikdashTourGuide::GetFooter() const
{
    if (!bRouteLoaded) return FString();
    const int32 Index = GetCurrentStopIndex();
    FString Label = TEXT("certain");
    if (StopText.IsValidIndex(Index))
    {
        Label = StopText[Index].Confidence == EMikdashConfidenceLabel::Certain ? TEXT("certain")
              : StopText[Index].Confidence == EMikdashConfidenceLabel::Disputed ? TEXT("disputed - the text names who holds what")
              : TEXT("authored - nobody said this; the project chose it");
    }
    return FString::Printf(TEXT("[%s]    %s next stop   %s back   %s %s   %s codex   %s hide"),
                           *Label,
                           *NextStopKey.GetDisplayName().ToString(),
                           *PreviousStopKey.GetDisplayName().ToString(),
                           *ToggleModeKey.GetDisplayName().ToString(),
                           GetTourMode() == EMikdashTourMode::WalkMeThere ? TEXT("(walking you there)") : TEXT("(follow the marker)"),
                           *CodexKey.GetDisplayName().ToString(),
                           *TogglePanelKey.GetDisplayName().ToString());
}

FString AMikdashTourGuide::GetStatusLine() const
{
    if (!Guide.IsRunning()) return FString();
    const MikdashTour::Progress Now = Guide.GetProgress();
    const int32 Index = GetCurrentStopIndex();
    const FString Name = StopText.IsValidIndex(Index) ? StopText[Index].Name.ToString() : FString();
    if (Guide.IsPaused())
    {
        return FString::Printf(TEXT("Tour paused at %s   %d/%d"), *Name, static_cast<int32>(Now.Visited), static_cast<int32>(Now.Total));
    }
    if (Guide.IsAtStop())
    {
        return FString::Printf(TEXT("%s   %d/%d   %.0f%%"), *Name, static_cast<int32>(Now.Visited),
                               static_cast<int32>(Now.Total), Now.FractionByDistance * 100.0);
    }
    return FString::Printf(TEXT("To %s: %.0f m   %d/%d   %.0f%%"), *Name, Guide.DistanceToTargetCm() / 100.0,
                           static_cast<int32>(Now.Visited), static_cast<int32>(Now.Total), Now.FractionByDistance * 100.0);
}

FString AMikdashTourGuide::GetPromptText() const
{
    if (FPlatformTime::Seconds() < TransientNoteUntil && !TransientNote.IsEmpty()) return TransientNote;
    if (!Guide.IsRunning() || Guide.IsPaused()) return FString();
    if (Panel == EMikdashTourPanel::Codex) return FString();

    if (WanderOffer != INDEX_NONE && StopText.IsValidIndex(WanderOffer))
    {
        return FString::Printf(TEXT("You are at %s. %s to make it the next stop."),
                               *StopText[WanderOffer].Name.ToString(), *RejoinKey.GetDisplayName().ToString());
    }
    if (Guide.IsOffRoute())
    {
        return FString::Printf(TEXT("Off the route by %.0f m. %s to head back, or keep exploring."),
                               Guide.CorridorDistanceCm() / 100.0, *RejoinKey.GetDisplayName().ToString());
    }
    if (Guide.IsAtStop() && Panel == EMikdashTourPanel::Hidden)
    {
        return FString::Printf(TEXT("%s to read about this place."), *TogglePanelKey.GetDisplayName().ToString());
    }
    if (!Guide.IsAtStop() && Panel != EMikdashTourPanel::Stop && Markers.Num() == 0)
    {
        // No marker meshes in the level, so give him the direction in words.
        const double Bearing = Guide.BearingToTargetDegrees();
        static const TCHAR* Compass[8] = { TEXT("north"), TEXT("north-east"), TEXT("east"), TEXT("south-east"),
                                           TEXT("south"), TEXT("south-west"), TEXT("west"), TEXT("north-west") };
        const int32 Sector = static_cast<int32>((Bearing + 22.5) / 45.0) % 8;
        return FString::Printf(TEXT("%.0f m %s"), Guide.DistanceToTargetCm() / 100.0, Compass[Sector]);
    }
    return FString();
}

FString AMikdashTourGuide::GetCodexHeading() const
{
    if (Codex == nullptr) return TEXT("Codex");
    if (!Codex->IsLoaded()) return TEXT("Codex - not loaded");
    FMikdashCodexEntry Entry;
    if (!Codex->GetEntryAt(CodexCursor, Entry)) return TEXT("Codex");
    return WithHebrew(Entry.Name, Entry.NameHebrew);
}

FString AMikdashTourGuide::GetCodexBody() const
{
    if (Codex == nullptr) return TEXT("No codex actor is present in this level.");
    if (!Codex->IsLoaded()) return Codex->GetLoadError();
    FMikdashCodexEntry Entry;
    if (!Codex->GetEntryAt(CodexCursor, Entry)) return FString();

    // Locked entries show their title and their label but not their body. The label is
    // never hidden: an entry that says the model invented something has to be visible
    // even before the visitor has walked to it.
    if (!Codex->IsUnlocked(Entry.Id))
    {
        return FString::Printf(TEXT("[%s]  Not yet visited. Reach the place this describes and it opens.\n\n%s"),
                               *AMikdashCodex::ConfidenceDisplayName(Entry.Confidence).ToString(),
                               *Codex->ConfidenceDefinition(Entry.Confidence).ToString());
    }

    FString Out = FString::Printf(TEXT("[%s]  %s\n\n%s"),
                                  *AMikdashCodex::ConfidenceDisplayName(Entry.Confidence).ToString(),
                                  *Codex->ConfidenceDefinition(Entry.Confidence).ToString(),
                                  *Entry.Summary.ToString());
    if (Entry.Measurements.Num() > 0)
    {
        Out += TEXT("\n");
        for (const FMikdashCodexMeasurement& Row : Entry.Measurements)
        {
            Out += FString::Printf(TEXT("\n  %s: %s"), *Row.Label.ToString(), *Row.Value.ToString());
            if (!Row.Source.IsEmpty()) Out += FString::Printf(TEXT("   [%s]"), *Row.Source.ToString());
        }
    }
    if (Entry.Positions.Num() > 0)
    {
        Out += TEXT("\n");
        for (const FMikdashCodexPosition& Row : Entry.Positions)
        {
            Out += FString::Printf(TEXT("\n  %s: %s"), *Row.Who.ToString(), *Row.Holds.ToString());
        }
    }
    if (Entry.Sources.Num() > 0)
    {
        Out += TEXT("\n\nSources: ");
        for (int32 I = 0; I < Entry.Sources.Num(); ++I)
        {
            if (I > 0) Out += TEXT("; ");
            Out += Entry.Sources[I].ToString();
        }
    }
    return Out;
}

FString AMikdashTourGuide::GetCodexFooter() const
{
    if (Codex == nullptr) return FString();
    const FName Category = Codex->GetCategories().IsValidIndex(CodexCategory)
        ? Codex->GetCategories()[CodexCategory] : FName(TEXT("all"));
    return FString::Printf(TEXT("%d of %d entries   %d unlocked   %d certain / %d disputed / %d authored   %s / %s browse   %s category (%s)   %s close"),
                           CodexCursor + 1, Codex->Num(), Codex->UnlockedCount(),
                           Codex->CountByConfidence(EMikdashConfidence::Certain),
                           Codex->CountByConfidence(EMikdashConfidence::Disputed),
                           Codex->CountByConfidence(EMikdashConfidence::Authored),
                           *NextStopKey.GetDisplayName().ToString(),
                           *PreviousStopKey.GetDisplayName().ToString(),
                           *ToggleModeKey.GetDisplayName().ToString(),
                           *Codex->GetCategoryName(Category).ToString(),
                           *CodexKey.GetDisplayName().ToString());
}

// ---------------------------------------------------------------------------
// Bookmark
// ---------------------------------------------------------------------------

FString AMikdashTourGuide::SaveBookmark() const
{
    const MikdashTour::Bookmark Mark = Guide.Save();
    return FString::Printf(TEXT("v1|%llu|%d|%d|%d"),
                           static_cast<unsigned long long>(Mark.VisitedMask),
                           static_cast<int32>(Mark.TargetIndex),
                           static_cast<int32>(Mark.TourMode),
                           static_cast<int32>(Mark.CurrentPhase));
}

bool AMikdashTourGuide::RestoreBookmark(const FString& Bookmark)
{
    TArray<FString> Parts;
    Bookmark.ParseIntoArray(Parts, TEXT("|"), false);
    if (Parts.Num() != 5 || Parts[0] != TEXT("v1")) return false;

    MikdashTour::Bookmark Mark;
    Mark.VisitedMask = static_cast<uint64>(FCString::Strtoui64(*Parts[1], nullptr, 10));
    const int32 Target = FCString::Atoi(*Parts[2]);
    const int32 Mode = FCString::Atoi(*Parts[3]);
    const int32 Phase = FCString::Atoi(*Parts[4]);
    if (Target < 0 || Target >= StopText.Num()) return false;
    if (Mode < 0 || Mode > 1) return false;
    if (Phase < 0 || Phase > static_cast<int32>(MikdashTour::Phase::Finished)) return false;
    Mark.TargetIndex = static_cast<std::size_t>(Target);
    Mark.TourMode = static_cast<MikdashTour::Mode>(Mode);
    Mark.CurrentPhase = static_cast<MikdashTour::Phase>(Phase);
    // A camera move is never restored mid-flight from a string: the flight is a moment,
    // not a place, and resuming into one would drop the visitor inside a wall.
    Mark.CameraMoving = false;
    if (!Guide.Restore(Mark)) return false;
    bEverStarted = true;
    UpdateMarkers();
    return true;
}

#undef LOCTEXT_NAMESPACE
