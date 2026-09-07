#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <locale>
#include <set>
#include <sstream>
#include <string>
#include <vector>

// Standalone C++14 state, with no Unreal, actor, filesystem or rule-authority dependency.
// Adapter owns collision/navigation, exact access review, storage and presentation.
namespace MikdashCrowd
{
using Seconds = std::uint64_t;
enum class SourceRole { Visitor, Owner, Levi, Kohen };

// Exact life.ts NPC placement envelope in source amot. NOT player/journey policy,
// not a swept route test, and not sufficient authorization for any service.
inline bool SourceNpcPointPermitted(SourceRole Role, double X, double Z)
{
    if (!std::isfinite(X) || !std::isfinite(Z)) return false;
    switch (Role)
    {
    case SourceRole::Visitor: return (X >= 34 && X < 50 && std::abs(Z) < 40)
        || (X > 75 && X < 150 && std::abs(Z) < 50);
    case SourceRole::Owner: return X >= 21 && X <= 27 && Z >= -28 && Z <= -22;
    case SourceRole::Levi: return X >= 31.5 && X <= 33 && std::abs(Z) < 40;
    case SourceRole::Kohen: return X > -48 && X < 31 && std::abs(Z) < 49;
    }
    return false;
}

struct Goal
{
    std::string Id, Label, Destination, Action;
    Seconds Earliest = 0, Duration = 1;
};
struct Identity
{
    std::string Id, Name, Start;
    SourceRole Role = SourceRole::Visitor;
    std::vector<Goal> Goals;
};
struct Route
{
    std::string Id, From, To, Resource;
    std::size_t Capacity = 1;
    Seconds Timeout = 120;
};
enum class Phase { Schedule, AccessReview, RouteWait, Traveling, StopRequested, Working, Complete };
struct Person
{
    std::string Id, Location, RouteId;
    std::size_t GoalIndex = 0;
    Seconds Remaining = 0, RouteDeadline = 0, Token = 0;
    bool Access = false, Near = false;
    Phase State = Phase::AccessReview;
    std::vector<Seconds> Completions;
};

class Runtime
{
public:
    // Configuration must be reviewed, stable across save/load, and modest in size.
    // Failure leaves the previous world untouched. IDs are unique, not display names.
    bool Configure(const std::vector<Identity>& Identities, const std::vector<Route>& Routes)
    {
        if (Identities.empty() || Identities.size() > 4096 || Routes.size() > 4096) return false;
        std::set<std::string> Ids;
        for (const Identity& I : Identities)
        {
            if (!TextValid(I.Id) || !TextValid(I.Name) || !TextValid(I.Start)
                || !Ids.insert(I.Id).second || I.Goals.empty() || I.Goals.size() > 64
                || static_cast<unsigned>(I.Role) > 3) return false;
            std::set<std::string> GoalIds;
            Seconds Previous = 0;
            for (const Goal& G : I.Goals)
            {
                if (!TextValid(G.Id) || !TextValid(G.Label) || !TextValid(G.Destination)
                    || !TextValid(G.Action) || G.Duration == 0 || G.Earliest < Previous
                    || !GoalIds.insert(G.Id).second) return false;
                Previous = G.Earliest;
            }
        }
        Ids.clear();
        for (const Route& R : Routes)
        {
            if (!TextValid(R.Id) || !TextValid(R.From) || !TextValid(R.To) || !TextValid(R.Resource)
                || !Ids.insert(R.Id).second || R.From == R.To || R.Capacity == 0
                || R.Capacity > 4096 || R.Timeout == 0) return false;
            for (const Route& Other : Routes)
                if (R.Resource == Other.Resource && R.Capacity != Other.Capacity) return false;
        }
        Definitions = Identities;
        Paths = Routes;
        People.clear();
        Clock = 0; NextToken = 1; Paused = false;
        for (const Identity& I : Definitions)
        {
            Person P;
            P.Id = I.Id; P.Location = I.Start; P.Remaining = I.Goals[0].Duration;
            People.push_back(P);
        }
        for (Person& P : People) Refresh(P);
        return true;
    }

