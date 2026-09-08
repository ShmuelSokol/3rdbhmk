// Standalone test for the shipped people-directory reader: MikdashPeopleDirectory.h.
// Compiled with cl /std:c++17 /W4 /WX and run without Unreal. Asserts stay enabled.
//
// Part one exercises the strict JSON reader. Part two exercises the authored schema, rule
// by rule, by mutating one field of a known-good document at a time. Part three, when the
// runner points MIKDASH_PEOPLE_JSON at it, validates the real authored people.json through
// exactly the code the game uses at startup.
// getenv is only used to locate the authored file the test runner points at.
#define _CRT_SECURE_NO_WARNINGS 1
#include "MikdashPeopleDirectory.h"

#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace
{
bool ParsesJson(const std::string& Text)
{
    MikdashJson::Value Root;
    MikdashJson::Reader Reader;
    return Reader.Parse(Text, Root);
}

void JsonReaderChecks()
{
    MikdashJson::Value Root;
    MikdashJson::Reader Reader;
    std::string Reason;

    assert(Reader.Parse("{\"a\": 1, \"b\": [true, false, null], \"c\": \"x\"}", Root, &Reason));
    assert(Reason.empty());
    assert(Root.IsObject() && Root.Members.size() == 3);
    assert(Root.Member("a") && Root.Member("a")->IsNumber() && Root.Member("a")->Number == 1.0);
    assert(Root.Member("b") && Root.Member("b")->IsArray() && Root.Member("b")->Items.size() == 3);
    assert(Root.Member("b")->Items[0].Type == MikdashJson::Kind::Bool && Root.Member("b")->Items[0].Boolean);
    assert(Root.Member("b")->Items[2].Type == MikdashJson::Kind::Null);
    assert(Root.Member("c")->Text == "x");
    assert(Root.Member("missing") == 0);

    // Numbers, including the negative and exponent forms the waypoints use.
    assert(Reader.Parse("[-2600, 0, 9.5, 1e3, -1.25E-2, 0.0]", Root));
    assert(Root.Items.size() == 6 && Root.Items[0].Number == -2600.0 && Root.Items[3].Number == 1000.0);

    // Escapes, including a surrogate pair, decoded to UTF-8.
    assert(Reader.Parse("[\"a\\\"b\\\\c\\/d\\n\\t\\u0041\\u00e9\\ud83d\\ude00\"]", Root));
    const std::string Decoded = Root.Items[0].Text;
    assert(Decoded.find("a\"b\\c/d\n\tA") == 0);
    assert(Decoded.size() == 10 + 2 + 4); // A, two-byte e-acute, four-byte emoji

    // A UTF-8 byte order mark is tolerated ahead of the value.
    assert(Reader.Parse("\xEF\xBB\xBF{\"version\":\"v\"}", Root) && Root.IsObject());

    // Everything strict about the reader.
    static const char* const Rejected[] = {
        "",                          // empty
        "  ",                        // whitespace only
        "{\"a\":1,}",                // trailing comma in an object
        "[1,]",                      // trailing comma in an array
        "{\"a\":1,\"a\":2}",         // duplicate key
        "{a:1}",                     // unquoted key
        "{'a':1}",                   // single quotes
        "// comment\n{}",            // comment
        "{} {}",                     // trailing document
        "{\"a\":01}",                // leading zero
        "{\"a\":+1}",                // explicit plus
        "{\"a\":.5}",                // no integer part
        "{\"a\":1.}",                // no fraction digits
        "{\"a\":1e}",                // no exponent digits
        "{\"a\":NaN}",               // not JSON
        "{\"a\":Infinity}",          // not JSON
        "{\"a\":\"line\nbreak\"}",   // raw control character
        "{\"a\":\"unterminated",     // unterminated string
        "{\"a\":\"\\q\"}",           // unknown escape
        "{\"a\":\"\\u00\"}",         // truncated escape
        "{\"a\":\"\\ud83d\"}",       // lone high surrogate
        "{\"a\":\"\\ude00\"}",       // lone low surrogate
        "[1",                        // unterminated array
        "{\"a\"1}",                  // missing colon
        "tru",                       // truncated literal
    };
    for (const char* Bad : Rejected)
    {
        assert(!ParsesJson(Bad));
    }

    // Depth is bounded: the value at the bottom counts, so 31 containers around a scalar
    // are accepted and 32 are not.
    const std::string Deep(31, '['), DeepClose(31, ']');
    assert(ParsesJson(Deep + "1" + DeepClose));
    assert(!ParsesJson("[" + Deep + "1" + DeepClose + "]"));
    std::printf("JSON reader: literals, numbers, escapes, surrogates, BOM, strictness and depth checked\n");
}

// ---------------------------------------------------------------------------------------
// A known-good document that every schema check starts from.
// ---------------------------------------------------------------------------------------
std::string Rect(double CX, double CY, double W, double H, double Z)
{
    std::ostringstream Out;
    Out.precision(10);
    const double HW = W / 2.0, HH = H / 2.0;
    const double X[4] = {CX - HW, CX + HW, CX + HW, CX - HW};
    const double Y[4] = {CY - HH, CY - HH, CY + HH, CY + HH};
    static const char* const Pause[4] = {"4", "3", "5", "4"};
    Out << "[";
    for (int I = 0; I < 4; ++I)
    {
        if (I) Out << ",";
        Out << "{\"at\":[" << X[I] << "," << Y[I] << "," << Z << "],"
            << "\"pause\":" << Pause[I] << ","
            << "\"label\":\"Walk the court leg " << I << "\","
            << "\"action\":\"Stand quietly at corner " << I << "\","
            << "\"look\":[0,0," << Z << "]}";
    }
    Out << "]";
    return Out.str();
}

std::string Person(const std::string& Id, const std::string& Name, const std::string& Role,
    const std::string& Zone, const std::string& Route, const std::string& Extra = std::string())
{
    std::ostringstream Out;
    Out << "{\"id\":\"" << Id << "\",\"name\":\"" << Name << "\",\"role\":\"" << Role
        << "\",\"garment\":\"linen-undyed\",\"zone\":\"" << Zone
        << "\",\"mission\":\"Walk the authored circuit and wait with the group.\","
        << "\"dialog\":[\"I came a long way to be here today.\","
        << "\"I am walking the court once before I sit down.\","
        << "\"My household is waiting near the wall for me.\"],"
        << "\"laps\":12,\"route\":" << Route;
    if (!Extra.empty()) Out << "," << Extra;
    Out << "}";
    return Out.str();
}

const char* const BasisPilgrim =
    "\"pilgrim\":{\"decision\":\"Pilgrims walk the outer court floor within the reviewed envelope.\","
    "\"evidence\":[\"Chagigah 1:1 via people-and-city.md:44\"],"
    "\"notClaimed\":[\"No court is given a Second Temple name\"],\"reviewFlag\":\"R\"}";
const char* const BasisVendor =
    "\"vendor\":{\"decision\":\"Vendors stand only on the platform deck outside the walled precinct.\","
    "\"evidence\":[\"No retail marker in the Azarah, people-and-city.md:72\"]}";
const char* const BasisKohen =
    "\"kohen\":{\"decision\":\"Kohanim cross the public floor in transit or off duty, never stationed.\","
    "\"evidence\":[\"Yechezkel 42:13-14 via halacha-and-service.md:50\"]}";

std::string Document(const std::string& Basis, const std::string& People)
{
    return std::string("{\"version\":\"test\",\"note\":\"fixture\",\"placementBasis\":{") + Basis
        + "},\"people\":[" + People + "]}";
}

bool Accepts(const std::string& Text, std::string* Reason = 0)
{
    MikdashPeople::Directory Directory;
    std::string Why;
    const bool Ok = MikdashPeople::ReadDirectoryText(Text, Directory, Why);
    if (Reason) *Reason = Why;
    return Ok;
}

void SchemaChecks()
{
    const std::string OuterRoute = Rect(4250, 1900, 1450, 1700, 300);
    const std::string DeckRoute = Rect(9650, 0, 600, 2500, 0);
    const std::string Good = Document(BasisPilgrim,
        Person("yoav-ben-shimi", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute));
    std::string Reason;
    assert(Accepts(Good, &Reason));
    assert(Reason.empty());

    MikdashPeople::Directory Directory;
    assert(MikdashPeople::ReadDirectoryText(Good, Directory, Reason));
    assert(Directory.Version == "test" && Directory.People.size() == 1);
    assert(Directory.People[0].Route.size() == 4 && Directory.People[0].Laps == 12);
    assert(Directory.People[0].Dialog.size() == 3);
    assert(Directory.BasisFor("pilgrim") && Directory.BasisFor("pilgrim")->Evidence.size() == 1);
    assert(Directory.BasisFor("pilgrim")->ReviewFlag == "R");
    assert(Directory.BasisFor("kohen") == 0);

    // A vendor belongs outside the precinct, and only there.
    const std::string VendorDeck = Document(BasisVendor,
        Person("ovadya-ben-ephrayim", "Ovadya ben Ephrayim", "vendor", "mount-deck", DeckRoute));
    assert(Accepts(VendorDeck));
    const std::string VendorInside = Document(BasisVendor,
        Person("ovadya-ben-ephrayim", "Ovadya ben Ephrayim", "vendor", "outer-court", OuterRoute));
    assert(!Accepts(VendorInside, &Reason));
    assert(Reason.find("vendor") != std::string::npos);

    // A kohen on the public floor must say why he is there.
    const std::string KohenBare = Document(BasisKohen,
        Person("pinchas-ben-achituv", "Pinchas ben Achituv", "kohen", "outer-court", OuterRoute));
    assert(!Accepts(KohenBare, &Reason));
    assert(Reason.find("presence") != std::string::npos);
    const std::string KohenStated = Document(BasisKohen,
        Person("pinchas-ben-achituv", "Pinchas ben Achituv", "kohen", "outer-court", OuterRoute,
            "\"presence\":\"Crossing the public court on the way to his watch; not serving here.\""));
    assert(Accepts(KohenStated, &Reason));

    // Every role used needs its own written basis.
    const std::string MissingBasis = Document(BasisPilgrim,
        Person("pinchas-ben-achituv", "Pinchas ben Achituv", "kohen", "outer-court", OuterRoute,
            "\"presence\":\"Crossing the public court on the way to his watch.\""));
    assert(!Accepts(MissingBasis, &Reason));
    assert(Reason.find("placementBasis") != std::string::npos);

    // Basis entries must carry at least one source reference.
    assert(!Accepts(Document("\"pilgrim\":{\"decision\":\"Pilgrims walk the outer court floor here.\"}",
        Person("yoav-ben-shimi", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute)), &Reason));
    assert(Reason.find("evidence") != std::string::npos);
    assert(!Accepts(Document("\"pilgrim\":{\"decision\":\"too short\",\"evidence\":[\"a reference\"]}",
        Person("yoav-ben-shimi", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute))));
    assert(!Accepts(Document("\"pilgrim\":\"a bare string is not enough\"",
        Person("yoav-ben-shimi", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute))));

    // Identity fields.
    assert(!Accepts(Document(BasisPilgrim, Person("Yoav", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute))));
    assert(!Accepts(Document(BasisPilgrim, Person("-yoav", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute))));
    assert(!Accepts(Document(BasisPilgrim, Person("yo", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute))));
    assert(!Accepts(Document(BasisPilgrim, Person("yoav-ben-shimi", "Y", "pilgrim", "outer-court", OuterRoute))));
    assert(!Accepts(Document(BasisPilgrim, Person("yoav-ben-shimi", "Yoav", "scribe", "outer-court", OuterRoute))));
    assert(!Accepts(Document(BasisPilgrim, Person("yoav-ben-shimi", "Yoav", "pilgrim", "inner-court", OuterRoute))));

    // Duplicate identity across two people.
    const std::string Second = Person("miryam-bas-elyakim", "Miryam bas Elyakim", "pilgrim", "outer-court",
        Rect(2400, 4400, 1450, 1700, 300));
    assert(Accepts(Document(BasisPilgrim,
        Person("yoav-ben-shimi", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute) + "," + Second)));
    assert(!Accepts(Document(BasisPilgrim,
        Person("yoav-ben-shimi", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute) + ","
        + Person("yoav-ben-shimi", "Miryam bas Elyakim", "pilgrim", "outer-court", OuterRoute)), &Reason));
    assert(Reason.find("duplicate person id") != std::string::npos);
    assert(!Accepts(Document(BasisPilgrim,
        Person("yoav-ben-shimi", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute) + ","
        + Person("miryam-bas-elyakim", "Yoav ben Shimi", "pilgrim", "outer-court", OuterRoute)), &Reason));
    assert(Reason.find("duplicate person name") != std::string::npos);

    // Dialog line count and shape.
    std::string TwoLines = Good;
    const std::string ThreeLines =
        "\"dialog\":[\"I came a long way to be here today.\","
        "\"I am walking the court once before I sit down.\","
        "\"My household is waiting near the wall for me.\"]";
    const std::string Replace = [&](const std::string& With) {
        std::string Copy = Good;
        const std::size_t At = Copy.find(ThreeLines);
        assert(At != std::string::npos);
        Copy.replace(At, ThreeLines.size(), With);
        return Copy;
    }("\"dialog\":[\"I came a long way to be here today.\",\"Only two lines here now.\"]");
    assert(!Accepts(Replace, &Reason));
    assert(Reason.find("dialog") != std::string::npos);
    TwoLines = Good;
    {
        const std::size_t At = TwoLines.find(ThreeLines);
        TwoLines.replace(At, ThreeLines.size(), "\"dialog\":[\"short\",\"short\",\"short\"]");
        assert(!Accepts(TwoLines));
    }

    // Laps.
    for (const char* Laps : {"\"laps\":0", "\"laps\":13", "\"laps\":2.5", "\"laps\":\"12\""})
    {
        std::string Copy = Good;
        const std::size_t At = Copy.find("\"laps\":12");
        Copy.replace(At, std::string("\"laps\":12").size(), Laps);
        assert(!Accepts(Copy));
    }

    // Route geometry, delegated to the shipped loop rules.
    struct Case { const char* Why; std::string Route; bool Expect; };
    const Case Cases[] = {
        {"loop far too small", Rect(4250, 1900, 400, 500, 300), false},
        {"loop far too large", Rect(4250, 3000, 4000, 4000, 300), false},
        {"just inside the lower bound", Rect(4250, 1900, 1500, 1500, 300), true},
        {"outside the region in x", Rect(900, 1900, 1450, 1700, 300), false},
        {"across the y=0 corridor", Rect(4250, 0, 1450, 1700, 300), false},
        {"off the floor height", Rect(4250, 1900, 1450, 1700, 500), false},
        {"deck loop at Z 0", Rect(9650, 0, 600, 2500, 0), true},
        {"deck loop at the court floor height", Rect(9650, 0, 600, 2500, 300), false},
    };
    for (const Case& Trial : Cases)
    {
        const bool Ok = Accepts(Document(BasisPilgrim,
            Person("yoav-ben-shimi", "Yoav ben Shimi", "pilgrim",
                std::string(Trial.Why).find("deck") == std::string::npos ? "outer-court" : "mount-deck",
                Trial.Route)));
        assert(Ok == Trial.Expect);
    }

    // Waypoint count and per-waypoint fields.
    assert(!Accepts(Document(BasisPilgrim, Person("yoav-ben-shimi", "Yoav", "pilgrim", "outer-court",
        "[{\"at\":[4000,1900,300],\"pause\":4,\"label\":\"One leg only\",\"action\":\"Stand still\",\"look\":[0,0,300]}]"))));
    {
        std::string Copy = Good;
        const std::size_t At = Copy.find("\"pause\":4");
        Copy.replace(At, std::string("\"pause\":4").size(), "\"pause\":2.5");
        assert(!Accepts(Copy, &Reason));
        assert(Reason.find("pause") != std::string::npos);
    }
    {
        std::string Copy = Good;
        const std::size_t At = Copy.find("\"label\":\"Walk the court leg 0\"");
        Copy.replace(At, std::string("\"label\":\"Walk the court leg 0\"").size(), "\"label\":\"\"");
        assert(!Accepts(Copy));
    }
    {
        std::string Copy = Good;
        const std::size_t At = Copy.find("\"look\":[0,0,300]");
        Copy.replace(At, std::string("\"look\":[0,0,300]").size(), "\"look\":[0,0]");
        assert(!Accepts(Copy));
    }

    // Root shape.
    assert(!Accepts("[]"));
    assert(!Accepts("{\"placementBasis\":{},\"people\":[]}"));
    assert(!Accepts(std::string("{\"version\":\"test\",\"placementBasis\":{") + BasisPilgrim + "},\"people\":[]}"));

    // Zone helpers agree with the schema.
    MikdashPeople::Zone Where = MikdashPeople::Zone::MountDeck;
    assert(MikdashPeople::ZoneFromKey("outer-court", Where) && Where == MikdashPeople::Zone::OuterCourt);
    assert(MikdashPeople::ZoneFromKey("mount-deck", Where) && Where == MikdashPeople::Zone::MountDeck);
    assert(!MikdashPeople::ZoneFromKey("azarah", Where));
    assert(MikdashPeople::ZoneFloorZ(MikdashPeople::Zone::OuterCourt) == 300.0);
    assert(MikdashPeople::ZoneFloorZ(MikdashPeople::Zone::MountDeck) == 0.0);
    assert(MikdashPeople::PointInZone(MikdashPeople::Zone::OuterCourt, MikdashRoute::Point2{4250, 1900}));
    assert(!MikdashPeople::PointInZone(MikdashPeople::Zone::OuterCourt, MikdashRoute::Point2{4250, 500}));
    assert(!MikdashPeople::PointInZone(MikdashPeople::Zone::OuterCourt, MikdashRoute::Point2{9650, 1900}));
    assert(MikdashPeople::PointInZone(MikdashPeople::Zone::MountDeck, MikdashRoute::Point2{9650, 0}));
    assert(!MikdashPeople::PointInZone(MikdashPeople::Zone::MountDeck, MikdashRoute::Point2{9650, 4000}));
    assert(!MikdashPeople::PointInZone(MikdashPeople::Zone::MountDeck, MikdashRoute::Point2{8000, 0}));
    std::printf("Schema: identity, roles, zones, presence, placement basis, dialog, laps and loop rules checked\n");
}

void AuthoredFileChecks()
{
    const char* const Path = std::getenv("MIKDASH_PEOPLE_JSON");
    if (!Path)
    {
        std::printf("Authored people.json: MIKDASH_PEOPLE_JSON not set; synthetic checks only\n");
        return;
    }
    std::ifstream File(Path, std::ios::binary);
    assert(File.good());
    std::ostringstream Buffer;
    Buffer << File.rdbuf();
    MikdashPeople::Directory Directory;
    std::string Reason;
    const bool Ok = MikdashPeople::ReadDirectoryText(Buffer.str(), Directory, Reason);
    if (!Ok) std::printf("Authored people.json rejected: %s\n", Reason.c_str());
    assert(Ok);
    assert(Directory.People.size() == 24);
    std::set<std::string> Garments, Roles;
    std::size_t Deck = 0, Court = 0, Vendors = 0;
    for (std::size_t I = 0; I < Directory.People.size(); ++I)
    {
        const MikdashPeople::Person& Individual = Directory.People[I];
        Garments.insert(Individual.Garment);
        Roles.insert(Individual.Role);
        assert(Individual.Dialog.size() >= 3 && Individual.Dialog.size() <= 5);
        assert(Individual.Route.size() >= 4 && Individual.Route.size() <= 6);
        assert(Directory.BasisFor(Individual.Role) != 0);
        if (Individual.Role == "vendor")
        {
            ++Vendors;
            assert(Individual.Where == MikdashPeople::Zone::MountDeck);
        }
        if (Individual.Role == "kohen" || Individual.Role == "levite")
            assert(!Individual.Presence.empty());
        if (Individual.Where == MikdashPeople::Zone::MountDeck) ++Deck; else ++Court;
        // Every start point must be far enough from every other so bodies do not spawn inside
        // one another; the population also refuses overlapping capsules at startup.
        for (std::size_t J = I + 1; J < Directory.People.size(); ++J)
        {
            const MikdashPeople::Waypoint& A = Individual.Route[0];
            const MikdashPeople::Waypoint& B = Directory.People[J].Route[0];
            const double Gap = MikdashRoute::Distance(MikdashRoute::Point2{A.X, A.Y}, MikdashRoute::Point2{B.X, B.Y});
            assert(Gap >= 150.0);
        }
    }
    assert(Vendors == 3 && Deck == 5 && Court == 19);
    assert(Roles.size() == 6);
    assert(Garments.size() >= 6 && Garments.size() <= 16);
    for (std::size_t I = 0; I < Directory.PlacementBasis.size(); ++I)
        assert(!Directory.PlacementBasis[I].Evidence.empty());
    std::printf("Authored people.json: 24 individuals, %d roles, %d garment variants, %d on the deck, all bases cited\n",
        static_cast<int>(Roles.size()), static_cast<int>(Garments.size()), static_cast<int>(Deck));
}
} // namespace

int main()
{
    JsonReaderChecks();
    SchemaChecks();
    AuthoredFileChecks();
    std::printf("PASS: people directory JSON reader and authored schema\n");
    return 0;
}
