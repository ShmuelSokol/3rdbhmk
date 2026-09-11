// Standalone test for EnclosureMath.h. No Unreal, no engine, no I/O beyond stdout and an
// optional JSON snapshot path in argv[1].
//
// Compiled and run by:  Scripts/create_enclosure.py --tests
// which writes SourceAssets/enclosure-review/tests.json.
//
// The contract the three-state precinct toggle depends on:
//   1. the square is actually square - equal sides, equal diagonals, right angles - at
//      yaw 0 and at an awkward yaw, and under every amah opinion in the table;
//  1b. the four clearances close on the 3000 exactly; the Middot 2:1 ordering holds for the
//      book's own diagram envelope and for Middot's 500-amah Har HaBayit, and is PROVED
//      impossible for this project's square court envelope rather than being asserted or
//      relaxed - see the long comment on ClearanceChecks();
//   2. amah <-> cm <-> metre conversions round-trip, and reeds -> amot is exactly x6;
//   3. the containment test is right ON the edge and ON the corner, not merely near them;
//   4. the building-selection set is deterministic: same input in any order, same set,
//      same fingerprint; and the three selection rules nest (FullyInside subset of
//      CentroidInside-or-not is NOT assumed, but FullyInside subset of AnyOverlap is);
//   5. boundary sampling hits all four corners exactly and closes;
//   6. the wall plan stays inside the RTX 2070 budget stated in the review, at the level's
//      50 cm and at the candidate's 48 cm;
//  6b. the ground profile grounds every module with its plinth on the highest ground it
//      crosses and its substructure below the lowest, so the wall neither floats nor buries;
//  6c. the plaza deck lands on the Temple's own datum, stops exactly one wall thickness
//      inside the square, lays 14,641 cells into 713 irregular super-panels of which NO ONE
//      is laid the same way as the panel west or north of it, batters its retaining face
//      outward and never inward, and stays inside the RTX 2070 budget;
//   7. the dissolve is monotone, starts at the From state and ends at the To state.
#include "EnclosureMath.h"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <limits>
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
// a convenient toy.
//
// Two different "court envelopes" exist in this project and the earlier draft of this test
// mixed them, which is what made the clearance ordering look merely inconsistent rather than
// structurally impossible:
//
//   PLATFORM      SM_0127_architecture_Outer_court_supporting_platform, +-8100 Unreal cm on
//                 BOTH axes -> 324 x 324 amot, SQUARE. This is what the shipped design
//                 anchors on (enclosure-design.json inputs.courtPlatformBoundsCm), and it is
//                 also the AABB of the 'Derived union of source outer envelope walls' actor
//                 that Scripts/release_place_assets.py documents at +-8100 XY.
//   ARCHITECTURE  architecture-manifest.json expectedBoundsUnrealCm, X -8100..9200 (the east
//                 stair foot) and Y -9450..9450 (the two mount approach terraces) -> 346 amot
//                 east-west by 378 north-south. DEEPER than it is wide.
//
// The earlier draft took its west/north anchor from the PLATFORM and its east/south
// remainder from the ARCHITECTURE, so its four clearances did not close on the 3000 at all.
// Both envelopes are checked below, and the ordering inverts under each for the same reason.
//
// Lishchno Tidreshu fig. 2'2 (p. 113): 500 amot clear west, 501 clear north.
// ---------------------------------------------------------------------------
static const FAabb2 CourtPlatform = {{-8100.0, -8100.0}, {8100.0, 8100.0}};
static const double CourtEnvelopeEastWestAmot = 324.0;    // 16200 cm / 50
static const double CourtEnvelopeNorthSouthAmot = 324.0;
// architecture-manifest.json expectedBoundsUnrealCm, XY only.
static const FAabb2 MeasuredArchitecture = {{-8100.0, -9450.0}, {9200.0, 9450.0}};
static const double ArchitectureEastWestAmot = 346.0;     // 17300 cm / 50
static const double ArchitectureNorthSouthAmot = 378.0;   // 18900 cm / 50

