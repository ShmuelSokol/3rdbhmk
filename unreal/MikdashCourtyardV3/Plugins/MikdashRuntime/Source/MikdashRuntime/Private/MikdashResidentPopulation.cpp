#include "MikdashResidentPopulation.h"
#include "MikdashResidentCharacter.h"
#include "MikdashSceneUnits.h"
#include "PopulationSceneMath.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include <string>

AMikdashResidentPopulation::AMikdashResidentPopulation()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
    GarmentMaterialSlots.Add(FName(TEXT("Mantle")));
}

void AMikdashResidentPopulation::BeginPlay()
{
    Super::BeginPlay();
    // The two startup paths are mutually exclusive; the authored directory wins and the
    // pilot is refused rather than silently running both against the same actor.
    if (bSpawnAuthoredPeopleOnBeginPlay && bActivateReviewedPilotOnBeginPlay)
    {
        Status = TEXT("Both startup paths were requested; nothing started. Choose one.");
        UE_LOG(LogTemp, Warning, TEXT("%s: %s"), *GetName(), *Status);
        return;
    }
    if (bSpawnAuthoredPeopleOnBeginPlay && !InitializeAuthoredPeople())
    {
        Status = TEXT("Authored people directory startup rejected; population remains stopped");
        UE_LOG(LogTemp, Warning, TEXT("%s: %s (%s)"), *GetName(), *Status, *DirectoryStatus);
    }
    else if (bActivateReviewedPilotOnBeginPlay && !InitializeReviewedPilot())
    {
        Status = TEXT("Authored startup initialization rejected; population remains stopped");
        UE_LOG(LogTemp, Warning, TEXT("%s: %s"), *GetName(), *Status);
    }
}

AMikdashResidentCharacter* AMikdashResidentPopulation::GetResidentAt(int32 Index) const
{
    return ActiveBodies.IsValidIndex(Index) ? ActiveBodies[Index].Get() : nullptr;
}

bool AMikdashResidentPopulation::ResolveCoordinateFrame(FString& Reason)
{
    if(SourceCoordinateRevision!=TEXT("Legacy50.v1"))
    { Reason=TEXT("Resident source coordinates must be explicitly legacy50 input"); return false; }
    return AMikdashSceneUnits::Resolve(GetWorld(),ActiveSceneFrame,Reason);
}

bool AMikdashResidentPopulation::ReviewSegment(int32 BodyIndex, const FVector& From, const FVector& To) const
{
    if (!GetWorld() || !ActiveBodies.IsValidIndex(BodyIndex) || !IsValid(ActiveBodies[BodyIndex])
        || !RoutePlans.IsValidIndex(BodyIndex) || From.ContainsNaN() || To.ContainsNaN()) return false;
    const AMikdashResidentCharacter* Body = ActiveBodies[BodyIndex];
    const FMikdashResidentRoutePlan& Plan = RoutePlans[BodyIndex];
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ResidentPilotReview), true);
    Query.AddIgnoredActor(this); Query.AddIgnoredActor(Body);
    if (Plan.bPilotBox)
    {
        // Convex box plus capsule inset makes the entire straight segment remain in the
        // authored outer visitor region. This is not a general sanctuary access policy.
        MikdashPopulationScene::Rect Box;
        // Original pilot rectangle4700..5300,900..1450 with physical capsule inset34.
        if(!MikdashPopulationScene::TryFootprint(ActiveSceneFrame,{{4700,900,5300,1450},-34,-34},Box)) return false;
        for (const FVector& Point : {From, To})
            if (Point.X < Box.MinX || Point.X > Box.MaxX || Point.Y < Box.MinY || Point.Y > Box.MaxY
                || FMath::Abs(Point.Z - Plan.FloorZ) > 12.0) return false;
    }
    else
    {
        // This body may only walk its own authored loop corridor (150 cm either side),
        // inside the zone it was authored for and on that zone's floor. Not an access policy.
        const MikdashPeople::Zone Where = Plan.bMountDeck ? MikdashPeople::Zone::MountDeck : MikdashPeople::Zone::OuterCourt;
        for (const FVector& Point : {From, To})
            if (!MikdashPopulationScene::PointInZone(ActiveSceneFrame,Where, {Point.X, Point.Y})
                || FMath::Abs(Point.Z - Plan.FloorZ) > MikdashRoute::FloorToleranceCm) return false;
        if (!MikdashRoute::SegmentWithinCorridor({From.X, From.Y}, {To.X, To.Y}, Plan.Loop)) return false;
    }
    // CeilToInt(double) returns int64, so the plain FMath::Max(1, ...) form here relied on an
    // int/int64 deduction that is at best fragile. Spelled out: same sample count, no ambiguity.
    const int32 Samples = FMath::Max<int32>(1, FMath::CeilToInt32(FVector::Distance(From, To) / 25.0));
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

