// Standalone test for EnclosureMath.h. No Unreal, no engine, no I/O beyond stdout and an
// optional JSON snapshot path in argv[1].
//
// Compiled and run by:  Scripts/create_enclosure.py --tests
// which writes SourceAssets/enclosure-review/tests.json.
//
// The contract the three-state precinct toggle depends on:
//   1. the square is actually square - equal sides, equal diagonals, right angles - at
//      yaw 0 and at an awkward yaw, and under every amah opinion in the table;
//   2. amah <-> cm <-> metre conversions round-trip, and reeds -> amot is exactly x6;
//   3. the containment test is right ON the edge and ON the corner, not merely near them;
//   4. the building-selection set is deterministic: same input in any order, same set,
//      same fingerprint; and the three selection rules nest (FullyInside subset of
//      CentroidInside-or-not is NOT assumed, but FullyInside subset of AnyOverlap is);
//   5. boundary sampling hits all four corners exactly and closes;
//   6. the wall plan stays inside the RTX 2070 budget stated in the review;
//   7. the dissolve is monotone, starts at the From state and ends at the To state.
#include "EnclosureMath.h"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using namespace MikdashEnclosure;

static bool Near(double A, double B, double Tolerance = 1e-9) { return std::abs(A - B) <= Tolerance; }

// Every measured number the test proves, echoed into the JSON snapshot so a reviewer sees
// values rather than the word PASS.
static std::string Snapshot;
static void Record(const char* Key, double Value)
{
    char Line[256];
    std::snprintf(Line, sizeof(Line), "%s  \"%s\": %.6f", Snapshot.empty() ? "" : ",\n", Key, Value);
    Snapshot += Line;
}
static void RecordInt(const char* Key, long long Value)
{
    char Line[256];
    std::snprintf(Line, sizeof(Line), "%s  \"%s\": %lld", Snapshot.empty() ? "" : ",\n", Key, Value);
    Snapshot += Line;
}
static void RecordText(const char* Key, const char* Value)
{
    char Line[512];
    std::snprintf(Line, sizeof(Line), "%s  \"%s\": \"%s\"", Snapshot.empty() ? "" : ",\n", Key, Value);
    Snapshot += Line;
}

// ---------------------------------------------------------------------------
// The real square this project places, so the test is testing the shipped numbers and not
// a convenient toy. Court supporting platform faces are +-8100 Unreal cm in X and the
// measured architecture spans Y -9450..9450 (SourceAssets/architecture-manifest.json).
// Lishchno Tidreshu fig. 2'2 (p. 113): 500 amot clear west, 501 clear north.
// ---------------------------------------------------------------------------
static const double CourtWestFaceCm = -8100.0;
static const double CourtNorthFaceCm = -8100.0;
static const double ClearWestAmot = 500.0;
static const double ClearNorthAmot = 501.0;

static FSquare BookSquare(double Yaw = 0.0)
{
    return MakeSquareFromNorthWestClearance({CourtWestFaceCm, CourtNorthFaceCm},
                                            ClearWestAmot, ClearNorthAmot,
                                            PrecinctSideAmot, ProjectCmPerAmah, Yaw);
}

