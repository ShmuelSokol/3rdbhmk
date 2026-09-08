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
    const FVector& OriginFeet, const FVector& DestinationFeet, bool bAllowReviewedDirectCorridor, double MaxDirectCorridorCm)
{
    const auto Reject = [this](const TCHAR* Reason) { RouteDiagnostic = Reason; return false; };
    const MikdashCrowd::Person* Person = Resident();
    if (!Person || !ReviewSegment) return Reject(TEXT("Unbound or missing authoritative reviewer"));
    if (RouteToken != 0) return Reject(TEXT("Existing reservation retained"));
    if (Crowd->IsPaused() || UGameplayStatics::IsGamePaused(this)) return Reject(TEXT("Paused"));
    if (Person->State != MikdashCrowd::Phase::RouteWait || !Person->Access)
        return Reject(TEXT("Schedule/access/state does not authorize route"));
    if (OriginFeet.ContainsNaN() || DestinationFeet.ContainsNaN()) return Reject(TEXT("Nonfinite waypoint"));
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    if (!Movement->IsMovingOnGround()) return Reject(TEXT("Body not grounded"));
    if (!NearFeet(Movement->GetActorFeetLocation(), OriginFeet)) return Reject(TEXT("Body not at confirmed origin"));

    TArray<FVector> Candidate;
    FString NavigationFailure;
    UNavigationSystemV1* Nav = UNavigationSystemV1::GetCurrent(GetWorld());
    if (!Nav) NavigationFailure = TEXT("Navigation system unavailable");
    else
    {
        FNavLocation ProjectedStart, ProjectedEnd;
        const FVector Extent(40.f, 40.f, 100.f);
        const FNavAgentProperties& Properties = Movement->GetNavAgentPropertiesRef();
        if (!Nav->ProjectPointToNavigation(OriginFeet, ProjectedStart, Extent, &Properties)
            || !Nav->ProjectPointToNavigation(DestinationFeet, ProjectedEnd, Extent, &Properties))
            NavigationFailure = TEXT("Navigation endpoint projection unavailable");
        else if (!NearFeet(ProjectedStart.Location, OriginFeet) || !NearFeet(ProjectedEnd.Location, DestinationFeet))
            return Reject(TEXT("Navigation projection outside reviewed waypoint tolerance"));
        else
        {
            UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(
                this, ProjectedStart.Location, ProjectedEnd.Location, this);
            if (!Path || !Path->IsValid() || Path->IsPartial() || Path->PathPoints.Num() < 2)
                NavigationFailure = TEXT("Complete navigation path unavailable");
            else if (!NearFeet(Path->PathPoints[0], OriginFeet) || !NearFeet(Path->PathPoints.Last(), DestinationFeet))
                return Reject(TEXT("Navigation path endpoints outside reviewed tolerance"));
            else Candidate = Path->PathPoints;
        }
    }
    const bool bDirect = Candidate.Num() == 0;
    if (bDirect)
    {
        if (!bAllowReviewedDirectCorridor) { RouteDiagnostic = NavigationFailure; return false; }
        const double CorridorLimit = FMath::IsFinite(MaxDirectCorridorCm) ? FMath::Clamp(MaxDirectCorridorCm, 0.0, 5000.0) : 100.0;
        if (FVector::DistSquared(OriginFeet, DestinationFeet) > FMath::Square(CorridorLimit)
            || FMath::Abs(OriginFeet.Z-DestinationFeet.Z) > 3.0)
            return Reject(TEXT("Direct corridor exceeds its length or flatness bound"));
        Candidate.Add(OriginFeet); Candidate.Add(DestinationFeet);
    }
    // Every candidate, including the opt-in straight corridor, receives the same
    // authoritative physical/access review. A rejection never selects another path.
    FVector From = Movement->GetActorFeetLocation();
    for (const FVector& To : Candidate)
    {
        if (To.ContainsNaN() || !ReviewSegment(ResidentId, From, To))
            return Reject(TEXT("Authoritative segment review rejected: access/floor/capsule"));
        From = To;
    }
    if (!ReviewSegment(ResidentId, From, DestinationFeet))
        return Reject(TEXT("Authoritative destination review rejected"));
    const uint64 Token = Crowd->Reserve(ResidentKey, std::string(TCHAR_TO_UTF8(*RouteId)));
    if (Token == 0) return Reject(TEXT("Reservation unavailable"));
    RoutePoints = MoveTemp(Candidate);
    RoutePoints.Add(DestinationFeet);
    MappedDestination = DestinationFeet;
    PointIndex = 0; RouteToken = Token; bNeedsPassageClearance = false;
    Recovery.Reset(); bHasLastFeet = false; SidestepCount = 0; bFacingEnabled = false;
    RouteDiagnostic = bDirect ? TEXT("Accepted reviewed direct corridor; ") + NavigationFailure : TEXT("Accepted reviewed navigation path");
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
    RoutePoints.Reset(); PointIndex = 0; Recovery.Reset(); bHasLastFeet = false;
    if (Crowd.IsValid()) Crowd->SetAccess(ResidentKey, false);
    if (RouteToken != 0)
    {
        bNeedsPassageClearance = true;
    }
}

