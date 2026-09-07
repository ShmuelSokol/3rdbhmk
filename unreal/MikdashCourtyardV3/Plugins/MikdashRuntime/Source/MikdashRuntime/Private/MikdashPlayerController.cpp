#include "MikdashPlayerController.h"
#include "MikdashDovePawn.h"
#include "SMikdashPreparation.h"
#include "AudioDevice.h"
#include "AudioDeviceHandle.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerInput.h"
#include "InputCoreTypes.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "MikdashWalkthrough"

namespace
{
class SMikdashMenu : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SMikdashMenu) {}
        SLATE_ARGUMENT(TWeakObjectPtr<AMikdashPlayerController>, Controller)
        SLATE_ARGUMENT(bool, HasStarted)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args)
    {
        Controller = Args._Controller;
        ButtonText = FCoreStyle::Get().GetWidgetStyle<FTextBlockStyle>("NormalText");
        ButtonText.SetFont(FCoreStyle::GetDefaultFontStyle("Regular", 18));
        ChildSlot
        [
            SNew(SBorder)
            .BorderBackgroundColor(FLinearColor(0.025f, 0.035f, 0.05f, 0.97f))
            .HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(28)
            [
                SNew(SBox).WidthOverride(760).MaxDesiredHeight(640)
                [
                    SNew(SScrollBox)
                    + SScrollBox::Slot()
                [
                    SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 18)
                    [SNew(STextBlock).Text(LOCTEXT("Title", "Third Beis HaMikdash"))
                        .Font(FCoreStyle::GetDefaultFontStyle("Bold", 28))]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 20)
                    [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true).Text(LOCTEXT("Source",
                        "A measured reconstruction based on Yechezkel.\nSurrounding Jerusalem and vegetation are illustrative.\nDevelopment preview: visuals and runtime are under review."))]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 20)
                    [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 18)).AutoWrapText(true).Text(LOCTEXT("Controls",
                        "W A S D or arrow keys: walk\nMouse: look around\nF: white dove / return to walking\nDove: Space up, Ctrl down, Shift fast\nAerial exploration is an architectural review mode.\nP or Escape: pause and release the mouse\nM: mute or restore sound\nAlt+F4: close the walkthrough"))]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 5)
                    [SNew(SButton).TextStyle(&ButtonText).HAlign(HAlign_Center).ContentPadding(FMargin(18, 12))
                        .Text(Args._HasStarted ? LOCTEXT("Resume", "Resume walkthrough") : LOCTEXT("Start", "Start walkthrough"))
                        .OnClicked_Lambda([this]() { if (Controller.IsValid()) Controller->ResumeWalkthrough(); return FReply::Handled(); })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 5)
                    [SNew(SButton).TextStyle(&ButtonText).HAlign(HAlign_Center).ContentPadding(FMargin(18, 12))
                        .Text_Lambda([this]() { return Controller.IsValid() && Controller->IsDoveFlightActive()
                            ? LOCTEXT("DoveReturn", "Return to walking") : LOCTEXT("DoveStart", "Explore as a white dove"); })
                        .OnClicked_Lambda([this]() { if (Controller.IsValid()) { Controller->RequestDoveFlightFromMenu(); } return FReply::Handled(); })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 5)
                    [SNew(STextBlock).AutoWrapText(true)
                        .Text_Lambda([this]() { return Controller.IsValid()
                            ? FText::FromString(Controller->GetDoveFlightStatus()) : FText::GetEmpty(); })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 5)
                    [SNew(SButton).TextStyle(&ButtonText).HAlign(HAlign_Center).ContentPadding(FMargin(18, 12))
                        .Text(LOCTEXT("Prepare", "Preparation: learn before arriving"))
                        .OnClicked_Lambda([this]() { if (Controller.IsValid()) Controller->ShowPreparationLesson(); return FReply::Handled(); })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 5)
                    [SNew(SButton).TextStyle(&ButtonText).HAlign(HAlign_Center).ContentPadding(FMargin(18, 12))
                        .Text_Lambda([this]() { return Controller.IsValid() && Controller->IsSoundMuted()
                            ? LOCTEXT("SoundOff", "Sound: off — turn on") : LOCTEXT("SoundOn", "Sound: on — mute"); })
                        .OnClicked_Lambda([this]() { if (Controller.IsValid()) Controller->ToggleSound(); return FReply::Handled(); })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 5)
                    [SNew(SButton).TextStyle(&ButtonText).HAlign(HAlign_Center).ContentPadding(FMargin(18, 12)).Text(LOCTEXT("Quit", "Quit"))
                        .OnClicked_Lambda([this]() { if (Controller.IsValid()) Controller->QuitWalkthrough(); return FReply::Handled(); })]
                ]
                ]
            ]
        ];
    }
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override
    {
        if (Controller.IsValid() && (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::P))
        {
            if (!Event.IsRepeat()) Controller->ToggleWalkthroughMenu();
            return FReply::Handled();
        }
        if (Controller.IsValid() && Event.GetKey() == EKeys::M)
        {
            if (!Event.IsRepeat()) Controller->ToggleSound();
            return FReply::Handled();
        }
        return SCompoundWidget::OnKeyDown(Geometry, Event);
    }