    const std::vector<Person>& Residents() const { return People; }
    const std::vector<Identity>& Plans() const { return Definitions; }
    Seconds Now() const { return Clock; }
    bool IsPaused() const { return Paused; }
    void SetPaused(bool Value) { Paused = Value; }
    const Person* Find(const std::string& Id) const
    {
        for (const Person& P : People) if (P.Id == Id) return &P;
        return nullptr;
    }
    bool SetNear(const std::string& Id, bool Value)
    {
        Person* P = Mutable(Id); if (!P) return false;
        P->Near = Value; return true;
    }
    // Supply only after task-specific mapped route/access review. This grants no
    // purity, service role or journey entitlement. Revocation requests physical stop.
    bool SetAccess(const std::string& Id, bool Value)
    {
        Person* P = Mutable(Id);
        if (!P || P->GoalIndex == Definition(*P).Goals.size()) return false;
        P->Access = Value;
        if (!Value && !P->RouteId.empty()) P->State = Phase::StopRequested;
        else Refresh(*P);
        return true;
    }

    // Call with simulation delta, never wall-clock catch-up after pause. Route timeouts
    // retain reservations until physical stop is acknowledged. No teleport on timeout.
    bool Advance(Seconds Delta)
    {
        if (Paused) return true;
        if (Delta > (std::numeric_limits<Seconds>::max)() - Clock) return false;
        const Seconds End = Clock + Delta;
        for (Person& P : People)
        {
            Refresh(P);
            if (P.State == Phase::Working || (P.State == Phase::Schedule && P.Access
                && P.Location == CurrentGoal(P).Destination))
            {
                const Seconds Begin = (std::max)(Clock, CurrentGoal(P).Earliest);
                const Seconds Available = End > Begin ? End - Begin : 0;
                const Seconds Used = (std::min)(Available, P.Remaining);
                P.Remaining -= Used;
                if (P.Remaining == 0)
                {
                    P.Completions.push_back(Begin + Used);
                    ++P.GoalIndex;
                    P.Access = false; // review each next goal; never inherit authorization
                    if (P.GoalIndex < Definition(P).Goals.size()) P.Remaining = CurrentGoal(P).Duration;
                }
            }
        }
        Clock = End;
        for (Person& P : People)
        {
            if (!P.RouteId.empty() && Clock >= P.RouteDeadline) P.State = Phase::StopRequested;
            Refresh(P);
        }
        return true;
    }

    // Adapter submits only a fully validated path from the last confirmed location.
    // A shared Resource serializes opposite-direction paths through the same doorway.
    // Submission order controls admission; adapter should rotate its waiting queue.
    Seconds Reserve(const std::string& Id, const std::string& RouteId)
    {
        Person* P = Mutable(Id); const Route* R = Path(RouteId);
        if (Paused || !P || !R || P->State != Phase::RouteWait || !P->Access
            || R->From != P->Location || R->To != CurrentGoal(*P).Destination
            || R->Timeout > (std::numeric_limits<Seconds>::max)() - Clock
            || NextToken == (std::numeric_limits<Seconds>::max)()) return 0;
        std::size_t Used = 0;
        for (const Person& Other : People)
        {
            const Route* Occupied = Path(Other.RouteId);
            if (Occupied && Occupied->Resource == R->Resource) ++Used;
        }
        if (Used >= R->Capacity) return 0;
        P->RouteId = R->Id; P->RouteDeadline = Clock + R->Timeout;
        P->Token = NextToken++; P->State = Phase::Traveling;
        return P->Token;
    }
    // Token rejects duplicate/stale callbacks. Adapter must verify capsule, actual
    // destination, entire swept path and current access before this acknowledgment.
    bool Arrive(const std::string& Id, Seconds Token, const std::string& Destination)
    {
        Person* P = Mutable(Id);
        if (Paused || !P || !P->Access || P->State != Phase::Traveling || Token == 0
            || Token != P->Token || Destination != CurrentGoal(*P).Destination) return false;
        P->Location = Destination;
        Release(*P); Refresh(*P); return true;
    }
    // Only after adapter has physically stopped/removed actor and cleared resource.
    // Location stays at last confirmed waypoint, so subsequent navigation must first
    // return there safely (or restore a verified transform at load), never teleport live.
    bool AcknowledgeStopped(const std::string& Id, Seconds Token)
    {
        Person* P = Mutable(Id);
        if (!P || P->RouteId.empty() || Token == 0 || Token != P->Token) return false;
        Release(*P); P->Access = false; P->State = Phase::AccessReview;
        Refresh(*P); return true;
    }

