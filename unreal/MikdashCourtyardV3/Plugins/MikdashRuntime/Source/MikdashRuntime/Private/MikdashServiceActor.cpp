#include "MikdashSceneUnits.h"
#include "MikdashServiceActor.h"
#include "Animation/AnimSequence.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "Components/SceneComponent.h"
#include "Materials/MaterialInterface.h"
#include "Misc/Paths.h"
#include "UObject/SoftObjectPath.h"

using namespace MikdashService;

namespace
{
// Feet-to-capsule geometry copied from the reviewed resident body so the two
// systems agree about what "clear" means. Not a fresh assumption.
constexpr float CapsuleRadius = 34.f;
constexpr float CapsuleHalfHeight = 96.f;
const FVector CapsuleLift(0.0, 0.0, 98.0);
constexpr double FloorProbeCm = 30.0;
constexpr double FloorAgreementCm = 3.0;
constexpr double FloorNormalZ = 0.95;
constexpr double LegSampleCm = 25.0;
constexpr double HeldReviewIntervalSeconds = 1.0;

FVector ToUnreal(const Point3& P) { return FVector(P.X, P.Y, P.Z); }
Point3 ToNative(const FVector& V) { return Point3{V.X, V.Y, V.Z}; }

const TCHAR* RefusalText(Refusal Why)
{
    switch (Why)
    {
    case Refusal::None: return TEXT("no refusal");
    case Refusal::EmptySequence: return TEXT("the sequence has too few stations");
    case Refusal::BadGeometry: return TEXT("a station coordinate or duration is not a usable number");
    case Refusal::CrossesKodeshLine: return TEXT("a station or leg reaches the paroches line at X -5600, which the ordinary-day scenario does not permit");
    case Refusal::OutsideReviewedEnvelope: return TEXT("a station or leg leaves the measured Ulam/doorway/Heikhal floor");
    case Refusal::ScenarioForbidsStation: return TEXT("a station belongs to the Yom Kippur scenario, which is not selected");
    case Refusal::BadFloorHeight: return TEXT("a station is not standing on the reviewed floor or on the three-step stone");
    case Refusal::BadLampGrouping: return TEXT("the two groups of lamps do not account for all seven");
    case Refusal::DurationOutOfWindow: return TEXT("the sequence does not last between the configured minimum and maximum");
    case Refusal::SequenceNotClosed: return TEXT("the sequence does not end where it began, so restarting it would teleport the figure");
    default: return TEXT("the sequence is not configured");
    }
}

// Fallbacks, most preferred first. MetaHumans are looked for on disk before any
// of these; see FindMetaHumanMesh.
const TCHAR* const MeshFallbacks[] = {
    TEXT("/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_Standard.V3_Pilgrim_Man_Standard"),
    TEXT("/Game/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2.PilgrimRigV2"),
};

bool LooksLikeSupportAsset(const FString& Name)
{
    static const TCHAR* const Suffixes[] = {TEXT("_Skeleton"), TEXT("_PhysicsAsset"), TEXT("_AnimBP"),
        TEXT("_Anim"), TEXT("_Skel"), TEXT("_ControlRig"), TEXT("_IK"), TEXT("_Retarget"), TEXT("_LOD")};
    for (const TCHAR* Suffix : Suffixes)
        if (Name.EndsWith(Suffix, ESearchCase::IgnoreCase)) return true;
    return false;
}
}

AMikdashServiceActor::AMikdashServiceActor()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    RootComponent->SetMobility(EComponentMobility::Movable);

    GarmentMaterialSlots = {TEXT("Garment"), TEXT("Robe"), TEXT("Cloth"), TEXT("Body")};
    GarmentFallbacks = {
        // No Kohen Gadol variant exists yet. These are the dressed pilgrim
        // materials already in the project; using one is explicitly recorded as
        // a stand-in, never as the eight golden garments.
        FSoftObjectPath(TEXT("/Game/MikdashV3/Runtime/PeopleV3/Materials/MI_Garment_KohenGadolGold.MI_Garment_KohenGadolGold")),
        FSoftObjectPath(TEXT("/Game/MikdashV3/Runtime/PeopleV3/Materials/MI_Garment_WoolIndigo.MI_Garment_WoolIndigo")),
        FSoftObjectPath(TEXT("/Game/MikdashV3/Runtime/PeopleV3/Materials/MI_Garment_LinenBleached.MI_Garment_LinenBleached")),
    };
}