private:
    FTextBlockStyle ButtonText;
    TWeakObjectPtr<AMikdashPlayerController> Controller;
};
}

AMikdashPlayerController::AMikdashPlayerController()
{
    PrimaryActorTick.bTickEvenWhenPaused = true;
    bShowMouseCursor = true;
    for (const TCHAR* Name : {TEXT("StoneL1"), TEXT("StoneL2"), TEXT("StoneL3"), TEXT("StoneR1"), TEXT("StoneR2"), TEXT("StoneR3")})
    {
        const FString Path = FString::Printf(TEXT("/Game/MikdashV3/Runtime/Audio/StoneFootstepsV1/SW_Fantozzi_%s.SW_Fantozzi_%s"), Name, Name);
        ConstructorHelpers::FObjectFinder<USoundBase> Sample(*Path);
        StoneSteps.Add(Sample.Object);
    }
    for (const TCHAR* Name : {TEXT("SandL1"), TEXT("SandL2"), TEXT("SandL3"), TEXT("SandR1"), TEXT("SandR2"), TEXT("SandR3")})
    {
        const FString Path = FString::Printf(TEXT("/Game/MikdashV3/Runtime/Audio/SoftFootstepsV1/SW_Fantozzi_%s.SW_Fantozzi_%s"), Name, Name);
        ConstructorHelpers::FObjectFinder<USoundBase> Sample(*Path);
        SoftSteps.Add(Sample.Object);
    }
}

void AMikdashPlayerController::BeginPlay()
{
    Super::BeginPlay();
    if (!IsLocalController()) return;
    ApplySoundVolume();
    if (FSlateApplication::IsInitialized())
        ActivationHandle = FSlateApplication::Get().OnApplicationActivationStateChanged()
            .AddUObject(this, &AMikdashPlayerController::ApplicationActivationChanged);
    OpenMenu();
}

void AMikdashPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    // Controller is above the pawn in BuildInputStack: keep template action
    // bindings from adding movement/look a second time or enabling jumping.
    InputComponent->bBlockInput = true;
    InputComponent->BindKey(EKeys::F, IE_Pressed, this, &AMikdashPlayerController::ToggleDoveFlight);
    InputComponent->BindKey(EKeys::Escape, IE_Pressed, this, &AMikdashPlayerController::ToggleWalkthroughMenu).bExecuteWhenPaused = true;
    InputComponent->BindKey(EKeys::P, IE_Pressed, this, &AMikdashPlayerController::ToggleWalkthroughMenu).bExecuteWhenPaused = true;
    InputComponent->BindKey(EKeys::M, IE_Pressed, this, &AMikdashPlayerController::ToggleSound).bExecuteWhenPaused = true;
    InputComponent->BindAxisKey(EKeys::MouseX, this, &AMikdashPlayerController::Turn);
    InputComponent->BindAxisKey(EKeys::MouseY, this, &AMikdashPlayerController::LookUp);
}

