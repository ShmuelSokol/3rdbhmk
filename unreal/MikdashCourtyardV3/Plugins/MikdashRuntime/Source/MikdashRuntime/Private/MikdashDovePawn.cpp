#include "MikdashDovePawn.h"
#include "MikdashDoveAppearance.h"
#include "Camera/CameraComponent.h"
#include "CollisionQueryParams.h"
#include "Components/SceneComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/HitResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
MikdashDove::Vec3 ToVec(const FVector& V) { return {V.X, V.Y, V.Z}; }
FVector ToFVector(const MikdashDove::Vec3& V) { return FVector(V.X, V.Y, V.Z); }
constexpr float CruiseSpeed = 1800.f, BoostSpeed = 6000.f;
}

// ---------------------------------------------------------------- movement

UMikdashDoveMovement::UMikdashDoveMovement()
{
    MaxSpeed = CruiseSpeed;
    Acceleration = 4500.f;
    Deceleration = 6500.f;
    TurningBoost = 5.f;
}

void UMikdashDoveMovement::ApplyControlInputToVelocity(float DeltaTime)
{
    ObstacleSpeedScale = 1.f; bSliding = false;
    if (UpdatedComponent && GetWorld() && PawnOwner)
    {
        const FVector Input = GetPendingInputVector();
        // Probe along the requested direction, or along the current velocity while coasting.
        FVector Probe = Input;
        if (Probe.IsNearlyZero(1e-3) && Velocity.SizeSquared() > FMath::Square(50.f)) Probe = Velocity;
        if (!Probe.IsNearlyZero(1e-3) && !Probe.ContainsNaN())
        {
            const FVector Start = UpdatedComponent->GetComponentLocation();
            const FVector End = Start + Probe.GetSafeNormal() * MikdashDove::ObstacleSweepLengthCm;
            FCollisionQueryParams Params(SCENE_QUERY_STAT(MikdashDoveSteer), false, PawnOwner);
            FHitResult Hit;
            if (GetWorld()->SweepSingleByChannel(Hit, Start, End, FQuat::Identity, ECC_Pawn,
                FCollisionShape::MakeSphere(static_cast<float>(MikdashDove::ObstacleSweepRadiusCm)), Params) && Hit.bBlockingHit)
            {
                const double Distance = Hit.bStartPenetrating ? 0.0 : static_cast<double>(Hit.Distance);
                const MikdashDove::SteerResult Steer = MikdashDove::SteerAroundObstacle(ToVec(Input), true, ToVec(Hit.ImpactNormal), Distance);
                ObstacleSpeedScale = static_cast<float>(Steer.SpeedScale);
                bSliding = Steer.bSliding;
                if (bSliding)
                {
                    // Replace the pending input with the slid direction; the base class consumes it.
                    ConsumeInputVector();
                    AddInputVector(ToFVector(Steer.Direction), true);
                }
            }
        }
    }
    Super::ApplyControlInputToVelocity(DeltaTime);
}

void UMikdashDoveMovement::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (!UpdatedComponent || !GetWorld() || !PawnOwner || ShouldSkipUpdate(DeltaTime)) return;
    const FVector Location = UpdatedComponent->GetComponentLocation();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(MikdashDoveClearance), false, PawnOwner);
    MikdashDove::ClearanceInput Clearance;
    FHitResult Floor, Ceiling;
    if (GetWorld()->LineTraceSingleByChannel(Floor, Location,
        Location - FVector(0, 0, MikdashDove::MinFloorClearanceCm + 200.0), ECC_Pawn, Params) && Floor.bBlockingHit)
    { Clearance.bFloorHit = true; Clearance.FloorDistanceCm = Floor.Distance; }
    if (GetWorld()->LineTraceSingleByChannel(Ceiling, Location,
        Location + FVector(0, 0, MikdashDove::MinCeilingClearanceCm + 100.0), ECC_Pawn, Params) && Ceiling.bBlockingHit)
    { Clearance.bCeilingHit = true; Clearance.CeilingDistanceCm = Ceiling.Distance; }
    LastFloorDistance = Clearance.bFloorHit ? static_cast<float>(Clearance.FloorDistanceCm) : -1.f;
    const double Correction = MikdashDove::AltitudeCorrection(Clearance);
    if (FMath::Abs(Correction) < 0.01) return;
    FHitResult MoveHit;
    SafeMoveUpdatedComponent(FVector(0, 0, Correction), UpdatedComponent->GetComponentQuat(), true, MoveHit);
    Velocity.Z = static_cast<float>(MikdashDove::ClampVerticalVelocity(Velocity.Z, Correction));
    UpdateComponentVelocity();
}