MikdashService::Scenario AMikdashServiceActor::NativeScenario() const
{
    return ServiceScenario == EMikdashServiceScenario::YomKippur
        ? MikdashService::Scenario::YomKippur : MikdashService::Scenario::OrdinaryDay;
}

void AMikdashServiceActor::BeginPlay()
{
    Super::BeginPlay();
    if (bStartOnBeginPlay && bSequenceEnabled)
    {
        StartService();
    }
    else
    {
        Status = TEXT("Standing by: the sequence is placed but not started. ")
            + GetScenarioDescription();
    }
}

void AMikdashServiceActor::EndPlay(const EEndPlayReason::Type Reason)
{
    StopService();
    if (bBodyWasSpawned && IsValid(Body))
    {
        Body->Destroy();
    }
    Body = nullptr;
    BodyMesh = nullptr;
    bBodyWasSpawned = false;
    Super::EndPlay(Reason);
}

// ---------------------------------------------------------------------------
// The sequence
// ---------------------------------------------------------------------------
bool AMikdashServiceActor::BuildSequence(FString& OutReason)
{
    Anchors A;
    A.UlamApproach = ToNative(UlamApproachPoint);
    A.Doorway = ToNative(DoorwayPoint);
    A.StoneStand = ToNative(TendingStonePoint);
    A.GoldenAltar = ToNative(GoldenAltarPoint);
    A.AltarFace = ToNative(GoldenAltarPoint + FVector(0, 0, 100));
    A.InnerStand = ToNative(InnerStandPoint);
    A.MenorahX = MenorahPoint.X;
    A.MenorahCentreY = MenorahPoint.Y;
    A.LampZ = MenorahPoint.Z + 150.0;

    MikdashSceneUnits::Frame Frame;
    if (!AMikdashSceneUnits::Resolve(GetWorld(), Frame, OutReason)) return false;
    Anchors Decoded;
    if (!DecodeScene(Frame, A, Decoded, SceneGeometry))
    { OutReason = TEXT("Invalid service scene-frame/legacy anchor conversion."); return false; }
    A = Decoded;

    LampSchedule Lamps;
    Lamps.PerLampSeconds = PerLampSeconds;
    DwellTimes Dwell;
    Dwell.ApproachSeconds = ApproachSeconds;
    Dwell.DoorwaySeconds = DoorwaySeconds;
    Dwell.StoneSeconds = StoneSeconds;
    Dwell.KuzSeconds = KuzSeconds;
    Dwell.WithdrawSeconds = WithdrawSeconds;
    Dwell.AltarSeconds = AltarSeconds;
    Dwell.InnerSeconds = InnerSeconds;

    Refusal Why = Refusal::None;
    if (!BuildMenorahSequence(NativeScenario(), A, Lamps, Dwell, Sequence, Why, SceneGeometry))
    {
        OutReason = FString::Printf(TEXT("The sequence could not be built: %s."), RefusalText(Why));
        return false;
    }

    // The Yom Kippur scenario is longer by construction; widen its window
    // rather than pretend the ordinary-day window still describes it.
    double MaxSeconds = MaxLoopSeconds;
    if (NativeScenario() == MikdashService::Scenario::YomKippur)
    {
        MaxSeconds += InnerSeconds + DoorwaySeconds
            + 2.0 * FVector::Dist2D(FVector(SceneGeometry.KodeshLineX, 0, 0), ToUnreal(A.InnerStand)) / FMath::Max(1.f, WalkSpeedCmPerSec);
    }

    if (!Runner.Configure(NativeScenario(), Sequence, WalkSpeedCmPerSec,
            RepeatIntervalSeconds, MinLoopSeconds, MaxSeconds, SceneGeometry))
    {
        OutReason = FString::Printf(
            TEXT("The sequence was refused at station %d: %s. Nothing moved."),
            static_cast<int32>(Runner.RefusedStation()), RefusalText(Runner.Why()));
        return false;
    }
    return true;
}

