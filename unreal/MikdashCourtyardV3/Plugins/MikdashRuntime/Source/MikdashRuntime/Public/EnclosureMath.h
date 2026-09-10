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
        {"feinstein",   "R' Moshe Feinstein, Igros Moshe OC I:136 - amah of about 21 1/4 inches", 54.0},
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

/** The amah the BOOK itself works in, recovered from its own two metric conversions rather
 * than from a stated shiur (it never states one): Ketz HaYamin on Yechezkel 42:16 gives the
 * 3000-amah side as "a kilometre and four hundred and forty metres approximately"
 * (1440 m / 3000 = 48.0 cm), and on Middot 2:3 it glosses a half-amah step as "about
 * twenty-four cm" (2 x 24 = 48). It coincides with R' Chaim Naeh's 48 cm, which is why the
 * table's smallest entry is also the book's. The LEVEL is nonetheless baked at 50; see
 * ProjectCmPerAmah immediately below and SourceAssets/enclosure-review/sources.md. */
constexpr double BookImpliedAmahRealCm = 48.0;
/** The metre figure the book prints for one side of the precinct, quoted so the arithmetic
 * above can be checked against it rather than merely asserted. */
constexpr double BookStatedPrecinctSideMetres = 1440.0;

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

/** The isolated 48 cm candidate map is baked at the book's own amah; its court platform
 * half-extent is 8100 x .96. Named here so the release script, the actor and the test agree
 * on the second target without restating the number. */
constexpr double Candidate48CmPerAmah = 48.0;

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

/** Axis-aligned box in level units. Declared here rather than with the containment
 * helpers because the clearance arithmetic below needs it. */
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

// ---------------------------------------------------------------------------
// 2b. Clearances - the number the book's diagram actually states
// ---------------------------------------------------------------------------
//
// The book does not place the 3000 by giving a centre. It gives the OPEN GROUND between
// the court and each of the four walls, and it states an ORDER for those four: largest
// south, then east, then north, least west. That order is Mishnah Middot 2:1's
// "rubo min hadarom, sheni lo min hamizrach, shlishi lo min hatzafon, umi'uto min
// hama'arav", carried to the Mount by Mishkenei Elyon 196 m.1 and by Lishchno Tidreshu
// fig. 2'2 (p. 113).
//
// THAT ORDER IS A CONSTRAINT ON THE COURT ENVELOPE, NOT A FREE CHOICE, and the arithmetic
// is worth spelling out because getting it wrong is what broke this file's first test:
//
//     West  + EnvelopeEastWest   + East  = Side
//     North + EnvelopeNorthSouth + South = Side
//   =>  South - East = (West + EnvelopeEastWest) - (North + EnvelopeNorthSouth)
//
// So with West < North - which "least west, third north" demands - South > East is
// possible ONLY IF the court envelope is wider east-west than it is deep north-south, by
// more than the west/north difference. Middot's own Azarah is exactly that shape, 187 amot
// east-west by 135 north-south (Middot 5:1), which is why the order comes out for the
// 500-amah Har HaBayit. The book's fig. 2'2 envelope is likewise wider than deep, about
// 351 x 346, giving 2149 east and 2153 south.
//
// This project's MEASURED court supporting platform is 324 x 324 amot - SQUARE
// (SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json, inputs.courtPlatformBoundsCm
// = +-8100 Unreal cm on BOTH axes). On a square envelope the identity collapses to
// South - East = West - North, so West < North forces South < East, and the book's order
// cannot hold - it inverts by exactly the west/north difference of one amah. That is a
// real, small, reportable consequence of anchoring on measured geometry instead of on the
// diagram, not something to paper over: enclosure-design.json's offsetRule currently claims
// the order is "preserved" while its own numbers (east 2176, south 2175) show it inverted
// by 1 amah = 50 cm on a 150,000 cm side. Both anchorings are therefore offered here, and
// the order is a value that gets CLASSIFIED and reported, never assumed.

/** The measured court supporting platform half-extent, both axes, in level units.
 * enclosure-design.json inputs.courtPlatformBoundsCm. 8100 cm = 162 amot, so 324 square. */
constexpr double CourtPlatformHalfExtentUnrealCm = 8100.0;
/** Middot 5:1: the Azarah is 187 amot east-west by 135 north-south. */
constexpr double MiddotAzarahEastWestAmot = 187.0;
constexpr double MiddotAzarahNorthSouthAmot = 135.0;
/** The envelope Lishchno Tidreshu fig. 2'2 is drawn around, read off the diagram; the
 * book's own east/south remainders (2149 / 2153) only reproduce at these values. */
constexpr double BookDiagramEnvelopeEastWestAmot = 351.0;
constexpr double BookDiagramEnvelopeNorthSouthAmot = 346.0;
/** The two clearances the diagram states outright; the other two are remainders. */
constexpr double BookClearWestAmot = 500.0;
constexpr double BookClearNorthAmot = 501.0;

/** Open ground between the court envelope and each wall, in amot. */
struct FClearances
{
    double WestAmot = 0.0;
    double NorthAmot = 0.0;
    double EastAmot = 0.0;
    double SouthAmot = 0.0;
};

/** The two remainders, given the two stated clearances and the envelope. Pure arithmetic:
 * this is the whole of the "east and south fall out of the 3000" step. */
inline FClearances ClearancesFromStated(double ClearWestAmot, double ClearNorthAmot,
                                        double EnvelopeEastWestAmot, double EnvelopeNorthSouthAmot,
                                        double SideAmot)
{
    FClearances C;
    C.WestAmot = ClearWestAmot;
    C.NorthAmot = ClearNorthAmot;
    C.EastAmot = SideAmot - ClearWestAmot - EnvelopeEastWestAmot;
    C.SouthAmot = SideAmot - ClearNorthAmot - EnvelopeNorthSouthAmot;
    return C;
}

/** The book's diagram in its own terms: 500 west, 501 north, envelope 351 x 346, so
 * 2149 east and 2153 south. This is the set that satisfies the stated order. */
inline FClearances BookDiagramClearances(double SideAmot = PrecinctSideAmot)
{
    return ClearancesFromStated(BookClearWestAmot, BookClearNorthAmot,
                                BookDiagramEnvelopeEastWestAmot, BookDiagramEnvelopeNorthSouthAmot,
                                SideAmot);
}

/** Middot 2:1 with Middot 5:1's Azarah: 100 west, 213 east, 115 north, 250 south around a
 * 187 x 135 Azarah inside 500. These four are a received reckoning (Rambam's commentary to
 * Middot 2:1, Tiferes Yisrael) and not a derivation - only their two sums are forced. */
inline FClearances MiddotHarHaBayitClearances()
{
    FClearances C;
    C.WestAmot = 100.0;
    C.NorthAmot = 115.0;
    C.EastAmot = 213.0;
    C.SouthAmot = 250.0;
    return C;
}

/** Measured clearances of an actual placed square about an actual court envelope. This is
 * what the release receipt reports; nothing here is assumed. Only meaningful at yaw 0,
 * where the square's sides are the cardinal directions. */
inline FClearances ClearancesOf(const FSquare& Square, const FAabb2& CourtEnvelopeUnrealCm,
                                double WorldCmPerAmah = ProjectCmPerAmah)
{
    const double H = Square.HalfSideUnrealCm;
    const FVec2& Centre = Square.CentreUnrealCm;
    FClearances C;
    C.WestAmot  = UnrealCmToAmot(CourtEnvelopeUnrealCm.Min.X - (Centre.X - H), WorldCmPerAmah);
    C.EastAmot  = UnrealCmToAmot((Centre.X + H) - CourtEnvelopeUnrealCm.Max.X, WorldCmPerAmah);
    C.NorthAmot = UnrealCmToAmot(CourtEnvelopeUnrealCm.Min.Y - (Centre.Y - H), WorldCmPerAmah);
    C.SouthAmot = UnrealCmToAmot((Centre.Y + H) - CourtEnvelopeUnrealCm.Max.Y, WorldCmPerAmah);
    return C;
}

/** How a set of four clearances stands to the Middot order. Reported, not asserted. */
enum class EClearanceOrder : int
{
    /** south > east > north > west, exactly as Middot 2:1 states it. */
    Middot = 0,
    /** east > south > north > west: the two large ones swapped. This is what anchoring on
     * a SQUARE court envelope with west < north necessarily produces. */
    EastSouthSwapped = 1,
    /** Anything else - the diagram has not been reproduced at all. */
    Other = 2,
};

