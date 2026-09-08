#include "MikdashFXDirector.h"

#include "MikdashServiceActor.h"
#include "PlumeMath.h"

#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Math/RotationMatrix.h"

// Brought in for the free functions; the two names that could collide with an
// engine symbol - Pi and the EstimatedOverdraw that shares its name with a member
// of this class - are written out in full at every use.
using namespace MikdashPlume;

namespace
{
/** The six parameter names every card material exposes. Six, and always the same
 *  six, so Scripts/create_fx_materials.py, Scripts/release_fx.py and this file
 *  cannot drift: a material that is missing one simply ignores the write, and the
 *  release script's readback is what proves the graph actually has them. */
static const FName P_Fade(TEXT("FXFade"));       // 0..1 overall multiplier
static const FName P_Erosion(TEXT("FXErosion")); // 0..1 masked-dissolve threshold
static const FName P_Seed(TEXT("FXSeed"));       // 0..1 per-card UV offset
static const FName P_Age(TEXT("FXAge"));         // 0..1 normalised age
static const FName P_Flicker(TEXT("FXFlicker")); // -1..1 band-limited flicker
static const FName P_VFlip(TEXT("VFlip"));       // 0 or 1

FORCEINLINE FVector ToFVector(const FVec3& V)
{
    return FVector(static_cast<FVector::FReal>(V.X), static_cast<FVector::FReal>(V.Y), static_cast<FVector::FReal>(V.Z));
}

/** Hash lane constants. Distinct per use so two effects never share a stream. */
constexpr uint32 LaneFireX = 0x46495245u;
constexpr uint32 LaneFireY = 0x46495259u;
constexpr uint32 LaneFireScale = 0x4649534Cu;
constexpr uint32 LaneColumnPhase = 0x434F4C50u;
constexpr uint32 LaneColumnSwirl = 0x434F4C53u;
constexpr uint32 LaneEmberAngle = 0x454D4241u;
constexpr uint32 LaneEmberRadius = 0x454D4252u;
constexpr uint32 LaneMoteU = 0x4D4F5455u;
constexpr uint32 LaneMoteV = 0x4D4F5456u;
constexpr uint32 LaneMoteW = 0x4D4F5457u;
constexpr uint32 LaneHaze = 0x48415A45u;

/** The engine plane is 100 x 100 cm at unit scale. */
constexpr double PlaneCm = 100.0;
}

AMikdashFXDirector::AMikdashFXDirector()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;
    // The whole point of this actor is per-frame motion; there is nothing to gain
    // from ticking before the player exists.
    PrimaryActorTick.TickGroup = TG_PostPhysics;

    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);
    SetActorEnableCollision(false);

    // Outer altar. SOURCE CLAIM (Avos 5:5): vertical in any wind.
    AltarProfile.SourceRadiusCm = 250.0;
    AltarProfile.RiseSpeedCmS = 340.0;
    AltarProfile.EntrainmentAlpha = 0.10;
    AltarProfile.MaxRadiusCm = 900.0;
    AltarProfile.MaxHeightCm = 4200.0;
    AltarProfile.bStraightColumnInWind = true;
    AltarProfile.MinOpacity = 0.05;

    // Ketores. Narrow "stafflike" column, Yoma 53a. Indoors, so no wind term.
    KetoresProfile.SourceRadiusCm = 21.0;
    KetoresProfile.RiseSpeedCmS = 150.0;
    KetoresProfile.EntrainmentAlpha = 0.06;
    KetoresProfile.MaxRadiusCm = 180.0;
    KetoresProfile.MaxHeightCm = 1920.0;   // 2925 ceiling - 1004.1667 altar top, rounded down
    KetoresProfile.bStraightColumnInWind = false;
    KetoresProfile.MinOpacity = 0.08;

    HeikhalRoom.SourceZCm = 1004.1666666666667;
    HeikhalRoom.CeilingZCm = 2925.0;
    HeikhalRoom.RoomRadiusCm = 1050.0;
    HeikhalRoom.SpreadTimeConstantS = 7.0;
    HeikhalRoom.FillTimeConstantS = 28.0;
    HeikhalRoom.MaxLayerDepthCm = 950.0;
}

// ---------------------------------------------------------------------------
// construction
// ---------------------------------------------------------------------------

void AMikdashFXDirector::ResolveDefaultAnchors()
{
    // MenorahV4 sits at (-5330, 315.176, 925) with yaw -90, so its local +X maps to
    // world -Y and the seven lamps run north to south (Rambam, Beit HaBechirah 3:8,
    // as recorded in ServiceScheduleMath.h). The local X centres are the
    // photograph-calibrated, deliberately NON-uniform values from
    // SourceAssets/vessels-review/MenorahV4/geometry-manifest.json: the branch radii
    // are 1 : 1.906 : 2.729, not 1 : 2 : 3.
    if (LampFlameCm.Num() != 7 || LampLightCm.Num() != 7)
    {
        const double LocalX[7] = {-45.045, -31.47, -16.5, 0.0, 16.5, 31.47, 45.045};
        const FVector Origin(-5330.0, 315.17599868774414, 925.0);
        // The model is the Institute's display vessel: each bowl carries a lid
        // (local Z 143.745..146.67) and a finial (146.67..150), and has no exposed
        // wick. The flame is therefore authored at the lid crown so that it reads
        // as a lit lamp rather than being buried under gold. That is a modelling
        // compromise, and it is recorded in the release receipt as one.
        const double FlameLocalZ = 146.67;
        const double LightLocalZ = 150.0;
        LampFlameCm.Reset(7);
        LampLightCm.Reset(7);
        for (int32 K = 0; K < 7; ++K)
        {
            LampFlameCm.Add(FVector(Origin.X, Origin.Y - LocalX[K], Origin.Z + FlameLocalZ));
            LampLightCm.Add(FVector(Origin.X, Origin.Y - LocalX[K], Origin.Z + LightLocalZ));
        }
    }

    if (ShaftTransforms.Num() == 0)
    {
        // DESIGN, needs review: the Heikhal window arrangement is not settled in
        // this build, so these are authored anchors and not derived from a window
        // mesh. Three beams from the south wall, angled down and north, which is
        // where a morning sun would put them for a building on this axis.
        const double BeamX[3] = {-3900.0, -4500.0, -5100.0};
        for (int32 K = 0; K < 3; ++K)
        {
            FTransform T;
            T.SetLocation(FVector(BeamX[K], 460.0, 2600.0));
            // The card's local +Y runs down the beam: pitch it down 38 degrees and
            // turn it to face north across the hall.
            T.SetRotation(FRotator(-38.0, -90.0, 0.0).Quaternion());
            // Card mesh is 100 cm square, so this is a beam 160 cm across (local X)
            // and 2200 cm long (local Y). UpdateShaftsAndMotes distributes the motes
            // along local Y for the same reason.
            T.SetScale3D(FVector(1.6, 22.0, 1.0));
            ShaftTransforms.Add(T);
        }
    }

    if (HeatHazeCm.Num() == 0)
    {
        // The first one sits directly over the fire: that is the altar's own heat
        // shimmer, the thing that makes the stone behind the flames wobble. The rest
        // are spread over the open courts, where hot limestone at midday does the
        // same on a larger and much weaker scale. Cards, not a volume.
        HeatHazeCm.Add(FVector(0.0, 0.0, 1420.0));
        HeatHazeCm.Add(FVector(900.0, 0.0, 1030.0));
        HeatHazeCm.Add(FVector(-600.0, 700.0, 1030.0));
        HeatHazeCm.Add(FVector(-600.0, -700.0, 1030.0));
        HeatHazeCm.Add(FVector(1800.0, 0.0, 1060.0));
    }
}