bool AMikdashServiceActor::StartService()
{
    StopService();
    if (!bSequenceEnabled)
    {
        Status = TEXT("Refused: the sequence switch is off.");
        return false;
    }
    if (!GetWorld())
    {
        Status = TEXT("Refused: there is no world to walk in.");
        return false;
    }

    FString Reason;
    if (!BuildSequence(Reason)) { Status = Reason; return false; }
    if (!ResolveBody(Reason)) { Status = Reason; return false; }

    // Place the body at the first station before the first tick, and only if
    // that placement is itself permitted.
    const FVector Start = ToUnreal(Sequence.Items[0].Stand);
    FString MoveReason;
    if (!MoveIsPermitted(Start, MoveReason))
    {
        Status = FString::Printf(TEXT("Refused before starting: %s"), *MoveReason);
        return false;
    }
    PlaceBody(Start, ToUnreal(Sequence.Items[0].Face));

    bActive = true;
    bPaused = false;
    bLegBlocked = false;
    ReviewedLegIndex = -1;
    NextReviewAtSeconds = 0.0;
    Status = FString::Printf(
        TEXT("Running: %d stations, seven lamps in two groups (five, then two), one loop of %.0f seconds, repeating every %.0f seconds. %s %s"),
        GetStationCount(), GetPlannedLoopSeconds(), RepeatIntervalSeconds,
        *GetScenarioDescription(), *BodyStatus);
    return true;
}

void AMikdashServiceActor::StopService()
{
    if (bActive)
    {
        Status = FString::Printf(TEXT("Stopped after %d completed sequences and %d blocked legs."),
            GetCompletedSequences(), GetBlockedLegCount());
    }
    bActive = false;
    bPaused = false;
    UpdateBodyAnimation(false);
}

void AMikdashServiceActor::SetServicePaused(bool bInPaused)
{
    bPaused = bInPaused;
}

void AMikdashServiceActor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bActive || !Runner.IsReady() || !IsValid(Body)) { UpdateBodyAnimation(false); return; }

    const UWorld* World = GetWorld();
    const double Now = World ? World->GetTimeSeconds() : 0.0;

    // Review the leg we are about to walk, once per leg, and again on a slow
    // cadence while it is held so a door that opens is noticed.
    const Progress& Before = Runner.Where();
    const bool bOnALeg = Before.State == Phase::Walking || Before.State == Phase::Held;
    if (bOnALeg && Before.Index > 0 && Before.Index < Sequence.Count)
    {
        const int32 LegIndex = static_cast<int32>(Before.Index);
        if (LegIndex != ReviewedLegIndex || (bLegBlocked && Now >= NextReviewAtSeconds))
        {
            const FVector From = ToUnreal(Sequence.Items[Before.Index - 1].Stand);
            const FVector To = ToUnreal(Sequence.Items[Before.Index].Stand);
            bLegBlocked = !ReviewLeg(From, To);
            ReviewedLegIndex = LegIndex;
            NextReviewAtSeconds = Now + HeldReviewIntervalSeconds;
        }
    }
    else
    {
        bLegBlocked = false;
        ReviewedLegIndex = -1;
    }

    Runner.Tick(DeltaSeconds, bLegBlocked, bPaused);
    if (bPaused) { UpdateBodyAnimation(false); return; }

    const FVector Stand = ToUnreal(Runner.CurrentStand());
    FString MoveReason;
    if (!MoveIsPermitted(Stand, MoveReason))
    {
        // Defence in depth. The plan was validated before it started, so this
        // cannot normally happen; if it ever does we stop rather than clamp.
        bActive = false;
        UpdateBodyAnimation(false);
        Status = FString::Printf(TEXT("Stopped: %s The figure was left standing where it was."), *MoveReason);
        return;
    }
    const FVector PreviousBodyLocation = Body->GetActorLocation();
    PlaceBody(Stand, ToUnreal(Runner.CurrentFace()));
    UpdateBodyAnimation(FVector::DistSquared(PreviousBodyLocation, Body->GetActorLocation()) > 0.0001);

    if (bLegBlocked)
    {
        Status = FString::Printf(
            TEXT("Holding: the straight leg to station %d is blocked, so the figure is standing still rather than walking through anything. %d legs blocked so far."),
            static_cast<int32>(Runner.Where().Index), GetBlockedLegCount());
    }
}