void AMikdashPlayerController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
    if (bDoveFlight && !IsValid(DovePawn)) ToggleDoveFlight();
    if (bPendingMenuDove)
    {
        if (bMenuOpen || IsPaused()) bPendingMenuDove=false;
        else if (GetWorld() && GetWorld()->GetRealTimeSeconds() >= MenuDoveDeadline)
        {
            bPendingMenuDove=false;
            DoveFlightStatus=TEXT("Dove flight could not start: stand on clear ground and try again");
            OpenMenu();
        }
        else if (ACharacter* Walker=Cast<ACharacter>(GetPawn()))
        {
            if (Walker->GetCharacterMovement()->IsMovingOnGround())
            {
                bPendingMenuDove=false;
                ToggleDoveFlight();
                if (!bDoveFlight) OpenMenu();
            }
        }
    }
    UpdateFootsteps(DeltaTime);
    if (bMenuOpen || !IsLocalController() || !GetPawn() || IsPaused()) return;
    ResidentClockSeconds += FMath::Max(0.0, static_cast<double>(DeltaTime));
    ResidentSimulation.AdvanceTo(static_cast<std::uint64_t>(ResidentClockSeconds));
    const float Forward = (IsInputKeyDown(EKeys::W) || IsInputKeyDown(EKeys::Up) ? 1.f : 0.f)
        - (IsInputKeyDown(EKeys::S) || IsInputKeyDown(EKeys::Down) ? 1.f : 0.f);
    const float Right = (IsInputKeyDown(EKeys::D) || IsInputKeyDown(EKeys::Right) ? 1.f : 0.f)
        - (IsInputKeyDown(EKeys::A) || IsInputKeyDown(EKeys::Left) ? 1.f : 0.f);
    const FRotator Heading(0.f, GetControlRotation().Yaw, 0.f);
    const FVector Direction = Heading.Vector() * Forward + FRotationMatrix(Heading).GetUnitAxis(EAxis::Y) * Right;
    if (bDoveFlight && IsValid(DovePawn))
    {
        const float Up=(IsInputKeyDown(EKeys::SpaceBar) ? 1.f : 0.f)
            -(IsInputKeyDown(EKeys::LeftControl) || IsInputKeyDown(EKeys::RightControl) ? 1.f : 0.f);
        DovePawn->SetFlightBoost(IsInputKeyDown(EKeys::LeftShift) || IsInputKeyDown(EKeys::RightShift));
        DovePawn->AddMovementInput((Direction+FVector(0,0,Up)).GetClampedToMaxSize(1.f));
    }
    else GetPawn()->AddMovementInput(Direction.GetClampedToMaxSize(1.f));
}

void AMikdashPlayerController::RequestDoveFlightFromMenu()
{
    if (!IsLocalController() || !GetWorld()) return;
    ResumeWalkthrough();
    if (bDoveFlight)
    {
        ToggleDoveFlight();
        if (bDoveFlight) OpenMenu();
        return;
    }
    DoveFlightStatus=TEXT("Preparing dove flight; waiting for grounded footing");
    bPendingMenuDove=true;
    MenuDoveDeadline=GetWorld()->GetRealTimeSeconds()+3.0;
}

void AMikdashPlayerController::ToggleDoveFlight()
{
    if (!IsLocalController() || !GetWorld() || bMenuOpen || IsPaused()) return;
    bPendingMenuDove=false;
    if (bDoveFlight)
    {
        if (!IsValid(ParkedWalker) || FVector::Dist(ParkedWalker->GetActorLocation(),ParkedWalkLocation)>5.f)
        { DoveFlightStatus=TEXT("Return unavailable: walking character changed; restart walkthrough safely"); return; }
        AMikdashDovePawn* PreviousDove=DovePawn;
        Possess(ParkedWalker);
        if (GetPawn()!=ParkedWalker) { DoveFlightStatus=TEXT("Return possession failed"); return; }
        ParkedWalker->GetCharacterMovement()->SetMovementMode(static_cast<EMovementMode>(ParkedMovementMode),ParkedCustomMovementMode);
        SetControlRotation(ParkedControlRotation);
        bDoveFlight=false;DovePawn=nullptr;ParkedWalker=nullptr;
        if (IsValid(PreviousDove)) PreviousDove->Destroy();
        if (PlayerInput) PlayerInput->FlushPressedKeys();
        DoveFlightStatus=TEXT("Ground walking restored at departure point");
        return;
    }
    ACharacter* Walker=Cast<ACharacter>(GetPawn());
    if (!Walker || !Walker->GetCharacterMovement()->IsMovingOnGround())
    { DoveFlightStatus=TEXT("Stand on the ground before beginning dove flight"); return; }
    FActorSpawnParameters Params;Params.Owner=this;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
    AMikdashDovePawn* Bird=GetWorld()->SpawnActor<AMikdashDovePawn>(AMikdashDovePawn::StaticClass(),
        Walker->GetActorLocation()+FVector(0,0,150),FRotator(0,GetControlRotation().Yaw,0),Params);
    if (!Bird) { DoveFlightStatus=TEXT("No clear space above: step into an open area"); return; }
    ParkedWalker=Walker;ParkedWalkLocation=Walker->GetActorLocation();ParkedControlRotation=GetControlRotation();
    ParkedMovementMode=static_cast<uint8>(Walker->GetCharacterMovement()->MovementMode.GetValue());
    ParkedCustomMovementMode=Walker->GetCharacterMovement()->CustomMovementMode;
    Walker->GetCharacterMovement()->StopMovementImmediately();
    Walker->ConsumeMovementInputVector();Walker->GetCharacterMovement()->DisableMovement();
    Possess(Bird);
    if (GetPawn()!=Bird)
    {
        Walker->GetCharacterMovement()->SetMovementMode(static_cast<EMovementMode>(ParkedMovementMode),ParkedCustomMovementMode);Possess(Walker);
        Bird->Destroy();ParkedWalker=nullptr;DoveFlightStatus=TEXT("Flight possession failed; walking retained");return;
    }
    DovePawn=Bird;bDoveFlight=true;
    if (PlayerInput) PlayerInput->FlushPressedKeys();
    DoveFlightStatus=TEXT("White dove: aerial architectural exploration; F returns to departure point");
}

