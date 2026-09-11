#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "PlumeMath.h"
#include "MikdashFXDirector.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UPointLightComponent;
class USceneComponent;
class AMikdashServiceActor;

/**
 * ONE actor that owns every fire, smoke, ember, light-shaft and haze effect in the
 * Mikdash scene, and the only place any of them is driven from.
 *
 * WHY ONE ACTOR
 *  - Translucent overdraw is the whole cost of this feature set, and a budget can
 *    only be enforced by something that can see every card at once. Each group asks
 *    for cards, the director hands out what the frame can afford, and
 *    GetEstimatedOverdraw() reports what it spent.
 *  - The shapes come from MikdashPlume (Public/PlumeMath.h), which is engine-free
 *    and covered by a standalone test. Nothing in this file re-derives a plume
 *    radius or a flicker value; it positions components and sets material
 *    parameters from numbers the tested header returned.
 *
 * WHAT IS DEPICTED, AND WHAT IS NOT ASSERTED
 *  - The outer altar's smoke column rises vertically at any wind speed. That is a
 *    depiction of a cited claim (Avos 5:5 lists among the miracles of the Mikdash
 *    that the column of smoke from the arrangement was not dispersed by the wind),
 *    NOT a physical result and NOT an assertion about how smoke behaves. The switch
 *    is FPlumeProfile::bStraightColumnInWind; the physical bent-plume path is kept
 *    live in the header and separately tested, so nothing here quietly conflates
 *    the two. SetWind() still feeds a wind, and the column still ignores it.
 *  - The outer altar fire is continuous (Vayikra 6:6, a perpetual fire that is not
 *    to go out). It is the ONLY continuous fire in the set.
 *  - The ketores plume is an EVENT with a beginning and an end, never a permanent
 *    emitter. Shemos 30:7-8 and Rambam, Temidin uMusafin 3:1 put the incense twice
 *    daily on the Golden Altar in the Heikhal; the research dossier
 *    Research/ketores-service-and-smoke.md says in terms that "regular service" is
 *    not evidence for a visual emitter that runs continuously. Its shape - a
 *    stafflike column to the ceiling, then spreading and descending until the
 *    chamber fills - follows Yoma 53a. Every velocity, depth and duration is a
 *    design value; the sugya gives none.
 *  - The seven lamps burn olive oil on a wick (Shemos 27:20, Vayikra 24:2), so they
 *    are authored at wick scale: a few centimetres, warm, one small light each.
 *    Not torches.
 *  - Colour, opacity, particle size, rise velocity and duration are artistic
 *    choices throughout. None of this is rabbinic approval, and none of it depicts
 *    the incense formula or maaleh ashan's botanical identity.
 *
 * HOW THE KETORES PLUME IS TRIGGERED
 *  AMikdashServiceActor drives the Kohen Gadol and pauses at the golden altar; its
 *  own action text says in terms that "the smoke itself is not produced here". That
 *  actor is not edited by this feature. Instead:
 *    - BeginKetores() / EndKetores() are BlueprintCallable, so a Blueprint, a
 *      sequence or that actor can call them directly; and
 *    - bFollowServiceActor (default true) makes this director find the service actor
 *      and start one event when its current action text reports the golden-altar
 *      station. The coupling therefore lives here, in the effects system, and the
 *      service system stays unaware of it.
 *  Re-entering the room does not restart a finished event, and a second trigger
 *  while an event is running is ignored rather than stacking a second plume.
 */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashFXDirector : public AActor
{
    GENERATED_BODY()

public:
    AMikdashFXDirector();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;

    // ---- assets, all set by Scripts/release_fx.py -------------------------
    /** A unit plane. /Engine/BasicShapes/Plane is what the release script assigns. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UStaticMesh> CardMesh;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> FlameAltarMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> FlameLampMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> SmokeColumnMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> SmokeKetoresMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> SmokeCeilingMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> SmokeHazeMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> EmberMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> DustMoteMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> LightShaftMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Assets")
    TObjectPtr<UMaterialInterface> HeatHazeMaterial;

    // ---- world anchors ----------------------------------------------------
    /** Top of the wood arrangement on the outer altar. Default is
     *  SM_2061..SM_2067 max Z from SourceAssets/architecture-manifest.json. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Anchors")
    FVector OuterAltarFireCm = FVector(0.0, 0.0, 1091.1667);

    /** Half width of the burning wood arrangement, used for card scatter and for
     *  the puffing frequency. SM_2061..SM_2067 span 325 cm in X. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Anchors")
    float OuterAltarFireDiameterCm = 325.0f;

    /** Top plane of the golden altar in the Heikhal. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Anchors")
    FVector GoldenAltarTopCm = FVector(-4650.0, 0.0, 1004.1667);

    /** Underside of SM_0148_roof_Sanctuary_ceiling. The indoor plume stops here;
     *  it must never leave the roof (research dossier, acceptance gates). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Anchors")
    float HeikhalCeilingZCm = 2925.0f;

    /** World positions of the seven lamp flames, north to south. Empty means "work
     *  them out from the MenorahV4 anchors below", which is what a fresh actor does. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Anchors")
    TArray<FVector> LampFlameCm;

    /** Where the seven small lamp lights sit. Same count as LampFlameCm. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Anchors")
    TArray<FVector> LampLightCm;

    /** One transform per light shaft: location at the window, rotation that turns the
     *  card so its local +Y runs down the beam, and scale (width, length, 1) in
     *  hundreds of centimetres, because the card mesh is 100 cm square. The plane's
     *  local Y is its length axis here, not X: that is also the axis the dust motes
     *  are distributed along, so the two must agree. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Anchors")
    TArray<FTransform> ShaftTransforms;

    /** Centres of the heat-haze cards: one directly over the fire, the rest spread
     *  across the courts. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Anchors")
    TArray<FVector> HeatHazeCm;

    /** 0 at dawn, 1 at midday. Heat haze over an open stone court is a midday thing,
     *  and showing it at first light is a tell. This actor does NOT read the clock:
     *  the time-of-day system owns that, and drives this through
     *  SetHeatHazeStrength() so the coupling stays one call in one direction. Left
     *  alone it sits at 1, which is the authored midday look. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash FX|Look", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float HeatHazeStrength = 1.0f;

    UFUNCTION(BlueprintCallable, Category = "Mikdash FX")
    void SetHeatHazeStrength(float Strength01);

    // ---- look and budget --------------------------------------------------
    /** 0 disables every effect; 1 is the authored look. The settings menu drives
     *  this, and the research dossier asks for a reduced-effects option that keeps
     *  the schedule and the source text intact - which it does, because this scales
     *  cards only and never touches the event state machine. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash FX|Budget", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float EffectsQuality = 1.0f;

    /** Beyond this the whole set is at full detail. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Budget", meta = (ClampMin = "1.0"))
    float FullDetailCm = 3000.0f;

    /** Beyond this an effect draws nothing at all. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Budget", meta = (ClampMin = "1.0"))
    float CutoffCm = 24000.0f;

    /** Cards added per frame while the pools fill after BeginPlay. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Budget", meta = (ClampMin = "1"))
    int32 CardsBuiltPerFrame = 12;

    /** Ceiling on the sum of EstimatedOverdraw over every group, in screen areas.
     *  Groups are trimmed from the cheapest-looking end until the sum fits. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Budget", meta = (ClampMin = "0.1"))
    float OverdrawBudget = 3.0f;

    /** The engine plane's V axis runs along its local +Y. If a card's flame ends up
     *  upside down in the editor, flip this instead of rebaking the texture; it
     *  feeds the VFlip scalar on every card material. Recorded as the one
     *  orientation this feature cannot verify without a visual check. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash FX|Look")
    bool bFlipCardV = false;

    // ---- wind -------------------------------------------------------------
    /** Wind speed fed to the plume math. The outer altar column ignores it by
     *  source claim; the haze and the ember drift do not. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash FX")
    void SetWind(float SpeedCmS, float DirectionDegrees);

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Wind", meta = (ClampMin = "0.0"))
    float WindSpeedCmS = 140.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Wind")
    float WindDirectionDegrees = 200.0f;

    // ---- the ketores event ------------------------------------------------
    /** Start one authored ketores event on the golden altar. Returns false, and
     *  changes nothing, if one is already running or the effect has no material.
     *  This is the entry point AMikdashServiceActor's incense station calls. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash FX|Ketores")
    bool BeginKetores();

    /** Stop the current event immediately, leaving no emitter running. Prefer
     *  letting it finish: the authored tail is part of the depiction. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash FX|Ketores")
    void EndKetores();

    UFUNCTION(BlueprintPure, Category = "Mikdash FX|Ketores")
    bool IsKetoresActive() const { return bKetoresActive; }

    UFUNCTION(BlueprintPure, Category = "Mikdash FX|Ketores")
    float GetKetoresSeconds() const { return static_cast<float>(KetoresSeconds); }

    /** Plain language, never a ruling: emitting, ascending, accumulating, tail. */
    UFUNCTION(BlueprintPure, Category = "Mikdash FX|Ketores")
    FString GetKetoresPhaseText() const;

    /** Watch AMikdashServiceActor and start an event when it reaches the golden
     *  altar. Off means the only way in is BeginKetores(). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash FX|Ketores")
    bool bFollowServiceActor = true;

    /** Substring of AMikdashServiceActor::GetCurrentActionText() that means the
     *  figure is at the incense station. Kept as data because that text is owned by
     *  another system and this one must not edit it. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Ketores")
    FString ServiceIncenseCue = TEXT("golden altar for the incense");

    /** Let AMikdashServiceActor decide which lamps burn while its sequence runs: a lamp
     *  is dark until the kohen kindles it at its own station and then burns until the
     *  next sequence (AMikdashServiceActor::IsLampBurning). Off, or with no running
     *  sequence in the map, all seven burn as before. The coupling is read-only and on
     *  this side, like the ketores cue: the service actor never calls this one. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash FX|Lamps")
    bool bLampsFollowService = true;

    /** Seconds a newly kindled flame takes to grow from a spark to full wick size. Design. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Lamps", meta = (ClampMin = "0.0"))
    float LampKindleRampSeconds = 0.8f;

    /** Luminous intensity of ONE lamp's light at full flame, in CANDELAS. An olive-oil
     *  wick is about a candle, and a candle is about 1 cd, so the default is 1.0. It will
     *  not light the hall against the 11,000 cd doorway fill and is not meant to: at the
     *  3-5 cm from the wick to its own lid it gives several hundred lux, a warm local pool
     *  on the gold. (Through cp14 these lights were built UNITLESS - the ULocalLightComponent
     *  constructor default - so the old SetIntensity(1.4) was about 0.002 cd.) */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Lamps", meta = (ClampMin = "0.0"))
    float LampLightCandela = 1.0f;

    /** Radius of the light's emitting sphere: about the width of a wick flame. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Lamps", meta = (ClampMin = "0.0"))
    float LampLightSourceRadiusCm = 0.8f;

    /** EmissiveScale written onto each lamp flame card, overriding MI_FX_Flame_Lamp's 9.
     *  Emissive is scene luminance (cd/m2); a small flame's is of the order of 5,000-10,000
     *  cd/m2, so 9 was about three orders too dark to register against gold lit by daylight
     *  through the doors. This scales the flame's LOOK for visibility and adds no light:
     *  the light stays LampLightCandela. Design value inside the physical range. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Lamps", meta = (ClampMin = "0.0"))
    float LampFlameEmissiveScale = 5000.0f;

    /** How many of the lamp flames are drawn this frame (0..7). */
    UFUNCTION(BlueprintPure, Category = "Mikdash FX|Lamps")
    int32 GetBurningLampCount() const { return BurningLampCount; }

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Ketores", meta = (ClampMin = "0.0"))
    float KetoresEmissionSeconds = 20.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Ketores", meta = (ClampMin = "0.0"))
    float KetoresAccumulateSeconds = 45.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash FX|Ketores", meta = (ClampMin = "0.0"))
    float KetoresDissipateSeconds = 60.0f;

    // ---- read-back --------------------------------------------------------
    UFUNCTION(BlueprintCallable, Category = "Mikdash FX")
    void SetEffectsQuality(float Scale01);

    /** How many cards are being drawn this frame, over every group. */
    UFUNCTION(BlueprintPure, Category = "Mikdash FX")
    int32 GetLiveCardCount() const { return LiveCardCount; }

    /** Sum of the per-group overdraw estimates, in screen areas. A budget, not a
     *  measurement: see MikdashPlume::EstimatedOverdraw. */
    UFUNCTION(BlueprintPure, Category = "Mikdash FX")
    float GetEstimatedOverdraw() const { return EstimatedOverdraw; }

    /** One line: what was built, what was missing, what was refused. */
    UFUNCTION(BlueprintPure, Category = "Mikdash FX")
    FString GetStatus() const { return Status; }

    /** The source register for the prompt and codex systems, as displayed text. */
    UFUNCTION(BlueprintPure, Category = "Mikdash FX")
    FString GetSourceNote() const;

    /** Numeric read-back for Scripts/release_fx.py: every number the release
     *  receipt records comes from here, so the receipt cannot drift from the actor.
     *  Keys are stable; values are the live authored numbers. */
    UFUNCTION(BlueprintPure, Category = "Mikdash FX")
    TMap<FString, float> GetNumericReadback() const;

private:
    /** One drawn card. Plain data: no UPROPERTY on the pointers because the
     *  components are also held in CardComponents, which is where the GC roots
     *  them, and duplicating the reference would only invite them to disagree. */
    struct FCard
    {
        UStaticMeshComponent* Component = nullptr;
        UMaterialInstanceDynamic* Material = nullptr;
        double Age = 0.0;
        /** 0 means "never drawn a lifetime yet". It has to be 0 and not some
         *  plausible-looking 1.0: UpdateAltarEmbers uses `Lifetime <= 0` as the
         *  signal to take the ember's first log-normal draw and give it a random
         *  start age, and a non-zero default silently skips that, which starts all
         *  ninety-six embers on the same frame and respawns them as one ring a
         *  second later. Every consumer already guards against a zero. */
        double Lifetime = 0.0;
        uint32 Seed = 1u;
        bool bCylindricalBillboard = true;
        bool bBillboard = true;
    };

    enum class EGroup : uint8
    {
        AltarFire, AltarColumn, AltarEmbers, AltarHaze,
        Ketores, KetoresCeiling,
        LampFlames, Shafts, Motes, HeatHaze,
        Count
    };

    // ---- construction -----------------------------------------------------
    UStaticMeshComponent* MakeCard(UMaterialInterface* Source, UMaterialInstanceDynamic*& OutMid, const TCHAR* Label);
    /** Which authored material a group draws with. One switch, so the plans below
     *  hold no raw pointer that could outlive the UPROPERTY holding it. */
    UMaterialInterface* SourceFor(EGroup Group) const;
    void PlanGroup(EGroup Group, int32 Target, bool bBillboard, bool bCylindrical);
    /** Append at most HowMany cards to a group, up to its planned target. */
    int32 GrowGroup(EGroup Group, int32 HowMany);
    /** Spread the remaining construction over frames. Returns cards added. */
    int32 GrowPools(int32 Budget);
    void BuildLights();
    void ResolveDefaultAnchors();

    // ---- per-frame --------------------------------------------------------
    void UpdateAltarFire(double Dt, const FVector& ViewCm, double Quality);
    void UpdateAltarColumn(double Dt, const FVector& ViewCm, double Quality);
    void UpdateAltarEmbers(double Dt, const FVector& ViewCm, double Quality);
    void UpdateAltarHaze(double Dt, const FVector& ViewCm, double Quality);
    void UpdateKetores(double Dt, const FVector& ViewCm, double Quality);
    void UpdateLamps(double Dt, const FVector& ViewCm, double Quality);
    void UpdateShaftsAndMotes(double Dt, const FVector& ViewCm, double Quality);
    void UpdateHeatHaze(double Dt, const FVector& ViewCm, double Quality);
    void PollServiceActor(double Dt);

    void PlaceCard(FCard& Card, const FVector& WorldCm, double WidthCm, double HeightCm, const FVector& ViewCm);
    void HideFrom(EGroup Group, int32 FirstHidden);
    int32 CardsFor(EGroup Group, double Quality, int32 MinCards, int32 MaxCards);

    TArray<FCard>& Cards(EGroup Group) { return CardPools[static_cast<int32>(Group)]; }

    // ---- state ------------------------------------------------------------
    UPROPERTY(Transient) TObjectPtr<USceneComponent> Root;
    /** Every card component, in one array so the GC keeps them alive. */
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> CardComponents;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> CardMaterials;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> AltarLight;
    UPROPERTY(Transient) TArray<TObjectPtr<UPointLightComponent>> LampLights;
    UPROPERTY(Transient) TWeakObjectPtr<AMikdashServiceActor> ServiceActor;

    TArray<FCard> CardPools[static_cast<int32>(EGroup::Count)];
    /** How many cards each group wants in the end, and how each one faces. The
     *  pools are filled a few cards per frame rather than all at once: building
     *  every card in BeginPlay means registering close to three hundred scene
     *  components in the frame the level opens, which is one visible hitch at
     *  exactly the moment a visitor is looking around for the first time. */
    int32 GroupTarget[static_cast<int32>(EGroup::Count)] = {};
    bool bGroupBillboard[static_cast<int32>(EGroup::Count)] = {};
    bool bGroupCylindrical[static_cast<int32>(EGroup::Count)] = {};

    MikdashPlume::FPlumeProfile AltarProfile;
    MikdashPlume::FPlumeProfile KetoresProfile;
    MikdashPlume::FCeilingSpread HeikhalRoom;
    MikdashPlume::FEmberProfile EmberProfile;
    MikdashPlume::FKetoresTiming KetoresTiming;
    MikdashPlume::FWind Wind;

    MikdashPlume::FFlicker AltarFlicker;
    MikdashPlume::FFlicker LampFlicker[7];

    bool bKetoresActive = false;
    bool bServiceCueLatched = false;
    /** Set once every group has reached its target, so a filled set stops paying
     *  for the per-frame sweep over all ten groups. */
    bool bPoolsComplete = false;
    /** Seconds until the next sweep for AMikdashServiceActor. Without this the
     *  director walks the whole actor list every frame in any map that has no
     *  service actor, which is every map until one is placed. */
    double SecondsToNextServiceScan = 0.0;
    double KetoresSeconds = 0.0;

    int32 LiveCardCount = 0;
    /** 0 = dark, 1 = full flame, per entry of LampFlameCm; ramps up on kindling. */
    TArray<float> LampKindleLevel;
    int32 BurningLampCount = 7;
    float EstimatedOverdraw = 0.0f;
    FString Status;
};
