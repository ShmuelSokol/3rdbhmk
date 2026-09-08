#include "MikdashGateSecurity.h"
#include "DrawDebugHelpers.h"
#include "Engine/World.h"

namespace
{
EMikdashGateStage ToBlueprintStage(MikdashQueue::EStage S)
{
    switch (S)
    {
    case MikdashQueue::EStage::WaitingAtDetector: return EMikdashGateStage::WaitingAtDetector;
    case MikdashQueue::EStage::AtDetector:        return EMikdashGateStage::AtDetector;
    case MikdashQueue::EStage::WaitingAtBagTable: return EMikdashGateStage::WaitingAtBagTable;
    case MikdashQueue::EStage::AtBagTable:        return EMikdashGateStage::AtBagTable;
    case MikdashQueue::EStage::Cleared:           return EMikdashGateStage::Cleared;
    case MikdashQueue::EStage::Refused:           return EMikdashGateStage::Refused;
    default:                                      return EMikdashGateStage::None;
    }
}
} // namespace

AMikdashGateSecurity::AMikdashGateSecurity()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;
    // Nothing here renders. The arches, tables, stanchions, booth, shoe rack and signs are
    // separate StaticMeshActors placed by Scripts/release_gate_security.py; this actor only
    // publishes where they are and how long the queue is.
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    RootComponent->SetMobility(EComponentMobility::Static);

    // Two guards by default: one beside the arches facing the queue, one at the booth.
    GuardPosts = {FVector(-40.f, -260.f, 0.f), FVector(150.f, 300.f, 0.f)};
    GuardPostFacingYaw = {180.f, 200.f};
}

MikdashQueue::FFlowParams AMikdashGateSecurity::BuildParams() const
{
    MikdashQueue::FFlowParams P;
    P.ArrivalsPerMinute = ArrivalsPerMinute;
    P.MeanServiceSeconds = MeanServiceSeconds;
    P.ServiceJitterSeconds = ServiceJitterSeconds;
    P.BagCheckProbability = BagCheckProbability;
    P.BagCheckSeconds = BagCheckSeconds;
    P.BagCheckJitterSeconds = BagCheckJitterSeconds;
    P.DetectorLanes = DetectorLanes;
    P.BagTables = BagTables;
    P.QueueCapacityPerLane = QueueCapacityPerLane;
    P.BagQueueCapacity = BagQueueCapacity;
    P.FairnessCapSeconds = FairnessCapSeconds;
    return P;
}

void AMikdashGateSecurity::RebuildCheckpoint()
{
    Checkpoint.Configure(BuildParams(), static_cast<uint64>(static_cast<uint32>(RandomSeed)) * 0x9E3779B97F4A7C15ull + 1ull);
    Scan.SweepDegrees = GuardSweepDegrees;
    Scan.PeriodSeconds = GuardSweepPeriodSeconds;
    Scan.DwellFraction = GuardSweepDwellFraction;
    ElapsedSeconds = 0.0;
    ArrivalCarrySeconds = 0.0;
    bConfigured = true;
}

void AMikdashGateSecurity::BeginPlay()
{
    Super::BeginPlay();
    RebuildCheckpoint();
}

#if WITH_EDITOR
void AMikdashGateSecurity::PostEditChangeProperty(FPropertyChangedEvent& Event)
{
    Super::PostEditChangeProperty(Event);
    if (bConfigured)
    {
        RebuildCheckpoint();
    }
}
#endif

void AMikdashGateSecurity::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bConfigured)
    {
        RebuildCheckpoint();
    }
    if (!FMath::IsFinite(DeltaSeconds) || DeltaSeconds <= 0.f)
    {
        return;
    }
    const double Step = FMath::Min<double>(DeltaSeconds, 1.0);   // a hitch must not fast-forward the queue
    ElapsedSeconds += Step;

    if (bSelfDrivenRehearsal)
    {
        // Arrivals are drawn from the same deterministic stream, so a rehearsal run is
        // reproducible. A crowd system that calls RequestToPass itself should turn this off.
        ArrivalCarrySeconds += Step;
        if (ArrivalCarrySeconds >= 0.25)
        {
            const int32 Arrivals = Checkpoint.DrawArrivals(ArrivalCarrySeconds);
            ArrivalCarrySeconds = 0.0;
            for (int32 I = 0; I < Arrivals; ++I)
            {
                Checkpoint.RequestToPass();
            }
        }
    }

    Checkpoint.Advance(Step);

    MikdashQueue::FTicket Waved;
    while (Checkpoint.PopWavedAside(Waved))
    {
        if (OnVisitorWavedAside.IsBound())
        {
            OnVisitorWavedAside.Broadcast(Waved.Id, 0);
        }
    }

    MikdashQueue::FTicket Done;
    while (Checkpoint.PopCleared(Done))
    {
        if (OnVisitorCleared.IsBound())
        {
            OnVisitorCleared.Broadcast(Done.Id, Done.Lane, static_cast<float>(Done.TotalWait()));
        }
    }

