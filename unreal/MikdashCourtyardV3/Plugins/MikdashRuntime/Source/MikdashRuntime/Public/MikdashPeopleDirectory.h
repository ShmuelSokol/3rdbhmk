#pragma once
#include "ResidentRouteLoop.h"
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <set>
#include <string>
#include <utility>
#include <vector>

// Engine-independent strict JSON reader and the authored people-directory schema.
//
// Shared by AMikdashResidentPopulation (which reads the staged
// Content/Distribution/People/people.json at startup) and by the standalone tests, so the
// tests exercise the exact parser and the exact rules that ship. There is no Unreal, file
// system, network or locale dependency here: the caller supplies the bytes.
//
// Nothing in this file authorizes anything. It validates authored text against authored
// bounds. Whether a body may physically walk a segment stays with the population actor's
// floor/capsule review. Whether a role belongs in a zone is an authoring decision that the
// directory must state in writing, with a source reference, before this file accepts it.
namespace MikdashJson
{
enum class Kind { Null, Bool, Number, String, Array, Object };

struct Value
{
    Kind Type = Kind::Null;
    bool Boolean = false;
    double Number = 0.0;
    std::string Text;
    std::vector<Value> Items;                              // Array
    std::vector<std::pair<std::string, Value>> Members;    // Object, authored order kept

    const Value* Member(const std::string& Key) const
    {
        for (const auto& Entry : Members) if (Entry.first == Key) return &Entry.second;
        return nullptr;
    }
    bool IsString() const { return Type == Kind::String; }
    bool IsNumber() const { return Type == Kind::Number && std::isfinite(Number); }
    bool IsArray() const { return Type == Kind::Array; }
    bool IsObject() const { return Type == Kind::Object; }
};

/** Strict reader: no comments, no trailing commas, no duplicate keys, no trailing bytes,
 * no NaN or Infinity, raw control characters rejected inside strings, depth and size bounded. */
class Reader
{
public:
    static const std::size_t MaxBytes = 4u * 1024u * 1024u;
    static const int MaxDepth = 32;

    bool Parse(const std::string& Source, Value& Out, std::string* Reason = nullptr)
    {
        Text = &Source; Index = 0; Depth = 0; Error.clear();
        Out = Value();
        if (Source.size() > MaxBytes) return Fail("document larger than 4 MiB", Reason);
        // A UTF-8 byte order mark is tolerated; nothing else may precede the value.
        if (Source.size() >= 3 && static_cast<unsigned char>(Source[0]) == 0xEF
            && static_cast<unsigned char>(Source[1]) == 0xBB
            && static_cast<unsigned char>(Source[2]) == 0xBF) Index = 3;
        if (!ParseValue(Out)) return Fail(Error.c_str(), Reason);
        SkipSpace();
        if (Index != Source.size()) return Fail("trailing characters after the document", Reason);
        if (Reason) Reason->clear();
        return true;
    }

private:
    const std::string* Text = nullptr;
    std::size_t Index = 0;
    int Depth = 0;
    std::string Error;

    bool Fail(const char* Why, std::string* Reason)
    {
        Error = Why;
        if (Reason) *Reason = Error;
        return false;
    }
    bool Reject(const char* Why) { Error = Why; return false; }
    bool AtEnd() const { return Index >= Text->size(); }
    char Peek() const { return (*Text)[Index]; }
    void SkipSpace()
    {
        while (!AtEnd())
        {
            const char C = Peek();
            if (C == ' ' || C == '\t' || C == '\n' || C == '\r') ++Index; else break;
        }
    }
    bool Literal(const char* Word)
    {
        const std::size_t Length = std::string(Word).size();
        if (Text->compare(Index, Length, Word) != 0) return Reject("unknown literal");
        Index += Length;
        return true;
    }

    bool ParseValue(Value& Out)
    {
        if (Depth >= MaxDepth) return Reject("nesting deeper than 32 levels");
        SkipSpace();
        if (AtEnd()) return Reject("unexpected end of document");
        switch (Peek())
        {
        case '{': return ParseObject(Out);
        case '[': return ParseArray(Out);
        case '"': Out.Type = Kind::String; return ParseString(Out.Text);
        case 't': Out.Type = Kind::Bool; Out.Boolean = true; return Literal("true");
        case 'f': Out.Type = Kind::Bool; Out.Boolean = false; return Literal("false");
        case 'n': Out.Type = Kind::Null; return Literal("null");
        default: return ParseNumber(Out);
        }
    }