// ---------------------------------------------------------------------------
// 1. Squareness
// ---------------------------------------------------------------------------
static void SquarenessChecks()
{
    const double Yaws[] = {0.0, 17.3456, 45.0, 90.0, 180.0, 273.19, -31.7};
    double Worst = 0.0;
    for (double Yaw : Yaws)
    {
        const FSquare Square = BookSquare(Yaw);
        const double Error = SquareShapeErrorUnrealCm(Square);
        Worst = std::max(Worst, Error);
        assert(Error < 1e-6);
        // The side really is 3000 amot, and 3000 amot really is 500 reeds.
        assert(Near(SquareSideAmot(Square), PrecinctSideAmot, 1e-9));
        assert(Near(AmotToReeds(SquareSideAmot(Square)), PrecinctReedsPerSide, 1e-12));
        // Perimeter and area agree with the side, which catches a half-side/side slip.
        assert(Near(SquarePerimeterUnrealCm(Square), 4.0 * SquareSideUnrealCm(Square), 1e-9));
        const double SideMetres = SquareSideUnrealCm(Square) / 100.0;
        assert(Near(SquareAreaSquareMetres(Square), SideMetres * SideMetres, 1e-6));
    }
    // Centred construction is square too, and its centre is where it was asked to be.
    const FSquare Centred = MakeSquareFromCentre({550.0, 0.0}, PrecinctSideAmot);
    assert(SquareShapeErrorUnrealCm(Centred) < 1e-6);
    assert(Near(Centred.CentreUnrealCm.X, 550.0) && Near(Centred.CentreUnrealCm.Y, 0.0));

    // The book anchoring must reproduce the west and north OUTER faces exactly, because
    // that is the statement being modelled - not an approximate placement.
    const FSquare Book = BookSquare();
    FVec2 Corners[4];
    SquareCorners(Book, Corners);
    const double ExpectedWest = CourtWestFaceCm - ClearWestAmot * ProjectCmPerAmah;
    const double ExpectedNorth = CourtNorthFaceCm - ClearNorthAmot * ProjectCmPerAmah;
    assert(Near(Corners[0].X, ExpectedWest, 1e-9));
    assert(Near(Corners[0].Y, ExpectedNorth, 1e-9));
    assert(Near(Corners[2].X, ExpectedWest + PrecinctSideAmot * ProjectCmPerAmah, 1e-9));
    assert(Near(Corners[2].Y, ExpectedNorth + PrecinctSideAmot * ProjectCmPerAmah, 1e-9));
    // And the east/south clearances that fall out of the 3000 are the diagram's remainder.
    const double ClearEast = UnrealCmToAmot(Corners[2].X - 8100.0);
    const double ClearSouth = UnrealCmToAmot(Corners[2].Y - 9450.0);
    Record("book_square_west_face_cm", ExpectedWest);
    Record("book_square_north_face_cm", ExpectedNorth);
    Record("book_square_centre_x_cm", Book.CentreUnrealCm.X);
    Record("book_square_centre_y_cm", Book.CentreUnrealCm.Y);
    Record("book_clear_east_amot", ClearEast);
    Record("book_clear_south_amot", ClearSouth);
    Record("worst_square_shape_error_cm", Worst);
    // Mishkenei Elyon 196 m.1 order: south largest, then east, then north, least west.
    assert(ClearSouth > ClearEast && ClearEast > ClearNorthAmot && ClearNorthAmot > ClearWestAmot);
    std::printf("squareness: worst corner/side/diagonal error %.3g cm over 7 yaws\n", Worst);
    std::printf("book square: west face %.0f cm, north face %.0f cm, clearances E %.0f / S %.0f amot\n",
                ExpectedWest, ExpectedNorth, ClearEast, ClearSouth);
}

// ---------------------------------------------------------------------------
// 2. Conversions round-trip, and the amah table behaves
// ---------------------------------------------------------------------------
static void ConversionChecks()
{
    assert(Near(ReedsToAmot(500.0), 3000.0, 1e-12));
    assert(Near(AmotToReeds(3000.0), 500.0, 1e-12));
    assert(Near(AmotToReeds(ReedsToAmot(137.5)), 137.5, 1e-12));

    const FAmahOpinion* Table = AmahOpinions();
    double Smallest = 1e9, Largest = 0.0;
    for (int Index = 0; Index < AmahOpinionCount; ++Index)
    {
        const FAmahOpinion& Opinion = Table[Index];
        assert(FindAmahOpinion(Opinion.Key) == &Opinion);
        assert(Opinion.RealCentimetres >= 48.0 && Opinion.RealCentimetres <= 58.0);
        Smallest = std::min(Smallest, Opinion.RealCentimetres);
        Largest = std::max(Largest, Opinion.RealCentimetres);
        // metres <-> amot round-trip under this opinion
        const double Metres = AmotToRealMetres(PrecinctSideAmot, Opinion.RealCentimetres);
        assert(Near(RealMetresToAmot(Metres, Opinion.RealCentimetres), PrecinctSideAmot, 1e-9));
        // Unreal cm <-> amot round-trip at the level's baked scale
        const double Cm = AmotToUnrealCm(PrecinctSideAmot);
        assert(Near(UnrealCmToAmot(Cm), PrecinctSideAmot, 1e-9));
        char Key[96];
        std::snprintf(Key, sizeof(Key), "precinct_side_metres_at_%s", Opinion.Key);
        Record(Key, Metres);
        const FPrecinctReport R = ReportUnderAmah(PrecinctSideAmot, Opinion.RealCentimetres);
        assert(Near(R.RatioToMiddot, PrecinctSideAmot / MiddotHarHaBayitAmot, 1e-9));
        assert(Near(R.RatioToMiddot, 6.0, 1e-9));   // 3000 : 500 is exactly six, always
        std::snprintf(Key, sizeof(Key), "precinct_area_sq_km_at_%s", Opinion.Key);
        Record(Key, R.AreaRealSquareKm);
    }
    assert(FindAmahOpinion("no-such-opinion") == nullptr);
    assert(FindAmahOpinion(nullptr) == nullptr);
    Record("amah_range_low_cm", Smallest);
    Record("amah_range_high_cm", Largest);
    // The disputed range is worth 288 m on a side; that is the point of reporting three.
    const double Spread = AmotToRealMetres(PrecinctSideAmot, Largest) - AmotToRealMetres(PrecinctSideAmot, Smallest);
    Record("precinct_side_metres_spread_across_opinions", Spread);
    assert(Spread > 250.0 && Spread < 350.0);
    std::printf("conversions: amah %.1f-%.1f cm, precinct side %.1f-%.1f m (spread %.1f m)\n",
                Smallest, Largest, AmotToRealMetres(PrecinctSideAmot, Smallest),
                AmotToRealMetres(PrecinctSideAmot, Largest), Spread);
}

