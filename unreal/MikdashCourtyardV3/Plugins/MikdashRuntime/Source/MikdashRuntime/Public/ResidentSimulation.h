#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

// A small authored simulation foundation, not a census or a halachic authority.
// Time, identities and memories live here; a navigation adapter must confirm arrivals.
// Near/far representation never moves, recreates or purifies a resident. State is
// persistent within this object's lifetime; disk saving is not implemented here.
namespace MikdashResidents
{
enum class Role { Host, Pilgrim, Kohen };
enum class Location { CityHome, CityMeeting, PreparationArea, ServiceBoundary, ServiceWork };
enum class TaskState { WaitingForSchedule, WaitingForReview, WaitingForRoute, Traveling, Working, Complete };

inline const char* RoleLabel(Role Value)
{
    switch (Value)
    {
    case Role::Host: return "Host";
    case Role::Pilgrim: return "Pilgrim";
    case Role::Kohen: return "Kohen";
    }
    return "Unknown";
}

inline const char* StateLabel(TaskState Value)
{
    switch (Value)
    {
    case TaskState::WaitingForSchedule: return "Waiting for scheduled time";
    case TaskState::WaitingForReview: return "Waiting for reviewed service authorization";
    case TaskState::WaitingForRoute: return "Waiting for an available route";
    case TaskState::Traveling: return "Awaiting confirmed arrival";
    case TaskState::Working: return "Attending to task";
    case TaskState::Complete: return "Plans completed";
    }
    return "Unknown";
}

struct Task
{
    const char* Id;
    const char* Goal;
    Location Destination;
    std::uint64_t EarliestSecond;
    std::uint64_t DurationSeconds;
    Role RequiredRole;
    bool RequiresReviewedServiceAuthorization;
    const char* SourceContext;
};

struct Resident
{
    const char* Id = "";
    const char* Name = "";
    Role ResidentRole = Role::Pilgrim;
    const char* Personality = "";
    const char* Relationship = "";
    std::array<Task, 3> Tasks{};
    Location CurrentLocation = Location::CityHome;
    Location Destination = Location::CityHome;
    TaskState State = TaskState::WaitingForSchedule;
    const char* GoalLabel = "";
    bool IsNear = false;
    bool RouteAvailable = true;
    bool ReviewedServiceAuthorization = false;
    std::size_t TaskIndex = 0;
    std::uint64_t RemainingWorkSeconds = 0;
    std::size_t CompletedCount = 0;
    std::array<const char*, 3> CompletedTaskIds{{nullptr, nullptr, nullptr}};
    std::array<std::uint64_t, 3> CompletionSeconds{{0, 0, 0}};
};

class Simulation
{
public:
    Simulation()
    {
        // Names, personalities, meeting points and durations are authored fiction.
        // Semantic locations require reviewed geometry mappings before 3D placement.
        People[0] = MakeResident("host_rivka", "Rivka", Role::Host,
            "Warm and attentive; prefers to help without drawing attention.",
            "Hosting Eliyahu's visiting group.", Location::CityHome,
            {{{"host_prepare", "Prepare the meeting place", Location::CityHome, 0, 30, Role::Host, false, "Design; hosting context: Yoma 12a"},
              {"host_meet", "Meet the visiting group", Location::CityMeeting, 60, 45, Role::Host, false, "Design; family rejoicing context: Devarim 16:11"},
              {"host_return", "Return home after welcoming visitors", Location::CityHome, 120, 30, Role::Host, false, "Design"}}});
        People[1] = MakeResident("pilgrim_eliyahu", "Eliyahu", Role::Pilgrim,
            "Thoughtful and curious; checks the plan before proceeding.",
            "Meeting Rivka before his group's preparation.", Location::CityHome,
            {{{"pilgrim_meet", "Find the agreed meeting place", Location::CityMeeting, 0, 30, Role::Pilgrim, false, "Design; pilgrimage context: Chagigah 1:1"},
              {"pilgrim_prepare", "Review the group's preparation plan", Location::PreparationArea, 60, 60, Role::Pilgrim, false, "Design; this task grants no purity or entry status"},
              {"pilgrim_wait", "Wait at the agreed service boundary", Location::ServiceBoundary, 150, 30, Role::Pilgrim, false, "Design; boundary must be mapped and reviewed"}}});
        People[2] = MakeResident("kohen_yonatan", "Yonatan", Role::Kohen,
            "Methodical and quietly encouraging; keeps his assignment in mind.",
            "Preparing for an assigned duty with his watch.", Location::CityHome,
            {{{"kohen_prepare", "Prepare for the duty assignment", Location::PreparationArea, 0, 45, Role::Kohen, false, "Design; duty rotation context: Taanit 4:2"},
              {"kohen_service", "Await the reviewed service assignment", Location::ServiceWork, 90, 60, Role::Kohen, true, "Unreviewed service placeholder; not a modeled avodah"},
              {"kohen_return", "Return to the agreed meeting point", Location::CityMeeting, 180, 30, Role::Kohen, false, "Design; home/duty distinction: Yechezkel 45:4 and Tamid 1:1"}}});
        for (Resident& Person : People) Refresh(Person, 0);
    }

    const std::array<Resident, 3>& Residents() const { return People; }
    std::uint64_t Now() const { return ClockSeconds; }

    const Resident* Find(const char* Id) const
    {
        if (!Id) return nullptr;
        for (const Resident& Person : People)
            if (std::strcmp(Person.Id, Id) == 0) return &Person;
        return nullptr;
    }