    bool ParseObject(Value& Out)
    {
        Out.Type = Kind::Object; ++Index; ++Depth;
        SkipSpace();
        if (!AtEnd() && Peek() == '}') { ++Index; --Depth; return true; }
        for (;;)
        {
            SkipSpace();
            if (AtEnd() || Peek() != '"') return Reject("object key must be a string");
            std::string Key;
            if (!ParseString(Key)) return false;
            for (std::size_t I = 0; I < Out.Members.size(); ++I)
                if (Out.Members[I].first == Key) return Reject("duplicate object key");
            SkipSpace();
            if (AtEnd() || Peek() != ':') return Reject("expected a colon after an object key");
            ++Index;
            Value Child;
            if (!ParseValue(Child)) return false;
            if (Out.Members.size() >= 512) return Reject("object has more than 512 members");
            Out.Members.push_back(std::make_pair(Key, Child));
            SkipSpace();
            if (AtEnd()) return Reject("unterminated object");
            if (Peek() == ',') { ++Index; continue; }
            if (Peek() == '}') { ++Index; --Depth; return true; }
            return Reject("expected a comma or a closing brace in an object");
        }
    }

    bool ParseArray(Value& Out)
    {
        Out.Type = Kind::Array; ++Index; ++Depth;
        SkipSpace();
        if (!AtEnd() && Peek() == ']') { ++Index; --Depth; return true; }
        for (;;)
        {
            Value Child;
            if (!ParseValue(Child)) return false;
            if (Out.Items.size() >= 4096) return Reject("array has more than 4096 items");
            Out.Items.push_back(Child);
            SkipSpace();
            if (AtEnd()) return Reject("unterminated array");
            if (Peek() == ',') { ++Index; continue; }
            if (Peek() == ']') { ++Index; --Depth; return true; }
            return Reject("expected a comma or a closing bracket in an array");
        }
    }

    static void AppendUtf8(std::string& Out, unsigned int Code)
    {
        if (Code < 0x80) Out.push_back(static_cast<char>(Code));
        else if (Code < 0x800)
        {
            Out.push_back(static_cast<char>(0xC0 | (Code >> 6)));
            Out.push_back(static_cast<char>(0x80 | (Code & 0x3F)));
        }
        else if (Code < 0x10000)
        {
            Out.push_back(static_cast<char>(0xE0 | (Code >> 12)));
            Out.push_back(static_cast<char>(0x80 | ((Code >> 6) & 0x3F)));
            Out.push_back(static_cast<char>(0x80 | (Code & 0x3F)));
        }
        else
        {
            Out.push_back(static_cast<char>(0xF0 | (Code >> 18)));
            Out.push_back(static_cast<char>(0x80 | ((Code >> 12) & 0x3F)));
            Out.push_back(static_cast<char>(0x80 | ((Code >> 6) & 0x3F)));
            Out.push_back(static_cast<char>(0x80 | (Code & 0x3F)));
        }
    }

    bool Hex4(unsigned int& Out)
    {
        if (Index + 4 > Text->size()) return Reject("truncated unicode escape");
        Out = 0;
        for (int Step = 0; Step < 4; ++Step)
        {
            const char C = (*Text)[Index++];
            unsigned int Digit = 0;
            if (C >= '0' && C <= '9') Digit = static_cast<unsigned int>(C - '0');
            else if (C >= 'a' && C <= 'f') Digit = static_cast<unsigned int>(C - 'a' + 10);
            else if (C >= 'A' && C <= 'F') Digit = static_cast<unsigned int>(C - 'A' + 10);
            else return Reject("non-hexadecimal digit in a unicode escape");
            Out = Out * 16 + Digit;
        }
        return true;
    }