// ---------------------------------------------------------------------------
// 3. Containment on edges and corners
// ---------------------------------------------------------------------------
static void ContainmentChecks()
{
    for (double Yaw : {0.0, 33.75, 90.0})
    {
        const FSquare Square = BookSquare(Yaw);
        FVec2 Corners[4];
        SquareCorners(Square, Corners);
        const double H = Square.HalfSideUnrealCm;

        // Centre is unambiguously inside.
        assert(ClassifyPoint(Square, Square.CentreUnrealCm) == EContainment::Inside);

        // Every corner is ON the boundary with any tolerance at all, and inclusive-inside.
        for (int Index = 0; Index < 4; ++Index)
        {
            assert(PointInside(Square, Corners[Index], 1e-6));
            assert(ClassifyPoint(Square, Corners[Index], 1e-6) == EContainment::Boundary);
        }

        // Every edge MIDPOINT likewise; and a point one cm outside an edge midpoint is out
        // while one cm inside is in. One centimetre on a 1.5 km side is 7e-6 of the span,
        // so this is a genuinely tight test of the local-frame rotation.
        for (int Index = 0; Index < 4; ++Index)
        {
            const FVec2 A = Corners[Index];
            const FVec2 B = Corners[(Index + 1) % 4];
            const FVec2 Mid = {(A.X + B.X) * 0.5, (A.Y + B.Y) * 0.5};
            assert(ClassifyPoint(Square, Mid, 1e-6) == EContainment::Boundary);
            const double OutYaw = DegToRad(SideOutwardYawDegrees(Square, Index));
            const FVec2 Normal = {std::cos(OutYaw), std::sin(OutYaw)};
            const FVec2 Out = {Mid.X + Normal.X * 1.0, Mid.Y + Normal.Y * 1.0};
            const FVec2 In = {Mid.X - Normal.X * 1.0, Mid.Y - Normal.Y * 1.0};
            assert(ClassifyPoint(Square, Out, 0.01) == EContainment::Outside);
            assert(ClassifyPoint(Square, In, 0.01) == EContainment::Inside);
        }

        // Just outside a CORNER along the diagonal is outside; just inside is inside.
        for (int Index = 0; Index < 4; ++Index)
        {
            const FVec2 Toward = Square.CentreUnrealCm - Corners[Index];
            const double L = Length(Toward);
            const FVec2 Unit = {Toward.X / L, Toward.Y / L};
            const FVec2 In = {Corners[Index].X + Unit.X * 2.0, Corners[Index].Y + Unit.Y * 2.0};
            const FVec2 Out = {Corners[Index].X - Unit.X * 2.0, Corners[Index].Y - Unit.Y * 2.0};
            assert(ClassifyPoint(Square, In, 0.01) == EContainment::Inside);
            assert(ClassifyPoint(Square, Out, 0.01) == EContainment::Outside);
        }

        // A point beyond the corner but inside both slabs of one axis must still be out.
        const FVec2 BeyondCorner = LocalToWorld(Square, {H + 10.0, H - 10.0});
        assert(ClassifyPoint(Square, BeyondCorner, 0.01) == EContainment::Outside);

        // Non-finite input never counts as inside; the release script feeds it real actor
        // bounds and a degenerate actor must not silently join the hide-set.
        const double NaN = std::numeric_limits<double>::quiet_NaN();
        assert(!PointInside(Square, {NaN, 0.0}, 1.0));
        assert(!PointInside(Square, {0.0, std::numeric_limits<double>::infinity()}, 1.0));

        // Box classification: a box hugging the centre is Inside, one straddling an edge is
        // Straddling, one far away is Outside, and one that SWALLOWS the whole square is
        // Straddling (the no-corner-inside case that a naive four-corner test would miss).
        const FAabb2 Middle = {LocalToWorld(Square, {-100.0, -100.0}), LocalToWorld(Square, {100.0, 100.0})};
        // A rotated square's local box is not axis-aligned in world, so only test the
        // axis-aligned case for the Inside assertion.
        if (Near(Yaw, 0.0))
        {
            assert(ClassifyBox(Square, Middle) == EOverlap::Inside);
            const FAabb2 Straddle = {{Corners[0].X - 500.0, Square.CentreUnrealCm.Y - 100.0},
                                     {Corners[0].X + 500.0, Square.CentreUnrealCm.Y + 100.0}};
            assert(ClassifyBox(Square, Straddle) == EOverlap::Straddling);
            const FAabb2 Far = {{Corners[0].X - 100000.0, Corners[0].Y - 100000.0},
                                {Corners[0].X - 90000.0, Corners[0].Y - 90000.0}};
            assert(ClassifyBox(Square, Far) == EOverlap::Outside);
        }
        const FAabb2 Swallow = {{Square.CentreUnrealCm.X - H * 4.0, Square.CentreUnrealCm.Y - H * 4.0},
                                {Square.CentreUnrealCm.X + H * 4.0, Square.CentreUnrealCm.Y + H * 4.0}};
        assert(ClassifyBox(Square, Swallow) == EOverlap::Straddling);
    }
    Record("containment_edge_probe_cm", 1.0);
    std::printf("containment: corners, edge midpoints and diagonals correct at 1 cm on a 150000 cm side\n");
}