// ---------------------------------------------------------------- pawn

AMikdashDovePawn::AMikdashDovePawn()
{
    PrimaryActorTick.bCanEverTick = true;
    AutoPossessAI = EAutoPossessAI::Disabled;
    FlightCollision = CreateDefaultSubobject<USphereComponent>(TEXT("FlightCollision"));
    FlightCollision->InitSphereRadius(24.f);
    FlightCollision->SetCollisionProfileName(TEXT("Pawn"));
    FlightCollision->SetCanEverAffectNavigation(false);
    SetRootComponent(FlightCollision);
    FlightMovement = CreateDefaultSubobject<UMikdashDoveMovement>(TEXT("FlightMovement"));
    FlightMovement->UpdatedComponent = FlightCollision;

    Body = CreateDefaultSubobject<USceneComponent>(TEXT("Body"));
    Body->SetupAttachment(FlightCollision);
    LeftWing = CreateDefaultSubobject<USceneComponent>(TEXT("LeftWing"));
    LeftWing->SetupAttachment(Body); LeftWing->SetRelativeLocation(FVector(0, -9, 5));
    RightWing = CreateDefaultSubobject<USceneComponent>(TEXT("RightWing"));
    RightWing->SetupAttachment(Body); RightWing->SetRelativeLocation(FVector(0, 9, 5));

    auto MakeMeshComponent = [this](const FName Name, USceneComponent* Parent)
    {
        UStaticMeshComponent* Part = CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Part->SetupAttachment(Parent);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCanEverAffectNavigation(false);
        Part->SetGenerateOverlapEvents(false);
        return Part;
    };
    // Imported DoveV2 meshes (assigned in BeginPlay when the map carries an appearance actor).
    BodyMesh = MakeMeshComponent(TEXT("BodyMesh"), Body); BodyMesh->SetVisibility(false);
    LeftWingMesh = MakeMeshComponent(TEXT("LeftWingMesh"), LeftWing); LeftWingMesh->SetVisibility(false);
    RightWingMesh = MakeMeshComponent(TEXT("RightWingMesh"), RightWing); RightWingMesh->SetVisibility(false);

    // Fallback: the earlier engine basic-shape silhouette, kept so flight never depends on an import.
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cone(TEXT("/Engine/BasicShapes/Cone.Cone"));
    auto Shape = [this, &MakeMeshComponent](const FName Name, USceneComponent* Parent, UStaticMesh* Mesh,
                       FVector Position, FVector Scale, FRotator Rotation = FRotator::ZeroRotator)
    {
        UStaticMeshComponent* Part = MakeMeshComponent(Name, Parent);
        Part->SetStaticMesh(Mesh);
        Part->SetRelativeLocation(Position); Part->SetRelativeScale3D(Scale); Part->SetRelativeRotation(Rotation);
        ProceduralParts.Add(Part);
    };
    Shape(TEXT("Body0"), Body, Sphere.Object, FVector::ZeroVector, FVector(.61,.25,.28));
    Shape(TEXT("Breast"), Body, Sphere.Object, FVector(15,0,4), FVector(.29,.25,.32));
    Shape(TEXT("Head"), Body, Sphere.Object, FVector(30,0,14), FVector(.19,.17,.19));
    Shape(TEXT("Beak"), Body, Cone.Object, FVector(42,0,14), FVector(.07,.07,.17), FRotator(90,0,0));
    for (int32 Index=0; Index<5; ++Index)
        Shape(FName(*FString::Printf(TEXT("TailFeather%d"),Index)), Body, Sphere.Object,
              FVector(-36, (Index-2)*5.f,0), FVector(.39,.067,.025), FRotator(0,(Index-2)*9.f,0));
    for (int32 Side : {-1,1})
    {
        USceneComponent* Wing = Side<0 ? LeftWing.Get() : RightWing.Get();
        Shape(FName(*FString::Printf(TEXT("WingShoulder%d"),Side)), Wing, Sphere.Object,
              FVector(-3,Side*19.f,0), FVector(.35,.55,.045), FRotator(0,Side*-12.f,0));
        for (int32 Index=0; Index<7; ++Index)
            Shape(FName(*FString::Printf(TEXT("FlightFeather%d_%d"),Side,Index)),Wing,Sphere.Object,
                  FVector(-15+Index*3.f,Side*(36+Index*3.f),0),
                  FVector(.075,.42-Index*.025,.024),FRotator(0,Side*(20+Index*7.f),0));
    }

    // Following camera placed by DoveFlightMath every tick: world-space, lagged, banking.
    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("DoveCamera"));
    FollowCamera->SetupAttachment(FlightCollision);
    FollowCamera->SetUsingAbsoluteLocation(true);
    FollowCamera->SetUsingAbsoluteRotation(true);
    FollowCamera->FieldOfView = 85.f;
    FollowCamera->bUsePawnControlRotation = false;
}