// ---------------------------------------------------------------------------
// Movement review. Straight legs, capsule swept, no NavMesh in this map.
// ---------------------------------------------------------------------------
bool AMikdashServiceActor::MoveIsPermitted(const FVector& To, FString& OutReason) const
{
    if (To.ContainsNaN())
    {
        OutReason = TEXT("the requested position is not a usable number.");
        return false;
    }
    if (NativeScenario() == MikdashService::Scenario::OrdinaryDay && To.X <= SceneGeometry.KodeshLineX)
    {
        OutReason = FString::Printf(
            TEXT("the ordinary-day scenario does not permit X %.1f, which reaches the paroches line at %.1f; the Kodesh HaKodashim is entered only on Yom Kippur."),
            To.X, SceneGeometry.KodeshLineX);
        return false;
    }
    const Zone Where = ZoneOf(ToNative(To), SceneGeometry);
    if (Where == Zone::Outside)
    {
        OutReason = FString::Printf(TEXT("the position (%.1f, %.1f) is outside the measured Ulam, doorway and Heikhal floor."), To.X, To.Y);
        return false;
    }
    if (!ZonePermitted(NativeScenario(), Where))
    {
        OutReason = TEXT("the position is in a zone this scenario does not permit.");
        return false;
    }
    return true;
}

bool AMikdashServiceActor::ReviewLeg(const FVector& From, const FVector& To) const
{
    const UWorld* World = GetWorld();
    if (!World) return false;

    FCollisionQueryParams Query(SCENE_QUERY_STAT(MikdashServiceLeg), false, this);
    if (IsValid(Body)) Query.AddIgnoredActor(Body);

    // Every sampled foot position must stand on a floor that is where we think
    // it is and flat enough to stand on. A missing trace is never "clear".
    const int32 Samples = FMath::Max<int32>(1, FMath::CeilToInt32(FVector::Distance(From, To) / LegSampleCm));
    for (int32 Step = 0; Step <= Samples; ++Step)
    {
        const FVector Feet = FMath::Lerp(From, To, static_cast<double>(Step) / Samples);
        FHitResult Floor;
        if (!World->LineTraceSingleByChannel(Floor, Feet + FVector(0, 0, FloorProbeCm),
                Feet - FVector(0, 0, FloorProbeCm), ECC_Visibility, Query)
            || !Floor.bBlockingHit
            || FMath::Abs(Floor.ImpactPoint.Z - Feet.Z) > FloorAgreementCm
            || Floor.ImpactNormal.Z < FloorNormalZ)
        {
            return false;
        }
    }

    const FCollisionShape Capsule = FCollisionShape::MakeCapsule(CapsuleRadius, CapsuleHalfHeight);
    if (World->OverlapBlockingTestByChannel(From + CapsuleLift, FQuat::Identity, ECC_Pawn, Capsule, Query)
        || World->OverlapBlockingTestByChannel(To + CapsuleLift, FQuat::Identity, ECC_Pawn, Capsule, Query))
    {
        return false;
    }
    FHitResult Obstacle;
    return !World->SweepSingleByChannel(Obstacle, From + CapsuleLift, To + CapsuleLift,
        FQuat::Identity, ECC_Pawn, Capsule, Query);
}

void AMikdashServiceActor::PlaceBody(const FVector& Feet, const FVector& FaceTarget)
{
    if (!IsValid(Body)) return;
    FRotator Facing = Body->GetActorRotation();
    const FVector Delta = FaceTarget - Feet;
    if (Delta.SizeSquared2D() > 1.0)
    {
        Facing = FRotationMatrix::MakeFromX(FVector(Delta.X, Delta.Y, 0.0)).Rotator();
        Facing.Yaw += ActiveBodyYawDegrees;
    }
    Body->SetActorLocationAndRotation(Feet, Facing, /*bSweep=*/false, nullptr, ETeleportType::None);
}

void AMikdashServiceActor::UpdateBodyAnimation(bool bMoving)
{
    // Authored bodies keep their own animation setup. Switch only on real movement,
    // so a held/paused body never walks in place and clips do not restart each tick.
    if (!bBodyWasSpawned || !IsValid(BodyMesh)) return;
    UAnimSequence* Desired = bMoving && IsValid(WalkAnimation) ? WalkAnimation.Get() : IdleAnimation.Get();
    if (!IsValid(Desired) || Desired == PlayingBodyAnimation) return;
    if (!BodyMesh->GetSkeletalMeshAsset() || Desired->GetSkeleton() != BodyMesh->GetSkeletalMeshAsset()->GetSkeleton()) return;
    BodyMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    BodyMesh->SetAnimation(Desired);
    BodyMesh->Play(true);
    PlayingBodyAnimation = Desired;
}