// ---------------------------------------------------------------------------
// 4. Building selection is deterministic
// ---------------------------------------------------------------------------
static std::vector<FBuildingRef> SyntheticCity(unsigned Seed, bool bWithTerrainTiles)
{
    // A city the shape of the real one: a dense cluster the size of the Old City sitting
    // west of the court, plus scatter out to +-2.5 km, plus - when asked - the 256
    // oversized terrain tiles that caused this project a day of false positives.
    std::mt19937 Random(Seed);
    std::uniform_real_distribution<double> Spread(-250000.0, 250000.0);
    std::uniform_real_distribution<double> Cluster(-50000.0, 5000.0);
    std::uniform_real_distribution<double> Size(400.0, 3000.0);
    std::vector<FBuildingRef> City;
    for (int Index = 0; Index < 4000; ++Index)
    {
        FBuildingRef Ref;
        Ref.Id = 100000000LL + Index;
        const bool bInCluster = (Index % 3) != 0;
        const double CX = bInCluster ? Cluster(Random) : Spread(Random);
        const double CY = bInCluster ? Cluster(Random) : Spread(Random);
        const double HalfW = Size(Random) * 0.5, HalfH = Size(Random) * 0.5;
        Ref.CentroidUnrealCm = {CX, CY};
        Ref.BoundsUnrealCm = {{CX - HalfW, CY - HalfH}, {CX + HalfW, CY + HalfH}};
        City.push_back(Ref);
    }
    if (bWithTerrainTiles)
    {
        // 16 x 16 tiles of 800 m, every one of which encloses the Temple in Z and several
        // of which enclose it in XY. Marked excluded, exactly as the release script does.
        for (int Row = 0; Row < 16; ++Row)
        {
            for (int Col = 0; Col < 16; ++Col)
            {
                FBuildingRef Tile;
                Tile.Id = 900000000LL + Row * 16 + Col;
                const double X0 = -640000.0 + Col * 80000.0;
                const double Y0 = -640000.0 + Row * 80000.0;
                Tile.BoundsUnrealCm = {{X0, Y0}, {X0 + 80000.0, Y0 + 80000.0}};
                Tile.CentroidUnrealCm = AabbCentre(Tile.BoundsUnrealCm);
                Tile.bExcluded = true;
                City.push_back(Tile);
            }
        }
    }
    return City;
}