    bool ParseString(std::string& Out)
    {
        Out.clear(); ++Index; // opening quote
        for (;;)
        {
            if (AtEnd()) return Reject("unterminated string");
            const unsigned char C = static_cast<unsigned char>((*Text)[Index]);
            if (C == '"') { ++Index; return true; }
            if (C < 0x20) return Reject("raw control character inside a string");
            if (Out.size() >= 4096) return Reject("string longer than 4096 bytes");
            if (C != '\\') { Out.push_back(static_cast<char>(C)); ++Index; continue; }
            ++Index;
            if (AtEnd()) return Reject("unterminated escape");
            const char Escape = (*Text)[Index++];
            switch (Escape)
            {
            case '"': Out.push_back('"'); break;
            case '\\': Out.push_back('\\'); break;
            case '/': Out.push_back('/'); break;
            case 'b': Out.push_back('\b'); break;
            case 'f': Out.push_back('\f'); break;
            case 'n': Out.push_back('\n'); break;
            case 'r': Out.push_back('\r'); break;
            case 't': Out.push_back('\t'); break;
            case 'u':
            {
                unsigned int Code = 0;
                if (!Hex4(Code)) return false;
                if (Code >= 0xD800 && Code <= 0xDBFF)
                {
                    if (Index + 2 > Text->size() || (*Text)[Index] != '\\' || (*Text)[Index + 1] != 'u')
                        return Reject("high surrogate without its pair");
                    Index += 2;
                    unsigned int Low = 0;
                    if (!Hex4(Low)) return false;
                    if (Low < 0xDC00 || Low > 0xDFFF) return Reject("invalid low surrogate");
                    Code = 0x10000 + ((Code - 0xD800) << 10) + (Low - 0xDC00);
                }
                else if (Code >= 0xDC00 && Code <= 0xDFFF) return Reject("unpaired low surrogate");
                AppendUtf8(Out, Code);
                break;
            }
            default: return Reject("unknown escape sequence");
            }
        }
    }

    bool ParseNumber(Value& Out)
    {
        const std::size_t Start = Index;
        if (!AtEnd() && Peek() == '-') ++Index;
        if (AtEnd() || Peek() < '0' || Peek() > '9') return Reject("number must begin with a digit");
        if (Peek() == '0') ++Index;
        else while (!AtEnd() && Peek() >= '0' && Peek() <= '9') ++Index;
        if (!AtEnd() && Peek() == '.')
        {
            ++Index;
            if (AtEnd() || Peek() < '0' || Peek() > '9') return Reject("a digit is required after the decimal point");
            while (!AtEnd() && Peek() >= '0' && Peek() <= '9') ++Index;
        }
        if (!AtEnd() && (Peek() == 'e' || Peek() == 'E'))
        {
            ++Index;
            if (!AtEnd() && (Peek() == '+' || Peek() == '-')) ++Index;
            if (AtEnd() || Peek() < '0' || Peek() > '9') return Reject("a digit is required in the exponent");
            while (!AtEnd() && Peek() >= '0' && Peek() <= '9') ++Index;
        }
        // The slice is already restricted to the JSON grammar. strtod's only
        // locale-sensitive character is the radix point, and the grammar admits only '.'.
        const std::string Slice = Text->substr(Start, Index - Start);
        Out.Type = Kind::Number;
        Out.Number = std::strtod(Slice.c_str(), 0);
        if (!std::isfinite(Out.Number)) return Reject("number is not finite");
        return true;
    }
};
} // namespace MikdashJson

namespace MikdashPeople
{
using MikdashRoute::Point2;

enum class Zone { OuterCourt, MountDeck };

// Outer court floor: the authored region already used by the reviewed extended route.
// Mount deck: the platform surface near the east gate approach, at Z 0, outside the walled
// precinct. Both are AUTHORING envelopes, not access rulings; the population's floor and
// capsule review remains the only physical evidence that a step is walkable, and no zone
// here is claimed to be a named Second Temple court.
const double MountMinX = 9300.0, MountMaxX = 10000.0, MountMaxAbsY = 3000.0;
const double MountFloorZ = 0.0;

inline double ZoneFloorZ(Zone Where) { return Where == Zone::MountDeck ? MountFloorZ : MikdashRoute::FloorZ; }

inline bool PointInZone(Zone Where, const Point2& P)
{
    if (Where == Zone::OuterCourt) return MikdashRoute::PointInRegion(P);
    return MikdashRoute::Finite(P) && P.X >= MountMinX && P.X <= MountMaxX && std::abs(P.Y) <= MountMaxAbsY;
}

inline bool ZoneFromKey(const std::string& Key, Zone& Out)
{
    if (Key == "outer-court") { Out = Zone::OuterCourt; return true; }
    if (Key == "mount-deck") { Out = Zone::MountDeck; return true; }
    return false;
}
inline const char* ZoneKey(Zone Where) { return Where == Zone::MountDeck ? "mount-deck" : "outer-court"; }

struct Waypoint
{
    double X = 0, Y = 0, Z = 0;
    double PauseSeconds = 0;
    std::string Label, Action;
    double LookX = 0, LookY = 0, LookZ = 0;
};

struct Person
{
    std::string Id, Name, Role, Mission, Garment, Origin, Presence;
    Zone Where = Zone::OuterCourt;
    std::vector<std::string> Dialog;
    std::vector<Waypoint> Route;
    int Laps = 1;
    /** Optional authored body: "body": {"variant": "V3_Pilgrim_Man_Standard", "visualScale": 0.97}.
     * The variant names a registered skeletal body; the scale goes on the skeletal mesh COMPONENT
     * only (never the actor, capsule or amah). Empty variant = the population's default body. */
    std::string BodyVariant;
    double VisualScale = 1.0;
};
// Parser bounds for the authored visual scale; the population applies its own narrower review
// range (0.84..1.04) and falls back to 1.0 with a note outside it.
const double MinVisualScale = 0.5, MaxVisualScale = 1.5;

/** A written, source-referenced reason that a role stands where it is authored to stand. */
struct Placement
{
    std::string Role, Decision, ReviewFlag;
    std::vector<std::string> Evidence, NotClaimed;
};

struct Directory
{
    std::string Version, Note;
    std::vector<Placement> PlacementBasis;
    std::vector<Person> People;