void AMikdashResidentCharacter::RequestResidentStop() { RouteDiagnostic = TEXT("External stop requested; reservation retained if active"); FailRoute(); }

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
    // A conversation freezes the body where it stands and turns it to the walker. The route
    // reservation, goal index and access are all left exactly as they were, so the resident
    // simply carries on from here when the panel closes. The two-second block recovery is
    // held off as well: standing still on purpose is not being blocked.
    if (bConversationHold)
    {
        StopBody();
        Recovery.Reset(); bHasLastFeet = false;
        UpdateConversationFacing(DeltaSeconds);
        return;
    }
    if (RouteToken == 0) { UpdateStandingFacing(DeltaSeconds); return; }
    if (Person->Token != RouteToken || Person->State != MikdashCrowd::Phase::Traveling || !Person->Access)
    {
        RouteDiagnostic = TEXT("Travel interrupted: token/state/access changed"); FailRoute(); return;
    }
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    if (!Movement->IsMovingOnGround()) { RouteDiagnostic = TEXT("Travel interrupted: lost ground"); FailRoute(); return; }
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
            RouteDiagnostic = TEXT("Physical arrival/state confirmation rejected"); FailRoute(); return;
        }
        RouteDiagnostic = TEXT("Physical arrival confirmed");
        RouteToken = 0; RoutePoints.Reset(); PointIndex = 0;
        return;
    }
    FVector Target = RoutePoints[PointIndex];
    if (!ReviewSegment(ResidentId, Feet, Target)) { RouteDiagnostic = TEXT("Travel interrupted: authoritative floor/capsule/access review"); FailRoute(); return; }
    // Obstacle recovery: held still for two seconds against a target -> reviewed 100 cm sidestep,
    // then retry the same target. Rejected sidesteps simply wait for the route timeout.
    const double MovedCm = bHasLastFeet ? FVector::Dist2D(Feet, LastFeet) : 0.0;
    LastFeet = Feet; bHasLastFeet = true;
    if (Recovery.Advance(DeltaSeconds, MovedCm, true) && TrySidestep(Feet, Target)) Target = RoutePoints[PointIndex];
    FVector Direction = Target - Feet; Direction.Z = 0.0;
    if (Direction.IsNearlyZero()) { FailRoute(); return; }
    AddMovementInput(Direction.GetSafeNormal(), 1.f, true);
}

bool AMikdashResidentCharacter::TrySidestep(const FVector& Feet, const FVector& Target)
{
    // Both sides go through the same authoritative review; nothing unreviewed is walked.
    for (int32 Attempt = 0; Attempt < 2; ++Attempt)
    {
        const MikdashRoute::Point2 Side = Recovery.SidestepTarget({Feet.X, Feet.Y}, {Target.X, Target.Y});
        const FVector SideFeet(Side.X, Side.Y, Feet.Z);
        if (ReviewSegment(ResidentId, Feet, SideFeet) && ReviewSegment(ResidentId, SideFeet, Target))
        {
            RoutePoints.Insert(SideFeet, PointIndex);
            ++SidestepCount;
            RouteDiagnostic = FString::Printf(TEXT("Blocked 2 s: reviewed sidestep %d of 100 cm, retrying"), SidestepCount);
            return true;
        }
    }
    RouteDiagnostic = TEXT("Blocked 2 s: both sidesteps rejected by review; waiting");
    return false;
}