static void SelectionChecks()
{
    const FSquare Square = BookSquare();
    const std::vector<FBuildingRef> City = SyntheticCity(20260908u, true);

    std::vector<long long> Selected;
    const FSelectionCounts Counts = SelectBuildings(City, Square, ESelectionRule::CentroidInside, 0.0, Selected);
    assert(Counts.Excluded == 256);
    assert(Counts.Selected > 0);
    assert(std::is_sorted(Selected.begin(), Selected.end()));
    const unsigned long long Fingerprint = SelectionFingerprint(Selected);

    // Order independence: the editor may enumerate actors in any order. Shuffle and the
    // set, its order and its fingerprint must be identical.
    std::vector<FBuildingRef> Shuffled = City;
    std::mt19937 Random(7u);
    std::shuffle(Shuffled.begin(), Shuffled.end(), Random);
    std::vector<long long> SelectedAgain;
    const FSelectionCounts CountsAgain = SelectBuildings(Shuffled, Square, ESelectionRule::CentroidInside, 0.0, SelectedAgain);
    assert(SelectedAgain == Selected);
    assert(SelectionFingerprint(SelectedAgain) == Fingerprint);
    assert(CountsAgain.Selected == Counts.Selected && CountsAgain.Excluded == Counts.Excluded);

    // Repeat runs of the identical input are bit-identical.
    std::vector<long long> Third;
    SelectBuildings(City, Square, ESelectionRule::CentroidInside, 0.0, Third);
    assert(Third == Selected);

    // THE TRAP, asserted directly. Without the exclusion flag the 256 terrain tiles - whose
    // AABBs are 800 m and enclose the whole Temple - are swept into the hide-set, and the
    // count jumps. That is the 100%-false-positive failure this test exists to prevent.
    std::vector<FBuildingRef> Unguarded = City;
    for (std::size_t Index = 0; Index < Unguarded.size(); ++Index) Unguarded[Index].bExcluded = false;
    std::vector<long long> WithTiles;
    SelectBuildings(Unguarded, Square, ESelectionRule::AnyOverlap, 0.0, WithTiles);
    std::vector<long long> WithoutTiles;
    SelectBuildings(City, Square, ESelectionRule::AnyOverlap, 0.0, WithoutTiles);
    const int TileFalsePositives = static_cast<int>(WithTiles.size() - WithoutTiles.size());
    assert(TileFalsePositives > 0);
    RecordInt("terrain_tile_false_positives_if_unguarded", TileFalsePositives);

    // The three rules nest the way the names promise.
    std::vector<long long> Full, Any;
    SelectBuildings(City, Square, ESelectionRule::FullyInside, 0.0, Full);
    SelectBuildings(City, Square, ESelectionRule::AnyOverlap, 0.0, Any);
    assert(std::includes(Any.begin(), Any.end(), Full.begin(), Full.end()));
    assert(Full.size() <= Selected.size() && Selected.size() <= Any.size());

    // An empty city selects nothing and fingerprints to the FNV offset basis.
    std::vector<long long> Empty;
    const FSelectionCounts NoCounts = SelectBuildings({}, Square, ESelectionRule::CentroidInside, 0.0, Empty);
    assert(NoCounts.Considered == 0 && Empty.empty());
    assert(SelectionFingerprint(Empty) == 1469598103934665603ULL);

    RecordInt("selection_considered", Counts.Considered);
    RecordInt("selection_excluded_terrain_tiles", Counts.Excluded);
    RecordInt("selection_centroid_inside", static_cast<long long>(Selected.size()));
    RecordInt("selection_fully_inside", static_cast<long long>(Full.size()));
    RecordInt("selection_any_overlap", static_cast<long long>(Any.size()));
    RecordInt("selection_straddling", Counts.Straddling);
    char Text[64];
    std::snprintf(Text, sizeof(Text), "%016llx", Fingerprint);
    RecordText("selection_fingerprint_fnv1a", Text);
    std::printf("selection: %d considered, %d terrain tiles excluded, %zu inside, fingerprint %s\n",
                Counts.Considered, Counts.Excluded, Selected.size(), Text);
    std::printf("selection: unguarded terrain tiles would have added %d false positives\n", TileFalsePositives);
}