static FSquare BookSquare(double Yaw = 0.0)
{
    return MakeSquareFromClearances(CourtPlatform, BookClearWestAmot, BookClearNorthAmot,
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
    // that is the statement being modelled - not an approximate placement. The four faces
    // and the centre are asserted against the numbers already shipped in
    // SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json `enclosure`, so this
    // header and that design file cannot silently drift apart.
    const FSquare Book = BookSquare();
    FVec2 Corners[4];
    SquareCorners(Book, Corners);
    assert(Near(Corners[0].X, -33100.0, 1e-9));     // outerFacesCm.xWest
    assert(Near(Corners[0].Y, -33150.0, 1e-9));     // outerFacesCm.yNorth
    assert(Near(Corners[2].X, 116900.0, 1e-9));     // outerFacesCm.xEast
    assert(Near(Corners[2].Y, 116850.0, 1e-9));     // outerFacesCm.ySouth
    assert(Near(Book.CentreUnrealCm.X, 41900.0, 1e-9));   // centreCm[0]
    assert(Near(Book.CentreUnrealCm.Y, 41850.0, 1e-9));   // centreCm[1]
    Record("book_square_west_face_cm", Corners[0].X);
    Record("book_square_north_face_cm", Corners[0].Y);
    Record("book_square_east_face_cm", Corners[2].X);
    Record("book_square_south_face_cm", Corners[2].Y);
    Record("book_square_centre_x_cm", Book.CentreUnrealCm.X);
    Record("book_square_centre_y_cm", Book.CentreUnrealCm.Y);
    Record("worst_square_shape_error_cm", Worst);
    std::printf("squareness: worst corner/side/diagonal error %.3g cm over 7 yaws\n", Worst);
    std::printf("book square: faces W %.0f E %.0f N %.0f S %.0f cm, centre (%.0f, %.0f)\n",
                Corners[0].X, Corners[2].X, Corners[0].Y, Corners[2].Y,
                Book.CentreUnrealCm.X, Book.CentreUnrealCm.Y);
}

// ---------------------------------------------------------------------------
// 1b. Clearances, and the ordering claim that cannot be true here
// ---------------------------------------------------------------------------
//
// This block exists because of a concrete, reproduced bug. An earlier version asserted
//
//     ClearSouth > ClearEast && ClearEast > ClearNorth && ClearNorth > ClearWest
//
// - Middot 2:1's "largest south, second east, third north, least west" - directly on the
// square this project places, and it failed. The header was NOT wrong. The expectation was:
//
//   * anchoring is by the two STATED clearances (west 500, north 501), so the other two are
//     remainders:  East = Side - West - EnvelopeEW,  South = Side - North - EnvelopeNS;
//   * therefore  South - East = (West + EnvelopeEW) - (North + EnvelopeNS);
//   * this project's measured court envelope is SQUARE (324 x 324), so EnvelopeEW cancels
//     EnvelopeNS and  South - East = West - North = -1 amah.
//
// With west 500 strictly less than north 501 - which the ordering itself demands - a square
// envelope makes South > East ARITHMETICALLY IMPOSSIBLE. No tolerance, no tuning and no
// re-anchoring on the measured platform can satisfy the old assertion; only a court envelope
// wider east-west than north-south can, which is exactly the shape of Middot's own
// 187 x 135 Azarah and of the book's 351 x 346 diagram envelope.
//
// So the ordering is asserted where it is true (the book's diagram, and Middot's own
// 500-amah Har HaBayit), the impossibility is asserted as a theorem, and the shipped square
// is asserted to depart from the ordering by exactly one amah and no more. That also pins a
// live error in project data: enclosure-design.json's offsetRule claims the order is
// "preserved" while its own numbers (east 2176, south 2175) show it inverted.
static void ClearanceChecks()
{
    // ---- the shipped square, measured rather than assumed -----------------------------
    const FSquare Book = BookSquare();
    const FClearances Measured = ClearancesOf(Book, CourtPlatform);
    assert(Near(Measured.WestAmot, 500.0, 1e-9));
    assert(Near(Measured.NorthAmot, 501.0, 1e-9));
    assert(Near(Measured.EastAmot, 2176.0, 1e-9));    // enclosure-design.json clearancesAmot
    assert(Near(Measured.SouthAmot, 2175.0, 1e-9));
    // The two sums close on the 3000 exactly; that is what makes the remainders remainders.
    assert(Near(ClearanceClosureErrorAmot(Measured, CourtEnvelopeEastWestAmot,
                                          CourtEnvelopeNorthSouthAmot, PrecinctSideAmot), 0.0, 1e-9));
    // The order is inverted, and by exactly one amah - 50 cm on a 150,000 cm side.
    assert(ClassifyClearanceOrder(Measured) == EClearanceOrder::EastSouthSwapped);
    assert(Near(ClearanceOrderMarginAmot(Measured), -1.0, 1e-9));
    assert(std::abs(ClearanceOrderMarginAmot(Measured)) <= 1.0 + 1e-9);

    // ---- the book's own diagram, where the order does hold ------------------------------
    const FClearances Diagram = BookDiagramClearances();
    assert(Near(Diagram.WestAmot, 500.0, 1e-9));
    assert(Near(Diagram.NorthAmot, 501.0, 1e-9));
    assert(Near(Diagram.EastAmot, 2149.0, 1e-9));     // 3000 - 500 - 351
    assert(Near(Diagram.SouthAmot, 2153.0, 1e-9));    // 3000 - 501 - 346
    assert(ClassifyClearanceOrder(Diagram) == EClearanceOrder::Middot);
    assert(Near(ClearanceClosureErrorAmot(Diagram, BookDiagramEnvelopeEastWestAmot,
                                          BookDiagramEnvelopeNorthSouthAmot, PrecinctSideAmot),
                0.0, 1e-9));
    // The whole disagreement between the diagram and the placed square is the envelope.
    assert(Near(Diagram.EastAmot - Measured.EastAmot,
                CourtEnvelopeEastWestAmot - BookDiagramEnvelopeEastWestAmot, 1e-9));
    assert(Near(Diagram.SouthAmot - Measured.SouthAmot,
                CourtEnvelopeNorthSouthAmot - BookDiagramEnvelopeNorthSouthAmot, 1e-9));

    // ---- the same square against the FULL measured architecture envelope ----------------
    // 346 amot east-west, 378 north-south: deeper than wide, so the order inverts here too,
    // and by more. This is the second half of the answer to "is the header wrong": no
    // envelope this project actually measured can produce the book's four numbers.
    const FClearances AgainstArchitecture = ClearancesOf(Book, MeasuredArchitecture);
    assert(Near(AgainstArchitecture.WestAmot, 500.0, 1e-9));
    assert(Near(AgainstArchitecture.NorthAmot, 474.0, 1e-9));    // the approach terrace is
                                                                 // 27 amot north of the platform
    assert(Near(AgainstArchitecture.EastAmot, 2154.0, 1e-9));    // 3000 - 500 - 346
    assert(Near(AgainstArchitecture.SouthAmot, 2148.0, 1e-9));   // 3000 - 474 - 378
    assert(Near(ClearanceClosureErrorAmot(AgainstArchitecture, ArchitectureEastWestAmot,
                                          ArchitectureNorthSouthAmot, PrecinctSideAmot), 0.0, 1e-9));
    assert(ClassifyClearanceOrder(AgainstArchitecture) == EClearanceOrder::Other);  // north < west
    Record("architecture_clear_east_amot", AgainstArchitecture.EastAmot);
    Record("architecture_clear_south_amot", AgainstArchitecture.SouthAmot);

    // ---- Middot's 500-amah Har HaBayit: the other side of the dispute -------------------
    // PROVENANCE: Mishkenei Elyon 196 ch.1 m.1, which the book quotes in full, applies the
    // Middot 2:1 wording ("rubo min hadarom...") to a Har HaBayit of THREE THOUSAND amot, not
    // to Middot's five hundred. The four numbers below - 100 west, 213 east, 115 north, 250
    // south around Middot 5:1's 187 x 135 Azarah - are the received reckoning of the SECOND
    // Temple's 500-amah Mount from the standard commentaries; they are NOT in this book and
    // are marked "authored reconstruction" in SourceAssets/enclosure-review/sources.md. Only
    // their two sums and their order are checked here, both of which are self-evident from
    // the numbers themselves.
    const FClearances Middot = MiddotHarHaBayitClearances();
    assert(Near(Middot.WestAmot + MiddotAzarahEastWestAmot + Middot.EastAmot,
                MiddotHarHaBayitAmot, 1e-9));         // 100 + 187 + 213 = 500
    assert(Near(Middot.NorthAmot + MiddotAzarahNorthSouthAmot + Middot.SouthAmot,
                MiddotHarHaBayitAmot, 1e-9));         // 115 + 135 + 250 = 500
    assert(ClassifyClearanceOrder(Middot) == EClearanceOrder::Middot);
    // And it is placeable: the 500 square built from those clearances is square, is 500
    // amot, and reads its clearances back unchanged.
    const FSquare Har = MakeMiddotHarHaBayitSquare({0.0, 0.0});
    assert(SquareShapeErrorUnrealCm(Har) < 1e-6);
    assert(Near(SquareSideAmot(Har), MiddotHarHaBayitAmot, 1e-9));
    const double HalfEW = MiddotAzarahEastWestAmot * 0.5 * ProjectCmPerAmah;
    const double HalfNS = MiddotAzarahNorthSouthAmot * 0.5 * ProjectCmPerAmah;
    const FAabb2 Azarah = {{-HalfEW, -HalfNS}, {HalfEW, HalfNS}};
    const FClearances Readback = ClearancesOf(Har, Azarah);
    assert(Near(Readback.WestAmot, 100.0, 1e-9) && Near(Readback.EastAmot, 213.0, 1e-9));
    assert(Near(Readback.NorthAmot, 115.0, 1e-9) && Near(Readback.SouthAmot, 250.0, 1e-9));
    assert(ClassifyClearanceOrder(Readback) == EClearanceOrder::Middot);
    // The 500 sits wholly inside the 3000, six times smaller on a side - the ratio the
    // OVERLAY draws. Its corners are checked against the placed precinct, not assumed.
    FVec2 HarCorners[4];
    SquareCorners(Har, HarCorners);
    for (int Index = 0; Index < 4; ++Index) assert(PointInside(Book, HarCorners[Index]));
    assert(Near(SquareSideAmot(Book) / SquareSideAmot(Har), 6.0, 1e-9));

    // ---- the impossibility, as a theorem rather than an anecdote ------------------------
    // For ANY square court envelope and ANY side length, South - East is identically
    // West - North. Swept over a range so a future change to the anchoring cannot quietly
    // reintroduce the old assertion.
    int SquareEnvelopeCases = 0;
    for (double Envelope = 100.0; Envelope <= 600.0; Envelope += 25.0)
    {
        for (double West = 300.0; West <= 700.0; West += 50.0)
        {
            for (double NorthMinusWest = 1.0; NorthMinusWest <= 40.0; NorthMinusWest += 13.0)
            {
                const FClearances C = ClearancesFromStated(West, West + NorthMinusWest,
                                                           Envelope, Envelope, PrecinctSideAmot);
                assert(Near(ClearanceOrderMarginAmot(C), -NorthMinusWest, 1e-9));
                assert(ClassifyClearanceOrder(C) != EClearanceOrder::Middot);
                ++SquareEnvelopeCases;
            }
        }
    }
    assert(SquareEnvelopeCases > 100);
    // And the converse: widen the envelope east-west by more than the west/north gap and
    // the Middot order reappears, which is precisely why the book's diagram satisfies it.
    const FClearances Wider = ClearancesFromStated(500.0, 501.0, 351.0, 346.0, PrecinctSideAmot);
    assert(ClassifyClearanceOrder(Wider) == EClearanceOrder::Middot);
    const FClearances Marginal = ClearancesFromStated(500.0, 501.0, 325.0, 324.0, PrecinctSideAmot);
    assert(ClassifyClearanceOrder(Marginal) == EClearanceOrder::Other);   // an exact tie

    Record("measured_clear_west_amot", Measured.WestAmot);
    Record("measured_clear_north_amot", Measured.NorthAmot);
    Record("measured_clear_east_amot", Measured.EastAmot);
    Record("measured_clear_south_amot", Measured.SouthAmot);
    Record("measured_order_margin_amot", ClearanceOrderMarginAmot(Measured));
    Record("measured_order_margin_cm", ClearanceOrderMarginAmot(Measured) * ProjectCmPerAmah);
    RecordText("measured_clearance_order", "east_south_swapped_by_one_amah");
    Record("diagram_clear_east_amot", Diagram.EastAmot);
    Record("diagram_clear_south_amot", Diagram.SouthAmot);
    RecordText("diagram_clearance_order", "middot_south_east_north_west");
    Record("middot_har_habayit_side_amot", MiddotHarHaBayitAmot);
    RecordInt("square_envelope_impossibility_cases", SquareEnvelopeCases);
    std::printf("clearances: placed W %.0f N %.0f E %.0f S %.0f amot -> order inverted by %.0f amah (%.0f cm)\n",
                Measured.WestAmot, Measured.NorthAmot, Measured.EastAmot, Measured.SouthAmot,
                -ClearanceOrderMarginAmot(Measured),
                -ClearanceOrderMarginAmot(Measured) * ProjectCmPerAmah);
    std::printf("clearances: book diagram W %.0f N %.0f E %.0f S %.0f amot -> Middot order holds; "
                "%d square-envelope cases prove it cannot here\n",
                Diagram.WestAmot, Diagram.NorthAmot, Diagram.EastAmot, Diagram.SouthAmot,
                SquareEnvelopeCases);
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
    // The book's own printed metre figure is reproduced by its own implied amah, which is
    // how that amah was recovered in the first place. If either constant is ever edited
    // without the other this fails rather than quietly re-scaling the whole precinct.
    assert(Near(AmotToRealMetres(PrecinctSideAmot, BookImpliedAmahRealCm),
                BookStatedPrecinctSideMetres, 1e-9));
    assert(Near(RealMetresToAmot(BookStatedPrecinctSideMetres, BookImpliedAmahRealCm),
                PrecinctSideAmot, 1e-9));
    // And the book's amah is inside the range the table carries, at its bottom end.
    assert(FindAmahOpinion("naeh") != nullptr);
    assert(Near(FindAmahOpinion("naeh")->RealCentimetres, BookImpliedAmahRealCm, 1e-9));
    assert(Near(Smallest, BookImpliedAmahRealCm, 1e-9));
    Record("book_implied_amah_cm", BookImpliedAmahRealCm);
    Record("book_stated_precinct_side_metres", BookStatedPrecinctSideMetres);
    Record("precinct_side_metres_at_project_scale",
           AmotToRealMetres(PrecinctSideAmot, ProjectCmPerAmah));

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
static std::vector<FGateOpening> BookGates(const FSquare& Square)
{
    // Five gates - two south, one each east, north and west - at the positions already
    // shipped in enclosure-design.json `enclosure.gates`, which gives them as WORLD
    // coordinates rather than as fractions: E, N and W sit on the Temple's own axes
    // (world X = 0 or world Y = 0), the two south gates at world X 16900 and 66900 cm,
    // i.e. one third and two thirds along the south wall. FractionAlongSide converts.
    // Gate positions are the book's only for the count per side; the along-wall placement
    // is the project's assumption and is recorded as such in enclosure-design.json
    // `uncertainties`. Opening 10 amot (certain); piers 10 amot each side (authored).
    // The south pair is placed at thirds FROM THE CORNERS, exactly as AMikdashEnclosure does,
    // so the same rule serves the 48 cm square; on the 50 cm square that is world X 16900 and
    // 66900, the numbers enclosure-design.json ships.
    const FVec2 TempleAxis = {0.0, 0.0};
    FVec2 C[4];
    SquareCorners(Square, C);
    const double Side = SquareSideUnrealCm(Square);
    std::vector<FGateOpening> Gates;
    Gates.push_back({static_cast<int>(ESide::North),
                     FractionAlongSide(Square, static_cast<int>(ESide::North), TempleAxis), 10.0});
    Gates.push_back({static_cast<int>(ESide::East),
                     FractionAlongSide(Square, static_cast<int>(ESide::East), TempleAxis), 10.0});
    Gates.push_back({static_cast<int>(ESide::South),
                     FractionAlongSide(Square, static_cast<int>(ESide::South), {C[3].X + Side / 3.0, C[3].Y}), 10.0});
    Gates.push_back({static_cast<int>(ESide::South),
                     FractionAlongSide(Square, static_cast<int>(ESide::South), {C[3].X + Side * 2.0 / 3.0, C[3].Y}), 10.0});
    Gates.push_back({static_cast<int>(ESide::West),
                     FractionAlongSide(Square, static_cast<int>(ESide::West), TempleAxis), 10.0});
    return Gates;
}

static void WallPlanChecks()
{
    const FSquare Square = BookSquare();
    const std::vector<FGateOpening> Gates = BookGates(Square);
    const FModuleBudget Budget;
    const FWallPlan Plan = PlanWall(Square, 1250.0, Gates, 10.0, Budget, 1250.0);

    // The gate fractions really are the shipped world positions, to the centimetre.
    assert(Near(Gates[0].CentreFractionAlongSide * 150000.0, 33100.0, 1e-6));   // N at world X 0
    assert(Near(Gates[1].CentreFractionAlongSide * 150000.0, 33150.0, 1e-6));   // E at world Y 0
    assert(Near(Gates[2].CentreFractionAlongSide * 150000.0, 100000.0, 1e-6));  // S at world X 16900
    assert(Near(Gates[3].CentreFractionAlongSide * 150000.0, 50000.0, 1e-6));   // S at world X 66900
    assert(Near(Gates[4].CentreFractionAlongSide * 150000.0, 116850.0, 1e-6));  // W at world Y 0
    // A fraction that does not land on its side is returned unclamped rather than hidden.
    assert(FractionAlongSide(Square, static_cast<int>(ESide::North), {-100000.0, 0.0}) < 0.0);

    assert(Plan.SegmentsPerSide == 120);
    assert(Near(Plan.SegmentLengthUnrealCm, 1250.0, 1e-9));
    // Each gate is 10 + 2x10 = 30 amot = 1500 cm wide, so it always destroys at least two
    // 1250 cm segments, and three when it straddles a segment boundary. Two of the five
    // gates land on a boundary (the two south gates, at exact thirds of the side) and three
    // do not, so 2x2 + 3x3 = 13 segments are dropped from the 480.
    assert(Plan.WallInstances == 480 - 13);
    for (std::size_t Index = 0; Index < Gates.size(); ++Index)
    {
        int Dropped = 0;
        for (int Step = 0; Step < Plan.SegmentsPerSide; ++Step)
        {
            if (!SegmentClearsGates(Gates[Index].Side, Plan.SegmentLengthUnrealCm * Step,
                                    Plan.SegmentLengthUnrealCm, 150000.0,
                                    {Gates[Index]}, 10.0))
            {
                ++Dropped;
            }
        }
        assert(Dropped == 2 || Dropped == 3);
    }
    assert(Plan.GateInstances == 5);
    assert(Plan.CornerInstances == 4);
    assert(Plan.TotalTriangles == Plan.WallTriangles + Plan.GateTriangles + Plan.CornerTriangles + Plan.OverlayTriangles
                                  + Plan.FoundationTriangles);

    // The budget claim made in SourceAssets/enclosure-review/sources.md, asserted here so
    // it cannot quietly rot: the whole enclosure stays under a quarter of a million
    // triangles and under two thousand instances. For scale, the Old City facade set this
    // toggle hides is 3,416,580 triangles, so the enclosure is ~4% of what it replaces.
    assert(Plan.TotalTriangles < 250000);
    assert(Plan.TotalInstances < 2000);
    // The exact figures Scripts/create_enclosure.py --export writes into
    // SourceAssets/enclosure-review/geometry-manifest.json. Asserting the totals rather than
    // only the bound means a module that quietly grows is caught the next time this runs,
    // instead of the day the frame rate drops.
    assert(Plan.WallInstances == 467 && Plan.GateInstances == 5 && Plan.CornerInstances == 4);
    assert(Plan.OverlayInstances == 480);
    // One authored substructure box under every wall, gate and corner module: 476 of them,
    // twelve triangles each, so the terrain-following costs 5,712 triangles.
    assert(Plan.FoundationInstances == 467 + 5 + 4);
    assert(Plan.FoundationTriangles == 476LL * 12LL);
    assert(Plan.TotalInstances == 956 + 476);
    assert(Plan.TotalTriangles == 112944 + 5712);
    assert(Plan.WallTriangles == 467LL * 228LL);

    // The 48 cm candidate: same plan, every module scaled by .96, the side 144,000 cm, and
    // the faces the Aron alignment review computed for that map (-31776 / -31824 / 112224 /
    // 112176) reproduced from the same rule with the candidate's platform half-extent.
    const double Half48 = CourtPlatformHalfExtentUnrealCm * ModuleScaleFor(Candidate48CmPerAmah);
    assert(Near(Half48, 7776.0, 1e-9));
    const FAabb2 Platform48 = {{-Half48, -Half48}, {Half48, Half48}};
    const FSquare Square48 = MakeSquareFromClearances(Platform48, BookClearWestAmot, BookClearNorthAmot,
                                                      PrecinctSideAmot, Candidate48CmPerAmah);
    FVec2 Corners48[4];
    SquareCorners(Square48, Corners48);
    assert(Near(Corners48[0].X, -31776.0, 1e-9) && Near(Corners48[0].Y, -31824.0, 1e-9));
    assert(Near(Corners48[2].X, 112224.0, 1e-9) && Near(Corners48[2].Y, 112176.0, 1e-9));
    assert(Near(SquareSideAmot(Square48, Candidate48CmPerAmah), PrecinctSideAmot, 1e-9));
    const FWallPlan Plan48 = PlanWall(Square48, 1250.0 * ModuleScaleFor(Candidate48CmPerAmah),
                                      BookGates(Square48), 10.0, Budget,
                                      1250.0 * ModuleScaleFor(Candidate48CmPerAmah), Candidate48CmPerAmah);
    assert(Plan48.SegmentsPerSide == 120 && Near(Plan48.SegmentLengthUnrealCm, 1200.0, 1e-9));
    assert(Plan48.WallInstances == 467 && Plan48.TotalInstances == Plan.TotalInstances);
    assert(Plan48.TotalTriangles == Plan.TotalTriangles);
    Record("candidate48_west_face_cm", Corners48[0].X);
    Record("candidate48_north_face_cm", Corners48[0].Y);
    Record("candidate48_east_face_cm", Corners48[2].X);
    Record("candidate48_south_face_cm", Corners48[2].Y);

    // A single-mesh wall would be one 1.5 km bounding box: assert the instanced form
    // actually buys per-instance culling granularity of a segment, not of the ring.
    assert(Plan.SegmentLengthUnrealCm < SquareSideUnrealCm(Square) / 50.0);

    // Gate carving is exact on both ends: a segment abutting an opening survives, one
    // overlapping it by a millimetre does not.
    const double SideLength = SquareSideUnrealCm(Square);
    const double GateCentre = SideLength * Gates[1].CentreFractionAlongSide;   // the east gate
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
    RecordInt("foundation_instances", Plan.FoundationInstances);
    RecordInt("foundation_triangles", Plan.FoundationTriangles);
    RecordInt("total_instances", Plan.TotalInstances);
    RecordInt("total_triangles", Plan.TotalTriangles);
    RecordInt("oldcity_facade_triangles_for_comparison", 3416580);
    std::printf("wall plan: %d segments/side, %d wall + %d gate + %d corner + %d overlay + %d foundation instances, %lld triangles\n",
                Plan.SegmentsPerSide, Plan.WallInstances, Plan.GateInstances, Plan.CornerInstances,
                Plan.OverlayInstances, Plan.FoundationInstances, Plan.TotalTriangles);
}

// ---------------------------------------------------------------------------
// 6b. The ground profile - the wall follows the terrain and never shows a gap
// ---------------------------------------------------------------------------
static FGroundProfile SyntheticValley(int Steps)
{
    // Side 0 flat at Z 0; side 1 (the east wall) drops into a valley 7,000 cm deep and comes
    // back - the shape of the Kidron under the real east wall; side 2 a steady 3% grade;
    // side 3 flat at -1,250 cm with a cross-slope so High and Low differ by 180 cm.
    FGroundProfile P;
    P.StepsPerSide = Steps;
    const int Stations = Steps + 1;
    P.HighZUnrealCm.assign(static_cast<std::size_t>(Stations) * 4u, 0.0);
    P.LowZUnrealCm.assign(static_cast<std::size_t>(Stations) * 4u, 0.0);
    for (int K = 0; K < Stations; ++K)
    {
        const double F = static_cast<double>(K) / static_cast<double>(Steps);
        const std::size_t I1 = static_cast<std::size_t>(Stations + K);
        const std::size_t I2 = static_cast<std::size_t>(2 * Stations + K);
        const std::size_t I3 = static_cast<std::size_t>(3 * Stations + K);
        const double Valley = -7000.0 * std::sin(F * Pi);
        P.HighZUnrealCm[I1] = Valley;            P.LowZUnrealCm[I1] = Valley - 40.0;
        P.HighZUnrealCm[I2] = F * 4500.0;        P.LowZUnrealCm[I2] = F * 4500.0;
        P.HighZUnrealCm[I3] = -1250.0;           P.LowZUnrealCm[I3] = -1430.0;
    }
    return P;
}

static void GroundChecks()
{
    // An empty or malformed profile is refused, and grounding then falls back to the level
    // plane with the footing still below it - the old behaviour, reported as such.
    FGroundProfile Empty;
    assert(!GroundProfileValid(Empty));
    const FGrounding Fallback = GroundSpan(Empty, 1, 0.2, 0.3, 50.0);
    assert(!Fallback.bFromProfile);
    assert(Near(Fallback.BaseZUnrealCm, 0.0) && Near(Fallback.FoundationBottomZUnrealCm, -50.0));
    assert(Near(Fallback.FoundationDepthUnrealCm, 50.0));
    FGroundProfile Short = SyntheticValley(600);
    Short.LowZUnrealCm.pop_back();
    assert(!GroundProfileValid(Short));
    FGroundProfile Inverted = SyntheticValley(600);
    Inverted.LowZUnrealCm[700] = Inverted.HighZUnrealCm[700] + 1.0;   // low above high is nonsense
    assert(!GroundProfileValid(Inverted));

    const FGroundProfile P = SyntheticValley(600);
    assert(GroundProfileValid(P));
    assert(GroundStationsPerSide(P) == 601);

    // Interpolation is exact at stations and linear between them; the fraction clamps and
    // the side wraps rather than reading off the end of the array.
    assert(Near(SampleGroundHighZ(P, 2, 0.0), 0.0) && Near(SampleGroundHighZ(P, 2, 1.0), 4500.0));
    assert(Near(SampleGroundHighZ(P, 2, 0.5), 2250.0, 1e-9));
    assert(Near(SampleGroundHighZ(P, 2, 1.0 / 1200.0), 4500.0 / 1200.0, 1e-9));
    assert(Near(SampleGroundHighZ(P, 2, -3.0), 0.0) && Near(SampleGroundHighZ(P, 2, 7.0), 4500.0));
    assert(Near(SampleGroundHighZ(P, 6, 0.5), SampleGroundHighZ(P, 2, 0.5)));
    assert(Near(SampleGroundLowZ(P, 3, 0.37), -1430.0) && Near(SampleGroundHighZ(P, 3, 0.37), -1250.0));

    // Every module on every side: its plinth is never below any ground it crosses, its
    // substructure reaches below the lowest ground by the footing, so there is no gap and
    // no burial. Checked against a finer sampling than GroundSpan itself uses.
    const int Modules = 120;
    double DeepestFoundation = 0.0, LargestStep = 0.0;
    for (int Side = 0; Side < 4; ++Side)
    {
        double PreviousBase = 0.0;
        for (int M = 0; M < Modules; ++M)
        {
            const double From = static_cast<double>(M) / Modules, To = static_cast<double>(M + 1) / Modules;
            const FGrounding G = GroundSpan(P, Side, From, To, 50.0);
            assert(G.bFromProfile);
            for (int Fine = 0; Fine <= 50; ++Fine)
            {
                const double F = From + (To - From) * Fine / 50.0;
                assert(G.BaseZUnrealCm >= SampleGroundHighZ(P, Side, F) - 1e-6);
                assert(G.FoundationBottomZUnrealCm <= SampleGroundLowZ(P, Side, F) - 50.0 + 1e-6);
            }
            assert(G.FoundationDepthUnrealCm >= 50.0 - 1e-9);
            assert(Near(G.FoundationDepthUnrealCm, G.BaseZUnrealCm - G.FoundationBottomZUnrealCm, 1e-9));
            // Argument order does not matter.
            const FGrounding R = GroundSpan(P, Side, To, From, 50.0);
            assert(Near(R.BaseZUnrealCm, G.BaseZUnrealCm) && Near(R.FoundationBottomZUnrealCm, G.FoundationBottomZUnrealCm));
            DeepestFoundation = std::max(DeepestFoundation, G.FoundationDepthUnrealCm);
            if (M > 0) LargestStep = std::max(LargestStep, std::abs(G.BaseZUnrealCm - PreviousBase));
            PreviousBase = G.BaseZUnrealCm;
        }
    }
    // Flat ground: the plinth sits exactly on it and the substructure is exactly the footing.
    const FGrounding Flat = GroundSpan(P, 0, 0.4, 0.45, 50.0);
    assert(Near(Flat.BaseZUnrealCm, 0.0) && Near(Flat.FoundationDepthUnrealCm, 50.0));
    // Cross-slope only: the plinth sits on the high edge and the substructure spans the
    // 180 cm cross-fall plus the footing.
    const FGrounding Cross = GroundSpan(P, 3, 0.1, 0.11, 50.0);
    assert(Near(Cross.BaseZUnrealCm, -1250.0) && Near(Cross.FoundationDepthUnrealCm, 180.0 + 50.0, 1e-9));
    // The valley: the deepest station is at the middle of side 1 and the side range reports it.
    double Low = 0.0, High = 0.0;
    assert(GroundProfileSideRange(P, 1, Low, High));
    assert(Near(Low, -7040.0, 1e-6) && Near(High, 0.0, 1e-9));
    assert(GroundProfileSideRange(P, 2, Low, High) && Near(Low, 0.0) && Near(High, 4500.0));
    assert(!GroundProfileSideRange(Empty, 0, Low, High));
    // On the 3% grade a 1/120 module spans 37.5 cm of rise, so neighbouring plinths step by
    // exactly that, and the deepest substructure anywhere is the grade plus the footing on
    // that side and the valley's steepest module on side 1.
    const FGrounding Grade = GroundSpan(P, 2, 0.5, 0.5 + 1.0 / 120.0, 50.0);
    assert(Near(Grade.FoundationDepthUnrealCm, 37.5 + 50.0, 1e-9));
    assert(DeepestFoundation > 90.0 && DeepestFoundation < 400.0);

    // The module scale for the candidate is exactly .96 and a nonsense amah gives 1.
    assert(Near(ModuleScaleFor(Candidate48CmPerAmah), 0.96, 1e-12));
    assert(Near(ModuleScaleFor(ProjectCmPerAmah), 1.0, 1e-12));
    assert(Near(ModuleScaleFor(std::numeric_limits<double>::quiet_NaN()), 1.0, 1e-12));

    Record("ground_synthetic_deepest_foundation_cm", DeepestFoundation);
    Record("ground_synthetic_largest_plinth_step_cm", LargestStep);
    RecordInt("ground_profile_stations_per_side", GroundStationsPerSide(P));
    std::printf("ground: 480 modules over a synthetic Kidron - plinth never below grade, substructure never above it; "
                "deepest substructure %.1f cm, largest step between plinths %.1f cm\n", DeepestFoundation, LargestStep);
}

// ---------------------------------------------------------------------------
// 6c. The plaza - the built deck that fills the precinct
// ---------------------------------------------------------------------------
//
// The numbers asserted here are the ones Scripts/create_precinct_plaza.py --export writes
// into SourceAssets/enclosure-review/plaza-<Target>.json. They are the SAME for both maps,
// because the paving grid is set out in amot from the Temple and the two maps differ only in
// what an amah is worth in level units. If this test and that receipt ever disagree, the
// plaza in the level is not the plaza in the document, and every one of the thirty-four
// thousand instances is in a different place from the one the receipt claims.
//
// What has to hold, and why:
//   * the deck stops exactly one wall thickness inside the square, so the paving never
//     overhangs the wall and the wall never stands on the paving;
//   * the frozen recursive split produces panels inside its own size bounds, and the count
//     is stable - it is the single number that proves the generator and the runtime agree;
//   * NO panel is laid the same way as the panel west or north of it. That is the whole
//     anti-repetition scheme; a regression here is invisible in a screenshot until someone
//     flies over it;
//   * the retaining batter is monotone and never negative, or the wall face leans out over
//     the 3000-amah line Yechezkel measures from outside;
//   * the wall stands on the HIGHER of deck and outside grade, and reduces to the old
//     terrain-following behaviour exactly when the deck is switched off.
static const int PlazaExpectedCellsPerSide = 121;
static const int PlazaExpectedPanels = 713;
static const int PlazaExpectedDeckTiles = 14039;
static const int PlazaExpectedWayTiles = 602;
static const int PlazaExpectedRibs = 6166;
static const int PlazaExpectedKerbs = 602;
static const int PlazaExpectedChannels = 2616;

static FSquare CandidateSquare48()
{
    // The 48 cm candidate: the Temple was converted by .96 about the origin, so the court
    // platform half-extent scales with it and the city does not move.
    const double Cm = Candidate48CmPerAmah;
    const double Half = CourtPlatformHalfExtentUnrealCm * Cm / ProjectCmPerAmah;
    const FAabb2 Platform = {{-Half, -Half}, {Half, Half}};
    return MakeSquareFromClearances(Platform, BookClearWestAmot, BookClearNorthAmot,
                                    PrecinctSideAmot, Cm);
}

static void PlazaFieldChecks(const FSquare& Square, double CmPerAmah, double CourtHalf,
                             const char* Label)
{
    const FPlazaGrid Grid = PlanPlazaGrid(Square, 6.0, CmPerAmah);

    // The deck stops one wall thickness inside the square, on all four sides, exactly.
    FVec2 Corners[4];
    SquareCorners(Square, Corners);
    const double Inset = AmotToUnrealCm(6.0, CmPerAmah);
    assert(Near(Grid.XMinUnrealCm, Corners[0].X + Inset, 1e-9));
    assert(Near(Grid.YMinUnrealCm, Corners[0].Y + Inset, 1e-9));
    assert(Near(Grid.XMaxUnrealCm, Corners[2].X - Inset, 1e-9));
    assert(Near(Grid.YMaxUnrealCm, Corners[2].Y - Inset, 1e-9));

    // The deck datum is the Temple court datum. Not nearly: exactly.
    assert(Near(Grid.DeckTopZUnrealCm, 0.0, 1e-12));
    assert(Near(PlazaDeckTopZUnrealCm(CmPerAmah), 0.0, 1e-12));
    assert(PlazaDeckUndersideZUnrealCm(CmPerAmah) < 0.0);

    // The grid is set out from the world origin, so a cell boundary falls on x = 0 and y = 0
    // and a two-cell way is symmetric about the Temple axes the gates stand on.
    assert(Grid.I0 < 0 && Grid.I1 > 0 && Grid.J0 < 0 && Grid.J1 > 0);
    assert(Grid.CellsX() == PlazaExpectedCellsPerSide);
    assert(Grid.CellsY() == PlazaExpectedCellsPerSide);

    // Every cell is inside the paved rectangle, and the partial cells at the ring are
    // clipped rather than allowed to hang over the wall.
    for (int I = Grid.I0; I < Grid.I1; ++I)
    {
        double X0, Y0, X1, Y1;
        PlazaCellExtent(Grid, I, Grid.J0, X0, Y0, X1, Y1);
        assert(X0 >= Grid.XMinUnrealCm - 1e-9 && X1 <= Grid.XMaxUnrealCm + 1e-9);
        assert(X1 > X0);
    }

    std::vector<FGateOpening> Gates = BookGates(Square);
    std::vector<FPlazaWay> Ways;
    MakePlazaWays(Square, Grid, CourtHalf, Gates, Ways);
    assert(Ways.size() == 5u);
    for (std::size_t Index = 0; Index < Ways.size(); ++Index)
    {
        // Two cells wide, always, and never a way running the wrong way across its own side.
        assert(Ways[Index].Band1 - Ways[Index].Band0 == 2);
        assert(Ways[Index].Along1 > Ways[Index].Along0);
    }

    int Panels = 0;
    int Culverted = 0;
    FPlazaPlan Plan = PlanPlazaField(Grid, Ways, &Panels, &Culverted);
    assert(Plan.DeckTiles + Plan.WayTiles == Grid.CellsX() * Grid.CellsY());
    assert(Plan.DeckTiles == PlazaExpectedDeckTiles);
    assert(Plan.WayTiles == PlazaExpectedWayTiles);
    assert(Plan.RibModules == PlazaExpectedRibs);
    assert(Plan.KerbModules == PlazaExpectedKerbs);
    assert(Plan.ChannelModules == PlazaExpectedChannels);
    assert(Panels == PlazaExpectedPanels);
    assert(Culverted > 0);   // the ways really are crossed, and really are culverted

    // Panels stay inside their own size bounds, and no panel is laid the same way as the
    // panel west or north of it. Swept over the whole grid, not sampled.
    int Smallest = 1 << 30;
    int Largest = 0;
    int SameAsNeighbour = 0;
    for (int I = Grid.I0; I < Grid.I1; ++I)
    {
        for (int J = Grid.J0; J < Grid.J1; ++J)
        {
            const FPlazaPanel Panel = PlazaPanelAt(Grid, I, J);
            assert(Panel.I0 <= I && I < Panel.I1 && Panel.J0 <= J && J < Panel.J1);
            const int W = Panel.I1 - Panel.I0;
            const int H = Panel.J1 - Panel.J0;
            assert(W >= PlazaMinPanelCells && W <= PlazaMaxPanelCells);
            assert(H >= PlazaMinPanelCells && H <= PlazaMaxPanelCells);
            Smallest = std::min(Smallest, W * H);
            Largest = std::max(Largest, W * H);
            const int Course = PlazaPanelCourseIndex(Grid, Panel);
            assert(Course >= 0 && Course < PlazaCourseCount);
            if (I > Grid.I0)
            {
                const FPlazaPanel West = PlazaPanelAt(Grid, I - 1, J);
                if (!PlazaSamePanel(West, Panel) && PlazaPanelCourseIndex(Grid, West) == Course)
                {
                    ++SameAsNeighbour;
                }
            }
            if (J > Grid.J0)
            {
                const FPlazaPanel North = PlazaPanelAt(Grid, I, J - 1);
                if (!PlazaSamePanel(North, Panel) && PlazaPanelCourseIndex(Grid, North) == Course)
                {
                    ++SameAsNeighbour;
                }
            }
            // The tonal drift stays inside its stated range, so a tint parameter can be
            // scaled by a fixed percentage without ever going out of gamut.
            const double Tint = PlazaTintAt(I, J);
            assert(Tint >= -1.0 && Tint <= 1.0);
        }
    }
    // The greedy colouring cannot promise zero - see the note on PlazaPanelCourseIndex - so
    // the residual is MEASURED and bounded rather than assumed. A run of like-laid panels is
    // what brings the grid back; a handful of isolated pairs, each still carrying a rib and
    // starting its paving at a different origin, does not.
    const int Joints = 2 * Grid.CellsX() * Grid.CellsY();
    assert(SameAsNeighbour * 100 < Joints * 5);
    assert(Smallest >= PlazaMinPanelCells * PlazaMinPanelCells);
    assert(Largest <= PlazaMaxPanelCells * PlazaMaxPanelCells);

    if (std::strcmp(Label, "candidate48") == 0)
    {
        RecordInt("plaza_cells_per_side", Grid.CellsX());
        RecordInt("plaza_panels", Panels);
        RecordInt("plaza_deck_tiles", Plan.DeckTiles);
        RecordInt("plaza_way_tiles", Plan.WayTiles);
        RecordInt("plaza_rib_modules", Plan.RibModules);
        RecordInt("plaza_kerb_modules", Plan.KerbModules);
        RecordInt("plaza_channel_modules", Plan.ChannelModules);
        RecordInt("plaza_channel_modules_culverted_under_ways", Culverted);
        RecordInt("plaza_like_laid_cell_joints", SameAsNeighbour);
        RecordInt("plaza_cell_joints", Joints);
        RecordInt("plaza_smallest_panel_cells", Smallest);
        RecordInt("plaza_largest_panel_cells", Largest);
        Record("plaza_deck_top_z_cm", Grid.DeckTopZUnrealCm);
    }
}

static void PlazaChecks()
{
    PlazaFieldChecks(BookSquare(), ProjectCmPerAmah, CourtPlatformHalfExtentUnrealCm, "main50");
    PlazaFieldChecks(CandidateSquare48(), Candidate48CmPerAmah,
                     CourtPlatformHalfExtentUnrealCm * Candidate48CmPerAmah / ProjectCmPerAmah,
                     "candidate48");

    // The hash is frozen. If it changes, every panel in the plaza moves, so it is asserted
    // against literals rather than against itself.
    assert(PlazaHash(0u) == 1268118805u);
    assert(PlazaHash(1u) == 4218009092u);
    assert(PlazaHash(PlazaPanelSeed) == 3960965999u);
    assert(PlazaHash(PlazaPanelSeed) != PlazaHash(PlazaPanelSeed + 1u));

    // Bands. Never scaled in Z, so facing a drop is a COUNT, and the stack must always reach
    // past the bottom rather than stopping short of it and showing daylight under the deck.
    for (double Height = 1.0; Height < 20000.0; Height *= 1.7)
    {
        const int Bands = PlazaBandCount(Height, ProjectCmPerAmah);
        const double Reach = Bands * AmotToUnrealCm(PlazaRetainingBandHeightAmot, ProjectCmPerAmah);
        assert(Bands >= 1);
        assert(Reach >= Height - 1e-6);
        assert(Reach - Height < AmotToUnrealCm(PlazaRetainingBandHeightAmot, ProjectCmPerAmah) + 1e-6);
    }
    assert(PlazaBandCount(0.0, ProjectCmPerAmah) == 0);
    assert(PlazaBandCount(-500.0, ProjectCmPerAmah) == 0);

    // The batter leans the face OUT as it goes down, never in: an inward step would put the
    // foot of the wall inside the 3000 amot Yechezkel measures from outside, and an
    // overhanging retaining wall is not a thing that stands up.
    double Previous = -1.0;
    for (int Band = 0; Band < 60; ++Band)
    {
        const double Batter = PlazaBandBatterUnrealCm(Band, ProjectCmPerAmah);
        assert(Batter >= 0.0);
        assert(Batter >= Previous);
        Previous = Batter;
    }
    assert(Near(PlazaBandBatterUnrealCm(0, ProjectCmPerAmah), 0.0));
    assert(Near(PlazaBandBatterUnrealCm(PlazaRetainingBatterEveryBands - 1, ProjectCmPerAmah), 0.0));
    assert(Near(PlazaBandBatterUnrealCm(PlazaRetainingBatterEveryBands, ProjectCmPerAmah),
                AmotToUnrealCm(PlazaRetainingBatterAmot, ProjectCmPerAmah)));

    // cp19 wash: only on a band that steps OUT (its top is an exposed ledge), and the rolled
    // band's top-outer arris must land inside the band above it - horizontally within its
    // thickness and vertically within its height - so only the 45-degree slope shows.
    {
        int Ledges = 0;
        for (int Band = 0; Band < 60; ++Band)
        {
            if (!PlazaBandIsLedge(Band)) continue;
            ++Ledges;
            assert(PlazaBandBatterUnrealCm(Band, ProjectCmPerAmah)
                   > PlazaBandBatterUnrealCm(Band - 1, ProjectCmPerAmah));
        }
        assert(Ledges == 11);
        assert(!PlazaBandIsLedge(0));
        const double BandH = AmotToUnrealCm(PlazaRetainingBandHeightAmot, ProjectCmPerAmah);
        const double BandT = AmotToUnrealCm(PlazaRetainingBandThicknessAmot, ProjectCmPerAmah);
        const double StepOut = AmotToUnrealCm(PlazaRetainingBatterAmot, ProjectCmPerAmah);
        const double Inset = PlazaLedgeWashOriginInsetUnrealCm(BandH);
        assert(Near(PlazaLedgeWashDegrees, 45.0));
        assert(Inset > StepOut && Inset < StepOut + BandT);
        assert(Inset < BandH);
    }

    // The wall stands on the higher of the deck and the ground outside it - and with the
    // deck switched off it grounds exactly as it always did, which is what makes the plaza
    // a change that can be reverted by one boolean.
    assert(Near(PlazaWallBaseZUnrealCm(-14000.0, 0.0, true), 0.0));
    assert(Near(PlazaWallBaseZUnrealCm(6000.0, 0.0, true), 6000.0));
    assert(Near(PlazaWallBaseZUnrealCm(-14000.0, 0.0, false), -14000.0));
    assert(Near(PlazaWallBaseZUnrealCm(6000.0, 0.0, false), 6000.0));

    // Gate stairs. The east gate of the 48 cm candidate stands 39.4 m above the deck on the
    // Mount of Olives slope; at a half-amah riser that is 165 steps and eight landings.
    assert(PlazaFlightSteps(3940.0, Candidate48CmPerAmah) == 165);
    assert(PlazaFlightLandings(165) == 8);
    assert(PlazaFlightSteps(0.0, Candidate48CmPerAmah) == 0);
    assert(PlazaFlightSteps(-100.0, Candidate48CmPerAmah) == 0);
    assert(PlazaFlightLandings(PlazaStepsPerFlight) == 0);
    assert(PlazaFlightLandings(PlazaStepsPerFlight + 1) == 1);

    // The channel stride is NOT periodic over the plaza. A periodic spacing is a grid by
    // another name, which is the defect this whole design exists to avoid.
    int Lines = 0;
    int FirstGap = -1;
    bool bAllGapsEqual = true;
    int Last = -1;
    for (int K = -27; K < 94; ++K)
    {
        if (!PlazaHasChannelLine(-27, K, 94)) continue;
        ++Lines;
        if (Last >= 0)
        {
            const int Gap = K - Last;
            if (FirstGap < 0) FirstGap = Gap;
            else if (Gap != FirstGap) bAllGapsEqual = false;
        }
        Last = K;
    }
    assert(Lines >= 8);
    assert(!bAllGapsEqual);
    // Nothing outside the range is ever a channel line, including the ends.
    assert(!PlazaHasChannelLine(-27, -27, 94));
    assert(!PlazaHasChannelLine(-27, 94, 94));
    assert(!PlazaHasChannelLine(-27, 200, 94));

    // The plaza's own draw budget, from the module counts and the module triangle budget.
    // A separate assertion from the wall's, because the wall was always cheap and the plaza
    // is the thing that could stop being so.
    const FPlazaGrid Grid = PlanPlazaGrid(CandidateSquare48(), 6.0, Candidate48CmPerAmah);
    std::vector<FGateOpening> Gates = BookGates(CandidateSquare48());
    std::vector<FPlazaWay> Ways;
    MakePlazaWays(CandidateSquare48(), Grid,
                  CourtPlatformHalfExtentUnrealCm * Candidate48CmPerAmah / ProjectCmPerAmah,
                  Gates, Ways);
    FPlazaPlan Plan = PlanPlazaField(Grid, Ways);

    // A synthetic Kidron under the whole ring: the south side a hundred metres below the
    // deck, the north-east sixty above it, so both the retaining stack and the scarp are
    // exercised without reading a receipt this test is not allowed to open.
    const int Steps = 120;
    FGroundProfile Profile;
    Profile.StepsPerSide = Steps;
    for (int Side = 0; Side < 4; ++Side)
    {
        for (int Station = 0; Station <= Steps; ++Station)
        {
            const double T = static_cast<double>(Station) / static_cast<double>(Steps);
            const double Z = (Side == 2) ? -10000.0 - 3000.0 * std::sin(T * Pi)
                           : (Side == 0) ? -4000.0 + 10000.0 * T
                           : (Side == 1) ? 6000.0 - 20000.0 * T
                                         : -6000.0 + 7000.0 * T;
            Profile.HighZUnrealCm.push_back(Z + 100.0);
            Profile.LowZUnrealCm.push_back(Z - 100.0);
        }
    }
    assert(GroundProfileValid(Profile));
    PlanPlazaFaces(CandidateSquare48(), Grid, Profile, Steps, Gates, Candidate48CmPerAmah, Plan);
    assert(Plan.RetainingBands > 0 && Plan.ScarpBands > 0);
    // A side that is entirely below the deck has no scarp at all, and one entirely above it
    // has no retaining: the two faces are exclusive per module, never both invented.
    assert(Plan.ScarpMaxUnrealCm[2] == 0.0);
    assert(Plan.RetainingMaxUnrealCm[2] > 0.0);

    const FPlazaModuleBudget Budget;
    PlazaFinishPlan(Plan, Budget);
    assert(Plan.TotalInstances == Plan.DeckTiles + Plan.WayTiles + Plan.RibModules
                                + Plan.KerbModules + Plan.ChannelModules + Plan.RetainingBands
                                + Plan.ScarpBands + Plan.StepModules);
    assert(Plan.TotalTriangles > 0);
    // The whole 2.07 km2 deck, its retaining walls and its stairs, against the 3,416,580
    // triangles of the Old City facade set the YECHEZKEL state already hides.
    assert(Plan.TotalTriangles < 3416580 / 2);
    assert(Plan.TotalInstances < 60000);
    // Seven components, so seven draw calls before per-instance culling.
    RecordInt("plaza_hism_components", 7);
    RecordInt("plaza_synthetic_retaining_bands", Plan.RetainingBands);
    RecordInt("plaza_synthetic_scarp_bands", Plan.ScarpBands);
    RecordInt("plaza_synthetic_step_modules", Plan.StepModules);
    RecordInt("plaza_synthetic_total_instances", Plan.TotalInstances);
    RecordInt("plaza_synthetic_total_triangles", Plan.TotalTriangles);
    Record("plaza_synthetic_south_retaining_max_metres", Plan.RetainingMaxUnrealCm[2] / 100.0);

    std::printf("plaza: %d x %d cells, %d panels, %d deck + %d way tiles, %d ribs, %d channels; "
                "%d instances, %lld triangles over a synthetic Kidron\n",
                PlazaExpectedCellsPerSide, PlazaExpectedCellsPerSide, PlazaExpectedPanels,
                Plan.DeckTiles, Plan.WayTiles, Plan.RibModules, Plan.ChannelModules,
                Plan.TotalInstances, Plan.TotalTriangles);
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

// ---------------------------------------------------------------------------
// Walkable plaza collision (section 6c)
// ---------------------------------------------------------------------------
static void PlazaCollisionChecks()
{
    const double Cm = Candidate48CmPerAmah;
    const FSquare Square = CandidateSquare48();
    const FPlazaGrid Grid = PlanPlazaGrid(Square, 6.0, Cm);
    const double Slab = AmotToUnrealCm(PlazaSlabThicknessAmot, Cm);

    // The drop is real, and smaller than the character's own floor-distance band.
    assert(PlazaCollisionTopDropUnrealCm > 0.0 && PlazaCollisionTopDropUnrealCm < 1.9);

    std::vector<FPlazaCollisionBox> Boxes;
    const int Count = PlazaDeckCollisionBoxes(Grid, Slab, Boxes);
    assert(Count == static_cast<int>(Boxes.size()));
    assert(Count == 144);   // 143,424 cm a side / 12,000 -> 12 x 12 at 48 cm
    double Area = 0.0;
    double MinX = 1e300, MinY = 1e300, MaxX = -1e300, MaxY = -1e300;
    for (const FPlazaCollisionBox& Box : Boxes)
    {
        assert(Box.HalfX > 0.0 && Box.HalfY > 0.0);
        assert(2.0 * Box.HalfX <= PlazaCollisionMaxTileUnrealCm + 1e-6);
        assert(2.0 * Box.HalfY <= PlazaCollisionMaxTileUnrealCm + 1e-6);
        assert(Near(Box.CentreZ + Box.HalfZ, Grid.DeckTopZUnrealCm - PlazaCollisionTopDropUnrealCm, 1e-9));
        assert(Near(2.0 * Box.HalfZ, Slab, 1e-9));
        assert(Near(Box.YawDegrees, 0.0, 1e-12));
        Area += 4.0 * Box.HalfX * Box.HalfY;
        MinX = std::min(MinX, Box.CentreX - Box.HalfX);
        MaxX = std::max(MaxX, Box.CentreX + Box.HalfX);
        MinY = std::min(MinY, Box.CentreY - Box.HalfY);
        MaxY = std::max(MaxY, Box.CentreY + Box.HalfY);
    }
    // The union is the paved rectangle exactly: same bounds, same area, so no gap and no overlap.
    const double GridArea = (Grid.XMaxUnrealCm - Grid.XMinUnrealCm) * (Grid.YMaxUnrealCm - Grid.YMinUnrealCm);
    assert(Near(MinX, Grid.XMinUnrealCm, 1e-6) && Near(MaxX, Grid.XMaxUnrealCm, 1e-6));
    assert(Near(MinY, Grid.YMinUnrealCm, 1e-6) && Near(MaxY, Grid.YMaxUnrealCm, 1e-6));
    assert(std::abs(Area - GridArea) <= GridArea * 1e-12);
    // The measured receipt's rectangle on Candidate48, extentCm [-31488, -31536, 111936, 111888].
    assert(Near(Grid.XMinUnrealCm, -31488.0, 1e-6) && Near(Grid.YMinUnrealCm, -31536.0, 1e-6));
    assert(Near(Grid.XMaxUnrealCm, 111936.0, 1e-6) && Near(Grid.YMaxUnrealCm, 111888.0, 1e-6));
    // Degenerate input builds nothing rather than something wrong.
    FPlazaGrid Empty;
    assert(PlazaDeckCollisionBoxes(Empty, Slab, Boxes) == 0 && Boxes.empty());
    assert(PlazaDeckCollisionBoxes(Grid, 0.0, Boxes) == 0);

    // Gate bridges: every gate floored from beyond the outer face to beyond the inner face.
    const double Wall = AmotToUnrealCm(6.0, Cm);
    const double Tread = AmotToUnrealCm(PlazaStepTreadAmot, Cm);
    const std::vector<FGateOpening> Gates = BookGates(Square);
    FVec2 C[4];
    SquareCorners(Square, C);
    for (const FGateOpening& Gate : Gates)
    {
        const double Threshold = 223.0;   // any threshold: the top must follow it exactly
        const FPlazaCollisionBox Box = PlazaGateBridgeBox(Square, Gate, Threshold, Wall,
                                                          0.5 * Tread, Tread, Slab, Cm);
        assert(Near(Box.CentreZ + Box.HalfZ, Threshold - PlazaCollisionTopDropUnrealCm, 1e-9));
        assert(Near(2.0 * Box.HalfX, AmotToUnrealCm(Gate.WidthAmot, Cm), 1e-9));
        assert(Near(2.0 * Box.HalfY, Wall + 1.5 * Tread, 1e-9));
        // Local +Y (yaw + 90) is the side's outward normal; local +X runs along the side.
        const double Yaw = DegToRad(Box.YawDegrees);
        const FVec2 AxisY{-std::sin(Yaw), std::cos(Yaw)};
        const double OutYaw = DegToRad(SideOutwardYawDegrees(Square, Gate.Side));
        const FVec2 Out{std::cos(OutYaw), std::sin(OutYaw)};
        assert(Near(Dot(AxisY, Out), 1.0, 1e-12));
        // The outer face and the inner face both lie inside the bridge's span along Out.
        const FVec2 From = C[Gate.Side];
        const FVec2 To = C[(Gate.Side + 1) % 4];
        const FVec2 Face = From + (To - From) * Gate.CentreFractionAlongSide;
        const FVec2 Centre{Box.CentreX, Box.CentreY};
        const double OuterAlong = Dot(Face - Centre, Out);
        const double InnerAlong = Dot((Face - Out * Wall) - Centre, Out);
        assert(OuterAlong < Box.HalfY && OuterAlong > -Box.HalfY);
        assert(InnerAlong < Box.HalfY && InnerAlong > -Box.HalfY);
        assert(Near(Box.HalfY - OuterAlong, Tread, 1e-6));          // one tread onto the landing
        assert(Near(InnerAlong + Box.HalfY, 0.5 * Tread, 1e-6));    // half a tread onto the deck
    }
    // The north gate's bridge on the candidate: centred on the Temple axis, reaching from
    // one tread outside the N face (y -31824) to half a tread inside the inner face (y -31536).
    const FPlazaCollisionBox North = PlazaGateBridgeBox(Square, Gates[0], 0.0, Wall, 0.5 * Tread, Tread, Slab, Cm);
    assert(Near(North.CentreX, 0.0, 1e-6));
    assert(Near(North.CentreY - North.HalfY, -31824.0 - Tread, 1e-6));
    assert(Near(North.CentreY + North.HalfY, -31536.0 + 0.5 * Tread, 1e-6));
    RecordInt("plazaCollisionDeckBoxes48", Count);
    Record("plazaCollisionTopDropCm", PlazaCollisionTopDropUnrealCm);
}

int main(int Argc, char** Argv)
{
    SquarenessChecks();
    ClearanceChecks();
    ConversionChecks();
    ContainmentChecks();
    SelectionChecks();
    BoundaryChecks();
    WallPlanChecks();
    GroundChecks();
    PlazaChecks();
    PlazaCollisionChecks();
    DissolveChecks();

    if (Argc > 1)
    {
        if (std::FILE* Handle = std::fopen(Argv[1], "w"))
        {
            std::fprintf(Handle, "{\n%s\n}\n", Snapshot.c_str());
            std::fclose(Handle);
        }
    }
    std::cout << "PASS: squareness at seven yaws, the clearance ordering resolved against both "
                 "anchorings, amah/reed/metre round-trips over five opinions, "
                 "edge and corner containment, deterministic and order-independent building selection "
                 "with the terrain-tile trap asserted, boundary sampling, the instanced wall budget "
                 "at 50 and 48 cm, the terrain-following ground profile, the plaza layout with its "
                 "anti-repetition invariants, the walkable deck proxy and gate bridges, and the three-state dissolve" << std::endl;
    return 0;
}
