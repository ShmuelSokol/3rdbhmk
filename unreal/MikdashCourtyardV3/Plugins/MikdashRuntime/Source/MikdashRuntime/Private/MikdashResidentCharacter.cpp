#include "MikdashResidentCharacter.h"

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"

AMikdashResidentCharacter::AMikdashResidentCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
    AutoPossessAI = EAutoPossessAI::Disabled;
    AutoPossessPlayer = EAutoReceiveInput::Disabled;
    GetCapsuleComponent()->InitCapsuleSize(34.f, 96.f);
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    Movement->bRunPhysicsWithNoController = true;
    Movement->bOrientRotationToMovement = true;
    Movement->MaxWalkSpeed = 180.f; // authored walking pace; native tuning pending
    Movement->MaxStepHeight = 45.f; // matches current walkthrough capability
    Movement->RotationRate = FRotator(0.f, 240.f, 0.f);
    bUseControllerRotationYaw = false;
}

bool AMikdashResidentCharacter::BindResident(const TSharedPtr<MikdashCrowd::Runtime>& SharedRuntime,
    const FString& StableId, FMikdashResidentSegmentReview SegmentReview)
{
    if (RouteToken != 0 || !SharedRuntime.IsValid() || !SegmentReview || StableId.IsEmpty()) return false;
    const std::string Key(TCHAR_TO_UTF8(*StableId));
    if (!SharedRuntime->Find(Key)) return false;
    StopBody();
    Crowd = SharedRuntime; ResidentId = StableId; ResidentKey = Key;
    ReviewSegment = MoveTemp(SegmentReview);
    bNeedsPassageClearance = false;
    return true;
}

const MikdashCrowd::Person* AMikdashResidentCharacter::Resident() const
{
    return Crowd.IsValid() ? Crowd->Find(ResidentKey) : nullptr;
}

const MikdashCrowd::Identity* AMikdashResidentCharacter::Plan() const
{
    if (!Crowd.IsValid()) return nullptr;
    for (const MikdashCrowd::Identity& Identity : Crowd->Plans())
        if (Identity.Id == ResidentKey) return &Identity;
    return nullptr;
}

bool AMikdashResidentCharacter::NearFeet(const FVector& A, const FVector& B)
{
    return !A.ContainsNaN() && !B.ContainsNaN() && FVector::DistSquared2D(A, B) <= FMath::Square(HorizontalTolerance)
        && FMath::Abs(A.Z - B.Z) <= VerticalTolerance;
}

bool AMikdashResidentCharacter::RequestReviewedRoute(const FString& RouteId,
    const FVector& OriginFeet, const FVector& DestinationFeet)
{
    const MikdashCrowd::Person* Person = Resident();
    if (!Person || !ReviewSegment || RouteToken != 0 || Crowd->IsPaused() || UGameplayStatics::IsGamePaused(this)
        || Person->State != MikdashCrowd::Phase::RouteWait || !Person->Access
        || OriginFeet.ContainsNaN() || DestinationFeet.ContainsNaN()) return false;
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    if (!Movement->IsMovingOnGround() || !NearFeet(Movement->GetActorFeetLocation(), OriginFeet)) return false;
    UNavigationSystemV1* Nav = UNavigationSystemV1::GetCurrent(GetWorld());
    if (!Nav) return false;
    FNavLocation ProjectedStart, ProjectedEnd;
    const FVector Extent(40.f, 40.f, 100.f);
    const FNavAgentProperties& Properties = Movement->GetNavAgentPropertiesRef();
    if (!Nav->ProjectPointToNavigation(OriginFeet, ProjectedStart, Extent, &Properties)
        || !Nav->ProjectPointToNavigation(DestinationFeet, ProjectedEnd, Extent, &Properties)
        || !NearFeet(ProjectedStart.Location, OriginFeet) || !NearFeet(ProjectedEnd.Location, DestinationFeet)) return false;
    UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(
        this, ProjectedStart.Location, ProjectedEnd.Location, this);
    if (!Path || !Path->IsValid() || Path->IsPartial() || Path->PathPoints.Num() < 2
        || !NearFeet(Path->PathPoints[0], OriginFeet) || !NearFeet(Path->PathPoints.Last(), DestinationFeet)) return false;
    FVector From = Movement->GetActorFeetLocation();
    for (const FVector& To : Path->PathPoints)
    {
        if (To.ContainsNaN() || !ReviewSegment(ResidentId, From, To)) return false;
        From = To;
    }
    if (!ReviewSegment(ResidentId, From, DestinationFeet)) return false;
    const uint64 Token = Crowd->Reserve(ResidentKey, std::string(TCHAR_TO_UTF8(*RouteId)));
    if (Token == 0) return false;
    RoutePoints = Path->PathPoints;
    RoutePoints.Add(DestinationFeet);
    MappedDestination = DestinationFeet;
    PointIndex = 0; RouteToken = Token; bNeedsPassageClearance = false;
    return true;
}

void AMikdashResidentCharacter::StopBody()
{
    ConsumeMovementInputVector();
    GetCharacterMovement()->StopMovementImmediately();
}