// ---------------------------------------------------------------------------
// 5. Boundary sampling
// ---------------------------------------------------------------------------
static void BoundaryChecks()
{
    for (double Yaw : {0.0, 22.5})
    {
        const FSquare Square = BookSquare(Yaw);
        std::vector<FBoundarySample> Samples;
        const int PerSide = SampleBoundary(Square, 1250.0, Samples);
        assert(PerSide == 120);                        // 150000 cm / 1250 cm
        assert(Samples.size() == static_cast<std::size_t>(PerSide) * 4u);

        FVec2 Corners[4];
        SquareCorners(Square, Corners);
        int CornerHits = 0;
        for (std::size_t Index = 0; Index < Samples.size(); ++Index)
        {
            const FBoundarySample& Sample = Samples[Index];
            // Every sample lies on the boundary, to a micron.
            assert(ClassifyPoint(Square, Sample.PositionUnrealCm, 1e-3) == EContainment::Boundary);
            if (Sample.bCorner)
            {
                ++CornerHits;
                assert(Distance(Sample.PositionUnrealCm, Corners[Sample.Side]) < 1e-6);
            }
            // Distance along increases monotonically and the step is exactly uniform.
            if (Index > 0)
            {
                const double Step = Sample.DistanceAlongUnrealCm - Samples[Index - 1].DistanceAlongUnrealCm;
                assert(Near(Step, SquareSideUnrealCm(Square) / PerSide, 1e-6));
            }
        }
        assert(CornerHits == 4);

        // The ring closes: the step from the last sample back to the first equals the rest.
        const double Wrap = SquarePerimeterUnrealCm(Square) - Samples.back().DistanceAlongUnrealCm;
        assert(Near(Wrap, SquareSideUnrealCm(Square) / PerSide, 1e-6));

        // Outward yaws are the four cardinals plus the square's own yaw, all distinct.
        for (int Side = 0; Side < 4; ++Side)
        {
            const double A = SideOutwardYawDegrees(Square, Side);
            const double B = SideOutwardYawDegrees(Square, (Side + 1) % 4);
            double Delta = std::abs(A - B);
            if (Delta > 180.0) Delta = 360.0 - Delta;
            assert(Near(Delta, 90.0, 1e-9));
        }
        // Negative and out-of-range side indices wrap rather than reading off the table.
        assert(Near(SideOutwardYawDegrees(Square, -1), SideOutwardYawDegrees(Square, 3), 1e-9));
        assert(Near(SideOutwardYawDegrees(Square, 7), SideOutwardYawDegrees(Square, 3), 1e-9));

        // Degenerate requests return nothing rather than looping.
        std::vector<FBoundarySample> None;
        assert(SampleBoundary(Square, 0.0, None) == 0 && None.empty());
        assert(SampleBoundary(Square, -5.0, None) == 0 && None.empty());
    }
    RecordInt("boundary_samples_per_side_at_1250cm", 120);
    RecordInt("boundary_samples_total", 480);
    std::printf("boundary: 480 samples, all four corners exact, uniform 1250 cm step, ring closes\n");
}

// ---------------------------------------------------------------------------
// 6. The wall plan fits an RTX 2070
// ---------------------------------------------------------------------------
static std::vector<FGateOpening> BookGates()
{
    // Lishchno Tidreshu pp. 115-117 after Mishkenei Elyon 196 m.2 and Middot 1:3:
    // two gates south, one east, one north, one west; opening 10 amot wide.
    std::vector<FGateOpening> Gates;
    Gates.push_back({static_cast<int>(ESide::North), 0.50, 10.0});
    Gates.push_back({static_cast<int>(ESide::East),  0.50, 10.0});
    Gates.push_back({static_cast<int>(ESide::South), 0.30, 10.0});
    Gates.push_back({static_cast<int>(ESide::South), 0.70, 10.0});
    Gates.push_back({static_cast<int>(ESide::West),  0.50, 10.0});
    return Gates;
}