// ---------------------------------------------------------------------------
// The body: best available at run time, degrading cleanly and recording which.
// ---------------------------------------------------------------------------
USkeletalMesh* AMikdashServiceActor::FindMetaHumanMesh(FString& OutPath) const
{
    // UE 5.8 ships the MetaHuman plugins; another agent may be enabling them
    // and adding characters. Scan the content folder directly so no
    // AssetRegistry module dependency is added to this plugin's build rules.
    const FString Root = FPaths::ProjectContentDir() / TEXT("MetaHumans");
    if (!IFileManager::Get().DirectoryExists(*Root)) return nullptr;

    TArray<FString> Files;
    IFileManager::Get().FindFilesRecursive(Files, *Root, TEXT("*.uasset"), true, false);
    Files.Sort();
    for (const FString& File : Files)
    {
        const FString Name = FPaths::GetBaseFilename(File);
        if (LooksLikeSupportAsset(Name)) continue;
        FString Relative = File;
        FPaths::MakePathRelativeTo(Relative, *FPaths::ProjectContentDir());
        const FString Package = TEXT("/Game/") + FPaths::GetPath(Relative) / Name;
        const FString Object = Package + TEXT(".") + Name;
        if (USkeletalMesh* Found = LoadObject<USkeletalMesh>(nullptr, *Object))
        {
            OutPath = Object;
            return Found;
        }
    }
    return nullptr;
}

USkeletalMesh* AMikdashServiceActor::FindBestMesh(EMikdashServiceBodySource& OutSource, FString& OutPath) const
{
    if (IsValid(ConfiguredMesh))
    {
        OutSource = EMikdashServiceBodySource::ConfiguredMesh;
        OutPath = ConfiguredMesh->GetPathName();
        return ConfiguredMesh;
    }
    FString Path;
    if (USkeletalMesh* Meta = FindMetaHumanMesh(Path))
    {
        OutSource = EMikdashServiceBodySource::MetaHuman;
        OutPath = Path;
        return Meta;
    }
    for (const FSoftObjectPath& Candidate : ExtraMeshCandidates)
    {
        if (Candidate.IsNull()) continue;
        if (USkeletalMesh* Extra = Cast<USkeletalMesh>(Candidate.TryLoad()))
        {
            OutSource = EMikdashServiceBodySource::ConfiguredMesh;
            OutPath = Extra->GetPathName();
            return Extra;
        }
    }
    for (const TCHAR* Fallback : MeshFallbacks)
    {
        if (USkeletalMesh* Rig = LoadObject<USkeletalMesh>(nullptr, Fallback))
        {
            OutSource = FString(Fallback).Contains(TEXT("PilgrimRigV3"))
                ? EMikdashServiceBodySource::PilgrimRigV3 : EMikdashServiceBodySource::PilgrimRigV2;
            OutPath = Rig->GetPathName();
            return Rig;
        }
    }
    OutSource = EMikdashServiceBodySource::NoneAvailable;
    OutPath.Reset();
    return nullptr;
}

bool AMikdashServiceActor::ApplyGarment(USkeletalMeshComponent* Mesh, FString& OutReason)
{
    if (!Mesh) { OutReason = TEXT("no mesh component to dress"); return false; }

    UMaterialInterface* Chosen = IsValid(GarmentMaterial) ? GarmentMaterial.Get() : nullptr;
    if (!Chosen)
    {
        for (const FSoftObjectPath& Candidate : GarmentFallbacks)
        {
            if (Candidate.IsNull()) continue;
            if (UMaterialInterface* Found = Cast<UMaterialInterface>(Candidate.TryLoad()))
            {
                Chosen = Found;
                break;
            }
        }
    }
    if (!Chosen)
    {
        ResolvedGarmentPath.Reset();
        OutReason = TEXT("no garment material was found; the body keeps the mesh's own materials");
        return false;
    }

    int32 Applied = 0, Verified = 0;
    for (const FName& Slot : GarmentMaterialSlots)
    {
        const int32 Index = Mesh->GetMaterialIndex(Slot);
        if (Index < 0) continue;
        // UE 5.8: material setters can report failure even when the assignment
        // took. Never trust the return value; read the slot back instead.
        Mesh->SetMaterial(Index, Chosen);
        ++Applied;
        if (Mesh->GetMaterial(Index) == Chosen) ++Verified;
    }
    ResolvedGarmentPath = Chosen->GetPathName();
    OutReason = FString::Printf(
        TEXT("garment %s applied to %d of %d named slots, %d verified by read-back; %s"),
        *ResolvedGarmentPath, Applied, GarmentMaterialSlots.Num(), Verified,
        TEXT("this is a STAND-IN, not the eight golden garments (see SourceAssets/runtime-review/kohen-service/sources.md)"));
    return Verified > 0;
}