    // Monotonic shared simulation clock. Caller freezes it during pause. A clock
    // jump cannot complete travel; only already-arrived eligible work can advance.
    bool AdvanceTo(std::uint64_t Seconds)
    {
        if (Seconds < ClockSeconds) return false;
        for (Resident& Person : People) AdvanceResident(Person, ClockSeconds, Seconds);
        ClockSeconds = Seconds;
        return true;
    }

    bool SetNear(const char* Id, bool Value)
    {
        Resident* Person = FindMutable(Id);
        if (!Person) return false;
        Person->IsNear = Value;
        return true;
    }

    bool SetRouteAvailable(const char* Id, bool Value)
    {
        Resident* Person = FindMutable(Id);
        if (!Person) return false;
        Person->RouteAvailable = Value;
        Refresh(*Person, ClockSeconds);
        return true;
    }

    // Adapter boundary only: an approved rules engine must supply authorization
    // for this particular placeholder assignment. Never bind this to "immersed".
    // Revocation suspends work without discarding prior task memory or progress.
    bool SetReviewedServiceAuthorization(const char* Id, bool Value)
    {
        Resident* Person = FindMutable(Id);
        if (!Person || Person->ResidentRole != Role::Kohen) return false;
        Person->ReviewedServiceAuthorization = Value;
        Refresh(*Person, ClockSeconds);
        return true;
    }

    // A near or far navigation adapter must verify destination arrival and its
    // mapped access rules. The simulation cannot fabricate positional evidence.
    bool ConfirmArrival(const char* Id, Location ArrivedAt)
    {
        Resident* Person = FindMutable(Id);
        if (!Person || Person->State != TaskState::Traveling
            || !Person->RouteAvailable || Person->Destination != ArrivedAt) return false;
        Person->CurrentLocation = ArrivedAt;
        Refresh(*Person, ClockSeconds);
        return Person->State == TaskState::Working;
    }

private:
    std::array<Resident, 3> People{};
    std::uint64_t ClockSeconds = 0;

    static Resident MakeResident(const char* Id, const char* Name, Role ResidentRole,
        const char* Personality, const char* Relationship, Location Start,
        const std::array<Task, 3>& Tasks)
    {
        Resident Result;
        Result.Id = Id;
        Result.Name = Name;
        Result.ResidentRole = ResidentRole;
        Result.Personality = Personality;
        Result.Relationship = Relationship;
        Result.CurrentLocation = Start;
        Result.Tasks = Tasks;
        Result.RemainingWorkSeconds = Tasks[0].DurationSeconds;
        return Result;
    }

    Resident* FindMutable(const char* Id)
    {
        if (!Id) return nullptr;
        for (Resident& Person : People)
            if (std::strcmp(Person.Id, Id) == 0) return &Person;
        return nullptr;
    }

    static void Refresh(Resident& Person, std::uint64_t AtSecond)
    {
        if (Person.TaskIndex == Person.Tasks.size())
        {
            Person.State = TaskState::Complete;
            Person.GoalLabel = "Today's authored plan is complete";
            Person.Destination = Person.CurrentLocation;
            return;
        }
        const Task& Current = Person.Tasks[Person.TaskIndex];
        Person.GoalLabel = Current.Goal;
        Person.Destination = Current.Destination;
        if (Current.RequiredRole != Person.ResidentRole
            || (Current.RequiresReviewedServiceAuthorization && !Person.ReviewedServiceAuthorization))
            Person.State = TaskState::WaitingForReview;
        else if (AtSecond < Current.EarliestSecond)
            Person.State = TaskState::WaitingForSchedule;
        else if (Person.CurrentLocation == Current.Destination)
            Person.State = TaskState::Working;
        else
            Person.State = Person.RouteAvailable ? TaskState::Traveling : TaskState::WaitingForRoute;
    }

    static void AdvanceResident(Resident& Person, std::uint64_t From, std::uint64_t To)
    {
        std::uint64_t Cursor = From;
        // Each iteration either finishes a task or stops, except for one schedule
        // wait per task. This remains bounded for arbitrarily large clock jumps.
        while (Person.TaskIndex < Person.Tasks.size())
        {
            Refresh(Person, Cursor);
            if (Person.State == TaskState::WaitingForSchedule)
            {
                const std::uint64_t Start = Person.Tasks[Person.TaskIndex].EarliestSecond;
                if (Start > To) break;
                Cursor = Start;
                Refresh(Person, Cursor);
            }
            if (Person.State != TaskState::Working) break;
            const std::uint64_t Available = To - Cursor;
            const std::uint64_t Used = Available < Person.RemainingWorkSeconds
                ? Available : Person.RemainingWorkSeconds;
            Person.RemainingWorkSeconds -= Used;
            Cursor += Used;
            if (Person.RemainingWorkSeconds != 0) break;
            Person.CompletedTaskIds[Person.CompletedCount] = Person.Tasks[Person.TaskIndex].Id;
            Person.CompletionSeconds[Person.CompletedCount] = Cursor;
            ++Person.CompletedCount;
            ++Person.TaskIndex;
            if (Person.TaskIndex < Person.Tasks.size())
                Person.RemainingWorkSeconds = Person.Tasks[Person.TaskIndex].DurationSeconds;
        }
        Refresh(Person, To);
    }
};
} // namespace MikdashResidents
