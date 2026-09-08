#include "MikdashResidentPopulation.h"
#include "MikdashResidentCharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include <string>

AMikdashResidentPopulation::AMikdashResidentPopulation()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
}

void AMikdashResidentPopulation::BeginPlay()
{
    Super::BeginPlay();
    if (bActivateReviewedPilotOnBeginPlay && !InitializeReviewedPilot())
    {
        Status = TEXT("Authored startup initialization rejected; population remains stopped");
        UE_LOG(LogTemp, Warning, TEXT("%s: %s"), *GetName(), *Status);
    }
}

bool AMikdashResidentPopulation::ReviewSegment(int32 BodyIndex, const FVector& From, const FVector& To) const
{
    if (!GetWorld() || !Bodies.IsValidIndex(BodyIndex) || !IsValid(Bodies[BodyIndex])
        || From.ContainsNaN() || To.ContainsNaN()) return false;
    const AMikdashResidentCharacter* Body = Bodies[BodyIndex];
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ResidentPilotReview), true);
    Query.AddIgnoredActor(this); Query.AddIgnoredActor(Body);
    if (IsExtendedBody(BodyIndex))
    {
        // The extended body may only walk the authored loop corridor (150 cm either side),
        // inside the outer-court region and on the Z 300 floor. Not a general access policy.
        for (const FVector& Point : {From, To})
            if (!MikdashRoute::PointInRegion({Point.X, Point.Y}) || FMath::Abs(Point.Z - MikdashRoute::FloorZ) > MikdashRoute::FloorToleranceCm) return false;
        if (!MikdashRoute::SegmentWithinCorridor({From.X, From.Y}, {To.X, To.Y}, LoopPoints)) return false;
    }
    else
    {
        // Convex box plus capsule inset makes the entire straight segment remain in the
        // authored outer visitor region. This is not a general sanctuary access policy.
        for (const FVector& Point : {From, To})
            if (Point.X < 4734 || Point.X > 5266 || Point.Y < 934 || Point.Y > 1416
                || FMath::Abs(Point.Z - 300.0) > 12.0) return false;
    }
    const int32 Samples = FMath::Max(1, FMath::CeilToInt(FVector::Distance(From, To) / 25.0));
    for (int32 Step = 0; Step <= Samples; ++Step)
    {
        const FVector Feet = FMath::Lerp(From, To, static_cast<double>(Step) / Samples);
        FHitResult Floor;
        if (!GetWorld()->LineTraceSingleByChannel(Floor, Feet + FVector(0,0,30),
            Feet - FVector(0,0,30), ECC_Visibility, Query) || !Floor.bBlockingHit
            || FMath::Abs(Floor.ImpactPoint.Z - Feet.Z) > 3.0 || Floor.ImpactNormal.Z < 0.95) return false;
    }
    // Keep 2 cm separation above reviewed floor; never interpret missing traces as clear.
    FHitResult Obstacle;
    const FCollisionShape Capsule = FCollisionShape::MakeCapsule(34.f, 96.f);
    const FVector Lift(0,0,98);
    if (GetWorld()->OverlapBlockingTestByChannel(From + Lift, FQuat::Identity, ECC_Pawn, Capsule, Query)
        || GetWorld()->OverlapBlockingTestByChannel(To + Lift, FQuat::Identity, ECC_Pawn, Capsule, Query)) return false;
    return !GetWorld()->SweepSingleByChannel(Obstacle, From + Lift, To + Lift,
        FQuat::Identity, ECC_Pawn, Capsule, Query);
}

