#pragma once
#include <cstdint>
// POD boundary only. No proof inline/template definitions enter a UE translation unit.
namespace MeasuredStrict {
constexpr unsigned MaxVertices=256,MaxFaces=128,MaxShapes=32,MaxDepth=8;
struct Transform {double scale[3],translation[3],quaternion[4];};
struct Vertex {uint32_t xyzBits[3];uint32_t originalParticle;}; // No coordinate weld.
struct Face {uint32_t index[3];int32_t external;uint32_t shape,internal;};
struct Shape {uint64_t component,instance,ordinal;uint32_t firstVertex,vertices,firstFace,faces,depth;
    Transform outerToInner[MaxDepth];};
struct Query {double min[3],max[3];};
struct Snapshot {uint64_t acquisition,world,geometry,binding;uint32_t vertices,faces,shapes;
    Query capturedQuery;
    Vertex vertex[MaxVertices];Face face[MaxFaces];Shape shape[MaxShapes];};
struct Q {int64_t n,d;};
struct Request {uint64_t acquisition,world,geometry,binding;int32_t profile;
    Q from[2],to[2],root[3],maxSlope,heightTolerance,contactBelowRoot;double origin[3];};
struct Interval {double lo,hi;};
enum class Status:uint32_t {Refused,SupportCovered,SurfaceClear,PotentialObstacle};
enum class FaceClass:uint8_t {Unknown,Separated,SupportContact,PotentialObstacle};
enum class Cull:uint32_t {Refused,Keep,Disjoint};
struct Evidence {Status status;uint32_t vertices,faces;double radius,signedMinZ,signedMaxZ;
    Interval vertex[MaxVertices][3];uint8_t supportFace[MaxFaces];
    Query query;FaceClass faceClass[MaxFaces];uint32_t separatedFaces,contactFaces,potentialFaces;
    uint8_t queryEnclosed,surfaceClassificationComplete;
    // Always false in this phase: triangle support cannot establish these facts.
    uint8_t obstaclesComplete,worldComplete;};
}
extern "C" bool MeasuredStrictCover(const MeasuredStrict::Snapshot*,const MeasuredStrict::Request*,MeasuredStrict::Evidence*) noexcept;
extern "C" bool MeasuredStrictMakeQuery(const MeasuredStrict::Request*,MeasuredStrict::Query*) noexcept;
extern "C" MeasuredStrict::Cull MeasuredStrictCullBounds(const MeasuredStrict::Shape*,const uint32_t* MinBits,
 const uint32_t* MaxBits,const MeasuredStrict::Query*) noexcept;
extern "C" MeasuredStrict::Cull MeasuredStrictCullTriangle(const MeasuredStrict::Shape*,
 const MeasuredStrict::Vertex* ThreePoints,const MeasuredStrict::Query*) noexcept;