inline EClearanceOrder ClassifyClearanceOrder(const FClearances& C)
{
    if (!(C.NorthAmot > C.WestAmot)) return EClearanceOrder::Other;
    if (!(C.EastAmot > C.NorthAmot) || !(C.SouthAmot > C.NorthAmot)) return EClearanceOrder::Other;
    if (C.SouthAmot > C.EastAmot) return EClearanceOrder::Middot;
    if (C.EastAmot > C.SouthAmot) return EClearanceOrder::EastSouthSwapped;
    return EClearanceOrder::Other;   // an exact tie states no order at all
}

/** South minus east, in amot. Positive is the Middot order; the magnitude is the honest
 * size of the departure, which the review document quotes in centimetres. */
inline double ClearanceOrderMarginAmot(const FClearances& C) { return C.SouthAmot - C.EastAmot; }

/** The identity the two sums must satisfy. Returns the worst residual in amot. */
inline double ClearanceClosureErrorAmot(const FClearances& C, double EnvelopeEastWestAmot,
                                        double EnvelopeNorthSouthAmot, double SideAmot)
{
    const double EastWest = std::abs(C.WestAmot + EnvelopeEastWestAmot + C.EastAmot - SideAmot);
    const double NorthSouth = std::abs(C.NorthAmot + EnvelopeNorthSouthAmot + C.SouthAmot - SideAmot);
    return std::max(EastWest, NorthSouth);
}

/** Place a square so a measured court envelope sits inside it at the given west/north
 * clearances. The general form of MakeSquareFromNorthWestClearance, kept separate because
 * the caller here supplies the envelope it measured rather than a bare corner. */
inline FSquare MakeSquareFromClearances(const FAabb2& CourtEnvelopeUnrealCm,
                                        double ClearWestAmot, double ClearNorthAmot,
                                        double SideAmot,
                                        double WorldCmPerAmah = ProjectCmPerAmah,
                                        double YawDegrees = 0.0)
{
    return MakeSquareFromNorthWestClearance(CourtEnvelopeUnrealCm.Min, ClearWestAmot, ClearNorthAmot,
                                            SideAmot, WorldCmPerAmah, YawDegrees);
}

/** Middot's 500-amah Har HaBayit placed about the Azarah centre at the received
 * 100/115/213/250 clearances. This is the OTHER side of the dispute, drawn as its own ring
 * so a viewer sees 500 amot and 3000 amot at once instead of being told which is right. */