#if ENABLE_DRAW_DEBUG
    if (bDrawDebug && GetWorld())
    {
        for (int32 L = 0; L < Checkpoint.GetLaneCount(); ++L)
        {
            const FTransform Arch = GetDetectorTransform(L);
            DrawDebugBox(GetWorld(), Arch.GetLocation() + FVector(0, 0, 110), FVector(20, 55, 110),
                         Arch.GetRotation(), FColor(140, 160, 190), false, -1.f, 0, 2.f);
            for (int32 S = 0; S < Checkpoint.QueueLength(L); ++S)
            {
                DrawDebugCircle(GetWorld(), LocalToWorld(QueueSlotLocal(L, S), 0.f).GetLocation() + FVector(0, 0, 2),
                                26.f, 12, FColor(220, 190, 90), false, -1.f, 0, 1.5f, FVector(1, 0, 0), FVector(0, 1, 0));
            }
        }
        for (int32 B = 0; B < Checkpoint.GetParams().BagTables; ++B)
        {
            DrawDebugBox(GetWorld(), GetBagTableTransform(B).GetLocation() + FVector(0, 0, 45),
                         FVector(90, 35, 45), GetActorQuat(), FColor(190, 150, 110), false, -1.f, 0, 2.f);
        }
        for (int32 G = 0; G < GuardPosts.Num(); ++G)
        {
            const FTransform Post = GetGuardPostTransform(G);
            DrawDebugDirectionalArrow(GetWorld(), Post.GetLocation() + FVector(0, 0, 165),
                                      Post.GetLocation() + FVector(0, 0, 165) + GetGuardLookRotation(G).Vector() * 220.f,
                                      30.f, FColor(120, 210, 140), false, -1.f, 0, 2.f);
        }
    }
#endif
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

FTransform AMikdashGateSecurity::LocalToWorld(const FVector& LocalCm, float LocalYaw) const
{
    const FTransform Actor = GetActorTransform();
    const FQuat Rot = Actor.GetRotation() * FQuat(FRotator(0.f, LocalYaw, 0.f));
    return FTransform(Rot, Actor.TransformPosition(LocalCm), FVector::OneVector);
}

FVector AMikdashGateSecurity::DetectorLocal(int32 Lane) const
{
    const int32 Count = FMath::Max(1, FMath::Min(DetectorLanes, MikdashQueue::MaxLanes));
    const float Centred = (static_cast<float>(Lane) - 0.5f * static_cast<float>(Count - 1)) * LaneSpacingCm;
    return FVector(0.f, Centred, 0.f);
}

FVector AMikdashGateSecurity::QueueSlotLocal(int32 Lane, int32 SlotIndex) const
{
    // Slot 0 stands one pitch back from the arch; the line runs away from the gate (-X).
    const FVector Arch = DetectorLocal(Lane);
    return FVector(Arch.X - QueuePitchCm * static_cast<float>(SlotIndex + 1), Arch.Y, 0.f);
}

FVector AMikdashGateSecurity::BagTableLocal(int32 Index) const
{
    return BagTableOffsetCm + FVector(0.f, BagTableSpacingCm * static_cast<float>(Index), 0.f);
}

FTransform AMikdashGateSecurity::GetDetectorTransform(int32 Lane) const
{
    if (Lane < 0 || Lane >= FMath::Min(DetectorLanes, MikdashQueue::MaxLanes))
    {
        return FTransform::Identity;
    }
    const FTransform Actor = GetActorTransform();
    return FTransform(Actor.GetRotation(), Actor.TransformPosition(DetectorLocal(Lane)), FVector::OneVector);
}

FTransform AMikdashGateSecurity::GetBagTableTransform(int32 Index) const
{
    if (Index < 0 || Index >= FMath::Min(BagTables, MikdashQueue::MaxBagTables))
    {
        return FTransform::Identity;
    }
    const FTransform Actor = GetActorTransform();
    return FTransform(Actor.GetRotation(), Actor.TransformPosition(BagTableLocal(Index)), FVector::OneVector);
}