void AMikdashResidentCharacter::FailRoute()
{
    StopBody();
    RoutePoints.Reset(); PointIndex = 0;
    if (Crowd.IsValid()) Crowd->SetAccess(ResidentKey, false);
    if (RouteToken != 0)
    {
        bNeedsPassageClearance = true;
    }
}

void AMikdashResidentCharacter::RequestResidentStop() { FailRoute(); }

bool AMikdashResidentCharacter::ConfirmPassageCleared(uint64 ExpectedToken)
{
    if (!Crowd.IsValid() || !bNeedsPassageClearance || ExpectedToken == 0 || ExpectedToken != RouteToken
        || !GetVelocity().IsNearlyZero()) return false;
    if (!Crowd->AcknowledgeStopped(ResidentKey, ExpectedToken)) return false;
    RouteToken = 0; bNeedsPassageClearance = false;
    return true;
}

void AMikdashResidentCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const MikdashCrowd::Person* Person = Resident();
    const bool bPaused = !Person || Crowd->IsPaused() || UGameplayStatics::IsGamePaused(this);
    if (GetMesh() && bPaused != bWasPaused) GetMesh()->bPauseAnims = bPaused;
    bWasPaused = bPaused;
    if (bPaused) { StopBody(); return; }
    if (RouteToken == 0) return;
    if (Person->Token != RouteToken || Person->State != MikdashCrowd::Phase::Traveling || !Person->Access)
    {
        FailRoute(); return;
    }
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    if (!Movement->IsMovingOnGround()) { FailRoute(); return; }
    const FVector Feet = Movement->GetActorFeetLocation();
    while (RoutePoints.IsValidIndex(PointIndex) && NearFeet(Feet, RoutePoints[PointIndex])) ++PointIndex;
    if (!RoutePoints.IsValidIndex(PointIndex))
    {
        StopBody();
        const MikdashCrowd::Identity* Identity = Plan();
        if (!Identity || Person->GoalIndex >= Identity->Goals.size()
            || !NearFeet(Feet, MappedDestination) || !ReviewSegment(ResidentId, Feet, MappedDestination)
            || !Crowd->Arrive(ResidentKey, RouteToken, Identity->Goals[Person->GoalIndex].Destination))
        {
            FailRoute(); return;
        }
        RouteToken = 0; RoutePoints.Reset(); PointIndex = 0;
        return;
    }
    const FVector Target = RoutePoints[PointIndex];
    if (!ReviewSegment(ResidentId, Feet, Target)) { FailRoute(); return; }
    FVector Direction = Target - Feet; Direction.Z = 0.0;
    if (Direction.IsNearlyZero()) { FailRoute(); return; }
    AddMovementInput(Direction.GetSafeNormal(), 1.f, true);
}

FString AMikdashResidentCharacter::GetResidentName() const
{
    const MikdashCrowd::Identity* Identity = Plan();
    return Identity ? FString(UTF8_TO_TCHAR(Identity->Name.c_str())) : FString();
}

FString AMikdashResidentCharacter::GetResidentGoal() const
{
    const MikdashCrowd::Person* Person = Resident(); const MikdashCrowd::Identity* Identity = Plan();
    return Person && Identity && Person->GoalIndex < Identity->Goals.size()
        ? FString(UTF8_TO_TCHAR(Identity->Goals[Person->GoalIndex].Label.c_str())) : FString();
}

FString AMikdashResidentCharacter::GetResidentAction() const
{
    const MikdashCrowd::Person* Person = Resident(); const MikdashCrowd::Identity* Identity = Plan();
    return Person && Identity && Person->State == MikdashCrowd::Phase::Working && Person->GoalIndex < Identity->Goals.size()
        ? FString(UTF8_TO_TCHAR(Identity->Goals[Person->GoalIndex].Action.c_str())) : FString();
}

FString AMikdashResidentCharacter::GetResidentState() const
{
    const MikdashCrowd::Person* Person = Resident();
    if (!Person) return TEXT("Unbound");
    if (Crowd->IsPaused() || UGameplayStatics::IsGamePaused(this)) return TEXT("Paused");
    switch (Person->State)
    {
    case MikdashCrowd::Phase::Schedule: return TEXT("Waiting for schedule");
    case MikdashCrowd::Phase::AccessReview: return TEXT("Waiting for reviewed access");
    case MikdashCrowd::Phase::RouteWait: return TEXT("Waiting for route");
    case MikdashCrowd::Phase::Traveling: return TEXT("Traveling");
    case MikdashCrowd::Phase::StopRequested: return TEXT("Stopped; passage clearance required");
    case MikdashCrowd::Phase::Working: return TEXT("Attending to goal");
    case MikdashCrowd::Phase::Complete: return TEXT("Plan complete");
    }
    return TEXT("Unknown");
}

void AMikdashResidentCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    FailRoute(); // owner releases reservation only after this body's collision is gone
    Crowd.Reset(); ReviewSegment = nullptr;
    Super::EndPlay(EndPlayReason);
}