bool AMikdashServiceActor::ResolveBody(FString& OutReason)
{
    if (IsValid(AuthoredBody))
    {
        Body = AuthoredBody;
        ActiveBodyYawDegrees = 0.0f;
        bBodyWasSpawned = false;
        BodySource = EMikdashServiceBodySource::AuthoredActor;
        BodyMesh = Body->FindComponentByClass<USkeletalMeshComponent>();
        ResolvedMeshPath = BodyMesh && BodyMesh->GetSkeletalMeshAsset()
            ? BodyMesh->GetSkeletalMeshAsset()->GetPathName() : FString();
        BodyStatus = FString::Printf(
            TEXT("Body: the authored actor %s already in the map (mesh %s). Its appearance was not changed."),
            *Body->GetName(), ResolvedMeshPath.IsEmpty() ? TEXT("unknown") : *ResolvedMeshPath);
        Body->SetActorEnableCollision(true);
        return true;
    }

    EMikdashServiceBodySource Source = EMikdashServiceBodySource::NotResolved;
    FString Path;
    USkeletalMesh* Mesh = FindBestMesh(Source, Path);
    if (!Mesh)
    {
        BodySource = EMikdashServiceBodySource::NoneAvailable;
        BodyStatus = TEXT("Body: no MetaHuman under /Game/MetaHumans and no PilgrimRigV3 or PilgrimRigV2 could be loaded.");
        OutReason = BodyStatus + TEXT(" The sequence is refused rather than run with an invisible figure.");
        return false;
    }

    UWorld* World = GetWorld();
    if (!World) { OutReason = TEXT("Refused: no world to spawn the body in."); return false; }
    if (!FMath::IsFinite(ConfiguredBodyVisualScale) || ConfiguredBodyVisualScale <= 0.0f || !FMath::IsFinite(ConfiguredBodyYawDegrees))
    { OutReason = TEXT("Refused: invalid physical body scale/facing."); return false; }

    FActorSpawnParameters Params;
    Params.Owner = this;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    ASkeletalMeshActor* Spawned = World->SpawnActor<ASkeletalMeshActor>(
        ASkeletalMeshActor::StaticClass(), GetActorLocation(), GetActorRotation(), Params);
    if (!Spawned) { OutReason = TEXT("Refused: the service body could not be spawned."); return false; }

    // A static-mobility actor does not dirty its package on a transform change
    // and, more to the point here, cannot be walked at all. Movable, always.
    if (USceneComponent* SpawnedRoot = Spawned->GetRootComponent())
    {
        SpawnedRoot->SetMobility(EComponentMobility::Movable);
    }
#if WITH_EDITOR
    Spawned->SetActorLabel(TEXT("RELEASE_KohenGadolService_Body"));
#endif
    Body = Spawned;
    bBodyWasSpawned = true;
    BodySource = Source;
    ResolvedMeshPath = Path;
    FString AnimationResolution;
    if (Source == EMikdashServiceBodySource::PilgrimRigV3)
    {
        // Automatic standard-V3 fallback must not inherit incompatible V2 clips.
        // Compatible authored clips remain intact; explicit mesh/body paths never enter here.
        const FString ClipRoot = TEXT("/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/V3_Pilgrim_Man_Standard/SkeletalMeshes/");
        auto ResolveClip = [&](TObjectPtr<UAnimSequence>& Clip, const TCHAR* ClipName)
        {
            if (IsValid(Clip) && Clip->GetSkeleton() == Mesh->GetSkeleton())
                return FString::Printf(TEXT("retained compatible %s"), *Clip->GetPathName());
            const FString AssetPath = ClipRoot + ClipName + TEXT(".") + ClipName;
            UAnimSequence* Fallback = LoadObject<UAnimSequence>(nullptr, *AssetPath);
            if (IsValid(Fallback) && Fallback->GetSkeleton() == Mesh->GetSkeleton())
            {
                Clip = Fallback;
                return FString::Printf(TEXT("automatic V3 clip %s"), *Fallback->GetPathName());
            }
            Clip = nullptr;
            return FString::Printf(TEXT("MISSING compatible V3 clip %s; animation unavailable"), *AssetPath);
        };
        AnimationResolution = ResolveClip(IdleAnimation, TEXT("V3_Pilgrim_Man_StandardA_Pilgrim_Original_Idle"))
            + TEXT("; ") + ResolveClip(WalkAnimation, TEXT("V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk"));
    }
    ActiveBodyYawDegrees = Source == EMikdashServiceBodySource::ConfiguredMesh ? ConfiguredBodyYawDegrees
        : Source == EMikdashServiceBodySource::PilgrimRigV3 ? -90.0f : 0.0f;
    Spawned->SetActorScale3D(FVector(Source == EMikdashServiceBodySource::ConfiguredMesh ? ConfiguredBodyVisualScale : 1.0f));
    PlayingBodyAnimation = nullptr;

    BodyMesh = Spawned->GetSkeletalMeshComponent();
    if (BodyMesh)
    {
        BodyMesh->SetMobility(EComponentMobility::Movable);
        BodyMesh->SetSkeletalMeshAsset(Mesh);
        BodyMesh->SetCollisionProfileName(TEXT("Pawn"));
        UpdateBodyAnimation(false);
    }

    FString GarmentReason;
    ApplyGarment(BodyMesh, GarmentReason);

    const TCHAR* SourceText =
        Source == EMikdashServiceBodySource::MetaHuman ? TEXT("a MetaHuman found under /Game/MetaHumans")
        : Source == EMikdashServiceBodySource::PilgrimRigV3 ? TEXT("the PilgrimRigV3 skeletal mesh")
        : Source == EMikdashServiceBodySource::ConfiguredMesh ? TEXT("the mesh configured on this actor")
        : TEXT("the PilgrimRigV2 skeletal mesh (no MetaHuman and no V3 rig were available)");
    BodyStatus = FString::Printf(TEXT("Body: %s at %s. Garment: %s."),
        SourceText, *ResolvedMeshPath, *GarmentReason);
    if (!AnimationResolution.IsEmpty()) BodyStatus += TEXT(" Animation: ") + AnimationResolution;
    return true;
}

