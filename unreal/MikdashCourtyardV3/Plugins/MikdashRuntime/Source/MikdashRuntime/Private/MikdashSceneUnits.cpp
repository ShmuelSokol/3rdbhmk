#include "MikdashSceneUnits.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

AMikdashSceneUnits::AMikdashSceneUnits()
{
    PrimaryActorTick.bCanEverTick = false;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("SceneUnitsRoot"));
    SetActorEnableCollision(false);
}

bool AMikdashSceneUnits::TryGetFrame(MikdashSceneUnits::Frame& Frame, FString& Error) const
{
    Error.Reset();
    MikdashSceneUnits::Frame Candidate;
    Candidate.SchemaVersion = static_cast<uint32>(DescriptorSchemaVersion);
    Candidate.FixedOrigin = {FixedArchitectureOriginCm.X, FixedArchitectureOriginCm.Y, FixedArchitectureOriginCm.Z};
    if (CoordinateRevision == EMikdashSceneCoordinateRevision::Legacy50V1 && SceneRevision == TEXT("Legacy50.v1"))
        Candidate.CoordinateRevision = MikdashSceneUnits::Revision::Legacy50V1;
    else if (CoordinateRevision == EMikdashSceneCoordinateRevision::Selected48V1 && SceneRevision == TEXT("Selected48.v1"))
        Candidate.CoordinateRevision = MikdashSceneUnits::Revision::Selected48V1;
    else
    {
        Error = TEXT("Scene coordinate enum and revision identity do not match a supported layout.");
        return false;
    }
    if (!MikdashSceneUnits::Valid(Candidate))
    {
        Error = TEXT("Unsupported scene-units schema or non-finite architecture origin.");
        return false;
    }
    Frame = Candidate; return true;
}

bool AMikdashSceneUnits::ValidateDescriptor(FString& Error) const
{
    MikdashSceneUnits::Frame Frame;
    return TryGetFrame(Frame, Error);
}

bool AMikdashSceneUnits::Resolve(const UWorld* World, MikdashSceneUnits::Frame& Frame, FString& Error)
{
    Error.Reset();
    if (!World) { Error = TEXT("No world for scene-unit resolution."); return false; }
    const AMikdashSceneUnits* Found = nullptr;
    for (TActorIterator<AMikdashSceneUnits> It(World); It; ++It)
    {
        if (!IsValid(*It)) continue;
        if (Found) { Error = TEXT("More than one scene-units descriptor exists in this world."); return false; }
        Found = *It;
    }
    if (Found) return Found->TryGetFrame(Frame, Error);
    Frame = MikdashSceneUnits::Frame{}; // historical unmarked maps, no global default mutation
    return true;
}

bool AMikdashSceneUnits::ConvertLegacyTemplePoint(FVector LegacyPoint, FVector& Converted, FString& Error) const
{
    MikdashSceneUnits::Frame Frame;
    MikdashUnits::PointCm Point;
    if (!TryGetFrame(Frame, Error)) return false;
    if (!MikdashSceneUnits::TryLegacyTemplePoint(Frame, {LegacyPoint.X, LegacyPoint.Y, LegacyPoint.Z}, Point))
    { Error = TEXT("Invalid legacy architectural point or conversion overflow."); return false; }
    Converted = FVector(Point.X, Point.Y, Point.Z); return true;
}

bool AMikdashSceneUnits::PlaceAboveLegacyTempleSupport(FVector LegacySupport, double PhysicalHeightCm,
                                                     FVector& Converted, FString& Error) const
{
    MikdashSceneUnits::Frame Frame;
    MikdashUnits::PointCm Point;
    if (!TryGetFrame(Frame, Error)) return false;
    if (!MikdashSceneUnits::TryLegacyTempleSupport(Frame, {LegacySupport.X, LegacySupport.Y, LegacySupport.Z}, PhysicalHeightCm, Point))
    { Error = TEXT("Invalid legacy support, physical height or conversion overflow."); return false; }
    Converted = FVector(Point.X, Point.Y, Point.Z); return true;
}