bool AMikdashResidentPopulation::BindConfiguredBodies(const std::vector<MikdashCrowd::Identity>& Plans,
    const std::vector<MikdashCrowd::Route>& Routes)
{
    Crowd = MakeShared<MikdashCrowd::Runtime>();
    if (!Crowd->Configure(Plans, Routes)) { Crowd.Reset(); return false; }
    Walking.Init(false, ActiveBodies.Num());
    ReviewCooldown.Init(0.0, ActiveBodies.Num());
    TWeakObjectPtr<AMikdashResidentPopulation> WeakOwner(this);
    for (int32 Index = 0; Index < ActiveBodies.Num(); ++Index)
    {
        const FString StableId(UTF8_TO_TCHAR(Plans[static_cast<std::size_t>(Index)].Id.c_str()));
        if (!ActiveBodies[Index]->BindResident(Crowd, StableId,
            [WeakOwner, Index](const FString&, const FVector& From, const FVector& To)
            { return WeakOwner.IsValid() && WeakOwner->ReviewSegment(Index, From, To); }))
        { StopPopulation(); Status = TEXT("Binding failed; stopped; restart world before retry"); return false; }
        ActiveBodies[Index]->AddTickPrerequisiteActor(this);
        ActiveBodies[Index]->GetMesh()->PlayAnimation(IdleAnimation, true);
    }
    return true;
}