bool AMikdashResidentPopulation::ValidateExtendedRoute(const FVector& BodyStart, FString& Reason) const
{
    const int32 Count = ExtendedRouteWaypoints.Num();
    if (ExtendedRouteLabels.Num() != Count || ExtendedRouteActions.Num() != Count
        || ExtendedRoutePauseSeconds.Num() != Count || ExtendedRouteLookTargets.Num() != Count)
    { Reason = TEXT("waypoint, label, action, pause and look-target arrays must have equal length"); return false; }
    if (ExtendedRouteLaps < 1 || Count * ExtendedRouteLaps > 64) { Reason = TEXT("laps must be 1..12 (at most 64 goals)"); return false; }
    if (Count == 0 || ExtendedRouteWaypoints[0].ContainsNaN() || FVector::Distance(ExtendedRouteWaypoints[0], BodyStart) > 3.0)
    { Reason = TEXT("waypoint 0 must be the body's reviewed start position"); return false; }
    std::vector<MikdashRoute::Point2> Points; std::vector<double> Pauses; std::vector<std::string> Labels;
    for (int32 Index = 0; Index < Count; ++Index)
    {
        const FVector& P = ExtendedRouteWaypoints[Index];
        if (P.ContainsNaN() || FMath::Abs(P.Z - MikdashRoute::FloorZ) > MikdashRoute::FloorToleranceCm) { Reason = TEXT("waypoint off the Z 300 outer-court floor"); return false; }
        if (ExtendedRouteLookTargets[Index].ContainsNaN() || ExtendedRouteActions[Index].IsEmpty()) { Reason = TEXT("look target or action missing"); return false; }
        Points.push_back({P.X, P.Y}); Pauses.push_back(ExtendedRoutePauseSeconds[Index]);
        Labels.push_back(std::string(TCHAR_TO_UTF8(*ExtendedRouteLabels[Index])));
    }
    std::string Why;
    if (!MikdashRoute::ValidateLoop(Points, Pauses, Labels, &Why)) { Reason = FString(UTF8_TO_TCHAR(Why.c_str())); return false; }
    Reason.Empty();
    return true;
}

FString AMikdashResidentPopulation::WaypointName(const std::string& Key, std::size_t Index) const
{
    const FString Name(UTF8_TO_TCHAR(Key.c_str()));
    return Index == 0 ? Name + TEXT("-start") : Name + FString::Printf(TEXT("-wp-%d"), static_cast<int32>(Index));
}