    const Placement* BasisFor(const std::string& Role) const
    {
        for (std::size_t I = 0; I < PlacementBasis.size(); ++I)
            if (PlacementBasis[I].Role == Role) return &PlacementBasis[I];
        return 0;
    }
};

const std::size_t MinPeople = 1, MaxPeople = 64;
const std::size_t MinDialogLines = 3, MaxDialogLines = 5;
const int MinLaps = 1, MaxLaps = 12, MaxGoalsPerPerson = 64;

inline bool RoleKnown(const std::string& Role)
{
    return Role == "pilgrim" || Role == "kohen" || Role == "levite"
        || Role == "host" || Role == "guide" || Role == "vendor";
}

// Commerce does not belong inside the walled precinct: a vendor is authored only on the
// Mount platform deck outside it. A kohen or Levite standing on the public outer-court
// floor must additionally say, in "presence", why he is passing through rather than
// serving, because chamber occupancy and a teaching post are not claimed by this project.
inline bool RoleAllowedInZone(const std::string& Role, Zone Where)
{
    if (Role == "vendor") return Where == Zone::MountDeck;
    return true;
}
inline bool RoleRequiresPresenceNote(const std::string& Role, Zone Where)
{
    return (Role == "kohen" || Role == "levite") && Where == Zone::OuterCourt;
}

inline bool SingleLine(const std::string& S, std::size_t Least, std::size_t Most)
{
    return S.size() >= Least && S.size() <= Most && S.find_first_of("\r\n\t") == std::string::npos;
}

/** Asset-style key: letters, digits, underscores and inner hyphens (e.g. V3_Pilgrim_Man_Standard). */
inline bool AssetKeyValid(const std::string& S, std::size_t Least, std::size_t Most)
{
    if (S.size() < Least || S.size() > Most) return false;
    for (std::size_t I = 0; I < S.size(); ++I)
    {
        const char C = S[I];
        const bool Word = (C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '_';
        if (!Word && !(C == '-' && I != 0 && I + 1 != S.size())) return false;
    }
    return true;
}

inline bool SlugValid(const std::string& S, std::size_t Least, std::size_t Most)
{
    if (S.size() < Least || S.size() > Most) return false;
    for (std::size_t I = 0; I < S.size(); ++I)
    {
        const char C = S[I];
        const bool Alnum = (C >= 'a' && C <= 'z') || (C >= '0' && C <= '9');
        if (!Alnum && !(C == '-' && I != 0 && I + 1 != S.size())) return false;
    }
    return true;
}

/** Validates one authored person and fills Out. Reason carries the first failure. */
inline bool ReadPerson(const MikdashJson::Value& Node, Person& Out, std::string& Reason)
{
    Out = Person();
    if (!Node.IsObject()) { Reason = "person must be an object"; return false; }
    struct Local
    {
        static bool Str(const MikdashJson::Value& N, const char* Key, std::string& Into)
        {
            const MikdashJson::Value* V = N.Member(Key);
            if (!V || !V->IsString()) return false;
            Into = V->Text; return true;
        }
    };
    #define MIKDASH_PEOPLE_FAIL(Why) do { Reason = (Why); return false; } while (false)
    if (!Local::Str(Node, "id", Out.Id) || !SlugValid(Out.Id, 3, 48))
        MIKDASH_PEOPLE_FAIL("id must be 3 to 48 characters of a-z, 0-9 and inner hyphens");
    if (!Local::Str(Node, "name", Out.Name) || !SingleLine(Out.Name, 2, 64))
        MIKDASH_PEOPLE_FAIL("name must be one line of 2 to 64 characters");
    if (!Local::Str(Node, "role", Out.Role) || !RoleKnown(Out.Role))
        MIKDASH_PEOPLE_FAIL("role must be pilgrim, kohen, levite, host, guide or vendor");
    if (!Local::Str(Node, "mission", Out.Mission) || !SingleLine(Out.Mission, 8, 200))
        MIKDASH_PEOPLE_FAIL("mission must be one line of 8 to 200 characters");
    if (!Local::Str(Node, "garment", Out.Garment) || !SlugValid(Out.Garment, 2, 32))
        MIKDASH_PEOPLE_FAIL("garment variant key must be a 2 to 32 character slug");
    if (Node.Member("origin") && (!Local::Str(Node, "origin", Out.Origin) || !SingleLine(Out.Origin, 2, 64)))
        MIKDASH_PEOPLE_FAIL("origin, when present, must be one short line");
    std::string ZoneText;
    if (!Local::Str(Node, "zone", ZoneText) || !ZoneFromKey(ZoneText, Out.Where))
        MIKDASH_PEOPLE_FAIL("zone must be outer-court or mount-deck");
    if (!RoleAllowedInZone(Out.Role, Out.Where))
        MIKDASH_PEOPLE_FAIL("a vendor may only be authored on the mount-deck, never inside the precinct");
    if (Node.Member("presence") && (!Local::Str(Node, "presence", Out.Presence) || !SingleLine(Out.Presence, 8, 160)))
        MIKDASH_PEOPLE_FAIL("presence, when present, must be one line of 8 to 160 characters");
    if (RoleRequiresPresenceNote(Out.Role, Out.Where) && Out.Presence.empty())
        MIKDASH_PEOPLE_FAIL("a kohen or Levite on the outer-court floor must state a presence reason");

    const MikdashJson::Value* Lines = Node.Member("dialog");
    if (!Lines || !Lines->IsArray() || Lines->Items.size() < MinDialogLines || Lines->Items.size() > MaxDialogLines)
        MIKDASH_PEOPLE_FAIL("dialog must be 3 to 5 first-person lines");
    for (std::size_t I = 0; I < Lines->Items.size(); ++I)
    {
        const MikdashJson::Value& Line = Lines->Items[I];
        if (!Line.IsString() || !SingleLine(Line.Text, 12, 300))
            MIKDASH_PEOPLE_FAIL("each dialog line must be one line of 12 to 300 characters");
        Out.Dialog.push_back(Line.Text);
    }

    if (const MikdashJson::Value* Body = Node.Member("body"))
    {
        if (!Body->IsObject()) MIKDASH_PEOPLE_FAIL("body, when present, must be an object {variant, visualScale}");
        if (!Local::Str(*Body, "variant", Out.BodyVariant) || !AssetKeyValid(Out.BodyVariant, 3, 64))
            MIKDASH_PEOPLE_FAIL("body variant must be a 3 to 64 character asset key");
        const MikdashJson::Value* Scale = Body->Member("visualScale");
        if (!Scale || !Scale->IsNumber() || !std::isfinite(Scale->Number)
            || Scale->Number < MinVisualScale || Scale->Number > MaxVisualScale)
            MIKDASH_PEOPLE_FAIL("body visualScale must be a finite number from 0.5 to 1.5");
        Out.VisualScale = Scale->Number;
    }

    const MikdashJson::Value* Laps = Node.Member("laps");
    if (!Laps || !Laps->IsNumber() || Laps->Number != std::floor(Laps->Number)
        || Laps->Number < MinLaps || Laps->Number > MaxLaps)
        MIKDASH_PEOPLE_FAIL("laps must be a whole number from 1 to 12");
    Out.Laps = static_cast<int>(Laps->Number);

    const MikdashJson::Value* Route = Node.Member("route");
    if (!Route || !Route->IsArray() || Route->Items.size() < MikdashRoute::MinPoints
        || Route->Items.size() > MikdashRoute::MaxPoints)
        MIKDASH_PEOPLE_FAIL("route must have 4 to 6 waypoints");
    if (Route->Items.size() * static_cast<std::size_t>(Out.Laps) > static_cast<std::size_t>(MaxGoalsPerPerson))
        MIKDASH_PEOPLE_FAIL("waypoints times laps must not exceed 64 goals");

    std::vector<Point2> Points; std::vector<double> Pauses; std::vector<std::string> Labels;
    for (std::size_t I = 0; I < Route->Items.size(); ++I)
    {
        const MikdashJson::Value& Step = Route->Items[I];
        if (!Step.IsObject()) MIKDASH_PEOPLE_FAIL("waypoint must be an object");
        Waypoint W;
        const MikdashJson::Value* At = Step.Member("at");
        const MikdashJson::Value* Look = Step.Member("look");
        if (!At || !At->IsArray() || At->Items.size() != 3) MIKDASH_PEOPLE_FAIL("waypoint at must be [x, y, z]");
        if (!Look || !Look->IsArray() || Look->Items.size() != 3) MIKDASH_PEOPLE_FAIL("waypoint look must be [x, y, z]");
        for (int K = 0; K < 3; ++K)
        {
            if (!At->Items[K].IsNumber()) MIKDASH_PEOPLE_FAIL("waypoint at must be finite numbers");
            if (!Look->Items[K].IsNumber()) MIKDASH_PEOPLE_FAIL("waypoint look must be finite numbers");
        }
        W.X = At->Items[0].Number; W.Y = At->Items[1].Number; W.Z = At->Items[2].Number;
        W.LookX = Look->Items[0].Number; W.LookY = Look->Items[1].Number; W.LookZ = Look->Items[2].Number;
        const MikdashJson::Value* Pause = Step.Member("pause");
        if (!Pause || !Pause->IsNumber()) MIKDASH_PEOPLE_FAIL("waypoint pause must be a number");
        W.PauseSeconds = Pause->Number;
        const MikdashJson::Value* Label = Step.Member("label");
        const MikdashJson::Value* Action = Step.Member("action");
        if (!Label || !Label->IsString() || !SingleLine(Label->Text, 4, 120))
            MIKDASH_PEOPLE_FAIL("waypoint label must be one short line");
        if (!Action || !Action->IsString() || !SingleLine(Action->Text, 4, 120))
            MIKDASH_PEOPLE_FAIL("waypoint action must be one short line");
        W.Label = Label->Text; W.Action = Action->Text;
        if (!PointInZone(Out.Where, Point2{W.X, W.Y})) MIKDASH_PEOPLE_FAIL("waypoint outside its authored zone");
        if (std::abs(W.Z - ZoneFloorZ(Out.Where)) > MikdashRoute::FloorToleranceCm)
            MIKDASH_PEOPLE_FAIL("waypoint off its zone floor height");
        if (!MikdashRoute::Finite(Point2{W.LookX, W.LookY}) || std::abs(W.LookX) > 40000.0 || std::abs(W.LookY) > 40000.0)
            MIKDASH_PEOPLE_FAIL("look target is implausibly far from the authored world");
        Points.push_back(Point2{W.X, W.Y}); Pauses.push_back(W.PauseSeconds); Labels.push_back(W.Label);
        Out.Route.push_back(W);
    }
    std::string Why;
    // The same closed-loop geometry rule as the shipped extended route: 4 to 6 points,
    // 60 to 120 m around, a 3 to 5 second pause and a readable label at every point, and
    // no two consecutive points closer than two metres.
    if (!MikdashRoute::ValidateLoopGeometry(Points, Pauses, Labels, &Why)) { Reason = Why; return false; }
    Reason.clear();
    return true;
    #undef MIKDASH_PEOPLE_FAIL
}

inline bool ReadPlacement(const std::string& Role, const MikdashJson::Value& Node, Placement& Out, std::string& Reason)
{
    Out = Placement();
    Out.Role = Role;
    if (!RoleKnown(Role)) { Reason = "placementBasis names a role the schema does not know"; return false; }
    if (!Node.IsObject()) { Reason = "each placementBasis entry must be an object"; return false; }
    const MikdashJson::Value* Decision = Node.Member("decision");
    if (!Decision || !Decision->IsString() || Decision->Text.size() < 20 || Decision->Text.size() > 1200)
    { Reason = "placementBasis decision must be 20 to 1200 characters of written reasoning"; return false; }
    Out.Decision = Decision->Text;
    const MikdashJson::Value* Evidence = Node.Member("evidence");
    if (!Evidence || !Evidence->IsArray() || Evidence->Items.empty() || Evidence->Items.size() > 8)
    { Reason = "placementBasis evidence must be 1 to 8 source references"; return false; }
    for (std::size_t I = 0; I < Evidence->Items.size(); ++I)
    {
        if (!Evidence->Items[I].IsString() || !SingleLine(Evidence->Items[I].Text, 8, 300))
        { Reason = "each placementBasis evidence entry must be one short source reference"; return false; }
        Out.Evidence.push_back(Evidence->Items[I].Text);
    }
    const MikdashJson::Value* NotClaimed = Node.Member("notClaimed");
    if (NotClaimed)
    {
        if (!NotClaimed->IsArray() || NotClaimed->Items.size() > 8)
        { Reason = "placementBasis notClaimed must be an array of at most 8 lines"; return false; }
        for (std::size_t I = 0; I < NotClaimed->Items.size(); ++I)
        {
            if (!NotClaimed->Items[I].IsString() || !SingleLine(NotClaimed->Items[I].Text, 8, 300))
            { Reason = "each placementBasis notClaimed entry must be one short line"; return false; }
            Out.NotClaimed.push_back(NotClaimed->Items[I].Text);
        }
    }
    const MikdashJson::Value* Flag = Node.Member("reviewFlag");
    if (Flag)
    {
        if (!Flag->IsString() || !SingleLine(Flag->Text, 1, 200))
        { Reason = "placementBasis reviewFlag, when present, must be one short line"; return false; }
        Out.ReviewFlag = Flag->Text;
    }
    Reason.clear();
    return true;
}

/** Full directory: version, note, one written placement basis per role used, and people. */
inline bool ReadDirectory(const MikdashJson::Value& Root, Directory& Out, std::string& Reason)
{
    Out = Directory();
    if (!Root.IsObject()) { Reason = "document root must be an object"; return false; }
    const MikdashJson::Value* Version = Root.Member("version");
    if (!Version || !Version->IsString() || !SingleLine(Version->Text, 1, 32))
    { Reason = "version must be a short single-line string"; return false; }
    Out.Version = Version->Text;
    const MikdashJson::Value* Note = Root.Member("note");
    if (Note)
    {
        if (!Note->IsString() || Note->Text.size() > 2000)
        { Reason = "note, when present, must be a string of at most 2000 characters"; return false; }
        Out.Note = Note->Text;
    }
    const MikdashJson::Value* Basis = Root.Member("placementBasis");
    if (!Basis || !Basis->IsObject() || Basis->Members.empty())
    { Reason = "placementBasis must record in writing why each role stands where it does"; return false; }
    for (std::size_t I = 0; I < Basis->Members.size(); ++I)
    {
        Placement Entry;
        if (!ReadPlacement(Basis->Members[I].first, Basis->Members[I].second, Entry, Reason)) return false;
        Out.PlacementBasis.push_back(Entry);
    }
    const MikdashJson::Value* People = Root.Member("people");
    if (!People || !People->IsArray() || People->Items.size() < MinPeople || People->Items.size() > MaxPeople)
    { Reason = "people must be an array of 1 to 64 individuals"; return false; }
    std::set<std::string> Ids, Names, Roles;
    for (std::size_t I = 0; I < People->Items.size(); ++I)
    {
        Person Individual;
        if (!ReadPerson(People->Items[I], Individual, Reason)) return false;
        if (!Ids.insert(Individual.Id).second) { Reason = "duplicate person id"; return false; }
        if (!Names.insert(Individual.Name).second) { Reason = "duplicate person name"; return false; }
        Roles.insert(Individual.Role);
        Out.People.push_back(Individual);
    }
    for (std::set<std::string>::const_iterator It = Roles.begin(); It != Roles.end(); ++It)
        if (!Out.BasisFor(*It)) { Reason = "a role is used by a person but has no written placementBasis entry"; return false; }
    Reason.clear();
    return true;
}

/** Convenience: bytes in, validated directory out. */
inline bool ReadDirectoryText(const std::string& Text, Directory& Out, std::string& Reason)
{
    MikdashJson::Value Root;
    MikdashJson::Reader Json;
    if (!Json.Parse(Text, Root, &Reason)) return false;
    return ReadDirectory(Root, Out, Reason);
}
} // namespace MikdashPeople