UStaticMeshComponent* AMikdashFXDirector::MakeCard(UMaterialInterface* Source, UMaterialInstanceDynamic*& OutMid, const TCHAR* Label)
{
    OutMid = nullptr;
    if (!CardMesh || !Source)
    {
        return nullptr;
    }
    UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(this, UStaticMeshComponent::StaticClass(), NAME_None, RF_Transient);
    if (!Component)
    {
        return nullptr;
    }
    Component->SetMobility(EComponentMobility::Movable);
    Component->SetupAttachment(Root);
    Component->SetStaticMesh(CardMesh);
    // None of these cards is ever a physical object, a shadow caster or a decal
    // receiver. Left on, a few dozen translucent cards would quietly add a shadow
    // pass and a collision query each, which is exactly the cost this effect set
    // cannot afford on a 2070.
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Component->SetCollisionProfileName(TEXT("NoCollision"));
    Component->SetGenerateOverlapEvents(false);
    Component->SetCastShadow(false);
    Component->bCastDynamicShadow = false;
    Component->bReceivesDecals = false;
    Component->bUseAsOccluder = false;
    Component->SetVisibility(false);
    Component->RegisterComponent();

    OutMid = UMaterialInstanceDynamic::Create(Source, this, FName(Label));
    if (OutMid)
    {
        OutMid->SetScalarParameterValue(P_VFlip, bFlipCardV ? 1.0f : 0.0f);
        Component->SetMaterial(0, OutMid);
        CardMaterials.Add(OutMid);
    }
    CardComponents.Add(Component);
    return Component;
}

UMaterialInterface* AMikdashFXDirector::SourceFor(EGroup Group) const
{
    switch (Group)
    {
    case EGroup::AltarFire:      return FlameAltarMaterial;
    case EGroup::AltarColumn:    return SmokeColumnMaterial;
    case EGroup::AltarEmbers:    return EmberMaterial;
    case EGroup::AltarHaze:      return SmokeHazeMaterial;
    case EGroup::Ketores:        return SmokeKetoresMaterial;
    case EGroup::KetoresCeiling: return SmokeCeilingMaterial;
    case EGroup::LampFlames:     return FlameLampMaterial;
    case EGroup::Shafts:         return LightShaftMaterial;
    case EGroup::Motes:          return DustMoteMaterial;
    case EGroup::HeatHaze:       return HeatHazeMaterial;
    default:                     return nullptr;
    }
}

void AMikdashFXDirector::PlanGroup(EGroup Group, int32 Target, bool bBillboard, bool bCylindrical)
{
    const int32 Index = static_cast<int32>(Group);
    GroupTarget[Index] = SourceFor(Group) ? FMath::Max(0, Target) : 0;
    bGroupBillboard[Index] = bBillboard;
    bGroupCylindrical[Index] = bCylindrical;
    CardPools[Index].Reset(GroupTarget[Index]);
}

int32 AMikdashFXDirector::GrowGroup(EGroup Group, int32 HowMany)
{
    const int32 Index = static_cast<int32>(Group);
    TArray<FCard>& Pool = CardPools[Index];
    UMaterialInterface* Source = SourceFor(Group);
    if (!Source || HowMany <= 0)
    {
        return 0;
    }
    int32 Added = 0;
    while (Pool.Num() < GroupTarget[Index] && Added < HowMany)
    {
        const int32 I = Pool.Num();
        FCard Card;
        Card.Seed = HashCombine3(0x4658u, static_cast<uint32>(Index), static_cast<uint32>(I) + 1u);
        Card.Component = MakeCard(Source, Card.Material, *FString::Printf(TEXT("FX_%d_%d"), Index, I));
        Card.bBillboard = bGroupBillboard[Index];
        Card.bCylindricalBillboard = bGroupCylindrical[Index];
        if (!Card.Component)
        {
            // The mesh or the material is missing. Stop asking; the group is off,
            // and looping to the target would allocate nothing forever.
            GroupTarget[Index] = Pool.Num();
            break;
        }
        if (Card.Material)
        {
            Card.Material->SetScalarParameterValue(P_Seed, static_cast<float>(HashToUnit(Card.Seed, static_cast<uint32>(I), 0x53454544u)));
        }
        Pool.Add(Card);
        ++Added;

        // A shaft card is placed once, here, and never billboarded afterwards: a
        // shaft of light has a direction, and turning it to face the camera is the
        // single most common way this effect goes wrong.
        if (Group == EGroup::Shafts && ShaftTransforms.IsValidIndex(I))
        {
            Pool.Last().Component->SetWorldTransform(ShaftTransforms[I]);
        }
    }
    return Added;
}

int32 AMikdashFXDirector::GrowPools(int32 Budget)
{
    if (bPoolsComplete)
    {
        return 0;
    }
    int32 Added = 0;
    for (int32 G = 0; G < static_cast<int32>(EGroup::Count); ++G)
    {
        if (Added >= Budget)
        {
            break;
        }
        if (CardPools[G].Num() < GroupTarget[G])
        {
            Added += GrowGroup(static_cast<EGroup>(G), Budget - Added);
        }
    }
    // Decide the latch from the state AFTER growing, not before, or a set that just
    // finished would still be swept for one more frame.
    bool bAnyOutstanding = false;
    for (int32 G = 0; G < static_cast<int32>(EGroup::Count); ++G)
    {
        if (CardPools[G].Num() < GroupTarget[G])
        {
            bAnyOutstanding = true;
            break;
        }
    }
    bPoolsComplete = !bAnyOutstanding;
    return Added;
}

void AMikdashFXDirector::BuildLights()
{
    // One fire light. Movable and shadowless: the flicker is the point, and a
    // shadow-casting flickering light on an RTX 2070 costs more than the entire
    // rest of this effect set put together.
    AltarLight = NewObject<UPointLightComponent>(this, UPointLightComponent::StaticClass(), NAME_None, RF_Transient);
    if (AltarLight)
    {
        AltarLight->SetMobility(EComponentMobility::Movable);
        AltarLight->SetupAttachment(Root);
        AltarLight->CastShadows = false;
        AltarLight->bUseTemperature = true;
        AltarLight->SetTemperature(2100.0f);
        AltarLight->SetAttenuationRadius(2600.0f);
        AltarLight->SetIntensity(90.0f);
        AltarLight->SetLightColor(FLinearColor(1.0f, 0.62f, 0.32f));
        AltarLight->RegisterComponent();
        AltarLight->SetWorldLocation(OuterAltarFireCm + FVector(0.0, 0.0, 60.0));
    }

    LampLights.Reset();
    for (int32 K = 0; K < LampLightCm.Num(); ++K)
    {
        UPointLightComponent* Light = NewObject<UPointLightComponent>(this, UPointLightComponent::StaticClass(), NAME_None, RF_Transient);
        if (!Light)
        {
            continue;
        }
        Light->SetMobility(EComponentMobility::Movable);
        Light->SetupAttachment(Root);
        Light->CastShadows = false;
        Light->bUseTemperature = true;
        Light->SetTemperature(1850.0f);
        // A wick flame is a small light, not a lamp fixture. 260 cm of reach and a
        // candela or so: enough to warm the gold beside it and to be seen doing it,
        // not enough to light the hall.
        Light->SetAttenuationRadius(260.0f);
        Light->SetIntensity(1.4f);
        Light->SetLightColor(FLinearColor(1.0f, 0.72f, 0.42f));
        Light->RegisterComponent();
        Light->SetWorldLocation(LampLightCm[K]);
        LampLights.Add(Light);
    }
}