void AMikdashResidentCharacter::SetStandingFacingTarget(const FVector& WorldTarget, bool bEnabled)
{
    bFacingEnabled = bEnabled && !WorldTarget.ContainsNaN();
    FacingTarget = WorldTarget;
}

void AMikdashResidentCharacter::UpdateStandingFacing(float DeltaSeconds)
{
    if (!bFacingEnabled || !GetVelocity().IsNearlyZero(1.0) || !GetCharacterMovement()->IsMovingOnGround()) return;
    const FVector Feet = GetCharacterMovement()->GetActorFeetLocation();
    if (FVector::DistSquared2D(Feet, FacingTarget) < FMath::Square(50.0)) return;
    const double TargetYaw = MikdashRoute::YawTowardDegrees({Feet.X, Feet.Y}, {FacingTarget.X, FacingTarget.Y});
    const double Yaw = MikdashRoute::TurnToward(GetActorRotation().Yaw, TargetYaw, DeltaSeconds);
    SetActorRotation(FRotator(0.0, Yaw, 0.0));
}

void AMikdashResidentCharacter::SetResidentProfile(const FString& InName, const FString& InRole,
    const FString& InMission, const FString& InOrigin, const FString& InPresence,
    const FString& InGarmentVariant, const TArray<FString>& InDialogLines)
{
    DisplayName = InName; RoleTitle = InRole; Mission = InMission;
    Origin = InOrigin; PresenceNote = InPresence; GarmentVariant = InGarmentVariant;
    DialogLines = InDialogLines;
}

void AMikdashResidentCharacter::SetResidentBody(const FString& InVariantId, double InVisualScale, bool bInFallback)
{
    BodyVariantId = InVariantId;
    BodyVisualScale = FMath::IsFinite(InVisualScale) ? InVisualScale : 1.0;
    bBodyFallback = bInFallback;
}

void AMikdashResidentCharacter::SetConversationHold(bool bHold, FVector FaceWorldTarget)
{
    bConversationHold = bHold && !FaceWorldTarget.ContainsNaN();
    ConversationFacing = FaceWorldTarget;
    if (bConversationHold) StopBody();
    else { Recovery.Reset(); bHasLastFeet = false; }
}

void AMikdashResidentCharacter::UpdateConversationFacing(float DeltaSeconds)
{
    if (!GetCharacterMovement()->IsMovingOnGround()) return;
    const FVector Feet = GetCharacterMovement()->GetActorFeetLocation();
    if (FVector::DistSquared2D(Feet, ConversationFacing) < FMath::Square(30.0)) return;
    const double TargetYaw = MikdashRoute::YawTowardDegrees({Feet.X, Feet.Y}, {ConversationFacing.X, ConversationFacing.Y});
    const double Yaw = MikdashRoute::TurnToward(GetActorRotation().Yaw, TargetYaw, DeltaSeconds);
    SetActorRotation(FRotator(0.0, Yaw, 0.0));
}

FString AMikdashResidentCharacter::GetResidentName() const
{
    if (!DisplayName.IsEmpty()) return DisplayName;
    const MikdashCrowd::Identity* Identity = Plan();
    return Identity ? FString(UTF8_TO_TCHAR(Identity->Name.c_str())) : FString();
}

FString AMikdashResidentCharacter::GetResidentGoal() const
{
    const MikdashCrowd::Person* Person = Resident(); const MikdashCrowd::Identity* Identity = Plan();
    if (!Person || !Identity) return FString();
    if (Person->GoalIndex >= Identity->Goals.size()) return TEXT("Plan complete: resting with the group");
    return FString(UTF8_TO_TCHAR(Identity->Goals[Person->GoalIndex].Label.c_str()));
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