bool AMikdashResidentPopulation::InitializeReviewedPilot()
{
    if (bActive || Crowd.IsValid() || !GetWorld() || !GetWorld()->IsGameWorld()
        || Bodies.Num() != 5 || !IdleAnimation || !WalkAnimation) return false;
    const FVector Positions[] = { FVector(4900,1000,300), FVector(5120,1120,300),
        FVector(4980,1260,300), FVector(5240,1330,300), FVector(4760,1180,300) };
    // Extended loop: validated first because the first leg's review depends on it. An invalid
    // configuration is reported and ignored; the short authored pilot still runs.
    bExtendedRoute = false; LoopPoints.clear();
    if (ExtendedRouteBodyIndex >= 0)
    {
        FString Reason;
        if (ExtendedRouteBodyIndex > 4) Reason = TEXT("body index must be 0..4");
        else if (ValidateExtendedRoute(Positions[ExtendedRouteBodyIndex], Reason))
        {
            for (const FVector& P : ExtendedRouteWaypoints) LoopPoints.push_back({P.X, P.Y});
            bExtendedRoute = true;
            ExtendedStatus = FString::Printf(TEXT("Extended loop: body %d, %d waypoints, %.1f m, %d laps"), ExtendedRouteBodyIndex,
                ExtendedRouteWaypoints.Num(), MikdashRoute::LoopLengthCm(LoopPoints) / 100.0, ExtendedRouteLaps);
        }
        if (!bExtendedRoute)
        {
            ExtendedStatus = TEXT("Extended route ignored: ") + Reason;
            UE_LOG(LogTemp, Warning, TEXT("%s: %s"), *GetName(), *ExtendedStatus);
        }
    }
    TSet<AMikdashResidentCharacter*> Unique;
    Origins.Reset(); Destinations.Reset();
    for (int32 Index = 0; Index < 5; ++Index)
    {
        AMikdashResidentCharacter* Body = Bodies[Index];
        if (!IsValid(Body) || Body->GetWorld() != GetWorld() || Unique.Contains(Body)
            || !Body->GetResidentId().IsEmpty()) return false;
        Unique.Add(Body);
        USkeletalMesh* Mesh = Body->GetMesh()->GetSkeletalMeshAsset();
        if (!Mesh || Mesh->GetSkeleton() != IdleAnimation->GetSkeleton()
            || Mesh->GetSkeleton() != WalkAnimation->GetSkeleton()
            || !Body->GetActorScale3D().Equals(FVector::OneVector, 0.001)
            || FMath::Abs(Body->GetCapsuleComponent()->GetScaledCapsuleRadius()-34.f) > 0.01f
            || FMath::Abs(Body->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-96.f) > 0.01f) return false;
        const FVector Feet = Body->GetCharacterMovement()->GetActorFeetLocation();
        if (FVector::Distance(Feet, Positions[Index]) > 3.0) return false;
        Origins.Add(Positions[Index]);
        // Small individually reviewed route, not repetitive crowd wandering; the extended
        // body's first leg goes to its second authored waypoint instead.
        Destinations.Add(IsExtendedBody(Index) ? ExtendedRouteWaypoints[1] : Positions[Index] + FVector(Index == 3 ? -80 : 80, 0, 0));
        if (!ReviewSegment(Index, Origins[Index], Destinations[Index]))
        {
            if (!IsExtendedBody(Index)) return false;
            // Physical review of the first leg failed: keep the pilot, drop the extension.
            bExtendedRoute = false; LoopPoints.clear();
            ExtendedStatus = TEXT("Extended route ignored: first leg failed floor/capsule review at startup");
            UE_LOG(LogTemp, Warning, TEXT("%s: %s"), *GetName(), *ExtendedStatus);
            Destinations[Index] = Positions[Index] + FVector(Index == 3 ? -80 : 80, 0, 0);
            if (!ReviewSegment(Index, Origins[Index], Destinations[Index])) return false;
        }
    }
    std::vector<MikdashCrowd::Identity> Plans;
    std::vector<MikdashCrowd::Route> Routes;
    for (int32 Index = 0; Index < 5; ++Index)
    {
        const std::string Key = "authored-outer-visitor-0" + std::to_string(Index + 1);
        MikdashCrowd::Identity Plan;
        Plan.Id = Key; Plan.Name = "Fictional visitor " + std::to_string(Index + 1);
        Plan.Start = Key + "-start";
        if (IsExtendedBody(Index))
        {
            const std::size_t N = LoopPoints.size();
            for (std::size_t J = 0; J < N * static_cast<std::size_t>(ExtendedRouteLaps); ++J)
            {
                const MikdashRoute::Leg Leg = MikdashRoute::LegForGoal(J, N);
                MikdashCrowd::Goal Goal;
                Goal.Id = Key + "-goal-" + std::to_string(J);
                Goal.Label = std::string(TCHAR_TO_UTF8(*ExtendedRouteLabels[static_cast<int32>(Leg.To)]));
                Goal.Destination = std::string(TCHAR_TO_UTF8(*WaypointName(Key, Leg.To)));
                Goal.Action = std::string(TCHAR_TO_UTF8(*ExtendedRouteActions[static_cast<int32>(Leg.To)]));
                Goal.Earliest = static_cast<MikdashCrowd::Seconds>(Index * 4);
                Goal.Duration = static_cast<MikdashCrowd::Seconds>(FMath::Max(1, FMath::RoundToInt(ExtendedRoutePauseSeconds[static_cast<int32>(Leg.To)])));
                Plan.Goals.push_back(Goal);
                MikdashCrowd::Route Route;
                Route.Id = Key + "-leg-" + std::to_string(J);
                Route.From = std::string(TCHAR_TO_UTF8(*WaypointName(Key, Leg.From)));
                Route.To = Goal.Destination;
                Route.Resource = "outer-visitor-loop"; Route.Capacity = 1; Route.Timeout = 90;
                Routes.push_back(Route);
            }
        }
        else
        {
            MikdashCrowd::Goal Goal;
            Goal.Id = Key + "-observe"; Goal.Label = "Walk to a nearby meeting place";
            Goal.Destination = Key + "-meeting"; Goal.Action = "Wait quietly";
            Goal.Earliest = static_cast<MikdashCrowd::Seconds>(Index * 4); Goal.Duration = 30;
            Plan.Goals.push_back(Goal);
            MikdashCrowd::Route Route;
            Route.Id = Key + "-route"; Route.From = Plan.Start; Route.To = Goal.Destination;
            Route.Resource = "outer-visitor-pilot"; Route.Capacity = 1; Route.Timeout = 60;
            Routes.push_back(Route);
        }
        Plans.push_back(Plan);
    }
    Crowd = MakeShared<MikdashCrowd::Runtime>();
    if (!Crowd->Configure(Plans, Routes)) { Crowd.Reset(); return false; }
    Walking.Init(false, 5);
    TWeakObjectPtr<AMikdashResidentPopulation> WeakOwner(this);
    for (int32 Index = 0; Index < 5; ++Index)
    {
        const FString StableId(UTF8_TO_TCHAR(Plans[Index].Id.c_str()));
        if (!Bodies[Index]->BindResident(Crowd, StableId,
            [WeakOwner, Index](const FString&, const FVector& From, const FVector& To)
            { return WeakOwner.IsValid() && WeakOwner->ReviewSegment(Index, From, To); }))
        { StopPopulation(); Status = TEXT("Binding failed; stopped; restart world before retry"); return false; }
        Bodies[Index]->AddTickPrerequisiteActor(this);
        Bodies[Index]->GetMesh()->PlayAnimation(IdleAnimation, true);
    }
    bActive = true; Status = TEXT("Pilot bound; collision/nav review may hold residents idle");
    return true;
}