void AMikdashFXDirector::BeginPlay()
{
    Super::BeginPlay();

    ResolveDefaultAnchors();

    KetoresTiming.EmissionSeconds = KetoresEmissionSeconds;
    KetoresTiming.AccumulateSeconds = KetoresAccumulateSeconds;
    KetoresTiming.DissipateSeconds = KetoresDissipateSeconds;

    // The plume math caps the indoor column so it cannot leave the roof; make the
    // anchor agree with whatever ceiling this map actually has, rather than trusting
    // the constructor default.
    HeikhalRoom.CeilingZCm = HeikhalCeilingZCm;
    HeikhalRoom.SourceZCm = GoldenAltarTopCm.Z;
    KetoresProfile.MaxHeightCm = FMath::Max(50.0, HeikhalRoom.CeilingZCm - HeikhalRoom.SourceZCm - 5.0);

    SetWind(WindSpeedCmS, WindDirectionDegrees);

    AltarFlicker.Reset(0x4D495A42u, PuffingFrequencyHz(OuterAltarFireDiameterCm), 4.0);
    for (int32 K = 0; K < 7; ++K)
    {
        // 0.6 cm wick. Design value: no source gives a wick thickness, and the
        // vessel diameter would be the wrong number here because the correlation is
        // in the diameter of the burning region.
        LampFlicker[K].Reset(0x4C414D50u + static_cast<uint32>(K), PuffingFrequencyHz(0.6), 4.5);
    }

    PlanGroup(EGroup::AltarFire, 18, true, true);
    PlanGroup(EGroup::AltarColumn, 14, true, true);
    PlanGroup(EGroup::AltarEmbers, 96, true, false);
    PlanGroup(EGroup::AltarHaze, 6, true, true);
    PlanGroup(EGroup::Ketores, 16, true, true);
    PlanGroup(EGroup::KetoresCeiling, 8, false, false);
    PlanGroup(EGroup::LampFlames, LampFlameCm.Num(), true, true);
    PlanGroup(EGroup::Shafts, ShaftTransforms.Num(), false, false);
    PlanGroup(EGroup::Motes, 120, true, false);
    PlanGroup(EGroup::HeatHaze, HeatHazeCm.Num(), true, true);

    // Build the small, always-visible groups now so the fire and the lamps are lit
    // on the first frame; the ember and mote pools fill over the next few seconds
    // in Tick, where nobody can see them arrive. The counts come from GroupTarget
    // rather than being written out again, so the two can never disagree.
    for (const EGroup Group : {EGroup::AltarFire, EGroup::LampFlames,
                               EGroup::AltarColumn, EGroup::Shafts})
    {
        GrowGroup(Group, GroupTarget[static_cast<int32>(Group)]);
    }

    BuildLights();

    TArray<FString> Missing;
    if (!CardMesh) { Missing.Add(TEXT("CardMesh")); }
    if (!FlameAltarMaterial) { Missing.Add(TEXT("FlameAltarMaterial")); }
    if (!FlameLampMaterial) { Missing.Add(TEXT("FlameLampMaterial")); }
    if (!SmokeColumnMaterial) { Missing.Add(TEXT("SmokeColumnMaterial")); }
    if (!SmokeKetoresMaterial) { Missing.Add(TEXT("SmokeKetoresMaterial")); }
    if (!SmokeCeilingMaterial) { Missing.Add(TEXT("SmokeCeilingMaterial")); }
    if (!SmokeHazeMaterial) { Missing.Add(TEXT("SmokeHazeMaterial")); }
    if (!EmberMaterial) { Missing.Add(TEXT("EmberMaterial")); }
    if (!DustMoteMaterial) { Missing.Add(TEXT("DustMoteMaterial")); }
    if (!LightShaftMaterial) { Missing.Add(TEXT("LightShaftMaterial")); }
    if (!HeatHazeMaterial) { Missing.Add(TEXT("HeatHazeMaterial")); }

    int32 Planned = 0;
    for (int32 G = 0; G < static_cast<int32>(EGroup::Count); ++G)
    {
        Planned += GroupTarget[G];
    }
    Status = Missing.Num() == 0
        ? FString::Printf(TEXT("%d cards planned, %d built on the first frame, %d lamp lights, %d shafts. ")
                          TEXT("Outer altar fire continuous; ketores is an event."),
                          Planned, CardComponents.Num(), LampLights.Num(), GroupTarget[static_cast<int32>(EGroup::Shafts)])
        : FString::Printf(TEXT("%d cards planned; missing assets, those effects are OFF: %s"),
                          Planned, *FString::Join(Missing, TEXT(", ")));
}

void AMikdashFXDirector::EndPlay(const EEndPlayReason::Type Reason)
{
    // "No repeating emitter after its authored end" is an acceptance gate in
    // Research/ketores-service-and-smoke.md. Leaving here counts as an end.
    bKetoresActive = false;
    Super::EndPlay(Reason);
}

// ---------------------------------------------------------------------------
// public control
// ---------------------------------------------------------------------------

void AMikdashFXDirector::SetWind(float SpeedCmS, float DirectionDegrees)
{
    WindSpeedCmS = FMath::Max(0.0f, SpeedCmS);
    WindDirectionDegrees = DirectionDegrees;
    const double Radians = FMath::DegreesToRadians(static_cast<double>(WindDirectionDegrees));
    Wind.DirX = FMath::Cos(Radians);
    Wind.DirY = FMath::Sin(Radians);
    Wind.SpeedCmS = WindSpeedCmS;
}

bool AMikdashFXDirector::BeginKetores()
{
    if (bKetoresActive)
    {
        // A second trigger during an event is ignored, not stacked. Re-entering the
        // room must not restart a running offering.
        return false;
    }
    if (Cards(EGroup::Ketores).Num() == 0)
    {
        // The pools fill over the first few frames, and the ember pool alone can
        // absorb the whole per-frame budget for eight of them. A trigger that
        // arrives inside that window - a level sequence firing on BeginPlay, or
        // release_fx.py calling this and then reading IsKetoresActive() - must not
        // be told there is no effect. Build the group now instead.
        GrowGroup(EGroup::Ketores, GroupTarget[static_cast<int32>(EGroup::Ketores)]);
        GrowGroup(EGroup::KetoresCeiling, GroupTarget[static_cast<int32>(EGroup::KetoresCeiling)]);
    }
    if (Cards(EGroup::Ketores).Num() == 0)
    {
        // Genuinely nothing to draw with: no material, or no card mesh.
        return false;
    }
    bKetoresActive = true;
    KetoresSeconds = 0.0;
    return true;
}