// ---------------------------------------------------------------------------
// Read-back
// ---------------------------------------------------------------------------
FString AMikdashServiceActor::GetCurrentActionText() const
{
    if (!bActive) return TEXT("The figure is standing still; the lamp service is not running.");
    if (bPaused) return TEXT("Paused. The figure is standing exactly where it was.");
    return FString(Runner.CurrentAction());
}

FString AMikdashServiceActor::GetScenarioDescription() const
{
    if (NativeScenario() == MikdashService::Scenario::YomKippur)
    {
        return TEXT("Scenario: Yom Kippur. This scenario is off by default and was turned on deliberately. ")
            TEXT("It adds only an entry past the paroches and an exit; nothing of that day's inner service is depicted. ")
            TEXT("On any other day the Kohen Gadol does not go beyond the paroches (Vayikra 16:2; Rambam, Biat HaMikdash 2:1).");
    }
    return TEXT("Scenario: an ordinary day. The Kohen Gadol is tending and kindling the menorah lamps in the Heikhal. ")
        TEXT("The daily lamp service is ordinarily an ordinary kohen's, but the Kohen Gadol may perform any service he wishes, ")
        TEXT("and the lamps are named among the services he performs (Mishnah Yoma 1:2, Yoma 14a; Rambam, Klei HaMikdash 5:12). ")
        TEXT("He does not go beyond the paroches at X -5600; that happens only on Yom Kippur, which is a separate scenario here. ")
        TEXT("This is a depiction, not a ruling, and the pacing is authored.");
}

int32 AMikdashServiceActor::GetCurrentLamp() const
{
    return bActive && !bPaused ? Runner.CurrentLamp() : 0;
}

int32 AMikdashServiceActor::GetCompletedSequences() const
{
    return Runner.IsReady() ? static_cast<int32>(Runner.Where().CompletedLoops) : 0;
}

int32 AMikdashServiceActor::GetBlockedLegCount() const
{
    return Runner.IsReady() ? static_cast<int32>(Runner.Where().BlockedLegs) : 0;
}

float AMikdashServiceActor::GetPlannedLoopSeconds() const
{
    return Runner.IsReady() ? static_cast<float>(Runner.LoopSeconds()) : 0.f;
}

int32 AMikdashServiceActor::GetStationCount() const
{
    return static_cast<int32>(Sequence.Count);
}