// ---------------------------------------------------------------------------------------
// The original five-figure reviewed pilot, unchanged in behaviour.
// ---------------------------------------------------------------------------------------
bool AMikdashResidentPopulation::InitializeReviewedPilot()
{
    if (bActive || Crowd.IsValid() || !GetWorld() || !GetWorld()->IsGameWorld()
        || Bodies.Num() != 5 || !IdleAnimation || !WalkAnimation) return false;
    if(!ResolveCoordinateFrame(Status)) return false;
    const FVector LegacyPositions[] = { FVector(4900,1000,300), FVector(5120,1120,300),
        FVector(4980,1260,300), FVector(5240,1330,300), FVector(4760,1180,300) };
    FVector Positions[5];
    for(int32 I=0;I<5;++I)
    {
        MikdashUnits::PointCm P;
        if(!MikdashSceneUnits::TryLegacyTemplePoint(ActiveSceneFrame,
            {LegacyPositions[I].X,LegacyPositions[I].Y,LegacyPositions[I].Z},P)) return false;
        Positions[I]=FVector(P.X,P.Y,P.Z);
    }
    RuntimeExtendedWaypoints.Reset();RuntimeExtendedLookTargets.Reset();
    // Extended loop: validated first because the first leg's review depends on it. An invalid
    // configuration is reported and ignored; the short authored pilot still runs.
    bExtendedRoute = false; LoopPoints.clear();
    if (ExtendedRouteBodyIndex >= 0)
    {
        FString Reason;
        if (ExtendedRouteBodyIndex > 4) Reason = TEXT("body index must be 0..4");
        else if (ValidateExtendedRoute(LegacyPositions[ExtendedRouteBodyIndex], Reason))
        {
            bool ConvertedOkay=true;
            std::vector<double> Pauses;std::vector<std::string> Labels;
            for(int32 I=0;I<ExtendedRouteWaypoints.Num();++I)
            {
                const FVector& Source=ExtendedRouteWaypoints[I];
                const FVector& Look=ExtendedRouteLookTargets[I];
                MikdashUnits::PointCm Point,Target;
                if(!MikdashSceneUnits::TryLegacyTemplePoint(ActiveSceneFrame,{Source.X,Source.Y,Source.Z},Point)
                    || !MikdashPopulationScene::TryLook(ActiveSceneFrame,{Look.X,Look.Y,Look.Z},Target)
                    || !MikdashPopulationScene::PointInZone(ActiveSceneFrame,MikdashPeople::Zone::OuterCourt,{Point.X,Point.Y}))
                { ConvertedOkay=false;Reason=TEXT("Extended route contains unclassified or invalid converted points");break; }
                RuntimeExtendedWaypoints.Add(FVector(Point.X,Point.Y,Point.Z));
                RuntimeExtendedLookTargets.Add(FVector(Target.X,Target.Y,Target.Z));
                LoopPoints.push_back({Point.X,Point.Y});Pauses.push_back(ExtendedRoutePauseSeconds[I]);
                Labels.push_back(TCHAR_TO_UTF8(*ExtendedRouteLabels[I]));
            }
            std::string Why;
            if(ConvertedOkay && !MikdashRoute::ValidateLoopGeometry(LoopPoints,Pauses,Labels,&Why))
            { ConvertedOkay=false;Reason=FString(UTF8_TO_TCHAR(Why.c_str())); }
            bExtendedRoute=ConvertedOkay;
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
    ActiveBodies.Reset(); RoutePlans.Reset(); Origins.Reset(); Destinations.Reset();
    // Reserved up front: FMikdashResidentRoutePlan holds std::vector, and reserving keeps
    // TArray from relocating already-constructed plans while the list is being built.
    ActiveBodies.Reserve(5); RoutePlans.Reserve(5);
    bBodiesWereSpawned = false;
    for (int32 Index = 0; Index < 5; ++Index)
    {
        AMikdashResidentCharacter* Body = Bodies[Index];
        if (!IsValid(Body) || Body->GetWorld() != GetWorld() || Unique.Contains(Body)
            || !Body->GetResidentId().IsEmpty()) { ActiveBodies.Reset(); RoutePlans.Reset(); return false; }
        Unique.Add(Body);
        USkeletalMesh* Mesh = Body->GetMesh()->GetSkeletalMeshAsset();
        if (!Mesh || Mesh->GetSkeleton() != IdleAnimation->GetSkeleton()
            || Mesh->GetSkeleton() != WalkAnimation->GetSkeleton()
            || !Body->GetActorScale3D().Equals(FVector::OneVector, 0.001)
            || FMath::Abs(Body->GetCapsuleComponent()->GetScaledCapsuleRadius()-34.f) > 0.01f
            || FMath::Abs(Body->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-96.f) > 0.01f)
        { ActiveBodies.Reset(); RoutePlans.Reset(); return false; }
        const FVector Feet = Body->GetCharacterMovement()->GetActorFeetLocation();
        if (FVector::Distance(Feet, Positions[Index]) > 3.0) { ActiveBodies.Reset(); RoutePlans.Reset(); return false; }
        ActiveBodies.Add(Body);
        FMikdashResidentRoutePlan Plan;
        Plan.Key = FString::Printf(TEXT("authored-outer-visitor-%02d"), Index + 1);
        Plan.bPilotBox = !IsExtendedBody(Index);
        Plan.bLooping = IsExtendedBody(Index);
        Plan.CorridorCm = IsExtendedBody(Index) ? ExtendedLegCorridorCm : 100.0;
        Plan.FloorZ = Positions[Index].Z;
        if (IsExtendedBody(Index))
        {
            Plan.Waypoints = RuntimeExtendedWaypoints;
            Plan.LookTargets = RuntimeExtendedLookTargets;
            Plan.Loop = LoopPoints;
        }
        RoutePlans.Add(Plan);
        Origins.Add(Positions[Index]);
        // Small individually reviewed route, not repetitive crowd wandering; the extended
        // body's first leg goes to its second authored waypoint instead.
        Destinations.Add(IsExtendedBody(Index) ? RuntimeExtendedWaypoints[1] : Positions[Index] + FVector(Index == 3 ? -80 : 80, 0, 0));
        if (!ReviewSegment(Index, Origins[Index], Destinations[Index]))
        {
            if (!IsExtendedBody(Index)) { ActiveBodies.Reset(); RoutePlans.Reset(); return false; }
            // Physical review of the first leg failed: keep the pilot, drop the extension.
            bExtendedRoute = false; LoopPoints.clear();
            RoutePlans[Index].bPilotBox = true; RoutePlans[Index].bLooping = false;
            RoutePlans[Index].CorridorCm = 100.0; RoutePlans[Index].Loop.clear();
            ExtendedStatus = TEXT("Extended route ignored: first leg failed floor/capsule review at startup");
            UE_LOG(LogTemp, Warning, TEXT("%s: %s"), *GetName(), *ExtendedStatus);
            Destinations[Index] = Positions[Index] + FVector(Index == 3 ? -80 : 80, 0, 0);
            if (!ReviewSegment(Index, Origins[Index], Destinations[Index])) { ActiveBodies.Reset(); RoutePlans.Reset(); return false; }
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
    if (!BindConfiguredBodies(Plans, Routes)) { ActiveBodies.Reset(); RoutePlans.Reset(); return false; }
    bActive = true; Status = TEXT("Pilot bound; collision/nav review may hold residents idle");
    return true;
}

// ---------------------------------------------------------------------------------------
// The staged people directory.
// ---------------------------------------------------------------------------------------
bool AMikdashResidentPopulation::LoadDirectoryText(FString& OutText, FString& OutReason)
{
    TArray<FString> Candidates;
    if (FPaths::IsRelative(PeopleDirectoryFile))
    {
        // Content/Distribution is staged non-UFS by DefaultGame.ini, so the same relative
        // path resolves in the editor and in a packaged build.
        Candidates.Add(FPaths::Combine(FPaths::ProjectContentDir(), PeopleDirectoryFile));
        Candidates.Add(FPaths::Combine(FPaths::ProjectDir(), TEXT("Content"), PeopleDirectoryFile));
    }
    else Candidates.Add(PeopleDirectoryFile);
    for (const FString& Candidate : Candidates)
    {
        const FString Full = FPaths::ConvertRelativePathToFull(Candidate);
        if (!FPaths::FileExists(Full)) continue;
        const int64 Size = IFileManager::Get().FileSize(*Full);
        if (Size <= 0 || Size > 4 * 1024 * 1024)
        { OutReason = FString::Printf(TEXT("directory file size %lld is empty or over 4 MiB: %s"), Size, *Full); return false; }
        if (!FFileHelper::LoadFileToString(OutText, *Full))
        { OutReason = TEXT("directory file could not be read: ") + Full; return false; }
        ResolvedDirectoryPath = Full;
        OutReason.Empty();
        return true;
    }
    OutReason = TEXT("no staged people directory found for '") + PeopleDirectoryFile + TEXT("'");
    return false;
}

UMaterialInterface* AMikdashResidentPopulation::GarmentFor(const FString& VariantKey) const
{
    for (int32 Index = 0; Index < GarmentVariantKeys.Num(); ++Index)
        if (GarmentVariantKeys[Index] == VariantKey && GarmentMaterials.IsValidIndex(Index))
            return GarmentMaterials[Index];
    return nullptr;
}

AMikdashResidentCharacter* AMikdashResidentPopulation::SpawnAuthoredBody(
    const MikdashPeople::Person& Individual, FString& OutReason)
{
    const MikdashPeople::Waypoint& Start = Individual.Route[0];
    const MikdashPeople::Waypoint& Next = Individual.Route[1];
    const FVector Feet(Start.X, Start.Y, Start.Z);
    const double Yaw = MikdashRoute::YawTowardDegrees({Start.X, Start.Y}, {Next.X, Next.Y});
    FActorSpawnParameters Params;
    Params.Owner = this;
    // Refuse rather than nudge: a body pushed off its authored waypoint 0 could not start
    // its own loop, and a body forced into geometry could not walk at all.
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;
    AMikdashResidentCharacter* Body = GetWorld()->SpawnActor<AMikdashResidentCharacter>(
        AMikdashResidentCharacter::StaticClass(), Feet + FVector(0, 0, 96), FRotator(0.0, Yaw, 0.0), Params);
    if (!Body) { OutReason = TEXT("spawn refused: the capsule at waypoint 0 is not clear"); return nullptr; }
    USkeletalMeshComponent* Mesh = Body->GetMesh();
    Mesh->SetSkeletalMeshAsset(ResidentMesh);
    Mesh->SetRelativeLocation(FVector(0, 0, -96));
    Mesh->SetRelativeRotation(FRotator(0, 90, 0));
    Mesh->SetCollisionProfileName(TEXT("NoCollision"));
    Mesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    Body->GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));
    // Garment: one material instance per authored variant key, applied only to the named
    // garment slots. A missing variant or slot leaves the rig's own material in place.
    if (UMaterialInterface* Garment = GarmentFor(FString(UTF8_TO_TCHAR(Individual.Garment.c_str()))))
    {
        int32 Applied = 0;
        for (const FName& Slot : GarmentMaterialSlots)
        {
            const int32 SlotIndex = Mesh->GetMaterialIndex(Slot);
            if (SlotIndex != INDEX_NONE) { Mesh->SetMaterial(SlotIndex, Garment); ++Applied; }
        }
        if (Applied == 0) OutReason = TEXT("garment material found but no named slot matched");
    }
    else OutReason = TEXT("no garment material registered for variant '") + FString(UTF8_TO_TCHAR(Individual.Garment.c_str())) + TEXT("'");
    TArray<FString> Lines;
    for (std::size_t Line = 0; Line < Individual.Dialog.size(); ++Line)
        Lines.Add(FString(UTF8_TO_TCHAR(Individual.Dialog[Line].c_str())));
    Body->SetResidentProfile(FString(UTF8_TO_TCHAR(Individual.Name.c_str())),
        FString(UTF8_TO_TCHAR(Individual.Role.c_str())),
        FString(UTF8_TO_TCHAR(Individual.Mission.c_str())),
        FString(UTF8_TO_TCHAR(Individual.Origin.c_str())),
        FString(UTF8_TO_TCHAR(Individual.Presence.c_str())),
        FString(UTF8_TO_TCHAR(Individual.Garment.c_str())), Lines);
#if WITH_EDITOR
    Body->SetActorLabel(FString(TEXT("Resident_")) + FString(UTF8_TO_TCHAR(Individual.Id.c_str())));
#endif
    return Body;
}

bool AMikdashResidentPopulation::InitializeAuthoredPeople()
{
    if (bActive || Crowd.IsValid() || !GetWorld() || !GetWorld()->IsGameWorld())
    { DirectoryStatus = TEXT("Refused: already active, or not a game world"); return false; }
    if(!ResolveCoordinateFrame(DirectoryStatus)) return false;
    if (!ResidentMesh || !IdleAnimation || !WalkAnimation)
    { DirectoryStatus = TEXT("Refused: resident mesh, idle and walk animations must all be assigned"); return false; }
    if (ResidentMesh->GetSkeleton() != IdleAnimation->GetSkeleton()
        || ResidentMesh->GetSkeleton() != WalkAnimation->GetSkeleton())
    { DirectoryStatus = TEXT("Refused: the animations do not belong to the resident mesh's skeleton"); return false; }
    if (GarmentVariantKeys.Num() != GarmentMaterials.Num())
    { DirectoryStatus = TEXT("Refused: garment variant keys and materials must be the same length"); return false; }

    FString Text, Reason;
    if (!LoadDirectoryText(Text, Reason)) { DirectoryStatus = TEXT("Refused: ") + Reason; return false; }
    MikdashPeople::Directory Directory;
    std::string Why;
    // The same reader and the same rules the standalone tests exercise. An invalid file is
    // refused whole; a partially valid crowd is never assembled.
    if (!MikdashPeople::ReadDirectoryText(std::string(TCHAR_TO_UTF8(*Text)), Directory, Why))
    { DirectoryStatus = TEXT("Refused: ") + FString(UTF8_TO_TCHAR(Why.c_str())); return false; }
    if(ActiveSceneFrame.CoordinateRevision==MikdashSceneUnits::Revision::Selected48V1 && Directory.Version!="people-v3")
    { DirectoryStatus=TEXT("Refused: candidate48 resident adapter only has a scope audit for people-v3");return false; }

    ActiveBodies.Reset(); RoutePlans.Reset(); Origins.Reset(); Destinations.Reset();
    // Reserved up front for the same reason as the pilot path above.
    ActiveBodies.Reserve(static_cast<int32>(Directory.People.size()));
    RoutePlans.Reserve(static_cast<int32>(Directory.People.size()));
    bBodiesWereSpawned = true;
    bExtendedRoute = false; LoopPoints.clear();
    std::vector<MikdashCrowd::Identity> Plans;
    std::vector<MikdashCrowd::Route> Routes;
    TArray<FString> Skipped, Notes;
    for (std::size_t Which = 0; Which < Directory.People.size(); ++Which)
    {
        MikdashPeople::Person Individual;
        if(!MikdashPopulationScene::TryPerson(ActiveSceneFrame,Directory.People[Which],Individual,Why))
        {
            Skipped.Add(FString(UTF8_TO_TCHAR(Directory.People[Which].Id.c_str()))+TEXT(": coordinate/route refusal: ")
                +FString(UTF8_TO_TCHAR(Why.c_str())));
            continue;
        }
        FString SpawnNote;
        AMikdashResidentCharacter* Body = SpawnAuthoredBody(Individual, SpawnNote);
        if (!Body)
        {
            Skipped.Add(FString(UTF8_TO_TCHAR(Individual.Id.c_str())) + TEXT(": ") + SpawnNote);
            continue;
        }
        if (!SpawnNote.IsEmpty()) Notes.Add(FString(UTF8_TO_TCHAR(Individual.Id.c_str())) + TEXT(": ") + SpawnNote);
        const int32 Index = ActiveBodies.Num();
        ActiveBodies.Add(Body);
        FMikdashResidentRoutePlan Plan;
        Plan.Key = FString(UTF8_TO_TCHAR(Individual.Id.c_str()));
        Plan.bLooping = true;
        Plan.bPilotBox = false;
        Plan.bMountDeck = Individual.Where == MikdashPeople::Zone::MountDeck;
        MikdashPopulationScene::TryFloor(ActiveSceneFrame,Individual.Where,Plan.FloorZ);
        Plan.CorridorCm = ExtendedLegCorridorCm;
        for (std::size_t Step = 0; Step < Individual.Route.size(); ++Step)
        {
            const MikdashPeople::Waypoint& W = Individual.Route[Step];
            Plan.Waypoints.Add(FVector(W.X, W.Y, W.Z));
            Plan.LookTargets.Add(FVector(W.LookX, W.LookY, W.LookZ));
            Plan.Loop.push_back({W.X, W.Y});
        }
        RoutePlans.Add(Plan);
        Origins.Add(Plan.Waypoints[0]);
        Destinations.Add(Plan.Waypoints[1]);

        const std::string Key = "authored-person-" + Individual.Id;
        MikdashCrowd::Identity Identity;
        Identity.Id = Key;
        Identity.Name = Individual.Name;
        Identity.Start = Key + "-start";
        // The shared model's SourceRole is a source placement-envelope label this population
        // never consults for authorization, so every body is registered as an ordinary
        // visitor. The authored role lives on the character profile, where it is presentation.
        Identity.Role = MikdashCrowd::SourceRole::Visitor;
        const std::size_t N = Individual.Route.size();
        const MikdashCrowd::Seconds Stagger = static_cast<MikdashCrowd::Seconds>((Which % 12) * 2);
        for (std::size_t Goal = 0; Goal < N * static_cast<std::size_t>(Individual.Laps); ++Goal)
        {
            const MikdashRoute::Leg Leg = MikdashRoute::LegForGoal(Goal, N);
            MikdashCrowd::Goal Step;
            Step.Id = Key + "-goal-" + std::to_string(Goal);
            Step.Label = Individual.Route[Leg.To].Label;
            Step.Destination = std::string(TCHAR_TO_UTF8(*WaypointName(Key, Leg.To)));
            Step.Action = Individual.Route[Leg.To].Action;
            Step.Earliest = Stagger;
            Step.Duration = static_cast<MikdashCrowd::Seconds>(
                FMath::Max(1, FMath::RoundToInt(static_cast<float>(Individual.Route[Leg.To].PauseSeconds))));
            Identity.Goals.push_back(Step);
            MikdashCrowd::Route Leg2;
            Leg2.Id = Key + "-leg-" + std::to_string(Goal);
            Leg2.From = std::string(TCHAR_TO_UTF8(*WaypointName(Key, Leg.From)));
            Leg2.To = Step.Destination;
            // One private resource per person: nobody's loop can ever serialize behind
            // anybody else's, and two bodies that meet resolve it physically by sidestep.
            Leg2.Resource = Key + "-loop";
            Leg2.Capacity = 1; Leg2.Timeout = 180;
            Routes.push_back(Leg2);
        }
        Plans.push_back(Identity);
    }
    if (ActiveBodies.Num() == 0)
    {
        DirectoryStatus = FString::Printf(TEXT("Refused: %d authored people, none could be spawned clear of geometry"),
            static_cast<int32>(Directory.People.size()));
        DestroySpawnedBodies();
        return false;
    }
    if (!BindConfiguredBodies(Plans, Routes))
    {
        DirectoryStatus = TEXT("Refused: the crowd model rejected the assembled configuration");
        DestroySpawnedBodies();
        RoutePlans.Reset(); Origins.Reset(); Destinations.Reset();
        return false;
    }
    bActive = true;
    DirectoryStatus = FString::Printf(TEXT("Directory '%s': %d authored, %d walking, %d skipped, %d notes; file %s"),
        *FString(UTF8_TO_TCHAR(Directory.Version.c_str())), static_cast<int32>(Directory.People.size()),
        ActiveBodies.Num(), Skipped.Num(), Notes.Num(), *ResolvedDirectoryPath);
    for (const FString& Line : Skipped) UE_LOG(LogTemp, Warning, TEXT("%s: skipped %s"), *GetName(), *Line);
    for (const FString& Line : Notes) UE_LOG(LogTemp, Warning, TEXT("%s: note %s"), *GetName(), *Line);
    Status = TEXT("Authored people bound; collision/nav review may hold residents idle");
    UE_LOG(LogTemp, Display, TEXT("%s: %s"), *GetName(), *DirectoryStatus);
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
    for (int32 Index = 0; Index < ActiveBodies.Num(); ++Index)
    {
        AMikdashResidentCharacter* Body = ActiveBodies[Index];
        if (!IsValid(Body)) { StopPopulation(); Status = TEXT("Body missing: stopped; reservations retained"); return; }
        const std::string Key(TCHAR_TO_UTF8(*Body->GetResidentId()));
        const MikdashCrowd::Person* Person = Crowd->Find(Key);
        if (!Person) { StopPopulation(); return; }
        const FMikdashResidentRoutePlan& Plan = RoutePlans[Index];
        FString RouteId = FString(UTF8_TO_TCHAR((Key + "-route").c_str()));
        double CorridorCm = Plan.CorridorCm;
        if (Plan.bLooping)
        {
            // Current leg from the shared model's goal index; origins/destinations follow it.
            const std::size_t N = Plan.Loop.size();
            const MikdashRoute::Leg Leg = MikdashRoute::LegForGoal(Person->GoalIndex, N);
            Origins[Index] = Plan.Waypoints[static_cast<int32>(Leg.From)];
            Destinations[Index] = Plan.Waypoints[static_cast<int32>(Leg.To)];
            RouteId = FString(UTF8_TO_TCHAR((Key + "-leg-" + std::to_string(Person->GoalIndex)).c_str()));
            // Pause behavior: while attending a goal (or finished), face that waypoint's look
            // target. A conversation overrides this: the body faces the walker instead.
            const bool Standing = !Body->IsInConversation()
                && (Person->State == MikdashCrowd::Phase::Working || Person->State == MikdashCrowd::Phase::Complete);
            const std::size_t At = Person->State == MikdashCrowd::Phase::Complete ? 0 : Leg.To;
            Body->SetStandingFacingTarget(Plan.LookTargets[static_cast<int32>(At)], Standing);
        }
        // A body that stopped mid-leg (route timeout, a lost conversation, an interrupted
        // review) keeps its reservation until this owner has confirmed it is physically
        // stopped and its own capsule is clear. Every loop resource is private to one body,
        // so no doorway is being released on anybody else's behalf.
        if (Body->NeedsPassageClearance() && Body->GetVelocity().IsNearlyZero(1.0)
            && !Body->IsInConversation())
        {
            const FVector Feet = Body->GetCharacterMovement()->GetActorFeetLocation();
            if (ReviewSegment(Index, Feet, Feet)) Body->ConfirmPassageCleared(Body->GetRouteToken());
        }
        // Reviewing a whole authored leg costs one floor trace every 25 cm plus a capsule
        // sweep. A body whose corridor is blocked would otherwise pay that on every frame
        // forever, and with two dozen bodies that is the one pathological case. A blocked or
        // refused review is therefore retried four times a second instead of sixty. This
        // delays a retry; it never substitutes for one, and never approves anything.
        const double Now = GetWorld()->GetTimeSeconds();
        if ((Person->State == MikdashCrowd::Phase::AccessReview || Person->State == MikdashCrowd::Phase::RouteWait)
            && Now >= ReviewCooldown[Index])
        {
            const bool Clear = !Body->IsInConversation() && ReviewSegment(Index, Origins[Index], Destinations[Index]);
            Crowd->SetAccess(Key, Clear);
            if (!Clear && !Body->IsInConversation())
                Status = FString::Printf(TEXT("%s: physical corridor review blocked (bounds/floor/capsule)"), *Body->GetResidentId());
            const bool Started = Clear && Body->RequestReviewedRoute(RouteId, Origins[Index], Destinations[Index], true, CorridorCm);
            ReviewCooldown[Index] = Started ? 0.0 : Now + 0.25;
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
    for (AMikdashResidentCharacter* Body : ActiveBodies)
        if (IsValid(Body)) { Body->SetConversationHold(false, FVector::ZeroVector); Body->RequestResidentStop(); }
}

void AMikdashResidentPopulation::DestroySpawnedBodies()
{
    if (!bBodiesWereSpawned) return;
    for (AMikdashResidentCharacter* Body : ActiveBodies)
        if (IsValid(Body)) Body->Destroy();
    ActiveBodies.Reset();
}

void AMikdashResidentPopulation::EndPlay(const EEndPlayReason::Type Reason)
{
    StopPopulation();
    DestroySpawnedBodies();
    Super::EndPlay(Reason);
}