void AMikdashFXDirector::EndKetores()
{
    bKetoresActive = false;
    KetoresSeconds = 0.0;
    HideFrom(EGroup::Ketores, 0);
    HideFrom(EGroup::KetoresCeiling, 0);
}

FString AMikdashFXDirector::GetKetoresPhaseText() const
{
    if (!bKetoresActive)
    {
        return TEXT("No incense is being offered. The golden altar is not a permanent smoke source.");
    }
    switch (KetoresPhaseAt(KetoresTiming, KetoresProfile, HeikhalRoom, KetoresSeconds))
    {
    case EKetoresPhase::Emitting:
        return TEXT("The incense has just been placed on the coals; the smoke is beginning to rise.");
    case EKetoresPhase::Ascending:
        return TEXT("A narrow column is rising toward the ceiling of the Heikhal.");
    case EKetoresPhase::Accumulating:
        return TEXT("The smoke has reached the ceiling and is spreading and settling downward.");
    case EKetoresPhase::Dissipating:
        return TEXT("The offering is over; what is left is thinning out.");
    default:
        return TEXT("Idle.");
    }
}

FString AMikdashFXDirector::GetSourceNote() const
{
    return TEXT("The fire on the outer altar is continuous (Vayikra 6:6). Its column of smoke is shown rising "
                "straight up whatever the wind does: Avos 5:5 lists that among the miracles of the Mikdash. "
                "That is a depiction of a cited claim, not a physical result, and this project keeps the "
                "ordinary wind-bent behaviour in the same code so the two are never confused. "
                "The incense on the golden altar is an event, not a permanent smoke source: it is offered twice "
                "a day in the Heikhal (Shemos 30:7-8; Rambam, Temidin uMusafin 3:1), and its shape - a narrow "
                "column to the ceiling, then spreading and settling - follows Yoma 53a. The seven lamps burn "
                "olive oil on a wick (Shemos 27:20). Colour, thickness, speed and duration are all artistic "
                "choices; the sources give none of them. Nothing here is a ruling.");
}

void AMikdashFXDirector::SetHeatHazeStrength(float Strength01)
{
    HeatHazeStrength = FMath::Clamp(Strength01, 0.0f, 1.0f);
}

void AMikdashFXDirector::SetEffectsQuality(float Scale01)
{
    EffectsQuality = FMath::Clamp(Scale01, 0.0f, 1.0f);
}

TMap<FString, float> AMikdashFXDirector::GetNumericReadback() const
{
    TMap<FString, float> Out;
    Out.Add(TEXT("outerAltarFireX"), static_cast<float>(OuterAltarFireCm.X));
    Out.Add(TEXT("outerAltarFireY"), static_cast<float>(OuterAltarFireCm.Y));
    Out.Add(TEXT("outerAltarFireZ"), static_cast<float>(OuterAltarFireCm.Z));
    Out.Add(TEXT("outerAltarFireDiameterCm"), OuterAltarFireDiameterCm);
    Out.Add(TEXT("outerAltarPuffingHz"), static_cast<float>(PuffingFrequencyHz(OuterAltarFireDiameterCm)));
    Out.Add(TEXT("outerAltarColumnHeightCm"), static_cast<float>(AltarProfile.MaxHeightCm));
    Out.Add(TEXT("outerAltarColumnTopZCm"), static_cast<float>(OuterAltarFireCm.Z + AltarProfile.MaxHeightCm));
    Out.Add(TEXT("outerAltarStraightColumn"), AltarProfile.bStraightColumnInWind ? 1.0f : 0.0f);
    Out.Add(TEXT("outerAltarAxisOffsetAtTopCm"),
            static_cast<float>(PlumeAxisOffsetCm(AltarProfile, AltarProfile.MaxHeightCm, Wind)));
    Out.Add(TEXT("goldenAltarTopZCm"), static_cast<float>(GoldenAltarTopCm.Z));
    Out.Add(TEXT("ketoresColumnHeightCm"), static_cast<float>(KetoresProfile.MaxHeightCm));
    Out.Add(TEXT("ketoresColumnTopZCm"), static_cast<float>(GoldenAltarTopCm.Z + KetoresProfile.MaxHeightCm));
    Out.Add(TEXT("heikhalCeilingZCm"), HeikhalCeilingZCm);
    Out.Add(TEXT("ketoresCeilingClearanceCm"),
            static_cast<float>(HeikhalCeilingZCm - (GoldenAltarTopCm.Z + KetoresProfile.MaxHeightCm)));
    Out.Add(TEXT("ketoresImpingementSeconds"),
            static_cast<float>(CeilingImpingementTimeS(KetoresProfile, HeikhalRoom)));
    Out.Add(TEXT("ketoresEventSeconds"),
            static_cast<float>(CeilingImpingementTimeS(KetoresProfile, HeikhalRoom)
                               + KetoresTiming.AccumulateSeconds + KetoresTiming.DissipateSeconds));
    Out.Add(TEXT("lampCount"), static_cast<float>(LampFlameCm.Num()));
    Out.Add(TEXT("lampPuffingHz"), static_cast<float>(PuffingFrequencyHz(0.6)));
    for (int32 K = 0; K < LampFlameCm.Num(); ++K)
    {
        Out.Add(FString::Printf(TEXT("lamp%dY"), K), static_cast<float>(LampFlameCm[K].Y));
        Out.Add(FString::Printf(TEXT("lamp%dZ"), K), static_cast<float>(LampFlameCm[K].Z));
    }
    Out.Add(TEXT("shaftCount"), static_cast<float>(ShaftTransforms.Num()));
    // cardsBuilt ramps for the first fraction of a second while the pools fill, so
    // a receipt that sampled only that would record a number that depends on when
    // it looked. cardsPlanned is the stable one and is what to compare across runs.
    int32 Planned = 0;
    for (int32 G = 0; G < static_cast<int32>(EGroup::Count); ++G)
    {
        Planned += GroupTarget[G];
    }
    Out.Add(TEXT("cardsPlanned"), static_cast<float>(Planned));
    Out.Add(TEXT("cardsBuilt"), static_cast<float>(CardComponents.Num()));
    Out.Add(TEXT("heatHazeStrength"), HeatHazeStrength);
    Out.Add(TEXT("liveCards"), static_cast<float>(LiveCardCount));
    Out.Add(TEXT("estimatedOverdraw"), EstimatedOverdraw);
    Out.Add(TEXT("effectsQuality"), EffectsQuality);
    return Out;
}

// ---------------------------------------------------------------------------
// per-frame helpers
// ---------------------------------------------------------------------------