inline FSquare MakeMiddotHarHaBayitSquare(FVec2 AzarahCentreUnrealCm,
                                          double WorldCmPerAmah = ProjectCmPerAmah,
                                          double YawDegrees = 0.0)
{
    const FClearances C = MiddotHarHaBayitClearances();
    const double HalfEastWest = AmotToUnrealCm(MiddotAzarahEastWestAmot * 0.5, WorldCmPerAmah);
    const double HalfNorthSouth = AmotToUnrealCm(MiddotAzarahNorthSouthAmot * 0.5, WorldCmPerAmah);
    const FAabb2 Azarah = {{AzarahCentreUnrealCm.X - HalfEastWest, AzarahCentreUnrealCm.Y - HalfNorthSouth},
                           {AzarahCentreUnrealCm.X + HalfEastWest, AzarahCentreUnrealCm.Y + HalfNorthSouth}};
    return MakeSquareFromClearances(Azarah, C.WestAmot, C.NorthAmot, MiddotHarHaBayitAmot,
                                    WorldCmPerAmah, YawDegrees);
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

/** Where a world point projects onto one side, as a fraction 0..1 from that side's START
 * corner (corner i, walking clockwise). The book gives gate positions as world coordinates
 * on the Temple's own axes - "the east gate is on the east-west axis" - so this is the
 * function that turns a stated gate position into an FGateOpening fraction. Values outside
 * 0..1 mean the point does not project onto that side and are returned unclamped, because
 * silently clamping a mis-specified gate onto a corner is worse than a visible number. */
inline double FractionAlongSide(const FSquare& Square, int Side, const FVec2& WorldPoint)
{
    FVec2 C[4];
    SquareCorners(Square, C);
    const int Index = ((Side % 4) + 4) % 4;
    const FVec2 From = C[Index];
    const FVec2 To = C[(Index + 1) % 4];
    const FVec2 Edge = To - From;
    const double LengthSquared = Dot(Edge, Edge);
    if (!(LengthSquared > 0.0)) return 0.0;
    return Dot(WorldPoint - From, Edge) / LengthSquared;
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
// 5b. Ground profile - how the wall follows the terrain
// ---------------------------------------------------------------------------
//
// The instanced wall used to sit on the level plane (Z 0), which floats it over the Kidron
// (the ground there is 60-90 m below the Mount deck) and buries it on the slopes above. The
// fix is a GROUND PROFILE: the terrain height under the wall footprint, sampled offline by
// Scripts/create_enclosure.py from the OSM terrain grid (jerusalem.json `terrain.heights`,
// amot, 257 x 257, step 50 amot, origin -6400 amot, converted with the level's baked
// alignment) and, where that grid disagrees with the level's own tiles, from the
// FutureMountV1 tile receipts. The profile is baked onto AMikdashEnclosure by the release
// script as two float arrays; nothing here traces against collision, so the result is the
// same in a commandlet, in PIE and in a cooked build.
//
// STATIONS. Each side is divided into StepsPerSide equal steps; station k of side s is at
// fraction k / StepsPerSide from the side's START corner (corner s, see ESide), and there
// are StepsPerSide + 1 stations per side so both corners are stations. Two values per
// station: the HIGHEST and the LOWEST ground under the wall's footprint across its
// thickness at that station. Four sides are stored consecutively.
//
// POLICY (authored; the sources say nothing about foundations - see sources.md section 4b).
// A module stands with its plinth on the HIGHEST ground it crosses, so the full six-amah
// section is always exposed and never buried; an authored substructure (a plain box, the
// foundation module) fills from the LOWEST ground the module crosses, less a footing, up to
// the plinth. That is what "no gap shows" means numerically: FoundationBottomZ <= every
// ground sample under the module - Footing, and BaseZ >= every ground sample.

struct FGroundProfile
{
    int StepsPerSide = 0;
    /** 4 * (StepsPerSide + 1) values, side-major, station-minor. */
    std::vector<double> HighZUnrealCm;
    std::vector<double> LowZUnrealCm;
};

inline int GroundStationsPerSide(const FGroundProfile& Profile)
{
    return Profile.StepsPerSide > 0 ? Profile.StepsPerSide + 1 : 0;
}

/** A profile is usable only when it is complete and finite. An unusable profile makes every
 * grounding fall back to the level plane, which is the old behaviour and is reported. */
inline bool GroundProfileValid(const FGroundProfile& Profile)
{
    const int Stations = GroundStationsPerSide(Profile);
    if (Stations <= 0) return false;
    const std::size_t Wanted = static_cast<std::size_t>(Stations) * 4u;
    if (Profile.HighZUnrealCm.size() != Wanted || Profile.LowZUnrealCm.size() != Wanted) return false;
    for (std::size_t Index = 0; Index < Wanted; ++Index)
    {
        if (!std::isfinite(Profile.HighZUnrealCm[Index]) || !std::isfinite(Profile.LowZUnrealCm[Index])) return false;
        if (Profile.LowZUnrealCm[Index] > Profile.HighZUnrealCm[Index] + 1e-9) return false;
    }
    return true;
}

/** Linear interpolation of one array of a valid profile at a fraction along a side. The
 * fraction is clamped to 0..1; the side index wraps. */
inline double SampleProfileArray(const std::vector<double>& Values, int StepsPerSide, int Side, double Fraction)
{
    const int Stations = StepsPerSide + 1;
    const int SideIndex = ((Side % 4) + 4) % 4;
    const double F = std::max(0.0, std::min(1.0, std::isfinite(Fraction) ? Fraction : 0.0));
    const double Position = F * static_cast<double>(StepsPerSide);
    int K = static_cast<int>(std::floor(Position));
    if (K >= StepsPerSide) K = StepsPerSide - 1;
    if (K < 0) K = 0;
    const double T = Position - static_cast<double>(K);
    const std::size_t Base = static_cast<std::size_t>(SideIndex) * static_cast<std::size_t>(Stations);
    const double A = Values[Base + static_cast<std::size_t>(K)];
    const double B = Values[Base + static_cast<std::size_t>(K) + 1u];
    return A + (B - A) * T;
}

inline double SampleGroundHighZ(const FGroundProfile& Profile, int Side, double Fraction)
{
    if (!GroundProfileValid(Profile)) return 0.0;
    return SampleProfileArray(Profile.HighZUnrealCm, Profile.StepsPerSide, Side, Fraction);
}
inline double SampleGroundLowZ(const FGroundProfile& Profile, int Side, double Fraction)
{
    if (!GroundProfileValid(Profile)) return 0.0;
    return SampleProfileArray(Profile.LowZUnrealCm, Profile.StepsPerSide, Side, Fraction);
}

/** Where one module (or gate, or corner) meets the ground. */
struct FGrounding
{
    /** Z of the module's own origin: its plinth sits here. */
    double BaseZUnrealCm = 0.0;
    /** Bottom of the authored substructure. */
    double FoundationBottomZUnrealCm = 0.0;
    /** BaseZ - FoundationBottomZ; never less than the footing. */
    double FoundationDepthUnrealCm = 0.0;
    /** Extremes of the ground actually sampled under the module. */
    double GroundHighZUnrealCm = 0.0;
    double GroundLowZUnrealCm = 0.0;
    /** False when the profile was unusable and the module fell back to the level plane. */
    bool bFromProfile = false;
};

/** Ground a span of one side, from FromFraction to ToFraction (either order), sampling the
 * profile at Subsamples points inclusive of both ends. FootingUnrealCm is how far below the
 * lowest sampled ground the substructure reaches - a whole amah by default in the actor. */
inline FGrounding GroundSpan(const FGroundProfile& Profile, int Side, double FromFraction, double ToFraction,
                             double FootingUnrealCm, int Subsamples = 9)
{
    FGrounding G;
    const double Footing = std::max(0.0, std::isfinite(FootingUnrealCm) ? FootingUnrealCm : 0.0);
    if (!GroundProfileValid(Profile))
    {
        G.BaseZUnrealCm = 0.0;
        G.FoundationBottomZUnrealCm = -Footing;
        G.FoundationDepthUnrealCm = Footing;
        G.bFromProfile = false;
        return G;
    }
    if (Subsamples < 2) Subsamples = 2;
    const double Lo = std::min(FromFraction, ToFraction);
    const double Hi = std::max(FromFraction, ToFraction);
    double High = -1e300, Low = 1e300;
    for (int Index = 0; Index < Subsamples; ++Index)
    {
        const double F = Lo + (Hi - Lo) * static_cast<double>(Index) / static_cast<double>(Subsamples - 1);
        High = std::max(High, SampleProfileArray(Profile.HighZUnrealCm, Profile.StepsPerSide, Side, F));
        Low = std::min(Low, SampleProfileArray(Profile.LowZUnrealCm, Profile.StepsPerSide, Side, F));
    }
    G.GroundHighZUnrealCm = High;
    G.GroundLowZUnrealCm = Low;
    G.BaseZUnrealCm = High;
    G.FoundationBottomZUnrealCm = Low - Footing;
    G.FoundationDepthUnrealCm = G.BaseZUnrealCm - G.FoundationBottomZUnrealCm;
    G.bFromProfile = true;
    return G;
}

/** Lowest and highest station values of one side, for the report. Returns false on an
 * unusable profile. */
inline bool GroundProfileSideRange(const FGroundProfile& Profile, int Side, double& OutLowZ, double& OutHighZ)
{
    if (!GroundProfileValid(Profile)) return false;
    const int Stations = GroundStationsPerSide(Profile);
    const std::size_t Base = static_cast<std::size_t>(((Side % 4) + 4) % 4) * static_cast<std::size_t>(Stations);
    OutLowZ = 1e300;
    OutHighZ = -1e300;
    for (int Index = 0; Index < Stations; ++Index)
    {
        OutLowZ = std::min(OutLowZ, Profile.LowZUnrealCm[Base + static_cast<std::size_t>(Index)]);
        OutHighZ = std::max(OutHighZ, Profile.HighZUnrealCm[Base + static_cast<std::size_t>(Index)]);
    }
    return true;
}

/** The modules are baked at ProjectCmPerAmah; a level baked at another amah (the 48 cm
 * candidate) scales every module uniformly by this factor so a 25-amah module stays 25 amot. */
inline double ModuleScaleFor(double WorldCmPerAmah)
{
    return (ProjectCmPerAmah > 0.0 && std::isfinite(WorldCmPerAmah)) ? WorldCmPerAmah / ProjectCmPerAmah : 1.0;
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
    /** One authored substructure box under every wall, gate and corner instance. */
    int FoundationInstances = 0;
    long long WallTriangles = 0;
    long long GateTriangles = 0;
    long long CornerTriangles = 0;
    long long OverlayTriangles = 0;
    long long FoundationTriangles = 0;
    long long TotalTriangles = 0;
    int TotalInstances = 0;
};

/** Triangles per module. These are not estimates: they are the counts
 * Scripts/create_enclosure.py actually writes, recorded in
 * SourceAssets/enclosure-review/geometry-manifest.json `meshes[].triangles`, and the export
 * refuses to run if a module comes out different. Keeping them here rather than in the
 * generator is what lets the budget be asserted without an engine or a file read. */
struct FModuleBudget
{
    /** 19 boxes: plinth, body, coping and eight pilasters on each face. */
    int WallSegmentTriangles = 228;
    /** 7 boxes: two piers with jamb orders, lintel, the mass above it, cornice. */
    int GateTriangles = 84;
    /** 6 boxes: plinth, body, coping and a three-step marker pylon. */
    int CornerTriangles = 72;
    /** One thin closed slab, so the overlay band is two-sided and never vanishes as the
     * viewer crosses the line - the moment it is most wanted. */
    int OverlayQuadTriangles = 12;
    /** One plain closed box, scaled per instance to the depth GroundSpan computes. */
    int FoundationTriangles = 12;
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
    Plan.FoundationInstances = Plan.WallInstances + Plan.GateInstances + Plan.CornerInstances;
    Plan.WallTriangles = static_cast<long long>(Plan.WallInstances) * Budget.WallSegmentTriangles;
    Plan.GateTriangles = static_cast<long long>(Plan.GateInstances) * Budget.GateTriangles;
    Plan.CornerTriangles = static_cast<long long>(Plan.CornerInstances) * Budget.CornerTriangles;
    Plan.OverlayTriangles = static_cast<long long>(Plan.OverlayInstances) * Budget.OverlayQuadTriangles;
    Plan.FoundationTriangles = static_cast<long long>(Plan.FoundationInstances) * Budget.FoundationTriangles;
    Plan.TotalTriangles = Plan.WallTriangles + Plan.GateTriangles + Plan.CornerTriangles + Plan.OverlayTriangles
                        + Plan.FoundationTriangles;
    Plan.TotalInstances = Plan.WallInstances + Plan.GateInstances + Plan.CornerInstances + Plan.OverlayInstances
                        + Plan.FoundationInstances;
    return Plan;
}

// ---------------------------------------------------------------------------
// 6b. The plaza - the built deck the precinct encloses
// ---------------------------------------------------------------------------
//
// WHY THERE IS A PLAZA AT ALL. Until 9 September 2026 the YECHEZKEL state hid the modern
// buildings inside the ring and left the raw DEM terrain showing, so the precinct read as a
// bald patch cut out of the city. Shmuel's decision that day was to build it instead:
// "either you put it as a platform, like a flat flat platform that's built out into those
// dimensions to just expand the plaza, or you have to restore the buildings that are there
// now. I would say make it a flat plaza for the dimensions of the area that has call sets,
// that expanded area."
//
// So: A FLAT BUILT DECK ACROSS THE WHOLE 3000-AMAH FOOTPRINT. That decision is the USER'S;
// Yechezkel gives the extent and nothing else. Every dimension below is AUTHORED, and the
// retaining, the paving layout, the channels and the stairs are this project's design.
//
// THE DATUM: THE DECK TOP IS Z 0, THE TEMPLE'S OWN DATUM. Not chosen for tidiness - it is
// the only height at which the deck meets what is already built:
//   * SM_0127_architecture_Outer_court_supporting_platform, the measured outer court
//     supporting platform, has its UNDERSIDE at Z 0 exactly and rises to Z 299 over
//     +-8100 cm (architecture-manifest.json expectedBoundsUnrealCm). A deck any lower
//     leaves a gap under a 162 m square platform; any higher buries its plinth.
//   * The project's own precedent for a built platform on this site, FutureMountV1, put
//     its deck at Z 0 too: every surface vertex in mount-platform.mesh.json is Z = 0.0,
//     with a skirt to 40 m. The plaza is that platform continued to the precinct wall.
//   * That mesh is NOT placed in either Walkthrough map (the Nanite census of 7,519 meshes
//     lists no platform category), so nothing on the deck plane can z-fight it.
// Z 0 is 748.0 m above sea level in this level's frame. The ground under the precinct runs
// from 611.6 m in the Kidron gorge to 810.5 m on the Mount of Olives, so a flat deck at the
// Temple's datum is deep fill on the south and east and a cut on the north-east. Both are
// measured and reported by Scripts/create_precinct_plaza.py; neither is tuned away.
//
// THE GRID IS SET OUT FROM THE TEMPLE, NOT FROM THE WALL. Cells are 25 amot - the same
// module as the wall - stepping from the world origin, so the world axes (which carry the
// north, east and west gates) fall on cell boundaries and a two-cell processional way is
// exactly symmetric about them. The cells at the ring are partial and are scaled to fit.
//
// ANTI-REPETITION. 1.44 km of a 5 m paving tile reads as a grid from the air, which is
// exactly what the decision was made to avoid. Seven devices, all authored, all here so the
// generator and the runtime produce the same layout: irregular super-panels from a frozen
// recursive split (never a lattice); a course direction per panel from a five-value set,
// never equal to the panel west or north of it; per-instance UV origin so no two panels
// start the pattern at the same place; an ashlar rib on every panel joint so the seam is
// deliberate; processional ways in the other approved paving, laid across the direction of
// travel; a channel network on a non-periodic spacing; and a slow tonal drift far coarser
// than the tile.
//
// HOW THE SHADER-SIDE DEVICES REACH THE SHADER, and one hard-won rule. The course direction
// from PlazaPanelCourseIndex, the origin from PlazaPanelUvOriginAmot and the drift from
// PlazaTintAt are baked onto the deck component as five per-instance custom data floats and
// read by M_PrecinctPlaza_Paving with STOCK NODES ONLY. The first version of that material did
// the same arithmetic in two `Custom` nodes of author-written HLSL taking those five floats as
// arguments; it compiled clean in the editor and CRASHED ShaderCompileWorker at cook time with
// an access violation (-1073741819) on FLocalVertexFactory base-pass permutations, failing the
// whole package. Per-instance custom data was NOT at fault - the shipped crowd and vehicle
// materials read it with stock nodes - and neither is a Custom node on its own; the
// combination was. Never put author-written HLSL between per-instance data and the output
// here. See Scripts/release_precinct_plaza.py::build_paving_master for the full account.
//
// -------------------------------------------------------------------------------------
// 6b-ii. WHAT AN SCW ACCESS VIOLATION DOES AND DOES NOT PROVE - added 2026-09-10, after the
// rule above was applied to a material that turned out to be innocent.
//
// Checkpoint cp05 failed the cook with the SAME signature as the plaza: ShaderCompileWorker
// return code -1073741819 (0xC0000005), FLocalVertexFactory, no HLSL diagnostic of any kind,
// every job in the dead worker's batch belonging to one material (M_JudeanFlora_Leaf). Read
// through the lens of the rule above, that looks like an open-and-shut second offence.
// IT WAS NOT THE GRAPH. The leaf material contains no Custom node at all, and a controlled
// experiment cleared it:
//
//   * The material was rebuilt IN PLACE with a byte-identical graph, which gives every
//     expression a fresh FGuid and therefore a fresh shader-map DDC key.
//   * The next cook logged "Missing cached shadermap ... PCD3D_SM6" and "... PCD3D_SM5" for
//     it with NEW key hashes, so the permutations that had crashed were recompiled COLD.
//   * 8,708 / 8,708 packages, "Success - 0 error(s), 0 warning(s)", no crash.
//
// So the generated HLSL was always valid. Three things mislead here, and all three are cheap
// to check before anyone amputates a working feature:
//
//   1. "SCW N Queued Jobs, Unknown number of processed jobs!" means the N jobs listed are the
//      CONTENTS OF THE DEAD WORKER'S BATCH, not N independent failures. Their distribution
//      across vertex and pixel stages is the batch's composition and carries no signal about
//      which stage was at fault. It does tell you which MATERIAL was in flight.
//   2. "Falling back to directly compiling which will be very slow" means the engine
//      recompiled those same jobs IN PROCESS. If a later cook shows NO "Missing cached
//      shadermap" line for that material, every one of its jobs - including the ones printed
//      as Failed - compiled successfully and the shader map is complete in the DDC. That is
//      positive evidence that the HLSL is fine.
//   3. Free RAM at cook START does not discriminate: this box's cook drives available physical
//      memory to 100-500 MB on EVERY run, pass or fail. Memory pressure is therefore a
//      constant across these cooks and cannot by itself explain why one material's worker died
//      and another's did not - but neither does the crash prove the graph is at fault.
//
// THE DISCRIMINATING TEST, and it costs one cook: force a cold shader map for the suspect
// material (rebuild its graph in place so the DDC key changes) and cook again. Compiles cold
// => the graph is valid and the crash was a worker process death; crashes again cold => the
// graph is implicated and the bisect above is the way. Do this BEFORE removing features: on
// cp05 the "fix" would have been to delete per-instance colour variation from 225,780 plants
// to cure a fault that was never in the material.
//
// The plaza rule stands as written - a Custom node fed by per-instance data is still
// forbidden, and rebuilding it without one did fix that cook. What is corrected here is the
// DIAGNOSIS: -1073741819 on its own is the compiler DYING, which is not the same as the
// compiler REJECTING a graph, and only the cold-recompile test tells the two apart.

/** Deck top, in amot ABOVE the Temple court datum. ZERO, and the note above is why: the
 *  measured court supporting platform stands on this plane and the FutureMountV1 platform
 *  deck is this plane. Kept as a named constant rather than a bare 0.0 so that moving the
 *  deck is one edit in one place, with a test that follows it. */
constexpr double PlazaDeckDatumOffsetAmot = 0.0;
/** Deck slab thickness in amot. The underside is never seen: the retaining ring closes the
 *  perimeter and the fill beneath it is not modelled (see the limitation in sources.md). */
constexpr double PlazaSlabThicknessAmot = 1.0;
/** Paving cell, in amot. The wall module, so the plaza and the wall share one setting-out. */
constexpr double PlazaCellAmot = 25.0;
/** Processional way width in amot: two cells. */
constexpr double PlazaWayWidthAmot = 50.0;
/** Drainage channel: a two-amah invert half an amah deep, with lipped rims standing an eighth
 *  of an amah proud of the deck - so no face is ever coplanar with the paving - and lapping a
 *  fifth of an amah over the invert on each side, leaving a 1.6-amah opening. */
constexpr double PlazaChannelWidthAmot = 2.0;
constexpr double PlazaChannelDepthAmot = 0.5;
constexpr double PlazaChannelRimProudAmot = 0.125;
/** The perimeter channel runs this far inside the deck edge. */
constexpr double PlazaPerimeterChannelInsetAmot = 10.0;
/** Panel rib: one amah wide, a quarter proud. */
constexpr double PlazaRibWidthAmot = 1.0;
constexpr double PlazaRibProudAmot = 0.25;
/** Way kerb: one amah wide, half an amah proud. */
constexpr double PlazaKerbWidthAmot = 1.0;
constexpr double PlazaKerbProudAmot = 0.5;
/** Retaining band: one wall module long, five amot high, three amot thick. Bands are NEVER
 *  scaled in Z, because MI_HerodianV4_Ashlar maps v = world Z / 300 cm and a scaled band
 *  would stretch its courses off the world-Z levels every other stone sits on. The lowest
 *  band simply over-runs into the ground, which is free and correct. */
constexpr double PlazaRetainingBandHeightAmot = 5.0;
constexpr double PlazaRetainingBandThicknessAmot = 3.0;
/** BATTER, not setback, and the direction matters. A Herodian retaining wall is widest at
 *  its foot: each course stands a little PROUD of the one above it, so the face leans back
 *  as it rises. The precinct's measured outer face is therefore the face at DECK level - the
 *  3000 amot are measured where the wall stands - and every band below it steps one amah
 *  further out per five bands, 1 in 25. On the 137 m south face that is 5.5 m of spread at
 *  the foot, which is both what a wall that tall needs and what gives the face a horizontal
 *  ledge line every 25 amot of height instead of one unbroken plane.
 *  The scarp on a cut side uses the same function upward: a revetment leans into its hill. */
constexpr int PlazaRetainingBatterEveryBands = 5;
constexpr double PlazaRetainingBatterAmot = 1.0;
/** Monumental stair from the deck up to a gate threshold that stands above it. */
constexpr double PlazaStepRiserAmot = 0.5;
constexpr double PlazaStepTreadAmot = 2.0;
constexpr double PlazaStepWidthAmot = 50.0;
constexpr int PlazaStepsPerFlight = 20;
constexpr double PlazaLandingDepthAmot = 10.0;
/** Super-panel size bounds, in cells. Max must be at least 2*Min - 1 or the split cannot
 *  always terminate; 3 and 8 give panels of 36 m to 96 m a side. */
constexpr int PlazaMinPanelCells = 3;
constexpr int PlazaMaxPanelCells = 8;
/** Chance out of 256 that a panel already inside the size bounds splits again anyway. */
constexpr int PlazaSplitChance256 = 96;
/** Frozen. Changing this re-lays the whole plaza, so it is a constant and not a parameter. */
constexpr std::uint32_t PlazaPanelSeed = 0x5EED5A17u;
/** The five course directions, degrees. Not multiples of 45 alone: 22.5 and 67.5 are what
 *  stop the eye finding the world axes in the field paving. */
constexpr int PlazaCourseCount = 5;
inline double PlazaCourseAngleDegrees(int Index)
{
    static const double Angles[PlazaCourseCount] = {0.0, 22.5, 45.0, 67.5, 90.0};
    return Angles[((Index % PlazaCourseCount) + PlazaCourseCount) % PlazaCourseCount];
}

/** Deck top in level units: the Temple court datum itself. */
inline double PlazaDeckTopZUnrealCm(double WorldCmPerAmah = ProjectCmPerAmah)
{
    return AmotToUnrealCm(PlazaDeckDatumOffsetAmot, WorldCmPerAmah);
}
inline double PlazaDeckUndersideZUnrealCm(double WorldCmPerAmah = ProjectCmPerAmah)
{
    return PlazaDeckTopZUnrealCm(WorldCmPerAmah) - AmotToUnrealCm(PlazaSlabThicknessAmot, WorldCmPerAmah);
}

/** FNV-1a over four bytes. The one hash the generator and the runtime share; if these two
 *  ever disagree the plaza is laid differently in Python and in C++ and every panel moves. */
inline std::uint32_t PlazaHash(std::uint32_t Value)
{
    std::uint32_t H = 2166136261u;
    for (int Byte = 0; Byte < 4; ++Byte)
    {
        H ^= (Value >> (Byte * 8)) & 0xFFu;
        H *= 16777619u;
    }
    return H;
}

/** The paved rectangle and its cell grid, set out from the world origin. Cells run
 *  [I0, I1) x [J0, J1); cell I spans x in [I * Cell, (I+1) * Cell) before clipping, and the
 *  first and last cell on each axis are clipped to the deck edge. */
struct FPlazaGrid
{
    double CellUnrealCm = 0.0;
    int I0 = 0, I1 = 0, J0 = 0, J1 = 0;
    double XMinUnrealCm = 0.0, XMaxUnrealCm = 0.0;
    double YMinUnrealCm = 0.0, YMaxUnrealCm = 0.0;
    double DeckTopZUnrealCm = 0.0;
    int CellsX() const { return I1 - I0; }
    int CellsY() const { return J1 - J0; }
};

/** The deck runs to the INNER face of the wall on every side: on a fill side the retaining
 *  face is coplanar with the precinct's outer face and the wall stands on the deck behind
 *  it; on a cut side the scarp face is the wall's inner face and the wall stands on the
 *  crest. Either way the paving stops one wall thickness inside the square. */
inline FPlazaGrid PlanPlazaGrid(const FSquare& Square, double WallThicknessAmot,
                                double WorldCmPerAmah = ProjectCmPerAmah)
{
    FPlazaGrid Grid;
    const double H = Square.HalfSideUnrealCm;
    const double Inset = AmotToUnrealCm(WallThicknessAmot, WorldCmPerAmah);
    Grid.CellUnrealCm = AmotToUnrealCm(PlazaCellAmot, WorldCmPerAmah);
    if (!(Grid.CellUnrealCm > 0.0) || !(H > 0.0)) return Grid;
    Grid.XMinUnrealCm = Square.CentreUnrealCm.X - H + Inset;
    Grid.XMaxUnrealCm = Square.CentreUnrealCm.X + H - Inset;
    Grid.YMinUnrealCm = Square.CentreUnrealCm.Y - H + Inset;
    Grid.YMaxUnrealCm = Square.CentreUnrealCm.Y + H - Inset;
    Grid.I0 = static_cast<int>(std::floor(Grid.XMinUnrealCm / Grid.CellUnrealCm));
    Grid.I1 = static_cast<int>(std::ceil(Grid.XMaxUnrealCm / Grid.CellUnrealCm));
    Grid.J0 = static_cast<int>(std::floor(Grid.YMinUnrealCm / Grid.CellUnrealCm));
    Grid.J1 = static_cast<int>(std::ceil(Grid.YMaxUnrealCm / Grid.CellUnrealCm));
    Grid.DeckTopZUnrealCm = PlazaDeckTopZUnrealCm(WorldCmPerAmah);
    return Grid;
}

/** The clipped extent of one cell, in world cm. A cell at the ring is a partial cell and the
 *  tile instance is scaled to it, so the paving reaches the wall without overhanging it. */
inline void PlazaCellExtent(const FPlazaGrid& Grid, int I, int J,
                            double& OutX0, double& OutY0, double& OutX1, double& OutY1)
{
    OutX0 = std::max(Grid.XMinUnrealCm, static_cast<double>(I) * Grid.CellUnrealCm);
    OutX1 = std::min(Grid.XMaxUnrealCm, static_cast<double>(I + 1) * Grid.CellUnrealCm);
    OutY0 = std::max(Grid.YMinUnrealCm, static_cast<double>(J) * Grid.CellUnrealCm);
    OutY1 = std::min(Grid.YMaxUnrealCm, static_cast<double>(J + 1) * Grid.CellUnrealCm);
}

/** One super-panel: a rectangle of cells, laid in one course direction. */
struct FPlazaPanel
{
    int I0 = 0, J0 = 0, I1 = 0, J1 = 0;
    std::uint32_t Id = 0u;
};

/** Which super-panel a cell belongs to. A frozen recursive binary split of the whole grid,
 *  NOT a lattice: panel sizes and offsets both vary, which is what makes the plaza read as
 *  laid stone rather than as a checkerboard. Walks down from the root every call, which is
 *  a few dozen integer operations - deliberately stateless so the generator, the runtime
 *  and the test cannot drift apart through a cache. */
inline FPlazaPanel PlazaPanelAt(const FPlazaGrid& Grid, int I, int J)
{
    FPlazaPanel Panel;
    Panel.I0 = Grid.I0; Panel.J0 = Grid.J0; Panel.I1 = Grid.I1; Panel.J1 = Grid.J1;
    if (Grid.CellsX() <= 0 || Grid.CellsY() <= 0) return Panel;
    const int CI = std::max(Grid.I0, std::min(Grid.I1 - 1, I));
    const int CJ = std::max(Grid.J0, std::min(Grid.J1 - 1, J));
    for (int Depth = 0; Depth < 64; ++Depth)
    {
        const int W = Panel.I1 - Panel.I0;
        const int Ht = Panel.J1 - Panel.J0;
        const std::uint32_t Node = PlazaHash(PlazaPanelSeed
            ^ (static_cast<std::uint32_t>(Panel.I0) * 73856093u)
            ^ (static_cast<std::uint32_t>(Panel.J0) * 19349663u)
            ^ (static_cast<std::uint32_t>(W) * 83492791u)
            ^ (static_cast<std::uint32_t>(Ht) * 2654435761u));
        const bool bCanX = (W >= 2 * PlazaMinPanelCells);
        const bool bCanY = (Ht >= 2 * PlazaMinPanelCells);
        const bool bMust = (W > PlazaMaxPanelCells) || (Ht > PlazaMaxPanelCells);
        if (!bCanX && !bCanY) break;
        if (!bMust && static_cast<int>(Node & 255u) >= PlazaSplitChance256) break;
        bool bSplitX = bCanX;
        if (bCanX && bCanY) bSplitX = (W >= Ht);
        if (bMust)
        {
            // The axis that is over size must be the one that splits, when it can be.
            if (W > PlazaMaxPanelCells && bCanX) bSplitX = true;
            else if (Ht > PlazaMaxPanelCells && bCanY) bSplitX = false;
        }
        if (bSplitX)
        {
            const int Span = W - 2 * PlazaMinPanelCells + 1;
            const int Cut = Panel.I0 + PlazaMinPanelCells
                          + static_cast<int>((Node >> 8) % static_cast<std::uint32_t>(Span));
            if (CI < Cut) Panel.I1 = Cut; else Panel.I0 = Cut;
        }
        else
        {
            const int Span = Ht - 2 * PlazaMinPanelCells + 1;
            const int Cut = Panel.J0 + PlazaMinPanelCells
                          + static_cast<int>((Node >> 8) % static_cast<std::uint32_t>(Span));
            if (CJ < Cut) Panel.J1 = Cut; else Panel.J0 = Cut;
        }
    }
    Panel.Id = PlazaHash(PlazaHash(static_cast<std::uint32_t>(Panel.I0) * 2246822519u
                                 ^ static_cast<std::uint32_t>(Panel.J0) * 3266489917u)
                       ^ static_cast<std::uint32_t>(Panel.I1) * 668265263u
                       ^ static_cast<std::uint32_t>(Panel.J1) * 374761393u);
    return Panel;
}

inline bool PlazaSamePanel(const FPlazaPanel& A, const FPlazaPanel& B)
{
    return A.I0 == B.I0 && A.J0 == B.J0 && A.I1 == B.I1 && A.J1 == B.J1;
}

inline int PlazaRawCourseIndex(const FPlazaPanel& Panel)
{
    return static_cast<int>(PlazaHash(Panel.Id ^ 0x9E3779B9u) % static_cast<std::uint32_t>(PlazaCourseCount));
}

/** Course direction for a panel: greedy five-colouring against everything already laid to
 *  its west and north.
 *
 *  Two neighbours laid the same way merge into one bigger panel to the eye, and a run of
 *  them is the grid coming back - so the panel takes the first direction, walking up from
 *  its own hashed preference, that no panel along its west or north joint is using. EVERY
 *  panel on those joints is checked, not just the one at the corner: a panel eight cells
 *  deep can abut four shorter ones, and a match anywhere along the joint is a match.
 *
 *  The neighbours are compared by their OWN hashed preference rather than by their final
 *  colour. Doing otherwise would make each panel's colour depend on its neighbour's, which
 *  depends on its neighbour's, all the way back to the north-west corner - a hundred-deep
 *  recursion per cell, in a function called fourteen thousand times at load. The residual is
 *  a small number of joints where two panels do end up alike; EnclosureMathTest.cpp measures
 *  it rather than assuming it away, and those joints still carry a rib and still start their
 *  paving at different origins, so they do not read as one panel. */
inline int PlazaPanelCourseIndex(const FPlazaGrid& Grid, const FPlazaPanel& Panel)
{
    bool Taken[PlazaCourseCount] = {};
    if (Panel.I0 > Grid.I0)
    {
        for (int J = Panel.J0; J < Panel.J1; ++J)
        {
            Taken[PlazaRawCourseIndex(PlazaPanelAt(Grid, Panel.I0 - 1, J))] = true;
        }
    }
    if (Panel.J0 > Grid.J0)
    {
        for (int I = Panel.I0; I < Panel.I1; ++I)
        {
            Taken[PlazaRawCourseIndex(PlazaPanelAt(Grid, I, Panel.J0 - 1))] = true;
        }
    }
    const int Wanted = PlazaRawCourseIndex(Panel);
    for (int Offset = 0; Offset < PlazaCourseCount; ++Offset)
    {
        const int Candidate = (Wanted + Offset) % PlazaCourseCount;
        if (!Taken[Candidate]) return Candidate;
    }
    // Every direction is already in use along this panel's joints. Keep its own preference
    // rather than picking arbitrarily; the rib and the UV origin still separate it.
    return Wanted;
}

/** Where a panel's paving pattern starts, in amot, so no two panels begin the 5 m tile at
 *  the same place. Two values in [0, 25). */
inline void PlazaPanelUvOriginAmot(const FPlazaPanel& Panel, double& OutU, double& OutV)
{
    const std::uint32_t H = PlazaHash(Panel.Id ^ 0x85EBCA6Bu);
    OutU = static_cast<double>(H & 1023u) / 1024.0 * PlazaCellAmot;
    OutV = static_cast<double>((H >> 10) & 1023u) / 1024.0 * PlazaCellAmot;
}

/** Slow tonal drift, -1..1, at a wavelength far coarser than the tile: value noise on a
 *  lattice of PlazaTintCells cells (about 120 m), smoothstep-interpolated. This is the
 *  variation every photograph of a real esplanade has and a tiled texture never does. */
constexpr int PlazaTintCells = 10;
inline double PlazaTintLatticeValue(int LI, int LJ)
{
    const std::uint32_t H = PlazaHash(static_cast<std::uint32_t>(LI) * 374761393u
                                    ^ static_cast<std::uint32_t>(LJ) * 668265263u ^ 0xC2B2AE35u);
    return static_cast<double>(H & 0xFFFFu) / 32767.5 - 1.0;
}
inline double PlazaTintAt(int I, int J)
{
    const double FX = static_cast<double>(I) / static_cast<double>(PlazaTintCells);
    const double FY = static_cast<double>(J) / static_cast<double>(PlazaTintCells);
    const int LI = static_cast<int>(std::floor(FX));
    const int LJ = static_cast<int>(std::floor(FY));
    // Hermite ease, written out rather than calling SmoothStep01: that lives in section 7,
    // below this one, and the plaza belongs beside the wall it paves.
    const double UX = FX - static_cast<double>(LI);
    const double UY = FY - static_cast<double>(LJ);
    const double TX = UX * UX * (3.0 - 2.0 * UX);
    const double TY = UY * UY * (3.0 - 2.0 * UY);
    const double A = PlazaTintLatticeValue(LI, LJ);
    const double B = PlazaTintLatticeValue(LI + 1, LJ);
    const double C = PlazaTintLatticeValue(LI, LJ + 1);
    const double D = PlazaTintLatticeValue(LI + 1, LJ + 1);
    const double Top = A + (B - A) * TX;
    const double Bottom = C + (D - C) * TX;
    return Top + (Bottom - Top) * TY;
}

/** A processional way: an axis-aligned band of cells from one gate towards the Mount, paved
 *  in the other approved material and laid ACROSS the direction of travel. */
struct FPlazaWay
{
    /** True when the way runs north-south (its band is a range of I). */
    bool bNorthSouth = true;
    int Band0 = 0, Band1 = 0;      // cell indices across the way, [Band0, Band1)
    int Along0 = 0, Along1 = 0;    // cell indices along the way, [Along0, Along1)
    int Gate = 0;                  // index into the gate list, for the receipt
};

/** Cell classes. A way overrides the field paving; nothing else does. There is deliberately
 *  NO hole under the court supporting platform: that platform is a solid box standing on
 *  Z 0, so the deck simply runs under it, costing about 970 tiles of hidden paving (12
 *  triangles each) and buying a deck with no edge condition to get wrong. */
enum class EPlazaCell : int { Deck = 0, Way = 1 };

/** Non-periodic cross-channel spacing, in cells. A periodic spacing is a grid by another
 *  name; this sequence sums to 62 cells over five terms, so it repeats only after 1,550
 *  amot - longer than any run on the plaza. */
inline int PlazaChannelStrideCells(int Index)
{
    static const int Strides[5] = {11, 14, 9, 16, 12};
    return Strides[((Index % 5) + 5) % 5];
}

/** Is there a cross channel on the cell boundary at index K? Walks the stride sequence from
 *  the grid origin so both axes and every consumer agree without storing a list. */
inline bool PlazaHasChannelLine(int Origin, int K, int Limit)
{
    if (K <= Origin || K >= Limit) return false;
    int At = Origin;
    for (int Step = 0; Step < 4096; ++Step)
    {
        At += PlazaChannelStrideCells(Step);
        if (At == K) return true;
        if (At > K || At >= Limit) return false;
    }
    return false;
}

/** Triangles per plaza module, exactly as Scripts/create_precinct_plaza.py writes them.
 *  Same contract as FModuleBudget: the export refuses to run if a module differs. */
struct FPlazaModuleBudget
{
    /** One closed slab, scaled in X and Y for a partial cell at the ring. */
    int DeckTileTriangles = 12;
    /** The same slab in the other approved paving, for the processional ways. */
    int WayTileTriangles = 12;
    /** Panel rib: one closed box standing a quarter of an amah proud. */
    int RibTriangles = 12;
    /** Way kerb: one closed box, scaled in X to its run. */
    int KerbTriangles = 12;
    /** Drainage channel: floor and two rims, three boxes. */
    int ChannelTriangles = 36;
    /** Retaining/scarp band: one closed box, never scaled in Z. */
    int RetainingBandTriangles = 12;
    /** One step, scaled in X to the flight width. */
    int StepTriangles = 12;
};

/** The whole plaza, counted. Mirrors FWallPlan: the generator writes these numbers into
 *  SourceAssets/enclosure-review/plaza-<Target>.json and the release script proves the
 *  placed actor's own build produced exactly them. */
struct FPlazaPlan
{
    int DeckTiles = 0;
    int WayTiles = 0;
    int RibModules = 0;
    int KerbModules = 0;
    int ChannelModules = 0;
    int RetainingBands = 0;
    int ScarpBands = 0;
    int StepModules = 0;
    long long DeckTriangles = 0;
    long long WayTriangles = 0;
    long long RibTriangles = 0;
    long long KerbTriangles = 0;
    long long ChannelTriangles = 0;
    long long RetainingTriangles = 0;
    long long ScarpTriangles = 0;
    long long StepTriangles = 0;
    long long TotalTriangles = 0;
    int TotalInstances = 0;
    /** Tallest retaining and scarp stack on each side, in level units. Reported. */
    double RetainingMaxUnrealCm[4] = {0.0, 0.0, 0.0, 0.0};
    double ScarpMaxUnrealCm[4] = {0.0, 0.0, 0.0, 0.0};
};

inline void PlazaFinishPlan(FPlazaPlan& Plan, const FPlazaModuleBudget& Budget)
{
    Plan.DeckTriangles = static_cast<long long>(Plan.DeckTiles) * Budget.DeckTileTriangles;
    Plan.WayTriangles = static_cast<long long>(Plan.WayTiles) * Budget.WayTileTriangles;
    Plan.RibTriangles = static_cast<long long>(Plan.RibModules) * Budget.RibTriangles;
    Plan.KerbTriangles = static_cast<long long>(Plan.KerbModules) * Budget.KerbTriangles;
    Plan.ChannelTriangles = static_cast<long long>(Plan.ChannelModules) * Budget.ChannelTriangles;
    Plan.RetainingTriangles = static_cast<long long>(Plan.RetainingBands) * Budget.RetainingBandTriangles;
    Plan.ScarpTriangles = static_cast<long long>(Plan.ScarpBands) * Budget.RetainingBandTriangles;
    Plan.StepTriangles = static_cast<long long>(Plan.StepModules) * Budget.StepTriangles;
    Plan.TotalTriangles = Plan.DeckTriangles + Plan.WayTriangles + Plan.RibTriangles + Plan.KerbTriangles
                        + Plan.ChannelTriangles + Plan.RetainingTriangles + Plan.ScarpTriangles
                        + Plan.StepTriangles;
    Plan.TotalInstances = Plan.DeckTiles + Plan.WayTiles + Plan.RibModules + Plan.KerbModules
                        + Plan.ChannelModules + Plan.RetainingBands + Plan.ScarpBands + Plan.StepModules;
}

/** How many fixed-height bands face a drop of HeightUnrealCm. Bands are never scaled in Z,
 *  so the answer is a count and the lowest band over-runs into the ground. */
inline int PlazaBandCount(double HeightUnrealCm, double WorldCmPerAmah = ProjectCmPerAmah)
{
    const double Band = AmotToUnrealCm(PlazaRetainingBandHeightAmot, WorldCmPerAmah);
    if (!(Band > 0.0) || !(HeightUnrealCm > 0.0) || !std::isfinite(HeightUnrealCm)) return 0;
    return static_cast<int>(std::ceil(HeightUnrealCm / Band - 1e-9));
}

/** How far band B stands PROUD of the deck-level face, in level units. B is 0 at the deck
 *  and increases away from it - downward for a retaining stack, upward for a scarp - so the
 *  return value is always the outward offset of that band's face. Never negative: nothing
 *  overhangs. */
inline double PlazaBandBatterUnrealCm(int Band, double WorldCmPerAmah = ProjectCmPerAmah)
{
    if (Band <= 0 || PlazaRetainingBatterEveryBands <= 0) return 0.0;
    const int Steps = Band / PlazaRetainingBatterEveryBands;
    return AmotToUnrealCm(PlazaRetainingBatterAmot * static_cast<double>(Steps), WorldCmPerAmah);
}

/** Wall base with a deck present: the wall stands on whichever is higher, the deck or the
 *  ground OUTSIDE it. On a fill side that is the deck, and the retaining wall carries it;
 *  on a cut side that is the outside grade, and the wall stands on the crest of the scarp
 *  with the plaza a storey below its inner face. With bDeck false this is the old behaviour
 *  exactly, which is why the deck can be switched off without touching the wall code. */
inline double PlazaWallBaseZUnrealCm(double GroundHighZUnrealCm, double DeckTopZUnrealCm, bool bDeck)
{
    return bDeck ? std::max(GroundHighZUnrealCm, DeckTopZUnrealCm) : GroundHighZUnrealCm;
}

/** A flight from the deck up to a gate threshold above it: number of steps, and how many
 *  landings break it. Zero steps when the gate sits on the deck. */
inline int PlazaFlightSteps(double RiseUnrealCm, double WorldCmPerAmah = ProjectCmPerAmah)
{
    const double Riser = AmotToUnrealCm(PlazaStepRiserAmot, WorldCmPerAmah);
    if (!(Riser > 0.0) || !(RiseUnrealCm > 0.0) || !std::isfinite(RiseUnrealCm)) return 0;
    return static_cast<int>(std::ceil(RiseUnrealCm / Riser - 1e-9));
}
inline int PlazaFlightLandings(int Steps)
{
    if (Steps <= PlazaStepsPerFlight) return 0;
    return (Steps - 1) / PlazaStepsPerFlight;
}

/** The five processional ways, two cells wide, from each gate to the court platform.
 *
 *  The grid is set out from the world origin, so the north, east and west gates - which
 *  stand on the Temple's own axes - fall exactly on a cell boundary and their ways are
 *  symmetric about them to the centimetre. The two south gates are at thirds of the south
 *  wall and do NOT fall on a boundary; their bands are snapped to the nearest one, and the
 *  snap is at most half a cell (about 6 m on a 24 m road), which the receipt records per way
 *  rather than leaving a reader to discover it in a screenshot.
 */
inline void MakePlazaWays(const FSquare& Square, const FPlazaGrid& Grid,
                          double CourtHalfExtentUnrealCm, const std::vector<FGateOpening>& Gates,
                          std::vector<FPlazaWay>& OutWays)
{
    OutWays.clear();
    if (!(Grid.CellUnrealCm > 0.0)) return;
    FVec2 Corners[4];
    SquareCorners(Square, Corners);
    const int CourtCells = static_cast<int>(std::ceil(CourtHalfExtentUnrealCm / Grid.CellUnrealCm));
    for (std::size_t Index = 0; Index < Gates.size(); ++Index)
    {
        const FGateOpening& Gate = Gates[Index];
        const int Side = ((Gate.Side % 4) + 4) % 4;
        const FVec2& From = Corners[Side];
        const FVec2& To = Corners[(Side + 1) % 4];
        const FVec2 At{From.X + (To.X - From.X) * Gate.CentreFractionAlongSide,
                       From.Y + (To.Y - From.Y) * Gate.CentreFractionAlongSide};
        FPlazaWay Way;
        Way.Gate = static_cast<int>(Index);
        Way.bNorthSouth = (Side == 0 || Side == 2);
        const double Axis = Way.bNorthSouth ? At.X : At.Y;
        const int Centre = static_cast<int>(std::floor(Axis / Grid.CellUnrealCm + 0.5));
        if (Way.bNorthSouth)
        {
            Way.Band0 = std::max(Grid.I0, Centre - 1);
            Way.Band1 = std::min(Grid.I1, Centre + 1);
            Way.Along0 = (Side == 0) ? Grid.J0 : std::max(Grid.J0, CourtCells);
            Way.Along1 = (Side == 0) ? std::min(Grid.J1, -CourtCells) : Grid.J1;
        }
        else
        {
            Way.Band0 = std::max(Grid.J0, Centre - 1);
            Way.Band1 = std::min(Grid.J1, Centre + 1);
            Way.Along0 = (Side == 1) ? std::max(Grid.I0, CourtCells) : Grid.I0;
            Way.Along1 = (Side == 1) ? Grid.I1 : std::min(Grid.I1, -CourtCells);
        }
        OutWays.push_back(Way);
    }
}

/** Is this cell part of a processional way? Linear over five ways, which is cheaper than any
 *  set for five, and stateless, which is what keeps the generator and the runtime in step. */
inline bool PlazaCellIsWay(const std::vector<FPlazaWay>& Ways, int I, int J)
{
    for (std::size_t Index = 0; Index < Ways.size(); ++Index)
    {
        const FPlazaWay& Way = Ways[Index];
        const int Band = Way.bNorthSouth ? I : J;
        const int Along = Way.bNorthSouth ? J : I;
        if (Band >= Way.Band0 && Band < Way.Band1 && Along >= Way.Along0 && Along < Way.Along1)
        {
            return true;
        }
    }
    return false;
}

/** The ground-INDEPENDENT part of the plaza: how many deck tiles, way tiles, panel ribs,
 *  way kerbs and channel modules the layout produces, and how many distinct super-panels the
 *  frozen split made. Called by the runtime for its readback, by the standalone test, and
 *  mirrored in Scripts/create_precinct_plaza.py; if any two of those three disagree the
 *  plaza is laid differently in the receipt and in the level. */
inline FPlazaPlan PlanPlazaField(const FPlazaGrid& Grid, const std::vector<FPlazaWay>& Ways,
                                 int* OutPanelCount = nullptr, int* OutCulverted = nullptr)
{
    FPlazaPlan Plan;
    if (OutPanelCount != nullptr) *OutPanelCount = 0;
    if (OutCulverted != nullptr) *OutCulverted = 0;
    if (Grid.CellsX() <= 0 || Grid.CellsY() <= 0) return Plan;

    std::vector<unsigned long long> PanelKeys;
    PanelKeys.reserve(2048);
    for (int I = Grid.I0; I < Grid.I1; ++I)
    {
        for (int J = Grid.J0; J < Grid.J1; ++J)
        {
            const FPlazaPanel Panel = PlazaPanelAt(Grid, I, J);
            if (OutPanelCount != nullptr)
            {
                auto Field = [](int Value) { return static_cast<unsigned long long>(static_cast<std::uint32_t>(Value + 1000) & 0xFFFFu); };
                PanelKeys.push_back((Field(Panel.I0) << 48) | (Field(Panel.J0) << 32)
                                  | (Field(Panel.I1) << 16) | Field(Panel.J1));
            }
            if (PlazaCellIsWay(Ways, I, J)) ++Plan.WayTiles; else ++Plan.DeckTiles;
            if (I > Grid.I0 && !PlazaSamePanel(PlazaPanelAt(Grid, I - 1, J), Panel)) ++Plan.RibModules;
            if (J > Grid.J0 && !PlazaSamePanel(PlazaPanelAt(Grid, I, J - 1), Panel)) ++Plan.RibModules;
        }
    }
    if (OutPanelCount != nullptr)
    {
        std::sort(PanelKeys.begin(), PanelKeys.end());
        PanelKeys.erase(std::unique(PanelKeys.begin(), PanelKeys.end()), PanelKeys.end());
        *OutPanelCount = static_cast<int>(PanelKeys.size());
    }

    for (std::size_t Index = 0; Index < Ways.size(); ++Index)
    {
        const FPlazaWay& Way = Ways[Index];
        Plan.KerbModules += 2 * std::max(0, Way.Along1 - Way.Along0);
    }

    // The perimeter ring, then the cross channels. A cross channel is CULVERTED under a
    // processional way rather than cut across it - a road with an open trench in it is not a
    // road - and the omitted modules are counted so the receipt can say how many.
    Plan.ChannelModules += 2 * Grid.CellsX() + 2 * Grid.CellsY();
    for (int K = Grid.I0 + 1; K < Grid.I1; ++K)
    {
        if (!PlazaHasChannelLine(Grid.I0, K, Grid.I1)) continue;
        for (int J = Grid.J0; J < Grid.J1; ++J)
        {
            if (PlazaCellIsWay(Ways, K, J) || PlazaCellIsWay(Ways, K - 1, J))
            {
                if (OutCulverted != nullptr) ++(*OutCulverted);
            }
            else ++Plan.ChannelModules;
        }
    }
    for (int K = Grid.J0 + 1; K < Grid.J1; ++K)
    {
        if (!PlazaHasChannelLine(Grid.J0, K, Grid.J1)) continue;
        for (int I = Grid.I0; I < Grid.I1; ++I)
        {
            if (PlazaCellIsWay(Ways, I, K) || PlazaCellIsWay(Ways, I, K - 1))
            {
                if (OutCulverted != nullptr) ++(*OutCulverted);
            }
            else ++Plan.ChannelModules;
        }
    }
    return Plan;
}

/** The ground-DEPENDENT part: retaining bands where the ground is below the deck, scarp bands
 *  where it is above, and the gate stairs. Adds into Plan so the two halves compose. */
inline void PlanPlazaFaces(const FSquare& Square, const FPlazaGrid& Grid, const FGroundProfile& Profile,
                           int SegmentsPerSide, const std::vector<FGateOpening>& Gates,
                           double WorldCmPerAmah, FPlazaPlan& Plan)
{
    const double SideLength = SquareSideUnrealCm(Square);
    if (!(SideLength > 0.0) || SegmentsPerSide <= 0) return;
    const double DeckZ = Grid.DeckTopZUnrealCm;
    for (int Side = 0; Side < 4; ++Side)
    {
        for (int Step = 0; Step < SegmentsPerSide; ++Step)
        {
            const double F0 = static_cast<double>(Step) / static_cast<double>(SegmentsPerSide);
            const double F1 = static_cast<double>(Step + 1) / static_cast<double>(SegmentsPerSide);
            const FGrounding G = GroundSpan(Profile, Side, F0, F1, 0.0);
            const double Fill = DeckZ - G.GroundLowZUnrealCm;
            if (Fill > 0.0)
            {
                Plan.RetainingBands += PlazaBandCount(Fill, WorldCmPerAmah);
                Plan.RetainingMaxUnrealCm[Side] = std::max(Plan.RetainingMaxUnrealCm[Side], Fill);
            }
            const double Cut = G.GroundHighZUnrealCm - DeckZ;
            if (Cut > 0.0)
            {
                Plan.ScarpBands += PlazaBandCount(Cut, WorldCmPerAmah);
                Plan.ScarpMaxUnrealCm[Side] = std::max(Plan.ScarpMaxUnrealCm[Side], Cut);
            }
        }
    }
    const int LandingUnits = std::max(1, static_cast<int>(std::floor(
        PlazaLandingDepthAmot / PlazaStepTreadAmot + 0.5)));
    const double HalfCell = Grid.CellUnrealCm * 0.5 / SideLength;
    for (std::size_t Index = 0; Index < Gates.size(); ++Index)
    {
        const FGateOpening& Gate = Gates[Index];
        const double T = Gate.CentreFractionAlongSide;
        const FGrounding G = GroundSpan(Profile, Gate.Side, std::max(0.0, T - HalfCell),
                                        std::min(1.0, T + HalfCell), 0.0);
        const double Base = PlazaWallBaseZUnrealCm(G.GroundHighZUnrealCm, DeckZ, true);
        const int Steps = PlazaFlightSteps(Base - DeckZ, WorldCmPerAmah);
        Plan.StepModules += Steps + PlazaFlightLandings(Steps) * LandingUnits;
    }
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