static void WallPlanChecks()
{
    const FSquare Square = BookSquare();
    const std::vector<FGateOpening> Gates = BookGates();
    const FModuleBudget Budget;
    const FWallPlan Plan = PlanWall(Square, 1250.0, Gates, 10.0, Budget, 1250.0);

    assert(Plan.SegmentsPerSide == 120);
    assert(Near(Plan.SegmentLengthUnrealCm, 1250.0, 1e-9));
    // Five gates, each 10 + 2x10 = 30 amot = 1500 cm wide, so each removes exactly two
    // 1250 cm segments from its side.
    assert(Plan.WallInstances == 480 - 10);
    assert(Plan.GateInstances == 5);
    assert(Plan.CornerInstances == 4);
    assert(Plan.TotalTriangles == Plan.WallTriangles + Plan.GateTriangles + Plan.CornerTriangles + Plan.OverlayTriangles);

    // The budget claim made in SourceAssets/enclosure-review/sources.md, asserted here so
    // it cannot quietly rot: the whole enclosure stays under a quarter of a million
    // triangles and under two thousand instances. For scale, the Old City facade set this
    // toggle hides is 3,416,580 triangles, so the enclosure is ~4% of what it replaces.
    assert(Plan.TotalTriangles < 250000);
    assert(Plan.TotalInstances < 2000);

    // A single-mesh wall would be one 1.5 km bounding box: assert the instanced form
    // actually buys per-instance culling granularity of a segment, not of the ring.
    assert(Plan.SegmentLengthUnrealCm < SquareSideUnrealCm(Square) / 50.0);

    // Gate carving is exact on both ends: a segment abutting an opening survives, one
    // overlapping it by a millimetre does not.
    const double SideLength = SquareSideUnrealCm(Square);
    const double GateCentre = SideLength * 0.5;
    assert(SegmentClearsGates(static_cast<int>(ESide::East), GateCentre - 750.0 - 1250.0, 1250.0, SideLength, Gates, 10.0));
    assert(!SegmentClearsGates(static_cast<int>(ESide::East), GateCentre - 750.0 + 1.0, 1250.0, SideLength, Gates, 10.0));
    // A side with no gate on it keeps every segment.
    assert(SegmentClearsGates(99, 0.0, 1250.0, SideLength, Gates, 10.0));

    RecordInt("wall_segments_per_side", Plan.SegmentsPerSide);
    Record("wall_segment_length_cm", Plan.SegmentLengthUnrealCm);
    RecordInt("wall_instances", Plan.WallInstances);
    RecordInt("gate_instances", Plan.GateInstances);
    RecordInt("corner_instances", Plan.CornerInstances);
    RecordInt("overlay_instances", Plan.OverlayInstances);
    RecordInt("total_instances", Plan.TotalInstances);
    RecordInt("total_triangles", Plan.TotalTriangles);
    RecordInt("oldcity_facade_triangles_for_comparison", 3416580);
    std::printf("wall plan: %d segments/side, %d wall + %d gate + %d corner + %d overlay instances, %lld triangles\n",
                Plan.SegmentsPerSide, Plan.WallInstances, Plan.GateInstances, Plan.CornerInstances,
                Plan.OverlayInstances, Plan.TotalTriangles);
}