    // Portable text payload; adapter writes atomically to SaveGame/file storage.
    std::string Save() const
    {
        std::ostringstream Out; Out.imbue(std::locale::classic());
        Out << "MIKDASH_CROWD 1 " << Fingerprint() << ' ' << Clock << ' ' << Paused
            << ' ' << NextToken << ' ' << People.size() << '\n';
        for (const Person& P : People)
        {
            Out << std::quoted(P.Id) << ' ' << std::quoted(P.Location) << ' ' << P.GoalIndex
                << ' ' << P.Remaining << ' ' << P.Near << ' ' << P.Completions.size();
            for (Seconds T : P.Completions) Out << ' ' << T;
            Out << '\n';
        }
        return Out.str();
    }
    // Transactional restore into identical reviewed configuration. Transient route
    // reservations and access approvals deliberately expire; adapter must destroy/stop
    // old actors before load, restore confirmed positions and revalidate every task.
    bool Load(const std::string& Data)
    {
        if (People.empty() || Data.size() > 4 * 1024 * 1024) return false;
        std::istringstream In(Data); In.imbue(std::locale::classic());
        std::string Magic; Seconds Version = 0, Hash = 0, NewClock = 0, Pause = 0, Token = 0, Count = 0;
        if (!(In >> Magic) || Magic != "MIKDASH_CROWD" || !Unsigned(In, Version) || Version != 1
            || !Unsigned(In, Hash) || Hash != Fingerprint() || !Unsigned(In, NewClock)
            || !Unsigned(In, Pause) || Pause > 1 || !Unsigned(In, Token) || Token == 0
            || !Unsigned(In, Count) || Count != People.size()) return false;
        std::vector<Person> Restored;
        for (std::size_t Index = 0; Index < People.size(); ++Index)
        {
            Person P; Seconds GoalIndex = 0, Near = 0, Completed = 0;
            if (!(In >> std::quoted(P.Id) >> std::quoted(P.Location)) || P.Id != Definitions[Index].Id
                || !Unsigned(In, GoalIndex) || GoalIndex > Definitions[Index].Goals.size()
                || !Unsigned(In, P.Remaining) || !Unsigned(In, Near) || Near > 1
                || !Unsigned(In, Completed) || Completed != GoalIndex) return false;
            P.GoalIndex = static_cast<std::size_t>(GoalIndex); P.Near = Near != 0;
            const Identity& I = Definitions[Index];
            const std::string Expected = P.GoalIndex == 0 ? I.Start : I.Goals[P.GoalIndex - 1].Destination;
            if (P.Location != Expected && (P.GoalIndex == I.Goals.size()
                || P.Location != I.Goals[P.GoalIndex].Destination)) return false;
            if (P.GoalIndex == I.Goals.size() ? P.Remaining != 0
                : (P.Remaining == 0 || P.Remaining > I.Goals[P.GoalIndex].Duration)) return false;
            if (P.GoalIndex < I.Goals.size() && P.Remaining < I.Goals[P.GoalIndex].Duration
                && P.Location != I.Goals[P.GoalIndex].Destination) return false;
            Seconds Previous = 0;
            for (std::size_t J = 0; J < P.GoalIndex; ++J)
            {
                Seconds T = 0;
                if (!Unsigned(In, T) || T > NewClock || T < Previous || T < I.Goals[J].Earliest
                    || T - I.Goals[J].Earliest < I.Goals[J].Duration
                    || T - Previous < I.Goals[J].Duration) return false;
                P.Completions.push_back(T); Previous = T;
            }
            if (P.GoalIndex < I.Goals.size())
            {
                const Goal& G = I.Goals[P.GoalIndex];
                const Seconds Worked = G.Duration - P.Remaining;
                const Seconds EarliestWork = (std::max)(Previous, G.Earliest);
                if (Worked != 0 && (NewClock < EarliestWork || Worked > NewClock - EarliestWork))
                    return false;
            }
            Restored.push_back(P);
        }
        In >> std::ws; if (!In.eof()) return false;
        People = Restored; Clock = NewClock; Paused = Pause != 0; NextToken = (std::max)(Token, NextToken);
        for (Person& P : People) Refresh(P);
        return true;
    }

private:
    std::vector<Identity> Definitions;
    std::vector<Route> Paths;
    std::vector<Person> People;
    Seconds Clock = 0, NextToken = 1;
    bool Paused = false;
    static bool TextValid(const std::string& S)
    {
        return !S.empty() && S.size() <= 512 && S.find_first_of("\r\n") == std::string::npos;
    }
    static bool Unsigned(std::istream& In, Seconds& Value)
    {
        std::string S; if (!(In >> S) || S.empty() || S.size() > 20) return false;
        Value = 0;
        for (char C : S)
        {
            if (C < '0' || C > '9') return false;
            const Seconds Digit = static_cast<Seconds>(C - '0');
            if (Value > ((std::numeric_limits<Seconds>::max)() - Digit) / 10) return false;
            Value = Value * 10 + Digit;
        }
        return true;
    }
    Person* Mutable(const std::string& Id)
    {
        for (Person& P : People) if (P.Id == Id) return &P;
        return nullptr;
    }
    const Identity& Definition(const Person& P) const
    {
        return Definitions[static_cast<std::size_t>(&P - People.data())];
    }
    const Goal& CurrentGoal(const Person& P) const { return Definition(P).Goals[P.GoalIndex]; }
    const Route* Path(const std::string& Id) const
    {
        for (const Route& R : Paths) if (R.Id == Id) return &R;
        return nullptr;
    }
    static void Release(Person& P) { P.RouteId.clear(); P.Token = 0; P.RouteDeadline = 0; }
    void Refresh(Person& P)
    {
        if (P.State == Phase::StopRequested && !P.RouteId.empty()) return;
        if (P.GoalIndex == Definition(P).Goals.size()) P.State = Phase::Complete;
        else if (!P.Access) P.State = Phase::AccessReview;
        else if (Clock < CurrentGoal(P).Earliest) P.State = Phase::Schedule;
        else if (!P.RouteId.empty()) P.State = Phase::Traveling;
        else if (P.Location == CurrentGoal(P).Destination) P.State = Phase::Working;
        else P.State = Phase::RouteWait;
    }
    Seconds Fingerprint() const
    {
        std::ostringstream S; S.imbue(std::locale::classic());
        for (const Identity& I : Definitions)
        {
            S << std::quoted(I.Id) << std::quoted(I.Name) << std::quoted(I.Start)
                << static_cast<unsigned>(I.Role) << ':' << I.Goals.size() << ';';
            for (const Goal& G : I.Goals) S << std::quoted(G.Id) << std::quoted(G.Label)
                << std::quoted(G.Destination) << std::quoted(G.Action) << G.Earliest << ':' << G.Duration << ';';
        }
        S << '|';
        for (const Route& R : Paths) S << std::quoted(R.Id) << std::quoted(R.From) << std::quoted(R.To)
            << std::quoted(R.Resource) << R.Capacity << ':' << R.Timeout << ';';
        Seconds Hash = 14695981039346656037ULL;
        for (unsigned char C : S.str()) { Hash ^= C; Hash *= 1099511628211ULL; }
        return Hash;
    }
};
} // namespace MikdashCrowd