bool AMikdashDovePawn::ApplyAppearance(const AMikdashDoveAppearance* Appearance)
{
    if (!Appearance || !Appearance->IsComplete()) return false;
    return ApplyMeshes(Appearance->BodyMesh, Appearance->LeftWingMesh, Appearance->RightWingMesh,
        Appearance->LeftShoulderCm, Appearance->RightShoulderCm);
}

bool AMikdashDovePawn::ApplyMeshes(UStaticMesh* InBody, UStaticMesh* InLeftWing, UStaticMesh* InRightWing,
    const FVector& LeftShoulderCm, const FVector& RightShoulderCm)
{
    if (!InBody || !InLeftWing || !InRightWing || LeftShoulderCm.ContainsNaN() || RightShoulderCm.ContainsNaN()) return false;
    BodyMesh->SetStaticMesh(InBody);
    LeftWingMesh->SetStaticMesh(InLeftWing);
    RightWingMesh->SetStaticMesh(InRightWing);
    LeftWing->SetRelativeLocation(LeftShoulderCm);
    RightWing->SetRelativeLocation(RightShoulderCm);
    for (UStaticMeshComponent* Part : ProceduralParts) if (Part) Part->SetVisibility(false);
    for (UStaticMeshComponent* Part : {BodyMesh.Get(), LeftWingMesh.Get(), RightWingMesh.Get()}) Part->SetVisibility(true);
    bImportedMeshes = true;
    return true;
}

void AMikdashDovePawn::BeginPlay()
{
    Super::BeginPlay();
    PreviousYaw = GetActorRotation().Yaw;
    if (UWorld* World = GetWorld())
        for (TActorIterator<AMikdashDoveAppearance> It(World); It; ++It)
            if (ApplyAppearance(*It)) break;
    if (!bImportedMeshes)
    {
        // Editor/PIE convenience after an import but before the map carries the appearance
        // actor. Quiet: a missing asset simply keeps the procedural silhouette.
        const TCHAR* Paths[] = { TEXT("/Game/MikdashV3/Runtime/DoveV2/Meshes/SM_DoveBodyV2.SM_DoveBodyV2"),
            TEXT("/Game/MikdashV3/Runtime/DoveV2/Meshes/SM_DoveWingLeftV2.SM_DoveWingLeftV2"),
            TEXT("/Game/MikdashV3/Runtime/DoveV2/Meshes/SM_DoveWingRightV2.SM_DoveWingRightV2") };
        UStaticMesh* Loaded[3] = { nullptr, nullptr, nullptr };
        for (int32 Index = 0; Index < 3; ++Index)
            Loaded[Index] = LoadObject<UStaticMesh>(nullptr, Paths[Index], nullptr, LOAD_NoWarn | LOAD_Quiet);
        const AMikdashDoveAppearance* Defaults = GetDefault<AMikdashDoveAppearance>();
        ApplyMeshes(Loaded[0], Loaded[1], Loaded[2], Defaults->LeftShoulderCm, Defaults->RightShoulderCm);
    }
}