void AMikdashFXDirector::PlaceCard(FCard& Card, const FVector& WorldCm, double WidthCm, double HeightCm, const FVector& ViewCm)
{
    if (!Card.Component)
    {
        return;
    }
    FRotator Rotation = Card.Component->GetComponentRotation();
    if (Card.bBillboard)
    {
        FVector ToView = ViewCm - WorldCm;
        if (Card.bCylindricalBillboard)
        {
            // Fire and smoke stay upright. A spherically billboarded smoke column
            // rolls when the camera pitches, and the roll is what makes cheap smoke
            // read as cardboard.
            ToView.Z = 0.0;
        }
        if (!ToView.Normalize())
        {
            ToView = FVector(1.0, 0.0, 0.0);
        }
        // Plane mesh: +Z is its normal, +Y its V axis. Point +Z at the viewer and
        // +Y at the floor, so V = 0 is the top edge of the card, which is the
        // orientation the flame texture is baked for.
        Rotation = FRotationMatrix::MakeFromZY(ToView, FVector(0.0, 0.0, -1.0)).Rotator();
    }
    Card.Component->SetWorldLocationAndRotation(WorldCm, Rotation, false, nullptr, ETeleportType::TeleportPhysics);
    Card.Component->SetWorldScale3D(FVector(WidthCm / PlaneCm, HeightCm / PlaneCm, 1.0));
    Card.Component->SetVisibility(true);
}

void AMikdashFXDirector::HideFrom(EGroup Group, int32 FirstHidden)
{
    TArray<FCard>& Pool = Cards(Group);
    for (int32 I = FMath::Max(0, FirstHidden); I < Pool.Num(); ++I)
    {
        if (Pool[I].Component)
        {
            Pool[I].Component->SetVisibility(false);
        }
    }
}

int32 AMikdashFXDirector::CardsFor(EGroup Group, double Quality, int32 MinCards, int32 MaxCards)
{
    const int32 Available = Cards(Group).Num();
    const int32 Want = CardCountForQuality(Quality * static_cast<double>(EffectsQuality), MinCards, MaxCards);
    const int32 Count = FMath::Clamp(Want, 0, Available);
    LiveCardCount += Count;
    return Count;
}

// ---------------------------------------------------------------------------
// groups
// ---------------------------------------------------------------------------

void AMikdashFXDirector::UpdateAltarFire(double Dt, const FVector& ViewCm, double Quality)
{
    TArray<FCard>& Pool = Cards(EGroup::AltarFire);
    const int32 Count = CardsFor(EGroup::AltarFire, Quality, 6, 18);
    const double Flicker = AltarFlicker.Advance(Dt);
    const double Half = 0.5 * static_cast<double>(OuterAltarFireDiameterCm);

    if (AltarLight)
    {
        // The light and the cards share one flicker stream, so the stone brightens
        // on the same frame the flame does. Two independent flickers would read as
        // two fires.
        AltarLight->SetIntensity(static_cast<float>(90.0 * FlickerMultiplier(Flicker, 0.22)));
        AltarLight->SetVisibility(Count > 0);
    }

    for (int32 I = 0; I < Count; ++I)
    {
        FCard& Card = Pool[I];
        const double Jx = HashToSigned(Card.Seed, static_cast<uint32>(I), LaneFireX) * Half * 0.78;
        const double Jy = HashToSigned(Card.Seed, static_cast<uint32>(I), LaneFireY) * Half * 0.55;
        const double ScaleJitter = 0.62 + 0.55 * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneFireScale);

        // Each card runs its own phase of the same puffing cycle, so the fire has a
        // travelling wave through it rather than pulsing as one block.
        Card.Age += Dt;
        const double CardPhase = static_cast<double>(I) / FMath::Max(1, Count);
        const double Local = FMath::Sin(2.0 * MikdashPlume::Pi * (Card.Age * PuffingFrequencyHz(OuterAltarFireDiameterCm) + CardPhase));
        const double Mult = FlickerMultiplier(0.65 * Flicker + 0.35 * Local, 0.30);

        const double HeightCm = 250.0 * ScaleJitter * Mult;
        const double WidthCm = 190.0 * ScaleJitter;
        PlaceCard(Card, OuterAltarFireCm + FVector(Jx, Jy, HeightCm * 0.45), WidthCm, HeightCm, ViewCm);
        if (Card.Material)
        {
            Card.Material->SetScalarParameterValue(P_Flicker, static_cast<float>(Flicker));
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(EffectsQuality * Quality));
            Card.Material->SetScalarParameterValue(P_Erosion, static_cast<float>(0.30 + 0.25 * HashToUnit(Card.Seed, static_cast<uint32>(I), 0x45524F53u)));
            Card.Material->SetScalarParameterValue(P_Age, static_cast<float>(FMath::Fmod(Card.Age, 4.0) * 0.25));
        }
    }
    HideFrom(EGroup::AltarFire, Count);
}

void AMikdashFXDirector::UpdateAltarColumn(double Dt, const FVector& ViewCm, double Quality)
{
    TArray<FCard>& Pool = Cards(EGroup::AltarColumn);
    const int32 Count = CardsFor(EGroup::AltarColumn, Quality, 4, 14);
    if (Count == 0)
    {
        HideFrom(EGroup::AltarColumn, 0);
        return;
    }
    const double Traverse = FMath::Max(0.5, PlumeTimeToHeightS(AltarProfile, AltarProfile.MaxHeightCm));

    for (int32 I = 0; I < Count; ++I)
    {
        FCard& Card = Pool[I];
        // Cards are spread evenly through one traverse, so the column is a
        // continuous ribbon of puffs rather than a train that visibly repeats.
        Card.Age = FMath::Fmod(Card.Age + Dt, Traverse);
        const double Offset = Traverse * (static_cast<double>(I) / static_cast<double>(Count));
        const double Age = FMath::Fmod(Card.Age + Offset, Traverse);

        // SOURCE CLAIM (Avos 5:5): with bStraightColumnInWind the axis offset this
        // returns is exactly zero at every wind speed, which is what makes the
        // column stand up in a gale. The wind is still passed in; the model, not
        // this call site, is what ignores it.
        const FPlumeSample S = SamplePlumeAtAge(AltarProfile, Age, Wind);
        const FVector World = OuterAltarFireCm + ToFVector(S.AxisOffsetWorldCm);

        // A little swirl so the column is not a perfectly straight tube. This is
        // decoration on the axis, not a bend: it is bounded by a fraction of the
        // local radius, so the card never leaves the tested envelope.
        const double Swirl = 0.22 * S.RadiusCm;
        const double Angle = 2.0 * MikdashPlume::Pi * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneColumnSwirl) + Age * 0.5;
        const FVector Wobble(Swirl * FMath::Cos(Angle), Swirl * FMath::Sin(Angle), 0.0);

        const double WidthCm = 2.0 * S.RadiusCm * 1.15;
        const double HeightCm = WidthCm * 1.05;
        PlaceCard(Card, World + Wobble, WidthCm, HeightCm, ViewCm);
        if (Card.Material)
        {
            const double Age01 = Age / Traverse;
            Card.Material->SetScalarParameterValue(P_Age, static_cast<float>(Age01));
            // Opacity from the top-hat dilution, times a fade at the very top so the
            // column ends rather than being cut off by the draw distance.
            const double EndFade = FMath::Clamp(1.0 - (Age01 - 0.82) / 0.18, 0.0, 1.0);
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(S.Opacity * EndFade * EffectsQuality * Quality));
            Card.Material->SetScalarParameterValue(P_Erosion, static_cast<float>(0.18 + 0.62 * Age01));
            Card.Material->SetScalarParameterValue(P_Flicker, static_cast<float>(HashToSigned(Card.Seed, static_cast<uint32>(I), LaneColumnPhase)));
        }
    }
    HideFrom(EGroup::AltarColumn, Count);
}