FTransform AMikdashGateSecurity::GetGuardPostTransform(int32 Index) const
{
    if (!GuardPosts.IsValidIndex(Index))
    {
        return FTransform::Identity;
    }
    const FTransform Actor = GetActorTransform();
    const float Yaw = GuardPostFacingYaw.IsValidIndex(Index) ? GuardPostFacingYaw[Index] : 180.f;
    const FQuat Rot = Actor.GetRotation() * FQuat(FRotator(0.f, Yaw, 0.f));
    return FTransform(Rot, Actor.TransformPosition(GuardPosts[Index]), FVector::OneVector);
}

float AMikdashGateSecurity::GetGuardHeadYawOffset(int32 Index) const
{
    if (!GuardPosts.IsValidIndex(Index))
    {
        return 0.f;
    }
    MikdashQueue::FGuardScan S = Scan;
    // Each post gets its own phase so two guards never sweep in lockstep.
    S.PhaseSeconds = static_cast<double>(Index) * S.PeriodSeconds * 0.37;
    return static_cast<float>(S.YawOffsetAt(ElapsedSeconds));
}

FRotator AMikdashGateSecurity::GetGuardLookRotation(int32 Index) const
{
    const FTransform Post = GetGuardPostTransform(Index);
    FRotator R = Post.GetRotation().Rotator();
    R.Yaw += GetGuardHeadYawOffset(Index);
    return R;
}

// ---------------------------------------------------------------------------
// The public request
// ---------------------------------------------------------------------------

float AMikdashGateSecurity::RequestToPass(FMikdashGatePass& OutPass)
{
    if (!bConfigured)
    {
        RebuildCheckpoint();
    }
    OutPass = FMikdashGatePass();
    const MikdashQueue::FPassGrant G = Checkpoint.RequestToPass();
    OutPass.bAccepted = G.bAccepted;
    OutPass.TicketId = G.TicketId;
    OutPass.Lane = G.Lane;
    OutPass.SlotIndex = G.SlotIndex;
    OutPass.bBagCheck = G.bBagCheck;
    OutPass.EstimatedWaitSeconds = static_cast<float>(G.EstimatedWaitSeconds);
    if (!G.bAccepted)
    {
        OutPass.EstimatedWaitSeconds = -1.f;
        return -1.f;
    }
    const FTransform Actor = GetActorTransform();
    OutPass.StandTransform = FTransform(Actor.GetRotation(),
                                        Actor.TransformPosition(QueueSlotLocal(G.Lane, G.SlotIndex)),
                                        FVector::OneVector);
    return OutPass.EstimatedWaitSeconds;
}

int32 AMikdashGateSecurity::GetQueueLength(int32 Lane) const
{
    return Lane < 0 ? Checkpoint.TotalQueueLength() : Checkpoint.QueueLength(Lane);
}

float AMikdashGateSecurity::GetEstimatedWaitSeconds(bool bAssumeBagCheck) const
{
    return static_cast<float>(Checkpoint.EstimatedWaitSeconds(Checkpoint.ShortestLane(), bAssumeBagCheck));
}

bool AMikdashGateSecurity::GetStandTransform(int32 TicketId, FTransform& OutTransform, EMikdashGateStage& OutStage) const
{
    OutTransform = FTransform::Identity;
    OutStage = EMikdashGateStage::Cleared;
    MikdashQueue::FTicket T;
    int32 Slot = -1;
    if (!Checkpoint.FindTicket(TicketId, T, Slot))
    {
        return false;
    }
    OutStage = ToBlueprintStage(T.Stage);
    const FTransform Actor = GetActorTransform();
    FVector Local;
    switch (T.Stage)
    {
    case MikdashQueue::EStage::WaitingAtDetector:
        Local = QueueSlotLocal(T.Lane, Slot);
        break;
    case MikdashQueue::EStage::AtDetector:
        Local = DetectorLocal(T.Lane);
        break;
    case MikdashQueue::EStage::WaitingAtBagTable:
        // Waiting behind the tables, one pitch apart, on the bag-table side.
        Local = BagTableLocal(0) + FVector(-QueuePitchCm * static_cast<float>(Slot + 1), 0.f, 0.f);
        break;
    case MikdashQueue::EStage::AtBagTable:
        Local = BagTableLocal(0);
        break;
    default:
        Local = DetectorLocal(FMath::Max(0, T.Lane));
        break;
    }
    OutTransform = FTransform(Actor.GetRotation(), Actor.TransformPosition(Local), FVector::OneVector);
    return true;
}

