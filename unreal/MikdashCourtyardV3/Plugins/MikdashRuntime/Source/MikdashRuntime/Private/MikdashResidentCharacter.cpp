#include "MikdashResidentCharacter.h"

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Math/RandomStream.h"
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
    // Presentational locomotion tuning. See the MikdashGait note in the header for why every
    // one of these differs from what was here before. The capsule, the route, the segment
    // review, access and the amah frame are untouched.
    Movement->MaxWalkSpeed = static_cast<float>(MikdashGait::BaseWalkSpeedCm); // was a uniform 180
    Movement->MaxStepHeight = 45.f; // matches current walkthrough capability
    Movement->RotationRate = FRotator(0.f, static_cast<float>(MikdashGait::WalkTurnRateDegPerSec), 0.f);
    // A person does not reach walking pace in one frame and does not stop dead. The engine
    // defaults (2048 cm/s^2 both ways) put a body at full pace in 0.09 s, which is precisely
    // what makes the in-place walk clip snap on at full stride.
    Movement->MaxAcceleration = static_cast<float>(MikdashGait::MaxAccelerationCm);
    Movement->BrakingDecelerationWalking = static_cast<float>(MikdashGait::BrakingDecelerationCm);
    Movement->bUseSeparateBrakingFriction = true;
    Movement->BrakingFriction = 1.5f;
    Movement->GroundFriction = 5.f;
    bUseControllerRotationYaw = false;
}

void AMikdashResidentCharacter::ConfigureGait(uint32 Seed, double InVisualScale, double ClipGroundSpeedCmPerSec)
{
    // One deterministic stream per person: the same resident always walks the same way across
    // runs and builds, and two neighbours spawned from the same directory never share a pace,
    // a cadence or a gait phase. Nothing here is random at runtime.
    FRandomStream Stream(static_cast<int32>((Seed | 1u) & 0x7fffffffu));
    const double Scale = (FMath::IsFinite(InVisualScale) && InVisualScale > 0.1) ? InVisualScale : 1.0;
    CadenceBias = 1.0 + Stream.FRandRange(-MikdashGait::CadenceSpread, MikdashGait::CadenceSpread);
    GaitPhase01 = Stream.FRand();
    // Pace is DERIVED FROM THE CLIP whenever the caller knows what the clip supports, because
    // a body that translates faster than its own stride is the single loudest puppet tell in
    // the scene. Doing it this way also means the day the walk clip is re-authored with a
    // natural 70-73 cm step, changing one measured number makes every resident walk at a
    // natural pace with no other edit. A taller person covers more ground per step, so the
    // body's visual scale multiplies through; the per-person cadence bias then IS the play
    // rate, and stays within a few percent of 1.0.
    const bool bDerived = FMath::IsFinite(ClipGroundSpeedCmPerSec) && ClipGroundSpeedCmPerSec > 1.0;
    const double Wanted = bDerived
        ? ClipGroundSpeedCmPerSec * Scale * CadenceBias
        : (MikdashGait::BaseWalkSpeedCm
            + Stream.FRandRange(-MikdashGait::WalkSpeedSpreadCm, MikdashGait::WalkSpeedSpreadCm)) * Scale;
    PreferredWalkSpeedCm = FMath::Clamp(Wanted, MikdashGait::MinWalkSpeedCm, MikdashGait::MaxWalkSpeedCm);
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    Movement->MaxWalkSpeed = static_cast<float>(PreferredWalkSpeedCm);
    // A slower walker also takes a corner more slowly.
    const double TurnRate = MikdashGait::WalkTurnRateDegPerSec * FMath::Clamp(CadenceBias, 0.85, 1.15);
    Movement->RotationRate = FRotator(0.f, static_cast<float>(TurnRate), 0.f);
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
    const FVector Heading = Direction.GetSafeNormal();
    // Ease the input down into the final stop and into a corner. Driving full-scale input up
    // to the last centimetre and then releasing it is what makes an arrival read as a machine
    // halting; holding walking pace through a 90 degree turn is what makes a corner read as a
    // turret. Neither eases past the reviewed waypoint tolerance: the floor of MinInputScale
    // still closes the remaining distance.
    double InputScale = 1.0;
    if (PointIndex == RoutePoints.Num() - 1)
    {
        InputScale = FMath::Clamp(FVector::Dist2D(Feet, Target) / MikdashGait::ArrivalEaseCm,
            MikdashGait::MinInputScale, 1.0);
    }
    const FVector Velocity2D(GetVelocity().X, GetVelocity().Y, 0.0);
    if (Velocity2D.SizeSquared() > FMath::Square(MikdashGait::CornerSlowSpeedCm))
    {
        const double Alignment = FVector::DotProduct(Velocity2D.GetSafeNormal(), Heading);
        InputScale = FMath::Min(InputScale, FMath::GetMappedRangeValueClamped(
            FVector2D(MikdashGait::CornerHardCos, MikdashGait::CornerSoftCos),
            FVector2D(MikdashGait::CornerMinScale, 1.0), Alignment));
    }
    // Never ease below what the two-second block watchdog reads as stuck; a body deliberately
    // slowing for a corner or a stop is not a body being obstructed.
    InputScale = FMath::Max(InputScale, FMath::Min(1.0,
        MikdashRoute::BlockedSpeedCmPerSecond * MikdashGait::BlockWatchdogMargin
            / FMath::Max(1.0, PreferredWalkSpeedCm)));
    AddMovementInput(Heading, static_cast<float>(InputScale), true);
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
    // A standing turn has no turn-in-place clip behind it, so it is always a frozen-feet
    // pivot. Slowing it and refusing to chase a few degrees is the most that can be done from
    // here; the cure is a locomotion Animation Blueprint with turn-in-place.
    if (FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw, TargetYaw)) < MikdashGait::StandingTurnDeadZoneDeg) return;
    const double Yaw = MikdashRoute::TurnToward(GetActorRotation().Yaw, TargetYaw, DeltaSeconds,
        MikdashGait::StandingTurnRateDegPerSec);
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
    if (FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw, TargetYaw)) < MikdashGait::StandingTurnDeadZoneDeg) return;
    const double Yaw = MikdashRoute::TurnToward(GetActorRotation().Yaw, TargetYaw, DeltaSeconds,
        MikdashGait::StandingTurnRateDegPerSec);
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
