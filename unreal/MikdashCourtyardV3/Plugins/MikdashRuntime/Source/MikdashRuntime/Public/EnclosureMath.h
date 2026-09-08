#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>

// Engine-independent arithmetic for the Yechezkel 42:15-20 sacred precinct and for the
// three-state MODERN / YECHEZKEL / OVERLAY toggle that shows it over modern Jerusalem.
//
// Shared by three consumers, which is the whole reason it is a header and not a .cpp:
//   * AMikdashEnclosure (Private/MikdashEnclosure.cpp) - run-time state, dissolve, hiding;
//   * Scripts/create_enclosure.py - offline wall/gate/overlay geometry, same square;
//   * Scripts/release_enclosure.py - which modern building actors fall inside;
//   * Tests/EnclosureMathTest.cpp - the standalone cl.exe test.
// If those four ever disagree about where the square is, the bug is here and only here.
//
// UNITS. Two different centimetres live in this file and confusing them is the classic
// error, so they are always named:
//   * UNREAL CM  - the level's own units. The Jerusalem OSM context, the measured
//                  architecture and the FutureMountV1 platform were all baked at
//                  ProjectCmPerAmah = 50 Unreal cm per amah (0.5 m/amah). That is a
//                  property of the existing level, NOT a halachic claim, and this file
//                  never changes it.
//   * REAL CM    - what an amah is worth in the physical world, which is disputed. The
//                  AmahOpinions table carries the common range (48.0 - 58.0 cm) so the
//                  SAME 3000-amah square can be reported in metres under each opinion
//                  without re-baking a single vertex.
// So: the model is built once at 50 Unreal cm/amah; the metre figure quoted to a viewer
// depends on which amah he holds. See SourceAssets/enclosure-review/sources.md.
//
// FRAME. Unreal's: +X east, +Y SOUTH, +Z up. Yaw is degrees clockwise seen from above
// (Unreal's sign), so yaw 0 means the square's sides run exactly east-west/north-south.
//
// NOT IN THIS FILE: no halachic ruling, no engine type, no I/O, no globals, no allocation
// beyond the std::vector outputs the caller owns.
namespace MikdashEnclosure
{
// ---------------------------------------------------------------------------
// 1. The amah, and the fact that its length is disputed
// ---------------------------------------------------------------------------

/** One opinion about the physical length of an amah. `Key` is the stable identifier the
 * Python generators and the receipts use; `Attribution` is the position, not a proof. */
struct FAmahOpinion
{
    const char* Key;
    const char* Attribution;
    double RealCentimetres;
};

/** The common range, smallest first. Deliberately a range and not a ruling: this project
 * does not decide the shiur, it reports what the square measures under each. */
inline const FAmahOpinion* AmahOpinions()
{
    static const FAmahOpinion Table[] = {
        {"naeh",        "R' Avraham Chaim Naeh, Shiurei Torah - amah of 6 tefachim x 8 cm", 48.0},
        {"project",     "Project world scale; the round half-metre the level is baked at",  50.0},
        {"feinstein",   "R' Moshe Feinstein, Igros Moshe OC I:136 - 21 3/8 inch amah",       54.0},
        {"chazon-ish",  "Chazon Ish, Kuntres HaShiurim - amah of 6 tefachim x 9.6 cm",       57.6},
        {"chazon-ish-stringent", "Chazon Ish, stringent rounding used for de'oraisa shiurim", 58.0},
    };
    return Table;
}
constexpr int AmahOpinionCount = 5;

/** Lookup by key. Returns nullptr when the key is unknown, never a silent default. */
inline const FAmahOpinion* FindAmahOpinion(const char* Key)
{
    if (Key == nullptr) return nullptr;
    const FAmahOpinion* Table = AmahOpinions();
    for (int Index = 0; Index < AmahOpinionCount; ++Index)
    {
        if (std::strcmp(Table[Index].Key, Key) == 0) return &Table[Index];
    }
    return nullptr;
}

/** The level's baked world scale. Changing this would invalidate every existing actor
 * transform in the Walkthrough map, so it is a constant, not a setting. */
constexpr double ProjectCmPerAmah = 50.0;
/** Yechezkel 42:16-19: the precinct is measured in reeds, and a reed is six amot
 * (Yechezkel 40:5, "a reed of six amot, an amah and a tefach"). */
constexpr double AmotPerReed = 6.0;
/** Yechezkel 42:20: five hundred by five hundred. */
constexpr double PrecinctReedsPerSide = 500.0;
/** 500 x 6 = 3000 amot per side. The single number the whole toggle turns on. */
constexpr double PrecinctSideAmot = PrecinctReedsPerSide * AmotPerReed;
/** Mishnah Middot 2:1, the Har HaBayit of the Second Temple: 500 amot square. Kept here
 * because the OVERLAY state draws it beside the 3000 so a viewer sees the ratio 6:1. */
constexpr double MiddotHarHaBayitAmot = 500.0;
/** Yechezkel 45:1 / 48:8-20, the terumah: 25,000 on a side. Whether those 25,000 are
 * amot or reeds is itself disputed; the overlay ring is drawn in amot and labelled. */
constexpr double TerumahSideAmot = 25000.0;

inline double ReedsToAmot(double Reeds) { return Reeds * AmotPerReed; }
inline double AmotToReeds(double Amot) { return Amot / AmotPerReed; }

/** Amot -> level units. Exact for the values the generators use. */
inline double AmotToUnrealCm(double Amot, double WorldCmPerAmah = ProjectCmPerAmah)
{
    return Amot * WorldCmPerAmah;
}
inline double UnrealCmToAmot(double UnrealCm, double WorldCmPerAmah = ProjectCmPerAmah)
{
    return (WorldCmPerAmah == 0.0) ? 0.0 : UnrealCm / WorldCmPerAmah;
}
/** Amot -> physical metres under one opinion about the amah. This is the only function
 * that is allowed to know that an amah might not be 50 cm. */
inline double AmotToRealMetres(double Amot, double AmahRealCm)
{
    return Amot * AmahRealCm / 100.0;
}
inline double RealMetresToAmot(double Metres, double AmahRealCm)
{
    return (AmahRealCm == 0.0) ? 0.0 : Metres * 100.0 / AmahRealCm;
}

// ---------------------------------------------------------------------------
// 2. Vectors, and the square itself
// ---------------------------------------------------------------------------
constexpr double Pi = 3.14159265358979323846;

struct FVec2
{
    double X = 0.0;
    double Y = 0.0;
};
inline FVec2 operator+(const FVec2& A, const FVec2& B) { return {A.X + B.X, A.Y + B.Y}; }
inline FVec2 operator-(const FVec2& A, const FVec2& B) { return {A.X - B.X, A.Y - B.Y}; }
inline FVec2 operator*(const FVec2& A, double S) { return {A.X * S, A.Y * S}; }
inline double Dot(const FVec2& A, const FVec2& B) { return A.X * B.X + A.Y * B.Y; }
inline double Length(const FVec2& A) { return std::sqrt(Dot(A, A)); }
inline double Distance(const FVec2& A, const FVec2& B) { return Length(A - B); }
inline bool Finite(const FVec2& A) { return std::isfinite(A.X) && std::isfinite(A.Y); }
inline double DegToRad(double D) { return D * Pi / 180.0; }
inline double RadToDeg(double R) { return R * 180.0 / Pi; }

/** The precinct, as one axis-aligned-then-rotated square in level units.
 *
 * HalfSideUnrealCm is half of 3000 amot; keeping the half-side rather than the side is
 * what makes the containment test a pair of |.| <= H comparisons in local space, which is
 * exact on the edge instead of accumulating a subtraction. */
struct FSquare
{
    FVec2 CentreUnrealCm;
    double HalfSideUnrealCm = 0.0;
    double YawDegrees = 0.0;
};

/** Rotate a world offset into the square's local frame (inverse of the square's yaw). */
inline FVec2 WorldToLocal(const FSquare& Square, const FVec2& World)
{
    const double R = DegToRad(Square.YawDegrees);
    const double C = std::cos(R), S = std::sin(R);
    const FVec2 D = World - Square.CentreUnrealCm;
    return {D.X * C + D.Y * S, -D.X * S + D.Y * C};
}
inline FVec2 LocalToWorld(const FSquare& Square, const FVec2& Local)
{
    const double R = DegToRad(Square.YawDegrees);
    const double C = std::cos(R), S = std::sin(R);
    return {Square.CentreUnrealCm.X + Local.X * C - Local.Y * S,
            Square.CentreUnrealCm.Y + Local.X * S + Local.Y * C};
}

inline double SquareSideUnrealCm(const FSquare& Square) { return 2.0 * Square.HalfSideUnrealCm; }
inline double SquareSideAmot(const FSquare& Square, double WorldCmPerAmah = ProjectCmPerAmah)
{
    return UnrealCmToAmot(SquareSideUnrealCm(Square), WorldCmPerAmah);
}
inline double SquarePerimeterUnrealCm(const FSquare& Square) { return 8.0 * Square.HalfSideUnrealCm; }
inline double SquareAreaSquareMetres(const FSquare& Square)
{
    const double Side = SquareSideUnrealCm(Square) / 100.0;
    return Side * Side;
}

/** Centred construction: the reading in which the House stands in the middle of the
 * precinct. Not the book's reading; offered because a viewer asks for it immediately. */
inline FSquare MakeSquareFromCentre(FVec2 CentreUnrealCm, double SideAmot,
                                    double WorldCmPerAmah = ProjectCmPerAmah, double YawDegrees = 0.0)
{
    FSquare Square;
    Square.CentreUnrealCm = CentreUnrealCm;
    Square.HalfSideUnrealCm = AmotToUnrealCm(SideAmot, WorldCmPerAmah) * 0.5;
    Square.YawDegrees = YawDegrees;
    return Square;
}

/** The book's construction (Lishchno Tidreshu p. 113, fig. 2'2): the Sanctuary does NOT
 * stand in the middle. Open ground is largest south, then east, then north, least west.
 * The square is therefore pinned by the clearance from the Temple envelope's north-west
 * corner to the wall's west and north OUTER faces, and the east/south clearances fall out
 * of the 3000.
 *
 * CourtNorthWestUnrealCm is the north-west corner of the measured court envelope
 * (smallest X, smallest Y - remember +Y is south, so smallest Y is north). */
inline FSquare MakeSquareFromNorthWestClearance(FVec2 CourtNorthWestUnrealCm,
                                                double ClearWestAmot, double ClearNorthAmot,
                                                double SideAmot,
                                                double WorldCmPerAmah = ProjectCmPerAmah,
                                                double YawDegrees = 0.0)
{
    const double SideCm = AmotToUnrealCm(SideAmot, WorldCmPerAmah);
    const double WestFace = CourtNorthWestUnrealCm.X - AmotToUnrealCm(ClearWestAmot, WorldCmPerAmah);
    const double NorthFace = CourtNorthWestUnrealCm.Y - AmotToUnrealCm(ClearNorthAmot, WorldCmPerAmah);
    FSquare Square;
    Square.CentreUnrealCm = {WestFace + SideCm * 0.5, NorthFace + SideCm * 0.5};
    Square.HalfSideUnrealCm = SideCm * 0.5;
    Square.YawDegrees = YawDegrees;
    return Square;
}

/** Corner order is fixed and load-bearing: 0 = NW, 1 = NE, 2 = SE, 3 = SW, walking
 * clockwise on screen when +Y is south. Side i runs from corner i to corner (i+1)%4, so
 * side 0 is NORTH, 1 is EAST, 2 is SOUTH, 3 is WEST. Gate placement depends on this. */
enum class ESide : int { North = 0, East = 1, South = 2, West = 3 };

inline void SquareCorners(const FSquare& Square, FVec2 OutCorners[4])
{
    const double H = Square.HalfSideUnrealCm;
    const FVec2 Local[4] = {{-H, -H}, {H, -H}, {H, H}, {-H, H}};
    for (int Index = 0; Index < 4; ++Index) OutCorners[Index] = LocalToWorld(Square, Local[Index]);
}

/** Proof, not assertion: all four sides equal, both diagonals equal, all four corners
 * right-angled. Returns the worst absolute error in cm; the test asserts on this. */
inline double SquareShapeErrorUnrealCm(const FSquare& Square)
{
    FVec2 C[4];
    SquareCorners(Square, C);
    const double Side = SquareSideUnrealCm(Square);
    double Worst = 0.0;
    for (int Index = 0; Index < 4; ++Index)
    {
        const FVec2& A = C[Index];
        const FVec2& B = C[(Index + 1) % 4];
        const FVec2& P = C[(Index + 3) % 4];
        Worst = std::max(Worst, std::abs(Distance(A, B) - Side));
        // Right angle: the dot of the two edges leaving this corner, normalised by the
        // side length so the number stays in centimetres and is comparable to the others.
        const double Skew = std::abs(Dot(B - A, P - A)) / (Side > 0.0 ? Side : 1.0);
        Worst = std::max(Worst, Skew);
    }
    const double Diagonal = Side * std::sqrt(2.0);
    Worst = std::max(Worst, std::abs(Distance(C[0], C[2]) - Diagonal));
    Worst = std::max(Worst, std::abs(Distance(C[1], C[3]) - Diagonal));
    return Worst;
}

// ---------------------------------------------------------------------------
// 3. Containment - the test that decides which modern buildings vanish
// ---------------------------------------------------------------------------

/** Boundary is a real third answer, not a rounding artefact: a building whose centroid
 * lands within EdgeTolerance of the wall line must be reported, never silently binned. */
enum class EContainment : int { Outside = 0, Boundary = 1, Inside = 2 };

inline EContainment ClassifyPoint(const FSquare& Square, const FVec2& WorldPoint,
                                  double EdgeToleranceUnrealCm = 0.0)
{
    if (!Finite(WorldPoint) || !std::isfinite(Square.HalfSideUnrealCm)) return EContainment::Outside;
    const FVec2 Local = WorldToLocal(Square, WorldPoint);
    const double H = Square.HalfSideUnrealCm;
    const double Tol = std::max(0.0, EdgeToleranceUnrealCm);
    const double DX = std::abs(Local.X), DY = std::abs(Local.Y);
    if (DX > H + Tol || DY > H + Tol) return EContainment::Outside;
    if (DX >= H - Tol || DY >= H - Tol) return EContainment::Boundary;
    return EContainment::Inside;
}

/** Inclusive test: a point exactly on the wall line is inside. Yechezkel 42:20 measures
 * the wall itself, so the boundary belongs to the precinct. */
inline bool PointInside(const FSquare& Square, const FVec2& WorldPoint,
                        double EdgeToleranceUnrealCm = 0.0)
{
    return ClassifyPoint(Square, WorldPoint, EdgeToleranceUnrealCm) != EContainment::Outside;
}

struct FAabb2
{
    FVec2 Min;
    FVec2 Max;
};
inline FVec2 AabbCentre(const FAabb2& Box) { return {(Box.Min.X + Box.Max.X) * 0.5, (Box.Min.Y + Box.Max.Y) * 0.5}; }
inline double AabbLongestSide(const FAabb2& Box)
{
    return std::max(Box.Max.X - Box.Min.X, Box.Max.Y - Box.Min.Y);
}

enum class EOverlap : int { Outside = 0, Straddling = 1, Inside = 2 };

/** Box classification. Straddling is the honest answer for a footprint the wall cuts;
 * the caller decides policy (the release script hides straddlers only under
 * ESelectionRule::AnyOverlap and records the count either way). */
inline EOverlap ClassifyBox(const FSquare& Square, const FAabb2& Box, double EdgeToleranceUnrealCm = 0.0)
{
    const FVec2 Corners[4] = {Box.Min, {Box.Max.X, Box.Min.Y}, Box.Max, {Box.Min.X, Box.Max.Y}};
    int InsideCount = 0;
    for (int Index = 0; Index < 4; ++Index)
    {
        if (PointInside(Square, Corners[Index], EdgeToleranceUnrealCm)) ++InsideCount;
    }
    if (InsideCount == 4) return EOverlap::Inside;
    if (InsideCount > 0) return EOverlap::Straddling;
    // No corner inside still leaves two overlap cases: the square inside the box, and a
    // cross. Both are caught by testing the square's corners against the box.
    FVec2 SquareCorners4[4];
    SquareCorners(Square, SquareCorners4);
    for (int Index = 0; Index < 4; ++Index)
    {
        const FVec2& P = SquareCorners4[Index];
        if (P.X >= Box.Min.X - EdgeToleranceUnrealCm && P.X <= Box.Max.X + EdgeToleranceUnrealCm &&
            P.Y >= Box.Min.Y - EdgeToleranceUnrealCm && P.Y <= Box.Max.Y + EdgeToleranceUnrealCm)
        {
            return EOverlap::Straddling;
        }
    }
    return EOverlap::Outside;
}

// ---------------------------------------------------------------------------
// 4. Building selection - deterministic, sorted, fingerprinted
// ---------------------------------------------------------------------------

/** One candidate to hide. Id is the OSM way id for a context building and a stable hash
 * of the actor label for an authored one; either way it must be stable across runs. */
struct FBuildingRef
{
    long long Id = 0;
    FVec2 CentroidUnrealCm;
    FAabb2 BoundsUnrealCm;
    /** Set by the caller from the actor's folder/mesh path. An excluded candidate is
     * never selected and is counted separately - this is where the 256 terrain tiles and
     * the five hollow union actors are kept out of the answer. */
    bool bExcluded = false;
};

enum class ESelectionRule : int
{
    /** Default. Robust against a footprint whose AABB is larger than the building. */
    CentroidInside = 0,
    /** Only footprints entirely within the wall line. The conservative set. */
    FullyInside = 1,
    /** Everything the wall line touches. The largest set. */
    AnyOverlap = 2,
};

struct FSelectionCounts
{
    int Considered = 0;
    int Excluded = 0;
    int Selected = 0;
    int Straddling = 0;
    int Outside = 0;
};

/** Fills OutSortedIds with the selected ids in ascending order. Sorting inside the
 * function - not at the call site - is what makes the set order-independent of however
 * the editor happened to enumerate actors this run. */
inline FSelectionCounts SelectBuildings(const std::vector<FBuildingRef>& Candidates,
                                        const FSquare& Square, ESelectionRule Rule,
                                        double EdgeToleranceUnrealCm,
                                        std::vector<long long>& OutSortedIds)
{
    FSelectionCounts Counts;
    OutSortedIds.clear();
    for (std::size_t Index = 0; Index < Candidates.size(); ++Index)
    {
        const FBuildingRef& Ref = Candidates[Index];
        ++Counts.Considered;
        if (Ref.bExcluded)
        {
            ++Counts.Excluded;
            continue;
        }
        const EOverlap Box = ClassifyBox(Square, Ref.BoundsUnrealCm, EdgeToleranceUnrealCm);
        if (Box == EOverlap::Straddling) ++Counts.Straddling;
        bool bTake = false;
        switch (Rule)
        {
            case ESelectionRule::CentroidInside:
                bTake = PointInside(Square, Ref.CentroidUnrealCm, EdgeToleranceUnrealCm);
                break;
            case ESelectionRule::FullyInside:
                bTake = (Box == EOverlap::Inside);
                break;
            case ESelectionRule::AnyOverlap:
                bTake = (Box != EOverlap::Outside);
                break;
        }
        if (bTake) OutSortedIds.push_back(Ref.Id);
        else ++Counts.Outside;
    }
    std::sort(OutSortedIds.begin(), OutSortedIds.end());
    OutSortedIds.erase(std::unique(OutSortedIds.begin(), OutSortedIds.end()), OutSortedIds.end());
    Counts.Selected = static_cast<int>(OutSortedIds.size());
    return Counts;
}

/** FNV-1a over the sorted ids. Two runs that produce the same fingerprint produced the
 * same hide-set; the receipt carries it so a later run can prove nothing drifted. */
inline unsigned long long SelectionFingerprint(const std::vector<long long>& SortedIds)
{
    unsigned long long Hash = 1469598103934665603ULL;
    for (std::size_t Index = 0; Index < SortedIds.size(); ++Index)
    {
        unsigned long long Value = static_cast<unsigned long long>(SortedIds[Index]);
        for (int Byte = 0; Byte < 8; ++Byte)
        {
            Hash ^= (Value >> (Byte * 8)) & 0xFFULL;
            Hash *= 1099511628211ULL;
        }
    }
    return Hash;
}

// ---------------------------------------------------------------------------
// 5. Boundary sampling - what the OVERLAY draws and what the wall instances sit on
// ---------------------------------------------------------------------------

/** One place on the boundary. Yaw is the outward normal's yaw, which is what an instanced
 * wall segment or an overlay ribbon quad wants for its transform. */
struct FBoundarySample
{
    FVec2 PositionUnrealCm;
    double DistanceAlongUnrealCm = 0.0;   // 0 at the NW corner, increasing clockwise
    double OutwardYawDegrees = 0.0;
    int Side = 0;                          // ESide
    int IndexOnSide = 0;
    bool bCorner = false;
};

/** Outward yaw for each side, given the square's own yaw. North side faces -Y (yaw 270),
 * east +X (0), south +Y (90), west -X (180) before the square's rotation is added. */
inline double SideOutwardYawDegrees(const FSquare& Square, int Side)
{
    static const double Base[4] = {270.0, 0.0, 90.0, 180.0};
    double Yaw = Base[((Side % 4) + 4) % 4] + Square.YawDegrees;
    while (Yaw < 0.0) Yaw += 360.0;
    while (Yaw >= 360.0) Yaw -= 360.0;
    return Yaw;
}

/** Samples the whole boundary at approximately TargetSpacing, snapped so every side gets
 * the same whole number of equal steps and every CORNER is hit exactly. Returns the number
 * of samples per side. The last sample is not a duplicate of the first: the ring is
 * closed implicitly, so a caller drawing a line strip must wrap.
 *
 * Determinism matters here as much as in the selection: the wall instances and the overlay
 * ribbon must land on the same points every run or the dissolve cross-fades between two
 * slightly different rings. */
inline int SampleBoundary(const FSquare& Square, double TargetSpacingUnrealCm,
                          std::vector<FBoundarySample>& OutSamples)
{
    OutSamples.clear();
    const double Side = SquareSideUnrealCm(Square);
    if (!(Side > 0.0) || !(TargetSpacingUnrealCm > 0.0)) return 0;
    int PerSide = static_cast<int>(std::ceil(Side / TargetSpacingUnrealCm - 1e-9));
    if (PerSide < 1) PerSide = 1;
    FVec2 Corners[4];
    SquareCorners(Square, Corners);
    OutSamples.reserve(static_cast<std::size_t>(PerSide) * 4u);
    for (int SideIndex = 0; SideIndex < 4; ++SideIndex)
    {
        const FVec2& From = Corners[SideIndex];
        const FVec2& To = Corners[(SideIndex + 1) % 4];
        const double Yaw = SideOutwardYawDegrees(Square, SideIndex);
        for (int Step = 0; Step < PerSide; ++Step)
        {
            const double T = static_cast<double>(Step) / static_cast<double>(PerSide);
            FBoundarySample Sample;
            Sample.PositionUnrealCm = {From.X + (To.X - From.X) * T, From.Y + (To.Y - From.Y) * T};
            Sample.DistanceAlongUnrealCm = Side * (static_cast<double>(SideIndex) + T);
            Sample.OutwardYawDegrees = Yaw;
            Sample.Side = SideIndex;
            Sample.IndexOnSide = Step;
            Sample.bCorner = (Step == 0);
            OutSamples.push_back(Sample);
        }
    }
    return PerSide;
}

// ---------------------------------------------------------------------------
// 6. Wall instancing and the draw budget
// ---------------------------------------------------------------------------

/** A gate opening, expressed as a fraction along its own side so it survives a change of
 * amah or of side length. The book (pp. 115-117) puts five gates on the outer wall:
 * two south, one east, one north, one west. */
struct FGateOpening
{
    int Side = 0;
    double CentreFractionAlongSide = 0.5;
    double WidthAmot = 10.0;
};

/** Does an instance of length SegmentLength starting at StartAlongSide clear every gate on
 * its side? A segment that would cut into an opening is dropped and the gate module is
 * placed there instead. */
inline bool SegmentClearsGates(int Side, double StartAlongSideUnrealCm, double SegmentLengthUnrealCm,
                               double SideLengthUnrealCm, const std::vector<FGateOpening>& Gates,
                               double GateJambWidthAmot, double WorldCmPerAmah = ProjectCmPerAmah)
{
    const double SegLo = StartAlongSideUnrealCm;
    const double SegHi = StartAlongSideUnrealCm + SegmentLengthUnrealCm;
    for (std::size_t Index = 0; Index < Gates.size(); ++Index)
    {
        const FGateOpening& Gate = Gates[Index];
        if (Gate.Side != Side) continue;
        const double Full = AmotToUnrealCm(Gate.WidthAmot + 2.0 * GateJambWidthAmot, WorldCmPerAmah);
        const double Centre = SideLengthUnrealCm * Gate.CentreFractionAlongSide;
        const double GateLo = Centre - Full * 0.5;
        const double GateHi = Centre + Full * 0.5;
        if (SegHi > GateLo + 1e-6 && SegLo < GateHi - 1e-6) return false;
    }
    return true;
}

/** The whole reason the wall is instanced. A 1.4-1.5 km wall as one static mesh would be
 * a single 1.5 km bounding box: no frustum culling, no occlusion culling, one LOD for the
 * whole ring, and a re-import for any change. As N identical modules on a hierarchical
 * instanced component the GPU sees one draw per component with per-instance culling. */
struct FWallPlan
{
    int SegmentsPerSide = 0;
    double SegmentLengthUnrealCm = 0.0;
    int WallInstances = 0;
    int GateInstances = 0;
    int CornerInstances = 0;
    int OverlayInstances = 0;
    long long WallTriangles = 0;
    long long GateTriangles = 0;
    long long CornerTriangles = 0;
    long long OverlayTriangles = 0;
    long long TotalTriangles = 0;
    int TotalInstances = 0;
};

struct FModuleBudget
{
    int WallSegmentTriangles = 240;
    int GateTriangles = 900;
    int CornerTriangles = 320;
    int OverlayQuadTriangles = 8;
};

/** Plans the ring: how many segments per side at approximately NominalSegmentLength,
 * how many are dropped for gates, and what that costs. Segment length is snapped so a
 * side is a whole number of segments - a fractional last segment on a 1.5 km wall is the
 * kind of thing that shows as a seam from the air. */
inline FWallPlan PlanWall(const FSquare& Square, double NominalSegmentLengthUnrealCm,
                          const std::vector<FGateOpening>& Gates, double GateJambWidthAmot,
                          const FModuleBudget& Budget, double OverlaySpacingUnrealCm,
                          double WorldCmPerAmah = ProjectCmPerAmah)
{
    FWallPlan Plan;
    const double SideLength = SquareSideUnrealCm(Square);
    if (!(SideLength > 0.0) || !(NominalSegmentLengthUnrealCm > 0.0)) return Plan;
    Plan.SegmentsPerSide = static_cast<int>(std::floor(SideLength / NominalSegmentLengthUnrealCm + 0.5));
    if (Plan.SegmentsPerSide < 1) Plan.SegmentsPerSide = 1;
    Plan.SegmentLengthUnrealCm = SideLength / static_cast<double>(Plan.SegmentsPerSide);
    for (int Side = 0; Side < 4; ++Side)
    {
        for (int Step = 0; Step < Plan.SegmentsPerSide; ++Step)
        {
            const double Start = Plan.SegmentLengthUnrealCm * static_cast<double>(Step);
            if (SegmentClearsGates(Side, Start, Plan.SegmentLengthUnrealCm, SideLength, Gates,
                                   GateJambWidthAmot, WorldCmPerAmah))
            {
                ++Plan.WallInstances;
            }
        }
    }
    Plan.GateInstances = static_cast<int>(Gates.size());
    Plan.CornerInstances = 4;
    std::vector<FBoundarySample> Samples;
    SampleBoundary(Square, OverlaySpacingUnrealCm, Samples);
    Plan.OverlayInstances = static_cast<int>(Samples.size());
    Plan.WallTriangles = static_cast<long long>(Plan.WallInstances) * Budget.WallSegmentTriangles;
    Plan.GateTriangles = static_cast<long long>(Plan.GateInstances) * Budget.GateTriangles;
    Plan.CornerTriangles = static_cast<long long>(Plan.CornerInstances) * Budget.CornerTriangles;
    Plan.OverlayTriangles = static_cast<long long>(Plan.OverlayInstances) * Budget.OverlayQuadTriangles;
    Plan.TotalTriangles = Plan.WallTriangles + Plan.GateTriangles + Plan.CornerTriangles + Plan.OverlayTriangles;
    Plan.TotalInstances = Plan.WallInstances + Plan.GateInstances + Plan.CornerInstances + Plan.OverlayInstances;
    return Plan;
}

// ---------------------------------------------------------------------------
// 7. The three states and the dissolve between them
// ---------------------------------------------------------------------------

enum class EPrecinctState : int
{
    /** What exists today: the Old City stands, the Temple on its platform, no enclosure. */
    Modern = 0,
    /** The 3000-amah precinct built. Modern buildings inside are HIDDEN, never deleted. */
    Yechezkel = 1,
    /** The boundary drawn over the standing modern city. Nothing disappears. */
    Overlay = 2,
};

/** What each subsystem is worth in a pure state. Every value is 0..1 and everything the
 * actor animates is one of these four; a transition is a lerp of the four, which is why a
 * dissolve never needs a special case per state pair. */
struct FStateWeights
{
    /** Opacity/dissolve of the solid wall, gates and corners. */
    double SolidWall = 0.0;
    /** Opacity of the translucent boundary band and the ground line of light. */
    double OverlayBand = 0.0;
    /** Visibility of modern buildings that fall inside the boundary. 1 = fully shown. */
    double ModernInside = 1.0;
    /** Brightness of the corner and gate marker lights, which read at 1.5 km when the
     * wall itself is a thin line on screen. */
    double Markers = 0.0;
};

inline FStateWeights WeightsFor(EPrecinctState State)
{
    FStateWeights W;
    switch (State)
    {
        case EPrecinctState::Modern:
            W.SolidWall = 0.0; W.OverlayBand = 0.0; W.ModernInside = 1.0; W.Markers = 0.0;
            break;
        case EPrecinctState::Yechezkel:
            W.SolidWall = 1.0; W.OverlayBand = 0.0; W.ModernInside = 0.0; W.Markers = 0.35;
            break;
        case EPrecinctState::Overlay:
            W.SolidWall = 0.0; W.OverlayBand = 1.0; W.ModernInside = 1.0; W.Markers = 1.0;
            break;
    }
    return W;
}

/** Hermite ease. Used rather than a linear ramp because the thing being cross-faded is a
 * 1.5 km ribbon: a linear alpha reads as a hard edge sweeping past. */
inline double SmoothStep01(double T)
{
    if (!std::isfinite(T)) return 0.0;
    const double C = std::max(0.0, std::min(1.0, T));
    return C * C * (3.0 - 2.0 * C);
}

struct FDissolve
{
    EPrecinctState From = EPrecinctState::Modern;
    EPrecinctState To = EPrecinctState::Modern;
    double ElapsedSeconds = 0.0;
    double DurationSeconds = 0.0;
};

/** 0 at the start of a transition, 1 at the end. A zero or negative duration is an
 * immediate cut, which is what a load or a console set wants. */
inline double DissolveAlpha(const FDissolve& Transition)
{
    if (!(Transition.DurationSeconds > 0.0)) return 1.0;
    return SmoothStep01(Transition.ElapsedSeconds / Transition.DurationSeconds);
}

inline FStateWeights BlendWeights(const FDissolve& Transition)
{
    const FStateWeights A = WeightsFor(Transition.From);
    const FStateWeights B = WeightsFor(Transition.To);
    const double T = DissolveAlpha(Transition);
    FStateWeights W;
    W.SolidWall = A.SolidWall + (B.SolidWall - A.SolidWall) * T;
    W.OverlayBand = A.OverlayBand + (B.OverlayBand - A.OverlayBand) * T;
    W.ModernInside = A.ModernInside + (B.ModernInside - A.ModernInside) * T;
    W.Markers = A.Markers + (B.Markers - A.Markers) * T;
    return W;
}

/** A hidden actor costs nothing, but SetActorHiddenInGame is binary: there is no half a
 * building. So a building fades by material dissolve while ModernInside is strictly
 * between 0 and 1, and is hard-hidden only once it reaches 0. This function is the single
 * place that rule lives, so the actor and the receipt agree. */
inline bool ShouldHardHide(double ModernInsideWeight)
{
    return ModernInsideWeight <= 1e-4;
}
inline bool NeedsDissolveMaterial(double ModernInsideWeight)
{
    return ModernInsideWeight > 1e-4 && ModernInsideWeight < 1.0 - 1e-4;
}

// ---------------------------------------------------------------------------
// 8. Reporting helpers - the numbers the review document has to quote
// ---------------------------------------------------------------------------

struct FPrecinctReport
{
    double SideAmot = 0.0;
    double SideReeds = 0.0;
    double AmahRealCm = 0.0;
    double SideRealMetres = 0.0;
    double AreaRealSquareKm = 0.0;
    /** Middot 2:1's 500-amah Har HaBayit under the same amah, for the ratio. */
    double MiddotSideRealMetres = 0.0;
    double RatioToMiddot = 0.0;
};

inline FPrecinctReport ReportUnderAmah(double SideAmot, double AmahRealCm)
{
    FPrecinctReport R;
    R.SideAmot = SideAmot;
    R.SideReeds = AmotToReeds(SideAmot);
    R.AmahRealCm = AmahRealCm;
    R.SideRealMetres = AmotToRealMetres(SideAmot, AmahRealCm);
    R.AreaRealSquareKm = (R.SideRealMetres / 1000.0) * (R.SideRealMetres / 1000.0);
    R.MiddotSideRealMetres = AmotToRealMetres(MiddotHarHaBayitAmot, AmahRealCm);
    R.RatioToMiddot = (R.MiddotSideRealMetres > 0.0) ? R.SideRealMetres / R.MiddotSideRealMetres : 0.0;
    return R;
}

} // namespace MikdashEnclosure
