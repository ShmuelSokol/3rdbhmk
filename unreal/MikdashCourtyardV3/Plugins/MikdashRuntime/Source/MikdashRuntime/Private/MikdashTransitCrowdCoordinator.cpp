#include "MikdashTransitCrowdCoordinator.h"
#include "MikdashCrowdField.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

AMikdashTransitCrowdCoordinator::AMikdashTransitCrowdCoordinator()
{
    PrimaryActorTick.bCanEverTick = true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    WalkInstances = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("TransferWalk"));
    PhotoInstances = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("TransferPhoto"));
    for (UInstancedStaticMeshComponent* Component : {WalkInstances.Get(), PhotoInstances.Get()})
    {
        Component->SetupAttachment(GetRootComponent()); Component->SetMobility(EComponentMobility::Movable);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision); Component->SetCastShadow(false);
        Component->SetCanEverAffectNavigation(false);
    }
}
void AMikdashTransitCrowdCoordinator::BeginPlay()
{
    Super::BeginPlay();
    if (bActivateOnBeginPlay) InitializeCoordinator();
}
bool AMikdashTransitCrowdCoordinator::InitializeCoordinator()
{
    if (bRunning || !GetWorld() || !GetWorld()->IsGameWorld() || !IsValid(Transit) || !IsValid(CrowdField)
        || Transit->GetWorld()!=GetWorld() || CrowdField->GetWorld()!=GetWorld()
        || CrowdField->PoseMeshes.IsEmpty() || !CrowdField->PoseMeshes[0]
        || !FMath::IsFinite(WalkSpeedCmPerSecond) || WalkSpeedCmPerSecond <= 0) return false;
    WalkInstances->SetStaticMesh(CrowdField->PoseMeshes[0]); PhotoInstances->SetStaticMesh(PhotographerPoseMesh);
    WalkInstances->ClearInstances(); PhotoInstances->ClearInstances();
    Figures.SetNum(FMath::Clamp(MaxConcurrentFigures,1,512));
    const FTransform Hidden(FQuat::Identity,FVector(0,0,-200000),FVector::ZeroVector);
    for (int32 Index=0; Index<Figures.Num(); ++Index) { WalkInstances->AddInstance(Hidden,true); PhotoInstances->AddInstance(Hidden,true); }
    Seen.Clear(); Cursor=0; Boarded=0; Alighted=0; Expired=0; Refused=0; PhotoRequests=0;
    AddTickPrerequisiteActor(Transit);
    Transit->OnPassengerExchange.AddUniqueDynamic(this,&AMikdashTransitCrowdCoordinator::HandleExchange);
    bRunning=true; return true;
}
void AMikdashTransitCrowdCoordinator::ShutdownCoordinator()
{
    if (IsValid(Transit)) { Transit->OnPassengerExchange.RemoveDynamic(this,&AMikdashTransitCrowdCoordinator::HandleExchange); RemoveTickPrerequisiteActor(Transit); }
    bRunning=false; Figures.Reset(); Seen.Clear(); WalkInstances->ClearInstances(); PhotoInstances->ClearInstances();
}
void AMikdashTransitCrowdCoordinator::EndPlay(const EEndPlayReason::Type Reason)
{
    ShutdownCoordinator(); Super::EndPlay(Reason);
}
int32 AMikdashTransitCrowdCoordinator::GetActiveTransferCount() const
{
    int32 Count=0; for (const FMikdashTransferFigure& Figure : Figures) if (Figure.bActive) ++Count; return Count;
}
bool AMikdashTransitCrowdCoordinator::GroundPoint(const FVector& Approximate,FVector& Feet) const
{
    if (Approximate.ContainsNaN()) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(TransitCrowdGround),true);
    Query.AddIgnoredActor(this); Query.AddIgnoredActor(Transit); Query.AddIgnoredActor(CrowdField);
    FHitResult Hit;
    if (!GetWorld()->LineTraceSingleByChannel(Hit,Approximate+FVector(0,0,250),Approximate-FVector(0,0,250),ECC_Visibility,Query)
        || !Hit.bBlockingHit || Hit.ImpactNormal.Z<0.8 || FMath::Abs(Hit.ImpactPoint.Z-Approximate.Z)>150) return false;
    Feet=Hit.ImpactPoint; return true;
}
bool AMikdashTransitCrowdCoordinator::CorridorClear(const FVector& From,const FVector& To,int32 IgnoreSlot) const
{
    if (!IsValid(CrowdField) || !CrowdField->IsTransitSegmentAllowed(From,To,34)) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(TransitCrowdSweep),true);
    Query.AddIgnoredActor(this); Query.AddIgnoredActor(Transit); Query.AddIgnoredActor(CrowdField);
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(FVector::Distance(From,To)/25.0));
    for(int32 Step=0;Step<=Steps;++Step)
    {
        const FVector Point=FMath::Lerp(From,To,static_cast<double>(Step)/Steps); FVector Feet;
        if(!GroundPoint(Point,Feet) || FMath::Abs(Feet.Z-Point.Z)>5) return false;
    }
    // Other transfer figures are noncolliding instances; enforce their clearance explicitly.
    for(int32 Index=0;Index<Figures.Num();++Index)
    {
        const auto& Other=Figures[Index];
        if(Index==IgnoreSlot || !Other.bActive || !Other.bVisible) continue;
        if(FMath::PointDistToSegment(Other.Position,From,To)<70) return false;
    }
    const FVector Lift(0,0,98); const FCollisionShape Capsule=FCollisionShape::MakeCapsule(34,96);
    if(GetWorld()->OverlapBlockingTestByChannel(From+Lift,FQuat::Identity,ECC_Pawn,Capsule,Query)
        || GetWorld()->OverlapBlockingTestByChannel(To+Lift,FQuat::Identity,ECC_Pawn,Capsule,Query)) return false;
    FHitResult Hit;
    return !GetWorld()->SweepSingleByChannel(Hit,From+Lift,To+Lift,FQuat::Identity,ECC_Pawn,Capsule,Query);
}
void AMikdashTransitCrowdCoordinator::HandleExchange(const FMikdashPassengerExchange& Request)
{
    if(!bRunning || !Transit->IsPassengerExchangeOpen(Request) || Request.Count<=0 || Request.BoardingPoint.ContainsNaN()
        || !FMath::IsFinite(Request.SecondsAvailable) || Request.SecondsAvailable<=0) return;
    const std::string Key=MikdashTransitCrowd::Key(TCHAR_TO_UTF8(*Request.RouteId.ToString()),Request.Generation,Request.VehicleId,Request.RunIndex,Request.GlobalStopIndex);
    if(!Seen.Insert(Key)) return;
    const auto Window=MikdashTransitCrowd::ExchangeWindow(Request.StartSimulationSeconds,Request.SecondsAvailable);
    FVector Door; if(!GroundPoint(Request.BoardingPoint,Door)) { Refused+=Request.Count; return; }
    const FVector Furniture=Transit->GetStopFurniturePoint(Request.GlobalStopIndex);
    FVector Out=Furniture-Door; Out.Z=0;
    if(Out.SizeSquared2D()<100) { Refused+=Request.Count; return; }
    Out.Normalize(); const FVector Side(-Out.Y,Out.X,0);
    // Alighters first; boarders start only in the second portion of the open-door window.
    for(int32 Direction=0;Direction<2;++Direction)
    {
        int32 AtStop=0; for(const auto& Figure:Figures) if(Figure.bActive && Figure.Request.GlobalStopIndex==Request.GlobalStopIndex) ++AtStop;
        const int32 Count=MikdashTransitCrowd::Admission(Request.Count,GetActiveTransferCount(),Figures.Num(),AtStop,FMath::Clamp(MaxFiguresPerStop,1,64));
        Refused+=Request.Count-Count;
        const int32 DesiredPhotos=Direction==0 ? Transit->SuggestPhotographerCount(Request.GlobalStopIndex,Count,Request.RunIndex) : 0;
        PhotoRequests+=DesiredPhotos;
        for(int32 Person=0;Person<Count;++Person)
        {
            int32 Slot=INDEX_NONE; for(int32 Index=0;Index<Figures.Num();++Index) if(!Figures[Index].bActive) { Slot=Index; break; }
            if(Slot==INDEX_NONE) break;
            const bool Photo=Person<DesiredPhotos && PhotographerPoseMesh;
            const double Start=(Direction==0?Request.StartSimulationSeconds:Window.BoardingStart)+Person*0.75;
            const double Deadline=Direction==0?Window.AlightingEnd:Window.Deadline;
            const FVector Approximate=Furniture+Out*(100+(Person/4)*90)+Side*((Person%4-1.5)*90);
            FVector Gather;
            if(!GroundPoint(Approximate,Gather)) { ++Refused; continue; }
            const FVector From=Direction==0?Door:Gather,To=Direction==0?Gather:Door;
            if(!MikdashTransitCrowd::Fits(FVector::Distance(From,To),WalkSpeedCmPerSecond,Deadline-Start)
                || !CorridorClear(From,To)) { ++Refused; continue; }
            auto& Figure=Figures[Slot]; Figure=FMikdashTransferFigure(); Figure.Request=Request;
            Figure.StableId=FString(UTF8_TO_TCHAR(Key.c_str()))+FString::Printf(TEXT(":%d:%d"),Direction,Person);
            Figure.Position=From; Figure.Destination=To; Figure.StartAt=Start; Figure.Deadline=Deadline;
            Figure.LastUpdate=Start; Figure.bAlighting=Direction==0; Figure.bPhotographer=Photo; Figure.bActive=true;
        }
    }
}
void AMikdashTransitCrowdCoordinator::Retire(int32 Slot)
{
    Figures[Slot].bActive=false; Figures[Slot].bVisible=false; Render(Slot);
}
void AMikdashTransitCrowdCoordinator::Render(int32 Slot)
{
    const auto& Figure=Figures[Slot];
    FTransform Transform(FQuat::Identity,FVector(0,0,-200000),FVector::ZeroVector);
    if(Figure.bVisible && Figure.bActive)
    {
        FVector Facing=(Figure.bPhotoStanding?PhotographerLookAt:Figure.Destination)-Figure.Position; Facing.Z=0;
        Transform=FTransform(FRotator(0,Facing.Rotation().Yaw,0),Figure.Position,FVector::OneVector);
    }
    const FTransform Hidden(FQuat::Identity,FVector(0,0,-200000),FVector::ZeroVector);
    WalkInstances->UpdateInstanceTransform(Slot,Figure.bPhotoStanding?Hidden:Transform,true,false,true);
    PhotoInstances->UpdateInstanceTransform(Slot,Figure.bPhotoStanding?Transform:Hidden,true,false,true);
}
void AMikdashTransitCrowdCoordinator::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!bRunning || !IsValid(Transit) || Transit->IsTransitPaused() || UGameplayStatics::IsGamePaused(this)) return;
    const double Now=Transit->GetTransitSeconds();
    // Deadlines are checked for ALL reserved slots even when movement is budgeted.
    for(int32 Index=0;Index<Figures.Num();++Index)
        if(Figures[Index].bActive && (Now>=Figures[Index].Deadline || !Transit->IsTransitActive()
            || Now<Figures[Index].LastUpdate
            || (!Figures[Index].bPhotoStanding && !Transit->IsPassengerExchangeOpen(Figures[Index].Request))))
        { ++Expired; Retire(Index); }
    for(int32 Visited=0;Visited<FMath::Min(Figures.Num(),FMath::Clamp(UpdateBudget,1,128));++Visited)
    {
        const int32 Slot=Cursor; Cursor=(Cursor+1)%Figures.Num(); auto& Figure=Figures[Slot];
        if(!Figure.bActive || Now<Figure.StartAt) continue;
        const double Dt=FMath::Clamp(Now-Figure.LastUpdate,0.0,0.25); Figure.LastUpdate=Now;
        if(!Figure.bVisible)
        {
            if(!CorridorClear(Figure.Position,Figure.Position,Slot)) continue;
            Figure.bVisible=true;
        }
        if(Figure.bPhotoStanding)
        {
            if(!CorridorClear(Figure.Position,Figure.Position,Slot)) { ++Expired; Retire(Slot); }
            else Render(Slot);
            continue;
        }
        const FVector Difference=Figure.Destination-Figure.Position;
        const FVector Next=Figure.Position+Difference.GetSafeNormal()*FMath::Min(Difference.Size(),Dt*WalkSpeedCmPerSecond);
        if(!CorridorClear(Figure.Position,Next,Slot)) { Render(Slot); continue; }
        Figure.Position=Next;
        if(FVector::DistSquared(Figure.Position,Figure.Destination)<=25.0)
        {
            if(Figure.bAlighting) ++Alighted; else ++Boarded;
            if(Figure.bAlighting && Figure.bPhotographer)
            {
                // Real door-to-gather travel completed first. Bounded photography can
                // continue after doors close, still consuming its concurrency slot.
                Figure.bPhotoStanding=true; Figure.Deadline=Now+12.0; Render(Slot);
            }
            else Retire(Slot);
        }
        else Render(Slot);
    }
    WalkInstances->MarkRenderStateDirty(); PhotoInstances->MarkRenderStateDirty();
}
FString AMikdashTransitCrowdCoordinator::GetCoordinatorSummary() const
{
    return FString::Printf(TEXT("active=%d cap=%d boarded=%d alighted=%d expired=%d refused=%d photographerRequests=%d poseConfigured=%s; background instances, not resident AI"),
        GetActiveTransferCount(),Figures.Num(),Boarded,Alighted,Expired,Refused,PhotoRequests,PhotographerPoseMesh?TEXT("yes"):TEXT("no"));
}