EMikdashGateStage AMikdashGateSecurity::GetPassStage(int32 TicketId) const
{
    MikdashQueue::FTicket T;
    int32 Slot = -1;
    return Checkpoint.FindTicket(TicketId, T, Slot) ? ToBlueprintStage(T.Stage) : EMikdashGateStage::Cleared;
}

int32 AMikdashGateSecurity::GetDetectorLaneCount() const { return Checkpoint.GetLaneCount(); }
int32 AMikdashGateSecurity::GetBagTableCount() const { return Checkpoint.GetParams().BagTables; }
int32 AMikdashGateSecurity::GetServedCount() const { return Checkpoint.ServedCount(); }
int32 AMikdashGateSecurity::GetRefusedCount() const { return Checkpoint.RefusedCount(); }
float AMikdashGateSecurity::GetMeanWaitSeconds() const { return static_cast<float>(Checkpoint.MeanObservedTotalWaitSeconds()); }
float AMikdashGateSecurity::GetLongestWaitSeconds() const { return static_cast<float>(Checkpoint.MaxObservedTotalWaitSeconds()); }

float AMikdashGateSecurity::GetWorstCaseWaitSeconds() const
{
    return static_cast<float>(MikdashQueue::WorstCaseWaitSeconds(Checkpoint.GetParams()));
}

bool AMikdashGateSecurity::IsFair() const
{
    return Checkpoint.FairnessHolds();
}

bool AMikdashGateSecurity::IsFairnessCeilingAchievable() const
{
    return MikdashQueue::CeilingIsAchievable(Checkpoint.GetParams());
}

int32 AMikdashGateSecurity::GetRecommendedQueueCapacity() const
{
    return MikdashQueue::CapacityForCeiling(Checkpoint.GetParams());
}

int32 AMikdashGateSecurity::GetBagLineFullCount() const
{
    return Checkpoint.BagLineFullCount();
}

FString AMikdashGateSecurity::GetFairnessReport() const
{
    const char* Reason = "";
    const bool bOk = Checkpoint.FairnessHolds(Reason);
    return FString::Printf(TEXT("%s served=%d refused=%d meanWait=%.2fs longestWait=%.2fs bound=%.2fs%s%s"),
                           bOk ? TEXT("FAIR") : TEXT("UNFAIR"),
                           Checkpoint.ServedCount(), Checkpoint.RefusedCount(),
                           Checkpoint.MeanObservedTotalWaitSeconds(),
                           Checkpoint.MaxObservedTotalWaitSeconds(),
                           MikdashQueue::WorstCaseWaitSeconds(Checkpoint.GetParams()),
                           bOk ? TEXT("") : TEXT(" reason="), bOk ? TEXT("") : ANSI_TO_TCHAR(Reason));
}

FString AMikdashGateSecurity::GetEffectiveParameterReport() const
{
    const MikdashQueue::FFlowParams& P = Checkpoint.GetParams();
    const double Analytic = MikdashQueue::MeanWaitMMc(P);
    return FString::Printf(TEXT("lanes=%d bagTables=%d capacity=%d bagLine=%d arrivals=%.1f/min "
                                "service=%.2f+-%.2fs bagCheck=%.0f%% at %.2f+-%.2fs utilisation=%.3f "
                                "meanWaitMMc=%s worstCase=%.1fs ceiling=%.1fs ceilingAchievable=%s "
                                "recommendedCapacity=%d"),
                           P.DetectorLanes, P.BagTables, P.QueueCapacityPerLane, P.BagQueueCapacity,
                           P.ArrivalsPerMinute, P.MeanServiceSeconds, P.ServiceJitterSeconds,
                           P.BagCheckProbability * 100.0, P.BagCheckSeconds, P.BagCheckJitterSeconds,
                           MikdashQueue::Utilisation(P),
                           Analytic > 1e9 ? TEXT("saturated") : *FString::Printf(TEXT("%.2fs"), Analytic),
                           MikdashQueue::WorstCaseWaitSeconds(P), P.FairnessCapSeconds,
                           MikdashQueue::CeilingIsAchievable(P) ? TEXT("yes") : TEXT("NO"),
                           MikdashQueue::CapacityForCeiling(P));
}