// ---------------------------------------------------------------------------
// 7. The dissolve
// ---------------------------------------------------------------------------
static void DissolveChecks()
{
    assert(Near(SmoothStep01(0.0), 0.0) && Near(SmoothStep01(1.0), 1.0));
    assert(Near(SmoothStep01(0.5), 0.5));
    assert(Near(SmoothStep01(-3.0), 0.0) && Near(SmoothStep01(9.0), 1.0));

    const EPrecinctState States[3] = {EPrecinctState::Modern, EPrecinctState::Yechezkel, EPrecinctState::Overlay};
    for (EPrecinctState From : States)
    {
        for (EPrecinctState To : States)
        {
            FDissolve Transition;
            Transition.From = From;
            Transition.To = To;
            Transition.DurationSeconds = 2.5;

            // Endpoints are the pure states, exactly.
            Transition.ElapsedSeconds = 0.0;
            FStateWeights W = BlendWeights(Transition);
            const FStateWeights A = WeightsFor(From);
            assert(Near(W.SolidWall, A.SolidWall) && Near(W.OverlayBand, A.OverlayBand));
            assert(Near(W.ModernInside, A.ModernInside) && Near(W.Markers, A.Markers));
            Transition.ElapsedSeconds = 2.5;
            W = BlendWeights(Transition);
            const FStateWeights B = WeightsFor(To);
            assert(Near(W.SolidWall, B.SolidWall) && Near(W.OverlayBand, B.OverlayBand));
            assert(Near(W.ModernInside, B.ModernInside) && Near(W.Markers, B.Markers));

            // Monotone and bounded across the whole transition - no overshoot, which on a
            // translucent 1.5 km band would read as a flash.
            double PrevWall = -1.0, PrevBand = -1.0;
            const bool bWallRising = B.SolidWall >= A.SolidWall;
            const bool bBandRising = B.OverlayBand >= A.OverlayBand;
            for (int Step = 0; Step <= 100; ++Step)
            {
                Transition.ElapsedSeconds = 2.5 * Step / 100.0;
                W = BlendWeights(Transition);
                assert(W.SolidWall >= -1e-12 && W.SolidWall <= 1.0 + 1e-12);
                assert(W.OverlayBand >= -1e-12 && W.OverlayBand <= 1.0 + 1e-12);
                assert(W.ModernInside >= -1e-12 && W.ModernInside <= 1.0 + 1e-12);
                if (Step > 0)
                {
                    if (bWallRising) assert(W.SolidWall >= PrevWall - 1e-12);
                    else assert(W.SolidWall <= PrevWall + 1e-12);
                    if (bBandRising) assert(W.OverlayBand >= PrevBand - 1e-12);
                    else assert(W.OverlayBand <= PrevBand + 1e-12);
                }
                PrevWall = W.SolidWall;
                PrevBand = W.OverlayBand;
            }
        }
    }

    // A zero duration is an immediate cut, and never divides by zero.
    FDissolve Instant;
    Instant.From = EPrecinctState::Modern;
    Instant.To = EPrecinctState::Yechezkel;
    Instant.DurationSeconds = 0.0;
    assert(Near(DissolveAlpha(Instant), 1.0));
    assert(Near(BlendWeights(Instant).SolidWall, 1.0));

    // The hide rule: buildings fade while the weight is between the ends, and are only
    // hard-hidden at zero. Nothing is ever deleted, so MODERN restores every one.
    assert(!ShouldHardHide(1.0) && !NeedsDissolveMaterial(1.0));
    assert(ShouldHardHide(0.0) && !NeedsDissolveMaterial(0.0));
    assert(!ShouldHardHide(0.5) && NeedsDissolveMaterial(0.5));

    // OVERLAY must never hide anything - that is its whole purpose.
    assert(Near(WeightsFor(EPrecinctState::Overlay).ModernInside, 1.0));
    // MODERN must never draw wall or band.
    const FStateWeights Modern = WeightsFor(EPrecinctState::Modern);
    assert(Near(Modern.SolidWall, 0.0) && Near(Modern.OverlayBand, 0.0) && Near(Modern.Markers, 0.0));
    // YECHEZKEL hides everything inside and raises the wall.
    const FStateWeights Yechezkel = WeightsFor(EPrecinctState::Yechezkel);
    assert(Near(Yechezkel.SolidWall, 1.0) && Near(Yechezkel.ModernInside, 0.0));

    Record("dissolve_duration_seconds_tested", 2.5);
    RecordInt("dissolve_state_pairs_checked", 9);
    std::printf("dissolve: 9 state pairs monotone and bounded; OVERLAY hides nothing; MODERN restores all\n");
}

int main(int Argc, char** Argv)
{
    SquarenessChecks();
    ConversionChecks();
    ContainmentChecks();
    SelectionChecks();
    BoundaryChecks();
    WallPlanChecks();
    DissolveChecks();

    if (Argc > 1)
    {
        if (std::FILE* Handle = std::fopen(Argv[1], "w"))
        {
            std::fprintf(Handle, "{\n%s\n}\n", Snapshot.c_str());
            std::fclose(Handle);
        }
    }
    std::cout << "PASS: squareness at seven yaws, amah/reed/metre round-trips over five opinions, "
                 "edge and corner containment, deterministic and order-independent building selection "
                 "with the terrain-tile trap asserted, boundary sampling, the instanced wall budget "
                 "and the three-state dissolve" << std::endl;
    return 0;
}