void AMikdashFXDirector::UpdateAltarEmbers(double Dt, const FVector& ViewCm, double Quality)
{
    TArray<FCard>& Pool = Cards(EGroup::AltarEmbers);
    const int32 Count = CardsFor(EGroup::AltarEmbers, Quality, 0, 96);
    const double Half = 0.5 * static_cast<double>(OuterAltarFireDiameterCm);

    for (int32 I = 0; I < Count; ++I)
    {
        FCard& Card = Pool[I];
        if (Card.Lifetime <= 0.0)
        {
            Card.Lifetime = EmberLifetimeS(EmberProfile, Card.Seed, static_cast<uint32>(I));
            Card.Age = Card.Lifetime * HashToUnit(Card.Seed, static_cast<uint32>(I), 0x494E4954u);
        }
        Card.Age += Dt;
        if (Card.Age >= Card.Lifetime)
        {
            // Respawn with a fresh draw from the same log-normal, advancing the
            // index so the next life is not a repeat of the last one.
            Card.Seed = HashCombine3(Card.Seed, static_cast<uint32>(I), 0x5245535Eu);
            Card.Lifetime = EmberLifetimeS(EmberProfile, Card.Seed, static_cast<uint32>(I));
            Card.Age = 0.0;
        }

        const double Height = EmberHeightCm(EmberProfile, AltarProfile, Card.Age);
        const double Angle = 2.0 * MikdashPlume::Pi * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneEmberAngle);
        // Embers drift outward as they rise, and the wind does move them: nothing
        // in Avos 5:5 is about sparks.
        const double Radial = Half * 0.55 * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneEmberRadius)
                              + 0.35 * PlumeRadiusCm(AltarProfile, Height);
        double DirX = 1.0, DirY = 0.0;
        NormalisedWindDir(Wind, DirX, DirY);
        const double Drift = 0.20 * Wind.SpeedCmS * Card.Age;
        const FVector World = OuterAltarFireCm
            + FVector(Radial * FMath::Cos(Angle) + DirX * Drift,
                      Radial * FMath::Sin(Angle) + DirY * Drift,
                      Height);

        const double Brightness = EmberBrightness(Card.Age, Card.Lifetime);
        const double SizeCm = 4.0 + 6.0 * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneFireScale);
        PlaceCard(Card, World, SizeCm, SizeCm, ViewCm);
        if (Card.Material)
        {
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(Brightness * EffectsQuality * Quality));
            Card.Material->SetScalarParameterValue(P_Age, static_cast<float>(Card.Age / FMath::Max(1e-3, Card.Lifetime)));
        }
    }
    HideFrom(EGroup::AltarEmbers, Count);
}

void AMikdashFXDirector::UpdateAltarHaze(double Dt, const FVector& ViewCm, double Quality)
{
    TArray<FCard>& Pool = Cards(EGroup::AltarHaze);
    const int32 Count = CardsFor(EGroup::AltarHaze, Quality, 2, 6);
    for (int32 I = 0; I < Count; ++I)
    {
        FCard& Card = Pool[I];
        Card.Age += Dt;
        const double Angle = 2.0 * MikdashPlume::Pi * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneHaze) + Card.Age * 0.05;
        const double R = 300.0 + 420.0 * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneHaze + 1u);
        const FVector World = OuterAltarFireCm
            + FVector(R * FMath::Cos(Angle), R * FMath::Sin(Angle),
                      140.0 + 260.0 * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneHaze + 2u));
        PlaceCard(Card, World, 1500.0, 900.0, ViewCm);
        if (Card.Material)
        {
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(EffectsQuality * Quality));
            Card.Material->SetScalarParameterValue(P_Age, static_cast<float>(FMath::Fmod(Card.Age, 30.0) / 30.0));
        }
    }
    HideFrom(EGroup::AltarHaze, Count);
}

void AMikdashFXDirector::UpdateKetores(double Dt, const FVector& ViewCm, double Quality)
{
    if (!bKetoresActive)
    {
        HideFrom(EGroup::Ketores, 0);
        HideFrom(EGroup::KetoresCeiling, 0);
        return;
    }

    KetoresSeconds += Dt;
    const double Impinge = CeilingImpingementTimeS(KetoresProfile, HeikhalRoom);
    const double End = Impinge + KetoresTiming.AccumulateSeconds + KetoresTiming.DissipateSeconds;
    if (KetoresSeconds > End)
    {
        // The authored end. Nothing keeps running afterwards, which is one of the
        // research document's acceptance gates.
        EndKetores();
        return;
    }

    const double Density = KetoresDensity(KetoresTiming, KetoresProfile, HeikhalRoom, KetoresSeconds);
    const double SinceImpinge = KetoresSeconds - Impinge;

    // ---- the rising column ----
    TArray<FCard>& Column = Cards(EGroup::Ketores);
    const int32 Count = CardsFor(EGroup::Ketores, Quality, 4, 16);
    const double Traverse = FMath::Max(0.5, PlumeTimeToHeightS(KetoresProfile, KetoresProfile.MaxHeightCm));
    for (int32 I = 0; I < Count; ++I)
    {
        FCard& Card = Column[I];
        Card.Age = FMath::Fmod(Card.Age + Dt, Traverse);
        const double Age = FMath::Fmod(Card.Age + Traverse * (static_cast<double>(I) / static_cast<double>(Count)), Traverse);
        const FPlumeSample S = SamplePlumeAtAge(KetoresProfile, Age, FWind());
        const double Height = S.HeightCm;
        // The column must not clip the roof. The profile is already capped, and
        // this is the belt to that pair of braces.
        const double Z = FMath::Min(GoldenAltarTopCm.Z + Height, static_cast<double>(HeikhalCeilingZCm) - 4.0);
        const double WidthCm = 2.0 * S.RadiusCm * 1.2;
        PlaceCard(Card, FVector(GoldenAltarTopCm.X, GoldenAltarTopCm.Y, Z), WidthCm, WidthCm * 1.35, ViewCm);
        if (Card.Material)
        {
            const double Age01 = Age / Traverse;
            Card.Material->SetScalarParameterValue(P_Age, static_cast<float>(Age01));
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(S.Opacity * Density * EffectsQuality * Quality));
            Card.Material->SetScalarParameterValue(P_Erosion, static_cast<float>(0.22 + 0.55 * Age01));
        }
    }
    HideFrom(EGroup::Ketores, Count);

    // ---- the ceiling layer: spreads, then descends ----
    TArray<FCard>& Layer = Cards(EGroup::KetoresCeiling);
    if (SinceImpinge <= 0.0)
    {
        HideFrom(EGroup::KetoresCeiling, 0);
        return;
    }
    const int32 LayerCount = CardsFor(EGroup::KetoresCeiling, Quality, 2, 8);
    const double SpreadR = CeilingSpreadRadiusCm(HeikhalRoom, SinceImpinge);
    const double Depth = CeilingLayerDepthCm(HeikhalRoom, SinceImpinge);
    const double BottomZ = CeilingLayerBottomZCm(HeikhalRoom, SinceImpinge);
    const double Fraction = CeilingSpreadFraction(HeikhalRoom, SinceImpinge);
    for (int32 I = 0; I < LayerCount; ++I)
    {
        FCard& Card = Layer[I];
        Card.Age += Dt;
        // Flat, ceiling-parallel cards: a layer of smoke under a roof is a slab,
        // and billboarding it would turn it into a curtain.
        const double Angle = 2.0 * MikdashPlume::Pi * (static_cast<double>(I) / FMath::Max(1, LayerCount))
                             + 0.05 * Card.Age;
        const double R = SpreadR * (0.25 + 0.6 * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneColumnSwirl));
        const FVector World(GoldenAltarTopCm.X + R * FMath::Cos(Angle),
                            GoldenAltarTopCm.Y + R * FMath::Sin(Angle),
                            FMath::Max(BottomZ, static_cast<double>(HeikhalCeilingZCm) - Depth * 0.5));
        if (Card.Component)
        {
            Card.Component->SetWorldLocationAndRotation(World, FRotator::ZeroRotator, false, nullptr, ETeleportType::TeleportPhysics);
            const double Size = FMath::Max(200.0, SpreadR * 1.1);
            Card.Component->SetWorldScale3D(FVector(Size / PlaneCm, Size / PlaneCm, 1.0));
            Card.Component->SetVisibility(true);
        }
        if (Card.Material)
        {
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(0.55 * Fraction * Density * EffectsQuality * Quality));
            Card.Material->SetScalarParameterValue(P_Age, static_cast<float>(FMath::Clamp(Depth / FMath::Max(1.0, HeikhalRoom.MaxLayerDepthCm), 0.0, 1.0)));
            Card.Material->SetScalarParameterValue(P_Erosion, static_cast<float>(0.35 + 0.4 * (1.0 - Fraction)));
        }
    }
    HideFrom(EGroup::KetoresCeiling, LayerCount);
}