void AMikdashPlayerController::Turn(float Value) { if (!bMenuOpen) AddYawInput(Value); }
void AMikdashPlayerController::LookUp(float Value) { if (!bMenuOpen) AddPitchInput(-Value); }

void AMikdashPlayerController::UpdateFootsteps(float DeltaTime)
{
    ACharacter* WalkingCharacter = Cast<ACharacter>(GetPawn());
    if (!IsLocalController() || !WalkingCharacter) { FootstepPawn.Reset(); FootstepCadence.Reset(); return; }
    const FVector Position = WalkingCharacter->GetActorLocation();
    if (FootstepPawn.Get() != WalkingCharacter)
    {
        FootstepPawn = WalkingCharacter;
        LastFootstepPosition = Position;
        FootstepCadence.Reset();
        return;
    }
    const float Distance = FVector::Dist2D(Position, LastFootstepPosition);
    LastFootstepPosition = Position;
    const float Speed = WalkingCharacter->GetVelocity().Size2D();
    // Shared tested cadence uses actual displacement, never just held input.
    if (!FootstepCadence.Advance(Distance, Speed, DeltaTime,
        WalkingCharacter->GetCharacterMovement()->IsMovingOnGround(), bMenuOpen || IsPaused())) return;
    const UStaticMeshComponent* Floor = Cast<UStaticMeshComponent>(WalkingCharacter->GetCharacterMovement()->CurrentFloor.HitResult.GetComponent());
    if (!Floor || !Floor->GetStaticMesh()) return;
    const FString FloorAsset = Floor->GetStaticMesh()->GetPathName();
    const bool SoftGround = FloorAsset.StartsWith(TEXT("/Game/MikdashV3/JerusalemContext/Terrain/"))
        || FloorAsset.StartsWith(TEXT("/Game/MikdashV3/FutureMountV1/Terrain/"));
    const bool HardGround = FloorAsset.StartsWith(TEXT("/Game/MikdashV3/Architecture/"))
        || FloorAsset.StartsWith(TEXT("/Game/MikdashV3/JerusalemContext/Streets/"))
        || FloorAsset.StartsWith(TEXT("/Game/MikdashV3/JerusalemContext/Buildings/"))
        || FloorAsset == TEXT("/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface.SM_MountPlatform_Surface");
    // Unknown/new floor families require an explicit sound assignment.
    if (!SoftGround && !HardGround) return;
    const TArray<TObjectPtr<USoundBase>>& Samples = SoftGround ? SoftSteps : StoneSteps;
    int32 Variation = FMath::RandRange(0, 2);
    if (Variation == LastStepVariation[FootstepSide]) Variation = (Variation + FMath::RandRange(1, 2)) % 3;
    const int32 Index = FootstepSide * 3 + Variation;
    LastStepVariation[FootstepSide] = Variation;
    FootstepSide = 1 - FootstepSide;
    if (!bSoundMuted && Samples.IsValidIndex(Index) && Samples[Index])
    {
        UGameplayStatics::PlaySound2D(this, Samples[Index]);
        UE_LOG(LogTemp, Verbose, TEXT("MIKDASH_FOOTSTEP sample=%d soft=%d floor=%s distance=%f"), Index, SoftGround, *FloorAsset, Distance);
    }
}

