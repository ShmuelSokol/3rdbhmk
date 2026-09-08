#pragma once
#include <algorithm>
#include <cmath>
#include <deque>
#include <set>
#include <string>
namespace MikdashTransitCrowd
{
inline int Admission(int Requested, int Active, int GlobalCap, int AtStop, int StopCap)
{
    if (Requested <= 0 || Active < 0 || AtStop < 0) return 0;
    return (std::max)(0, (std::min)(Requested, (std::min)(GlobalCap-Active, StopCap-AtStop)));
}
inline bool Fits(double Distance, double Speed, double Available, double Delay = 0)
{
    return std::isfinite(Distance) && std::isfinite(Speed) && std::isfinite(Available)
        && std::isfinite(Delay) && Distance >= 0 && Distance <= 5000 && Speed > 0 && Delay >= 0
        && Available > Delay && Distance / Speed + Delay + 0.5 < Available;
}
struct Window { double AlightingEnd = 0, BoardingStart = 0, Deadline = 0; };
inline Window ExchangeWindow(double Start, double Duration)
{
    if (!std::isfinite(Start) || !std::isfinite(Duration) || Duration <= 0) return {};
    return {Start + Duration * 0.45, Start + Duration * 0.45, Start + Duration * 0.95};
}
inline std::string Key(const std::string& Route, int Generation, int Vehicle, int Run, int Stop)
{
    return std::to_string(Route.size()) + ":" + Route + ":" + std::to_string(Generation) + ":"
        + std::to_string(Vehicle) + ":" + std::to_string(Run) + ":" + std::to_string(Stop);
}
class RecentKeys
{
    std::set<std::string> Seen;
    std::deque<std::string> Order;
public:
    bool Insert(const std::string& Value)
    {
        if (!Seen.insert(Value).second) return false;
        Order.push_back(Value);
        if (Order.size() > 1024) { Seen.erase(Order.front()); Order.pop_front(); }
        return true;
    }
    void Clear() { Seen.clear(); Order.clear(); }
};
}