void AMikdashFXDirector::UpdateLamps(double Dt, const FVector& ViewCm, double Quality)
{
    TArray<FCard>& Pool = Cards(EGroup::LampFlames);
    const int32 Count = FMath::Min(Pool.Num(), LampFlameCm.Num());
    // The lamps are never trimmed for budget: seven small cards cost almost nothing
    // and a menorah with four lit lamps would be wrong in a way a frame rate does
    // not justify. They are switched off as a block when quality reaches zero.
    const bool bOn = Quality > 0.0 && EffectsQuality > 0.0;
    LiveCardCount += bOn ? Count : 0;

    for (int32 K = 0; K < Count; ++K)
    {
        FCard& Card = Pool[K];
        if (!bOn)
        {
            if (Card.Component) { Card.Component->SetVisibility(false); }
            if (LampLights.IsValidIndex(K) && LampLights[K]) { LampLights[K]->SetVisibility(false); }
            continue;
        }
        const double Flicker = LampFlicker[K % 7].Advance(Dt);
        const double Mult = FlickerMultiplier(Flicker, 0.32);
        // Wick scale: about 7 cm of flame on a 3 cm base. Anything larger stops
        // reading as an oil lamp and starts reading as a torch.
        const double HeightCm = 7.0 * Mult;
        const double WidthCm = 3.2;
        PlaceCard(Card, LampFlameCm[K] + FVector(0.0, 0.0, HeightCm * 0.5), WidthCm, HeightCm, ViewCm);
        if (Card.Material)
        {
            Card.Material->SetScalarParameterValue(P_Flicker, static_cast<float>(Flicker));
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(EffectsQuality));
            Card.Material->SetScalarParameterValue(P_Erosion, 0.22f);
        }
        if (LampLights.IsValidIndex(K) && LampLights[K])
        {
            LampLights[K]->SetVisibility(true);
            LampLights[K]->SetIntensity(static_cast<float>(1.4 * Mult * EffectsQuality));
        }
    }
    HideFrom(EGroup::LampFlames, bOn ? Count : 0);
}

void AMikdashFXDirector::UpdateShaftsAndMotes(double Dt, const FVector& ViewCm, double Quality)
{
    // ---- the shafts themselves ----
    TArray<FCard>& Shafts = Cards(EGroup::Shafts);
    const int32 ShaftCount = (Quality > 0.0 && EffectsQuality > 0.0) ? Shafts.Num() : 0;
    LiveCardCount += ShaftCount;
    for (int32 I = 0; I < Shafts.Num(); ++I)
    {
        FCard& Card = Shafts[I];
        if (!Card.Component)
        {
            continue;
        }
        if (I >= ShaftCount)
        {
            Card.Component->SetVisibility(false);
            continue;
        }
        Card.Age += Dt;
        Card.Component->SetVisibility(true);
        if (Card.Material)
        {
            // A shaft is only visible when you are looking across it, never along
            // it. The material does the view-angle falloff; this supplies the
            // overall level.
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(EffectsQuality * Quality));
            Card.Material->SetScalarParameterValue(P_Age, static_cast<float>(FMath::Fmod(Card.Age, 60.0) / 60.0));
        }
    }

    // ---- motes, which live only inside the shafts ----
    if (ShaftTransforms.Num() == 0)
    {
        // No beams, no motes. Checked before CardsFor so the budget is not charged
        // for cards that are about to be hidden.
        HideFrom(EGroup::Motes, 0);
        return;
    }
    TArray<FCard>& Motes = Cards(EGroup::Motes);
    const int32 MoteCount = CardsFor(EGroup::Motes, Quality, 0, 120);
    for (int32 I = 0; I < MoteCount; ++I)
    {
        FCard& Card = Motes[I];
        Card.Age += Dt;
        const int32 Beam = static_cast<int32>(HashToUnit(Card.Seed, static_cast<uint32>(I), LaneMoteW) * ShaftTransforms.Num()) % ShaftTransforms.Num();
        const FTransform& T = ShaftTransforms[Beam];
        // Position in the beam's own frame: along it, across it, and a slow drift
        // that wraps. Motes outside the beam would be invisible anyway, and putting
        // them there would only cost fill rate.
        const double Along = FMath::Fmod(HashToUnit(Card.Seed, static_cast<uint32>(I), LaneMoteU) + Card.Age * 0.012, 1.0);
        const double Across = HashToSigned(Card.Seed, static_cast<uint32>(I), LaneMoteV);
        const double Up = HashToSigned(Card.Seed, static_cast<uint32>(I), LaneMoteW + 1u);
        // The plane spans -50..+50 in its own X and Y before scale, so a point is
        // built in UNSCALED card space and TransformPosition applies the beam's
        // width and length for us. Doing the scaling by hand here and then
        // transforming again is the obvious way to get a mote cloud that is
        // twenty-two times too long.
        const FVector Local(Across * 50.0,
                            (Along - 0.5) * PlaneCm,
                            Up * 18.0);
        const FVector World = T.TransformPosition(Local);
        const double SizeCm = 1.6 + 2.2 * HashToUnit(Card.Seed, static_cast<uint32>(I), LaneFireScale);
        PlaceCard(Card, World, SizeCm, SizeCm, ViewCm);
        if (Card.Material)
        {
            // Fade in and out at the ends of the beam so motes do not pop.
            const double Ends = FMath::Min(FMath::Clamp(Along / 0.12, 0.0, 1.0), FMath::Clamp((1.0 - Along) / 0.12, 0.0, 1.0));
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(Ends * EffectsQuality * Quality));
        }
    }
    HideFrom(EGroup::Motes, MoteCount);
}