void AMikdashPlayerController::OpenMenu()
{
    if (bMenuOpen || !IsLocalController() || !GetWorld() || !GetWorld()->GetGameViewport()) return;
    bMenuOpen = true;
    SetPause(true);
    if (PlayerInput) PlayerInput->FlushPressedKeys();
    if (ACharacter* WalkingCharacter = Cast<ACharacter>(GetPawn())) WalkingCharacter->GetCharacterMovement()->StopMovementImmediately();
    bShowMouseCursor = true;
    MenuWidget = SNew(SMikdashMenu).Controller(this).HasStarted(bHasStarted);
    GetWorld()->GetGameViewport()->AddViewportWidgetContent(MenuWidget.ToSharedRef(), 100);
    FInputModeGameAndUI Mode;
    Mode.SetWidgetToFocus(MenuWidget).SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock).SetHideCursorDuringCapture(false);
    SetInputMode(Mode);
    UE_LOG(LogTemp, Display, TEXT("MIKDASH_MENU_OPEN cursor=visible pause=%d"), IsPaused());
}

void AMikdashPlayerController::ShowPreparationLesson()
{
    if (!bMenuOpen || !GetWorld() || !GetWorld()->GetGameViewport()) return;
    if (MenuWidget.IsValid()) GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(MenuWidget.ToSharedRef());
    MenuWidget = SNew(SMikdashPreparation).Journey(&PreparationJourney)
        .OnBack(FSimpleDelegate::CreateUObject(this, &AMikdashPlayerController::BackToWalkthroughMenu));
    GetWorld()->GetGameViewport()->AddViewportWidgetContent(MenuWidget.ToSharedRef(), 100);
    FInputModeGameAndUI Mode;
    Mode.SetWidgetToFocus(MenuWidget).SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock).SetHideCursorDuringCapture(false);
    SetInputMode(Mode);
    UE_LOG(LogTemp, Display, TEXT("MIKDASH_PREPARATION_OPEN"));
}

void AMikdashPlayerController::BackToWalkthroughMenu()
{
    if (GetWorld() && GetWorld()->GetGameViewport() && MenuWidget.IsValid())
        GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(MenuWidget.ToSharedRef());
    MenuWidget.Reset();
    bMenuOpen = false;
    OpenMenu();
}

void AMikdashPlayerController::ResumeWalkthrough()
{
    if (!bMenuOpen) return;
    if (GetWorld() && GetWorld()->GetGameViewport() && MenuWidget.IsValid())
        GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(MenuWidget.ToSharedRef());
    MenuWidget.Reset();
    bMenuOpen = false;
    bHasStarted = true;
    if (PlayerInput) PlayerInput->FlushPressedKeys();
    SetPause(false);
    bShowMouseCursor = false;
    FInputModeGameOnly Mode;
    Mode.SetConsumeCaptureMouseDown(true);
    SetInputMode(Mode);
    UE_LOG(LogTemp, Display, TEXT("MIKDASH_MENU_RESUME cursor=hidden pause=%d"), IsPaused());
}

void AMikdashPlayerController::ToggleWalkthroughMenu()
{
    if (bMenuOpen)
    {
        // Escape releases/resumes an existing walk, but never starts one.
        // Only the explicit Start button may capture the pointer initially.
        if (bHasStarted) ResumeWalkthrough();
    }
    else OpenMenu();
}
void AMikdashPlayerController::ApplicationActivationChanged(bool bActive) { if (!bActive) OpenMenu(); }

void AMikdashPlayerController::ApplySoundVolume()
{
    if (GetWorld())
        if (FAudioDeviceHandle Device = GetWorld()->GetAudioDevice()) Device->SetTransientPrimaryVolume(bSoundMuted ? 0.f : 1.f);
}
void AMikdashPlayerController::ToggleSound()
{
    bSoundMuted = !bSoundMuted;
    ApplySoundVolume();
    SaveConfig();
    UE_LOG(LogTemp, Display, TEXT("MIKDASH_SOUND muted=%d"), bSoundMuted);
}
void AMikdashPlayerController::QuitWalkthrough()
{
    UKismetSystemLibrary::QuitGame(this, this, EQuitPreference::Quit, false);
}

void AMikdashPlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
    if (IsValid(ParkedWalker)) ParkedWalker->GetCharacterMovement()->SetMovementMode(static_cast<EMovementMode>(ParkedMovementMode),ParkedCustomMovementMode);
    if (IsValid(DovePawn)) DovePawn->Destroy();
    DovePawn=nullptr;ParkedWalker=nullptr;bDoveFlight=false;
    if (FSlateApplication::IsInitialized())
        FSlateApplication::Get().OnApplicationActivationStateChanged().Remove(ActivationHandle);
    if (GetWorld() && GetWorld()->GetGameViewport() && MenuWidget.IsValid())
        GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(MenuWidget.ToSharedRef());
    MenuWidget.Reset();
    Super::EndPlay(Reason);
}

#undef LOCTEXT_NAMESPACE