void AMikdashResidentPopulation::SetPopulationPaused(bool Value)
{
    bUserPaused = Value;
    if (Crowd.IsValid()) Crowd->SetPaused(Value || UGameplayStatics::IsGamePaused(this));
}

void AMikdashResidentPopulation::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bActive || !Crowd.IsValid()) return;
    if (!FMath::IsFinite(DeltaSeconds)) { StopPopulation(); Status = TEXT("Nonfinite delta: stopped"); return; }
    const bool Paused = bUserPaused || UGameplayStatics::IsGamePaused(this);
    Crowd->SetPaused(Paused);
    if (Paused) return;
    FractionalSeconds += FMath::Max(0.f, DeltaSeconds);
    const auto Whole = static_cast<MikdashCrowd::Seconds>(FractionalSeconds);
    if (Whole) { Crowd->Advance(Whole); FractionalSeconds -= static_cast<double>(Whole); }
    for (int32 Index = 0; Index < Bodies.Num(); ++Index)
    {
        AMikdashResidentCharacter* Body = Bodies[Index];
        if (!IsValid(Body)) { StopPopulation(); Status = TEXT("Body missing: stopped; reservations retained"); return; }
        const std::string Key(TCHAR_TO_UTF8(*Body->GetResidentId()));
        const MikdashCrowd::Person* Person = Crowd->Find(Key);
        if (!Person) { StopPopulation(); return; }
        const bool Extended = IsExtendedBody(Index);
        FString RouteId = FString(UTF8_TO_TCHAR((Key + "-route").c_str()));
        double CorridorCm = 100.0;
        if (Extended)
        {
            // Current leg from the shared model's goal index; origins/destinations follow it.
            const std::size_t N = LoopPoints.size();
            const MikdashRoute::Leg Leg = MikdashRoute::LegForGoal(Person->GoalIndex, N);
            Origins[Index] = ExtendedRouteWaypoints[static_cast<int32>(Leg.From)];
            Destinations[Index] = ExtendedRouteWaypoints[static_cast<int32>(Leg.To)];
            RouteId = FString(UTF8_TO_TCHAR((Key + "-leg-" + std::to_string(Person->GoalIndex)).c_str()));
            CorridorCm = ExtendedLegCorridorCm;
            // Pause behavior: while attending a goal (or finished), face that waypoint's look target.
            const bool Standing = Person->State == MikdashCrowd::Phase::Working || Person->State == MikdashCrowd::Phase::Complete;
            const std::size_t At = Person->State == MikdashCrowd::Phase::Complete ? 0 : Leg.To;
            Body->SetStandingFacingTarget(ExtendedRouteLookTargets[static_cast<int32>(At)], Standing);
        }
        if (Person->State == MikdashCrowd::Phase::AccessReview || Person->State == MikdashCrowd::Phase::RouteWait)
        {
            const bool Clear = ReviewSegment(Index, Origins[Index], Destinations[Index]);
            Crowd->SetAccess(Key, Clear);
            if (!Clear) Status = FString::Printf(TEXT("%s: physical corridor review blocked (bounds/floor/capsule)"), *Body->GetResidentId());
            if (Clear) Body->RequestReviewedRoute(RouteId, Origins[Index], Destinations[Index], true, CorridorCm);
        }
        // In-place walking is tied to actual velocity, never to an assigned goal alone.
        const bool Moving = Body->GetVelocity().SizeSquared2D() > 25.0;
        if (Moving != Walking[Index])
        {
            Body->GetMesh()->PlayAnimation(Moving ? WalkAnimation.Get() : IdleAnimation.Get(), true);
            Walking[Index] = Moving;
        }
        // StopRequested keeps its reservation. No automatic passage-clear claim.
    }
}

void AMikdashResidentPopulation::StopPopulation()
{
    bActive = false;
    if (Crowd.IsValid()) Crowd->SetPaused(true);
    for (AMikdashResidentCharacter* Body : Bodies)
        if (IsValid(Body)) Body->RequestResidentStop();
}
void AMikdashResidentPopulation::EndPlay(const EEndPlayReason::Type Reason)
{
    StopPopulation();
    Super::EndPlay(Reason);
}