void AMikdashDovePawn::SetFlightBoost(bool bBoost) { FlightMovement->MaxSpeed = bBoost ? BoostSpeed : CruiseSpeed; }
float AMikdashDovePawn::GetFlightSpeed() const { return FlightMovement->GetMaxSpeed(); }

void AMikdashDovePawn::UpdateWings(float DeltaSeconds)
{
    const FVector Velocity = GetVelocity();
    const double Angle = Wings.Advance(DeltaSeconds, Velocity.Z, Velocity.Size());
    // Positive roll lifts +Y: the right wing rises with +Angle, the left (-Y) wing with -Angle.
    LeftWing->SetRelativeRotation(FRotator(0, 0, -Angle));
    RightWing->SetRelativeRotation(FRotator(0, 0, Angle));
}

void AMikdashDovePawn::UpdateBodyPose(float DeltaSeconds)
{
    const FVector Velocity = GetVelocity();
    const FRotator Current = GetActorRotation();
    double Yaw = Current.Yaw;
    if (Velocity.SizeSquared2D() > 100.0) Yaw = Velocity.Rotation().Yaw;
    const double YawRate = DeltaSeconds > 0.f ? MikdashDove::WrapDegrees(Yaw - PreviousYaw) / static_cast<double>(DeltaSeconds) : 0.0;
    PreviousYaw = Yaw;
    const double Alpha = MikdashDove::LagAlpha(DeltaSeconds, MikdashDove::CameraLagSeconds);
    SmoothedYawRate += (YawRate - SmoothedYawRate) * Alpha;
    const double TargetPitch = MikdashDove::BodyPitchDegrees(ToVec(Velocity));
    const double TargetRoll = MikdashDove::BankRoll(SmoothedYawRate);
    const double Pitch = Current.Pitch + (TargetPitch - Current.Pitch) * Alpha;
    const double Roll = Current.Roll + (TargetRoll - Current.Roll) * Alpha;
    SetActorRotation(FRotator(Pitch, Yaw, Roll));
}

void AMikdashDovePawn::UpdateCamera(float DeltaSeconds)
{
    const AController* Pilot = GetController();
    const FRotator Control = Pilot ? Pilot->GetControlRotation() : GetActorRotation();
    MikdashDove::CameraInput In;
    In.PawnPosition = ToVec(GetActorLocation()); In.Velocity = ToVec(GetVelocity());
    In.ControlYawDegrees = Control.Yaw; In.ControlPitchDegrees = FRotator::NormalizeAxis(Control.Pitch);
    In.YawRateDegreesPerSecond = SmoothedYawRate; In.Dt = DeltaSeconds;
    const MikdashDove::CameraOutput Out = MikdashDove::AdvanceCamera(Camera, In);
    FVector Position = ToFVector(Out.Position);
    const FVector Focus = ToFVector(Out.Focus);
    if (UWorld* World = GetWorld())
    {
        // Keep the camera out of walls: shorten toward the focus on a blocking hit.
        FCollisionQueryParams Params(SCENE_QUERY_STAT(MikdashDoveCamera), false, this);
        FHitResult Hit;
        if (World->SweepSingleByChannel(Hit, Focus, Position, FQuat::Identity, ECC_Camera,
            FCollisionShape::MakeSphere(12.f), Params) && Hit.bBlockingHit)
            Position = Hit.Location;
    }
    FRotator Look = (Focus - Position).Rotation();
    if ((Focus - Position).IsNearlyZero(1.f)) Look = Control;
    Look.Roll = Out.RollDegrees;
    FollowCamera->SetWorldLocationAndRotation(Position, Look);
}

void AMikdashDovePawn::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!FMath::IsFinite(DeltaSeconds) || DeltaSeconds <= 0.f) return;
    UpdateWings(DeltaSeconds);
    UpdateBodyPose(DeltaSeconds);
    UpdateCamera(DeltaSeconds);
}
