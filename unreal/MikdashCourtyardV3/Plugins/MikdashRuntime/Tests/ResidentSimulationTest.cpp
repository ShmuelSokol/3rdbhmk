#include "ResidentSimulation.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <limits>

using namespace MikdashResidents;

static const Resident& Get(const Simulation& World, const char* Id)
{
    const Resident* Result = World.Find(Id);
    assert(Result);
    return *Result;
}

static void NearFarContinuity()
{
    Simulation Near;
    Simulation Far;
    assert(Near.SetNear("host_rivka", true));
    assert(Near.AdvanceTo(15));
    assert(Far.AdvanceTo(15));
    assert(Near.SetNear("host_rivka", false));
    assert(Near.AdvanceTo(30));
    assert(Far.AdvanceTo(30));
    assert(Near.SetNear("host_rivka", true));
    const Resident& A = Get(Near, "host_rivka");
    const Resident& B = Get(Far, "host_rivka");
    assert(A.Id == B.Id && std::strcmp(A.Name, "Rivka") == 0);
    assert(std::strcmp(A.Personality, B.Personality) == 0);
    assert(A.CompletedCount == 1 && B.CompletedCount == 1);
    assert(A.CompletionSeconds[0] == 30 && B.CompletionSeconds[0] == 30);
    assert(A.TaskIndex == B.TaskIndex && A.RemainingWorkSeconds == B.RemainingWorkSeconds);
    assert(A.State == TaskState::WaitingForSchedule);
    assert(Near.AdvanceTo(59));
    assert(!Near.ConfirmArrival("host_rivka", Location::CityMeeting));
    assert(Near.AdvanceTo(60));
    assert(Get(Near, "host_rivka").State == TaskState::Traveling);
}

static void TravelAndClockConstraints()
{
    Simulation World;
    assert(World.SetRouteAvailable("pilgrim_eliyahu", false));
    assert(!World.ConfirmArrival("pilgrim_eliyahu", Location::CityMeeting));
    assert(World.AdvanceTo(100000));
    const Resident& Waiting = Get(World, "pilgrim_eliyahu");
    assert(Waiting.CurrentLocation == Location::CityHome && Waiting.CompletedCount == 0);
    assert(Waiting.State == TaskState::WaitingForRoute);
    assert(!World.AdvanceTo(99999) && World.Now() == 100000);
    assert(World.SetRouteAvailable("pilgrim_eliyahu", true));
    assert(!World.ConfirmArrival("pilgrim_eliyahu", Location::ServiceWork));
    assert(World.ConfirmArrival("pilgrim_eliyahu", Location::CityMeeting));
    assert(!World.ConfirmArrival("pilgrim_eliyahu", Location::CityMeeting));
    assert(World.AdvanceTo(100029));
    assert(Get(World, "pilgrim_eliyahu").CompletedCount == 0);
    assert(World.AdvanceTo(100030));
    const Resident& Finished = Get(World, "pilgrim_eliyahu");
    assert(Finished.CompletedCount == 1 && Finished.CompletionSeconds[0] == 100030);
    assert(Finished.CurrentLocation == Location::CityMeeting);
    assert(Finished.Destination == Location::PreparationArea && Finished.State == TaskState::Traveling);
    assert(World.AdvanceTo((std::numeric_limits<std::uint64_t>::max)()));
    assert(Get(World, "pilgrim_eliyahu").CompletedCount == 1); // no travel skipped even at max clock
}

static void ServiceAuthorization()
{
    Simulation World;
    assert(!World.SetReviewedServiceAuthorization("pilgrim_eliyahu", true));
    assert(World.ConfirmArrival("kohen_yonatan", Location::PreparationArea));
    assert(World.AdvanceTo(90));
    assert(Get(World, "kohen_yonatan").State == TaskState::WaitingForReview);
    assert(!World.ConfirmArrival("kohen_yonatan", Location::ServiceWork));
    assert(World.AdvanceTo(120));
    assert(Get(World, "kohen_yonatan").CompletedCount == 1);
    assert(World.SetReviewedServiceAuthorization("kohen_yonatan", true));
    assert(World.ConfirmArrival("kohen_yonatan", Location::ServiceWork));
    assert(World.AdvanceTo(140));
    assert(Get(World, "kohen_yonatan").RemainingWorkSeconds == 40);
    assert(World.SetReviewedServiceAuthorization("kohen_yonatan", false));
    assert(World.AdvanceTo(1000));
    assert(Get(World, "kohen_yonatan").RemainingWorkSeconds == 40);
    assert(Get(World, "kohen_yonatan").CompletedCount == 1);
    assert(World.SetReviewedServiceAuthorization("kohen_yonatan", true));
    assert(World.AdvanceTo(1040));
    assert(Get(World, "kohen_yonatan").CompletedCount == 2);
    assert(Get(World, "kohen_yonatan").CompletionSeconds[1] == 1040);
    assert(World.ConfirmArrival("kohen_yonatan", Location::CityMeeting));
    assert(World.AdvanceTo(1070));
    assert(Get(World, "kohen_yonatan").State == TaskState::Complete);
    assert(World.AdvanceTo(5000));
    assert(Get(World, "kohen_yonatan").CompletedCount == 3); // no repeated rewards/memory entries
}

static void DeterminismAndInvalidIds()
{
    Simulation Chunked;
    Simulation Single;
    for (std::uint64_t Second = 0; Second <= 200; ++Second) assert(Chunked.AdvanceTo(Second));
    assert(Single.AdvanceTo(200));
    for (const Resident& A : Chunked.Residents())
    {
        const Resident& B = Get(Single, A.Id);
        assert(A.TaskIndex == B.TaskIndex && A.State == B.State);
        assert(A.CompletedCount == B.CompletedCount && A.CompletionSeconds == B.CompletionSeconds);
        assert(A.RemainingWorkSeconds == B.RemainingWorkSeconds);
    }
    assert(!Single.Find(nullptr) && !Single.Find("unknown"));
    assert(!Single.SetNear(nullptr, true));
    assert(!Single.SetRouteAvailable("unknown", true));
    assert(!Single.SetReviewedServiceAuthorization(nullptr, true));
    assert(!Single.ConfirmArrival("unknown", Location::CityHome));
}

int main()
{
    NearFarContinuity();
    TravelAndClockConstraints();
    ServiceAuthorization();
    DeterminismAndInvalidIds();
    std::cout << "Resident simulation: continuity, clock, travel, authorization and memory checks passed\n";
}