void AMikdashFXDirector::UpdateHeatHaze(double Dt, const FVector& ViewCm, double Quality)
{
    TArray<FCard>& Pool = Cards(EGroup::HeatHaze);
    const int32 Count = CardsFor(EGroup::HeatHaze, Quality, 2, 5);
    // Card 0 is the fire's own shimmer and is exempt from HeatHazeStrength below,
    // so it has to be exempt from the strength cutoff here too. Cutting the whole
    // group at dawn would take the shimmer off a fire this file documents as
    // continuous (Vayikra 6:6), which is the sort of contradiction that only shows
    // up in a dawn screenshot.
    const int32 Drawn = (HeatHazeStrength <= 0.0f) ? FMath::Min(1, Count) : Count;
    for (int32 I = 0; I < Drawn && I < HeatHazeCm.Num(); ++I)
    {
        FCard& Card = Pool[I];
        Card.Age += Dt;
        // Index 0 is the altar's own shimmer: narrower, taller and much stronger
        // than the court cards, because it sits in the rising column of hot gas
        // rather than over warm paving.
        const bool bAtFire = (I == 0);
        const double WidthCm = bAtFire ? 900.0 : 2400.0;
        const double HeightCm = bAtFire ? 900.0 : 700.0;
        PlaceCard(Card, HeatHazeCm[I], WidthCm, HeightCm, ViewCm);
        if (Card.Material)
        {
            const double Level = (bAtFire ? 1.0 : static_cast<double>(HeatHazeStrength))
                                 * EffectsQuality * Quality;
            Card.Material->SetScalarParameterValue(P_Fade, static_cast<float>(Level));
            Card.Material->SetScalarParameterValue(P_Age, static_cast<float>(FMath::Fmod(Card.Age, 20.0) / 20.0));
        }
    }
    HideFrom(EGroup::HeatHaze, Drawn);
}

void AMikdashFXDirector::PollServiceActor(double Dt)
{
    if (!bFollowServiceActor)
    {
        return;
    }
    if (!ServiceActor.IsValid())
    {
        // A map with no service actor is the normal case until one is placed, and
        // TActorIterator walks the whole level. Once a second is plenty for
        // noticing a figure who takes tens of seconds to walk to the altar.
        SecondsToNextServiceScan -= Dt;
        if (SecondsToNextServiceScan > 0.0)
        {
            return;
        }
        SecondsToNextServiceScan = 1.0;
        if (UWorld* W = GetWorld())
        {
            for (TActorIterator<AMikdashServiceActor> It(W); It; ++It)
            {
                ServiceActor = *It;
                break;
            }
        }
    }
    AMikdashServiceActor* Actor = ServiceActor.Get();
    if (!Actor)
    {
        return;
    }
    // The service actor's own action text at the incense station says in terms that
    // "the smoke itself is not produced here". This is where it is produced. The
    // coupling is one string, held here, so that system never has to know about
    // this one; ServiceIncenseCue is exposed so a text change is a data fix.
    const bool bAtStation = Actor->IsServiceActive() && Actor->GetCurrentActionText().Contains(ServiceIncenseCue);
    if (bAtStation && !bServiceCueLatched)
    {
        // Latched whatever BeginKetores returns, and deliberately so. It now builds
        // its own cards on demand, so the only way it can refuse is a missing
        // material or card mesh - a condition retrying every frame would not fix.
        // Latching only on success would be worse: BeginKetores also refuses while
        // an event is already running, so the plume would restart the instant the
        // previous one ended.
        bServiceCueLatched = true;
        BeginKetores();
    }
    else if (!bAtStation)
    {
        // Latch released when he leaves, so the NEXT visit offers again; the tail of
        // the current event keeps running on its own clock in the meantime.
        bServiceCueLatched = false;
    }
}

// ---------------------------------------------------------------------------

void AMikdashFXDirector::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    // Clamped so a hitch or a breakpoint cannot teleport a plume: the same clamp
    // FFlicker::Advance applies, for the same reason.
    const double Dt = FMath::Clamp(static_cast<double>(DeltaSeconds), 1.0 / 1000.0, 0.25);

    FVector ViewCm = GetActorLocation();
    if (UWorld* W = GetWorld())
    {
        if (APlayerController* PC = W->GetFirstPlayerController())
        {
            FVector Loc;
            FRotator Rot;
            PC->GetPlayerViewPoint(Loc, Rot);
            ViewCm = Loc;
        }
    }

    PollServiceActor(Dt);

    // Fill the rest of the pools a few cards at a time.
    GrowPools(FMath::Max(1, CardsBuiltPerFrame));

    LiveCardCount = 0;

    // Distance quality per anchor, not per actor: the altar can be at full detail
    // while the Heikhal interior is beyond the cutoff, and drawing the indoor
    // effects for a viewer standing in the outer court is pure waste.
    const double QAltar = DistanceQuality(FVector::Dist(ViewCm, OuterAltarFireCm), FullDetailCm, CutoffCm);
    const double QHeikhal = DistanceQuality(FVector::Dist(ViewCm, GoldenAltarTopCm), FullDetailCm, CutoffCm);
    const double QMenorah = LampFlameCm.Num() > 0
        ? DistanceQuality(FVector::Dist(ViewCm, LampFlameCm[LampFlameCm.Num() / 2]), FullDetailCm, CutoffCm)
        : 0.0;

    UpdateAltarFire(Dt, ViewCm, QAltar);
    UpdateAltarColumn(Dt, ViewCm, QAltar);
    UpdateAltarEmbers(Dt, ViewCm, QAltar);
    UpdateAltarHaze(Dt, ViewCm, QAltar);
    UpdateKetores(Dt, ViewCm, QHeikhal);
    UpdateLamps(Dt, ViewCm, QMenorah);
    UpdateShaftsAndMotes(Dt, ViewCm, QHeikhal);
    UpdateHeatHaze(Dt, ViewCm, QAltar);

    // Overdraw estimate. Crude on purpose: a card's screen fraction is taken as its
    // world area over the square of its distance, scaled to a 90 degree field. It is
    // a budget to check a capture against, never a measurement.
    double Overdraw = 0.0;
    for (int32 G = 0; G < static_cast<int32>(EGroup::Count); ++G)
    {
        for (const FCard& Card : CardPools[G])
        {
            if (!Card.Component || !Card.Component->IsVisible())
            {
                continue;
            }
            const FVector Scale = Card.Component->GetComponentScale();
            const double AreaCm2 = Scale.X * Scale.Y * PlaneCm * PlaneCm;
            const double D = FMath::Max(50.0, FVector::Dist(ViewCm, Card.Component->GetComponentLocation()));
            // Qualified: this class has a member called EstimatedOverdraw, and class
            // scope beats the using-directive, so the unqualified name is the float.
            Overdraw += MikdashPlume::EstimatedOverdraw(1, AreaCm2 / (D * D * 2.0));
        }
    }
    EstimatedOverdraw = static_cast<float>(Overdraw);

    // If the frame is over budget, trim quality rather than popping a group out.
    // One-sided: it never raises EffectsQuality back on its own, because that is a
    // user setting and this is a safety valve.
    if (EstimatedOverdraw > OverdrawBudget && EffectsQuality > 0.25f)
    {
        EffectsQuality = FMath::Max(0.25f, EffectsQuality - static_cast<float>(Dt) * 0.5f);
    }
}
